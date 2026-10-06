"""Sequential isolated C6 workers. Timing, tracing, restore and audit are separate."""
import sys,json,time,gzip,tracemalloc,subprocess,statistics,hashlib,platform
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def worker(lane,size,trace):
    if lane=='reference':
        sys.path[:0]=[str(ROOT/'baseline/c5_reference'),str(ROOT/'baseline/HLE_Rebuild_R21B')]
        from tests_c5.fixtures import setup_c3,cell,CruxShellEngine,ALICE
        from hle_unified.crux_shell_audit import audit
        e=setup_c3(engine_type=CruxShellEngine);run=lambda:cell(e,'Theorize','accumulation')
    else:
        sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
        from tests_c6.fixtures import fixture,finish_selection,downstream,seed_intent,ALICE,SelectionEngine,setup_c3,cell
        from hle_unified.selection_audit import audit
        if lane=='adapted':
            e=setup_c3(engine_type=SelectionEngine);run=lambda:cell(e,'Theorize','accumulation')
        else:
            e,r=fixture('Theorize','accumulation',inactive=size if lane.startswith('history') else 0,shared_history=lane=='history-shared')
            if lane=='alternatives':
                for i in range(size-1):seed_intent(e,'alternative-'+str(i),cap=1+i%4)
            def run():
                _,d=finish_selection(e,r);assert d['recipe']=='theorize-accumulation-v1' and d['failure'] is None
                native=e._movement_inputs[e._jobs[ALICE,r.key+':movement'].identity][0]
                return downstream(e,native,'Theorize','accumulation')
    before=e.wallet(ALICE)['energy'];old=e.world.resolve;calls=[0];refs=set()
    if trace:
        def counted(ref):calls[0]+=1;refs.add(ref);return old(ref)
        e.world.resolve=counted;tracemalloc.start()
    start=time.perf_counter();cpu=time.process_time();run();cpu=time.process_time()-cpu;wall=time.perf_counter()-start
    memory=None
    if trace:
        current,peak=tracemalloc.get_traced_memory();tracemalloc.stop();e.world.resolve=old
        memory=dict(retained=current,peak=peak,resolve_calls=calls[0],unique_refs=len(refs))
    spent=before-e.wallet(ALICE)['energy']
    t=time.perf_counter();cp=e.checkpoint();checkpoint=time.perf_counter()-t
    t=time.perf_counter();restored=type(e).restore(cp);restore=time.perf_counter()-t;assert restored.checkpoint()==cp
    t=time.perf_counter();a=audit(e.world.journal(),e.access.checkpoint());auditing=time.perf_counter()-t;assert a['passed']
    return dict(lane=lane,size=size,traced=trace,active_wall=wall,active_cpu=cpu,modeled_active_work=spent,memory=memory,
        checkpoint_seconds=checkpoint,restore_seconds=restore,audit_seconds=auditing,checkpoint_bytes=len(cp.encode()),
        compressed_bytes=len(gzip.compress(cp.encode(),mtime=0)),demonstrated_consumers=1,exact_restore=True,
        world_sha256=hashlib.sha256(e.world.checkpoint().encode()).hexdigest(),access_sha256=hashlib.sha256(e.access.checkpoint().encode()).hexdigest())

def main(out):
    out.mkdir(parents=True,exist_ok=False);samples=[]
    manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for pattern in ('hle_unified/*.py','tools/measure_c6.py','contracts/C6*') for p in ROOT.glob(pattern)}
    (out/'source.json').write_text(json.dumps(manifest,indent=2))
    jobs=[(lane,0,False) for _ in range(3) for lane in ('reference','adapted')]
    jobs += [(lane,size,trace) for lane in ('history-shared','history-unique') for size in (0,100,1000) for trace in (False,False,True)]
    jobs += [('alternatives',size,trace) for size in (1,4,16) for trace in (False,False,True)]
    for i,(lane,size,trace) in enumerate(jobs):
        p=subprocess.run([sys.executable,__file__,'worker',lane,str(size),str(int(trace))],text=True,capture_output=True)
        (out/f'{i:02d}-{lane}-{size}.stdout.json').write_text(p.stdout);(out/f'{i:02d}-{lane}-{size}.stderr.txt').write_text(p.stderr)
        if p.returncode:raise RuntimeError(f'worker {i} failed')
        samples.append(json.loads(p.stdout));print('measured',i,lane,size,trace,flush=True)
    rows=[]
    for lane,size in dict.fromkeys((s['lane'],s['size']) for s in samples):
        ss=[s for s in samples if (s['lane'],s['size'])==(lane,size)];timed=[s for s in ss if not s['traced']]
        rows.append(dict(lane=lane,size=size,samples=len(timed),median_active=statistics.median(s['active_wall'] for s in timed),median_cpu=statistics.median(s['active_cpu'] for s in timed),
            median_restore=statistics.median(s['restore_seconds'] for s in timed),median_audit=statistics.median(s['audit_seconds'] for s in timed),modeled_work=ss[0]['modeled_active_work'],
            bytes=ss[0]['checkpoint_bytes'],memory=next((s['memory'] for s in ss if s['traced']),None)))
    ratio=rows[1]['median_active']/rows[0]['median_active'];history=[r for r in rows if r['lane'].startswith('history')];hist_ratio=max(r['median_active'] for r in history)/min(r['median_active'] for r in history)
    unchanged=all(hashlib.sha256((ROOT/k).read_bytes()).hexdigest()==v for k,v in manifest.items())
    direct=[s for s in samples if s['lane'] in ('reference','adapted')]
    matched_semantics=len({(s['world_sha256'],s['access_sha256']) for s in direct})==1
    passed=matched_semantics and ratio<=2 and hist_ratio<=3 and rows[0]['modeled_work']==rows[1]['modeled_work'] and len({r['modeled_work'] for r in history})==1 and unchanged
    result=dict(passed=passed,workers=len(samples),reference_ratio=ratio,history_ratio=hist_ratio,source_unchanged=unchanged,matched_direct_world_and_access=matched_semantics,python=sys.version,platform=platform.platform(),rows=rows,samples=samples)
    (out/'summary.json').write_text(json.dumps(result,indent=2));assert passed
if __name__=='__main__':
    if sys.argv[1]=='worker':print(json.dumps(worker(sys.argv[2],int(sys.argv[3]),bool(int(sys.argv[4])))))
    else:main(Path(sys.argv[1]))
