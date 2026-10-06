"""Preserve the 636-test baseline and execute the R16A assessment controls."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'evidence/r16a/validation');a=p.parse_args()
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    inherited=subprocess.run([sys.executable,'tools/r15_validate.py','--out',str(out/'inherited')],cwd=ROOT)
    new=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests_r16a','-t','.','-v'],cwd=ROOT,capture_output=True,text=True)
    log=new.stdout+new.stderr;(out/'r16a.log').write_text(log)
    match=re.search(r'Ran (\d+) tests',log);count=int(match.group(1)) if match else 0
    prior=json.loads((out/'inherited/summary.json').read_text())
    frozen=json.loads((ROOT/'docs/r16a/Protocol_R16A_v1.json').read_text())['parent_acceptance_sha256']
    preserved=hashlib.sha256((ROOT/'docs/r12/acceptance_v1.json').read_bytes()).hexdigest()==frozen
    result={'schema':'r16a-validation-v1','inherited':prior['total'],'r16a':count,'total':prior['total']+count,
            'parent_acceptance_unchanged':preserved,
            'passed':inherited.returncode==0 and prior['total']==636 and new.returncode==0 and count==50 and log.rstrip().endswith('OK') and preserved}
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
    return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
