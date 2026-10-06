"""A delivery/clock harness; choices are made only by AutonomousEngine.step."""
from dataclasses import asdict
from pathlib import Path
from u14_support import *
from tests_u6 import fixtures as f
from hle_unified.autonomy_audit import audit
from hle_unified import codec


def setup_case(case):
    # Supply resources only in the initial world, before any cognition or work.
    base=f.setup5(tim=case['tim'],budget=case['budget'],prepare=False,hidden_wear=case['hidden_kit_wear'])
    world=f.OperationStore()
    for tx in base.world.journal():
        versions=[]
        for v in tx.versions:
            if v.ref==f.SAW and case['serviceable']:v=f.tool(f.SAW,wear=case['wear'])
            if v.ref==f.CARE:v=f.stock(f.CARE,'care',case.get('care_quantity',2))
            versions.append(v)
        world.create(tx.key,f.WRITER,tuple(versions))
    base=f.CognitiveEngine(world,f.LAW_REF)
    f.basics(base,f.ALICE);f.show(base,f.ALICE,f.ObjectRef(f.BOB,1));f.show(base,f.ALICE,f.CUE5)
    f.show(base,f.ALICE,f.RULE,selectors=(f.Selector('rule','definition',('facets','0')),))
    f.seed(base,'initial-account',case['prior'])
    if case['serviceable']:f.disclose_fields(base,f.ALICE,f.SAW,('wear','max_wear'),'initial-wear')
    if case['offer']:f.help_offer(base,'initial-offer',f.SAW)
    e=f.AutonomousEngine.adopt(base)
    e.configure('configure-alice',f.AutonomyConfig(f.ALICE,f.ROOM,f.CUE5,f.RULE,f.SAW,f.KIT,f.STOCK,f.CARE,
        f.REPAIR,f.BOB,f.SAW2,goal_uses=case['goal_uses'],work_limit=case['work_limit']))
    return e


def run_case(case,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False);write_json(out/'case.json',case)
    e=setup_case(case)
    delivered=set();queued={};rows=[];restores=[];branch=None
    for turn in range(case['horizon']):
        s=e.state(f.ALICE)
        if s.await_event and s.await_event not in delivered:queued.setdefault(s.await_event,turn+case['latency'])
        targets=(e,) if branch is None else (e,branch)
        for event,due in tuple(queued.items()):
            if due<=turn:
                for x in targets:x.deliver_event('release-delivery:'+str(turn)+':'+event.identity.key,event,f.ALICE)
                delivered.add(event);del queued[event]
        if turn==case['offer_at'] and not case['offer']:
            for x in targets:f.help_offer(x,'late-assistance',f.SAW,read=False)
        for x in targets:x.step('release-turn:'+str(turn),f.ALICE)
        s=e.state(f.ALICE)
        rows.append(dict(turn=turn,decision=s.decision,reason=s.reason,phase=s.phase,
            uses=s.uses,failures=s.failures,active_kind=s.active_kind,energy=e.wallet(f.ALICE)['energy']))
        if branch is not None and branch.state(f.ALICE)!=s:raise ValueError('continued participant state differs')
        if turn in case['checkpoints']:
            cp=e.checkpoint()
            if branch is not None and branch.checkpoint()!=cp:raise ValueError('continued engine differs')
            save_gzip(out/('turn-'+str(turn)+'.checkpoint.json.gz'),cp)
            write_json(out/('turn-'+str(turn)+'.delivery_queue.json'),
                dict(queued=[dict(event=codec.encode(k),due=v) for k,v in queued.items()],
                     delivered=[codec.encode(k) for k in sorted(delivered)]))
            t=time.perf_counter();branch=f.AutonomousEngine.restore(cp)
            restores.append(dict(turn=turn,seconds=time.perf_counter()-t,exact=branch.checkpoint()==cp))
    continuation=branch is not None and branch.checkpoint()==e.checkpoint()
    state=e.state(f.ALICE);wallet=e.wallet(f.ALICE)
    success=state.uses>=case['goal_uses'] and state.stopped
    outcome='satisfied' if success else 'budget_censored' if min(wallet['energy'],wallet['time'])==0 else 'named_wait' if state.wait_kind or state.phase=='help_wait' else 'horizon_censored'
    artifact=keep_engine(out,'final',e,audit)
    checks=dict(raw_audits=artifact['accounting']['passed'] and artifact['semantic']['passed'],
                checkpoint_continuation=continuation and len(restores)==len(case['checkpoints']) and all(r['exact'] for r in restores),
                positive_demand=(not case['require_success'] or success),
                no_unobserved_progress=state.uses<=artifact['semantic']['physical_commits'],
                every_opportunity_retained=len(rows)==case['horizon'])
    write_json(out/'trajectory.json',rows)
    result=dict(case=case,passed=all(checks.values()),checks=checks,outcome=outcome,
        final_state=codec.canonical(asdict(state)),restores=restores,artifact=artifact)
    write_json(out/'summary.json',result);return result


def control_case(case,out):
    """Matched first-action controls across types and newly combined history."""
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    a=f.setup6(tim=case['tim'],budget=6000,hidden_kit_wear=0)
    b=f.setup6(tim=case['tim'],budget=6000,hidden_kit_wear=10)
    initial=a.participant_view(f.ALICE).bytes()==b.participant_view(f.ALICE).bytes()
    first_a=f.first_choice(a);first_b=f.first_choice(b)
    isolation=initial and first_a==first_b and a.state(f.ALICE)==b.state(f.ALICE)
    c=f.setup6(tim=case['tim'],budget=6000,prior='serviceable',serviceable=True,wear=2)
    d=f.setup6(tim=case['tim'],budget=6000,prior='serviceable',serviceable=True,wear=2,anticipation=False)
    ca,da=f.first_choice(c),f.first_choice(d)
    checks=dict(hidden_state_isolated=isolation,anticipation_changes_action=ca=='care' and da=='use',
                matched_preaction_cost=c.wallet(f.ALICE)==d.wallet(f.ALICE))
    artifacts={k:keep_engine(out,k,x,audit) for k,x in (('hidden-good',a),('hidden-broken',b),('anticipation',c),('ablation',d))}
    result=dict(case=case,passed=all(checks.values()),checks=checks,artifacts=artifacts)
    write_json(out/'summary.json',result);return result
