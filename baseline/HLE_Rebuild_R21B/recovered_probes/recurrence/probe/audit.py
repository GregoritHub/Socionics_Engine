"""Independent final-artifact completeness and receipt-accounting checks."""
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path

from hle.codec import loads

ROOT = Path(__file__).resolve().parents[1]


def run():
    evidence = ROOT / "evidence"
    plan = json.loads((ROOT / "docs/acceptance.json").read_text())
    summary = json.loads((evidence / "summary.json").read_text())
    rows = [json.loads(line) for line in (evidence / "trials.jsonl").read_text().splitlines()]
    static_expected = {(s, layout, p) for s in plan["seeds"] for layout in plan["static_layouts"] for p in plan["policies"]}
    dynamic_expected = {(r, at, p) for r in range(1, 22) for at in plan["dynamic"]["update_slots"] for p in plan["dynamic"]["policies"]}
    static = [r for r in rows if r["condition"] == "static"]
    dynamic = [r for r in rows if r["condition"] == "dynamic"]
    assert len(rows) == 450 == summary["trajectories"]
    assert [r["id"] for r in rows] == list(range(450))
    assert {(r["seed"], r["layout"], r["policy"]) for r in static} == static_expected
    assert {(r["changed_cue"], r["update_slot"], r["policy"]) for r in dynamic} == dynamic_expected
    assert sum(r["actions"]["count"] for r in rows) == 4410 == summary["physical_actions"]
    checks = 0
    for row in rows:
        assert [s["budget"] for s in row["snapshots"]] == plan["budgets"]
        for s in row["snapshots"]:
            assert s["correct"] + s["wrong"] + s["unknown"] == s["targets"] == len(s["choices"])
            assert 0 <= s["recall_energy"] == s["recall_time"] <= s["budget"]
        assert row["actions"]["count"] == len(row["actions"]["events"])
        assert row["actions"]["energy"] == row["actions"]["time"]
        checks += 1
    aggregates = json.loads((evidence / "aggregates.json").read_text())
    for a in aggregates:
        subset = [s for r in rows if (r["condition"], r["layout"], r["policy"]) ==
            (a["condition"], a["layout"], a["policy"]) for s in r["snapshots"] if s["budget"] == a["budget"]]
        assert len(subset) == a["cases"]
        assert sum(s["correct"] for s in subset) == a["correct"]
        assert sum(s["targets"] for s in subset) == a["targets"]
        assert a["accuracy"] == a["correct"] / a["targets"]
    # Independently count charged WorkRecords from every selected engine journal.
    billed = 0
    for chosen in summary["selected_checkpoints"]:
        row = rows[chosen["trial"]]
        envelope = json.loads(gzip.open(ROOT / chosen["checkpoint"], "rt").read())
        cp = loads(envelope["body"]["world"])
        costs = Counter()
        for tx in cp.journal:
            command = tx.command
            if command is not None and command.command_id.startswith("probe:"):
                for work in tx.works:
                    for amount in work.charged:
                        costs[amount.unit.key] += amount.amount
        assert costs["r2.energy_quantum"] == row["recall_energy"]
        assert costs["r2.time_quantum"] == row["recall_time"]
        assert hashlib.sha256(envelope["body"]["world"].encode()).hexdigest() == row["world_sha256_before_actions"]
        billed += 1
    result = {"complete": True, "trajectories_checked": checks, "aggregate_rows_checked": len(aggregates),
        "selected_journals_billed_independently": billed, "physical_actions": 4410,
        "declaration_sha256": hashlib.sha256((ROOT / "docs/acceptance.json").read_bytes()).hexdigest()}
    assert result["declaration_sha256"] == summary["declaration_sha256"]
    (evidence / "artifact_audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    run()
