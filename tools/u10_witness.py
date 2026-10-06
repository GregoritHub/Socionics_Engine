"""Raw development witnesses for U10 meaning, repair, consent and continuation."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"baseline/HLE_Rebuild_R21B")]
sys.dont_write_bytecode=True
from tests_u10.fixtures import *
from hle_unified.language_audit import audit
from inspect_u10 import readable


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--out",type=Path,required=True)
    out=parser.parse_args().out;out.mkdir(parents=True,exist_ok=False)
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

    e,d=circuit10()
    checks["unknown_term_asks_a_received_question"]=d["unknown"]["status"]=="clarification" and d["question"]["meaning"][0]=="clarify"
    checks["single_demonstration_remains_tentative"]=d["learned"][0]["status"]=="tentative"
    checks["independent_demonstrations_stabilize_term"]=d["learned"][1]["status"]=="stable"
    checks["recipient_has_own_meaning_identity"]=d["learned"][1]["ref"].identity!=d["teacher"]["entry"]["ref"].identity
    checks["learner_does_not_inherit_teacher_capacity"]=not any(x["kind"]=="capacity" for x in e.composition_view(BOB))
    checks["known_term_changes_actual_behavior"]=d["first"]["status"]=="succeeded" and d["first"]["trace"]==("repair","use","care")
    checks["unseen_composition_of_word_and_actions_executes"]=d["composed"]["trace"]==("repair","use","care","use","care") and d["composed"]["status"]=="succeeded"
    checks["composition_has_observed_extra_use"]=thaw(d["composed"]["state"])["progress"]["uses"]==2
    checks["overbroad_use_has_observed_failure"]=d["failed"]["failure_kind"]=="observed_counterexample" and d["failed"]["status"]=="failed"
    checks["failed_material_effect_remains"]=e.world.head(ref("bob-fragile").identity).facet(Material).condition=="damaged"
    checks["challenge_suspends_lexical_agreement"]=d["challenged"]["status"]=="challenged" and d["challenged"]["program"] is None
    checks["teacher_receives_grounded_counterexample"]=d["report_received"]["reason"]=="observed_counterexample"
    checks["one_new_branch_example_does_not_repair_meaning"]=d["revision"]["learned"][0]["status"]=="tentative"
    repaired=d["revision"]["learned"][-1]
    checks["stable_new_distinction_repairs_meaning"]=repaired["status"]=="stable" and repaired["split"]==("eq",("field","target","max_wear"),1)
    checks["old_semantics_remain_addressable"]=unpack(e.world.resolve(d["learned"][1]["ref"]))["program"]==d["learned"][1]["program"]
    checks["fragile_return_uses_new_branch"]=d["returns"][0]["trace"]==("repair","use","repair") and d["returns"][0]["status"]=="succeeded"
    checks["ordinary_return_preserves_old_branch"]=d["returns"][1]["trace"]==("repair","use","care") and d["returns"][1]["status"]=="succeeded"
    main_audit=keep("grounded_meaning_and_repair",e)
    checks["raw_accounting_and_language_lineage"]=main_audit["passed"] and main_audit["meaning_repairs"]==1
    checks["wallet_debits_match_raw_charges"]=sum(e.wallet(a)["initial_energy"]-e.wallet(a)["energy"] for a in (ALICE,BOB,EVE))==main_audit["charged_energy"]
    restored=LanguageEngine.restore(e.checkpoint())
    checks["complete_history_replays_exactly"]=restored.checkpoint()==e.checkpoint()
    (out/"meaning_trace.json").write_text(json.dumps(readable({k:d[k] for k in ("unknown","learned","first","composed","failed","challenged","report_received","revision","returns")}),indent=2)+"\n")

    partial,t=teacher10();slots=reveal10(partial,"bob-first",actor=ALICE)
    m=work10(partial,"partial-message","send",peer=BOB,act="request",body=("word",t["entry"]["term"]),slots=slots,goal=GOAL)[-1]
    key=deliver10(partial,m,read=False)
    checks["delivery_alone_has_no_processed_meaning"]=not partial.participant_view(BOB).resolve(m["ref"]) and not partial.language_view(BOB)
    perform(partial,OperationRequest("read:"+key,BOB,"read",ROOM,delivery="show:"+key),limit=10000)
    partial.start("partial-start",LanguageRequest("partial",BOB,"interpret",ROOM,CUE5,focus=m["ref"]))
    partial.advance("partial-work",BOB,"partial",1)
    checks["partial_payment_has_no_interpretation"]=not partial.language_view(BOB)
    keep("partial_interpretation",partial)
    other=LanguageEngine.restore(partial.checkpoint())
    for engine in (partial,other):
        engine.advance("remaining-work",BOB,"partial",100000);engine.commit("finish-interpretation",BOB,"partial")
    checks["partial_interpretation_continues_exactly"]=partial.checkpoint()==other.checkpoint()

    s,t=teacher10();slots=reveal10(s,"bob-promise",actor=ALICE);reveal10(s,"bob-promise",actor=BOB)
    for act in ("statement","question","explanation","intention"):
        body=("test",("eq",("field","target","condition"),"serviceable" if act=="statement" else "damaged"))
        goal=()
        if act in ("explanation","intention"):
            body=("because",body,t["entry"]["program"]) if act=="explanation" else t["entry"]["program"]
            goal=GOAL
        message=work10(s,act+"-send","send",peer=BOB,act=act,body=body,slots=slots,goal=goal)[-1]
        deliver10(s,message);interp=work10(s,act+"-interpret","interpret",actor=BOB,focus=message["ref"])[0]
        reply=work10(s,act+"-respond","respond",actor=BOB,focus=interp["ref"])
        if act=="statement":checks["received_false_statement_is_disputed"]=interp["assessment"]=="contradicted"
        if act=="question":checks["question_gets_grounded_answer"]=reply[-1]["act"]=="answer" and dict(codec.loads(reply[-1]["payload"]))["body"][1]=="supported"
        if act=="explanation":checks["explanation_preserves_grounded_reason"]=interp["assessment"]=="supported" and interp["meaning"][0]=="because"
        if act=="intention":checks["intentions_do_not_execute_material_effects"]=s.world.head(ref("bob-promise").identity).facet(Material).condition=="damaged"
    _,interp=request10(s,t["entry"],"bob-promise",prefix="promise-request",body=t["entry"]["program"])
    response=response10(s,interp,prefix="promise-response")
    checks["request_does_not_create_automatic_promise"]=not any(x["kind"]=="commitment" for x in s.language_view(BOB))
    promise=next(x for x in work10(s,"explicit-promise","send",actor=BOB,peer=ALICE,act="commitment",body=interp["meaning"],slots=slots,goal=GOAL) if x["kind"]=="commitment")
    checks["explicit_promise_is_open_before_performance"]=promise["status"]=="open"
    run=enact_response10(s,response,prefix="promise-run",steps=1)
    (out/"partial_practical_response.checkpoint.json").write_text(s.checkpoint())
    restored=LanguageEngine.restore(s.checkpoint())
    for engine in (s,restored):
        complete=continue10(engine,run,prefix="promise-run")
        settled=work10(engine,"settle-promise","settle",actor=BOB,focus=promise["ref"],practice=complete["ref"])[0]
    checks["practical_continuation_and_settlement_replay_exactly"]=s.checkpoint()==restored.checkpoint()
    checks["promise_fulfillment_has_actual_observations"]=settled["status"]=="fulfilled" and bool(settled["observations"])
    keep("speech_acts_and_commitment",s)

    no_skill,t=teacher10(setup10(train_bob=False))
    _,i=request10(no_skill,t["entry"],body=t["entry"]["program"])
    response=response10(no_skill,i)
    checks["understanding_does_not_grant_unpracticed_skill"]=i["status"]=="understood" and response["reason"]=="own_practice_required"
    keep("unpracticed_receiver",no_skill)

    result={"schema":"hle-u10-witness-v1","checks":checks,"check_count":len(checks),"artifacts":artifacts,
        "passed":all(checks.values()),"scope":"Declared finite workshop development witnesses; no U14 release holdout claim."}
    (out/"summary.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"passed":result["passed"],"checks":len(checks),"failed":[k for k,v in checks.items() if not v]}),flush=True)
    return 0 if result["passed"] else 1


if __name__=="__main__":raise SystemExit(main())
