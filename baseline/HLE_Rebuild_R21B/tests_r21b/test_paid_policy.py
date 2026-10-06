import copy
import hashlib
import json
from dataclasses import replace
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from hle.clearance_records import EpisodeResourceContract, WithdrawEvidence, PartnerShift
from hle.clearance_demo import offers, finish_order, command
from hle.closure import ClosureWorld
from hle.contracts import WorkStatus, Ref, Kind
from hle.individuation_demo import do, run_order
from hle.individuation_records import CircuitCommand
from hle.paid_work import semantic_key
from hle.world_records import Credit, Tick
from r21b_policy import run_candidate, run_reference_policy, make_contract_world, protocol, PROTOCOL_ID, PROTOCOL_SHA256, BUDGETS
from r21b_audit import audit_episode, horizon_audit, evaluate_feasibility
from r21b_work_audit import audit_paid_work
from r21_workloads import make_world


class Declaration(unittest.TestCase):
    def test_frozen_contract_retains_old_protocols_and_release_seeds(self):
        p = protocol()
        for file, key in [('docs/r21/Protocol_R21_v1.json', 'preserved_v1_sha256'),
                          ('docs/r21a/Protocol_R21_v2.json', 'preserved_v2_sha256')]:
            self.assertEqual(hashlib.sha256((ROOT/file).read_bytes()).hexdigest(), p[key])
        self.assertEqual(p['evaluation']['evaluation_seeds'], list(range(2001, 2011)))
        self.assertEqual(p['evaluation']['individual_episodes'], 480)
        self.assertEqual(p['evaluation']['minimum_constrained_success_fraction'], [1, 1])

    def test_old_small_wallet_cannot_be_relabelled_as_new_positive_regime(self):
        w, _ = make_world('iee', 12, 20000)
        with self.assertRaises(ValueError):
            w.execute(EpisodeResourceContract('contract', 'episode', 'constrained_feasible', 12, PROTOCOL_ID, PROTOCOL_SHA256))
        self.assertEqual(len(w._journal), 1)

    def test_unknown_policy_digest_and_late_enrollment_rejected(self):
        for late in (False, True):
            w, _ = make_world('iee', 12, BUDGETS['adequate'])
            if late: w.execute(Tick('earlier'))
            with self.assertRaises(ValueError):
                w.execute(EpisodeResourceContract('c', 'e', 'adequate', 12, PROTOCOL_ID,
                                                  PROTOCOL_SHA256 if late else '0'*64))

    def test_held_out_seeds_rejected_by_both_constructions(self):
        for fn in (run_candidate, run_reference_policy):
            with self.assertRaisesRegex(ValueError, 'reserved'): fn('iee', 2001, 'inadequate')

    def test_zero_budget_cannot_compile_or_acquire(self):
        w, m = run_candidate('sli', 11, 'inadequate')
        a = audit_episode(w, m)
        self.assertTrue(a['integrity_passed'])
        self.assertFalse(a['successful_full_horizon'])
        self.assertFalse(w._paid_option_cache)
        self.assertFalse(w._capacities)
        self.assertFalse(w._aspect_caps)

    def test_topup_rejected_by_runtime(self):
        w, _ = make_contract_world('iee', 12, 'adequate')
        with self.assertRaisesRegex(ValueError, 'top-ups'):
            w.execute(Credit('credit', w.config.actors[0], 1, 1, 'forbidden'))


class IntegratedPolicy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch('hle.clearance_runtime.ClearanceMonitor.report', side_effect=AssertionError('observer consulted')):
            cls.w, cls.meta = run_candidate('iee', 12, 'constrained_feasible')
        cls.audit = audit_episode(cls.w, cls.meta)

    @classmethod
    def training_world(cls):
        w, _ = make_contract_world('iee', 12, 'constrained_feasible')
        for tx in cls.w._journal[2:cls.meta['cuts']['aspects']]:
            w.execute(tx.command)
            if w._journal[-1] != tx: raise AssertionError('training prefix changed')
        return w

    @staticmethod
    def offered(w, prefix):
        f = offers(w, 'selection.equal_renewal', prefix)[0]
        w.execute(f); do(w, f.key, f.partner, 'menu')
        return f

    def test_full_paid_episode_preserves_every_acceptance_obligation(self):
        a = self.audit
        self.assertTrue(a['successful_full_horizon'], a['errors'])
        self.assertTrue(a['history']['passed'])
        self.assertEqual(len(a['raw_clearance']['reference']['rows']), 13)
        self.assertTrue(all(r['passed'] for r in a['raw_clearance']['reference']['rows']))
        self.assertEqual(a['sustained']['eligible'], 100)
        self.assertEqual(a['sustained']['demand_changes'], 2)
        self.assertEqual(a['resources']['unfinished_count'], 0)
        self.assertFalse(a['resources']['credit_events'])
        self.assertGreater(a['paid_work']['reused_options'], 1000)

    def test_separately_executed_reference_is_a_successful_witness(self):
        gate, other, meta, checked = evaluate_feasibility(self.w, self.meta)
        self.assertTrue(gate['passed'])
        self.assertIsNot(other, self.w)
        self.assertEqual(meta['construction'], 'independent_from_genesis')
        self.assertTrue(checked['successful_full_horizon'])

    def test_audit_ignores_runtime_cache_and_choice_helpers(self):
        with patch('hle.paid_work.semantic_key', side_effect=AssertionError('runtime key consulted')), \
             patch('hle.clearance.ClearanceWorld._select_work_option', side_effect=AssertionError('runtime selector consulted')):
            self.assertTrue(audit_paid_work(self.w)['passed'])

    def test_duplicate_horizon_rows_cannot_replace_later_paid_opportunities(self):
        rows = copy.deepcopy(self.meta['opportunities']); rows[10] = rows[9]
        a = horizon_audit(self.w, rows, 12, self.meta['cuts']['clearance'])
        self.assertFalse(a['passed'])

    def test_forged_paid_extent_fails_independent_audit(self):
        w = copy.copy(self.w); w._journal = list(self.w._journal)
        i = next(i for i,t in enumerate(w._journal) if type(t.command) is CircuitCommand and t.command.operator == 'choose')
        t = w._journal[i]; plan = replace(t.job.plan, content_units=t.job.plan.content_units+1)
        w._journal[i] = replace(t, job=replace(t.job, plan=plan))
        self.assertFalse(audit_paid_work(w)['passed'])

    def test_renamed_instance_and_shifted_epoch_reuse_exact_same_semantics(self):
        w = self.training_world(); f = self.offered(w, 'warm'); finish_order(w, f.key)
        f2 = self.offered(w, 'repeat'); order = w._circuit_orders[f2.key]
        extent, basis = w._choose_quote(order)
        self.assertEqual(extent, 2+2*len(f2.options)+1)
        self.assertTrue(basis)
        for option in f2.options:
            k = semantic_key(w.config.context, f2, option, w._records[order.menu])
            self.assertIsNotNone(w._paid_entry(f2.learner, k))

    def test_changed_inputs_cannot_collide_with_reused_predicates(self):
        w = self.training_world(); f = self.offered(w, 'keys'); order = w._circuit_orders[f.key]
        menu = w._records[order.menu]; o = f.options[-1]
        original = semantic_key(w.config.context, f, o, menu)
        changes = [dict(available=False),dict(condition='dirty'),dict(observed_epoch=o.observed_epoch+1),
            dict(start=7),dict(ready_at=8),dict(duration=3),dict(load=2),dict(output=1),dict(cost=1),
            dict(claims=(('station','one'),('station','two'))),dict(license='exclusive')]
        for change in changes:
            with self.subTest(change=change):
                self.assertNotEqual(original, semantic_key(w.config.context, f, replace(o, **change), menu))
        for change in [dict(partner=f.helper),dict(due=f.due+1),dict(budget=f.budget+1),
                       dict(credits=f.credits+1),dict(minimum_output=f.minimum_output+1)]:
            # Preserve distinct identities for the partner swap.
            if 'partner' in change: change['helper'] = f.partner
            self.assertNotEqual(original, semantic_key(w.config.context, replace(f, **change), o, menu))

    def test_partial_work_neither_populates_cache_nor_publishes_choice(self):
        w = self.training_world(); f = self.offered(w, 'partial')
        before = copy.deepcopy(w._paid_option_cache)
        c = replace(command(w, f.key, f.learner, 'choose'), work_limit=1)
        e = w.execute(c)
        self.assertEqual(e.outcome, WorkStatus.PARTIAL)
        self.assertEqual(w._paid_option_cache, before)
        self.assertIsNone(w._circuit_orders[f.key].chosen)
        text = w.checkpoint(); r = ClosureWorld.restore(text)
        self.assertEqual(text, r.checkpoint())
        for target in (w, r): target.execute(replace(c, command_id='complete-partial', work_limit=10000))
        self.assertEqual(w._journal[-1], r._journal[-1])
        self.assertEqual(w._paid_option_cache, r._paid_option_cache)
        self.assertEqual(w._journal[-1].event.outcome, WorkStatus.COMPLETED)

    def test_withdrawn_paid_source_is_not_reused(self):
        w = self.training_world(); f = self.offered(w, 'warm-withdraw'); finish_order(w, f.key)
        f2 = self.offered(w, 'cold-after-withdraw'); order = w._circuit_orders[f2.key]
        before, basis = w._choose_quote(order)
        source = next(r for r in basis if r.kind == Kind.EVENT)
        w.execute(WithdrawEvidence('withdraw-paid-source', source, 'test exact paid-source withdrawal'))
        after, new_basis = w._choose_quote(order)
        self.assertGreater(after, before)
        self.assertNotIn(source, new_basis)

    def test_withdrawal_during_partial_reuse_fails_without_refund(self):
        w = self.training_world(); f = self.offered(w, 'warm-partial'); finish_order(w, f.key)
        f2 = self.offered(w, 'reuse-partial')
        c = replace(command(w, f2.key, f2.learner, 'choose'), work_limit=1)
        w.execute(c); source = next(r for r in w._circuit_jobs[f2.learner,c.task_id].basis if r.kind == Kind.EVENT)
        paid = w._wallets[f2.learner].energy
        w.execute(WithdrawEvidence('withdraw-during-work', source, 'test invalidation during paid work'))
        w.execute(replace(c, command_id='continue-invalid', work_limit=10000))
        self.assertEqual(w._journal[-1].event.outcome, WorkStatus.FAILED)
        self.assertIsNone(w._circuit_orders[f2.key].chosen)
        self.assertLessEqual(w._wallets[f2.learner].energy, paid)

    def test_changed_partner_schedule_still_causes_a_fresh_physical_failure(self):
        w = self.training_world(); f = self.offered(w, 'stale-consent')
        do(w, f.key, f.learner, 'choose')
        chosen = next(o for o in f.options if o.key == w._circuit_orders[f.key].chosen)
        w.execute(PartnerShift('shift-after-choice', f.partner, (chosen.start,)))
        do(w, f.key, f.learner, 'apply')
        signal = w._records[w._circuit_orders[f.key].outcome]
        self.assertFalse(signal.success)
        self.assertIn('fe', signal.errors)

    def test_withdrawn_capacity_cannot_be_replaced_by_cached_predicates(self):
        w = self.training_world(); f = self.offered(w, 'missing-aspect')
        do(w, '', f.learner, 'withdraw', aspect='si')
        do(w, f.key, f.learner, 'choose')
        order = w._circuit_orders[f.key]
        self.assertLess(len(order.uses), 8)
        self.assertNotIn('si', w._current_aspects(f.learner))

    def test_new_concurrent_offer_invalidates_a_partial_choice_quote(self):
        w = self.training_world(); f = self.offered(w, 'partial-group')
        c = replace(command(w, f.key, f.learner, 'choose'), work_limit=1)
        w.execute(c)
        later = offers(w, 'selection.equal_renewal', 'new-group-member')[0]
        later = replace(later, epoch=f.epoch,
                        options=tuple(replace(o, observed_epoch=f.epoch) for o in later.options))
        w.execute(later)
        w.execute(replace(c, command_id='continue-changed-group', work_limit=10000))
        self.assertEqual(w._journal[-1].event.outcome, WorkStatus.FAILED)
        self.assertIsNone(w._circuit_orders[f.key].chosen)


if __name__ == '__main__': unittest.main()
