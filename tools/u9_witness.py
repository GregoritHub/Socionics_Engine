"""Finite raw U9 development witnesses, including failed and unfinished work."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"baseline/HLE_Rebuild_R21B")]
sys.dont_write_bytecode=True
from tests_u9.fixtures import *
from hle_unified import codec
from hle_unified.composition_audit import audit
from hle_unified import composition_language as language


def main():
    p=argparse.ArgumentParser();p.add_argument("--out",type=Path,required=True)
    out=p.parse_args().out;out.mkdir(parents=True,exist_ok=False)
    checks,artifacts={},{}
    def keep(name,e):
        checkpoint=e.checkpoint()
        (out/(name+".checkpoint.json")).write_text(checkpoint)
        raw=codec.dumps(tuple(e.world.journal()))
        (out/(name+".transactions.json")).write_text(raw)
        result=audit(e.world.journal())
        (out/(name+".audit.json")).write_text(json.dumps(result,indent=2)+"\n")
        artifacts[name]={"checkpoint_sha256":hashlib.sha256(checkpoint.encode()).hexdigest(),
                         "raw_sha256":hashlib.sha256(raw.encode()).hexdigest(),"audit":result}
        return result

    e,d=revised9()
    checks["generated_absent_complete_answer"]=d["capacity"]["program"]==("seq",(("act","repair"),("act","use"),("act","care")))
    checks["unfamiliar_transfer_succeeds"]=d["transfer"]["status"]=="succeeded" and thaw(d["transfer"]["initial"])["target"]["max_wear"]==4
    checks["observed_failed_generalization_preserved"]=d["failed"]["status"]=="failed" and d["failed"]["failure_kind"]=="observed_counterexample"
    checks["material_failure_has_persistent_consequence"]=e.world.head(ref("counter").identity).facet(Material).condition=="damaged"
    checks["failure_generates_two_distinct_demands"]={x["reason"] for x in d["repair_demands"]}=={"failed_generalization","persistent_consequence"}
    checks["new_branch_constructed"]=d["candidate"]["program"]==("seq",(("act","repair"),("act","use"),("act","repair")))
    checks["feature_split_generated"]=d["revised"]["split"]==("eq",("field","target","max_wear"),1)
    checks["previous_organization_preserved"]=d["revised"]["program"][3]==("call",d["capacity"]["ref"]) and e.world.resolve(d["capacity"]["ref"]).ref==d["capacity"]["ref"]
    checkpoint=e.checkpoint();(out/"before_later_return.checkpoint.json").write_text(checkpoint)
    restored=CompositionEngine.restore(checkpoint)
    for engine in (e,restored):
        old=notice9(engine,"old-return")
        old_run=run9(engine,old,d["revised"],prefix="old-return")
    checks["retained_old_branch_later_return"]=old_run["status"]=="succeeded" and old_run["trace"]==("repair","use","care")
    checks["full_return_continuation_replays_exactly"]=e.checkpoint()==restored.checkpoint()
    consequence=next(x for x in d["repair_demands"] if x["reason"]=="persistent_consequence")
    recovery=find9(e,consequence,prefix="recover-search")
    recovery_run=run9(e,consequence,recovery,prefix="recover-run")
    checks["actual_recovery_after_persistent_failure"]=recovery_run["status"]=="succeeded" and e.world.head(ref("counter").identity).facet(Material).condition=="serviceable"
    checks["recovery_does_not_erase_prior_completed_work"]=thaw(recovery_run["initial"])["progress"]["uses"]==1
    goal=(("ge",("field","progress","uses"),2),*GOAL[1:])
    new=notice9(e,"ready-fragile",goal=goal)
    extension=find9(e,new,prefix="conditional-extension")
    extended_run=run9(e,new,extension,prefix="conditional-extension-run")
    checks["constructs_extension_with_retained_subprocedure"]=extension["program"]==("seq",(("act","use"),("call",d["revised"]["ref"])))
    checks["condition_uses_observed_intermediate_state"]=extended_run["status"]=="succeeded" and extended_run["trace"]==("use","repair","use","repair")
    main_audit=keep("composition_and_revision",e)
    checks["independent_raw_accounting"]=main_audit["passed"] and main_audit["charged_energy"]==main_audit["charged_time"]
    checks["wallet_matches_raw_charges"]=e.wallet(ALICE)["initial_energy"]-e.wallet(ALICE)["energy"]==main_audit["charged_energy"]

    deep=setup9();goal=(("ge",("field","progress","uses"),3),*GOAL[1:])
    demand=notice9(deep,"deep",goal=goal)
    shallow=find9(deep,demand,prefix="shallow",depth=2)
    (out/"depth_limited.checkpoint.json").write_text(deep.checkpoint())
    checks["bounded_repertoire_exhaustion_retains_deferred_work"]=shallow["status"]=="repertoire_exhausted_at_depth" and bool(shallow["deferred"])
    candidate=find9(deep,shallow,prefix="deeper",depth=8,tickets=300)
    checks["further_funding_extends_retained_complexity"]=candidate["kind"]=="candidate" and len(candidate["program"][1])==7
    run=run9(deep,demand,candidate,prefix="deep-run")
    checks["extended_complexity_is_useful"]=run["status"]=="succeeded" and thaw(run["state"])["progress"]["uses"]==3
    keep("extended_search",deep)

    partial=setup9();demand=notice9(partial)
    r=CompositionRequest("partial",ALICE,"search",ROOM,CUE5,focus=demand["ref"])
    partial.start("partial-start",r);partial.advance("partial-work",ALICE,r.key,1)
    checks["partial_payment_grants_no_candidate"]=not any(x["kind"]=="candidate" for x in partial.composition_view(ALICE))
    original=partial.checkpoint();keep("partial_search",partial)
    restored=CompositionEngine.restore(original)
    for engine in (partial,restored):
        engine.advance("remainder",ALICE,r.key,1000000);engine.commit("complete",ALICE,r.key)
    checks["partial_paid_search_continues_exactly"]=partial.checkpoint()==restored.checkpoint()

    scarce=setup9(budget=400);demand=notice9(scarce)
    request=CompositionRequest("scarce",ALICE,"search",ROOM,CUE5,focus=demand["ref"])
    scarce.start("scarce-start",request);scarce.advance("scarce-work",ALICE,request.key,1000000)
    checks["scarcity_is_partial_not_proof_of_no_solution"]=scarce.wallet(ALICE)["energy"]==0 and scarce.job_status(ALICE,request.key)["status"]=="partial" and not any(x["kind"]=="search" for x in scarce.composition_view(ALICE))
    keep("scarcity",scarce)

    loan=setup9();demand=loan9(loan);candidate=find9(loan,demand,prefix="loan-search")
    run=run9(loan,demand,candidate,prefix="loan-run")
    checks["relations_change_actual_custody_and_obligation"]=run["status"]=="succeeded" and loan.world.head(ref("loan").identity).facet(Material).custodian==BOB
    keep("relational_procedure",loan)
    alt,cap=trained9();demand=notice9(alt,"ready-train")
    candidate=find9(alt,demand,prefix="ready-search");run=run9(alt,demand,candidate,prefix="ready-run")
    other=do9(alt,"retain-ready","retain",focus=run["ref"])[0]
    demand=notice9(alt,"ready-return");candidate=find9(alt,demand,prefix="alternative-search")
    run=run9(alt,demand,candidate,prefix="alternative-run")
    checks["ordered_alternative_constructed_and_executed"]=candidate["program"][1][0][0]=="choice" and run["status"]=="succeeded"
    keep("guarded_alternatives",alt)
    summary={"schema":"hle-u9-witness-v1","checks":checks,"passed":all(checks.values()),"artifacts":artifacts,
        "scope":"Declared development panel; only participant-relative transfer contexts, no U14 release or universal closure claim."}
    (out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps({"passed":summary["passed"],"checks":len(checks),"failed":[k for k,v in checks.items() if not v]}))
    return 0 if summary["passed"] else 1


if __name__=="__main__":raise SystemExit(main())
