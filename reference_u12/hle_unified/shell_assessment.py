"""Offline demand-conditioned U7 assessor. No runtime dependency on this file.

Classification is an engineering operationalization on explicit opportunity
contracts, not a diagnosis of a person or a proof of the source theory.
"""
from .material import attrs
from .operations import indexed
from .records import Role


def assess(transactions):
    from .shell_audit import audit
    audit(transactions)
    versions = {v.ref: v for tx in transactions for v in tx.versions}
    jobs = {}
    for tx in transactions:
        for v in tx.versions:
            if attrs(v).get("record_type") == "operation":
                jobs[v.ref.identity] = attrs(v)
    candidates, rows = {}, []
    for tx in transactions:
        for v in tx.versions:
            if v.ref.identity.namespace != "u7.encounter":
                continue
            d = attrs(v)
            known = {k[6:]: value for k, value in d.items() if k.startswith("known.")}
            if not d["demand"]:
                label = "no_demand"
            elif d["reason"] == "incomplete_access_or_recall":
                label = "missing_knowledge"
            elif not known.get("safe", True):
                label = "accurate_threat_recognition"
            elif known.get("requires_partner") and not known.get("willing"):
                label = "partner_refusal"
            elif not known.get("available", False):
                label = "unavailable_route"
            elif known.get("approval_required") and not known.get("approved"):
                label = "actual_approval_requirement"
            elif not indexed(d, "pattern.") and d["requested_route"] != known.get("recommended"):
                label = "ordinary_disagreement"
            elif indexed(d, "pattern.") and d["route"] != d["base_route"] and not known.get("approval_required", True):
                label = "changed_encounter_candidate"
                for pattern in indexed(d, "pattern."):
                    candidates.setdefault(pattern, []).append(v.ref)
            else:
                label = "no_defensive_maintenance_established"
            rows.append({"encounter": v.ref, "actor": d["actor"], "target": d["target"],
                "classification": label, "patterns": indexed(d, "pattern."), "route": d["route"]})
    recurrent = {p: refs for p, refs in candidates.items() if len(refs) >= 2}
    for row in rows:
        if row["classification"] == "changed_encounter_candidate" and any(p in recurrent for p in row["patterns"]):
            row["classification"] = "defensive_maintenance"
    # Censored processing is never mislabeled as a completed defensive choice.
    for job in jobs.values():
        if job.get("u7") and job["status"] in ("pending", "partial", "waiting", "cancelled"):
            wallets = [attrs(v) for v in versions.values() if attrs(v).get("record_type") == "wallet"
                       and attrs(v)["actor"] == job["actor"]]
            last = wallets[-1]
            remaining = job["required"]-job["completed"]
            label = "insufficient_resources" if min(last["energy"], last["time"]) < remaining else "incomplete_processing"
            if job["status"] == "cancelled":
                label = "cancelled_processing"
            rows.append({"operation_key": job["key"], "actor": job["actor"], "target": job["target"],
                         "classification": label, "patterns": (), "route": None})
    return {"schema": "hle-u7-demand-assessment-v1", "rows": rows,
        "recurrent_patterns": tuple({"pattern": p, "origin_mode": attrs(versions[p])["origin_mode"],
            "encounters": tuple(refs)} for p, refs in recurrent.items()),
        "scope": "Finite paid opportunities; clearance and universal Shell detection remain unassessed."}
