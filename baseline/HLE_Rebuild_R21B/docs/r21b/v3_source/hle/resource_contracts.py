"""R21A requirement order within one explicitly selected episode allocation.

Actual demand resources remain actual wallets. The order says nothing about
affordability. Historical compare_demands and unenrolled episodes retain v1.
"""
from dataclasses import dataclass

from .clearance_records import EpisodeResourceContract
from .contracts import Ref, Kind
from .development_contracts import (DevelopmentalDemand, ResourceEnvelope,
                                    DemandComparison, Comparison)

PROTOCOL_ID = 'r21.resource-comparison.v2'
PROTOCOL_SHA256 = 'acc58b9bc450e177747645ef5b4b5fc741a8b83d1edbfa229f92fec8eccdda04'
PROTOCOL_REF = Ref(Kind.PROTOCOL, PROTOCOL_ID, 2)
BUDGETS = {'adequate': 100000, 'constrained_feasible': 20000, 'inadequate': 0}
V3_ID = 'r21.integrated-policy.v3'
V3_SHA256 = '03d563755b2a1a2da88a98939fcf882189e4563216e4467b23af0dc40e822d20'
V3_BUDGETS = {'adequate': 200000, 'constrained_feasible': 100000, 'inadequate': 0}
V3_CONTROLS = (V3_ID+'.no_reuse', V3_ID+'.legacy_cost')


def specification(command):
    """Select exact historical semantics; never upgrade an existing episode."""
    if command.protocol_id == PROTOCOL_ID and command.protocol_sha256 == PROTOCOL_SHA256:
        return BUDGETS, PROTOCOL_REF
    if command.protocol_id in (V3_ID,)+V3_CONTROLS and command.protocol_sha256 == V3_SHA256:
        return V3_BUDGETS, Ref(Kind.PROTOCOL, command.protocol_id, 3)
    raise ValueError('unsupported resource/comparison contract')


def protocol_ref(command):
    return specification(command)[1]


@dataclass(frozen=True)
class ResourceFrame:
    contract: EpisodeResourceContract
    actor: Ref
    allocation: ResourceEnvelope


def validate_declaration(w, command):
    if len(w._journal) != 1 or w.clearance_monitor.resource_contract is not None:
        raise ValueError('select the episode contract immediately after genesis')
    budgets, _ = specification(command)
    if command.regime not in budgets:
        raise ValueError('unsupported resource/comparison contract')
    budget = budgets[command.regime]
    if (set(x.actor for x in w.config.wallets) != set(w.config.actors)
            or any((x.energy, x.time) != (budget, budget) for x in w.config.wallets)):
        raise ValueError('genesis wallets must match the declared per-actor regime')


def frame_for(w, actor):
    allocation = next(x for x in w.config.wallets if x.actor == actor)
    return ResourceFrame(w.clearance_monitor.resource_contract, actor,
                         ResourceEnvelope(allocation.energy, allocation.time, None))


def wallet_relation(current, prior):
    delta = (current.energy-prior.energy, current.time-prior.time)
    return ('equal' if not any(delta) else
            'less_headroom' if all(x <= 0 for x in delta) else
            'more_headroom' if all(x >= 0 for x in delta) else 'mixed_headroom')


def compare_demands_v2(current, prior, current_frame, prior_frame):
    """Componentwise requirements; actual declining wallets remain recorded.

Changed identity/context/party/allocation, mixed requirements, credits, or
increased balances cannot silently become an equal/greater demand claim.
"""
    if type(current) is not DevelopmentalDemand or type(prior) is not DevelopmentalDemand:
        raise ValueError('versioned demands required')
    a = {r.name: r.magnitude for r in current.requirements}
    b = {r.name: r.magnitude for r in prior.requirements}
    changes = tuple((k, b[k], a[k]) for k in sorted(a.keys() & b.keys()) if a[k] != b[k])

    def valid_frame(demand, frame):
        if type(frame) is not ResourceFrame or type(frame.contract) is not EpisodeResourceContract:
            return False
        c = frame.contract
        try: budgets, ref = specification(c)
        except ValueError: return False
        return (c.regime in budgets and frame.actor == demand.participants[0]
                and demand.comparison_protocol == ref
                and frame.allocation == ResourceEnvelope(budgets[c.regime], budgets[c.regime], None)
                and demand.resources.replenishment_rule is None
                and demand.resources.energy <= frame.allocation.energy
                and demand.resources.time <= frame.allocation.time)

    def duration(d):
        s = d.duration
        return None if s.end is None else (s.end.tick-s.start.tick, s.end.order-s.start.order)

    scope = ('family', 'comparison_protocol', 'required_outcomes', 'movements',
             'context', 'participants', 'material_lineage', 'constraints')
    valid = (valid_frame(current, current_frame) and valid_frame(prior, prior_frame)
             and current_frame == prior_frame
             and wallet_relation(current.resources, prior.resources) in ('equal', 'less_headroom'))
    if (not valid or any(getattr(current, k) != getattr(prior, k) for k in scope)
            or duration(current) != duration(prior) or a.keys() != b.keys()):
        return DemandComparison(current.ref, prior.ref, Comparison.INCOMPARABLE, changes,
                                'v2 demand scope or fixed allocation changed')
    delta = [a[k]-b[k] for k in a]
    relation = (Comparison.EQUAL if not any(delta) else
                Comparison.GREATER if all(x >= 0 for x in delta) else
                Comparison.LESSER if all(x <= 0 for x in delta) else Comparison.INCOMPARABLE)
    return DemandComparison(current.ref, prior.ref, relation, changes,
                            'v2 requirement order only; actual affordability is separate')
