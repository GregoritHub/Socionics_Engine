"""Independent saved-world verifier; no evaluator or participant replay imports."""
import sys,json,gzip,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
from hle_unified.compact import unseal
from hle_unified.material import OperationStore,attrs
from hle_unified.workflow_shell_audit import audit
from hle_unified.workflow_selection_audit import audit as native_audit
from hle_unified.workflow_reference import decode
from hle_unified.workflow_audit import payload
from hle_unified.selection_records import NAMES,FACES

def verify(base):
    rows=[];by_cell={}
    for p in sorted(base.glob('*.json.gz')):
        raw=unseal(gzip.decompress(p.read_bytes()).decode(),'hle-full-crux-c7-workflow-shell-v1')
        world=OperationStore.restore(raw['world']);txs=world.journal();native_audit(txs,raw['access'])
        versions={v.ref:v for tx in txs for v in tx.versions};heads={v.ref.identity:v for tx in txs for v in tx.versions}
        admissions=[attrs(v) for v in versions.values() if v.ref.identity.namespace=='c7sh.admission'];assert len(admissions)==1
        d=admissions[0];rejection=None
        try:report=audit(txs,raw['access'])
        except ValueError as exc:
            rejection=str(exc)
            assert p.stem.endswith('-bypass.json') and 'admission disagrees with paid encounter' in rejection
        arm='bypass' if rejection else 'corrected' if report['workflow_shell_completed'] else 'deformed'
        assert p.name.endswith('-'+arm+'.json.gz')
        if arm=='deformed':
            assert report['workflow_shell_deformed']==1 and d['child'] is None
            query='unavailable';child_spent=0
        else:
            c=attrs(heads[d['child'].identity]);assert c['status']=='succeeded';child_spent=c['spent']
            consumer=[attrs(v) for v in heads.values() if attrs(v).get('key')==c['key']+'-consumer' and attrs(v).get('c7w')]
            assert len(consumer)==1 and consumer[0]['status']=='succeeded'
            query=payload(versions[consumer[0]['binding']])['next_task'];assert query is not None
            if arm=='corrected':
                releases=[attrs(v) for v in heads.values() if attrs(v).get('u8') and attrs(v).get('purpose')=='release' and attrs(v).get('status')=='succeeded']
                assert len(releases)==1 and releases[0]['spent']>0
        row=dict(file=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),recipe=d['requested_recipe'],arm=arm,
            admission_spent=d['admission_spent'],child_spent=child_spent,query=query,rejection=rejection)
        rows.append(row);cell=by_cell.setdefault(d['requested_recipe'],{});assert arm not in cell;cell[arm]=row
        (base/'independent_progress.json').write_text(json.dumps(dict(worlds=len(rows),rows=rows),indent=2)+'\n')
        print('AUDIT',p.name,flush=True)
    expected={'workflow-'+n.lower()+'-'+f+'-v1' for n in NAMES for f in FACES}
    assert set(by_cell)==expected and len(rows)==96
    for cell in by_cell.values():
        assert set(cell)=={'deformed','corrected','bypass'}
        assert cell['deformed']['admission_spent']==cell['bypass']['admission_spent']
        assert cell['corrected']['query']==cell['bypass']['query']!=cell['deformed']['query']
    result=dict(passed=True,pairs=32,worlds=96,bypasses_rejected=32,participant_replay=False,rows=rows)
    (base/'independent_verification.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':verify(Path(sys.argv[1]))
