"""Participant decisions over received information only; no world or evaluator.

The grammar and conservative decision thresholds are engineering choices.
Task goals are opportunities. Rules, programs, votes and revised terms are outputs.
"""
from . import codec, composition_language as lang
from .operations import indexed


def payload(view, ref):
    rows = [p.value for p in view.resolve(ref) if p.address.key == "payload"]
    if len(rows) != 1: raise ValueError("public content must be delivered and paid-read")
    return dict(codec.loads(rows[0]))


def encounter(view, ref, context, cue):
    d = {p.address.key:p.value for p in view.resolve(ref)}
    if (ref.identity.namespace != "u7.encounter" or d.get("actor") != view.snapshot.actor
            or d.get("context") != context or d.get("cue") != cue):
        raise ValueError("processed own encounter in this scope required")
    return d


def boundary(enc):
    if not enc.get("demand"): return "no_current_demand"
    if enc.get("truncated") or enc.get("reason")=="incomplete_access_or_recall" or "known.safe" not in enc: return "incomplete_access"
    if not enc["known.safe"]: return "received_threat"
    if not enc.get("known.available"): return "route_unavailable"
    if enc.get("known.requires_partner") and not enc.get("known.willing"): return "partner_refusal"
    if enc.get("known.approval_required") and not enc.get("known.approved"): return "actual_requirement"
    return None


def authority(enc):
    return "approval" if enc.get("approval") else "self_check"


def construct(view, slots, goal, context, limit):
    initial, sources, _ = lang.snapshot(view, slots)
    primitives = lang.acquired(view, context)
    session = dict(goal=goal, depth=6, queue=((initial,(),0),), deferred=(),
                   visited=(lang.signature(initial),), repertoire=(), considered=0)
    session, program, considered = lang.search_ticket(session, primitives, {}, view.snapshot.actor, limit,6,128)
    if program is None: raise ValueError("no candidate within paid search: " + session["status"])
    status, predicted, trace, _ = lang.simulate(program, initial, view.snapshot.actor, {}, 128)
    if status != "ok" or not lang.meets(predicted, goal): raise ValueError("unverified procedural candidate")
    bound, definitions = dict(slots), dict(primitives)
    agenda = tuple(("work", view.snapshot.actor, definitions[name],
        tuple(sorted((role,bound[slot].identity) for role,slot in lang.SCHEMAS[name]["inputs"]))) for name in trace)
    return dict(program=agenda, symbolic=program, initial=initial, predicted=predicted,
                trace=trace, considered=considered, search_status=session["status"], material_sources=sources)


def decide(view, proposal, enc):
    reason = boundary(enc)
    if reason: return "refuse", reason
    action, gate = proposal["effect"], proposal["gate"]
    if action == "dissolve": return "accept", "withdraw_collective_service_preserve_history"
    if action == "succession": return "accept", "explicit_successor_with_continuing_terms"
    if authority(enc) == "approval" and gate == "self_check":
        return "negotiate", "own_attribution_still_requires_authorization"
    # Conservative initial uptake is not permanent acceptance: a participant
    # can learn from a received consequence that this exact gate blocked work.
    harms = []
    for p in view.snapshot.particulars:
        if p.address.key != "payload" or not p.source.identity.namespace.startswith("u12."): continue
        d = dict(codec.loads(p.value))
        if (d.get("kind") == "consequence" and d.get("bearer") == view.snapshot.actor
                and d.get("outcome") == "approval_wait" and proposal.get("institution")
                and d["institution"].identity == proposal["institution"].identity): harms.append(d)
    if gate == "approval" and authority(enc) == "self_check" and harms:
        return "negotiate", "received_avoidable_delay"
    return "accept", "safe_goal_with_explicit_terms"


def render(proposal):
    gate = "Obtain the steward's permission before collective work" if proposal["gate"] == "approval" else "Check safety and material readiness before collective work"
    return gate + "; use the practiced actions needed to meet the shared material goal. " + proposal["reason"]
