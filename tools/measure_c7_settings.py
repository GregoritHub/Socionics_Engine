"""Isolated cost workers. No semantics-preserving speedup is claimed."""
import sys,json,time,subprocess,statistics,tracemalloc,gzip,platform
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
from evaluate_c7_settings import manifest,report

def worker(history,shared,count,traced):
    from tests_c7_workflow.fixtures import setup_workflow,authored,request,work,ALICE,WorkflowEngine
    from hle_unified.workflow_audit import audit
    start=time.perf_counter();e=setup_workflow(inactive=history,shared=shared)
    rows=tuple(('step-'+str(i),'care' if i==0 else 'use',() if i==0 else ('step-'+str(i-1),),i,i+2,ALICE) for i in range(count))
    own=authored(e,'cost-intent',rows);setup=time.perf_counter()-start;before=e.wallet(ALICE)['energy']
    if traced:tracemalloc.start()
    start=time.perf_counter();cpu=time.process_time()
    for i in range(4):out=work(e,request(e,'cost-'+str(i),'Theorize','accumulation',(own,)))
    active=time.perf_counter()-start;active_cpu=time.process_time()-cpu
    peak=tracemalloc.get_traced_memory()[1] if traced else None
    if traced:tracemalloc.stop()
    start=time.perf_counter();work(e,request(e,'cost-query','use-system',None,(out,),completed=('step-0',),clock=1));consumer=time.perf_counter()-start
    start=time.perf_counter();checkpoint=e.checkpoint();cp_time=time.perf_counter()-start
    start=time.perf_counter();restored=WorkflowEngine.restore(checkpoint);restore=time.perf_counter()-start;assert restored.checkpoint()==checkpoint
    start=time.perf_counter();checked=audit(e.world.journal(),e.access.checkpoint());audit_time=time.perf_counter()-start;assert checked['passed']
    print(json.dumps(dict(history=history,shared=shared,tasks=count,traced=traced,movements=4,queries=1,setup_seconds=setup,
        active_seconds=active,active_cpu_seconds=active_cpu,consumer_seconds=consumer,checkpoint_seconds=cp_time,
        restore_seconds=restore,audit_seconds=audit_time,traced_peak_bytes=peak,checkpoint_bytes=len(checkpoint.encode()),gzip_bytes=len(gzip.compress(checkpoint.encode(),mtime=0)),
        actor_work=before-e.wallet(ALICE)['energy'],transactions=len(e.world.journal()),passed=True)))

def main(out):
    out.mkdir(parents=True,exist_ok=False);source=manifest();(out/'source.json').write_text(report(source));rows=[]
    configs=[(n,shared,2) for shared in (False,True) for n in (0,100,1000)]+[(0,False,n) for n in (4,8)]
    for n,shared,count in configs:
        for sample,traced in ((0,False),(1,False),(2,True)):
            key=f'h{n}-s{int(shared)}-t{count}-r{sample}';path=out/(key+'.json')
            proc=subprocess.run([sys.executable,__file__,'--worker',str(n),str(int(shared)),str(count),str(int(traced))],cwd=ROOT,capture_output=True,text=True)
            (out/(key+'.stderr.log')).write_text(proc.stderr);path.write_text(proc.stdout)
            if proc.returncode:raise RuntimeError(key+' worker failed')
            row=json.loads(proc.stdout);rows.append(row);print(key,round(row['active_seconds'],4),flush=True)
    medians={}
    for shared in (False,True):
        values=[statistics.median(r['active_seconds'] for r in rows if r['history']==n and r['shared']==shared and r['tasks']==2 and not r['traced']) for n in (0,100,1000)]
        medians[str(shared)]=dict(medians=values,largest_smallest_ratio=max(values)/min(values),passed=max(values)/min(values)<=3.0)
    unchanged=source==manifest();summary=dict(passed=unchanged and all(v['passed'] for v in medians.values()),source_unchanged=unchanged,
        workers=len(rows),history_panel=medians,host=platform.platform(),python=sys.version,rows=rows,
        limitation='Shared-host isolated processes; traced workers excluded from timing medians. Four main movements and one downstream query per worker. No per-new-capacity or optimization claim.')
    (out/'summary.json').write_text(report(summary));print('measurement complete',summary['passed'],flush=True);assert summary['passed']
if __name__=='__main__':
    if sys.argv[1]=='--worker':worker(int(sys.argv[2]),bool(int(sys.argv[3])),int(sys.argv[4]),bool(int(sys.argv[5])))
    else:main(Path(sys.argv[1]))
