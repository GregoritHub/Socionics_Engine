import unittest
from dataclasses import replace
from hle_unified.records import Material
from hle_unified.operations import OperationEngine
from hle_unified.material import attrs, available
from hle_unified.store import next_version
from .fixtures import *


class U4Acceptance(unittest.TestCase):
    def test_u4_01_paid_repair_interrupt_restore_and_resume(self):
        engine = setup()
        before_budget = engine.wallet(ALICE)["energy"]
        request = repair(engine)
        engine.start("start", request)
        engine.advance("partial", ALICE, request.key, 2)
        self.assertEqual(engine.job_status(ALICE, request.key)["completed"], 2)
        self.assertEqual(engine.world.head(SAW.identity).ref, SAW)
        self.assertEqual(available(engine.world.head(STOCK.identity)), 2)
        saved = engine.checkpoint()
        restored = OperationEngine.restore(saved)
        self.assertEqual(restored.checkpoint(), saved)
        for world in (engine, restored):
            world.advance("rest", ALICE, request.key, 100)
            self.assertEqual(world.world.head(SAW.identity).ref, SAW)
            world.commit("effect", ALICE, request.key)
        self.assertEqual(engine.checkpoint(), restored.checkpoint())
        self.assertEqual(engine.world.head(SAW.identity).facet(Material).condition, "serviceable")
        self.assertEqual(attrs(engine.world.head(KIT.identity))["wear"], 1)
        self.assertEqual(available(engine.world.head(STOCK.identity)), 1)
        self.assertEqual(before_budget - engine.wallet(ALICE)["energy"], 6)

    def test_u4_02_stale_definition_retains_work_and_earlier_effect(self):
        engine = setup()
        first = perform(engine, repair(engine))
        for r in (KIT, STOCK):
            show(engine, ALICE, engine.world.head(r.identity).ref)
        engine.start("second", repair(engine, "second", SAW2))
        engine.advance("second-partial", ALICE, "second", 2)
        old = engine.world.resolve(FORM)
        changed = next_version(old, label="Revised tool definition")
        # Definition content, not a label alone, is a live semantic dependency.
        changed = replace(changed, facets=(replace(old.facet(Definition), meaning="New workshop tool constraints"),))
        view = engine.participant_view(ALICE).bytes()
        engine.declare("definition-change", (changed,))
        self.assertEqual(engine.participant_view(ALICE).bytes(), view)
        engine.advance("second-finish", ALICE, "second", 100)
        failed = engine.commit("second-effect", ALICE, "second")
        state = engine.job_status(ALICE, "second")
        self.assertEqual((state["status"], state["failure"], state["spent"]), ("failed", "stale_dependency", 6))
        self.assertEqual(engine.world.head(SAW2.identity).ref, SAW2)
        self.assertEqual(engine.world.head(SAW.identity).facet(Material).condition, "serviceable")
        self.assertEqual(attrs(engine.world.resolve(first))["outcome"], "succeeded")
        self.assertEqual(attrs(engine.world.resolve(failed))["outcome"], "failed")
        self.assertEqual(available(engine.world.head(STOCK.identity)), 1)

    def test_u4_03_competing_repairs_never_double_spend(self):
        for targets in ((SAW, SAW2), (SAW2, SAW)):
            with self.subTest(targets=targets):
                engine = setup(quantity=1)
                a, b = repair(engine, "a", targets[0]), repair(engine, "b", targets[1])
                engine.start("a", a)
                engine.start("b", b)
                engine.advance("b-wait", ALICE, "b", 100)
                self.assertEqual(engine.job_status(ALICE, "b")["status"], "waiting")
                self.assertEqual(engine.job_status(ALICE, "b")["spent"], 0)
                engine.advance("a-work", ALICE, "a", 100)
                engine.commit("a-effect", ALICE, "a")
                engine.advance("b-work", ALICE, "b", 100)
                engine.commit("b-effect", ALICE, "b")
                self.assertEqual(engine.job_status(ALICE, "b")["failure"], "stale_dependency")
                self.assertEqual(available(engine.world.head(STOCK.identity)), 0)
                self.assertEqual(engine.world.head(targets[1].identity).ref, targets[1])

    def test_u4_04_event_delivery_read_interpretation_retention_are_separate(self):
        engine = setup()
        basics(engine, BOB)
        before_a, before_b = engine.participant_view(ALICE).bytes(), engine.participant_view(BOB).bytes()
        event = perform(engine, repair(engine))
        self.assertEqual(engine.participant_view(ALICE).bytes(), before_a)
        self.assertEqual(engine.participant_view(BOB).bytes(), before_b)
        obs = engine.deliver_event("alice-delivery", event, ALICE)
        self.assertFalse(engine.participant_view(ALICE).resolve(obs))
        read = OperationRequest("read-physical", ALICE, "read", ROOM, delivery="alice-delivery")
        engine.start("read-start", read)
        engine.advance("read-partial", ALICE, read.key, 1)
        self.assertFalse(engine.participant_view(ALICE).resolve(obs))
        engine.advance("read-rest", ALICE, read.key, 1)
        engine.commit("read-commit", ALICE, read.key)
        self.assertTrue(engine.participant_view(ALICE).resolve(obs))
        self.assertFalse(engine.participant_view(ALICE).snapshot.bindings)
        interpret = binding(engine, "help-account", ALICE, obs)
        perform(engine, interpret)
        self.assertEqual(len(engine.participant_view(ALICE).snapshot.bindings), 1)
        self.assertFalse(engine.participant_view(ALICE).can_use(REPAIR, ROOM))
        perform(engine, OperationRequest("retain-repair", ALICE, "acquire", ROOM, procedure=REPAIR, practice=event))
        self.assertTrue(engine.participant_view(ALICE).can_use(REPAIR, ROOM))
        self.assertEqual(engine.participant_view(BOB).bytes(), before_b)
        bob_obs = receive(engine, event, BOB, "bob-later")
        self.assertGreater(engine.world.resolve(bob_obs).facet(Account).at, engine.world.resolve(obs).facet(Account).at)
        self.assertFalse(engine.participant_view(BOB).snapshot.bindings)
        self.assertFalse(engine.participant_view(BOB).can_use(REPAIR, ROOM))
        self.assertEqual(engine.world.resolve(obs).facet(Account).sources, (event,))
        restored = OperationEngine.restore(engine.checkpoint())
        self.assertEqual(restored.participant_view(ALICE).bytes(), engine.participant_view(ALICE).bytes())
