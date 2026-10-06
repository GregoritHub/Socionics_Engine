import unittest
from dataclasses import replace
from tests_u9.fixtures import *
from hle_unified import composition_language as language
from hle_unified.composition_audit import audit


class ControlTests(unittest.TestCase):
    def test_partial_paid_search_has_no_candidate_and_replays(self):
        e=setup9();d=notice9(e)
        r=CompositionRequest("partial",ALICE,"search",ROOM,CUE5,focus=d["ref"])
        e.start("partial-start",r);e.advance("partial-work",ALICE,r.key,1)
        self.assertFalse(any(x["kind"]=="candidate" for x in e.composition_view(ALICE)))
        checkpoint=e.checkpoint();restored=CompositionEngine.restore(checkpoint)
        with self.assertRaises(ValueError):e.commit("too-soon",ALICE,r.key)
        for obj in (e,restored):
            obj.advance("remaining",ALICE,r.key,1000000);obj.commit("finish",ALICE,r.key)
        self.assertEqual(e.checkpoint(),restored.checkpoint())
        self.assertEqual(restored.wallet(ALICE),e.wallet(ALICE))

    def test_insufficient_energy_retains_partial_work(self):
        e=setup9(budget=400);d=notice9(e)
        r=CompositionRequest("scarce",ALICE,"search",ROOM,CUE5,focus=d["ref"])
        e.start("scarce-start",r);e.advance("scarce-work",ALICE,r.key,1000000)
        self.assertEqual(e.wallet(ALICE)["energy"],0)
        self.assertEqual(e.job_status(ALICE,r.key)["status"],"partial")
        self.assertFalse(any(x["kind"]=="search" for x in e.composition_view(ALICE)))
        self.assertEqual(CompositionEngine.restore(e.checkpoint()).checkpoint(),e.checkpoint())

    def test_cancellation_cannot_grant_capacity_or_refund(self):
        e=setup9();d=notice9(e);before=e.wallet(ALICE)["energy"]
        r=CompositionRequest("cancel",ALICE,"search",ROOM,CUE5,focus=d["ref"])
        e.start("cancel-start",r);e.advance("cancel-work",ALICE,r.key,2);e.cancel("cancel-end",ALICE,r.key)
        self.assertEqual(before-e.wallet(ALICE)["energy"],2)
        self.assertFalse(any(x["kind"] in ("candidate","capacity") for x in e.composition_view(ALICE)))

    def test_ticket_exhaustion_preserves_frontier(self):
        e=setup9();d=notice9(e)
        s=do9(e,"one","search",focus=d["ref"],limit=1)[0]
        self.assertEqual(s["status"],"ticket_exhausted");self.assertTrue(s["queue"])
        c=find9(e,s,prefix="continue")
        self.assertEqual(c["kind"],"candidate")

    def test_exhaustion_is_scoped_to_enumerated_repertoire(self):
        e=setup9();d=notice9(e,goal=(("eq",("field","target","condition"),"impossible"),))
        s=find9(e,d,depth=1)
        self.assertEqual(s["status"],"repertoire_exhausted_at_depth")
        self.assertEqual(s["depth"],1)
        self.assertNotIn("no_solution",s)

    def test_source_names_do_not_supply_composition(self):
        outputs=[]
        for tag in ("","opaque-71-"):
            e=setup9(tag=tag);d=notice9(e,tag=tag);c=find9(e,d)
            outputs.append((c["program"],e.wallet(ALICE)["energy"]))
        self.assertEqual(*outputs)

    def test_unobserved_counterexample_cannot_change_training(self):
        outputs=[]
        for value in (1,9):
            e=setup9(hidden_max=value);d=notice9(e);c=find9(e,d)
            outputs.append((c["program"],e.wallet(ALICE)["energy"],e.participant_view(ALICE).bytes()))
        self.assertEqual(*outputs)

    def test_search_and_prediction_have_no_material_effect(self):
        e=setup9();d=notice9(e);before=tuple(e.world.head(x.identity) for _,x in slots9())
        find9(e,d)
        self.assertEqual(before,tuple(e.world.head(x.identity) for _,x in slots9()))

    def test_unacquired_visible_definition_cannot_supply_skill(self):
        e=setup9(train=False)
        show(e,ALICE,ref("primitive-repair"),selectors=(Selector("procedure","definition",("facets","0")),))
        d=notice9(e)
        r=CompositionRequest("untrained",ALICE,"search",ROOM,CUE5,focus=d["ref"])
        perform(e,r,limit=100000)
        self.assertEqual(e.job_status(ALICE,r.key)["status"],"failed")
        self.assertFalse(any(x["kind"]=="candidate" for x in e.composition_view(ALICE)))

    def test_missing_or_unprocessed_fields_do_not_enable_search(self):
        e=setup9()
        for _,obj in slots9():show(e,ALICE,obj)
        r=CompositionRequest("unread",ALICE,"notice",ROOM,CUE5,slots=slots9(),goal=GOAL)
        with self.assertRaises(ValueError):e.start("unread-start",r)

    def test_another_actor_does_not_inherit_private_capacity(self):
        e,c=trained9()
        self.assertEqual(e.composition_view(BOB),())
        with self.assertRaises(ValueError):e._owned(BOB,c["ref"])
        with self.assertRaises(ValueError):show(e,BOB,c["ref"])
        self.assertFalse(e.participant_view(BOB).snapshot.acquired)

    def test_unrelated_received_definition_preserves_pending_search(self):
        e=setup9();d=notice9(e)
        r=CompositionRequest("change",ALICE,"search",ROOM,CUE5,focus=d["ref"])
        e.start("change-start",r);e.advance("change-pay",ALICE,r.key,1000000)
        # Delivery is not processing. Cancellation frees the actor for another
        # processing action; pending ready work can coexist with a U4 read.
        p=ref("primitive-return")
        show(e,ALICE,p,selectors=(Selector("procedure","definition",("facets","0")),))
        # An unrelated definition has no effect: the prepared sources stay exact.
        e.commit("change-end",ALICE,r.key)
        self.assertEqual(e.job_status(ALICE,r.key)["status"],"succeeded")

    def test_changed_processed_material_invalidates_pending_search(self):
        e=setup9();d=notice9(e)
        r=CompositionRequest("change-material",ALICE,"search",ROOM,CUE5,focus=d["ref"])
        e.start("change-material-start",r);e.advance("change-material-pay",ALICE,r.key,1000000)
        roles=dict(slots9())
        perform(e,OperationRequest("external-work",ALICE,"repair",ROOM,
            evidence=evidence(e,ALICE,roles["target"]),target=roles["target"],tool=roles["tool"],stock=roles["repair_stock"]))
        reveal9(e)
        e.commit("change-material-end",ALICE,r.key)
        self.assertEqual(e.job_status(ALICE,r.key)["status"],"failed")
        self.assertEqual(e.job_status(ALICE,r.key)["spent"],e.job_status(ALICE,r.key)["required"])

    def test_detached_views_cannot_edit_retained_programs(self):
        e,c=trained9();old=e.participant_view(ALICE).bytes()
        exposed=e.composition_view(ALICE)
        for d in exposed:d["status"]="forged"
        self.assertEqual(e._construct[c["ref"]]["status"],"retained")
        self.assertEqual(old,e.participant_view(ALICE).bytes())

    def test_unobserved_execution_cannot_retain_mastery(self):
        e=setup9();d=notice9(e);c=find9(e,d)
        r=do9(e,"begin","instantiate",focus=d["ref"],item=c["ref"])[0]
        plan,r=do9(e,"pick","select",focus=r["ref"])
        e.enact("act",ALICE,"physical",plan["ref"]);e.advance("work",ALICE,"physical",1000);event=e.commit("end",ALICE,"physical")
        obs=e.deliver_event("not-read",event,ALICE)
        with self.assertRaises(ValueError):e.start("observe-unread",CompositionRequest("observe",ALICE,"observe",ROOM,CUE5,focus=r["ref"],observation=obs))
        perform(e,CompositionRequest("retain-unfinished",ALICE,"retain",ROOM,CUE5,focus=r["ref"]),limit=10000)
        self.assertEqual(e.job_status(ALICE,"retain-unfinished")["status"],"failed")

    def test_same_selected_step_cannot_execute_twice(self):
        e=setup9();d=notice9(e);c=find9(e,d);r=do9(e,"begin","instantiate",focus=d["ref"],item=c["ref"])[0]
        plan,r=do9(e,"pick","select",focus=r["ref"])
        e.enact("act",ALICE,"physical",plan["ref"])
        with self.assertRaises(ValueError):e.enact("again",ALICE,"physical2",plan["ref"])

    def test_stale_definition_blocks_real_execution(self):
        e=setup9();d=notice9(e);c=find9(e,d);r=do9(e,"begin","instantiate",focus=d["ref"],item=c["ref"])[0]
        plan,r=do9(e,"pick","select",focus=r["ref"])
        before=e.world.head(ref("train").identity)
        e.enact("act",ALICE,"physical",plan["ref"])
        prior=e.world.resolve(plan["procedure"])
        e.declare("changed-definition",(next_version(prior,label="changed revision"),))
        e.advance("work",ALICE,"physical",1000);e.commit("end",ALICE,"physical")
        self.assertEqual(e.job_status(ALICE,"physical")["status"],"failed")
        self.assertEqual(before,e.world.head(ref("train").identity))

    def test_importing_finished_procedure_is_rejected(self):
        e,c=trained9()
        with self.assertRaises(ValueError):e.declare("forgery",(e.world.resolve(c["ref"]),))

    def test_call_cycle_and_interpreter_budget_are_explicit(self):
        r=ref("cycle");caps={r:{"program":("call",r),"guard":()}}
        with self.assertRaises(ValueError):language.validate(("call",r),caps)
        e=setup9();slots=reveal9(e);state=snapshot(e.participant_view(ALICE),slots)[0]
        p=("seq",tuple(("act","repair") for _ in range(10)))
        status,_,_,_=language.simulate(p,state,ALICE,{},1)
        self.assertEqual(status,"budget")

    def test_raw_audit_rejects_forged_ticket(self):
        e,c=trained9();txs=list(e.world.journal())
        for i,tx in enumerate(txs):
            for j,v in enumerate(tx.versions):
                if attrs(v).get("u9") and attrs(v).get("status")=="pending":
                    d=attrs(v);d["recall_units"]+=1
                    versions=list(tx.versions);versions[j]=replace(v,attributes=attributes(d))
                    txs[i]=replace(tx,versions=tuple(versions))
                    with self.assertRaises(ValueError):audit(tuple(txs))
                    return
        self.fail("no paid operation found")

    def test_cancelled_execution_does_not_induce_false_generalization(self):
        e,cap=trained9();d=notice9(e,"transfer")
        run=do9(e,"begin-cancel","instantiate",focus=d["ref"],item=cap["ref"])[0]
        plan,run=do9(e,"pick-cancel","select",focus=run["ref"])
        e.enact("act-cancel",ALICE,"cancel-physical",plan["ref"])
        e.advance("part-cancel",ALICE,"cancel-physical",1)
        event=e.cancel("cancel-physical-end",ALICE,"cancel-physical")
        obs=receive(e,event,ALICE,"cancel-outcome")
        rows=do9(e,"observe-cancel","observe",focus=run["ref"],observation=obs)
        self.assertEqual(rows[0]["status"],"interrupted")
        self.assertFalse(any(x.get("reason")=="failed_generalization" for x in rows))
        self.assertTrue(audit(e.world.journal())["passed"])

    def test_adopts_u8_without_changing_retained_history(self):
        from tests_u8.fixtures import trained8,returned8
        prior,p=trained8();e=CompositionEngine.adopt(prior)
        self.assertEqual(e.development_view(ALICE),prior.development_view(ALICE))
        self.assertEqual(e.composition_view(ALICE),())
        returned8(e,p);returned8(prior,p)
        self.assertEqual(e.world.checkpoint(),prior.world.checkpoint())
        self.assertEqual(e.access.checkpoint(),prior.access.checkpoint())

    def test_assessment_cannot_change_participant_continuation(self):
        e,c=trained9();other=CompositionEngine.restore(e.checkpoint())
        assessment=audit(e.world.journal());assessment["evaluator_label"]="arbitrary changed label"
        a=notice9(e,"transfer");b=notice9(other,"transfer")
        ca=find9(e,a,prefix="after-assessment");cb=find9(other,b,prefix="after-assessment")
        self.assertEqual(ca,cb);self.assertEqual(e.checkpoint(),other.checkpoint())

    def test_midprocedure_restore_preserves_residual_stack_and_effects(self):
        e=setup9();d=notice9(e);c=find9(e,d)
        run=do9(e,"checkpoint-begin","instantiate",focus=d["ref"],item=c["ref"])[0]
        run=continue9(e,run,prefix="checkpoint-run",steps=1)
        self.assertTrue(run["remaining"]);self.assertEqual(run["index"],1)
        other=CompositionEngine.restore(e.checkpoint())
        continue9(e,run,prefix="checkpoint-run");continue9(other,run,prefix="checkpoint-run")
        self.assertEqual(e.checkpoint(),other.checkpoint())

    def test_inner_conditional_rechecks_the_later_state(self):
        e=setup9();slots=reveal9(e,"ready-fragile");state=snapshot(e.participant_view(ALICE),slots)[0]
        program=("seq",(("act","use"),("if",("eq",("field","target","condition"),"damaged"),("act","repair"),("act","care"))))
        first,left,_=language.take_step((program,),state,{},32)
        self.assertEqual(first,"use")
        after=language.action(state,first,ALICE)
        next_action,_,_=language.take_step(left,after,{},32)
        self.assertEqual(next_action,"repair")

    def test_interpreter_budget_preserves_prior_enumeration_accounting(self):
        # A deliberately supplied interpreter fixture; no acquisition claim.
        e=setup9();slots=reveal9(e,"ready-fragile");state=snapshot(e.participant_view(ALICE),slots)[0]
        cap=ref("bounded-call-fixture")
        capacities={cap:{"program":("seq",(("act","repair"),)),"guard":(("eq",("field","target","condition"),"damaged"),)}}
        s={"goal":GOAL,"queue":((state,(),0),),"deferred":(),"visited":(language.signature(state),),"depth":4,"considered":0,"repertoire":(cap,)}
        stopped,_,attempts=language.search_ticket(s,(("use",ref("primitive-use")),),capacities,ALICE,20,4,1)
        self.assertEqual(stopped["status"],"evaluation_budget")
        self.assertGreater(attempts,0);self.assertEqual(stopped["considered"],attempts)
        resumed,program,later=language.search_ticket(stopped,(("use",ref("primitive-use")),),capacities,ALICE,20,4,16)
        self.assertEqual(resumed["considered"],attempts+later)
        self.assertIsNotNone(program)


if __name__=="__main__":unittest.main()
