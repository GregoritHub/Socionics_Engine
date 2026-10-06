"""Frozen, resumable release panels. Never discard or overwrite a case result."""
import argparse
import json
import subprocess
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from u14_support import *


def worker(panel,case,out):
    if panel=='autonomy':
        from u14_autonomy import run_case
    elif panel=='controls':
        from u14_autonomy import control_case as run_case
    elif panel=='population':
        from u14_population import run_case
    elif panel=='language':
        from u14_transfer import language_case as run_case
    elif panel=='nesting':
        from u14_transfer import nesting_case as run_case
    else:raise ValueError('unknown panel')
    return run_case(case,out)


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    p.add_argument('--panel',required=True,choices=('autonomy','controls','population','language','nesting'))
    p.add_argument('--case',type=int);p.add_argument('--resume',action='store_true');p.add_argument('--development',type=Path)
    p.add_argument('--jobs',type=int,default=1,choices=range(1,7))
    a=p.parse_args()
    protocol=json.loads((a.development or ROOT/'contracts/U14_Protocol_v1.json').read_text())
    identity='development' if a.development else verify_freeze()
    cases=protocol['panels'][a.panel]
    if not cases:raise ValueError('empty panel is unassessed, never a pass')
    if len({c['id'] for c in cases})!=len(cases):raise ValueError('duplicate case identity')
    if a.case is not None:
        case=cases[a.case];start=time.perf_counter()
        try:
            result=worker(a.panel,case,a.out)
            if not a.development:verify_freeze()
            result['seconds']=time.perf_counter()-start;result['source_identity']=identity
            write_json(a.out/'summary.json',result)
            print(json.dumps(dict(id=case['id'],passed=result['passed'],seconds=result['seconds'])),flush=True)
            return 0 if result['passed'] else 1
        except Exception as exc:
            a.out.mkdir(parents=True,exist_ok=True)
            (a.out/'exception.txt').write_text(traceback.format_exc())
            # Preserve the closest available live engine, including partial work.
            tb=exc.__traceback__;engines=[]
            while tb:
                for k in ('e','x','engine'):
                    e=tb.tb_frame.f_locals.get(k)
                    if e is not None and hasattr(e,'checkpoint'):engines.append(e)
                tb=tb.tb_next
            if engines:
                try:save_gzip(a.out/'failed.checkpoint.json.gz',engines[-1].checkpoint())
                except Exception as save_error:(a.out/'checkpoint_error.txt').write_text(repr(save_error))
            result=dict(case=case,passed=False,exception=repr(exc),seconds=time.perf_counter()-start,source_identity=identity)
            write_json(a.out/'summary.json',result);traceback.print_exc();return 1
    a.out.mkdir(parents=True,exist_ok=a.resume)
    if a.resume:
        if json.loads((a.out/'execution_source.json').read_text())!=source_manifest():raise ValueError('source changed on resume')
    else:write_json(a.out/'execution_source.json',source_manifest())
    rows=[]
    def execute(i,case):
        directory=a.out/case['id'];summary=directory/'summary.json'
        if summary.exists() and a.resume:
            result=json.loads(summary.read_text())
            if result['case']!=case or result.get('source_identity')!=identity:raise ValueError('resumed case identity differs')
            code=0 if result['passed'] else 1
        else:
            command=[sys.executable,str(ROOT/'tools/run_u14.py'),'--panel',a.panel,'--case',str(i),'--out',str(directory)]
            if a.development:command+=['--development',str(a.development.resolve())]
            with (a.out/(case['id']+'.log')).open('w') as log:
                proc=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
            code=proc.returncode
            result=json.loads(summary.read_text()) if summary.exists() else dict(passed=False,exception='worker did not produce summary')
        row=dict(id=case['id'],passed=result['passed'],exit_code=code,seconds=result.get('seconds'),
                 outcome=result.get('outcome'),successes=result.get('successes'))
        return row
    with ThreadPoolExecutor(max_workers=a.jobs) as executor:
        pending={executor.submit(execute,i,case):i for i,case in enumerate(cases)}
        completed={}
        for future in as_completed(pending):
            index=pending[future];row=future.result();completed[index]=row
            rows=[completed[i] for i in sorted(completed)]
            write_json(a.out/'progress.json',rows);print(json.dumps(row),flush=True)
    unchanged=identity=='development' or verify_freeze()==identity
    result=dict(panel=a.panel,planned=len(cases),executed=len(rows),passed=unchanged and all(r['passed'] and r['exit_code']==0 for r in rows),
                rows=rows,source_unchanged=unchanged,source_identity=identity)
    write_json(a.out/'summary.json',result);return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
