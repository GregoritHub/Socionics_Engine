"""Save the prospective FB4.2 four-parent and sixteen-face panel."""
import json
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "baseline/HLE_Rebuild_R21B")]

from hle_unified.workflow_nesting_audit import audit_parent, audit_face_pair
from tests_workflow_nesting_faces.fixtures import parent_world, face_pair, PATHS
from tools.evaluate_workflow_selection import manifest, save


def main(out):
    out.mkdir(parents=True, exist_ok=False)
    freeze = manifest(); (out / "source_freeze.json").write_text(json.dumps(freeze, indent=2) + "\n")
    parents = []; faces = []
    for mode in ("normal", "failed-child", "membership-change", "participant-withdrawal"):
        engine = None
        try:
            engine, _ = parent_world(mode)
            report = audit_parent(engine.world.journal(), engine.access.checkpoint())
            parents.append(dict(mode=mode, audit=report, world=save(out, "parent-" + mode, engine)))
            (out / "parent_rows.json").write_text(json.dumps(parents, indent=2, default=str) + "\n")
            print("PASS parent", mode, flush=True)
        except Exception:
            (out / ("parent-" + mode + "-failure.txt")).write_text(traceback.format_exc())
            if engine is not None: save(out, "parent-" + mode + "-failed", engine)
            raise
    for route in PATHS:
        accumulation = expenditure = None
        try:
            accumulation, expenditure, _, _ = face_pair(route)
            report = audit_face_pair(accumulation.world.journal(), accumulation.access.checkpoint(),
                expenditure.world.journal(), expenditure.access.checkpoint(), route)
            faces.append(dict(route=route, audit=report,
                accumulation=save(out, route + "-accumulation", accumulation),
                expenditure=save(out, route + "-expenditure", expenditure)))
            (out / "face_rows.json").write_text(json.dumps(faces, indent=2, default=str) + "\n")
            print("PASS faces", route, flush=True)
        except Exception:
            (out / (route + "-face-failure.txt")).write_text(traceback.format_exc())
            if accumulation is not None: save(out, route + "-accumulation-failed", accumulation)
            if expenditure is not None: save(out, route + "-expenditure-failed", expenditure)
            raise
    unchanged = manifest() == freeze
    summary = dict(passed=unchanged and len(parents) == 4 and len(faces) == 16,
        parent_worlds=len(parents), face_pairs=len(faces), face_worlds=len(faces) * 2,
        raw_worlds=len(parents) + len(faces) * 2,
        converged_pairs=sum(x["audit"]["converged_final_answer"] for x in faces),
        divergent_pairs=sum(not x["audit"]["converged_final_answer"] for x in faces),
        source_unchanged=unchanged)
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    assert summary["passed"]


if __name__ == "__main__": main(Path(sys.argv[1]))
