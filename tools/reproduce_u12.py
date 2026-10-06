"""Freeze source identity and rerun U12 plus the complete U11 reproduction panel."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True
from evaluate_u12 import source_manifest


def main():
    p=argparse.ArgumentParser();p.add_argument("--out",type=Path,required=True)
    out=p.parse_args().out.resolve();out.mkdir(parents=True,exist_ok=False)
    before=source_manifest()
    (out/"execution_source.json").write_text(json.dumps(before,indent=2)+"\n")
    digest=hashlib.sha256(json.dumps(before,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    rows=[]
    stages=(("u12","evaluate_u12.py"),("u12_witnesses","u12_witness.py"),("inherited","reproduce_u11.py"))
    def run(stage):
        name,script=stage
        command=[sys.executable,str(ROOT/"tools"/script),"--out",str(out/name)]
        start=time.perf_counter();started=datetime.now(timezone.utc).isoformat()
        r=subprocess.run(command,cwd=ROOT,env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1"},capture_output=True,text=True)
        (out/(name+".log")).write_text(r.stdout+r.stderr)
        return {"stage":name,"command":command,"started_utc":started,"seconds":time.perf_counter()-start,"exit_code":r.returncode}
    # Independent read-only processes share immutable source and distinct outputs.
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures=[pool.submit(run,stage) for stage in stages]
        for future in as_completed(futures):
            rows.append(future.result())
            (out/"progress.json").write_text(json.dumps(rows,indent=2)+"\n")
            print(json.dumps(rows[-1]),flush=True)
    rows.sort(key=lambda row:[x[0] for x in stages].index(row["stage"]))
    same=before==source_manifest()
    result={"schema":"hle-u12-reproduction-v1","rows":rows,"execution_manifest_sha256":digest,
        "execution_source_unchanged":same,"passed":same and all(r["exit_code"]==0 for r in rows)}
    (out/"summary.json").write_text(json.dumps(result,indent=2)+"\n")
    return 0 if result["passed"] else 1


if __name__=="__main__":raise SystemExit(main())
