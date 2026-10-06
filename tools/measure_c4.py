"""C4 prospective performance protocol; sequential isolated workers."""
import argparse,gzip,hashlib,importlib.util,json,os,platform,statistics,subprocess,sys,time,tracemalloc,types
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
sys.dont_write_bytecode=True
from tests_c4.fixtures import *
from hle_unified.crossing_audit import audit as audit_c3


def reference_engine():
    for name,filename,redirect in (
        ('_c3_crux_reference','c3_crux_execution.py',None),
        ('_c3_self_reference','c3_self_execution.py',('from .crux_execution import CruxEngine','from ._c3_crux_reference import CruxEngine')),
        ('_c3_cross_reference','c3_crossing_execution.py',('from .self_execution import SelfRouteEngine','from ._c3_self_reference import SelfRouteEngine'))):
        full='hle_unified.'+name; mod=types.ModuleType(full); mod.__package__='hle_unified'; sys.modules[full]=mod
        source=(ROOT/'reference'/filename).read_text()
        if redirect: source=source.replace(*redirect)
        exec(compile(source,str(ROOT/'reference'/filename),'exec'),mod.__dict__)
    return mod.CrossingEngine


def worker(a):
    rows=[]
    names=FAMILIES if a.lane=='panel' else ('nested',) if a.lane in ('depth','dependencies') else ('Theorize','Share','Coordinate','Organize','Apply')
    reference=reference_engine() if a.lane=='reference' else None
    for name in names:
        if a.lane in ('reference','adapted'):
            e=setup_c3(engine_type=reference if a.lane=='reference' else CruxCompositionEngine)
            face='accumulation' if name in ('Theorize','Organize') else 'expenditure'
            run=lambda:cell(e,name,face)
        else:
            e=setup(inactive=a.inactive,shared=a.shape=='shared')
            run=(lambda:nested(e,depth=a.size if a.lane=='depth' else 1,dependencies=a.size if a.lane=='dependencies' else 2)) if name=='nested' else lambda:family(e,name)
        original=e.world.resolve; calls=[0]; refs=set(); before=sum(e.wallet(x)['energy'] for x in (ALICE,BOB,EVE))
        if a.mode=='trace':
            def counted(ref): calls[0]+=1;refs.add(ref);return original(ref)
            e.world.resolve=counted;tracemalloc.start()
        cpu=time.process_time();start=time.perf_counter();out=run();wall=time.perf_counter()-start;cpu=time.process_time()-cpu
        memory=None
        if a.mode=='trace':
            retained,peak=tracemalloc.get_traced_memory();tracemalloc.stop();e.world.resolve=original
            memory=dict(retained_bytes=retained,peak_bytes=peak,resolve_calls=calls[0],unique_refs=len(refs))
        active=before-sum(e.wallet(x)['energy'] for x in (ALICE,BOB,EVE))
        start=time.perf_counter();cp=e.checkpoint();checkpoint=time.perf_counter()-start
        start=time.perf_counter();q=type(e).restore(cp);restoring=time.perf_counter()-start;assert q.checkpoint()==cp
        start=time.perf_counter();report=(audit_c3 if a.lane=='reference' else audit)(e.world.journal(),e.access.checkpoint());auditing=time.perf_counter()-start
        outcome=consequence(e,out) if a.lane in ('reference','adapted') else out['outcome']
        rows.append(dict(name=name,outcome=outcome,active_wall_seconds=wall,active_cpu_seconds=cpu,checkpoint_seconds=checkpoint,
            restore_seconds=restoring,audit_seconds=auditing,checkpoint_bytes=len(cp.encode()),compressed_checkpoint_bytes=len(gzip.compress(cp.encode(),mtime=0)),
            attempts=sum(report.get(k,0) for k in ('c3_attempts','c4_attempts')),completions=sum(report.get(k,0) for k in ('c3_completed','c4_completed')),
            semantic_steps=sum(report.get(k,0) for k in ('c3_semantic_steps','c4_steps')),modeled_total_work=report['charged_energy'],
            modeled_active_work=active,memory=memory,exact_restore=True,audit_passed=report['passed']))
    keys=('active_wall_seconds','active_cpu_seconds','checkpoint_seconds','restore_seconds','audit_seconds','checkpoint_bytes',
          'compressed_checkpoint_bytes','attempts','completions','semantic_steps','modeled_total_work','modeled_active_work')
    memory=None if a.mode!='trace' else dict(peak_bytes=max(r['memory']['peak_bytes'] for r in rows),retained_bytes=sum(r['memory']['retained_bytes'] for r in rows),
        resolve_calls=sum(r['memory']['resolve_calls'] for r in rows),unique_refs_sum=sum(r['memory']['unique_refs'] for r in rows))
    print(json.dumps(dict(lane=a.lane,shape=a.shape,inactive=a.inactive,size=a.size,mode=a.mode,
        **{k:sum(r[k] for r in rows) for k in keys},outcomes=[r['outcome'] for r in rows],memory=memory,cases=rows,
        exact_restore=True,audit_passed=True)),flush=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path);p.add_argument('--worker',action='store_true')
    p.add_argument('--lane',default='panel');p.add_argument('--shape',default='shared');p.add_argument('--inactive',type=int,default=0)
    p.add_argument('--size',type=int,default=1);p.add_argument('--mode',default='time');a=p.parse_args()
    if a.worker:return worker(a)
    a.out.mkdir(parents=True,exist_ok=False)
    paths=sorted({*ROOT.glob('hle_unified/*.py'),*ROOT.glob('tests_c*/*.py'),*ROOT.glob('reference/c3_*.py'),Path(__file__),ROOT/'contracts/C4_Protocol_v1.json'})
    manifest={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in paths}
    (a.out/'execution_source.json').write_text(json.dumps(manifest,indent=2)+'\n')
    jobs=[]
    for i in range(3):
        for lane in ('reference','adapted'):jobs.append((lane,'shared',0,1,'time',i))
    for shape in ('shared','unique'):
        for count in (0,100,1000):
            for i,mode in enumerate(('time','time','trace')):jobs.append(('panel',shape,count,1,mode,i))
    for lane in ('depth','dependencies'):
        for size in (1,2,4):
            for i in range(2):jobs.append((lane,'shared',0,size,'time',i))
    samples=[]
    for lane,shape,count,size,mode,i in jobs:
        key=f'{lane}-{shape}-{count}-{size}-{mode}-{i}'
        command=[sys.executable,__file__,'--worker','--lane',lane,'--shape',shape,'--inactive',str(count),'--size',str(size),'--mode',mode]
        done=subprocess.run(command,capture_output=True,text=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
        (a.out/(key+'.stdout.json')).write_text(done.stdout);(a.out/(key+'.stderr.txt')).write_text(done.stderr)
        if done.returncode:raise RuntimeError('measurement failed: '+key)
        samples.append(json.loads(done.stdout));print('measured '+key,flush=True)
    rows=[]
    for group in dict.fromkeys((s['lane'],s['shape'],s['inactive'],s['size']) for s in samples):
        values=[s for s in samples if (s['lane'],s['shape'],s['inactive'],s['size'])==group]
        timed=[s for s in values if s['mode']=='time'];trace=next((s for s in values if s['mode']=='trace'),None)
        row={k:timed[0][k] for k in ('lane','shape','inactive','size','attempts','completions','semantic_steps','modeled_total_work','modeled_active_work','outcomes','checkpoint_bytes','compressed_checkpoint_bytes')}
        row.update(samples=len(timed),memory=trace['memory'] if trace else None,
            **{'median_'+k:statistics.median(s[k] for s in timed) for k in ('active_wall_seconds','active_cpu_seconds','checkpoint_seconds','restore_seconds','audit_seconds')})
        rows.append(row)
    invariant=lambda s:json.dumps([s[k] for k in ('attempts','completions','semantic_steps','modeled_total_work','modeled_active_work','outcomes')])
    ratio=rows[1]['median_active_wall_seconds']/rows[0]['median_active_wall_seconds']
    panel=[r for r in rows if r['lane']=='panel'];history_ratio=max(r['median_active_wall_seconds'] for r in panel)/min(r['median_active_wall_seconds'] for r in panel)
    unchanged=all(hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==sha for f,sha in manifest.items())
    passed=ratio<=1.5 and invariant(rows[0])==invariant(rows[1]) and history_ratio<=1.75 and unchanged
    passed=passed and len({invariant(s) for s in samples if s['lane']=='panel'})==1 and len({(r['memory']['resolve_calls'],r['memory']['unique_refs_sum']) for r in panel})==1
    summary=dict(passed=passed,source_unchanged=unchanged,c3_ratio=ratio,c3_tolerance=1.5,history_ratio=history_ratio,history_tolerance=1.75,
        workers=len(samples),timing_workers=sum(s['mode']=='time' for s in samples),trace_workers=sum(s['mode']=='trace' for s in samples),
        rows=rows,python=sys.version,platform=platform.platform(),cpu_count=os.cpu_count(),
        accounting='Fresh sequential processes. Engine setup excluded; supplied content retention, exchanges, child receipts, parent review and downstream uses included. Restore constructs fresh engines within each worker. Peaks are largest independent case; other costs sum cases. Depth and child count varied separately. Populations and alternative search unassessed. Exact history retained.')
    (a.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items() if k!='rows'}),flush=True)
    if not passed:raise SystemExit(1)

if __name__=='__main__':main()
