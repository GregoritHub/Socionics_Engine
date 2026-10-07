"""Independent raw FB5.2 verifier; no scheduler, selector, engine or fixture import."""
import gzip
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "baseline/HLE_Rebuild_R21B")]

from hle_unified.compact import unseal
from hle_unified.material import OperationStore, attrs
from hle_unified.population_audit import audit_population
from hle_unified.selection_records import loads

SCHEMA = "hle-full-crux-c7-workflow-selection-v4"
CASES = ("default-17", "default-43", "default-89", "diagnostic-17")


def identity(path):
    return dict(file=path.name, bytes=path.stat().st_size,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def verify(folder):
    rows = []
    for key in CASES:
        engine_path = folder / (key + "-engine.json.gz")
        state_path = folder / (key + "-population.json.gz")
        raw = unseal(gzip.decompress(engine_path.read_bytes()).decode(), SCHEMA)
        transactions = OperationStore.restore(raw["world"]).journal()
        state = loads(gzip.decompress(state_path.read_bytes()).decode())
        report = audit_population(transactions, state)
        profiles = sorted({attrs(v)["tim"] for tx in transactions for v in tx.versions
                           if "tim" in attrs(v) and attrs(v).get("actor") in
                           {r["fields"]["actor"] for r in state["requests"]}})
        if profiles != ["iee", "sli"]:
            raise ValueError("population type frames differ")
        rows.append(dict(case=key, profiles=profiles, audit=report,
                         engine=identity(engine_path), population=identity(state_path)))
    result = dict(passed=len(rows) == 4 and all(x["audit"]["passed"] for x in rows),
                  raw_worlds=len(rows), participant_replay=False,
                  native_completions=sum(x["audit"]["native_completions"] for x in rows),
                  repeated_outputs=sum(x["audit"]["repeated_outputs"] for x in rows), rows=rows)
    (folder / "independent_verification.json").write_text(json.dumps(result, indent=2) + "\n")
    assert result["passed"]
    print("PASS", json.dumps({k: v for k, v in result.items() if k != "rows"}), flush=True)
    return result


if __name__ == "__main__":
    verify(Path(sys.argv[1]))
