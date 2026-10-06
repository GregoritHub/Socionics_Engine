"""Run every frozen legacy test in module-isolated interpreter processes.

This is a regression execution amendment, not a runtime or test amendment.
Both incomplete monolithic attempts remain separate release evidence.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import resource
import subprocess
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from u14_support import BASE, digest, source_manifest, verify_freeze, write_json
from evaluate_u2 import EvidenceResult, flatten


def runner_identity():
    p = ROOT / 'U14_Regression_Execution_Amendment_v1.json'
    contract = json.loads(p.read_text())
    if digest(Path(__file__).read_bytes()) != contract['runner_sha256']:
        raise ValueError('regression runner differs from prospective amendment')
    return digest(p.read_bytes()), contract


def discover():
    loader = unittest.TestLoader()
    tests = []
    for directory in sorted(BASE.glob('tests*')):
        if directory.is_dir():
            tests.extend(flatten(loader.discover(str(directory), top_level_dir=str(BASE))))
    return list({t.id(): t for t in tests}.values())


def worker(module, out, contract):
    identity = verify_freeze()
    from hle_unified.efficiency import install_legacy_optimizations
    install_legacy_optimizations()
    tests = list(flatten(unittest.TestLoader().loadTestsFromName(module)))
    expected = contract['modules'][module]
    if [t.id() for t in tests] != expected:
        raise ValueError('isolated module discovery changed')
    started = time.perf_counter()
    with (out / (module + '.tests.log')).open('w', buffering=1) as log:
        result = unittest.TextTestRunner(stream=log, verbosity=2, resultclass=EvidenceResult).run(unittest.TestSuite(tests))
    same = verify_freeze() == identity
    result_ids = [r['test_id'] for r in result.rows]
    summary = dict(module=module, tests=result.testsRun, failures=len(result.failures),
        errors=len(result.errors), skipped=len(result.skipped), rows=result.rows,
        seconds=time.perf_counter()-started, max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        source_identity=identity, source_unchanged=same,
        passed=result.wasSuccessful() and not result.skipped and same and result_ids == expected)
    write_json(out / (module + '.json'), summary)
    return 0 if summary['passed'] else 1


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--module')
    p.add_argument('--jobs', type=int, default=3, choices=range(1, 7))
    a = p.parse_args()
    runner_hash, contract = runner_identity()
    if a.module:
        return worker(a.module, a.out, contract)
    identity = verify_freeze()
    actual = [t.id() for t in discover()]
    expected = [t for names in contract['modules'].values() for t in names]
    if actual != expected or len(actual) != 840 or len(set(actual)) != 840:
        raise ValueError('full frozen legacy test population changed')
    a.out.mkdir(parents=True, exist_ok=False)
    shards = a.out / 'modules'; shards.mkdir()
    write_json(a.out / 'execution_source.json', source_manifest())
    write_json(a.out / 'execution_amendment.json', contract)
    started = time.perf_counter()

    def run(module):
        command = [sys.executable, str(Path(__file__)), '--module', module, '--out', str(shards)]
        start = time.perf_counter()
        with (shards / (module + '.process.log')).open('w') as log:
            try:
                code = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=1200).returncode
            except subprocess.TimeoutExpired:
                code = 'timeout'
        summary_path = shards / (module + '.json')
        summary = json.loads(summary_path.read_text()) if summary_path.exists() else {}
        row = dict(module=module, command=command, exit_code=code,
                   seconds=time.perf_counter()-start, tests=summary.get('tests', 0),
                   passed=code == 0 and summary.get('passed', False))
        print(json.dumps(row), flush=True)
        return row

    results = {}
    with ThreadPoolExecutor(max_workers=a.jobs) as pool:
        futures = {pool.submit(run, module): module for module in contract['modules']}
        for f in as_completed(futures):
            row = f.result(); results[row['module']] = row
            write_json(a.out / 'progress.json', list(results.values()))
    rows = []; summaries = []
    for module in contract['modules']:
        path = shards / (module + '.json')
        if path.exists():
            summary = json.loads(path.read_text()); summaries.append(summary)
            rows.extend(summary['rows'])
    same = verify_freeze() == identity and runner_identity()[0] == runner_hash
    complete = [r['test_id'] for r in rows] == expected
    summary = dict(stage='legacy', execution_mode='one fresh interpreter per test module',
        tests=sum(s['tests'] for s in summaries), failures=sum(s['failures'] for s in summaries),
        errors=sum(s['errors'] for s in summaries), skipped=sum(s['skipped'] for s in summaries),
        seconds=time.perf_counter()-started, rows=rows,
        modules=[results[m] for m in contract['modules']], source_identity=identity,
        source_unchanged=same, amendment_sha256=runner_hash, exact_test_population=complete,
        prior_attempts=['legacy_stalled_attempt', 'legacy_crashed_attempt'],
        limitation='This establishes the complete isolated regression population, not successful completion in one long-lived interpreter. The earlier stall and diagnostic interpreter crash remain unexplained.',
        passed=complete and same and all(r['passed'] for r in results.values())
               and all(s['source_identity'] == identity and s['source_unchanged'] for s in summaries))
    write_json(a.out / 'summary.json', summary)
    print(json.dumps({k:v for k,v in summary.items() if k not in ('rows','modules')}), flush=True)
    return 0 if summary['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
