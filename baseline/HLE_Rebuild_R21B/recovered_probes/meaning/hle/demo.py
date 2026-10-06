"""An inspectable R2 fixture, not an autonomous learning demonstration."""
from .contracts import ActionRequest, ClaimStatus, Kind, Proposition, Ref, TimeScope
from .world import World
from .world_records import (Attempt, Correction, Credit, Entity, INSPECT,
    MemoryDraft, MessageDraft, Ownership, RETAIN, SEND, TRANSFER, Wallet,
    Witness, WorldConfig)

ALICE = Ref(Kind.ENTITY, "alice", 1)
BOB = Ref(Kind.ENTITY, "bob", 1)
BOX = Ref(Kind.ENTITY, "box", 1)
TOOL = Ref(Kind.ENTITY, "tool", 1)
ROOM = Ref(Kind.CONTEXT, "workroom", 1)


def config(energy=20, time=20, witnesses=(), links=((ALICE, BOB), (BOB, ALICE))):
    return WorldConfig(ROOM, (Entity(ALICE, "Alice", "actor"), Entity(BOB, "Bob", "actor"),
        Entity(BOX, "Box", "object"), Entity(TOOL, "Tool", "object")), (ALICE, BOB),
        (Ownership(BOX, ALICE), Ownership(TOOL, BOB)),
        (Wallet(ALICE, energy, time), Wallet(BOB, energy, time)), witnesses, links)


def request(actor, operation, inputs=(), basis=()):
    return ActionRequest(actor, operation, inputs, basis)


def run_demo():
    world = World(config())
    world.execute(Attempt("transfer", "transfer", request(ALICE, TRANSFER, (BOX, BOB))))
    bob_view, _ = world.participant_input(BOB)
    claim = Proposition(BOX, "owned_by", ALICE, ROOM, TimeScope(world.now, None))
    world.execute(Attempt("belief", "belief", request(BOB, RETAIN, basis=(bob_view.observations[0].ref,)),
        memory=MemoryDraft("ownership", (claim,), ClaimStatus.ENDORSED, "fixture account based on initial ownership")))
    belief = world.participant_input(BOB)[0].own_memories[0]
    held = Proposition(belief.ref, "held_by", BOB, ROOM, TimeScope(world.now, None))
    held_result = world.truth.check(held, world.now)
    content_result = world.truth.check(claim, world.now)
    failed = world.execute(Attempt("mistaken_transfer", "mistaken_transfer", request(ALICE, TRANSFER, (BOX, BOB))))
    message_claim = Proposition(BOX, "owned_by", BOB, ROOM, TimeScope(world.now, None))
    alice_receipt = world.participant_input(ALICE)[0].observations[1]
    world.execute(Attempt("tell", "tell", request(ALICE, SEND, (BOB,), (alice_receipt.ref,)),
        message=MessageDraft((message_claim,))))
    partial_world = World(config(energy=1, time=3))
    partial = partial_world.execute(Attempt("partial", "transfer", request(ALICE, TRANSFER, (BOX, BOB))))
    restored = World.restore(partial_world.checkpoint())
    for candidate in (partial_world, restored):
        candidate.execute(Credit("supply", ALICE, 1, 0, "explicit experimental resource supply"))
        candidate.execute(Attempt("resume", "transfer", request(ALICE, TRANSFER, (BOX, BOB))))
    correction = world.execute(Correction("correct", world.truth.journal()[1].event.ref, ALICE,
        "fixture: correct the current ownership record prospectively"))
    return world, {
        "milestone": "R2", "scope": "deterministic fixture; no autonomous learning or Shell assessment",
        "events": len(world.truth.journal()), "belief_existence": held_result.status.value,
        "belief_content_agreement": content_result.status.value,
        "failed_action": {"outcome": failed.outcome.value,
            "energy_charged": world.truth.resolve(failed.work[0]).charged[0].amount},
        "partial_action": partial.outcome.value,
        "continuation_identical": partial_world.checkpoint() == restored.checkpoint(),
        "correction": {"event": correction.ref.key, "corrects": correction.corrects.key,
            "prior_factual_check_stale": not world.truth.is_current(content_result)},
        "next": "R3: relational Fool's Memory"
    }
