from collections import Counter
from dataclasses import replace
import hashlib
import json
import unittest
from unittest.mock import patch

from hle.cards import CARDS, card
from hle.codec import canonical
from hle.contracts import WorkStatus
from hle.demo import ALICE, BOB
from hle.memory_records import MemoryCommand, RecallQuery
from hle.metabolism_records import Capability, MetabolicCommand
from hle.organization import OrganizationWorld
from .engine import Session, owned_wallet
from .learning import describe, read_meaning


def reach(session, predicate, chunk=16):
    for _ in range(20000):
        if predicate(session): return session
        if not session.step(chunk): raise AssertionError("unexpected resource stop")
    raise AssertionError("stage not reached")


class MeaningFidelity(unittest.TestCase):
    def test_consequences_create_meanings_and_only_embody_creates_capability(self):
        s = Session()
        self.assertEqual(s.assignments, {})
        self.assertIsNone(s.world.binding_head(BOB, "meaning:a"))
        reach(s, lambda s: s.episode == 4)
        for row in s.rows:
            self.assertIsNone(row["meaning_before"])
            self.assertEqual(row["meaning_after"]["check"], not row["actor_owned_at_demand"])
        caps = [(tx, r) for tx in s.world._journal for r in getattr(tx, "extra", ()) if type(r) is Capability]
        self.assertEqual(len(caps), 2)
        for tx, capability in caps:
            self.assertIsInstance(tx.command, MetabolicCommand)
            self.assertEqual(type(tx.command.payload).__name__, "EmbodyDraft")
            self.assertTrue(s.world.processing_record(BOB, capability.application).discrepancy)

    def test_opposite_histories_same_cues_opposite_substantive_expectations(self):
        a, b = [reach(Session(history=h), lambda s: s.episode == 12) for h in ("east_reliable", "west_reliable")]
        self.assertEqual(a.assignments, b.assignments)
        for scene in ("a", "b", "c", "d"):
            meanings = [read_meaning(s.world.memory_head(BOB, "meaning:" + scene), BOB) for s in (a, b)]
            self.assertEqual(meanings[0].cue, meanings[1].cue)
            self.assertNotEqual(meanings[0].check, meanings[1].check)
            self.assertNotEqual([x[0] for x in meanings[0].samples], [x[0] for x in meanings[1].samples])

    def test_shared_card_keeps_opposing_contextual_meanings(self):
        s = reach(Session(), lambda s: s.episode == 12)
        a, d = [read_meaning(s.world.memory_head(BOB, "meaning:" + c), BOB) for c in ("a", "d")]
        self.assertEqual(a.cue, d.cue)
        self.assertNotEqual(a.context, d.context)
        self.assertFalse(a.check); self.assertTrue(d.check)

    def test_context_mismatch_changes_real_recalled_guard_and_action(self):
        results = {}
        for policy in ("learned", "shuffled", "fixed_direct"):
            s = reach(Session(policy=policy), lambda s: s.episode == 14)
            results[policy] = s.rows[13]
        self.assertIsNotNone(results["learned"]["guard"])
        self.assertEqual(results["learned"]["actions"][0]["operation"], "r2.inspect")
        self.assertTrue(results["learned"]["appropriate"])
        for policy in ("shuffled", "fixed_direct"):
            self.assertIsNone(results[policy]["guard"])
            self.assertEqual(results[policy]["actions"][0]["operation"], "r2.transfer")
            self.assertEqual(results[policy]["invalid_transfers"], 1)

    def test_reversal_updates_meaning_and_frozen_control_keeps_old_binding(self):
        a, b = [Session(policy=p).run() for p in ("learned", "frozen")]
        self.assertTrue(all(r["appropriate"] for r in a.rows[32:]))
        self.assertEqual(sum(r["appropriate"] for r in b.rows[32:]), 4)
        self.assertTrue(a.rows[32]["meaning_before"]["check"])
        self.assertFalse(b.rows[32]["meaning_before"]["check"])
        self.assertEqual(b.world.binding_head(BOB, "meaning:a").ref.revision, 3)
        self.assertEqual(a.world.binding_head(BOB, "meaning:a").ref.revision, 10)

    def test_write_alone_does_not_redirect_exact_binding(self):
        s = reach(Session(), lambda s: s.episode == 4 and s.stage == "learn")
        old = s.world.binding_head(BOB, "meaning:a")
        reach(s, lambda s: s.stage == "publish")
        self.assertNotEqual(s.proposed.ref, old.target)
        self.assertEqual(s.world.binding_head(BOB, "meaning:a"), old)
        q = RecallQuery(s.cues, s.contexts["a"], s.world.now, relation="meaning.scene")
        s.world.execute(MemoryCommand("test-old-query", "test-old-query", BOB, q))
        result = s.world.recall_result(BOB, s.world.memory_job(BOB, "test-old-query").result)
        self.assertEqual(result.hits[0].memory, old.target)
        s.step(16)
        self.assertEqual(s.world.resolve_binding(BOB, old.ref).target, old.target)
        self.assertEqual(s.world.binding_head(BOB, "meaning:a").target, s.proposed.ref)

    def test_unpaid_meaning_write_and_bind_cannot_activate_or_advance_phase(self):
        for stage in ("learn", "publish"):
            full = reach(Session(), lambda s: s.stage == stage, chunk=1)
            limited = Session(budget=full.spent + 1).run(chunk=1)
            self.assertEqual(limited.stage, stage)
            self.assertEqual(limited.phases, 2)
            self.assertIsNone(limited.world.binding_head(BOB, "meaning:a"))
            self.assertEqual(limited.assignments, {})
            if stage == "learn": self.assertIsNone(limited.world.memory_head(BOB, "meaning:a"))
            self.assertFalse(limited.step(1))
            limited.credit(50, 50)
            reach(limited, lambda s: s.episode == 1, chunk=1)
            self.assertEqual(limited.phases, 3)
            self.assertIsNotNone(limited.world.binding_head(BOB, "meaning:a"))

    def test_each_resource_dimension_gates_paid_recall(self):
        for energy, time in ((0, 5), (5, 0)):
            s = Session(budget=energy, time_budget=time).run(chunk=1)
            self.assertEqual(s.phases, 0)
            self.assertIsNone(s.meaning_recall)
            s.credit(1 if energy == 0 else 0, 1 if time == 0 else 0)
            s.step(1)
            self.assertIsNotNone(s.meaning_recall)
            self.assertEqual(s.stage, "choose")

    def test_exact_retry_does_not_charge_or_publish_twice(self):
        s = Session(); s.step(1); s.step(1)
        command = s.world._journal[-1].command
        cp = s.checkpoint()
        s.world.execute(command)
        self.assertEqual(s.checkpoint(), cp)

    def test_private_meanings_and_sources_reject_other_owner(self):
        s = reach(Session(), lambda s: s.episode == 1)
        meaning = s.world.memory_head(BOB, "meaning:a")
        with self.assertRaises(ValueError): s.world.read_revision(ALICE, meaning.ref)
        with self.assertRaises(ValueError): read_meaning(meaning, ALICE)
        binding = s.world.binding_head(BOB, "meaning:a")
        with self.assertRaises(ValueError): s.world.resolve_binding(ALICE, binding.ref)
        with self.assertRaises(ValueError):
            s.world.execute(MemoryCommand("foreign", "foreign", ALICE,
                RecallQuery(s.cues, s.contexts["a"], s.world.now)))

    def test_participant_stages_do_not_consult_evaluator_owner(self):
        s = Session()
        while s.episode < 8:
            if s.stage == "start": s.step(16)
            else:
                with patch("hle.world.TruthView.current_fact", side_effect=AssertionError("participant read Truth")):
                    s.step(16)

    def test_hidden_future_history_cannot_change_current_choice_before_feedback(self):
        a, b = [reach(Session(history=h), lambda s: s.stage == "decision") for h in ("east_reliable", "west_reliable")]
        self.assertEqual((a.check, a.cue, a.selected, a.target), (b.check, b.cue, b.selected, b.target))
        # Different hidden ownership has not supplied either actor a learned answer.
        self.assertIsNone(a.previous); self.assertIsNone(b.previous)

    def test_checkpoint_at_all_paid_boundaries_continues_identically(self):
        s, seen = Session(), set()
        while s.episode < 1:
            stage = s.stage
            if stage not in ("start", "choose", "begin", "close"):
                getter = s.world.processing_job if stage in ("theory", "apply", "embody") else s.world.memory_job
                job = getter(BOB, f"m:0:{stage}")
                stage += ":partial" if job and job.completed_units and job.outcome != WorkStatus.COMPLETED else ":start"
            if stage not in seen:
                other = Session.restore(s.checkpoint()); seen.add(stage)
                s.step(1); other.step(1)
                self.assertEqual(s.checkpoint(), other.checkpoint())
            else: s.step(1)
        self.assertTrue({"theory:partial", "apply:partial", "embody:partial", "decision:partial", "learn:partial", "publish:partial"} <= seen)

    def test_checkpoint_inspection_before_conditional_transfer(self):
        s = reach(Session(), lambda s: s.episode == 21 and s.stage == "apply")
        for _ in range(200):
            job = s.world.processing_job(BOB, "m:21:apply")
            if job and job.enactments and job.result is None: break
            s.step(1)
        else: self.fail("conditional transfer boundary not found")
        other = Session.restore(s.checkpoint())
        s.step(1); other.step(1)
        self.assertEqual(s.checkpoint(), other.checkpoint())

    def test_rehashed_forged_meaning_state_is_rejected(self):
        s = reach(Session(), lambda s: s.episode == 1)
        cp = json.loads(s.checkpoint())
        cp["body"]["controller"]["assignments"]["a"] = "arcana:21"
        cp["sha256"] = hashlib.sha256(canonical(cp["body"]).encode()).hexdigest()
        with self.assertRaises(ValueError): Session.restore(canonical(cp))

    def test_quiet_and_recall_preserve_experience_not_post_transfer_mislabel(self):
        s = reach(Session(), lambda s: s.episode == 14)
        self.assertTrue(s.rows[0]["appropriate"])
        self.assertEqual(s.rows[0]["meaning_after"]["samples"], [False])
        self.assertEqual(s.rows[12]["meaning_before"]["samples"], [False, False, False])
        self.assertTrue(s.rows[13]["appropriate"])
        self.assertEqual(len([tx for tx in s.world._journal if tx.command and tx.command.command_id.startswith("quiet:")]), 10)
        self.assertEqual(len({r["item"] for r in s.rows}), len(s.rows))

    def test_anonymous_display_keeps_execution_identical_and_card_geometry_intact(self):
        a, b = [Session(labels=labels).run() for labels in ("cards", "anonymous")]
        self.assertEqual(a.rows, b.rows)
        self.assertEqual(a.world.checkpoint(), b.world.checkpoint())
        self.assertNotEqual(a.result()["display_names"], b.result()["display_names"])
        self.assertEqual((a.phases, a.phase), (120, (3, 0)))
        self.assertEqual(len(CARDS), 130)
        self.assertEqual([card(f"arcana:{n}").folded_location for n in (19, 20, 21)], [1, 2, 3])

    def test_independent_journal_replay_and_budget_receipts(self):
        s = Session(budget=600).run()
        costs = Counter()
        for tx in s.world._journal:
            if tx.command and tx.command.command_id.startswith("paid:"):
                for work in tx.works:
                    for amount in work.charged: costs[amount.unit.key] += amount.amount
        self.assertEqual(costs["r2.energy_quantum"], s.spent)
        self.assertEqual(costs["r2.time_quantum"], s.spent)
        self.assertEqual(s.spent + owned_wallet(s.world)[0], 600)
        self.assertEqual(s.external_credit, s.external_spent)
        self.assertFalse(s.done)
        self.assertEqual(OrganizationWorld.restore(s.world.checkpoint()).checkpoint(), s.world.checkpoint())


if __name__ == "__main__": unittest.main(verbosity=2)
