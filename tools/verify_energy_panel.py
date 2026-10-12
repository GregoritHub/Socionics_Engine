"""Independent standalone reconstruction of Phase7 raw panel records."""
import concurrent.futures,gzip,hashlib,json,pathlib,sys,traceback
from dataclasses import replace
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
from tools.run_energy_regression import manifest
from hle_unified.compact import unseal
from hle_unified.material import OperationStore,attrs,attributes
from hle_unified.selection_records import loads,dumps
from hle_unified.workflow_selection_audit import audit,extent
from hle_unified.workflow_audit import audit as native_audit
from hle_unified.population_audit import audit_population
from hle_unified.workflow_agenda_population_audit import audit_agenda_population
from hle_unified.conditioning_audit import observations
from hle_unified.energy_audit import cumulative_energy

def read(out,item):
    b=(out/item['file']).read_bytes();assert hashlib.sha256(b).hexdigest()==item['sha256']
    return gzip.decompress(b).decode()

def raw(text):
    e=json.loads(text);payload=unseal(text,e['schema'])
    return OperationStore.restore(payload['world']).journal(),payload['access']

def normalized_transactions(txs):
    result=[]
    for tx in txs:
        versions=[]
        for v in tx.versions:
            d=attrs(v)
            if d.get('record_type')=='wallet':d['energy']=0;d.pop('resource_model',None)
            if v.ref.identity.namespace in ('c6.snapshot','c7ws.snapshot'):
                s=loads(d['payload']);s['wallet']=(0,s['wallet'][1]);d['payload']=dumps(s)
            versions.append(replace(v,attributes=attributes(d)))
        result.append(replace(tx,versions=tuple(versions)))
    return repr(tuple(result))

def population_signature(state):
    if isinstance(state,dict):
        return {k:population_signature(v) for k,v in state.items() if k!='engine'}
    if isinstance(state,list):return [population_signature(v) for v in state]
    return state

def payment_boundaries(txs):
    heads={v.ref.identity:v for tx in txs for v in tx.versions};jobs=[];stops=[]
    wallets={attrs(v)['actor']:attrs(v) for v in heads.values() if attrs(v).get('record_type')=='wallet'}
    for v in heads.values():
        d=attrs(v)
        if d.get('record_type')!='operation':continue
        jobs.append((d['actor'].key,d['key'],d['completed'],d['required'],d['status']))
        if d['completed']<d['required'] and d['status'] not in ('cancelled','failed','succeeded'):
            w=wallets[d['actor']];cost=cumulative_energy(d,d['completed']+1)-cumulative_energy(d,d['completed']) if w.get('resource_model')=='grade-v1' else 1
            if w['time']==0 or w['energy']<cost:
                stops.append(dict(actor=d['actor'].key,key=d['key'],completed=d['completed'],required=d['required'],wallet_energy=w['energy'],wallet_time=w['time'],next_energy=cost,currency='time' if w['time']==0 else 'energy'))
    return sorted(jobs),stops

def pair(out,row):
    assert row['passed'], 'generation did not complete'
    results=[];signatures=[]
    for model in row['models']:
        txs,access=raw(read(out,model['engine']));report=audit(txs,access)
        obs=json.loads(dumps(observations(txs)));bounds,stops=payment_boundaries(txs)
        ap=unseal(access,json.loads(access)['schema'])
        signature=[normalized_transactions(txs),repr((ap['nodes'],ap['events']))]
        popreport=None
        if 'population' in model:
            state=loads(read(out,model['population']))
            popreport=audit_population(txs,state) if row['spec']['kind']=='core' else audit_agenda_population(txs,access,state)
            ps=population_signature(state)
            # Only the energy component of recorded two-ledger charge is exempt.
            def charges(obj):
                if isinstance(obj,dict):
                    result={}
                    for k,v in obj.items():
                        if k=='charged' and isinstance(v,tuple):
                            if len(v)==2 and all(type(n) is int for n in v):v=(0,v[1])
                            else:
                                assert all(isinstance(t,tuple) and len(t)==3 for t in v)
                                v=tuple((actor,0,time) for actor,energy,time in v)
                            result[k]=v
                        else:result[k]=charges(v)
                    return result
                if isinstance(obj,list):return [charges(v) for v in obj]
                return obj
            signature.append(dumps(charges(ps)))
        if model['setup_failure'] and not stops:raise AssertionError('setup failure is not independently explained by unavailable currency')
        control=None
        if 'control' in model:
            ct,ca=raw(read(out,model['control']));native_audit(ct,ca,extent_check=extent,extended_flags=('c7ws',));observations(ct)
            try:audit(ct,ca)
            except ValueError as exc:
                assert 'choice withheld' in str(exc);control=str(exc)
            else:raise AssertionError('withheld native child accepted')
        signatures.append(signature)
        results.append(dict(model=model['model'],audit=report,population_audit=popreport,conditioning=obs,paid_boundaries=bounds,unaffordable_next_steps=stops,control_rejected=control,setup_failure=model['setup_failure']))
    ample=row['spec']['funding']=='ample'
    match=signatures[0]==signatures[1] and row['models'][0].get('outcome')==row['models'][1].get('outcome')
    divergent=results[0]['paid_boundaries']!=results[1]['paid_boundaries']
    return json.loads(dumps(dict(id=row['spec']['id'],spec=row['spec'],passed=not ample or match,P1_match=match if ample else None,P3_qualifies=not ample and divergent and any(r['unaffordable_next_steps'] for r in results),models=results)))

def main(out):
    freeze=manifest();assert freeze==json.loads((out/'source_freeze.json').read_text())
    panel=json.loads((out/'summary.json').read_text());assert panel['passed']
    rows=[];failures=[]
    for source in panel['rows']:
        try:rows.append(pair(out,source))
        except Exception:failures.append(dict(id=source['spec']['id'],error=traceback.format_exc()))
        if (len(rows)+len(failures))%32==0:print('audited',len(rows),'errors',len(failures),flush=True)
    forbidden=[x for x in sys.modules if x.startswith('hle_unified.') and 'execution' in x]
    result=dict(passed=not failures and all(r['passed'] for r in rows) and manifest()==freeze and not forbidden,P1='held' if not failures and all(r['passed'] for r in rows) else 'failed',P2='held' if not failures else 'failed',P3='held' if any(r['P3_qualifies'] for r in rows) else 'not tested/not testable',pairs=len(rows),ample_pairs=sum(r['P1_match'] is not None for r in rows),controls=sum(bool(m['control_rejected']) for r in rows for m in r['models']),source_unchanged=manifest()==freeze,execution_imports=forbidden,failures=failures,rows=rows)
    (out/'independent_audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='rows'}),flush=True)
    return result
if __name__=='__main__':sys.exit(not main(pathlib.Path(sys.argv[1]).resolve())['passed'])
