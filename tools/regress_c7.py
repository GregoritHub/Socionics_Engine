"""Full isolated package regression, retaining each failure and timeout."""
import sys,subprocess,json,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=False);rows=[]
for package in [f'tests_u{i}' for i in range(2,15)]+[f'tests_c{i}' for i in range(1,8)]:
    start=time.perf_counter();error=None
    try:
        with (out/(package+'.stdout.log')).open('w') as f:
            p=subprocess.run([sys.executable,str(ROOT/'tools/test_c6.py'),str(out/package),package],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=600)
        code=p.returncode
    except subprocess.TimeoutExpired:code=None;error='600 second package timeout'
    path=out/package/'summary.json';summary=json.loads(path.read_text()) if path.exists() else None
    rows.append(dict(package=package,exit_code=code,error=error,summary=summary,seconds=time.perf_counter()-start))
    (out/'summary.json').write_text(json.dumps(dict(passed=all(x['exit_code']==0 and x['summary'] and x['summary']['passed'] for x in rows),packages=rows),indent=2))
    print(package,code,error,round(time.perf_counter()-start,2),flush=True)
