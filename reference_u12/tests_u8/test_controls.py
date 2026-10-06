import unittest
from dataclasses import replace
from tests_u8.fixtures import *
from hle_unified.development_values import pack, attrs as values8
from hle_unified.development_assessment import assess, evaluate_return_sequences
from hle_unified.records import Assessment, EvidenceStatus
from hle_unified.operations import NativeAccess


class ControlTests(unittest.TestCase):
    def local(self):
        e=setup8();p=generated(e);release8(e,"local",p)
        return e,p

    def test_partial_operation_restores_then_commits_same_correction(self):
        e=setup8();p=generated(e);supply8(e,"facts")
        r=request8(e,"partial","release",p)
        e.start("start",r);e.advance("one",ALICE,r.key,1)
        self.assertFalse(e._corrections)
        restored=DevelopmentEngine.restore(e.checkpoint())
        for x in (e,restored):x.advance("finish",ALICE,r.key,1000);x.commit("commit",ALICE,r.key)
        self.assertEqual(e.checkpoint(),restored.checkpoint())
        self.assertTrue(audit(e.world.journal())["passed"])

    def test_cancel_preserves_charges_and_does_not_release(self):
        e=setup8();p=generated(e);supply8(e,"facts")
        r=request8(e,"cancel","release",p);before=e.wallet(ALICE)["energy"]
        e.start("start",r);e.advance("part",ALICE,r.key,1);e.cancel("cancel",ALICE,r.key)
        self.assertEqual(e.wallet(ALICE)["energy"],before-1)
        self.assertFalse(e._corrections)
        self.assertTrue(audit(e.world.journal())["passed"])

    def test_scarcity_cannot_publish_capacity(self):
        e=setup8(budget=130);p=generated(e);supply8(e,"facts")
        r=request8(e,"scarce","release",p)
        e.start("start",r);e.advance("work",ALICE,r.key,10000)
        self.assertEqual(e.job_status(ALICE,r.key)["status"],"partial")
        with self.assertRaises(ValueError):e.commit("commit",ALICE,r.key)
        self.assertFalse(e._corrections)
        self.assertTrue(audit(e.world.journal())["passed"])

    def test_unread_opportunity_does_not_correct(self):
        e=setup8();p=generated(e)
        s=supply8(e,"unread",target=GROUP,read=False)
        with self.assertRaises(ValueError):request8(e,"no-evidence","release",p,(GROUP,))
        self.assertFalse(e._corrections)

    def test_partial_fields_cannot_hide_actual_requirement(self):
        e=setup8();p=generated(e)
        s=supply8(e,"partial",target=GROUP,deliver=False,approval_required=True)
        v=e.world.resolve(s)
        selectors=tuple(Selector(a.name,"detail",("attributes",str(i),"value")) for i,a in enumerate(v.attributes) if a.name!="approval_required")
        show(e,ALICE,s,selectors=selectors,subject=GROUP)
        with self.assertRaises(ValueError):develop(e,request8(e,"release","release",p,(GROUP,)))

    def test_received_counterchange_invalidates_pending_work_with_spend_retained(self):
        e=setup8();p=generated(e);supply8(e,"initial")
        r=request8(e,"pending","release",p);e.start("start",r);e.advance("paid",ALICE,r.key,1000)
        # Native reads can process a newly delivered fact while realization awaits commit.
        supply8(e,"changed",safe=False)
        event=e.commit("commit",ALICE,r.key)
        self.assertEqual(e.job_status(ALICE,r.key)["status"],"failed")
        self.assertGreater(e.job_status(ALICE,r.key)["spent"],0)
        self.assertFalse(e._corrections)
        self.assertTrue(audit(e.world.journal())["passed"])

    def test_hidden_changes_do_not_alter_participant_input_or_choice(self):
        e,p=self.local();supply8(e,"current",target=GROUP)
        restored=DevelopmentEngine.restore(e.checkpoint())
        before=restored.participant_view(ALICE).bytes()
        supply8(restored,"hidden",target=GROUP,deliver=False,safe=False)
        self.assertEqual(before,restored.participant_view(ALICE).bytes())
        a=respond8(e,"test",p,(GROUP,),prepare=False)
        b=respond8(restored,"test",p,(GROUP,),prepare=False)
        self.assertEqual(e._response_results[a]["row.0.route"],restored._response_results[b]["row.0.route"])

    def test_truncated_recall_is_not_clearance_or_mastery(self):
        e,p=trained8();supply8(e,"later",target=MEMORY)
        r=request8(e,"truncated","respond",p,(MEMORY,),visit_limit=1)
        event=develop(e,r)
        self.assertEqual(e._response_results[event]["row.0.route"],"inspect")
        self.assertFalse(practice8(e,"not-mastered",p,event)["independent"])
        assessment=assess(e.world.journal())
        self.assertNotEqual(assessment["findings"][0]["finite_return_status"],"established")
        self.assertEqual(assessment["responses"][-1]["classification"],"incomplete_retained_access")

    def test_unknown_partner_cannot_be_changed_by_request_only(self):
        e,p=trained8();supply8(e,"facts",target=MEMORY,partner=ObjectRef(BOB,1))
        event=respond8(e,"switch",p,(MEMORY,),partner=ObjectRef(EVE,1),prepare=False)
        self.assertFalse(e._response_results[event]["completed_demand"])
        self.assertEqual(e._response_results[event]["row.0.reason"],"unverified_partner")

    def test_foreign_owner_cannot_use_alice_development(self):
        e,p=self.local()
        r=request8(e,"foreign","release",p)
        with self.assertRaises(ValueError):e.start("foreign",replace(r,actor=BOB))
        self.assertFalse(e.development_view(BOB)["capacities"])
        self.assertFalse(e.development_view(BOB)["corrections"])

    def test_foreign_observation_cannot_be_practiced(self):
        e,p=self.local();event=respond8(e,"task",p)
        with self.assertRaises(ValueError):e.deliver_event("foreign",event,BOB)

    def test_undelivered_actual_outcome_does_not_grant_practice(self):
        e,p=self.local();event=respond8(e,"task",p)
        fake=ref("fake-observation")
        draft=ObjectVersion(fake,WRITER,"Unverified claimed outcome",(Role.OBSERVATION,),
            (Account(SAW,(),Moment(0,0),ALICE,(event,)),),occurrence=Occurrence.OBSERVATION,
            attributes=attributes({"event":event,"outcome":"succeeded"}))
        e.declare("fake",(draft,));show(e,ALICE,fake,selectors=tuple(Selector(a.name,"detail",("attributes",str(i),"value")) for i,a in enumerate(draft.attributes)))
        addresses=tuple(x.address for x in e.participant_view(ALICE).resolve(fake))
        r=request8(e,"fake-practice","practice",p,observation=fake,evidence_=addresses)
        with self.assertRaises(ValueError):e.start("fake-practice",r)

    def test_duplicate_reorganization_requires_new_experience(self):
        e,p=trained8()
        with self.assertRaises(ValueError):reorganize8(e,"same",p)

    def test_unrelated_affordance_does_not_supply_training(self):
        e,p=self.local();event=respond8(e,"other",p,(GROUP,),trigger=OTHER_TRIGGER)
        self.assertEqual(e._response_results[event]["row.0.route"],"engage")
        self.assertFalse(practice8(e,"other-practice",p,event)["independent"])

    def test_other_effects_are_explicitly_unassessed(self):
        e=setup8(generate=False);ref_=inject(e,Effect("forecast"));p=e.pattern_view(ALICE)[0]
        supply8(e,"facts")
        with self.assertRaises(ValueError):develop(e,request8(e,"release","release",p))
        self.assertFalse(e._capacities)

    def test_local_scope_is_exact_target_revision(self):
        e,p=self.local()
        newer=next_version(e.world.resolve(GROUP),label="Revised group")
        e.declare("group-revision",(newer,));show(e,ALICE,newer.ref)
        release8(e,"old-group",p,GROUP)
        event=respond8(e,"new-group",p,(newer.ref,))
        self.assertFalse(e._response_results[event]["completed_demand"])

    def test_account_and_access_replay_remain_exact(self):
        e,p=trained8();view=e.participant_view(ALICE);cutoff=len(view.snapshot.history)
        respond8(e,"later",p,(MEMORY,))
        self.assertEqual(view.bytes(),e.participant_view(ALICE,through=cutoff).bytes())
        self.assertEqual(NativeAccess.restore(e.access.checkpoint()).checkpoint(),e.access.checkpoint())

    def test_development_view_is_detached(self):
        e,p=trained8();v=e.development_view(ALICE);v["capacities"][0]["max_load"]=10000
        self.assertEqual(e._capacities[p.ref]["max_load"],2)

    def test_assessor_output_cannot_change_actor(self):
        e,p=self.local();before=e.checkpoint();assess(e.world.journal())
        self.assertEqual(before,e.checkpoint())
        label=ObjectVersion(ref("assessment"),WRITER,"Offline assessment",(Role.ASSESSMENT,),
            (Assessment(SAW,"development",EvidenceStatus.ESTABLISHED,(SAW,),"fixture"),))
        e.declare("assessment",(label,))
        with self.assertRaises(ValueError):show(e,ALICE,label.ref)

    def test_tampered_capacity_rejected_by_raw_audit(self):
        e,p=trained8();rows=[]
        for tx in e.world.journal():
            changed=[]
            for v in tx.versions:
                if v.ref.identity.namespace=="u8.capacity":
                    d=values8(v);d["max_load"]=10;v=replace(v,attributes=attributes(pack(d)))
                changed.append(v)
            rows.append(replace(tx,versions=tuple(changed)))
        with self.assertRaises(ValueError):audit(tuple(rows))

    def test_tampered_charge_rejected_by_raw_audit(self):
        e,p=self.local();rows=[]
        for tx in e.world.journal():
            changed=[]
            for v in tx.versions:
                d=attrs(v)
                if d.get("u8") and d["spent"]>0:
                    d["spent"]-=1;v=replace(v,attributes=attributes(d))
                changed.append(v)
            rows.append(replace(tx,versions=tuple(changed)))
        with self.assertRaises(ValueError):audit(tuple(rows))

    def test_one_endpoint_does_not_prove_composite_return(self):
        result=evaluate_return_sequences(0,lambda x,op:{0:1,1:2,2:2}[x],lambda x:x<2,(("return",),("return","return")))
        self.assertEqual([r["status"] for r in result["rows"]],["established","failed"])
        self.assertEqual(result["universal_composition"],"unassessed")


if __name__=="__main__":unittest.main()
