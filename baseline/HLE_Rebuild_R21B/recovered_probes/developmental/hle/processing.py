"""Pure participant computations: no world, evaluator or hidden-state input."""
from functools import lru_cache
from .contracts import ActionRequest, ClaimStatus, Kind, Ref
from .crux import Polarity
from .model_a import element_at, fields, position_of, shortest_paths
from .metabolism_records import (Account, ApplyDraft, EmbodyDraft, RoutePlan,
    TheorizeDraft, UnderstandDraft)
from .world_records import INSPECT, TRANSFER


def route_active(plan, completed):
    """Last fully funded hop; shared by R4, R6 and R11."""
    active = plan.path[0]
    for node, units in zip(plan.path[1:], plan.hop_units):
        if completed < units: break
        active, completed = node, completed - units
    return active


@lru_cache(maxsize=2048)
def _route_geometry(tim, active, target, polarity, positional_prices):
    """Bounded immutable topology cache; no actor, evidence, work or result keys."""
    supports = (5, 7) if polarity == Polarity.ACCUMULATION else (6, 8)
    price = lambda e: 5 - fields(position_of(tim, e))["dimensionality"] if positional_prices else 1
    candidates = []
    for seat in supports:
        support = element_at(tim, seat)
        for first in shortest_paths(tim, active, support):
            for second in shortest_paths(tim, support, target):
                path = first + second[1:]
                units = tuple(price(e) for e in path[1:])
                candidates.append((sum(units), len(path), path, seat, len(first) - 1, units))
    _, _, path, seat, at, units = min(candidates)
    return path, tuple(position_of(tim, e) for e in path), seat, at, units, price(target)


def plan_route(profile, active, formal, payload, content_size, policy):
    """Fixed targets and numerical prices are R4 hypotheses, not source laws."""
    tim = profile.tim if policy.typed_routing else "ile"
    target = {TheorizeDraft: "ti", ApplyDraft: "te",
              EmbodyDraft: "si", UnderstandDraft: "fi"}[type(payload)]
    path, positions, seat, at, units, price = _route_geometry(
        tim, active, target, formal.polarity, policy.positional_prices)
    return RoutePlan(profile.tim, tim, path, positions, seat, at, units,
                     max(1, content_size) * price)


def derive_account(ref, actor, draft, recall, memories, capabilities):
    """Align exact recalled claims; equal-time conflict never chooses by order.

    Scope start is an explicit experimental recency policy, not a truth score.
    Only proposition indexes selected by the completed recall are considered.
    """
    by_ref = {m.ref: m for m in memories}
    candidates, basis, guards = [], [], []
    for hit in recall.hits:
        m = by_ref[hit.memory]
        basis.append(m.ref)
        if m.claim_status in (ClaimStatus.RETRACTED, ClaimStatus.DISPUTED):
            continue
        guards.extend(c for c in m.capabilities if c in capabilities
                      and capabilities[c].rule == "inspect_before_transfer")
        for index in hit.proposition_indexes:
            p = m.content[index]
            if p.subject == draft.item and p.relation == "owned_by" and p.context == recall.query.context:
                candidates.append(p)
    claim, uncertainty = None, "no usable recalled ownership claim"
    if candidates:
        newest = max(p.scope.start for p in candidates)
        latest = tuple(p for p in candidates if p.scope.start == newest)
        owners = {(type(p.object), p.object) for p in latest}
        if len(owners) == 1:
            claim = min(latest, key=lambda p: (p.scope.end is None,
                        p.scope.end.tick if p.scope.end else 0, p.scope.end.order if p.scope.end else 0))
            uncertainty = "recalled account; current accuracy unassessed"
        else:
            uncertainty = "conflicting ownership claims at the same declared time"
    if recall.truncated:
        claim, uncertainty = None, "truncated recall cannot establish an unambiguous account"
    guard = min(guards, key=lambda r: (r.key, r.revision)) if guards else None
    return Account(ref, actor, draft.item, draft.recipient, claim,
                   tuple(basis), recall.ref, guard, uncertainty)


def select_action(account):
    """A recalled prediction can guide an attempt; it is never a world fact."""
    transfer = account.guard is None and account.claim is not None and account.claim.object == account.owner
    op = TRANSFER if transfer else INSPECT
    inputs = (account.item, account.recipient) if transfer else (account.item,)
    return ActionRequest(account.owner, op, inputs, account.evidence)


def after_inspection(account, observation):
    claims = tuple(p for p in observation.content
        if p.subject == account.item and p.relation == "owned_by")
    if len(claims) != 1: raise ValueError("inspection must expose exactly one ownership result")
    observed = claims[0]
    discrepancy = account.claim is not None and observed.object != account.claim.object
    action = (ActionRequest(account.owner, TRANSFER, (account.item, account.recipient),
              account.evidence + (observation.ref,))
              if observed.object == account.owner else None)
    return action, discrepancy


def observed_content(account, observations):
    """Retain the latest delivered consequence, without reconstructing hidden state."""
    candidates = tuple(p for o in observations for p in o.content
        if p.subject == account.item and p.relation == "owned_by")
    if candidates:
        return (candidates[-1],), ClaimStatus.ENDORSED
    return (() if account.claim is None else (account.claim,)), ClaimStatus.TENTATIVE
