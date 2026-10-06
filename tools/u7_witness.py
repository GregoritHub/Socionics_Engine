"""Inspectable U7 cross-target histories, controls, physical comparison and replay."""
import argparse
from dataclasses import asdict, is_dataclass
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'baseline/HLE_Rebuild_R21B')]
sys.dont_write_bytecode = True
from tests_u7.fixtures import *
from hle_unified import codec
from hle_unified.shell_audit import audit
from hle_unified.shell_assessment import assess
from hle_unified.operations import NativeAccess
from hle_unified.records import Assessment, EvidenceStatus


def main():
    p = argparse.ArgumentParser(); p.add_argument('--out', required=True, type=Path)
    out = p.parse_args().out; out.mkdir(parents=True, exist_ok=False)
    checks = {}
    def save(name, value):
        (out/name).write_text(value if type(value) is str else json.dumps(value, indent=2,
            default=lambda o: asdict(o) if is_dataclass(o) else str(o))+'\n')
    def check(name, value):
        checks[name] = bool(value); save('checks.in_progress.json', checks)
        if not value: raise AssertionError(name)
    def bundle(name, engine):
        save(name+'.checkpoint.json', engine.checkpoint())
        raw = '\n'.join(codec.dumps(tx) for tx in engine.world.journal())+'\n'
        save(name+'.transactions.jsonl', raw)
        decoded = tuple(codec.loads(line) for line in raw.splitlines())
        measured = audit(decoded)
        save(name+'.raw_audit.json', measured)
        save(name+'.assessment.json', assess(decoded))
        return measured

    e = setup7(); initial = e.participant_view(ALICE); cutoff = len(initial.snapshot.history)
    save('alice.initial.json', initial.bytes())
    pattern = generated(e); rows = cross_target(e)
    save('cross_target.bindings.json', rows)
    save('generated.pattern.json', pattern)
    measurement = bundle('cross_target', e)
    check('one_generated_pattern_no_fixture', measurement['generated_patterns'] == 1 and measurement['injected_patterns'] == 0)
    check('all_eight_target_categories', set(rows) == set(TARGETS))
    check('common_origin_distinct_target_bindings', all(r['pattern.0'] == pattern.ref for r in rows.values()) and len({r['target'] for r in rows.values()}) == 8)
    check('processing_changes_at_every_target', all(r['base_route'] == 'engage' and r['route'] == 'wait' for r in rows.values()))
    check('actor_carrier_bearer_retained', all((r['actor'],r['carrier'],r['bearer']) == (ALICE,ObjectRef(BOB,1),ObjectRef(EVE,1)) for r in rows.values()))
    check('paid_distinct_origin_experiences', len(pattern.evidence) == 2 and all(attrs(e.world.resolve(r))['spent'] > 0 for r in pattern.evidence))
    check('recurrence_after_processed_counterevidence', sum(r['classification']=='defensive_maintenance' for r in assess(e.world.journal())['rows']) == 8)
    check('nonmental_target_stays_nonmental', e.world.resolve(SAW).roles == (Role.MATERIAL,))
    check('hypothetical_target_stays_hypothetical', e.world.resolve(POSSIBILITY).occurrence == Occurrence.HYPOTHETICAL)
    check('no_unearned_acquired_capacity', not e.participant_view(ALICE).snapshot.acquired)
    check('historical_participant_view_exact', e.participant_view(ALICE, through=cutoff).bytes() == initial.bytes())
    check('full_engine_replay_exact', ShellEngine.restore(e.checkpoint()).checkpoint() == e.checkpoint())
    check('native_journal_replay_exact', OperationStore.restore(e.world.checkpoint()).checkpoint() == e.world.checkpoint())
    check('access_history_replay_exact', NativeAccess.restore(e.access.checkpoint()).checkpoint() == e.access.checkpoint())
    check('raw_cost_and_lineage_audit', measurement['passed'])

    source = supply(e, 'unrelated', target=SAW2, trigger=OTHER_TRIGGER)
    row = attrs(e.world.resolve(meet(e, 'unrelated', source, target=SAW2)))
    check('unrelated_affordance_unchanged', row['route']=='engage' and not indexed(row,'pattern.'))
    bundle('unrelated_control', e)

    physical = {}
    for generate, name in ((True,'generated'),(False,'generation_ablation')):
        x = setup7(generate=generate, prior='serviceable', serviceable=True)
        for i,target in enumerate((SAW,SAW2)):
            s=supply(x,'learning-'+str(i),target=target,feedback='blame'); meet(x,'learning-'+str(i),s,target=target)
        before=x.wallet(ALICE)['energy']
        choice=first_choice(x); drive(x,delivery=False,prefix='execute')
        physical[name]={'choice':choice,'wear':attrs(x.world.head(SAW.identity))['wear'],'budget_before_forecast':before,
                        'audit':bundle(name+'.physical',x)}
    save('physical.comparison.json',physical)
    check('matched_generation_history_costs',physical['generated']['budget_before_forecast']==physical['generation_ablation']['budget_before_forecast'])
    check('generated_pattern_changes_actual_choice',physical['generated']['choice']=='inspect' and physical['generation_ablation']['choice']=='use')
    check('actual_material_consequences_differ',physical['generated']['wear']==0 and physical['generation_ablation']['wear']==1)
    check('forecast_application_is_paid',physical['generated']['audit']['forecast_applications']==1)

    operators={}
    for kind in ('obligation','salience','forecast','exclude_route','approval'):
        x=setup7(generate=False); inject(x,Effect(kind)); s=supply(x,'effect'); meet(x,'effect',s)
        operators[kind]=bundle('operator.'+kind,x)
    check('all_five_operators_have_marked_fixture_witnesses',len(operators)==5 and all(m['injected_patterns']==1 and m['generated_patterns']==0 for m in operators.values()))

    negatives={}
    for name,terms,request_changes in (
        ('threat',{'safe':False},{}), ('refusal',{'requires_partner':True,'willing':False},{}),
        ('actual_requirement',{'approval_required':True},{}), ('rest',{}, {'demand':False}),
        ('ordinary_disagreement',{}, {'route':'inspect'})):
        x=setup7(generate=False); s=supply(x,'control',**terms); meet(x,'control',s,**request_changes)
        negatives[name]=assess(x.world.journal())['rows'][-1]['classification']; bundle('control.'+name,x)
    x=setup7(); s=supply(x,'unread',target=GROUP,read=False); meet(x,'unread',s,target=GROUP)
    negatives['unread']=assess(x.world.journal())['rows'][-1]['classification']; bundle('control.unread',x)
    x=setup7(budget=75); s=supply(x,'scarcity'); r=request7(x,'scarcity',s)
    x.start('begin',r); x.advance('work',ALICE,r.key,1000)
    negatives['scarcity']=assess(x.world.journal())['rows'][-1]['classification']; bundle('control.scarcity',x)
    save('negative_controls.json',negatives)
    check('legitimate_boundaries_not_shells', negatives=={'threat':'accurate_threat_recognition','refusal':'partner_refusal',
        'actual_requirement':'actual_approval_requirement','rest':'no_demand','ordinary_disagreement':'ordinary_disagreement',
        'unread':'missing_knowledge','scarcity':'insufficient_resources'})

    x=setup7(); generated(x); s=supply(x,'partial'); r=request7(x,'partial',s)
    x.start('begin',r); x.advance('one',ALICE,r.key,1); cp=x.checkpoint(); save('partial.checkpoint.json',cp)
    restored=ShellEngine.restore(cp)
    for engine in (x,restored): engine.advance('finish',ALICE,r.key,1000); engine.commit('commit',ALICE,r.key)
    check('paid_partial_continuation_exact',x.checkpoint()==restored.checkpoint())
    bundle('partial.completed',x)

    x=setup7(); generated(x); before=x.checkpoint(); assess(x.world.journal())
    check('offline_assessment_cannot_change_participant',x.checkpoint()==before)
    label=ObjectVersion(ref('assessor'),WRITER,'Offline only',(Role.ASSESSMENT,),
        (Assessment(SAW,'deformation',EvidenceStatus.ESTABLISHED,(SAW,),'injected isolation check'),))
    x.declare('assessor',(label,)); rejected=False
    try:show(x,ALICE,label.ref)
    except ValueError:rejected=True
    check('assessment_disclosure_is_rejected',rejected)
    save('assessor_isolation.checkpoint.json',x.checkpoint())

    summary={'schema':'hle-u7-witness-v1','checks':checks,'check_count':len(checks),
             'passed':all(checks.values()),'cross_target':measurement,'physical':physical,'negative_controls':negatives}
    save('summary.json',summary); print(json.dumps({'passed':summary['passed'],'checks':len(checks),'cross_target':measurement}),flush=True)
    return 0


if __name__=='__main__':raise SystemExit(main())
