"""Independent FB4.2 workflow-parent and route-face reconstruction.

Imports no executor, selection policy, scheduler, or test fixture.  The accepted
workflow auditor validates every ordinary workflow operation first; this module
then reconstructs only the new bounded parent and the paired face claims.
"""
from .workflow_audit import audit as workflow_audit
from .workflow_reference import encode, decode
from .workflow_nesting_records import PARENT_RECIPE, definition
from .crux_audit import _access
from .cognitive_audit import audit_extent
from .material import attrs
from .operations import indexed
from .records import Account, Occurrence
from .particulars import DetailAddress


FACE_RESPONSIBILITY = {
    "Contemplate": ("status", "differentiated", "rehearsed", "content"),
    "Express": ("mode", "readiness", "performance", "usable output"),
    "Share": ("status", "examined", "contribution", "interaction"),
    "Theorize": ("status", "hypothesis", "submitted", "content"),
    "Embody": ("status", "interpretation", "decision_policy", "content"),
    "Act": ("mode", "readiness", "performance", "usable output"),
    "Coordinate": ("status", "examined", "contribution", "interaction"),
    "Organize": ("status", "dependency_hypothesis", "operating", "usable output"),
    "Identify": ("status", "interpretation", "decision_policy", "commitment"),
    "Mobilize": ("mode", "readiness", "performance", "usable output"),
    "Commune": ("status", "examined", "renewed", "commitment"),
    "Institutionalize": ("status", "draft", "ratified", "commitment"),
    "Understand": ("status", "interpretation", "decision_policy", "content"),
    "Apply": ("mode", "trial", "performance", "usable output"),
    "Educate": ("status", "examined", "contribution", "interaction"),
    "Integrate": ("status", "reconciled", "coupled", "content"),
}


def _payload(version):
    account = version.facet(Account)
    if account is None:
        return decode(attrs(version)["payload"])
    if len(account.content) != 1 or account.content[0].relation not in ("c7w.data", "c7n.data", "payload"):
        raise ValueError("exact workflow or parent payload required")
    return decode(account.content[0].object)


def extent(d):
    from .workflow_audit import extent as workflow_extent
    if not d.get("c7n"):
        return workflow_extent(d)
    r = PARENT_RECIPE
    if (d["movement"], d["origin"], d["destination"], d["polarity"], d["material_units"], d["route_count"]) != (r.name, r.origin, r.destination, r.polarity, 0, 2):
        raise ValueError("workflow parent formal contract differs")
    if tuple(d[f"route.{i}.element"][0] for i in range(2)) != ("n", "n"):
        raise ValueError("workflow parent Fold differs")
    audit_extent(d)


def _versions(transactions):
    versions = {}; heads = {}
    for tx in transactions:
        for value in tx.versions:
            versions[value.ref] = value; heads[value.ref.identity] = value
    return versions, heads


def audit_parent(transactions, access_text):
    txs = tuple(transactions)
    report = workflow_audit(txs, access_text, extent_check=extent, extended_flags=("c7n",))
    versions, final_heads = _versions(txs)
    times = {v.ref: tx.at.tick for tx in txs for v in tx.versions}
    details, bindings = _access(access_text, versions, times)
    heads = {}; starts = {}; prepared = {}; chains = {}; results = []; terminals = []
    for tx in txs:
        for job in (v for v in tx.versions if attrs(v).get("c7n")):
            d = attrs(job); ident = job.ref.identity; actor = d["actor"]
            if ident not in starts:
                if versions[d["recipe"]] != definition():
                    raise ValueError("workflow parent recipe altered")
                addresses = tuple(DetailAddress(v, d[f"evidence.key.{i}"])
                    for i, v in enumerate(indexed(d, "evidence.delivery.")))
                paid = [details[actor, a] for a in addresses]
                if len(set(addresses)) != len(addresses) or any(at >= tx.at.tick for _, at in paid):
                    raise ValueError("future or repeated parent evidence")
                sources = tuple(dict.fromkeys(p.source for p, _ in paid))
                claims = decode(d["children_payload"]); children = claims["children"]; links = claims["links"]
                refs = indexed(d, "source.")
                if not 1 <= len(children) <= 8 or refs != tuple(x[1] for x in children) or len({x[0].identity for x in children}) != len(children):
                    raise ValueError("invalid workflow child declaration")
                if len(set(links)) != len(links) or any(not 0 <= a < b < len(children) for a, b in links):
                    raise ValueError("invalid workflow child DAG")
                values = []; rows = []; operations = {}; depth = 1
                for (operation, output) in children:
                    child = attrs(versions[operation])
                    receipt = {p.address.key: p.value for p, _ in paid if p.source == operation}
                    if any(k not in receipt or receipt[k] != child.get(k) for k in ("actor", "context", "status", "spent", "result")):
                        raise ValueError("child operation receipt not paid-read")
                    if (operation.identity.namespace != "u4.operation" or final_heads[operation.identity].ref != operation
                            or child.get("actor") != actor or child.get("context") != d["context"]
                            or not (child.get("c7w") or child.get("c7n"))
                            or child.get("status") not in ("succeeded", "failed", "cancelled")):
                        raise ValueError("unavailable terminal workflow child")
                    if child.get("content_target", child.get("target")).identity != d["content_target"].identity:
                        raise ValueError("workflow child target differs")
                    if output.identity.namespace == "u4.observation":
                        selected = [p for p, _ in paid if p.source == output]
                        value = {p.address.key: p.value for p in selected}
                        if value.get("event") != child["result"] or value.get("context") != d["context"]:
                            raise ValueError("wrong child event observation")
                        value = dict(value, kind="child_event")
                    else:
                        if output not in bindings:
                            raise ValueError("unretained workflow child output")
                        binding, at = bindings[output]
                        if binding.actor != actor or binding.context != d["context"] or binding.target.identity != d["content_target"].identity or at >= tx.at.tick:
                            raise ValueError("foreign or future child output")
                        value = _payload(versions[output])
                    if output.identity.namespace != "u4.observation" and output not in (child.get("binding"), *indexed(child, "public.")):
                        raise ValueError("wrong workflow child output")
                    require_inherited = child["status"] == "succeeded" and output.identity.namespace != "u4.observation"
                    if operation not in indexed(d, "dependency.") or require_inherited and any(x not in indexed(d, "dependency.") for x in indexed(child, "dependency.")):
                        raise ValueError("lost child or transitive dependency")
                    fulfilled = child["status"] == "succeeded" and value.get("complete", True) and value.get("status") not in ("declined", "blocked")
                    rows.append((operation, output, child["status"], child["origin"], child["destination"],
                                 actor, child["polarity"], fulfilled, child["movement"]))
                    operations[operation] = child["spent"]
                    if value.get("kind") == "workflow_parent":
                        depth = max(depth, value["depth"] + 1)
                        for ref, spent in value["operations"]:
                            if ref in operations and operations[ref] != spent:
                                raise ValueError("inconsistent duplicate descendant charge")
                            operations[ref] = spent
                    values.append(value)
                if depth > 4 or len(operations) > 64:
                    raise ValueError("workflow nesting budget exceeded")
                for left, right in links:
                    ca, cb = children[left], children[right]
                    da, db = attrs(versions[ca[0]]), attrs(versions[cb[0]])
                    if da["destination"] != db["origin"] or ca[1] not in indexed(db, "source."):
                        raise ValueError("disconnected workflow child handoff")
                operations = tuple(sorted(operations.items(), key=lambda x: (x[0].identity.namespace, x[0].identity.key, x[0].revision)))
                complete = all(row[7] for row in rows)
                wanted = dict(kind="workflow_parent", target=d["content_target"], context=d["context"],
                    children=children, links=links, outcomes=tuple(rows), complete=complete,
                    status="complete" if complete else "blocked", depth=depth, operations=operations,
                    cited_spending=sum(n for _, n in operations), polarities=tuple(row[6] for row in rows),
                    competence=False, executable=False, authority=None, group=d["group"])
                units = 1 + len(addresses) + sum(1 + len(encode(v)) // 64 for v in values) + len(operations)
                if d["recall_units"] != units:
                    raise ValueError("unpaid workflow parent evidence")
                starts[ident] = d; prepared[ident] = (wanted, sources); chains[ident] = []
            wanted, sources = prepared[ident]; chain = chains[ident]
            mutable = {"completed", "spent", "status", "failure", "result", "steps_completed", "last_step", "binding"}
            if any(d[k] != value for k, value in starts[ident].items() if k not in mutable):
                raise ValueError("workflow parent inputs changed during review")
            threshold = d["recall_units"]; thresholds = []
            for i in range(2):
                threshold += sum(indexed(d, f"route.{i}.charges.")) + d[f"route.{i}.content_units"]
                thresholds.append(threshold)
            for step in (v for v in tx.versions if v.ref.identity.namespace == "c7n.step"):
                i = len(chain); sd = attrs(step); account = step.facet(Account)
                if (i >= 2 or (sd["index"], sd["step"], sd["operation"], sd["recipe"], sd["content_kind"], sd["paid_threshold"], sd["predecessor"]) !=
                        (i, PARENT_RECIPE.steps[i], job.previous, PARENT_RECIPE.ref, "c7n", thresholds[i], chain[-1].ref if chain else d["source_input"])):
                    raise ValueError("invalid paid workflow parent handoff")
                if account.holder != actor or account.referent != d["content_target"] or account.sources != (sd["predecessor"], *sources):
                    raise ValueError("workflow parent meaning scope differs")
                correct = dict(kind="reviewed_children", content=encode(wanted)) if i == 0 else wanted
                if _payload(step) != correct:
                    raise ValueError("workflow parent semantic postcondition differs")
                chain.append(step)
            if len(chain) != d["steps_completed"] or len(chain) != sum(x <= d["completed"] for x in thresholds):
                raise ValueError("missing paid workflow parent content")
            if d["status"] == "succeeded":
                if len(chain) != 2 or any(final_heads[x.identity].ref != x for x in indexed(d, "dependency.")):
                    raise ValueError("stale or unfinished workflow parent completed")
                output = d["binding"]
                if output not in bindings or _payload(versions[output]) != wanted or versions[output].occurrence != Occurrence.INTERPRETATION:
                    raise ValueError("unjustified workflow parent output")
                if wanted["competence"] or wanted["executable"] or wanted["authority"] is not None:
                    raise ValueError("workflow parent summary grants capacity")
                results.append(dict(output=output, complete=wanted["complete"], status=wanted["status"],
                                    operations=len(wanted["operations"]), cited_spending=wanted["cited_spending"]))
            if d["status"] in ("succeeded", "failed", "cancelled"):
                terminals.append(dict(status=d["status"], failure=d.get("failure")))
        heads.update({v.ref.identity: v for v in tx.versions})
    report.update(workflow_parent_attempts=len(starts), workflow_parent_completed=len(results),
        workflow_parent_results=results, workflow_parent_terminals=terminals,
        workflow_parent_independent_content_check=True)
    return report


def _face_world(transactions, access_text, route, face):
    report = workflow_audit(tuple(transactions), access_text)
    versions, heads = _versions(transactions)
    jobs = {attrs(v).get("key"): attrs(v) for v in heads.values() if attrs(v).get("c7w")}
    main = jobs.get("case")
    if main is None or (main["movement"], main["polarity"], main["status"]) != (route, face, "succeeded"):
        raise ValueError("missing requested route face")
    value = _payload(versions[main["last_step"]])
    consumer = jobs.get("case-consumer")
    if consumer is None or consumer["status"] != "succeeded" or not consumer.get("binding"):
        raise ValueError("fixed downstream workflow query missing")
    answer = _payload(versions[consumer["binding"]])
    return report, main, value, (answer.get("next_task"), answer.get("next_action"),
        answer.get("responsible"), answer.get("feasible"), answer.get("authorized"), answer.get("status"))


def audit_face_pair(accumulation_transactions, accumulation_access,
                    expenditure_transactions, expenditure_access, route):
    if route not in FACE_RESPONSIBILITY:
        raise ValueError("unknown workflow route")
    accumulation_transactions = tuple(accumulation_transactions); expenditure_transactions = tuple(expenditure_transactions)
    if len(accumulation_transactions) < 105 or accumulation_transactions[:105] != expenditure_transactions[:105]:
        raise ValueError("route faces do not share the fixed fresh starting world")
    ar, aj, av, answer_a = _face_world(accumulation_transactions, accumulation_access, route, "accumulation")
    er, ej, ev, answer_e = _face_world(expenditure_transactions, expenditure_access, route, "expenditure")
    field, expected_a, expected_e, locus = FACE_RESPONSIBILITY[route]
    if (av.get(field), ev.get(field)) != (expected_a, expected_e):
        raise ValueError("route face responsibility content differs")
    if (aj["actor"], aj["context"]) != (ej["actor"], ej["context"]):
        raise ValueError("route face actor or context differs")
    if route != "Act" and aj["content_target"].identity != ej["content_target"].identity:
        raise ValueError("route face actor, context or target differs")
    return dict(passed=True, route=route, accumulation=expected_a, expenditure=expected_e,
        responsibility_locus=locus, accumulation_spent=aj["spent"], expenditure_spent=ej["spent"],
        accumulation_answer=answer_a, expenditure_answer=answer_e,
        converged_final_answer=answer_a == answer_e,
        accumulation_workflow_attempts=ar["workflow_attempts"], expenditure_workflow_attempts=er["workflow_attempts"],
        participant_replay=False)
