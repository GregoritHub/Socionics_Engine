"""Frozen 512-case second-setting matrix and 32 matched semantic controls."""
import sys,json,gzip,hashlib,time,traceback
from dataclasses import asdict,is_dataclass
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
from hle.model_a import TYPES
from tests_c7_workflow.fixtures import *
from hle_unified.workflow_audit import audit

def report(value):return json.dumps(value,indent=2,default=lambda v:asdict(v) if is_dataclass(v) else str(v))
def manifest():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for pattern in ('hle_unified/*.py','tests_*/*.py','tools/*c7_settings.py','contracts/C7_Second_Setting*') for p in ROOT.glob(pattern)}
def write_world(folder,key,engine):
    path=folder/(key+'.json.gz');path.write_bytes(gzip.compress(engine.checkpoint().encode(),mtime=0))
    return dict(file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size)
def run_type(out,tim):
    rows=[];controls=[];started=time.perf_counter()
    for name in PATHS:
        for face in FACES:
            key=f'{tim}-{name}-{face}'
            try:
                e=setup_workflow(tim);before=e.wallet(ALICE)['energy'];witness=cell(e,name,face)
                job=e.job_status(ALICE,'case');assert job['status']=='succeeded';checked=audit(e.world.journal(),e.access.checkpoint());assert checked['passed']
                after=witness['consequence'];assert after['next_task'] is not None
                if name=='Act':assert witness['owner_use']=='succeeded'
                row=dict(type=tim,route=name,face=face,raw=write_world(out,key,e),spent=job['spent'],
                    main_operation=e._jobs[ALICE,'case'],source_inputs=witness['inputs'],output=witness['result'],consumer=witness['downstream'],
                    after=after,owner_use=witness.get('owner_use'),total_alice_work=before-e.wallet(ALICE)['energy'],
                    independent_raw_audit=True,main_completions=checked['workflow_main_completed'],semantic_steps=checked['workflow_steps'])
                rows.append(row)
                if tim=='iee':
                    c=setup_workflow(tim,engine_type=Ablated);other=cell(c,name,face);cd=c.job_status(ALICE,'case')
                    assert cd['spent']==job['spent'];assert other['consequence']['next_task']!=after['next_task']
                    assert (other['consequence']['completed'],other['consequence']['clock'])==(after['completed'],after['clock'])
                    if name=='Act':assert other['owner_use']=='failed'
                    try:audit(c.world.journal(),c.access.checkpoint())
                    except ValueError as exc:
                        rejection=str(exc);assert 'semantic postcondition' in rejection
                    else:raise AssertionError('withheld semantic step passed ordinary validator')
                    controls.append(dict(route=name,face=face,raw=write_world(out,key+'-control',c),spent=cd['spent'],
                        after=other['consequence'],owner_use=other.get('owner_use'),expected_ordinary_audit_rejection=rejection,
                        matched_main_cost=True,fixed_downstream_question=True,changed_downstream=True))
            except Exception:
                (out/(key+'-failure.txt')).write_text(traceback.format_exc());raise
    return tim,rows,controls,time.perf_counter()-started

def main(out):
    from concurrent.futures import ProcessPoolExecutor,as_completed
    out.mkdir(parents=True,exist_ok=False);source=manifest();(out/'source.json').write_text(report(source));rows=[];controls=[]
    (out/'protocol.json').write_bytes((ROOT/'contracts/C7_Second_Setting_Protocol_v1.json').read_bytes())
    with ProcessPoolExecutor(max_workers=4) as pool:
        jobs=[pool.submit(run_type,out,tim) for tim in TYPES]
        for job in as_completed(jobs):
            tim,rr,cc,seconds=job.result();rows.extend(rr);controls.extend(cc)
            (out/'matrix.json').write_text(report(rows));(out/'controls.json').write_text(report(controls))
            print(tim,len(rows),len(controls),round(seconds,2),flush=True)
    unchanged=source==manifest();summary=dict(passed=unchanged and len(rows)==512 and len(controls)==32,source_unchanged=unchanged,
        matrix_worlds=len(rows),semantic_controls=len(controls),cells=len({(r['route'],r['face']) for r in rows}),types=len(TYPES),isolated_type_workers=4)
    (out/'summary.json').write_text(report(summary));print(report(summary),flush=True);assert summary['passed']
if __name__=='__main__':main(Path(sys.argv[1]))
