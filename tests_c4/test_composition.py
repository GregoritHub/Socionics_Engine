import unittest
from dataclasses import replace
from hle.model_a import TYPES
from tests_c4.fixtures import *
from tests_u11.fixtures import work as collective_work
from hle_unified.crux_composition_records import COMPOSITION_RECIPES


class CompositionTests(unittest.TestCase):
    def test_five_connected_families_across_sixteen_types(self):
        for tim in TYPES:
            for name,wanted in zip(FAMILIES,(2,1,4,2,4)):
                with self.subTest(tim=tim,family=name):
                    e=setup(tim); out=family(e,name)
                    self.assertEqual(out["outcome"],wanted)
                    p=read_data(e,out["parent"])
                    self.assertTrue(p["complete"]); self.assertEqual(p["links"],out["links"])
                    self.assertTrue(audit(e.world.journal(),e.access.checkpoint())["passed"])

    def test_seven_matched_semantic_controls(self):
        for name in (*FAMILIES,"parent","context"):
            run=(nested if name=="parent" else context_case if name=="context" else lambda e:family(e,name))
            e=setup(); c=setup(engine_type=Ablated); a=run(e); b=run(c)
            self.assertEqual(e.job_status(ALICE,"case")["spent"],c.job_status(ALICE,"case")["spent"])
            self.assertNotEqual(a["outcome"],b["outcome"])
            self.assertTrue(audit(e.world.journal(),e.access.checkpoint())["passed"])
            with self.assertRaises(ValueError): audit(c.world.journal(),c.access.checkpoint())

    def prepared_recipes(self):
        e=setup(); family(e,FAMILIES[1])
        yield before_request(e,"case-renew")
        q,r=before_request(e,"case"); yield q,r
        q,r=before_request(e,"case"); yield q,replace(r,recipe="commune-accumulation-v1")
        e=setup(); family(e,FAMILIES[4])
        q,r=before_request(e,"case"); yield q,r
        q,r=before_request(e,"case"); yield q,replace(r,recipe="integrate-accumulation-v1")
        e=setup(); yield e,context_case(e,prepare_only=True)
        e=setup(); yield e,nested(e,prepare_only=True)
        e=setup(); nested(e); yield before_request(e,"case-release")

    def test_eight_recipes_exact_continuation_at_three_boundaries(self):
        for e,r in self.prepared_recipes():
            baseline=e.checkpoint()
            for boundary in range(3):
                with self.subTest(recipe=r.recipe,boundary=boundary):
                    a=CruxCompositionEngine.restore(baseline); a.start("begin",r); d=a.job_status(ALICE,r.key)
                    first=d["recall_units"]+sum(indexed(d,"route.0.charges."))+d["route.0.content_units"]
                    a.advance("partial",ALICE,r.key,(1,first,d["required"])[boundary])
                    cp=a.checkpoint(); b=CruxCompositionEngine.restore(cp)
                    self.assertEqual(cp,b.checkpoint())
                    for z in (a,b):
                        if z.job_status(ALICE,r.key)["status"]!="ready": z.advance("resume",ALICE,r.key,100000)
                        z.commit("finish",ALICE,r.key)
                    self.assertEqual(a.checkpoint(),b.checkpoint())
                    audit(a.world.journal(),a.access.checkpoint())

    def test_cancel_every_recipe_preserves_spending_without_output(self):
        for e,r in self.prepared_recipes():
            before=e.wallet(ALICE)["energy"]; e.start("begin",r); e.advance("partial",ALICE,r.key,1); e.cancel("stop",ALICE,r.key)
            self.assertEqual(e.wallet(ALICE)["energy"],before-1)
            self.assertIsNone(e.job_status(ALICE,r.key).get("binding"))
            audit(e.world.journal(),e.access.checkpoint())

    def test_exhaustion_preserves_child_work_and_no_parent_completion(self):
        p=setup(); nested(p,prepare_only=True); cost=p.wallet(ALICE)["initial_energy"]-p.wallet(ALICE)["energy"]
        e=setup(budget=cost+1); r=nested(e,prepare_only=True)
        e.start("begin",r); e.advance("pay",ALICE,r.key,100000); e.advance("empty",ALICE,r.key,100000)
        self.assertEqual(e.job_status(ALICE,r.key)["spent"],1)
        with self.assertRaises(ValueError): e.commit("free",ALICE,r.key)
        self.assertEqual(len(r.children),2); audit(e.world.journal(),e.access.checkpoint())

    def test_cancelled_child_blocks_parent_and_later_release(self):
        e=setup(); out=nested(e,failed=True)
        p=read_data(e,out["parent"])
        self.assertFalse(p["complete"]); self.assertEqual(p["status"],"blocked")
        self.assertEqual(p["outcomes"][-1][2],"cancelled"); self.assertEqual(out["outcome"],0)
        self.assertGreater(p["cited_spending"],0); audit(e.world.journal(),e.access.checkpoint())

    def test_material_failure_remains_a_failed_child(self):
        e=setup(); m=model(e,cap=20)
        event=work(e,cross_req(e,"too-large","apply-expenditure-v1",(m,),stock=SUPPLY,demand=20),allow_failure=True)
        obs=receive(e,event,ALICE,"failed-material")
        children=(child(e,"model",m),child(e,"too-large",obs))
        p=work(e,parent_request(e,children,links=((0,1),)))
        self.assertFalse(read_data(e,p)["complete"])
        self.assertEqual(e.job_status(ALICE,"too-large")["status"],"failed")
        self.assertEqual(attrs(e.world.head(SUPPLY.identity))["consumed"],0)
        audit(e.world.journal(),e.access.checkpoint())

    def test_parent_spends_only_own_review_and_deduplicates_descendants(self):
        e=setup(); m=model(e); leaf=child(e,"model",m)
        left=work(e,parent_request(e,(leaf,),"left")); right=work(e,parent_request(e,(leaf,),"right"))
        r=parent_request(e,(child(e,"left",left),child(e,"right",right)),"root")
        before=e.wallet(ALICE)["energy"]; out=work(e,r); p=read_data(e,out)
        self.assertEqual(before-e.wallet(ALICE)["energy"],e.job_status(ALICE,"root")["spent"])
        self.assertEqual(len(p["operations"]),3)
        self.assertEqual(p["cited_spending"],sum(e.job_status(ALICE,k)["spent"] for k in ("model","left","right")))
        cp=e.checkpoint(); work(e,r); self.assertEqual(cp,e.checkpoint())
        audit(e.world.journal(),e.access.checkpoint())

    def test_declared_depth_bound_and_exact_nested_costs(self):
        for depth in (1,2,4):
            e=setup(); out=nested(e,depth=depth)
            p=read_data(e,out["parent"]); self.assertEqual(p["depth"],depth)
            self.assertEqual(len(p["operations"]),2+depth-1)
            if depth==4:
                r=parent_request(e,(child(e,"case-level-3",out["parent"]),),"too-deep")
                with self.assertRaises(ValueError): e.start("too-deep",r)
            audit(e.world.journal(),e.access.checkpoint())

    def test_group_change_and_real_withdrawal_invalidate_parent(self):
        for mode in ("group","withdrawal"):
            e=setup(); out=family(e,FAMILIES[1]); p=read_data(e,out["parent"])
            q,r=before_request(e,"case-parent"); q.start("begin-parent",r); q.advance("paid-parent",ALICE,r.key,100000)
            if mode=="group": collective_work(q,"leave-now","leave",actor=BOB,focus=r.group)
            else:
                own=ref("case-renew-b"); old=q.world.resolve(own); acc=old.facet(Account)
                changed=comp.decode(acc.content[0].object); changed["consent"]=False
                new=next_version(old,facets=(replace(acc,content=(replace(acc.content[0],object=comp.encode(changed)),)),))
                q.declare("withdraw",(new,))
                perform(q,OperationRequest("retain-withdrawal",BOB,"bind",ROOM,binding=new.ref,evidence=evidence(q,BOB,SAW)))
            q.commit("finish-parent",ALICE,r.key)
            self.assertEqual(q.job_status(ALICE,r.key)["failure"],"stale_dependency")
            self.assertIsNone(q.job_status(ALICE,r.key).get("binding"))
            audit(q.world.journal(),q.access.checkpoint())

    def test_stale_successful_parent_cannot_release_after_child_revision(self):
        e=setup(); out=nested(e); model_ref=out["children"][0].output
        own=ref("case-child-0-intent"); e.declare("revision",(next_version(e.world.resolve(own),label="Revised intention"),))
        release=request(e,"late-release","release-v1",(out["parent"],model_ref))
        work(e,release,allow_failure=True)
        self.assertEqual(e.job_status(ALICE,"late-release")["failure"],"stale_dependency")
        audit(e.world.journal(),e.access.checkpoint())

    def test_endpoint_equality_cannot_substitute_an_unrelated_history(self):
        e=setup(); out=family(e,FAMILIES[0]); unrelated=model(e,"unrelated")
        children=(child(e,"unrelated",unrelated),out["children"][1])
        with self.assertRaisesRegex(ValueError,"actual content handoff"):
            e.start("unrelated-parent",parent_request(e,children,"unrelated-parent",links=((0,1),)))

    def test_unread_or_foreign_child_and_forged_output_are_rejected(self):
        e=setup(); out=nested(e); r=parent_request(e,out["children"],"again")
        with self.assertRaises(ValueError): e.start("foreign",replace(r,actor=BOB))
        with self.assertRaises(ValueError): e.start("unread",replace(r,evidence=(DetailAddress("missing","payload"),)))
        with self.assertRaises(ValueError): e.start("forged",replace(r,children=(replace(r.children[0],operation=r.children[1].operation),r.children[1])))
        with self.assertRaises(ValueError): e.declare("import",(e.world.resolve(out["parent"]),))
        with self.assertRaises(ValueError): expose4(e,BOB,out["parent"])
        # Reconstruct before the final child's receipt is paid-read.
        delivery=e.participant_view(ALICE).resolve(r.children[-1].operation)[0].address.delivery
        q=CruxCompositionEngine(OperationStore.restore(e._initial),LAW_REF)
        for command,_ in e._commands.values():
            if command[0]=="start" and type(command[2]) is OperationRequest and command[2].delivery==delivery: break
            q._execute(command)
        with self.assertRaises(ValueError): q.start("missing-receipt",r)

    def test_context_transfer_needs_local_evidence_and_does_not_copy_authority(self):
        e=setup(); r=context_case(e,prepare_only=True)
        with self.assertRaises(ValueError): e.start("shortcut",replace(cross_req(e,"shortcut","use-system-v1",(r.inputs[0],)),context=r.context))
        with self.assertRaises(ValueError): e.start("missing-local",replace(r,inputs=r.inputs[:2]))
        out=work(e,r); d=read_data(e,out)
        self.assertEqual((d["source_context"],d["context"]),(ROOM,r.context)); self.assertEqual(d["cap"],1)
        self.assertIsNone(d["authority"]); self.assertTrue(d["uncertain"]); audit(e.world.journal(),e.access.checkpoint())

    def test_distinct_histories_and_mixed_faces_survive_return(self):
        e=setup(); out=family(e,FAMILIES[0]); p=read_data(e,out["parent"])
        self.assertEqual((p["outcomes"][0][3],p["outcomes"][-1][4]),("I","I"))
        self.assertEqual(p["polarities"],("accumulation","expenditure","expenditure"))
        self.assertEqual(attrs(e.world.head(SUPPLY.identity))["consumed"],4)
        self.assertEqual(out["outcome"],2)
        self.assertNotEqual(read_data(e,out["children"][0].output),read_data(e,out["children"][-1].output))
        self.assertGreater(p["cited_spending"],0)

    def test_commune_accumulation_preserves_difference_without_commitment(self):
        e=setup(); family(e,FAMILIES[1]); q,r=before_request(e,"case")
        out=work(q,replace(r,recipe="commune-accumulation-v1")); d=read_data(q,out)
        self.assertFalse(d["authorized"]); self.assertTrue(d["difference"]); self.assertEqual(d["prior_difference"],"capacity_difference")
        audit(q.world.journal(),q.access.checkpoint())

    def test_uncoupled_integrate_permits_assessment_and_trial_only(self):
        e=setup(); a=model(e,"one",cap=5); b=model(e,"two",cap=2)
        out=work(e,request(e,"integrate","integrate-expenditure-v1",(a,b)))
        self.assertFalse(read_data(e,out)["coupled"])
        with self.assertRaises(ValueError): e.start("forbidden",cross_req(e,"forbidden","apply-expenditure-v1",(out,),stock=SUPPLY))
        event=work(e,cross_req(e,"trial","apply-accumulation-v1",(out,),stock=SUPPLY))
        self.assertEqual(attrs(e.world.head(SUPPLY.identity))["consumed"],1); audit(e.world.journal(),e.access.checkpoint())

    def test_nested_summary_cannot_be_used_as_model_or_borrowed_competence(self):
        e=setup()
        out=nested(e)
        self.assertFalse(read_data(e,out["parent"])["competence"])
        with self.assertRaises(ValueError): e.start("wrong-schema",cross_req(e,"wrong-schema","apply-expenditure-v1",(out["parent"],),stock=SUPPLY))
        with self.assertRaises(ValueError): e.start("borrow",request(e,"borrow","release-v1",(out["parent"],out["children"][0].output),actor=BOB))
        with self.assertRaises(ValueError): e.enact("borrow-act",BOB,"borrow-act",out["decision"])

    def test_compatible_numeric_limits_keep_conflicts_and_provenance(self):
        e=setup(); out=family(e,FAMILIES[4]); integrated=read_data(e,out["children"][1].output)
        self.assertEqual(integrated["limits"],(6,2)); self.assertTrue(integrated["differences"])
        self.assertEqual(len(integrated["components"]),2); self.assertTrue(integrated["uncertain"])

    def test_raw_postconditions_handoffs_costs_and_parent_claims(self):
        e=setup(); nested(e)
        for mode in ("content","predecessor","paid","polarity","children","spending"):
            changed=False; txs=[]
            for tx in e.world.journal():
                values=[]
                for v in tx.versions:
                    if not changed and v.ref.identity.namespace=="c4.step":
                        d=attrs(v)
                        if mode in ("content","children","spending"):
                            acc=v.facet(Account); val=comp.decode(acc.content[0].object); nested_value=comp.decode(val["work"])
                            if mode=="content": nested_value["complete"]=False
                            elif mode=="children": nested_value["children"]=()
                            else: nested_value["cited_spending"]+=1
                            val["work"]=comp.encode(nested_value)
                            v=replace(v,facets=(replace(acc,content=(replace(acc.content[0],object=comp.encode(val)),)),))
                        else:
                            k={"predecessor":"predecessor","paid":"paid_threshold","polarity":"polarity"}[mode]
                            d[k]={"predecessor":ROOM,"paid":0,"polarity":"wrong"}[mode]; v=replace(v,attributes=attributes(d))
                        changed=True
                    values.append(v)
                txs.append(replace(tx,versions=tuple(values)))
            with self.subTest(mode=mode),self.assertRaises(ValueError): audit(txs,e.access.checkpoint())

    def test_display_labels_do_not_change_meaning(self):
        e=setup(); family(e,FAMILIES[1])
        txs=[replace(tx,versions=tuple(replace(v,label="Changed display label") if v.ref.identity.namespace in ("c4.step","c4.output","c4.message") else v for v in tx.versions)) for tx in e.world.journal()]
        self.assertTrue(audit(txs,e.access.checkpoint())["passed"])

    def test_c3_checkpoint_upgrade_preserves_world_and_access(self):
        e=setup_c3(); cell(e,"Theorize","accumulation")
        q=CruxCompositionEngine.from_c3(e.checkpoint())
        self.assertEqual(q.world.checkpoint(),e.world.checkpoint()); self.assertEqual(q.access.checkpoint(),e.access.checkpoint())
        self.assertTrue(audit(q.world.journal(),q.access.checkpoint())["passed"])

    def test_renewal_cannot_mint_another_commitment_from_the_same_exchange(self):
        e=setup();family(e,FAMILIES[1])
        for cancelled in (False,True):
            q,r=before_request(e,"case")
            q.start("begin",r);q.advance("first-work",ALICE,r.key,1)
            if cancelled:q.cancel("cancel",ALICE,r.key)
            else:
                q.advance("rest-work",ALICE,r.key,100000);q.commit("finish",ALICE,r.key)
            cp=q.checkpoint();restored=CruxCompositionEngine.restore(cp)
            for branch in (q,restored):
                with self.assertRaisesRegex(ValueError,"already attempted"):
                    branch.start("reused-renewal",replace(r,key="reused-renewal"))
                self.assertEqual(branch.checkpoint(),cp)
            audit(q.world.journal(),q.access.checkpoint())
