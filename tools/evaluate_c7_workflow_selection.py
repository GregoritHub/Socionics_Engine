"""FB2.4 actual automatic type matrix and separate responsiveness worlds."""
import sys,json,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
from tests_workflow_selection.final_fixtures import *
from tools.evaluate_workflow_selection import manifest,save
from hle.model_a import TYPES

def matrix(out):
    out.mkdir(parents=True,exist_ok=False);freeze=manifest();(out/'source_freeze.json').write_text(json.dumps(freeze,indent=2)+'\n');rows=[]
    for tim in ('iee',*(t for t in TYPES if t!='iee')):
        for name in ALL_NAMES:
            for face in FACES:
                key=tim+'-'+name+'-'+face;e=q=None
                try:
                    e,r,b=final_fixture(name,face,tim=tim);d=finish(e,r)
                    assert d['recipe']=='workflow-'+name.lower()+'-'+face+'-v1' and d['failure'] is None and d['child'] is not None
                    later=consume(e,r,b);good=social_query(e,r,name)
                    assert later['consequence']['next_task'] is not None
                    audit(e.world.journal(),e.access.checkpoint())
                    row=dict(tim=tim,name=name,face=face,selected=d['selected'],comparison_spent=d['spent'],
                        child_spent=e.job_status(ALICE,r.key+':movement')['spent'],good=good,witness=save(out,key,e))
                    if tim=='iee':
                        q,s,_=final_fixture(name,face,WithheldFinal,tim);c=finish(q,s);bad=social_query(q,s,name)
                        assert d['spent']==c['spent'] and c['child'] is None and good!=bad
                        native_audit(q.world.journal(),q.access.checkpoint(),extent_check=extent,extended_flags=('c7ws',))
                        try:audit(q.world.journal(),q.access.checkpoint())
                        except ValueError as exc:
                            rejection=str(exc);assert 'choice withheld' in rejection
                        else:raise AssertionError('withheld choice passed')
                        row.update(control_result=bad,expected_rejection=rejection,control=save(out,key+'-control',q))
                    rows.append(row);(out/'rows.json').write_text(json.dumps(rows,indent=2)+'\n')
                    print('PASS',key,flush=True)
                except Exception:
                    (out/(key+'-failure.txt')).write_text(traceback.format_exc())
                    if e:save(out,key+'-failed-witness',e)
                    if q:save(out,key+'-failed-control',q)
                    raise
    unchanged=manifest()==freeze
    assert len(rows)==512 and len({(x['tim'],x['selected']) for x in rows})==512
    (out/'summary.json').write_text(json.dumps(dict(passed=unchanged,cases=512,controls=32,source_unchanged=unchanged),indent=2)+'\n');assert unchanged

def responsive(out):
    out.mkdir(parents=True,exist_ok=False);freeze=manifest();(out/'source_freeze.json').write_text(json.dumps(freeze,indent=2)+'\n')
    observed={}
    try:
        worlds,pairs=responsiveness(lambda name,e,bad:observed.update({name:(e,bad)}))
        rows=[dict(name=name,expected_rejection=bad,raw=save(out,name,e)) for name,e,bad in worlds]
        unchanged=manifest()==freeze
        (out/'summary.json').write_text(json.dumps(dict(passed=unchanged,pairs=pairs,rows=rows,worlds=len(rows),
            source_unchanged=unchanged),indent=2)+'\n');assert unchanged
        print('PASS three responsiveness pairs; nine raw worlds; two unresponsive choices rejected',flush=True)
    except Exception:
        (out/'failure.txt').write_text(traceback.format_exc())
        for name,(e,_) in observed.items():
            try:save(out,name+'-failed',e)
            except Exception:(out/(name+'-checkpoint-error.txt')).write_text(traceback.format_exc())
        raise

if __name__=='__main__':
    (responsive if sys.argv[1]=='responsiveness' else matrix)(Path(sys.argv[2]))
