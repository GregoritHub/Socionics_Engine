import hashlib
import json
from pathlib import Path
import unittest

from hle.model_a import TYPES
from tools.r12_specification import load_declaration, planned_panel, specification

ROOT = Path(__file__).resolve().parents[1]


class Specification(unittest.TestCase):
    def test_frozen_declaration_and_all_source_statuses(self):
        protocol, lock = load_declaration()
        ledger = json.loads((ROOT / "docs/r12/source_ledger_v1.json").read_text())
        for source in ledger["sources"]:
            self.assertEqual(hashlib.sha256((ROOT / source["file"]).read_bytes()).hexdigest(), source["sha256"])
        self.assertEqual(len({d["id"] for d in ledger["mechanisms"]}), len(ledger["mechanisms"]))
        for item in ledger["mechanisms"]:
            self.assertTrue(all(item[k] for k in ("status", "source", "decision", "gate")))

    def test_exact_recovered_manuscripts_match_crossing_pins(self):
        protocol = json.loads((ROOT / "baseline/crossing/crossing_protocol.json").read_text())
        available = {hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT / "reference/r12_sources").glob("*")}
        for source in protocol["sources"]:
            self.assertIn(source["sha256"], available, source["filename"])

    def test_pinned_crossing_archive_and_all_42_runtime_modules(self):
        p = ROOT / "reference/r12_input/HLE_R11_with_Content_Crossing_v1.zip"
        self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(), "1f39ace84655725dc2bcd740c28202ea2768951dafa1587510c11371ba87c324")
        modules = list((ROOT / "baseline/crossing/vendor/r11/hle").glob("*.py"))
        self.assertEqual(len(modules), 42)
        # The original R12 assertion is retained at reference/r12_tests/.
        # R13 must change codec and entrypoints. Verify historical byte identity
        # against its pinned R12 manifest, then enforce the explicit change set.
        historical = json.loads((ROOT / "docs/r13/release_manifest_R12.json").read_text())
        pins = {r["path"]: r["sha256"] for r in historical["files"]}
        changes = json.loads((ROOT / "docs/r13/Source_Changes_R13.json").read_text())
        self.assertEqual(set(changes["changed_runtime_modules"]),
                         {"hle/__init__.py", "hle/__main__.py", "hle/codec.py"})
        for p in modules:
            name = "hle/" + p.name
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(), pins[name])
            if name in ("hle/memory.py", "hle/memory_records.py"):
                from tools.r145_preservation import verify_changed
                verify_changed(ROOT,name)
                self.assertEqual(p.read_bytes(), (ROOT / "reference/r14_preserved" / name).read_bytes())
            elif name not in changes["changed_runtime_modules"]:
                self.assertEqual(p.read_bytes(), (ROOT / name).read_bytes())

    def test_all_480_cases_unexecuted_and_seeds_disjoint(self):
        protocol, _ = load_declaration()
        panel = planned_panel(protocol)
        self.assertEqual(len(panel), 480)
        self.assertEqual(len({p["case_id"] for p in panel}), 480)
        self.assertEqual(set(protocol["evaluation"]["types"]), set(TYPES))
        self.assertFalse(set(protocol["evaluation"]["development_seeds"]) & set(protocol["evaluation"]["evaluation_seeds"]))
        self.assertTrue(all(not p["executed"] and p["status"] == "unassessed" for p in panel))
        self.assertTrue(all(m["status"] == "unassessed" for m in specification()["milestones"]))

    def test_positive_and_negative_controls_cover_all_signs_and_stages(self):
        protocol, _ = load_declaration()
        self.assertEqual({c["milestone"] for c in protocol["checks"]}, {f"R{n}" for n in range(13, 22)})
        fixtures = [c for c in protocol["checks"] if c["required_run_kind"] == "fixture"]
        self.assertEqual(len(fixtures), 5)
        self.assertTrue(all(c["required"] and c["negative_control"] for c in protocol["checks"]))
        operators = json.loads((ROOT / "docs/r12/operator_registry_v1.json").read_text())["operators"]
        for op in operators:
            self.assertTrue(all(op[k] for k in ("status", "source", "domain", "effect", "failure_conditions", "gate")))

    def test_clearance_scope_and_sustained_protocol_are_fixed(self):
        p, _ = load_declaration()
        self.assertEqual(len(p["held_out_challenges"]), 12)
        self.assertEqual(len({c["family"] for c in p["held_out_challenges"]}), 3)
        self.assertEqual(p["recurrence"]["maintenance_threshold"], 3)
        self.assertEqual(p["recurrence"]["sensitivity_thresholds"], [2, 5])
        self.assertEqual(p["evaluation"]["continuation_eligible_opportunities"], 100)
        self.assertEqual(p["evaluation"]["continuation_demand_changes"], 2)
        self.assertFalse(p["evaluation"]["exclude_incomplete_from_denominator"])
