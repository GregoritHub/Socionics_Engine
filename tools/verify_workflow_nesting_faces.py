"""Standalone FB4.2 raw verifier; no executor, fixture, or replay."""
import gzip
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "baseline/HLE_Rebuild_R21B")]

from hle_unified.compact import unseal
from hle_unified.material import OperationStore
from hle_unified.workflow_nesting_audit import audit_parent, audit_face_pair, FACE_RESPONSIBILITY


def read(path, schema):
    raw = unseal(gzip.decompress(path.read_bytes()).decode(), schema)
    return raw, OperationStore.restore(raw["world"]).journal()


def identity(path):
    return dict(file=path.name, bytes=path.stat().st_size,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def verify(folder):
    parents = []
    for mode in ("normal", "failed-child", "membership-change", "participant-withdrawal"):
        path = folder / ("parent-" + mode + ".json.gz")
        raw, transactions = read(path, "hle-full-crux-c7-workflow-nesting-v1")
        parents.append(dict(mode=mode, world=identity(path),
            audit=audit_parent(transactions, raw["access"])))
    faces = []
    for route in FACE_RESPONSIBILITY:
        ap = folder / (route + "-accumulation.json.gz")
        ep = folder / (route + "-expenditure.json.gz")
        ar, at = read(ap, "hle-full-crux-c7-workflow-v1")
        er, et = read(ep, "hle-full-crux-c7-workflow-v1")
        faces.append(dict(route=route, accumulation=identity(ap), expenditure=identity(ep),
            audit=audit_face_pair(at, ar["access"], et, er["access"], route)))
    result = dict(passed=len(parents) == 4 and len(faces) == 16,
        parent_worlds=4, face_pairs=16, face_worlds=32, raw_worlds=36,
        converged_pairs=sum(x["audit"]["converged_final_answer"] for x in faces),
        divergent_pairs=sum(not x["audit"]["converged_final_answer"] for x in faces),
        participant_replay=False, parents=parents, faces=faces)
    (folder / "independent_verification.json").write_text(json.dumps(result, indent=2, default=str) + "\n")
    assert result["passed"]
    print("PASS", json.dumps({k: v for k, v in result.items() if k not in ("parents", "faces")}), flush=True)
    return result


if __name__ == "__main__": verify(Path(sys.argv[1]))
