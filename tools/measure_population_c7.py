"""Stopping-policy measurements; semantic policy change, not a speedup claim."""
import sys,json,time,gzip,tracemalloc,subprocess,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def worker(mode,count,trace):
    sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
    from tests_c7.fixtures import population
    from hle_unified.population import Population
    from hle_unified.population_audit import audit_population
    from hle_unified.selection_audit import audit
    from hle_unified.selection_records import loads
    p,types=population(17,count,repeat_limit=2 if mode=='stop' else None)
    before={r.actor:p.engine.wallet(r.actor)['energy'] for r in p.requests}
    if trace:tracemalloc.start()
    start=time.perf_counter();cpu=time.process_time();result=p.run(20000);cpu=time.process_time()-cpu;wall=time.perf_counter()-start
    memory=None
    if trace:memory=dict(zip(('retained','peak'),tracemalloc.get_traced_memory()));tracemalloc.stop()
    assert result['done']
    cp=p.checkpoint();t=time.perf_counter();q=Population.restore(cp);restore=time.perf_counter()-t;assert cp==q.checkpoint()
    t=time.perf_counter();a=audit(p.engine.world.journal(),p.engine.access.checkpoint());a2=audit_population(p.engine.world.journal(),loads(cp));auditing=time.perf_counter()-t
    assert a['passed'] and a2['passed']
    completed=[x for x in p.events if x.get('native_status')=='succeeded']
    signatures=[]
    for row in completed:
        if row.get('output') in p.engine.participant_view(row['actor'])._bindings:
            b=p.engine.participant_view(row['actor'])._bindings[row['output']]
            signatures.append((b.actor,b.context,b.target,tuple((z.relation,z.object) for z in b.content)))
    return dict(mode=mode,actors=count,traced=trace,result=result,types=types,wall_seconds=wall,cpu_seconds=cpu,memory=memory,
        modeled_work=sum(before[r.actor]-p.engine.wallet(r.actor)['energy'] for r in p.requests),completed_native=len(completed),
        distinct_scoped_retained_payloads=len(set(signatures)),demonstrated_new_capacities=None,
        cost_per_native_completion=wall/len(completed) if completed else None,cost_per_new_capacity=None,
        restore_seconds=restore,audit_seconds=auditing,checkpoint_bytes=len(cp.encode()),compressed_bytes=len(gzip.compress(cp.encode(),mtime=0)),
        exact_restore=True,raw_audit=True,world_hash=hashlib.sha256(p.engine.world.checkpoint().encode()).hexdigest())
def main(out):
    out.mkdir(parents=True,exist_ok=False);rows=[]
    manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for pat in ('hle_unified/*.py','tests_c7/*.py','tools/measure_population_c7.py') for p in ROOT.glob(pat)}
    (out/'source.json').write_text(json.dumps(manifest,indent=2))
    jobs=[(mode,n,trace) for mode in ('stop','monitor') for n in (2,3) for trace in (False,False,True)]
    for i,(mode,n,trace) in enumerate(jobs):
        p=subprocess.run([sys.executable,__file__,'worker',mode,str(n),str(int(trace))],text=True,capture_output=True)
        (out/f'{i:02d}.stdout.json').write_text(p.stdout);(out/f'{i:02d}.stderr.txt').write_text(p.stderr)
        assert p.returncode==0,p.stderr
        row=json.loads(p.stdout);rows.append(row);print('worker',i,mode,n,trace,flush=True)
    unchanged=all(hashlib.sha256((ROOT/k).read_bytes()).hexdigest()==v for k,v in manifest.items())
    assert unchanged
    (out/'summary.json').write_text(json.dumps(dict(passed=True,workers=len(rows),source_unchanged=unchanged,rows=rows,
        scope='Different stopping policies intentionally perform different work. No matched-semantic speedup or new capacity claim.'),indent=2))
if __name__=='__main__':
    if sys.argv[1]=='worker':print(json.dumps(worker(sys.argv[2],int(sys.argv[3]),bool(int(sys.argv[4])))))
    else:main(Path(sys.argv[1]))
