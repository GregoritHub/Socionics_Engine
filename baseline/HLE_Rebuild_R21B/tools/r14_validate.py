"""Execute inherited preservation tests and every current R14 integration test."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=ROOT/'evidence/r14/validation');args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=True);(out/'summary.json').unlink(missing_ok=True)
    jobs=[
        ('r11_regression',ROOT,['-m','unittest','discover','-s','tests','-t','.','-v'],353),
        ('r12_contracts',ROOT,['-m','unittest','discover','-s','tests_r12','-t','.','-v'],34),
        ('r13_integration',ROOT,['-m','unittest','discover','-s','tests_r13','-t','.','-v'],61),
        ('r14_autonomy',ROOT,['-m','unittest','discover','-s','tests_r14','-t','.','-v'],53),
        ('pinned_crossing_source',ROOT/'baseline/crossing',['verify_sources.py'],None),
        ('crossing_and_studies',ROOT/'baseline/crossing',['-m','unittest','discover','-s','tests','-v'],26),
        ('recurrence_fidelity',ROOT/'recovered_probes/recurrence',['-m','unittest','probe.test_recurrence','-v'],14),
        ('developmental_fidelity',ROOT/'recovered_probes/developmental',['-m','unittest','devprobe.test_engine','-v'],14),
        ('meaning_fidelity',ROOT/'recovered_probes/meaning',['-m','unittest','meaningprobe.test_engine','-v'],18),
        ('oig_reference',ROOT,['tools/r12_oig_reference.py'],None),
        ('frozen_parent_specification',ROOT,['tools/r12_specification.py'],None),
    ]
    rows=[]
    for name,cwd,command,count in jobs:
        start=time.perf_counter();error=None
        try:
            child=subprocess.run([sys.executable]+command,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,
                env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},timeout=900)
            text=child.stdout;code=child.returncode
        except subprocess.TimeoutExpired as exc:
            text=exc.stdout or ''
            if isinstance(text,bytes):text=text.decode(errors='replace')
            text+='\nVALIDATION TIMEOUT; not a pass.\n';code=124;error='timeout'
        p=out/(name+'.log');tmp=p.with_suffix('.tmp');tmp.write_text(text);tmp.replace(p)
        match=re.search(r'Ran (\d+) tests?',text);observed=int(match.group(1)) if match else None
        complete=count is None or observed==count and text.rstrip().endswith('OK')
        row={'name':name,'cwd':str(cwd.relative_to(ROOT)),'command':['python']+command,'exit_code':code,
            'tests':observed,'expected_tests':count,'log_complete':complete,'seconds':round(time.perf_counter()-start,6),
            'error':error,'log_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
        rows.append(row);print(json.dumps(row),flush=True)
        (out/'running.json').write_text(json.dumps({'jobs':rows,'done':False},indent=2)+'\n')
    parent=hashlib.sha256((ROOT/'docs/r12/acceptance_v1.json').read_bytes()).hexdigest()
    protocol=json.loads((ROOT/'docs/r14/Protocol_R14_v1.json').read_text())
    result={'schema':'hle-r14-validation-v1','python':sys.version,'jobs':rows,'distinct_tests':sum(r['tests'] or 0 for r in rows),
        'r14_tests':53,'parent_acceptance_unchanged':parent==protocol['parent_acceptance_sha256'],
        'passed':all(r['exit_code']==0 and r['log_complete'] for r in rows) and parent==protocol['parent_acceptance_sha256']}
    p=out/'summary.json';p.with_suffix('.tmp').write_text(json.dumps(result,indent=2)+'\n');p.with_suffix('.tmp').replace(p)
    print(json.dumps({'passed':result['passed'],'distinct_tests':result['distinct_tests']}),flush=True)
    return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
