"""Exact original-checkpoint continuation, sustained diagnostic and replay cuts."""
import gc,gzip,hashlib,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from r21_workloads import bounded,BudgetStop,opportunity,renewal_case,fresh
from r21_reference import renewal_audit,resource_audit
from r21_evidence import save,trace
from hle.closure import ClosureWorld
from hle.closure_reference import compare
from hle.clearance_demo import borrow,defensive_return
from hle.clearance_records import WithdrawEvidence,ClearanceBoundary
from hle.conversion_records import ConversionTransaction
from hle.closure_records import ClosureResult
from hle.world_records import Credit,Tick
from hle.contracts import WorkStatus

OUT=ROOT/'evidence/r21/continuation'

def copied(base):
    w=fresh(base)
    for tx in base._journal[1:]:
        w.execute(tx.command)
        if w._journal[-1]!=tx:raise AssertionError('original prefix changed')
    return w

def checkpoint(name,w,next_tx=None):
    began=time.perf_counter();cp=w.checkpoint()
    with gzip.open(OUT/(name+'.checkpoint.json.gz'),'wt') as f:f.write(cp)
    r=ClosureWorld.restore(cp)
    exact=r.checkpoint()==cp
    if next_tx is not None:
        r.execute(next_tx.command);next_exact=r._journal[-1]==next_tx
    else:
        cmd=Tick('r21:restore-probe:'+name);w.execute(cmd);r.execute(cmd)
        next_exact=r._journal==w._journal
    result={'name':name,'transactions':len(r._journal),'checkpoint_bytes':len(cp.encode()),
            'sha256':hashlib.sha256(cp.encode()).hexdigest(),'exact_restore':exact,
            'exact_next_transaction':next_exact,'seconds':time.perf_counter()-began}
    save(OUT/(name+'.replay.json'),result)
    print(json.dumps(result),flush=True);del r,cp;gc.collect();return result

def replay_cuts(base):
    targets={};seen=set()
    for i,tx in enumerate(base._journal):
        names=[]
        if isinstance(tx,ConversionTransaction) and tx.event.outcome==WorkStatus.COMPLETED:
            if tx.job.operation in ('release','context','reorganize','try','reflect','retain'):
                names.append('phase_'+tx.job.operation)
        if tx.event.outcome==WorkStatus.PARTIAL:names.append('partial_job')
        if any(m.ref.revision>1 for m in tx.memories):names.append('memory_revision')
        if isinstance(tx.command,ClearanceBoundary) and tx.command.operation=='close':
            if tx.command.case=='':
                # Boundary close does not carry its case; the thirteenth close
                # is the first established clearance in this preserved trace.
                count=sum(isinstance(t.command,ClearanceBoundary) and t.command.operation=='close' for t in base._journal[:i+1])
                if count==13:names.append('clearance')
        for r in getattr(tx,'extra',()):
            if isinstance(r,ClosureResult):names.append('shared_depth_'+str(r.depth))
        for name in names:
            if name not in seen:targets.setdefault(i,[]).append(name);seen.add(name)
    w=fresh(base);rows=[]
    for i,tx in enumerate(base._journal[1:],1):
        w.execute(tx.command)
        if w._journal[-1]!=tx:raise AssertionError('historical replay mismatch')
        if i in targets:
            for name in targets[i]:rows.append(checkpoint(name,w,base._journal[i+1] if i+1<len(base._journal) else None))
    return rows

def continue_world(base,name,credit=0):
    w=copied(base);start=len(w._journal);rows=[];stop=None
    if credit:
        for a in w.config.actors:w.execute(Credit('r21:diagnostic:'+a.key,a,credit,credit,'explicit supplemental diagnostic allocation; excluded from frozen panel'))
    try:
        with bounded(w):
            for n in range(100):rows.append(opportunity(w,renewal_case(17,n),17,n))
    except BudgetStop as e:stop=str(e)
    audit=renewal_audit(w,rows);reference=compare(w)
    result={'name':name,'source_prefix_transactions':start,'prefix_unchanged':w._journal[:start]==base._journal,
        'new_allocation_per_actor':credit,'frozen_panel_credit':False,'resource_stop':stop,
        'current_clearance':w.clearance_report()['status'],'sustained':audit,
        'independent':reference,'resources':resource_audit(w,allow_credits=True),
        'trace':trace(OUT/(name+'.transactions.jsonl.gz'),w)}
    result['passed']=result['prefix_unchanged'] and audit['passed'] and reference['passed'] and result['resources']['passed']
    save(OUT/(name+'.json'),result)
    print(json.dumps({'name':name,'eligible':audit['eligible'],'changes':audit['demand_changes'],'status':result['current_clearance'],'resource_stop':stop,'passed':result['passed']}),flush=True)
    return w,result

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    with gzip.open(ROOT/'evidence/r20/panel/continued_r19.checkpoint.json.gz','rt') as f:source=f.read()
    base=ClosureWorld.restore(source)
    origin={'sha256':hashlib.sha256(source.encode()).hexdigest(),'transactions':len(base._journal),
            'exact_restore':base.checkpoint()==source,'independent':compare(base)}
    save(OUT/'original.json',origin);del source;gc.collect()
    cuts=replay_cuts(base)
    w,fixed=continue_world(base,'original_budget');fixed_cp=checkpoint('original_budget_stop',w)
    del w;gc.collect()
    w,supplemental=continue_world(base,'supplemental_horizon',2000000)
    cp=checkpoint('supplemental_horizon',w)
    recurrence=[];item=w.clearance_monitor.original_item
    with bounded(w):
        for n in range(3):
            borrow(w,item,w.config.actors[1]);defensive_return(w,item)
            r=w.clearance_report();recurrence.append({'engagement':n+1,'status':r['status'],'counts':r['recurrence_counts'],'independent':compare(w)['passed']})
    rec_cp=checkpoint('recurrence',w)
    save(OUT/'recurrence.json',{'rows':recurrence,'checkpoint':rec_cp,'history_preserved':any(h['status']=='cleared_in_scope' for h in w.clearance_report()['history'])})
    trace(OUT/'recurrence.transactions.jsonl.gz',w);del w;gc.collect()
    w=copied(base);actor=w.config.actors[0];cap=w._aspect_caps[actor,'si']
    w.execute(WithdrawEvidence('r21:nested-withdrawal',w._origins[cap.practice],'withdraw native child practice origin'))
    nested={'report':w.closure_report(),'independent':compare(w),'checkpoint':checkpoint('nested_invalidation',w)}
    nested['passed']=all(r['current_status']=='invalidated' for r in nested['report']['claims']) and nested['independent']['passed']
    save(OUT/'nested_invalidation.json',nested);trace(OUT/'nested_invalidation.transactions.jsonl.gz',w)
    summary={'schema':'r21-continuation-v1','original':origin,'cuts':cuts,'original_budget':{k:fixed[k] for k in ('passed','resource_stop','current_clearance')},
        'original_budget_eligible':fixed['sustained']['eligible'],'original_budget_checkpoint':fixed_cp,
        'supplemental_eligible':supplemental['sustained']['eligible'],'supplemental_passed':supplemental['passed'],
        'supplemental_checkpoint':cp,'recurrence':recurrence,'recurrence_checkpoint':rec_cp,'nested_passed':nested['passed'],
        'replay_passed':origin['exact_restore'] and all(r['exact_restore'] and r['exact_next_transaction'] for r in cuts+[fixed_cp,cp,rec_cp,nested['checkpoint']]),
        'scope':'supplemental horizon is diagnostic; it cannot pass the fixed-budget release gate'}
    save(OUT/'summary.json',summary);print(json.dumps({k:v for k,v in summary.items() if k not in ('original','cuts')}),flush=True)
    return 0 if summary['replay_passed'] and supplemental['passed'] and nested['passed'] and recurrence[-1]['status']=='recurrent' else 1
if __name__=='__main__':raise SystemExit(main())
