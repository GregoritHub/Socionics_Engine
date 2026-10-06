"""Participant-only content operators: no world, truth or evaluation input.

This finite policy reconciles one property of one identified object/context.
It neither invents missing card meanings nor generalizes a skill to new tools.
"""
from . import codec
from .records import (Definition, Occurrence, Proposition, TimeScope, Moment,
                      ClaimStatus, ObjectRef, ObjectId)


def rule_from(view, ref):
    candidates = [p.value for p in view.resolve(ref) if type(p.value) is Definition]
    if len(candidates) != 1:
        raise ValueError("processed exact rule definition required")
    rule = {a.name: a.value for a in candidates[0].constraints}
    if not isinstance(rule.get("relation"), str) or not rule["relation"]:
        raise ValueError("rule must name its property relation")
    if rule.get("default") != "inspect" or any(v not in ("inspect", "use")
            for k, v in rule.items() if k.startswith("when.")):
        raise ValueError("unsupported finite action policy")
    return rule


def grouped(details):
    groups = {}
    for p in details:
        row = groups.setdefault(p.source, {})
        if p.address.key in row:
            prior = row[p.address.key]
            if any(getattr(prior, k) != getattr(p, k) for k in
                   ("source", "subject", "category", "path", "value", "occurrence")):
                raise ValueError("ambiguous evidence field")
            # Re-delivery has a different paid address, not a different fact.
            continue
        row[p.address.key] = p
    return groups


def most_recent(claims):
    """Exact object revisions order local material claims, not delivery order."""
    if not claims:
        return None, "unknown"
    newest = max(p.subject.revision for p in claims)
    latest = [p for p in claims if p.subject.revision == newest]
    if len({codec.dumps(p.object) for p in latest}) != 1:
        return None, "conflict"
    return min(latest, key=codec.dumps), "supported"


def retained_claims(bindings, relation, target, context):
    """A paid corrected account governs its exact revision; history is retained.

    U6 continuation exposed that same-revision corrections otherwise competed
    forever with the very remembered claim they corrected. Equally current
    corrected accounts can still conflict; newer material revisions still win.
    """
    bindings = tuple(b for b in bindings if b.endorsement not in (ClaimStatus.RETRACTED, ClaimStatus.DISPUTED))
    rows = [(b, p) for b in bindings
        for p in b.content if p.relation == relation and p.subject.identity == target.identity
        and p.context == context and p.scope.end is None]
    accounts = [b for b in bindings if b.ref.identity.namespace == "u5.account"
        and b.target.identity == target.identity and b.context == context
        and b.meaning.startswith("integrate: " + relation + ";")]
    newest = max([p.subject.revision for b, p in rows]+[b.target.revision for b in accounts], default=0)
    current = [b for b in accounts if b.target.revision == newest]
    if current:
        corrected = [[p for p in b.content if p.relation == relation] for b in current]
        # A paid unresolved correction must not resurrect the superseded belief.
        return [] if any(not claims for claims in corrected) else [p for claims in corrected for p in claims]
    return [p for b, p in rows]


def derive(view, request):
    rule = rule_from(view, request.rule)
    relation = rule["relation"]
    traversal = view.traverse(request.cue, request.context, visit_limit=request.visit_limit)
    details = tuple(view.detail(a) for a in request.evidence)
    if any(p is None for p in details):
        raise ValueError("cognition cannot use undelivered or unprocessed evidence")
    claims = retained_claims(traversal.bindings, relation, request.target, request.context)
    prior, prior_status = most_recent(claims)
    observed, offers = [], []
    for source, row in grouped(details).items():
        values = {k: p.value for k, p in row.items()}
        target = values.get("target")
        if (type(target) is not ObjectRef or target.identity != request.target.identity
                or values.get("context") != request.context):
            continue
        if (request.purpose == "integrate" and relation in row
                and all(p.occurrence == Occurrence.OBSERVATION for p in row.values())
                and values.get("outcome") == "succeeded" and type(values.get("event")) is ObjectRef):
            observed.append(Proposition(target, relation, values[relation], request.context,
                TimeScope(Moment(target.revision, 0), None)))
        if (request.purpose == "plan" and values.get("offer") == "assistance"
                and values.get("receiver") == request.actor and type(values.get("giver")) is ObjectId
                and values["giver"] != request.actor and values.get("operation") == "repair"
                and all(type(values.get(k)) is ObjectRef for k in ("tool", "stock"))
                and all(p.occurrence == Occurrence.REMEMBERED_CLAIM for p in row.values())
                and target == request.target):
            offers.append((source, values))
    # Reading a consequence does not silently update a conceptual account.
    current, status = most_recent(claims)
    # Native observations may correct a remembered claim at the same revision.
    # Mutually conflicting observations remain unresolved; older observations
    # never roll a newer retained material revision back.
    if observed and max(p.subject.revision for p in observed) >= max(
            (p.subject.revision for p in claims), default=0):
        current, status = most_recent(observed)
    if traversal.truncated:
        current, status = None, "truncated"
    tension = status
    if current is not None and prior is not None:
        tension = ("same_revision_disagreement" if current.subject == prior.subject else "revision_change") \
            if current.object != prior.object else "none"
    elif current is not None:
        tension = "new_evidence" if observed else "none"
    target = current.subject if current is not None else max(
        (request.target, *(p.subject for p in claims), *(p.subject for p in observed)), key=lambda ref: ref.revision)
    action = rule["default"]
    offer = None
    if current is not None:
        action = rule.get("when." + codec.canonical(codec.encode(current.object)), rule["default"])
        if relation == "condition" and current.object == "damaged" and len(offers) == 1:
            source, terms = offers[0]
            if target == terms["target"]:
                action, offer = "repair", (source, terms)
    content = (() if current is None else (current,))
    if request.purpose == "plan":
        content += (Proposition(target, "u5.action", action, request.context,
                                TimeScope(Moment(target.revision, 0), None)),)
        if offer:
            for key in ("tool", "stock", "giver"):
                content += (Proposition(target, "u5." + key, offer[1][key], request.context,
                                        TimeScope(Moment(target.revision, 0), None)),)
    addresses = tuple(dict.fromkeys((*request.evidence,
        *(p.address for p in traversal.particulars), *(p.address for p in view.resolve(request.rule)))))
    return {"traversal": traversal, "relation": relation, "prior": prior,
        "claim": current, "status": status, "tension": tension, "target": target,
        "content": content, "addresses": addresses, "action": action,
        "offer": None if offer is None else offer[0],
        "observed": tuple(observed), "prior_status": prior_status}


def plan_request(view, binding_ref, key):
    """Only the actor's paid retained plan can construct a native action."""
    from .operation_records import OperationRequest
    bindings = {b.ref: b for b in view.snapshot.bindings}
    b = bindings.get(binding_ref)
    if b is None or b.ref.identity.namespace != "u5.plan":
        raise ValueError("actor-owned completed plan required")
    if any(x.ref.identity == b.ref.identity and x.ref.revision > b.ref.revision for x in bindings.values()):
        raise ValueError("superseded plan cannot authorize new work")
    content = {p.relation: p.object for p in b.content if p.relation.startswith("u5.")}
    action = content.get("u5.action")
    if action not in ("inspect", "use", "repair"):
        raise ValueError("plan has no supported action")
    return OperationRequest(key, view.snapshot.actor, action, b.context,
        participants=(() if action != "repair" else (content["u5.giver"],)),
        target=b.target, tool=content.get("u5.tool"), stock=content.get("u5.stock"),
        evidence=b.particulars)
