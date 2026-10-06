"""C5 sequential isolated workers, timing and tracing kept separate."""
import sys,json,time,gzip,tracemalloc,subprocess,statistics,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
from tests_c5.fixtures import *
from hle_unified.crux_shell_audit import audit

def worker(lane,size,trace):
    if lane in ('reference','adapted'):
        e=setup_c3(engine_type=CruxCompositionEngine if lane=='reference' else CruxShellEngine)
        run=lambda:cell(e,'Theorize','accumulation')
    else:
        e=setup(inactive=size if lane.startswith('history') else 0,shared=lane=='history-shared',generate=False)
        dev.supply8(e,'opportunity',approved=True)
        if lane=='patterns':
            for i in range(size):dev.inject(e,Effect('approval'),key='effect-'+str(i))
        r=prepare(e,'Theorize','accumulation')
        def run():
            _,receipt=finish(e,r);assert receipt['admitted'];return downstream(e,r,'Theorize','accumulation')
    before=e.wallet(ALICE)['energy'];original=e.world.resolve;calls=[0];seen=set()
    if trace:
        def counted(ref):calls[0]+=1;seen.add(ref);return original(ref)
        e.world.resolve=counted;tracemalloc.start()
    start=time.perf_counter();cpu=time.process_time();run();cpu=time.process_time()-cpu;wall=time.perf_counter()-start
    memory=None
    if trace:
        current,peak=tracemalloc.get_traced_memory();tracemalloc.stop();e.world.resolve=original
        memory=dict(retained=current,peak=peak,resolve_calls=calls[0],unique_refs=len(seen))
    spent=before-e.wallet(ALICE)['energy']
    start=time.perf_counter();cp=e.checkpoint();checkpoint=time.perf_counter()-start
    start=time.perf_counter();restored=type(e).restore(cp);restore=time.perf_counter()-start
    assert restored.checkpoint()==cp
    start=time.perf_counter();a=(content_audit if lane=='reference' else audit)(e.world.journal(),e.access.checkpoint());auditing=time.perf_counter()-start
    assert a['passed']
    return dict(lane=lane,size=size,traced=trace,active_wall=wall,active_cpu=cpu,modeled_active_work=spent,memory=memory,
        checkpoint_seconds=checkpoint,restore_seconds=restore,audit_seconds=auditing,checkpoint_bytes=len(cp.encode()),
        compressed_bytes=len(gzip.compress(cp.encode(),mtime=0)),attempts=a['attempts'] if 'attempts' in a else None,
        demonstrated_consumers=1,wall_per_demonstrated_consumer=wall,exact_restore=True)

def main(out):
    out.mkdir(parents=True,exist_ok=False);samples=[]
    jobs=[(lane,0,False) for _ in range(3) for lane in ('reference','adapted')]
    jobs += [(lane,size,trace) for lane in ('history-shared','history-unique') for size in (0,100,1000) for trace in (False,False,True)]
    jobs += [('patterns',size,trace) for size in (1,4,16) for trace in (False,False,True)]
    for i,(lane,size,trace) in enumerate(jobs):
        p=subprocess.run([sys.executable,__file__,'worker',lane,str(size),str(int(trace))],text=True,capture_output=True)
        (out/f'{i:02d}-{lane}-{size}.stdout.json').write_text(p.stdout);(out/f'{i:02d}-{lane}-{size}.stderr.txt').write_text(p.stderr)
        if p.returncode:raise RuntimeError(f'worker {i} failed')
        samples.append(json.loads(p.stdout));print('measured',i,lane,size,trace,flush=True)
    rows=[]
    for lane,size in dict.fromkeys((s['lane'],s['size']) for s in samples):
        ss=[s for s in samples if (s['lane'],s['size'])==(lane,size)];timed=[s for s in ss if not s['traced']]
        rows.append(dict(lane=lane,size=size,samples=len(timed),median_active=statistics.median(s['active_wall'] for s in timed),
            median_cpu=statistics.median(s['active_cpu'] for s in timed),median_restore=statistics.median(s['restore_seconds'] for s in timed),
            median_audit=statistics.median(s['audit_seconds'] for s in timed),modeled_work=ss[0]['modeled_active_work'],
            bytes=ss[0]['checkpoint_bytes'],memory=next((s['memory'] for s in ss if s['traced']),None)))
    ratio=rows[1]['median_active']/rows[0]['median_active'];history=[r for r in rows if r['lane'].startswith('history')]
    hist_ratio=max(r['median_active'] for r in history)/min(r['median_active'] for r in history)
    passed=ratio<=2 and hist_ratio<=3 and rows[0]['modeled_work']==rows[1]['modeled_work'] and len({r['modeled_work'] for r in history})==1
    result=dict(passed=passed,workers=len(samples),reference_ratio=ratio,history_ratio=hist_ratio,rows=rows,samples=samples)
    (out/'summary.json').write_text(json.dumps(result,indent=2));assert passed,result
if __name__=='__main__':
    if sys.argv[1]=='worker':print(json.dumps(worker(sys.argv[2],int(sys.argv[3]),bool(int(sys.argv[4])))))
    else:main(Path(sys.argv[1]))
