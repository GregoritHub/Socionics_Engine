"""Reproduce R15 causal comparisons, route coverage, replay, and cost witnesses."""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from hle.compensation_demo import case, fund_command, run
from hle.compensation import CompensationWorld
from hle.compensation_records import ReleaseTransaction, ReleaseCommand, DEPENDENCY
from hle.compensation_evaluation import evaluate
from hle.contracts import WorkStatus
from hle.world_records import Credit, Tick
from hle.codec import dumps, loads
from hle.model_a import TYPES


def replay_prefix(w,n):
    b=CompensationWorld(w.config,w.profiles,w.policy,w.agents,w.organization_policies,w.semantic_policy,
                       w.workshop,w.autonomy,release=w.release,reviewers=w.reviewers)
    for tx in w._journal[1:n]:b.execute(tx.command)
    return b


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'evidence/r15/panel');args=p.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    def save(name,obj):
        (out/(name+'.json')).write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')
    results={};worlds={};timings={}
    for name,kwargs in [('maintained',{}),('ordinary',{'gated_history':False}),
                        ('revision_ablation',{'revision_unit':0}),('refusal_reownership',{'refusal':True})]:
        start=time.perf_counter();w,setup=case(**kwargs);timings[name]=time.perf_counter()-start
        report=evaluate(w,setup);save(name,report);worlds[name]=w;results[name]=report
        cp=w.checkpoint();(out/(name+'.checkpoint.json')).write_text(cp)
        restored=CompensationWorld.restore(cp)
        if restored.checkpoint()!=cp:raise AssertionError(name+' continuation mismatch')
        print(json.dumps({'case':name,'events':report['events'],'maintained_optional':report['maintained_optional_engagements'],
                          'correct_optional':report['correct_optional_endpoints'],'accounting_errors':len(report['oracle_errors'])}),flush=True)
    # Normalize all three current wallets at the exact first optional opportunity.
    # This changes no evidence, concept, response history or selected operation.
    matched=[]
    for name in ('maintained','ordinary'):
        full=worlds[name]
        tx=next(t for t in full._journal if type(t) is ReleaseTransaction and t.decision and t.decision.view.item.key=='tool:3')
        w=replay_prefix(full,tx.event.when.tick)
        for actor in w.config.actors:
            wallet=w._wallets[actor];w.execute(Credit('match:'+actor.key,actor,250000-wallet.energy,250000-wallet.time,'matched current resource envelope'))
        balances={a.key:(b.energy,b.time) for a,b in w._wallets.items()}
        w.execute(replace(tx.command,command_id='matched:consider',task_id='matched:consider'))
        d=w._journal[-1].decision;run(w)
        report=evaluate(w)
        matched.append({'case':name,'before_balances':balances,'item':d.view.item.key,'required':d.view.required,
                        'clean':d.view.clean,'owned_due':d.view.owned and d.view.due,'mode':d.selection.mode,
                        'support_count':len(d.view.supports),'oracle_errors':report['oracle_errors']})
    save('matched_resources',matched)
    type_rows=[]
    for tim in TYPES:
        w,s=case(history=1,renewals=1,tim=tim);r=evaluate(w,s)
        type_rows.append({'type':tim,'maintained':r['maintained_optional_engagements'],
                          'correct':r['correct_optional_endpoints'],'logical_work':r['logical_work'],
                          'optional_work':r['optional_release_work_by_item'],'oracle_errors':r['oracle_errors'],
                          'exhausted':any(x['horizon_exhausted'] for x in s['scheduling'])})
    save('types',type_rows)
    carrier_rows=[]
    for name,kw in [('cheaper_lender',{'quotes':(1,4)}),('renamed',{'names':('zeta','alpha','omega')})]:
        w,s=case(history=1,renewals=1,**kw);r=evaluate(w,s)
        carrier_rows.append({'case':name,'choices':r['choices'],'oracle_errors':r['oracle_errors']})
    save('carriers',carrier_rows)
    small,ss=case(history=1,renewals=1);cp=loads(small.checkpoint())
    replay=[]
    prefixes={1,len(cp.journal)}|{i+1 for i,t in enumerate(cp.journal) if type(t) is ReleaseTransaction}
    for n in sorted(prefixes):
        text=dumps(replace(cp,journal=cp.journal[:n]));w=CompensationWorld.restore(text)
        exact=w.checkpoint()==text
        if n<len(cp.journal):w.execute(cp.journal[n].command);exact=exact and w._journal[-1]==cp.journal[n]
        replay.append({'prefix':n,'exact_checkpoint_and_next':exact})
    partial=[]
    for op in ('consider','enact','review','assimilate'):
        target=next(t for t in small._journal if type(t) is ReleaseTransaction and t.command.operator==op and t.event.when.tick>ss['cuts'][1])
        w=replay_prefix(small,target.event.when.tick);cmd=replace(target.command,command_id='partial:'+op,work_limit=1)
        w.execute(cmd);t=w._journal[-1];other=CompensationWorld.restore(w.checkpoint())
        unpublished=not any((t.material,t.treatment,t.concept,t.decision,t.messages))
        for b in (w,other):fund_command(b,replace(cmd,command_id='finish:'+op,work_limit=10000))
        partial.append({'operator':op,'initial_status':t.event.outcome.value,'initial_paid':t.job.paid,
                        'no_early_output':unpublished,'exact_continuation':w.checkpoint()==other.checkpoint()})
    save('replay',{'prefixes':replay,'partial_phases':partial})
    target=next(t for t in small._journal if type(t) is ReleaseTransaction and t.decision and not t.decision.view.required)
    inactive=[]
    class NoIteration(list):
        def __iter__(self):raise AssertionError('ordinary consideration iterated inactive journal')
    for ticks in (0,100,1000):
        w=replay_prefix(small,target.event.when.tick)
        for i in range(ticks):w.execute(Tick('inactive:'+str(i)))
        w._journal=NoIteration(w._journal)
        start=time.perf_counter();w.execute(target.command);elapsed=time.perf_counter()-start
        tx=w._journal[-1]
        inactive.append({'inactive_ticks':ticks,'work':sum(x.completed_units for x in tx.works),
                         'mode':tx.decision.selection.mode,'history_iteration':False})
        timings['inactive_'+str(ticks)]=elapsed
    save('inactive_history',inactive)
    gates={
        'R15.1':results['maintained']['maintained_optional_engagements']==3 and results['ordinary']['maintained_optional_engagements']==0
                  and results['maintained']['final_dependency'] and not results['ordinary']['final_dependency']
                  and matched[0]['before_balances']==matched[1]['before_balances'] and [x['mode'] for x in matched]==['confirm','direct'],
        'R15.2':results['refusal_reownership']['material_history'][-1]['treatment']=='reown'
                  and len({x['carrier'] for x in results['refusal_reownership']['material_history'] if x['treatment']=='externalize'})==2,
        'R15.3':results['maintained']['correct_optional_endpoints']==3
                  and all(x>0 for x in results['maintained']['optional_release_work_by_item'].values())
                  and sum(r['approved'] and r['explicit_optional_evidence'] for r in results['maintained']['responses'])==3,
        'independent_accounting':all(not r['oracle_errors'] for r in results.values()) and all(not r['oracle_errors'] for r in matched),
        'all_type_routes':all(r['maintained']==1 and r['correct']==1 and not r['oracle_errors'] and not r['exhausted'] for r in type_rows),
        'replay':all(r['exact_checkpoint_and_next'] for r in replay) and all(r['no_early_output'] and r['exact_continuation'] for r in partial),
        'inactive_history':len({r['work'] for r in inactive})==1,
    }
    save('timings',timings)
    summary={'schema':'r15-panel-v1','gates':gates,'passed':all(gates.values()),
             'parent_progress':'4/10 if packaged regression gates also pass; six remain',
             'scope':'generated compensation and material treatment only; R16-R21 remain open'}
    save('summary',summary);print(json.dumps(summary),flush=True)
    return 0 if summary['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
