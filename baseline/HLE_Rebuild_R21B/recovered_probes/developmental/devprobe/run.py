"""Execute the predeclared panel; save complete ledgers and selected journals."""
from collections import Counter, defaultdict
import gzip
import hashlib
import itertools
import json
from pathlib import Path
import time

from hle.demo import BOB
from hle.model_a import TYPES
from hle.organization import OrganizationWorld
from devprobe.engine import Session

ROOT = Path(__file__).resolve().parents[1]


def sha(value): return hashlib.sha256(value.encode()).hexdigest()


def receipts(session):
    costs = Counter()
    capabilities = []
    physical = Counter()
    for tx in session.world._journal:
        cmd = tx.command
        if cmd is None or not cmd.command_id.startswith("paid:"): continue
        for work in tx.works:
            for amount in work.charged: costs[amount.unit.key] += amount.amount
        for r in getattr(tx, "extra", ()):
            if type(r).__name__ == "Capability":
                capabilities.append({"ref": r.ref.key, "operation": type(cmd.payload).__name__,
                    "application": r.application.key, "evidence": [x.key for x in r.evidence]})
            elif type(r).__name__ == "Enactment":
                physical[(r.request.operation.key, r.outcome.value)] += 1
    if costs["r2.energy_quantum"] != session.spent or costs["r2.time_quantum"] != session.spent:
        raise AssertionError("charged work does not match controller ledger")
    return {"energy": costs["r2.energy_quantum"], "time": costs["r2.time_quantum"],
        "capability_creations": capabilities,
        "physical_actions": [{"operation": op, "outcome": status, "count": count} for (op, status), count in sorted(physical.items())]}


def aggregate(rows):
    groups = defaultdict(list)
    for r in rows:
        if r["panel"] == "main":
            c = r["config"]
            groups[(c["regime"], c["budget"], c["policy"])].append(r)
    result = []
    for (regime, budget, policy), group in sorted(groups.items()):
        episodes = [e for r in group for e in r["episodes"]]
        post = [e for e in episodes if e["episode"] > 0]
        result.append({"regime": regime, "budget": budget, "policy": policy, "runs": len(group),
            "completed_runs": sum(r["done"] for r in group), "completed_demands": len(episodes),
            "planned_demands": len(group) * 12, "appropriate_demands": sum(e["appropriate"] for e in episodes),
            "post_training_appropriate": sum(e["appropriate"] for e in post), "post_training_completed": len(post),
            "post_training_planned": len(group) * 11, "invalid_transfers": sum(e["invalid_transfers"] for e in episodes),
            "actual_failed_transfers_including_partial_circuits": sum(a["count"] for r in group for a in r["receipts"]["physical_actions"]
                if a["operation"] == "r2.transfer" and a["outcome"] == "failed"),
            "mean_cost": sum(r["recall_processing_retention_cost"] for r in group) / len(group),
            "minimum_cost": min(r["recall_processing_retention_cost"] for r in group),
            "maximum_cost": max(r["recall_processing_retention_cost"] for r in group),
            "mean_route_units_completed": sum(e["route_units"] for e in episodes) / len(group),
            "retained_capacity_established_runs": sum(any(p["study"] == "retained" and p["retained_capacity"] == "established" for p in r["reports"]) for r in group),
            "new_object_guard_uses": sum(e["heldout"] and e["guard"] is not None for e in episodes)})
    return result


def run():
    start = time.monotonic()
    plan = json.loads((ROOT / "docs/acceptance.json").read_text())
    evidence = ROOT / "evidence"
    (evidence / "checkpoints").mkdir(exist_ok=True)
    rows, saved = [], []
    def execute(config, panel, keep=False):
        session = Session(**config).run(plan["work_chunk"])
        row = session.result()
        row.update(id=len(rows), panel=panel, receipts=receipts(session))
        checkpoint = session.checkpoint()
        row["controller_checkpoint_sha256"] = sha(checkpoint)
        row["world_sha256"] = sha(session.world.checkpoint())
        if keep:
            path = evidence / "checkpoints" / f"case_{row['id']:03d}.json.gz"
            with gzip.open(path, "wt", encoding="utf-8") as f: f.write(checkpoint)
            if Session.restore(checkpoint).checkpoint() != checkpoint:
                raise AssertionError("controller continuation replay failed")
            if OrganizationWorld.restore(session.world.checkpoint()).checkpoint() != session.world.checkpoint():
                raise AssertionError("independent R11 journal replay failed")
            saved.append({"id": row["id"], "path": str(path.relative_to(ROOT)),
                "controller_replay": True, "independent_engine_replay": True})
        rows.append(row)
    for regime, budget, tim, seed in itertools.product(plan["regimes"], plan["actor_work_budgets"], plan["types"], plan["seeds"]):
        for policy in plan["policies"]:
            execute(dict(regime=regime, budget=budget, tim=tim, seed=seed, policy=policy), "main",
                tim == "iee" and seed == 17)
        if seed == plan["seeds"][-1]: print(f"{regime} budget={budget} type={tim}: {len(rows)} cases", flush=True)
    for neutral, tim in itertools.product((False, True), sorted(TYPES)):
        execute(dict(regime="volatile", budget=2400, tim=tim, seed=17, policy="coupled", neutral=neutral),
            "route_control", neutral and tim in ("iee", "lsi"))
    ledger = "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows)
    tmp = evidence / "trials.complete.tmp"
    tmp.write_text(ledger); tmp.replace(evidence / "trials.jsonl")
    if (evidence / "trials.jsonl").read_text() != ledger: raise AssertionError("incomplete final ledger")
    aggregates = aggregate(rows)
    (evidence / "aggregates.json").write_text(json.dumps(aggregates, indent=2) + "\n")
    primary = [r for r in rows if r["panel"] == "main" and r["config"]["regime"] == "volatile" and r["config"]["budget"] == 2400]
    coupled = [r for r in primary if r["config"]["policy"] == "coupled"]
    d1 = all(r["done"] and r["episodes"][0]["discrepancy"] and r["episodes"][0]["capabilities"]
        and r["episodes"][0]["guard"] is None and all(c["operation"] == "EmbodyDraft" for c in r["receipts"]["capability_creations"]) for r in coupled)
    rate = lambda policy: sum(e["appropriate"] for r in primary if r["config"]["policy"] == policy for e in r["episodes"] if e["episode"] > 0) / (18 * 11)
    d2 = all(r["done"] and all(r["episodes"][i]["guard"] is not None and r["episodes"][i]["appropriate"] for i in (1, 6, 11)) for r in coupled) and rate("coupled") >= .95
    rates = {p: rate(p) for p in plan["policies"]}
    early = {p: sum(r["episodes"][1]["guard"] is not None for r in primary if r["config"]["policy"] == p and r["completed"] >= 2) for p in plan["policies"]}
    d3 = rates["coupled"] - rates["feedback_off"] >= .20 and early["coupled"] > max(early["episode_only"], early["once_per_outer"])
    pairs = []
    for r in rows:
        if r["panel"] != "main" or r["config"]["policy"] != "coupled": continue
        matches = [o for o in rows if o["panel"] == "main" and o["config"]["policy"] == "generic_coupled"
            and all(o["config"][k] == r["config"][k] for k in ("regime", "budget", "tim", "seed"))]
        pairs.append(len(matches) == 1 and matches[0]["world_sha256"] == r["world_sha256"] and matches[0]["episodes"] == r["episodes"])
    routes = [r for r in rows if r["panel"] == "route_control"]
    neutral = [r for r in routes if r["config"]["neutral"]]
    signature = lambda r: (r["recall_processing_retention_cost"], [(e["appropriate"], e["invalid_transfers"], e["paths"]) for e in r["episodes"]])
    neutral_same = all(signature(r) == signature(neutral[0]) for r in neutral)
    summary = {"experiment": plan["experiment"], "declaration_sha256": hashlib.sha256((ROOT / "docs/acceptance.json").read_bytes()).hexdigest(),
        "trajectories": len(rows), "main_trajectories": 360, "route_controls": len(routes),
        "completed_circuits": sum(r["completed"] for r in rows),
        "actual_actions": sum(a["count"] for r in rows for a in r["receipts"]["physical_actions"]),
        "selected_checkpoints": saved, "selected_controller_and_engine_replays": 2 * len(saved),
        "D1_experience_derived_acquisition": d1, "D2_retention_and_transfer": d2,
        "D3_feedback_advantage": d3, "primary_post_training_rates": rates,
        "early_new_object_guard_uses": early, "generic_matched_pairs": len(pairs), "D5_generic_equivalence": all(pairs),
        "neutral_all_types_equal_cost_paths_outcomes": neutral_same,
        "typed_costs": {r["config"]["tim"]: r["recall_processing_retention_cost"] for r in routes if not r["config"]["neutral"]},
        "neutral_costs": {r["config"]["tim"]: r["recall_processing_retention_cost"] for r in neutral},
        "elapsed_seconds": round(time.monotonic() - start, 3)}
    (evidence / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "selected_checkpoints"}, indent=2), flush=True)


if __name__ == "__main__": run()
