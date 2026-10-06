"""Pure bounded model over detached participant information and acquired use.

The transition model is a declared workshop hypothesis, not learned physics.
Unknown inputs stay unknown. It never calls a world or native feasibility check.
"""
from dataclasses import replace
from .records import Occurrence, ObjectRef, Procedure, ClaimStatus
from .cognitive_content import plan_request, grouped, most_recent, retained_claims
from .operation_records import OperationRequest, EXTENTS, SIGNATURES


def known_ref(view, identity):
    refs = [p.subject for p in view.snapshot.particulars if p.subject.identity == identity]
    refs += [p.source for p in view.snapshot.particulars if p.source.identity == identity]
    refs += [p.value for p in view.snapshot.particulars
             if type(p.value) is ObjectRef and p.value.identity == identity]
    return max(refs, key=lambda r: r.revision) if refs else None


def observed_rows(view, context):
    return [(source, {k: p.value for k, p in row.items()})
        for source, row in grouped(view.snapshot.particulars).items()
        if row and all(p.occurrence == Occurrence.OBSERVATION for p in row.values())
        and row.get("context") is not None and row["context"].value == context]


def state_of(view, target, context, bindings=None):
    """Retained condition, plus explicitly available exact material particulars.

    Raw outcomes do not replace U5's retained conceptual condition. They may
    supply inspected wear/limits and exact accessible revisions for execution.
    """
    claims = retained_claims((b for b in (view._heads.values() if bindings is None else bindings)
        if b.context == context), "condition", target, context)
    claim, status = most_recent(claims)
    result = {"condition": claim.object if claim else None, "wear": None,
              "max_wear": None, "available": None, "status": status}
    values = {}
    for p in view.lookup(subject=target.identity):
        if p.address.key in ("wear", "max_wear", "available") and type(p.value) is int:
            # Revisions, not arrival order, determine recency. Conflicts stay unknown.
            values.setdefault(p.address.key, []).append((p.subject.revision, p.value))
    for key, entries in values.items():
        revision = max(r for r, v in entries)
        latest = {v for r, v in entries if r == revision}
        result[key] = next(iter(latest)) if len(latest) == 1 else None
    # A successful repair/care/use observation projects the new wear but does
    # not change the retained condition until paid integration has occurred.
    return result


def evidence_for(view, target, context):
    values = list(view.lookup(subject=target.identity))
    for source, row in grouped(view.snapshot.particulars).items():
        v = {k: p.value for k, p in row.items()}
        t = v.get("target")
        if type(t) is ObjectRef and t.identity == target.identity and v.get("context") == context:
            values.extend(row.values())
    return tuple(dict.fromkeys(p.address for p in values))


def offers(view, config):
    found = []
    for source, row in grouped(view.snapshot.particulars).items():
        v = {k: p.value for k, p in row.items()}
        target = v.get("target")
        if (v.get("offer") == "assistance" and v.get("receiver") == config.actor
                and type(target) is ObjectRef and target.identity == config.target.identity
                and v.get("context") == config.context and v.get("operation") == "repair"
                and all(p.occurrence == Occurrence.REMEMBERED_CLAIM for p in row.values())):
            found.append(source)
    return tuple(sorted(found))


def needs(view, config, state, wallet):
    threats = [(source.revision, row["threat"]) for source, row in observed_rows(view, config.context)
        if type(row.get("target")) is ObjectRef and row["target"].identity == config.target.identity
        and type(row.get("threat")) is int and row["threat"] >= 0]
    fear = min(10, max((v for r, v in threats), default=0))
    # Danger clearance is intentionally not inferred from silence or time.
    scarcity = min(10, max(0, 20 - min(wallet["energy"], wallet["time"])) // 2)
    if config.stock is not None:
        stock = state_of(view, config.stock, config.context)
        if stock["available"] == 0:
            scarcity = max(scarcity, 8)
    return {"pressure": min(10, max(0, config.goal_uses-state.uses) + state.turns//config.urgency_after),
            "fear": fear, "scarcity": scarcity, "boredom": min(10, state.monotony)}


def transition(kind, before):
    after = dict(before)
    condition, wear, maximum = (before[k] for k in ("condition", "wear", "max_wear"))
    outcome, uncertain = "succeeded", []
    if kind == "use":
        if condition == "damaged":
            outcome = "failed"
        elif condition != "serviceable":
            outcome = None
            uncertain.append("condition")
        if outcome == "succeeded":
            if wear is None or maximum is None:
                after["condition"], after["wear"] = None, None
                uncertain.append("wear_limit")
            else:
                after["wear"] = wear + 1
                after["condition"] = "damaged" if wear+1 >= maximum else "serviceable"
    elif kind == "care":
        if condition != "serviceable" or wear == 0:
            outcome = "failed" if condition == "damaged" or wear == 0 else None
        after["wear"] = None if wear is None else max(0, wear-1)
        if wear is None:
            uncertain.append("wear")
    elif kind == "repair":
        outcome = "succeeded" if condition == "damaged" else ("failed" if condition == "serviceable" else None)
        after.update(condition="serviceable" if outcome == "succeeded" else condition,
                     wear=0 if outcome == "succeeded" else wear)
        uncertain.append("tool_and_stock_feasibility")
    else:  # Inspection predicts receipt availability, never its unobserved content.
        after.update(condition=None, wear=None)
        uncertain.append("unobserved_condition")
    return outcome, after, tuple(uncertain)


def forecast(view, request):
    c = request.config
    primary = plan_request(view, request.plan, request.key + ":candidate")
    target = primary.target
    recalled = view.traverse(c.cue, c.context, visit_limit=c.visit_limit)
    before = state_of(view, target, c.context, recalled.bindings)
    evidence = primary.evidence
    choices = [(primary.kind, primary, "paid_u5_plan")]
    if primary.kind != "inspect":
        choices.append(("inspect", OperationRequest(primary.key, c.actor, "inspect", c.context,
            target=target, evidence=evidence), "native_inspection"))
    care = known_ref(view, c.care.identity) if c.care else None
    if before["condition"] == "serviceable" and before["wear"] not in (None, 0) and care:
        supply = state_of(view, care, c.context)["available"]
        if supply != 0:
            choices.append(("care", OperationRequest(primary.key, c.actor, "care", c.context,
                target=target, stock=care, evidence=evidence), "native_care"))
    # Merely reading or naming a procedure never adds this candidate.
    if primary.kind != "repair" and c.procedure and view.can_use(c.procedure, c.context):
        rows = [p.value for p in view.resolve(c.procedure) if type(p.value) is Procedure]
        tool = known_ref(view, c.tool.identity) if c.tool else None
        stock = known_ref(view, c.stock.identity) if c.stock else None
        if (len(rows) == 1 and rows[0].executor == "u4.repair.v1"
                and rows[0].inputs == SIGNATURES["repair"] and not any((rows[0].steps, rows[0].effects, rows[0].preconditions))
                and tool and stock and before["condition"] == "damaged"):
            choices.append(("repair", OperationRequest(primary.key, c.actor, "procedure", c.context,
                target=target, tool=tool, stock=stock, procedure=c.procedure, evidence=evidence), "acquired_procedure"))
    rows, nodes = [], 0
    for kind, operation, source in choices:
        if nodes >= c.max_nodes:
            break
        outcome, after, unknown = transition(kind, before)
        nodes += 1
        future = None
        depth = 1
        if c.horizon == 2 and kind in ("care", "repair") and nodes < c.max_nodes:
            future = transition("use", after)[1]["condition"]
            nodes += 1
            depth = 2
        damaged = after["condition"] == "damaged" or future == "damaged"
        utility = {"use": 8, "repair": 6, "care": 2, "inspect": 1}[kind]
        if kind in ("repair", "care") and future == "serviceable":
            utility += 4
        if damaged:
            utility -= 12
        if outcome == "failed":
            utility -= 20
        if recalled.truncated:
            utility = -100 if kind != "inspect" else 0
            unknown += ("truncated_recall",)
        rows.append({"kind": kind, "request": operation, "basis": source,
            "outcome": outcome, "condition": after["condition"], "wear": after["wear"],
            "uncertainty": unknown, "depth": depth, "future_condition": future,
            "utility": utility, "cost": 1+EXTENTS[kind], "risk": int(damaged)})
    return {"candidates": tuple(rows), "primary": primary.kind, "nodes": nodes,
        "visited": recalled.visited, "truncated_recall": recalled.truncated,
        "coverage": "complete" if len(rows) == len(choices) and all(
            r["depth"] == c.horizon or r["kind"] not in ("care", "repair") for r in rows) else "censored",
        "unevaluated": len(choices)-len(rows), "target": target}


def choose(result, config, need, wallet):
    affordable = [r for r in result["candidates"] if r["cost"] + 2 <= min(wallet["energy"], wallet["time"])]
    if not affordable:
        return None
    if not config.anticipation:
        return next((r for r in affordable if r["kind"] == result["primary"]), None)
    # Pressure only modestly favors immediate work; fear penalizes predicted damage.
    score = lambda r: r["utility"] + (min(3, need["pressure"]//3) if r["kind"] == "use" else 0) \
        - need["fear"]*r["risk"] - (need["scarcity"]//4 if r["kind"] in ("care", "repair") else 0)
    return max(affordable, key=lambda r: (score(r), -r["cost"], r["kind"]))
