"""Raw finite development, withdrawal, generalization and material witnesses."""
import argparse
from dataclasses import asdict,is_dataclass
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
sys.dont_write_bytecode=True
from tests_u8.fixtures import *
from hle_unified import codec
from hle_unified.development_assessment import assess,evaluate_return_sequences
from hle_unified.operations import NativeAccess


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True,type=Path)
    out=parser.parse_args().out;out.mkdir(parents=True,exist_ok=False)
    checks={}
    def save(name,value):
        (out/name).write_text(value if type(value) is str else json.dumps(value,indent=2,
            default=lambda x:asdict(x) if is_dataclass(x) else str(x))+'\n')
    def check(name,value):
        checks[name]=bool(value);save('checks.in_progress.json',checks)
        if not value:raise AssertionError(name)
    def bundle(name,e):
        save(name+'.checkpoint.json',e.checkpoint())
        raw='\n'.join(codec.dumps(tx) for tx in e.world.journal())+'\n'
        save(name+'.transactions.jsonl',raw)
        decoded=tuple(codec.loads(line) for line in raw.splitlines())
        measurement=audit(decoded);assessment=assess(decoded)
        save(name+'.raw_audit.json',measurement);save(name+'.assessment.json',assessment)
        save(name+'.actor_development.json',e.development_view(ALICE))
        return measurement,assessment

    e=setup8();p=generated(e);origin=e.world.resolve(p.origin)
    initial=e.participant_view(ALICE);cutoff=len(initial.snapshot.history)
    support=respond8(e,'supported',p,approved=True)
    assisted=practice8(e,'supported-practice',p,support)
    check('supported_success_is_not_independent_practice',e._response_results[support]['completed_demand'] and not assisted['independent'])
    check('support_does_not_grant_generalized_capacity',not e._capacities)
    withdrawn=respond8(e,'withdrawn',p)
    check('withdrawal_without_learning_reopens_pattern',not e._response_results[withdrawn]['completed_demand'])
    release8(e,'local-saw',p)
    local=respond8(e,'local-return',p)
    residual=respond8(e,'residual',p,(GROUP,),partner=ObjectRef(EVE,1))
    check('local_repair_changes_only_its_binding',e._response_results[local]['completed_demand'] and not e._response_results[residual]['completed_demand'])
    check('residual_displaces_same_origin_to_changed_carrier',e._treatments[p.origin]['kind']=='displacement' and e._treatments[p.origin]['carrier']==ObjectRef(EVE,1))
    local_measure,local_assessment=bundle('local_and_residual',e)
    check('local_success_does_not_establish_clearance',local_assessment['findings'][0]['finite_return_status']=='unassessed')
    e,p=trained8(e)
    cap=e._capacities[p.ref];features=(p.origin,p.owner,p.context,p.cue,p.trigger,cap['organization'],cap['max_load'])
    save('retained_before_returns.json',e.development_view(ALICE))
    check('two_independent_batches_retain_load_two',cap['max_load']==2 and len(cap['examples'])==2)
    before_return=e.checkpoint();save('before_returns.checkpoint.json',before_return)
    returned8(e,p)
    check('changed_partner_and_unfamiliar_targets_handled_without_support',all(x['independent'] and not x['supported'] and x['partner']==ObjectRef(EVE,1) for x in e._practices[p.ref][-2:]))
    check('renewed_demand_is_harder_than_initial_single_target',all(len(x['targets'])==2 for x in e._practices[p.ref][-2:]) and e._response_results[support]['load']==1)
    check('reownership_keeps_original_material_identity',e._treatments[p.origin]['ownership']=='reowned' and e.world.resolve(p.origin)==origin)
    check('reownership_removes_external_carrier_without_deleting_pattern',e._treatments[p.origin]['carrier'] is None and e.pattern_view(ALICE)==(p,))
    cap_after=e._capacities[p.ref]
    after=(p.origin,p.owner,p.context,p.cue,p.trigger,cap_after['organization'],cap_after['max_load'])
    check('declared_capacity_identity_survives_enumerated_returns',features==after)
    measured,assessment=bundle('development_and_returns',e)
    check('scoped_finite_returns_established',assessment['findings'][0]['finite_return_status']=='established')
    check('universal_composition_remains_unassessed',assessment['findings'][0]['universal_composition']=='unassessed')
    check('accuracy_and_supported_path_are_separate',local_assessment['findings'][0]['factual_accuracy']['correct']<local_assessment['findings'][0]['factual_accuracy']['adjudicable'] and local_assessment['findings'][0]['useful_capacity']['completed_batches']>0)
    check('historical_actor_view_reconstructs_exactly',e.participant_view(ALICE,through=cutoff).bytes()==initial.bytes())
    check('native_and_access_histories_replay_exactly',OperationStore.restore(e.world.checkpoint()).checkpoint()==e.world.checkpoint() and NativeAccess.restore(e.access.checkpoint()).checkpoint()==e.access.checkpoint())
    restored=DevelopmentEngine.restore(before_return);returned8(restored,p)
    check('checkpoint_continuation_reproduces_returns_and_reownership',restored.checkpoint()==e.checkpoint())

    base,p2=trained8(setup8(serviceable=True,prior='serviceable'),reorganize=False)
    control=DevelopmentEngine.restore(base.checkpoint());candidate=base
    reorganize8(candidate,'reorganize',p2)
    physical={}
    for name,x in (('without_reorganization',control),('retained_reorganization',candidate)):
        balance=x.wallet(ALICE)['energy'];choice=first_choice(x);drive(x,delivery=False,prefix='execute')
        audit_,_=bundle(name+'.physical',x)
        physical[name]={'choice':choice,'wear':attrs(x.world.head(SAW.identity))['wear'],
            'energy_before_forecast':balance,'audit':audit_}
    save('physical.comparison.json',physical)
    check('physical_target_has_no_local_correction',all((p2.ref,SAW) not in x._corrections for x in (candidate,control)))
    check('practice_changes_later_u6_choice',physical['without_reorganization']['choice']=='inspect' and physical['retained_reorganization']['choice']=='use')
    check('actual_u4_consequences_differ',physical['without_reorganization']['wear']==0 and physical['retained_reorganization']['wear']==1)
    check('both_physical_arms_have_ample_resource_margin',min(row['energy_before_forecast'] for row in physical.values())>1000)

    x,p3=trained8()
    overload=respond8(x,'overload',p3,(MEMORY,POSSIBILITY,ACTION))
    practice8(x,'overload-practice',p3,overload)
    check('unsupported_load_does_not_inflate_capacity',not x._response_results[overload]['completed_demand'] and x._capacities[p3.ref]['max_load']==2)
    negatives={}
    for i,(name,terms,demand) in enumerate((('threat',{'safe':False},True),('refusal',{'requires_partner':True,'willing':False},True),
            ('actual_requirement',{'approval_required':True},True),('unavailable',{'available':False},True),('rest',{},False))):
        event=respond8(x,'negative-'+str(i),p3,(MEMORY,),demand=demand,**terms)
        negatives[name]=x._response_results[event]['row.0.route']
    save('negative_controls.json',negatives);bundle('limits_and_boundaries',x)
    check('real_boundaries_and_rest_preserved',negatives=={'threat':'wait','refusal':'wait','actual_requirement':'wait','unavailable':'wait','rest':'rest'})

    x=setup8();p4=generated(x);supply8(x,'facts');r=request8(x,'partial','release',p4)
    x.start('start',r);x.advance('one',ALICE,r.key,1);cp=x.checkpoint();save('partial.checkpoint.json',cp)
    y=DevelopmentEngine.restore(cp)
    for obj in (x,y):obj.advance('finish',ALICE,r.key,1000);obj.commit('commit',ALICE,r.key)
    check('partial_paid_correction_continues_exactly',x.checkpoint()==y.checkpoint())
    bundle('partial.completed',x)
    example=evaluate_return_sequences(0,lambda state,op:{0:1,1:2,2:2}[state],lambda state:state<2,(('return',),('return','return')))
    save('canon.composite_counterexample.json',example)
    check('single_endpoint_does_not_erase_composite_failure',[r['status'] for r in example['rows']]==['established','failed'])
    summary={'schema':'hle-u8-witness-v1','checks':checks,'check_count':len(checks),'passed':all(checks.values()),
        'development':measured,'physical':physical,'negative_controls':negatives}
    save('summary.json',summary);print(json.dumps({'passed':summary['passed'],'checks':len(checks),'development':measured}),flush=True)
    return 0


if __name__=='__main__':raise SystemExit(main())
