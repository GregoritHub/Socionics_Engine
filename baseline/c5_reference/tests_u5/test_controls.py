import unittest
from tests_u5.fixtures import *
from hle_unified.compact import unseal,seal
from hle_unified.cognitive_audit import audit
from hle_unified.cognitive_records import catalog


class Controls(unittest.TestCase):
    def test_hidden_material_has_identical_view_and_plan(self):
        signatures=[]
        for wear in range(8):
            e=setup5(hidden_wear=wear)
            before=e.participant_view(ALICE).bytes()
            r=request5(e)
            derived=derive(e.participant_view(ALICE),r)
            p=think(e,r)
            signatures.append((before,derived["content"],e.world.resolve(p).facet(Account)))
        self.assertTrue(all(x==signatures[0] for x in signatures))

    def test_other_actor_cannot_enact_or_read_private_account(self):
        e=setup5()
        p=think(e,request5(e))
        with self.assertRaises(ValueError):e.enact("steal",BOB,"steal",p)
        with self.assertRaises(ValueError):show(e,BOB,p)

    def test_undelivered_and_partially_read_event_cannot_revise(self):
        e=setup5()
        p=think(e,request5(e))
        before=e.participant_view(ALICE).bytes()
        event=enact(e,p)
        self.assertEqual(e.participant_view(ALICE).bytes(),before)
        obs=e.deliver_event("later",event,ALICE)
        e.start("read-start",OperationRequest("read-later",ALICE,"read",ROOM,delivery="later"))
        e.advance("read-half",ALICE,"read-later",1)
        self.assertFalse(e.participant_view(ALICE).resolve(obs))
        with self.assertRaises(ValueError):request5(e,"bad","integrate",source=obs)

    def test_wrong_target_and_receiver_offers_do_not_authorize_repair(self):
        for options in ({"offer_target":SAW2},{"offer_receiver":BOB}):
            e=setup5(**options)
            p=think(e,request5(e))
            self.assertEqual(plan_request(e.participant_view(ALICE),p,"check").kind,"inspect")

    def test_same_revision_false_belief_corrects_from_observation(self):
        e=setup5(prior="serviceable")
        event=perform(e,OperationRequest("inspect",ALICE,"inspect",ROOM,target=SAW,evidence=evidence(e,ALICE,SAW)))
        obs=receive(e,event,ALICE,"inspect")
        retained=think(e,request5(e,"correction","integrate",source=obs))
        self.assertEqual(e.world.resolve(retained).facet(Account).content[0].object,"damaged")
        field=e.world.resolve(e.job_status(ALICE,"correction")["field"])
        self.assertEqual(attrs(field)["tension"],"same_revision_disagreement")

    def test_conflicting_memories_keep_uncertainty(self):
        e=setup5()
        seed(e,"contradiction","serviceable")
        p=think(e,request5(e))
        self.assertEqual(plan_request(e.participant_view(ALICE),p,"check").kind,"inspect")
        field=attrs(e.world.resolve(e.job_status(ALICE,"plan")["field"]))
        self.assertEqual(field["status"],"conflict")

    def test_expired_and_wrong_property_memories_not_used(self):
        e=setup5()
        seed(e,"wrong-property","serviceable",relation="owner")
        seed(e,"expired","serviceable",scope=TimeScope(Moment(0,0),Moment(1,0)))
        p=think(e,request5(e))
        self.assertEqual(plan_request(e.participant_view(ALICE),p,"check").kind,"repair")

    def test_truncated_recall_has_no_confident_claim(self):
        e=setup5()
        seed(e,"more","serviceable")
        p=think(e,request5(e,visit_limit=1))
        self.assertEqual(plan_request(e.participant_view(ALICE),p,"check").kind,"inspect")
        self.assertEqual(attrs(e.world.resolve(e.job_status(ALICE,"plan")["field"]))["status"],"truncated")
        event=enact(e,p,"fallback-inspection")
        self.assertEqual(attrs(e.world.resolve(event))["primitive"],"inspect")

    def test_wrong_context_offer_is_ignored(self):
        e=setup5()
        other=ref("wrong-context")
        e.declare("other-room",(ObjectVersion(other,WRITER,"Elsewhere",(Role.CONTEXT,)),))
        offer=e.world.resolve(OFFER)
        amended=next_version(offer,attributes=attributes({**attrs(offer),"context":other}))
        e.declare("different-context",(amended,))
        show(e,ALICE,amended.ref,selectors=tuple(Selector(a.name,"detail",("attributes",str(i),"value")) for i,a in enumerate(amended.attributes)))
        p=think(e,request5(e,source=amended.ref))
        self.assertEqual(plan_request(e.participant_view(ALICE),p,"check").kind,"inspect")

    def test_older_observation_does_not_erase_newer_retention(self):
        e=setup5()
        old_event=perform(e,OperationRequest("old-inspect",ALICE,"inspect",ROOM,target=SAW,evidence=evidence(e,ALICE,SAW)))
        old_obs=receive(e,old_event,ALICE,"old")
        p=think(e,request5(e))
        event=enact(e,p)
        new_obs=receive(e,event,ALICE,"new")
        think(e,request5(e,"new-retain","integrate",source=new_obs))
        retained=think(e,request5(e,"old-retain","integrate",source=old_obs))
        claim=e.world.resolve(retained).facet(Account).content[0]
        self.assertEqual((claim.subject.revision,claim.object),(2,"serviceable"))

    def test_failed_physical_effect_is_not_evidence_of_repair(self):
        e=setup5()
        bad=OperationRequest("bad-use",ALICE,"use",ROOM,target=SAW,evidence=evidence(e,ALICE,SAW))
        event=perform(e,bad)
        self.assertEqual(attrs(e.world.resolve(event))["outcome"],"failed")
        obs=receive(e,event,ALICE,"failed")
        retained=think(e,request5(e,"failed-retain","integrate",source=obs))
        self.assertEqual(e.world.resolve(retained).facet(Account).content[0].object,"damaged")

    def test_same_revision_conflicting_observations_remain_unresolved(self):
        e=setup5()
        event=perform(e,OperationRequest("inspect",ALICE,"inspect",ROOM,target=SAW,evidence=evidence(e,ALICE,SAW)))
        obs=receive(e,event,ALICE,"actual")
        # Declared noisy-observation control; it is not a generated world event.
        original=e.world.resolve(obs)
        noisy=replace(original,ref=ref("noisy-observation"),attributes=attributes({**attrs(original),"condition":"serviceable"}))
        e.declare("noise",(noisy,))
        show(e,ALICE,noisy.ref,selectors=tuple(Selector(a.name,"detail",("attributes",str(i),"value")) for i,a in enumerate(noisy.attributes)))
        r=request5(e,"conflicting","integrate",source=obs)
        r=replace(r,evidence=r.evidence+tuple(p.address for p in e.participant_view(ALICE).resolve(noisy.ref)))
        retained=think(e,r)
        self.assertEqual(e.world.resolve(retained).facet(Account).content,())

    def test_new_actor_binding_invalidates_pending_cognition_without_refund(self):
        e=setup5()
        e.start("start",request5(e))
        e.advance("work",ALICE,"plan",1000)
        spent=e.job_status(ALICE,"plan")["spent"]
        seed(e,"new-binding","serviceable")
        e.commit("commit",ALICE,"plan")
        d=e.job_status(ALICE,"plan")
        self.assertEqual(d["failure"],"changed_actor_recall")
        self.assertEqual(d["spent"],spent)

    def test_source_definitions_cannot_be_silently_changed(self):
        e=setup5()
        before=e.checkpoint()
        with self.assertRaises(ValueError):
            e.declare("rewrite-source",(next_version(e.world.resolve(CUE5),label="invented"),))
        self.assertEqual(e.checkpoint(),before)

    def test_zero_and_time_limited_cognition_retains_no_result(self):
        initial=setup5()
        setup_cost=500-initial.wallet(ALICE)["energy"]
        for budget,clock,expected in ((setup_cost,500,0),(500,setup_cost+1,1)):
            e=setup5(budget=budget,time_budget=clock)
            e.start("start",request5(e))
            e.advance("work",ALICE,"plan",1000)
            self.assertEqual(e.job_status(ALICE,"plan")["spent"],expected)
            with self.assertRaises(ValueError):e.commit("too-early",ALICE,"plan")
            self.assertFalse(any(b.ref.identity.namespace=="u5.plan" for b in e.participant_view(ALICE).snapshot.bindings))

    def test_concurrent_cognitive_work_rejected_before_charge(self):
        e=setup5()
        e.start("start",request5(e))
        cp=e.checkpoint()
        with self.assertRaises(ValueError):e.start("overlap",request5(e,"second"))
        self.assertEqual(e.checkpoint(),cp)

    def test_rule_revision_invalidates_pending_result(self):
        e=setup5()
        e.start("start",request5(e))
        e.advance("work",ALICE,"plan",1000)
        e.declare("rule-change",(next_version(e.world.resolve(RULE),label="Changed rule"),))
        e.commit("commit",ALICE,"plan")
        self.assertEqual(e.job_status(ALICE,"plan")["failure"],"stale_dependency")

    def test_prior_plan_cannot_override_new_retained_account(self):
        e=setup5()
        p=think(e,request5(e))
        event=enact(e,p)
        obs=receive(e,event,ALICE,"consequence")
        think(e,request5(e,"retain","integrate",source=obs))
        with self.assertRaises(ValueError):e.enact("old",ALICE,"old",p)

    def test_revision_correction_does_not_undo_material_history(self):
        e,refs=circuit()
        cp=e.world.resolve(ObjectRef(SAW.identity,2))
        self.assertEqual(cp.facet(Material).condition,"serviceable")
        self.assertEqual(e.world.resolve(SAW).facet(Material).condition,"damaged")
        self.assertEqual(attrs(e.world.head(STOCK.identity))["consumed"],1)

    def test_rehashed_checkpoint_cannot_forge_retained_state(self):
        e,refs=circuit()
        data=unseal(e.checkpoint(),e.SCHEMA)
        data["access"]=setup5().access.checkpoint()
        with self.assertRaises(ValueError):CognitiveEngine.restore(seal(e.SCHEMA,data))

    def test_independent_audit_checks_routes_accounting_and_lineage(self):
        e,_=circuit()
        result=audit(e.world.journal())
        self.assertTrue(result["passed"])
        self.assertEqual(result["conceptual_commits"],3)
        self.assertEqual(result["concept_linked_actions"],2)

    def test_audit_rejects_forged_route_and_conclusion(self):
        e,_=circuit()
        txs=list(e.world.journal())
        i=next(i for i,t in enumerate(txs) if any(attrs(v).get("u5") for v in t.versions))
        t=txs[i];v=t.versions[0]
        forged=replace(v,attributes=attributes({**attrs(v),"route.0.dimensionality":99}))
        broken=txs[:];broken[i]=replace(t,versions=(forged,)+t.versions[1:])
        with self.assertRaises(ValueError):audit(tuple(broken))
        i=next(i for i,t in enumerate(txs) if any(v.ref.identity.namespace=="u5.account" for v in t.versions))
        t=txs[i]
        def corrupt(v):
            if v.ref.identity.namespace!="u5.account":return v
            a=v.facet(Account)
            return replace(v,facets=(replace(a,content=(replace(a.content[0],object="invented"),)),))
        broken=txs[:];broken[i]=replace(t,versions=tuple(corrupt(v) for v in t.versions))
        with self.assertRaises(ValueError):audit(tuple(broken))
