"""FB2.2 cumulative automatic panel; raw evidence preserved per case."""
import sys,json,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
from tests_workflow_selection.crossing_fixtures import *
from tools.evaluate_workflow_selection import manifest,save
from tools.verify_workflow_selection import audit,extent
from hle_unified.workflow_audit import audit as native_audit

def main(out):
    out.mkdir(parents=True,exist_ok=False);freeze=manifest();(out/'source_freeze.json').write_text(json.dumps(freeze,indent=2)+'\n');rows=[]
    for name in PANEL_NAMES:
        for face in FACES:
            key=name+'-'+face;e=q=None
            try:
                e,r,b=crossing_fixture(name,face);q,s,_=crossing_fixture(name,face,WithheldCrossing)
                d=finish(e,r);c=finish(q,s)
                assert d['recipe']=='workflow-'+name.lower()+'-'+face+'-v1' and d['failure'] is None and d['child'] is not None
                assert d['spent']==c['spent'] and c['child'] is None
                later=consume(e,r,b);good=crossing_query(e,r,name);bad=crossing_query(q,s,name)
                assert good!=bad and later['consequence']['next_task'] is not None
                audit(e.world.journal(),e.access.checkpoint())
                native_audit(q.world.journal(),q.access.checkpoint(),extent_check=extent,extended_flags=('c7ws',))
                try:audit(q.world.journal(),q.access.checkpoint())
                except ValueError as exc:
                    rejection=str(exc);assert 'choice withheld' in rejection
                else:raise AssertionError('withheld choice passed')
                rows.append(dict(name=name,face=face,comparison_spent=d['spent'],child_spent=e.job_status(ALICE,'auto:movement')['spent'],
                    good=good,control_result=bad,expected_rejection=rejection,witness=save(out,key,e),control=save(out,key+'-control',q)))
                (out/'rows.json').write_text(json.dumps(rows,indent=2)+'\n');print('PASS',key,flush=True)
            except Exception:
                (out/(key+'-failure.txt')).write_text(traceback.format_exc())
                if e:save(out,key+'-failed-witness',e)
                if q:save(out,key+'-failed-control',q)
                raise
    unchanged=manifest()==freeze
    (out/'summary.json').write_text(json.dumps(dict(passed=unchanged,cases=20,controls=20,source_unchanged=unchanged),indent=2)+'\n');assert unchanged

if __name__=='__main__':main(Path(sys.argv[1]))
