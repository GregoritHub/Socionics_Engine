"""Independent chronological U8 auditor. Does not import development policies.

Reconstructs actual payments, observations, local scope, distinct practice,
capacity load and origin treatment. Exact access replay additionally verifies
disclosure selectors; raw transactions alone do not include those selectors.
"""
from .development_values import attrs
from .operations import indexed
from .records import Account, Occurrence
from .shell_audit import audit as audit_parent, effects

FIELDS = ("trigger", "available", "safe", "requires_partner", "willing",
          "approval_required", "approved", "feedback", "recommended")


def _safe(k):
    return (all(n in k for n in FIELDS) and k["safe"] and k["available"]
            and (not k["requires_partner"] or k["willing"]) and not k["approval_required"])


def audit(transactions, **accounting):
    versions, read, retained, patterns, corrections, capacities, practices = {}, {}, {}, {}, {}, {}, {}
    responses, events, treatments, snapshots = {}, set(), {}, {}
    counts = dict(local_corrections=0, response_batches=0, supported_batches=0,
                  independent_practices=0, nonqualifying_practices=0, reorganizations=0,
                  displacements=0, reownerships=0, development_surfaces=0)

    def known(actor, target, context):
        latest = {}
        for s in read.get(actor, ()):
            d = attrs(versions[s])
            if (d.get("schema") == "u7.encounter-facts-v1" and d.get("receiver") == actor
                    and d.get("target") == target and d.get("context") == context):
                if s.identity not in latest or latest[s.identity].revision < s.revision:
                    latest[s.identity] = s
        sources = tuple(sorted(latest.values()))
        result = {}
        for name in (*FIELDS, "partner"):
            vals = {attrs(versions[s])[name] for s in sources if name in attrs(versions[s])}
            if len(vals) == 1:
                result[name] = next(iter(vals))
        return result, sources

    def basis(p, target, k, load, recalled):
        if not _safe(k) or any(kind not in ("approval", "obligation") for kind, _, _ in effects(patterns[p])):
            return None
        local = corrections.get((p, target))
        if local and local["binding"] in recalled:
            return local["ref"]
        cap = capacities.get(p)
        if cap and cap["binding"] in recalled and load <= cap["max_load"]:
            return cap["ref"]
        return None

    for tx in transactions:
        pending = {v.ref: v for v in tx.versions}
        available = {**versions, **pending}
        # Snapshot the applicable development at each U7 operation's start.
        for v in tx.versions:
            d = attrs(v)
            if d.get("record_type") == "operation" and d.get("u7"):
                snapshots[v.ref] = (dict(corrections), dict(capacities), tuple(indexed(d, "recalled.")))
            if d.get("record_type") == "operation" and d.get("status") == "succeeded":
                if d["primitive"] == "read":
                    receipt = next(x for x in tx.versions if x.ref.identity.namespace == "u4.receipt")
                    read.setdefault(d["actor"], set()).add(attrs(receipt)["input.0"])
                if d.get("binding"):
                    retained.setdefault(d["actor"], set()).add(d["binding"])
            if d.get("record_type") == "operation" and d.get("u8"):
                expected = max(1, d["evidence_count"]+d["recalled_count"]+d["target_count"]+d["example_count"])
                if (d["recall_units"] != expected or d["target_count"] != len(indexed(d, "target."))
                        or d["recalled_count"] != len(indexed(d, "recalled."))
                        or not set(indexed(d, "source.")) <= read.get(d["actor"], set())
                        or not set(indexed(d, "recalled.")) <= retained.get(d["actor"], set())):
                    raise ValueError("unearned development work or unowned evidence")
            if v.ref.identity.namespace == "u7.pattern":
                patterns[v.ref] = d

        for v in tx.versions:
            ns, d = v.ref.identity.namespace, attrs(v)
            if ns not in ("u8.correction", "u8.response", "u8.practice", "u8.capacity", "u8.treatment", "u8.surface"):
                continue
            job = attrs(versions[d["operation"]])
            terminal = next((attrs(x) for x in tx.versions if x.previous == d["operation"]), None)
            if not job.get("u8") or job["status"] != "ready" or terminal is None or terminal["status"] != "succeeded":
                raise ValueError("development effect lacks completed paid work")
            if d["actor"] != job["actor"]:
                raise ValueError("foreign development owner")
            if ns == "u8.surface":
                counts["development_surfaces"] += 1
                continue
            p = patterns[d["pattern"]]
            if d["origin"] != p["origin"] or d["actor"] != p["owner"] or d["pattern"] != job["pattern"]:
                raise ValueError("lost original material or pattern ownership")
            if ns != "u8.treatment":
                if (d["context"], d["cue"], d["trigger"]) != (p["context"], p["cue"], p["trigger"]):
                    raise ValueError("development escaped its scope")
                binding = available[d["binding"]]
                if (binding.occurrence != Occurrence.INTERPRETATION or binding.facet(Account).holder != d["actor"]
                        or d["binding"] != terminal["binding"]):
                    raise ValueError("unretained development content")
            if ns == "u8.correction":
                k, sources = known(d["actor"], d["target"], d["context"])
                if (job["purpose"] != "release" or not _safe(k) or k["approved"] or k["trigger"] != p["trigger"]
                        or any(kind not in ("approval", "obligation") for kind, _, _ in effects(p))
                        or set(d["sources"]) != set(sources) or d["approval_required"] is not False
                        or d["targets"] != (d["target"],) or job["truncated"]):
                    raise ValueError("local correction lacks applicable counterevidence")
                corrections[d["pattern"], d["target"]] = d
                counts["local_corrections"] += 1
            elif ns == "u8.response":
                if job["purpose"] != "respond" or d["targets"] != indexed(job, "target.") or d["load"] != len(d["targets"]):
                    raise ValueError("response load differs from paid demand")
                completed, supported = d["demand"], False
                for i, target in enumerate(d["targets"]):
                    k, sources = known(d["actor"], target, d["context"])
                    prefix = f"row.{i}."
                    recorded = {n[len(prefix)+6:]: value for n, value in d.items() if n.startswith(prefix+"known.")}
                    if recorded != k or d[prefix+"sources"] != sources or d[prefix+"target"] != target:
                        raise ValueError("response uses unreceived, incomplete or hidden opportunity")
                    selected = {ref: pd for ref, pd in patterns.items() if (pd["owner"],pd["context"],pd["cue"],pd["trigger"]) ==
                                (d["actor"],d["context"],d["cue"],k.get("trigger"))}
                    bases = tuple((ref,b) for ref in selected if (b := basis(ref,target,k,d["load"],indexed(job,"recalled."))) is not None)
                    active = {ref: pd for ref,pd in selected.items() if ref not in {x[0] for x in bases}}
                    base = "engage"
                    if not d["demand"]: base = "rest"
                    elif d["truncated"] or any(n not in k for n in FIELDS): base = "inspect"
                    elif not k["safe"] or not k["available"] or k["requires_partner"] and not k["willing"] or k["approval_required"] and not k["approved"]: base = "wait"
                    intent, applied = base, ()
                    if base == "engage":
                        used = {ref: tuple((kind, amount) for kind, path, amount in effects(pd) if path in ("*","engage")) for ref,pd in active.items()}
                        used = {ref: es for ref,es in used.items() if es}
                        flat = [item for es in used.values() for item in es]
                        applied = tuple(used)
                        if any(kind in ("approval","obligation") for kind,_ in flat) and not k["approved"]: intent = "wait"
                        elif any(kind in ("forecast","exclude_route") for kind,_ in flat) or sum(n for kind,n in flat if kind=="salience") < 0: intent = "inspect"
                        elif sum(n for kind,n in flat if kind=="salience") > 0: intent = "attend"
                    if k.get("partner") != d["partner"]: intent = "inspect"
                    if (d[prefix+"route"], d[prefix+"base_route"], d[prefix+"patterns"], d[prefix+"bases"]) != (intent,base,applied,bases):
                        raise ValueError("response not justified by scoped retained work")
                    completed = completed and intent == "engage" and k.get("trigger") == p["trigger"]
                    supported = supported or k.get("approved",False)
                if d["completed_demand"] != completed or d["supported"] != supported:
                    raise ValueError("supported or blocked response mislabeled independent")
                event = available[d["event"]]
                if (event.occurrence != Occurrence.ACTUAL_EVENT or attrs(event)["development_response"] != v.ref
                        or any(attrs(event)[n] != d[n] for n in ("completed_demand","supported","load"))):
                    raise ValueError("response lacks actual execution event")
                responses[v.ref] = d
                counts["response_batches"] += 1
                counts["supported_batches"] += int(supported)
            elif ns == "u8.practice":
                response = responses[d["response"]]
                obs = versions[d["observation"]]
                od = attrs(obs)
                event_key = d["pattern"], d["event"]
                if (job["purpose"] != "practice" or event_key in events or d["observation"] not in read.get(d["actor"],set())
                        or obs.occurrence != Occurrence.OBSERVATION or obs.ref.identity.namespace != "u4.observation"
                        or obs.facet(Account).sources != (d["event"],) or od["development_response"] != response["ref"]
                        or response["actor"] != d["actor"] or response["pattern"] != d["pattern"]
                        or any(d[n] != response[n] for n in ("targets","partner","context","cue","supported","event"))):
                    raise ValueError("practice is duplicate, foreign or lacks its observed outcome")
                if any(od[n] != response[n] for n in ("completed_demand","supported","load")):
                    raise ValueError("observed performance differs from actual response")
                expected = response["completed_demand"] and not response["supported"] and not job["truncated"]
                if d["independent"] != expected:
                    raise ValueError("independent practice was not independently performed")
                cap = capacities.get(d["pattern"])
                cap_used = cap is not None and all((d["pattern"],cap["ref"]) in response[f"row.{i}.bases"] for i in range(response["load"]))
                if d["capacity"] != (cap["ref"] if cap_used else None):
                    raise ValueError("practice claims unused capacity")
                events.add(event_key)
                practices[v.ref] = d
                counts["independent_practices" if expected else "nonqualifying_practices"] += 1
            elif ns == "u8.capacity":
                examples = [practices[x] for x in d["examples"]]
                if (job["purpose"] != "reorganize" or len(examples)<2 or len(set(d["examples"])) != len(examples)
                        or any(not x["independent"] or x["pattern"] != d["pattern"] or x["actor"] != d["actor"]
                               or x["binding"] not in indexed(job,"recalled.") for x in examples)
                        or len({t.identity for x in examples for t in x["targets"]}) < 2
                        or d["max_load"] != sorted((len(x["targets"]) for x in examples),reverse=True)[1]
                        or d["organization"] != "check_opportunity_then_engage"):
                    raise ValueError("capacity exceeds retained independent evidence")
                capacities[d["pattern"]] = d
                counts["reorganizations"] += 1
            elif ns == "u8.treatment":
                prior = treatments.get(d["origin"])
                if v.previous != (None if prior is None else prior["ref"]) or d["prior_carrier"] != (None if prior is None else prior["carrier"]):
                    raise ValueError("treatment broke material history")
                if d["original_carrier"] != attrs(available[d["origin"]]).get("carrier"):
                    raise ValueError("original material carrier was replaced")
                if d["kind"] == "reownership":
                    cap = capacities[d["pattern"]]
                    returned = [practices[x] for x in d["returns"]]
                    trained = [practices[x] for x in cap["examples"]]
                    if (job["purpose"] != "reown" or d["ownership"] != "reowned" or d["carrier"] is not None
                            or d["evidence"] != cap["ref"] or len(returned)<2 or len(set(d["returns"])) != len(returned)
                            or any(not x["independent"] or x["capacity"] != cap["ref"] or len(x["targets"])<cap["max_load"] for x in returned)
                            or not any({t.identity for t in x["targets"]}-{t.identity for y in trained for t in y["targets"]} for x in returned)
                            or not any(x["partner"] not in {y["partner"] for y in trained} for x in returned)):
                        raise ValueError("reownership lacks independent renewed returns")
                    counts["reownerships"] += 1
                elif d["ownership"] != "externally_attributed" or d["carrier"] is None:
                    raise ValueError("local treatment silently cleared origin ownership")
                if d["kind"] == "displacement":
                    response = responses[d["evidence"]]
                    if not any(response[f"row.{i}.patterns"] and response[f"row.{i}.route"] != response[f"row.{i}.base_route"] for i in range(response["load"])):
                        raise ValueError("displacement lacks actual residual recurrence")
                    counts["displacements"] += 1
                treatments[d["origin"]] = d
        for v in tx.versions:
            d = attrs(v)
            if d.get("u8") and d.get("status") == "succeeded":
                chain = [attrs(x) for x in tx.versions if x.ref.identity.namespace == "u8.surface"]
                if len(chain) != d["route_count"] or chain[-1]["retained"] != d["binding"]:
                    raise ValueError("missing retained realization chain")
        versions.update(pending)

    def pattern_filter(d, active):
        local, caps, recalled = snapshots[d["operation"]]
        k = {n[6:]:v for n,v in d.items() if n.startswith("known.")}
        if not _safe(k): return active
        filtered = {}
        for ref,p in active.items():
            c, cap = local.get((ref,d["target"])), caps.get(ref)
            correctable = all(kind in ("approval","obligation") for kind,_,_ in effects(p))
            if not correctable or not (c and c["binding"] in recalled or cap and cap["binding"] in recalled and cap["max_load"]>=1):
                filtered[ref] = p
        return filtered

    result = audit_parent(transactions, pattern_filter=pattern_filter, **accounting)
    result.update(counts)
    return result
