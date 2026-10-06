#!/usr/bin/env python3
"""Reproduce R5 integrated evidence, explicit detector controls and scoped costs."""
import argparse
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from hle.assessment import AssessedWorld
from hle.assessment_demo import (begin,capacity_controls,clearance_case,declare,
    detector_case,drain,end,false_account_fixture,run_assessment_demo,world)
from hle.assessment_records import DeclareStudy,MaterialCommand
from hle.codec import encode
from hle.contracts import Kind,Ref
from hle.demo import ALICE,BOB,BOX,TOOL,request
from hle.metabolism_demo import remember_initial
from hle.world_records import Attempt,INSPECT,Tick
from tests.reference_assessment import complete_report


def write(path,value):path.write_text(json.dumps(value,indent=2)+"\n")


def save_case(folder,name,w,summary):
    path=folder/name;path.mkdir(parents=True,exist_ok=True)
    (path/"checkpoint.json").write_text(w.checkpoint())
    write(path/"summary.json",summary)
    write(path/"reports.json",[encode(r) for r in w._reports.values()])
    write(path/"trials.json",[encode(r) for r in w._trial_results.values()])
    with (path/"events.jsonl").open("w") as f:
        for tx in w.truth.journal():f.write(json.dumps(encode(tx),sort_keys=True)+"\n")
    assert AssessedWorld.restore(w.checkpoint()).checkpoint()==w.checkpoint()


def projection_case():
    w=world();old,a,ob=false_account_fixture(w);s=declare(w,fixture=True)
    t,_=begin(w,s,"projection")
    w.execute(MaterialCommand("generate",BOB,"intent","generate",a.ref))
    m=w._material_heads["3:bob:1:intent"]
    w.execute(MaterialCommand("externalize",BOB,"intent","externalize",m.ref))
    external=w._material_heads["3:bob:1:intent"]
    w.execute(MaterialCommand("express",BOB,"intent","express",external.ref))
    use=w._journal[-1].extra[0]
    w.execute(MaterialCommand("reown",BOB,"intent","reown",external.ref))
    owned=w._material_heads["3:bob:1:intent"]
    w.execute(MaterialCommand("express-again",BOB,"intent","express",owned.ref))
    renewed=w._journal[-1].extra[0]
    end(w,t);drain(w)
    return w,{"provenance":"injected_detector_fixture","account":a.ref.key,
        "material":m.ref.key,"carrier":external.carrier.key,"message":use.message.key,
        "consequence":"attribution delivered to Alice; unverified testimony",
        "reowned_revision":owned.ref.revision,"renewed_outcome":renewed.outcome,
        "path":w.report(s.ref).results[2].status.value,
        "generated_shell_claim":False}


def profile():
    rows=[]
    for inactive,unrelated in ((0,0),(2000,0),(0,200),(2000,200)):
        medians=[];saves=[];restores=[];last=None
        for repeat in range(3):
            w=world();remember_initial(w);s=declare(w)
            for i in range(unrelated):
                spec=replace(s.spec,ref=Ref(Kind.ASSESSMENT,f"unrelated:{i}",1),declared_at=w.now)
                other=replace(s,spec=spec,actor=ALICE,item=TOOL,memory_key=f"inactive:{i}")
                w.execute(DeclareStudy(f"declare-unrelated:{i}",other))
            drain(w,"initial",unrelated+1)
            for i in range(inactive):w.execute(Tick(f"inactive:{i}"))
            visited=w.assessment_visits
            durations=[]
            for i in range(24):
                before=time.perf_counter_ns()
                w.execute(Attempt(f"inspect:{i}",f"inspect:{i}",request(BOB,INSPECT,(BOX,))))
                assert w.pending_assessments()==(s.ref,)
                drain(w,f"report:{i}")
                durations.append(time.perf_counter_ns()-before)
            assert w.assessment_visits-visited==24
            medians.append(statistics.median(durations)/1000)
            before=time.perf_counter();checkpoint=w.checkpoint();saves.append((time.perf_counter()-before)*1000)
            before=time.perf_counter();restored=AssessedWorld.restore(checkpoint);restores.append((time.perf_counter()-before)*1000)
            assert restored.checkpoint()==checkpoint
            last={"checkpoint_bytes":len(checkpoint.encode()),"events":len(w._journal),"assessment_visits_active":24}
        rows.append({"inactive_ticks":inactive,"unrelated_studies":unrelated,
            "active_microseconds_median":statistics.median(medians),"repeat_medians_us":medians,
            "save_ms_median":statistics.median(saves),"replay_ms_median":statistics.median(restores),**last})
    return {"scope":"24 paid inspections + affected report per repeat; 3 repeats; setup excluded; no speed acceptance threshold",
        "limits":"fixed tiny active content; one actor dependency; no population/scaling acceptance; checkpoint retains whole history",
        "python":sys.version,"platform":platform.platform(),"machine":platform.machine(),"cases":rows}


PANEL={
"A01":["test_context_reuses_same_cue_and_same_card_has_no_single_content","test_multiple_cues_one_memory_and_deduplicated_roots"],
"A02":["test_useful_variable_paths_of_1_2_4_and_17_records"],
"A03":["test_a03_assessments_do_not_enter_participant_inputs_or_action_selection","test_hidden_ownership_and_evaluator_work_do_not_change_account_or_selection"],
"A04":["test_a04_actor_substitution_is_not_hidden_by_same_graph_shape"],
"A05":["test_a05_empty_memory_is_ignorance_and_zero_denominator_unassessed","test_repeated_demand_with_missing_information_is_not_a_shell"],
"A06":["test_a06_energy_and_time_limit_do_not_become_foreclosure","test_resource_replenishment_changes_new_opportunity_and_resumes_work"],
"A07":["test_a07_stable_false_account_returns_identity_without_becoming_true"],
"A08":["test_a08_correct_endpoint_keeps_discrepancy_and_paid_path_failure","test_predeclared_path_budget_cannot_be_erased_by_return"],
"A09":["test_a09_matched_quiet_trajectories_need_demand_to_imply_foreclosure","test_quiet_interval_does_not_clear_a_previous_candidate"],
"A10":["test_a10_capacity_requires_use_on_original_and_heldout_object","test_same_and_heldout_demand_have_matched_capacity_ablations","test_candidate_clearance_requires_renewed_correction_and_transfer"],
"A11":["test_a11_complete_material_carrier_action_consequence_reownership_chain","test_ordinary_false_ownership_account_is_not_projection_evidence"],
"A12":["test_all_type_routes_match_independent_positional_oracle","test_type_effects_change_paths_and_costs_with_equal_semantic_evidence","test_neutral_routing_and_prices_remove_type_effects"],
"A13":["test_a13_canon_single_return_passes_repeat_fails","test_equivalence_preserving_finite_model_closes_only_declared_domain"],
"A14":["test_a14_every_integrated_prefix_continues_exactly","test_partial_assessment_queue_and_partial_processing_survive_reload","test_rehashed_report_and_opportunity_tampering_rejects"],
"A15":["test_a15_reports_match_independent_full_comparison_at_every_update","test_active_assessment_avoids_global_history_and_unrelated_records","test_clock_expiry_invalidates_only_when_scope_boundary_is_crossed"]}


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--tests",type=Path,required=True);args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    results=json.loads(args.tests.read_text())
    panel={}
    for key,names in PANEL.items():
        found=[next(t for t in results["tests"] if t["test"].endswith("."+name)) for name in names]
        panel[key]={"passed":all(t["status"]=="passed" for t in found),"tests":[t["test"] for t in found],
            "scope":"explicit material-treatment fixture; not generated Shell evidence" if key=="A11" else
                    "bounded type/routing controls; independently adapting exchanges remain R6" if key=="A12" else "declared bounded fixtures"}
    assert all(p["passed"] for p in panel.values()) and results["successful"]
    write(args.output/"acceptance_panel.json",panel)
    w,summary=run_assessment_demo();save_case(args.output,"integrated",w,summary)
    counts={}
    for mode in ("rest","foreclosure","compensation"):
        w,s=detector_case(mode);r=w.report(s.ref);counts[mode]=r.shell
        save_case(args.output,mode,w,{"shell":r.shell,"provenance":r.provenance,"generated_shell_claim":False})
    w,s=detector_case("foreclosure",energy=0);save_case(args.output,"resource_limited",w,{"shell":w.report(s.ref).shell})
    w,s,labels=clearance_case();save_case(args.output,"retained_correction",w,{"lifecycle":labels,"scope":"clearance within injected fixture and tested demands only"})
    w,s=projection_case();save_case(args.output,"projection_reownership",w,s)
    write(args.output/"capacity_controls.json",capacity_controls())
    write(args.output/"profile.json",profile())
    digests=[]
    for seed in ("1","7","91"):
        env=dict(os.environ,PYTHONHASHSEED=seed)
        result=subprocess.run([sys.executable,"-c","import hashlib; from hle.assessment_demo import run_assessment_demo; print(hashlib.sha256(run_assessment_demo()[0].checkpoint().encode()).hexdigest())"],cwd=ROOT,env=env,text=True,capture_output=True,check=True)
        digests.append({"hash_seed":seed,"checkpoint_sha256":result.stdout.strip()})
    assert len({r["checkpoint_sha256"] for r in digests})==1
    write(args.output/"hash_seed_controls.json",digests)
    write(args.output/"summary.json",{"milestone":"R5","panel_passed":len(panel),"tests":results["tests_run"],"detectors":counts,"generated_shell_claim":False,"general_closure":"unassessed"})
    print(json.dumps({"panel_passed":len(panel),"tests":results["tests_run"],"output":str(args.output)}))


if __name__=="__main__":main()
