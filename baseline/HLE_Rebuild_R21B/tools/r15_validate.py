"""Preserved 601-test baseline and the R15 behavioral/continuation gates."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'evidence/r15/validation');args=p.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    (out/'summary.json').unlink(missing_ok=True)
    baseline=subprocess.run([sys.executable,'tools/r145_validate.py',str(out/'inherited')],cwd=ROOT)
    tests=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests_r15','-t','.','-v'],cwd=ROOT,capture_output=True,text=True)
    output=tests.stdout+tests.stderr;(out/'r15.log').write_text(output)
    match=re.search(r'Ran (\d+) tests',output);count=int(match.group(1)) if match else 0
    inherited=json.loads((out/'inherited/summary.json').read_text())
    protocol=json.loads((ROOT/'docs/r15/Protocol_R15_v1.json').read_text())
    unchanged=hashlib.sha256((ROOT/'docs/r12/acceptance_v1.json').read_bytes()).hexdigest()==protocol['parent_acceptance_sha256']
    result={'schema':'r15-validation-v1','inherited_tests':inherited['total'],'r15_tests':count,
            'total':inherited['total']+count,'parent_acceptance_unchanged':unchanged,
            'passed':baseline.returncode==0 and tests.returncode==0 and count==35 and output.rstrip().endswith('OK') and unchanged}
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
    return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
