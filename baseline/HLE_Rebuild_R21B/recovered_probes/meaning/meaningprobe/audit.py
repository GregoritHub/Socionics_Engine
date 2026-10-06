"""Independent grid, data, cost, capability, runtime and replay audit."""
from collections import Counter
import argparse
import gzip
import hashlib
import itertools
import json
from pathlib import Path

from hle.organization import OrganizationWorld
from .engine import Session

ROOT = Path(__file__).resolve().parents[1]


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(replay=True):
    evidence = ROOT / "evidence"
    plan = json.loads((ROOT / "docs/acceptance.json").read_text())
    summary = json.loads((evidence / "summary.json").read_text())
    rows = [json.loads(line) for line in (evidence / "trials.jsonl").read_text().splitlines()]
    assert digest(ROOT / "docs/acceptance.json") == summary["declaration_sha256"] == "0a1be4d91f8397dc4b2ee05902d6f5cbbd9df50f509871df3052982450bd984a"
    assert len(rows) == 92 and [r["id"] for r in rows] == list(range(92))
    expected = {(h,t,s,p) for h,t,s,p in itertools.product(plan["histories"], plan["types"], plan["seeds"], plan["policies"])}
    main = [r for r in rows if r["panel"] == "main"]
    key = lambda r: tuple(r["config"][k] for k in ("history","tim","seed","policy"))
    assert len(main) == 80 and {key(r) for r in main} == expected
    assert all(r["done"] and r["completed"] == 40 and r["config"]["budget"] == 8000 for r in main)
    scarce = [r for r in rows if r["panel"] == "scarce"]
    assert len(scarce) == 10 and {key(r) for r in scarce} == {(h,"iee",17,p) for h,p in itertools.product(plan["histories"], plan["policies"])}
    assert all(r["config"]["budget"] == 600 for r in scarce)
    controls = [r for r in rows if r["panel"] == "control"]
    assert len(controls) == 2 and {(r["config"]["discovery"],r["config"]["labels"]) for r in controls} == {("reverse","cards"),("forward","anonymous")}
    semantic_samples, actual_actions, pending_cost = 0, 0, 0
    for r in rows:
        assert r["paid_cost"] == r["receipts"]["energy"] == r["receipts"]["time"] == sum(r["cost_by_stage"].values())
        assert sum(r["receipts"]["operation_units"].values()) == r["paid_cost"]
        assert r["paid_cost"] + r["remaining_resources"][0] == r["config"]["budget"]
        assert r["remaining_resources"][0] == r["remaining_resources"][1]
        assert r["external_actor_credit"] == r["external_actor_fixture_cost"]
        assert r["setup_cost"] == 164
        assert len(r["episodes"]) == r["completed"]
        assert [e["episode"] for e in r["episodes"]] == list(range(r["completed"]))
        assert len({e["item"] for e in r["episodes"]}) == len(r["episodes"])
        assert r["receipts"]["meaning_writes"] in (r["completed"], r["completed"] + 1)
        assert all(c["operation"] == "EmbodyDraft" for c in r["receipts"]["capabilities"])
        if r["done"]: assert r["completed_phases"] == 120 and r["phase"] == [3,0]
        closed_cost = sum(e["cost"] for e in r["episodes"])
        assert closed_cost <= r["paid_cost"]
        if r["done"]: assert closed_cost == r["paid_cost"]
        pending_cost += r["paid_cost"] - closed_cost
        physical = Counter({(a["operation"],a["outcome"]):a["count"] for a in r["receipts"]["physical_actions"]})
        closed_physical = Counter((a["operation"],a["outcome"]) for e in r["episodes"] for a in e["actions"])
        assert all(physical[k] >= v for k,v in closed_physical.items())
        if r["done"]: assert physical == closed_physical
        actual_actions += sum(physical.values())
        for e in r["episodes"]:
            expected_owner = e["scene"] in ("a","c")
            if r["config"]["history"] == "west_reliable": expected_owner = not expected_owner
            if e["round"] >= 5: expected_owner = not expected_owner
            assert e["actor_owned_at_demand"] == expected_owner
            assert e["round"] == e["episode"] // 4
            assert e["end_perspective"] == "I"
            candidate = e["candidate_meaning"]
            assert candidate["samples"][-1] == (not expected_owner)
            assert candidate["check"] == (2 * sum(candidate["samples"]) >= len(candidate["samples"]))
            assert len(candidate["samples"]) <= 3
            assert candidate["scene"] == e["scene"] and candidate["cue"] == e["cue"]
            semantic_samples += 1
            invalid = sum(a["operation"] == "r2.transfer" and a["outcome"] == "failed" for a in e["actions"])
            transferred = any(a["operation"] == "r2.transfer" and a["outcome"] == "completed" for a in e["actions"])
            assert e["invalid_transfers"] == invalid
            assert e["appropriate"] == (invalid == 0 and (transferred if expected_owner else not transferred))
            frozen = r["config"]["policy"] == "frozen" and e["round"] >= 3
            assert e["published"] != frozen
            assert e["meaning_after"] == (e["meaning_before"] if frozen else candidate)
            if r["config"]["policy"] == "learned" and e["meaning_before"] is not None:
                assert e["selected_check"] == e["meaning_before"]["check"]
                assert e["selected_meaning"] == e["meaning_before"]
                if e["selected_check"]: assert e["actions"][0]["operation"] == "r2.inspect"
    # Recompute acceptance rates independently from the declared windows.
    rates = {}
    for window, rounds in (("retained",(3,4)),("adapted",(8,9))):
        for policy in plan["policies"]:
            eps = [e for r in main if r["config"]["policy"] == policy for e in r["episodes"] if e["round"] in rounds]
            assert len(eps) == 128
            rates[window,policy] = sum(e["appropriate"] for e in eps) / 128
            assert rates[window,policy] == summary[window + "_rates"][policy]
    assert rates["retained","learned"] >= .95 and rates["adapted","learned"] >= .95
    assert all(rates["retained","learned"] - rates["retained",p] >= .2 for p in ("fixed_direct","shuffled"))
    assert rates["adapted","learned"] - rates["adapted","frozen"] >= .2
    learned = [r for r in main if r["config"]["policy"] == "learned"]
    opposites = 0
    for r in learned:
        if r["config"]["history"] != "east_reliable": continue
        other = next(o for o in learned if o["config"]["history"] == "west_reliable" and all(o["config"][k] == r["config"][k] for k in ("tim","seed")))
        for a,b in zip(r["episodes"][8:12],other["episodes"][8:12]):
            assert a["cue"] == b["cue"] and a["meaning_after"]["check"] != b["meaning_after"]["check"]
            opposites += 1
    assert opposites == 32
    baseline = next(r for r in learned if r["config"]["tim"] == "iee" and r["config"]["seed"] == 17 and r["config"]["history"] == "east_reliable")
    anon = next(r for r in controls if r["config"]["labels"] == "anonymous")
    assert anon["world_sha256"] == baseline["world_sha256"] and anon["episodes"] == baseline["episodes"]
    reverse = next(r for r in controls if r["config"]["discovery"] == "reverse")
    signature = lambda r: {(e["round"],e["scene"]):(e["selected_check"],e["appropriate"],e["actions"][0]["operation"],e["meaning_after"]["check"]) for e in r["episodes"]}
    assert signature(reverse) == signature(baseline)
    assert summary["completed_circuits"] == semantic_samples
    assert summary["actual_actions"] == actual_actions
    runtime = json.loads((evidence / "runtime_identity.json").read_text())
    assert len(runtime["files"]) == 42
    assert {p.name for p in (ROOT / "hle").glob("*.py")} == set(runtime["files"])
    for name, checksum in runtime["files"].items(): assert digest(ROOT / "hle" / name) == checksum
    replays = []
    if replay:
        for selected in summary["selected_checkpoints"]:
            row = rows[selected["id"]]
            with gzip.open(ROOT / selected["path"], "rt", encoding="utf-8") as f: cp = f.read()
            assert hashlib.sha256(cp.encode()).hexdigest() == row["controller_sha256"]
            session = Session.restore(cp)
            assert session.checkpoint() == cp
            world = json.loads(cp)["body"]["world"]
            assert OrganizationWorld.restore(world).checkpoint() == world
            assert hashlib.sha256(world.encode()).hexdigest() == row["world_sha256"]
            actual = session.result()
            for k in ("episodes","paid_cost","reports","completed","pending_stage"):
                assert actual[k] == row[k]
            replays.append(row["id"])
    tests = (evidence / "tests.log").read_text()
    assert "Ran 18 tests" in tests and tests.rstrip().endswith("OK")
    result = {"audit": "passed", "grid_cases": len(rows), "owned_outcome_samples_checked": semantic_samples,
        "physical_actions_checked": actual_actions, "pending_work_units_included": pending_cost,
        "runtime_modules_unchanged": 42, "opposite_history_context_pairs": opposites,
        "fidelity_tests": 18, "M5_fidelity_and_evidence": True if replay else "replays_not_repeated",
        "controller_and_independent_engine_replays": len(replays) * 2, "replayed_case_ids": replays,
        "declaration_sha256": summary["declaration_sha256"]}
    filename = "artifact_audit.json" if replay else "quick_audit.json"
    (evidence / filename).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-replay", action="store_true")
    audit(not parser.parse_args().no_replay)
