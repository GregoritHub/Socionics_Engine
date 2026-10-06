import copy
import gzip
import hashlib
import json
import sys
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from hle.contracts import Ref, Kind, Moment, TimeScope
from hle.development_contracts import ResourceEnvelope, Requirement, Comparison, compare_demands
from hle.resource_contracts import (PROTOCOL_ID, PROTOCOL_SHA256, PROTOCOL_REF,
                                    ResourceFrame, compare_demands_v2)
from hle.clearance_records import EpisodeResourceContract
from hle.clearance_reference import compare
from hle.closure import ClosureWorld
from hle.world_records import Credit, Tick
from hle.autonomy_records import WorkshopCommand
from tests_r12.test_contracts import demand, opportunity, A, B
from r21_workloads import make_world, run_episode, replay_witness
from r21a_policy import make_contract_world, run_reference_policy, protocol
from r21a_audit import audit_episode, horizon_audit, evaluate_feasibility


class RequirementOrder(unittest.TestCase):
    def setUp(self):
        self.command = EpisodeResourceContract('contract', 'fixture', 'adequate', 11, PROTOCOL_ID, PROTOCOL_SHA256)
        self.frame = ResourceFrame(self.command, A, ResourceEnvelope(100000, 100000, None))
        self.prior = demand(comparison_protocol=PROTOCOL_REF)

    def compare(self, **changes):
        return compare_demands_v2(replace(self.prior, **changes), self.prior, self.frame, self.frame)

    def test_spending_does_not_reclassify_requirement_increase(self):
        current = replace(self.prior, resources=ResourceEnvelope(90, 85, None),
                          requirements=(Requirement('temporal_dependencies', 2), Requirement('missing_testimony', 0)))
        self.assertEqual(compare_demands(current, self.prior).relation, Comparison.INCOMPARABLE)
        self.assertEqual(compare_demands_v2(current, self.prior, self.frame, self.frame).relation, Comparison.GREATER)
        self.assertEqual((current.resources.energy, self.prior.resources.energy), (90, 100))

    def test_less_wallet_is_not_itself_a_greater_requirement(self):
        self.assertEqual(self.compare(resources=ResourceEnvelope(2, 3, None)).relation, Comparison.EQUAL)

    def test_equal_shape_with_empty_wallet_cannot_confer_eligibility(self):
        empty = ResourceEnvelope(0, 0, None)
        self.assertEqual(self.compare(resources=empty).relation, Comparison.EQUAL)
        self.assertFalse(opportunity(resources=empty).eligible)

    def test_mixed_and_lesser_requirements_remain_distinct(self):
        self.assertEqual(self.compare(requirements=(Requirement('temporal_dependencies', 0),
            Requirement('missing_testimony', 1))).relation, Comparison.INCOMPARABLE)
        self.assertEqual(self.compare(requirements=(Requirement('temporal_dependencies', 0),
            Requirement('missing_testimony', 0))).relation, Comparison.LESSER)

    def test_scope_changes_remain_incomparable(self):
        changes = ({'participants': (A, Ref(Kind.ENTITY, 'other', 1))},
                   {'context': Ref(Kind.CONTEXT, 'elsewhere', 1)},
                   {'material_lineage': (Ref(Kind.MEMORY, 'other', 1),)},
                   {'constraints': ('other consent',)}, {'required_outcomes': ('other result',)},
                   {'comparison_protocol': Ref(Kind.PROTOCOL, 'unknown', 1)},
                   {'duration': TimeScope(Moment(0, 0), Moment(2, 0))},
                   {'requirements': (Requirement('new_dimension', 1),)})
        for change in changes:
            with self.subTest(change=change):self.assertEqual(self.compare(**change).relation, Comparison.INCOMPARABLE)

    def test_increased_or_replenished_wallet_is_out_of_scope(self):
        for wallet in (ResourceEnvelope(101, 100, None), ResourceEnvelope(90, 101, None),
                       ResourceEnvelope(100001, 100001, None),
                       ResourceEnvelope(90, 90, Ref(Kind.RULE, 'funding', 1))):
            with self.subTest(wallet=wallet):self.assertEqual(self.compare(resources=wallet).relation, Comparison.INCOMPARABLE)

    def test_episode_actor_and_allocation_are_not_interchangeable(self):
        for frame in (replace(self.frame, contract=replace(self.command, episode_id='another')),
                      replace(self.frame, actor=B), replace(self.frame, allocation=ResourceEnvelope(20000, 20000, None))):
            with self.subTest(frame=frame):
                self.assertEqual(compare_demands_v2(self.prior, self.prior, frame, self.frame).relation, Comparison.INCOMPARABLE)


class ActivationAndCompatibility(unittest.TestCase):
    def test_frozen_v2_and_unchanged_v1_declarations(self):
        p = protocol()
        for name, key in (('docs/r21/Protocol_R21_v1.json', 'preserved_v1_sha256'),
                          ('docs/r12/acceptance_v1.json', 'r12_acceptance_sha256')):
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(), p[key])
        self.assertEqual(p['evaluation']['evaluation_seeds'], list(range(2001, 2011)))

    def test_no_retrofit_after_any_prior_event(self):
        w, _ = make_world('iee', 12, 100000)
        w.execute(Tick('already-started'))
        declaration = EpisodeResourceContract('contract', 'late', 'adequate', 12, PROTOCOL_ID, PROTOCOL_SHA256)
        before = tuple(w._journal)
        with self.assertRaisesRegex(ValueError, 'immediately after genesis'):w.execute(declaration)
        self.assertEqual(tuple(w._journal), before)

    def test_budget_and_protocol_mismatch_rejected_before_mutation(self):
        for budget, digest in ((20000, PROTOCOL_SHA256), (100000, '0'*64)):
            w, _ = make_world('iee', 12, budget)
            with self.assertRaises(ValueError):
                w.execute(EpisodeResourceContract('bad', 'bad', 'adequate', 12, PROTOCOL_ID, digest))
            self.assertEqual(len(w._journal), 1)

    def test_runtime_rejects_credit_even_without_driver_guard(self):
        w, _ = make_contract_world('iee', 12, 'adequate')
        before = w.checkpoint()
        with self.assertRaisesRegex(ValueError, 'top-ups'):
            w.execute(Credit('hidden-funding', w.config.actors[0], 1, 0, 'forbidden'))
        self.assertEqual(w.checkpoint(), before)

    def test_declaration_replay_is_idempotent_and_restore_keeps_contract(self):
        w, _ = make_contract_world('iee', 12, 'adequate')
        w.execute(w._journal[1].command)
        self.assertEqual(len(w._journal), 2)
        text = w.checkpoint();restored = ClosureWorld.restore(text)
        self.assertEqual(text, restored.checkpoint())
        for x in (w, restored):x.execute(Tick('same-next'))
        self.assertEqual(w._journal[-1], restored._journal[-1])

    def test_original_r20_checkpoint_retains_v1_and_exact_next_event(self):
        with gzip.open(ROOT/'evidence/r20/panel/continued_r19.checkpoint.json.gz', 'rt') as f:text = f.read()
        w = ClosureWorld.restore(text)
        self.assertEqual(text, w.checkpoint())
        self.assertIsNone(w.clearance_monitor.resource_contract)
        restored = ClosureWorld.restore(text)
        for x in (w, restored):x.execute(Tick('r21a:legacy-next'))
        self.assertEqual(w._journal[-1], restored._journal[-1])
        self.assertTrue(compare(w)['passed'])

    def test_reserved_seeds_are_not_development_inputs(self):
        with self.assertRaisesRegex(ValueError, 'reserved for R21C'):
            run_reference_policy('iee', 2001, 'inadequate')


class PaidIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch('hle.clearance_runtime.ClearanceMonitor.report', side_effect=AssertionError('evaluator consultation')):
            cls.w, cls.meta = run_reference_policy('iee', 12, 'adequate')
        cls.audit = audit_episode(cls.w, cls.meta)

    def test_all_thirteen_paid_development_cases_agree_independently(self):
        self.assertNotIn('error', self.meta)
        self.assertTrue(self.audit['integrity_passed'], self.audit['errors'])
        rows = self.audit['raw_clearance']['reference']['rows']
        self.assertEqual(len(rows), 13)
        self.assertTrue(all(r['passed'] for r in rows))
        for row in rows:
            if row['case'].endswith('increased_requirement'):
                self.assertEqual(row['comparison'], 'greater')
                self.assertEqual(row['resource_relation'], 'less_headroom')
                self.assertNotEqual(row['comparison_wallets']['prior'], row['comparison_wallets']['current'])

    def test_same_v1_workload_still_records_comparison_failure(self):
        w, meta = run_episode('iee', 12, 100000)
        rows = w.clearance_report()['rows']
        self.assertEqual(len(rows), 13)
        self.assertFalse(meta['cleared'])
        self.assertTrue(compare(w)['passed'])
        for row in rows:
            if row['case'].endswith('increased_requirement'):
                self.assertEqual(row['comparison'], 'incomparable')
                self.assertFalse(row['passed'])

    def test_spending_and_history_are_preserved_but_horizon_is_incomplete(self):
        self.assertTrue(self.audit['history']['passed'], self.audit['history'])
        self.assertGreater(len(self.meta['opportunities']), 0)
        self.assertLess(len(self.meta['opportunities']), 100)
        self.assertIsNotNone(self.meta['resource_stop'])
        self.assertFalse(self.audit['successful_full_horizon'])
        self.assertEqual(self.audit['resources']['credit_events'], [])
        self.assertGreater(self.audit['resources']['unfinished_count'], 0)

    def test_checkpoint_preserves_partial_work_and_v2_comparison(self):
        text = self.w.checkpoint();restored = ClosureWorld.restore(text)
        self.assertEqual(text, restored.checkpoint())
        self.assertEqual(restored.clearance_report(), self.w.clearance_report())
        self.assertTrue(compare(restored)['passed'])

    def test_duplicate_intervals_and_quiet_time_do_not_supply_horizon(self):
        rows = [copy.deepcopy(self.meta['opportunities'][0]) for _ in range(100)]
        result = horizon_audit(self.w, rows, 12, self.meta['cuts']['clearance'])
        self.assertFalse(result['passed']);self.assertTrue(result['errors'])
        self.assertFalse(horizon_audit(self.w, [], 12, self.meta['cuts']['clearance'])['passed'])

    def test_metadata_cannot_replace_real_paid_success(self):
        fake = copy.deepcopy(self.meta);fake.update(stage='finished', resource_stop=None)
        fake['scope']['history'] = 0
        checked = audit_episode(self.w, fake)
        self.assertFalse(checked['integrity_passed'])
        self.assertFalse(checked['successful_full_horizon'])

    def test_success_label_cannot_replace_physical_return_facts(self):
        altered = copy.copy(self.w);altered._journal = list(self.w._journal)
        row = self.meta['opportunities'][0]
        for i in range(row['start'], row['stop']):
            tx = altered._journal[i]
            if type(tx.command) is WorkshopCommand and tx.command.operation == 'return':
                changes = tuple(c for c in tx.event.changes if (c.after or c.before).relation != 'loan_active')
                self.assertLess(len(changes), len(tx.event.changes))
                altered._journal[i] = replace(tx, event=replace(tx.event, changes=changes))
        checked = horizon_audit(altered, [row], 12, self.meta['cuts']['clearance'])
        self.assertTrue(any('physical facts' in e for e in checked['errors']))

    def test_reference_detects_corrupt_live_wallet_reporting(self):
        with patch.object(self.w, 'clearance_report', wraps=self.w.clearance_report) as report:
            damaged = copy.deepcopy(self.w.clearance_report())
            damaged['rows'][0]['resource_contract']['actual_start'][0] += 1
            report.return_value = damaged
            self.assertFalse(compare(self.w)['passed'])

    def test_independent_policy_is_constructed_not_accepted_from_replay(self):
        w, meta = run_reference_policy('iee', 12, 'constrained_feasible')
        with patch('r21a_audit.run_reference_policy', wraps=run_reference_policy) as construct:
            gate, witness, other, audit = evaluate_feasibility(w, meta)
        construct.assert_called_once_with('iee', 12, 'constrained_feasible', evaluation=False)
        self.assertIsNot(w, witness)
        self.assertTrue(gate['same_scope']);self.assertFalse(gate['passed'])
        self.assertTrue(audit['integrity_passed']);self.assertIsNotNone(other['resource_stop'])

    def test_zero_budget_is_honest_deferral_not_clearance(self):
        w, meta = run_reference_policy('iee', 12, 'inadequate')
        audit = audit_episode(w, meta)
        self.assertTrue(audit['integrity_passed'])
        self.assertEqual(w._capacities, {})
        self.assertFalse(audit['successful_full_horizon'])
        self.assertIsNotNone(meta['resource_stop'])
        self.assertEqual(replay_witness(w)._journal, w._journal)


if __name__ == '__main__':unittest.main()
