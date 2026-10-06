#!/usr/bin/env python3
"""Export the R2 trace and bounded cost measurements; standard library only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from hle.codec import dumps, encode
from hle.demo import ALICE, BOB, BOX, ROOM, config, request, run_demo
from hle.world import World
from hle.world_records import Attempt, INSPECT, TRANSFER, Tick


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def profile():
    cases = []
    for inactive in (0, 2000):
        action_times, evaluator_times = [], []
        for repeat in range(5):
            world = World(config(energy=1000, time=1000))
            for i in range(inactive):
                world.execute(Tick(f"inactive:{i}"))
            cursor = world.participant_input(BOB)[1]
            for i in range(64):
                started = time.perf_counter_ns()
                world.execute(Attempt(f"active:{i}", f"active:{i}", request(BOB, INSPECT, (BOX,))))
                _, cursor = world.participant_input(BOB, cursor)
                action_times.append(time.perf_counter_ns()-started)
                proposition = world.truth.current_fact(BOX, "owned_by", ROOM)
                started = time.perf_counter_ns()
                world.truth.check(proposition, world.now)
                evaluator_times.append(time.perf_counter_ns()-started)
        started = time.perf_counter_ns()
        checkpoint = world.checkpoint()
        checkpoint_ms = (time.perf_counter_ns()-started)/1e6
        started = time.perf_counter_ns()
        restored = World.restore(checkpoint)
        restore_ms = (time.perf_counter_ns()-started)/1e6
        assert restored.checkpoint() == checkpoint
        cases.append({"inactive_events": inactive, "repeats": 5, "active_attempts_per_repeat": 64,
            "active_action_plus_inbox_median_us": statistics.median(action_times)/1000,
            "pointwise_evaluator_median_us": statistics.median(evaluator_times)/1000,
            "checkpoint_ms": checkpoint_ms, "restore_ms": restore_ms,
            "checkpoint_bytes": len(checkpoint.encode()), "events": len(world.truth.journal()),
            "records": len(world._records), "retained_bob_observations": len(world._inboxes[BOB]),
            "undelivered_bob_observations": len(world._inboxes[BOB])-cursor,
            "continuation_data_identical": restored.checkpoint() == checkpoint})
    return {"python": sys.version, "platform": platform.platform(), "clock": "perf_counter_ns",
        "conditions": "two actors/two objects; 64 paid inspections per repeat, five repeats; explicit cursor consumption",
        "interpretation": "descriptive bounded measurements; no timing threshold or population-scaling claim; retained history and replay remain linear costs",
        "cases": cases}


def hash_seed_control():
    source = "import hashlib; from hle.demo import run_demo; print(hashlib.sha256(run_demo()[0].checkpoint().encode()).hexdigest())"
    outcomes = []
    for seed in (1, 42, 314159):
        env = dict(os.environ, PYTHONHASHSEED=str(seed))
        run = subprocess.run([sys.executable, "-c", source], cwd=ROOT, env=env,
            capture_output=True, text=True, timeout=30)
        outcomes.append({"hash_seed": seed, "returncode": run.returncode,
                         "stdout": run.stdout.strip(), "stderr": run.stderr})
    passed = all(o["returncode"] == 0 for o in outcomes) and len({o["stdout"] for o in outcomes}) == 1
    if not passed:
        raise RuntimeError(outcomes)
    return {"passed": passed, "command": source, "runs": outcomes}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    world, summary = run_demo()
    write(args.output / "demo_summary.json", summary)
    write(args.output / "configuration.json", encode(world.config))
    (args.output / "demo_checkpoint.json").write_text(world.checkpoint()+"\n")
    with (args.output / "transactions.jsonl").open("w") as stream:
        for transaction in world.truth.journal():
            stream.write(json.dumps(encode(transaction), sort_keys=True) + "\n")
    rows = ["# R2 worked trace", "", "This is an explicit control fixture. Beliefs and commands are supplied; autonomous learning starts in later milestones.", "",
        "| Tick | Event | Outcome | Ownership change | Energy / time charged | Other retained evidence |",
        "| --- | --- | --- | --- | --- | --- |"]
    for tx in world.truth.journal():
        changes = [f"{c.after.subject.key} → {c.after.object.key}" for c in tx.event.changes
                   if c.after is not None and c.after.relation == "owned_by"]
        costs = [f"{w.owner.key}: " + "/".join(str(a.amount) for a in w.charged) for w in tx.works]
        notes = []
        if tx.memories:
            notes.append("endorsed ownership belief retained; content is false at this tick")
        if tx.messages:
            notes.append("Alice's attributed testimony delivered to Bob; no automatic belief revision")
        if tx.event.corrects:
            notes.append(f"explicit correction of {tx.event.corrects.key}; old observations and costs preserved")
        rows.append(f"| {tx.event.when.tick} | {tx.event.action} | {tx.event.outcome.value} | {'; '.join(changes) or '—'} | {'; '.join(costs) or '0 / 0'} | {'; '.join(notes) or '—'} |")
    (args.output / "Worked_Trace.md").write_text("\n".join(rows)+"\n")
    left, right = World(config()), World(config())
    left.execute(Attempt("hidden", "hidden", request(ALICE, TRANSFER, (BOX, BOB))))
    right.execute(Attempt("hidden", "hidden", request(ALICE, TRANSFER, (BOX, ALICE))))
    left_input, cursor = left.participant_input(BOB)
    right_input, _ = right.participant_input(BOB)
    assert left_input == right_input
    for candidate in (left, right):
        candidate.execute(Attempt("inspect", "inspect", request(BOB, INSPECT, (BOX,))))
    after_left, _ = left.participant_input(BOB, cursor)
    after_right, _ = right.participant_input(BOB, cursor)
    assert after_left != after_right
    write(args.output / "observation_isolation.json", {
        "identical_before_permitted_inspection": left_input == right_input,
        "left_input_sha256": hashlib.sha256(dumps(left_input).encode()).hexdigest(),
        "right_input_sha256": hashlib.sha256(dumps(right_input).encode()).hexdigest(),
        "initial_observer_input": encode(left_input),
        "different_after_permitted_inspection": after_left != after_right,
        "left_inspection": encode(after_left.observations), "right_inspection": encode(after_right.observations)})
    write(args.output / "hash_seed_control.json", hash_seed_control())
    write(args.output / "bounded_profile.json", profile())
    print(json.dumps({"output": str(args.output.resolve()), "summary": summary}))


if __name__ == "__main__":
    main()
