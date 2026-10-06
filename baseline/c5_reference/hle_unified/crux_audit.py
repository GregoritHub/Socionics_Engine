"""Independent C1 reconstruction from raw transactions and access events.

Does not import the movement executor, its content functions, selector, or
runtime indexes. Shared record/geometry definitions are the specification.
"""
from dataclasses import fields, is_dataclass
from . import codec
from .compact import ValuePool, unseal
from .particulars import record_registry, DetailAddress, Particular, Delivery
from .records import Account, Definition, Occurrence, ObjectRef, ClaimStatus
from .material import attrs
from .operations import indexed
from .cognitive_audit import audit as cognitive_audit, audit_extent as cognitive_extent
from .crux_records import RECIPES, definition


def _path(value, path):
    for component in path:
        if type(value) is tuple and component.isdecimal():
            value = value[int(component)]
        elif is_dataclass(value) and component in {f.name for f in fields(value)}:
            value = getattr(value, component)
        else:
            raise ValueError("invalid audited projection path")
    return value


def _access(text, versions, times):
    raw = unseal(text, "hle-unified-u4-access-v1")
    pool = ValuePool(record_registry())
    pool.load_nodes(raw["nodes"])
    grants, revoked, delivered, details, bindings = {}, set(), {}, {}, {}
    used_receipts = set()
    for token in raw["events"]:
        command, result = pool.get(pool.import_token(token))
        method = command[0]
        if method == "grant":
            g = command[1]
            if (g.actor, g.key) in grants:
                raise ValueError("duplicate audit grant")
            source = versions[g.source]
            account = source.facet(Account)
            if account is not None and account.holder not in (None, g.actor):
                raise ValueError("foreign private source")
            grants[g.actor, g.key] = g
        elif method == "revoke":
            revoked.add((command[1], command[2]))
        elif method == "deliver":
            _, actor, key, grant_key, at = command
            g = grants[actor, grant_key]
            if (actor, grant_key) in revoked or (actor, key) in delivered:
                raise ValueError("unavailable or repeated delivery")
            source = versions[g.source]
            expected = Delivery(key, actor, at, g.source, tuple(
                Particular(DetailAddress(key, s.key), s.category, g.source, g.subject,
                    s.path, _path(source, s.path), source.occurrence) for s in g.selectors))
            if expected != result:
                raise ValueError("delivery differs from its exact granted fields")
            delivered[actor, key] = expected
        elif method in ("process", "bind", "acquire"):
            actor, receipt_ref = command[1], command[-1]
            if receipt_ref in used_receipts:
                raise ValueError("receipt consumed twice")
            used_receipts.add(receipt_ref)
            rd = attrs(versions[receipt_ref])
            operation = "read" if method == "process" else method
            if (rd["actor"] != actor or rd["operation"] != operation
                    or rd["spent"] != rd["required"] or rd["completed"] != rd["required"]):
                raise ValueError("access without completed owned work")
            if method == "process":
                d = delivered[actor, command[2]]
                if rd["work_key"] != d.key or indexed(rd, "input.") != (d.source,):
                    raise ValueError("read receipt differs from delivery")
                for p in d.particulars:
                    details[actor, p.address] = p, times[receipt_ref]
            elif method == "bind":
                _, _, ref, addresses, _ = command
                if type(result) is not tuple or len(result) != 2 or result[1].ref != receipt_ref:
                    raise ValueError("binding access event lacks its receipt")
                result = result[0]
                v = versions[ref]
                a, bd = v.facet(Account), attrs(v)
                sources = tuple(dict.fromkeys(details[actor, addr][0].source for addr in addresses))
                if (a.holder != actor or indexed(rd, "input.") != (ref, *sources)
                        or set(sources) != set(a.sources) or rd["work_key"] != ref.identity.key
                        or result.ref != ref or result.actor != actor or result.content != a.content
                        or result.particulars != addresses or result.target != a.referent
                        or result.context != bd["context"] or result.cue != bd["cue"]
                        or result.endorsement.value != bd["endorsement"]
                        or result.receipt != receipt_ref):
                    raise ValueError("retained binding differs from raw paid content")
                bindings[ref] = result, times[receipt_ref]
    return details, bindings


def _extent(d):
    if not d.get("c1"):
        return cognitive_extent(d)
    recipe = RECIPES[d["recipe_key"]]
    if ((d["movement"], d["origin"], d["destination"], d["polarity"], d["material_units"])
            != (recipe.name, recipe.origin, recipe.destination, recipe.polarity, recipe.material_units)):
        raise ValueError("movement differs from its recipe")
    adjusted = dict(d, required=d["required"] - recipe.material_units)
    cognitive_extent(adjusted)


def _atoms(value):
    a = value.facet(Account)
    result = {p.relation: p.object for p in a.content}
    if len(result) != len(a.content):
        raise ValueError("duplicate semantic field")
    return result


def audit(transactions, access_text, *, extent_check=_extent, extended_flags=()):
    transactions = tuple(transactions)
    base = cognitive_audit(transactions, extent_check=extent_check, extended_flags=("c1", *extended_flags))
    versions = {v.ref: v for tx in transactions for v in tx.versions}
    times = {v.ref: tx.at.tick for tx in transactions for v in tx.versions}
    details, bindings = _access(access_text, versions, times)
    starts, chains, prepared, results, owned_outputs = {}, {}, {}, [], set()
    for tx in transactions:
        jobs = [v for v in tx.versions if attrs(v).get("c1")]
        if not jobs:
            continue
        if len(jobs) != 1:
            raise ValueError("ambiguous movement transaction")
        job = jobs[0]
        d = attrs(job)
        identity, actor = job.ref.identity, d["actor"]
        recipe = RECIPES[d["recipe_key"]]
        if identity not in starts:
            if versions[d["recipe"]] != definition(recipe):
                raise ValueError("recipe definition mismatch")
            b, at = bindings[d["source_input"]]
            if b.actor != actor or at >= tx.at.tick or (b.context, b.cue) != (d["context"], d["cue"]):
                raise ValueError("unowned, future or wrongly scoped input")
            if any(other.ref.identity == b.ref.identity and other.ref.revision > b.ref.revision
                   and other_at < tx.at.tick for other, other_at in bindings.values()):
                raise ValueError("superseded input at movement start")
            addresses = tuple(DetailAddress(delivery, d[f"evidence.key.{i}"])
                for i, delivery in enumerate(indexed(d, "evidence.delivery.")))
            paid = [details[actor, addr] for addr in addresses]
            if any(read_at >= tx.at.tick for _, read_at in paid):
                raise ValueError("movement uses future reading")
            if d["recall_units"] != 1 + len(addresses) + len(b.content):
                raise ValueError("recall work differs from inspected content")
            state = {"binding": b, "details": [p for p, _ in paid], "addresses": addresses}
            if recipe.name == "Theorize":
                rules = [p.value for p, _ in paid if p.source == d["rule"] and type(p.value) is Definition]
                if len(rules) != 1:
                    raise ValueError("policy content was not paid-read")
                state["rule"] = {a.name: a.value for a in rules[0].constraints}
            else:
                if b.ref not in owned_outputs:
                    raise ValueError("no prior completed C1 model")
                state["model"] = {p.relation.removeprefix("c1."): p.object for p in b.content}
            if recipe.name == "Embody":
                selected = state["details"][:d["request_evidence_count"]]
                if len({p.source for p in selected}) != 1 or any(p.occurrence != Occurrence.OBSERVATION for p in selected):
                    raise ValueError("comparison needs one coherent observation")
                o = {p.address.key: p.value for p in selected}
                if (o.get("model") != b.ref or o.get("context") != b.context or o.get("primitive") != "inspect"
                        or o.get("outcome") != "succeeded" or o["target"].identity != b.target.identity
                        or o["target"].revision < b.target.revision):
                    raise ValueError("trial scope mismatch")
                event = versions[o["event"]]
                ed = attrs(event)
                observation = versions[selected[0].source]
                if (event.occurrence != Occurrence.ACTUAL_EVENT or ed.get("movement") != "Apply"
                        or ed.get("actor") != actor or ed.get("model") != b.ref
                        or observation.ref.identity.namespace != "u4.observation"
                        or observation.facet(Account).sources != (event.ref,)):
                    raise ValueError("comparison lacks actual native trial provenance")
                if (attrs(observation) != {k:v for k,v in ed.items() if not k.startswith("participant.")}
                        or observation.facet(Account).content != event.facet(Account).content
                        or observation.facet(Account).referent != event.facet(Account).referent
                        or observation.facet(Account).holder != actor):
                    raise ValueError("observation rewrites its actual trial event")
                state["observed"] = o
            starts[identity], prepared[identity], chains[identity] = d, state, []
        start, p, chain = starts[identity], prepared[identity], chains[identity]
        for k, value in start.items():
            if k not in {"completed", "spent", "status", "failure", "result", "steps_completed", "last_step", "binding"} and d[k] != value:
                raise ValueError("immutable movement input or contract changed")
        threshold = d["recall_units"]
        thresholds = []
        for i in range(len(recipe.steps)):
            threshold += sum(indexed(d, f"route.{i}.charges.")) + d[f"route.{i}.content_units"]
            thresholds.append(threshold)
        for step in (v for v in tx.versions if v.ref.identity.namespace == "c1.step"):
            sd, a = attrs(step), step.facet(Account)
            i = len(chain)
            if (i >= len(recipe.steps) or sd["index"] != i or sd["step"] != recipe.steps[i]
                    or sd["operation"] != job.previous or a.holder != actor
                    or sd["paid_threshold"] != thresholds[i] or d["completed"] < thresholds[i]
                    or sd["predecessor"] != (start["source_input"] if not chain else chain[-1].ref)
                    or (sd["origin"], sd["destination"], sd["polarity"])
                    != (d[f"route.{i}.origin"], d[f"route.{i}.destination"], recipe.polarity)):
                raise ValueError("unpaid or disconnected semantic step")
            b = p["binding"]
            if sd["step"] == "hypothesize":
                possibilities = {codec.dumps(c.object): c.object for c in b.content
                    if c.relation == "condition" and c.subject == b.target and c.context == b.context and c.scope.end is None}
                if b.endorsement in (ClaimStatus.DISPUTED, ClaimStatus.RETRACTED):
                    possibilities = {}
                expected_value = next(iter(possibilities.values())) if len(possibilities) == 1 else None
                expected = {"expected": expected_value, "test": "inspect", "relation": "condition",
                    "status": "tentative" if expected_value is not None else "unknown",
                    "on_serviceable": p["rule"]['when."serviceable"'], "on_damaged": p["rule"]['when."damaged"'],
                    "default": p["rule"]["default"]}
                target, kind = b.target, "model"
            elif sd["step"] == "instantiate":
                expected = {"primitive": p["model"]["test"], "expected": p["model"]["expected"],
                    "relation": p["model"]["relation"], "model": b.ref}
                target, kind = b.target, "trial"
            elif sd["step"] == "compare":
                m, o = p["model"], p["observed"]
                assessment = "untested" if m["expected"] is None else (
                    "supported_in_case" if m["expected"] == o["condition"] else "contradicted_in_case")
                expected = {"expected": m["expected"], "observed": o["condition"],
                    "comparison": assessment, "event": o["event"]}
                target, kind = o["target"], "assessment"
            else:
                comparison = _atoms(chain[-1])
                expected = {"condition": comparison["observed"], "status": "supported",
                            "tension": comparison["comparison"]}
                target, kind = chain[-1].facet(Account).referent, "personal"
            if (sd["content_kind"] != kind or a.referent != target or codec.dumps(tuple(sorted(_atoms(step).items()))) != codec.dumps(tuple(sorted(expected.items())))
                    or any(c.subject != target or c.context != b.context for c in a.content)):
                raise ValueError("semantic content differs from accessible input transformation")
            chain.append(step)
        if d["steps_completed"] != sum(t <= d["completed"] for t in thresholds) or len(chain) != d["steps_completed"]:
            raise ValueError("paid semantic output omitted or duplicated")
        if d["last_step"] != (None if not chain else chain[-1].ref):
            raise ValueError("movement points to wrong semantic result")
        if d["status"] == "succeeded":
            if len(chain) != len(recipe.steps):
                raise ValueError("incomplete semantic result")
            if recipe.name == "Apply":
                trial = _atoms(chain[-1])
                ed = attrs(versions[d["result"]])
                if (d["primitive"] != trial["primitive"] or d["target"] != chain[-1].facet(Account).referent
                        or ed["model"] != trial["model"] or ed["trial"] != chain[-1].ref):
                    raise ValueError("material event bypassed the generated trial")
                output = d["result"]
            else:
                output = d["binding"]
                bound = versions[output].facet(Account)
                actual = {c.relation: c.object for c in bound.content}
                last = _atoms(chain[-1])
                expected = {"c1." + k: v for k, v in last.items()} if recipe.name == "Theorize" else {"condition": last["condition"]}
                if (codec.dumps(tuple(sorted(actual.items()))) != codec.dumps(tuple(sorted(expected.items()))) or bound.holder != actor
                        or bound.referent != chain[-1].facet(Account).referent):
                    raise ValueError("retained result did not consume final semantic content")
                if recipe.name == "Theorize":
                    owned_outputs.add(output)
            results.append({"movement": recipe.name, "polarity": recipe.polarity,
                "input": codec.encode(d["source_input"]), "output": codec.encode(output),
                "semantic_steps": [codec.encode(s.ref) for s in chain], "paid_work": d["spent"],
                "material_work": recipe.material_units})
    base.update(c1_movements=len(results), c1_semantic_steps=sum(len(c) for c in chains.values()),
                c1_results=results, exact_access_reconstructed=True)
    return base
