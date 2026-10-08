"""Build the Release 1.0 joint section-9 ledger from immutable raw evidence.

The builder does not execute the engine and does not promote historical prose to
evidence.  Every evidentiary field is a content-addressed reference to a saved
world/checkpoint.  Batch 6.2 may add its freeze acceptance at
``evidence/FB6.2/Acceptance.json``; until then section 9.12 remains open.
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

ARCHIVES = {
    "c2": {
        "file_name": "HLE_Full_Crux_C2_Evidence_v1.zip",
        "library_file_id": "libfile_a72d37ac5fac81919ca066a12838b50b",
        "file_id": "file_00000000952481f5aca66d3980d18c7b",
        "bytes": 2735649,
        "sha256": "95af2c60593235d3b53c6130128366a09aca780aaea04cee999e4ad2e7fe2361",
    },
    "c3": {
        "file_name": "HLE_Full_Crux_C3_Evidence_v1(1).zip",
        "library_file_id": "libfile_b45be6b185ac8191a1a7cf08198703e8",
        "file_id": "file_00000000146081f599f053bfd8e68e50",
        "bytes": 12788947,
        "sha256": "f666109201031836050c70c6048e6b24276ce7003058d5a74496dc1ffbee66b8",
    },
    "c4": {
        "file_name": "HLE_Full_Crux_C4_Evidence_v1.zip",
        "library_file_id": "libfile_3632e1b9d7648191976b4dc452d29ad5",
        "file_id": "file_0000000032cc81f5880da1e507c38f68",
        "bytes": 7963085,
        "sha256": "ff1eb74a11ff37b0d843ed09db5a6525c68d5c242d4fd0e849052fc9edb17dc1",
    },
    "c5": {
        "file_name": "HLE_Full_Crux_C5_Evidence_v1.zip",
        "library_file_id": "libfile_ac4f6303a49c81918fccf9135a272e79",
        "file_id": "file_000000005b4481f5b1f80cd7cf32de43",
        "bytes": 29026838,
        "sha256": "cd10349fee7ddf13d80e0ab4b5154266ef1d7c88776cd5f27ecc939b667d8f7d",
    },
    "c7_original": {
        "file_name": "HLE_Full_Crux_C7_Evidence_v2.zip",
        "library_file_id": "libfile_9d4b7893f3b48191b58467a74f80cc46",
        "bytes": 361646273,
        "sha256": "5a43c6d53a52df0884dd53b6ac2e3bf778696aae472aad9bea6b71148639783d",
    },
    "fb2.4": {
        "file_name": "Socionics_Final_Build_FB2.4_Attempt3_Evidence.zip",
        "library_file_id": "libfile_ca3933d078fc8191ac1df6c631d97e0f",
        "file_id": "file_00000000dea481f5b361019b8f20ed7f",
        "bytes": 73482270,
        "sha256": "941c387212198241d669ef7b49c909cdb5a853baaf20c02f8d965b829af0ad52",
    },
    "fb3.1": {
        "file_name": "Socionics_Final_Build_FB3.1_Evidence.zip",
        "library_file_id": "libfile_97794a2fa93481918309e115ce4f01fe",
        "file_id": "file_00000000ecb881f5b29d0a5bee2aa32c",
        "bytes": 15310983,
        "sha256": "519b1c94f698e46d81791930440dff22e1e3a5d87f26c45dd0d7b64020004aab",
    },
    "fb3.2": {
        "file_name": "Socionics_Final_Build_FB3.2_Attempt3_Evidence.zip",
        "library_file_id": "libfile_e02a7f94f60c819198310b348649412d",
        "file_id": "file_00000000e44081f5aec9fb5a61827e1b",
        "bytes": 27041446,
        "sha256": "78a25d3d9357493152bc72e4be1c06b8d808b18fd50b2069e8e27f3ca4c855f6",
    },
    "fb4.1": {
        "file_name": "Socionics_Final_Build_FB4.1_Evidence.zip",
        "library_file_id": "libfile_c06cafc408b88191803a984a832c736e",
        "file_id": "file_000000008c84820ea5464b573df75ed2",
        "bytes": 2024755,
        "sha256": "af9db4a060b9365d8ad83982b15c374866fac15b1829578fa30b02ac5a0eacc4",
    },
    "fb4.2": {
        "file_name": "Socionics_Final_Build_FB4.2_Evidence.zip",
        "library_file_id": "libfile_3e917d8d23e48191a155c6d7defd9975",
        "file_id": "file_0000000041e88246b68a700c013dacdb",
        "bytes": 4757794,
        "sha256": "bcc3c2e356974fee501be7dcd026d251afed62a2166f246ef21af19219b08741",
    },
    "fb5.5": {
        "file_name": "Socionics_Final_Build_FB5.5_Evidence.zip",
        "library_file_id": "libfile_13c0fc1d0320819192b1df6a596fba06",
        "file_id": "file_00000000744c82069f11e03bcfd7c6ee",
        "bytes": 11088803,
        "sha256": "6b937ad3d27409426bebf8b4e622bafb768a848b75122c71fe2a005bb0df864e",
    },
    "fb5.6": {
        "file_name": "Socionics_Final_Build_FB5.6_Evidence.zip",
        "library_file_id": "libfile_724e93ce09008191a105e54d8e66b9fb",
        "file_id": "file_000000000cfc8206a734e46eb53cef7d",
        "bytes": 11427947,
        "sha256": "6cb06f34991b9c83c6b3fd976124951b54f62d9257cf9d6c2126981231bda9ba",
    },
}

FAMILIES = {
    ("Theorize", "accumulation"): ("01", "theorize-apply-embody"),
    ("Apply", "expenditure"): ("01", "theorize-apply-embody"),
    ("Embody", "expenditure"): ("01", "theorize-apply-embody"),
    ("Share", "accumulation"): ("02", "share-commune-identify"),
    ("Commune", "expenditure"): ("02", "share-commune-identify"),
    ("Identify", "expenditure"): ("02", "share-commune-identify"),
    ("Coordinate", "expenditure"): ("03", "coordinate-mobilize"),
    ("Mobilize", "expenditure"): ("03", "coordinate-mobilize"),
    ("Institutionalize", "expenditure"): ("04", "institutionalize-educate"),
    ("Educate", "accumulation"): ("04", "institutionalize-educate"),
    ("Organize", "expenditure"): ("05", "organize-integrate-apply"),
    ("Integrate", "expenditure"): ("05", "organize-integrate-apply"),
}


def load(path: Path):
    data = path.read_bytes()
    if path.suffix == ".gz":
        data = gzip.decompress(data)
    return json.loads(data)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record_source_freeze(run_dir: Path, protocol: Path) -> dict:
    repository = Path(__file__).resolve().parents[1]
    paths = (
        Path(__file__).resolve(),
        repository / "tools/verify_c7_final.py",
        protocol.resolve(),
    )
    freeze = {
        str(path.relative_to(repository)): digest(path)
        for path in paths
    }
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "source_freeze.json").write_text(json.dumps(freeze, indent=2, sort_keys=True) + "\n")
    return freeze


def raw_ref(root: Path, archive: str, member: str) -> dict:
    path = root / member
    if not path.is_file():
        raise FileNotFoundError(path)
    if path.suffix == ".gz":
        value = load(path)
        if not isinstance(value, dict):
            raise ValueError(f"raw world is not an object: {member}")
    return {
        "archive": archive,
        "member": member,
        "sha256": digest(path),
        "bytes": path.stat().st_size,
    }


def canonical_base(root: Path, route: str, face: str) -> tuple[dict, dict, dict]:
    level = "C2" if route in SELF_ROUTES else "C3"
    archive = level.lower()
    base = f"HLE_Full_Crux_{level}_Evidence_v1/witnesses/{route.lower()}-{face}"
    result = load(root / base / "result.json")
    ablated = load(root / (base + "-ablated") / "result.json")
    assert result["route"] == route and result["polarity"] == face
    assert result["raw_audit_passed"] and result["exact_restore"]
    assert not result["control"] and result["terminal_status"] == "succeeded"
    assert ablated["control"] and not ablated["raw_audit_passed"]
    assert ablated["control_rejection"]
    assert result["consequence"] != ablated["consequence"]
    assert result["movement_spending"] == ablated["movement_spending"]
    return (
        raw_ref(root, archive, base + "/engine.checkpoint.json.gz"),
        raw_ref(root, archive, base + "-ablated/engine.checkpoint.json.gz"),
        result,
    )


def type_refs(root: Path, setting: str, route: str, face: str) -> dict:
    if setting == "canonical":
        folder, archive = "evidence_c6/types_final", "c7_original"
        manifest = f"{folder}/summary.json"
    else:
        folder, archive = "evidence/FB2.4/attempt3/matrix", "fb2.4"
        manifest = f"{folder}/rows.json"
    return {
        "manifest": raw_ref(root, archive, manifest),
        "representative_world": raw_ref(root, archive, f"{folder}/iee-{route}-{face}.json.gz"),
        "type_cases": len(TYPES),
    }


def selection_refs(root: Path, setting: str, route: str, face: str) -> dict:
    if setting == "canonical":
        folder, archive = "evidence_c6/panel_final", "c7_original"
    else:
        folder, archive = "evidence/FB2.4/attempt3/matrix", "fb2.4"
    return {
        "witness": raw_ref(root, archive, f"{folder}/iee-{route}-{face}.json.gz"),
        "control": raw_ref(root, archive, f"{folder}/iee-{route}-{face}-control.json.gz"),
    }


def shell_refs(root: Path, setting: str, route: str, face: str) -> dict:
    if setting == "canonical":
        admission = "evidence_c5/admission_panel_final"
        active = "evidence_c5/active_panel_attempt1"
        return {
            "prevention": {
                "deformed": raw_ref(root, "c5", f"{admission}/{route}-{face}-deformed.json.gz"),
                "corrected": raw_ref(root, "c5", f"{admission}/{route}-{face}-corrected.json.gz"),
            },
            "active_interruption": {
                "deformed": raw_ref(root, "c5", f"{active}/{route}-{face}-deformed.json.gz"),
                "corrected": raw_ref(root, "c5", f"{active}/{route}-{face}-corrected.json.gz"),
            },
        }
    admission = "evidence/FB3.1/attempt2/matrix"
    active = "evidence/FB3.2/attempt3/matrix"
    longitudinal = "evidence/FB5.6/attempt4/matrix"
    return {
        "prevention": {
            "deformed": raw_ref(root, "fb3.1", f"{admission}/{route}-{face}-deformed.json.gz"),
            "corrected": raw_ref(root, "fb3.1", f"{admission}/{route}-{face}-corrected.json.gz"),
        },
        "active_interruption": {
            "deformed": raw_ref(root, "fb3.2", f"{active}/{route}-{face}-interrupted.json.gz"),
            "control": raw_ref(root, "fb3.2", f"{active}/{route}-{face}-control.json.gz"),
        },
        "longitudinal_controls": [
            raw_ref(root, "fb5.6", f"{longitudinal}/iee-02-exact-correction-witness.json.gz"),
            raw_ref(root, "fb5.6", f"{longitudinal}/iee-04-same-target-recurrence.json.gz"),
            raw_ref(root, "fb5.6", f"{longitudinal}/iee-05-changed-target-recurrence.json.gz"),
            raw_ref(root, "fb5.6", f"{longitudinal}/unsupported-salience-still-interrupted.json.gz"),
        ],
    }


def composition_refs(root: Path, setting: str, route: str, face: str) -> dict:
    family = FAMILIES.get((route, face))
    if family is None:
        return {"applicable": False, "reason_code": "not_a_principal_step_in_declared_five_family_panel"}
    number, slug = family
    if setting == "canonical":
        base = f"HLE_Full_Crux_C4_Evidence_v1/witnesses/{number}"
        refs = [
            raw_ref(root, "c4", base + "-healthy/engine.checkpoint.json.gz"),
            raw_ref(root, "c4", base + "-control/engine.checkpoint.json.gz"),
        ]
    else:
        base = "evidence/FB4.1/attempt3/matrix"
        refs = [
            raw_ref(root, "fb4.1", f"{base}/{slug}.json.gz"),
            raw_ref(root, "fb4.1", f"{base}/{slug}-ablation.json.gz"),
        ]
    return {"applicable": True, "family": slug, "worlds": refs}


def nesting_refs(root: Path, setting: str) -> dict:
    if setting == "canonical":
        base = "HLE_Full_Crux_C4_Evidence_v1/witnesses"
        names = ("06-healthy", "06-control", "07-healthy", "07-control", "08-cancelled-child")
        worlds = [raw_ref(root, "c4", f"{base}/{name}/engine.checkpoint.json.gz") for name in names]
    else:
        base = "evidence/FB4.2/attempt3/matrix"
        rows = load(root / base / "parent_rows.json")
        worlds = [raw_ref(root, "fb4.2", f"{base}/{row['world']['file']}") for row in rows]
    return {"applicable": True, "scope": "release_panel", "worlds": worlds}


def partial_refs(root: Path, setting: str, route: str, face: str, base_world: dict) -> list[dict]:
    if setting == "canonical":
        return [
            base_world,
            raw_ref(root, "c4", "HLE_Full_Crux_C4_Evidence_v1/witnesses/08-cancelled-child/engine.checkpoint.json.gz"),
        ]
    folder = "evidence/FB3.2/attempt3/matrix/continuations"
    return [
        raw_ref(root, "fb3.2", f"{folder}/{route}-{face}-{suffix}.json.gz")
        for suffix in ("checkpoint", "original", "restored")
    ]


def face_refs(root: Path, setting: str, route: str) -> list[dict]:
    if setting == "canonical":
        return [canonical_base(root, route, face)[0] for face in FACES]
    folder = "evidence/FB4.2/attempt3/matrix"
    return [raw_ref(root, "fb4.2", f"{folder}/{route}-{face}.json.gz") for face in FACES]


def sustained_ref(root: Path, route: str, face: str) -> dict:
    rows = load(root / "evidence/FB5.5/attempt1/rows.json")
    row = next(item for item in rows if item["name"] == route and item["face"] == face)
    return raw_ref(root, "fb5.5", f"evidence/FB5.5/attempt1/{row['witness']['file']}")


def release_freeze_status(root: Path) -> tuple[bool, list[dict]]:
    acceptance = root / "evidence/FB6.2/Acceptance.json"
    if not acceptance.is_file():
        return False, []
    value = load(acceptance)
    if value.get("passed") is not True or value.get("source_unchanged") is not True:
        return False, []
    refs = []
    for item in value.get("raw_worlds", []):
        refs.append(raw_ref(root, "fb6.2", item))
    return bool(refs), refs


def setting_entry(root: Path, setting: str, route: str, face: str, freeze_ok: bool, freeze_refs: list[dict]) -> dict:
    canonical_world, canonical_control, _ = canonical_base(root, route, face)
    if setting == "canonical":
        semantics, control = canonical_world, canonical_control
        costs = canonical_world
    else:
        folder = "evidence_c7_settings/matrix_final"
        semantics = raw_ref(root, "c7_original", f"{folder}/iee-{route}-{face}.json.gz")
        control = raw_ref(root, "c7_original", f"{folder}/iee-{route}-{face}-control.json.gz")
        costs = sustained_ref(root, route, face)
    types = type_refs(root, setting, route, face)
    selection = selection_refs(root, setting, route, face)
    shell = shell_refs(root, setting, route, face)
    composition = composition_refs(root, setting, route, face)
    nesting = nesting_refs(root, setting)
    partial = partial_refs(root, setting, route, face, semantics)
    faces = face_refs(root, setting, route)
    requirements = {
        "9.1": {"status": "passed", "evidence_fields": ["implemented_semantics", "downstream_consequence"]},
        "9.2": {"status": "passed", "evidence_fields": ["type_matrix"]},
        "9.3": {"status": "passed", "evidence_fields": ["implemented_semantics"]},
        "9.4": {"status": "passed", "evidence_fields": ["controls"]},
        "9.5": ({"status": "passed", "evidence_fields": ["composition"]}
                if composition["applicable"] else {"status": "not_applicable", "reason_code": composition["reason_code"]}),
        "9.6": {"status": "passed", "evidence_fields": ["polarity_pair"]},
        "9.7": {"status": "passed", "evidence_fields": ["implemented_semantics", "controls"]},
        "9.8": {"status": "passed", "evidence_fields": ["partial_and_failed"]},
        "9.9": {"status": "passed", "evidence_fields": ["shell"]},
        "9.10": {"status": "passed", "evidence_fields": ["automatic_selection"]},
        "9.11": {"status": "passed", "evidence_fields": ["nesting"], "scope": "release_panel"},
        "9.12": ({"status": "passed", "evidence": freeze_refs, "scope": "release_freeze"}
                 if freeze_ok else {"status": "pending", "reason_code": "batch_6.2_release_freeze_not_present"}),
    }
    missing = [section for section, item in requirements.items() if item["status"] not in {"passed", "not_applicable"}]
    return {
        "implemented_semantics": semantics,
        "what_changed": semantics,
        "how": semantics,
        "downstream_consequence": semantics,
        "automatic_selection": selection,
        "type_matrix": types,
        "controls": {"witness": semantics, "defining_step_ablation": control},
        "shell": shell,
        "composition": composition,
        "nesting": nesting,
        "polarity_pair": faces,
        "partial_and_failed": partial,
        "costs": costs,
        "remaining_limits": (["batch_6.2_release_freeze_not_present"] if not freeze_ok else []),
        "requirements": requirements,
        "complete": not missing,
        "missing": missing,
    }


def build(root: Path, protocol: Path) -> dict:
    protocol_sha = digest(protocol)
    freeze_ok, freeze_refs = release_freeze_status(root)
    rows = []
    for route in ROUTES:
        for face in FACES:
            settings = {
                name: setting_entry(root, name, route, face, freeze_ok, freeze_refs)
                for name in ("canonical", "workflow")
            }
            missing = sorted({item for entry in settings.values() for item in entry["missing"]})
            rows.append({
                "route": route,
                "polarity": face,
                "settings": settings,
                "full_release_complete": not missing,
                "missing_items": missing,
            })
    complete = sum(row["full_release_complete"] for row in rows)
    ledger = {
        "schema": "hle-c7-final-ledger-v1",
        "status": "machine-checked evidence integration",
        "protocol": {"path": "contracts/C7_Final_Protocol_v1.json", "sha256": protocol_sha},
        "evidence_archives": ARCHIVES,
        "row_count": len(rows),
        "settings": ["canonical", "workflow"],
        "complete_cells": complete,
        "incomplete_cells": len(rows) - complete,
        "full_release_complete": complete == 32,
        "release_freeze_present": freeze_ok,
        "rows": rows,
        "not_claimed": [
            "unrestricted_human_meaning", "universal_shell_detector", "general_learning",
            "general_cross_owner_nesting", "open_ended_development", "optimization_gain",
            "release_1.1", "phase_7",
        ],
    }
    objects: list[list] = []
    object_index: dict[tuple, int] = {}

    def intern(value):
        if isinstance(value, dict):
            if {"archive", "member", "sha256", "bytes"} <= set(value):
                identity = (value["archive"], value["member"], value["sha256"], value["bytes"])
                if identity not in object_index:
                    object_index[identity] = len(objects)
                    objects.append(list(identity))
                return {"r": object_index[identity], "h": value["sha256"]}
            return {key: intern(item) for key, item in value.items()}
        if isinstance(value, list):
            return [intern(item) for item in value]
        return value

    compact = intern(ledger)
    compact["evidence_objects"] = objects
    return compact


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence_root", type=Path)
    parser.add_argument("output", type=Path, nargs="?", default=Path("C7_Final_Ledger_v1.json"))
    parser.add_argument("--protocol", type=Path, default=Path("contracts/C7_Final_Protocol_v1.json"))
    parser.add_argument("--run-dir", type=Path, default=Path("evidence/FB6.1/attempt1"))
    args = parser.parse_args()
    freeze = record_source_freeze(args.run_dir, args.protocol)
    ledger = build(args.evidence_root.resolve(), args.protocol)
    args.output.write_text(json.dumps(ledger, sort_keys=True, separators=(",", ":")) + "\n")
    print(json.dumps({
        "passed": True,
        "rows": ledger["row_count"],
        "complete_cells": ledger["complete_cells"],
        "release_freeze_present": ledger["release_freeze_present"],
        "source_freeze_files": len(freeze),
        "output": str(args.output),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
