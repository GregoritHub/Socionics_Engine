"""Sequential isolated C2 timings; no speedup claim on new semantic workloads."""
import argparse,gzip,hashlib,importlib.util,json,os,platform,statistics,subprocess,sys,time,tracemalloc
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
sys.dont_write_bytecode=True
from tests_c2.fixtures import *
from tests_c2.test_self_routes import NAMES,FACES,consequence
from hle_unified.self_audit import audit
from hle_unified import codec
from hle_unified.crux_audit import audit as c1_audit


def reference_engine():
    spec=importlib.util.spec_from_file_location('hle_unified._c1_reference',ROOT/'reference/c1_crux_execution.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.CruxEngine


def worker(a):
    rows=[]
    configurations=[(n,f) for n in NAMES for f in FACES] if a.lane=='panel' else [(None,None)]
    for name,face in configurations:
        if a.lane in ('reference','c2'):
            cls=reference_engine() if a.lane=='reference' else SelfRouteEngine
            e=setup_c1(engine_type=cls,inactive=a.inactive,shared=a.shape=='shared')
            execute=lambda: run_circuit(e)
        elif a.lane=='scale':
            e=setup_c2(inactive=a.inactive,shared=a.shape=='shared')
            first=seed_data(e,'scale-a',dict(kind='system',nodes=(('repair',('damaged',),('serviceable',),'repair',ALICE),)))
            second=seed_data(e,'scale-b',dict(kind='system',nodes=tuple((f'use-{i}',('serviceable',),('used',),'use',ALICE) for i in range(a.nodes-1))))
            expose(e,ALICE,SAW)
            request=req(e,'merge','integrate-accumulation-v1',(first,second))
            def execute():
                result=work(e,request); later=consume(e,result)
                assert 'used' in data(e,later)['reachable']
                return dict(result=result,downstream=later)
        else:
            e=setup_c2(actual='serviceable' if name=='Act' and face=='expenditure' else 'damaged',
                       inactive=a.inactive,shared=a.shape=='shared')
            execute=lambda:cell(e,name,face)
        original=e.world.resolve;calls=[0];refs=set()
        if a.mode=='trace':
            def counted(ref): calls[0]+=1;refs.add(ref);return original(ref)
            e.world.resolve=counted;tracemalloc.start()
        before=sum(e.wallet(x)['energy'] for x in (ALICE,BOB,EVE))
        cpu=time.process_time();wall=time.perf_counter();out=execute()
        wall=time.perf_counter()-wall;cpu=time.process_time()-cpu
        after=sum(e.wallet(x)['energy'] for x in (ALICE,BOB,EVE))
        memory=None
        if a.mode=='trace':
            retained,peak=tracemalloc.get_traced_memory();tracemalloc.stop();e.world.resolve=original
            memory=dict(retained_bytes=retained,peak_bytes=peak,resolve_calls=calls[0],unique_refs=len(refs))
        cp=e.checkpoint();world=e.world.checkpoint()
        start=time.perf_counter();restored=type(e).restore(cp);restore=time.perf_counter()-start
        assert restored.checkpoint()==cp
        start=time.perf_counter();report=(c1_audit if a.lane=='reference' else audit)(e.world.journal(),e.access.checkpoint());audit_time=time.perf_counter()-start
        if a.lane in ('reference','c2'):
            action=next(p.object for p in e.world.resolve(out['after']).facet(Account).content if p.relation=='u5.action')
            assert action=='use'; outcome=action; attempts=3;completed=report['c1_movements'];self_completed=0;steps=report['c1_semantic_steps']
        elif a.lane=='panel':
            outcome=codec.encode(consequence(e,out,name));attempts=report['c2_attempts'];completed=report['c2_completed'];self_completed=report['c2_self_completed'];steps=report['c2_semantic_steps']
        else:
            outcome=codec.encode(data(e,out['downstream'])['reachable']);attempts=report['c2_attempts'];completed=report['c2_completed'];self_completed=report['c2_self_completed'];steps=report['c2_semantic_steps']
        rows.append(dict(route=name,polarity=face,active_wall_seconds=wall,active_cpu_seconds=cpu,restore_seconds=restore,audit_seconds=audit_time,
            memory=memory,engine_checkpoint_bytes=len(cp.encode()),world_checkpoint_bytes=len(world.encode()),compressed_world_bytes=len(gzip.compress(world.encode(),mtime=0)),
            movement_attempts=attempts,movement_completions=completed,self_completions=self_completed,semantic_steps=steps,
            modeled_total_work=report['charged_energy'],modeled_active_work=before-after,outcome=outcome,exact_restore=True,audit_passed=report['passed']))
    totals={k:sum(r[k] for r in rows) for k in ('active_wall_seconds','active_cpu_seconds','restore_seconds','audit_seconds','engine_checkpoint_bytes','world_checkpoint_bytes','compressed_world_bytes','movement_attempts','movement_completions','self_completions','semantic_steps','modeled_total_work','modeled_active_work')}
    memory=None if a.mode!='trace' else dict(peak_bytes=max(r['memory']['peak_bytes'] for r in rows),retained_bytes=sum(r['memory']['retained_bytes'] for r in rows),resolve_calls=sum(r['memory']['resolve_calls'] for r in rows),unique_refs_sum=sum(r['memory']['unique_refs'] for r in rows))
    print(json.dumps(dict(lane=a.lane,mode=a.mode,inactive=a.inactive,shape=a.shape,nodes=a.nodes,
        **totals,memory=memory,outcomes=[r['outcome'] for r in rows],cases=rows,exact_restore=True,audit_passed=True)),flush=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path);p.add_argument('--worker',action='store_true');p.add_argument('--lane',default='panel',choices=('reference','c2','panel','scale'))
    p.add_argument('--shape',default='shared');p.add_argument('--inactive',type=int,default=100);p.add_argument('--nodes',type=int,default=2);p.add_argument('--mode',default='time');a=p.parse_args()
    if a.worker:return worker(a)
    a.out.mkdir(parents=True,exist_ok=False)
    paths=sorted({*ROOT.glob('hle_unified/*.py'),*ROOT.glob('tests_c*/*.py'),*ROOT.glob('tools/*c2*.py'),ROOT/'reference/c1_crux_execution.py',ROOT/'contracts/C2_Protocol_v1.json'})
    manifest={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in paths}
    (a.out/'execution_source.json').write_text(json.dumps(manifest,indent=2)+'\n')
    samples=[]
    jobs=[]
    for i in range(5):
        for lane in ('reference','c2'):jobs.append((lane,'shared',100,2,'time',i))
    for shape in ('shared','unique'):
        for inactive in (100,1000,10000):
            jobs.extend(('panel',shape,inactive,2,mode,i) for i,mode in enumerate(('time','time','time','trace')))
    for nodes in (2,8,16):jobs.extend(('scale','shared',100,nodes,mode,i) for i,mode in enumerate(('time','time','time','trace')))
    for lane,shape,inactive,nodes,mode,i in jobs:
        key=f'{lane}-{shape}-{inactive}-{nodes}-{mode}-{i}'
        command=[sys.executable,__file__,'--worker','--lane',lane,'--shape',shape,'--inactive',str(inactive),'--nodes',str(nodes),'--mode',mode]
        done=subprocess.run(command,capture_output=True,text=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
        (a.out/(key+'.stdout.json')).write_text(done.stdout);(a.out/(key+'.stderr.txt')).write_text(done.stderr)
        if done.returncode:raise RuntimeError('failed measurement '+key)
        samples.append(json.loads(done.stdout)); print('measured '+key,flush=True)
    rows=[]
    for lane,shape,inactive,nodes in dict.fromkeys((s['lane'],s['shape'],s['inactive'],s['nodes']) for s in samples):
        found=[s for s in samples if (s['lane'],s['shape'],s['inactive'],s['nodes'])==(lane,shape,inactive,nodes)]
        timed=[s for s in found if s['mode']=='time'];traced=next((s for s in found if s['mode']=='trace'),None)
        row={k:timed[0][k] for k in ('lane','shape','inactive','nodes','movement_attempts','movement_completions','self_completions','semantic_steps','modeled_total_work','modeled_active_work','outcomes','engine_checkpoint_bytes','world_checkpoint_bytes','compressed_world_bytes')}
        row.update(samples=len(timed),**{'median_'+k:statistics.median(s[k] for s in timed) for k in ('active_wall_seconds','active_cpu_seconds','restore_seconds','audit_seconds')},memory=traced['memory'] if traced else None)
        rows.append(row)
    reference,adapted=rows[:2];ratio=adapted['median_active_wall_seconds']/reference['median_active_wall_seconds']
    fixed=[s for s in samples if s['lane']=='panel'];fixed_trace=[r for r in rows if r['lane']=='panel']
    invariant=lambda s:json.dumps([s[k] for k in ('movement_attempts','movement_completions','self_completions','semantic_steps','modeled_total_work','modeled_active_work','outcomes')],sort_keys=True)
    unchanged=all(hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==sha for f,sha in manifest.items())
    passed=(ratio<=1.5 and invariant(reference)==invariant(adapted) and len({invariant(s) for s in fixed})==1
        and len({(r['memory']['resolve_calls'],r['memory']['unique_refs_sum']) for r in fixed_trace})==1 and unchanged)
    result=dict(passed=passed,source_unchanged=unchanged,c1_ratio=ratio,tolerance=1.5,rows=rows,
        workers=len(samples),timed_samples=sum(s['mode']=='time' for s in samples),trace_workers=sum(s['mode']=='trace' for s in samples),
        python=sys.version,platform=platform.platform(),
        accounting='Panel rows sum eight independent engine cases. Allocation peak is the largest case; retained allocation and checkpoint bytes are sums. Active work includes fixture-authored inputs and actual exchange/consumers, excludes engine setup, checkpoint creation, restore and audit. Eight effects are established by the separate causal-pair witnesses; timing workers repeat the healthy cases.')
    (a.out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(passed=passed,c1_ratio=ratio,workers=len(samples))),flush=True)
    if not passed:raise SystemExit(1)

if __name__=='__main__':main()
