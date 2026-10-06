"""Inspectible U12 causal witnesses, including refusal and unfinished work."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"baseline/HLE_Rebuild_R21B")]
sys.dont_write_bytecode=True
from tests_u12.fixtures import *
from hle_unified.institution_audit import audit
from hle_unified.records import Governance
from inspect_u10 import readable


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--out",type=Path,required=True)
    out=parser.parse_args().out;out.mkdir(parents=True,exist_ok=False)
    checks,artifacts,trace={},{},{}
    def keep(name,e):
        cp=e.checkpoint();raw=codec.dumps(tuple(e.world.journal()));a=audit(e.world.journal())
        (out/(name+".checkpoint.json")).write_text(cp)
        (out/(name+".transactions.json")).write_text(raw)
        (out/(name+".audit.json")).write_text(json.dumps(a,indent=2)+"\n")
        artifacts[name]={"checkpoint_sha256":hashlib.sha256(cp.encode()).hexdigest(),
            "transactions_sha256":hashlib.sha256(raw.encode()).hexdigest(),"audit":a}
        print(name,flush=True)
        return a

    e,d=active12();rule=d["institution"];original=e.world.resolve(rule["ref"])
    a=keep("maintained_public_projection",e)
    checks["no_finished_rule_was_supplied"]=d["group"].get("rules",())==() and d["proposal"]["considered"]>0
    checks["program_generated_from_practiced_primitives"]=d["proposal"]["symbolic"]==("seq",(("act","use"),("act","care")))
    checks["personal_patterns_are_generated_from_distinct_received_episodes"]=all(p.origin_mode=="generated" and len(p.evidence)>=2 for actor in (ALICE,BOB) for p in e.pattern_view(actor))
    checks["generated_attribution_reaches_public_proposal"]=bool(d["proposal"]["patterns"]) and d["proposal"]["gate"]=="approval"
    checks["participants_separately_paid_for_exact_consent"]=len(rule["votes"])==2 and {e._records11[r]["owner"] for r in rule["votes"]}=={ALICE,BOB}
    checks["maintained_rule_follows_repeated_actual_work"]=rule["status"]=="active" and a["institutional_practices"]==2 and a["constituent_attempts"]==4
    checks["public_rule_is_attached_to_same_group_identity"]=e.world.resolve(rule["group"]).facet(Governance).rules==(rule["ref"],)
    trace["origin_to_public_rule"]={k:d[k] for k in ("proposal","trial","practices","institution")}

    before=e.world.head(ref("u12-tool-bob").identity)
    app,consequence=op12(e,"public-delay","apply",actor=BOB,focus=rule["ref"],slots=slots12(e,BOB))
    dispute=op12(e,"public-dispute","dispute",actor=BOB,focus=consequence["ref"])[0]
    checks["public_burden_names_actual_bearer_and_rule"]=consequence["bearer"]==BOB and consequence["rule_cause"]==rule["proposal"]
    checks["maintained_gate_changes_actual_service"]=consequence["outcome"]=="approval_wait" and e.world.head(before.ref.identity)==before and consequence["spent"]>0
    checks["dispute_preserves_consequence_and_rule"]=dispute["consequence"]==consequence["ref"] and e.world.resolve(rule["ref"])==original
    keep("public_burden_and_dispute",e)

    correct12(e,ALICE,"alice-correct")
    checks["private_correction_leaves_rule_exactly_unchanged"]=e.world.head(rule["ref"].identity)==original
    first=propose12(e,rule,"first-review",intent="review",support=dispute["ref"])
    votes=vote12(e,first,"first-review-votes")
    for v in votes:expose12(e,ALICE,v["ref"])
    op12(e,"failed-unilateral-amendment","ratify",focus=first["ref"],expect=False)
    checks["independent_partner_disagreement_prevents_public_rewrite"]=[v["choice"] for v in votes]==["accept","negotiate"] and e.world.head(rule["ref"].identity)==original
    _,still_waiting=op12(e,"still-governed","apply",actor=BOB,focus=rule["ref"],slots=slots12(e,BOB))
    checks["private_and_public_correction_diverge_in_later_behavior"]=first["gate"]=="self_check" and still_waiting["outcome"]=="approval_wait"
    keep("private_correction_public_rule",e)

    correct12(e,BOB,"bob-correct")
    counter=op12(e,"counterproposal","counter",actor=BOB,focus=first["ref"],slots=slots12(e,BOB))[0]
    vote12(e,counter,"counter-votes")
    rule=ratify12(e,counter,"collective-revision",actor=BOB)
    settled=e._records11[e._heads11[dispute["ref"].identity]]
    checks["revision_requires_fresh_exact_consents"]=rule["gate"]=="self_check" and rule["predecessor"]==d["institution"]["ref"] and all(e._records11[v]["proposal"]==counter["ref"] for v in rule["votes"])
    checks["collective_dispute_resolution_keeps_historical_burden"]=settled["status"]=="resolved" and settled["bearer"]==BOB and e._records11[consequence["ref"]]==consequence
    run,pr=practice12(e,rule,"corrected-service",actor=BOB)
    checks["corrected_rule_changes_real_constituent_work"]=run["status"]=="succeeded" and len(run["events"])==2 and run["permission"] is None
    checks["old_rule_and_commitments_remain_addressable"]=e.world.resolve(original.ref)==original and all(e.world.resolve(v).facet(Relation) is not None for v in original.facet(Governance).obligations)
    keep("collective_correction_and_work",e)
    trace["correction"]={"private_proposal":first,"disagreement":votes,"counter":counter,"revised_rule":rule,"resolved_dispute":settled,"later_run":run}

    succession=propose12(e,rule,"succession",intent="succession",peer=BOB)
    vote12(e,succession,"succession-votes")
    rule=ratify12(e,succession,"successor-enacted")
    group_after=work(e,"founder-departure","leave",focus=rule["group"])[0]
    run,pr=practice12(e,rule,"after-founder",actor=BOB)
    checks["institution_survives_consented_succession_and_founder_departure"]=rule["steward"]==BOB and ALICE not in group_after["members"] and run["status"]=="succeeded"
    checks["founder_history_and_personal_pattern_remain"]=len(e.pattern_view(ALICE))==1 and bool(e.development_view(ALICE)["corrections"])

    invitation=work(e,"invite-newcomer","invite",actor=BOB,focus=group_after["ref"],peer=EVE)[0]
    group_after=work(e,"newcomer-joins","join",actor=EVE,focus=invitation["ref"])[0]
    lesson=op12(e,"teach-newcomer","teach",actor=BOB,focus=rule["ref"],peer=EVE)[0]
    understanding=op12(e,"learner-processes","learn",actor=EVE,focus=lesson["ref"])[0]
    assent=op12(e,"learner-assents","assent",actor=EVE,focus=understanding["ref"])[0]
    op12(e,"learner-lacks-skill","apply",actor=EVE,focus=rule["ref"],slots=slots12(e,EVE),expect=False)
    checks["teaching_and_assent_do_not_grant_personal_mastery"]=assent["permission_active"] and not e.participant_view(EVE).can_use(ref("u11-primitive-use"),ROOM) and e.job_status(EVE,"learner-lacks-skill")["status"]=="failed"
    train(e,EVE,("use","care"));newrun,pr=practice12(e,rule,"newcomer-real-work",actor=EVE)
    checks["newcomer_performs_after_own_practice"]=newrun["status"]=="succeeded" and understanding["gate"]==rule["gate"]
    keep("succession_and_newcomer",e)

    pending=op12(e,"unfinished-work","apply",actor=BOB,focus=rule["ref"],slots=slots12(e,BOB))[0]
    duty=work(e,"unfinished-consent","accept",actor=BOB,focus=pending["ref"])[0]
    dissolving=propose12(e,rule,"propose-dissolution",actor=BOB,intent="dissolve")
    vote12(e,dissolving,"dissolution-votes")
    closed=ratify12(e,dissolving,"dissolved",actor=BOB)
    work(e,"stale-old-work","select",actor=BOB,focus=pending["ref"],expect=False)
    checks["dissolution_requires_current_members_not_departed_founder"]=dissolving["electorate"]==tuple(sorted((BOB,EVE))) and closed["status"]=="dissolved"
    checks["dissolution_preserves_unfinished_duty_and_earlier_work"]=e._records11[duty["ref"]]["status"]=="open" and e.job_status(BOB,"stale-old-work")["status"]=="failed" and e._records11[newrun["ref"]]["status"]=="succeeded"
    final=keep("complete_institution_history",e)
    checks["independent_debits_equal_all_wallet_losses"]=final["charged_energy"]==sum(e.wallet(a)["initial_energy"]-e.wallet(a)["energy"] for a in (ALICE,BOB,EVE))
    restored=InstitutionEngine.restore(e.checkpoint())
    checks["complete_history_replays_exactly"]=restored.checkpoint()==e.checkpoint()

    ablation,g=setup12(patterns=());p=propose12(ablation,g)
    checks["matched_history_ablation_changes_gate_not_material_recipe"]=p["gate"]=="self_check" and p["symbolic"]==d["proposal"]["symbolic"]
    keep("no_attribution_control",ablation)
    encounter12(ablation,"real-danger",BOB,safe=False)
    v=op12(ablation,"boundary-vote","respond",actor=BOB,focus=p["ref"])[0]
    checks["legitimate_threat_is_refusal_without_shell"]=v["choice"]=="refuse" and v["reason"]=="received_threat" and not ablation.pattern_view(BOB)
    keep("legitimate_boundary_control",ablation)

    other,od=active12(domain="pump")
    checks["distinct_material_context_supports_same_institution_path"]=od["institution"]["status"]=="active" and od["proposal"]["symbolic"]==("seq",(("act","repair"),("act","use"),("act","care"))) and od["proposal"]["symbolic"]!=d["proposal"]["symbolic"]
    keep("water_pump_institution",other)

    partial,g=setup12();slots=slots12(partial,ALICE)
    request=InstitutionRequest("partial",ALICE,"propose",ROOM,CUE5,g["ref"],encounter=current_encounter(partial,ALICE),slots=slots,goal=GOAL)
    partial.start("start",request);partial.advance("part",ALICE,"partial",7)
    keep("partial_institutional_work",partial)
    continued=InstitutionEngine.restore(partial.checkpoint())
    checks["partial_work_has_no_early_public_effect"]=not any(x["kind"]=="proposal" for x in partial._records11.values())
    for engine in (partial,continued):engine.advance("rest",ALICE,"partial",100000);engine.commit("commit",ALICE,"partial")
    checks["partial_work_continues_with_exact_charges_and_outputs"]=partial.checkpoint()==continued.checkpoint()
    keep("continued_institutional_work",partial)

    low,g=setup12(budget=30000)
    request=InstitutionRequest("exhausted",ALICE,"propose",ROOM,CUE5,g["ref"],encounter=current_encounter(low,ALICE),slots=slots12(low,ALICE),goal=GOAL,limit=1000000)
    low.start("start",request);low.advance("spend",ALICE,"exhausted",10000000)
    checks["exhaustion_is_retained_partial_work_not_a_rule"]=low.wallet(ALICE)["energy"]==0 and low.job_status(ALICE,"exhausted")["status"]=="partial" and not any(x["kind"]=="proposal" for x in low._records11.values())
    keep("exhausted_coordination",low)
    (out/"institution_causal_trace.json").write_text(json.dumps(readable(trace),indent=2)+"\n")
    result={"schema":"hle-u12-witness-v1","passed":all(checks.values()),"checks":checks,"check_count":len(checks),"artifacts":artifacts,
        "scope":"Deterministic development witnesses in two named material contexts; no release holdouts or efficiency claim."}
    (out/"summary.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"passed":result["passed"],"checks":len(checks),"failed":[k for k,v in checks.items() if not v]}),flush=True)
    return 0 if result["passed"] else 1


if __name__=="__main__":raise SystemExit(main())
