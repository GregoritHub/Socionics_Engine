from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
import unittest

from hle.cards import CARDS, card, fold
from hle.codec import dumps, loads
from hle.contracts import (ClaimStatus, CueDescriptor, EvidenceStatus, Kind,
    Moment, Proposition, Ref, TimeScope, WorkStatus)
from hle.demo import ALICE, BOB, BOX, TOOL, ROOM, config, request
from hle.memory import RelationalWorld, observed_revision, ownership_action
from hle.memory_records import (AckDraft, BindDraft, ContextDraft, CursorDraft,
    LINKED, MemoryCommand, MemoryTransaction, RecallQuery, WriteDraft)
from hle.world import World
from hle.world_records import Attempt, Credit, INSPECT, MessageDraft, SEND, Tick, TRANSFER
from .reference_memory import NoWalkDict, NoWalkList, complete_recall
from .support import rules

CUE = card("arcana:1").ref
SECOND = card("minor:Wand:10").ref
SCOPE = TimeScope(Moment(0, 0), None)


def world(energy=10000, time=10000):
    return RelationalWorld(config(energy=energy, time=time))


def claim(value=BOB, *, item=BOX, relation="owned_by", context=ROOM, scope=SCOPE):
    return Proposition(item, relation, value, context, scope)


def perform(w, payload, *, actor=BOB, basis=None, key=None, task=None, limit=64):
    key = key or f"m:{len(w._journal)}"
    if basis is None:
        basis = (w.select_input(actor, after=0)[0].observations[0].ref,)
    cmd = MemoryCommand(key, task or key, actor, payload, basis, limit)
    w.execute(cmd)
    return cmd


def write(w, key="m", content=None, links=(), expected=None, actor=BOB):
    content = (claim(),) if content is None else content
    basis = (w.select_input(actor, after=0)[0].observations[0].ref,) + (() if expected is None else (expected,))
    perform(w, WriteDraft(key, content, links, ClaimStatus.ENDORSED, expected, "test fixture"), actor=actor, basis=basis)
    return w.memory_head(actor, key)


def bind(w, memory, key="b", cue=CUE, context=ROOM, scope=SCOPE, expected=None):
    basis = (memory.ref,) + (() if expected is None else (expected,))
    perform(w, BindDraft(key, cue, context, memory.ref, scope, expected), actor=memory.owner, basis=basis)
    return w.binding_head(memory.owner, key)


def recall(w, *, cues=(CUE,), context=ROOM, at=None, subject=None, relation=None,
           visit_limit=64, actor=BOB, limit=64, key=None):
    q = RecallQuery(cues, context, w.now if at is None else at, subject, relation, visit_limit)
    cmd = perform(w, q, actor=actor, basis=(), limit=limit, key=key)
    job = w.memory_job(actor, cmd.task_id)
    return None if job.result is None else w.recall_result(actor, job.result), cmd


def navigate(w, hops, actor=BOB):
    old = w.navigation(actor)
    perform(w, CursorDraft((CUE,), LINKED if hops else None, hops, None if old is None else old.ref),
            actor=actor, basis=() if old is None else (old.ref,))


class SourceCatalog(unittest.TestCase):
    @rules("F01", "U01", "O01")
    def test_catalog_fold_layers_courts_and_unlocated_fool(self):
        self.assertEqual(len(CARDS), 130)
        self.assertEqual(len({c.ref for c in CARDS}), 130)
        self.assertIsNone(card("arcana:0").folded_location)
        self.assertIsNone(card("arcana:0").layer_label)
        groups = {}
        for rank in range(1, 22):
            c = card(f"arcana:{rank}")
            groups.setdefault(c.folded_location, []).append(rank)
            self.assertEqual(c.rank, rank)
        self.assertEqual(groups[1], [1, 10, 19])
        self.assertEqual([len(groups[i]) for i in range(1, 10)], [3, 3, 3, 2, 2, 2, 2, 2, 2])
        self.assertEqual(card("arcana:19").layer_label, "Identity")
        self.assertEqual(card("arcana:11").symbol, "Justice")
        self.assertEqual(card("minor:Wand:12").symbol, "Knight of Wand")
        self.assertEqual(card("standard:Club:12").symbol, "Queen of Club")
        self.assertIsNone(card("minor:Wand:10").layer_label)
        self.assertEqual(card("minor:Wand:14").folded_location, 5)
        with self.assertRaises(ValueError): card("standard:Club:14")
        for invalid in (0, -1, True, 1.0):
            with self.assertRaises(ValueError): fold(invalid)
        self.assertFalse(any("identity_cycle" in vars(c) for c in CARDS))

    @rules("F01", "F02")
    def test_fold_collision_does_not_conflate_cues_or_targets(self):
        w = world()
        refs = (CUE, card("arcana:10").ref, card("arcana:19").ref, SECOND)
        for i, cue in enumerate(refs): bind(w, write(w, str(i)), str(i), cue=cue)
        for i, cue in enumerate(refs):
            r, _ = recall(w, cues=(cue,))
            self.assertEqual([h.memory for h in r.hits], [w.memory_head(BOB, str(i)).ref])


class Associations(unittest.TestCase):
    @rules("F02", "F03")
    def test_context_reuses_same_cue_and_same_card_has_no_single_content(self):
        w = world()
        perform(w, ContextDraft("family", "family episode"))
        context = w._journal[-1].contexts[0].ref
        a = write(w, "room", (claim(),))
        b = write(w, "family", (claim(ALICE, context=context),))
        bind(w, a, "room"); bind(w, b, "family", context=context)
        for ctx, expected in ((ROOM, a), (context, b)):
            r, _ = recall(w, context=ctx)
            self.assertEqual(tuple(h.memory for h in r.hits), (expected.ref,))
        self.assertEqual(w._records[CUE], card("arcana:1"))

    @rules("F02", "F03")
    def test_multiple_cues_one_memory_and_deduplicated_roots(self):
        w = world(); m = write(w)
        b1, b2 = bind(w, m), bind(w, m, "second", cue=SECOND)
        for cues in ((CUE,), (SECOND,), (CUE, SECOND), (SECOND, CUE)):
            r, _ = recall(w, cues=cues)
            self.assertEqual([v.memory for v in r.visited], [m.ref])
            self.assertEqual(len(r.bindings), len(cues))
            self.assertEqual(r.hits[0].proposition_indexes, (0,))

    @rules("F02", "F03")
    def test_721_memories_share_one_cue_without_capacity_rule(self):
        w = world()
        for i in range(721): bind(w, write(w, str(i)), str(i))
        r, cmd = recall(w, visit_limit=1000, limit=1000)
        self.assertEqual(len(r.hits), 721)
        self.assertEqual(len(r.visited), 721)
        self.assertFalse(r.truncated)
        self.assertEqual(w.memory_job(BOB, cmd.task_id).completed_units, 722)

    @rules("F02", "F03")
    def test_binding_and_content_half_open_scopes_filter_independently(self):
        w = world(); start, end = Moment(0, 0), Moment(1, 0)
        m = write(w, content=(claim(scope=TimeScope(start, end)), claim(ALICE)))
        bind(w, m, scope=SCOPE)
        first, _ = recall(w, at=start)
        second, _ = recall(w, at=end)
        self.assertEqual(first.hits[0].proposition_indexes, (0, 1))
        self.assertEqual(second.hits[0].proposition_indexes, (1,))
        old = w.binding_head(BOB, "b")
        bind(w, m, scope=TimeScope(start, end), expected=old.ref)
        absent, _ = recall(w, at=end)
        self.assertFalse(absent.visited)
        self.assertFalse(absent.hits)

    @rules("F03", "F06")
    def test_subject_relation_filters_and_missing_details_not_invented(self):
        w = world(); m = write(w, content=(claim(), claim(item=TOOL), claim("unclear", relation="intent")))
        bind(w, m)
        r, _ = recall(w, subject=TOOL, relation="owned_by")
        self.assertEqual(r.hits[0].proposition_indexes, (1,))
        missing, _ = recall(w, relation="weight")
        self.assertFalse(missing.hits)
        self.assertEqual(len(missing.visited), 1)
        self.assertFalse(hasattr(r, "truth"))

    @rules("F03")
    def test_explicit_limit_reports_truncation(self):
        w = world()
        for i in range(4): bind(w, write(w, str(i)), str(i))
        short, _ = recall(w, visit_limit=2)
        full, _ = recall(w, visit_limit=4)
        self.assertTrue(short.truncated)
        self.assertEqual(len(short.visited), 2)
        self.assertFalse(full.truncated)
        self.assertEqual(len(full.visited), 4)

    @rules("F03")
    def test_no_binding_completes_with_empty_unassessed_result(self):
        w = world(); r, cmd = recall(w)
        self.assertFalse(r.hits); self.assertFalse(r.visited)
        self.assertEqual(w.memory_job(BOB, cmd.task_id).completed_units, 1)


class NavigationTests(unittest.TestCase):
    @rules("F03", "F04")
    def test_useful_variable_paths_of_1_2_4_and_17_records(self):
        for count in (1, 2, 4, 17):
            with self.subTest(count=count):
                w = world(); target = write(w, "leaf")
                root = target
                for i in range(count - 1): root = write(w, str(i), (), (root.ref,))
                bind(w, root); navigate(w, count - 1)
                r, _ = recall(w)
                self.assertEqual(len(r.visited), count)
                self.assertEqual([h.memory for h in r.hits], [target.ref])
                self.assertEqual([v.depth for v in r.visited], list(range(count)))

    @rules("F03", "F04")
    def test_cursor_competence_changes_access_without_changing_organization(self):
        w = world(); leaf = write(w, "leaf"); root = write(w, "root", (), (leaf.ref,)); b = bind(w, root)
        before = (w.read_revision(BOB, root.ref), w.read_revision(BOB, leaf.ref), w.resolve_binding(BOB, b.ref))
        direct, _ = recall(w)
        self.assertEqual(len(direct.visited), 1); self.assertFalse(direct.hits)
        navigate(w, 1)
        skilled, _ = recall(w)
        self.assertEqual([h.memory for h in skilled.hits], [leaf.ref])
        navigate(w, 0)
        direct_again, _ = recall(w)
        self.assertFalse(direct_again.hits)
        self.assertEqual(before, (w.read_revision(BOB, root.ref), w.read_revision(BOB, leaf.ref), w.resolve_binding(BOB, b.ref)))

    @rules("F03")
    def test_branched_shared_fragment_visited_once_with_traceable_parent(self):
        w = world(); leaf = write(w, "leaf")
        left, right = write(w, "left", (), (leaf.ref,)), write(w, "right", (), (leaf.ref,))
        root = write(w, "root", (), (right.ref, left.ref)); bind(w, root); navigate(w, 10)
        r, _ = recall(w)
        self.assertEqual([v.memory for v in r.visited], [root.ref, right.ref, left.ref, leaf.ref])
        self.assertEqual(r.visited[-1].parent, right.ref)
        self.assertEqual([h.memory for h in r.hits], [leaf.ref])

    @rules("F03", "F05", "F08")
    def test_pending_recall_pins_binding_memory_and_cursor_revisions(self):
        w = world(); leaf = write(w, "leaf"); root = write(w, "root", (), (leaf.ref,))
        b = bind(w, root); navigate(w, 1)
        result, cmd = recall(w, limit=1)
        self.assertIsNone(result)
        original_nav = w.navigation(BOB).ref
        changed = write(w, "leaf", (claim(ALICE),), expected=leaf.ref)
        bind(w, changed, expected=b.ref); navigate(w, 0)
        w.execute(replace(cmd, command_id="resume", work_limit=64))
        r = w.recall_result(BOB, w.memory_job(BOB, cmd.task_id).result)
        self.assertEqual(r.bindings, (b.ref,))
        self.assertEqual(r.navigation, original_nav)
        self.assertEqual([h.memory for h in r.hits], [leaf.ref])
        self.assertEqual((r.bindings, r.visited, r.hits, r.truncated), complete_recall(w, r))

    @rules("F03", "F05")
    def test_linked_memory_in_wrong_context_is_not_returned_as_a_hit(self):
        w = world(); perform(w, ContextDraft("other", "another context"))
        other = w._journal[-1].contexts[0].ref
        leaf = write(w, "leaf", (claim(context=other),))
        root = write(w, "root", (), (leaf.ref,)); bind(w, root); navigate(w, 1)
        r, _ = recall(w)
        self.assertEqual(len(r.visited), 2); self.assertFalse(r.hits)


class RevisionTests(unittest.TestCase):
    @rules("F05", "F02")
    def test_old_binding_remains_exact_until_explicit_rebind(self):
        w = world(); old = write(w); b1 = bind(w, old)
        new = write(w, content=(claim(ALICE),), expected=old.ref)
        r, _ = recall(w)
        self.assertEqual(r.hits[0].memory, old.ref)
        b2 = bind(w, new, expected=b1.ref)
        r2, _ = recall(w)
        self.assertEqual(r2.hits[0].memory, new.ref)
        self.assertEqual(w.resolve_binding(BOB, b1.ref).target, old.ref)
        self.assertEqual(w.read_revision(BOB, old.ref).content[0].object, BOB)
        self.assertEqual(b2.ref.revision, 2)
        self.assertEqual(new.replaces, old.ref)
        self.assertIn(b1.ref, b2.learned_from)

    @rules("F05", "F07")
    def test_stale_write_fails_after_retained_work_without_lost_update(self):
        w = world(); old = write(w)
        pending = WriteDraft("m", (claim(ALICE),), (), ClaimStatus.ENDORSED, old.ref, "pending")
        cmd = perform(w, pending, basis=(old.ref,), limit=1)
        competing = write(w, content=(claim("another", relation="intent"),), expected=old.ref)
        before = w.truth.wallet(BOB)
        event = w.execute(replace(cmd, command_id="resume"))
        self.assertEqual(event.outcome, WorkStatus.FAILED)
        self.assertEqual(w.memory_head(BOB, "m"), competing)
        self.assertEqual(w.truth.wallet(BOB).energy, before.energy - 1)
        self.assertEqual(w.memory_job(BOB, cmd.task_id).completed_units, 2)

    @rules("F05", "F07")
    def test_stale_rebinding_does_not_replace_competing_head(self):
        w = world(); old = write(w); b = bind(w, old); new = write(w, content=(claim(ALICE),), expected=old.ref)
        p = BindDraft("b", CUE, ROOM, new.ref, SCOPE, b.ref)
        cmd = perform(w, p, basis=(new.ref, b.ref), limit=1)
        competing = bind(w, old, cue=SECOND, expected=b.ref)
        event = w.execute(replace(cmd, command_id="resume"))
        self.assertEqual(event.outcome, WorkStatus.FAILED)
        self.assertEqual(w.binding_head(BOB, "b"), competing)

    @rules("F05", "F10")
    def test_observation_revision_copies_scope_refs_and_provenance(self):
        w = world(); view, _ = w.select_input(BOB)
        draft, basis = observed_revision(view, view.observations[0].ref, BOX, "owned_by", "ownership")
        perform(w, draft, basis=basis)
        old = w.memory_head(BOB, "ownership")
        w.execute(Attempt("hidden", "hidden", request(ALICE, TRANSFER, (BOX, BOB))))
        w.apply(request(BOB, INSPECT, (BOX,)))
        view, _ = w.select_input(BOB, memories=(old.ref,))
        observed = view.observations[-1]
        draft, basis = observed_revision(view, observed.ref, BOX, "owned_by", "ownership", old)
        perform(w, draft, basis=basis)
        new = w.memory_head(BOB, "ownership")
        self.assertEqual(new.content, (observed.content[-1],))
        self.assertEqual(new.observations, (observed.ref,))
        self.assertEqual(new.derived_from, (old.ref,))
        self.assertEqual(old.content[0].object, ALICE)
        self.assertEqual(new.content[0].object, BOB)

    @rules("F05", "F06")
    def test_testimony_revision_is_tentative_and_unknown_accuracy_stays_unassessed(self):
        w = world(); p = claim("friendly", relation="intent")
        w.execute(Attempt("message", "message", request(ALICE, SEND, (BOB,)), message=MessageDraft((p,))))
        view, _ = w.select_input(BOB)
        draft, basis = observed_revision(view, view.observations[-1].ref, BOX, "intent", "intent")
        perform(w, draft, basis=basis)
        m = w.memory_head(BOB, "intent")
        self.assertEqual(m.claim_status, ClaimStatus.TENTATIVE)
        self.assertEqual(w.truth.check(p, w.now).status, EvidenceStatus.UNASSESSED)

    @rules("F05", "F06")
    def test_observation_helper_rejects_absent_ambiguous_or_foreign_input(self):
        w = world(); view, _ = w.select_input(BOB)
        for ref, relation in ((Ref(Kind.OBSERVATION, "missing", 1), "owned_by"),
                              (view.observations[0].ref, "unknown")):
            with self.assertRaises(ValueError): observed_revision(view, ref, BOX, relation, "x")
        o = view.observations[0]
        duplicate = replace(o, content=(claim(), claim(ALICE)))
        with self.assertRaises(ValueError): observed_revision(replace(view, observations=(duplicate,)), o.ref, BOX, "owned_by", "x")
        old = write(w, actor=ALICE)
        with self.assertRaises(ValueError): observed_revision(view, o.ref, BOX, "owned_by", "x", old)

    @rules("F05", "F09")
    def test_rebinding_moves_bucket_and_preserves_old_context(self):
        w = world(); m = write(w); old = bind(w, m)
        bind(w, m, cue=SECOND, expected=old.ref)
        gone, _ = recall(w); found, _ = recall(w, cues=(SECOND,))
        self.assertFalse(gone.hits)
        self.assertEqual(found.hits[0].memory, m.ref)
        self.assertEqual(w.resolve_binding(BOB, old.ref), old)
        self.assertNotIn((BOB, CUE, ROOM), w._buckets)


class BoundariesAndActions(unittest.TestCase):
    @rules("F06")
    def test_private_records_cannot_be_read_bound_linked_or_selected(self):
        w = world(); secret = write(w, actor=ALICE); binding = bind(w, secret)
        for operation in (lambda: w.read_revision(BOB, secret.ref),
                          lambda: w.resolve_binding(BOB, binding.ref),
                          lambda: w.select_input(BOB, memories=(secret.ref,)),
                          lambda: bind(w, replace(secret, owner=BOB)),
                          lambda: write(w, links=(secret.ref,))):
            before = w.checkpoint()
            with self.assertRaises(ValueError): operation()
            self.assertEqual(w.checkpoint(), before)

    @rules("F06")
    def test_invalid_inputs_reject_before_charges_or_mutation(self):
        w = world(); m = write(w)
        invalid = [MemoryCommand("bad", "bad", BOB, RecallQuery((CUE,), ROOM, Moment(999, 0))),
            MemoryCommand("bad", "bad", BOB, BindDraft("bad", Ref(Kind.CUE, "invented", 1), ROOM, m.ref, SCOPE), (m.ref,)),
            MemoryCommand("bad", "bad", BOB, WriteDraft("bad", (claim(Ref(Kind.ENTITY, "hidden", 1)),), (), ClaimStatus.ENDORSED, None, "bad"), (m.ref,)),
            MemoryCommand("bad", "bad", BOB, AckDraft(0, 999)),
            MemoryCommand("bad", "bad", BOB, WriteDraft("bad", (), (), ClaimStatus.ENDORSED, None, "bad")),
            MemoryCommand("bad", "bad", BOB, BindDraft("bad", CUE, ROOM, m.ref, SCOPE))]
        for cmd in invalid:
            before = w.checkpoint()
            with self.assertRaises(ValueError): w.execute(cmd)
            self.assertEqual(w.checkpoint(), before)

    @rules("F03", "F06", "F10")
    def test_hidden_world_and_evaluator_calls_leave_recall_and_action_identical(self):
        left, right = world(), world()
        for w in (left, right): bind(w, write(w, content=(claim(ALICE),)))
        left.execute(Attempt("hidden", "hidden", request(ALICE, TRANSFER, (BOX, BOB))))
        right.execute(Attempt("hidden", "hidden", request(ALICE, TRANSFER, (BOX, ALICE))))
        left.truth.check(claim(), left.now)
        l, _ = recall(left); r, _ = recall(right)
        self.assertEqual(l, r)
        lv, _ = left.select_input(BOB, memories=tuple(h.memory for h in l.hits))
        rv, _ = right.select_input(BOB, memories=tuple(h.memory for h in r.hits))
        self.assertEqual(lv, rv)
        self.assertEqual(ownership_action(lv, BOX, ALICE, ROOM, left.now), ownership_action(rv, BOX, ALICE, ROOM, right.now))
        for w in (left, right): w.apply(request(BOB, INSPECT, (BOX,)))
        self.assertNotEqual(left.select_input(BOB)[0].observations[-1].content, right.select_input(BOB)[0].observations[-1].content)

    @rules("F10", "F05")
    def test_recalled_correction_changes_permitted_action_and_world_consequence(self):
        w = world(); view, _ = w.select_input(BOB)
        draft, basis = observed_revision(view, view.observations[0].ref, BOX, "owned_by", "ownership")
        perform(w, draft, basis=basis); old = w.memory_head(BOB, "ownership"); binding = bind(w, old)
        w.execute(Attempt("transfer", "transfer", request(ALICE, TRANSFER, (BOX, BOB))))
        before, _ = recall(w)
        view, _ = w.select_input(BOB, memories=tuple(h.memory for h in before.hits))
        inspection = ownership_action(view, BOX, ALICE, ROOM, w.now)
        self.assertEqual(inspection.operation, INSPECT); w.apply(inspection)
        view, _ = w.select_input(BOB, memories=(old.ref,))
        draft, basis = observed_revision(view, view.observations[-1].ref, BOX, "owned_by", "ownership", old)
        perform(w, draft, basis=basis); new = w.memory_head(BOB, "ownership"); bind(w, new, expected=binding.ref)
        after, _ = recall(w)
        view, _ = w.select_input(BOB, memories=tuple(h.memory for h in after.hits))
        action = ownership_action(view, BOX, ALICE, ROOM, w.now)
        self.assertEqual(action.operation, TRANSFER); self.assertEqual(action.based_on, (new.ref,))
        self.assertEqual(w.apply(action).outcome, WorkStatus.COMPLETED)
        self.assertEqual(w.truth.current_fact(BOX, "owned_by", ROOM).object, ALICE)

    @rules("F06", "F10")
    def test_ambiguity_absence_and_retracted_content_choose_inspection(self):
        w = world(); a = write(w, "a"); b = write(w, "b", (claim(ALICE),))
        for refs in ((), (a.ref, b.ref), (b.ref,)):
            view, _ = w.select_input(BOB, memories=refs)
            self.assertEqual(ownership_action(view, BOX, ALICE, ROOM, w.now).operation, INSPECT)
        perform(w, WriteDraft("a", a.content, (), ClaimStatus.RETRACTED, a.ref, "withdrawn"), basis=(a.ref,))
        view, _ = w.select_input(BOB, memories=(w.memory_head(BOB, "a").ref,))
        self.assertEqual(ownership_action(view, BOX, ALICE, ROOM, w.now).operation, INSPECT)

    @rules("F06", "F08")
    def test_inbox_cursor_is_actor_specific_persistent_and_checked(self):
        w = world(); view, through = w.select_input(BOB)
        perform(w, AckDraft(0, through), basis=tuple(o.ref for o in view.observations))
        restored = RelationalWorld.restore(w.checkpoint())
        self.assertEqual(w.select_input(BOB), restored.select_input(BOB))
        self.assertEqual(len(w.select_input(BOB)[0].observations), 1)  # acknowledgement receipt
        self.assertEqual(len(w.select_input(ALICE)[0].observations), 1)  # original genesis
        cmd = perform(w, AckDraft(0, through), basis=())
        self.assertEqual(w.memory_job(BOB, cmd.task_id).outcome, WorkStatus.FAILED)

    @rules("F06")
    def test_returned_memory_bindings_results_and_cursor_are_immutable(self):
        w = world(); m = write(w); b = bind(w, m); navigate(w, 1); r, _ = recall(w)
        for record, field, value in ((m, "content", ()), (b, "target", m.ref), (r, "hits", ()), (w.navigation(BOB), "max_hops", 999)):
            with self.assertRaises(FrozenInstanceError): setattr(record, field, value)


class WorkAndReplay(unittest.TestCase):
    @rules("F07", "F08")
    def test_all_16_energy_time_pairs_preserve_partial_work_and_resume(self):
        for energy in range(4):
            for time in range(4):
                with self.subTest(energy=energy, time=time):
                    w = world(4 + energy, 4 + time); bind(w, write(w))
                    r, cmd = recall(w)
                    job = w.memory_job(BOB, cmd.task_id)
                    spent = min(2, energy, time)
                    self.assertEqual(job.completed_units, spent)
                    self.assertEqual(w.truth.wallet(BOB).energy, energy - spent)
                    self.assertEqual(w.truth.wallet(BOB).time, time - spent)
                    self.assertEqual(job.outcome, WorkStatus.COMPLETED if spent == 2 else WorkStatus.PARTIAL if spent else WorkStatus.DEFERRED)
                    self.assertEqual(r is not None, spent == 2)
                    restored = RelationalWorld.restore(w.checkpoint())
                    if spent < 2:
                        for candidate in (w, restored):
                            candidate.execute(Credit("fund", BOB, 2, 2, "test supply"))
                            candidate.execute(replace(cmd, command_id="resume"))
                            self.assertEqual(candidate.memory_job(BOB, cmd.task_id).completed_units, 2)
                    self.assertEqual(w.checkpoint(), restored.checkpoint())

    @rules("F07")
    def test_partial_write_publishes_nothing_and_charges_only_remaining_work(self):
        w = world(1, 1)
        draft = WriteDraft("m", (claim(), claim(item=TOOL)), (), ClaimStatus.TENTATIVE, None, "three units")
        cmd = perform(w, draft)
        self.assertIsNone(w.memory_head(BOB, "m"))
        self.assertEqual(w.memory_job(BOB, cmd.task_id).completed_units, 1)
        w.execute(Credit("fund", BOB, 2, 2, "test supply"))
        w.execute(replace(cmd, command_id="resume"))
        self.assertIsNotNone(w.memory_head(BOB, "m"))
        self.assertEqual(w.truth.wallet(BOB).energy, 0)

    @rules("F07", "F08")
    def test_duplicate_commands_do_not_double_charge_and_changed_retries_reject(self):
        w = world(); bind(w, write(w)); r, cmd = recall(w)
        before = w.checkpoint(); w.execute(cmd)
        self.assertEqual(before, w.checkpoint())
        with self.assertRaises(ValueError): w.execute(replace(cmd, work_limit=1))
        with self.assertRaises(ValueError): w.execute(replace(cmd, command_id="again"))
        self.assertEqual(before, w.checkpoint())

    @rules("F07")
    def test_changed_pending_query_rejects_without_losing_progress(self):
        w = world(); bind(w, write(w)); _, cmd = recall(w, limit=1)
        before = w.checkpoint()
        with self.assertRaises(ValueError):
            w.execute(replace(cmd, command_id="bad", payload=replace(cmd.payload, visit_limit=1)))
        self.assertEqual(w.checkpoint(), before)

    @rules("F07", "F08")
    def test_every_work_record_conserves_resources_in_order(self):
        w = world(); leaf = write(w); root = write(w, "root", (), (leaf.ref,)); bind(w, root); navigate(w, 5); recall(w)
        balances = {a: (10000, 10000) for a in (ALICE, BOB)}
        for tx in w.truth.journal():
            for work in tx.works:
                self.assertEqual(tuple(a.amount for a in work.before), balances[work.owner])
                balances[work.owner] = tuple(a.amount for a in work.after)
                self.assertEqual(w.truth.resolve(work.ref), work)
                self.assertEqual(work.completed_units, work.charged[0].amount)
        self.assertEqual(balances[BOB], (w.truth.wallet(BOB).energy, w.truth.wallet(BOB).time))

    @rules("F08")
    def test_every_demo_prefix_restores_and_continues_identically(self):
        from hle.memory_demo import run_memory_demo
        w, _ = run_memory_demo()
        journal = w.truth.journal()
        for split in range(1, len(journal) + 1):
            prefix = RelationalWorld(w.config)
            for tx in journal[1:split]: prefix.execute(tx.command)
            restored = RelationalWorld.restore(prefix.checkpoint())
            for tx in journal[split:]: restored.execute(tx.command)
            self.assertEqual(restored.checkpoint(), w.checkpoint())
            self.assertEqual(restored._buckets, w._buckets)
            self.assertEqual(restored._memory_jobs, w._memory_jobs)
            self.assertEqual(restored.select_input(BOB), w.select_input(BOB))

    @rules("F08")
    def test_rehashed_record_job_cursor_and_binding_tampering_rejects(self):
        w = world(); bind(w, write(w)); navigate(w, 1); recall(w, limit=1)
        cp = loads(w.checkpoint())
        variants = []
        for i, tx in enumerate(cp.journal):
            if type(tx) is not MemoryTransaction: continue
            if tx.bindings:
                variants.append(replace(cp, journal=cp.journal[:i] + (replace(tx, bindings=(replace(tx.bindings[0], cue=SECOND),)),) + cp.journal[i+1:]))
            if tx.navigations:
                variants.append(replace(cp, journal=cp.journal[:i] + (replace(tx, navigations=(replace(tx.navigations[0], max_hops=99),)),) + cp.journal[i+1:]))
        variants.append(replace(cp, journal=cp.journal[:-1] + (replace(cp.journal[-1], job=replace(cp.journal[-1].job, completed_units=99)),)))
        variants.append(replace(cp, journal=cp.journal + (cp.journal[-1],)))
        for variant in variants:
            with self.assertRaises(ValueError): RelationalWorld.restore(dumps(variant))

    @rules("F08")
    def test_r2_checkpoint_still_restores_in_r2_world(self):
        w = World(config()); w.apply(request(BOB, INSPECT, (BOX,)))
        self.assertEqual(World.restore(w.checkpoint()).checkpoint(), w.checkpoint())
        with self.assertRaises(ValueError): RelationalWorld.restore(w.checkpoint())


class IndexedWork(unittest.TestCase):
    @rules("F09", "F03")
    def test_live_indexes_match_full_reference_across_graphs_scopes_and_rebinding(self):
        for count in (1, 2, 4, 9):
            w = world(); memories = []
            for i in range(count):
                links = tuple(m.ref for m in memories[-2:])
                memories.append(write(w, str(i), (claim(BOB if i % 2 else ALICE),), links))
                bind(w, memories[-1], str(i), cue=CUE if i % 2 else SECOND)
            navigate(w, count)
            for cues in ((CUE,), (SECOND,), (CUE, SECOND), (SECOND, CUE)):
                for limit in (1, 3, 20):
                    r, _ = recall(w, cues=cues, visit_limit=limit)
                    self.assertEqual((r.bindings, r.visited, r.hits, r.truncated), complete_recall(w, r))
            for i, m in enumerate(memories):
                old = w.binding_head(BOB, str(i)); bind(w, m, str(i), cue=CUE, expected=old.ref)
            r, _ = recall(w)
            self.assertEqual((r.bindings, r.visited, r.hits, r.truncated), complete_recall(w, r))

    @rules("F09", "F06")
    def test_active_recall_and_action_cannot_scan_inactive_history_or_memory(self):
        for inactive in (0, 2000):
            w = world(); bind(w, write(w))
            for i in range(30): bind(w, write(w, f"unrelated:{i}"), f"unrelated:{i}", cue=SECOND)
            for i in range(inactive): w.execute(Tick(f"inactive:{i}"))
            cursor = w.select_input(BOB)[1]
            w._journal = NoWalkList(w._journal)
            w._changes = NoWalkList(w._changes)
            w._records = NoWalkDict(w._records)
            w._binding_heads = NoWalkDict(w._binding_heads)
            w._memory_heads[BOB] = NoWalkDict(w._memory_heads[BOB])
            r, _ = recall(w)
            self.assertEqual(len(r.visited), 1)
            view, cursor = w.select_input(BOB, memories=tuple(h.memory for h in r.hits), after=cursor)
            w.apply(ownership_action(view, BOX, ALICE, ROOM, w.now))
            self.assertLessEqual(len(w.select_input(BOB, after=cursor)[0].observations), 1)

    @rules("F09", "F05")
    def test_many_old_binding_revisions_leave_one_active_bucket_entry(self):
        w = world(); m = write(w); b = bind(w, m)
        for _ in range(100): b = bind(w, m, expected=b.ref)
        self.assertEqual(len(w._buckets[(BOB, CUE, ROOM)]), 1)
        r, _ = recall(w)
        self.assertEqual(r.bindings, (b.ref,))
        self.assertEqual(len(r.visited), 1)

    @rules("F01", "F10")
    def test_all_r3_checks_have_registered_rules_and_policy_is_predeclared(self):
        root = Path(__file__).resolve().parents[1]
        registry = json.loads((root / "docs/rules.json").read_text())
        ids = {r["id"] for r in registry["rules"]}
        for cls in (SourceCatalog, Associations, NavigationTests, RevisionTests, BoundariesAndActions, WorkAndReplay, IndexedWork):
            for name in unittest.defaultTestLoader.getTestCaseNames(cls):
                links = getattr(getattr(cls, name), "rule_ids", ())
                self.assertTrue(links and set(links) <= ids)
        self.assertTrue(json.loads((root / "docs/acceptance_plan_R3.json").read_text())["declared_before_acceptance"])
