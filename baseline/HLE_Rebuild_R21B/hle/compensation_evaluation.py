"""Offline R15 witnesses, independently folded from committed transactions.

Does not call participant selection, read runtime derived material indexes, or
issue a Shell/clearance verdict. Correct endpoints and maintained prerequisites
are separate reported variables. Integer accounting is reconstructed in full.
"""
from .contracts import WorkStatus, Kind, Observation
from .world_records import ENERGY, TIME, Credit, Message
from .autonomy_records import WorkshopCommand
from .compensation_records import (ReleaseTransaction, ReleaseDecision, ReleasePacket,
                                    REQUIRED, CONFIRMED, DEPENDENCY, WIRE)
from .codec import loads


def address(ref):
    return None if ref is None else ref.key + '@' + str(ref.revision)


def evaluate(world, setup=None):
    worker = world.config.actors[0]
    balances = {x.actor: (x.energy, x.time) for x in world.config.wallets}
    facts = {}; records = {}; messages = {}; decisions = {}; material = {}; treatments = {}
    errors = []; choices = []; returns = []; responses = []; debits = []; revisions = []
    concept = None; job_paid = {}; last_treatment = {}; total = 0
    for tx in world._journal:
        e = tx.event; records[e.ref] = e
        for cause in e.causes:
            if cause.event not in records or cause.event == e.ref: errors.append('invalid cause at ' + address(e.ref))
        for change in e.changes:
            p = change.before or change.after; key = (p.subject, p.relation, p.context)
            if facts.get(key) != change.before: errors.append('before fact mismatch at ' + address(e.ref))
            if change.after is None: facts.pop(key, None)
            else: facts[key] = change.after
        for work in tx.works:
            before = {a.unit: a.amount for a in work.before}; after = {a.unit: a.amount for a in work.after}
            charged = {a.unit: a.amount for a in work.charged}; credited = {a.unit:a.amount for a in work.credited}
            if (before.get(ENERGY), before.get(TIME)) != balances[work.owner]: errors.append('wallet before mismatch')
            if any(before[u] + credited.get(u,0) - after[u] != charged.get(u, 0) for u in (ENERGY, TIME)): errors.append('charge conservation mismatch')
            if type(tx.command) is not Credit and any(charged.get(u, 0) != work.completed_units for u in (ENERGY, TIME)): errors.append('logical unit mismatch')
            if type(tx.command) is Credit and (credited != {ENERGY:tx.command.energy,TIME:tx.command.time} or charged): errors.append('credit mismatch')
            balances[work.owner] = (after[ENERGY], after[TIME]); records[work.ref] = work
            total += charged.get(ENERGY,0)
        for record in tx.observations + tx.messages + tx.memories:
            records[record.ref] = record
        for m in tx.messages: messages[m.ref] = m
        current_concept = getattr(tx, 'concept', None)
        if current_concept is not None:
            records[current_concept.ref] = current_concept
            if current_concept.owner == worker:
                concept = current_concept
                revisions.append({'event': address(e.ref), 'ref': address(concept.ref),
                                  'dependency': DEPENDENCY in concept.relations,
                                  'practiced': concept.practiced})
        if type(tx) is ReleaseTransaction:
            j = tx.job; key = (tx.command.actor, tx.command.task_id)
            prior_paid = job_paid.get(key, 0)
            spent = sum(w.completed_units for w in tx.works)
            if j.paid != prior_paid + spent or j.paid > j.plan.required: errors.append('release payment progression mismatch')
            job_paid[key] = j.paid
            if any((tx.material, tx.treatment, tx.decision, tx.concept, tx.messages)) and (j.paid != j.plan.required or e.outcome != WorkStatus.COMPLETED):
                errors.append('unfunded or failed publication')
            if tx.material is not None:
                m = tx.material; material[m.ref] = m; records[m.ref] = m
                if m.owner != tx.command.actor or m.origin_event != e.ref: errors.append('invented material origin')
                if m.concept_at_origin not in records or not m.evidence_at_origin: errors.append('missing material content basis')
            if tx.treatment is not None:
                t = tx.treatment; origin = material.get(t.lineage); old = last_treatment.get(t.treating_actor)
                if origin is None or origin.owner != t.origin_actor or origin.origin_event not in t.source_events:
                    errors.append('material source erased or rewritten')
                if old is not None and (t.previous_revision != old.ref or t.lineage != old.lineage or not set(old.source_events) <= set(t.source_events)):
                    errors.append('broken treatment predecessor or origin')
                if not t.work_refs or any(r not in records for r in t.work_refs + t.selection_evidence + t.consequences):
                    errors.append('missing treatment witness')
                for ref in t.selection_evidence:
                    r = records.get(ref)
                    owner = r.observer if type(r) is Observation else getattr(r, 'owner', None)
                    if owner != t.treating_actor: errors.append('foreign treatment evidence')
                records[t.ref] = t; treatments[t.ref] = t; last_treatment[t.treating_actor] = t
            if tx.decision is not None:
                d = tx.decision; records[d.ref] = d; decisions[d.ref] = d
                v = d.view; obs = records[v.terms]
                local = {p.relation: p.object for p in obs.content if p.subject == v.item}
                seen_concept = records.get(v.concept)
                independently_eligible = (local.get('condition') == 'clean' and local.get('owned_by') == v.owner
                    and local.get('loan_active') is True and local.get('return_due') is True)
                if v.required != local.get(REQUIRED) or v.dependency != (seen_concept is not None and DEPENDENCY in seen_concept.relations):
                    errors.append('decision does not match owned evidence')
                choices.append({'decision': address(d.ref), 'event': address(e.ref), 'item': v.item.key,
                    'loan': address(v.loan), 'required': local.get(REQUIRED), 'eligible': independently_eligible,
                    'clean': local.get('condition') == 'clean', 'own_due': independently_eligible,
                    'learned_dependency': v.dependency, 'support_count': len(v.supports),
                    'mode': d.selection.mode, 'carrier': None if d.selection.carrier is None else d.selection.carrier.key,
                    'return_recipient': getattr(local.get('return_to'), 'key', None),
                    'alternatives': d.selection.alternatives,
                    'balance_after_consider': balances[v.owner], 'material': address(d.material)})
            d = tx.decision
            if d is None and tx.command.operator == 'enact': d = decisions.get(tx.command.source)
            if d is None and tx.command.operator in ('review', 'assimilate'):
                obs = records[tx.command.source]
                packet = loads(next(p.object for p in obs.content if p.relation == WIRE))
                d = decisions.get(packet.decision)
            if d is not None:
                debits.append({'event': address(e.ref), 'decision': address(d.ref), 'item': d.view.item.key,
                               'actor': tx.command.actor.key, 'operator': tx.command.operator,
                               'units': spent, 'optional': not d.view.required, 'dependency': d.view.dependency})
            elif j.view is not None:
                debits.append({'event':address(e.ref),'decision':None,'item':j.view.item.key,
                               'actor':tx.command.actor.key,'operator':tx.command.operator,
                               'units':spent,'optional':not j.view.required,'dependency':j.view.dependency})
            for msg in tx.messages:
                packet = loads(msg.content[0].object)
                if packet.kind == 'response':
                    responses.append({'event': address(e.ref), 'decision': address(packet.decision), 'item': packet.item.key,
                         'carrier': msg.sender.key, 'recipient': msg.receiver.key, 'approved': packet.approved,
                         'explicit_optional_evidence': not packet.required, 'reason': packet.reason})
        c = tx.command
        if type(c) is WorkshopCommand and c.operation == 'return' and c.actor == worker:
            item = c.inputs[0]; f = {r: p.object for (i, r, context), p in facts.items() if i == item}
            returns.append({'event': address(e.ref), 'item': item.key, 'completed': e.outcome == WorkStatus.COMPLETED,
                            'clean': f.get('condition') == 'clean', 'loan_closed': f.get('loan_active') is False,
                            'right_owner': f.get('owned_by') == f.get('return_to'),
                            'dependency_before_result_integration': concept is not None and DEPENDENCY in concept.relations})
    optional = [c for c in choices if not c['required']]
    maintained = [c for c in optional if c['eligible'] and c['learned_dependency'] and c['mode'] == 'confirm']
    optional_items = {c['item'] for c in optional}
    endpoints = [r for r in returns if r['item'] in optional_items]
    costs = {i: sum(d['units'] for d in debits if d['item'] == i and d['optional']) for i in sorted(optional_items)}
    history = []
    for t in treatments.values():
        history.append({'ref': address(t.ref), 'lineage': address(t.lineage), 'origin_actor': t.origin_actor.key,
            'origin_events': [address(r) for r in t.source_events], 'treatment': t.treatment.value,
            'carrier': None if t.carrier is None else t.carrier.key, 'previous': address(t.previous_revision),
            'evidence': [address(r) for r in t.selection_evidence], 'work': [address(r) for r in t.work_refs],
            'consequences': [address(r) for r in t.consequences]})
    return {'schema': 'r15-offline-witness-v1', 'events': len(world._journal), 'logical_work': total,
            'setup': setup, 'choices': choices, 'responses': responses, 'returns': returns,
            'optional_engagements': len(optional), 'maintained_optional_engagements': len(maintained),
            'correct_optional_endpoints': sum(r['completed'] and r['clean'] and r['loan_closed'] and r['right_owner'] for r in endpoints),
            'optional_release_work_by_item': costs, 'release_debits': debits, 'material_history': history,
            'concept_revisions': revisions, 'final_dependency': concept is not None and DEPENDENCY in concept.relations,
            'final_balances': {a.key: b for a, b in balances.items()}, 'oracle_errors': errors,
            'shell_assessment': 'unassessed; joint five-sign assessment belongs to R16',
            'clearance_assessment': 'unassessed; funded local reownership is not R17 conversion or R19 clearance'}
