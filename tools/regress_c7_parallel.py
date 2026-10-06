"""Independent inherited packages in four isolated subprocess workers."""
import sys,subprocess,json,time,hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
ROOT=Path(__file__).resolve().parents[1]

def run(out,package):
    start=time.perf_counter();error=None
    try:
        with (out/(package+'.stdout.log')).open('w') as f:
            p=subprocess.run([sys.executable,str(ROOT/'tools/test_c6.py'),str(out/package),package],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=900)
        code=p.returncode
    except subprocess.TimeoutExpired:code=None;error='900 second package timeout'
    path=out/package/'summary.json';summary=json.loads(path.read_text()) if path.exists() else None
    return dict(package=package,exit_code=code,error=error,summary=summary,seconds=time.perf_counter()-start)

def main(out):
    out.mkdir(parents=True,exist_ok=False);rows=[]
    source={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for pattern in ('hle_unified/*.py','tests_*/*.py','tools/test_c6.py','tools/regress_c7_parallel.py') for p in ROOT.glob(pattern)}
    (out/'source.json').write_text(json.dumps(source,indent=2))
    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs=[pool.submit(run,out,package) for package in [f'tests_u{i}' for i in range(2,15)]+[f'tests_c{i}' for i in range(1,8)]]
        for job in as_completed(jobs):
            row=job.result();rows.append(row)
            print(row['package'],row['exit_code'],round(row['seconds'],2),flush=True)
            (out/'progress.json').write_text(json.dumps(rows,indent=2))
    unchanged=all(hashlib.sha256((ROOT/k).read_bytes()).hexdigest()==v for k,v in source.items())
    summary=dict(passed=unchanged and all(r['exit_code']==0 and r['summary'] and r['summary']['passed'] for r in rows),source_unchanged=unchanged,workers=4,packages=rows)
    (out/'summary.json').write_text(json.dumps(summary,indent=2));assert summary['passed']
if __name__=='__main__':main(Path(sys.argv[1]))
