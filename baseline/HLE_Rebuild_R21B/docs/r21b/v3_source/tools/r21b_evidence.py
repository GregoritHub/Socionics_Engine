"""Declared development cases, raw traces and separate constructive witnesses."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import gc
import gzip
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from r21b_policy import run_candidate, protocol
from r21b_audit import audit_episode, evaluate_feasibility
from r21a_evidence import trace


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2)+'\n')


def execute_case(task):
    spec, out, independent = task; out = Path(out)
    tim, seed, regime = (spec[k] for k in ('tim', 'seed', 'regime'))
    mode = spec.get('mode', 'reuse')
    name = f'{tim}_{seed}_{regime}'+('' if mode == 'reuse' else '.'+mode)
    start = time.perf_counter()
    w, meta = run_candidate(tim, seed, regime, mode=mode)
    checked = audit_episode(w, meta)
    artifacts = {'candidate': trace(out/(name+'.transactions.jsonl.gz'), w)}
    result = {'meta': meta, 'assessment': checked, 'traces': artifacts}
    gate = {'passed': False, 'same_scope': False}; other_audit = None
    if independent:
        gate, other, other_meta, other_audit = evaluate_feasibility(w, meta)
        artifacts['independent'] = trace(out/(name+'.independent.transactions.jsonl.gz'), other)
        result.update(feasibility=gate, independent_meta=other_meta, independent_assessment=other_audit)
        del other; gc.collect()
    if (tim, seed, regime, mode) in (('iee', 12, 'constrained_feasible', 'reuse'),
                                   ('sli', 11, 'constrained_feasible', 'reuse')):
        with gzip.open(out/(name+'.checkpoint.json.gz'), 'wt') as stream: stream.write(w.checkpoint())
    save(out/(name+'.json'), result)
    rows = checked['raw_clearance']['reference']['rows']
    row = dict(name=name, tim=tim, seed=seed, regime=regime, mode=mode,
        stage=meta['stage'], error=meta.get('error'), resource_stop=meta['resource_stop'],
        clearance_passed=sum(r['passed'] for r in rows), clearance_total=len(rows),
        opportunities=len(meta['opportunities']), candidate_success=checked['successful_full_horizon'],
        independent_executed=independent,
        independent_success=None if other_audit is None else other_audit['successful_full_horizon'],
        integrity_passed=checked['integrity_passed'],
        independent_integrity_passed=None if other_audit is None else other_audit['integrity_passed'],
        feasibility_passed=gate['passed'], same_scope=gate['same_scope'],
        unfinished=checked['resources']['unfinished_count'],
        work=checked['resources']['charged'], paid_reuse=checked['paid_work'],
        seconds=time.perf_counter()-start)
    return row


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, default=ROOT/'evidence/r21b/development')
    p.add_argument('--workers', type=int, default=2)
    p.add_argument('--adequate-diagnostics', action='store_true')
    p.add_argument('--controls', action='store_true')
    args = p.parse_args(); out = args.out.resolve(); out.mkdir(parents=True, exist_ok=True)
    declaration = json.loads((ROOT/'docs/r21b/Development_Panel_v1.json').read_text())
    cases = declaration['controls'] if args.controls else declaration['cases']
    if args.adequate_diagnostics: cases = [r for r in cases if r['seed'] == 11 and r['regime'] == 'adequate']
    assert not {r['seed'] for r in cases} & set(protocol()['evaluation']['evaluation_seeds'])
    independent = not (args.adequate_diagnostics or args.controls)
    source = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
              for folder in ('hle', 'tools') for p in sorted((ROOT/folder).glob('*.py'))}
    save(out/'run_source.json', source)
    results = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for row in pool.map(execute_case, [(r, str(out), independent) for r in cases]):
            results.append(row)
            save(out/'progress.json', {'planned': len(cases), 'rows': results})
            print(json.dumps({k:v for k,v in row.items() if k not in ('work','paid_reuse')}), flush=True)
    positive = [r for r in results if r['regime'] != 'inadequate']
    zero = [r for r in results if r['regime'] == 'inadequate']
    summary = dict(schema='r21b-development-evidence-v1', release_evaluation=False,
        planned=len(cases), executed=len(results), independent_executions=sum(r['independent_executed'] for r in results),
        positive_count=len(positive), zero_count=len(zero), held_out_seeds_used=[], rows=results)
    summary['passed'] = (independent and len(results) == len(cases)
        and all(r['integrity_passed'] and r['independent_integrity_passed'] and r['same_scope'] and not r['error'] for r in results)
        and all(r['feasibility_passed'] and r['clearance_passed'] == 13 and r['opportunities'] == 100 and r['unfinished'] == 0 for r in positive)
        and all(not r['candidate_success'] and not r['independent_success'] and r['opportunities'] == 0 for r in zero))
    save(out/'summary.json', summary)
    print(json.dumps({k:v for k,v in summary.items() if k != 'rows'}), flush=True)
    return 0 if summary['passed'] or not independent else 1


if __name__ == '__main__': raise SystemExit(main())
