from dataclasses import replace
import json
import unittest
from unittest.mock import patch

from hle_unified.compact import CompactStore, ValuePool, seal, unseal, VersionIndex
from hle_unified.particulars import *
from hle_unified.records import (ObjectVersion, Attribute, Role, Definition, SourceStatus,
    Account, Occurrence, Assessment, EvidenceStatus, Agency, Memory)
from hle_unified.store import ObjectStore, next_version
from tests_u2.fixtures import bowl, LAW
from tests_u3.fixtures import *


class AccessControls(unittest.TestCase):
    def setUp(self):
        self.world, self.access = setup()

    def test_delivery_partial_completion_and_work_history(self):
        work = disclose(self.access, ALICE.identity, "owner", SAW,
            (Selector("owner", "ownership", ("facets", "0", "owner")),), completed=1)
        view = self.access.view(ALICE.identity)
        self.assertEqual(view.lookup(key="owner"), ())
        self.assertEqual(view.snapshot.pending, (Pending("owner", Moment(5, 0)),))
        self.assertFalse(view.receipt(work).complete)
        saved = self.access.checkpoint()
        resumed = AccessLedger.restore(saved)
        final = receipt(resumed.world, "read-complete", ALICE.identity, "read", "owner", (SAW,))
        resumed.process(ALICE.identity, "owner", final)
        self.assertEqual(resumed.view(ALICE.identity).lookup(key="owner")[0].value, ALICE.identity)
        self.assertEqual([r.completed for r in resumed.view(ALICE.identity).work_receipts("read", "owner")], [1, 2])
        self.assertFalse(resumed.view(ALICE.identity).snapshot.pending)

    def test_receipt_wrong_owner_work_revision_or_authority_rejects_atomically(self):
        self.access.grant(Grant("g", ALICE.identity, SAW, SAW, (Selector("owner", "ownership", ("facets", "0", "owner")),)))
        self.access.deliver(ALICE.identity, "d", "g", Moment(0, 0))
        self.world.transfer("transfer", WRITER, SAW, BOB.identity, actor=ALICE.identity)
        for i, actor, key, source in ((0, BOB.identity, "d", SAW), (1, ALICE.identity, "other", SAW),
                                     (2, ALICE.identity, "d", ref("saw", 2))):
            with self.subTest(i=i):
                r = receipt(self.world, "wrong-" + str(i), actor, "read", key, (source,))
                before = self.access.view(ALICE.identity).bytes()
                with self.assertRaises(ValueError):
                    self.access.process(ALICE.identity, "d", r)
                self.assertEqual(before, self.access.view(ALICE.identity).bytes())
        good = receipt(self.world, "forged", ALICE.identity, "read", "d", (SAW,))
        old = self.world.resolve(good)
        forged = replace(old, ref=ref("unrecognized-writer"), writer=WRITER)
        self.world.create("fake-work", WRITER, (forged,))
        with self.assertRaises(ValueError):
            self.access.process(ALICE.identity, "d", forged.ref)

    def test_receipt_reuse_and_work_rollback_reject(self):
        work = disclose(self.access, ALICE.identity, "owner", SAW,
            (Selector("owner", "ownership", ("facets", "0", "owner")),), completed=1)
        before = self.access.view(ALICE.identity).bytes()
        with self.assertRaises(ValueError):
            self.access.process(ALICE.identity, "owner", work)
        bad = receipt(self.world, "backwards", ALICE.identity, "read", "owner", (SAW,), completed=0)
        with self.assertRaises(ValueError):
            self.access.process(ALICE.identity, "owner", bad)
        self.assertEqual(before, self.access.view(ALICE.identity).bytes())

    def test_grant_revocation_retains_memory_and_grants_no_future_revision(self):
        basics(self.access, ALICE.identity)
        before = self.access.view(ALICE.identity).bytes()
        self.access.revoke(ALICE.identity, "grant-tool")
        with self.assertRaises(ValueError):
            self.access.deliver(ALICE.identity, "again", "grant-tool", Moment(6, 0))
        self.world.transfer("hidden", WRITER, SAW, BOB.identity, actor=ALICE.identity)
        self.assertEqual(before, self.access.view(ALICE.identity).bytes())
        self.assertEqual(self.access.view(ALICE.identity).resolve(ref("saw", 2)), ())

    def test_reference_disclosure_does_not_disclose_target_contents(self):
        basics(self.access, ALICE.identity)
        view = self.access.view(ALICE.identity)
        self.assertEqual(view.detail(DetailAddress("tool", "form")).value, FORM)
        self.assertEqual(view.resolve(FORM), ())
        self.assertEqual(view.resolve(ref("missing")), ())
        self.assertEqual(view.lookup(subject=FORM.identity), ())
        self.assertEqual(view.lookup(key="hidden-cache-reason"), ())

    def test_other_actor_private_account_and_capability_cannot_be_disclosed(self):
        basics(self.access, BOB.identity)
        private = bind(self.access, BOB.identity, "private")
        self.assertRaises(ValueError, self.access.grant,
            Grant("spy", ALICE.identity, private, SAW, (Selector("meaning", "detail", ("attributes", "2", "value")),)))
        bob = self.world.resolve(BOB)
        new = next_version(bob, facets=(Agency(BOB.identity, (REPAIR,)), Memory(BOB.identity, (private,))))
        self.world.revise("private-state", WRITER, new)
        self.assertRaises(ValueError, self.access.grant,
            Grant("spy2", ALICE.identity, new.ref, BOB, (Selector("use", "detail", ("facets", "0", "acquired", "0")),)))

    def test_assessments_are_excluded_from_participant_access(self):
        evaluation = ObjectVersion(ref("assessment"), WRITER, "Privileged result", (Role.ASSESSMENT,),
            (Assessment(SAW, "truth", EvidenceStatus.UNASSESSED, (), "Not participant evidence"),))
        self.world.create("assessment", WRITER, (evaluation,))
        self.assertRaises(ValueError, self.access.grant, Grant("g", ALICE.identity, evaluation.ref, SAW,
            (Selector("label", "detail", ("label",)),)))

    def test_exact_names_dates_events_and_receipts_have_separate_indexes(self):
        basics(self.access, ALICE.identity)
        event = ObjectVersion(ref("event"), WRITER, "Transfer observed", (Role.EVENT,),
            (Account(SAW, (), Moment(2, 7)),), occurrence=Occurrence.ACTUAL_EVENT)
        self.world.create("event", WRITER, (event,))
        work = disclose(self.access, ALICE.identity, "event", event.ref,
            (Selector("date", "date", ("facets", "0", "at")), Selector("event", "event", ("ref",))))
        view = self.access.view(ALICE.identity)
        self.assertEqual(len(view.lookup(category="name", value="Workshop saw")), 1)
        self.assertEqual(view.lookup(category="date", value=Moment(2, 7))[0].source, event.ref)
        self.assertEqual(view.lookup(category="event", value=event.ref)[0].occurrence, Occurrence.ACTUAL_EVENT)
        self.assertEqual(view.receipt(work).inputs, (event.ref,))
        self.assertEqual(view.receipt(ref("not-a-receipt")), None)

    def test_same_named_instances_have_distinct_particulars(self):
        self.world.create("bowls", WRITER, (bowl("bowl-a"), bowl("bowl-b")))
        for name in ("bowl-a", "bowl-b"):
            disclose(self.access, ALICE.identity, name, ref(name), (Selector("name", "name", ("label",)),))
        view = self.access.view(ALICE.identity)
        self.assertEqual(len(view.lookup(value="White bowl")), 2)
        self.assertEqual(len(view.lookup(subject=ident("bowl-a"))), 1)

    def test_concept_links_are_contextual_bounded_and_cycle_safe(self):
        basics(self.access, ALICE.identity)
        first = bind(self.access, ALICE.identity, "first", links=(ref("first"),))
        second = bind(self.access, ALICE.identity, "second", links=(first,))
        view = self.access.view(ALICE.identity)
        self.assertEqual(view.traverse(CUE, ROOM).visited, (first, second))
        self.assertTrue(view.traverse(CUE, ROOM, visit_limit=1).truncated)
        self.assertFalse(view.traverse(CUE, ROOM, visit_limit=2).truncated)
        self.assertEqual(view.traverse(CUE, RULE).visited, ())
        with self.assertRaises(ValueError):
            view.traverse(CUE, ROOM, visit_limit=True)

    def test_binding_cannot_use_undelivered_details_or_other_actor_links(self):
        for actor in (ALICE.identity, BOB.identity):
            basics(self.access, actor)
        foreign = bind(self.access, BOB.identity, "bob-only")
        invalid = interpretation(self.world, "illegal-link", ALICE.identity, links=(foreign,))
        work = receipt(self.world, "illegal-work", ALICE.identity, "bind", "illegal-link", (invalid, SAW))
        before = self.access.view(ALICE.identity).bytes()
        with self.assertRaises(ValueError):
            self.access.bind(ALICE.identity, invalid, (DetailAddress("tool", "owner"),), work)
        with self.assertRaises(ValueError):
            self.access.bind(ALICE.identity, invalid, (DetailAddress("never-received", "owner"),), work)
        self.assertEqual(before, self.access.view(ALICE.identity).bytes())

    def test_partial_acquisition_cannot_grant_use(self):
        basics(self.access, ALICE.identity)
        show_procedure(self.access, ALICE.identity)
        work = receipt(self.world, "partial-use", ALICE.identity, "acquire", "repair", (REPAIR, ROOM), completed=1)
        with self.assertRaises(ValueError):
            self.access.acquire(ALICE.identity, REPAIR, ROOM, "repair", work)
        self.assertFalse(self.access.view(ALICE.identity).can_use(REPAIR, ROOM))

    def test_reading_procedure_name_is_not_reading_its_structure(self):
        basics(self.access, ALICE.identity)
        disclose(self.access, ALICE.identity, "name-only", REPAIR, (Selector("name", "name", ("label",)),))
        work = receipt(self.world, "name-use", ALICE.identity, "acquire", "repair", (REPAIR, ROOM))
        with self.assertRaises(ValueError):
            self.access.acquire(ALICE.identity, REPAIR, ROOM, "repair", work)

    def test_actor_view_is_detached_and_immutable(self):
        basics(self.access, ALICE.identity)
        view = self.access.view(ALICE.identity)
        self.assertFalse(hasattr(view, "world"))
        with self.assertRaises(AttributeError):
            view.snapshot = None
        with self.assertRaises(TypeError):
            view._keys["secret"] = ()
        old = view.bytes()
        bind(self.access, ALICE.identity, "new")
        self.assertEqual(view.bytes(), old)
        self.assertNotEqual(self.access.view(ALICE.identity).bytes(), old)

    def test_grant_rejects_malformed_projection_before_publication(self):
        for path in (("__dict__",), ("facets", "-1"), ("facets", "00"), ("facets", "10")):
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    self.access.grant(Grant("bad", ALICE.identity, SAW, SAW, (Selector("bad", "detail", path),)))
        self.assertFalse(self.access._grants)

    def test_actor_local_history_ignores_other_actor_event_count(self):
        basics(self.access, ALICE.identity)
        early = self.access.view(ALICE.identity).bytes()
        count = len(self.access.view(ALICE.identity).snapshot.history)
        basics(self.access, BOB.identity)
        bind(self.access, BOB.identity, "b")
        self.assertEqual(self.access.view(ALICE.identity).bytes(), early)
        self.assertEqual(self.access.view(ALICE.identity, through=count).bytes(), early)
        self.assertEqual(len(self.access.view(ALICE.identity, through=0).snapshot.history), 0)

    def test_historical_rights_do_not_rebind_to_current_actor_roles(self):
        basics(self.access, ALICE.identity)
        before = self.access.view(ALICE.identity).bytes()
        old = self.world.resolve(ALICE)
        self.world.revise("later-role", WRITER, next_version(old, roles=(Role.RECORD,)))
        restored = AccessLedger.restore(self.access.checkpoint())
        self.assertEqual(restored.view(ALICE.identity).bytes(), before)

    def test_exact_value_index_distinguishes_boolean_and_integer(self):
        obj = ObjectVersion(ref("typed-values"), WRITER, "values", (Role.RECORD,),
            attributes=(Attribute("flag", False), Attribute("count", 0)))
        self.world.create("typed-values", WRITER, (obj,))
        disclose(self.access, ALICE.identity, "typed", obj.ref,
            (Selector("flag", "detail", ("attributes", "0", "value")),
             Selector("count", "detail", ("attributes", "1", "value"))))
        view = self.access.view(ALICE.identity)
        self.assertEqual([p.address.key for p in view.lookup(value=False)], ["flag"])
        self.assertEqual([p.address.key for p in view.lookup(value=0)], ["count"])


class CompactControls(unittest.TestCase):
    def test_retry_cannot_replace_boolean_with_equal_valued_integer(self):
        world, _ = setup()
        obj = ObjectVersion(ref("typed-retry"), WRITER, "flag", (Role.RECORD,), attributes=(Attribute("v", False),))
        tx = world.create("typed-retry", WRITER, (obj,))
        before = world.checkpoint()
        with self.assertRaises(ValueError):
            world.commit(tx.key, tx.writer, (replace(obj, attributes=(Attribute("v", 0),)),), tx.lineage)
        self.assertEqual(world.checkpoint(), before)

    def test_24_revision_trace_matches_independent_full_snapshot_store(self):
        full = base()
        compact = CompactStore.from_store(full)
        for i in range(24):
            old = full.head(RULE.identity)
            value = next_version(old, label="Rule " + str(i),
                attributes=(Attribute("value", [False, 0, True, 1, None, "1"][i % 6]),))
            full.revise("r" + str(i), WRITER, value)
            compact.revise("r" + str(i), WRITER, value)
            self.assertEqual(full.checkpoint(), compact.canonical_checkpoint())
        restored = CompactStore.restore(compact.checkpoint())
        self.assertEqual(full.checkpoint(), restored.canonical_checkpoint())
        for tx in full.journal():
            for version in tx.versions:
                self.assertEqual(codec.dumps(version), codec.dumps(restored.resolve(version.ref)))

    def test_unchanged_state_is_omitted_and_type_changes_are_retained(self):
        full = base()
        v = ObjectVersion(ref("flag"), WRITER, "flag", (Role.RECORD,), attributes=(Attribute("flag", False),))
        full.create("flag", WRITER, (v,))
        compact = CompactStore.from_store(full)
        nv = next_version(v, attributes=(Attribute("flag", 0),))
        compact.revise("flag-zero", WRITER, nv)
        self.assertEqual([n for n, _ in compact._versions.rows[nv.ref][1]], ["attributes"])
        self.assertIs(type(compact.resolve(nv.ref).attributes[0].value), int)
        self.assertIs(type(compact.resolve(v.ref).attributes[0].value), bool)

    def test_equal_immutable_definitions_are_physically_shared_with_distinct_ids(self):
        world, _ = setup()
        shared = Definition("One shared structure.", SourceStatus.ENGINEERING)
        a = ObjectVersion(ref("a"), WRITER, "A", (Role.DEFINITION,), (shared,))
        b = ObjectVersion(ref("b"), WRITER, "B", (Role.DEFINITION,), (replace(shared),))
        world.create("definitions", WRITER, (a, b))
        self.assertIs(world.resolve(a.ref).facet(Definition), world.resolve(b.ref).facet(Definition))
        self.assertNotEqual(world.resolve(a.ref).ref, world.resolve(b.ref).ref)

    def test_material_lineage_and_rejected_writes_preserve_laws(self):
        full = base()
        compact = CompactStore.from_store(full)
        for store in (full, compact):
            store.create("stock", WRITER, (bowl("stock", 5),))
            store.restructure("split", WRITER, (ref("stock"),), (bowl("small", 2), bowl("large", 3)),
                actor=ALICE.identity, rule=LAW, reason="matched conservation witness")
            store.transfer("transfer", WRITER, ref("small"), BOB.identity, actor=ALICE.identity)
        self.assertEqual(full.checkpoint(), compact.canonical_checkpoint())
        before = compact.checkpoint()
        with self.assertRaises(ValueError):
            compact.transfer("bad", WRITER, ref("large"), BOB.identity, actor=BOB.identity)
        self.assertEqual(before, compact.checkpoint())

    def test_exact_dependency_index_and_cache_invalidation_are_internal(self):
        world, access = setup()
        basics(access, ALICE.identity)
        old = access.view(ALICE.identity)
        self.assertIn(SAW, world.dependents(FORM))
        self.assertNotIn(SAW, world.dependents(ref("bowl-form", 2)))
        old_form = world.resolve(FORM)
        world.revise("form", WRITER, next_version(old_form, label="Hidden current form"))
        new = access.view(ALICE.identity)
        self.assertIsNot(old, new)
        self.assertEqual(old.bytes(), new.bytes())

    def test_pool_hash_verification_and_collision_reject(self):
        pool = ValuePool()
        a = pool.put(("a",))
        pool.nodes[a[1]] = ("tuple", ("tampered",))
        with self.assertRaises(ValueError):
            pool.put(("a",))
        bad = [["tuple", [["@", 0]]]]
        with self.assertRaises(ValueError):
            ValuePool().load_nodes(bad)

    def test_rehashed_compact_checkpoint_with_unused_or_reordered_data_rejects(self):
        world, _ = setup()
        data = unseal(world.checkpoint(), CompactStore.SCHEMA)
        extra = ValuePool()
        extra.put(("unreferenced",))
        data["nodes"].extend(extra.export()[0])
        with self.assertRaises(ValueError):
            CompactStore.restore(seal(CompactStore.SCHEMA, data))
        data = unseal(world.checkpoint(), CompactStore.SCHEMA)
        data["journal"].reverse()
        with self.assertRaises(ValueError):
            CompactStore.restore(seal(CompactStore.SCHEMA, data))

    def test_access_replay_rejects_rehashed_omission_and_extra_nodes(self):
        world, access = setup()
        basics(access, ALICE.identity)
        data = unseal(access.checkpoint(), AccessLedger.SCHEMA)
        del data["events"][0]
        with self.assertRaises((ValueError, KeyError)):
            AccessLedger.restore(seal(AccessLedger.SCHEMA, data))
        data = unseal(access.checkpoint(), AccessLedger.SCHEMA)
        pool = ValuePool()
        pool.put(("unreachable",))
        data["nodes"].extend(pool.export()[0])
        with self.assertRaises(ValueError):
            AccessLedger.restore(seal(AccessLedger.SCHEMA, data))


if __name__ == "__main__":
    unittest.main()
