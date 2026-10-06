"""R10 evaluation regression checks, including negative oracle controls."""
import unittest
from dataclasses import replace

from hle.contracts import WorkStatus
from hle.organization import OrganizationWorld
from hle.organization_records import OrganizationResult
from hle.socion_records import Reception
from tools.r10_oracle import check_world, reconstruct
from tools.r10_workloads import run_case
from .support import rules


class SustainedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d, cls.row, cls.prefix = run_case(cycles=2, initial_rounds=1,
            revised_rounds=1, successor_rounds=1)

    @rules('V01', 'V02')
    def test_repeated_lifecycle_reuses_learned_alternative(self):
        self.assertIsNone(self.row['blocked'])
        self.assertEqual([c['before_new_training'] for c in self.row['cycles']],
            ['unresolved', 'proposed'])
        self.assertEqual([c['generations'] for c in self.row['cycles']], [[1, 2, 3]] * 2)
        self.assertFalse(any(self.row['diagnostics']['unfinished_jobs'].values()))

    @rules('V02')
    def test_oracle_reconstructs_multiple_institution_identities(self):
        result = check_world(self.d.w)
        self.assertEqual(result['activations'], 18)
        self.assertEqual(result['mismatches'], 0)
        self.assertEqual(result['outcomes']['failed'], 2)

    @rules('V02')
    def test_oracle_rejects_missing_consent_reception(self):
        journal = list(self.d.w._journal)
        found = False
        for i, tx in enumerate(journal):
            if any(type(r) is Reception and r.outcome == WorkStatus.COMPLETED
                    and ':vote:' in r.command.task_id for r in getattr(tx, 'extra', ())):
                journal[i] = replace(tx, extra=tuple(r for r in tx.extra if type(r) is not Reception))
                found = True; break
        self.assertTrue(found)
        with self.assertRaisesRegex(AssertionError, 'consent not paid'):
            reconstruct(self.d.w.config, journal)

    @rules('V02')
    def test_oracle_rejects_unearned_proposal(self):
        journal = list(self.d.w._journal)
        for i, tx in enumerate(journal):
            candidates = [r for r in getattr(tx, 'extra', ()) if type(r) is OrganizationResult
                and r.kind == 'proposal' and r.status == 'proposed']
            if candidates:
                target = candidates[0]
                changed = replace(target, terms=replace(target.terms,
                    steps=('inspect',) * 7 + ('transfer',)))
                journal[i] = replace(tx, extra=tuple(changed if r == target else r for r in tx.extra))
                break
        with self.assertRaisesRegex(AssertionError, 'unearned organization'):
            reconstruct(self.d.w.config, journal)

    @rules('V02')
    def test_oracle_detects_corrupt_incremental_practice(self):
        w = OrganizationWorld.restore(self.prefix)
        actor = w.config.actors[0]
        key = next(iter(w._practice[actor]))
        w._practice[actor][key] = replace(w._practice[actor][key], successes=999)
        with self.assertRaisesRegex(AssertionError, 'incremental practice'):
            check_world(w)

    @rules('V01', 'V02')
    def test_replenished_resources_preserve_behavior_and_total_cost(self):
        d, row, _ = run_case(resources='replenished', cycles=2,
            initial_rounds=1, revised_rounds=1, successor_rounds=1)
        self.assertGreater(row['deferrals'], 0)
        self.assertEqual(row['debits'], self.row['debits'])
        self.assertEqual([c['revised_steps'] for c in row['cycles']],
            [c['revised_steps'] for c in self.row['cycles']])
        self.assertEqual(check_world(d.w)['outcomes'], check_world(self.d.w)['outcomes'])

    @rules('V01', 'V02')
    def test_inspection_intervention_blocks_transfer(self):
        d, row, _ = run_case(prefix=2, cycles=1, initial_rounds=1,
            revised_rounds=1, successor_rounds=1, capture_prefix=False)
        self.assertEqual(row['cycles'][0]['intervention_outcome'], 'blocked')
        oracle = check_world(d.w)
        self.assertEqual(oracle['outcomes']['blocked'], 1)
        self.assertEqual(oracle['failed_transfers'], 0)

    @rules('V01', 'V02')
    def test_unfunded_attempt_preserves_incomplete_status(self):
        for energy, available_time in ((0, 1000), (1000, 0)):
            d, row, _ = run_case(energy=energy, time_budget=available_time, capture_prefix=False)
            self.assertIsNotNone(row['blocked'])
            self.assertFalse(row['cycles'])
            self.assertEqual(sum(row['debits'].values()), 0)
            self.assertEqual(check_world(d.w)['physical_owners'], {'item000': 'p00'})

    @rules('V03')
    def test_cycle_boundary_restores_then_continues_exactly(self):
        w = OrganizationWorld.restore(self.prefix)
        for tx in self.d.w._journal[len(w._journal):]:
            w.execute(tx.command)
            self.assertEqual(w._journal[-1], tx)
        self.assertEqual(w.checkpoint(), self.d.w.checkpoint())


if __name__ == '__main__':
    unittest.main()
