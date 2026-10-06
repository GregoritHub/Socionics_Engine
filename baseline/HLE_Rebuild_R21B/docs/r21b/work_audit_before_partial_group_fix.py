"""Independent raw fold of v3 extents, paid reuse provenance and actual choice.

No participant caches, selectors, cost-quote helpers or evaluator statuses are
read. The finite predicate equations and extent schedule are reimplemented.
"""
from hle.individuation_records import CircuitCommand, CircuitOffer, CircuitTransaction
from hle.clearance_records import EpisodeResourceContract, WithdrawEvidence
from hle.contracts import WorkStatus
from hle.model_a import fields, position_of
from hle.resource_contracts import V3_ID, V4_ID


def key_for(context, f, o, menu):
    return (context, f.partner, o.available, o.condition, o.observed_epoch-f.epoch,
            o.start, o.ready_at, o.duration, o.load, o.output, o.cost, o.claims,
            o.license, f.due, f.budget, f.credits, f.minimum_output,
            dict(menu.permissions).get(o.key, False), dict(menu.acknowledgments).get(o.key, False))


def predicates(f, o, menu):
    claims = {}
    for k, v in o.claims: claims.setdefault(k, set()).add(v)
    return dict(ne=o.available, si=o.condition == 'clean' and o.observed_epoch == f.epoch,
        ni=o.ready_at <= o.start and o.start+o.duration <= f.due,
        se=o.load <= f.budget, te=o.cost <= f.credits and o.output >= f.minimum_output,
        ti=all(len(v) == 1 for v in claims.values()),
        fi=dict(menu.permissions).get(o.key, False), fe=dict(menu.acknowledgments).get(o.key, False))


def audit_paid_work(w):
    orders = {}; records = {}; origins = {}; groups = {}; invalid = set()
    cache = {}; jobs = {}; pending = {}; errors = []; mode = 'legacy_cost'
    counts = dict(jobs=0, choices=0, option_lookups=0, reused_options=0,
                  computed_keys=0, source_receipts=0, charged=0)

    def check(ok, reason, event):
        if not ok: errors.append(event.key+': '+reason)

    def live(ref): return ref not in invalid and origins.get(ref) not in invalid

    for tx in w._journal:
        c = tx.command; er = tx.event.ref
        if type(c) is EpisodeResourceContract:
            mode = 'reuse' if c.protocol_id in (V3_ID,V4_ID) else c.protocol_id.rsplit('.', 1)[-1]
        if type(c) is WithdrawEvidence: invalid.add(c.source)
        if tx.event.corrects is not None: invalid.add(tx.event.corrects)
        if type(c) is CircuitOffer:
            groups.setdefault((c.learner, c.partner, c.epoch), []).append(c.key)
        if type(c) is CircuitCommand and mode in ('reuse', 'no_reuse', 'legacy_cost'):
            j = tx.job; order = orders.get(c.order); op = c.operator
            fresh_job = (c.actor, c.task_id) not in jobs
            actor_cache = cache.setdefault(c.actor, {})
            new = {}; receipts = []; keys = []; hits = 0
            if op == 'choose':
                f = order.offer; menu = records[order.menu]
                for o in f.options:
                    k = key_for(w.config.context, f, o, menu); keys.append(k)
                    entry = actor_cache.get(k) if mode == 'reuse' else None
                    if entry is not None and all(live(r) for r in entry[1]):
                        hits += 1; receipts.extend(entry[1])
                        check(entry[0] == predicates(f, o, menu), 'reused value differs from fresh predicates', er)
                    else: new[k] = predicates(f, o, menu)
            if fresh_job:
                if mode == 'legacy_cost': extent = 2 if order is None else 2+8*len(order.offer.options)
                elif order is None or op == 'withdraw': extent = 2
                elif op in ('menu', 'refresh'): extent = 2+2*len(order.offer.options)
                elif op == 'choose':
                    f = order.offer
                    extent = 2+2*len(f.options)+8*len(new)+len(groups[f.learner, f.partner, f.epoch])
                elif op == 'review': extent = 5
                elif op in ('coordinate', 'organize'): extent = 3
                elif op == 'apply': extent = 11
                elif op in ('inspect', 'consult'): extent = 3+len(records[order.outcome].errors)
                elif op == 'feedback':
                    extent = 3+len(order.uses)+8*len(order.provisional)+len(records[order.signal].errors)
                else: extent = -1
                price = lambda e: 5-fields(position_of(j.plan.routing_type, e))['dimensionality'] if w.policy.positional_prices else 1
                check(j.plan.content_units == extent*price(j.plan.path[-1]), 'unjustified work extent or price', er)
                check(j.plan.hop_units == tuple(price(e) for e in j.plan.path[1:]), 'hop price changed', er)
                check(set(receipts) <= set(j.basis), 'missing paid reuse source in causal basis', er)
                jobs[c.actor, c.task_id] = (j.plan, j.basis, j.version, j.signature, 0)
                counts['jobs'] += 1
                if op == 'choose':
                    counts['option_lookups'] += len(keys); counts['reused_options'] += hits
                    counts['computed_keys'] += len(new); counts['source_receipts'] += len(set(receipts))
            plan, basis, version, signature, paid = jobs[c.actor, c.task_id]
            check((j.plan, j.basis, j.version, j.signature) == (plan, basis, version, signature),
                  'partial job changed its paid contract', er)
            spent = sum(r.completed_units for r in tx.works)
            check(j.paid == paid+spent and j.paid <= plan.required, 'paid job conservation', er)
            for work in tx.works:
                check(work.required_units == plan.required-paid and
                      all(x.amount == work.completed_units for x in work.charged), 'work receipt extent', er)
            jobs[c.actor, c.task_id] = (plan, basis, version, signature, j.paid)
            counts['charged'] += spent
            if tx.event.outcome == WorkStatus.COMPLETED:
                check(j.paid == plan.required, 'unpaid result publication', er)
                check(all(live(r) for r in basis), 'invalid support published a result', er)
                if op == 'choose':
                    counts['choices'] += 1
                    f = order.offer; menu = records[order.menu]
                    guards = {records[r].aspect for r in j.signature if hasattr(records.get(r), 'aspect')}
                    guards |= set(pending.get(c.actor, {}))
                    options = []
                    for n, o in enumerate(f.options):
                        values = predicates(f, o, menu); load = 0; remaining = 0
                        for other_key in groups[f.learner, f.partner, f.epoch]:
                            other = orders[other_key]
                            if other.outcome is None: remaining += 1
                            else:
                                s = records[other.outcome]
                                prior = next((x for x in other.offer.options if x.key == s.option), None)
                                if s.success and prior is not None and prior.start == o.start: load += prior.load
                        if 'se' in guards: values['se'] = o.load <= max(0, f.budget-load)//max(1, remaining)
                        if all(values[a] for a in guards): options.append((o.cost, o.start+o.duration, n, o.key))
                    expected = min(options)[-1] if options else None
                    check(tx.order.chosen == expected, 'choice differs from fresh owned constraints', er)
                    if mode == 'reuse':
                        for k, value in new.items(): actor_cache[k] = (value, (er, order.bulletin, menu.ref))
            elif op == 'choose':
                check(tx.order is None and not tx.capacities, 'incomplete choose published owned content', er)
        # Only raw committed payloads enter the independent derived state.
        records[er] = tx.event; origins[er] = er
        for attr in ('communication', 'signal', 'order', 'capacity', 'candidate', 'study', 'account', 'processing'):
            rec = getattr(tx, attr, None)
            if rec is not None and hasattr(rec, 'ref'): records[rec.ref] = rec; origins[rec.ref] = er
        for rec in getattr(tx, 'capacities', ()):
            records[rec.ref] = rec; origins[rec.ref] = er
        if type(tx) is CircuitTransaction:
            if tx.order is not None:
                orders[tx.order.offer.key] = tx.order
                if type(c) is CircuitOffer:
                    records[tx.order.bulletin] = c; origins[tx.order.bulletin] = er
            if tx.tentative is not None: pending[c.actor] = dict(tx.tentative)
    return {'schema': 'r21b-paid-work-raw-audit-v1', 'passed': not errors,
            'mode': mode, 'errors': errors, **counts,
            'retained_predicate_entries': sum(len(x) for x in cache.values())}
