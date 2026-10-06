import unittest
from dataclasses import replace
from hle.model_a import TYPES
from tests_c2.fixtures import *
from hle_unified.self_audit import audit
from hle_unified.self_records import SELF_RECIPES
from tests_u11.fixtures import work as collective_work

NAMES=("Contemplate","Act","Commune","Integrate")
FACES=("accumulation","expenditure")


def make(name,face,**kwargs):
    return setup_c2(actual="serviceable" if name=="Act" and face=="expenditure" else "damaged",**kwargs)


def consequence(e,out,name):
    if name=="Act": return attrs(e.world.resolve(out["downstream"]))["outcome"]
    d=data(e,out["downstream"],out.get("consumer_actor",ALICE))
    if name=="Commune": return (d["action"],d["amount"])
    if name=="Integrate": return (d["action"],d["reachable"])
    return d["action"]


class SelfRouteTests(unittest.TestCase):
    def test_eight_contracts_all_sixteen_types(self):
        for tim in TYPES:
            for name in NAMES:
                for face in FACES:
                    with self.subTest(tim=tim,name=name,face=face):
                        e=make(name,face,tim=tim); out=cell(e,name,face)
                        d=e.job_status(ALICE,"case")
                        self.assertEqual(d["status"],"succeeded")
                        self.assertEqual(d["origin"],d["destination"])
                        self.assertEqual(d["route_count"],2)
                        self.assertGreater(d["spent"],0)
                        self.assertEqual(audit(e.world.journal(),e.access.checkpoint())["c2_self_completed"],1)
                        if name=="Act": self.assertEqual(consequence(e,out,name),"succeeded")
                        elif name=="Contemplate": self.assertEqual(consequence(e,out,name),"inspect")
                        elif name=="Commune": self.assertEqual(consequence(e,out,name),("propose" if face=="accumulation" else "consume",2))
                        else:
                            self.assertIn("used",data(e,out["downstream"])["reachable"])
                            if face=="expenditure": self.assertEqual(attrs(e.world.resolve(out["follow_event"]))["outcome"],"succeeded")

    def test_eight_matched_semantic_ablations(self):
        for name in NAMES:
            for face in FACES:
                with self.subTest(name=name,face=face):
                    e=make(name,face); control=make(name,face,engine_type=Ablated)
                    out=cell(e,name,face); other=cell(control,name,face)
                    self.assertEqual(e.job_status(ALICE,"case")["spent"],control.job_status(ALICE,"case")["spent"])
                    self.assertNotEqual(consequence(e,out,name),consequence(control,other,name))
                    self.assertTrue(audit(e.world.journal(),e.access.checkpoint())["passed"])
                    with self.assertRaisesRegex(ValueError,"semantic postcondition"):
                        audit(control.world.journal(),control.access.checkpoint())

    def test_exact_continuation_at_semantic_and_material_boundaries(self):
        for name in NAMES:
            for face in FACES:
                for boundary in (0,1,2,3):
                    with self.subTest(name=name,face=face,boundary=boundary):
                        e=make(name,face); out=cell(e,name,face,prepare_only=True); r=out["request"]
                        e.start("start-case",r); d=e.job_status(ALICE,r.key)
                        first=d["recall_units"]+sum(indexed(d,"route.0.charges."))+d["route.0.content_units"]
                        units=(1,first,first+1,d["required"])[boundary]
                        e.advance("partial",ALICE,r.key,units)
                        cp=e.checkpoint(); restored=SelfRouteEngine.restore(cp)
                        self.assertEqual(cp,restored.checkpoint())
                        for branch in (e,restored):
                            if branch.job_status(ALICE,r.key)["status"]!="ready": branch.advance("finish-work",ALICE,r.key,100000)
                            branch.commit("finish",ALICE,r.key)
                        self.assertEqual(e.checkpoint(),restored.checkpoint())
                        self.assertTrue(audit(e.world.journal(),e.access.checkpoint())["passed"])

    def test_cancel_does_not_refund_or_publish_partial_content(self):
        for name in NAMES:
            for face in FACES:
                e=make(name,face); r=cell(e,name,face,prepare_only=True)["request"]
                before=e.wallet(ALICE)["energy"]
                e.start("begin",r); e.advance("part",ALICE,r.key,1); e.cancel("stop",ALICE,r.key)
                self.assertEqual(e.wallet(ALICE)["energy"],before-1)
                self.assertIsNone(e.job_status(ALICE,r.key).get("binding"))
                self.assertEqual(SelfRouteEngine.restore(e.checkpoint()).checkpoint(),e.checkpoint())
                audit(e.world.journal(),e.access.checkpoint())

    def test_exhaustion_retains_work_without_success(self):
        probe=setup_c2(); cell(probe,"Contemplate","accumulation",prepare_only=True)
        used=probe.wallet(ALICE)["initial_energy"]-probe.wallet(ALICE)["energy"]
        e=setup_c2(budget=used+1); r=cell(e,"Contemplate","accumulation",prepare_only=True)["request"]
        e.start("begin",r); e.advance("work",ALICE,r.key,10000)
        self.assertEqual(e.job_status(ALICE,r.key)["spent"],1)
        e.advance("exhausted",ALICE,r.key,10000)
        self.assertEqual(e.job_status(ALICE,r.key)["spent"],1)
        with self.assertRaises(ValueError): e.commit("free",ALICE,r.key)
        audit(e.world.journal(),e.access.checkpoint())

    def test_zero_displacement_is_not_zero_work(self):
        e=setup_c2(); r=cell(e,"Contemplate","accumulation",prepare_only=True)["request"]
        e.start("begin",r)
        with self.assertRaises(ValueError): e.commit("free",ALICE,r.key)
        with self.assertRaises(ValueError): replace(r,elements=("te","te"))
        self.assertEqual(e.job_status(ALICE,r.key)["steps_completed"],0)

    def test_stale_owned_input_fails_without_erasing_paid_work(self):
        e=setup_c2(); out=cell(e,"Contemplate","accumulation",prepare_only=True); r=out["request"]
        e.start("begin",r); e.advance("paid",ALICE,r.key,10000)
        e.declare("changed-claim",(next_version(e.world.resolve(r.input),label="Revised prior"),))
        e.commit("finish",ALICE,r.key)
        self.assertEqual(e.job_status(ALICE,r.key)["failure"],"stale_dependency")
        self.assertIsNone(e.job_status(ALICE,r.key).get("binding"))
        audit(e.world.journal(),e.access.checkpoint())

    def test_stale_membership_invalidates_commune(self):
        e=setup_c2(); out=cell(e,"Commune","expenditure",prepare_only=True); r=out["request"]
        e.start("begin",r); e.advance("paid",ALICE,r.key,10000)
        collective_work(e,"departure","leave",actor=BOB,focus=r.group)
        e.commit("finish",ALICE,r.key)
        self.assertEqual(e.job_status(ALICE,r.key)["failure"],"stale_dependency")
        audit(e.world.journal(),e.access.checkpoint())

    def test_unread_reply_cannot_complete_shared_meaning(self):
        e=setup_c2(); out=cell(e,"Commune","accumulation",prepare_only=True); r=out["request"]
        reply=r.inputs[1]
        delivery=e.participant_view(ALICE).resolve(reply)[0].address.delivery
        other=SelfRouteEngine(OperationStore.restore(e._initial),LAW_REF)
        for command,_ in e._commands.values():
            if command[0]=="start" and type(command[2]) is OperationRequest and command[2].kind=="read" and command[2].delivery==delivery: break
            other._execute(command)
        with self.assertRaisesRegex(ValueError,"paid-read"):
            other.start("too-soon",r)

    def test_foreign_owned_content_and_wrong_scope_rejected(self):
        e=setup_c2(); out=cell(e,"Contemplate","accumulation",prepare_only=True); r=out["request"]
        show(e,BOB,SAW)
        with self.assertRaises(ValueError): e.start("foreign",replace(r,actor=BOB,evidence=evidence(e,BOB,SAW)))
        with self.assertRaises(ValueError): e.start("scope",replace(r,cue=CUE))

    def test_private_steps_cannot_be_disclosed_or_injected(self):
        e=setup_c2(); cell(e,"Contemplate","accumulation",consumer=False)
        d=e.job_status(ALICE,"case"); step=e.world.resolve(d["last_step"])
        with self.assertRaises(ValueError): e.disclose("leak",BOB,step.ref,(Selector("name","name",("label",)),))
        with self.assertRaises(ValueError): e.declare("forge",(step,))

    def test_dissent_is_retained_and_does_not_grant_action(self):
        e=setup_c2(); out=cell(e,"Commune","expenditure",consent=False)
        self.assertFalse(data(e,out["result"])["authorized"])
        self.assertEqual(data(e,out["result"])["status"],"declined")
        with self.assertRaises(ValueError): e.enact("not-consent",BOB,"denied",out["downstream"])
        self.assertEqual(attrs(e.world.resolve(ref("bob-consumables")))["consumed"],0)
        audit(e.world.journal(),e.access.checkpoint())

    def test_accumulation_agreement_is_not_commitment(self):
        e=setup_c2(); out=cell(e,"Commune","accumulation")
        self.assertEqual(data(e,out["result"])["positions"],(5,2))
        self.assertTrue(data(e,out["result"])["difference"])
        with self.assertRaises(ValueError): e.enact("not-committed",BOB,"denied",out["downstream"])
        proposal=e.job_status(BOB,"case-later")["public.0"]
        self.assertEqual(data(e,proposal)["amount"],2)

    def test_one_attempt_commitment_cannot_be_spent_twice(self):
        e=setup_c2(); out=cell(e,"Commune","expenditure")
        source=e.job_status(ALICE,"case")["public.0"]
        next_plan=consume(e,source,"again",actor=BOB,group=out["extra"]["group"],stock=e.world.head(ref("bob-consumables").identity).ref,demand=4)
        with self.assertRaisesRegex(ValueError,"one-attempt"):
            e.enact("repeat",BOB,"repeat",next_plan)
        self.assertEqual(attrs(e.world.head(ref("bob-consumables").identity))["consumed"],2)

    def test_reconciled_model_has_no_execution_authority(self):
        e=setup_c2(); out=cell(e,"Integrate","accumulation")
        self.assertIn("used",data(e,out["downstream"])["reachable"])
        with self.assertRaises(ValueError): e.enact("not-coupled",ALICE,"denied",out["downstream"])
        self.assertEqual(e.world.head(SAW.identity).ref,SAW)

    def test_system_conflicts_cycles_and_external_requirements(self):
        cases=[("conflict",(("restore",("serviceable",),("used",),"use",ALICE),),"conflicts"),
               ("cycle",(("undo",("serviceable",),("damaged",),"damage",ALICE),),"cycles"),
               ("external",(("maintain",("worn",),("maintained",),"care",ALICE),),"external")]
        for label,nodes,field in cases:
            e=setup_c2(); a=seed_data(e,"a",dict(kind="system",nodes=(("restore",("damaged",),("serviceable",),"repair",ALICE),)))
            b=seed_data(e,"b",dict(kind="system",nodes=nodes))
            result=work(e,req(e,"merge","integrate-expenditure-v1",(a,b)))
            d=data(e,result); self.assertTrue(d[field])
            if label!="external": self.assertFalse(d["coupled"])
            audit(e.world.journal(),e.access.checkpoint())

    def test_unowned_system_authority_is_rejected(self):
        e=setup_c2(); bad=dict(kind="system",nodes=(("x",("damaged",),("serviceable",),"repair",BOB),))
        ref1=seed(e,"bad-system",sem.encode(bad),relation="c2.data")
        good=seed_data(e,"good",dict(kind="system",nodes=(("y",("serviceable",),("used",),"use",ALICE),)))
        with self.assertRaises(ValueError): e.start("bad",req(e,"bad","integrate-expenditure-v1",(ref1,good)))

    def test_act_preconditions_preserve_failed_work(self):
        e=setup_c2(actual="serviceable")
        r=req(e,"invalid-repair","act-accumulation-v1",(SAW,KIT,STOCK),tool=KIT,stock=STOCK)
        perform(e,r,limit=10000)
        self.assertEqual(e.job_status(ALICE,r.key)["status"],"failed")
        self.assertGreater(e.job_status(ALICE,r.key)["spent"],0)
        self.assertEqual(attrs(e.world.resolve(STOCK))["consumed"],0)
        audit(e.world.journal(),e.access.checkpoint())

    def test_hidden_state_does_not_change_personal_result(self):
        results=[]
        for actual in ("serviceable","damaged"):
            e=setup_c2(actual=actual); out=cell(e,"Contemplate","expenditure",consumer=False)
            results.append(data(e,out["result"]))
        self.assertEqual(*results)

    def test_transfer_second_tool_retains_scoped_content(self):
        for name in NAMES:
            e=setup_c2(); out=cell(e,name,"accumulation",target=SAW2)
            if name!="Act": self.assertEqual(e.participant_view(ALICE)._bindings[out["result"]].target,SAW2)
            audit(e.world.journal(),e.access.checkpoint())

    def test_raw_audit_rejects_forged_semantics_debits_and_predecessors(self):
        e=setup_c2(); cell(e,"Integrate","expenditure")
        for mode in ("content","predecessor","paid","polarity"):
            changed=[]; done=False
            for tx in e.world.journal():
                values=[]
                for v in tx.versions:
                    if not done and v.ref.identity.namespace=="c2.step":
                        d=attrs(v)
                        if mode=="content":
                            a=v.facet(Account); content=dict(sem.decode(a.content[0].object)); content["compatible"]=False
                            v=replace(v,facets=(replace(a,content=(replace(a.content[0],object=sem.encode(content)),)),))
                        else:
                            d[{"predecessor":"predecessor","paid":"paid_threshold","polarity":"polarity"}[mode]]={"predecessor":ROOM,"paid":0,"polarity":"wrong"}[mode]
                            v=replace(v,attributes=attributes(d))
                        done=True
                    values.append(v)
                changed.append(replace(tx,versions=tuple(values)))
            with self.subTest(mode=mode),self.assertRaises(ValueError): audit(changed,e.access.checkpoint())

    def test_display_labels_do_not_supply_semantic_capacity(self):
        e=setup_c2(); cell(e,"Integrate","accumulation")
        txs=[replace(tx,versions=tuple(replace(v,label="renamed") if v.ref.identity.namespace in ("c2.step","c2.output") else v for v in tx.versions)) for tx in e.world.journal()]
        self.assertTrue(audit(txs,e.access.checkpoint())["passed"])

    def test_c1_upgrade_preserves_exact_old_behavior(self):
        old=setup_c1(); current=SelfRouteEngine.from_c1(old.checkpoint())
        run_circuit(old); run_circuit(current)
        self.assertEqual(old.world.checkpoint(),current.world.checkpoint())
        self.assertEqual(old.access.checkpoint(),current.access.checkpoint())
        audit(current.world.journal(),current.access.checkpoint())

    def test_duplicate_commands_do_not_duplicate_work(self):
        e=setup_c2(); r=cell(e,"Contemplate","accumulation",prepare_only=True)["request"]
        e.start("begin",r); e.advance("work",ALICE,r.key,10000); e.commit("finish",ALICE,r.key)
        cp=e.checkpoint(); e.start("begin",r); e.advance("work",ALICE,r.key,10000); e.commit("finish",ALICE,r.key)
        self.assertEqual(cp,e.checkpoint())

if __name__=="__main__": unittest.main()
