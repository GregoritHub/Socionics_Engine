"""Predeclared sustained population panel; no missing release gate inferred."""
import sys,json,time,gzip,hashlib,traceback
from dataclasses import asdict,is_dataclass
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
from tests_c7.fixtures import population
from hle_unified.population import Population
from hle_unified.selection_audit import audit
from hle_unified.material import attrs
from hle_unified.population_audit import audit_population
from hle_unified.operations import indexed
from hle_unified.selection_records import dumps,loads

def report(value):
    return json.dumps(value,default=lambda x:asdict(x) if is_dataclass(x) else str(x),indent=2)

def run(out):
    out.mkdir(parents=True,exist_ok=False)
    manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for pat in ('hle_unified/*.py','tests_c7/*.py','contracts/C7*','tools/evaluate_c7.py') for p in ROOT.glob(pat)}
    (out/'source.json').write_text(json.dumps(manifest,indent=2));rows=[]
    for seed in (17,43,89):
        for n in (2,3):
            name=f'population-{seed}-{n}';start=time.perf_counter()
            try:
                p,types=population(seed,n)
                before={r.actor:p.engine.wallet(r.actor)['energy'] for r in p.requests}
                p.run(37);mid=p.checkpoint();(out/(name+'-mid.json.gz')).write_bytes(gzip.compress(mid.encode(),mtime=0))
                q=Population.restore(mid);assert mid==q.checkpoint()
                # Continue both for one round to check exact partial progression;
                # remaining horizon uses the cold-restored population.
                p.run(n);q.run(n);assert p.checkpoint()==q.checkpoint()
                p=q;result=p.run(20000);assert result['done'],result
                cp=p.checkpoint();(out/(name+'.json.gz')).write_bytes(gzip.compress(cp.encode(),mtime=0))
                a=audit(p.engine.world.journal(),p.engine.access.checkpoint());assert a['passed']
                population_audit=audit_population(p.engine.world.journal(),loads(cp))
                generated=set();used=[];finished=[];failed=[];deferred=0;recipes={}
                # Exact input/output join over committed C6 records. It establishes
                # reuse, not novel capacity or a matched causal ablation.
                versions={v.ref:v for t in p.engine.world.journal() for v in t.versions}
                decisions=[v for v in versions.values() if v.ref.identity.namespace=='c6.decision']
                for v in decisions:
                    d=attrs(v);job=attrs(versions[d['operation']]);actor=job['actor'];key=job['key']
                    candidates=loads(attrs(versions[d['candidates']])['payload'])
                    deferred+=sum(int(x['deferred']) for x in candidates)
                    if d['failure']:failed.append(dict(key=key,reason=d['failure']))
                    if (actor,key+':movement') not in p.engine._jobs:continue
                    child=p.engine.job_status(actor,key+':movement')
                    native=p.engine._movement_inputs.get(p.engine._jobs[actor,key+':movement'].identity)
                    inputs=tuple(native[0].inputs) if native else ()
                    links=tuple(x for x in inputs if x in generated)
                    if links:used.append(dict(key=key,inputs=links,child_status=child['status']))
                    if child['status']=='succeeded':
                        finished.append(key);recipes[d['recipe']]=recipes.get(d['recipe'],0)+1
                        if child.get('binding'):generated.add(child['binding'])
                        if child.get('result'):generated.add(child['result'])
                    else:failed.append(dict(key=key,reason=child['failure'] or child['status']))
                assert finished, 'no native work completed'
                assert all(any(x.get('native_status')=='succeeded' and x['actor']==r.actor for x in p.events) for r in p.requests), 'every actor must complete native work'
                row=dict(case=name,seed=seed,types=types,actors=n,result=result,attempts=len(decisions),completed_native=len(finished),
                    failures=failed,recipes=recipes,generated_output_reuses=used,deferred_candidate_cells=deferred,
                    modeled_work={r.actor.key:before[r.actor]-p.engine.wallet(r.actor)['energy'] for r in p.requests},
                    exact_interrupted_continuation=True,audit=a,population_audit=population_audit,checkpoint_bytes=len(cp.encode()),
                    raw_file=name+'.json.gz',raw_sha256=hashlib.sha256((out/(name+'.json.gz')).read_bytes()).hexdigest(),
                    elapsed_seconds=time.perf_counter()-start,
                    limitation='Retained output reuse is not itself a matched causal capacity gain. Initial demands supplied. No replenishment.')
                rows.append(row);(out/(name+'.summary.json')).write_text(report(row));print(name,row['completed_native'],len(used),round(row['elapsed_seconds'],2),flush=True)
            except Exception:
                (out/(name+'-failure.txt')).write_text(traceback.format_exc());raise
    unchanged=all(hashlib.sha256((ROOT/k).read_bytes()).hexdigest()==v for k,v in manifest.items())
    (out/'summary.json').write_text(report(dict(passed=unchanged,source_unchanged=unchanged,worlds=len(rows),rows=rows)));assert unchanged
if __name__=='__main__':run(Path(sys.argv[1]))
