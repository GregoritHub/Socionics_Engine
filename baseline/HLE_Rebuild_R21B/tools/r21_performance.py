"""Frozen active/inactive benchmark on the full R20/R21 runtime."""
import argparse,gc,gzip,json,platform,statistics,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from r21_workloads import fresh
from r21_reference import resource_audit
from r21_evidence import save
from hle.closure import ClosureWorld
from hle.clearance_reference import compare
from hle.clearance_demo import physical,finish_order
from hle.individuation_demo import make_offer,do
from hle.world_records import Credit,Tick
from hle.contracts import WorkStatus

class Counted(dict):
    def __init__(self,base):super().__init__(base);self.visits=0
    def __getitem__(self,k):self.visits+=1;return super().__getitem__(k)
    def get(self,k,d=None):self.visits+=1;return super().get(k,d)
    def __contains__(self,k):self.visits+=1;return super().__contains__(k)

class NoScan(list):
    def __iter__(self):raise AssertionError('participant work scanned inactive journal')
    def __reversed__(self):raise AssertionError('participant work reversed inactive journal')

def queue_snapshot(w):
    return {'open_circuit_orders':sum(not o.closed for o in w._circuit_orders.values()),
        'unread_autonomy_observations':{a.key:max(0,len(w._inboxes[a])-w.autonomy_state(a).cursor) for a in w.config.actors},
        'pending_autonomy_commands':{a.key:w.autonomy_state(a).pending is not None for a in w.config.actors},
        'pending_memory_patches':{a.key:len(w.autonomy_state(a).patches) for a in w.config.actors},
        'note':'Unread notifications are retained separately from the 32 explicitly scheduled circuit work items; not counted as completed autonomous processing.'}

def online_timers(w):
    clock={'seconds':0.,'calls':0}
    for monitor in (w.shell_monitor,w.account_monitor,w.clearance_monitor):
        original=monitor.feed
        def feed(*args,_original=original,**kwargs):
            start=time.perf_counter()
            try:return _original(*args,**kwargs)
            finally:clock['seconds']+=time.perf_counter()-start;clock['calls']+=1
        monitor.feed=feed
    return clock

def measure(base,kind,n,out,spec):
    w=fresh(base)
    for tx in base._journal[1:]:w.execute(tx.command)
    for a in w.config.actors:w.execute(Credit('benchmark:'+a.key,a,100000000,100000000,'separate performance allocation'))
    item=w.clearance_monitor.original_item
    actor=w.config.actors[0]
    for i in range(n):
        if kind=='tick':w.execute(Tick(f'inactive:{i}'))
        else:physical(w,actor,'inspect',(item,))
    queues_before=queue_snapshot(w)
    start=time.perf_counter();cp=w.checkpoint();checkpoint_seconds=time.perf_counter()-start
    raw_bytes=len(cp.encode())
    start=time.perf_counter();compressed=gzip.compress(cp.encode(),mtime=0);archive_seconds=time.perf_counter()-start
    archive_bytes=len(compressed);del compressed
    start=time.perf_counter();r=ClosureWorld.restore(cp);restore_seconds=time.perf_counter()-start
    exact=r._journal==w._journal and r.closure_report()==w.closure_report()
    del r,cp;gc.collect()
    start=time.perf_counter();raw=compare(w);reference_seconds=time.perf_counter()-start
    w._records=Counted(w._records);w._origins=Counted(w._origins)
    observer=online_timers(w);samples=[]
    for batch in range(spec['warmup_runs']+spec['measured_runs']):
        keys=[]
        for i in range(spec['active_work_items']):
            f=make_offer(w,f'profile:{batch}:{i}','si',held=True,all_traps=True)
            w.execute(f);do(w,f.key,f.partner,'menu');keys.append(f.key)
        active_before=sum(not o.closed for o in w._circuit_orders.values())
        # Original R20 has no unfinished individual work orders.
        if active_before!=32:raise AssertionError('active workload is not exactly 32')
        w._journal=NoScan(w._journal)
        before=(w._records.visits+w._origins.visits,observer['seconds'],len(w._journal))
        t=time.perf_counter()
        for key in keys:do(w,key,actor,'choose')
        total=time.perf_counter()-t
        assessed=observer['seconds']-before[1]
        visits=w._records.visits+w._origins.visits-before[0]
        w._journal=w._journal[:]
        published=sum(w._circuit_orders[k].chosen is not None for k in keys)
        if published!=32:raise AssertionError('unpublished eligible choice')
        # Finish all 32 before the next batch. This work is measured separately
        # from the choice-tick sample and remains in the retained journal.
        t=time.perf_counter()
        for key in keys:finish_order(w,key)
        drain=time.perf_counter()-t
        outstanding=sum(not o.closed for o in w._circuit_orders.values())
        if outstanding:raise AssertionError('eligible work was discarded')
        row={'batch':batch,'warmup':batch<spec['warmup_runs'],'total_seconds':total,
             'participant_seconds':total-assessed,'online_assessment_seconds':assessed,
             'affected_record_visits':visits,'active_before':active_before,
             'published':published,'unfinished_after_drain':outstanding,'drain_seconds':drain,
             'no_journal_scan':True}
        samples.append(row)
    measured=[r for r in samples if not r['warmup']]
    result={'kind':kind,'inactive_history':n,'samples':samples,
        'median_seconds':statistics.median(r['total_seconds'] for r in measured),
        'median_participant_seconds':statistics.median(r['participant_seconds'] for r in measured),
        'median_assessment_seconds':statistics.median(r['online_assessment_seconds'] for r in measured),
        'median_affected_record_visits':statistics.median(r['affected_record_visits'] for r in measured),
        'checkpoint_bytes':raw_bytes,'checkpoint_seconds':checkpoint_seconds,
        'archive_bytes':archive_bytes,'archive_seconds':archive_seconds,
        'restore_seconds':restore_seconds,'exact_restore':exact,'offline_reference_seconds':reference_seconds,
        'reference_passed':raw['passed'],'resources':resource_audit(w,allow_credits=True)}
    result['queues_before']=queues_before;result['queues_after']=queue_snapshot(w)
    save(out/f'{kind}_{n}.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('samples','resources')}),flush=True)
    del w;gc.collect();return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'evidence/r21/performance');a=p.parse_args()
    spec=json.loads((ROOT/'docs/r12/acceptance_v1.json').read_text())['performance'];a.out.mkdir(parents=True,exist_ok=True)
    with gzip.open(ROOT/'evidence/r20/panel/continued_r19.checkpoint.json.gz','rt') as f:base=ClosureWorld.restore(f.read())
    rows=[];gates=[]
    for kind in ('tick','completed_inspection'):
        group=[]
        for n in spec['inactive_history_sizes']:
            row=measure(base,kind,n,a.out,spec);rows.append(row);group.append(row)
        first,last=group[0],group[-1]
        ratios=[b['checkpoint_bytes']/a['checkpoint_bytes'] for a,b in zip(group,group[1:])]
        g={'kind':kind,'median_tick_ratio':last['median_seconds']/first['median_seconds'],
           'affected_visits_ratio':last['median_affected_record_visits']/first['median_affected_record_visits'],
           'checkpoint_ratios_per_10x':ratios}
        g['passed']=g['median_tick_ratio']<=2 and g['affected_visits_ratio']<=2 and max(ratios)<=25
        gates.append(g)
    result={'schema':'r21-performance-v1','gates':gates,'rows':rows,'spec':spec,
        'passed':all(g['passed'] for g in gates) and all(r['exact_restore'] and r['reference_passed'] and r['resources']['passed'] for r in rows),
        'python':sys.version,'platform':platform.platform(),
        'scope':'32 paid choices on full continuing world, with completion between batches; no claim that every possible scheduler operation has this cost'}
    save(a.out/'summary.json',result);print(json.dumps({'gates':gates,'passed':result['passed']}),flush=True)
    return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
