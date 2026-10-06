"""U13 tests with every outcome retained; includes all native predecessors."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'baseline/HLE_Rebuild_R21B'
sys.path[:0] = [str(ROOT), str(BASE)]
sys.dont_write_bytecode = True
from evaluate_u2 import EvidenceResult, flatten


def source_manifest():
    paths = []
    for d in ('hle_unified', 'tools', *(f'tests_u{i}' for i in range(2, 14)), 'reference_u12'):
        paths += list((ROOT/d).rglob('*.py'))
    paths += list((BASE/'hle').glob('*.py'))
    paths += [p for p in (ROOT/'contracts').glob('*') if p.is_file()]
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(paths))}


def main():
    p = argparse.ArgumentParser(); p.add_argument('--out', type=Path, required=True)
    p.add_argument('--stage', default='native', choices=('native', 'u13', 'legacy'))
    args = p.parse_args(); args.out.mkdir(parents=True, exist_ok=False)
    from hle_unified.efficiency import install_legacy_optimizations
    install_legacy_optimizations()
    before = source_manifest()
    (args.out/'execution_source.json').write_text(json.dumps(before, indent=2)+'\n')
    loader = unittest.TestLoader(); tests = []
    if args.stage == 'legacy':
        for directory in sorted(BASE.glob('tests*')):
            if directory.is_dir():
                tests += list(flatten(loader.discover(str(directory), top_level_dir=str(BASE))))
    else:
        for i in (range(2, 14) if args.stage == 'native' else (13,)):
            tests += list(flatten(loader.discover(str(ROOT/f'tests_u{i}'), top_level_dir=str(ROOT))))
    tests = list({t.id(): t for t in tests}.values())
    start = time.perf_counter()
    with (args.out/'tests.log').open('w') as log:
        result = unittest.TextTestRunner(stream=log, verbosity=2, resultclass=EvidenceResult).run(unittest.TestSuite(tests))
    summary = {'schema': 'hle-u13-tests-v1', 'stage': args.stage, 'tests': result.testsRun,
        'failures': len(result.failures), 'errors': len(result.errors), 'skipped': len(result.skipped),
        'seconds': time.perf_counter()-start, 'rows': result.rows,
        'execution_source_unchanged': before == source_manifest()}
    summary['passed'] = result.wasSuccessful() and not result.skipped and summary['execution_source_unchanged']
    (args.out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k != 'rows'}), flush=True)
    return 0 if summary['passed'] else 1


if __name__ == '__main__': raise SystemExit(main())
