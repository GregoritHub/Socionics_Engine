import unittest
from dataclasses import replace
from tests_u6.fixtures import *
from hle_unified.anticipation import forecast, choose, state_of
from hle_unified.autonomy_audit import audit
from hle_unified.compact import seal, unseal


class Continuation(unittest.TestCase):
    def test_forecast_changes_affordable_action_under_matched_cost(self):
        a=setup6(prior="serviceable",serviceable=True,wear=2)
        b=setup6(prior="serviceable",serviceable=True,wear=2,anticipation=False)
        self.assertEqual(first_choice(a),"care")
        self.assertEqual(first_choice(b),"use")
        self.assertEqual(a.wallet(ALICE),b.wallet(ALICE))
        self.assertGreater(a.wallet(ALICE)["energy"],6)
        self.assertEqual(attrs(a.world.head(SAW.identity))["wear"],2)

    def test_prediction_is_hypothetical_and_cannot_be_foreign_knowledge(self):
        e=setup6(); first_choice(e)
        self.assertTrue(predictions(e))
        self.assertTrue(all(p.occurrence==Occurrence.HYPOTHETICAL for p in predictions(e)))
        self.assertEqual(e.world.head(SAW.identity).ref,SAW)
        self.assertFalse(e.participant_view(BOB).snapshot.bindings)
        with self.assertRaises(ValueError):show(e,BOB,predictions(e)[0].ref)

    def test_workshop_runs_repair_learning_and_two_uses_without_action_script(self):
        e=setup6(); rows=drive(e,latency=2)
        self.assertTrue(e.state(ALICE).stopped)
        self.assertEqual(e.state(ALICE).uses,2)
        self.assertEqual(e.state(ALICE).reason,"standing_demand_satisfied_by_observed_work")
        self.assertEqual(attrs(e.world.head(STOCK.identity))["consumed"],1)
        self.assertEqual(attrs(e.world.head(SAW.identity))["wear"],2)
        self.assertFalse(e.participant_view(ALICE).can_use(REPAIR,ROOM))
        self.assertTrue(any(r["decision"]=="rest" for r in rows))

    def test_received_surprise_investigates_corrects_and_continues(self):
        e=setup6(prior="serviceable"); rows=drive(e)
        surprises=[v for v in errors(e) if attrs(v)["surprise"]]
        self.assertEqual(len(surprises),1)
        self.assertEqual(attrs(surprises[0])["errors"],"outcome")
        self.assertIn("test_received_surprise",[r["reason"] for r in rows])
        self.assertEqual(e.state(ALICE).uses,2)
        self.assertEqual(e.world.resolve(ref("initial-account")).facet(Account).content[0].object,"serviceable")
        self.assertTrue(audit(e.world.journal())["passed"])

    def test_unseen_effect_waits_without_cost_or_history_growth(self):
        e=setup6(prior="serviceable"); drive(e,delivery=False)
        self.assertIsNotNone(e.state(ALICE).await_event)
        self.assertFalse(errors(e))
        # One transition names the external wait; subsequent polls are quiescent.
        e.step("idle-0",ALICE); cp=e.checkpoint()
        for i in range(8):self.assertIsNone(e.step("idle-"+str(i+1),ALICE))
        self.assertEqual(e.checkpoint(),cp)
        self.assertFalse(errors(e))

    def test_delivery_and_partial_read_do_not_appraise(self):
        e=setup6(prior="serviceable",work_limit=1); drive(e,delivery=False)
        obs=e.deliver_event("arrived",e.state(ALICE).await_event,ALICE)
        self.assertFalse(errors(e)); self.assertFalse(e.participant_view(ALICE).resolve(obs))
        e.step("read-start",ALICE)
        self.assertEqual(e.state(ALICE).active_kind,"read")
        self.assertFalse(errors(e)); self.assertFalse(e.participant_view(ALICE).resolve(obs))
        e.step("read-half",ALICE)
        self.assertFalse(e.participant_view(ALICE).resolve(obs))

    def test_unrelated_event_does_not_satisfy_named_wait(self):
        e=setup6(); drive(e,delivery=False)
        waiting=e.state(ALICE).await_event
        event=perform(e,OperationRequest("other-inspect",ALICE,"inspect",ROOM,target=SAW2,evidence=evidence(e,ALICE,SAW2)))
        e.deliver_event("unrelated",event,ALICE)
        for i in range(8):e.step("unrelated-read-"+str(i),ALICE)
        self.assertEqual(e.state(ALICE).await_event,waiting)
        self.assertEqual(e.state(ALICE).uses,0)
        self.assertFalse(errors(e))

    def test_hidden_material_variants_keep_same_pre_delivery_choice(self):
        rows=[]
        for wear in (0,4,9,10):
            e=setup6(hidden_kit_wear=wear)
            before=e.participant_view(ALICE).bytes()
            choice=first_choice(e)
            rows.append((before,choice,e.state(ALICE),tuple(p.facet(Account).content for p in predictions(e))))
        self.assertTrue(all(row==rows[0] for row in rows))

    def test_repeated_observed_failure_switches_to_paid_request(self):
        e=setup6(hidden_kit_wear=10); rows=drive(e)
        self.assertEqual(e.state(ALICE).failures,2)
        self.assertEqual(e.state(ALICE).phase,"help_wait")
        self.assertIn("switch",[r["decision"] for r in rows])
        self.assertEqual(e.state(ALICE).decision,"ask")
        self.assertTrue(e.participant_view(BOB).snapshot.pending)
        self.assertFalse(e.participant_view(BOB).snapshot.particulars)
        self.assertEqual(audit(e.world.journal())["requests"],1)

    def test_new_assistance_delivery_wakes_pending_intent(self):
        e=setup6(offer=False); drive(e)
        self.assertEqual(e.state(ALICE).phase,"help_wait")
        oldtarget=e.state(ALICE).target
        help_offer(e,"later-offer",oldtarget,read=False)
        rows=drive(e,prefix="resumed")
        self.assertIn("received_changed_assistance",[r["reason"] for r in rows])
        self.assertEqual(e.state(ALICE).uses,2)

    def test_partial_plan_restores_identically(self):
        e=setup6(work_limit=1)
        e.step("begin",ALICE); e.step("work",ALICE)
        self.assertEqual(e.state(ALICE).active_kind,"plan")
        cp=e.checkpoint(); clone=AutonomousEngine.restore(cp)
        for x in (e,clone):
            for i in range(3):x.step("next-"+str(i),ALICE)
        self.assertEqual(e.checkpoint(),clone.checkpoint())

    def test_partial_forecast_restores_identically(self):
        e=setup6(work_limit=1)
        drive(e,delivery=False,stop_when=lambda x:x.state(ALICE).active_kind=="anticipate")
        e.step("forecast-first-unit",ALICE)
        self.assertEqual(e.state(ALICE).active_kind,"anticipate")
        cp=e.checkpoint(); clone=AutonomousEngine.restore(cp)
        self.assertEqual(clone.checkpoint(),cp)
        for x in (e,clone):first_choice(x,prefix="finish-forecast")
        self.assertEqual(e.checkpoint(),clone.checkpoint())

    def test_partial_material_action_restores_identically(self):
        e=setup6(work_limit=1); first_choice(e)
        e.step("partial-action",ALICE)
        self.assertEqual(e.job_status(ALICE,e.state(ALICE).active)["completed"],1)
        clone=AutonomousEngine.restore(e.checkpoint())
        for x in (e,clone):drive(x,delivery=False,prefix="resume-action")
        self.assertEqual(e.checkpoint(),clone.checkpoint())

    def test_wait_checkpoint_continues_after_allowed_delivery(self):
        e=setup6(); drive(e,delivery=False)
        clone=AutonomousEngine.restore(e.checkpoint())
        for x in (e,clone):drive(x,prefix="wake")
        self.assertEqual(e.checkpoint(),clone.checkpoint())
        self.assertEqual(e.state(ALICE).uses,2)

    def test_stopped_actor_does_not_spin_and_commands_are_idempotent(self):
        e=setup6(goal_uses=0)
        result=e.step("stop",ALICE); cp=e.checkpoint()
        self.assertEqual(e.step("stop",ALICE),result)
        self.assertIsNone(e.step("after-stop",ALICE))
        self.assertEqual(e.checkpoint(),cp)
        with self.assertRaises(ValueError):e.step("stop",BOB)

    def test_budget_stop_retains_partial_work_and_no_negative_budget(self):
        probe=setup6(); preparation=1200-probe.wallet(ALICE)["energy"]
        e=setup6(budget=preparation+5,work_limit=1)
        drive(e)
        self.assertTrue(e.state(ALICE).stopped)
        self.assertTrue(e.state(ALICE).active)
        self.assertGreaterEqual(min(e.wallet(ALICE)[k] for k in ("energy","time")),0)
        self.assertFalse(predictions(e))
        self.assertEqual(AutonomousEngine.restore(e.checkpoint()).state(ALICE),e.state(ALICE))

    def test_rest_reduces_fatigue_only_and_preserves_unfinished_thought(self):
        e=setup6(fatigue_limit=5,work_limit=2)
        for i in range(20):
            before=e.state(ALICE); wallet=e.wallet(ALICE); acquired=e.participant_view(ALICE).snapshot.acquired
            e.step("fatigue-"+str(i),ALICE)
            if e.state(ALICE).decision=="rest":break
        else:self.fail("rest was never caused by work")
        self.assertEqual(e.state(ALICE).active,before.active)
        self.assertLess(e.state(ALICE).fatigue,before.fatigue)
        self.assertEqual(e.wallet(ALICE)["energy"],wallet["energy"]-1)
        self.assertEqual(e.wallet(ALICE)["time"],wallet["time"]-1)
        self.assertEqual(e.participant_view(ALICE).snapshot.acquired,acquired)

    def test_pressure_changes_available_processing_but_not_skill(self):
        states=[]
        for demand in (1,10):
            e=setup6(goal_uses=demand,work_limit=2)
            e.step("begin",ALICE); e.step("work",ALICE)
            states.append((e.state(ALICE).pressure,e.job_status(ALICE,e.state(ALICE).active)["spent"],e.participant_view(ALICE).snapshot.acquired))
        self.assertGreater(states[1][0],states[0][0])
        self.assertGreater(states[1][1],states[0][1])
        self.assertEqual(states[1][2],states[0][2])

    def test_boredom_causes_paid_exploration_without_acquisition(self):
        e=setup6(goal_uses=4,boredom_limit=1)
        rows=drive(e,stop_when=lambda x:x.state(ALICE).decision=="explore")
        self.assertEqual(e.state(ALICE).decision,"explore")
        self.assertGreaterEqual(e.state(ALICE).boredom,1)
        self.assertEqual(e.job_status(ALICE,e.state(ALICE).active)["target"].identity,SAW2.identity)
        self.assertFalse(e.participant_view(ALICE).snapshot.acquired)

    def test_processed_threat_sets_boundary_and_preserves_partial_work(self):
        e=setup6(); e.step("begin",ALICE); e.step("partial",ALICE)
        before=e.state(ALICE).active
        obs=ObjectVersion(ref("declared-threat"),WRITER,"Declared threat input",(Role.OBSERVATION,),
            (Account(SAW,(),Moment(0,0),ALICE),),occurrence=Occurrence.OBSERVATION,
            attributes=attributes({"target":SAW,"context":ROOM,"threat":4}))
        e.declare("threat-input",(obs,))
        e.disclose("threat-delivery",ALICE,obs.ref,tuple(Selector(a.name,"detail",("attributes",str(i),"value")) for i,a in enumerate(obs.attributes)),SAW)
        for i in range(8):e.step("threat-"+str(i),ALICE)
        self.assertEqual(e.state(ALICE).reason,"processed_threat_exceeds_declared_boundary")
        self.assertEqual(e.state(ALICE).active,before)
        self.assertFalse(e.participant_view(ALICE).snapshot.acquired)

    def test_bounded_forecast_reports_censored_coverage(self):
        e=setup6(prior="serviceable",serviceable=True,wear=2,max_nodes=1)
        first_choice(e)
        f=e._forecast_results[e.state(ALICE).forecast]
        self.assertEqual(f["nodes"],1)
        self.assertEqual(f["coverage"],"censored")
        self.assertGreater(f["unevaluated"],0)

    def test_named_procedure_does_not_award_forecast_candidate(self):
        e=setup6(offer=False); first_choice(e)
        self.assertNotIn("acquired_procedure",[attrs(p)["basis"] for p in predictions(e)])

    def test_actual_acquired_procedure_adds_repair_candidate(self):
        e=setup6(offer=False)
        event=perform(e,repair(e,"practice-other",target=SAW2))
        receive(e,event,ALICE,"practice")
        perform(e,OperationRequest("acquire",ALICE,"acquire",ROOM,procedure=REPAIR,practice=event))
        show(e,ALICE,e.world.head(KIT.identity).ref)
        first_choice(e)
        self.assertEqual(e.state(ALICE).last_action,"repair")
        self.assertIn("acquired_procedure",[attrs(p)["basis"] for p in predictions(e)])

    def test_same_revision_correction_guides_later_u5_plan(self):
        e=setup5(prior="serviceable")
        event=perform(e,OperationRequest("inspect",ALICE,"inspect",ROOM,target=SAW,evidence=evidence(e,ALICE,SAW)))
        obs=receive(e,event,ALICE,"truth")
        think(e,request5(e,"correct","integrate",source=obs))
        plan=think(e,request5(e,"later"))
        self.assertEqual(plan_request(e.participant_view(ALICE),plan,"check").kind,"repair")

    def test_forecast_stale_account_fails_without_refunding(self):
        e=setup6()
        drive(e,delivery=False,stop_when=lambda x:x.state(ALICE).active_kind=="anticipate")
        key=e.state(ALICE).active
        e.advance("pay-forecast",ALICE,key,100)
        spent=e.job_status(ALICE,key)["spent"]
        seed(e,"new-memory","serviceable")
        e.commit("stale-forecast",ALICE,key)
        self.assertEqual(e.job_status(ALICE,key)["failure"],"changed_actor_recall")
        self.assertEqual(e.job_status(ALICE,key)["spent"],spent)
        self.assertFalse(predictions(e))

    def test_cancelled_anticipation_keeps_charges_and_publishes_nothing(self):
        e=setup6(work_limit=1)
        drive(e,delivery=False,stop_when=lambda x:x.state(ALICE).active_kind=="anticipate")
        key=e.state(ALICE).active
        e.advance("one-unit",ALICE,key,1); wallet=e.wallet(ALICE)
        e.cancel("cancel-forecast",ALICE,key)
        self.assertEqual(e.wallet(ALICE),wallet)
        self.assertFalse(predictions(e))

    def test_wrong_owner_cannot_start_forecast(self):
        e=setup6(); first_choice(e)
        cp=e.checkpoint()
        with self.assertRaises(ValueError):ForecastRequest("foreign",BOB,e.state(ALICE).plan,e._configs[ALICE])
        self.assertEqual(e.checkpoint(),cp)

    def test_rehashed_forged_checkpoint_is_rejected(self):
        e=setup6(); e.step("begin",ALICE)
        data=unseal(e.checkpoint(),e.SCHEMA)
        data["world"]=setup6().world.checkpoint()
        with self.assertRaises(ValueError):AutonomousEngine.restore(seal(e.SCHEMA,data))

    def test_raw_audit_and_tamper_controls(self):
        e=setup6(); drive(e)
        txs=list(e.world.journal()); result=audit(txs)
        self.assertEqual(result["anticipated_actions"],3)
        self.assertEqual(result["appraisals"],3)
        for namespace,change in (("u6.prediction",lambda v:replace(v,roles=(Role.EVENT,),occurrence=Occurrence.ACTUAL_EVENT)),
            ("u6.prediction_error",lambda v:replace(v,attributes=attributes({**attrs(v),"surprise":not attrs(v)["surprise"]}))),
            ("u6.state",lambda v:replace(v,attributes=attributes({**attrs(v),"fatigue":99})))):
            index=next(i for i,t in enumerate(txs) if any(v.ref.identity.namespace==namespace and (namespace!="u6.state" or v.previous) for v in t.versions))
            t=txs[index]
            corrupt=replace(t,versions=tuple(change(v) if v.ref.identity.namespace==namespace else v for v in t.versions))
            broken=txs[:]; broken[index]=corrupt
            with self.assertRaises(ValueError):audit(broken)
