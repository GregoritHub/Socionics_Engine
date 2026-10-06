"""Raw U11 witnesses, including controlled noncompletion and exact continuation."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"baseline/HLE_Rebuild_R21B")]
sys.dont_write_bytecode=True
from tests_u11.fixtures import *
from tests_u11.test_collective import team
from hle_unified.collective_audit import audit
from hle_unified.material import attrs as raw_attrs
from inspect_u10 import readable


def main():
    p=argparse.ArgumentParser();p.add_argument("--out",type=Path,required=True)
    out=p.parse_args().out;out.mkdir(parents=True,exist_ok=False)
    checks,artifacts={},{}
    def keep(name,e):
        checkpoint=e.checkpoint();raw=codec.dumps(tuple(e.world.journal()))
        (out/(name+".checkpoint.json")).write_text(checkpoint)
        (out/(name+".transactions.json")).write_text(raw)
        result=audit(e.world.journal())
        (out/(name+".audit.json")).write_text(json.dumps(result,indent=2)+"\n")
        artifacts[name]={"checkpoint_sha256":hashlib.sha256(checkpoint.encode()).hexdigest(),
            "raw_sha256":hashlib.sha256(raw.encode()).hexdigest(),"audit":result}
        print(name,flush=True)
        return result

    e,d=circuit11();reference,dr=circuit11(flat=True)
    main=keep("nested_collective_work",e);keep("detailed_reference",reference)
    checks["nested_run_completes_with_four_actual_steps"]=d["run"]["status"]=="succeeded" and len(d["run"]["events"])==4
    sequence=[raw_attrs(e.world.resolve(r))["primitive"] for r in d["run"]["events"]]
    checks["actual_steps_are_repair_transfer_use_care"]=sequence==["repair","transfer","use","care"]
    checks["two_participants_perform_their_own_steps"]={raw_attrs(e.world.resolve(r))["actor"] for r in d["run"]["events"]}=={ALICE,BOB}
    checks["nested_and_detailed_material_states_agree"]=all(e.world.head(k.identity)==reference.world.head(k.identity)
        for k in (SHARED,BOB_CARE,ref("u11-kit-alice"),ref("u11-repair-alice")))
    def physical(engine,run):
        return tuple((raw_attrs(engine.world.resolve(x))["primitive"],raw_attrs(engine.world.resolve(raw_attrs(engine.world.resolve(x))["operation"]))["spent"]) for x in run["events"])
    checks["nested_and_detailed_primitive_work_agrees"]=physical(e,d["run"])==physical(reference,dr["run"])
    checks["scoped_final_summaries_agree"]=d["after"]["public"]==dr["after"]["public"]
    checks["overlapping_resource_is_counted_once"]=dict(d["before"]["public"])["resource_count"]==4
    checks["subgroup_and_parent_retain_separate_capacity"]=d["child_capacity"]["owner"]==d["child"]["ref"].identity and d["capacity"]["owner"]==d["root"]["ref"].identity
    checks["parent_capacity_has_all_actual_observations"]=d["capacity"]["events"]==d["run"]["events"] and main["collective_capacities"]==2
    checks["group_capacity_is_not_a_personal_skill"]=not any(e.participant_view(a).can_use(d["capacity"]["ref"],ROOM) for a in (ALICE,BOB,EVE))
    checks["wallets_match_independent_raw_debits"]=sum(e.wallet(a)["initial_energy"]-e.wallet(a)["energy"] for a in (ALICE,BOB,EVE))==main["charged_energy"]
    checks["whole_history_restores_exactly"]=CollectiveEngine.restore(e.checkpoint()).checkpoint()==e.checkpoint()
    (out/"collective_trace.json").write_text(json.dumps(readable(d),indent=2)+"\n")

    partial,g,p=team();selection,run=select(partial,instantiate(partial,p),"partial")
    partial.enact("partial-enact",ALICE,"partial-physical",selection["ref"])
    partial.advance("partial-pay",ALICE,"partial-physical",2)
    keep("partial_constituent_work",partial)
    checks["partial_physical_work_has_no_early_effect"]=partial.world.head(SHARED.identity).ref==SHARED
    checks["partial_work_preserves_real_reservations"]=bool(partial._locks) and partial.job_status(ALICE,"partial-physical")["spent"]==2
    restored=CollectiveEngine.restore(partial.checkpoint())
    for engine in (partial,restored):
        engine.advance("rest",ALICE,"partial-physical",1000);event=engine.commit("effect",ALICE,"partial-physical")
        obs=receive(engine,event,ALICE,"continued-result")
        finished=work(engine,"continued-observe","observe",focus=run["ref"],observation=obs)[0]
    checks["partial_constituent_continuation_replays_exactly"]=partial.checkpoint()==restored.checkpoint()
    checks["only_observed_work_advances_run"]=finished["index"]==1 and finished["status"]=="active"
    keep("continued_constituent_work",partial)

    consent,g,p=team();run=instantiate(consent,p);run=perform_step(consent,run,"completed-repair")
    repaired=consent.world.head(SHARED.identity)
    selection,run=select(consent,run,"transfer")
    consent.enact("transfer-enact",ALICE,"transfer-physical",selection["ref"])
    consent.advance("transfer-pay",ALICE,"transfer-physical",1000)
    budget=consent.wallet(ALICE)["energy"]
    duty=consent._duties11[run["ref"].identity,BOB]
    withdrawn=work(consent,"withdraw","withdraw",actor=BOB,focus=duty)[0]
    event=consent.commit("withheld-effect",ALICE,"transfer-physical")
    checks["withdrawn_consent_blocks_ready_effect"]=consent.job_status(ALICE,"transfer-physical")["failure"]=="stale_dependency"
    checks["withdrawal_preserves_paid_work"]=consent.wallet(ALICE)["energy"]==budget and consent.job_status(ALICE,"transfer-physical")["spent"]==3
    checks["earlier_repair_is_not_rolled_back"]=consent.world.head(SHARED.identity)==repaired
    checks["withdrawal_preserves_open_obligation"]=withdrawn["status"]=="open" and not withdrawn["permission_active"]
    group_after=work(consent,"departure","leave",actor=BOB,focus=g["ref"])[0]
    checks["departure_does_not_erase_obligation"]=consent.world.resolve(withdrawn["ref"]).facet(Relation).predicate=="collective_work_due" and BOB not in group_after["members"]
    keep("withdrawal_and_departure",consent)

    missing,g,p=team(train_bob=False);run=instantiate(missing,p,accept=False)
    work(missing,"unpracticed-consent","accept",actor=BOB,focus=run["ref"],expect=False)
    checks["joining_does_not_grant_primitive_acquisition"]=not missing.participant_view(BOB).can_use(ref("u11-primitive-use"),ROOM)
    checks["unpracticed_worker_cannot_accept"]=missing.job_status(BOB,"unpracticed-consent")["status"]=="failed"
    keep("unpracticed_member",missing)

    observed,g,p=team();run=instantiate(observed,p);run=perform_step(observed,run,"repair");run=perform_step(observed,run,"handoff")
    summary=work(observed,"summary-only","summarize",actor=BOB,focus=g["ref"])[0];expose(observed,BOB,summary["ref"])
    work(observed,"without-detail","select",actor=BOB,focus=run["ref"],expect=False)
    checks["aggregate_summary_cannot_supply_missing_tool_detail"]=observed.job_status(BOB,"without-detail")["status"]=="failed"
    expose(observed,BOB,observed.world.head(SHARED.identity).ref)
    selection,run=work(observed,"with-detail","select",actor=BOB,focus=run["ref"])
    checks["paid_detail_resolution_enables_selection"]=selection["status"]=="prepared"
    keep("summary_requires_detail",observed)

    exhausted=setup11(budget=3000);g=repair_group(exhausted);expose(exhausted,ALICE,g["ref"])
    request=CollectiveRequest("too-large",ALICE,"summarize",ROOM,CUE5,focus=g["ref"],limit=100000)
    exhausted.start("start",request);exhausted.advance("work",ALICE,"too-large",10000000)
    checks["budget_exhaustion_retains_partial_work"]=exhausted.wallet(ALICE)["energy"]==0 and exhausted.job_status(ALICE,"too-large")["status"]=="partial"
    checks["unfinished_coordination_installs_no_summary"]=not any(x["kind"]=="summary" for x in exhausted._records11.values())
    keep("exhausted_coordination",exhausted)

    hidden,g,p=team();root=group(hidden,"parent",members=(g["ref"],));other=group(hidden,"other",resources=(BOB_CARE,))
    before=hidden.participant_view(BOB).snapshot
    for item in (g,root,other):nesting.project(hidden.world,item["ref"].identity,"inventory",128)
    nesting.project(hidden.world,root["ref"].identity,"membership",128)
    for obj in (SHARED,hidden.world.head(ref("u11-kit-alice").identity).ref,hidden.world.head(ref("u11-repair-alice").identity).ref):expose(hidden,ALICE,obj)
    perform(hidden,OperationRequest("hidden-repair",ALICE,"repair",ROOM,target=SHARED,
        tool=hidden.world.head(ref("u11-kit-alice").identity).ref,stock=hidden.world.head(ref("u11-repair-alice").identity).ref,evidence=evidence(hidden,ALICE,SHARED)))
    checks["hidden_child_change_conveys_no_participant_fact"]=before==hidden.participant_view(BOB).snapshot
    checks["relevant_child_invalidates_all_dependent_inventory"]=all(("u11.projection",i["ref"].identity,"inventory") not in hidden.world.cache.values for i in (g,root))
    checks["unrelated_inventory_and_structural_scope_remain_cached"]=("u11.projection",other["ref"].identity,"inventory") in hidden.world.cache.values and ("u11.projection",root["ref"].identity,"membership") in hidden.world.cache.values
    keep("hidden_child_invalidation",hidden)

    result={"schema":"hle-u11-witness-v1","checks":checks,"check_count":len(checks),"artifacts":artifacts,
        "passed":all(checks.values()),"scope":"Declared deterministic U11 development witnesses; no release holdout or efficiency claim."}
    (out/"summary.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"passed":result["passed"],"checks":len(checks),"failed":[k for k,v in checks.items() if not v]}),flush=True)
    return 0 if result["passed"] else 1


if __name__=="__main__":raise SystemExit(main())
