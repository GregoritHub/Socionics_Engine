"""Independent bounded R16A replay on raw committed R15 transactions.

Does not use the live monitor, detector predicates, projected_path, participant
selector or derived runtime indexes. It independently identifies the supported
placement chain and quotient representatives. The shared tariff and recovered
OIG reference are mathematical definitions, not behavioral selection rules.
"""
from .contracts import WorkStatus, Ref, Kind
from .compensation_records import ReleaseTransaction, DEPENDENCY, REQUIRED, WIRE
from .autonomy_records import WorkshopCommand
from .world_records import ENERGY, TIME
from .crux import Perspective as P, Polarity
from .concept_structure import conceptual_path
from .processing import _route_geometry
from .development_structure import LensContent, observe_trajectory
from .shell_records import PROJECTION
from .shell_assessment import oig_json, reftext
from .codec import loads


def reference(world):
    records = {}; facts = {}; demands = {}; loans = {}; decision_to_loan = {}; works = {}; result = []
    profiles = {p.owner: p for p in world.profiles}
    for tx in world._journal:
        e = tx.event; cmd = tx.command
        for change in e.changes:
            p = change.after or change.before; key = p.subject, p.relation, p.context
            if facts.get(key) != change.before: raise ValueError('reference fact-chain mismatch')
            if change.after is None: facts.pop(key, None)
            else: facts[key] = change.after
        for r in (e,) + tx.works + tx.observations + tx.messages + tx.memories: records[r.ref] = r
        for name in ('concept', 'material', 'treatment', 'decision'):
            r = getattr(tx, name, None)
            if r is not None: records[r.ref] = r
        for d in getattr(tx, 'demands', ()):
            if d.specification.family == 'return_commitment': demands[d.owner, d.item] = d
        if cmd is not None and hasattr(cmd, 'task_id') and hasattr(cmd, 'actor'):
            works.setdefault((cmd.actor, cmd.task_id), []).extend(tx.works)
        if e.outcome != WorkStatus.COMPLETED: continue
        if type(tx) is ReleaseTransaction:
            packet = None; d = tx.decision
            if d is None and cmd.operator == 'enact': d = records[cmd.source]
            elif d is None and cmd.operator in ('review', 'assimilate'):
                o = records[cmd.source]; packet = loads(next(p.object for p in o.content if p.relation == WIRE))
                d = records[packet.decision]
            if d is None: continue
            v = d.view; key = d.owner, v.loan
            if tx.decision is not None and key not in loans:
                o = records[v.terms]; c = records.get(v.concept)
                if o.observer != d.owner or o.delivered_at.tick > e.when.tick:
                    raise ValueError('reference inaccessible terms')
                f = {p.relation: p.object for p in o.content if p.subject == v.item and p.context == world.config.context}
                learned = c is not None and DEPENDENCY in c.relations
                if f[REQUIRED] != v.required or learned != v.dependency: raise ValueError('reference view mismatch')
                lineage = d.material or (None if c is None else Ref(Kind.MEMORY, c.ref.key, 1))
                if lineage is None or lineage not in records: raise ValueError('reference missing lineage')
                current = tx.processing.active; cost = 0; extent = 1 + world.release.revision_unit * len(v.supports)
                for edge in conceptual_path(tx.job.plan.routing_type):
                    path, seats, support, at, hop, price = _route_geometry(tx.job.plan.routing_type, current,
                                    edge.element, Polarity.ACCUMULATION, world.policy.positional_prices)
                    cost += sum(hop) + extent * price; current = path[-1]
                balance = {r.unit: r.amount for r in tx.works[-1].after}
                demand = demands.get((d.owner, v.item))
                physical = (f.get('condition') == 'clean' and f.get('loan_active') is True
                            and f.get('return_due') is True and f.get('owned_by') == d.owner)
                status = 'eligible'
                if demand is None or demand.status != 'active': status = 'no_demand'
                elif not physical or c is None or not c.practiced: status = 'unavailable_operation'
                elif min(balance[ENERGY], balance[TIME]) < cost: status = 'insufficient_resources'
                loans[key] = {'item': v.item, 'path': [LensContent((P.I,), (), world.config.context, PROJECTION)],
                    'lineage': lineage, 'opportunity': status, 'first_place': None, 'placement_dependency': False,
                    'witness': [], 'units': 0, 'tim': profiles[d.owner].tim}
            b = loans.get(key)
            if b is None: continue
            domains = None; conflicting = False
            if cmd.operator == 'consider':
                domains = (P.I,); conflicting = v.dependency and not v.required
            elif cmd.operator == 'enact':
                if d.selection.mode == 'confirm':
                    domains = (P.I, P.WE); conflicting = v.dependency and not v.required
                    b['placement_dependency'] = conflicting
                    if conflicting and b['first_place'] is None: b['first_place'] = e.ref
                elif d.selection.mode == 'reconcile': domains = (P.I,)
            elif cmd.operator == 'review':
                domains = (P.IT, P.WE); conflicting = b['placement_dependency']
            elif cmd.operator == 'assimilate' and b['first_place'] is not None:
                current = records[tx.job.view.concept]
                kept = DEPENDENCY in current.relations
                domains = (P.I,); conflicting = b['placement_dependency'] or (kept and not v.required)
                if kept and not packet.required and not v.required and not b['witness']:
                    b['witness'] = [reftext(b['first_place']), reftext(e.ref)]
            elif cmd.operator == 'assimilate':
                # A warranted required confirmation also has an assimilation
                # operation, without a conflicting material representative.
                domains = (P.I,)
            if domains is not None:
                b['path'].append(LensContent(domains, (b['lineage'],) if conflicting else (), world.config.context, PROJECTION))
                b['units'] += sum(w.completed_units for w in works[cmd.actor, cmd.task_id])
        elif type(cmd) is WorkshopCommand and cmd.operation == 'return':
            keys = [k for k, b in loans.items() if k[0] == cmd.actor and b['item'] == cmd.inputs[0]]
            if len(keys) != 1: continue
            key = keys[0]; b = loans.pop(key)
            f = {r: p.object for (i, r, ctx), p in facts.items() if i == b['item'] and ctx == world.config.context}
            correct = f.get('condition') == 'clean' and f.get('loan_active') is False and f.get('owned_by') == f.get('return_to')
            b['path'].append(LensContent((P.IT,), (), world.config.context, PROJECTION))
            b['units'] += sum(w.completed_units for w in works[cmd.actor, cmd.task_id])
            eligible = b['opportunity'] == 'eligible'
            result.append({'engagement': reftext(key[1]), 'opportunity': b['opportunity'],
                'placement': 'unassessed' if not eligible else 'positive' if b['witness'] else 'negative',
                'events': b['witness'] if eligible else [], 'endpoint': 'correct' if correct else 'failed',
                'work_units': b['units'], 'oig': oig_json(observe_trajectory(b['tim'], b['path']))})
    return result
