"""The 72 unchanged external fidelity checks in the U1 912-test panel."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'baseline/HLE_Rebuild_R21B'


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    jobs=[('pinned_crossing_source','baseline/crossing',['verify_sources.py'],0),
          ('crossing_and_studies','baseline/crossing',['-m','unittest','discover','-s','tests','-v'],26),
          ('recurrence_fidelity','recovered_probes/recurrence',['-m','unittest','probe.test_recurrence','-v'],14),
          ('developmental_fidelity','recovered_probes/developmental',['-m','unittest','devprobe.test_engine','-v'],14),
          ('meaning_fidelity','recovered_probes/meaning',['-m','unittest','meaningprobe.test_engine','-v'],18)]
    rows=[]
    for name,cwd,argv,expected in jobs:
        command=[sys.executable,*argv];start=time.perf_counter()
        run=subprocess.run(command,cwd=BASE/cwd,capture_output=True,text=True)
        log=run.stdout+run.stderr;(a.out/(name+'.log')).write_text(log)
        m=re.search(r'Ran (\d+) tests',log)
        count=int(m.group(1)) if m else 0
        row=dict(name=name,command=command,cwd=str(BASE/cwd),tests=count,
                 expected=expected,exit_code=run.returncode,seconds=time.perf_counter()-start,
                 passed=run.returncode==0 and count==expected and (expected==0 or log.rstrip().endswith('OK')))
        rows.append(row);print(json.dumps(row),flush=True)
    result={'schema':'hle-u13-inherited-fidelity-v1','rows':rows,'tests':sum(r['tests'] for r in rows),'passed':all(r['passed'] for r in rows)}
    (a.out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
