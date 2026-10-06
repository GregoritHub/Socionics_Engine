"""Run only the four additional post-review C2 controls."""
import argparse,hashlib,json,sys,time,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
sys.dont_write_bytecode=True
from evaluate_u2 import EvidenceResult
from tests_c2.test_review import ReviewTests

p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
paths=sorted({*ROOT.glob('hle_unified/*.py'),*ROOT.glob('tests_c2/*.py'),Path(__file__)})
source={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in paths}
(a.out/'execution_source.json').write_text(json.dumps(source,indent=2)+'\n')
start=time.perf_counter()
with (a.out/'tests.log').open('w') as log:
 result=unittest.TextTestRunner(stream=log,verbosity=2,resultclass=EvidenceResult).run(unittest.defaultTestLoader.loadTestsFromTestCase(ReviewTests))
unchanged=all(hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==h for f,h in source.items())
summary=dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),rows=result.rows,seconds=time.perf_counter()-start,source_unchanged=unchanged,passed=result.wasSuccessful() and unchanged and not result.skipped)
(a.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items() if k!='rows'}))
raise SystemExit(0 if summary['passed'] else 1)
