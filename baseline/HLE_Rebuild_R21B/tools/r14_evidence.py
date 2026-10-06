"""Run the frozen R14 finite-domain panel. This is evaluation, not participant policy."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import platform
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from hle.autonomy_demo import world,run,report
from hle.autonomy_evaluation import audit,reference_demands,all_prefixes,fresh_schedulers,positive
from hle.autonomy_records import WorkshopCommand,AutonomousTransaction
from hle.autonomy import AutonomousWorld
from hle.autonomy_policy import decide
from hle.model_a import TYPES,stack
from hle.world_records import Tick,Credit,Attempt,TRANSFER
from hle.contracts import ActionRequest,WorkStatus
from tests_r14.helpers import actors_items,advance_until,next_selection,autonomous_only,until_used,ever_families


def write(p,value):
    p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2)+'\n');tmp.replace(p)


def checkpoint(out,name,w):
    raw=w.checkpoint().encode();path=out/(name+'.json.gz');path.write_bytes(gzip.compress(raw,mtime=0))
    restored=AutonomousWorld.restore(raw.decode())
    if restored.checkpoint()!=raw.decode():raise AssertionError('checkpoint mismatch '+name)
    return {'file':path.name,'bytes_uncompressed':len(raw),'events':len(w._journal),'sha256_uncompressed':hashlib.sha256(raw).hexdigest(),'exact_restore':True}


def observation_controls():
    w=world();a,b,t,p=actors_items(w);advance_until(w,lambda x:next_selection(x,a));other=AutonomousWorld.restore(w.checkpoint())
    w.execute(Attempt('hidden','hidden',ActionRequest(b,TRANSFER,(t,a),())));other.execute(Tick('same-time-control'))
    different=w.truth.current_fact(t,'owned_by',w.config.context).object!=other.truth.current_fact(t,'owned_by',other.config.context).object
    views=w.local_view(a)==other.local_view(a);choices=decide(w.local_view(a),'same')==decide(other.local_view(a),'same')
    # Clone before decision so the second intervention compares fresh direct observation.
    visible=[AutonomousWorld.restore(x.checkpoint()) for x in (w,other)]
    w.autonomy_step(a);other.autonomy_step(a)
    actual=w.autonomy_state(a)==other.autonomy_state(a) and w.own_demands(a)==other.own_demands(a)
    for x in visible:
        x.execute(WorkshopCommand('look','look',a,'inspect',(t,)));autonomous_only(x,a)
    used=[any(tx.event.action=='r14.use' and tx.command.actor==a for tx in x._journal) for x in visible]
    result={'hidden_ownership_differs':different,'complete_local_views_equal':views,'pure_choices_equal':choices,'paid_actual_decisions_equal':actual,
        'after_visible_inspection_use_selected':used,'uninformed_owner_case_waiting':visible[1].autonomy_state(a).decision.kind=='waiting'}
    result['passed']=all((different,views,choices,actual,used==[True,False],result['uninformed_owner_case_waiting']))
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'evidence/r14/panels');args=p.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    (out/'summary.json').unlink(missing_ok=True)
    protocol=json.loads((ROOT/'docs/r14/Protocol_R14_v1.json').read_text());rows=[];saved=[];times=[]
    for tim in TYPES:
        for seed in protocol['evaluation']['evaluation_seeds']:
            started=time.perf_counter();w=world(tim=tim,seed=seed);scheduling=run(w,horizon=protocol['evaluation']['horizon'])
            measured=audit(w);reference=reference_demands(w);ok=positive(w) and not scheduling['horizon_exhausted'] and not scheduling['resource_censored']
            fixed=stack(w._profiles[w.config.actors[0]].tim)==stack(tim)
            row={'case':tim+':'+str(seed),'tim':tim,'seed':seed,'passed':ok and fixed,'fixed_stack':list(stack(tim)),
                'trace':report(w,scheduling),'accounting':measured,'reference':reference}
            rows.append(row);times.append({'case':row['case'],'seconds':round(time.perf_counter()-started,6)})
            if tim=='sli' and seed==101:saved.append(checkpoint(out,'positive_sli_101',w))
        print('positive type completed',tim,flush=True)
    write(out/'population.json',rows)
    cases=[('no_wear',{'wear':False},('return_commitment',)),('no_loan',{'borrowed':False},('maintenance',)),
           ('no_due_trigger',{'due':False},('maintenance',)),('refusal',{'may_lend':False},()),('no_tool',{'tool':False},()),
           ('quiet',{'intentions':()},()),('teaching',{'borrowed':False,'native_use':False,'teaching':True},('maintenance',)),
           ('unsupported_teacher',{'borrowed':False,'native_use':False},())]
    controls=[]
    for name,kw,expected in cases:
        w=world(**kw);schedule=run(w);a=w.config.actors[0];found=ever_families(w,a)-{'production'}
        ok=found==set(expected) and not schedule['horizon_exhausted'] and not schedule['resource_censored']
        if name=='quiet':
            before=[(w.autonomy_state(a),w._wallets[a]) for a in w.config.actors]
            for i in range(40):w.execute(Tick('quiet:'+str(i)));run(w)
            ok=ok and before==[(w.autonomy_state(a),w._wallets[a]) for a in w.config.actors]
        if name=='teaching':
            piece=actors_items(w)[3];ok=ok and w.truth.current_fact(piece,'condition',w.config.context).object=='ready'
            saved.append(checkpoint(out,name,w))
        controls.append({'case':name,'config':kw,'expected_generated_consequence_families':list(expected),'found_families':sorted(found),
            'trace':report(w,schedule),'accounting':audit(w),'reference':reference_demands(w),'passed':ok})
    # Counterfactual interventions cancel both effects before participant discovery.
    w=world();a,b,t,piece=actors_items(w);until_used(w)
    w.execute(WorkshopCommand('external-clean','external-clean',a,'clean',(t,)))
    w.execute(WorkshopCommand('external-return','external-return',a,'return',(t,)))
    run(w);absent=not ({'maintenance','return_commitment'} & ever_families(w,a))
    controls.append({'case':'net_reversal_before_discovery','fixture_interventions_explicit':True,'passed':absent,'trace':report(w),'accounting':audit(w),'reference':reference_demands(w)})
    write(out/'effect_controls.json',controls)
    isolated=observation_controls();write(out/'observation_isolation.json',isolated)
    resource=[]
    for budget in (0,1,4,20):
        w=world(energy=budget);s=run(w)
        resource.append({'budget_each_resource':budget,'schedule':s,'demands':len(w._demand_records),'physical_actions':len(report(w)['actions']),
            'accounting':audit(w),'passed':s['resource_censored'] and not w._demand_records and not report(w)['actions']})
    w=world(energy=30,work_limit=2);before=run(w);saved.append(checkpoint(out,'depleted_partial_work',w));r=AutonomousWorld.restore(w.checkpoint())
    for x in (w,r):
        for a in x.config.actors:x.execute(Credit('fund:'+a.key,a,10000,10000,'declared resumption'))
        run(x,horizon=3000)
    resume=w.checkpoint()==r.checkpoint() and positive(w)
    resource.append({'case':'partial_resource_resume','before':before,'accounting':audit(w),'exact_continuation_and_completed':resume,'passed':resume})
    write(out/'resources.json',resource)
    w=world();run(w);print('checking all',len(w._journal),'prefixes',flush=True)
    prefixes=all_prefixes(w);fresh=fresh_schedulers();saved.append(checkpoint(out,'all_prefix_trace',w))
    write(out/'continuation.json',{'same_external_commands':prefixes,'fresh_actor_schedulers':fresh});write(out/'checkpoints.json',saved)
    write(out/'measurements.json',{'python':sys.version,'platform':platform.platform(),'timings':times,
        'scope':'Measured local finite workload; not R21 sustained performance acceptance. Other processes may share host CPU.'})
    result={'schema':'hle-r14-panels-v1','population_cases':len(rows),'population_passed':sum(r['passed'] for r in rows),
        'types':len(TYPES),'seed_variations':protocol['evaluation']['evaluation_seeds'],'effect_controls':len(controls),
        'effect_controls_passed':sum(r['passed'] for r in controls),'observation_isolation':isolated,'resource_cases':len(resource),
        'resource_cases_passed':sum(r['passed'] for r in resource),'checkpoint_prefixes':prefixes['prefixes'],'prefix_cutpoints':prefixes['cutpoints'],
        'fresh_actor_schedulers':fresh['fresh_controllers'],'replayable_checkpoints':len(saved),
        'passed':all(r['passed'] for r in rows+controls+resource) and isolated['passed'] and prefixes['passed'] and fresh['passed'],
        'scope':'Three declared finite demand families, seeded standing motives and primitive repertoire. No externally assigned next task in positive runs. No R15-R21 verdict.',
        'r21_480_cases_executed':0}
    write(out/'summary.json',result);print(json.dumps(result),flush=True)
    return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
