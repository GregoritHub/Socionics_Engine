"""Run the unchanged inherited verification chain, then R19 controls."""
import argparse,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'evidence/r19/validation');p.add_argument('--inherited-only',action='store_true');a=p.parse_args()
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    prior=subprocess.run([sys.executable,'tools/r18_validate.py','--out',str(out/'inherited')],cwd=ROOT)
    inherited=json.loads((out/'inherited/summary.json').read_text())
    if a.inherited_only:return prior.returncode
    run=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests_r19','-t','.','-v'],cwd=ROOT,capture_output=True,text=True)
    log=run.stdout+run.stderr;(out/'r19.log').write_text(log);m=re.search(r'Ran (\d+) tests',log);count=int(m.group(1)) if m else 0
    summary={'schema':'r19-validation-v1','inherited':inherited['total'],'r19':count,'total':inherited['total']+count,
        'passed':prior.returncode==0 and inherited['passed'] and inherited['total']==788 and run.returncode==0 and count==37 and log.rstrip().endswith('OK')}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary),flush=True)
    return 0 if summary['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
