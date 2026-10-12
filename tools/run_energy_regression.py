"""Exact accepted method inventory, isolated packages, unchanged full source."""
import concurrent.futures,hashlib,json,pathlib,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]

def manifest():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(ROOT.rglob('*')) if p.is_file() and '.git' not in p.parts
            and '__pycache__' not in p.parts and 'evidence' not in p.parts
            and (p.suffix=='.py' or p.relative_to(ROOT).parts[0]=='contracts')}

def main(out):
    out.mkdir(parents=True,exist_ok=False)
    freeze=manifest();(out/'source_freeze.json').write_text(json.dumps(freeze,indent=2)+'\n')
    accepted=json.loads((ROOT/'evidence/Corrective5/attempt1/Accepted_Method_Inventory.json').read_text())['method_ids']
    packages=sorted({s.split('.')[0] for s in accepted}|{'tests_energy'})
    def run(package):
        t=time.monotonic()
        with (out/(package+'.stdout.log')).open('w') as log:
            code=subprocess.run([sys.executable,'tools/test_c6.py',str(out/package),package],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT).returncode
        summary=out/package/'summary.json'
        return dict(package=package,exit_code=code,seconds=time.monotonic()-t,summary=json.loads(summary.read_text()) if summary.exists() else None)
    rows=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for future in concurrent.futures.as_completed([pool.submit(run,p) for p in packages]):
            r=future.result();rows.append(r)
            (out/'progress.json').write_text(json.dumps(rows,indent=2)+'\n')
            print(r['package'],r['exit_code'],round(r['seconds'],1),flush=True)
    outcomes=[row for r in rows if r['summary'] for row in r['summary']['rows']]
    ids={x['test_id'] for x in outcomes};passed={x['test_id'] for x in outcomes if x['status']=='passed'}
    result=dict(passed=all(r['exit_code']==0 for r in rows) and set(accepted)<=passed and manifest()==freeze,
                accepted_required=len(accepted),missing=sorted(set(accepted)-ids),failed=sorted(ids-passed),distinct_methods=len(ids),
                source_unchanged=manifest()==freeze,method_ids=sorted(ids),packages=[{k:v for k,v in r.items() if k!='summary'} for r in rows])
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ('method_ids','packages')}),flush=True)
    return result
if __name__=='__main__':sys.exit(not main(pathlib.Path(sys.argv[1]).resolve())['passed'])
