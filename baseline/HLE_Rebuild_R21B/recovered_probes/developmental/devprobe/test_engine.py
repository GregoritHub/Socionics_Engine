from collections import Counter
from dataclasses import replace
import hashlib
import json
import unittest
from unittest.mock import patch

from hle.cards import CARDS, card
from hle.codec import canonical
from hle.crux import Perspective
from hle.demo import BOB
from hle.metabolism_records import Capability, MetabolicCommand
from hle.organization import OrganizationWorld
from devprobe.engine import Session, owned_wallet


def reach(session, predicate, chunk=1):
    for _ in range(10000):
        if predicate(session): return session
        if not session.step(chunk): raise AssertionError("unexpected resource stop")
    raise AssertionError("stage not reached")


class DevelopmentalFidelity(unittest.TestCase):
    def test_first_discrepancy_creates_real_embodied_capability(self):
        s = reach(Session(), lambda s: s.episode == 1)
        row = s.rows[0]
        self.assertTrue(row["discrepancy"])
        self.assertIsNone(row["guard"])
        self.assertEqual(row["invalid_transfers"], 1)
        self.assertEqual(len(row["capabilities"]), 1)
        caps = [(tx, r) for tx in s.world._journal for r in getattr(tx, "extra", ()) if type(r) is Capability]
        self.assertEqual(len(caps), 1)
        tx, capability = caps[0]
        self.assertIsInstance(tx.command, MetabolicCommand)
        self.assertEqual(type(tx.command.payload).__name__, "EmbodyDraft")
        application = s.world.processing_record(BOB, capability.application)
        self.assertTrue(application.discrepancy)

    def test_cross_object_feedback_ablation_changes_actual_action(self):
        controls = {}
        for policy in ("coupled", "episode_only", "feedback_off", "once_per_outer"):
            s = reach(Session(policy=policy), lambda s: s.episode == 2)
            controls[policy] = s.rows[1]
            self.assertTrue(s.rows[1]["heldout"])
            self.assertEqual(s.rows[1]["prediction"], "bob")
        self.assertEqual(controls["coupled"]["actions"][0]["operation"], "r2.inspect")
        self.assertTrue(controls["coupled"]["appropriate"])
        for p in ("episode_only", "feedback_off", "once_per_outer"):
            self.assertEqual(controls[p]["actions"][0]["operation"], "r2.transfer")
            self.assertEqual(controls[p]["invalid_transfers"], 1)

    def test_new_memory_does_not_redirect_original_binding(self):
        s = Session()
        old = s.world.binding_head(BOB, "original:0")
        reach(s, lambda s: s.episode == 1)
        current = s.world.binding_head(BOB, "current:0")
        self.assertEqual(s.world.binding_head(BOB, "original:0"), old)
        self.assertNotEqual(current.target, old.target)
        self.assertEqual(s.world.resolve_binding(BOB, old.ref).target, old.target)

    def test_unpaid_publication_holds_world_phase(self):
        full = reach(Session(), lambda s: s.stage == "publish")
        limited = Session(budget=full.spent + 1).run(chunk=1)
        self.assertEqual(limited.stage, "publish")
        self.assertEqual(limited.phases, 2)
        self.assertIsNone(limited.world.binding_head(BOB, "shared"))
        self.assertFalse(limited.step(1))
        self.assertEqual(limited.phases, 2)
        limited.credit(1, 1)
        limited.step(1); limited.step(1)
        self.assertEqual((limited.episode, limited.phases), (1, 3))
        self.assertIsNotNone(limited.world.binding_head(BOB, "shared"))

    def test_energy_and_time_each_gate_progress(self):
        for energy, time in ((0, 5), (5, 0)):
            s = Session(budget=energy, time_budget=time).run(chunk=1)
            self.assertEqual(s.phases, 0)
            self.assertIsNone(s.recall)
            s.credit(2 if energy == 0 else 0, 2 if time == 0 else 0)
            self.assertTrue(s.step(1)); self.assertTrue(s.step(1))
            self.assertIsNotNone(s.recall)

    def test_exact_retry_no_double_charge_or_output(self):
        s = Session(); s.step(1); s.step(1)
        command = s.world._journal[-1].command
        checkpoint = s.checkpoint()
        s.world.execute(command)
        self.assertEqual(s.checkpoint(), checkpoint)

    def test_checkpoint_every_stage_and_partial_processing_continues(self):
        s = Session()
        seen = set()
        for _ in range(600):
            if s.episode >= 1: break
            key = s.stage
            if key in ("theory", "apply", "embody"):
                job = s.world.processing_job(BOB, f"d:0:{key}")
                key += ":partial" if job and job.completed_units else ":start"
            if key not in seen:
                restored = Session.restore(s.checkpoint())
                seen.add(key)
                s.step(1); restored.step(1)
                self.assertEqual(restored.checkpoint(), s.checkpoint())
            else: s.step(1)
        self.assertTrue({"recall", "theory:partial", "apply:partial", "embody:partial", "rebind", "publish", "close"} <= seen)

    def test_checkpoint_after_inspection_before_conditional_transfer(self):
        s = reach(Session(), lambda s: s.episode == 2 and s.stage == "apply")
        for _ in range(200):
            job = s.world.processing_job(BOB, "d:2:apply")
            if job and job.enactments and job.result is None: break
            s.step(1)
        else: self.fail("conditional action boundary not found")
        restored = Session.restore(s.checkpoint())
        s.step(1); restored.step(1)
        self.assertEqual(s.checkpoint(), restored.checkpoint())

    def test_rehashed_invented_controller_rejected(self):
        s = Session(); s.step(1)
        cp = json.loads(s.checkpoint())
        cp["body"]["controller"]["phases"] = 3
        cp["sha256"] = hashlib.sha256(canonical(cp["body"]).encode()).hexdigest()
        with self.assertRaises(ValueError): Session.restore(canonical(cp))

    def test_paid_stages_do_not_consult_evaluator_owner(self):
        s = Session()
        for _ in range(1000):
            if s.episode == 2: break
            if s.stage == "start": s.step(16)
            else:
                with patch("hle.world.TruthView.current_fact", side_effect=AssertionError("participant read Truth")):
                    s.step(16)
        self.assertEqual(s.episode, 2)

    def test_retention_survives_quiet_interval_and_new_objects(self):
        s = Session().run()
        self.assertEqual(s.rows[1]["guard"], s.rows[6]["guard"])
        self.assertEqual(s.rows[1]["guard"], s.rows[11]["guard"])
        self.assertTrue(s.rows[11]["heldout"])
        self.assertTrue(s.rows[11]["appropriate"])
        ticks = [tx for tx in s.world._journal if tx.command and tx.command.command_id.startswith("quiet:")]
        self.assertEqual(len(ticks), 10)
        report = s.result()["reports"][-1]
        self.assertEqual(report["retained_capacity"], "established")
        self.assertNotIn("cleared", report["shell"])
        self.assertNotEqual(report["closure"], "established")

    def test_joint_clock_cards_and_real_perspective_returns(self):
        s = Session().run()
        self.assertEqual((s.phases, s.phase, s.episode), (36, (0, 0), 12))
        self.assertEqual(s.phases // 9, 4)
        self.assertEqual(s.phases // 3, 12)
        self.assertTrue(all(e["end_perspective"] == Perspective.I.value for e in s.rows))
        self.assertEqual(len(CARDS), 130)
        self.assertEqual([card(f"arcana:{r}").folded_location for r in (19, 20, 21)], [1, 2, 3])

    def test_generic_stage_names_leave_complete_execution_identical(self):
        a = Session(policy="coupled").run()
        b = Session(policy="generic_coupled").run()
        self.assertEqual(a.rows, b.rows)
        self.assertEqual(a.world.checkpoint(), b.world.checkpoint())

    def test_work_receipts_independently_reconcile_wallet(self):
        s = Session(budget=600).run()
        amounts = Counter()
        for tx in s.world._journal:
            command = tx.command
            if command is not None and command.command_id.startswith("paid:"):
                for w in tx.works:
                    for amount in w.charged: amounts[amount.unit.key] += amount.amount
        self.assertEqual(amounts["r2.energy_quantum"], s.spent)
        self.assertEqual(amounts["r2.time_quantum"], s.spent)
        self.assertEqual(s.spent + owned_wallet(s.world)[0], 600)
        self.assertEqual(s.external_credit, s.external_spent)
        self.assertFalse(s.done)
        self.assertNotEqual(s.stage, "done")


if __name__ == "__main__": unittest.main(verbosity=2)
