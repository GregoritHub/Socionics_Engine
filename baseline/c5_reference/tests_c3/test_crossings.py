import unittest
from dataclasses import replace
from hle.model_a import TYPES
from tests_c3.fixtures import *
from hle_unified.crossing_audit import audit
from tests_u11.fixtures import work as collective_work

EXPECTED={"Express":(6,3),"Share":(2,2),"Theorize":(3,3),"Embody":(5,5),
    "Coordinate":(2,2),"Organize":(5,5),"Identify":(2,2),"Mobilize":(6,4),
    "Institutionalize":(2,2),"Understand":(3,3),"Apply":(5,3),"Educate":(2,2)}

class CrossingTests(unittest.TestCase):
    def test_twenty_four_contracts_across_sixteen_types(self):
        for tim in TYPES:
            for name in PATHS:
                for i,face in enumerate(FACES):
                    with self.subTest(tim=tim,route=name,face=face):
                        e=setup_c3(tim); out=cell(e,name,face); d=e.job_status(ALICE,"case")
                        self.assertEqual(d["status"],"succeeded")
                        self.assertEqual((d["origin"],d["destination"]),PATHS[name][:2])
                        self.assertEqual(consequence(e,out),EXPECTED[name][i])
                        self.assertGreater(d["spent"],0)
                        self.assertTrue(audit(e.world.journal(),e.access.checkpoint())["passed"])

    def test_matched_semantic_ablations_change_all_later_uses(self):
        for name in PATHS:
            for face in FACES:
                with self.subTest(route=name,face=face):
                    e=setup_c3(); c=setup_c3(engine_type=Ablated)
                    out=cell(e,name,face); other=cell(c,name,face)
                    self.assertEqual(e.job_status(ALICE,"case")["spent"],c.job_status(ALICE,"case")["spent"])
                    self.assertNotEqual(consequence(e,out),consequence(c,other))
                    with self.assertRaises(ValueError): audit(c.world.journal(),c.access.checkpoint())

    def test_exact_continuation_three_boundaries_all_cells(self):
        for name in PATHS:
            for face in FACES:
                for boundary in range(3):
                    with self.subTest(route=name,face=face,boundary=boundary):
                        e=setup_c3(); r=cell(e,name,face,prepare_only=True)["request"]
                        e.start("begin",r); d=e.job_status(ALICE,r.key)
                        first=d["recall_units"]+sum(indexed(d,"route.0.charges."))+d["route.0.content_units"]
                        e.advance("partial",ALICE,r.key,(1,first,d["required"])[boundary])
                        cp=e.checkpoint(); q=CrossingEngine.restore(cp)
                        self.assertEqual(cp,q.checkpoint())
                        for branch in (e,q):
                            if branch.job_status(ALICE,r.key)["status"]!="ready": branch.advance("resume",ALICE,r.key,100000)
                            branch.commit("finish",ALICE,r.key)
                        self.assertEqual(e.checkpoint(),q.checkpoint())
                        audit(e.world.journal(),e.access.checkpoint())

    def test_cancel_all_cells_retains_work_and_private_intermediates(self):
        for name in PATHS:
            for face in FACES:
                e=setup_c3(); r=cell(e,name,face,prepare_only=True)["request"]
                before=e.wallet(ALICE)["energy"]; e.start("begin",r); e.advance("partial",ALICE,r.key,1)
                e.cancel("cancel",ALICE,r.key)
                self.assertEqual(e.wallet(ALICE)["energy"],before-1)
                self.assertIsNone(e.job_status(ALICE,r.key).get("binding"))
                audit(e.world.journal(),e.access.checkpoint())

    def test_exhaustion_cannot_grant_output_or_refund(self):
        probe=setup_c3(); cell(probe,"Express","expenditure",prepare_only=True)
        used=probe.wallet(ALICE)["initial_energy"]-probe.wallet(ALICE)["energy"]
        e=setup_c3(budget=used+1); r=cell(e,"Express","expenditure",prepare_only=True)["request"]
        e.start("begin",r); e.advance("work",ALICE,r.key,10000); e.advance("empty",ALICE,r.key,10000)
        self.assertEqual(e.job_status(ALICE,r.key)["spent"],1)
        with self.assertRaises(ValueError): e.commit("free",ALICE,r.key)
        self.assertEqual(attrs(e.world.resolve(SUPPLY))["consumed"],0)
        audit(e.world.journal(),e.access.checkpoint())

    def test_foreign_inputs_wrong_scope_and_unread_evidence(self):
        e=setup_c3(); r=cell(e,"Theorize","accumulation",prepare_only=True)["request"]
        for invalid in (replace(r,actor=BOB,peer=ALICE),replace(r,cue=CUE),replace(r,evidence=(DetailAddress("missing","x"),))):
            with self.assertRaises(ValueError): e.start("bad",invalid)

    def test_unread_reply_and_sent_offer_do_not_make_shared_meaning(self):
        e=setup_c3(); r=cell(e,"Share","expenditure",prepare_only=True)["request"]
        reply=r.inputs[2]; delivery=e.participant_view(ALICE).resolve(reply)[0].address.delivery
        q=CrossingEngine(OperationStore.restore(e._initial),LAW_REF)
        for command,_ in e._commands.values():
            if command[0]=="start" and type(command[2]) is OperationRequest and command[2].delivery==delivery: break
            q._execute(command)
        with self.assertRaises(ValueError): q.start("unread",r)
        with self.assertRaises(ValueError): e.start("only-transmitted",replace(r,inputs=r.inputs[:2]))

    def test_no_import_or_private_step_disclosure(self):
        e=setup_c3(); cell(e,"Understand","expenditure",consumer=False)
        d=e.job_status(ALICE,"case"); step=e.world.resolve(d["last_step"])
        with self.assertRaises(ValueError): e.declare("fabricate",(step,))
        with self.assertRaises(ValueError): expose(e,BOB,step.ref)
        with self.assertRaises(ValueError): expose(e,EVE,d["binding"])

    def test_dissent_retained_without_performance_permission(self):
        for name in ("Share","Identify","Institutionalize"):
            e=setup_c3(); out=cell(e,name,"expenditure",consent=False)
            decision=data(e,out["downstream"],out["consumer_actor"])
            self.assertFalse(decision["permitted"])
            with self.assertRaises(ValueError): e.enact("denied",out["consumer_actor"],"denied",out["downstream"])
            audit(e.world.journal(),e.access.checkpoint())
        e=setup_c3(); r=cell(e,"Mobilize","expenditure",consent=False,prepare_only=True)["request"]
        with self.assertRaises(ValueError): e.start("without-assent",r)

    def test_draft_cannot_ratify_itself_or_authorize_apply(self):
        e=setup_c3(); proposal,g=draft(e)
        with self.assertRaises(ValueError): e.start("no-votes",req(e,"no-votes","institutionalize-expenditure-v1",(proposal,),group=g,peer=BOB))
        current=e.world.head(SUPPLY.identity).ref; expose(e,ALICE,current)
        with self.assertRaises(ValueError): e.start("draft-apply",req(e,"draft-apply","apply-expenditure-v1",(proposal,),stock=current,group=g))

    def test_wrong_draft_votes_and_duplicate_voter_rejected(self):
        e=setup_c3(); proposal,g=draft(e); v=votes(e,proposal,g,"votes")
        other,g2=draft(e,"other")
        with self.assertRaises(ValueError): e.start("wrong-votes",req(e,"wrong-votes","institutionalize-expenditure-v1",(other,*v),group=g2,peer=BOB))
        own=seed_intent(e,"again-own")
        work(e,req(e,"again-vote","vote-v1",(proposal,own),group=g))
        duplicate=e.job_status(ALICE,"again-vote")["public.0"]; expose(e,ALICE,duplicate)
        with self.assertRaises(ValueError): e.start("duplicate",req(e,"duplicate","institutionalize-expenditure-v1",(proposal,v[0],duplicate),group=g,peer=BOB))

    def test_stale_group_and_transitive_stance_invalidate_paid_work(self):
        for mode in ("group","stance"):
            e=setup_c3(); r=cell(e,"Share","expenditure",prepare_only=True)["request"]
            e.start("begin",r); e.advance("paid",ALICE,r.key,10000)
            if mode=="group": collective_work(e,"depart","leave",actor=BOB,focus=r.group)
            else:
                own=ref("case-receiver")
                e.declare("changed-stance",(next_version(e.world.resolve(own),label="Withdrawn old stance"),))
            e.commit("finish",ALICE,r.key)
            self.assertEqual(e.job_status(ALICE,r.key)["failure"],"stale_dependency")
            self.assertGreater(e.job_status(ALICE,r.key)["spent"],0)
            audit(e.world.journal(),e.access.checkpoint())

    def test_one_attempt_survives_cancellation_and_public_aliases(self):
        e=setup_c3(); r=cell(e,"Mobilize","expenditure",prepare_only=True)["request"]
        e.start("begin",r); e.cancel("stop",ALICE,r.key)
        with self.assertRaisesRegex(ValueError,"already attempted"):
            e.start("retry",replace(r,key="retry"))
        owned=e._self_public[r.input]["binding"]
        with self.assertRaisesRegex(ValueError,"already attempted"):
            e.start("alias",replace(r,key="alias",inputs=(owned,)))
        audit(e.world.journal(),e.access.checkpoint())

    def test_shared_allowance_cannot_be_spent_through_both_apis(self):
        from tests_c2.fixtures import consume as consume_c2
        for first in ("c2","c3"):
            e=setup_c3(); source,g=shared(e)
            if first=="c2":
                plan=consume_c2(e,source,"legacy",target=SAW,group=g,stock=SUPPLY,demand=2)
                enact(e,plan,"legacy-action")
                current=e.world.head(SUPPLY.identity).ref; expose(e,ALICE,current)
                with self.assertRaises(ValueError): e.start("cross",req(e,"cross","mobilize-expenditure-v1",(source,),stock=current,group=g,peer=BOB))
            else:
                work(e,req(e,"cross","mobilize-expenditure-v1",(source,),stock=SUPPLY,group=g,peer=BOB))
                current=e.world.head(SUPPLY.identity).ref; expose(e,ALICE,current)
                plan=consume_c2(e,source,"legacy",target=SAW,group=g,stock=current,demand=2)
                with self.assertRaises(ValueError): e.enact("legacy-action",ALICE,"legacy-action",plan)
            audit(e.world.journal(),e.access.checkpoint())

    def test_material_failure_retains_paid_work_without_effect(self):
        for foreign in (False,True):
            e=setup_c3(quantity=1); r=cell(e,"Express","expenditure",prepare_only=True)["request"]
            if foreign: r=replace(r,stock=ref("bob-consumables"))
            work(e,r,allow_failure=True)
            self.assertEqual(e.job_status(ALICE,r.key)["status"],"failed")
            self.assertGreater(e.job_status(ALICE,r.key)["spent"],0)
            self.assertEqual(attrs(e.world.resolve(r.stock))["consumed"],0)
            audit(e.world.journal(),e.access.checkpoint())

    def test_missing_row_edges_are_composite_and_attitudes_can_vary(self):
        for name in PATHS:
            e=setup_c3(); r=cell(e,name,"accumulation",prepare_only=True)["request"]
            elements=CROSSING_RECIPES[r.recipe].elements
            changed=tuple(x[0]+("e" if x[1]=="i" else "i") for x in elements)
            work(e,replace(r,elements=changed)); audit(e.world.journal(),e.access.checkpoint())
        e=setup_c3(); r=cell(e,"Express","accumulation",prepare_only=True)["request"]
        with self.assertRaises(ValueError): replace(r,elements=("si",))

    def test_hidden_stock_change_does_not_alter_undelivered_theory(self):
        values=[]
        for quantity in (2,9):
            e=setup_c3(quantity=quantity); out=cell(e,"Theorize","accumulation",consumer=False)
            values.append(data(e,out["result"]))
        self.assertEqual(*values)

    def test_observation_revision_changes_reusable_model_use(self):
        e=setup_c3(); out=cell(e,"Organize","accumulation",consumer=False)
        before=data(e,out["result"])["cap"]
        perform(e,OperationRequest("deplete",ALICE,"consume",ROOM,stock=SUPPLY,amount=4,evidence=evidence(e,ALICE,SUPPLY)))
        obs=inspect(e,"reobserve"); new=work(e,req(e,"reorganize","organize-accumulation-v1",(obs,)))
        self.assertEqual((before,data(e,new)["cap"]),(6,2))
        current=e.world.head(SUPPLY.identity).ref
        plan=work(e,req(e,"changed-case","use-system-v1",(new,),stock=current,demand=5))
        self.assertEqual(data(e,plan)["amount"],2)
        audit(e.world.journal(),e.access.checkpoint())

    def test_received_rule_does_not_grant_practiced_competence(self):
        e=setup_c3(); out=cell(e,"Educate","expenditure")
        public=e.job_status(ALICE,"case")["public.0"]
        result=data(e,public)
        self.assertTrue(result["teaching"]); self.assertFalse(result["competence"])
        self.assertNotEqual(result["receiver_answer"],consequence(e,out))
        self.assertFalse(e.participant_view(BOB).can_use(REPAIR,ROOM))

    def test_native_observation_forgery_rejected_independently(self):
        e=setup_c3(); cell(e,"Organize","accumulation")
        txs=[]; changed=False
        for tx in e.world.journal():
            values=[]
            for v in tx.versions:
                if not changed and v.ref.identity.namespace=="u4.observation":
                    d=attrs(v); d["available"]=999; v=replace(v,attributes=attributes(d)); changed=True
                values.append(v)
            txs.append(replace(tx,versions=tuple(values)))
        with self.assertRaises(ValueError): audit(txs,e.access.checkpoint())

    def test_raw_semantics_debits_predecessors_polarity_and_public_result(self):
        e=setup_c3(); cell(e,"Share","expenditure")
        for mode in ("content","predecessor","paid","polarity","public","audience"):
            changed=False; txs=[]
            for tx in e.world.journal():
                values=[]
                for v in tx.versions:
                    ns="c3.message" if mode in ("public","audience") else "c3.step"
                    if not changed and v.ref.identity.namespace==ns:
                        d=attrs(v)
                        if mode=="content":
                            a=v.facet(Account); val=cross.decode(a.content[0].object); val["cap"]=999
                            v=replace(v,facets=(replace(a,content=(replace(a.content[0],object=cross.encode(val)),)),))
                        elif mode=="public":
                            val=cross.decode(d["payload"]); val["cap"]=999; d["payload"]=cross.encode(val); v=replace(v,attributes=attributes(d))
                        else:
                            k={"predecessor":"predecessor","paid":"paid_threshold","polarity":"polarity","audience":"audience.1"}[mode]
                            d[k]={"predecessor":ROOM,"paid":0,"polarity":"wrong","audience":EVE}[mode]
                            v=replace(v,attributes=attributes(d))
                        changed=True
                    values.append(v)
                txs.append(replace(tx,versions=tuple(values)))
            with self.subTest(mode=mode),self.assertRaises(ValueError): audit(txs,e.access.checkpoint())

    def test_display_labels_are_not_the_semantic_operation(self):
        e=setup_c3(); cell(e,"Institutionalize","expenditure")
        txs=[replace(tx,versions=tuple(replace(v,label="renamed") if v.ref.identity.namespace in ("c3.step","c3.output","c3.message") else v for v in tx.versions)) for tx in e.world.journal()]
        self.assertTrue(audit(txs,e.access.checkpoint())["passed"])

    def test_duplicate_commands_do_not_duplicate_debits(self):
        e=setup_c3(); r=cell(e,"Apply","expenditure",prepare_only=True)["request"]
        work(e,r); cp=e.checkpoint(); work(e,r)
        self.assertEqual(cp,e.checkpoint())

    def test_c2_upgrade_preserves_exact_world_access_and_behavior(self):
        old=setup_c2(); new=CrossingEngine.from_c2(old.checkpoint())
        for branch in (old,new): cell_c2(branch,"Commune","expenditure")
        self.assertEqual(old.world.checkpoint(),new.world.checkpoint())
        self.assertEqual(old.access.checkpoint(),new.access.checkpoint())
        audit(new.world.journal(),new.access.checkpoint())

    def test_polarity_faces_have_distinct_downstream_permissions(self):
        for name in ("Embody","Identify","Understand","Organize"):
            results=[]
            for face in FACES:
                e=setup_c3(); out=cell(e,name,face); decision=data(e,out["downstream"])
                results.append(decision["amount"])
                self.assertEqual(decision["permitted"],face=="expenditure")
                self.assertEqual("event" in out,face=="expenditure")
                audit(e.world.journal(),e.access.checkpoint())
            self.assertEqual(*results)

    def test_received_governed_arrangement_does_not_borrow_authority(self):
        e=setup_c3(); cell(e,"Organize","expenditure",consumer=False)
        public=e.job_status(ALICE,"case")["public.0"]; expose(e,BOB,public)
        plan=work(e,req(e,"read-arrangement","use-system-v1",(public,),actor=BOB,stock=ref("bob-consumables")))
        self.assertFalse(data(e,plan,BOB)["permitted"])
        with self.assertRaises(ValueError): e.enact("borrowed",BOB,"borrowed",plan)
        with self.assertRaises(ValueError):
            e.start("borrowed-apply",req(e,"borrowed-apply","apply-expenditure-v1",(public,),actor=BOB,stock=ref("bob-consumables")))
        audit(e.world.journal(),e.access.checkpoint())

if __name__=="__main__": unittest.main()
