"""One isolated, matched U13 worker. Reference processes never enable U13."""
import argparse
import gc
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import statistics
import sys
import time
import tracemalloc

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'baseline/HLE_Rebuild_R21B'
sys.dont_write_bytecode = True


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def timed(fn, repeat=1):
    samples = []
    for _ in range(repeat):
        gc.collect()
        t = time.perf_counter(); value = fn(); samples.append(time.perf_counter() - t)
        del value
    return samples


def native(args, protocol):
    from tests_u12.fixtures import setup12
    from tests_u4.fixtures import ALICE, BOB, ROOM, WRITER, ref, show, definition
    from hle_unified.records import ObjectVersion, Role, Attribute
    from hle_unified.institutions import InstitutionEngine
    from hle_unified.institution_audit import audit
    from hle_unified import codec
    e, _ = setup12()
    form = ref('inactive-definition')
    e.declare('inactive-definition', (definition(form, 'Inactive benchmark record definition'),))
    print('native setup complete', flush=True)
    for i in range(args.history):
        links = () if args.kind != 'dense' else tuple(
            Attribute('link.' + str(j), ref('inactive-' + str(j)))
            for j in range(max(0, i - 8), i))
        v = ObjectVersion(ref('inactive-' + str(i)), WRITER,
            ('unique history ' + str(i)) if args.kind == 'unique' else 'inactive shared structure',
            (Role.RECORD,), definition=form, attributes=(Attribute('number', i if args.kind == 'unique' else 7), *links))
        e.declare('inactive-' + str(i), (v,))
    before = len(e.world._journal)
    samples = []
    visits = [0]
    original_resolve = e.world.resolve
    def resolve(ref):
        visits[0] += 1
        return original_resolve(ref)
    e.world.resolve = resolve
    # Audit is offline in this runtime; no assessor work is mixed into active time.
    for batch in range(protocol['native']['warmup_runs'] + protocol['native']['measured_runs']):
        prior_visits = visits[0]
        start = time.perf_counter()
        for i in range(protocol['native']['active_work_items']):
            actor = ALICE if i % 2 == 0 else BOB
            show(e, actor, ROOM, key=f'bench:{batch}:{i}')
        samples.append({'seconds': time.perf_counter() - start,
                        'warmup': batch < protocol['native']['warmup_runs'],
                        'affected_record_visits': visits[0] - prior_visits,
                        'completed': protocol['native']['active_work_items']})
    e.world.resolve = original_resolve
    print('native active samples complete', flush=True)
    cp = e.checkpoint()
    serialization = timed(e.checkpoint)
    compressed = gzip.compress(cp.encode(), compresslevel=9, mtime=0)
    (args.out.parent/'final.checkpoint.json.gz').write_bytes(compressed)
    compression = timed(lambda: gzip.compress(cp.encode(), compresslevel=9, mtime=0))
    restore_samples = timed(lambda: InstitutionEngine.restore(cp), protocol['native']['timed_checkpoint_repetitions'])
    print('native timed restores complete', flush=True)
    t = time.perf_counter(); journal = e.world.journal(); report = audit(journal); evaluator = time.perf_counter() - t
    protected = {'checkpoint': digest(cp), 'transactions': digest(codec.dumps(journal)),
                 'views': [digest(e.participant_view(a).bytes()) for a in (ALICE, BOB)],
                 'wallets': [e.wallet(a) for a in (ALICE, BOB)],
                 'transactions_count': len(journal), 'new_transactions': len(journal) - before,
                 'queues': {'locks': len(e._locks), 'unfinished': sum(
                     e.job_status(a, k)['status'] in ('pending', 'partial') for a, k in e._jobs)}}
    # Wallet dictionaries contain typed references: canonical bytes are authority.
    protected['wallets'] = digest(codec.dumps(tuple(tuple(sorted(w.items())) for w in protected['wallets'])))
    restored = InstitutionEngine.restore(cp)
    exact = restored.checkpoint() == cp
    assessment_passed = report['passed']
    del restored, journal, report
    memory = None
    if args.history == 1000:
        del e, original_resolve, resolve; gc.collect()
        tracemalloc.start()
        measured = InstitutionEngine.restore(cp)
        gc.collect()
        live, peak = tracemalloc.get_traced_memory(); tracemalloc.stop()
        memory = {'live_bytes': live, 'peak_bytes': peak}
        print('native traced restore complete', flush=True)
        del measured
    return {'samples': samples, 'median_participant_seconds': statistics.median(x['seconds'] for x in samples if not x['warmup']),
            'median_affected_record_visits': statistics.median(x['affected_record_visits'] for x in samples if not x['warmup']),
            'checkpoint_bytes': len(cp.encode()), 'gzip_bytes': len(compressed),
            'serialization_seconds': serialization, 'compression_seconds': compression,
            'restore_samples': restore_samples, 'restore_seconds': statistics.median(restore_samples),
            'evaluator_seconds': evaluator, 'online_assessment_seconds': 0,
            'memory': memory, 'exact_restore': exact, 'assessment_passed': assessment_passed, 'protected': protected}


def common(args, protocol):
    from hle.closure import ClosureWorld
    import r21_performance as perf
    from r21_reference import resource_audit
    from hle.codec import dumps
    protected = {}
    def capture(w, **kw):
        checkpoint_text = w.checkpoint()
        (args.out.parent/'final.checkpoint.json.gz').write_bytes(gzip.compress(checkpoint_text.encode(), compresslevel=9, mtime=0))
        protected.update(checkpoint=digest(checkpoint_text),
            wallets=digest(dumps(tuple(w._wallets.items()))),
            transactions=len(w._journal), queues=perf.queue_snapshot(w))
        return resource_audit(w, **kw)
    perf.resource_audit = capture
    with gzip.open(BASE/'evidence/r20/panel/continued_r19.checkpoint.json.gz', 'rt') as f:
        w = ClosureWorld.restore(f.read())
    result = perf.measure(w, args.kind, args.history, args.out.parent,
        {k: protocol['common'][k] for k in ('active_work_items', 'warmup_runs', 'measured_runs')})
    result['protected'] = protected
    return result


def checkpoint(args, protocol):
    from hle.closure import ClosureWorld
    from hle.world_records import Tick
    from r21b_work_audit import audit_paid_work
    from hle.codec import dumps
    path = BASE/'evidence/r21b/development'/(args.kind + '.checkpoint.json.gz')
    with gzip.open(path, 'rt') as f:
        cp = f.read()
    # Same warm import/cache exercise on both sides, excluded from all measurements.
    w = ClosureWorld.restore(cp)
    print('legacy checkpoint warm restore complete', flush=True)
    encoded = w.checkpoint()
    serialization = timed(w.checkpoint)
    compressed = gzip.compress(encoded.encode(), compresslevel=9, mtime=0)
    compression = timed(lambda: gzip.compress(encoded.encode(), compresslevel=9, mtime=0))
    report = audit_paid_work(w)
    w.execute(Tick('u13:checkpoint-continuation:' + args.kind))
    continuation = w.checkpoint()
    continued = digest(continuation)
    (args.out.parent/'continuation.checkpoint.json.gz').write_bytes(gzip.compress(continuation.encode(), compresslevel=9, mtime=0))
    del continuation
    wallets = digest(dumps(tuple(w._wallets.items())))
    del w; gc.collect()
    samples = timed(lambda: ClosureWorld.restore(cp), protocol['common']['timed_checkpoint_repetitions'])
    print('legacy checkpoint timed restores complete', flush=True)
    gc.collect(); tracemalloc.start()
    w = ClosureWorld.restore(cp)
    gc.collect()
    live, peak = tracemalloc.get_traced_memory(); tracemalloc.stop()
    print('legacy checkpoint traced restore complete', flush=True)
    return {'restore_samples': samples, 'restore_seconds': statistics.median(samples),
        'serialization_seconds': serialization, 'compression_seconds': compression,
        'live_bytes': live, 'peak_bytes': peak, 'gzip_bytes': len(compressed),
        'raw_bytes': len(cp.encode()), 'exact_roundtrip': encoded == cp, 'audit': report,
        'protected': {'checkpoint': digest(cp), 'continuation': continued, 'wallets': wallets}}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--suite', choices=('native', 'common', 'checkpoint'), required=True)
    p.add_argument('--mode', choices=('reference', 'candidate'), required=True)
    p.add_argument('--kind', required=True); p.add_argument('--history', type=int, default=0)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args(); args.out.parent.mkdir(parents=True, exist_ok=True)
    refroot = ROOT/'reference_u12' if args.mode == 'reference' else ROOT
    sys.path[:0] = [str(refroot), str(BASE), str(BASE/'tools')]
    if args.mode == 'candidate':
        from hle_unified.efficiency import install_legacy_optimizations
        install_legacy_optimizations()
    protocol = json.loads((ROOT/'contracts/U13_Protocol_v1.json').read_text())
    result = globals()[args.suite](args, protocol)
    result.update(suite=args.suite, mode=args.mode, kind=args.kind, history=args.history,
                  python=sys.version, platform=platform.platform(),
                  process_max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    args.out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'suite': args.suite, 'mode': args.mode, 'kind': args.kind,
                      'history': args.history, 'out': str(args.out)}), flush=True)


if __name__ == '__main__':
    main()
