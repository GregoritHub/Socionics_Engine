"""Execute R12's frozen acceptance specification without claiming future runs.

Produces the exact 480-case planned individual grid and all missing gates.
No simulation, future behavior, detector or clearance result is fabricated.
"""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from hle.development_protocol import acceptance_status


def load_declaration(root=ROOT):
    directory = root / "docs/r12"
    lock = json.loads((directory / "declaration_lock_v1.json").read_text())
    for name, expected in lock["files"].items():
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != expected:
            raise ValueError("frozen declaration changed: " + name)
    return json.loads((directory / "acceptance_v1.json").read_text()), lock


def planned_panel(protocol):
    evaluation = protocol["evaluation"]
    return [{"case_id": f"{tim}.{seed}.{regime}", "tim": tim, "seed": seed,
             "resource_regime": regime, "resources": budget,
             "status": "unassessed", "executed": False}
            for tim, seed, (regime, budget) in itertools.product(
                evaluation["types"], evaluation["evaluation_seeds"], evaluation["regimes"].items())]


def specification():
    protocol, lock = load_declaration()
    digest = lock["files"]["acceptance_v1.json"]
    rows = planned_panel(protocol)
    if len(rows) != protocol["evaluation"]["individual_episodes"]:
        raise ValueError("declared case count does not match grid")
    milestones = []
    for n in range(13, 22):
        cases = [c["id"] for c in protocol["checks"] if c["milestone"] == f"R{n}"]
        milestones.append({"milestone": f"R{n}", "checks": cases,
                           "status": acceptance_status(cases, (), digest).value})
    return {"schema": "r12-executable-specification-v1", "protocol_sha256": digest,
            "milestones": milestones, "planned_individual_episodes": len(rows),
            "executed_individual_episodes": 0, "panel": rows,
            "note": "This is the frozen executable specification, not R13–R21 acceptance evidence."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "evidence/r12/executable_specification.json")
    args = parser.parse_args()
    data = specification()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, indent=2) + "\n")
    print(json.dumps({"frozen_specification_valid": True,
        "planned_individual_episodes": data["planned_individual_episodes"],
        "executed_individual_episodes": 0, "future_milestones_unassessed": len(data["milestones"]),
        "protocol_sha256": data["protocol_sha256"]}))


if __name__ == "__main__":
    main()
