"""Frozen R16B runtime panel; R16A fixture evidence remains preserved."""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from hle.reconciliation_demo import case,world
from hle.reconciliation import ReconciliationWorld
from hle.reconciliation_records import ReconciliationPolicy,AccountTransaction
from hle.reconciliation_reference import compare
from hle.compensation_evaluation import evaluate
from hle.compensation_demo import run,introduce
from hle.shell_assessment import JointShellAssessment,json_value
from hle.world_records import Tick,Credit
from hle.codec import loads,dumps


def write(out,name,data):
    (out/name).write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')


def prefix(w,n):
    cp=loads(w.checkpoint())
    return ReconciliationWorld.restore(dumps(replace(cp,base=replace(cp.base,journal=cp.base.journal[:n]))))


def counts(w):
    signs={s:0 for s in ('premature_translation','forced_placement','new_defensive_structure','residual_fragmentation','foreclosure')}
    for g in w.joint_report()['groups']:
        for s in signs:signs[s]+=g['signs'][s]['positive']
    return signs


def panel(out):
    out.mkdir(parents=True,exist_ok=True);timings={};runs={};worlds={};checks={}
    variants=[('maintained',{}),('ordinary',{'gated_history':False}),
      ('timely',{'account_policy':ReconciliationPolicy(distinction_unit=0)}),
      ('scaffold',{'account_policy':ReconciliationPolicy(scaffold_unit=0)}),
      ('open',{'account_policy':ReconciliationPolicy(cross_check=True)}),
      ('initiated',{'account_policy':ReconciliationPolicy(guard_unit=999)}),
      ('refusal',{'account_policy':ReconciliationPolicy(willing=False)})]
    for name,args in variants:
        at=time.perf_counter();w,setup=case(**args);worlds[name]=w
        audit=evaluate(w,setup);ref=compare(w);report=w.joint_report();cp=w.checkpoint()
        restored=ReconciliationWorld.restore(cp)
        exact=restored.checkpoint()==cp and restored.joint_report()==report
        data={'setup':setup,'joint':report,'independent':ref,'accounting':audit,'exact_restore':exact,
              'positive_engagements':counts(w),'checkpoint_bytes':len(cp.encode()),'checkpoint_sha256':hashlib.sha256(cp.encode()).hexdigest()}
        runs[name]=data;write(out,name+'.json',data)
        if name=='maintained':
            (out/'maintained.checkpoint.json').write_text(cp)
            write(out,'maintained.traces.json',json_value(w.account_monitor.traces))
        timings[name]=round(time.perf_counter()-at,6)
        print(json.dumps({'case':name,'positive':data['positive_engagements'],'reference':ref['passed'],'exact':exact}),flush=True)
    main=worlds['maintained'];small,_=case(history=1,renewals=1)
    boundaries=[1];seen=set()
    for i,tx in enumerate(small._journal):
        if type(tx) is AccountTransaction and tx.event.outcome.value=='completed' and tx.job.operation not in seen:
            seen.add(tx.job.operation);boundaries.append(i+1)
    boundaries.append(len(small._journal));continuation=[]
    for n in sorted(set(boundaries)):
        v=prefix(small,n);cp=v.checkpoint();again=ReconciliationWorld.restore(cp)
        equal=again.checkpoint()==cp
        next_equal=True
        if n<len(small._journal):
            again.execute(small._journal[n].command);next_equal=again._journal[-1]==small._journal[n]
        continuation.append({'prefix_events':n,'checkpoint_equal':equal,'next_event_equal':next_equal})
    partial=[]
    for name in ('summarize','integrate','wrapper','guard'):
        i=next(i for i,t in enumerate(small._journal) if type(t) is AccountTransaction and t.job.operation==name)
        v=prefix(small,i);cmd=replace(small._journal[i].command,work_limit=1);v.execute(cmd)
        no_output=v._journal[-1].state is None and not v._journal[-1].parts
        r=ReconciliationWorld.restore(v.checkpoint());nxt=replace(cmd,command_id='panel:partial:'+name)
        v.execute(nxt);r.execute(nxt)
        partial.append({'operation':name,'no_early_output':no_output,'exact_continuation':v.checkpoint()==r.checkpoint()})
    write(out,'continuation.json',{'prefixes':continuation,'partial':partial})
    inactive=[]
    index=next(i for i,t in enumerate(small._journal) if type(t) is AccountTransaction and t.job.operation=='summarize')
    for n in (0,100,1000):
        v=prefix(small,index)
        for k in range(n):v.execute(Tick('inactive:'+str(k)))
        class IndexedOnly(list):
            def __iter__(self):raise AssertionError('ordinary operation scanned journal')
        v._journal=IndexedOnly(v._journal)
        v.execute(small._journal[index].command)
        inactive.append({'quiet_ticks':n,'required':v._journal[-1].job.plan.required,
                         'charged':sum(w.completed_units for w in v._journal[-1].works),'closed_engagements':len(v.account_monitor.traces)})
    write(out,'inactive.json',inactive)
    sensitivity=[]
    for threshold in (2,3,5):
        g=JointShellAssessment(threshold)
        for t in main.account_monitor.traces:g.append(t)
        sensitivity.append({'threshold':threshold,'signs':g.report()['signs']})
    write(out,'sensitivity.json',sensitivity)
    # Exact current-wallet match before renewed optional opportunities.
    pair=[world(history=3,renewals=1,gated_history=x) for x in (True,False)]
    for w in pair:
        run(w)
        for i in range(3):introduce(w,i);run(w)
    targets={a.key:(max(w._wallets[w.config.actors[j]].energy for w in pair),max(w._wallets[w.config.actors[j]].time for w in pair)) for j,a in enumerate(pair[0].config.actors)}
    matched=[]
    for number,w in enumerate(pair):
        for a in w.config.actors:
            e,t=targets[a.key];b=w._wallets[a]
            w.execute(Credit('match:'+a.key,a,e-b.energy,t-b.time,'exact controlled current-wallet match'))
        before={a.key:[w._wallets[a].energy,w._wallets[a].time] for a in w.config.actors}
        introduce(w,3);run(w)
        last=w.account_monitor.traces[-1];g=JointShellAssessment(1);g.append(last)
        matched.append({'history':'gated' if number==0 else 'direct','wallets_before':before,'signs':g.report()['signs'],'independent':compare(w),'accounting_errors':evaluate(w)['oracle_errors']})
    write(out,'matched_resources.json',matched)
    checks['R16.1']=all(n==3 for n in runs['maintained']['positive_engagements'].values()) and not any(runs['ordinary']['positive_engagements'].values()) and all(
        runs[name]['positive_engagements'][sign]==0 for name,sign in [('timely','premature_translation'),('timely','forced_placement'),('scaffold','new_defensive_structure'),('open','residual_fragmentation'),('initiated','foreclosure')])
    checks['R16.2']=all(r['independent']['passed'] and not r['accounting']['oracle_errors'] and not r['joint']['errors'] for r in runs.values())
    checks['R16.3']=all(t.increase is not None and t.increase.greater and any(op.name=='construct' and op.tick>t.increase.tick for op in t.operations) for t in main.account_monitor.traces)
    checks['exact_replay']=all(r['exact_restore'] for r in runs.values()) and all(x['checkpoint_equal'] and x['next_event_equal'] for x in continuation) and all(x['no_early_output'] and x['exact_continuation'] for x in partial)
    checks['inactive']=len({r['required'] for r in inactive})==1 and len({r['charged'] for r in inactive})==1 and all(r['closed_engagements']==0 for r in inactive)
    checks['matched_current_resources']=matched[0]['wallets_before']==matched[1]['wallets_before'] and all(s['positive']==1 for s in matched[0]['signs'].values()) and all(s['positive']==0 for s in matched[1]['signs'].values()) and all(r['independent']['passed'] and not r['accounting_errors'] for r in matched)
    checks['refusal_unassessed']=all(all(s['positive']==0 and s['negative']==0 for s in g['signs'].values()) for g in runs['refusal']['joint']['groups'])
    checks['frozen_acceptance']=hashlib.sha256((ROOT/'docs/r12/acceptance_v1.json').read_bytes()).hexdigest()=='91c7ca3b79cfa5b455268ff0bb497defdce33e91d808e42f14c0c01f16291c1b'
    summary={'schema':'r16-runtime-panel-v1','gates':checks,'passed':all(checks.values()),'positive_engagements':{n:r['positive_engagements'] for n,r in runs.items()},
        'work_units':{n:r['accounting']['logical_work'] for n,r in runs.items()},'events':{n:r['accounting']['events'] for n,r in runs.items()},
        'physical_returns':{n:r['accounting']['correct_optional_endpoints'] for n,r in runs.items()},'parent_R16_complete':all(checks.values()),'remaining_parent_milestones':5 if all(checks.values()) else 6}
    write(out,'summary.json',summary);write(out,'timings.json',timings)
    print(json.dumps(summary),flush=True)
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'evidence/r16b/panel');args=p.parse_args()
    raise SystemExit(0 if panel(args.out.resolve())['passed'] else 1)
