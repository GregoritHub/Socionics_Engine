"""Inspectable R3 memory-to-action example under supplied participant policies."""
from dataclasses import replace
from .cards import card
from .contracts import ClaimStatus, Moment, TimeScope
from .demo import ALICE, BOB, BOX, ROOM, config, request
from .memory import RelationalWorld, observed_revision, ownership_action
from .memory_records import (AckDraft, BindDraft, CursorDraft, LINKED,
    MemoryCommand, RecallQuery, WriteDraft)
from .world_records import Attempt, TRANSFER


def run_memory_demo():
    w = RelationalWorld(config(energy=100, time=100))
    cue, alternate, scene_cue = (card(key).ref for key in
                                ("arcana:1", "minor:Wand:10", "arcana:10"))
    scope = TimeScope(Moment(0, 0), None)

    def do(key, payload, basis=(), limit=64):
        command = MemoryCommand(key, key, BOB, payload, basis, limit)
        w.execute(command)
        return command

    def retrieve(key, seed, limit=64):
        cmd = do(key, RecallQuery((seed,), ROOM, w.now, BOX, "owned_by"), limit=limit)
        job = w.memory_job(BOB, key)
        return cmd, None if job.result is None else w.recall_result(BOB, job.result)

    view, through = w.select_input(BOB)
    draft, basis = observed_revision(view, view.observations[0].ref, BOX, "owned_by", "ownership")
    do("retain_initial", draft, basis)
    initial = w.memory_head(BOB, "ownership")
    do("bind_initial", BindDraft("ownership", cue, ROOM, initial.ref, scope), (initial.ref,))
    first_binding = w.binding_head(BOB, "ownership")
    do("bind_alternate", BindDraft("alternate", alternate, ROOM, initial.ref, scope), (initial.ref,))
    do("acknowledge_genesis", AckDraft(0, through), basis)
    w.execute(Attempt("hidden_transfer", "hidden_transfer", request(ALICE, TRANSFER, (BOX, BOB))))
    _, stale = retrieve("recall_initial", cue)
    view, _ = w.select_input(BOB, memories=tuple(h.memory for h in stale.hits))
    first_action = ownership_action(view, BOX, ALICE, ROOM, w.now)
    w.apply(first_action)
    view, _ = w.select_input(BOB, memories=(initial.ref,))
    inspected = view.observations[-1]
    draft, basis = observed_revision(view, inspected.ref, BOX, "owned_by", "ownership", initial)
    do("retain_inspection", draft, basis)
    corrected = w.memory_head(BOB, "ownership")
    do("rebind_ownership", BindDraft("ownership", cue, ROOM, corrected.ref, scope, first_binding.ref),
       (corrected.ref, first_binding.ref))
    do("retain_scene", WriteDraft("scene", (), (corrected.ref,), ClaimStatus.TENTATIVE, None,
       "scene links to an observed ownership fragment"), (corrected.ref,))
    scene = w.memory_head(BOB, "scene")
    do("bind_scene", BindDraft("scene", scene_cue, ROOM, scene.ref, scope), (scene.ref,))
    do("configure_navigation", CursorDraft((scene_cue,), LINKED, 1), (scene.ref,))
    cmd, partial = retrieve("recall_scene", scene_cue, 1)
    suspended = w.checkpoint()
    restored = RelationalWorld.restore(suspended)
    for candidate in (w, restored):
        candidate.execute(replace(cmd, command_id="resume_scene", work_limit=64))
    continuation_identical = w.checkpoint() == restored.checkpoint()
    result = w.recall_result(BOB, w.memory_job(BOB, cmd.task_id).result)
    view, through = w.select_input(BOB, memories=tuple(h.memory for h in result.hits))
    second_action = ownership_action(view, BOX, ALICE, ROOM, w.now)
    consequence = w.apply(second_action)
    do("acknowledge_processed", AckDraft(1, through), tuple(h.memory for h in result.hits))
    return w, {
        "milestone": "R3", "scope": "supplied observation/revision/action policies; no Crux or Shell claim",
        "events": len(w.truth.journal()), "first_action": first_action.operation.key,
        "second_action": second_action.operation.key, "second_outcome": consequence.outcome.value,
        "owner_after_action": w.truth.current_fact(BOX, "owned_by", ROOM).object.key,
        "initial_memory_revision": initial.ref.revision,
        "corrected_memory_revision": corrected.ref.revision,
        "old_binding_still_names_initial_revision": w.resolve_binding(BOB, first_binding.ref).target == initial.ref,
        "alternate_cue_still_names_initial_revision": w.binding_head(BOB, "alternate").target == initial.ref,
        "scene_recall_visits": [v.memory.key for v in result.visited],
        "scene_recall_hit_revisions": [h.memory.revision for h in result.hits],
        "partial_recall_exposed_no_result": partial is None,
        "continuation_identical": continuation_identical,
        "bob_energy_remaining": w.truth.wallet(BOB).energy,
        "bob_time_remaining": w.truth.wallet(BOB).time,
        "next": "R4: integrate Crux and Model A with memory and action"
    }
