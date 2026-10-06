"""Reproduce the fixed acceptance panel. Standard library only; run from root."""
from collections import Counter, defaultdict
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
import time

from hle.contracts import WorkStatus
from hle.world_records import Attempt, INSPECT, TRANSFER
from probe.decision import decide, permitted
from probe.fixtures import ALICE, BOB, make_fixture
from probe.recurrence import CANONICAL, Session

ROOT = Path(__file__).resolve().parents[1]


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def summary_at(s, fixture, items):
    results, memories = permitted(s)
    choices = {}
    counts = Counter()
    for item in items:
        owner, action = decide(ALICE, BOB, item, results, memories)
        choices[item.key] = None if owner is None else owner.key
        counts["unknown" if owner is None else "correct" if owner == fixture.expected[item] else "wrong"] += 1
        expected_operation = TRANSFER if fixture.expected[item] == ALICE else INSPECT
        counts["appropriate"] += action.operation == expected_operation
    visits = [v.memory for r in results for v in r.visited]
    seen_cues, seen_content = set(), set()
    new_on_repeats = 0
    repeat_consultations = 0
    for r in results:
        content = {(h.memory, index) for h in r.hits for index in h.proposition_indexes}
        if len(r.query.cues) == 1 and r.query.cues[0] in seen_cues:
            repeat_consultations += 1
            new_on_repeats += len(content - seen_content)
        seen_cues.update(r.query.cues); seen_content.update(content)
    return {"correct": counts["correct"], "wrong": counts["wrong"], "unknown": counts["unknown"],
        "targets": len(items), "appropriate": counts["appropriate"], "choices": choices,
        "published_queries": len(results), "unique_visited": len(set(visits)),
        "repeated_visits": len(visits) - len(set(visits)),
        "repeat_consultations": repeat_consultations, "new_content_on_repeats": new_on_repeats,
        "finished": s.done, "completed_frames": s.index // 3 if s.phase is not None else None,
        "phase": None if s.phase is None else [s.phase.outer, s.phase.inner]}


def act(s, fixture, items):
    # All decisions use the SAME completed recall snapshot. Later action receipts
    # never feed subsequent decisions in this evaluation of retrieved memory.
    results, memories = permitted(s)
    decisions = [decide(ALICE, BOB, item, results, memories)[1] for item in items]
    before = s.world.truth.wallet(ALICE)
    rows = []
    for item, action in zip(items, decisions):
        key = f"outcome:{item.key}"
        txevent = s.world.execute(Attempt(key, key, action))
        appropriate = action.operation == (TRANSFER if fixture.expected[item] == ALICE else INSPECT)
        rows.append({"item": item.key, "operation": action.operation.key,
            "appropriate": appropriate, "outcome": txevent.outcome.value,
            "owner_after": s.world.truth.current_fact(item, "owned_by", s.world.config.context).object.key})
    after = s.world.truth.wallet(ALICE)
    return {"count": len(rows), "appropriate": sum(r["appropriate"] for r in rows),
        "completed": sum(r["outcome"] == WorkStatus.COMPLETED.value for r in rows),
        "failed": sum(r["outcome"] == WorkStatus.FAILED.value for r in rows),
        "energy": before.energy - after.energy, "time": before.time - after.time, "events": rows}


def execute_trial(base, policy, budgets, *, dynamic=None):
    f = deepcopy(base)
    s = Session(f.world, ALICE, policy, dynamic[2] if dynamic else base.seed)
    rank, update_at, seed = dynamic if dynamic else (None, None, base.seed)
    items = (f.by_cue[rank],) if dynamic else tuple(sorted(f.expected, key=lambda ref: ref.key))
    paid, update_cost, snapshots, last_publication = 0, 0, [], 0
    for slot in range(1, max(budgets) + 1):
        previous = s.index
        paid += s.step()
        if s.index != previous:
            last_publication = slot
        if dynamic and slot == update_at:
            update_cost += f.change(rank, prefix=f"external:{slot}")
        if slot in budgets:
            row = summary_at(s, f, items)
            row.update(budget=slot, recall_energy=paid, recall_time=paid, update_cost=update_cost)
            snapshots.append(row)
    checkpoint = s.checkpoint()
    state_hash = digest(s.world.checkpoint())
    action_results = act(s, f, items)
    return s, checkpoint, {"policy": policy, "seed": seed, "changed_cue": rank,
        "update_slot": update_at, "setup_energy": base.setup_energy, "recall_energy": paid,
        "recall_time": paid, "update_cost": update_cost, "last_publication_slot": last_publication,
        "world_sha256_before_actions": state_hash, "checkpoint_sha256_before_actions": digest(checkpoint),
        "snapshots": snapshots, "actions": action_results}


def aggregate(trials):
    buckets = defaultdict(list)
    for trial in trials:
        for row in trial["snapshots"]:
            buckets[(trial["condition"], trial["layout"], trial["policy"], row["budget"])].append(row)
    rows = []
    for (condition, layout, policy, budget), values in sorted(buckets.items()):
        total = sum(r["targets"] for r in values)
        rows.append({"condition": condition, "layout": layout, "policy": policy, "budget": budget,
            "cases": len(values), "targets": total,
            "correct": sum(r["correct"] for r in values), "wrong": sum(r["wrong"] for r in values),
            "unknown": sum(r["unknown"] for r in values),
            "accuracy": sum(r["correct"] for r in values) / total,
            "mean_recall_energy": sum(r["recall_energy"] for r in values) / len(values),
            "mean_repeated_visits": sum(r["repeated_visits"] for r in values) / len(values),
            "new_content_on_repeats": sum(r["new_content_on_repeats"] for r in values)})
    return rows


def run():
    begin = time.monotonic()
    declaration = ROOT / "docs/acceptance.json"
    plan = json.loads(declaration.read_text())
    evidence = ROOT / "evidence"
    evidence.mkdir(exist_ok=True)
    (evidence / "checkpoints").mkdir(exist_ok=True)
    trials, selected = [], []
    def record(trial, session, checkpoint, save):
        trial["id"] = len(trials)
        if save:
            path = evidence / "checkpoints" / f"trial_{trial['id']:03d}.json.gz"
            with gzip.open(path, "wt", encoding="utf-8") as stream:
                stream.write(checkpoint)
            restored = Session.restore(checkpoint)
            if restored.checkpoint() != checkpoint:
                raise AssertionError("selected checkpoint did not replay exactly")
            action_path = evidence / "checkpoints" / f"trial_{trial['id']:03d}_after_actions.json.gz"
            with gzip.open(action_path, "wt", encoding="utf-8") as stream:
                stream.write(session.world.checkpoint())
            from hle.organization import OrganizationWorld
            if OrganizationWorld.restore(session.world.checkpoint()).checkpoint() != session.world.checkpoint():
                raise AssertionError("selected physical action journal did not replay exactly")
            selected.append({"trial": trial["id"], "checkpoint": str(path.relative_to(ROOT)),
                "action_checkpoint": str(action_path.relative_to(ROOT)), "replayed": True})
        trials.append(trial)
        with (evidence / "trials.jsonl").open("a") as out:
            out.write(json.dumps(trial, sort_keys=True) + "\n")
    (evidence / "trials.jsonl").write_text("")
    for layout in plan["static_layouts"]:
        for seed in plan["seeds"]:
            base = make_fixture(seed, layout); base.seed = seed
            for policy in plan["policies"]:
                session, checkpoint, trial = execute_trial(base, policy, plan["budgets"])
                trial.update(condition="static", layout=layout)
                record(trial, session, checkpoint, seed == plan["seeds"][0] and policy in
                    (CANONICAL, "same_order_unique", "batch_unique"))
            print(f"static {layout} seed={seed}: {len(trials)} trajectories", flush=True)
    dynamic = plan["dynamic"]
    base = make_fixture(dynamic["seed"]); base.seed = dynamic["seed"]
    for update_at in dynamic["update_slots"]:
        for rank in range(1, 22):
            for policy in dynamic["policies"]:
                session, checkpoint, trial = execute_trial(base, policy, plan["budgets"],
                    dynamic=(rank, update_at, base.seed))
                register = "Identity" if rank >= 19 else "Ego" if rank >= 10 else "Super-Ego"
                trial.update(condition="dynamic", layout=register)
                record(trial, session, checkpoint, rank in (1, 19) and policy in
                    (CANONICAL, "same_order_unique", "batch_unique", "generic_same_sequence"))
        print(f"dynamic update={update_at}: {len(trials)} trajectories", flush=True)
    # Persist one complete final ledger. Incremental progress rows are useful
    # during execution, but are never the authoritative final artifact.
    ledger = "".join(json.dumps(t, sort_keys=True) + "\n" for t in trials)
    final_ledger = evidence / "trials.jsonl"
    temporary = evidence / "trials.complete.tmp"
    temporary.write_text(ledger)
    temporary.replace(final_ledger)
    if final_ledger.read_text() != ledger:
        raise AssertionError("final evidence ledger did not persist exactly")
    totals = aggregate(trials)
    (evidence / "aggregates.json").write_text(json.dumps(totals, indent=2) + "\n")
    controls = ("same_order_unique", "flat_unique", "shuffled_repeated", "batch_unique")
    def mean_accuracy(policy, layout=None):
        rows = [r for r in totals if r["condition"] == "static" and r["budget"] < 128
            and r["policy"] == policy and (layout is None or r["layout"] == layout)]
        return sum(r["correct"] for r in rows) / sum(r["targets"] for r in rows)
    means = {p: mean_accuracy(p) for p in (CANONICAL,) + controls}
    best = max(controls, key=lambda p: means[p])
    improvement = means[CANONICAL] - means[best]
    no_layout_harm = all(mean_accuracy(CANONICAL, layout) >= mean_accuracy(best, layout)
        for layout in plan["static_layouts"])
    static = [t for t in trials if t["condition"] == "static"]
    u1 = all(t["snapshots"][-1]["correct"] == 21 and t["actions"]["completed"] == 21
        and t["actions"]["appropriate"] == 21 for t in static)
    pairs = []
    for t in trials:
        if t["policy"] != CANONICAL: continue
        other = next(o for o in trials if o["condition"] == t["condition"] and o["layout"] == t["layout"]
            and o["seed"] == t["seed"] and o["changed_cue"] == t["changed_cue"]
            and o["update_slot"] == t["update_slot"] and o["policy"] == "generic_same_sequence")
        pairs.append(t["world_sha256_before_actions"] == other["world_sha256_before_actions"]
            and t["snapshots"] == other["snapshots"] and t["actions"] == other["actions"])
    result = {"experiment": plan["experiment"], "declaration_sha256": hashlib.sha256(declaration.read_bytes()).hexdigest(),
        "trajectories": len(trials), "static_trajectories": len(static), "dynamic_trajectories": len(trials) - len(static),
        "budgeted_target_evaluations": sum(r["targets"] for t in trials for r in t["snapshots"]),
        "physical_actions": sum(t["actions"]["count"] for t in trials),
        "selected_full_journals_replayed": len(selected) * 2,
        "selected_checkpoints": selected, "U1_full_static_recall_and_actions": u1,
        "U2_static_advantage": improvement >= .05 and no_layout_harm,
        "mean_static_accuracy_under_128": means, "best_generic_control": best,
        "improvement_percentage_points": improvement * 100, "no_layout_harm": no_layout_harm,
        "generic_schedule_pairs": len(pairs), "U3_identical_generic_pairs": all(pairs),
        "elapsed_seconds": round(time.monotonic() - begin, 3)}
    (evidence / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "selected_checkpoints"}, indent=2), flush=True)


if __name__ == "__main__":
    run()
