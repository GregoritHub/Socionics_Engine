import unittest
from dataclasses import replace
from tests_c7_workflow.fixtures import *
from hle_unified.workflow_audit import audit
from hle_unified.workflow_reference import schedule as reference_schedule
from tests_u11.fixtures import work as collective_work

class WorkflowTests(unittest.TestCase):
    def test_all_32_cells_and_matched_defining_step_controls(self):
        for name in PATHS:
            for face in FACES:
                with self.subTest(route=name,face=face):
                    e=setup_workflow();q=setup_workflow(engine_type=Ablated)
                    good=cell(e,name,face);bad=cell(q,name,face)
                    self.assertEqual(e.job_status(ALICE,"case")["status"],"succeeded")
                    self.assertEqual(e.job_status(ALICE,"case")["spent"],q.job_status(ALICE,"case")["spent"])
                    self.assertNotEqual(good["consequence"]["next_task"],bad["consequence"]["next_task"])
                    if name=="Act":self.assertEqual((good["owner_use"],bad["owner_use"]),("succeeded","failed"))
                    self.assertTrue(audit(e.world.journal(),e.access.checkpoint())["passed"])
                    with self.assertRaisesRegex(ValueError,"semantic postcondition"):audit(q.world.journal(),q.access.checkpoint())

    def test_exact_continuation_all_cells_three_paid_boundaries(self):
        for name in PATHS:
            for face in FACES:
                for boundary in range(3):
                    with self.subTest(route=name,face=face,boundary=boundary):
                        e=setup_workflow();r=cell(e,name,face,prepare_only=True)["request"]
                        e.start("begin",r);d=e.job_status(ALICE,"case")
                        first=d["recall_units"]+sum(indexed(d,"route.0.charges."))+d["route.0.content_units"]
                        e.advance("partial",ALICE,"case",(1,first,d["required"])[boundary]);cp=e.checkpoint();q=WorkflowEngine.restore(cp)
                        self.assertEqual(cp,q.checkpoint())
                        for branch in (e,q):
                            if branch.job_status(ALICE,"case")["status"]!="ready":branch.advance("resume",ALICE,"case",100000)
                            branch.commit("finish",ALICE,"case")
                        self.assertEqual(e.checkpoint(),q.checkpoint());audit(q.world.journal(),q.access.checkpoint())

    def test_window_conflict_cycle_missing_dependency_and_order_matter(self):
        cases=[tasks(),(("maintain","care",("handover",),0,2,ALICE),tasks()[1]),
            (tasks()[1],),(("maintain","care",(),3,3,ALICE),("handover","transfer",("maintain",),1,2,ALICE))]
        for rows in cases:
            e=setup_workflow();out=model(e,"m",rows);got=data(e,out)
            self.assertEqual({k:got[k] for k in reference_schedule((dict(tasks=rows),))},reference_schedule((dict(tasks=rows),)))
            self.assertEqual(got["feasible"],rows==tasks());audit(e.world.journal(),e.access.checkpoint())
        e=setup_workflow();a=model(e,"a",tasks());narrow=(tuple((*tasks()[0][:3],3,4,ALICE)),tasks()[1]);b=model(e,"b",narrow)
        z=work(e,request(e,"merge","Integrate","accumulation",(a,b)))
        self.assertIn("maintain",data(e,z)["conflicts"]);self.assertFalse(data(e,z)["feasible"])

    def test_foreign_unread_wrong_context_and_authored_shared_claims_rejected(self):
        e=setup_workflow();r=cell(e,"Theorize","accumulation",prepare_only=True)["request"]
        for invalid in (replace(r,actor=BOB),replace(r,cue=CUE),replace(r,evidence=(DetailAddress("absent","x"),))):
            with self.assertRaises(ValueError):e.start("bad",invalid)
        fake=authored(e,"fake");v=e.world.resolve(fake);p=v.facet(Account).content[0]
        forged=replace(v,ref=ref("forged-shared"),facets=(replace(v.facet(Account),content=(replace(p,object=wf.encode(dict(kind="shared",tasks=tasks(),authorized=True))),)),))
        e.declare("fake-declaration",(forged,));perform(e,OperationRequest("bind-fake",ALICE,"bind",ROOM,binding=forged.ref,evidence=evidence(e,ALICE,DEVICE)))
        with self.assertRaises(ValueError):e.start("fake-use",request(e,"fake-use","Mobilize","accumulation",(forged.ref,)))

    def test_missing_receiver_read_and_foreign_message_disclosure_rejected(self):
        e=setup_workflow();r=cell(e,"Educate","expenditure",prepare_only=True)["request"]
        reply=r.inputs[2];delivery=e.participant_view(ALICE).resolve(reply)[0].address.delivery
        q=WorkflowEngine(OperationStore.restore(e._initial),LAW_REF)
        for command,_ in e._commands.values():
            if command[0]=="start" and type(command[2]) is OperationRequest and command[2].delivery==delivery:break
            q._execute(command)
        with self.assertRaises(ValueError):q.start("unread",r)
        with self.assertRaises(ValueError):expose(e,EVE,reply)
        with self.assertRaises(ValueError):e.start("missing",replace(r,inputs=r.inputs[:2]))

    def test_understanding_dissent_and_practiced_skill_are_distinct(self):
        for name in ("Share","Educate","Commune"):
            e=setup_workflow();out=cell(e,name,"expenditure",consent=False);result=data(e,out["result"])
            self.assertTrue(result["understood"]);self.assertFalse(result["authorized"]);self.assertFalse(result["competence"])
            self.assertEqual(out["consequence"]["next_task"],"handover")
            self.assertFalse(e.participant_view(BOB).can_use(REPAIR,ROOM))
            with self.assertRaises(ValueError):e.start("force",request(e,"force","Mobilize","expenditure",(out["result"],),stock=CARE,peer=BOB,group=out["extra"]["group"]))
            audit(e.world.journal(),e.access.checkpoint())

    def test_draft_and_wrong_or_duplicate_votes_cannot_ratify(self):
        e=setup_workflow();source,g=draft(e,"draft");v=votes(e,source,g,"votes")
        with self.assertRaises(ValueError):e.start("draft-apply",request(e,"draft-apply","Apply","accumulation",(source,),group=g,peer=BOB))
        with self.assertRaises(ValueError):e.start("no-votes",request(e,"no-votes","Institutionalize","expenditure",(source,),group=g,peer=BOB))
        own=authored(e,"another-vote-stance",kind="stance")
        work(e,request(e,"another-vote","vote",None,(source,own),group=g,peer=BOB));dup=e.job_status(ALICE,"another-vote")["public.0"];expose(e,ALICE,dup)
        with self.assertRaises(ValueError):e.start("duplicate",request(e,"duplicate","Institutionalize","expenditure",(source,v[0],dup),group=g,peer=BOB))
        observe(e,"renew-wear",primitive="use")
        other,g2=draft(e,"other-draft")
        with self.assertRaises(ValueError):e.start("wrong",request(e,"wrong","Institutionalize","expenditure",(other,*v),group=g2,peer=BOB))

    def test_changed_membership_invalidates_paid_work(self):
        e=setup_workflow();r=cell(e,"Share","expenditure",prepare_only=True)["request"]
        e.start("begin",r);e.advance("pay",ALICE,"case",100000)
        collective_work(e,"depart","leave",actor=BOB,focus=r.group)
        e.commit("end",ALICE,"case");self.assertEqual(e.job_status(ALICE,"case")["failure"],"stale_dependency")
        audit(e.world.journal(),e.access.checkpoint())

    def test_cancel_exhaustion_and_missing_command_preserve_paid_work(self):
        for name in PATHS:
            for face in FACES:
                e=setup_workflow();r=cell(e,name,face,prepare_only=True)["request"];before=e.wallet(ALICE)["energy"]
                e.start("begin",r);e.advance("pay",ALICE,"case",1);e.cancel("cancel",ALICE,"case")
                self.assertEqual(e.wallet(ALICE)["energy"],before-1);self.assertIsNone(e.job_status(ALICE,"case").get("binding"))
                audit(e.world.journal(),e.access.checkpoint())
        probe=setup_workflow();cell(probe,"Theorize","accumulation",prepare_only=True)
        used=probe.wallet(ALICE)["initial_energy"]-probe.wallet(ALICE)["energy"]
        e=setup_workflow(budget=used+1);r=cell(e,"Theorize","accumulation",prepare_only=True)["request"]
        e.start("begin",r);e.advance("empty",ALICE,"case",100000)
        self.assertEqual(e.job_status(ALICE,"case")["spent"],1)
        with self.assertRaises(ValueError):e.commit("free",ALICE,"case")
        audit(e.world.journal(),e.access.checkpoint())

    def test_receivers_answer_changed_case_without_borrowing_binding(self):
        e=setup_workflow();out=cell(e,"Educate","expenditure");source=e.job_status(ALICE,"case")["public.0"]
        initial=work(e,request(e,"learner-first","use-shared",None,(source,),actor=BOB,peer=ALICE,group=out["extra"]["group"]))
        self.assertEqual(data(e,initial,BOB)["next_task"],"maintain")
        self.assertEqual(out["consequence"]["next_task"],"handover")
        late=work(e,request(e,"learner-late","use-shared",None,(source,),actor=BOB,peer=ALICE,group=out["extra"]["group"],clock=9))
        self.assertIsNone(data(e,late,BOB)["next_task"]);audit(e.world.journal(),e.access.checkpoint())

    def test_material_failure_and_one_attempt_shared_commitment(self):
        e=setup_workflow();r=cell(e,"Mobilize","expenditure",prepare_only=True)["request"]
        e.start("begin",r);e.cancel("cancel",ALICE,"case")
        with self.assertRaises(ValueError):e.start("retry",replace(r,key="retry"))
        e=setup_workflow();r=cell(e,"Express","expenditure",prepare_only=True)["request"]
        # Stale concrete revision causes a paid failed commit, without refund.
        observe(e,"earlier-maintenance",primitive="care")
        work(e,r,allow_failure=True);self.assertEqual(e.job_status(ALICE,"case")["status"],"failed")
        self.assertGreater(e.job_status(ALICE,"case")["spent"],0);audit(e.world.journal(),e.access.checkpoint())

    def test_raw_tampering_with_semantics_price_time_or_public_uptake_fails(self):
        e=setup_workflow();cell(e,"Educate","expenditure")
        for mode in ("content","paid","predecessor","public","audience","time"):
            changed=False;txs=[]
            for tx in e.world.journal():
                vs=[]
                for v in tx.versions:
                    ns="u4.event" if mode=="time" else "c7w.message" if mode in ("public","audience") else "c7w.step"
                    if not changed and v.ref.identity.namespace==ns:
                        d=attrs(v)
                        if mode=="content":
                            ac=v.facet(Account);p=ac.content[0];z=wf.decode(p.object);z["unearned"]=True
                            v=replace(v,facets=(replace(ac,content=(replace(p,object=wf.encode(z)),)),))
                        else:
                            k={"paid":"paid_threshold","predecessor":"predecessor","public":"payload","audience":"audience.0","time":"workflow_tick"}[mode]
                            d[k]={"paid":0,"predecessor":ROOM,"public":wf.encode(dict(kind="fabricated")),"audience":EVE,"time":-1}[mode]
                            v=replace(v,attributes=attributes(d))
                        changed=True
                    vs.append(v)
                txs.append(replace(tx,versions=tuple(vs)))
            with self.subTest(mode=mode),self.assertRaises((ValueError,KeyError)):audit(txs,e.access.checkpoint())

    def test_display_labels_do_not_determine_semantics_and_duplicate_commands_are_idempotent(self):
        e=setup_workflow();out=cell(e,"Integrate","expenditure",consumer=False)
        cp=e.checkpoint();work(e,out["request"]);self.assertEqual(e.checkpoint(),cp)
        txs=[replace(tx,versions=tuple(replace(v,label="unrelated display label") if v.ref.identity.namespace.startswith("c7w.") and v.ref.identity.namespace!="c7w.recipe" else v for v in tx.versions)) for tx in e.world.journal()]
        audit(txs,e.access.checkpoint())

    def test_hypothetical_completion_cannot_skip_actual_physical_work(self):
        e=setup_workflow();r=cell(e,"Apply","expenditure",prepare_only=True)["request"]
        with self.assertRaises(ValueError):replace(r,completed=("maintain",))
        with self.assertRaises(ValueError):replace(r,clock=1)
        e.start("start",r);e.advance("partial",ALICE,"case",1)
        with self.assertRaises(ValueError):e.commit("unpaid",ALICE,"case")

    def test_observed_chronology_not_input_permutation_determines_inference(self):
        e=setup_workflow();r=cell(e,"Organize","accumulation",prepare_only=True)["request"]
        a=work(e,r);b=work(e,replace(r,key="reversed",inputs=tuple(reversed(r.inputs))))
        self.assertEqual(data(e,a)["tasks"],data(e,b)["tasks"]);audit(e.world.journal(),e.access.checkpoint())

    def test_generated_rule_teaching_and_coupled_procedure_material_composition(self):
        e=setup_workflow();out=cell(e,"Institutionalize","expenditure",consumer=False)
        rule=e.job_status(ALICE,"case")["public.0"];expose(e,ALICE,rule)
        offer,reply,g=exchange(e,rule,"teach-rule",domain="system",g=out["extra"]["group"])
        learned=work(e,request(e,"teach","Educate","expenditure",(rule,offer,reply),peer=BOB,group=g))
        self.assertTrue(data(e,learned)["teaching"]);self.assertFalse(data(e,learned)["competence"])
        # Ratified authorization governs a later actual operation after renewed wear.
        observe(e,"renewed-use",primitive="use");current=e.world.head(DEVICE.identity).ref;expose(e,ALICE,current)
        stock_ref=e.world.head(CARE.identity).ref;expose(e,ALICE,stock_ref)
        work(e,request(e,"governed-care","Apply","expenditure",(rule,),target=current,stock=stock_ref,group=g,peer=BOB))
        self.assertEqual(attrs(e.world.head(DEVICE.identity))["wear"],0);audit(e.world.journal(),e.access.checkpoint())
        e=setup_workflow();out=cell(e,"Integrate","expenditure",consumer=False)
        work(e,request(e,"coupled-care","Apply","expenditure",(out["result"],),stock=CARE));audit(e.world.journal(),e.access.checkpoint())

    def test_undelivered_physical_change_cannot_rewrite_theory(self):
        values=[]
        for hidden in (False,True):
            e=setup_workflow();own=authored(e,"owned")
            if hidden:
                perform(e,OperationRequest("unreceived-care",ALICE,"care",ROOM,target=DEVICE,stock=CARE,evidence=evidence(e,ALICE,DEVICE)))
            out=work(e,request(e,"theory","Theorize","accumulation",(own,)))
            values.append(data(e,out));audit(e.world.journal(),e.access.checkpoint())
        self.assertEqual(*values)

    def test_understood_contribution_can_retain_incompatible_receiver_window(self):
        e=setup_workflow();own=authored(e,"own");offer,reply,g=exchange(e,own,"exchange")
        rows=(tuple((*tasks()[0][:3],10,12,ALICE)),tasks()[1])
        other=authored(e,"other-window",rows,actor=BOB,kind="stance")
        work(e,request(e,"different-reply","reply",None,(offer,other),actor=BOB,peer=ALICE,group=g))
        reply=e.job_status(BOB,"different-reply")["public.0"];expose(e,ALICE,reply)
        result=work(e,request(e,"share","Share","expenditure",(own,offer,reply),peer=BOB,group=g));z=data(e,result)
        self.assertTrue(z["understood"]);self.assertTrue(z["difference"]);self.assertFalse(z["authorized"])
        self.assertIn("maintain",z["conflicts"]);audit(e.world.journal(),e.access.checkpoint())

    def test_received_operating_model_does_not_transfer_ownership_authority(self):
        e=setup_workflow();r=cell(e,"Organize","expenditure",prepare_only=True)["request"]
        output=work(e,replace(r,peer=BOB))
        public=e.job_status(ALICE,"case")["public.0"]
        expose(e,BOB,public)
        current=e.world.head(DEVICE.identity).ref;expose(e,BOB,current)
        with self.assertRaises(ValueError):work(e,request(e,"borrowed-authority","Apply","expenditure",(public,),actor=BOB,target=current,stock=CARE))
        self.assertEqual(data(e,output)["authority"],ALICE)
        self.assertFalse(e.participant_view(BOB).can_use(REPAIR,ROOM));audit(e.world.journal(),e.access.checkpoint())

if __name__=="__main__":unittest.main()
