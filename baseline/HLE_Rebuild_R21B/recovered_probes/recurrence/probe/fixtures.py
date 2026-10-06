"""Synthetic declared histories, separated from the participant decision adapter."""
from dataclasses import dataclass
import random

from hle.cards import card
from hle.contracts import ActionRequest, ClaimStatus, Kind, Ref, TimeScope, Moment, WorkStatus
from hle.memory import observed_revision
from hle.memory_records import BindDraft, CursorDraft, LINKED, MemoryCommand, WriteDraft
from hle.metabolism_records import Profile, ProcessingPolicy
from hle.organization import OrganizationWorld
from hle.socion_records import AgentPolicy
from hle.world_records import Attempt, Entity, INSPECT, Ownership, TRANSFER, Wallet, WorldConfig

ALICE = Ref(Kind.ENTITY, "alice", 1)
BOB = Ref(Kind.ENTITY, "bob", 1)
ROOM = Ref(Kind.CONTEXT, "recurrence-room", 1)
SCOPE = TimeScope(Moment(0, 0), None)


def perform(w, key, payload, basis=()):
    w.execute(MemoryCommand(key, key, ALICE, payload, basis, 4096))
    job = w.memory_job(ALICE, key)
    if job.outcome != WorkStatus.COMPLETED:
        raise AssertionError(f"fixture setup did not complete: {key}")
    return job


def remember(w, item, key, previous=None, prefix="setup"):
    command_id = f"{prefix}:inspect:{item.key}"
    w.execute(Attempt(command_id, command_id, ActionRequest(ALICE, INSPECT, (item,), ())))
    view, _ = w.select_input(ALICE, memories=() if previous is None else (previous.ref,))
    obs = next(o for o in reversed(view.observations)
               if any(p.subject == item and p.relation == "owned_by" for p in o.content))
    draft, basis = observed_revision(view, obs.ref, item, "owned_by", key, previous)
    perform(w, f"{prefix}:write:{item.key}", draft, basis)
    return w.memory_head(ALICE, key)


def bind(w, memory, rank, key, prefix="setup", expected=None):
    basis = (memory.ref,) + (() if expected is None else (expected.ref,))
    perform(w, f"{prefix}:bind:{key}", BindDraft(key, card(f"arcana:{rank}").ref,
        ROOM, memory.ref, SCOPE, None if expected is None else expected.ref), basis)


@dataclass
class Fixture:
    world: OrganizationWorld
    by_cue: dict
    expected: dict  # Evaluator/external-intervention state, never passed to decide().
    setup_energy: int

    def change(self, rank, *, alternate=False, prefix="update"):
        item = self.by_cue[rank]
        old_owner = self.expected[item]
        new_owner = BOB if old_owner == ALICE else ALICE
        key = f"{prefix}:transfer:{item.key}"
        before = sum(self.world.truth.wallet(a).energy for a in (ALICE, BOB))
        self.world.execute(Attempt(key, key, ActionRequest(old_owner, TRANSFER, (item, new_owner), ())))
        previous = self.world.memory_head(ALICE, item.key)
        new = remember(self.world, item, item.key, previous, prefix)
        if alternate:
            destination = (rank + 6) % 21 + 1
            bind(self.world, new, destination, f"updated:{rank}", prefix)
        else:
            old_binding = self.world.binding_head(ALICE, f"cue:{rank}")
            bind(self.world, new, rank, f"cue:{rank}", prefix, old_binding)
        self.expected[item] = new_owner
        after = sum(self.world.truth.wallet(a).energy for a in (ALICE, BOB))
        return before - after


def make_fixture(seed=17, layout="direct", energy=20000, time_budget=None):
    if layout not in ("direct", "shared", "revised"):
        raise ValueError("unknown fixture")
    items = tuple(Ref(Kind.ENTITY, f"item:{i:02d}", 1) for i in range(21))
    owners = [ALICE if i % 2 == 0 else BOB for i in range(21)]
    rng = random.Random(seed)
    rng.shuffle(owners)
    expected = dict(zip(items, owners))
    ranks = list(range(1, 22)); rng.shuffle(ranks)
    by_cue = dict(zip(ranks, items))
    cfg = WorldConfig(ROOM, tuple(Entity(a, a.key, "actor") for a in (ALICE, BOB)) +
        tuple(Entity(i, i.key, "object") for i in items), (ALICE, BOB),
        tuple(Ownership(i, expected[i]) for i in items),
        tuple(Wallet(a, energy, energy if time_budget is None else time_budget) for a in (ALICE, BOB)),
        (), ((ALICE, BOB), (BOB, ALICE)))
    w = OrganizationWorld(cfg, (Profile(ALICE, "lse"), Profile(BOB, "eii")),
        ProcessingPolicy(), (AgentPolicy(ALICE), AgentPolicy(BOB)))
    memories = {item: remember(w, item, item.key) for item in items}
    for rank in range(1, 22):
        memory = memories[by_cue[rank]]
        if layout == "shared":
            links = (memory.ref, memories[by_cue[rank % 21 + 1]].ref)
            perform(w, f"setup:root:{rank}", WriteDraft(f"root:{rank}", (), links,
                ClaimStatus.ENDORSED, None, "declared shared scene fixture"), links)
            memory = w.memory_head(ALICE, f"root:{rank}")
        bind(w, memory, rank, f"cue:{rank}")
    if layout == "shared":
        perform(w, "setup:navigation", CursorDraft((card("arcana:1").ref,), LINKED, 5))
    fixture = Fixture(w, by_cue, expected, 0)
    if layout == "revised":
        for rank in (1, 4, 7, 10, 13, 16, 19):
            fixture.change(rank, alternate=True, prefix=f"history:{rank}")
    fixture.setup_energy = 2 * energy - sum(w.truth.wallet(a).energy for a in (ALICE, BOB))
    return fixture
