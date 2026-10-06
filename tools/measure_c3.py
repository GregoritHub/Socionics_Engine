"""Prospectively bounded C3 costs. Each worker is a fresh isolated process."""
import argparse,gzip,hashlib,importlib.util,json,os,platform,statistics,subprocess,sys,time,tracemalloc,types
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
sys.dont_write_bytecode=True
from tests_c3.fixtures import *
from tests_c2.test_self_routes import consequence as consequence_c2
from hle_unified.crossing_audit import audit
from hle_unified.self_audit import audit as audit_c2

def reference_engine():
    name='hle_unified._c2_crux_reference'
    spec=importlib.util.spec_from_file_location(name,ROOT/'reference/c2_crux_execution.py')
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod)
    name='hle_unified._c2_self_reference'; mod=types.ModuleType(name); mod.__package__='hle_unified'; sys.modules[name]=mod
    source=(ROOT/'reference/c2_self_execution.py').read_text().replace('from .crux_execution import CruxEngine','from ._c2_crux_reference import CruxEngine')
    exec(compile(source,str(ROOT/'reference/c2_self_execution.py'),'exec'),mod.__dict__)
    return mod.SelfRouteEngine

def worker(a):
    configurations=[(n,f) for n in PATHS for f in FACES]
    if a.lane in ('reference','adapted'): configurations=[(n,f) for n in ('Contemplate','Act','Commune','Integrate') for f in FACES]
    if a.lane=='scale': configurations=[('Organize','accumulation')]
    rows=[]
    for name,face in configurations:
        if a.lane in ('reference','adapted'):
            cls=reference_engine() if a.lane=='reference' else CrossingEngine
            e=setup_c2(actual='serviceable' if name=='Act' and face=='expenditure' else 'damaged',engine_type=cls,inactive=a.inactive,shared=a.shape=='shared')
            execute=lambda:cell_c2(e,name,face)
        else:
            e=setup_c3(inactive=a.inactive,shared=a.shape=='shared')
            execute=lambda:cell(e,name,face,dependencies=a.dependencies if a.lane=='scale' else 1)
        original=e.world.resolve; calls=[0]; refs=set()
        before=sum(e.wallet(x)['energy'] for x in (ALICE,BOB,EVE))
        if a.mode=='trace':
            def counted(ref): calls[0]+=1; refs.add(ref); return original(ref)
            e.world.resolve=counted; tracemalloc.start()
        cpu=time.process_time(); start=time.perf_counter(); out=execute()
        wall=time.perf_counter()-start; cpu=time.process_time()-cpu
        memory=None
        if a.mode=='trace':
            retained,peak=tracemalloc.get_traced_memory(); tracemalloc.stop(); e.world.resolve=original
            memory=dict(retained_bytes=retained,peak_bytes=peak,resolve_calls=calls[0],unique_refs=len(refs))
        after=sum(e.wallet(x)['energy'] for x in (ALICE,BOB,EVE))
        start=time.perf_counter(); cp=e.checkpoint(); checkpoint_seconds=time.perf_counter()-start
        start=time.perf_counter(); restored=type(e).restore(cp); restore_seconds=time.perf_counter()-start
        assert cp==restored.checkpoint()
        start=time.perf_counter(); report=(audit_c2 if a.lane=='reference' else audit)(e.world.journal(),e.access.checkpoint()); audit_seconds=time.perf_counter()-start
        if a.lane in ('reference','adapted'):
            outcome=consequence_c2(e,out,name); count=report['c2_attempts']; completed=report['c2_completed']; steps=report['c2_semantic_steps']
        else:
            outcome=consequence(e,out); count=report['c3_attempts']; completed=report['c3_completed']; steps=report['c3_semantic_steps']
        rows.append(dict(route=name,polarity=face,active_wall_seconds=wall,active_cpu_seconds=cpu,
            checkpoint_seconds=checkpoint_seconds,restore_seconds=restore_seconds,audit_seconds=audit_seconds,memory=memory,
            checkpoint_bytes=len(cp.encode()),compressed_checkpoint_bytes=len(gzip.compress(cp.encode(),mtime=0)),
            movement_attempts=count,movement_completions=completed,semantic_steps=steps,
            modeled_total_work=report['charged_energy'],modeled_active_work=before-after,outcome=outcome,
            exact_restore=True,audit_passed=report['passed']))
    keys=('active_wall_seconds','active_cpu_seconds','checkpoint_seconds','restore_seconds','audit_seconds','checkpoint_bytes',
        'compressed_checkpoint_bytes','movement_attempts','movement_completions','semantic_steps','modeled_total_work','modeled_active_work')
    totals={k:sum(r[k] for r in rows) for k in keys}
    memory=None if a.mode!='trace' else dict(peak_bytes=max(r['memory']['peak_bytes'] for r in rows),
        retained_bytes=sum(r['memory']['retained_bytes'] for r in rows),resolve_calls=sum(r['memory']['resolve_calls'] for r in rows),
        unique_refs_sum=sum(r['memory']['unique_refs'] for r in rows))
    print(json.dumps(dict(lane=a.lane,mode=a.mode,shape=a.shape,inactive=a.inactive,dependencies=a.dependencies,**totals,
        memory=memory,outcomes=[r['outcome'] for r in rows],cases=rows,exact_restore=True,audit_passed=True)),flush=True)

def main():
    p=argparse.ArgumentParser(); p.add_argument('--out',type=Path); p.add_argument('--worker',action='store_true')
    p.add_argument('--lane',default='panel',choices=('reference','adapted','panel','scale'))
    p.add_argument('--shape',default='shared'); p.add_argument('--inactive',type=int,default=0)
    p.add_argument('--dependencies',type=int,default=1); p.add_argument('--mode',default='time'); a=p.parse_args()
    if a.worker: return worker(a)
    a.out.mkdir(parents=True,exist_ok=False)
    paths=sorted({*ROOT.glob('hle_unified/*.py'),*ROOT.glob('tests_c*/*.py'),*ROOT.glob('tools/*c3*.py'),
        *ROOT.glob('reference/c2_*.py'),ROOT/'tools/export_crossing_witnesses.py',ROOT/'contracts/C3_Protocol_v1.json'})
    manifest={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in paths}
    (a.out/'execution_source.json').write_text(json.dumps(manifest,indent=2)+'\n')
    jobs=[]
    for i in range(3):
        for lane in ('reference','adapted'): jobs.append((lane,'shared',0,1,'time',i))
    for shape in ('shared','unique'):
        for inactive in (0,100,1000):
            jobs.extend(('panel',shape,inactive,1,mode,i) for i,mode in enumerate(('time','time','trace')))
    for dep in (1,2,4): jobs.extend(('scale','shared',0,dep,'time',i) for i in range(2))
    samples=[]
    for lane,shape,inactive,dep,mode,i in jobs:
        key=f'{lane}-{shape}-{inactive}-{dep}-{mode}-{i}'
        command=[sys.executable,__file__,'--worker','--lane',lane,'--shape',shape,'--inactive',str(inactive),
            '--dependencies',str(dep),'--mode',mode]
        done=subprocess.run(command,capture_output=True,text=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
        (a.out/(key+'.stdout.json')).write_text(done.stdout); (a.out/(key+'.stderr.txt')).write_text(done.stderr)
        if done.returncode: raise RuntimeError('failed measurement '+key)
        samples.append(json.loads(done.stdout)); print('measured '+key,flush=True)
    rows=[]
    for group in dict.fromkeys((s['lane'],s['shape'],s['inactive'],s['dependencies']) for s in samples):
        found=[s for s in samples if (s['lane'],s['shape'],s['inactive'],s['dependencies'])==group]
        timed=[s for s in found if s['mode']=='time']; traced=next((s for s in found if s['mode']=='trace'),None)
        row={k:timed[0][k] for k in ('lane','shape','inactive','dependencies','movement_attempts','movement_completions',
            'semantic_steps','modeled_total_work','modeled_active_work','outcomes','checkpoint_bytes','compressed_checkpoint_bytes')}
        row.update(samples=len(timed),memory=traced['memory'] if traced else None,
            **{'median_'+k:statistics.median(s[k] for s in timed) for k in ('active_wall_seconds','active_cpu_seconds',
                'checkpoint_seconds','restore_seconds','audit_seconds')})
        rows.append(row)
    invariant=lambda s: json.dumps([s[k] for k in ('movement_attempts','movement_completions','semantic_steps','modeled_total_work','modeled_active_work','outcomes')],sort_keys=True)
    reference,adapted=rows[:2]; ratio=adapted['median_active_wall_seconds']/reference['median_active_wall_seconds']
    fixed=[s for s in samples if s['lane']=='panel']; panels=[r for r in rows if r['lane']=='panel']
    history_ratio=max(r['median_active_wall_seconds'] for r in panels)/min(r['median_active_wall_seconds'] for r in panels)
    unchanged=all(hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==sha for f,sha in manifest.items())
    passed=(ratio<=1.5 and invariant(reference)==invariant(adapted) and history_ratio<=1.75
        and len({invariant(s) for s in fixed})==1
        and len({(r['memory']['resolve_calls'],r['memory']['unique_refs_sum']) for r in panels})==1 and unchanged)
    summary=dict(passed=passed,source_unchanged=unchanged,c2_ratio=ratio,c2_tolerance=1.5,history_ratio=history_ratio,
        history_tolerance=1.75,workers=len(samples),timing_workers=sum(s['mode']=='time' for s in samples),
        trace_workers=sum(s['mode']=='trace' for s in samples),rows=rows,python=sys.version,platform=platform.platform(),
        accounting='Sequential fresh workers. Setup excluded from active interval; content seeding, exchanges and downstream work included. Each panel sums independent cases. Peak is maximum case allocation; checkpoints and other costs are sums. Restore constructs fresh engines by exact replay within the worker. Dependency count varies received observations only. Other growth axes remain unassessed.')
    (a.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k!='rows'}),flush=True)
    if not passed: raise SystemExit(1)

if __name__=='__main__': main()
