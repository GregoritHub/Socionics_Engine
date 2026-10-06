from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
import hashlib
import json
from pathlib import Path
import sys
import unittest

from hle.contracts import ClaimStatus, EvidenceStatus
from hle_unified import codec, legacy
from hle_unified.records import (
    ObjectId, ObjectRef, ObjectVersion, Role, Material, Memory, Agency, Governance,
    Relation, Endpoint, Attribute, Account, Attitude, Assessment, Composition,
    Concept, Procedure, Definition, SourceStatus, Occurrence, Lifecycle, ChangeKind,
    Moment, TimeScope, Proposition, Lineage, LegacyPayload, LegacyRecord, LegacyEnum, LegacyField)
from hle_unified.store import ObjectStore, next_version
from .fixtures import WRITER, ALICE, BOB, ROOM, UNIT, FORM, LAW, RULE, base, bowl, event, ref, ident, active_quantities


class Controls(unittest.TestCase):
    def assert_rejected_without_change(self, store, action):
        before = store.checkpoint()
        with self.assertRaises(ValueError):
            action()
        self.assertEqual(store.checkpoint(), before)

    def test_strict_immutable_shapes_and_unique_role_state(self):
        with self.assertRaises(ValueError):
            ObjectRef(ident("x"), True)
        with self.assertRaises(ValueError):
            ObjectId(" ", "x")
        with self.assertRaises(ValueError):
            Attribute("mutable", [])
        with self.assertRaises(ValueError):
            ObjectVersion(ref("x"), WRITER, "x", (Role.MATERIAL,))
        with self.assertRaises(ValueError):
            replace(bowl("x"), facets=bowl("x").facets * 2)
        with self.assertRaises(FrozenInstanceError):
            bowl("x").label = "changed"
        with self.assertRaises(ValueError):
            Definition("Invented meaning", SourceStatus.UNSPECIFIED)
        self.assertIsNone(Definition(None, SourceStatus.UNSPECIFIED).meaning)

    def test_stale_revision_skip_and_writer_takeover_reject_atomically(self):
        s = base()
        old = s.resolve(RULE)
        new = next_version(old, label="revised")
        s.revise("first", WRITER, new)
        self.assert_rejected_without_change(s, lambda: s.revise("stale", WRITER, next_version(old, label="losing edit")))
        forged = replace(next_version(new, label="takeover"), writer="other.writer")
        self.assert_rejected_without_change(s, lambda: s.revise("takeover", "other.writer", forged))
        skipped = replace(new, ref=ref("return-rule", 4), previous=ref("return-rule", 3))
        self.assert_rejected_without_change(s, lambda: s.commit("skip", WRITER, (skipped,),
            (Lineage(ChangeKind.REVISE, (new.ref,), (skipped.ref,), (), "Skipped revision"),)))

    def test_mixed_valid_invalid_batch_leaves_no_published_objects(self):
        s = base()
        good = bowl("valid")
        bad = replace(bowl("invalid"), definition=ref("missing-definition"))
        self.assert_rejected_without_change(s, lambda: s.create("bad-batch", WRITER, (good, bad)))
        with self.assertRaises(KeyError):
            s.resolve(good.ref)
        self.assert_rejected_without_change(s, lambda: s.create("duplicate", WRITER, (good, good)))

    def test_relation_context_and_exact_endpoint_integrity(self):
        s = base()
        relation = Relation("owes", (Endpoint("debtor", ALICE), Endpoint("creditor", BOB)),
                            True, ALICE, TimeScope(Moment(0, 0), None))
        obj = ObjectVersion(ref("relation"), WRITER, "obligation", (Role.RELATION,), (relation,))
        self.assert_rejected_without_change(s, lambda: s.create("wrong-context", WRITER, (obj,)))
        missing = replace(relation, context=ROOM, endpoints=(Endpoint("debtor", ALICE), Endpoint("creditor", ref("bob", 99))))
        self.assert_rejected_without_change(s, lambda: s.create("missing-endpoint", WRITER, (replace(obj, facets=(missing,)),)))

    def test_same_key_retry_is_idempotent_and_conflict_rejects(self):
        s = base()
        obj = bowl("one")
        tx = s.create("one", WRITER, (obj,))
        before = s.checkpoint()
        self.assertEqual(s.create("one", WRITER, (obj,)), tx)
        self.assertEqual(before, s.checkpoint())
        self.assert_rejected_without_change(s, lambda: s.create("one", WRITER, (bowl("other"),)))

    def test_two_concurrent_writers_cannot_both_spend_one_revision(self):
        s = base()
        obj = bowl("concurrent", 8)
        s.create("stock", WRITER, (obj,))
        def attempt(token):
            try:
                s.restructure("consume-" + token, WRITER, (obj.ref,), (bowl(token, 8),),
                    actor=ALICE.identity, rule=LAW, reason="Concurrent ownership attempt")
                return True
            except ValueError:
                return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(attempt, ("a", "b")))
        self.assertEqual(sorted(outcomes), [False, True])
        self.assertEqual(active_quantities(s), {(ALICE.identity, UNIT): 8})

    def test_hypothesis_cannot_be_promoted_or_rewrite_actual_event(self):
        s = base()
        prediction = ObjectVersion(ref("possible"), WRITER, "possible", (Role.CLAIM,),
            (Account(RULE, (), Moment(1, 0), ALICE.identity),), occurrence=Occurrence.HYPOTHETICAL)
        actual = event("actual")
        s.create("accounts", WRITER, (prediction, actual))
        promoted = next_version(prediction, roles=(Role.EVENT,), occurrence=Occurrence.ACTUAL_EVENT)
        self.assert_rejected_without_change(s, lambda: s.revise("promote", WRITER, promoted))
        self.assert_rejected_without_change(s, lambda: s.revise("rewrite", WRITER, next_version(actual, label="rewritten")))
        with self.assertRaises(ValueError):
            replace(prediction, roles=(Role.CLAIM, Role.EVENT))
        with self.assertRaises(ValueError):
            Attitude(ALICE.identity, prediction.ref, ClaimStatus.ENDORSED, 101)
        with self.assertRaises(ValueError):
            Assessment(prediction.ref, "truth", EvidenceStatus.ESTABLISHED, (), "No evidence")

    def test_all_occurrence_categories_remain_distinct_after_roundtrip(self):
        s = base()
        roles = (Role.EVENT, Role.OBSERVATION, Role.CLAIM, Role.CLAIM, Role.INTERPRETATION)
        for i, (category, role) in enumerate(zip(Occurrence, roles)):
            obj = ObjectVersion(ref("category-" + str(i)), WRITER, category.value, (role,),
                (Account(RULE, (), Moment(i, 0), None if category == Occurrence.ACTUAL_EVENT else ALICE.identity),), occurrence=category)
            s.create("category-" + str(i), WRITER, (obj,))
        restored = ObjectStore.restore(s.checkpoint())
        self.assertEqual(len(restored.actual_events()), 1)
        self.assertEqual({restored.resolve(ref("category-" + str(i))).occurrence for i in range(5)}, set(Occurrence))

    def test_material_changes_require_supported_transition_and_owner(self):
        s = base()
        obj = bowl("owned", 4)
        s.create("owned", WRITER, (obj,))
        self.assert_rejected_without_change(s, lambda: s.transfer("steal", WRITER, obj.ref, BOB.identity, actor=BOB.identity))
        counterfeit = next_version(obj, facets=(replace(obj.facet(Material), quantity=100),))
        self.assert_rejected_without_change(s, lambda: s.revise("inflate", WRITER, counterfeit))
        new_owner = replace(obj.facet(Material), owner=BOB.identity, custodian=BOB.identity)
        self.assert_rejected_without_change(s, lambda: s.revise("unauthorized-generic-transfer", WRITER,
            next_version(obj, facets=(new_owner,))))
        self.assert_rejected_without_change(s, lambda: s.transfer("unknown-recipient", WRITER, obj.ref, ident("absent"), actor=ALICE.identity))

    def test_material_conservation_owner_unit_law_and_consumption_controls(self):
        s = base()
        obj = bowl("stock", 10)
        other = bowl("bob-stock", 5, owner=BOB)
        s.create("stocks", WRITER, (obj, other))
        scenarios = (
            ((obj.ref,), (bowl("inflated", 11),), ALICE.identity, LAW),
            ((obj.ref,), (bowl("lost", 9),), ALICE.identity, LAW),
            ((obj.ref,), (bowl("unauthorized", 10),), BOB.identity, LAW),
            ((obj.ref, other.ref), (bowl("mixed", 15),), ALICE.identity, LAW),
            ((obj.ref,), (bowl("unlawful", 10),), ALICE.identity, RULE),
            ((obj.ref,), (bowl("stolen", 10, owner=BOB),), ALICE.identity, LAW),
            ((obj.ref, obj.ref), (bowl("duplicated", 20),), ALICE.identity, LAW),
            ((obj.ref,), (replace(bowl("wrong-unit", 10), facets=(replace(obj.facet(Material), unit=FORM),)),), ALICE.identity, LAW),
        )
        for i, (inputs, outputs, actor, law) in enumerate(scenarios):
            with self.subTest(i=i):
                self.assert_rejected_without_change(s, lambda: s.restructure(str(i), WRITER, inputs, outputs,
                    actor=actor, rule=law, reason="Negative control"))

    def test_raw_commit_cannot_create_unretired_split_outputs(self):
        s = base()
        original = bowl("stock", 2)
        s.create("stock", WRITER, (original,))
        a, b = bowl("a"), bowl("b")
        edge = Lineage(ChangeKind.DIVIDE, (original.ref,), (a.ref, b.ref), (), "Unretired split", LAW)
        self.assert_rejected_without_change(s, lambda: s.commit("bad-split", WRITER, (a, b), (edge,), actor=ALICE.identity))

    def test_retirement_is_terminal_and_cannot_remove_material_state(self):
        s = base()
        original, target = bowl("old", 2), bowl("new", 2)
        s.create("old", WRITER, (original,))
        self.assert_rejected_without_change(s, lambda: s.revise("erase", WRITER,
            next_version(original, roles=(Role.RECORD,), facets=())))
        s.restructure("replace", WRITER, (original.ref,), (target,), actor=ALICE.identity, rule=LAW, reason="Replacement")
        retired = s.head(original.ref.identity)
        self.assert_rejected_without_change(s, lambda: s.revise("revive", WRITER,
            next_version(retired, lifecycle=Lifecycle.ACTIVE)))

    def test_definition_and_membership_changes_need_explicit_lineage(self):
        s = base()
        old = s.resolve(RULE)
        revised = next_version(old, facets=(Definition("New terms", SourceStatus.ENGINEERING),))
        edge = Lineage(ChangeKind.REVISE, (old.ref,), (revised.ref,), (), "Missing definition lineage")
        self.assert_rejected_without_change(s, lambda: s.commit("hidden-change", WRITER, (revised,), (edge,)))
        group = ObjectVersion(ref("group"), WRITER, "group", (Role.COLLECTIVE,), (Composition((ALICE.identity,), "voluntary"),))
        s.create("group", WRITER, (group,))
        updated = next_version(group, facets=(Composition((BOB.identity,), "voluntary"),))
        edge = Lineage(ChangeKind.REVISE, (group.ref,), (updated.ref,), (), "Missing membership lineage")
        self.assert_rejected_without_change(s, lambda: s.commit("hidden-membership", WRITER, (updated,), (edge,)))

    def test_definitions_and_optional_capabilities_use_exact_bindings(self):
        s = base()
        person = ObjectVersion(ref("learner"), WRITER, "Learner", (Role.PERSON,),
            (Memory(ident("learner")), Agency(ident("learner"))))
        concept = ObjectVersion(ref("concept"), WRITER, "Return concept", (Role.CONCEPT,),
            (Concept((Proposition(ALICE, "uses", RULE, ROOM, TimeScope(Moment(1, 0), None)),)),))
        procedure = ObjectVersion(ref("procedure"), WRITER, "Inspect then return", (Role.PROCEDURE,),
            (Procedure(("tool",), (), (), (), None),), definition=RULE)
        s.create("roles", WRITER, (person, concept, procedure))
        updated = next_version(s.resolve(RULE), facets=(Definition("New rule", SourceStatus.ENGINEERING),))
        s.revise("rule", WRITER, updated)
        rebound = next_version(procedure, definition=updated.ref)
        s.revise("explicit-rebind", WRITER, rebound)
        self.assertEqual(s.resolve(procedure.ref).definition, RULE)
        self.assertEqual(s.head(procedure.ref.identity).definition, updated.ref)
        self.assertEqual(s.resolve(person.ref).facet(Agency).acquired, ())
        self.assertEqual(s.resolve(person.ref).facet(Memory).entries, ())
        with self.assertRaises(ValueError):
            replace(person, facets=(Memory(ALICE.identity),))
        self.assertEqual(ObjectStore.restore(s.checkpoint()).checkpoint(), s.checkpoint())

    def test_codec_rejects_unknown_mutable_duplicate_and_tampered_values(self):
        s = base()
        text = s.checkpoint()
        corrupt = json.loads(text)
        corrupt["payload"]["fields"]["schema"] = "wrong"
        with self.assertRaises(ValueError):
            ObjectStore.restore(json.dumps(corrupt))
        corrupt["sha256"] = hashlib.sha256(codec.canonical(corrupt["payload"]).encode()).hexdigest()
        with self.assertRaises(ValueError):
            ObjectStore.restore(json.dumps(corrupt))
        for value in ([1, 2], {"mutable": True}, 2.5):
            with self.assertRaises(ValueError):
                codec.dumps(value)
        with self.assertRaises(ValueError):
            codec.loads('{"format":"a","format":"b"}')
        with self.assertRaises(ValueError):
            codec.decode({"record": "os.system", "fields": {}})

    def test_rehashed_journal_with_forged_material_quantity_rejects(self):
        s = base()
        obj = bowl("stock", 5)
        s.create("stock", WRITER, (obj,))
        target = bowl("replacement", 5)
        s.restructure("replace", WRITER, (obj.ref,), (target,), actor=ALICE.identity, rule=LAW, reason="Replacement")
        cp = codec.loads(s.checkpoint())
        last = cp.journal[-1]
        forged = replace(target, facets=(replace(target.facet(Material), quantity=6),))
        last = replace(last, versions=(last.versions[0], forged))
        altered = replace(cp, journal=cp.journal[:-1] + (last,))
        with self.assertRaisesRegex(ValueError, "conservation"):
            ObjectStore.restore(codec.dumps(altered))

    def test_replay_rejects_duplicate_out_of_order_and_unresolved_history(self):
        s = base()
        cp = codec.loads(s.checkpoint())
        for journal in ((cp.journal[0], cp.journal[0]),
                        (replace(cp.journal[0], at=Moment(2, 0)),)):
            with self.assertRaises(ValueError):
                ObjectStore.restore(codec.dumps(replace(cp, journal=journal)))
        self.assertEqual(ObjectStore.restore(ObjectStore().checkpoint()).journal(), ())

    def test_legacy_views_cannot_be_written_to_native_store(self):
        from hle.demo import config
        from hle.world import World
        w = World(config())
        view = legacy.object_view(w.truth.journal()[0].event)
        s = base()
        self.assert_rejected_without_change(s, lambda: s.create("second-writer", "legacy.r21b", (view,)))
        with self.assertRaises(FrozenInstanceError):
            view.label = "edited"
        with self.assertRaises(ValueError):
            legacy.recover_object(replace(view, roles=(Role.CLAIM,), occurrence=Occurrence.HYPOTHETICAL))

    def test_legacy_adapter_rejects_unknown_tag_changed_fields_and_identity(self):
        from hle.demo import config
        from hle.world import World
        value = World(config()).truth.journal()[0].event
        adapted = legacy.adapt(value)
        for invalid in (replace(adapted, tag="arbitrary.executable"),
                        replace(adapted, fields=adapted.fields[:-1]),
                        LegacyRecord("Record", ()),
                        LegacyEnum("WorkStatus", True)):
            with self.assertRaises(ValueError):
                legacy.recover(invalid)
        view = legacy.object_view(value)
        with self.assertRaises(ValueError):
            legacy.recover_object(replace(view, ref=ObjectRef(ObjectId("legacy.ref.event", "other"), 1)))
        with self.assertRaises(ValueError):
            legacy.recover_ref(ref("native"))
        with self.assertRaises(ValueError):
            legacy.object_view(value, address=ObjectRef(ObjectId("legacy.ref.event", "renamed"), 1))
        with self.assertRaises(ValueError):
            LegacyRecord("bad", (LegacyField("x", 1), LegacyField("x", 2)))

    def test_legacy_false_memory_and_observation_categories_are_exact(self):
        from hle.contracts import Proposition as LP, ClaimStatus
        from hle.demo import config, request, ALICE as LA, BOB as LB, BOX, ROOM as LR
        from hle.world import World
        from hle.world_records import Attempt, MemoryDraft, RETAIN
        w = World(config())
        claim = LP(BOX, "owned_by", LB, LR, TimeScope(w.now, None))
        w.execute(Attempt("remember-false", "job", request(LA, RETAIN),
            memory=MemoryDraft("belief", (claim,), ClaimStatus.ENDORSED, "False account fixture")))
        tx = w.truth.journal()[-1]
        for value, category in ((tx.event, Occurrence.ACTUAL_EVENT), (tx.observations[0], Occurrence.OBSERVATION),
                                (tx.memories[0], Occurrence.REMEMBERED_CLAIM)):
            view = legacy.object_view(value)
            self.assertEqual(view.occurrence, category)
            self.assertEqual(legacy.recover_object(codec.loads(codec.dumps(view))), value)
        self.assertEqual(w.truth.current_fact(BOX, "owned_by", LR).object, LA)

    def test_legacy_hidden_fact_and_evaluator_checks_do_not_leak_through_views(self):
        from hle.demo import config, request, ALICE as LA, BOB as LB, BOX
        from hle.world_records import Attempt, TRANSFER
        left, right = legacy.LegacyWorldBridge(config()), legacy.LegacyWorldBridge(config())
        left.execute(Attempt("hidden", "h", request(LA, TRANSFER, (BOX, LB))))
        right.execute(Attempt("hidden", "h", request(LA, TRANSFER, (BOX, LA))))
        left.inspect_object(legacy.adapt_ref(BOX))
        left.ownership_history(legacy.adapt_ref(BOX))
        self.assertEqual(left.participant_input(legacy.adapt_ref(LB)), right.participant_input(legacy.adapt_ref(LB)))

    def test_version4_zero_budget_checkpoint_exact_roundtrip_and_continuation(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "baseline/HLE_Rebuild_R21B/tools"))
        from r21b_policy import run_candidate
        from hle.closure import ClosureWorld
        from hle.world_records import Tick
        w, metadata = run_candidate("iee", 12, "inadequate")
        original = w.checkpoint()
        adapted = legacy.checkpoint_object(original, "v4-zero")
        converted = legacy.checkpoint_text(codec.loads(codec.dumps(adapted)))
        self.assertEqual(converted, original)
        restored = ClosureWorld.restore(converted)
        self.assertEqual(restored.checkpoint(), original)
        self.assertEqual(len(w._journal), 3)
        w.execute(Tick("after-roundtrip"))
        restored.execute(Tick("after-roundtrip"))
        self.assertEqual(restored.checkpoint(), w.checkpoint())
        self.assertFalse(restored._capacities)


if __name__ == "__main__":
    unittest.main()
