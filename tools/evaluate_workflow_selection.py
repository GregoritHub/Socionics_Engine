"""FB2.1 deterministic self-route witnesses and matched withheld choices."""
import sys,json,gzip,hashlib,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
from tests_workflow_selection.fixtures import *
from tools.verify_workflow_selection import audit,extent
from hle_unified.workflow_audit import audit as native_audit

def manifest():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(ROOT.rglob('*'))
        if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts and 'evidence' not in p.parts
        and (p.suffix=='.py' or p.relative_to(ROOT).parts[0]=='contracts')}

def save(out,key,e):
    p=out/(key+'.json.gz');p.write_bytes(gzip.compress(e.checkpoint().encode(),mtime=0))
    return dict(file=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest())

def main(out):
    out.mkdir(parents=True,exist_ok=False);freeze=manifest();(out/'source_freeze.json').write_text(json.dumps(freeze,indent=2)+'\n');rows=[]
    for name in SELF_NAMES:
        for face in FACES:
            key=name+'-'+face;e=q=None
            try:
                e,r,base=fixture(name,face);q,s,_=fixture(name,face,WithheldChoice)
                d=finish(e,r);c=finish(q,s)
                assert d['recipe']=='workflow-'+name.lower()+'-'+face+'-v1' and d['failure'] is None and d['child'] is not None
                assert d['spent']==c['spent'] and c['child'] is None
                later=consume(e,r,base);good=fixed_query(e,r,name);bad=fixed_query(q,s,name)
                assert good!=bad and later['consequence']['next_task'] is not None
                assert audit(e.world.journal(),e.access.checkpoint())['workflow_selections']==1
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
    (out/'summary.json').write_text(json.dumps(dict(passed=unchanged,cases=8,controls=8,source_unchanged=unchanged),indent=2)+'\n')
    assert unchanged

if __name__=='__main__':main(Path(sys.argv[1]))
