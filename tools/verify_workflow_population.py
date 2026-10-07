"""Standalone FB5.1 raw verifier; no scheduler, selector, engine or fixture import."""
import gzip
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "baseline/HLE_Rebuild_R21B")]

from hle_unified.compact import unseal
from hle_unified.material import OperationStore
from hle_unified.population_audit import audit_population
from hle_unified.selection_records import loads


CASES = ("fair", "interrupted", "material-feedback", "repetition", "exhaustion", "mixed")
ENGINE_SCHEMA = "hle-full-crux-c7-workflow-selection-v4"


def identity(path):
    return dict(file=path.name, bytes=path.stat().st_size,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def verify(folder):
    rows = []
    for name in CASES:
        engine_path = folder / (name + "-engine.json.gz")
        state_path = folder / (name + "-population.json.gz")
        raw = unseal(gzip.decompress(engine_path.read_bytes()).decode(), ENGINE_SCHEMA)
        transactions = OperationStore.restore(raw["world"]).journal()
        state = loads(gzip.decompress(state_path.read_bytes()).decode())
        report = audit_population(transactions, state)
        rows.append(dict(case=name, engine=identity(engine_path), population=identity(state_path),
                         turns=state["turn"], counts=state["counts"], stops=state["stopped"],
                         audit=report))
    result = dict(passed=len(rows) == len(CASES) and all(x["audit"]["passed"] for x in rows),
                  raw_worlds=len(rows), participant_replay=False,
                  total_turns=sum(x["turns"] for x in rows),
                  modeled_energy=sum(x["audit"]["modeled_energy"] for x in rows), rows=rows)
    (folder / "independent_verification.json").write_text(json.dumps(result, indent=2, default=str) + "\n")
    assert result["passed"]
    print("PASS", json.dumps({k: v for k, v in result.items() if k != "rows"}), flush=True)
    return result


if __name__ == "__main__":
    verify(Path(sys.argv[1]))
