"""Offline bounded reference; no World, selection, guard or runtime index helpers.

Reconstruct physical state, work conservation, exact local consent, linked plan
outcomes and practice summaries in one journal pass. It deliberately does not
claim independent coverage of the entire psychological/semantic model.
"""
from collections import Counter
from hle.codec import loads
from hle.contracts import Observation, WorkStatus
from hle.language_records import Interpretation
from hle.organization_records import OrganizationPacket, OrganizationResult, Ratify
from hle.socion_records import Reception
from hle.world_records import Attempt, Credit, INSPECT, RETAIN, SEND, TRANSFER

TERMINAL = (WorkStatus.COMPLETED, WorkStatus.FAILED)


def quantities(values):
    return {v.unit.key: v.amount for v in values}


def reconstruct(config, journal):
    owners = {o.item: o.owner for o in config.ownership}
    balances = {x.actor: {'r2.energy_quantum': x.energy, 'r2.time_quantum': x.time}
        for x in config.wallets}
    records = {}; heads = {}; received = set(); plans = {}; by_key = {}
    task_paid = {}; practice = {}; counts = Counter(); charged = Counter()

    def packet(actor, ref):
        r = records[ref]
        assert type(r) is Observation and r.observer == actor, 'foreign consent'
        assert (actor, ref) in received, 'consent not paid/received'
        message = records[r.source]
        value = loads(r.content[0].object)
        assert type(value) is OrganizationPacket and value.sender == message.sender, 'unauthenticated packet'
        return value

    def endpoint(ref):
        plan = plans[ref]; r = plan['record']
        if plan['indexed'] or plan['outcome'] not in ('fulfilled', 'failed', 'blocked'):
            return
        plan['indexed'] = True
        s = r.speech
        if s is None or len(s.calls) != 1 or not s.actions or s.actions[-1].operation != 'transfer':
            return
        call = s.calls[0]
        if len(call.arguments) != 2 or call.arguments[1] != r.owner:
            return
        item = call.arguments[0]
        if any(a.item != item for a in s.actions) or any(a.operation != 'inspect' for a in s.actions[:-1]):
            return
        meaning = records[r.definitions[0]].meaning if type(r) is Interpretation else r.terms.meaning
        if meaning.arity != 2 or tuple((p.subject, p.owner) for p in meaning.patterns) != ((0, 1),):
            return
        steps = tuple(a.operation for a in s.actions)
        key = (r.owner, item, meaning, steps)
        row = practice.setdefault(key, {'successes': 0, 'failures': 0, 'partners': set(), 'examples': ()})
        success = plan['outcome'] == 'fulfilled'
        row['successes' if success else 'failures'] += 1
        if success:
            row['partners'].add(s.actions[-1].recipient)
        row['examples'] = (row['examples'] + (ref,))[-2:]

    for index, tx in enumerate(journal):
        assert tx.event.when.tick == index, 'nonsequential journal'
        cmd = tx.command
        before_owner = None
        for work in tx.works:
            before, credits, costs, after = map(quantities,
                (work.before, work.credited, work.charged, work.after))
            assert before == balances[work.owner], 'work before balance mismatch'
            expected = {unit: before[unit] + credits.get(unit, 0) - costs.get(unit, 0) for unit in before}
            assert after == expected and min(after.values()) >= 0, 'work conservation mismatch'
            if type(cmd) is Credit:
                assert credits == {'r2.energy_quantum': cmd.energy, 'r2.time_quantum': cmd.time}
                assert not costs
            else:
                assert not credits, 'undocumented external credit'
                assert costs.get('r2.energy_quantum', 0) == work.completed_units
                assert costs.get('r2.time_quantum', 0) == work.completed_units
            charged[work.owner] += costs.get('r2.energy_quantum', 0)
            balances[work.owner] = after
        if type(cmd) is Attempt:
            a = cmd.action
            cost = {INSPECT: 1, TRANSFER: 2, SEND: 1, RETAIN: 1}[a.operation]
            key = (a.actor, cmd.task_id)
            task_paid[key] = task_paid.get(key, 0) + sum(work.completed_units for work in tx.works)
            assert task_paid[key] <= cost, 'physical task overpayment'
            changes = [c.after for c in tx.event.changes if c.after is not None and c.after.relation == 'owned_by']
            if task_paid[key] < cost:
                assert tx.event.outcome in (WorkStatus.PARTIAL, WorkStatus.DEFERRED)
                assert not changes and not tx.messages and not tx.memories, 'unpaid consequence'
            elif a.operation == TRANSFER:
                before_owner = owners[a.inputs[0]]
                success = before_owner == a.actor and a.inputs[1] != a.actor
                assert tx.event.outcome == (WorkStatus.COMPLETED if success else WorkStatus.FAILED), 'ownership outcome mismatch'
                if success:
                    assert len(changes) == 1 and changes[0].subject == a.inputs[0] and changes[0].object == a.inputs[1]
                    owners[a.inputs[0]] = a.inputs[1]
                else:
                    assert not changes, 'failed transfer changed ownership'
                counts['physical_transfers'] += 1
                counts['failed_transfers'] += int(not success)
            elif a.operation == INSPECT:
                actual = [p.object for o in tx.observations if o.observer == a.actor
                    for p in o.content if p.relation == 'owned_by']
                assert actual == [owners[a.inputs[0]]], 'inspection differs from physical state'
            elif a.operation == SEND:
                success = (a.actor, a.inputs[0]) in config.message_links
                assert tx.event.outcome == (WorkStatus.COMPLETED if success else WorkStatus.FAILED)
                assert len(tx.messages) == int(success)
            target = None
            for prefix in ('organization-act:', 'language-act:'):
                if cmd.task_id.startswith(prefix):
                    plan_key, action_index = cmd.task_id[len(prefix):].rsplit(':', 1)
                    target = by_key[plan_key]
                    plan = plans[target]; r = plan['record']
                    assert plan['outcome'] == 'pending' and int(action_index) == plan['done'], 'unauthorized plan continuation'
                    wanted = r.speech.actions[plan['done']]
                    assert a.actor == r.owner and a.operation == (INSPECT if wanted.operation == 'inspect' else TRANSFER)
                    assert a.inputs == (wanted.item,) + (() if wanted.recipient is None else (wanted.recipient,))
                    if type(r) is OrganizationResult:
                        head = heads[(r.owner, r.terms.identity)]
                        assert head.status == 'active' and head.terms == r.terms, 'inactive authorization'
                    if tx.event.outcome == WorkStatus.FAILED:
                        plan['outcome'] = 'failed'
                    elif tx.event.outcome == WorkStatus.COMPLETED:
                        plan['done'] += 1
                        if type(r) is OrganizationResult and a.operation == INSPECT and owners[wanted.item] != r.owner:
                            plan['outcome'] = 'blocked'
                        elif plan['done'] == len(r.speech.actions):
                            plan['outcome'] = 'fulfilled'
                    endpoint(target)
        for r in tx.works + tx.messages + tx.memories + tx.observations:
            records[r.ref] = r
        for r in getattr(tx, 'extra', ()):
            if type(r) is Reception and r.outcome == WorkStatus.COMPLETED:
                received.add((r.owner, r.command.observation))
            if type(r) is Interpretation and r.status == 'accepted' or type(r) is OrganizationResult and r.kind == 'run':
                plans[r.ref] = {'record': r, 'done': 0, 'outcome': 'pending' if r.status == 'accepted' else r.status, 'indexed': False}
                by_key[r.ref.key] = r.ref
                if type(r) is OrganizationResult and r.status == 'accepted':
                    head = heads[(r.owner, r.terms.identity)]
                    assert head.status == 'active' and head.terms == r.terms
            if type(r) is OrganizationResult and r.terms is not None:
                key = (r.owner, r.terms.identity)
                if r.kind == 'proposal' and r.status == 'proposed':
                    evidence = practice.get((r.owner, r.terms.item, r.terms.meaning, r.terms.steps))
                    assert evidence and evidence['successes'] >= 2 and evidence['successes'] - 2 * evidence['failures'] > 0, 'unearned organization proposal'
                    assert set(evidence['examples']) <= set(r.sources), 'proposal missing owned practice'
                    counts['supported_proposals'] += 1
                if r.kind == 'agreement':
                    assert type(cmd.payload) is Ratify
                    review = records[cmd.payload.review]
                    prior = heads.get(key)
                    valid = review.status == 'accepted' and review.owner == r.owner and review.previous == (None if prior is None else prior.ref)
                    voters = [r.owner]
                    for ref in cmd.payload.votes:
                        vote = packet(r.owner, ref)
                        valid &= vote.kind == 'review' and vote.status == 'accepted' and vote.terms == review.terms
                        voters.append(vote.sender)
                    valid &= len(voters) == len(set(voters)) and set(voters) == set(review.terms.members)
                    assert (r.status == 'active') == bool(valid), 'exact consent mismatch'
                    counts['activations' if valid else 'unagreed'] += 1
                changes_head = (r.kind == 'agreement' and r.status == 'active' or
                    r.kind == 'exit' and r.status == 'withdrawn' or
                    r.kind == 'dispute' and r.status == 'suspended' or
                    r.kind == 'notice' and r.status in ('active', 'suspended', 'dissolved'))
                if changes_head:
                    heads[key] = r
                    # Offline reference intentionally scans its bounded plans.
                    for plan in plans.values():
                        p = plan['record']
                        if type(p) is OrganizationResult and plan['outcome'] == 'pending' and p.owner == r.owner and p.terms.identity == r.terms.identity:
                            if r.status != 'active' or r.terms != p.terms:
                                plan['outcome'] = 'cancelled'
            records[r.ref] = r
    counts.update({'events': len(journal), 'practice_summaries': len(practice), 'linked_plans': len(plans)})
    return {'owners': owners, 'balances': balances, 'heads': heads, 'plans': plans,
        'practice': practice, 'counts': dict(counts), 'charged': charged}


def check_world(w):
    """Compare independent results with maintained views only after reconstruction."""
    result = reconstruct(w.config, w._journal)
    for actor, balance in result['balances'].items():
        wallet = w._wallets[actor]
        assert (wallet.energy, wallet.time) == (balance['r2.energy_quantum'], balance['r2.time_quantum'])
    for item, owner in result['owners'].items():
        assert w._facts[(item, 'owned_by', w.config.context)].object == owner
    for (actor, identity), head in result['heads'].items():
        assert w.organization_state(actor, identity) == head
    for ref, plan in result['plans'].items():
        r = plan['record']
        actual = w.language_outcome(r.owner, ref) if type(r) is Interpretation else w.organization_outcome(r.owner, ref)
        assert plan['outcome'] == actual, ('linked outcome', ref, actual, plan['outcome'])
    actual = {}
    for actor in w.config.actors:
        for p in w.practices(actor):
            actual[(actor, p.item, p.meaning, p.steps)] = {'successes': p.successes,
                'failures': p.failures, 'partners': set(p.partners), 'examples': p.examples}
    assert actual == result['practice'], 'incremental practice differs from journal reference'
    return {**result['counts'], 'mismatches': 0,
        'outcomes': dict(Counter(p['outcome'] for p in result['plans'].values())),
        'physical_owners': {k.key: v.key for k, v in result['owners'].items()},
        'energy_debits': {k.key: v for k, v in result['charged'].items()}}
