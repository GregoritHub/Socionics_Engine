from dataclasses import replace
import unittest
from unittest.mock import patch

from hle_unified.particulars import Grant, Selector, DetailAddress, ParticipantView, AccessLedger
from hle_unified.records import (ObjectVersion, Attribute, Role, Definition, SourceStatus,
    Account, Moment, Occurrence, Proposition, TimeScope)
from hle_unified.store import next_version
from tests_u3.fixtures import *


class Acceptance(unittest.TestCase):
    def test_U3_01_hidden_changes_leave_views_reasons_and_choices_equal(self):
        for variant in range(8):
            with self.subTest(variant=variant):
                world, access = setup()
                basics(access, ALICE.identity)
                baseline = access.view(ALICE.identity)
                before, decision = baseline.bytes(), choose(baseline)
                world.transfer("hidden-transfer", WRITER, SAW, BOB.identity, actor=ALICE.identity)
                # Different global histories and definitions remain undelivered.
                for index in range(variant):
                    old = world.head(RULE.identity)
                    world.revise("hidden-rule-" + str(index), WRITER,
                        next_version(old, facets=(Definition("Private rule " + str(index), SourceStatus.ENGINEERING),)))
                if variant % 2:
                    basics(access, BOB.identity)
                    bind(access, BOB.identity, "bob-fear", meaning="Assistance respects my terms.", confidence=21)
                    show_procedure(access, BOB.identity)
                    work = receipt(world, "bob-acquire", BOB.identity, "acquire", "repair", (REPAIR, ROOM))
                    access.acquire(BOB.identity, REPAIR, ROOM, "repair", work)
                after = access.view(ALICE.identity)
                self.assertIsNot(baseline, after)  # hidden dependency really invalidated the cache
                self.assertEqual(before, after.bytes())
                self.assertEqual(decision, choose(after))
                self.assertEqual(after.resolve(ref("saw", 2)), ())
                self.assertEqual(after.resolve(ref("never-existed")), ())
                self.assertFalse(after.can_use(REPAIR, ROOM))
                # A lawful delivery and completed read can now change a decision.
                disclose(access, ALICE.identity, "new-owner", ref("saw", 2),
                    (Selector("owner", "ownership", ("facets", "0", "owner")),))
                current = access.view(ALICE.identity)
                self.assertEqual(choose(current)["choice"], "request-use")
                self.assertEqual(choose(current)["reasons"], ["saw", 2])

    def test_U3_02_shared_structure_keeps_actor_learning_separate(self):
        world, access = setup()
        for actor in (ALICE.identity, BOB.identity):
            basics(access, actor)
        av, bv = access.view(ALICE.identity), access.view(BOB.identity)
        ad, bd = av.detail(DetailAddress("cue", "meaning")), bv.detail(DetailAddress("cue", "meaning"))
        self.assertIs(ad.value, bd.value)  # one physical immutable definition value
        bob_before = bv.bytes()
        bind(access, ALICE.identity, "alice-fear", confidence=94)
        show_procedure(access, ALICE.identity)
        read_only = access.view(ALICE.identity)
        self.assertFalse(read_only.can_use(REPAIR, ROOM))
        work = receipt(world, "alice-acquire", ALICE.identity, "acquire", "repair", (REPAIR, ROOM))
        access.acquire(ALICE.identity, REPAIR, ROOM, "repair", work)
        self.assertTrue(access.view(ALICE.identity).can_use(REPAIR, ROOM))
        self.assertFalse(access.view(ALICE.identity).can_use(REPAIR, ref("other-context")))
        self.assertEqual(bob_before, access.view(BOB.identity).bytes())
        self.assertEqual(access.view(BOB.identity).lookup(key="procedure"), ())
        self.assertFalse(access.view(BOB.identity).snapshot.bindings)
        with self.assertRaises(ValueError):
            access.acquire(BOB.identity, REPAIR, ROOM, "repair", work)

    def test_U3_03_indexed_particulars_and_concept_binding_share_exact_refs(self):
        world, access = setup()
        basics(access, ALICE.identity)
        before_history = access.view(ALICE.identity).snapshot.history
        with patch.object(ParticipantView, "traverse", side_effect=AssertionError("detail lookup traversed a concept")):
            detail = access.view(ALICE.identity).lookup(key="owner", subject=SAW.identity)[0]
            self.assertEqual(detail.source, SAW)
            self.assertEqual(detail.value, ALICE.identity)
        self.assertEqual(before_history, access.view(ALICE.identity).snapshot.history)
        binding = bind(access, ALICE.identity, "alice-fear")
        walk = access.view(ALICE.identity).traverse(CUE, ROOM)
        self.assertEqual(walk.visited, (binding,))
        self.assertEqual(walk.particulars, (detail,))
        self.assertEqual(walk.bindings[0].target, SAW)
        self.assertEqual(walk.bindings[0].confidence, 80)
        self.assertFalse(walk.truncated)
        self.assertEqual(access.view(ALICE.identity).traverse(CUE, RULE).visited, ())

    def test_incompatible_accounts_do_not_overwrite_material_truth(self):
        world, access = setup()
        basics(access, ALICE.identity)
        basics(access, BOB.identity)
        world.transfer("transfer", WRITER, SAW, BOB.identity, actor=ALICE.identity)
        claim = ObjectVersion(ref("alice-remembers"), WRITER, "Earlier ownership account", (Role.CLAIM,),
            (Account(SAW, (Proposition(SAW, "owner", ALICE.identity, ROOM, TimeScope(Moment(0, 0), None)),),
                Moment(3, 0), ALICE.identity),), occurrence=Occurrence.REMEMBERED_CLAIM)
        world.create("claim", WRITER, (claim,))
        disclose(access, ALICE.identity, "memory-owner", claim.ref,
            (Selector("owner", "ownership", ("facets", "0", "content", "0", "object")),), subject=SAW)
        disclose(access, BOB.identity, "actual-owner", ref("saw", 2),
            (Selector("owner", "ownership", ("facets", "0", "owner")),), subject=SAW)
        a = bind(access, ALICE.identity, "alice-account", addresses=(DetailAddress("memory-owner", "owner"),),
            meaning="The tool is mine; help may be control.", confidence=91)
        b = bind(access, BOB.identity, "bob-account", addresses=(DetailAddress("actual-owner", "owner"),),
            meaning="The tool was given to me; help can be offered.", confidence=63)
        self.assertEqual(access.view(ALICE.identity).lookup(key="owner")[-1].value, ALICE.identity)
        self.assertEqual(access.view(BOB.identity).lookup(key="owner")[-1].value, BOB.identity)
        self.assertEqual(world.head(SAW.identity).facet(Material).owner, BOB.identity)
        self.assertNotEqual(a, b)
        self.assertEqual(world.resolve(claim.ref).occurrence, Occurrence.REMEMBERED_CLAIM)

    def test_historical_binding_meanings_and_actor_views_restore_exactly(self):
        world, access = setup()
        basics(access, ALICE.identity)
        first = bind(access, ALICE.identity, "belief", meaning="Help means control.", confidence=83)
        earlier = access.view(ALICE.identity).bytes()
        earlier_sequence = len(access.view(ALICE.identity).snapshot.history)
        old_definition = world.resolve(CUE)
        world.revise("revise-cue", WRITER, next_version(old_definition,
            facets=(Definition("Changed public anchor wording.", SourceStatus.ENGINEERING),)))
        second = bind(access, ALICE.identity, "belief", meaning="Help can respect terms.", confidence=52, previous=first)
        restored = AccessLedger.restore(access.checkpoint())
        self.assertEqual(restored.checkpoint(), access.checkpoint())
        self.assertEqual(restored.view(ALICE.identity).bytes(), access.view(ALICE.identity).bytes())
        self.assertEqual(restored.view(ALICE.identity, through=earlier_sequence).bytes(), earlier)
        history = restored.view(ALICE.identity).snapshot.bindings
        self.assertEqual([b.meaning for b in history], ["Help means control.", "Help can respect terms."])
        self.assertEqual(restored.view(ALICE.identity).traverse(CUE, ROOM).visited, (second,))
        self.assertEqual(restored.view(ALICE.identity).detail(DetailAddress("cue", "meaning")).value, old_definition.facet(Definition))
        self.assertEqual(restored.world.resolve(first).ref, first)


if __name__ == "__main__":
    unittest.main()
