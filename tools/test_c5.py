import sys,json,hashlib,unittest,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
from evaluate_u2 import EvidenceResult,flatten
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=False)
manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for pat in ('hle_unified/*.py','tests_c5/*.py','tests_u7/*.py','tests_u8/*.py','tests_c4/*.py') for p in ROOT.glob(pat)}
(out/'source.json').write_text(json.dumps(manifest,indent=2));tests=[]
for package in (('tests_c5',) if '--c5-only' in sys.argv else ('tests_c5','tests_u7','tests_u8','tests_c4')):
 tests+=flatten(unittest.defaultTestLoader.discover(str(ROOT/package),top_level_dir=str(ROOT)))
start=time.perf_counter()
with (out/'tests.log').open('w') as f:r=unittest.TextTestRunner(stream=f,verbosity=2,resultclass=EvidenceResult).run(unittest.TestSuite(tests))
unchanged=all(hashlib.sha256((ROOT/k).read_bytes()).hexdigest()==v for k,v in manifest.items())
result=dict(passed=r.wasSuccessful() and unchanged,tests=r.testsRun,failures=len(r.failures),errors=len(r.errors),seconds=time.perf_counter()-start,source_unchanged=unchanged,rows=r.rows)
(out/'summary.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='rows'}));sys.exit(not result['passed'])
