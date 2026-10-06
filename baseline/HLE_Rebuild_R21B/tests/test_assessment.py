from dataclasses import replace
from itertools import product
import unittest
from hle.assessment import AssessedWorld
from hle.assessment_demo import (begin, declare, detector_case, drain, end,
    execute_offer, false_account_fixture, run_assessment_demo, world)
from hle.assessment_records import (AssessPending, BeginTrial, CarrierUse,
    DeclareStudy, EndTrial, MaterialCommand, MaterialState, StudyReport)
from hle.codec import dumps, loads
from hle.contracts import (ClaimStatus, Dimension, EvidenceStatus as E, Kind,
    IdeaPhase, Moment, Ref, TimeScope, WorkStatus)
from hle.crux import Perspective
from hle.demo import ALICE, BOB, BOX, TOOL, ROOM, request
from hle.idea import FiniteIDEA, FiniteProtocol
from hle.memory_records import MemoryCommand, WriteDraft
from hle.metabolism_demo import (CUE, LESSON, associate, finish, remember_initial, retrieve)
from hle.metabolism_records import (APPLY, EMBODY, THEORIZE, UNDERSTAND, ApplyDraft,
    EmbodyDraft, MetabolicCommand, TheorizeDraft, UnderstandDraft)
from hle.processing import select_action
from hle.world_records import Attempt, Correction, Credit, INSPECT, Tick, TRANSFER
from .reference_assessment import complete_report
from .reference_memory import NoWalkDict, NoWalkList
from .reference_world import fold
from .support import rules


def assert_reference(test, w, report):
    expected=complete_report(w.config,w.truth.journal(),w._studies[report.study],report.at,w.profiles)
    test.assertEqual(tuple(r.status for r in report.results),expected["statuses"])
    test.assertEqual(report.closure,expected["closure"])
    for key in ("shell","adjudicable","contradicted","unresolved","delivered","retained"):
        test.assertEqual(getattr(report,key),expected[key],key)
    a=w.truth.resolve(report.aggregate)
    test.assertEqual((a.trials,a.blocked_run,a.reconstruction_run,a.candidate_seen,a.corrected_run,a.capacity_items),expected["aggregate"])


class IdeaAndError(unittest.TestCase):
    @rules("S01")
    def test_failed_return_remains_in_broader_claim_after_later_success(self):
        from hle.cards import card
        w=world();original=remember_initial(w);s=declare(w,operations=(THEORIZE,UNDERSTAND))
        wrong=replace(original.content[0],object=BOB)
        w.execute(MemoryCommand("different","different",BOB,WriteDraft("different",(wrong,),(),ClaimStatus.ENDORSED,None,"deliberately different identity"),(original.ref,)))
        associate(w,w.memory_head(BOB,"different"),"different-cue",card("arcana:5").ref)
        for index in range(2):
            rr=retrieve(w,f"r:{index}",(card("arcana:5").ref,))
            t,o=begin(w,s,f"return:{index}",TheorizeDraft(rr,BOX,ALICE));a=execute_offer(w,o)
            old=w.memory_head(BOB,"box")
            finish(w,UnderstandDraft(a.result,"box",old.ref),f"understand:{index}")
            result=end(w,t)
            self.assertEqual(result.identity,E.FAILED if index==0 else E.ESTABLISHED)
        drain(w);r=w.report(s.ref)
        self.assertEqual(r.results[1].status,E.ESTABLISHED)
        self.assertEqual(r.closure,E.FAILED)
        assert_reference(self,w,r)
    @rules("S01")
    def test_phase_grid_preserves_unsupported_we_and_unproved_alignment(self):
        w,_=run_assessment_demo();r=w.report(Ref(Kind.ASSESSMENT,"study",1))
        self.assertEqual(len(r.phases),16)
        self.assertTrue(all(p.status==E.UNASSESSED for p in r.phases if p.cell.perspective==Perspective.WE))
        self.assertTrue(all(p.status==E.UNASSESSED for p in r.phases if p.cell.phase==IdeaPhase.ALIGN))
        self.assertTrue(all(p.status==E.ESTABLISHED for p in r.phases if p.cell.phase==IdeaPhase.INITIATE and p.cell.perspective!=Perspective.WE))

    @rules("S01")
    def test_failed_or_missing_contrast_propagates_without_redefining_identity(self):
        w=world();remember_initial(w);s=declare(w)
        unequal=s.contrasts[0]
        spec=replace(s.spec,ref=Ref(Kind.ASSESSMENT,"no-contrast",1),declared_at=w.now)
        other=replace(s,spec=spec,contrasts=(replace(unequal,right=unequal.left),))
        w.execute(DeclareStudy("no-contrast",other));drain(w)
        r=w.report(other.ref)
        self.assertTrue(all(p.status==E.FAILED for p in r.phases if p.cell.perspective==Perspective.I))
        self.assertTrue(all(p.status==E.UNASSESSED for p in r.phases if p.cell.perspective!=Perspective.I))

    @rules("S01")
    def test_a13_canon_single_return_passes_repeat_fails(self):
        model=FiniteIDEA((0,0,1),(FiniteProtocol("h",(1,2,2),(0,1,2)),))
        self.assertEqual(model.sequence(0,(0,))[0],E.ESTABLISHED)
        self.assertEqual(model.sequence(0,(0,0)),(E.FAILED,(0,1,2)))
        self.assertEqual(model.closure(0),E.UNASSESSED)

    @rules("S01")
    def test_equivalence_preserving_finite_model_closes_only_declared_domain(self):
        model=FiniteIDEA((0,0,1),(FiniteProtocol("swap",(1,0,2),(0,1,2)),))
        self.assertEqual(model.closure(0),E.ESTABLISHED)
        for n in range(7):self.assertEqual(model.sequence(0,(0,)*n)[0],E.ESTABLISHED)

    @rules("S01")
    def test_partial_protocol_and_unengaged_domain_unassessed(self):
        model=FiniteIDEA((0,1),(FiniteProtocol("partial",(None,1),(0,1)),),eligible=(0,))
        self.assertEqual(model.sequence(0,(0,))[0],E.UNASSESSED)
        self.assertEqual(model.sequence(1,(0,))[0],E.UNASSESSED)
        self.assertEqual(model.closure(0),E.UNASSESSED)

    @rules("S01")
    def test_malformed_and_duplicate_finite_protocols_reject(self):
        with self.assertRaises(ValueError):FiniteIDEA((0,1),(FiniteProtocol("bad",(0,2),(0,1)),))
        p=FiniteProtocol("same",(0,1),(0,1))
        with self.assertRaises(ValueError):FiniteIDEA((0,1),(p,p))

    @rules("S01","S02")
    def test_missing_engagement_is_unassessed_not_pass(self):
        w=world();remember_initial(w);s=declare(w);drain(w)
        r=w.report(s.ref)
        self.assertEqual([x.status for x in r.results],[E.ESTABLISHED,E.UNASSESSED,E.UNASSESSED,E.UNASSESSED])
        self.assertEqual(r.closure,E.UNASSESSED)

    @rules("S02")
    def test_a04_actor_substitution_is_not_hidden_by_same_graph_shape(self):
        w=world();m=remember_initial(w)
        w.execute(MemoryCommand("wrong","wrong",BOB,WriteDraft("box",(replace(m.content[0],object=BOB),),(),ClaimStatus.ENDORSED,m.ref,"same edge, wrong actor"),(m.ref,)))
        s=declare(w);drain(w);r=w.report(s.ref)
        self.assertEqual((r.adjudicable,r.contradicted,r.unresolved),(1,1,0))
        self.assertEqual(r.results[0].status,E.FAILED)

    @rules("S02")
    def test_a05_empty_memory_is_ignorance_and_zero_denominator_unassessed(self):
        w=world();s=declare(w);rr=retrieve(w,"empty")
        t,o=begin(w,s,"empty",TheorizeDraft(rr,BOX,ALICE))
        end(w,t);drain(w);r=w.report(s.ref)
        self.assertEqual((r.adjudicable,r.contradicted,r.retained),(0,0,0))
        self.assertEqual(r.results[0].status,E.UNASSESSED)
        self.assertEqual(r.shell,"ignorance")

    @rules("S02","S05")
    def test_repeated_demand_with_missing_information_is_not_a_shell(self):
        w=world();s=declare(w);rr=retrieve(w,"empty")
        for i in range(3):
            t,o=begin(w,s,f"ignorance:{i}",TheorizeDraft(rr,BOX,ALICE));end(w,t)
        drain(w)
        self.assertEqual(w.report(s.ref).shell,"ignorance")
        self.assertFalse(w._aggregates[s.ref].candidate_seen)

    @rules("S02")
    def test_wrong_context_and_expired_scope_stay_unresolved(self):
        w=world();m=remember_initial(w)
        # An inaccessible context cannot enter memory. Expired known content can.
        p=replace(m.content[0],scope=TimeScope(Moment(0,0),Moment(1,0)))
        w.execute(MemoryCommand("expired","expired",BOB,WriteDraft("box",(p,),(),ClaimStatus.ENDORSED,m.ref,"time-bound fact"),(m.ref,)))
        s=declare(w);drain(w);r=w.report(s.ref)
        self.assertEqual((r.unresolved,r.adjudicable),(1,0))
        self.assertEqual(r.results[0].status,E.UNASSESSED)

    @rules("S01","S02")
    def test_a07_stable_false_account_returns_identity_without_becoming_true(self):
        w=world();old=remember_initial(w)
        s=declare(w,operations=(THEORIZE,UNDERSTAND))
        w.execute(Attempt("hidden","hidden",request(ALICE,TRANSFER,(BOX,BOB))))
        r=retrieve(w,"r")
        t,o=begin(w,s,"false",TheorizeDraft(r,BOX,ALICE))
        a=execute_offer(w,o)
        finish(w,UnderstandDraft(a.result,"box",old.ref),"return")
        result=end(w,t);drain(w);report=w.report(s.ref)
        self.assertEqual(result.identity,E.ESTABLISHED)
        self.assertEqual(report.results[0].status,E.FAILED)
        self.assertEqual(report.shell,"no_persistent_candidate")
        self.assertEqual(report.delivered,0)
        assert_reference(self,w,report)

    @rules("S01")
    def test_study_features_and_protocols_cannot_be_changed_in_place(self):
        w=world();remember_initial(w);s=declare(w);before=w.checkpoint()
        with self.assertRaises(ValueError):w.execute(DeclareStudy("overwrite",replace(s,max_units=1)))
        self.assertEqual(before,w.checkpoint())
        with self.assertRaises(ValueError):replace(s,spec=replace(s.spec,identity_features=("constant",)))

    @rules("S01")
    def test_wrong_or_incomplete_sequence_does_not_establish_return(self):
        w=world();remember_initial(w);s=declare(w)
        rr=retrieve(w,"r");t,o=begin(w,s,"incomplete",TheorizeDraft(rr,BOX,ALICE))
        execute_offer(w,o);result=end(w,t)
        self.assertEqual(result.identity,E.UNASSESSED)


class DemandPathAndRetention(unittest.TestCase):
    @rules("S03")
    def test_a06_energy_and_time_limit_do_not_become_foreclosure(self):
        for resource in ("energy","time"):
            w=world(energy=100,time=100);old,a,ob=false_account_fixture(w)
            s=declare(w,operations=(APPLY,EMBODY),fixture=True)
            # Pay until both reach zero, then independently restore just one.
            for i in range(w.truth.wallet(BOB).energy):
                w.execute(Attempt(f"pay:{i}",f"pay:{i}",request(BOB,INSPECT,(BOX,))))
            w.execute(Credit("one-resource",BOB,0 if resource=="energy" else 100,0 if resource=="time" else 100,"controlled resource intervention"))
            for i in range(2):
                t,o=begin(w,s,f"limited:{i}",ApplyDraft(a.ref),corrective=(ob.ref,));end(w,t)
            execute_offer(w,o)
            drain(w);r=w.report(s.ref)
            self.assertEqual(r.shell,"resource_limited")
            self.assertEqual(r.results[1].status,E.UNASSESSED)
            self.assertFalse(w._aggregates[s.ref].candidate_seen)

    @rules("S03","S05")
    def test_unavailable_movement_and_single_opportunity_cannot_establish_foreclosure(self):
        w=world();m=remember_initial(w);s=declare(w)
        # Apply lacks an account and is unavailable from I; a fake ref is rejected by quote.
        t,o=begin(w,s,"unavailable",ApplyDraft(Ref(Kind.EVIDENCE,"missing-account",1)))
        end(w,t);drain(w)
        self.assertEqual(w.report(s.ref).shell,"opportunity_unassessed")
        self.assertFalse(w._aggregates[s.ref].candidate_seen)

    @rules("S03")
    def test_opportunity_quotes_match_independent_model_a_route_oracle(self):
        from hle.model_a import TYPES
        from .reference_processing import route_oracle
        for tim in TYPES:
            w=world(tim=tim);old,a,ob=false_account_fixture(w)
            s=declare(w,operations=(APPLY,EMBODY))
            state=w.processing_state(BOB)
            t,o=begin(w,s,"quote",ApplyDraft(a.ref),corrective=(ob.ref,))
            path,positions,seat,at,hops,content=route_oracle(tim,state.active,"te",True,1+len(a.evidence),True,True)
            self.assertEqual(w._starts[t].opportunity.required,sum(hops)+content+3)

    @rules("S03")
    def test_resource_replenishment_changes_new_opportunity_and_resumes_work(self):
        w,s=detector_case("foreclosure",energy=0)
        self.assertEqual(w.report(s.ref).shell,"resource_limited")
        a=next(r for r in w._records.values() if type(r).__name__=="Account")
        w.execute(Credit("fund",BOB,200,200,"external resource supply"))
        t,o=begin(w,s,"funded",ApplyDraft(a.ref));job=execute_offer(w,o)
        self.assertEqual(job.outcome,WorkStatus.COMPLETED)
        old=w.memory_head(BOB,"box")
        finish(w,EmbodyDraft(job.result,"box",old.ref),"funded-return")
        end(w,t);drain(w,"reassess")
        self.assertEqual(w.report(s.ref).shell,"no_persistent_candidate")

    @rules("S04")
    def test_a08_correct_endpoint_keeps_discrepancy_and_paid_path_failure(self):
        w,summary=run_assessment_demo()
        self.assertEqual(summary["initial_identity_return"],"established")
        self.assertEqual(summary["initial_path"],"failed")
        self.assertTrue(summary["initial_discrepancy"])
        first=w._trial_results[Ref(Kind.DEMAND,"trial:learn",2)]
        self.assertGreater(first.units,0)
        self.assertIn("perspective",first.cancellation)
        self.assertTrue(first.recurrence)

    @rules("S04")
    def test_predeclared_path_budget_cannot_be_erased_by_return(self):
        w=world();old=remember_initial(w);s=declare(w,operations=(THEORIZE,UNDERSTAND),max_units=1)
        rr=retrieve(w,"r");t,o=begin(w,s,"budget",TheorizeDraft(rr,BOX,ALICE));a=execute_offer(w,o)
        finish(w,UnderstandDraft(a.result,"box",old.ref),"return")
        result=end(w,t)
        self.assertEqual((result.identity,result.path),(E.ESTABLISHED,E.FAILED))

    @rules("S03","S05")
    def test_a09_matched_quiet_trajectories_need_demand_to_imply_foreclosure(self):
        rest,sr=detector_case("rest");blocked,sb=detector_case("foreclosure")
        self.assertEqual(rest.report(sr.ref).shell,"rest_or_stable_error")
        self.assertEqual(blocked.report(sb.ref).shell,"foreclosure_candidate")
        self.assertEqual(rest.truth.wallet(BOB),blocked.truth.wallet(BOB))
        self.assertEqual(rest.processing_state(BOB),blocked.processing_state(BOB))
        self.assertTrue(all(not r.visibility for r in blocked._trial_results.values()))

    @rules("S05")
    def test_compensation_needs_recurring_actual_reconstruction_and_counterevidence(self):
        w,s=detector_case("compensation")
        r=w.report(s.ref)
        self.assertEqual(r.shell,"compensation_candidate")
        self.assertEqual(r.provenance,"injected_detector_fixture")
        self.assertTrue(all(t.reconstruction and t.units>0 for t in w._trial_results.values()))
        self.assertEqual(r.results[2].status,E.FAILED)
        assert_reference(self,w,r)

    @rules("S05")
    def test_delivery_without_interpretability_does_not_establish_compensation(self):
        w=world();old,a,ob=false_account_fixture(w);s=declare(w,fixture=True,operations=(APPLY,EMBODY))
        # Omit direct corrective evidence from the declared opportunity.
        for i in range(2):
            t,o=begin(w,s,f"no-evidence:{i}",ApplyDraft(a.ref))
            head=w.memory_head(BOB,"box")
            w.execute(MemoryCommand(f"rewrite:{i}",f"rewrite:{i}",BOB,
                WriteDraft("box",old.content,(),ClaimStatus.ENDORSED,head.ref,"controlled repetition"),(head.ref,)))
            end(w,t)
        drain(w)
        self.assertNotEqual(w.report(s.ref).shell,"compensation_candidate")
        self.assertEqual(w._aggregates[s.ref].reconstruction_run,0)

    @rules("S05")
    def test_quiet_interval_does_not_clear_a_previous_candidate(self):
        w,s=detector_case("foreclosure")
        t,o=begin(w,s,"rest-after",demanded=False);w.execute(Tick("quiet-after"));end(w,t);drain(w,"again")
        self.assertEqual(w.report(s.ref).shell,"candidate_unresolved")

    @rules("S06")
    def test_a10_capacity_requires_use_on_original_and_heldout_object(self):
        w,summary=run_assessment_demo()
        self.assertEqual(summary["retained_capacity"],"established")
        self.assertEqual(summary["capacity_items"],["box","tool"])
        for r in w._reports.values():assert_reference(self,w,r)

    @rules("S06")
    def test_retained_label_without_renewed_action_stays_unassessed(self):
        from .test_metabolism import learn
        w=world();learn(w);s=declare(w,features=("capacity_rules",));drain(w)
        self.assertTrue(w.memory_head(BOB,"box").capabilities)
        self.assertEqual(w.report(s.ref).results[3].status,E.UNASSESSED)

    @rules("S05","S06")
    def test_candidate_clearance_requires_renewed_correction_and_transfer(self):
        from hle.assessment_demo import clearance_case
        w,s,labels=clearance_case()
        self.assertEqual(labels,["foreclosure_candidate","candidate_unresolved","candidate_unresolved","cleared_in_tested_demands"])
        self.assertEqual(w.report(s.ref).results[3].status,E.ESTABLISHED)
        assert_reference(self,w,w.report(s.ref))

    @rules("S06")
    def test_same_and_heldout_demand_have_matched_capacity_ablations(self):
        from hle.assessment_demo import capacity_controls
        rows=capacity_controls()
        for item in (BOX.key,TOOL.key):
            off,on=[r for r in rows if r["item"]==item]
            self.assertEqual(off["resources_before_recall"],on["resources_before_recall"])
            self.assertEqual(off["prediction"],on["prediction"])
            self.assertEqual((off["first_action"],on["first_action"]),(TRANSFER.key,INSPECT.key))
            self.assertEqual((off["outcome"],on["outcome"]),("failed","completed"))


class MaterialAndIsolation(unittest.TestCase):
    def material_fixture(self):
        w=world();old,a,ob=false_account_fixture(w)
        w.execute(MaterialCommand("generate",BOB,"intent","generate",a.ref))
        m=w._material_heads["3:bob:1:intent"]
        w.execute(MaterialCommand("externalize",BOB,"intent","externalize",m.ref))
        return w,w._material_heads["3:bob:1:intent"]

    @rules("S07")
    def test_a11_complete_material_carrier_action_consequence_reownership_chain(self):
        w,m=self.material_fixture();self.assertEqual(m.carrier,ALICE)
        before=len(w.select_input(ALICE)[0].observations)
        event=w.execute(MaterialCommand("express",BOB,"intent","express",m.ref))
        tx=w._journal[event.when.tick];use=tx.extra[0]
        self.assertEqual(use.material,m.ref);self.assertEqual(use.carrier,ALICE)
        message=w.truth.resolve(use.message)
        self.assertEqual((message.sender,message.receiver),(BOB,ALICE))
        self.assertIn(m.ref,message.based_on)
        self.assertGreater(len(w.select_input(ALICE)[0].observations),before)
        w.execute(MaterialCommand("reown",BOB,"intent","reown",m.ref))
        owned=w._material_heads["3:bob:1:intent"]
        self.assertEqual(owned.previous,m.ref)
        reloaded=AssessedWorld.restore(w.checkpoint())
        for target in (w,reloaded):
            target.execute(MaterialCommand("renewed-expression",BOB,"intent","express",owned.ref))
            self.assertEqual(target._journal[-1].extra[0].outcome,"withheld_after_reownership")
            self.assertFalse(target._journal[-1].messages)
        self.assertEqual(w.checkpoint(),reloaded.checkpoint())

    @rules("S07")
    def test_ordinary_false_ownership_account_is_not_projection_evidence(self):
        w=world();false_account_fixture(w)
        self.assertFalse(w._material_heads)
        self.assertFalse(any(type(r) is CarrierUse for r in w._records.values()))

    @rules("S07")
    def test_external_attribution_fails_path_despite_unchanged_memory(self):
        w,m=self.material_fixture();s=declare(w,fixture=True,operations=(APPLY,EMBODY))
        t,_=begin(w,s,"carrier")
        w.execute(MaterialCommand("express",BOB,"intent","express",m.ref))
        result=end(w,t)
        self.assertTrue(result.externalized_action);self.assertEqual(result.path,E.FAILED)
        self.assertFalse(result.reconstruction)

    @rules("S07")
    def test_foreign_and_stale_material_operations_reject_atomically(self):
        w,m=self.material_fixture();before=w.checkpoint()
        for cmd in (MaterialCommand("foreign",ALICE,"intent","express",m.ref),
                    MaterialCommand("stale",BOB,"intent","reown",m.previous)):
            with self.assertRaises(ValueError):w.execute(cmd)
            self.assertEqual(w.checkpoint(),before)

    @rules("S07")
    def test_zero_resource_material_operation_defers_without_output(self):
        w,m=self.material_fixture()
        for i in range(w.truth.wallet(BOB).energy):
            w.execute(Attempt(f"pay:{i}",f"pay:{i}",request(BOB,INSPECT,(BOX,))))
        w.execute(MaterialCommand("deferred",BOB,"intent","reown",m.ref))
        self.assertEqual(w._journal[-1].event.outcome,WorkStatus.DEFERRED)
        self.assertEqual(w._material_heads["3:bob:1:intent"],m)
        self.assertFalse(w._journal[-1].extra)

    @rules("S02","S08")
    def test_a03_assessments_do_not_enter_participant_inputs_or_action_selection(self):
        w=world();m=remember_initial(w);rr=retrieve(w,"r")
        a=finish(w,TheorizeDraft(rr,BOX,ALICE),"think")
        account=w.processing_record(BOB,a.result);action=select_action(account)
        before=w.select_input(BOB)[0];balance=w.truth.wallet(BOB)
        s=declare(w);drain(w)
        after=w.select_input(BOB)[0]
        self.assertEqual(before.observations,after.observations)
        self.assertEqual(balance,w.truth.wallet(BOB))
        self.assertEqual(action,select_action(w.processing_record(BOB,a.result)))
        self.assertNotIn(w.report(s.ref).ref,w._known[BOB])
        with self.assertRaises(ValueError):w.processing_record(BOB,w.report(s.ref).ref)


class ContinuationAndScheduling(unittest.TestCase):
    @rules("S09")
    def test_all_r5_tests_reference_registered_rules(self):
        import json
        from pathlib import Path
        ids={r["id"] for r in json.loads((Path(__file__).resolve().parents[1]/"docs/rules.json").read_text())["rules"]}
        for cls in (IdeaAndError,DemandPathAndRetention,MaterialAndIsolation,ContinuationAndScheduling):
            for name in unittest.defaultTestLoader.getTestCaseNames(cls):
                tags=getattr(getattr(cls,name),"rule_ids",())
                self.assertTrue(tags);self.assertTrue(set(tags)<=ids)
    @rules("S08","S09")
    def test_a14_every_integrated_prefix_continues_exactly(self):
        final,_=run_assessment_demo();journal=final.truth.journal()
        live=AssessedWorld(final.config,final.profiles,final.policy)
        for index in range(len(journal)):
            if index:live.execute(journal[index].command)
            resumed=AssessedWorld.restore(live.checkpoint())
            self.assertEqual(resumed.pending_assessments(),live.pending_assessments())
            for tx in journal[index+1:]:resumed.execute(tx.command)
            self.assertEqual(resumed.checkpoint(),final.checkpoint())

    @rules("S08")
    def test_partial_assessment_queue_and_partial_processing_survive_reload(self):
        w=world();remember_initial(w)
        studies=[declare(w,f"study:{i}") for i in range(3)]
        rr=retrieve(w,"r")
        w.execute(MetabolicCommand("partial","partial",BOB,TheorizeDraft(rr,BOX,ALICE),1))
        w.execute(AssessPending("one",1))
        resumed=AssessedWorld.restore(w.checkpoint())
        self.assertEqual(len(resumed.pending_assessments()),2)
        for target in (w,resumed):
            target.execute(MetabolicCommand("resume","partial",BOB,TheorizeDraft(rr,BOX,ALICE),64))
            drain(target,"finish-queue",1)
        self.assertEqual(w.checkpoint(),resumed.checkpoint())

    @rules("S08")
    def test_rehashed_report_and_opportunity_tampering_rejects(self):
        w,_=run_assessment_demo();cp=loads(w.checkpoint())
        index=next(i for i,t in enumerate(cp.journal) if any(type(r) is StudyReport for r in getattr(t,"extra",())))
        tx=cp.journal[index]
        bad=replace(tx,extra=tuple(replace(r,shell="invented_pass") if type(r) is StudyReport else r for r in tx.extra))
        with self.assertRaises(ValueError):AssessedWorld.restore(dumps(replace(cp,journal=cp.journal[:index]+(bad,)+cp.journal[index+1:])))
        index=next(i for i,t in enumerate(cp.journal) if type(t.command) is BeginTrial)
        tx=cp.journal[index];start=tx.extra[0]
        bad=replace(tx,extra=(replace(start,opportunity=replace(start.opportunity,required=0)),))
        with self.assertRaises(ValueError):AssessedWorld.restore(dumps(replace(cp,journal=cp.journal[:index]+(bad,)+cp.journal[index+1:])))

    @rules("S08")
    def test_idempotent_evaluation_and_close_do_not_duplicate_cost_or_trials(self):
        w=world();remember_initial(w);s=declare(w)
        cmd=AssessPending("once",1);w.execute(cmd);before=w.checkpoint();w.execute(cmd)
        self.assertEqual(w.checkpoint(),before)
        with self.assertRaises(ValueError):w.execute(replace(cmd,limit=2))

    @rules("S09")
    def test_a15_reports_match_independent_full_comparison_at_every_update(self):
        final,_=run_assessment_demo()
        w=AssessedWorld(final.config,final.profiles,final.policy)
        for i,tx in enumerate(final.truth.journal()):
            if i:w.execute(tx.command)
            self.assertEqual(w.state(),fold(w.config,w.truth.journal()))
            for study in w._studies.values():
                assert_reference(self,w,w._make_report(study))
            for report in (r for r in getattr(tx,"extra",()) if type(r) is StudyReport):
                assert_reference(self,w,report)
        for mode in ("rest","foreclosure","compensation"):
            w,s=detector_case(mode);assert_reference(self,w,w.report(s.ref))

    @rules("S09")
    def test_inactive_ticks_do_not_schedule_unchanged_assessments(self):
        w=world();remember_initial(w);s=declare(w);drain(w)
        for i in range(1000):w.execute(Tick(f"idle:{i}"))
        self.assertEqual(w.pending_assessments(),())
        self.assertEqual(w.assessment_visits,1)
        self.assertTrue(w.report_is_current(w.report(s.ref)))

    @rules("S09")
    def test_active_assessment_avoids_global_history_and_unrelated_records(self):
        w=world();remember_initial(w);s=declare(w);drain(w)
        for i in range(200):w.execute(Tick(f"idle:{i}"))
        w._journal=NoWalkList(w._journal);w._records=NoWalkDict(w._records)
        w._studies=NoWalkDict(w._studies);w._origins=NoWalkDict(w._origins)
        w._memory_heads[BOB]=NoWalkDict(w._memory_heads[BOB])
        w.execute(Attempt("change","change",request(ALICE,TRANSFER,(BOX,BOB))))
        self.assertEqual(w.pending_assessments(),(s.ref,));drain(w,"changed")
        self.assertEqual(w.report(s.ref).results[0].status,E.FAILED)

    @rules("S09")
    def test_clock_expiry_invalidates_only_when_scope_boundary_is_crossed(self):
        w=world();m=remember_initial(w)
        p=replace(m.content[0],scope=TimeScope(Moment(0,0),Moment(20,0)))
        w.execute(MemoryCommand("bounded","bounded",BOB,WriteDraft("box",(p,),(),ClaimStatus.ENDORSED,m.ref,"bounded assertion"),(m.ref,)))
        s=declare(w);drain(w)
        for i in range(20-w.now.tick):w.execute(Tick(f"clock:{i}"))
        self.assertIn(s.ref,w.pending_assessments());drain(w,"expired")
        self.assertEqual(w.report(s.ref).results[0].status,E.UNASSESSED)

    @rules("S09")
    def test_world_correction_invalidates_truth_without_rewriting_old_report(self):
        w=world();remember_initial(w);s=declare(w)
        transfer=w.execute(Attempt("transfer","transfer",request(ALICE,TRANSFER,(BOX,BOB))))
        drain(w);old=w.report(s.ref);self.assertEqual(old.results[0].status,E.FAILED)
        w.execute(Correction("correction",transfer.ref,ALICE,"explicit prospective correction"))
        self.assertFalse(w.report_is_current(old));drain(w,"correction-assess")
        self.assertEqual(w.report(s.ref).results[0].status,E.ESTABLISHED)
        self.assertEqual(w.truth.resolve(old.ref),old)
        self.assertEqual(old.results[0].status,E.FAILED)

    @rules("S09")
    def test_no_fabricated_assessor_claims_or_hardcoded_test_outcome(self):
        # Perturb factual owner and demand independently; dynamic references drive results.
        for actual_bob,demanded in product((False,True),repeat=2):
            w=world();remember_initial(w);s=declare(w)
            if actual_bob:w.execute(Attempt("transfer","transfer",request(ALICE,TRANSFER,(BOX,BOB))))
            rr=retrieve(w,"r");t,o=begin(w,s,"case",TheorizeDraft(rr,BOX,ALICE),demanded)
            end(w,t);drain(w)
            self.assertEqual(w.report(s.ref).results[0].status,E.FAILED if actual_bob else E.ESTABLISHED)
            self.assertFalse(w._aggregates[s.ref].candidate_seen)
