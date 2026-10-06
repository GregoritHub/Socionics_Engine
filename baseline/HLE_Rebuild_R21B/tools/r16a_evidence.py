"""Reproduce the declared R16A fixture/runtime/replay panel and retain failures."""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from hle.shell_fixtures import panel
from hle.shell_records import SIGNS
from hle.shell_demo import case, signatures
from hle.shell_runtime import ShellAssessmentWorld
from hle.shell_reference import reference
from hle.shell_assessment import json_value, JointShellAssessment, assess_engagement
from hle.compensation_evaluation import evaluate
from hle.compensation_demo import fund_command
from hle.compensation_records import ReleaseTransaction
from hle.world_records import Tick
from hle.codec import dumps, loads


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=ROOT/'evidence/r16a/panel')
    args = parser.parse_args(); out = args.out.resolve(); out.mkdir(parents=True, exist_ok=True)
    def save(name, value): (out/(name+'.json')).write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')
    fixtures = panel(); save('fixtures', fixtures)
    worlds = {}; outcomes = {}; timings = {}; gates = {}
    gates['five_fixture_sign_control_pairs'] = all(
        fixtures[s]['sign']['signs'][s]['status']=='established_in_window'
        and fixtures[s]['ordinary_control']['signs'][s]['status'] not in ('candidate','established_in_window') for s in SIGNS)
    for name, kwargs in [('maintained', {}), ('ordinary', {'gated_history':False}),
                         ('revision_ablation', {'revision_unit':0}), ('refusal_reownership', {'refusal':True})]:
        started = time.perf_counter(); w, setup = case(**kwargs); worlds[name] = w
        live = w.shell_report(); independent = reference(w); actual = signatures(w)
        accounting = evaluate(w, setup)
        save(name, {'assessment':live, 'signatures':actual, 'independent_reference':independent,
                    'reference_equal':actual==independent, 'accounting_errors':accounting['oracle_errors'],
                    'logical_work':accounting['logical_work'], 'correct_optional_endpoints':accounting['correct_optional_endpoints'],
                    'scheduling':setup['scheduling']})
        (out/(name+'.checkpoint.json')).write_text(w.checkpoint())
        save(name+'.traces', [json_value(t) for t in w.shell_monitor.traces])
        restored = ShellAssessmentWorld.restore(w.checkpoint())
        outcomes[name] = {'reference_equal':actual==independent,
                         'restore_equal':restored.shell_report()==live and restored.checkpoint()==w.checkpoint(),
                         'errors':live['errors']+accounting['oracle_errors'],
                         'placement_positives':sum(r['placement']=='positive' for r in actual),
                         'correct_optional_endpoints':accounting['correct_optional_endpoints']}
        timings[name] = time.perf_counter()-started
        print(json.dumps({'case':name, **outcomes[name]}), flush=True)
    gates['live_three_eligible_placements'] = outcomes['maintained']['placement_positives']==3 and outcomes['maintained']['correct_optional_endpoints']==3
    gates['ordinary_and_revision_no_placement'] = all(outcomes[n]['placement_positives']==0 for n in ('ordinary','revision_ablation'))
    gates['refusal_retries_count_one_engagement'] = outcomes['refusal_reownership']['placement_positives']==1
    gates['four_channels_honestly_unassessed'] = all(g['signs'][s]['status']=='unassessed'
        for w in worlds.values() for g in w.shell_report()['groups'] for s in SIGNS if s!='forced_placement')
    gates['independent_replay_and_accounting'] = all(r['reference_equal'] and r['restore_equal'] and not r['errors'] for r in outcomes.values())
    small, setup = case(history=1, renewals=1); cp = loads(small.checkpoint())
    boundaries = {1,len(cp.journal)} | {i+1 for i,t in enumerate(cp.journal) if type(t) is ReleaseTransaction}
    replay = []
    for n in sorted(boundaries):
        text = dumps(replace(cp,journal=cp.journal[:n])); a = ShellAssessmentWorld.restore(text)
        b = ShellAssessmentWorld.restore(a.checkpoint()); equal = a.checkpoint()==text and a.shell_report()==b.shell_report()
        if n < len(cp.journal):
            for w in (a,b): w.execute(cp.journal[n].command)
            equal = equal and a._journal[-1]==cp.journal[n] and a.shell_report()==b.shell_report()
        replay.append({'prefix':n, 'exact_checkpoint_assessment_and_next':equal})
    partial = []
    for op in ('consider','enact','review','assimilate'):
        target = next(t for t in small._journal if type(t) is ReleaseTransaction and t.command.operator==op and t.event.when.tick>setup['cuts'][1])
        a = ShellAssessmentWorld.restore(dumps(replace(cp,journal=cp.journal[:target.event.when.tick])))
        cmd = replace(target.command, command_id='partial:'+op, work_limit=1); a.execute(cmd)
        tx = a._journal[-1]; b = ShellAssessmentWorld.restore(a.checkpoint())
        no_early = not any((tx.material,tx.treatment,tx.concept,tx.decision,tx.messages))
        for w in (a,b): fund_command(w, replace(cmd,command_id='finish:'+op,work_limit=10000))
        partial.append({'operator':op,'no_early_output':no_early,
                        'identical_continuation':a.checkpoint()==b.checkpoint() and a.shell_report()==b.shell_report()})
    save('replay', {'boundaries':replay,'partial':partial})
    gates['prefix_and_partial_continuation'] = all(x['exact_checkpoint_assessment_and_next'] for x in replay) and all(x['no_early_output'] and x['identical_continuation'] for x in partial)
    target = next(t for t in small._journal if type(t) is ReleaseTransaction and t.decision and not t.decision.view.required)
    class NoIteration(list):
        def __iter__(self): raise AssertionError('inactive journal iteration')
    inactive=[]
    for ticks in (0,100,1000):
        w = ShellAssessmentWorld.restore(dumps(replace(cp,journal=cp.journal[:target.event.when.tick])))
        visits=w.shell_monitor.release_visits
        for i in range(ticks): w.execute(Tick('inactive:'+str(i)))
        unchanged=w.shell_monitor.release_visits==visits
        w._journal=NoIteration(w._journal); w.execute(target.command)
        inactive.append({'ticks':ticks,'inactive_release_visits_zero':unchanged,'paid_units':w._journal[-1].job.paid,
                         'new_release_visits':w.shell_monitor.release_visits-visits,'closed_engagements':len(w.shell_monitor.traces)})
    save('inactive',inactive)
    gates['no_inactive_history_scan'] = all(x['inactive_release_visits_zero'] and x['new_release_visits']==1 for x in inactive) and len({x['paid_units'] for x in inactive})==1
    sensitivity=[]
    for threshold in (2,3,5):
        a=JointShellAssessment(threshold)
        for t in worlds['maintained'].shell_monitor.traces:
            if assess_engagement(t)['signs']['forced_placement']['observation']=='positive':a.append(t)
        sensitivity.append({'threshold':threshold,'result':a.report()['signs']['forced_placement']})
    save('sensitivity',sensitivity)
    parent=hashlib.sha256((ROOT/'docs/r12/acceptance_v1.json').read_bytes()).hexdigest()
    protocol=json.loads((ROOT/'docs/r16a/Protocol_R16A_v1.json').read_text())
    gates['frozen_parent_unchanged']=parent==protocol['parent_acceptance_sha256']
    result={'schema':'r16a-panel-v1','gates':gates,'passed':all(gates.values()),'runtime_outcomes':outcomes,
            'parent_R16_complete':False,'parent_progress':[4,10],'remaining_parents':6,
            'R16_frozen_gates':{'R16.1':'open: only one of five runtime channels',
                                'R16.2':'partial: independent runtime replay for placement; fixture replay for all five',
                                'R16.3':'open: post-increase new structure tested only as fixture'},
            'next':'R16B: supply independent runtime witnesses for the remaining signs'}
    save('summary',result);save('timings',timings)
    print(json.dumps(result),flush=True)
    return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
