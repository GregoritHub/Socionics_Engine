"""All applicable inherited tests on the exact frozen release source."""
import argparse
import unittest
from u14_support import *
from evaluate_u2 import EvidenceResult,flatten


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    p.add_argument('--stage',choices=('native','legacy'),required=True);a=p.parse_args()
    identity=verify_freeze();a.out.mkdir(parents=True,exist_ok=False)
    write_json(a.out/'execution_source.json',source_manifest())
    from hle_unified.efficiency import install_legacy_optimizations
    install_legacy_optimizations()
    loader=unittest.TestLoader();tests=[]
    directories=sorted(BASE.glob('tests*')) if a.stage=='legacy' else [ROOT/f'tests_u{i}' for i in range(2,15)]
    for directory in directories:
        if directory.is_dir():tests.extend(flatten(loader.discover(str(directory),top_level_dir=str(BASE if a.stage=='legacy' else ROOT))))
    tests=list({t.id():t for t in tests}.values());start=time.perf_counter()
    with (a.out/'tests.log').open('w') as log:
        result=unittest.TextTestRunner(stream=log,verbosity=2,resultclass=EvidenceResult).run(unittest.TestSuite(tests))
    same=verify_freeze()==identity
    summary=dict(stage=a.stage,tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),
        seconds=time.perf_counter()-start,rows=result.rows,source_identity=identity,source_unchanged=same,
        passed=result.wasSuccessful() and not result.skipped and same)
    write_json(a.out/'summary.json',summary);print(json.dumps({k:v for k,v in summary.items() if k!='rows'}),flush=True)
    return 0 if summary['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
