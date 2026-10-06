"""Independently audit the complete evidence grid, bills, and action preconditions."""
from collections import Counter, defaultdict
import gzip
import hashlib
import itertools
import json
from pathlib import Path

from hle.codec import loads
from hle.demo import BOB
from hle.model_a import TYPES

ROOT = Path(__file__).resolve().parents[1]


def audit():
    e = ROOT / "evidence"
    plan = json.loads((ROOT / "docs/acceptance.json").read_text())
    summary = json.loads((e / "summary.json").read_text())
    rows = [json.loads(line) for line in (e / "trials.jsonl").read_text().splitlines()]
    assert len(rows) == 392 == summary["trajectories"]
    assert [r["id"] for r in rows] == list(range(392))
    expected = set(itertools.product(plan["regimes"], plan["actor_work_budgets"], plan["types"], plan["seeds"], plan["policies"]))
    actual = {(r["config"]["regime"], r["config"]["budget"], r["config"]["tim"], r["config"]["seed"], r["config"]["policy"]) for r in rows if r["panel"] == "main"}
    assert actual == expected and len(actual) == 360
    assert {(r["config"]["tim"], r["config"]["neutral"]) for r in rows if r["panel"] == "route_control"} == set(itertools.product(TYPES, (False, True)))
    for r in rows:
        assert r["completed"] == len(r["episodes"])
        assert [x["episode"] for x in r["episodes"]] == list(range(r["completed"]))
        assert r["recall_processing_retention_cost"] == r["receipts"]["energy"] == r["receipts"]["time"]
        assert r["recall_processing_retention_cost"] + r["remaining_resources"][0] == r["config"]["budget"]
        assert r["external_actor_credit"] == r["external_actor_fixture_cost"]
        assert r["completed_phases"] in (r["completed"] * 3, r["completed"] * 3 + 1, r["completed"] * 3 + 2)
        assert r["phase"] == [r["completed_phases"] % 9, r["completed_phases"] % 3]
        for ep in r["episodes"]:
            invalid = sum(a["operation"] == "r2.transfer" and a["outcome"] == "failed" for a in ep["actions"])
            transferred = any(a["operation"] == "r2.transfer" and a["outcome"] == "completed" for a in ep["actions"])
            assert ep["invalid_transfers"] == invalid
            assert ep["appropriate"] == (invalid == 0 and (transferred if ep["actor_owned_at_demand"] else not transferred))
        assert all(c["operation"] == "EmbodyDraft" for c in r["receipts"]["capability_creations"])
    aggregates = json.loads((e / "aggregates.json").read_text())
    for a in aggregates:
        group = [r for r in rows if r["panel"] == "main" and all(r["config"][k] == a[k] for k in ("regime", "budget", "policy"))]
        episodes = [x for r in group for x in r["episodes"]]
        assert a["runs"] == len(group) == 18
        assert a["completed_demands"] == len(episodes)
        assert a["appropriate_demands"] == sum(x["appropriate"] for x in episodes)
        assert a["invalid_transfers"] == sum(x["invalid_transfers"] for x in episodes)
        assert a["post_training_appropriate"] == sum(x["appropriate"] for x in episodes if x["episode"] > 0)
        assert a["mean_cost"] == sum(r["recall_processing_retention_cost"] for r in group) / len(group)
    billed, actions_checked, capacities_checked = 0, 0, 0
    for selected in summary["selected_checkpoints"]:
        text = gzip.open(ROOT / selected["path"], "rt", encoding="utf-8").read()
        body = json.loads(text)["body"]
        row = rows[selected["id"]]
        assert hashlib.sha256(text.encode()).hexdigest() == row["controller_checkpoint_sha256"]
        assert hashlib.sha256(body["world"].encode()).hexdigest() == row["world_sha256"]
        cp = loads(body["world"])
        ownership = {o.item: o.owner for o in cp.config.ownership}
        charges, episode_charges = Counter(), Counter()
        started = set()
        records = {}
        for tx in cp.journal:
            cmd = tx.command
            extras = getattr(tx, "extra", ())
            task = getattr(cmd, "task_id", "")
            paid = cmd is not None and cmd.command_id.startswith("paid:")
            if paid:
                index = int(task.split(":")[1])
                if index not in started and index < len(row["episodes"]):
                    ep = row["episodes"][index]
                    item = next(i for i in ownership if i.key == ep["item"])
                    assert ep["actor_owned_at_demand"] == (ownership[item] == BOB)
                    started.add(index)
                for work in tx.works:
                    for amount in work.charged:
                        charges[amount.unit.key] += amount.amount
                        if amount.unit.key == "r2.energy_quantum": episode_charges[index] += amount.amount
            for r in extras:
                if type(r).__name__ == "Enactment":
                    item = r.request.inputs[0]
                    expected_outcome = "completed" if r.request.operation.key == "r2.inspect" or ownership[item] == r.owner else "failed"
                    assert r.outcome.value == expected_outcome
                    actions_checked += 1
                if type(r).__name__ == "Capability":
                    assert type(cmd.payload).__name__ == "EmbodyDraft"
                    assert records[r.application].discrepancy
                    assert r.rule == "inspect_before_transfer"
                    capacities_checked += 1
            for change in tx.event.changes:
                if change.after is not None and change.after.relation == "owned_by":
                    ownership[change.after.subject] = change.after.object
            for r in extras: records[r.ref] = r
        assert charges["r2.energy_quantum"] == row["receipts"]["energy"]
        assert charges["r2.time_quantum"] == row["receipts"]["time"]
        for ep in row["episodes"]: assert ep["cost"] == episode_charges[ep["episode"]]
        billed += 1
    runtime = []
    baseline = ROOT.parent / "HLE_Rebuild_R11/hle"
    prior_identity = e / "runtime_identity.json"
    prior = {r["path"]: r for r in json.loads(prior_identity.read_text())} if prior_identity.exists() else {}
    for path in sorted((ROOT / "hle").glob("*.py")):
        original = baseline / path.name
        fingerprint = hashlib.sha256(path.read_bytes()).hexdigest()
        unchanged = (path.read_bytes() == original.read_bytes() if original.exists() else
            fingerprint == prior.get(path.name, {}).get("sha256") and prior[path.name]["unchanged_from_R11"])
        runtime.append({"path": path.name, "sha256": fingerprint, "unchanged_from_R11": unchanged})
    assert len(runtime) == 42 and all(r["unchanged_from_R11"] for r in runtime)
    result = {"complete": True, "trajectories": len(rows), "aggregate_rows": len(aggregates),
        "selected_journals_billed": billed, "action_preconditions_checked": actions_checked,
        "capability_origins_checked": capacities_checked,
        "declaration_sha256": hashlib.sha256((ROOT / "docs/acceptance.json").read_bytes()).hexdigest()}
    assert result["declaration_sha256"] == summary["declaration_sha256"]
    (e / "artifact_audit.json").write_text(json.dumps(result, indent=2) + "\n")
    (e / "runtime_identity.json").write_text(json.dumps(runtime, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__": audit()
