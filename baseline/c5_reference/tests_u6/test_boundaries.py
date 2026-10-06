import unittest
from dataclasses import replace
from tests_u6.fixtures import *
from hle_unified.anticipation import choose, state_of
from hle_unified.autonomy_audit import audit


class Boundaries(unittest.TestCase):
    def test_paid_unresolved_correction_does_not_resurrect_old_certainty(self):
        e=setup5(prior="serviceable")
        event=perform(e,OperationRequest("inspect",ALICE,"inspect",ROOM,target=SAW,evidence=evidence(e,ALICE,SAW)))
        obs=receive(e,event,ALICE,"real")
        noisy=replace(e.world.resolve(obs),ref=ref("conflicting-observation"),attributes=attributes({**attrs(e.world.resolve(obs)),"condition":"serviceable"}))
        e.declare("noise",(noisy,))
        show(e,ALICE,noisy.ref,selectors=tuple(Selector(a.name,"detail",("attributes",str(i),"value")) for i,a in enumerate(noisy.attributes)))
        r=request5(e,"unresolved","integrate",source=obs)
        r=replace(r,evidence=r.evidence+tuple(p.address for p in e.participant_view(ALICE).resolve(noisy.ref)))
        account=think(e,r)
        self.assertEqual(e.world.resolve(account).facet(Account).content,())
        later=think(e,request5(e,"later"))
        self.assertEqual(plan_request(e.participant_view(ALICE),later,"action").kind,"inspect")
        self.assertTrue(audit(e.world.journal())["passed"])

    def test_conflicting_target_receiver_context_or_operation_cannot_match_result(self):
        e=setup6(); drive(e,delivery=False)
        event=e.state(ALICE).await_event
        actual=e.world.resolve(event)
        for index,changed in enumerate(({"target":SAW2},{"actor":BOB},{"context":CUE},{"operation":SAW})):
            projected={k:v for k,v in attrs(actual).items() if not k.startswith("participant.")}
            projected.update(changed)
            value=ObjectVersion(ref("noisy-result-"+str(index)),WRITER,"Declared mismatched observation",(Role.OBSERVATION,),
                (Account(SAW,(),Moment(0,0),ALICE,(event,)),),occurrence=Occurrence.OBSERVATION,attributes=attributes(projected))
            e.declare("noise-"+str(index),(value,))
            show(e,ALICE,value.ref,selectors=tuple(Selector(a.name,"detail",("attributes",str(i),"value")) for i,a in enumerate(value.attributes)))
            self.assertIsNone(e._matching(e.participant_view(ALICE),e.state(ALICE)))
        self.assertFalse(errors(e))

    def test_resource_wait_requires_notice_then_attempts_again(self):
        e=setup6()
        r=repair(e,"competitor",target=SAW2)
        e.start("competitor-start",r)
        drive(e,delivery=False,prefix="blocked")
        self.assertEqual(e.state(ALICE).wait_kind,"resource")
        self.assertEqual(set(e.state(ALICE).wait_resources),{SAW,KIT,STOCK})
        active=e.state(ALICE).active
        self.assertEqual(e.job_status(ALICE,active)["spent"],0)
        e.advance("competitor-paid",ALICE,r.key,100)
        event=e.commit("competitor-commit",ALICE,r.key)
        # Hidden release and dependency invalidation do not wake a participant.
        cp=e.checkpoint()
        self.assertIsNone(e.step("hidden-release",ALICE))
        self.assertEqual(e.checkpoint(),cp)
        e.deliver_event("allowed-release-observation",event,ALICE)
        for i in range(15):
            e.step("release-read-"+str(i),ALICE)
            if e.job_status(ALICE,active)["spent"]:break
        self.assertGreater(e.job_status(ALICE,active)["spent"],0)
        # The old dependency cannot be silently updated to guarantee success.
        if e.job_status(ALICE,active)["status"]=="failed":
            self.assertEqual(e.job_status(ALICE,active)["failure"],"stale_dependency")

    def test_unrelated_delivery_does_not_release_resource_wait(self):
        e=setup6(); e.start("competing",repair(e,"competitor"))
        drive(e,delivery=False,prefix="blocked")
        active=e.state(ALICE).active
        show(e,ALICE,CUE,key="irrelevant")
        e.step("after-irrelevant",ALICE)
        self.assertEqual(e.job_status(ALICE,active)["spent"],0)
        self.assertEqual(e.state(ALICE).wait_kind,"resource")

    def test_scarcity_from_processed_stock_limits_work_without_granting_skill(self):
        e=setup6(work_limit=6)
        before=e.participant_view(ALICE).snapshot.acquired
        # A declared actor observation is a need-input control, not a world sink.
        obs=ObjectVersion(ref("stock-notice"),WRITER,"Declared stock observation",(Role.OBSERVATION,),
            (Account(STOCK,(),Moment(0,0),ALICE),),occurrence=Occurrence.OBSERVATION,
            attributes=attributes({"target":STOCK,"context":ROOM,"available":0}))
        e.declare("stock-notice",(obs,))
        show(e,ALICE,obs.ref,subject=STOCK,selectors=tuple(Selector(a.name,"detail",("attributes",str(i),"value")) for i,a in enumerate(obs.attributes)))
        e.step("begin",ALICE); e.step("work",ALICE)
        self.assertEqual(e.state(ALICE).scarcity,8)
        self.assertLess(e.job_status(ALICE,e.state(ALICE).active)["spent"],6)
        self.assertEqual(e.participant_view(ALICE).snapshot.acquired,before)
        self.assertEqual(attrs(e.world.head(STOCK.identity))["consumed"],0)

    def test_equal_need_and_history_different_tim_does_not_script_action(self):
        actions=[]
        for tim in ("iee","sli","ile"):
            e=setup6(tim=tim,prior="serviceable",serviceable=True,wear=2)
            actions.append(first_choice(e))
        self.assertEqual(actions,["care"]*3)

    def test_unaffordable_candidate_is_explicitly_unselected(self):
        e=setup6(); first_choice(e)
        result=e._forecast_results[e.state(ALICE).forecast]
        row=choose(result,e._configs[ALICE],{"pressure":2,"fear":0,"scarcity":10,"boredom":0},{"energy":1,"time":100})
        self.assertIsNone(row)

    def test_invalid_search_bounds_rejected_before_mutation(self):
        e=setup6(); cp=e.checkpoint()
        for changes in ({"horizon":0},{"horizon":3},{"max_nodes":0},{"max_nodes":17},{"work_limit":0}):
            with self.assertRaises(ValueError):replace(e._configs[ALICE],**changes)
        self.assertEqual(e.checkpoint(),cp)

    def test_clock_change_and_other_actor_work_do_not_change_local_motives(self):
        e=setup6(); drive(e,delivery=False)
        before=e.state(ALICE)
        # Bob's own name-reading advances world history only for Bob.
        show(e,BOB,ROOM,key="bob-room")
        cp=e.checkpoint(); self.assertIsNone(e.step("foreign-clock",ALICE))
        self.assertEqual(e.checkpoint(),cp)
        self.assertEqual(e.state(ALICE),before)

    def test_successful_correction_never_awards_unpracticed_procedure(self):
        e=setup6(prior="serviceable"); drive(e)
        self.assertFalse(e.participant_view(ALICE).can_use(REPAIR,ROOM))
        self.assertFalse(e.participant_view(BOB).can_use(REPAIR,ROOM))
        self.assertGreater(len(e.participant_view(ALICE).snapshot.bindings),1)

    def test_native_and_access_checkpoints_remain_exact(self):
        from hle_unified.operations import NativeAccess
        e=setup6(); first_choice(e)
        self.assertEqual(OperationStore.restore(e.world.checkpoint()).checkpoint(),e.world.checkpoint())
        self.assertEqual(NativeAccess.restore(e.access.checkpoint()).checkpoint(),e.access.checkpoint())
