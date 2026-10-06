"""Run all inherited tests and the R17 behavioral/integrity regression suite."""
import argparse,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'evidence/r17/validation');a=p.parse_args()
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    inherited=subprocess.run([sys.executable,'tools/r16_validate.py','--out',str(out/'inherited')],cwd=ROOT)
    new=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests_r17','-t','.','-v'],cwd=ROOT,capture_output=True,text=True)
    log=new.stdout+new.stderr;(out/'r17.log').write_text(log);m=re.search(r'Ran (\d+) tests',log);count=int(m.group(1)) if m else 0
    prior=json.loads((out/'inherited/summary.json').read_text())
    result={'schema':'r17-validation-v1','inherited':prior['total'],'r17':count,'total':prior['total']+count,
        'passed':inherited.returncode==0 and prior['passed'] and prior['total']==718 and new.returncode==0 and count==33 and log.rstrip().endswith('OK')}
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
    return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
