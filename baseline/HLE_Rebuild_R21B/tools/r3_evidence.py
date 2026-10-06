#!/usr/bin/env python3
"""Reproduce R3 trace, cross-process determinism and bounded access profiles."""
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
from hle.cards import card
from hle.codec import encode
from hle.contracts import ClaimStatus, Moment, Proposition, TimeScope
from hle.demo import ALICE, BOB, BOX, ROOM, config
from hle.memory import RelationalWorld
from hle.memory_demo import run_memory_demo
from hle.memory_records import BindDraft, MemoryCommand, MemoryTransaction, RecallQuery, WriteDraft
from hle.world_records import Tick
from tests.reference_world import fold
from tests.reference_memory import complete_recall


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def profile():
    cases = []
    cue, unrelated = card("arcana:1").ref, card("arcana:2").ref
    scope = TimeScope(Moment(0, 0), None)
    for inactive_events in (0, 2000):
        for inactive_memories in (0, 800):
            samples, replay_data = [], []
            for repeat in range(3):
                w = RelationalWorld(config(energy=100000, time=100000))
                provenance = (w.select_input(BOB)[0].observations[0].ref,)
                for i in range(inactive_memories + 1):
                    key = f"memory:{i}"
                    p = Proposition(BOX, "owned_by", ALICE, ROOM, scope)
                    w.execute(MemoryCommand(f"write:{i}", f"write:{i}", BOB,
                        WriteDraft(key, (p,), (), ClaimStatus.ENDORSED, None, "profile fixture"), provenance))
                    m = w.memory_head(BOB, key)
                    w.execute(MemoryCommand(f"bind:{i}", f"bind:{i}", BOB,
                        BindDraft(key, cue if i == 0 else unrelated, ROOM, m.ref, scope), (m.ref,)))
                for i in range(inactive_events): w.execute(Tick(f"inactive:{i}"))
                cursor = w.select_input(BOB)[1]
                for i in range(32):
                    key = f"recall:{i}"
                    command = MemoryCommand(key, key, BOB, RecallQuery((cue,), ROOM, w.now), ())
                    start = time.perf_counter_ns()
                    w.execute(command)
                    result = w.recall_result(BOB, w.memory_job(BOB, key).result)
                    _, cursor = w.select_input(BOB, memories=tuple(h.memory for h in result.hits), after=cursor)
                    samples.append(time.perf_counter_ns() - start)
                    assert len(result.visited) == 1 and len(result.hits) == 1
                start = time.perf_counter_ns(); checkpoint = w.checkpoint()
                save_ms = (time.perf_counter_ns() - start) / 1e6
                start = time.perf_counter_ns(); restored = RelationalWorld.restore(checkpoint)
                restore_ms = (time.perf_counter_ns() - start) / 1e6
                assert restored.checkpoint() == checkpoint
                replay_data.append({"save_ms": save_ms, "restore_ms": restore_ms})
            cases.append({"inactive_events": inactive_events, "inactive_memories": inactive_memories,
                "repeats": 3, "active_recalls_per_repeat": 32,
                "recall_plus_selected_input_median_us": statistics.median(samples)/1000,
                "recall_plus_selected_input_p95_us": sorted(samples)[int(len(samples)*.95)-1]/1000,
                "checkpoint_bytes": len(checkpoint.encode()), "events": len(w._journal),
                "records": len(w._records), "active_seed_bindings": 1, "visited_records_per_recall": 1,
                "completed_recall_units": 2,
                "unconsumed_inbox_observations": len(w._inboxes[BOB]) - cursor,
                "save_median_ms": statistics.median(x["save_ms"] for x in replay_data),
                "restore_median_ms": statistics.median(x["restore_ms"] for x in replay_data),
                "replay_samples": replay_data, "exact_replay": True})
    cpu = next((line.split(":", 1)[1].strip() for line in Path("/proc/cpuinfo").read_text().splitlines()
                if line.startswith("model name")), "unknown")
    return {"python": sys.version, "platform": platform.platform(), "cpu": cpu,
        "conditions": "three repeats; 32 independent two-unit recalls and selective inbox reads per repeat; initialization excluded",
        "interpretation": "descriptive bounded measurements; no timing gate, sustained population or bounded-history claim",
        "cases": cases}


def hashes():
    source = "import hashlib; from hle.memory_demo import run_memory_demo; print(hashlib.sha256(run_memory_demo()[0].checkpoint().encode()).hexdigest())"
    outcomes = []
    for seed in (1, 42, 314159):
        result = subprocess.run([sys.executable, "-c", source], cwd=ROOT,
            env=dict(os.environ, PYTHONHASHSEED=str(seed)), text=True, capture_output=True, timeout=30)
        outcomes.append({"seed": seed, "returncode": result.returncode,
                         "stdout": result.stdout.strip(), "stderr": result.stderr})
    passed = all(r["returncode"] == 0 for r in outcomes) and len({r["stdout"] for r in outcomes}) == 1
    if not passed: raise RuntimeError(outcomes)
    return {"passed": passed, "command": source, "runs": outcomes}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(); args.output.mkdir(parents=True, exist_ok=True)
    world, summary = run_memory_demo()
    write(args.output / "demo_summary.json", summary)
    write(args.output / "configuration.json", encode(world.config))
    (args.output / "demo_checkpoint.json").write_text(world.checkpoint() + "\n")
    with (args.output / "transactions.jsonl").open("w") as stream:
        for tx in world.truth.journal(): stream.write(json.dumps(encode(tx), sort_keys=True) + "\n")
    rows = ["# R3 worked memory trace", "", "A supplied observation-copy and ownership-action policy demonstrates memory use. Prices and navigation are experimental choices. This is not evidence of generated Shells or autonomous policy learning.", "",
            "| Tick | Operation | Outcome | Energy and time charged | Retained change |",
            "| --- | --- | --- | --- | --- |"]
    for tx in world.truth.journal():
        notes = [f"memory {m.ref.key} revision {m.ref.revision}" for m in tx.memories]
        if type(tx) is MemoryTransaction:
            notes += [f"binding {b.ref.key} revision {b.ref.revision} names memory revision {b.target.revision}" for b in tx.bindings]
            notes += [f"recall visits {len(r.visited)} fragments; {len(r.hits)} matching fragments; truncated={r.truncated}" for r in tx.recalls]
            if not notes: notes.append("progress/cursor retained in transaction")
        charge = sum(w.charged[0].amount for w in tx.works)
        rows.append(f"| {tx.event.when.tick} | {tx.event.action} | {tx.event.outcome.value} | {charge} / {charge} | {'; '.join(notes) or 'world transaction'} |")
    (args.output / "Worked_Trace.md").write_text("\n".join(rows) + "\n")
    # Independent full state fold after every actual transaction.
    replay = RelationalWorld(world.config)
    prefix_checks = []
    for i, tx in enumerate(world.truth.journal()):
        if i: replay.execute(tx.command)
        passed = replay.state() == fold(replay.config, replay.truth.journal())
        prefix_checks.append({"tick": i, "passed": passed})
        assert passed
    recall_checks = []
    for tx in world.truth.journal():
        if type(tx) is MemoryTransaction:
            for result in tx.recalls:
                actual = (result.bindings, result.visited, result.hits, result.truncated)
                passed = actual == complete_recall(world, result)
                recall_checks.append({"ref": encode(result.ref), "passed": passed})
                assert passed
    write(args.output / "independent_comparisons.json", {"state_prefixes": prefix_checks, "recalls": recall_checks})
    write(args.output / "hash_seed_control.json", hashes())
    write(args.output / "bounded_profile.json", profile())
    print(json.dumps({"summary": summary, "output": str(args.output.resolve())}))


if __name__ == "__main__": main()
