"""Independent verifier for the 32-row Release 1.0 joint ledger.

This verifier does not import the ledger builder.  It reconstructs coverage and
gate status from saved raw evidence and only then compares that result with the
declared ledger.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path


TYPES = (
    "ile", "sei", "ese", "lii", "eie", "lsi", "sle", "iei",
    "see", "ili", "lie", "esi", "lse", "eii", "iee", "sli",
)
SELF_ROUTES = {"Contemplate", "Act", "Commune", "Integrate"}
ROUTES = (
    "Contemplate", "Act", "Express", "Share", "Theorize", "Embody",
    "Coordinate", "Organize", "Identify", "Mobilize", "Commune",
    "Institutionalize", "Understand", "Apply", "Educate", "Integrate",
)
FACES = ("accumulation", "expenditure")
FAMILY_CELLS = {
    ("Theorize", "accumulation"), ("Apply", "expenditure"),
    ("Embody", "expenditure"), ("Share", "accumulation"),
    ("Commune", "expenditure"), ("Identify", "expenditure"),
    ("Coordinate", "expenditure"), ("Mobilize", "expenditure"),
    ("Institutionalize", "expenditure"), ("Educate", "accumulation"),
    ("Organize", "expenditure"), ("Integrate", "expenditure"),
}


def load(path: Path):
    data = path.read_bytes()
    if path.suffix == ".gz":
        data = gzip.decompress(data)
    return json.loads(data)


def identity(path: Path) -> tuple[str, int]:
    data = path.read_bytes()
    if path.suffix == ".gz":
        value = json.loads(gzip.decompress(data))
        if not isinstance(value, dict):
            raise ValueError(f"saved world is not an object: {path}")
        if {"payload", "schema", "sha256"} <= set(value):
            payload = json.dumps(value["payload"], sort_keys=True, separators=(",", ":"))
            if hashlib.sha256(payload.encode()).hexdigest() != value["sha256"]:
                raise ValueError(f"sealed payload digest differs: {path}")
    return hashlib.sha256(data).hexdigest(), len(data)


def require_world(path: Path, expected_schema: str | None = None) -> None:
    value = load(path)
    if not isinstance(value, dict):
        raise ValueError(f"world is not an object: {path}")
    if expected_schema is not None and value.get("schema") != expected_schema:
        raise ValueError(f"world schema differs: {path}")


def canonical_semantics(root: Path, route: str, face: str) -> None:
    level = "C2" if route in SELF_ROUTES else "C3"
    base = root / f"HLE_Full_Crux_{level}_Evidence_v1/witnesses/{route.lower()}-{face}"
    witness = load(base / "result.json")
    control = load(base.parent / (base.name + "-ablated") / "result.json")
    if (witness.get("route"), witness.get("polarity")) != (route, face):
        raise ValueError("canonical identity differs")
    if not witness.get("raw_audit_passed") or not witness.get("exact_restore"):
        raise ValueError("canonical witness did not reconstruct/restore")
    if witness.get("terminal_status") != "succeeded" or witness.get("control"):
        raise ValueError("canonical witness terminal differs")
    if control.get("raw_audit_passed") or not control.get("control") or not control.get("control_rejection"):
        raise ValueError("canonical control was not rejected by the ordinary auditor")
    if witness.get("movement_spending") != control.get("movement_spending"):
        raise ValueError("canonical matched spending differs")
    if witness.get("consequence") == control.get("consequence"):
        raise ValueError("canonical ablation did not change consequence")
    require_world(base / "engine.checkpoint.json.gz")
    require_world(base.parent / (base.name + "-ablated") / "engine.checkpoint.json.gz")


def workflow_semantics(root: Path, route: str, face: str) -> None:
    folder = root / "evidence_c7_settings/matrix_final"
    rows = load(folder / "matrix.json")
    controls = load(folder / "controls.json")
    row = next(item for item in rows if item["type"] == "iee" and item["route"] == route and item["face"] == face)
    control = next(item for item in controls if item["route"] == route and item["face"] == face)
    if not row.get("independent_raw_audit") or not row.get("after", {}).get("next_task"):
        raise ValueError("workflow semantic witness differs")
    if not all(control.get(key) for key in ("matched_main_cost", "fixed_downstream_question", "changed_downstream")):
        raise ValueError("workflow semantic control differs")
    require_world(folder / row["raw"]["file"], "hle-full-crux-c7-workflow-v1")
    require_world(folder / control["raw"]["file"], "hle-full-crux-c7-workflow-v1")


def all_types(root: Path, route: str, face: str) -> None:
    for tim in TYPES:
        require_world(root / f"evidence_c6/types_final/{tim}-{route}-{face}.json.gz")
        require_world(root / f"evidence/FB2.4/attempt3/matrix/{tim}-{route}-{face}.json.gz")


def selection(root: Path, route: str, face: str) -> None:
    canonical = root / "evidence_c6/panel_final"
    workflow = root / "evidence/FB2.4/attempt3/matrix"
    for folder in (canonical, workflow):
        require_world(folder / f"iee-{route}-{face}.json.gz")
        require_world(folder / f"iee-{route}-{face}-control.json.gz")
    rows = load(workflow / "rows.json")
    row = next(item for item in rows if item["tim"] == "iee" and item["name"] == route and item["face"] == face)
    if row.get("good") is None or not row.get("expected_rejection"):
        raise ValueError("workflow automatic selection row differs")


def shell(root: Path, route: str, face: str) -> None:
    paths = (
        f"evidence_c5/admission_panel_final/{route}-{face}-deformed.json.gz",
        f"evidence_c5/admission_panel_final/{route}-{face}-corrected.json.gz",
        f"evidence_c5/active_panel_attempt1/{route}-{face}-deformed.json.gz",
        f"evidence_c5/active_panel_attempt1/{route}-{face}-corrected.json.gz",
        f"evidence/FB3.1/attempt2/matrix/{route}-{face}-deformed.json.gz",
        f"evidence/FB3.1/attempt2/matrix/{route}-{face}-corrected.json.gz",
        f"evidence/FB3.2/attempt3/matrix/{route}-{face}-interrupted.json.gz",
        f"evidence/FB3.2/attempt3/matrix/{route}-{face}-control.json.gz",
    )
    for name in paths:
        require_world(root / name)
    for rows_path in (
        root / "evidence/FB3.1/attempt2/matrix/rows.json",
        root / "evidence/FB3.2/attempt3/matrix/rows.json",
    ):
        rows = load(rows_path)
        if not any(row["name"] == route and row["face"] == face for row in rows):
            raise ValueError("workflow Shell row missing")


def partial(root: Path, route: str, face: str) -> None:
    folder = root / "evidence/FB3.2/attempt3/matrix/continuations"
    values = []
    for suffix in ("checkpoint", "original", "restored"):
        path = folder / f"{route}-{face}-{suffix}.json.gz"
        require_world(path)
        values.append(identity(path)[0])
    if values[1] != values[2]:
        raise ValueError("workflow continuation final worlds differ")


def faces(root: Path, route: str) -> None:
    for face in FACES:
        require_world(root / f"evidence/FB4.2/attempt3/matrix/{route}-{face}.json.gz")
    rows = load(root / "evidence/FB4.2/attempt3/matrix/face_rows.json")
    selected = [row for row in rows if row["route"] == route]
    if len(selected) != 1 or not selected[0]["audit"]["passed"]:
        raise ValueError("polarity face pair differs")


def composition_and_nesting(root: Path) -> None:
    canonical = root / "HLE_Full_Crux_C4_Evidence_v1/witnesses"
    for number in ("01", "02", "03", "04", "05"):
        require_world(canonical / f"{number}-healthy/engine.checkpoint.json.gz")
        require_world(canonical / f"{number}-control/engine.checkpoint.json.gz")
    comp = root / "evidence/FB4.1/attempt3/matrix"
    rows = load(comp / "rows.json")
    if len(rows) != 5 or not all(row["audit"]["passed"] for row in rows):
        raise ValueError("workflow family panel differs")
    for row in rows:
        require_world(comp / row["witness"]["file"])
        require_world(comp / row["ablation"]["file"])
    for name in ("06-healthy", "06-control", "07-healthy", "07-control", "08-cancelled-child"):
        require_world(canonical / f"{name}/engine.checkpoint.json.gz")
    parent = root / "evidence/FB4.2/attempt3/matrix"
    parent_rows = load(parent / "parent_rows.json")
    if len(parent_rows) != 4 or not all(row["audit"]["passed"] for row in parent_rows):
        raise ValueError("workflow nesting panel differs")
    for row in parent_rows:
        require_world(parent / row["world"]["file"])


def sustained(root: Path, route: str, face: str) -> None:
    folder = root / "evidence/FB5.5/attempt1"
    rows = load(folder / "rows.json")
    row = next(item for item in rows if item["name"] == route and item["face"] == face)
    require_world(folder / row["witness"]["file"])
    require_world(folder / row["control"]["file"])
    if row["terminal_next_task"] is None:
        raise ValueError("sustained terminal consequence missing")


def release_freeze(root: Path) -> bool:
    path = root / "evidence/FB6.2/Acceptance.json"
    if not path.is_file():
        return False
    value = load(path)
    if value.get("passed") is not True or value.get("source_unchanged") is not True:
        return False
    worlds = value.get("raw_worlds", [])
    if not worlds:
        return False
    for member in worlds:
        require_world(root / member)
    return True


def check_declared_refs(root: Path, value, checked: set[str], objects: list) -> None:
    if isinstance(value, dict):
        if {"r", "h"} <= set(value):
            try:
                archive, member, sha256, size = objects[value["r"]]
            except (IndexError, TypeError, ValueError):
                raise ValueError("evidence registry reference missing") from None
            if sha256 != value["h"]:
                raise ValueError("evidence registry reference differs")
            path = root / member
            actual_sha, actual_size = identity(path)
            if (actual_sha, actual_size) != (sha256, size):
                raise ValueError(f"declared raw identity differs: {member}")
            checked.add(member)
            return
        if {"archive", "member", "sha256", "bytes"} <= set(value):
            path = root / value["member"]
            sha, size = identity(path)
            if (sha, size) != (value["sha256"], value["bytes"]):
                raise ValueError(f"declared raw identity differs: {value['member']}")
            checked.add(value["member"])
        for item in value.values():
            check_declared_refs(root, item, checked, objects)
    elif isinstance(value, list):
        for item in value:
            check_declared_refs(root, item, checked, objects)


def verify(root: Path, ledger_path: Path, output: Path | None) -> dict:
    repository = Path(__file__).resolve().parents[1]
    freeze_path = repository / "evidence/FB6.1/attempt1/source_freeze.json"
    freeze = load(freeze_path)
    for member, expected in freeze.items():
        if identity(repository / member)[0] != expected:
            raise ValueError(f"executed source differs from FB6.1 freeze: {member}")
    composition_and_nesting(root)
    freeze_ok = release_freeze(root)
    reconstructed = {}
    for route in ROUTES:
        for face in FACES:
            canonical_semantics(root, route, face)
            workflow_semantics(root, route, face)
            all_types(root, route, face)
            selection(root, route, face)
            shell(root, route, face)
            partial(root, route, face)
            faces(root, route)
            sustained(root, route, face)
            missing = [] if freeze_ok else ["9.12"]
            reconstructed[(route, face)] = {"complete": not missing, "missing": missing}

    ledger = load(ledger_path)
    objects = ledger.get("evidence_objects", [])
    if not objects:
        raise ValueError("evidence object registry missing")
    if ledger.get("row_count") != 32 or len(ledger.get("rows", [])) != 32:
        raise ValueError("ledger row count differs")
    declared = {(row["route"], row["polarity"]): row for row in ledger["rows"]}
    if set(declared) != set(reconstructed):
        raise ValueError("ledger cell identities differ")
    checked: set[str] = set()
    agreements = []
    for key, expected in reconstructed.items():
        row = declared[key]
        if row["full_release_complete"] != expected["complete"]:
            raise ValueError(f"completion differs for {key}")
        if row["missing_items"] != expected["missing"]:
            raise ValueError(f"missing items differ for {key}")
        for setting in ("canonical", "workflow"):
            entry = row["settings"][setting]
            sections = entry["requirements"]
            if set(sections) != {f"9.{number}" for number in range(1, 13)}:
                raise ValueError(f"section set differs for {key} {setting}")
            for number in range(1, 12):
                section = f"9.{number}"
                expected_status = "not_applicable" if section == "9.5" and key not in FAMILY_CELLS else "passed"
                if sections[section]["status"] != expected_status:
                    raise ValueError(f"{section} differs for {key} {setting}")
            expected_912 = "passed" if freeze_ok else "pending"
            if sections["9.12"]["status"] != expected_912:
                raise ValueError(f"9.12 differs for {key} {setting}")
        check_declared_refs(root, row, checked, objects)
        agreements.append({"route": key[0], "polarity": key[1], "agreed": True})

    result = {
        "passed": True,
        "independent_of_builder": True,
        "reads_saved_worlds": True,
        "rows_reconstructed": len(reconstructed),
        "rows_agreed": len(agreements),
        "raw_members_hash_checked": len(checked),
        "release_freeze_present": freeze_ok,
        "complete_cells": sum(item["complete"] for item in reconstructed.values()),
        "source_freeze_files": len(freeze),
        "agreements": agreements,
    }
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "agreements"}, sort_keys=True))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence_root", type=Path)
    parser.add_argument("ledger", type=Path, nargs="?", default=Path("C7_Final_Ledger_v1.json"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    verify(args.evidence_root.resolve(), args.ledger, args.output)


if __name__ == "__main__":
    main()
