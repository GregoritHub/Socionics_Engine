"""Execute the fixed panel; retain complete ledgers and selected full journals."""
from collections import Counter, defaultdict
import gzip
import hashlib
import itertools
import json
from pathlib import Path
import time

from hle.organization import OrganizationWorld
from .engine import Session

ROOT = Path(__file__).resolve().parents[1]


def sha(text): return hashlib.sha256(text.encode()).hexdigest()


def receipts(session):
    costs, physical, operations = Counter(), Counter(), Counter()
    capabilities, meaningful_writes = [], 0
    for tx in session.world._journal:
        cmd = tx.command
        if cmd is None or not cmd.command_id.startswith("paid:"): continue
        for work in tx.works:
            for amount in work.charged: costs[amount.unit.key] += amount.amount
            operations[work.operation.key] += sum(a.amount for a in work.charged if a.unit.key == "r2.energy_quantum")
        for m in tx.memories:
            if any(p.relation == "meaning.samples" for p in m.content): meaningful_writes += 1
        for r in getattr(tx, "extra", ()):
            if type(r).__name__ == "Capability":
                capabilities.append({"ref": r.ref.key, "operation": type(cmd.payload).__name__,
                    "application": r.application.key, "evidence": [e.key for e in r.evidence]})
            if type(r).__name__ == "Enactment": physical[(r.request.operation.key, r.outcome.value)] += 1
    if costs["r2.energy_quantum"] != session.spent or costs["r2.time_quantum"] != session.spent:
        raise AssertionError("controller cost disagrees with charged receipts")
    return {"energy": costs["r2.energy_quantum"], "time": costs["r2.time_quantum"],
        "operation_units": dict(operations), "meaning_writes": meaningful_writes,
        "capabilities": capabilities,
        "physical_actions": [{"operation": op, "outcome": outcome, "count": count} for (op, outcome), count in sorted(physical.items())]}


def aggregate(rows):
    groups = defaultdict(list)
    for row in rows:
        if row["panel"] != "control": groups[(row["panel"], row["config"]["policy"])].append(row)
    result = []
    windows = {"all": range(10), "retained": (3, 4), "transition": (5, 6, 7), "adapted": (8, 9)}
    for (panel, policy), group in sorted(groups.items()):
        for window, rounds in windows.items():
            episodes = [e for r in group for e in r["episodes"] if e["round"] in rounds]
            result.append({"panel": panel, "policy": policy, "window": window, "runs": len(group),
                "completed_runs": sum(r["done"] for r in group), "completed_demands": len(episodes),
                "planned_demands": len(group) * 4 * len(rounds),
                "appropriate": sum(e["appropriate"] for e in episodes),
                "invalid_transfers": sum(e["invalid_transfers"] for e in episodes),
                "inspections": sum(a["operation"] == "r2.inspect" for e in episodes for a in e["actions"]),
                "cost_closed_demands": sum(e["cost"] for e in episodes),
                "mean_total_paid_cost": sum(r["paid_cost"] for r in group) / len(group),
                "total_paid_cost_including_partial": sum(r["paid_cost"] for r in group),
                "invalid_transfers_including_partial": sum(a["count"] for r in group for a in r["receipts"]["physical_actions"]
                    if a["operation"] == "r2.transfer" and a["outcome"] == "failed")})
    return result


def findings(rows):
    primary = [r for r in rows if r["panel"] == "main"]
    learned = [r for r in primary if r["config"]["policy"] == "learned"]
    rate = lambda policy, rounds: sum(e["appropriate"] for r in primary if r["config"]["policy"] == policy
        for e in r["episodes"] if e["round"] in rounds) / (16 * 4 * len(rounds))
    retained = {p: rate(p, (3, 4)) for p in ("learned", "frozen", "shuffled", "fixed_direct", "fixed_cautious")}
    adapted = {p: rate(p, (8, 9)) for p in retained}
    pairs = []
    for r in learned:
        if r["config"]["history"] != "east_reliable": continue
        other = next(o for o in learned if o["config"]["history"] == "west_reliable" and
                     all(o["config"][k] == r["config"][k] for k in ("tim", "seed")))
        for a, b in zip(r["episodes"][8:12], other["episodes"][8:12]):
            pairs.append(a["cue"] == b["cue"] and a["scene"] == b["scene"] and
                         a["meaning_after"]["check"] != b["meaning_after"]["check"])
    contextual = []
    for r in learned:
        a, d = r["episodes"][8], r["episodes"][11]
        contextual.append(a["cue"] == d["cue"] and a["meaning_after"]["check"] != d["meaning_after"]["check"])
    baseline = next(r for r in learned if r["config"]["tim"] == "iee" and r["config"]["seed"] == 17 and r["config"]["history"] == "east_reliable")
    anonymous = next(r for r in rows if r["panel"] == "control" and r["config"]["labels"] == "anonymous")
    reverse = next(r for r in rows if r["panel"] == "control" and r["config"]["discovery"] == "reverse")
    semantic = lambda r: {(e["round"], e["scene"]): (e["selected_check"], e["appropriate"], e["actions"][0]["operation"], e["meaning_after"]["check"]) for e in r["episodes"]}
    label_equal = anonymous["episodes"] == baseline["episodes"] and anonymous["world_sha256"] == baseline["world_sha256"]
    order_equal = semantic(reverse) == semantic(baseline)
    m1 = all(pairs) and len(pairs) == 32 and all(r["done"] and all(e["meaning_before"] is None for e in r["episodes"][:4])
        and all(c["operation"] == "EmbodyDraft" for c in r["receipts"]["capabilities"]) for r in learned)
    m2 = retained["learned"] >= .95 and all(sum(e["appropriate"] for e in r["episodes"] if e["round"] in (3,4)) / 8 >= .95 for r in learned)
    m2 = m2 and all(retained["learned"] - retained[p] >= .20 for p in ("shuffled", "fixed_direct"))
    m3 = adapted["learned"] >= .95 and all(sum(e["appropriate"] for e in r["episodes"] if e["round"] in (8,9)) / 8 >= .95 for r in learned)
    m3 = m3 and adapted["learned"] - adapted["frozen"] >= .20
    return {"M1_experience_and_opposed_history": m1, "M2_retained_behavior": m2,
        "M3_reversal_adaptation": m3, "M4_context_and_controls": all(contextual) and label_equal and order_equal,
        "retained_rates": retained, "adapted_rates": adapted,
        "opposite_history_context_pairs": len(pairs), "all_pairs_opposing": all(pairs),
        "same_cue_opposite_context_runs": sum(contextual), "display_only_engine_equivalence": label_equal,
        "discovery_order_semantic_equivalence": order_equal,
        "R5_shell_counts": dict(Counter(p["shell"] for r in rows for p in r["reports"])),
        "R5_closure_counts": dict(Counter(p["closure"] for r in rows for p in r["reports"])),
        "R5_retained_capacity_counts": dict(Counter(p["retained_capacity"] for r in rows for p in r["reports"])),
        "M6_assessment_scope": all(p["closure"] != "established" and "clear" not in p["shell"] for r in rows for p in r["reports"])}


def run():
    start = time.monotonic()
    plan = json.loads((ROOT / "docs/acceptance.json").read_text())
    evidence = ROOT / "evidence"
    (evidence / "checkpoints").mkdir(parents=True, exist_ok=True)
    rows, saved = [], []
    def execute(config, panel, keep=False):
        session = Session(**config).run(plan["work_chunk"])
        row = session.result()
        row.update(id=len(rows), panel=panel, receipts=receipts(session))
        cp = session.checkpoint()
        row["controller_sha256"] = sha(cp)
        row["world_sha256"] = sha(session.world.checkpoint())
        if keep:
            path = evidence / "checkpoints" / f"case_{row['id']:03d}.json.gz"
            compressed = gzip.compress(cp.encode("utf-8"), mtime=0)
            temporary = path.with_suffix(".tmp")
            temporary.write_bytes(compressed); temporary.replace(path)
            if gzip.decompress(path.read_bytes()).decode("utf-8") != cp:
                raise AssertionError("saved checkpoint differs from completed execution")
            if Session.restore(cp).checkpoint() != cp: raise AssertionError("controller replay mismatch")
            if OrganizationWorld.restore(session.world.checkpoint()).checkpoint() != session.world.checkpoint():
                raise AssertionError("independent R11 replay mismatch")
            saved.append({"id": row["id"], "path": str(path.relative_to(ROOT)), "controller_replay": True, "engine_replay": True})
        rows.append(row)
    for history, tim, seed in itertools.product(plan["histories"], plan["types"], plan["seeds"]):
        for policy in plan["policies"]:
            keep = tim == "iee" and seed == 17 and (history == "east_reliable" or policy == "learned")
            execute(dict(history=history, tim=tim, seed=seed, policy=policy, budget=plan["main_budget"]), "main", keep)
        print(f"{history} {tim} seed={seed}: {len(rows)} cases", flush=True)
    for history, policy in itertools.product(plan["histories"], plan["policies"]):
        execute(dict(history=history, tim="iee", seed=17, policy=policy, budget=plan["scarce_budget"]), "scarce", history == "east_reliable")
    execute(dict(discovery="reverse"), "control", True)
    execute(dict(labels="anonymous"), "control", True)
    ledger = "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows)
    tmp = evidence / "trials.complete.tmp"
    tmp.write_text(ledger); tmp.replace(evidence / "trials.jsonl")
    if (evidence / "trials.jsonl").read_text() != ledger: raise AssertionError("incomplete ledger")
    (evidence / "aggregates.json").write_text(json.dumps(aggregate(rows), indent=2) + "\n")
    summary = {"experiment": plan["experiment"],
        "declaration_sha256": hashlib.sha256((ROOT / "docs/acceptance.json").read_bytes()).hexdigest(),
        "trajectories": len(rows), "completed_runs": sum(r["done"] for r in rows),
        "completed_circuits": sum(r["completed"] for r in rows),
        "actual_actions": sum(a["count"] for r in rows for a in r["receipts"]["physical_actions"]),
        "total_paid_units": sum(r["paid_cost"] for r in rows), "selected_checkpoints": saved,
        "selected_controller_and_engine_replays": len(saved) * 2,
        **findings(rows), "elapsed_seconds": round(time.monotonic() - start, 3)}
    (evidence / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k:v for k,v in summary.items() if k != "selected_checkpoints"}, indent=2), flush=True)


if __name__ == "__main__": run()
