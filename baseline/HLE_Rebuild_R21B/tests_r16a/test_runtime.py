import unittest
from dataclasses import replace
from unittest.mock import patch

from hle.shell_demo import case, signatures
from hle.shell_runtime import ShellAssessmentWorld
from hle.shell_reference import reference
from hle.shell_assessment import assess_engagement, JointShellAssessment
from hle.shell_records import SIGNS
from hle.compensation import CompensationWorld
from hle.compensation_demo import case as original_case, fund_command, run
from hle.compensation_records import ReleaseTransaction, ReleaseCommand
from hle.codec import loads, dumps
from hle.contracts import WorkStatus
from hle.world_records import Tick, Wallet


def prefix(w, end):
    cp = loads(w.checkpoint())
    return ShellAssessmentWorld.restore(dumps(replace(cp, journal=cp.journal[:end])))


class RuntimeIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = {name: case(**kw) for name, kw in (
            ('maintained', {}), ('ordinary', {'gated_history': False}),
            ('revision', {'revision_unit': 0}), ('refusal', {'refusal': True}))}
        cls.small, cls.setup = case(history=1, renewals=1)

    def test_live_generated_placement_has_three_independent_renewals(self):
        w, setup = self.cases['maintained']; report = w.shell_report()
        self.assertFalse(report['errors'])
        groups = [g for g in report['groups'] if g['signs']['forced_placement']['positive']]
        self.assertEqual(len(groups), 1)
        g = groups[0]; self.assertEqual(g['signs']['forced_placement']['positive'], 3)
        self.assertEqual(g['signs']['forced_placement']['status'], 'established_in_window')
        self.assertTrue(all(x['endpoint'] == 'correct' and x['opportunity'] == 'eligible' for x in g['engagements']))
        self.assertEqual(len({x['engagement'] for x in g['engagements']}), 3)

    def test_four_unimplemented_runtime_channels_remain_unknown(self):
        for w, _ in self.cases.values():
            for group in w.shell_report()['groups']:
                for sign in SIGNS:
                    if sign != 'forced_placement': self.assertEqual(group['signs'][sign]['status'], 'unassessed')
        self.assertTrue(self.small.shell_report()['parent_R16'].startswith('open'))

    def test_ordinary_history_and_revision_have_no_placement_positive(self):
        for name in ('ordinary', 'revision'):
            w, _ = self.cases[name]
            self.assertEqual(sum(g['signs']['forced_placement']['positive'] for g in w.shell_report()['groups']), 0)

    def test_required_confirmation_is_a_control_not_forced_placement(self):
        w, _ = self.cases['maintained']
        rows = signatures(w)
        self.assertEqual([x['placement'] for x in rows[:3]], ['unassessed', 'negative', 'negative'])

    def test_refused_carriers_and_retries_do_not_multiply_engagements(self):
        w, _ = self.cases['refusal']
        self.assertEqual(len(w.shell_monitor.traces), 6)
        self.assertEqual(sum(x['placement'] == 'positive' for x in signatures(w)), 1)
        self.assertFalse(any(g['signs']['forced_placement']['status'] == 'established_in_window' for g in w.shell_report()['groups']))

    def test_independent_raw_journal_reference_matches_every_supported_witness(self):
        with patch('hle.compensation.select_release', side_effect=AssertionError('reference called participant policy')):
            for w, _ in self.cases.values(): self.assertEqual(signatures(w), reference(w))

    def test_fixture_threshold_two_and_five_sensitivity_on_runtime_history(self):
        traces = [t for t in self.cases['maintained'][0].shell_monitor.traces
                  if assess_engagement(t)['signs']['forced_placement']['observation'] == 'positive']
        for threshold, expected in ((2,'established_in_window'), (3,'established_in_window'), (5,'candidate')):
            joint = JointShellAssessment(threshold)
            for t in traces: joint.append(t)
            self.assertEqual(joint.report()['signs']['forced_placement']['status'], expected)

    def test_monitor_does_not_change_original_policy_cost_or_checkpoint(self):
        original, _ = original_case(history=1, renewals=1)
        self.assertEqual(original.checkpoint(), self.small.checkpoint())
        # Read-only reporting can run repeatedly without adding a transaction.
        cp = self.small.checkpoint()
        for _ in range(4): self.small.shell_report()
        self.assertEqual(cp, self.small.checkpoint())

    def test_full_restore_rebuilds_assessment_without_serializing_verdict(self):
        cp = self.small.checkpoint(); restored = ShellAssessmentWorld.restore(cp)
        self.assertEqual(cp, restored.checkpoint())
        self.assertEqual(restored.shell_report(), self.small.shell_report())
        self.assertEqual(CompensationWorld.restore(cp).checkpoint(), cp)
        self.assertNotIn('established_in_window', cp)

    def test_every_release_boundary_restores_and_next_transaction_matches(self):
        cp = loads(self.small.checkpoint())
        boundaries = {1,len(cp.journal)} | {i+1 for i,t in enumerate(cp.journal) if type(t) is ReleaseTransaction}
        for n in sorted(boundaries):
            a = ShellAssessmentWorld.restore(dumps(replace(cp, journal=cp.journal[:n])))
            b = ShellAssessmentWorld.restore(a.checkpoint())
            self.assertEqual(a.shell_report(), b.shell_report())
            if n < len(cp.journal):
                a.execute(cp.journal[n].command); b.execute(cp.journal[n].command)
                self.assertEqual(a._journal[-1], cp.journal[n]); self.assertEqual(a.shell_report(), b.shell_report())

    def test_partial_work_has_no_early_witness_and_continues_exactly(self):
        for op in ('consider', 'enact', 'review', 'assimilate'):
            target = next(t for t in self.small._journal if type(t) is ReleaseTransaction and t.command.operator == op
                          and t.event.when.tick > self.setup['cuts'][1])
            w = prefix(self.small, target.event.when.tick)
            cmd = replace(target.command, command_id='partial:'+op, work_limit=1)
            w.execute(cmd); partial = w._journal[-1]
            self.assertEqual(partial.event.outcome, WorkStatus.PARTIAL)
            self.assertFalse(any((partial.material, partial.treatment, partial.concept, partial.decision, partial.messages)))
            self.assertTrue(w.shell_report()['incomplete_release_jobs'])
            other = ShellAssessmentWorld.restore(w.checkpoint())
            for x in (w,other): fund_command(x, replace(cmd, command_id='finish:'+op, work_limit=10000))
            self.assertEqual(w.shell_report(),other.shell_report())
            self.assertEqual(w.checkpoint(),other.checkpoint())

    def test_quiet_ticks_add_no_recurrence_and_do_not_traverse_journal(self):
        target = next(t for t in self.small._journal if type(t) is ReleaseTransaction and t.decision and not t.decision.view.required)
        class NoIteration(list):
            def __iter__(self): raise AssertionError('traversed inactive journal')
        rows = []
        for ticks in (0,100,1000):
            w = prefix(self.small, target.event.when.tick)
            baseline = w.shell_monitor.release_visits
            for i in range(ticks): w.execute(Tick('quiet:'+str(i)))
            self.assertEqual(w.shell_monitor.release_visits, baseline)
            w._journal = NoIteration(w._journal)
            w.execute(target.command)
            rows.append((w._journal[-1].job.paid, len(w.shell_monitor.traces), w.shell_monitor.release_visits-baseline))
        self.assertEqual(rows, [rows[0]]*3)

    def test_resource_limited_optional_demand_remains_unassessed(self):
        full = self.small
        target = next(t for t in full._journal if type(t) is ReleaseTransaction and t.decision and not t.decision.view.required)
        worker = full.config.actors[0]; before = dict((a.unit,a.amount) for a in target.works[0].before)
        from hle.world_records import ENERGY
        original_energy = next(w.energy for w in full.config.wallets if w.actor==worker)
        budget = original_energy-before[ENERGY]+target.job.plan.required+1
        config = replace(full.config, wallets=tuple(Wallet(w.actor,budget,budget) if w.actor==worker else w for w in full.config.wallets))
        w = ShellAssessmentWorld(config, full.profiles, full.policy, full.agents, full.organization_policies,
               full.semantic_policy, full.workshop, full.autonomy, release=full.release, reviewers=full.reviewers)
        for tx in full._journal[1:target.event.when.tick+1]: w.execute(tx.command)
        r = w.shell_report()['open_engagements'][0]
        self.assertEqual(r['opportunity'], 'insufficient_resources')
        self.assertEqual(r['signs']['forced_placement']['observation'], 'unassessed')

    def test_report_mutation_cannot_rewrite_stored_evidence(self):
        w = self.small; original = w.shell_report()
        modified = w.shell_report()
        modified['groups'][0]['engagements'][0]['endpoint'] = 'invented'
        self.assertEqual(original, w.shell_report())

    def test_rehashed_false_concept_checkpoint_fails_runtime_replay(self):
        cp = loads(self.small.checkpoint()); journal = list(cp.journal)
        index = next(i for i,t in enumerate(journal) if type(t) is ReleaseTransaction and t.concept is not None)
        t = journal[index]; journal[index] = replace(t, concept=replace(t.concept, relations=()))
        with self.assertRaises(ValueError): ShellAssessmentWorld.restore(dumps(replace(cp,journal=tuple(journal))))

    def test_scoped_oig_matches_reference_for_each_live_engagement(self):
        for w, _ in self.cases.values():
            self.assertTrue(all(g.reference_oig_matches() for g in w.shell_monitor.groups.values()))
            self.assertTrue(all(len(x['oig']['R']) == 12 for x in signatures(w)))


if __name__ == '__main__': unittest.main()
