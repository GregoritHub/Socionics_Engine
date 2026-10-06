import unittest
from dataclasses import replace
from tests_u11.fixtures import *
from hle_unified.collective_audit import audit
from hle_unified.records import Composition
from hle_unified.material import available
from hle_unified.operations import address


def team(*,train_bob=True):
    e=setup11(train_bob=train_bob)
    resources=(SHARED,ref("u11-kit-alice"),ref("u11-repair-alice"),BOB_CARE)
    g=group(e,"team",resources=tuple(e.world.head(x.identity).ref for x in resources))
    g=join(e,g)
    program=(step(ALICE,"repair",target=SHARED,tool=ref("u11-kit-alice"),stock=ref("u11-repair-alice")),
             step(ALICE,"transfer",target=SHARED,recipient=BOB),step(BOB,"use",target=SHARED),
             step(BOB,"care",target=SHARED,stock=BOB_CARE))
    return e,g,proposed(e,g,program)


class NestingTests(unittest.TestCase):
    def test_contextual_boundary_prevents_foreign_group_nesting(self):
        e=setup11();foreign=ref("foreign-room")
        e.declare("foreign-context",(ObjectVersion(foreign,WRITER,"Other room",(Role.CONTEXT,)),))
        expose(e,ALICE,foreign)
        perform(e,CollectiveRequest("foreign-group",ALICE,"compose",foreign,CUE5,boundary="Other room only"),limit=100000)
        child=indexed(e.job_status(ALICE,"foreign-group"),"output.")[0]
        work(e,"cross-context","compose",members=(child,),boundary="Workshop only",expect=False)
        self.assertEqual(e.job_status(ALICE,"cross-context")["status"],"failed")

    def test_overlap_counts_each_physical_instance_once(self):
        e=setup11();a=repair_group(e);b=group(e,"other",resources=(SHARED,))
        root=group(e,"root",members=(a["ref"],b["ref"]),resources=(SHARED,))
        s=work(e,"summary","summarize",focus=root["ref"])[0]
        self.assertEqual(dict(s["public"])["resource_count"],3)
        self.assertEqual(len(s["dependencies"]),6)
        self.assertEqual(audit(e.world.journal())["scoped_summaries"],1)

    def test_independent_detailed_inventory_projection_matches_aggregate(self):
        e=setup11();g=repair_group(e)
        a=work(e,"aggregate","summarize",focus=g["ref"])[0]
        b=work(e,"detailed","summarize",focus=g["ref"],mode="detailed")[0]
        m=[e.world.head(i).facet(Material) for i in g["resources"]]
        self.assertEqual(a["public"],b["public"])
        self.assertEqual(sum(row[-1] for row in dict(a["public"])["quantities_by_owner_unit"]),sum(x.quantity for x in m))

    def test_scoped_invalidation_reaches_affected_parents_only(self):
        e=setup11();a=repair_group(e);b=group(e,"b",resources=(SHARED,));root=group(e,"root",members=(a["ref"],b["ref"]))
        other=group(e,"unrelated",resources=(BOB_CARE,))
        for g in (a,b,root,other):nesting.project(e.world,g["ref"].identity,"inventory",128)
        nesting.project(e.world,root["ref"].identity,"membership",128)
        expose(e,ALICE,SHARED)
        # An inspection does not change material and hence should not invalidate.
        event=perform(e,OperationRequest("inspect",ALICE,"inspect",ROOM,target=SHARED,evidence=evidence(e,ALICE,SHARED)))
        self.assertIn(("u11.projection",root["ref"].identity,"inventory"),e.world.cache.values)
        for obj in (e.world.head(ref("u11-kit-alice").identity).ref,e.world.head(ref("u11-repair-alice").identity).ref):expose(e,ALICE,obj)
        perform(e,OperationRequest("change",ALICE,"repair",ROOM,target=SHARED,tool=e.world.head(ref("u11-kit-alice").identity).ref,
            stock=e.world.head(ref("u11-repair-alice").identity).ref,evidence=evidence(e,ALICE,SHARED)))
        for g in (a,b,root):self.assertNotIn(("u11.projection",g["ref"].identity,"inventory"),e.world.cache.values)
        self.assertIn(("u11.projection",other["ref"].identity,"inventory"),e.world.cache.values)
        self.assertIn(("u11.projection",root["ref"].identity,"membership"),e.world.cache.values)

    def test_projection_cache_does_not_change_participant_information(self):
        e=setup11();g=repair_group(e);before=e.participant_view(BOB).snapshot
        nesting.project(e.world,g["ref"].identity,"inventory",128)
        nesting.project(e.world,g["ref"].identity,"membership",128)
        self.assertEqual(before,e.participant_view(BOB).snapshot)
        with self.assertRaises(ValueError):work(e,"outsider","summarize",actor=BOB,focus=g["ref"])

    def test_summary_delivery_excludes_dependency_diagnostics(self):
        e=setup11();g=repair_group(e);s=work(e,"summary","summarize",focus=g["ref"])[0]
        v=e.world.resolve(s["ref"])
        selector=next(Selector(a.name,"detail",("attributes",str(i),"value")) for i,a in enumerate(v.attributes) if a.name.startswith("dependencies."))
        with self.assertRaises(ValueError):e.disclose("leak",ALICE,s["ref"],(selector,))
        expose(e,ALICE,s["ref"])
        body=dict(codec.loads(e.participant_view(ALICE).resolve(s["ref"])[0].value))
        self.assertNotIn("dependencies",body)

    def test_historical_summary_remains_exact_after_real_work(self):
        e,g,p=team();a=work(e,"before","summarize",focus=g["ref"])[0];old=e.world.resolve(a["ref"])
        run=perform_step(e,instantiate(e,p),"first")
        b=work(e,"after","summarize",focus=g["ref"])[0]
        self.assertEqual(e.world.resolve(a["ref"]),old)
        self.assertEqual(a["ref"].identity,b["ref"].identity)
        self.assertEqual(b["ref"].revision,a["ref"].revision+1)
        self.assertNotEqual(a["public"],b["public"])

    def test_membership_cycles_are_rejected_without_partial_changes(self):
        e=setup11();child=repair_group(e);root=group(e,"parent",members=(child["ref"],));before=e.world.head(child["ref"].identity)
        work(e,"cycle","link",focus=child["ref"],members=(root["ref"],),expect=False)
        self.assertEqual(e.world.head(child["ref"].identity),before)
        self.assertEqual(e.job_status(ALICE,"cycle")["status"],"failed")

    def test_finite_self_representation_does_not_create_a_membership_cycle(self):
        e=setup11();g=repair_group(e)
        r=ref("represented-system")
        v=ObjectVersion(r,WRITER,"Alice's representation of her group",(Role.CLAIM,),
            (Account(g["ref"],(),Moment(0,0),ALICE,(g["ref"],)),),occurrence=Occurrence.REMEMBERED_CLAIM)
        e.declare("representation",(v,))
        g=work(e,"link-representation","link",focus=g["ref"],members=(r,))[0]
        summary=work(e,"count","summarize",focus=g["ref"],scope="membership")[0]
        self.assertEqual(dict(summary["public"])["member_count"],2)
        self.assertEqual(e.world.resolve(r).facet(Account).referent.revision,1)

    def test_nested_graph_budget_is_a_real_failure(self):
        e=setup11();g=repair_group(e)
        for i in range(5):g=group(e,"level-"+str(i),members=(g["ref"],))
        work(e,"bounded","summarize",focus=g["ref"],limit=2,expect=False)
        self.assertEqual(e.job_status(ALICE,"bounded")["status"],"failed")
        self.assertGreater(e.job_status(ALICE,"bounded")["spent"],0)

    def test_direct_person_link_cannot_bypass_own_consent(self):
        e=setup11();g=repair_group(e)
        work(e,"forced","link",focus=g["ref"],members=(ObjectRef(BOB,1),),expect=False)
        self.assertNotIn(BOB,e.world.head(g["ref"].identity).facet(Composition).members)

    def test_irrelevant_member_revision_keeps_structural_summary_valid(self):
        e=setup11();g=repair_group(e)
        before=nesting.project(e.world,g["ref"].identity,"membership",128)
        old=e.world.head(ALICE)
        e.declare("unrelated-description",(next_version(old,label="Alice, revised description"),))
        self.assertIn(("u11.projection",g["ref"].identity,"membership"),e.world.cache.values)
        self.assertEqual(before,nesting.project(e.world,g["ref"].identity,"membership",128))

    def test_resource_inspection_obeys_its_declared_visit_budget(self):
        e=setup11();g=repair_group(e)
        work(e,"small-budget","summarize",focus=g["ref"],limit=3,expect=False)
        self.assertEqual(e.job_status(ALICE,"small-budget")["status"],"failed")

    def test_other_actor_cannot_accept_bobs_invitation(self):
        e=setup11();g=repair_group(e);inv=work(e,"invite","invite",focus=g["ref"],peer=BOB)[0]
        with self.assertRaises(ValueError):expose(e,EVE,inv["ref"])
        self.assertEqual(e._records11[inv["ref"]]["status"],"offered")

    def test_membership_does_not_transfer_material_ownership(self):
        e=setup11();g=repair_group(e);before=e.world.head(SHARED.identity)
        g=join(e,g)
        self.assertIn(BOB,e.world.head(g["ref"].identity).facet(Composition).members)
        self.assertEqual(e.world.head(SHARED.identity),before)
        self.assertTrue(audit(e.world.journal())["passed"])


class CollectiveWorkTests(unittest.TestCase):
    def test_nested_work_matches_explicit_leaf_program(self):
        nested,n=circuit11();detailed,d=circuit11(flat=True)
        for key in (SHARED,BOB_CARE,ref("u11-kit-alice"),ref("u11-repair-alice")):
            self.assertEqual(nested.world.head(key.identity),detailed.world.head(key.identity))
        def physical(e,run):
            return [(attrs(e.world.resolve(x))["actor"],attrs(e.world.resolve(x))["primitive"],
                     attrs(e.world.resolve(attrs(e.world.resolve(x))["operation"]))["spent"]) for x in run["events"]]
        self.assertEqual(physical(nested,n["run"]),physical(detailed,d["run"]))
        self.assertEqual(n["after"]["public"],d["after"]["public"])
        self.assertTrue(audit(nested.world.journal())["passed"])
        self.assertTrue(audit(detailed.world.journal())["passed"])

    def test_no_collective_step_without_all_assignees_accepting(self):
        e,g,p=team();run=instantiate(e,p,accept=False)
        for obj in (SHARED,e.world.head(ref("u11-kit-alice").identity).ref,e.world.head(ref("u11-repair-alice").identity).ref):expose(e,ALICE,obj)
        work(e,"select","select",focus=run["ref"],expect=False)
        self.assertEqual(e.world.head(SHARED.identity).ref,SHARED)

    def test_summary_alone_cannot_authorize_physical_detail(self):
        e,g,p=team();run=instantiate(e,p)
        s=work(e,"summary","summarize",focus=g["ref"])[0];expose(e,ALICE,s["ref"])
        # The shared tool was disclosed to name the group's resources, but Bob
        # still receives no per-tool detail through this aggregate payload.
        e2,g2,p2=team();run2=instantiate(e2,p2)
        run2=perform_step(e2,run2,"repair");run2=perform_step(e2,run2,"handoff")
        summary=work(e2,"bob-summary","summarize",actor=BOB,focus=g2["ref"])[0];expose(e2,BOB,summary["ref"])
        work(e2,"bob-select","select",actor=BOB,focus=run2["ref"],expect=False)
        self.assertEqual(e2.job_status(BOB,"bob-select")["status"],"failed")
        expose(e2,BOB,e2.world.head(SHARED.identity).ref)
        self.assertEqual(work(e2,"bob-resolved","select",actor=BOB,focus=run2["ref"])[0]["status"],"prepared")

    def test_unpracticed_member_cannot_accept_collective_work(self):
        e,g,p=team(train_bob=False);run=instantiate(e,p,accept=False)
        work(e,"bob-consent","accept",actor=BOB,focus=run["ref"],expect=False)
        self.assertEqual(e.job_status(BOB,"bob-consent")["status"],"failed")
        self.assertFalse(e.participant_view(BOB).can_use(ref("u11-primitive-use"),ROOM))

    def test_newcomer_still_needs_own_acquisition(self):
        e,result=circuit11();g=join(e,result["root"],EVE,"newcomer")
        for n in ("use","repair","care"):
            self.assertFalse(e.participant_view(EVE).can_use(ref("u11-primitive-"+n),ROOM))
        expose(e,EVE,result["capacity"]["ref"])
        self.assertEqual(result["capacity"]["owner"],g["ref"].identity)
        self.assertFalse(e.participant_view(EVE).can_use(result["capacity"]["ref"],ROOM))

    def test_newcomer_can_learn_separately_then_accept(self):
        e,g,p=team(train_bob=False)
        train(e,BOB,("use","care"))
        run=instantiate(e,p)
        self.assertIn((run["ref"].identity,BOB),e._duties11)
        self.assertTrue(e.participant_view(BOB).can_use(ref("u11-primitive-use"),ROOM))

    def test_premature_capacity_retention_is_rejected(self):
        e,g,p=team();run=instantiate(e,p)
        work(e,"premature","retain",focus=run["ref"],expect=False)
        self.assertFalse(any(x["kind"]=="capacity" for x in e._records11.values()))

    def test_departure_preserves_existing_duties_and_material_effects(self):
        e,g,p=team();run=perform_step(e,instantiate(e,p),"repair")
        material=e.world.head(SHARED.identity);duty=e.world.resolve(e._duties11[run["ref"].identity,BOB])
        g=work(e,"leave","leave",actor=BOB,focus=g["ref"])[0]
        self.assertNotIn(BOB,g["members"])
        self.assertEqual(e.world.resolve(duty.ref),duty)
        self.assertEqual(unpack(duty)["status"],"open")
        work(e,"stale-selection","select",focus=run["ref"],expect=False)
        self.assertEqual(e.world.head(SHARED.identity),material)
        self.assertTrue(audit(e.world.journal())["passed"])

    def test_withdrawal_stops_ready_effect_and_keeps_spent_work(self):
        e,g,p=team();run=instantiate(e,p);s,run=select(e,run)
        e.enact("enact",ALICE,"physical",s["ref"]);e.advance("pay",ALICE,"physical",1000)
        before=e.wallet(ALICE)["energy"]
        duty=e._duties11[run["ref"].identity,BOB]
        withdrawn=work(e,"withdraw","withdraw",actor=BOB,focus=duty)[0]
        event=e.commit("commit",ALICE,"physical")
        self.assertEqual(e.job_status(ALICE,"physical")["status"],"failed")
        self.assertEqual(e.wallet(ALICE)["energy"],before)
        self.assertEqual(e.world.head(SHARED.identity).ref,SHARED)
        self.assertFalse(withdrawn["permission_active"]);self.assertEqual(withdrawn["status"],"open")
        self.assertTrue(audit(e.world.journal())["passed"])

    def test_membership_change_blocks_an_already_paid_effect(self):
        e,g,p=team();run=instantiate(e,p);s,run=select(e,run)
        e.enact("enact",ALICE,"physical",s["ref"]);e.advance("pay",ALICE,"physical",1000)
        work(e,"leave","leave",actor=BOB,focus=g["ref"])
        e.commit("commit",ALICE,"physical")
        self.assertEqual(e.job_status(ALICE,"physical")["failure"],"stale_dependency")
        self.assertEqual(e.world.head(SHARED.identity).ref,SHARED)

    def test_a_selected_action_cannot_be_enacted_twice(self):
        e,g,p=team();s,run=select(e,instantiate(e,p))
        e.enact("enact",ALICE,"physical",s["ref"])
        with self.assertRaises(ValueError):e.enact("duplicate",ALICE,"other-physical",s["ref"])
        self.assertEqual(len(e._used11),1)

    def test_unread_physical_observation_does_not_advance_the_run(self):
        e,g,p=team();s,run=select(e,instantiate(e,p))
        e.enact("enact",ALICE,"physical",s["ref"]);e.advance("pay",ALICE,"physical",1000)
        event=e.commit("commit",ALICE,"physical");obs=e.deliver_event("delivered",event,ALICE)
        work(e,"unread","observe",focus=run["ref"],observation=obs,expect=False)
        self.assertEqual(e._heads11[run["ref"].identity],run["ref"])

    def test_cancelled_physical_work_is_not_successful_collective_work(self):
        e,g,p=team();s,run=select(e,instantiate(e,p))
        e.enact("enact",ALICE,"physical",s["ref"]);e.advance("pay",ALICE,"physical",2)
        event=e.cancel("cancel",ALICE,"physical");obs=receive(e,event,ALICE,"cancelled")
        failed=work(e,"record-cancel","observe",focus=run["ref"],observation=obs)[0]
        self.assertEqual(failed["status"],"failed");self.assertEqual(failed["index"],0)
        self.assertEqual(e.job_status(ALICE,"physical")["spent"],2)
        self.assertTrue(audit(e.world.journal())["passed"])

    def test_overlapping_groups_cannot_double_spend_one_tool(self):
        e,g,p=team();run=instantiate(e,p);s,run=select(e,run,"one")
        other=repair_group(e,"other");plan=proposed(e,other,(step(ALICE,"repair",target=SHARED,tool=ref("u11-kit-alice"),stock=ref("u11-repair-alice")),),"other-program")
        second=instantiate(e,plan,"other-run");s2,second=select(e,second,"two")
        e.enact("first",ALICE,"first-physical",s["ref"])
        e.enact("second",ALICE,"second-physical",s2["ref"])
        e.advance("waiting",ALICE,"second-physical",1000)
        self.assertEqual(e.job_status(ALICE,"second-physical")["spent"],0)
        e.advance("first-pay",ALICE,"first-physical",1000);e.commit("first-effect",ALICE,"first-physical")
        e.advance("second-pay",ALICE,"second-physical",1000);e.commit("second-effect",ALICE,"second-physical")
        self.assertEqual(e.job_status(ALICE,"second-physical")["status"],"failed")
        self.assertEqual(e.world.head(SHARED.identity).ref.revision,2)
        self.assertTrue(audit(e.world.journal())["passed"])


class IntegrityTests(unittest.TestCase):
    def test_u10_checkpoint_adoption_preserves_history_and_continued_language(self):
        from tests_u10.fixtures import setup10,work10,reveal10
        legacy=setup10(train_bob=False)
        adopted=CollectiveEngine.adopt(legacy)
        self.assertEqual(legacy.world.checkpoint(),adopted.world.checkpoint())
        self.assertEqual(legacy.access.checkpoint(),adopted.access.checkpoint())
        for engine in (legacy,adopted):
            slots=reveal10(engine,"bob-first",actor=ALICE)
            work10(engine,"continued-language","send",peer=BOB,act="statement",
                body=("test",("eq",("field","target","condition"),"damaged")),slots=slots)
        self.assertEqual(legacy.world.checkpoint(),adopted.world.checkpoint())
        self.assertEqual(legacy.access.checkpoint(),adopted.access.checkpoint())

    def test_partial_coordination_restores_and_continues_exactly(self):
        e=setup11();g=repair_group(e);expose(e,ALICE,g["ref"])
        r=CollectiveRequest("summary",ALICE,"summarize",ROOM,CUE5,focus=g["ref"])
        e.start("start",r);e.advance("partial",ALICE,"summary",7)
        checkpoint=e.checkpoint();other=CollectiveEngine.restore(checkpoint)
        self.assertEqual(other.checkpoint(),checkpoint)
        for engine in (e,other):
            engine.advance("rest",ALICE,"summary",100000);engine.commit("effect",ALICE,"summary")
        self.assertEqual(e.checkpoint(),other.checkpoint())

    def test_partial_physical_checkpoint_keeps_run_and_reservation(self):
        e,g,p=team();s,run=select(e,instantiate(e,p))
        e.enact("enact",ALICE,"physical",s["ref"]);e.advance("partial",ALICE,"physical",2)
        checkpoint=e.checkpoint();other=CollectiveEngine.restore(checkpoint)
        for engine in (e,other):
            engine.advance("rest",ALICE,"physical",1000);event=engine.commit("effect",ALICE,"physical")
            obs=receive(engine,event,ALICE,"received")
            work(engine,"settle","observe",focus=run["ref"],observation=obs)
        self.assertEqual(e.checkpoint(),other.checkpoint())

    def test_budget_exhaustion_never_installs_a_summary(self):
        e=setup11(budget=3000);g=repair_group(e);expose(e,ALICE,g["ref"])
        r=CollectiveRequest("unaffordable",ALICE,"summarize",ROOM,CUE5,focus=g["ref"],limit=100000)
        e.start("start",r);e.advance("exhaust",ALICE,"unaffordable",10000000)
        self.assertEqual(e.wallet(ALICE)["energy"],0)
        self.assertEqual(e.job_status(ALICE,"unaffordable")["status"],"partial")
        with self.assertRaises(ValueError):e.commit("premature",ALICE,"unaffordable")
        self.assertFalse(any(x["kind"]=="summary" for x in e._records11.values()))

    def test_cancelling_coordination_preserves_spent_work(self):
        e=setup11();g=repair_group(e);expose(e,ALICE,g["ref"])
        e.start("start",CollectiveRequest("cancel",ALICE,"summarize",ROOM,CUE5,focus=g["ref"]))
        e.advance("pay",ALICE,"cancel",11);before=e.wallet(ALICE)["energy"]
        e.cancel("cancel",ALICE,"cancel")
        self.assertEqual(e.wallet(ALICE)["energy"],before)
        self.assertEqual(e.job_status(ALICE,"cancel")["spent"],11)
        self.assertTrue(audit(e.world.journal())["passed"])

    def test_receiving_new_evidence_invalidates_partial_processing(self):
        e=setup11();g=repair_group(e);expose(e,ALICE,g["ref"])
        e.start("start",CollectiveRequest("pending",ALICE,"summarize",ROOM,CUE5,focus=g["ref"]))
        e.advance("pay",ALICE,"pending",7);expose(e,ALICE,BOB_CARE)
        e.advance("rest",ALICE,"pending",100000);e.commit("commit",ALICE,"pending")
        self.assertEqual(e.job_status(ALICE,"pending")["failure"],"received_evidence_changed")

    def test_source_route_is_lawful_for_all_sixteen_types(self):
        from hle.model_a import TYPES
        costs=set()
        for tim in TYPES:
            with self.subTest(tim=tim):
                e=setup11(tim=tim,train_bob=False);g=repair_group(e)
                self.assertTrue(audit(e.world.journal())["passed"])
                costs.add(e.job_status(ALICE,"repair-group")["route_execute"])
                self.assertEqual(g["members"],(ALICE,))
        self.assertGreater(len(costs),1)

    def test_raw_auditor_rejects_forged_summary_values(self):
        e=setup11();g=repair_group(e);summary=work(e,"summary","summarize",focus=g["ref"])[0]
        rows=list(e.world.journal())
        for i,tx in enumerate(rows):
            for value in tx.versions:
                if value.ref==summary["ref"]:
                    d=dict(summary);d["public"]=(('resource_count',999),)
                    rows[i]=replace(tx,versions=tuple(e._value11(d) if v.ref==value.ref else v for v in tx.versions))
        with self.assertRaises(ValueError):audit(tuple(rows))

    def test_restore_rejects_modified_final_state(self):
        from hle_unified.compact import seal,unseal
        e=setup11();g=repair_group(e)
        data=unseal(e.checkpoint(),e.SCHEMA);data["access"]="altered"
        with self.assertRaises(ValueError):CollectiveEngine.restore(seal(e.SCHEMA,data))

    def test_external_declaration_cannot_mint_collective_capacity(self):
        e=setup11()
        forged=record(address("u11.capacity","forged"),"Forged capacity",{"status":"retained"})
        with self.assertRaises(ValueError):e.declare("forge",(forged,))

    def test_repeat_command_is_idempotent_but_changed_content_is_rejected(self):
        e=setup11();g=repair_group(e);expose(e,ALICE,g["ref"])
        r=CollectiveRequest("summary",ALICE,"summarize",ROOM,CUE5,focus=g["ref"])
        first=e.start("start",r);count=len(e.world.journal())
        self.assertEqual(e.start("start",r),first);self.assertEqual(len(e.world.journal()),count)
        with self.assertRaises(ValueError):e.start("start",replace(r,scope="membership"))


if __name__=="__main__":unittest.main()
