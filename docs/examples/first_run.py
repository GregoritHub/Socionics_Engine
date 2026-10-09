"""Documentation demo over existing finite fixtures; no engine implementation.

Run from any directory. Only Python's standard library and this checkout are used.
Outputs must go to a new directory so previous attempts cannot be overwritten.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "baseline/HLE_Rebuild_R21B")]

from tests_workflow_selection.fixtures import fixture, finish, consume
from hle_unified.workflow_selection_execution import WorkflowSelectionEngine
from hle_unified.workflow_selection_audit import audit as selection_audit
from tests_workflow_shell.fixtures import panel_case


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)

    # The fixture supplies a maintenance problem and owned outcome demand.
    # This is a prepared research scenario, not spontaneous goal generation.
    engine, request, opportunity = fixture("Contemplate", "accumulation")
    decision = finish(engine, request)
    consequence = consume(engine, request, opportunity)["consequence"]["next_task"]
    checked = selection_audit(engine.world.journal(), engine.access.checkpoint())
    checkpoint = engine.checkpoint()
    restored = WorkflowSelectionEngine.restore(checkpoint)
    assert restored.checkpoint() == checkpoint
    assert decision["failure"] is None and decision["child"] is not None
    assert checked["workflow_selections"] == 1 and consequence is not None
    (args.output / "automatic_checkpoint.json").write_text(checkpoint)

    # Existing panel_case checks ordinary deformed/corrected worlds and requires
    # the ordinary auditor to reject the deliberately bypassed admission gate.
    worlds, shell = panel_case("Contemplate", "accumulation")
    for arm, world in worlds.items():
        (args.output / ("shell_" + arm + "_checkpoint.json")).write_text(world.checkpoint())
    result = {
        "passed": True,
        "scenario": "prepared timed-maintenance opportunity",
        "automatic_recipe": decision["recipe"],
        "downstream_next_task": consequence,
        "automatic_selections_audited": checked["workflow_selections"],
        "checkpoint_restore_exact": restored.checkpoint() == checkpoint,
        "shell": shell,
        "scope": "documentation smoke demonstration, not the 54-job release suite",
    }
    (args.output / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(args.output.iterdir()) if p.is_file()}
    (args.output / "SHA256.json").write_text(json.dumps(hashes, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
