"""Deterministic R4 demands; operations infer outcomes from their actual inputs."""
from .cards import card
from .contracts import Moment, TimeScope, WorkStatus
from .demo import ALICE, BOB, BOX, TOOL, ROOM, config, request
from .memory import observed_revision
from .memory_records import BindDraft, MemoryCommand, RecallQuery
from .metabolism import MetabolicWorld
from .metabolism_records import (ApplyDraft, EmbodyDraft, MetabolicCommand,
    Profile, TheorizeDraft, UnderstandDraft)
from .world_records import Attempt, TRANSFER

CUE = card("arcana:1").ref
LESSON = card("arcana:2").ref
SCOPE = TimeScope(Moment(0, 0), None)


def finish(world, payload, key, actor=BOB, work_limit=64):
    """Drive one explicitly supplied demand; stop when funds cannot progress it."""
    index = 0
    while True:
        world.execute(MetabolicCommand(f"{key}:{index}", key, actor, payload, work_limit))
        job = world.processing_job(actor, key)
        if job.outcome in (WorkStatus.COMPLETED, WorkStatus.FAILED): return job
        wallet = world.truth.wallet(actor)  # harness-only scheduling, no policy input
        if not min(wallet.energy, wallet.time): return job
        index += 1


def remember_initial(world, key="box", item=BOX, cue=CUE):
    view, _ = world.select_input(BOB, after=0)
    draft, basis = observed_revision(view, view.observations[0].ref, item, "owned_by", key)
    world.execute(MemoryCommand("remember:" + key, "remember:" + key, BOB, draft, basis))
    memory = world.memory_head(BOB, key)
    associate(world, memory, "bind:" + key, cue)
    return memory


def associate(world, memory, key, cue=CUE, expected=None):
    basis = (memory.ref,) + (() if expected is None else (expected,))
    world.execute(MemoryCommand(key, key, BOB,
        BindDraft(key, cue, ROOM, memory.ref, SCOPE, expected), basis))


def retrieve(world, key, cues=(CUE,), subject=None):
    world.execute(MemoryCommand(key, key, BOB,
        RecallQuery(cues, ROOM, world.now, subject, "owned_by"), (), 128))
    return world.memory_job(BOB, key).result


def run_metabolism_demo():
    world = MetabolicWorld(config(energy=600, time=600), (Profile(ALICE, "lse"), Profile(BOB, "iee")))
    original = remember_initial(world)
    # Bob's exact old cue remains Alice even after an unobserved world transfer.
    world.execute(Attempt("alice-transfers", "alice-transfers", request(ALICE, TRANSFER, (BOX, BOB))))
    recalled = retrieve(world, "recall-old")
    theorized = finish(world, TheorizeDraft(recalled, BOX, ALICE), "theorize")
    account = world.processing_record(BOB, theorized.result)
    applied = finish(world, ApplyDraft(account.ref), "apply", work_limit=3)
    application = world.processing_record(BOB, applied.result)
    embodied = finish(world, EmbodyDraft(application.ref, "box", original.ref), "embody")
    lesson = world.memory_head(BOB, "box")
    associate(world, lesson, "lesson-cue", LESSON)
    # The old binding still recalls revision 1. A new cue names the learned rule.
    heldout = remember_initial(world, "tool", TOOL, card("arcana:3").ref)
    recalled2 = retrieve(world, "recall-heldout", (card("arcana:3").ref, LESSON))
    account2 = finish(world, TheorizeDraft(recalled2, TOOL, ALICE), "theorize-heldout")
    app2 = finish(world, ApplyDraft(account2.result), "apply-heldout")
    final = finish(world, EmbodyDraft(app2.result, "tool", heldout.ref), "embody-heldout")
    # Alternate ITS -> I movement; no physical application is forced.
    recalled3 = retrieve(world, "recall-alternate", (LESSON,))
    account3 = finish(world, TheorizeDraft(recalled3, BOX, ALICE), "theorize-alternate")
    understood = finish(world, UnderstandDraft(account3.result, "personal-account"), "understand")
    restored = MetabolicWorld.restore(world.checkpoint())
    moves = [tx for tx in world.truth.journal() if type(tx.command) is MetabolicCommand]
    actions = [r for tx in moves for r in tx.extra if type(r).__name__ == "Enactment"]
    return world, {
        "milestone": "R4", "events": len(world.truth.journal()),
        "scope": "bounded executable operators and acquired checking grammar; no IDEA/Shell assessment",
        "initial_prediction": account.claim.object.key,
        "observed_discrepancy": application.discrepancy,
        "retained_revision": lesson.ref.revision,
        "retained_capability": [r.key for r in lesson.capabilities],
        "old_binding_revision": world.binding_head(BOB, "bind:box").target.revision,
        "actions": [{"operation": a.request.operation.key, "item": a.request.inputs[0].key,
                     "outcome": a.outcome.value} for a in actions],
        "heldout_completed": final.outcome.value,
        "alternate": "Theorize -> Understand",
        "alternate_retained": understood.result.key,
        "bob_spent": 600 - world.truth.wallet(BOB).energy,
        "continuation_identical": restored.checkpoint() == world.checkpoint(),
        "next": "R5: IDEA assessment, error and Shell candidates, retained correction panel"
    }
