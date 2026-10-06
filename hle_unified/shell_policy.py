"""Pure encounter and forecast transformations over actor-owned information.

These functions receive no world, assessor, global head or other actor's memory.
Extending the finite effect language requires an explicit handler and tests.
"""
from .records import ObjectRef
from .cognitive_content import grouped

FACT_SCHEMA = "u7.encounter-facts-v1"
FIELDS = ("trigger", "available", "safe", "requires_partner", "willing",
          "approval_required", "approved", "feedback", "recommended")


def facts(view, target, context, evidence=None):
    details = view.snapshot.particulars if evidence is None else tuple(view.detail(a) for a in evidence)
    if any(p is None for p in details):
        raise ValueError("encounter evidence must have been processed by this actor")
    rows = []
    for source, row in grouped(details).items():
        values = {k: p.value for k, p in row.items()}
        if (values.get("schema") == FACT_SCHEMA and values.get("target") == target
                and values.get("context") == context and values.get("receiver") == view.snapshot.actor):
            rows.append((source, values))
    # Select latest *received* revision per source identity; incompatible sources
    # remain unknown. Never consult a hidden current head or delivery order.
    latest = {}
    for source, values in rows:
        if source.identity not in latest or latest[source.identity][0].revision < source.revision:
            latest[source.identity] = source, values
    result = {}
    for name in FIELDS:
        values = {v[name] for _, v in latest.values() if name in v}
        if len(values) == 1:
            result[name] = next(iter(values))
    types = {"trigger": ObjectRef, "feedback": str, "recommended": str,
             **{k: bool for k in FIELDS if k not in ("trigger", "feedback", "recommended")}}
    result = {k: v for k, v in result.items() if type(v) is types[k]}
    return result, tuple(sorted(s for s, _ in latest.values()))


def applicable(patterns, actor, target, context, cue, known):
    return tuple(p for p in patterns if p.owner == actor and p.context == context
                 and p.cue == cue and p.trigger == known.get("trigger"))


def encounter(request, known, patterns, truncated=False):
    """No diagnosis: return an intention, attributed terms and imagined risk."""
    result = {"route": request.route, "base_route": request.route, "salience": 0,
              "forecast_risk": 0, "obligation": False, "approval": False,
              "excluded": False, "applied": (), "reason": "available_demand"}
    if not request.demand:
        result.update(route="rest", reason="no_current_demand")
    elif truncated or any(k not in known for k in FIELDS):
        result.update(route="inspect", reason="incomplete_access_or_recall")
    elif not known["safe"]:
        result.update(route="wait", reason="received_threat")
    elif not known["available"]:
        result.update(route="wait", reason="route_unavailable")
    elif known["requires_partner"] and not known["willing"]:
        result.update(route="wait", reason="received_partner_refusal")
    elif known["approval_required"] and not known["approved"]:
        result.update(route="wait", reason="received_actual_requirement")
    if result["reason"] != "available_demand":
        result["base_route"] = result["route"]
        return result
    applied = []
    for p in patterns:
        used = False
        for effect in p.effects:
            if effect.route not in ("*", request.route):
                continue
            used = True
            if effect.kind == "salience":
                result["salience"] += effect.amount
            elif effect.kind == "forecast":
                result["forecast_risk"] += effect.amount
            elif effect.kind == "obligation":
                result["obligation"] = True
            elif effect.kind == "approval":
                result["approval"] = True
            elif effect.kind == "exclude_route":
                result["excluded"] = True
        if used:
            applied.append(p.ref)
    if (result["obligation"] or result["approval"]) and not known["approved"]:
        result.update(route="wait", reason="await_attributed_authorization")
    elif result["excluded"] or result["forecast_risk"] > 0 or result["salience"] < 0:
        result.update(route="inspect", reason="reconsider_available_route")
    elif result["salience"] > 0:
        result.update(route="attend", reason="heightened_attention")
    result["applied"] = tuple(applied)
    return result


def deform_forecast(result, patterns, known):
    rows = []
    applied = []
    for original in result["candidates"]:
        row = dict(original)
        row["eligible"] = True
        for p in patterns:
            for effect in p.effects:
                if row["kind"] == "inspect" or effect.route not in ("*", row["kind"]):
                    continue
                if p.ref not in applied:
                    applied.append(p.ref)
                if effect.kind == "salience":
                    row["utility"] += effect.amount
                elif effect.kind == "forecast":
                    row.update(outcome="failed", risk=1, utility=row["utility"]-12*effect.amount)
                    row["uncertainty"] += ("attributed_adverse_outcome",)
                elif effect.kind == "exclude_route" or (effect.kind in ("approval", "obligation") and not known.get("approved", False)):
                    row["eligible"] = False
        rows.append(row)
    return {**result, "candidates": tuple(rows), "u7_applied": tuple(applied),
            "visited": tuple(dict.fromkeys((*result["visited"], *applied)))}
