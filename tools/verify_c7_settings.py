"""Verify saved raw worlds WITHOUT participant checkpoint replay or execution."""
import sys,json,gzip,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
from hle_unified.compact import unseal
from hle_unified.material import OperationStore
from hle_unified.workflow_audit import audit

def verify(folder):
    rows=[]
    for path in sorted(folder.glob('*.json.gz')):
        raw=unseal(gzip.decompress(path.read_bytes()).decode(),'hle-full-crux-c7-workflow-v1');world=OperationStore.restore(raw['world'])
        control=path.name.endswith('-control.json.gz');rejection=None
        try: result=audit(world.journal(),raw['access'])
        except ValueError as exc:
            rejection=str(exc)
            if not control or 'semantic postcondition' not in rejection:raise
        else:
            if control:raise AssertionError('control passed ordinary semantics')
            assert result['passed']
        rows.append(dict(file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),control=control,
            passed=not control,expected_rejection=rejection))
        if len(rows)%64==0:print('raw checked',len(rows),flush=True)
    assert len(rows)==544
    summary=dict(passed=True,ordinary_worlds=sum(not r['control'] for r in rows),deliberate_controls=sum(r['control'] for r in rows),
        invokes_participant_code=False,rows=rows)
    (folder/'independent_raw_verification.json').write_text(json.dumps(summary,indent=2));print('raw worlds verified',len(rows),flush=True)
if __name__=='__main__':verify(Path(sys.argv[1]))
