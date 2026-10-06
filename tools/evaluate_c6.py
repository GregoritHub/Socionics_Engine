"""Declared C6 automatic/type panel and matched choice-withholding controls."""
import sys,json,gzip,time,hashlib,traceback
from pathlib import Path
from dataclasses import asdict,is_dataclass,replace
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
from tests_c6.fixtures import *
from hle_unified.selection_audit import audit,extent
from hle_unified.crux_shell_audit import audit as native_audit
from hle.model_a import TYPES

def dump(v):return json.dumps(v,default=lambda x:asdict(x) if is_dataclass(x) else str(x),indent=2)
def save(e,path):
    cp=e.checkpoint();path.write_bytes(gzip.compress(cp.encode(),mtime=0));return dict(file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
def manifest(out):
    out.mkdir(parents=True,exist_ok=False)
    m={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for pat in ('hle_unified/*.py','tests_c6/*.py','contracts/C6*','tools/evaluate_c6.py') for p in ROOT.glob(pat)}
    (out/'source.json').write_text(dump(m));return m
class WithheldChoice(SelectionEngine):
    """Evaluator intervention after paid comparison: retain candidates, withhold winner."""
    def _select_policy(self,s):
        rows,winner=super()._select_policy(s);return rows,None

def panel(out,types=False):
    m=manifest(out);rows=[]
    for tim in (TYPES if types else ('iee',)):
        for name in NAMES:
            for face in FACES:
                key=tim+'-'+name+'-'+face;start=time.perf_counter()
                try:
                    e,r=fixture(name,face,tim)
                    if not types:
                        control=WithheldChoice.restore(e.checkpoint());control,cd=finish_selection(control,r)
                        csave=save(control,out/(key+'-control.json.gz'))
                        ca=native_audit(control.world.journal(),control.access.checkpoint(),extent_check=extent,extended_flags=('c6',));assert ca['passed']
                        try:audit(control.world.journal(),control.access.checkpoint())
                        except ValueError as exc:expected_rejection=str(exc)
                        else:raise AssertionError('ablation must fail the ordinary choice contract')
                        assert cd['selected'] is None and (ALICE,r.key+':movement') not in control._jobs
                    e,d=finish_selection(e,r)
                    assert d['recipe']==name.lower()+'-'+face+'-v1',(tim,name,face,d)
                    assert d['failure'] is None
                    child=e.job_status(ALICE,r.key+':movement');assert child['status']=='succeeded',child
                    native=e._movement_inputs[e._jobs[ALICE,r.key+':movement'].identity][0]
                    later=downstream(e,native,name,face) if not types else None
                    raw=save(e,out/(key+'.json.gz'));a=audit(e.world.journal(),e.access.checkpoint());assert a['passed']
                    row=dict(tim=tim,name=name,face=face,decision=d,child=child['result'],child_work=child['spent'],later=later,raw=raw,seconds=time.perf_counter()-start)
                    if not types:
                        assert cd['spent']==d['spent']
                        row['control']=dict(raw=csave,spent=cd['spent'],native_child=False,expected_choice_audit_rejection=expected_rejection,native_accounting_passed=True)
                    rows.append(row);(out/(key+'.json')).write_text(dump(row))
                    print('PASS',key,round(row['seconds'],2),flush=True)
                except Exception:
                    (out/(key+'-failure.txt')).write_text(traceback.format_exc());raise
    unchanged=all(hashlib.sha256((ROOT/k).read_bytes()).hexdigest()==v for k,v in m.items())
    result=dict(passed=unchanged,cases=len(rows),source_unchanged=unchanged,types=types,rows=rows)
    (out/'summary.json').write_text(dump(result));assert unchanged

def transfer(out):
    m=manifest(out);rows=[]
    for cap,obs in ((1,True),(4,True),(1,False)):
        e,r,d,value,later,source,observation=transfer_witness(cap,obs)
        assert audit(e.world.journal(),e.access.checkpoint())['passed']
        key='local-'+str(cap)+('-observed' if obs else '-unobserved');raw=save(e,out/(key+'.json.gz'))
        rows.append(dict(case=key,raw=raw,decision=d,output=value,later=later,source=source,observation=observation))
    for received in (False,True):
        e,r=fixture('Understand','expenditure')
        if received:inspect(e,'new-experience')
        e,d=finish_selection(e,r);name=d['recipe'].split('-')[0].title();native=e._movement_inputs[e._jobs[ALICE,r.key+':movement'].identity][0]
        later=downstream(e,native,name,'expenditure');assert audit(e.world.journal(),e.access.checkpoint())['passed']
        key='history-'+('new-observation' if received else 'retained-model');rows.append(dict(case=key,raw=save(e,out/(key+'.json.gz')),decision=d,later=later))
    e=setup(generate=False,engine_type=SelectionEngine);dev.supply8(e,'neutral')
    for obj in (SAW,KIT,STOCK):expose(e,ALICE,obj)
    demand=need(e,'repair-need',weights=(0,10,0,0),scope='condition')
    r=SelectionRequest('untrained',ALICE,ROOM,CUE5,SAW,demand,tool=KIT,repair_stock=STOCK,procedure=REPAIR,peer=BOB)
    e,d=finish_selection(e,r);assert d['selected'] is None;assert audit(e.world.journal(),e.access.checkpoint())['passed']
    rows.append(dict(case='before-practice',raw=save(e,out/'before-practice.json.gz'),decision=d))
    training(e);r=replace(r,key='trained');e,d=finish_selection(e,r)
    assert d['recipe']=='act-accumulation-v1';native=e._movement_inputs[e._jobs[ALICE,r.key+':movement'].identity][0]
    later=downstream(e,native,'Act','accumulation');assert audit(e.world.journal(),e.access.checkpoint())['passed']
    rows.append(dict(case='acquired-held-out-repair',raw=save(e,out/'acquired-held-out-repair.json.gz'),decision=d,later=later))
    unchanged=all(hashlib.sha256((ROOT/k).read_bytes()).hexdigest()==v for k,v in m.items())
    (out/'summary.json').write_text(dump(dict(passed=unchanged,worlds=len(rows),source_unchanged=unchanged,rows=rows)));assert unchanged
    print('PASS transfer/history/capacity',len(rows),flush=True)
if __name__=='__main__':
    lane=sys.argv[1];out=Path(sys.argv[2]);transfer(out) if lane=='transfer' else panel(out,lane=='types')
