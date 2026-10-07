"""Independent raw workflow Shell ledger; no evaluator, executor or replay."""
import sys,json,gzip,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
from hle_unified.compact import unseal
from hle_unified.material import OperationStore,attrs
from hle_unified.workflow_development_audit import audit,require_scoped_correction
from hle_unified.development_values import attrs as development_attrs
from hle_unified.selection_records import NAMES,FACES,loads,dumps
from hle_unified.shell_audit import effects
from hle_unified.operation_audit import indexed
from hle_unified.workflow_audit import payload


def read(path,schema='hle-full-crux-c7-workflow-interruption-v1'):
    raw=unseal(gzip.decompress(path.read_bytes()).decode(),schema)
    txs=OperationStore.restore(raw['world']).journal()
    return raw,txs,{v.ref:v for tx in txs for v in tx.versions}


def reference(path):
    return dict(file=str(path.resolve().relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def verify(base,prevention,active):
    rows=[];kinds=set();cells={};signs={};new_worlds=0
    for phase,folder,pattern,schema in (
        ('prevention',prevention,'*-deformed.json.gz','hle-full-crux-c7-workflow-shell-v1'),
        ('active',active,'*-interrupted.json.gz','hle-full-crux-c7-workflow-interruption-v1')):
        files=sorted(folder.glob(pattern));assert len(files)==32
        for path in files:
            raw,txs,vs=read(path,schema);report=audit(txs,raw['access']);rs=report['workflow_development_rows'];assert len(rs)==1
            r=rs[0];assert r['deformed'] and not r['completed'] and r['demand']
            admission=attrs(vs[r['ref']]);enc=attrs(vs[admission['encounter']]);ps=indexed(enc,'pattern.');assert len(ps)==1
            pd=attrs(vs[ps[0]]);es=tuple(effects(pd));assert len(es)==1;kind=es[0][0];kinds.add(kind)
            assert pd['origin_mode']==('generated' if kind=='approval' else 'injected_fixture')
            assert r['premature_translation']==(phase=='active')
            row=dict(phase=phase,recipe=r['requested'],effect=kind,origin_mode=pd['origin_mode'],
                raw=reference(path),diagnostics=r,opportunity=enc,pattern=ps[0],origin=pd['origin'])
            rows.append(row);cell=cells.setdefault(r['requested'],{});assert phase not in cell;cell[phase]=row
            for sign,present in report['workflow_diagnostic_signs'].items():signs[sign]=signs.get(sign,False) or present
    expected={'workflow-'+n.lower()+'-'+f+'-v1' for n in NAMES for f in FACES}
    assert set(cells)==expected and all(set(x)=={'active','prevention'} for x in cells.values())
    assert kinds=={'approval','obligation','salience','forecast','exclude_route'}
    snapshots=sorted(base.glob('0*.json.gz'));assert len(snapshots)==7
    history=[];originals=None;last_txs=()
    for i,path in enumerate(snapshots):
        raw,txs,vs=read(path);report=audit(txs,raw['access']);rs=report['workflow_development_rows']
        assert len(rs)==i+1 and tuple(txs[:len(last_txs)])==tuple(last_txs);last_txs=txs
        material={ref:v for ref,v in vs.items() if ref.identity.namespace in ('u7.material','u7.pattern')}
        if originals is None:originals=material
        assert material==originals
        assert not any(ref.identity.namespace=='u8.capacity' for ref in vs)
        for sign,present in report['workflow_diagnostic_signs'].items():signs[sign]=signs.get(sign,False) or present
        history.append(dict(raw=reference(path),last=rs[-1]));new_worlds+=1
    rows7=report['workflow_development_rows']
    assert [r['completed'] for r in rows7]==[False,False,False,True,False,True,False]
    assert rows7[1]['recurrence']=='same_target' and rows7[2]['recurrence']=='changed_target'
    assert rows7[0]['target']==rows7[1]['target']==rows7[3]['target'] and rows7[2]['target']!=rows7[0]['target']
    assert rows7[4]['target']==rows7[2]['target'] and rows7[4]['premature_translation']
    assert rows7[5]['supported'] and rows7[6]['premature_translation'] and not rows7[6]['supported']
    pattern=rows7[0]['patterns'][0]
    exact=require_scoped_correction(txs,raw['access'],pattern,rows7[3]['target'])
    assert exact in rows7[3]['local_corrections']
    try:require_scoped_correction(txs,raw['access'],pattern,rows7[2]['target'])
    except ValueError as exc:assert 'no actual exact-target correction' in str(exc)
    else:raise AssertionError('local correction was treated as blanket clearance')
    heads={v.ref.identity:v for v in vs.values()}
    consumers=[attrs(v) for v in heads.values() if attrs(v).get('c7w') and attrs(v).get('key') in ('corrected-consumer','supported-consumer')]
    assert len(consumers)==2 and all(c['status']=='succeeded' and c['spent']>0 and payload(vs[c['binding']])['next_task']=='handover' for c in consumers)
    refusals=[]
    for kind in ('forecast','salience','exclude_route'):
        before=base/('unsupported-'+kind+'-before.json.gz');after=base/('unsupported-'+kind+'-after.json.gz')
        assert before.read_bytes()==after.read_bytes()
        attempt=json.loads((base/('unsupported-'+kind+'-attempt.json')).read_text());request=loads(attempt['request'])
        assert request['purpose']=='release' and len(request['targets'])==1
        assert attempt['error']=='unsupported, incomplete or scaffolded local correction'
        refs=[]
        for path in (before,after,base/('unsupported-'+kind+'-still-interrupted.json.gz')):
            raw,txs,vs=read(path);report=audit(txs,raw['access']);pd=attrs(vs[request['pattern']])
            assert tuple(effects(pd))[0][0]==kind and not any(ref.identity.namespace=='u8.correction' for ref in vs)
            try:require_scoped_correction(txs,raw['access'],request['pattern'],request['targets'][0])
            except ValueError as exc:assert 'unsupported clearance' in str(exc)
            else:raise AssertionError('unsupported clearance claim accepted')
            refs.append(reference(path));new_worlds+=1
        assert report['workflow_development_rows'][-1]['premature_translation']
        refusals.append(dict(effect=kind,raw=refs,request=request,error=attempt['error']))
    assert all(signs.values()) and len(signs)==4 and new_worlds==16
    result=dict(passed=True,cells=32,effect_witnesses=64,effect_kinds=5,generated_effects=['approval'],
        diagnostic_signs=signs,new_raw_worlds=16,total_raw_worlds=80,refused_clearances=3,
        participant_replay=False,rows=list(cells.values()),history=history,refusals=refusals,
        limits='Bounded workflow simulation; no blanket clearance or mastery from support.')
    (base/'independent_verification.json').write_text(dumps(result)+'\n')
    print('PASS',json.dumps({k:v for k,v in result.items() if k not in ('rows','history','refusals')}),flush=True)
    return result


if __name__=='__main__':verify(*(Path(x) for x in sys.argv[1:]))
