"""Fail-closed C1 release reconstruction from retained raw evidence."""
import argparse
import gzip
import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"baseline/HLE_Rebuild_R21B")]
sys.dont_write_bytecode=True
from hle_unified import codec
from hle_unified.crux_audit import audit
from hle_unified.crux_execution import CruxEngine
from tests_c1.fixtures import WithoutComparison


def read(path):return json.loads(path.read_text())
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def witnesses(directory):
    summary=read(directory/"summary.json")
    expected={"enabled-use","rejected-use","supported-model","second-target","comparison-ablated"}
    if {r["case"] for r in summary["rows"]}!=expected:raise ValueError("missing or unexpected witness")
    rows=[]
    for case in sorted(expected):
        p=directory/case; claimed=read(p/"result.json")
        cp=gzip.decompress((p/"engine.checkpoint.json.gz").read_bytes()).decode()
        if hashlib.sha256(cp.encode()).hexdigest()!=claimed["checkpoint_sha256"]:raise ValueError("checkpoint digest mismatch")
        control=case=="comparison-ablated"
        engine=(WithoutComparison if control else CruxEngine).restore(cp)
        if engine.checkpoint()!=cp:raise ValueError("checkpoint replay mismatch")
        transactions=codec.loads(gzip.decompress((p/"transactions.json.gz").read_bytes()).decode())
        access=gzip.decompress((p/"access.checkpoint.json.gz").read_bytes()).decode()
        if codec.dumps(transactions)!=codec.dumps(engine.world.journal()) or access!=engine.access.checkpoint():
            raise ValueError("raw evidence differs from executed checkpoint")
        rejection=None
        try: report=audit(transactions,access)
        except ValueError as exc:
            if not control:raise
            rejection=str(exc)
        if control and (rejection is None or "semantic content" not in rejection):
            raise ValueError("ablation did not fail its defining semantic gate")
        refs={k:codec.decode(v) for k,v in claimed["refs"].items()}
        actions={key:next(p.object for p in engine.world.resolve(refs[key]).facet(codec.RECORDS["Account"]).content
                         if p.relation=="u5.action") for key in ("before","after")}
        if (actions["before"],actions["after"])!=(claimed["before_action"],claimed["after_action"]):
            raise ValueError("reported action differs from raw retained plan")
        rows.append({"case":case,"control":control,"ordinary_semantic_acceptance":not control,
                     "control_rejection":rejection,"exact_continuation":True})
    h=read(directory/"enabled-use/result.json");c=read(directory/"comparison-ablated/result.json")
    if h["movement_spending"]!=c["movement_spending"] or (h["after_action"],c["after_action"])!=("use","inspect"):
        raise ValueError("matched causal witness missing")
    return rows


def unchanged(manifest, exceptions=()):
    diffs={p for p,sha in read(manifest).items() if not (ROOT/p).is_file() or digest(ROOT/p)!=sha}
    if diffs!=set(exceptions):raise ValueError("unexpected source changes: "+repr(sorted(diffs)))


def main():
    p=argparse.ArgumentParser();p.add_argument("--evidence",type=Path,required=True);p.add_argument("--witness-only",action="store_true")
    a=p.parse_args();root=a.evidence
    witness_rows=witnesses(root/"witnesses")
    if a.witness_only:
        (root/"witness_review.json").write_text(json.dumps({"passed":True,"rows":witness_rows},indent=2)+"\n")
        print(json.dumps({"witness_review_passed":True,"cases":len(witness_rows)}));return
    first=read(root/"final_tests/summary.json");last=read(root/"final_c1_review_tests/summary.json")
    if any(not s["passed"] or not s["source_unchanged"] or s["failures"] or s["errors"] or s["skipped"] for s in (first,last)):
        raise ValueError("required regression stage failed")
    inherited={r["test_id"] for r in first["rows"] if not r["test_id"].startswith("tests_c1.") and r["status"]=="passed"}
    current={r["test_id"] for r in last["rows"] if r["test_id"].startswith("tests_c1.") and r["status"]=="passed"}
    if len(inherited)!=454 or len(current)!=21:raise ValueError("missing distinct required tests")
    unchanged(root/"final_tests/execution_source.json",("hle_unified/crux_audit.py","tests_c1/test_execution.py"))
    unchanged(root/"final_c1_review_tests/execution_source.json")
    unchanged(root/"measurements/execution_source.json")
    metrics=read(root/"measurements/summary.json")
    if not metrics["passed"] or metrics["worker_executions"]!=36 or metrics["timed_samples"]!=30:
        raise ValueError("incomplete performance baseline")
    expected={(s,n) for s in ("shared","unique") for n in (100,1000,10000)}
    if {(r["shape"],r["inactive_records"]) for r in metrics["rows"]}!=expected:
        raise ValueError("performance coverage mismatch")
    protocol_hash=digest(ROOT/"contracts/C1_Protocol_v1.json")
    if metrics["protocol_sha256"]!=protocol_hash:raise ValueError("measurement protocol changed")
    # Reconstruct the scaling gates from every retained worker, not its summary label.
    samples=[read(p) for p in sorted((root/"measurements").glob("*.stdout.txt"))]
    if len(samples)!=36 or not all(r["exact_restore"] and r["audit_passed"] for r in samples):
        raise ValueError("missing raw measurement worker")
    if len({(r["movement_completions"],r["semantic_steps"],r["modeled_total_work"],r["next_action"]) for r in samples})!=1:
        raise ValueError("inactive history changed active behavior")
    traced=[r for r in samples if r["mode"]=="trace"]
    if len(traced)!=6 or len({(r["memory"]["resolve_calls"],r["memory"]["unique_resolved_refs"]) for r in traced})!=1:
        raise ValueError("inactive history changed active resolution count")
    result={"schema":"hle-full-crux-c1-acceptance-v1","passed":True,"milestone":"C1",
        "progress":"1/7","distinct_tests":len(inherited|current),"inherited_native_tests":len(inherited),
        "current_c1_tests":len(current),"type_condition_cases":64,"witnesses":witness_rows,
        "timed_samples":30,"traced_workers":6,"protocol_sha256":protocol_hash,
        "limits":["three bounded accumulation recipes","one actor per circuit","inspection test in a finite workshop",
                  "supplied route sequencing","no new full-Crux cell completed","initial performance baseline; no speedup claim"]}
    (root/"acceptance_summary.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({k:v for k,v in result.items() if k not in ("witnesses","limits")}),flush=True)


if __name__=="__main__":main()
