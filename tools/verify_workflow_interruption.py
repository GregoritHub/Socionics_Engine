"""Independent raw interruption reconstruction; no executor or fixture imports."""
import sys,json,gzip,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
from hle_unified.compact import unseal
from hle_unified.material import OperationStore,attrs
from hle_unified.workflow_interruption_audit import audit
from hle_unified.workflow_shell_audit import audit as inherited_audit
from hle_unified.workflow_audit import payload
from hle_unified.selection_records import NAMES,FACES
from hle_unified.shell_records import KINDS
from hle_unified.shell_audit import effects
from hle_unified.operation_audit import indexed

def read(p):
    raw=unseal(gzip.decompress(p.read_bytes()).decode(),'hle-full-crux-c7-workflow-interruption-v1')
    world=OperationStore.restore(raw['world']);txs=world.journal()
    return raw,txs,{v.ref:v for tx in txs for v in tx.versions},{v.ref.identity:v for tx in txs for v in tx.versions}

def verify(base):
    rows=[];by_cell={};continuation_rows=[]
    for p in sorted(base.glob('*.json.gz')):
        raw,txs,versions,heads=read(p);inherited_audit(txs,raw['access']);rejection=None
        try:report=audit(txs,raw['access'])
        except ValueError as exc:
            rejection=str(exc);assert p.name.endswith('-bypass.json.gz') and 'escaped first boundary' in rejection
        admissions=[attrs(v) for v in versions.values() if v.ref.identity.namespace=='c7shi.admission'];assert len(admissions)==1
        d=admissions[0];c=attrs(heads[d['child'].identity]);recipe=d['requested_recipe']
        arm='bypass' if rejection else 'control' if report['workflow_interruption_completed'] else 'interrupted'
        assert p.name.endswith('-'+arm+'.json.gz')
        prefix=c['recall_units']+sum(indexed(c,'route.0.charges.'))+c['route.0.content_units'];effect=None;origin_mode=None
        if arm=='interrupted':
            a=report['workflow_interruption_rows'][0]
            assert a['early_substitution'] and not a['foreclosure'] and not a['completed']
            assert c['status']=='cancelled' and c['steps_completed']==1 and c['spent']==prefix
            enc=attrs(versions[d['encounter']]);patterns=indexed(enc,'pattern.');assert len(patterns)==1
            pattern=attrs(versions[patterns[0]]);es=tuple(effects(pattern));assert len(es)==1
            effect=es[0][0];origin_mode=pattern['origin_mode'];query='unavailable'
        else:
            assert c['status']=='succeeded'
            consumers=[attrs(v) for v in heads.values() if attrs(v).get('key')==c['key']+'-consumer' and attrs(v).get('c7w')]
            assert len(consumers)==1 and consumers[0]['status']=='succeeded'
            query=payload(versions[consumers[0]['binding']])['next_task'];assert query is not None
        row=dict(file=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),recipe=recipe,arm=arm,
            admission_spent=d['admission_spent'],prefix_spent=prefix,child_spent=c['spent'],
            query=query,effect=effect,origin_mode=origin_mode,rejection=rejection)
        rows.append(row);cell=by_cell.setdefault(recipe,{});assert arm not in cell;cell[arm]=row
        (base/'independent_progress.json').write_text(json.dumps(dict(panel_worlds=len(rows),continuation_pairs=len(continuation_rows)),indent=2)+'\n')
        print('AUDIT',p.name,flush=True)
    expected=['workflow-'+n.lower()+'-'+f+'-v1' for n in NAMES for f in FACES]
    assert set(by_cell)==set(expected) and len(rows)==96
    for i,recipe in enumerate(expected):
        cell=by_cell[recipe];assert set(cell)=={'interrupted','control','bypass'}
        a,b,c=cell['interrupted'],cell['bypass'],cell['control']
        assert a['admission_spent']==b['admission_spent'] and a['prefix_spent']==b['prefix_spent']
        assert c['query']==b['query']!=a['query']
        assert a['effect']==KINDS[i%len(KINDS)]
        assert a['origin_mode']==('generated' if a['effect']=='approval' else 'injected_fixture')
        key=NAMES[i//2]+'-'+FACES[i%2]
        files=[base/'continuations'/(key+'-'+arm+'.json.gz') for arm in ('checkpoint','original','restored')]
        assert files[1].read_bytes()==files[2].read_bytes()
        histories=[];spending=[]
        for j,p in enumerate(files):
            raw,txs,versions,heads=read(p);report=audit(txs,raw['access']);histories.append(txs)
            assert report['workflow_interruption_rows'][0]['early_substitution']
            jobs=[attrs(v) for v in heads.values() if attrs(v).get('u7') and attrs(v).get('key')=='after-stop']
            if j==0:assert not jobs
            else:
                assert len(jobs)==1 and jobs[0]['status']=='succeeded' and jobs[0]['spent']>0
                spending.append(jobs[0]['spent'])
        assert histories[1][:len(histories[0])]==histories[0] and histories[1]==histories[2]
        assert spending[0]==spending[1]
        continuation_rows.append(dict(recipe=recipe,exact=True,paid_work=spending[0],files=[dict(file=str(p.relative_to(base)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files]))
        (base/'independent_progress.json').write_text(json.dumps(dict(panel_worlds=96,continuation_pairs=len(continuation_rows)),indent=2)+'\n')
        print('CONTINUATION',key,flush=True)
    result=dict(passed=True,pairs=32,panel_worlds=96,continuation_worlds=96,exact_continuations=32,
        invalid_continuations_rejected=32,effects=5,participant_replay=False,rows=rows,continuations=continuation_rows)
    (base/'independent_verification.json').write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':verify(Path(sys.argv[1]))
