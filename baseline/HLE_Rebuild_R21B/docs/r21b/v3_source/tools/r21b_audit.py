"""Whole-episode contract evidence; replay and feasibility are separate gates."""
from dataclasses import replace

from hle.clearance_reference import compare
from hle.clearance_records import ClearanceBoundary, EpisodeResourceContract
from hle.clearance_demo import offers
from hle.individuation_records import CircuitOffer, CircuitTransaction
from hle.conversion_records import ConversionTransaction
from hle.autonomy_records import WorkshopCommand
from hle.contracts import WorkStatus
from hle.world_records import ENERGY, TIME
from r21_reference import resource_audit, renewal_audit
from r21_workloads import make_world, permutation, renewal_case
from r21b_policy import episode_scope, genesis_digest, run_reference_policy, POLICY_ID
from hle.resource_contracts import V3_BUDGETS as BUDGETS, V3_ID


def horizon_audit(w, rows, seed, clearance_stop):
    """Check complete, ordered, nonoverlapping actual environment exposures."""
    errors = []
    previous_stop = clearance_stop
    facts = {}
    def fold_facts(events):
        for tx in events:
            for change in tx.event.changes:
                p = change.after or change.before
                key = (p.subject.key, p.relation)
                if change.after is None:facts.pop(key, None)
                else:facts[key] = change.after.object
    if type(clearance_stop) is int and 0 <= clearance_stop <= len(w._journal):
        fold_facts(w._journal[:clearance_stop])
    for n, row in enumerate(rows):
        expected_case = renewal_case(seed, n)
        start, stop = row.get('start'), row.get('stop')
        if (type(start) is not int or type(stop) is not int
                or not 0 <= start < stop <= len(w._journal)
                or start != previous_stop):
            errors.append(f'opportunity {n+1}: missing, overlapping or invalid interval')
            continue
        previous_stop = stop
        events = w._journal[start:stop]
        if row.get('number') != n+1 or row.get('case') != expected_case:
            errors.append(f'opportunity {n+1}: schedule mismatch')
        expected = [replace(f, options=tuple(permutation(seed, f'renew:{n}')(f.options)))
                    for f in offers(w, expected_case, f'r21:{seed}:renew:{n}')]
        actual = [tx.command for tx in events if type(tx.command) is CircuitOffer]
        if actual != expected or row.get('orders') != [f.key for f in expected]:
            errors.append(f'opportunity {n+1}: raw offers differ from the full declared challenge')
        # Physical return must occur after owned conditional recall, in this
        # interval, for the same actual loan and item.
        item = row.get('item')
        loans = {tx.event.ref for tx in events if type(tx.command) is WorkshopCommand
                 and tx.command.operation == 'lend' and tx.command.inputs[0].key == item
                 and tx.command.inputs[1] == w.config.actors[0] and tx.event.outcome == WorkStatus.COMPLETED}
        uses = [(i, tx.use) for i, tx in enumerate(events) if type(tx) is ConversionTransaction
                and tx.use is not None and tx.use.owner == w.config.actors[0]
                and tx.use.item.key == item and tx.use.loan in loans and tx.use.capacity is not None]
        returns = [i for i, tx in enumerate(events) if type(tx.command) is WorkshopCommand
                   and tx.command.operation == 'return' and tx.command.actor == w.config.actors[0]
                   and tx.command.inputs[0].key == item and tx.event.outcome == WorkStatus.COMPLETED]
        if not any(i < j for i, _ in uses for j in returns):
            errors.append(f'opportunity {n+1}: missing own conditional physical return')
        fold_facts(events)
        if not (facts.get((item, 'condition')) == 'clean'
                and facts.get((item, 'loan_active')) is False
                and facts.get((item, 'owned_by')) is not None
                and facts.get((item, 'owned_by')) == facts.get((item, 'return_to'))):
            errors.append(f'opportunity {n+1}: physical facts do not establish clean authorized return')
        final_orders = {tx.order.offer.key: tx.order for tx in events
                        if type(tx) is CircuitTransaction and tx.order is not None}
        for key in row.get('orders', []):
            order = final_orders.get(key)
            if order is None or len(set(order.uses)) != 8:
                errors.append(f'opportunity {n+1}: eight distinct retained capacities required')
    # Never count repeated intervals, quiet ticks or metadata rows as demand.
    if errors:
        return {'passed': False, 'eligible': 0, 'demand_changes': 0, 'errors': errors,
                'completed_rows': len(rows)}
    result = renewal_audit(w, rows)
    result['passed'] = result['passed'] and len(rows) == 100
    result['errors'] = errors
    return result


def phase_spending(w, cuts):
    """Descriptive attribution only; full raw conservation is checked separately."""
    boundaries = [(name, cuts[name]) for name in ('conversion', 'aspects', 'clearance', 'horizon') if name in cuts]
    boundaries.append(('remaining_or_unfinished', len(w._journal)))
    start = 0; result = []
    for name, stop in boundaries:
        if type(stop) is not int or not start <= stop <= len(w._journal):
            raise ValueError('invalid phase interval')
        spent = {a.key: {'energy': 0, 'time': 0} for a in w.config.actors}
        for tx in w._journal[start:stop]:
            for work in tx.works:
                for charge in work.charged:
                    spent[work.owner.key]['energy' if charge.unit == ENERGY else 'time'] += charge.amount
        result.append({'phase_end': name, 'start': start, 'stop': stop, 'charged': spent})
        start = stop
    return result


def audit_episode(w, meta):
    errors = []
    scope = episode_scope(w)
    expected, _ = make_world(scope['tim'], scope['seed'], BUDGETS[scope['regime']])
    if scope['genesis_sha256'] != genesis_digest(expected):
        errors.append('genesis/policies differ from the declared scenario')
    if scope != meta.get('scope'):
        errors.append('reported scope differs from the actual episode')
    raw = compare(w)
    resources = resource_audit(w)
    if any(n for row in resources['credited'].values() for n in row.values()):
        errors.append('refunds or hidden credits are not permitted')
    begins = [i for i, tx in enumerate(w._journal) if type(tx.command) is ClearanceBoundary
              and tx.command.operation == 'begin']
    history_end = begins[0] if begins else len(w._journal)
    lend = set(); returned = set()
    for tx in w._journal[:history_end]:
        c = tx.command
        if type(c) is WorkshopCommand and tx.event.outcome == WorkStatus.COMPLETED:
            if c.operation == 'lend' and c.inputs[1] == w.config.actors[0]:lend.add(c.inputs[0].key)
            if c.operation == 'return' and c.actor == w.config.actors[0]:returned.add(c.inputs[0].key)
    required = {'tool:'+str(n) for n in range(scope['history']+scope['maintained']+2)}
    history = {'required_items': sorted(required), 'loaned': sorted(required & lend),
               'returned': sorted(required & returned), 'passed': required <= lend & returned}
    closes = [i for i, tx in enumerate(w._journal) if type(tx.command) is ClearanceBoundary
              and tx.command.operation == 'close']
    clearance_stop = meta.get('cuts', {}).get('clearance')
    if clearance_stop is not None:
        # The last delay challenge closes before its declared schedule reset.
        if len(closes) != 13 or clearance_stop != closes[-1]+2:
            errors.append('clearance cut does not cover the full raw challenge window')
    sustained = horizon_audit(w, meta.get('opportunities', []), scope['seed'], clearance_stop)
    clearance = raw['reference']['status'] == 'cleared_in_scope'
    from r21b_work_audit import audit_paid_work
    work_audit = audit_paid_work(w)
    complete = (work_audit['passed'] and not errors and raw['passed'] and resources['passed'] and history['passed']
                and clearance and sustained['passed'] and resources['unfinished_count'] == 0
                and meta.get('stage') == 'finished' and not meta.get('resource_stop')
                and not meta.get('error'))
    return {'schema': 'r21b-whole-episode-audit-v1', 'scope': scope,
            'integrity_passed': not errors and raw['passed'] and resources['passed'] and work_audit['passed'],
            'paid_work': work_audit,
            'errors': errors, 'history': history, 'raw_clearance': raw, 'resources': resources,
            'sustained': sustained, 'phase_spending': phase_spending(w, meta.get('cuts', {})),
            'successful_full_horizon': complete}


def evaluate_feasibility(candidate, candidate_meta, *, evaluation=False):
    """Always execute the independent construction; never accept a replay label."""
    assessed = audit_episode(candidate, candidate_meta)
    scope = assessed['scope']
    witness, metadata = run_reference_policy(scope['tim'], scope['seed'], scope['regime'], evaluation=evaluation)
    independent = audit_episode(witness, metadata)
    same = assessed['scope'] == independent['scope']
    result = {'schema': 'r21b-feasibility-gate-v1', 'policy_id': POLICY_ID,
              'execution': 'separately constructed from identical genesis; no candidate command input',
              'same_scope': same, 'candidate_success': assessed['successful_full_horizon'],
              'independent_success': independent['successful_full_horizon'],
              'passed': same and scope['protocol_id']==V3_ID and assessed['successful_full_horizon'] and independent['successful_full_horizon'],
              'failed_witness_is_not_impossibility_proof': True}
    return result, witness, metadata, independent
