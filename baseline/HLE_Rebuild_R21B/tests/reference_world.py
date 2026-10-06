"""Deliberately offline reference folds; no imports from hle.world."""
from hle.contracts import Moment
from hle.world_records import Wallet


def order(ref):
    return ref.kind.value, ref.key, ref.revision


def fold(config, journal):
    facts, tasks, memories, seen = {}, {}, {}, set()
    wallets = {w.actor: w for w in config.wallets}
    for index, tx in enumerate(journal):
        event = tx.event
        assert event.when == Moment(index, 0)
        assert all(c.event in seen for c in event.causes)
        if event.corrects is not None:
            assert event.corrects in seen
        assert event.ref not in seen
        seen.add(event.ref)
        for change in event.changes:
            fact = change.before or change.after
            key = (fact.subject, fact.relation, fact.context)
            assert facts.get(key) == change.before
            if change.after is None:
                del facts[key]
            else:
                facts[key] = change.after
        assert event.work == tuple(w.ref for w in tx.works)
        for work in tx.works:
            before = {a.unit.key: a.amount for a in work.before}
            credit = {a.unit.key: a.amount for a in work.credited}
            charged = {a.unit.key: a.amount for a in work.charged}
            after = {a.unit.key: a.amount for a in work.after}
            wallet = wallets[work.owner]
            assert before == {"r2.energy_quantum": wallet.energy, "r2.time_quantum": wallet.time}
            assert all(before[u] + credit.get(u, 0) - charged.get(u, 0) == after[u] for u in before)
            wallets[work.owner] = Wallet(work.owner, after["r2.energy_quantum"], after["r2.time_quantum"])
        if tx.task is not None:
            tasks[(tx.task.actor, tx.task.key)] = tx.task
        for memory in tx.memories:
            memories[(memory.owner, memory.ref.key)] = memory
    return (Moment(len(journal)-1, 1),
        tuple(sorted(facts.values(), key=lambda p: (order(p.subject), p.relation, order(p.context)))),
        tuple(wallets[a] for a in sorted(wallets, key=order)),
        tuple(tasks[k] for k in sorted(tasks, key=lambda k: (order(k[0]), k[1]))),
        tuple(memories[k] for k in sorted(memories, key=lambda k: (order(k[0]), k[1]))))


def fact_at(journal, claim, at):
    value = None
    source = None
    for tx in journal:
        if tx.event.when > at:
            break
        for change in tx.event.changes:
            fact = change.before or change.after
            if (fact.subject, fact.relation, fact.context) == (claim.subject, claim.relation, claim.context):
                value, source = change.after, tx.event.ref
    return value, source
