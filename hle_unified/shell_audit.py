"""Reconstruct U7 accounting, provenance and role separation from raw writes.

No runtime choice/effect policy, detector output, or engine cache is consulted.
Exact access replay additionally verifies disclosure selectors and bindings.
"""
from .autonomy_audit import audit as audit_parent
from .material import attrs
from .operations import indexed
from .records import Account, Occurrence


def effects(pd):
    i = 0
    while f"effect.{i}.kind" in pd:
        yield pd[f"effect.{i}.kind"], pd[f"effect.{i}.route"], pd[f"effect.{i}.amount"]
        i += 1


def validate_intention(d, patterns, pattern_filter=None):
    keys = ("trigger", "available", "safe", "requires_partner", "willing",
            "approval_required", "approved", "feedback", "recommended")
    k = {name: d.get("known."+name) for name in keys}
    gates = [(not d["demand"], "rest"),
             (d["truncated"] or any("known."+name not in d for name in keys), "inspect"),
             (k["safe"] is False, "wait"), (k["available"] is False, "wait"),
             (k["requires_partner"] is True and k["willing"] is False, "wait"),
             (k["approval_required"] is True and k["approved"] is False, "wait")]
    base = next((intent for applies, intent in gates if applies), d["requested_route"])
    eligible = not any(applies for applies, _ in gates)
    active = {p: pd for p, pd in patterns.items() if pd["owner"] == d["actor"]
              and pd["context"] == d["context"] and pd["cue"] == d["cue"] and pd["trigger"] == k["trigger"]}
    if pattern_filter is not None:
        active = pattern_filter(d, active)
    used = {p: [(kind, amount) for kind, route, amount in effects(pd) if route in ("*", d["requested_route"])]
            for p, pd in active.items()} if eligible else {}
    used = {p: es for p, es in used.items() if es}
    flat = [item for es in used.values() for item in es]
    salience = sum(amount for kind, amount in flat if kind == "salience")
    risk = sum(amount for kind, amount in flat if kind == "forecast")
    flags = {kind: any(k == kind for k, _ in flat) for kind in ("obligation", "approval", "exclude_route")}
    intended = base
    if eligible:
        if (flags["obligation"] or flags["approval"]) and not k["approved"]:
            intended = "wait"
        elif flags["exclude_route"] or risk > 0 or salience < 0:
            intended = "inspect"
        elif salience > 0:
            intended = "attend"
    expected = {"route": intended, "base_route": base, "salience": salience, "forecast_risk": risk,
                "obligation": flags["obligation"], "approval": flags["approval"], "excluded": flags["exclude_route"]}
    if set(indexed(d, "pattern.")) != set(used) or any(d[name] != value for name, value in expected.items()):
        raise ValueError("encounter intention does not follow its owned attributions and opportunity")


def audit(transactions, *, pattern_filter=None, **accounting):
    result = audit_parent(transactions, **accounting)
    versions, read, retained, patterns = {}, {}, {}, {}
    counts = dict(encounters=0, generated_patterns=0, injected_patterns=0, target_bindings=0,
                  forecast_applications=0, encounter_surfaces=0)
    for tx in transactions:
        pending = {v.ref: v for v in tx.versions}
        available = {**versions, **pending}
        for v in tx.versions:
            d = attrs(v)
            ns = v.ref.identity.namespace
            if d.get("record_type") == "operation" and d.get("u7"):
                if d["recall_units"] != max(1, d["evidence_count"]+d["recalled_count"])+d["effect_units"]:
                    raise ValueError("encounter recall/effect cost mismatch")
                if d["recalled_count"] != len(indexed(d, "recalled.")):
                    raise ValueError("invented recall count")
            if d.get("record_type") == "operation" and d.get("status") == "succeeded":
                actor = d["actor"]
                if d["primitive"] == "read":
                    receipt = next(x for x in tx.versions if x.ref.identity.namespace == "u4.receipt")
                    read.setdefault(actor, set()).add(attrs(receipt)["input.0"])
                if d.get("binding"):
                    retained.setdefault(actor, set()).add(d["binding"])
            if ns == "u7.pattern":
                sources = indexed(d, "source.")
                if not sources:
                    raise ValueError("pattern has no origin evidence")
                if d["origin_mode"] == "generated":
                    material = attrs(available[d["origin"]])
                    policy = next(attrs(x) for x in available.values() if x.ref.identity.namespace == "u7.policy"
                                  and attrs(x)["actor"] == d["owner"])
                    if material["owner"] != d["owner"] or indexed(material, "experience.") != sources or len(sources) < policy["threshold"]:
                        raise ValueError("generated material lost its owner or threshold history")
                    distinct = set()
                    for source in sources:
                        e = attrs(available[source])
                        if (e["actor"] != d["owner"] or e["known.feedback"] != "blame" or not e["demand"]
                                or e["base_route"] != "engage" or e["known.trigger"] != d["trigger"]
                                or e["context"] != d["context"] or e["cue"] != d["cue"]):
                            raise ValueError("pattern was not generated by its paid matching experiences")
                        distinct.update(indexed(e, "source."))
                    if len(distinct) < policy["threshold"]:
                        raise ValueError("repeat delivery masquerades as distinct experience")
                    counts["generated_patterns"] += 1
                elif d["origin_mode"] == "injected_fixture":
                    counts["injected_patterns"] += 1
                else:
                    raise ValueError("undeclared pattern origin")
                patterns[v.ref] = d
            if ns == "u7.encounter":
                job = attrs(versions[d["operation"]])
                completed = next((x for x in tx.versions if x.previous == d["operation"]), None)
                if completed is None or attrs(completed)["status"] != "succeeded" or job["status"] != "ready" or not job.get("u7"):
                    raise ValueError("encounter has no complete paid realization")
                if any(d[k] != job[k] for k in ("actor", "target", "context", "cue", "carrier", "bearer", "demand", "spent", "requested_route")):
                    raise ValueError("encounter changed its actor/target/carrier/bearer or demand")
                sources = indexed(d, "source.")
                if not set(sources) <= read.get(d["actor"], set()):
                    raise ValueError("unread encounter evidence")
                for source in sources:
                    f = attrs(versions[source])
                    if f.get("target") != d["target"] or f.get("context") != d["context"] or f.get("receiver") != d["actor"]:
                        raise ValueError("wrong target, context or recipient evidence")
                for key, value in d.items():
                    if key.startswith("known."):
                        values = {attrs(versions[s]).get(key[6:]) for s in sources if key[6:] in attrs(versions[s])}
                        if values != {value}:
                            raise ValueError("encounter fact not supported by its processed sources")
                for p in indexed(d, "pattern."):
                    pd = patterns[p]
                    if pd["owner"] != d["actor"] or pd["context"] != d["context"] or pd["cue"] != d["cue"] or pd["trigger"] != d["known.trigger"]:
                        raise ValueError("pattern escaped its actor/context/cue/affordance scope")
                validate_intention(d, patterns, pattern_filter)
                binding_ref = attrs(completed).get("binding")
                if binding_ref:
                    binding = available[binding_ref]
                    account = binding.facet(Account)
                    if account.holder != d["actor"] or account.referent != d["target"] or binding.occurrence != Occurrence.INTERPRETATION:
                        raise ValueError("target binding is unowned or promoted to fact")
                    counts["target_bindings"] += 1
                counts["encounters"] += 1
            if ns == "u7.surface":
                job = attrs(versions[d["operation"]])
                if job["status"] != "ready" or d["actor"] != job["actor"]:
                    raise ValueError("unpaid perspective content")
                counts["encounter_surfaces"] += 1
            if ns == "u7.forecast_application":
                job = attrs(versions[d["operation"]])
                forecast = attrs(versions[d["forecast"]])
                if job["status"] != "ready" or job["actor"] != d["actor"] or forecast["actor"] != d["actor"]:
                    raise ValueError("forecast application lacks owned paid work")
                for p in indexed(d, "pattern."):
                    pd = patterns[p]
                    if pd["owner"] != d["actor"] or pd["cue"] != d["cue"] or pd["context"] != d["context"]:
                        raise ValueError("foreign forecast attribution")
                if not set(indexed(d, "source.")) <= read.get(d["actor"], set()):
                    raise ValueError("forecast attribution used unread source")
                source_values = [attrs(versions[s]) for s in indexed(d, "source.")]
                for p in indexed(d, "pattern."):
                    if not any(s.get("target") == d["target"] and s.get("receiver") == d["actor"]
                               and s.get("context") == d["context"] and s.get("trigger") == patterns[p]["trigger"] for s in source_values):
                        raise ValueError("forecast attribution lacks a matching processed affordance")
                approvals = {s["approved"] for s in source_values if "approved" in s}
                approved = approvals == {True}
                i = 0
                while f"before.{i}.kind" in d:
                    kind = d[f"before.{i}.kind"]
                    utility, risk, outcome = (d[f"before.{i}."+name] for name in ("utility", "risk", "outcome"))
                    eligible = True
                    for p in indexed(d, "pattern."):
                        for effect, route, amount in effects(patterns[p]):
                            if kind == "inspect" or route not in ("*", kind):
                                continue
                            if effect == "salience": utility += amount
                            if effect == "forecast": utility, risk, outcome = utility-12*amount, 1, "failed"
                            if effect == "exclude_route" or effect in ("approval", "obligation") and not approved: eligible = False
                    if any(d[f"after.{i}."+name] != val for name, val in
                           (("kind", kind), ("utility", utility), ("risk", risk), ("outcome", outcome), ("eligible", eligible))):
                        raise ValueError("forecast deformation violates its declared effect")
                    i += 1
                counts["forecast_applications"] += 1
        versions.update(pending)
    result.update(counts)
    return result
