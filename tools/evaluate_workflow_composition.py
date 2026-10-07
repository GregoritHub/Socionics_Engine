"""Save the prospective FB4.1 five-family panel and five ablations."""
import json
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "baseline/HLE_Rebuild_R21B")]

from hle_unified.workflow_composition_audit import audit_pair
from tests_workflow_composition.fixtures import FAMILIES, pair
from tools.evaluate_workflow_selection import manifest, save


def main(out):
    out.mkdir(parents=True, exist_ok=False)
    freeze = manifest()
    (out / "source_freeze.json").write_text(json.dumps(freeze, indent=2) + "\n")
    rows = []
    for family in FAMILIES:
        witness = ablation = None
        try:
            witness, ablation, _, _ = pair(family)
            report = audit_pair(witness.world.journal(), witness.access.checkpoint(),
                                ablation.world.journal(), ablation.access.checkpoint(), family)
            rows.append({"family": family, "audit": report,
                         "witness": save(out, family, witness),
                         "ablation": save(out, family + "-ablation", ablation)})
            (out / "rows.json").write_text(json.dumps(rows, indent=2, default=str) + "\n")
            print("PASS", family, flush=True)
        except Exception:
            (out / (family + "-failure.txt")).write_text(traceback.format_exc())
            if witness is not None:
                save(out, family + "-failed-witness", witness)
            if ablation is not None:
                save(out, family + "-failed-ablation", ablation)
            raise
    unchanged = manifest() == freeze
    summary = {"passed": unchanged and len(rows) == 5, "families": len(rows),
               "witness_worlds": len(rows), "ablation_worlds": len(rows),
               "raw_worlds": len(rows) * 2, "source_unchanged": unchanged}
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    assert summary["passed"]


if __name__ == "__main__":
    main(Path(sys.argv[1]))
