#!/usr/bin/env python3
"""Reproduce R4 circuit traces, matched controls and descriptive bounded profiles."""
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
from hle.codec import encode
from hle.contracts import ClaimStatus, MovementRecord
from hle.demo import ALICE, BOB, BOX, TOOL, ROOM, config
from hle.metabolism import MetabolicWorld
from hle.metabolism_demo import (CUE, LESSON, associate, finish, remember_initial,
    retrieve, run_metabolism_demo)
from hle.metabolism_records import (ApplyDraft, EmbodyDraft, Enactment,
    MetabolicCommand, MetabolicTransaction, ProcessingPolicy, Profile,
    TheorizeDraft, UnderstandDraft)
from hle.memory_records import MemoryCommand, WriteDraft
from hle.model_a import TYPES
from hle.processing import select_action
from hle.world_records import Correction, Tick
from tests.reference_world import fold
from tests.reference_processing import processing_fold
from tests.test_metabolism import world, account, learn, single_ownership_head
from hle.cards import card


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def type_controls():
    results = []
    for routing, prices in ((True, True), (True, False), (False, True), (False, False)):
        for tim in TYPES:
            w = world(tim, policy=ProcessingPolicy(routing, prices))
            _, a = account(w)
            j = w.processing_job(BOB, "think")
            results.append({"type": tim, "typed_routing": routing, "positional_prices": prices,
                "path": list(j.plan.path), "positions": list(j.plan.positions),
                "support_position": j.plan.support_position, "content_units": j.plan.content_units,
                "processing_units": j.plan.required, "predicted_owner": a.claim.object.key,
                "selected_action": select_action(a).operation.key})
    full = [r for r in results if r["typed_routing"] and r["positional_prices"]]
    neutral = [r for r in results if not r["typed_routing"] and not r["positional_prices"]]
    assert len({(tuple(r["path"]),r["processing_units"]) for r in full}) > 1
    assert len({(tuple(r["path"]),r["processing_units"]) for r in neutral}) == 1
    assert len({(r["predicted_owner"],r["selected_action"]) for r in results}) == 1
    return {"conditions": "same public state, recalled evidence, initial active IE, budget, goal and memory; type and declared routing/price controls varied", "cases":results}


def capacity_controls():
    results = []
    for enabled in (False, True):
        w = world(); lesson = learn(w)
        remember_initial(w, "tool", TOOL, card("arcana:3").ref)
        associate(w, lesson, "learned", LESSON)
        w.execute(MemoryCommand("no-cap", "no-cap", BOB,
            WriteDraft("no-cap", lesson.content, (), ClaimStatus.ENDORSED, None,
                       "capacity ablation; same proposition"), (lesson.ref,)))
        associate(w, w.memory_head(BOB, "no-cap"), "control", card("arcana:4").ref)
        single_ownership_head(w)
        w.execute(Correction("hidden", w._heads[(TOOL,"owned_by",ROOM)], ALICE, "held-out hidden correction"))
        budget = w.truth.wallet(BOB)
        r = retrieve(w, "heldout", (card("arcana:3").ref, LESSON if enabled else card("arcana:4").ref))
        t = finish(w, TheorizeDraft(r, TOOL, ALICE), "heldout-think")
        a = w.processing_record(BOB, t.result)
        j = finish(w, ApplyDraft(a.ref), "heldout-apply")
        application = w.processing_record(BOB, j.result)
        first = w.processing_record(BOB, application.enactments[0])
        e = finish(w, EmbodyDraft(application.ref, "heldout-lesson"), "heldout-embody")
        retained = w.read_revision(BOB, e.result)
        results.append({"capability_recalled":enabled,"budget_before":budget.energy,
            "predicted_owner":a.claim.object.key,"first_action":first.request.operation.key,
            "application_outcome":j.outcome.value,"discrepancy":application.discrepancy,
            "retained_claim_owner":retained.content[0].object.key,
            "retained_attitude":retained.claim_status.value,
            "retained_capabilities":len(retained.capabilities),
            "checkpoint_sha256":hashlib.sha256(w.checkpoint().encode()).hexdigest()})
    assert results[0]["budget_before"] == results[1]["budget_before"]
    assert results[0]["application_outcome"] == "failed" and results[1]["application_outcome"] == "completed"
    assert results[1]["retained_claim_owner"] == "alice"
    return {"conditions":"identical preceding transactions and resources; alternate cue selects equal claim content with/without acquired procedure. A harness-only correction creates the same unseen ownership change in both variants. This is a controlled acquisition test, not spontaneous institution or Shell generation.","cases":results}


def profile():
    cases = []
    for inactive_events in (0, 2000):
        for inactive_memories in (0, 400):
            samples, checkpoints = [], []
            for repetition in range(3):
                w = world(energy=100000, time=100000)
                initial = remember_initial(w)
                r = retrieve(w, "base-recall")
                for i in range(inactive_memories):
                    key = f"inactive:{i}"
                    w.execute(MemoryCommand(key,key,BOB,
                        WriteDraft(key,initial.content,(),ClaimStatus.ENDORSED,None,"inactive profile material"),(initial.ref,)))
                for i in range(inactive_events): w.execute(Tick(f"clock:{i}"))
                cursor = len(w._inboxes[BOB])
                for i in range(16):
                    start = time.perf_counter_ns()
                    t = finish(w,TheorizeDraft(r,BOX,ALICE),f"think:{i}")
                    finish(w,UnderstandDraft(t.result,f"personal:{i}"),f"understand:{i}")
                    _, cursor = w.select_input(BOB, after=cursor)
                    samples.append(time.perf_counter_ns()-start)
                start=time.perf_counter_ns(); cp=w.checkpoint()
                save=(time.perf_counter_ns()-start)/1e6
                start=time.perf_counter_ns(); restored=MetabolicWorld.restore(cp)
                replay=(time.perf_counter_ns()-start)/1e6
                assert restored.checkpoint()==cp
                checkpoints.append({"bytes":len(cp.encode()),"save_ms":save,"replay_ms":replay})
            cases.append({"inactive_events":inactive_events,"inactive_memories":inactive_memories,
                "repeats":3,"cycles_per_repeat":16,"selected_memories":1,
                "two_movements_plus_selected_input_median_us":statistics.median(samples)/1000,
                "p95_us":sorted(samples)[int(len(samples)*.95)-1]/1000,
                "checkpoint_bytes":checkpoints[-1]["bytes"],"events":len(w._journal),
                "save_median_ms":statistics.median(v["save_ms"] for v in checkpoints),
                "replay_median_ms":statistics.median(v["replay_ms"] for v in checkpoints),
                "exact_replay":True,"samples":checkpoints})
    cpu = next((s.split(":",1)[1].strip() for s in Path("/proc/cpuinfo").read_text().splitlines()
                if s.startswith("model name")),"unknown")
    return {"python":sys.version,"platform":platform.platform(),"cpu":cpu,
        "conditions":"one retained recalled claim; each cycle performs Theorize and Understand plus selective input. Preparation excluded. Each cycle appends its own outputs; the amount of active selected content is fixed.",
        "interpretation":"descriptive bounded controls; no timing acceptance threshold or sustained-population claim", "cases":cases}


def hashes():
    code="import hashlib; from hle.metabolism_demo import run_metabolism_demo; print(hashlib.sha256(run_metabolism_demo()[0].checkpoint().encode()).hexdigest())"
    results=[]
    for seed in (0,1,777):
        p=subprocess.run([sys.executable,"-c",code],cwd=ROOT,
            env=dict(os.environ,PYTHONHASHSEED=str(seed)),capture_output=True,text=True,timeout=30)
        results.append({"seed":seed,"returncode":p.returncode,"digest":p.stdout.strip(),"stderr":p.stderr})
    assert all(x["returncode"]==0 for x in results) and len({x["digest"] for x in results})==1
    return {"passed":True,"runs":results}


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=True)
    w,summary=run_metabolism_demo()
    write(out/"demo_summary.json",summary)
    write(out/"configuration.json",{"world":encode(w.config),"profiles":encode(w.profiles),"policy":encode(w.policy)})
    (out/"demo_checkpoint.json").write_text(w.checkpoint()+"\n")
    (out/"transactions.jsonl").write_text("".join(json.dumps(encode(tx),sort_keys=True)+"\n" for tx in w.truth.journal()))
    rows=["# R4 worked processing trace","","All prices and content policies are declared experiments. Each row is a committed transaction; partial work and physical actions remain visible.","",
        "| Tick | Operation | Outcome | Charged energy/time | Content or action |", "| --- | --- | --- | --- | --- |"]
    routes=[]
    for tx in w.truth.journal():
        notes=[f"memory revision {m.ref.revision}: {m.ref.key}; capabilities={len(m.capabilities)}" for m in tx.memories]
        if type(tx) is MetabolicTransaction:
            for x in tx.extra:
                if type(x) is Enactment: notes.append(x.request.operation.key+" "+x.request.inputs[0].key+": "+x.outcome.value)
                if type(x) is MovementRecord: notes.append(x.formal.route.name+" / "+x.formal.polarity.value)
            routes.append({"tick":tx.event.when.tick,"task":tx.command.task_id,"route":list(tx.job.plan.path),
                "positions":list(tx.job.plan.positions),"support_position":tx.job.plan.support_position,
                "required_processing_units":tx.job.plan.required,"completed_processing_units":tx.job.completed_units,
                "phase":tx.job.phase,"active":tx.state.active,"perspective":tx.state.perspective.value,
                "result":None if tx.job.result is None else encode(tx.job.result)})
        paid=sum(r.charged[0].amount for r in tx.works)
        rows.append(f"| {tx.event.when.tick} | {tx.event.action} | {tx.event.outcome.value} | {paid}/{paid} | {'; '.join(notes) or tx.event.reason} |")
    (out/"Worked_Trace.md").write_text("\n".join(rows)+"\n")
    write(out/"processing_routes.json",routes)
    live=MetabolicWorld(w.config,w.profiles,w.policy);checks=[]
    for i,tx in enumerate(w.truth.journal()):
        if i:live.execute(tx.command)
        state,jobs,changes=processing_fold(live.profiles,live.truth.journal())
        assert live.state()==fold(live.config,live.truth.journal())
        assert state=={a:(s.active,s.perspective,s.busy) for a,s in live._processing_states.items()}
        assert jobs==live._processing_jobs and changes==tuple(live._processing_changes)
        checks.append({"tick":i,"world_and_processing_fold":True})
    write(out/"independent_comparisons.json",checks)
    write(out/"type_controls.json",type_controls())
    write(out/"capacity_controls.json",capacity_controls())
    write(out/"hash_seed_control.json",hashes())
    write(out/"bounded_profile.json",profile())
    print(json.dumps({"summary":summary,"output":str(out.resolve())}))


if __name__=="__main__":main()
