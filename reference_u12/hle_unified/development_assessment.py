"""Offline finite-return assessment; never imported by the runtime."""
from .development_values import attrs
from .development_audit import audit
from .operations import indexed
from .shell_audit import effects


def assess(transactions):
    measured = audit(transactions)
    versions = {v.ref:v for tx in transactions for v in tx.versions}
    patterns = {r:attrs(v) for r,v in versions.items() if r.identity.namespace == "u7.pattern"}
    capacities, treatments, summaries, rows = {}, {}, {}, []
    for tx_index,tx in enumerate(transactions):
        for v in tx.versions:
            d, ns = attrs(v),v.ref.identity.namespace
            if ns == "u8.capacity":capacities[d["pattern"]] = d
            if ns == "u8.treatment":treatments[d["pattern"]] = d
            if ns != "u8.response":continue
            summary = summaries.setdefault(d["pattern"], {"batches":0,"completed":0,"supported":0,
                "independent":0,"known_claims":0,"accurate_claims":0,"residual_rows":0,
                "unassessed_rows":0,"post_capacity":[]})
            summary["batches"] += 1
            summary["completed"] += int(d["completed_demand"])
            summary["supported"] += int(d["supported"])
            summary["independent"] += int(d["completed_demand"] and not d["supported"])
            for i,target in enumerate(d["targets"]):
                prefix = f"row.{i}."
                known = {n[len(prefix)+6:]:value for n,value in d.items() if n.startswith(prefix+"known.")}
                active = d[prefix+"patterns"]
                attributed = any(kind in ("approval","obligation") for p in active for kind,_,_ in effects(patterns[p]))
                accurate = None
                if "approval_required" in known:
                    perceived = known["approval_required"] or attributed
                    accurate = perceived == known["approval_required"]
                    summary["known_claims"] += 1
                    summary["accurate_claims"] += int(accurate)
                reason = d[prefix+"reason"]
                if not d["demand"]:label="no_demand"
                elif d["truncated"] or reason in ("incomplete_access_or_recall","unverified_partner"):
                    label="incomplete_retained_access";summary["unassessed_rows"]+=1
                elif d[prefix+"base_route"] != "engage":label="legitimate_or_unavailable_boundary"
                elif active and d[prefix+"route"] != "engage":
                    label="residual_recurrence";summary["residual_rows"]+=1
                elif d["supported"]:label="supported_performance"
                elif any(b.identity.namespace=="u8.capacity" for _,b in d[prefix+"bases"]):label="retained_capacity_performance"
                elif d[prefix+"bases"]:label="local_correction_performance"
                else:label="unattributed_response"
                rows.append({"response":v.ref,"actor":d["actor"],"target":target,
                    "classification":label,"accuracy_against_declared_facts":accurate,
                    "intent":d[prefix+"route"],"supported":d["supported"],"load":d["load"]})
            cap=capacities.get(d["pattern"])
            if cap and d["demand"] and d["load"]<=cap["max_load"]:
                summary["post_capacity"].append({"response":v.ref,"completed":d["completed_demand"],
                    "capacity":cap["ref"],
                    "supported":d["supported"],"truncated":d["truncated"],"load":d["load"],
                    "applicable":all(d[f"row.{i}.base_route"]=="engage" for i in range(d["load"]))})
    findings=[]
    for p,pattern in patterns.items():
        cap,treatment=capacities.get(p),treatments.get(p)
        summary=summaries.get(p,{})
        eligible=[x for x in summary.get("post_capacity",[]) if cap and x["capacity"]==cap["ref"]]
        broken=any(x["applicable"] and not x["completed"] and not x["supported"] for x in eligible)
        owned=treatment is not None and treatment["ownership"]=="reowned"
        # A reownership record is already checked against two observed independent
        # returns. A later applicable failure defeats the broader retained claim.
        status="failed" if cap and broken else "established" if cap and owned else "unassessed"
        findings.append({"pattern":p,"origin":pattern["origin"],"actor":pattern["owner"],
            "local_corrections":sum(r.identity.namespace=="u8.correction" and attrs(v)["pattern"]==p for r,v in versions.items()),
            "capacity":None if cap is None else cap["ref"],"maximum_retained_load":0 if cap is None else cap["max_load"],
            "material_ownership":None if treatment is None else treatment["ownership"],
            "finite_return_status":status,"factual_accuracy":{
                "correct":summary.get("accurate_claims",0),"adjudicable":summary.get("known_claims",0),
                "status":"assessed" if summary.get("known_claims",0) else "unassessed"},
            "useful_capacity":{"completed_batches":summary.get("completed",0),"total_batches":summary.get("batches",0),
                               "independent_batches":summary.get("independent",0)},
            "pathway":{"supported_batches":summary.get("supported",0),"residual_rows":summary.get("residual_rows",0)},
            "retained_access":{"incomplete_rows":summary.get("unassessed_rows",0),"observed_returns":0 if not owned else len(treatment["returns"])},
            "identity_features":None if cap is None else (pattern["origin"],pattern["owner"],pattern["context"],
                pattern["cue"],pattern["trigger"],cap["organization"],cap["max_load"]),
            "universal_composition":"unassessed"})
    return {"schema":"hle-u8-development-assessment-v1","findings":findings,"responses":rows,
            "accounting":measured,"scope":"Enumerated finite returns only; no universal clearance or identity-equivalence proof."}


def evaluate_return_sequences(initial, step, features, sequences):
    """Canon-style explicit tests; preserve a later failure after a good endpoint."""
    baseline=features(initial)
    rows=[]
    for sequence in sequences:
        state=initial
        for operation in sequence:
            state=step(state,operation)
        rows.append({"sequence":tuple(sequence),"identity_before":baseline,
                     "identity_after":features(state),"status":"established" if features(state)==baseline else "failed"})
    return {"rows":rows,"universal_composition":"unassessed"}
