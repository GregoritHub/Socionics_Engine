"""Inspectable U6 native histories, continuations, controls and independent audit."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
sys.dont_write_bytecode=True
from tests_u6.fixtures import *
from hle_unified import codec
from hle_unified.autonomy_audit import audit
from hle_unified.operations import NativeAccess


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',type=Path,required=True)
    out=parser.parse_args().out
    out.mkdir(parents=True,exist_ok=False)
    checks={}
    def save(name,value):
        (out/name).write_text(value if type(value) is str else json.dumps(value,indent=2)+'\n')
    def check(name,value):
        checks[name]=bool(value)
        save('checks.in_progress.json',checks)
        if not value:raise AssertionError(name)
    def bundle(prefix,e,rows):
        save(prefix+'.checkpoint.json',e.checkpoint())
        save(prefix+'.trace.json',rows)
        save(prefix+'.state.json',asdict(e.state(ALICE)))
        raw='\n'.join(codec.dumps(tx) for tx in e.world.journal())+'\n'
        save(prefix+'.transactions.jsonl',raw)
        measured=audit(tuple(codec.loads(line) for line in raw.splitlines()))
        save(prefix+'.raw_audit.json',measured)
        return measured

    e=setup6()
    initial=e.participant_view(ALICE)
    cutoff=len(initial.snapshot.history)
    save('alice.initial.json',initial.bytes())
    rows=drive(e,latency=2)
    normal=bundle('workshop.completed',e,rows)
    check('standing_demand_satisfied',e.state(ALICE).stopped and e.state(ALICE).uses==2)
    check('one_repair_two_uses',normal['anticipated_actions']==3 and normal['physical_commits']==3)
    check('one_stock_quantum_consumed',attrs(e.world.head(STOCK.identity))['consumed']==1)
    check('paid_retention_and_later_use',e.state(ALICE).target==ObjectRef(SAW.identity,4) and len(e.participant_view(ALICE).snapshot.bindings)>3)
    check('hypotheses_never_promoted',all(p.occurrence==Occurrence.HYPOTHETICAL for p in predictions(e)))
    check('needs_do_not_award_skill',not e.participant_view(ALICE).snapshot.acquired)
    check('rest_is_paid',normal['rests']>0 and e.wallet(ALICE)['energy']==e.wallet(ALICE)['time'])
    check('historical_view_exact',e.participant_view(ALICE,through=cutoff).bytes()==initial.bytes())
    check('full_engine_replay_exact',AutonomousEngine.restore(e.checkpoint()).checkpoint()==e.checkpoint())
    check('native_replay_exact',OperationStore.restore(e.world.checkpoint()).checkpoint()==e.world.checkpoint())
    check('access_replay_exact',NativeAccess.restore(e.access.checkpoint()).checkpoint()==e.access.checkpoint())
    check('raw_accounting_passes',normal['passed'])

    a=setup6(prior='serviceable',serviceable=True,wear=2)
    b=setup6(prior='serviceable',serviceable=True,wear=2,anticipation=False)
    ac,bc=first_choice(a),first_choice(b)
    check('anticipation_changes_affordable_action',(ac,bc)==('care','use'))
    check('ablation_has_matched_charges',a.wallet(ALICE)==b.wallet(ALICE))
    for label,x in (('anticipation',a),('ablation',b)):
        trace=drive(x,delivery=False,prefix='execute')
        bundle(label,x,trace)
    check('predicted_alternative_has_actual_effect',attrs(a.world.head(SAW.identity))['wear']==1 and attrs(b.world.head(SAW.identity))['wear']==3)

    s=setup6(prior='serviceable')
    trace=drive(s,delivery=False)
    check('unseen_failed_result_is_not_error',not errors(s) and s.state(ALICE).wait_ref==s.state(ALICE).await_event)
    s.step('settle-wait',ALICE)
    cp=s.checkpoint()
    for i in range(5):s.step('no-delivery-'+str(i),ALICE)
    check('waiting_has_no_poll_growth_or_cost',s.checkpoint()==cp)
    save('surprise.waiting.checkpoint.json',cp)
    restored=AutonomousEngine.restore(cp)
    for x in (s,restored):drive(x,prefix='wake')
    check('wait_continuation_exact',s.checkpoint()==restored.checkpoint())
    surprise=bundle('surprise.completed',s,trace)
    check('received_surprise_triggers_investigation',surprise['surprises']==1 and any(attrs(v).get('reason')=='test_received_surprise' for tx in s.world.journal() for v in tx.versions))
    check('investigation_changes_later_behavior',s.state(ALICE).uses==2 and s.state(ALICE).failures==1)
    check('original_wrong_belief_preserved',s.world.resolve(ref('initial-account')).facet(Account).content[0].object=='serviceable')

    p=setup6(work_limit=1)
    p.step('begin',ALICE);p.step('first-unit',ALICE)
    save('partial.plan.checkpoint.json',p.checkpoint())
    check('unfinished_plan_retained',p.state(ALICE).active_kind=='plan' and p.job_status(ALICE,p.state(ALICE).active)['spent']==1)
    drive(p,delivery=False,prefix='until-forecast',stop_when=lambda x:x.state(ALICE).active_kind=='anticipate')
    p.step('forecast-unit',ALICE)
    save('partial.forecast.checkpoint.json',p.checkpoint())
    clone=AutonomousEngine.restore(p.checkpoint())
    for x in (p,clone):first_choice(x,prefix='finish-forecast')
    check('unfinished_forecast_continues_exactly',p.checkpoint()==clone.checkpoint())
    p.step('action-unit',ALICE)
    save('partial.action.checkpoint.json',p.checkpoint())
    clone=AutonomousEngine.restore(p.checkpoint())
    for x in (p,clone):drive(x,delivery=False,prefix='finish-action')
    check('unfinished_action_continues_exactly',p.checkpoint()==clone.checkpoint())

    f=setup6(hidden_kit_wear=10)
    trace=drive(f)
    failure=bundle('repeated_failure',f,trace)
    check('repeated_failure_changes_strategy',f.state(ALICE).failures==2 and f.state(ALICE).switched and f.state(ALICE).phase=='help_wait')
    check('request_is_paid_and_recipient_must_read',failure['requests']==1 and bool(f.participant_view(BOB).snapshot.pending) and not f.participant_view(BOB).snapshot.particulars)

    # Three situated histories in one shared world, before material execution.
    population=setup6()
    for actor,prior in ((BOB,'serviceable'),(EVE,'uncertain')):
        basics(population,actor);show(population,actor,CUE5)
        show(population,actor,RULE,selectors=(Selector('rule','definition',('facets','0')),))
        seed(population,'prior-'+actor.key,prior,actor=actor)
        population.configure('configure-'+actor.key,AutonomyConfig(actor,ROOM,CUE5,RULE,SAW,
            tool=KIT,stock=STOCK,care=CARE,procedure=REPAIR))
    choices={actor.key:first_choice(population,prefix='actor-'+actor.key,actor=actor) for actor in (ALICE,BOB,EVE)}
    save('three_participants.choices.json',choices)
    save('three_participants.checkpoint.json',population.checkpoint())
    check('different_histories_produce_different_continuations',choices=={'alice':'repair','bob':'use','eve':'inspect'})
    check('forecasts_owned_by_distinct_participants',{p.facet(Account).holder for p in predictions(population)}=={ALICE,BOB,EVE})

    summary={'schema':'hle-u6-witness-v1','checks':checks,'passed':all(checks.values()),
        'check_count':len(checks),'workshop':normal,'surprise':surprise,'repeated_failure':failure,
        'workshop_opportunities':len(rows),'three_participants':choices}
    save('summary.json',summary)
    print(json.dumps({'passed':summary['passed'],'checks':len(checks),'workshop':normal}),flush=True)
    return 0


if __name__=='__main__':raise SystemExit(main())
