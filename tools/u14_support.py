"""Release evidence utilities. No participant decision policy is defined here."""
import gzip
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'baseline/HLE_Rebuild_R21B'
sys.path[:0] = [str(ROOT), str(BASE)]
sys.dont_write_bytecode = True


def digest(value):
    return hashlib.sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def save_gzip(path, text):
    Path(path).write_bytes(gzip.compress(text.encode(), compresslevel=6, mtime=0))


def source_manifest():
    paths = set()
    for directory in ('hle_unified', 'tools', 'reference_u12', *(f'tests_u{i}' for i in range(2, 15))):
        paths.update((ROOT / directory).rglob('*.py'))
    paths.update(BASE.rglob('*.py'))
    paths.update(p for p in (ROOT / 'contracts').iterdir()
                 if p.is_file() and not p.name.startswith('U14_Progress'))
    return {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in sorted(paths)}


def raw_accounting(transactions):
    """Reconstruct each owner's spending without importing executor helpers.

    In addition to the inherited semantic audit, check EVERY wallet transition,
    immutable allocation, operation work delta and owner. Input is raw writes.
    """
    heads, balances, initial, charged, latest_jobs = {}, {}, {}, {}, {}
    for tx in transactions:
        jobs, wallets = [], []
        for v in tx.versions:
            d = {a.name: a.value for a in v.attributes}
            if d.get('record_type') == 'operation': jobs.append((v, d))
            if d.get('record_type') == 'wallet': wallets.append((v, d))
        if len(jobs) > 1: raise ValueError('multiple jobs in one accounting transaction')
        delta = 0
        actor = None
        if jobs:
            v, d = jobs[0]
            old = heads.get(v.ref.identity, {})
            if old and (old['actor'] != d['actor'] or old['required'] != d['required']):
                raise ValueError('work owner or extent changed')
            delta = d['completed'] - old.get('completed', 0)
            if delta < 0 or d['spent'] != d['completed'] or d['completed'] > d['required']:
                raise ValueError('invalid work delta')
            if old and d['spent'] - old['spent'] != delta: raise ValueError('erased spending')
            actor = d['actor']
            charged[actor] = charged.get(actor, 0) + delta
            latest_jobs[v.ref.identity] = d
        changed = []
        for v, d in wallets:
            a = d['actor']; pair = (d['energy'], d['time'])
            allocation = (d['initial_energy'], d['initial_time'])
            if min(pair) < 0: raise ValueError('negative wallet')
            if a not in balances:
                if pair != allocation or v.previous is not None: raise ValueError('invalid allocation')
                initial[a] = pair
            else:
                if initial[a] != allocation: raise ValueError('allocation rewritten')
                if a != actor or delta <= 0: raise ValueError('unexplained wallet update')
                if pair != tuple(x-delta for x in balances[a]): raise ValueError('unmatched debit')
                changed.append(a)
            balances[a] = pair
        if delta and changed != [actor]: raise ValueError('work lacks exact owned debit')
        for v in tx.versions: heads[v.ref.identity] = {a.name: a.value for a in v.attributes}
    rows = []
    for actor in sorted(initial):
        spent = charged.get(actor, 0)
        if tuple(x-spent for x in initial[actor]) != balances[actor]:
            raise ValueError('aggregate wallet mismatch')
        rows.append(dict(actor=f'{actor.namespace}:{actor.key}', initial=list(initial[actor]),
                         remaining=list(balances[actor]), charged=spent))
    statuses = {}
    for d in latest_jobs.values(): statuses[d['status']] = statuses.get(d['status'], 0) + 1
    return dict(passed=True, actors=rows, total_charged=sum(charged.values()),
                job_statuses=statuses, transactions=len(transactions))


def keep_engine(out, name, engine, audit):
    from hle_unified import codec
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    cp = engine.checkpoint()
    checkpoint_seconds = time.perf_counter() - start
    start = time.perf_counter()
    report = audit(engine.world.journal())
    accounting = raw_accounting(engine.world.journal())
    if report['charged_energy'] != accounting['total_charged']:
        raise ValueError('independent auditors disagree')
    for actor in engine._wallets:
        actual = engine.wallet(actor)
        row = next(r for r in accounting['actors'] if r['actor'] == f'{actor.namespace}:{actor.key}')
        if row['remaining'] != [actual['energy'], actual['time']]:
            raise ValueError('runtime wallet differs from raw writes')
    evaluation_seconds = time.perf_counter() - start
    raw = codec.dumps(tuple(engine.world.journal()))
    save_gzip(out / (name + '.checkpoint.json.gz'), cp)
    save_gzip(out / (name + '.transactions.json.gz'), raw)
    write_json(out / (name + '.audit.json'), dict(semantic=report, accounting=accounting))
    return dict(checkpoint_sha256=digest(cp), transactions_sha256=digest(raw),
                checkpoint_bytes=len(cp.encode()), checkpoint_seconds=checkpoint_seconds,
                evaluator_seconds=evaluation_seconds, accounting=accounting,
                semantic=report, transaction_count=len(engine.world.journal()))


def verify_freeze():
    frozen = json.loads((ROOT / 'U14_Execution_Manifest_v1.json').read_text())
    now = source_manifest()
    if frozen != now:
        raise ValueError('release source differs from freeze: ' + repr(
            [k for k in set(frozen) | set(now) if frozen.get(k) != now.get(k)]))
    return digest(json.dumps(frozen, sort_keys=True))
