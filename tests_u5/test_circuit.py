import unittest
from tests_u5.fixtures import *
from hle_unified.cognitive_routes import progress


class Circuit(unittest.TestCase):
    def test_complete_causal_workshop(self):
        e, refs = circuit()
        self.assertEqual(e.world.head(SAW.identity).ref.revision, 3)
        self.assertEqual(attrs(e.world.head(SAW.identity))["wear"], 1)
        self.assertEqual(attrs(e.world.head(STOCK.identity))["consumed"], 1)
        self.assertEqual(plan_request(e.participant_view(ALICE), refs["later"], "check").kind, "use")
        self.assertEqual(e.job_status(ALICE, "later-use")["concept_plan"], refs["later"])
        account = e.world.resolve(refs["retained"]).facet(Account)
        self.assertEqual(account.referent, ObjectRef(SAW.identity, 2))
        self.assertIn(refs["observation"], account.sources)
        self.assertEqual(account.content[0].object, "serviceable")
        self.assertEqual(e.world.resolve(ref("initial-account")).facet(Account).content[0].object, "damaged")
        field = attrs(e.world.resolve(e.job_status(ALICE, "retain")["field"]))
        self.assertEqual(field["tension"], "revision_change")
        self.assertFalse(e.participant_view(ALICE).can_use(REPAIR, ROOM))

    def test_reading_without_integration_keeps_old_action(self):
        e = setup5()
        p = think(e, request5(e))
        event = enact(e, p)
        o = receive(e, event, ALICE, "consequence")
        plan = think(e, request5(e, "no-retention", source=o))
        self.assertEqual(plan_request(e.participant_view(ALICE), plan, "check").kind, "inspect")
        self.assertFalse(any(b.ref.identity.namespace == "u5.account" for b in e.participant_view(ALICE).snapshot.bindings))

    def test_partial_work_resume_and_exact_continuation(self):
        e = setup5()
        r = request5(e)
        e.start("start", r)
        e.advance("partial", ALICE, r.key, 13)
        self.assertFalse(any(b.ref.identity.namespace == "u5.plan" for b in e.participant_view(ALICE).snapshot.bindings))
        checkpoint = e.checkpoint()
        restored = CognitiveEngine.restore(checkpoint)
        self.assertEqual(restored.checkpoint(), checkpoint)
        for x in (e, restored):
            x.advance("rest", ALICE, r.key, 1000)
            x.commit("finish", ALICE, r.key)
            enact(x, x.job_status(ALICE,r.key)["binding"])
        self.assertEqual(e.checkpoint(), restored.checkpoint())

    def test_model_a_and_crux_progress_are_separate(self):
        e = setup5()
        e.start("start", request5(e))
        d = e.job_status(ALICE,"plan")
        e.advance("recall", ALICE, "plan", d["recall_units"])
        self.assertEqual(progress(e.job_status(ALICE,"plan")), (d["active_start"], "I", 0))
        e.advance("rest", ALICE, "plan", 1000)
        self.assertEqual(progress(e.job_status(ALICE,"plan"))[1:], ("IT",2))
        self.assertFalse(any(b.ref.identity.namespace == "u5.plan" for b in e.participant_view(ALICE).snapshot.bindings))

    def test_cancel_keeps_cost_and_completed_cursor(self):
        e = setup5()
        initial = e.wallet(ALICE)["energy"]
        e.start("start", request5(e))
        e.advance("partial", ALICE, "plan", 16)
        d = e.job_status(ALICE,"plan")
        cursor = progress(d)[0]
        e.cancel("cancel", ALICE, "plan")
        e.start("restart", request5(e,"again"))
        self.assertEqual(e.job_status(ALICE,"again")["active_start"],cursor)
        self.assertEqual(e.wallet(ALICE)["energy"], initial-16)

    def test_idempotent_commands_and_no_double_enact_commit(self):
        e = setup5()
        r = request5(e)
        first = e.start("start",r)
        cp = e.checkpoint()
        self.assertEqual(e.start("start",r),first)
        self.assertEqual(e.checkpoint(),cp)
        with self.assertRaises(ValueError):
            e.start("start",replace(r,key="changed"))
        e.advance("work",ALICE,r.key,1000)
        e.commit("done",ALICE,r.key)
        with self.assertRaises(ValueError):
            e.commit("again",ALICE,r.key)

    def test_completed_replay_and_historical_view(self):
        e = setup5()
        before = e.participant_view(ALICE)
        cutoff = len(before.snapshot.history)
        p = think(e,request5(e))
        enact(e,p)
        restored = CognitiveEngine.restore(e.checkpoint())
        self.assertEqual(restored.checkpoint(),e.checkpoint())
        self.assertEqual(restored.participant_view(ALICE,through=cutoff).bytes(),before.bytes())

    def test_paid_surfaces_have_real_responsibilities(self):
        e, refs = circuit()
        surfaces = [v for tx in e.world.journal() for v in tx.versions if v.ref.identity.namespace == "u5.surface"]
        self.assertEqual(len(surfaces),6)
        assistance = surfaces[0]
        self.assertEqual(attrs(assistance)["responsibility"],"assistance_terms")
        self.assertEqual(assistance.facet(Account).content[0].object,BOB)
        self.assertEqual(attrs(surfaces[3])["retained"],refs["retained"])
        self.assertEqual(surfaces[3].facet(Account).content[0].object,"serviceable")
