"""Reproducible raw witnesses and the three-question C1 evidence view."""
import argparse
import gzip
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "baseline/HLE_Rebuild_R21B")]
sys.dont_write_bytecode = True
from tests_c1.fixtures import *
from hle_unified.crux_audit import audit
from hle_unified import codec


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def pack(path, text):
    path.write_bytes(gzip.compress(text.encode(), mtime=0))


def plan_action(engine, ref):
    return next(p.object for p in engine.world.resolve(ref).facet(Account).content if p.relation == "u5.action")


def witness(out, name, **config):
    out.mkdir(parents=True, exist_ok=False)
    control = config.pop("control", False)
    e = setup_c1(engine_type=WithoutComparison if control else CruxEngine, **config)
    refs = run_circuit(e, target=config.get("target", SAW))
    if not control:
        perform(e, replace(hypothesis(e, "retheorize", target=config.get("target", SAW)), input=refs["retained"]))
        refs["new_model"] = e.job_status(ALICE, "retheorize")["binding"]
    rejected, report = None, None
    try:
        report = audit(e.world.journal(), e.access.checkpoint())
    except ValueError as exc:
        if not control: raise
        rejected = str(exc)
    if control and rejected is None:
        raise ValueError("ablation unexpectedly passed ordinary C1 acceptance")
    cp = e.checkpoint()
    restored = type(e).restore(cp)
    assert restored.checkpoint() == cp
    before, after = plan_action(e, refs["before"]), plan_action(e, refs["after"])
    state = e.world.resolve(refs["retained"]).facet(Account)
    result = {"case": name, "counterfactual_control": control, "prior": config.get("prior", "damaged"),
        "actual": config.get("actual", "serviceable"), "before_action": before, "after_action": after,
        "retained_condition": None if not state.content else state.content[0].object,
        "actual_later_event": attrs(e.world.resolve(refs["after_event"]))["outcome"],
        "what_changed": "actor-owned condition interpretation and later action policy" if before != after else "recorded interpretation; no new action choice demonstrated",
        "how": "paid hypothesis -> generated inspection trial -> received and paid-read outcome -> comparison -> retained interpretation",
        "what_becomes_possible": "native use succeeds" if after == "use" else "inspection remains selected; unsupported use is not authorized by this plan",
        "semantic_acceptance": not control, "control_rejection": rejected, "exact_continuation": True,
        "refs": {k:codec.encode(v) for k,v in refs.items()},
        "movement_spending": {key:e.job_status(ALICE,key)["spent"] for key in ("theory","trial","embody")},
        "checkpoint_sha256":hashlib.sha256(cp.encode()).hexdigest()}
    pack(out / "engine.checkpoint.json.gz", cp)
    pack(out / "transactions.json.gz", codec.dumps(e.world.journal()))
    pack(out / "access.checkpoint.json.gz", e.access.checkpoint())
    write(out / "result.json", result)
    if report: write(out / "independent_audit.json", report)
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--out",type=Path,required=True);a=parser.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    configs = [("enabled-use", {}), ("rejected-use", {"prior":"serviceable","actual":"damaged","tim":"eii"}),
        ("supported-model", {"prior":"serviceable","actual":"serviceable","tim":"sli"}),
        ("second-target", {"target":SAW2,"tim":"lii"}), ("comparison-ablated", {"control":True})]
    rows=[witness(a.out/name,name,**config) for name,config in configs]
    healthy,control=rows[0],rows[-1]
    assert healthy["movement_spending"]==control["movement_spending"]
    assert (healthy["after_action"],control["after_action"])==("use","inspect")
    write(a.out/"summary.json",{"passed":True,"witnesses":len(rows),"matched_causal_control":True,"rows":rows})
    print(json.dumps({"passed":True,"witnesses":len(rows),"matched_causal_control":True}),flush=True)


if __name__=="__main__": main()
