"""Full inherited validation and R20 causal controls on the delivered source."""
import argparse,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'evidence/r20/validation');a=p.parse_args()
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    prior=subprocess.run([sys.executable,'tools/r19_validate.py','--out',str(out/'inherited')],cwd=ROOT)
    inherited=json.loads((out/'inherited/summary.json').read_text())
    run=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests_r20','-t','.','-v'],cwd=ROOT,capture_output=True,text=True)
    log=run.stdout+run.stderr;(out/'r20.log').write_text(log);m=re.search(r'Ran (\d+) tests',log);count=int(m.group(1)) if m else 0
    result={'schema':'r20-validation-v1','inherited':inherited['total'],'r20':count,'total':inherited['total']+count,
        'passed':prior.returncode==0 and inherited['passed'] and inherited['total']==825 and run.returncode==0 and count>=30 and log.rstrip().endswith('OK')}
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
    return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
