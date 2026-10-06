"""Export the complete native conceptual/material circuit and matched controls."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
sys.dont_write_bytecode=True
from tests_u5.fixtures import *
from hle.model_a import TYPES
from hle_unified import codec
from hle_unified.cognitive_routes import progress
from hle_unified.cognitive_audit import audit
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
    e=setup5()
    initial_view=e.participant_view(ALICE)
    cutoff=len(initial_view.snapshot.history)
    save('alice.before.json',initial_view.bytes())
    save('bob.before.json',e.participant_view(BOB).bytes())
    r=request5(e)
    e.start('start-plan',r)
    e.advance('partial-plan',ALICE,r.key,13)
    partial=e.checkpoint()
    save('workshop.partial_concept.checkpoint.json',partial)
    other=CognitiveEngine.restore(partial)
    check('partial_checkpoint_exact',other.checkpoint()==partial)
    check('partial_work_no_plan',not any(b.ref.identity.namespace=='u5.plan' for b in e.participant_view(ALICE).snapshot.bindings))
    for x in (e,other):
        x.advance('rest-plan',ALICE,r.key,1000)
        x.commit('commit-plan',ALICE,r.key)
    check('partial_continuation_exact',e.checkpoint()==other.checkpoint())
    plan=e.job_status(ALICE,r.key)['binding']
    check('assistance_selects_repair',plan_request(e.participant_view(ALICE),plan,'check').kind=='repair')
    save('alice.after_plan.json',e.participant_view(ALICE).bytes())
    before_physical=e.participant_view(ALICE).bytes()
    event=enact(e,plan)
    check('repair_physical_effect',e.world.head(SAW.identity).facet(Material).condition=='serviceable')
    check('one_stock_quantum_consumed',attrs(e.world.head(STOCK.identity))['consumed']==1)
    check('repair_has_paid_plan_lineage',e.job_status(ALICE,'assisted-repair')['concept_plan']==plan)
    check('no_effect_disclosure_without_delivery',e.participant_view(ALICE).bytes()==before_physical)
    save('alice.after_effect_before_delivery.json',e.participant_view(ALICE).bytes())
    obs=receive(e,event,ALICE,'consequence')
    check('read_alone_has_no_revised_account',not any(b.ref.identity.namespace=='u5.account' for b in e.participant_view(ALICE).snapshot.bindings))
    integration=request5(e,'retain','integrate',source=obs)
    e.start('start-retain',integration)
    e.advance('partial-retain',ALICE,'retain',4)
    save('workshop.partial_retention.checkpoint.json',e.checkpoint())
    check('partial_retention_not_published',not any(b.ref.identity.namespace=='u5.account' for b in e.participant_view(ALICE).snapshot.bindings))
    e.advance('rest-retain',ALICE,'retain',1000)
    e.commit('commit-retain',ALICE,'retain')
    retained=e.job_status(ALICE,'retain')['binding']
    account=e.world.resolve(retained).facet(Account)
    check('retained_claim_from_observation',obs in account.sources and account.content[0].object=='serviceable')
    check('exact_repaired_revision_retained',account.referent==ObjectRef(SAW.identity,2))
    check('historical_belief_preserved',e.world.resolve(ref('initial-account')).facet(Account).content[0].object=='damaged')
    check('change_tension_explicit',attrs(e.world.resolve(e.job_status(ALICE,'retain')['field']))['tension']=='revision_change')
    later=think(e,request5(e,'later',source=obs))
    check('later_action_uses_retention',plan_request(e.participant_view(ALICE),later,'check').kind=='use')
    used=enact(e,later,'later-use')
    check('later_use_physically_executed',attrs(e.world.head(SAW.identity))['wear']==1)
    check('no_unearned_procedure_mastery',not e.participant_view(ALICE).can_use(REPAIR,ROOM))
    check('other_actor_not_awarded_account',not e.participant_view(BOB).snapshot.bindings)
    save('alice.completed.json',e.participant_view(ALICE).bytes())
    save('bob.completed.json',e.participant_view(BOB).bytes())
    save('workshop.completed.checkpoint.json',e.checkpoint())
    save('native.compact.checkpoint.json',e.world.checkpoint())
    save('situated.completed.checkpoint.json',e.access.checkpoint())
    save('native.transactions.jsonl','\n'.join(codec.dumps(t) for t in e.world.journal())+'\n')
    check('completed_engine_replay_exact',CognitiveEngine.restore(e.checkpoint()).checkpoint()==e.checkpoint())
    check('native_store_replay_exact',OperationStore.restore(e.world.checkpoint()).checkpoint()==e.world.checkpoint())
    check('access_replay_exact',NativeAccess.restore(e.access.checkpoint()).checkpoint()==e.access.checkpoint())
    check('historical_view_exact',e.participant_view(ALICE,through=cutoff).bytes()==initial_view.bytes())
    raw=tuple(codec.loads(line) for line in (out/'native.transactions.jsonl').read_text().splitlines())
    accounting=audit(raw)
    save('independent_raw_audit.json',accounting)
    check('independent_accounting_and_lineage',accounting['passed'] and accounting['concept_linked_actions']==2 and accounting['conceptual_commits']==3)
    # Ablation has the same delivered physical consequence but omits integration.
    ab=setup5()
    ap=think(ab,request5(ab))
    ao=receive(ab,enact(ab,ap),ALICE,'consequence')
    al=think(ab,request5(ab,'later',source=ao))
    check('retention_ablation_changes_action',plan_request(ab.participant_view(ALICE),al,'check').kind=='inspect')
    save('ablation.no_retention.checkpoint.json',ab.checkpoint())
    rows=[]
    for tim in TYPES:
        t=setup5(tim)
        t.start('start',request5(t))
        t.advance('limited',ALICE,'plan',18)
        d=t.job_status(ALICE,'plan')
        row={'tim':tim,'required':d['required'],'paid_at_limit':d['spent'],
             'active_at_limit':progress(d)[0],'perspective_at_limit':progress(d)[1],
             'completed_edges_at_limit':progress(d)[2],
             'route':{k:v for k,v in d.items() if k.startswith('route.')}}
        t.advance('rest',ALICE,'plan',1000)
        t.commit('commit',ALICE,'plan')
        row['action']=plan_request(t.participant_view(ALICE),t.job_status(ALICE,'plan')['binding'],'check').kind
        rows.append(row)
    save('matched_type_panel.json',rows)
    check('all_16_types_same_grounded_action',len(rows)==16 and {r['action'] for r in rows}=={'repair'})
    check('type_changes_paid_extent',len({r['required'] for r in rows})>1)
    check('same_work_different_progress',len({(r['active_at_limit'],r['completed_edges_at_limit']) for r in rows})>1)
    check('limited_work_identically_charged',{r['paid_at_limit'] for r in rows}=={18})
    save('circuit.references.json',{key:codec.encode(value) for key,value in {
        'tool_initial':SAW,'plan':plan,'physical_repair':event,'observed_repair':obs,
        'retained_account':retained,'later_plan':later,'later_physical_use':used}.items()})
    summary={'schema':'hle-u5-witness-v1','checks':checks,'passed':all(checks.values()),
        'check_count':len(checks),'accounting':accounting,
        'type_required_range':[min(r['required'] for r in rows),max(r['required'] for r in rows)]}
    save('summary.json',summary)
    print(json.dumps(summary),flush=True)
    return 0


if __name__=='__main__':raise SystemExit(main())
