from dataclasses import FrozenInstanceError, replace
from itertools import product
import json
import unittest

from hle.codec import dumps, loads
from hle.contracts import (ActionRequest, ClaimStatus, EvidenceStatus, Kind,
    Moment, Proposition, Ref, TimeScope, WorkStatus)
from hle.demo import ALICE, BOB, BOX, TOOL, ROOM, config, request, run_demo
from hle.world import World
from hle.world_records import (Attempt, Correction, Credit, Entity, INSPECT,
    MemoryDraft, MessageDraft, RETAIN, SEND, TRANSFER, Tick, Wallet, Witness)
from .reference_world import fold, fact_at
from .support import rules


def claim(world, owner=ALICE, item=BOX, relation="owned_by"):
    return Proposition(item, relation, owner, ROOM, TimeScope(world.now, None))


def transfer(world, actor=ALICE, recipient=BOB, item=BOX, key="transfer", task=None):
    return world.execute(Attempt(key, task or key, request(actor, TRANSFER, (item, recipient))))


def retain(world, actor=BOB, content=None, key="belief", local="account", basis=()):
    return world.execute(Attempt(key, key, request(actor, RETAIN, basis=basis),
        memory=MemoryDraft(local, (claim(world),) if content is None else content,
            ClaimStatus.ENDORSED, "explicit participant fixture account")))


class WorldTests(unittest.TestCase):
    @rules("W01", "E02")
    def test_exact_revisions_preserve_identity_and_labels(self):
        new_box = Ref(Kind.ENTITY, "box", 2)
        cfg = config()
        world = World(replace(cfg, entities=cfg.entities + (Entity(new_box, "Renamed box", "object"),)))
        self.assertEqual(world.truth.resolve(BOX).label, "Box")
        self.assertEqual(world.truth.resolve(new_box).label, "Renamed box")
        self.assertIsNone(world.truth.current_fact(new_box, "owned_by", ROOM))
        with self.assertRaises(KeyError):
            world.truth.resolve(Ref(Kind.ENTITY, "box", 3))
        snapshot = world.checkpoint()
        with self.assertRaises(ValueError):
            world.apply(request(ALICE, INSPECT, (new_box,)))
        self.assertEqual(snapshot, world.checkpoint())

    @rules("W01")
    def test_config_rejects_ambiguous_or_invalid_identity(self):
        cfg = config()
        variants = [dict(actors=(ALICE, ALICE)), dict(wallets=(cfg.wallets[0], cfg.wallets[0])),
            dict(ownership=(cfg.ownership[0], cfg.ownership[0])),
            dict(message_links=((BOB, BOB),)),
            dict(entities=cfg.entities + (Entity(Ref(Kind.ENTITY, "box", 3), "Skipped", "object"),))]
        for variant in variants:
            with self.subTest(variant=variant), self.assertRaises(ValueError):
                replace(cfg, **variant)

    @rules("W02", "W06")
    def test_all_216_three_action_sequences_against_independent_oracle(self):
        choices = ((ALICE, TRANSFER, (BOX, BOB)), (BOB, TRANSFER, (BOX, ALICE)),
            (ALICE, TRANSFER, (TOOL, BOB)), (BOB, TRANSFER, (TOOL, ALICE)),
            (ALICE, INSPECT, (BOX,)), (BOB, INSPECT, (TOOL,)))
        for sequence in product(range(6), repeat=3):
            world = World(config())
            owners, budget = {BOX: ALICE, TOOL: BOB}, {ALICE: 20, BOB: 20}
            for index, token in enumerate(sequence):
                actor, operation, inputs = choices[token]
                succeeds = operation == INSPECT or owners[inputs[0]] == actor
                budget[actor] -= 1 if operation == INSPECT else 2
                if succeeds and operation == TRANSFER:
                    owners[inputs[0]] = inputs[1]
                event = world.execute(Attempt(str(index), str(index), request(actor, operation, inputs)))
                self.assertEqual(event.outcome, WorkStatus.COMPLETED if succeeds else WorkStatus.FAILED)
                self.assertEqual(world.truth.wallet(actor), Wallet(actor, budget[actor], budget[actor]))
                for item in (BOX, TOOL):
                    self.assertEqual(world.truth.current_fact(item, "owned_by", ROOM).object, owners[item])
                self.assertEqual(world.state(), fold(world.config, world.truth.journal()))

    @rules("W03")
    def test_hidden_owner_and_evaluator_checks_do_not_change_input_or_action(self):
        left, right = World(config()), World(config())
        transfer(left)
        transfer(right, recipient=ALICE)  # same public clock/cost, hidden unsuccessful outcome
        left.truth.check(claim(left), left.now)
        lv, lc = left.participant_input(BOB)
        rv, rc = right.participant_input(BOB)
        self.assertEqual((lv, lc), (rv, rc))
        class Policy:
            def choose(self, view):
                return request(view.actor, INSPECT, (BOX,), (view.observations[-1].ref,))
        self.assertEqual(Policy().choose(lv), Policy().choose(rv))
        for world in (left, right):
            world.run_policy(BOB, Policy())
        self.assertNotEqual(left.participant_input(BOB, lc)[0].observations,
                            right.participant_input(BOB, rc)[0].observations)
        self.assertEqual(left.participant_input(BOB, lc)[0].observations[-1].content[-1].object, BOB)

    @rules("W03", "W04")
    def test_full_and_occurrence_witnesses_are_different_projections(self):
        for mode in ("full", "occurrence"):
            world = World(config(witnesses=(Witness(BOB, BOX, mode),)))
            cursor = world.participant_input(BOB)[1]
            event = transfer(world)
            observation = world.participant_input(BOB, cursor)[0].observations[0]
            self.assertEqual(observation.source, event.ref)
            self.assertEqual(observation.content, (event.changes[0].after,) if mode == "full" else ())

    @rules("W03")
    def test_participant_values_are_immutable_and_own_memory_only(self):
        world = World(config())
        retain(world, actor=ALICE)
        view, _ = world.participant_input(BOB)
        self.assertFalse(view.own_memories)
        self.assertFalse(hasattr(view, "truth"))
        self.assertFalse(hasattr(view, "world"))
        with self.assertRaises(FrozenInstanceError):
            view.available[0].amount = 999
        with self.assertRaises(FrozenInstanceError):
            view.observations[0].content[0].object = BOB
        self.assertEqual(world.truth.wallet(BOB).energy, 20)

    @rules("W03", "W04")
    def test_other_actor_evidence_and_forged_evidence_reject_atomically(self):
        world = World(config())
        retain(world, actor=ALICE)
        private = world.participant_input(ALICE)[0]
        for ref in (private.observations[0].ref, private.own_memories[0].ref,
                    Ref(Kind.OBSERVATION, "future", 1)):
            before = world.checkpoint()
            with self.assertRaises(ValueError):
                world.apply(request(BOB, INSPECT, (BOX,), (ref,)))
            self.assertEqual(before, world.checkpoint())

    @rules("W03")
    def test_policy_cannot_impersonate_another_actor(self):
        world = World(config())
        class BadPolicy:
            def choose(self, view):
                return request(ALICE, INSPECT, (BOX,))
        before = world.checkpoint()
        with self.assertRaises(ValueError):
            world.run_policy(BOB, BadPolicy())
        self.assertEqual(before, world.checkpoint())

    @rules("W04", "W05")
    def test_false_message_is_delivered_without_becoming_world_fact_or_belief(self):
        world = World(config())
        content = (claim(world, BOB),)
        cursor = world.participant_input(BOB)[1]
        evidence = world.participant_input(ALICE)[0].observations[0].ref
        event = world.execute(Attempt("send", "send", request(ALICE, SEND, (BOB,), (evidence,)),
            message=MessageDraft(content)))
        view = world.participant_input(BOB, cursor)[0]
        observation = view.observations[0]
        message = world.truth.resolve(observation.source)
        self.assertEqual((message.sender, message.receiver, message.event, message.based_on), (ALICE, BOB, event.ref, (evidence,)))
        self.assertEqual(observation.content, content)
        self.assertIn("unverified", observation.uncertainty)
        self.assertEqual(world.truth.check(content[0], world.now).status, EvidenceStatus.FAILED)
        self.assertFalse(view.own_memories)

    @rules("W04", "W06")
    def test_denied_directed_channel_costs_work_and_delivers_nothing(self):
        world = World(config(links=((BOB, ALICE),)))
        cursor = world.participant_input(BOB)[1]
        event = world.execute(Attempt("send", "send", request(ALICE, SEND, (BOB,)),
            message=MessageDraft((claim(world),))))
        self.assertEqual(event.outcome, WorkStatus.FAILED)
        self.assertEqual(world.truth.wallet(ALICE).energy, 19)
        self.assertFalse(world.participant_input(BOB, cursor)[0].observations)
        self.assertFalse(world.truth.journal()[-1].messages)

    @rules("W04")
    def test_payload_cannot_smuggle_private_memory_references(self):
        world = World(config())
        retain(world, actor=ALICE)
        memory = world.participant_input(ALICE)[0].own_memories[0]
        foreign = replace(claim(world), subject=memory.ref)
        before = world.checkpoint()
        with self.assertRaises(ValueError):
            world.execute(Attempt("send", "send", request(BOB, SEND, (ALICE,)), message=MessageDraft((foreign,))))
        self.assertEqual(before, world.checkpoint())

    @rules("W05")
    def test_belief_exists_while_content_is_wrong(self):
        world = World(config())
        transfer(world)
        wrong = claim(world, ALICE)
        retain(world, content=(wrong,))
        memory = world.participant_input(BOB)[0].own_memories[0]
        held = Proposition(memory.ref, "held_by", BOB, ROOM, TimeScope(world.now, None))
        self.assertEqual(memory.claim_status, ClaimStatus.ENDORSED)
        self.assertEqual(world.truth.check(held, world.now).status, EvidenceStatus.ESTABLISHED)
        self.assertEqual(world.truth.check(wrong, world.now).status, EvidenceStatus.FAILED)
        self.assertEqual(world.truth.current_fact(BOX, "owned_by", ROOM).object, BOB)

    @rules("W01", "W05")
    def test_memory_revision_preserves_historical_binding_without_exposing_other_owner(self):
        world = World(config())
        retain(world, actor=BOB, key="first")
        first = world.participant_input(BOB)[0].own_memories[0]
        retained_at = world.now
        retain(world, actor=BOB, key="second", content=(claim(world, BOB),), basis=(first.ref,))
        second = world.participant_input(BOB)[0].own_memories[0]
        retain(world, actor=ALICE, key="alice", local="account")
        self.assertEqual(second.replaces, first.ref)
        self.assertEqual(second.ref.revision, 2)
        self.assertEqual(world.truth.resolve(first.ref), first)
        self.assertEqual(second.derived_from, (first.ref,))
        held = Proposition(first.ref, "held_by", BOB, ROOM, TimeScope(retained_at, None))
        self.assertEqual(world.truth.check(held, retained_at).status, EvidenceStatus.ESTABLISHED)
        self.assertEqual(world.truth.check(held, world.now).status, EvidenceStatus.FAILED)
        self.assertNotEqual(world.participant_input(ALICE)[0].own_memories[0].ref.key, second.ref.key)

    @rules("W05")
    def test_referent_relation_context_and_time_are_not_graph_shape(self):
        world = World(config())
        good = claim(world)
        self.assertEqual(world.truth.check(good, world.now).status, EvidenceStatus.ESTABLISHED)
        self.assertEqual(world.truth.check(replace(good, object=BOB), world.now).status, EvidenceStatus.FAILED)
        unknown = (replace(good, relation="caused_by"),
            replace(good, subject=Ref(Kind.ENTITY, "box", 99)),
            replace(good, context=Ref(Kind.CONTEXT, "other", 1)),
            replace(good, scope=TimeScope(Moment(2, 0), None)))
        for proposition in unknown:
            self.assertEqual(world.truth.check(proposition, world.now).status, EvidenceStatus.UNASSESSED)
        self.assertEqual(world.truth.check(good, Moment(9, 0)).status, EvidenceStatus.UNASSESSED)
        bounded = replace(good, scope=TimeScope(Moment(0, 0), Moment(0, 1)))
        self.assertEqual(world.truth.check(bounded, world.now).status, EvidenceStatus.UNASSESSED)

    @rules("W06")
    def test_all_sixteen_energy_time_budgets_preserve_incomplete_work(self):
        for energy, time in product(range(4), repeat=2):
            world = World(config(energy=energy, time=time))
            event = transfer(world)
            spent = min(2, energy, time)
            status = (WorkStatus.DEFERRED, WorkStatus.PARTIAL, WorkStatus.COMPLETED)[spent]
            self.assertEqual(event.outcome, status)
            self.assertEqual(world.truth.wallet(ALICE), Wallet(ALICE, energy-spent, time-spent))
            self.assertEqual(world.truth.task(ALICE, "transfer").completed, spent)
            self.assertEqual(world.truth.current_fact(BOX, "owned_by", ROOM).object, BOB if spent == 2 else ALICE)
            self.assertEqual(world.state(), fold(world.config, world.truth.journal()))

    @rules("W06")
    def test_partial_resume_charges_only_remaining_units(self):
        world = World(config(energy=1, time=8))
        first = transfer(world, key="start", task="job")
        self.assertEqual(first.outcome, WorkStatus.PARTIAL)
        deferred = transfer(world, key="try_again", task="job")
        self.assertEqual(deferred.outcome, WorkStatus.DEFERRED)
        self.assertEqual(world.truth.task(ALICE, "job").completed, 1)
        world.execute(Credit("credit", ALICE, 1, 0, "test supply"))
        final = transfer(world, key="finish", task="job")
        self.assertEqual(final.outcome, WorkStatus.COMPLETED)
        final_work = world.truth.resolve(final.work[0])
        self.assertEqual((final_work.required_units, final_work.completed_units), (1, 1))
        self.assertEqual(world.truth.wallet(ALICE), Wallet(ALICE, 0, 6))

    @rules("W06")
    def test_failure_after_full_spending_is_not_refunded(self):
        world = World(config())
        event = transfer(world, actor=BOB, recipient=ALICE)
        work = world.truth.resolve(event.work[0])
        self.assertEqual((event.outcome, work.completed_units, work.required_units), (WorkStatus.FAILED, 2, 2))
        self.assertEqual(world.truth.wallet(BOB), Wallet(BOB, 18, 18))
        self.assertEqual(world.truth.current_fact(BOX, "owned_by", ROOM).object, ALICE)
        with self.assertRaises(ValueError):
            transfer(world, actor=BOB, recipient=ALICE, key="repeat", task="transfer")

    @rules("W06", "W07")
    def test_precondition_is_rechecked_after_partial_work(self):
        world = World(config(energy=3, time=3))
        head = transfer(world)
        transfer(world, actor=BOB, recipient=ALICE, key="return")
        partial = transfer(world, key="partial", task="new")
        self.assertEqual(partial.outcome, WorkStatus.PARTIAL)
        current = world.truth.journal()[2].event
        world.execute(Correction("change", current.ref, BOB, "known external record correction"))
        world.execute(Credit("credit", ALICE, 1, 1, "test supply"))
        failed = transfer(world, key="finish", task="new")
        self.assertEqual(failed.outcome, WorkStatus.FAILED)
        self.assertEqual(world.truth.resolve(failed.work[0]).completed_units, 1)

    @rules("W06", "W08")
    def test_idempotent_retry_and_conflicting_identifier(self):
        world = World(config())
        command = Attempt("id", "job", request(ALICE, TRANSFER, (BOX, BOB)))
        event = world.execute(command)
        saved = world.checkpoint()
        self.assertEqual(world.execute(command), event)
        self.assertEqual(world.checkpoint(), saved)
        resumed = World.restore(saved)
        self.assertEqual(resumed.execute(command), event)
        self.assertEqual(resumed.checkpoint(), saved)
        with self.assertRaises(ValueError):
            world.execute(replace(command, action=request(BOB, INSPECT, (BOX,))))
        self.assertEqual(world.checkpoint(), saved)

    @rules("W06")
    def test_partial_task_cannot_change_goal(self):
        world = World(config(energy=1))
        transfer(world, task="job")
        saved = world.checkpoint()
        with self.assertRaises(ValueError):
            transfer(world, key="changed", task="job", item=TOOL)
        self.assertEqual(world.checkpoint(), saved)

    @rules("W07", "W09")
    def test_explicit_correction_preserves_past_and_invalidates_only_affected_checks(self):
        world = World(config())
        original = transfer(world)
        when = world.now
        original_observations = world.participant_input(ALICE)[0].observations
        before_wallets = (world.truth.wallet(ALICE), world.truth.wallet(BOB))
        target = claim(world, BOB)
        result = world.truth.check(target, when)
        unrelated = claim(world, BOB, item=TOOL)
        unaffected = world.truth.check(unrelated, when)
        change = world.execute(Correction("fix", original.ref, ALICE, "correct fixture record"))
        self.assertEqual(change.corrects, original.ref)
        self.assertFalse(world.truth.is_current(result))
        self.assertIs(world.truth.check(unrelated, when), unaffected)
        self.assertEqual(world.truth.event(original.ref), original)
        self.assertEqual(world.participant_input(ALICE)[0].observations, original_observations)
        self.assertEqual((world.truth.wallet(ALICE), world.truth.wallet(BOB)), before_wallets)
        self.assertEqual(world.truth.check(target, when).status, EvidenceStatus.ESTABLISHED)
        self.assertEqual(world.truth.check(target, world.now).status, EvidenceStatus.FAILED)
        self.assertEqual(world.state(), fold(world.config, world.truth.journal()))

    @rules("W07")
    def test_non_head_correction_rejects_without_silent_history_rewrite(self):
        world = World(config())
        original = transfer(world)
        transfer(world, actor=BOB, recipient=ALICE, key="return")
        before = world.checkpoint()
        with self.assertRaises(ValueError):
            world.execute(Correction("fix", original.ref, ALICE, "too late for prospective head repair"))
        self.assertEqual(before, world.checkpoint())

    @rules("W08")
    def test_checkpoint_every_prefix_and_continuation_are_byte_identical(self):
        world, _ = run_demo()
        all_entries = world.truth.journal()
        for split in range(1, len(all_entries)+1):
            prefix = World(world.config)
            for tx in all_entries[1:split]:
                prefix.execute(tx.command)
            restored = World.restore(prefix.checkpoint())
            self.assertEqual(restored.checkpoint(), prefix.checkpoint())
            for tx in all_entries[split:]:
                self.assertEqual(prefix.execute(tx.command), restored.execute(tx.command))
            self.assertEqual(restored.checkpoint(), world.checkpoint())
            for actor in (ALICE, BOB):
                self.assertEqual(restored.participant_input(actor), world.participant_input(actor))

    @rules("W08")
    def test_partial_task_continues_after_reload(self):
        world = World(config(energy=1))
        transfer(world, key="start", task="job")
        resumed = World.restore(world.checkpoint())
        for candidate in (world, resumed):
            candidate.execute(Credit("credit", ALICE, 1, 0, "test supply"))
            transfer(candidate, key="finish", task="job")
        self.assertEqual(world.checkpoint(), resumed.checkpoint())

    @rules("W08")
    def test_corrupt_and_rehashed_semantically_forged_checkpoint_reject(self):
        world = World(config())
        transfer(world)
        raw = json.loads(world.checkpoint())
        raw["sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            World.restore(json.dumps(raw))
        checkpoint = loads(world.checkpoint())
        last = checkpoint.journal[-1]
        forged = replace(last, event=replace(last.event, reason="not the generated reason"))
        with self.assertRaises(ValueError):
            World.restore(dumps(replace(checkpoint, journal=checkpoint.journal[:-1]+(forged,))))
        with self.assertRaises(ValueError):
            World.restore(dumps(replace(checkpoint, journal=checkpoint.journal+(last,))))
        with self.assertRaises(ValueError):
            World.restore(dumps(replace(checkpoint, schema="future-unknown")))
        with self.assertRaises(ValueError):
            loads('{"format":1,"format":2}')

    @rules("W09", "W05")
    def test_incremental_factual_checks_match_full_history_at_every_prefix(self):
        world = World(config())
        for index in range(12):
            owner, recipient = (ALICE, BOB) if index % 2 == 0 else (BOB, ALICE)
            transfer(world, actor=owner, recipient=recipient, key=str(index))
            for tick in range(index+2):
                at = Moment(tick, 1)
                for item, value in product((BOX, TOOL), (ALICE, BOB)):
                    proposition = Proposition(item, "owned_by", value, ROOM, TimeScope(Moment(0, 0), None))
                    fact, source = fact_at(world.truth.journal(), proposition, at)
                    expected = EvidenceStatus.ESTABLISHED if fact.object == value else EvidenceStatus.FAILED
                    checked = world.truth.check(proposition, at)
                    self.assertEqual((checked.status, checked.evidence), (expected, (source,)))

    @rules("W09")
    def test_fixed_active_work_does_not_iterate_inactive_global_history(self):
        class NoIteration(list):
            def __iter__(self):
                raise AssertionError("ordinary execution traversed global history")
            def __getitem__(self, key):
                raise AssertionError("ordinary execution indexed or sliced global history")
        for inactive in (0, 2000):
            world = World(config())
            for i in range(inactive):
                world.execute(Tick(str(i)))
            cursor = world.participant_input(BOB)[1]
            world._journal = NoIteration(world._journal)
            transfer(world)
            view, new_cursor = world.participant_input(BOB, cursor)
            self.assertFalse(view.observations)
            self.assertEqual(cursor, new_cursor)
            self.assertEqual(world.truth.check(claim(world, BOB), world.now).status, EvidenceStatus.ESTABLISHED)

    @rules("W09")
    def test_change_and_inbox_cursors_return_only_new_work(self):
        world = World(config())
        _, change_cursor = world.truth.changed_since(0)
        _, inbox_cursor = world.participant_input(ALICE)
        event = transfer(world)
        changes, new_cursor = world.truth.changed_since(change_cursor)
        self.assertEqual(changes, ((event.ref, ((BOX, "owned_by", ROOM),)),))
        view, new_inbox = world.participant_input(ALICE, inbox_cursor)
        self.assertEqual(len(view.observations), 1)
        self.assertEqual(new_inbox, inbox_cursor+1)
        self.assertEqual(world.truth.changed_since(new_cursor), ((), new_cursor))

    @rules("W05", "W09")
    def test_future_unassessed_cache_expires_when_public_time_advances(self):
        world = World(config())
        proposition = claim(world)
        at = Moment(1, 1)
        before = world.truth.check(proposition, at)
        self.assertEqual(before.status, EvidenceStatus.UNASSESSED)
        world.execute(Tick("tick"))
        self.assertFalse(world.truth.is_current(before))
        self.assertEqual(world.truth.check(proposition, at).status, EvidenceStatus.ESTABLISHED)

    @rules("W02", "W10")
    def test_inspectable_demo_carries_required_distinctions(self):
        world, summary = run_demo()
        self.assertEqual(summary["belief_existence"], "established")
        self.assertEqual(summary["belief_content_agreement"], "failed")
        self.assertEqual(summary["failed_action"]["energy_charged"], 2)
        self.assertEqual(summary["partial_action"], "partial")
        self.assertTrue(summary["continuation_identical"])
        self.assertTrue(summary["correction"]["prior_factual_check_stale"])
        self.assertEqual(world.state(), fold(world.config, world.truth.journal()))
