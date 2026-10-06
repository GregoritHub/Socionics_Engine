"""Separate-process continuation of inherited suite after a stalled combined run."""
import sys,subprocess,json,time,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=False)
rows=[]
for package in ('tests_u4','tests_u5','tests_u6','tests_u7','tests_u8','tests_c1','tests_c2','tests_c3','tests_c4','tests_c5'):
    start=time.perf_counter()
    with (out/(package+'.stdout.log')).open('w') as f:
        p=subprocess.run([sys.executable,str(ROOT/'tools/test_c6.py'),str(out/package),package],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=600)
    result=json.loads((out/package/'summary.json').read_text());assert p.returncode==0 and result['passed'],package
    rows.extend(result['rows']);print('PASS',package,result['tests'],round(time.perf_counter()-start,2),flush=True)
(out/'summary.json').write_text(json.dumps(dict(passed=True,tests=len(rows),rows=rows),indent=2))
