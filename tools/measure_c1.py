"""First C1 baseline: sequential isolated samples, timed and traced separately."""
import argparse
import gzip
import hashlib
import json
import os
import platform
import statistics
import subprocess
import sys
import time
import tracemalloc
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"baseline/HLE_Rebuild_R21B")]
sys.dont_write_bytecode=True
from tests_c1.fixtures import *
from hle_unified.crux_audit import audit
from hle_unified import codec


def worker(args):
    e=setup_c1(inactive=args.inactive,shared=args.shape=="shared")
    counts={"calls":0,"refs":set()}
    original=e.world.resolve
    if args.mode=="trace":
        def counted(ref):
            counts["calls"]+=1;counts["refs"].add(ref)
            return original(ref)
        e.world.resolve=counted
        tracemalloc.start()
    cpu=time.process_time();wall=time.perf_counter()
    refs=run_circuit(e)
    elapsed=time.perf_counter()-wall;cpu=time.process_time()-cpu
    memory=None
    if args.mode=="trace":
        current,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
        e.world.resolve=original
        memory={"incremental_retained_bytes":current,"incremental_peak_bytes":peak,
                "resolve_calls":counts["calls"],"unique_resolved_refs":len(counts["refs"])}
    cp=e.checkpoint();world=e.world.checkpoint()
    start=time.perf_counter();restored=CruxEngine.restore(cp);restore_seconds=time.perf_counter()-start
    assert restored.checkpoint()==cp
    start=time.perf_counter();report=audit(e.world.journal(),e.access.checkpoint());audit_seconds=time.perf_counter()-start
    next_action=next(p.object for p in e.world.resolve(refs["after"]).facet(Account).content if p.relation=="u5.action")
    result={"shape":args.shape,"inactive_records":args.inactive,"mode":args.mode,
        "active_wall_seconds":elapsed,"active_cpu_seconds":cpu,"restore_seconds":restore_seconds,
        "audit_seconds":audit_seconds,"memory":memory,"engine_checkpoint_bytes":len(cp.encode()),
        "world_checkpoint_bytes":len(world.encode()),"compressed_world_bytes":len(gzip.compress(world.encode(),mtime=0)),
        "movement_attempts":3,"movement_completions":report["c1_movements"],"semantic_steps":report["c1_semantic_steps"],
        "modeled_total_work":report["charged_energy"],"downstream_effects_demonstrated":int(next_action=="use"),
        "next_action":next_action,"exact_restore":True,"audit_passed":report["passed"]}
    print(json.dumps(result),flush=True)


def main():
    p=argparse.ArgumentParser();p.add_argument("--out",type=Path);p.add_argument("--worker",action="store_true")
    p.add_argument("--inactive",type=int,default=100);p.add_argument("--shape",choices=("shared","unique"),default="shared")
    p.add_argument("--mode",choices=("time","trace"),default="time");a=p.parse_args()
    if a.worker:return worker(a)
    if a.out is None:p.error("--out required")
    a.out.mkdir(parents=True,exist_ok=False)
    paths=sorted((ROOT/"hle_unified").glob("*.py"))+sorted((ROOT/"tests_c1").glob("*.py"))+[Path(__file__),ROOT/"contracts/C1_Protocol_v1.json"]
    source={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in paths}
    (a.out/"execution_source.json").write_text(json.dumps(source,indent=2)+"\n")
    protocol=json.loads((ROOT/"contracts/C1_Protocol_v1.json").read_text())
    rows=[];all_raw=[]
    for shape in protocol["efficiency"]["history_shapes"]:
        for inactive in protocol["efficiency"]["inactive_records"]:
            samples=[]
            for index,mode in enumerate(["time"]*protocol["efficiency"]["samples"]+["trace"]):
                command=[sys.executable,__file__,"--worker","--shape",shape,"--inactive",str(inactive),"--mode",mode]
                done=subprocess.run(command,capture_output=True,text=True,env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1"})
                stem=f"{shape}-{inactive}-{index}-{mode}"
                (a.out/(stem+".stdout.txt")).write_text(done.stdout)
                (a.out/(stem+".stderr.txt")).write_text(done.stderr)
                if done.returncode:raise RuntimeError(f"measurement worker failed: {stem}")
                raw=json.loads(done.stdout);all_raw.append(raw)
                if mode=="time":samples.append(raw)
                else:traced=raw
            row={"shape":shape,"inactive_records":inactive,"samples":len(samples),
                "median_active_wall_seconds":statistics.median(x["active_wall_seconds"] for x in samples),
                "median_active_cpu_seconds":statistics.median(x["active_cpu_seconds"] for x in samples),
                "median_restore_seconds":statistics.median(x["restore_seconds"] for x in samples),
                "median_audit_seconds":statistics.median(x["audit_seconds"] for x in samples),
                **{k:traced[k] for k in ("memory","engine_checkpoint_bytes","world_checkpoint_bytes","compressed_world_bytes",
                   "movement_attempts","movement_completions","semantic_steps","modeled_total_work","downstream_effects_demonstrated")}}
            rows.append(row)
            print(json.dumps({"completed":f"{shape}-{inactive}","median_active_seconds":row["median_active_wall_seconds"]}),flush=True)
    invariants=[(r["movement_completions"],r["semantic_steps"],r["modeled_total_work"],r["next_action"]) for r in all_raw]
    count_invariants=[(r["memory"]["resolve_calls"],r["memory"]["unique_resolved_refs"]) for r in rows]
    passed=len(set(invariants))==1 and len(set(count_invariants))==1 and all(r["exact_restore"] and r["audit_passed"] for r in all_raw)
    unchanged=all(hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==sha for f,sha in source.items())
    passed=passed and unchanged
    result={"passed":passed,"source_unchanged":unchanged,"kind":"initial baseline; no speedup claim","rows":rows,
        "worker_executions":len(all_raw),"timed_samples":sum(r["samples"] for r in rows),
        "python":sys.version,"platform":platform.platform(),
        "protocol_sha256":hashlib.sha256((ROOT/"contracts/C1_Protocol_v1.json").read_bytes()).hexdigest()}
    (a.out/"summary.json").write_text(json.dumps(result,indent=2)+"\n")
    if not passed:raise SystemExit(1)


if __name__=="__main__":main()
