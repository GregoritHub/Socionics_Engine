"""Standalone FB4.1 raw verifier; no executor, fixture, or participant replay."""
import gzip
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "baseline/HLE_Rebuild_R21B")]

from hle_unified.compact import unseal
from hle_unified.material import OperationStore
from hle_unified.workflow_composition_audit import FAMILIES, audit_pair


def read(path):
    raw = unseal(gzip.decompress(path.read_bytes()).decode(), "hle-full-crux-c7-workflow-v1")
    return raw, OperationStore.restore(raw["world"]).journal()


def identity(path):
    return {"file": path.name, "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def verify(folder):
    rows = []
    for family in FAMILIES:
        wp = folder / (family + ".json.gz")
        ap = folder / (family + "-ablation.json.gz")
        wr, wt = read(wp)
        ar, at = read(ap)
        report = audit_pair(wt, wr["access"], at, ar["access"], family)
        rows.append({"family": family, "witness": identity(wp),
                     "ablation": identity(ap), "audit": report})
    result = {"passed": len(rows) == 5 and all(r["audit"]["passed"] for r in rows),
              "families": 5, "witness_worlds": 5, "ablation_worlds": 5,
              "raw_worlds": 10, "participant_replay": False, "rows": rows}
    (folder / "independent_verification.json").write_text(json.dumps(result, indent=2, default=str) + "\n")
    assert result["passed"]
    print("PASS", json.dumps({k: v for k, v in result.items() if k != "rows"}), flush=True)
    return result


if __name__ == "__main__":
    verify(Path(sys.argv[1]))
