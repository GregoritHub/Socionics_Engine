"""Reexecute every development candidate and witness on the final runtime.

The retained raw trace is an output comparator only. Scenario inputs come from
the frozen panel; no command replay enters either fresh construction.
"""
from concurrent.futures import ProcessPoolExecutor
import argparse
import gc
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from r21b_policy import run_candidate, run_reference_policy
from r21b_audit import audit_episode
from r21_workloads import trace_digest
from r21b_evidence import save


def verify_case(task):
    row, source, out = task
    name = f"{row['tim']}_{row['seed']}_{row['regime']}"
    result = {'name': name, **row}; digests = {}; scopes = []
    for label, fn in [('candidate', run_candidate), ('independent', run_reference_policy)]:
        w, meta = fn(row['tim'], row['seed'], row['regime'])
        a = audit_episode(w, meta)
        digests[label] = trace_digest(w); scopes.append(a['scope'])
        result[label] = {'integrity_passed': a['integrity_passed'],
            'successful_full_horizon': a['successful_full_horizon'],
            'raw_rows': len(a['raw_clearance']['reference']['rows']),
            'eligible': a['sustained']['eligible'], 'changes': a['sustained']['demand_changes'],
            'unfinished': a['resources']['unfinished_count'], 'error': meta.get('error'),
            'construction': meta['construction'], 'sha256': digests[label], 'events': len(w._journal)}
        del w; gc.collect()
    # A concurrently generated initial trace may still be finishing its write.
    deadline = time.monotonic()+1800
    while True:
        try: initial = json.loads((Path(source)/(name+'.json')).read_text()); break
        except (FileNotFoundError, json.JSONDecodeError):
            if time.monotonic() >= deadline: raise RuntimeError('retained trace comparator unavailable')
            time.sleep(1)
    result['same_scope'] = scopes[0] == scopes[1]
    result['matches_retained_raw_traces'] = all(digests[k] == initial['traces'][k]['sha256'] for k in digests)
    positive = row['regime'] != 'inadequate'
    result['passed'] = (result['same_scope'] and result['matches_retained_raw_traces']
        and all(result[k]['integrity_passed'] and not result[k]['error']
                and result[k]['successful_full_horizon'] == positive for k in digests))
    save(Path(out)/(name+'.json'), result)
    return result


def main():
    p = argparse.ArgumentParser(); p.add_argument('--workers', type=int, default=2)
    p.add_argument('--source', type=Path, default=ROOT/'evidence/r21b/development')
    p.add_argument('--out', type=Path, default=ROOT/'evidence/r21b/final_source')
    args = p.parse_args(); args.out.mkdir(parents=True, exist_ok=True)
    panel = json.loads((ROOT/'docs/r21b/Development_Panel_v2.json').read_text())
    source = {str(f.relative_to(ROOT)): hashlib.sha256(f.read_bytes()).hexdigest()
              for folder in ('hle', 'tools') for f in sorted((ROOT/folder).glob('*.py'))}
    save(args.out/'source.json', source)
    results = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(verify_case, [(r, str(args.source), str(args.out)) for r in panel['cases']]):
            results.append(result)
            save(args.out/'progress.json', {'planned': len(panel['cases']), 'rows': results})
            print(json.dumps({'name': result['name'], 'passed': result['passed'],
                              'candidate_success': result['candidate']['successful_full_horizon'],
                              'independent_success': result['independent']['successful_full_horizon']}), flush=True)
    unchanged = all((ROOT/f).is_file() and hashlib.sha256((ROOT/f).read_bytes()).hexdigest() == digest
                    for f, digest in source.items())
    summary = {'schema': 'r21b-final-source-reexecution-v1', 'planned': len(panel['cases']),
        'executed': len(results), 'separate_constructions': 2*len(results), 'source_unchanged': unchanged,
        'passed': unchanged and len(results) == len(panel['cases']) and all(r['passed'] for r in results),
        'held_out_seeds_used': [], 'rows': results}
    save(args.out/'summary.json', summary)
    print(json.dumps({k:v for k,v in summary.items() if k != 'rows'}), flush=True)
    return 0 if summary['passed'] else 1


if __name__ == '__main__': raise SystemExit(main())
