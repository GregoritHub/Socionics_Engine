from dataclasses import replace
from itertools import product
import json
from pathlib import Path
import unittest

from hle.cards import card
from hle.codec import dumps, loads
from hle.contracts import (ClaimStatus, EvidenceStatus, Kind, Moment,
    MovementRecord, Proposition, Ref, TimeScope, WorkStatus)
from hle.crux import Perspective, Polarity
from hle.demo import ALICE, BOB, BOX, TOOL, ROOM, config, request
from hle.memory_records import (BindDraft, MemoryCommand, RecallQuery, WriteDraft)
from hle.metabolism import MetabolicWorld
from hle.metabolism_demo import (CUE, LESSON, SCOPE, associate, finish,
    remember_initial, retrieve, run_metabolism_demo)
from hle.metabolism_records import (Account, Application, ApplyDraft,
    EmbodyDraft, Enactment, MetabolicCommand, MetabolicTransaction,
    ProcessingPolicy, Profile, TheorizeDraft, UnderstandDraft, movement)
from hle.model_a import ELEMENT, TYPES
from hle.processing import plan_route, select_action
from hle.world_records import (Attempt, Correction, Credit, INSPECT, Tick,
    TRANSFER, Witness)
from .reference_memory import NoWalkDict, NoWalkList
from .reference_processing import processing_fold, route_oracle
from .reference_world import fold
from .support import rules


def world(tim="iee", energy=2000, time=2000, policy=ProcessingPolicy(), witnesses=()):
    return MetabolicWorld(config(energy, time, witnesses), (Profile(ALICE, "lse"), Profile(BOB, tim)), policy)


def prepare(w, item=BOX):
    memory = remember_initial(w, item=item)
    recall = retrieve(w, "r")
    return memory, TheorizeDraft(recall, item, ALICE)


def account(w, item=BOX):
    old, draft = prepare(w, item)
    job = finish(w, draft, "think")
    return old, w.processing_record(BOB, job.result)


def single_ownership_head(w):
    # R2 corrections deliberately reject the ambiguous multi-object genesis.
    # Both matched variants execute this identical round trip first.
    w.execute(Attempt("head-out", "head-out", request(BOB, TRANSFER, (TOOL, ALICE))))
    w.execute(Attempt("head-back", "head-back", request(ALICE, TRANSFER, (TOOL, BOB))))


def learn(w):
    old = remember_initial(w)
    w.execute(Attempt("hidden-transfer", "hidden-transfer", request(ALICE, TRANSFER, (BOX, BOB))))
    r = retrieve(w, "r")
    a = finish(w, TheorizeDraft(r, BOX, ALICE), "think")
    application = finish(w, ApplyDraft(a.result), "act")
    finish(w, EmbodyDraft(application.result, "box", old.ref), "learn")
    return w.memory_head(BOB, "box")


class Operators(unittest.TestCase):
    @rules("P01", "P04", "P05")
    def test_integrated_circuit_and_alternate_have_real_outputs(self):
        w, summary = run_metabolism_demo()
        self.assertTrue(summary["observed_discrepancy"])
        self.assertEqual(summary["retained_revision"], 2)
        self.assertEqual(summary["old_binding_revision"], 1)
        self.assertTrue(summary["retained_capability"])
        self.assertEqual([a["operation"] for a in summary["actions"]], [INSPECT.key, TRANSFER.key]*2)
        self.assertEqual(w.truth.current_fact(TOOL, "owned_by", ROOM).object, ALICE)
        self.assertEqual(w.processing_state(BOB).perspective, Perspective.I)
        self.assertTrue(summary["continuation_identical"])

    @rules("P01", "P03")
    def test_theorize_has_exact_recall_and_memory_provenance(self):
        w = world(); m, a = account(w)
        self.assertEqual(a.claim, m.content[0])
        self.assertEqual(a.evidence, (m.ref,))
        self.assertEqual(w.recall_result(BOB, a.recall).hits[0].memory, m.ref)
        self.assertIsNone(a.guard)
        self.assertIn("unassessed", a.uncertainty)

    @rules("P01", "P06")
    def test_partial_routing_cannot_publish_an_account_or_memory(self):
        w = world(); _, draft = prepare(w)
        w.execute(MetabolicCommand("one", "thinking", BOB, draft, 1))
        j = w.processing_job(BOB, "thinking")
        self.assertEqual(j.outcome, WorkStatus.PARTIAL)
        self.assertIsNone(j.result)
        self.assertFalse(any(type(v) is Account for v in w._journal[-1].extra))
        self.assertEqual(w.processing_state(BOB).perspective, Perspective.I)

    @rules("P04", "P06")
    def test_apply_waits_for_physical_work_after_route_completion(self):
        w = world(); _, a = account(w, TOOL)
        cmd = MetabolicCommand("route", "application", BOB, ApplyDraft(a.ref))
        required = w._validate_processing(cmd)[0].plan.required
        w.execute(replace(cmd, work_limit=required))
        self.assertEqual(w.processing_job(BOB, "application").phase, "enact")
        self.assertIsNone(w.processing_job(BOB, "application").result)
        self.assertEqual(w.truth.current_fact(TOOL, "owned_by", ROOM).object, BOB)
        w.execute(replace(cmd, command_id="one-action-unit", work_limit=1))
        self.assertEqual(w.truth.current_fact(TOOL, "owned_by", ROOM).object, BOB)
        w.execute(replace(cmd, command_id="second-action-unit", work_limit=1))
        self.assertEqual(w.truth.current_fact(TOOL, "owned_by", ROOM).object, ALICE)

    @rules("P04")
    def test_inspection_then_transfer_cites_committed_observation(self):
        w = world(); old = remember_initial(w)
        w.apply(request(ALICE, TRANSFER, (BOX, BOB)))
        r = retrieve(w, "r"); a = finish(w, TheorizeDraft(r, BOX, ALICE), "a")
        job = finish(w, ApplyDraft(a.result), "apply")
        app = w.processing_record(BOB, job.result)
        actions = [w.processing_record(BOB, r) for r in app.enactments]
        self.assertEqual(len(actions), 2)
        self.assertIn(actions[0].observation, actions[1].request.based_on)
        self.assertLess(w._origins[actions[0].ref].key, w._origins[actions[1].ref].key)
        self.assertTrue(app.discrepancy)

    @rules("P04")
    def test_failed_transfer_does_not_reveal_the_hidden_owner(self):
        w = world(); _, a = account(w, TOOL)
        single_ownership_head(w)
        w.execute(Correction("hidden", w._heads[(TOOL, "owned_by", ROOM)], ALICE, "controlled hidden variant"))
        j = finish(w, ApplyDraft(a.ref), "apply")
        app = w.processing_record(BOB, j.result)
        o = w._owned(BOB, app.observations[0], (type(w._inboxes[BOB][0]),))
        self.assertEqual(j.outcome, WorkStatus.FAILED)
        self.assertTrue(app.discrepancy)
        self.assertFalse(any(p.relation == "owned_by" for p in o.content))
        self.assertEqual(w.processing_state(BOB).perspective, Perspective.IT)

    @rules("P04")
    def test_transfer_witness_visibility_matches_r2(self):
        for mode in ("full", "occurrence"):
            w = world(witnesses=(Witness(ALICE, TOOL, mode),)); _, a = account(w, TOOL)
            before = len(w._inboxes[ALICE])
            finish(w, ApplyDraft(a.ref), "apply")
            delivered = w._inboxes[ALICE][before:]
            self.assertEqual(len(delivered), 1)
            self.assertEqual(bool(delivered[0].content), mode == "full")

    @rules("P01", "P05")
    def test_understand_retains_personal_account_without_world_action(self):
        w = world(); m, a = account(w)
        owner = w.truth.current_fact(BOX, "owned_by", ROOM)
        job = finish(w, UnderstandDraft(a.ref, "personal"), "understand")
        retained = w.read_revision(BOB, job.result)
        self.assertEqual(retained.content, (a.claim,))
        self.assertEqual(retained.claim_status, ClaimStatus.TENTATIVE)
        self.assertEqual(retained.links, (m.ref,))
        self.assertEqual(w.truth.current_fact(BOX, "owned_by", ROOM), owner)

    @rules("P01", "P07")
    def test_wrong_origin_and_unsupported_payload_reject_atomically(self):
        w = world(); _, a = account(w)
        before = w.checkpoint()
        with self.assertRaises(ValueError):
            w.execute(MetabolicCommand("wrong", "wrong", BOB, TheorizeDraft(a.recall, BOX, ALICE)))
        with self.assertRaises(ValueError): MetabolicCommand("unsupported", "unsupported", BOB, "Express")
        self.assertEqual(before, w.checkpoint())


class EvidenceAndLearning(unittest.TestCase):
    @rules("P03")
    def test_empty_recall_yields_uncertainty_and_inspection(self):
        w = world(); r = retrieve(w, "empty")
        j = finish(w, TheorizeDraft(r, BOX, ALICE), "t")
        a = w.processing_record(BOB, j.result)
        self.assertIsNone(a.claim)
        self.assertEqual(select_action(a).operation, INSPECT)

    @rules("P03")
    def test_conflict_is_independent_of_cue_order(self):
        outputs = []
        for reverse in (False, True):
            w = world(); m = remember_initial(w)
            p = replace(m.content[0], object=BOB)
            w.execute(MemoryCommand("other", "other", BOB,
                WriteDraft("other", (p,), (), ClaimStatus.ENDORSED, None, "conflicting recalled fixture"), (m.ref,)))
            associate(w, w.memory_head(BOB, "other"), "other-cue", LESSON)
            r = retrieve(w, "r", (LESSON, CUE) if reverse else (CUE, LESSON))
            j = finish(w, TheorizeDraft(r, BOX, ALICE), "t")
            a = w.processing_record(BOB, j.result)
            outputs.append((a.claim, a.uncertainty, select_action(a).operation))
        self.assertEqual(outputs[0], outputs[1]); self.assertIsNone(outputs[0][0])

    @rules("P03")
    def test_selected_proposition_indexes_exclude_unrecalled_subject(self):
        w = world(); remember_initial(w)
        r = retrieve(w, "r", subject=TOOL)
        j = finish(w, TheorizeDraft(r, BOX, ALICE), "t")
        self.assertIsNone(w.processing_record(BOB, j.result).claim)

    @rules("P03")
    def test_truncation_cannot_become_certainty(self):
        w = world(); m = remember_initial(w)
        w.execute(MemoryCommand("write", "write", BOB,
            WriteDraft("other", m.content, (), ClaimStatus.ENDORSED, None, "second record"), (m.ref,)))
        associate(w, w.memory_head(BOB, "other"), "other")
        w.execute(MemoryCommand("r", "r", BOB, RecallQuery((CUE,), ROOM, w.now, visit_limit=1)))
        r = w.memory_job(BOB, "r").result
        j = finish(w, TheorizeDraft(r, BOX, ALICE), "t")
        a = w.processing_record(BOB, j.result)
        self.assertIsNone(a.claim); self.assertIn("truncated", a.uncertainty)

    @rules("P03", "P07")
    def test_hidden_ownership_and_evaluator_work_do_not_change_account_or_selection(self):
        outputs = []
        for hidden in (False, True):
            w = world(); m, draft = prepare(w, TOOL)
            single_ownership_head(w)
            if hidden:
                w.execute(Correction("variant", w._heads[(TOOL, "owned_by", ROOM)], ALICE, "hidden control"))
                w.truth.check(m.content[0], w.now)
            else: w.execute(Tick("variant"))
            j = finish(w, draft, "t")
            a = w.processing_record(BOB, j.result)
            outputs.append((a, j.plan, select_action(a)))
        self.assertEqual(outputs[0], outputs[1])

    @rules("P03", "P07")
    def test_foreign_recall_and_account_reject_without_charge(self):
        w = world(); _, a = account(w)
        before = w.checkpoint()
        with self.assertRaises(ValueError):
            w.execute(MetabolicCommand("foreign", "foreign", ALICE, TheorizeDraft(a.recall, BOX, BOB)))
        with self.assertRaises(ValueError): w.processing_record(ALICE, a.ref)
        self.assertEqual(w.checkpoint(), before)

    @rules("P05")
    def test_heldout_capability_changes_action_and_prevents_failed_transfer(self):
        observations = []
        for use_capability in (False, True):
            w = world(); lesson = learn(w)
            remember_initial(w, "tool", TOOL, card("arcana:3").ref)
            associate(w, lesson, "learned", LESSON)
            # Matched history/resources; only selected cue differs.
            if not use_capability:
                w.execute(MemoryCommand("no-cap", "no-cap", BOB,
                    WriteDraft("no-cap", lesson.content, (), ClaimStatus.ENDORSED, None,
                        "capacity ablation; same proposition"), (lesson.ref,)))
                substitute = w.memory_head(BOB, "no-cap")
                associate(w, substitute, "control", card("arcana:4").ref)
            else:
                # Identical write/bind costs and event count as the ablation.
                w.execute(MemoryCommand("no-cap", "no-cap", BOB,
                    WriteDraft("no-cap", lesson.content, (), ClaimStatus.ENDORSED, None,
                        "capacity ablation; same proposition"), (lesson.ref,)))
                associate(w, w.memory_head(BOB, "no-cap"), "control", card("arcana:4").ref)
            single_ownership_head(w)
            w.execute(Correction("hidden", w._heads[(TOOL, "owned_by", ROOM)], ALICE, "held-out hidden correction"))
            r = retrieve(w, "heldout", (card("arcana:3").ref, LESSON if use_capability else card("arcana:4").ref))
            j = finish(w, TheorizeDraft(r, TOOL, ALICE), "heldout-think")
            a = w.processing_record(BOB, j.result)
            applied = finish(w, ApplyDraft(a.ref), "heldout-apply")
            app = w.processing_record(BOB, applied.result)
            first = w.processing_record(BOB, app.enactments[0])
            observations.append((first.request.operation, applied.outcome, a.claim.object))
        self.assertEqual(observations, [(TRANSFER, WorkStatus.FAILED, BOB), (INSPECT, WorkStatus.COMPLETED, BOB)])

    @rules("P05")
    def test_agreement_does_not_invent_a_discrepancy_guard(self):
        w = world(); old, a = account(w, TOOL)
        application = finish(w, ApplyDraft(a.ref), "apply")
        finish(w, EmbodyDraft(application.result, "box", old.ref), "embody")
        self.assertFalse(w.memory_head(BOB, "box").capabilities)

    @rules("P05", "P07")
    def test_stale_retention_fails_after_work_and_preserves_newer_memory(self):
        w = world(); old, a = account(w)
        application = finish(w, ApplyDraft(a.ref), "apply")
        draft = EmbodyDraft(application.result, "box", old.ref)
        w.execute(MetabolicCommand("start", "learn", BOB, draft, 1))
        w.execute(MemoryCommand("competing", "competing", BOB,
            WriteDraft("box", old.content, (), ClaimStatus.ENDORSED, old.ref, "concurrent retention"), (old.ref,)))
        winner = w.memory_head(BOB, "box")
        before = w.truth.wallet(BOB).energy
        w.execute(MetabolicCommand("finish", "learn", BOB, draft, 100))
        self.assertEqual(w.processing_job(BOB, "learn").outcome, WorkStatus.FAILED)
        self.assertEqual(w.memory_head(BOB, "box"), winner)
        self.assertLess(w.truth.wallet(BOB).energy, before)
        self.assertEqual(w.processing_state(BOB).perspective, Perspective.IT)
        retry = finish(w, EmbodyDraft(application.result, "box", winner.ref), "retry")
        self.assertEqual(retry.outcome, WorkStatus.COMPLETED)

    @rules("P03", "P07")
    def test_pending_theory_keeps_exact_historical_binding(self):
        w = world(); old, draft = prepare(w)
        w.execute(MetabolicCommand("start", "think", BOB, draft, 1))
        p = replace(old.content[0], object=BOB)
        w.execute(MemoryCommand("new", "new", BOB,
            WriteDraft("box", (p,), (), ClaimStatus.ENDORSED, old.ref, "revision during processing"), (old.ref,)))
        w.execute(MetabolicCommand("finish", "think", BOB, draft, 100))
        a = w.processing_record(BOB, w.processing_job(BOB, "think").result)
        self.assertEqual(a.claim.object, ALICE)
        self.assertEqual(a.evidence, (old.ref,))


class RoutingAndWork(unittest.TestCase):
    @rules("P02", "P09")
    def test_all_type_routes_match_independent_positional_oracle(self):
        r = Ref(Kind.EVIDENCE, "input", 1)
        variants = ((TheorizeDraft(r, BOX, ALICE), "ti"), (ApplyDraft(r), "te"),
                    (EmbodyDraft(r, "x"), "si"), (UnderstandDraft(r, "x"), "fi"))
        for tim, active, (payload, target), typed, priced in product(TYPES, ELEMENT, variants, (False, True), (False, True)):
            policy = ProcessingPolicy(typed, priced)
            result = plan_route(Profile(BOB, tim, active), active, movement(payload), payload, 3, policy)
            expected = route_oracle(tim, active, target, type(payload) is ApplyDraft, 3, typed, priced)
            self.assertEqual((result.path, result.positions, result.support_position,
                result.support_index, result.hop_units, result.content_units), expected)

    @rules("P02", "P03")
    def test_type_effects_change_paths_and_costs_with_equal_semantic_evidence(self):
        plans, semantics = [], []
        for tim in TYPES:
            w = world(tim); _, a = account(w)
            j = w.processing_job(BOB, "think")
            plans.append((j.plan.path, j.plan.required)); semantics.append((a.claim, select_action(a).operation))
        self.assertGreater(len(set(plans)), 1)
        self.assertEqual(len(set(semantics)), 1)

    @rules("P02")
    def test_neutral_routing_and_prices_remove_type_effects(self):
        outcomes = []
        for tim in TYPES:
            w = world(tim, policy=ProcessingPolicy(False, False)); _, a = account(w)
            j = w.processing_job(BOB, "think")
            outcomes.append((j.plan.path, j.plan.required, w.truth.wallet(BOB), select_action(a)))
        self.assertEqual(len(set(outcomes)), 1)

    @rules("P02", "P06")
    def test_equal_budget_can_complete_one_type_while_another_remains_partial(self):
        charges = []
        for tim in TYPES:
            w = world(tim); _, draft = prepare(w)
            charges.append((w._validate_processing(MetabolicCommand("x", "x", BOB, draft))[0].plan.required, tim))
        low, high = min(charges), max(charges)
        self.assertLess(low[0], high[0])
        outputs = []
        for _, tim in (low, high):
            w = world(tim, energy=low[0]+6, time=low[0]+6); _, draft = prepare(w)
            outputs.append(finish(w, draft, "t").outcome)
        self.assertEqual(outputs, [WorkStatus.COMPLETED, WorkStatus.PARTIAL])

    @rules("P06")
    def test_energy_time_matrix_conserves_and_preserves_partial_units(self):
        for energy, time in product((0, 1, 2, 3, 8, 32), repeat=2):
            w = world(energy=energy+6, time=time+6); _, draft = prepare(w)
            w.execute(MetabolicCommand("start", "t", BOB, draft))
            job = w.processing_job(BOB, "t")
            expected = min(energy, time, job.plan.required)
            self.assertEqual(job.completed_units, expected)
            self.assertEqual(w.truth.wallet(BOB).energy, energy-expected)
            self.assertEqual(w.truth.wallet(BOB).time, time-expected)
            self.assertEqual(MetabolicWorld.restore(w.checkpoint()).checkpoint(), w.checkpoint())

    @rules("P06")
    def test_resume_after_credit_and_idempotent_retry_do_not_double_charge(self):
        w = world(energy=7, time=7); _, draft = prepare(w)
        first = MetabolicCommand("one", "t", BOB, draft)
        event = w.execute(first); snap = w.checkpoint()
        self.assertEqual(w.execute(first), event); self.assertEqual(w.checkpoint(), snap)
        w.execute(Credit("fund", BOB, 100, 100, "explicit resource supply"))
        w.execute(replace(first, command_id="resume"))
        job = w.processing_job(BOB, "t")
        self.assertEqual(job.outcome, WorkStatus.COMPLETED)
        self.assertEqual(w.truth.wallet(BOB).energy, 101-job.plan.required)
        with self.assertRaises(ValueError): w.execute(replace(first, command_id="terminal"))

    @rules("P06", "P07")
    def test_busy_actor_and_changed_continuation_reject_atomically(self):
        w = world(); _, draft = prepare(w)
        w.execute(MetabolicCommand("start", "t", BOB, draft, 1)); snap = w.checkpoint()
        with self.assertRaises(ValueError): w.execute(MetabolicCommand("other", "other", BOB, draft))
        with self.assertRaises(ValueError):
            w.execute(MetabolicCommand("change", "t", BOB, replace(draft, item=TOOL)))
        self.assertEqual(w.checkpoint(), snap)

    @rules("P06")
    def test_every_funded_stage_and_deferral_has_a_processing_witness(self):
        w = world(energy=6, time=6); _, draft = prepare(w)
        w.execute(MetabolicCommand("defer", "t", BOB, draft))
        tx = w._journal[-1]; witness = next(r for r in tx.extra if type(r) is MovementRecord)
        self.assertEqual(witness.outcome, WorkStatus.DEFERRED)
        self.assertEqual(len(witness.history), 1)
        self.assertEqual(w.truth.resolve(witness.history[0].work).completed_units, 0)
        self.assertEqual(witness.formal, movement(draft))


class ContinuationAndIndexes(unittest.TestCase):
    @rules("P07", "P09")
    def test_every_demo_prefix_restores_and_continues_identically(self):
        final, _ = run_metabolism_demo(); journal = final.truth.journal()
        live = MetabolicWorld(final.config, final.profiles, final.policy)
        for index in range(len(journal)):
            if index: live.execute(journal[index].command)
            restored = MetabolicWorld.restore(live.checkpoint())
            for tx in journal[index+1:]: restored.execute(tx.command)
            self.assertEqual(restored.checkpoint(), final.checkpoint())

    @rules("P07")
    def test_rehashed_route_state_and_account_tampering_rejects(self):
        w = world(); _, a = account(w); cp = loads(w.checkpoint()); tx = cp.journal[-1]
        mutations = [replace(tx, job=replace(tx.job, plan=replace(tx.job.plan, content_units=tx.job.plan.content_units+1))),
                     replace(tx, state=replace(tx.state, active="se")),
                     replace(tx, extra=tuple(replace(r, claim=replace(r.claim, object=BOB)) if type(r) is Account else r for r in tx.extra))]
        for mutated in mutations:
            with self.assertRaises(ValueError): MetabolicWorld.restore(dumps(replace(cp, journal=cp.journal[:-1]+(mutated,))))

    @rules("P07")
    def test_profile_and_policy_persist_with_partial_processing(self):
        w = world("lii", policy=ProcessingPolicy(True, False)); _, draft = prepare(w)
        w.execute(MetabolicCommand("one", "t", BOB, draft, 1))
        r = MetabolicWorld.restore(w.checkpoint())
        self.assertEqual(r.profiles, w.profiles); self.assertEqual(r.policy, w.policy)
        self.assertEqual(r.processing_state(BOB), w.processing_state(BOB))
        self.assertEqual(r.processing_job(BOB, "t"), w.processing_job(BOB, "t"))

    @rules("P08")
    def test_offline_folds_match_world_and_processing_after_every_event(self):
        final, _ = run_metabolism_demo()
        w = MetabolicWorld(final.config, final.profiles, final.policy)
        for i, tx in enumerate(final.truth.journal()):
            if i: w.execute(tx.command)
            states, jobs, changes = processing_fold(w.profiles, w.truth.journal())
            self.assertEqual(w.state(), fold(w.config, w.truth.journal()))
            self.assertEqual(states, {a:(s.active,s.perspective,s.busy) for a,s in w._processing_states.items()})
            self.assertEqual(jobs, w._processing_jobs)
            self.assertEqual(changes, tuple(w._processing_changes))

    @rules("P08")
    def test_processing_changed_suffix_reports_only_affected_actor(self):
        w = world(); _, draft = prepare(w); before = len(w._journal)
        w.execute(MetabolicCommand("one", "t", BOB, draft, 1)); w.execute(Tick("idle"))
        suffix, cursor = w.processing_changed_since(before)
        self.assertEqual([x[1] for x in suffix], [(BOB,), ()]); self.assertEqual(cursor, before+2)
        with self.assertRaises(ValueError): w.processing_changed_since(-1)

    @rules("P08")
    def test_active_operators_do_not_walk_inactive_global_indexes(self):
        w = world(); old, draft = prepare(w)
        for i in range(200): w.execute(Tick(f"old:{i}"))
        w._journal = NoWalkList(w._journal); w._changes = NoWalkList(w._changes)
        w._processing_changes = NoWalkList(w._processing_changes)
        w._records = NoWalkDict(w._records); w._origins = NoWalkDict(w._origins)
        w._memory_heads[BOB] = NoWalkDict(w._memory_heads[BOB])
        a = finish(w, draft, "t")
        app = finish(w, ApplyDraft(a.result), "a")
        e = finish(w, EmbodyDraft(app.result, "box", old.ref), "e")
        self.assertEqual(e.outcome, WorkStatus.COMPLETED)

    @rules("P09")
    def test_r4_tests_all_link_to_registered_rules(self):
        registry = json.loads((Path(__file__).resolve().parents[1]/"docs/rules.json").read_text())
        ids = {r["id"] for r in registry["rules"]}
        for cls in (Operators, EvidenceAndLearning, RoutingAndWork, ContinuationAndIndexes):
            for name in unittest.defaultTestLoader.getTestCaseNames(cls):
                self.assertTrue(set(getattr(getattr(cls, name), "rule_ids", ())) <= ids)
                self.assertTrue(getattr(getattr(cls, name), "rule_ids", ()))
