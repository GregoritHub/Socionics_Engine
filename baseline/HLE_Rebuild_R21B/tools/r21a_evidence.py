"""Development evidence for the contract amendment, not a release-panel rerun."""
import argparse
import gc
import gzip
import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from r21a_policy import run_reference_policy, protocol
from r21a_audit import audit_episode, evaluate_feasibility
from r21_evidence import save
from hle.codec import dumps
from r21_workloads import run_episode
from r21_reference import audit as v1_audit


def trace(path, w):
    """Close, verify the compressed stream, then atomically publish it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name+'.', suffix='.tmp', dir=path.parent)
    os.close(descriptor);temporary = Path(temporary)
    digest = hashlib.sha256();size = 0
    try:
        with gzip.open(temporary, 'wt', compresslevel=6) as stream:
            for tx in w._journal:
                line = dumps(tx)+'\n';stream.write(line);digest.update(line.encode());size += len(line.encode())
        actual = hashlib.sha256();length = 0
        with gzip.open(temporary, 'rb') as stream:
            for block in iter(lambda: stream.read(1024*1024), b''):
                actual.update(block);length += len(block)
        if actual.hexdigest()!=digest.hexdigest() or length!=size:
            raise ValueError('compressed trace failed exact readback')
        os.replace(temporary, path)
    finally:
        if temporary.exists():temporary.unlink()
    return {'path': path.name, 'sha256': digest.hexdigest(), 'uncompressed_bytes': size,
            'compressed_bytes': path.stat().st_size, 'transactions': len(w._journal),
            'gzip_readback_verified': True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=ROOT/'evidence/r21a/development')
    args = parser.parse_args();out = args.out;out.mkdir(parents=True, exist_ok=True)
    spec = json.loads((ROOT/'docs/r21a/Development_Panel_v1.json').read_text())
    assert not set(spec['seeds']) & set(protocol()['evaluation']['evaluation_seeds'])
    results = []
    for tim in spec['types']:
        for seed in spec['seeds']:
            for regime in spec['regimes']:
                start = time.perf_counter()
                name = f'{tim}_{seed}_{regime}'
                w, meta = run_reference_policy(tim, seed, regime)
                checked = audit_episode(w, meta)
                gate, independent, other, independent_audit = evaluate_feasibility(w, meta)
                artifacts = {'episode': trace(out/(name+'.transactions.jsonl.gz'), w),
                             'independent': trace(out/(name+'.independent.transactions.jsonl.gz'), independent)}
                save(out/(name+'.json'), {'meta': meta, 'assessment': checked, 'feasibility': gate,
                     'independent_meta': other, 'independent_assessment': independent_audit, 'traces': artifacts})
                rows = checked['raw_clearance']['reference']['rows']
                summary = {'name': name, 'tim': tim, 'seed': seed, 'regime': regime,
                    'history': meta['scope']['history'], 'clearance_rows': len(rows),
                    'passed_clearance_rows': sum(r['passed'] for r in rows),
                    'status': checked['raw_clearance']['reference']['status'],
                    'increased_rows': sum(r['case'].endswith('increased_requirement') for r in rows),
                    'greater_with_less_headroom': sum(r['case'].endswith('increased_requirement')
                        and r['comparison']=='greater' and r.get('resource_relation')=='less_headroom' for r in rows),
                    'completed_opportunities': len(meta['opportunities']), 'resource_stop': meta['resource_stop'],
                    'error': meta.get('error'), 'integrity_passed': checked['integrity_passed'],
                    'independent_integrity_passed': independent_audit['integrity_passed'],
                    'same_scope': gate['same_scope'], 'full_horizon_feasibility': gate['passed'],
                    'unfinished_jobs': checked['resources']['unfinished_count'],
                    'work': checked['resources']['charged'], 'seconds': time.perf_counter()-start}
                if (tim, seed, regime) in (('iee', 12, 'adequate'), ('sli', 11, 'constrained_feasible')):
                    with gzip.open(out/(name+'.checkpoint.json.gz'), 'wt') as f:f.write(w.checkpoint())
                results.append(summary);print(json.dumps(summary), flush=True)
                save(out/'progress.json', {'rows': results})
                del w, independent;gc.collect()
    # Re-execute one same-scenario v1 control; do not rewrite any R21 result.
    w, meta = run_episode('iee', 12, 100000)
    control = v1_audit(w, meta)
    save(out/'v1_same_scenario.json', {'meta': meta, 'assessment': control,
         'trace': trace(out/'v1_same_scenario.transactions.jsonl.gz', w)})
    increases = [r for r in control['raw_clearance']['reference']['rows'] if r['case'].endswith('increased_requirement')]
    summary = {'schema': 'r21a-development-evidence-v1', 'release_evaluation': False,
        'reserved_release_seeds_used': [], 'episodes': len(results), 'independent_executions': len(results),
        'rows': results, 'v1_control_preserves_three_incomparable_increases': len(increases)==3
            and all(r['comparison']=='incomparable' and not r['passed'] for r in increases),
        'full_horizon_feasibility_established': False}
    summary['contract_checks_passed'] = (len(results)==18 and summary['v1_control_preserves_three_incomparable_increases']
        and all(r['integrity_passed'] and r['independent_integrity_passed'] and r['same_scope']
                and r['error'] is None and r['increased_rows']==r['greater_with_less_headroom'] for r in results))
    summary['full_horizon_feasibility_established'] = all(r['full_horizon_feasibility'] for r in results if r['regime']!='inadequate')
    save(out/'summary.json', summary)
    print(json.dumps({k:v for k,v in summary.items() if k!='rows'}), flush=True)
    return 0 if summary['contract_checks_passed'] else 1


if __name__ == '__main__':raise SystemExit(main())
