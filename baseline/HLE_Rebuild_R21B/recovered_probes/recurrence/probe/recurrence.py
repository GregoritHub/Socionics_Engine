"""Declared scheduling hypothesis; all retrieval is paid R3 work inside R11.

This module neither edits the card catalog nor grants the participant Truth.
Three cue consultations form a scheduling frame, not a memory graph constraint.
"""
from dataclasses import dataclass
from itertools import permutations
import hashlib
import json
import random

from hle.cards import card
from hle.codec import canonical
from hle.contracts import WorkStatus
from hle.memory_records import MemoryCommand, RecallQuery
from hle.organization import OrganizationWorld


ORDERS = tuple(permutations((19, 20, 21)))
CANONICAL = "recurrence_192021"
POLICIES = tuple("recurrence_" + "".join(map(str, p)) for p in ORDERS) + (
    "same_order_unique", "flat_unique", "shuffled_repeated", "batch_unique",
    "generic_same_sequence",
)


@dataclass(frozen=True)
class Phase:
    outer: int = 0
    inner: int = 0

    def __post_init__(self):
        if type(self.outer) is not int or type(self.inner) is not int:
            raise ValueError("integer phases required")
        if not (0 <= self.outer < 9 and 0 <= self.inner < 3):
            raise ValueError("phase outside declared cycle")

    def advance(self):
        return Phase((self.outer + 1) % 9, (self.inner + 1) % 3)

    def cues(self, order=(19, 20, 21)):
        if tuple(sorted(order)) != (19, 20, 21):
            raise ValueError("Identity order must be a permutation of 19,20,21")
        return self.outer + 1, self.outer + 10, order[self.inner]


def schedule(policy, seed=17, outer=0, inner=0):
    if policy not in POLICIES:
        raise ValueError("unknown experimental policy")
    order = next((p for p in ORDERS if policy == "recurrence_" + "".join(map(str, p))), (19, 20, 21))
    phase = Phase(outer, inner)
    repeated = []
    for _ in range(9):
        repeated.extend(phase.cues(order))
        phase = phase.advance()
    if policy == "same_order_unique":
        repeated = list(dict.fromkeys(repeated))
    elif policy == "flat_unique":
        repeated = list(range(1, 22))
    elif policy == "shuffled_repeated":
        random.Random(seed + 7001).shuffle(repeated)
    elif policy == "batch_unique":
        return (tuple(range(1, 22)),)
    return tuple((rank,) for rank in repeated)


class Session:
    """One unit per attempt; unfinished jobs keep their exact query and cursor.

    A fresh query samples current bindings. A pending query keeps R3's frozen
    binding snapshot. Revisited cues are fresh jobs, so explicit rebinding can
    change a later result. No pending-job hits are exposed through results().
    """
    def __init__(self, world, actor, policy=CANONICAL, seed=17, outer=0, inner=0):
        self.world, self.actor = world, actor
        self.policy, self.seed, self.start = policy, seed, Phase(outer, inner)
        self.groups = schedule(policy, seed, outer, inner)
        self.index, self.calls = 0, 0
        self.published = []

    @property
    def done(self):
        return self.index == len(self.groups)

    @property
    def phase(self):
        if not (self.policy.startswith("recurrence_") or self.policy == "generic_same_sequence"):
            return None
        frames = self.index // 3
        return Phase((self.start.outer + frames) % 9, (self.start.inner + frames) % 3)

    def step(self):
        if self.done:
            return 0
        task = f"probe:{self.index}"
        old = self.world.memory_job(self.actor, task)
        payload = old.command.payload if old else RecallQuery(
            tuple(card(f"arcana:{n}").ref for n in self.groups[self.index]),
            self.world.config.context, self.world.now, relation="owned_by", visit_limit=4096,
        )
        command = MemoryCommand(f"probe:{self.index}:{self.calls}", task, self.actor, payload, (), 1)
        before = self.world.truth.wallet(self.actor)  # Evaluator accounting only.
        self.world.execute(command)
        self.calls += 1
        job = self.world.memory_job(self.actor, task)
        after = self.world.truth.wallet(self.actor)
        paid = before.energy - after.energy
        if before.time - after.time != paid or paid not in (0, 1):
            raise AssertionError("R3 step was not one equal energy/time unit")
        if job.outcome == WorkStatus.COMPLETED:
            if job.result is None:
                raise AssertionError("completed recall must publish a result")
            self.published.append(job.result)
            self.index += 1
        elif job.outcome == WorkStatus.FAILED:
            raise AssertionError("valid probe recall failed")
        return paid

    def results(self):
        return tuple(self.world.recall_result(self.actor, ref) for ref in self.published)

    def checkpoint(self):
        body = {
            "schema": "hle-id-recurrence-probe-v1", "world": self.world.checkpoint(),
            "actor": self.actor.key, "policy": self.policy, "seed": self.seed,
            "outer": self.start.outer, "inner": self.start.inner,
            "index": self.index, "calls": self.calls,
            "phase": None if self.phase is None else [self.phase.outer, self.phase.inner],
        }
        return canonical({"body": body, "sha256": hashlib.sha256(canonical(body).encode()).hexdigest()})

    @classmethod
    def restore(cls, text):
        envelope = json.loads(text)
        if set(envelope) != {"body", "sha256"}:
            raise ValueError("invalid probe checkpoint envelope")
        b = envelope["body"]
        if hashlib.sha256(canonical(b).encode()).hexdigest() != envelope["sha256"]:
            raise ValueError("probe checkpoint checksum mismatch")
        expected = {"schema", "world", "actor", "policy", "seed", "outer", "inner", "index", "calls", "phase"}
        if set(b) != expected or b["schema"] != "hle-id-recurrence-probe-v1":
            raise ValueError("unknown probe checkpoint")
        w = OrganizationWorld.restore(b["world"])
        actors = [a for a in w.config.actors if a.key == b["actor"]]
        if len(actors) != 1:
            raise ValueError("unknown probe owner")
        result = cls(w, actors[0], b["policy"], b["seed"], b["outer"], b["inner"])
        # Reconstruct the wrapper state from verified engine transactions.
        # A checksum alone would accept a rehashed, invented phase or cursor.
        index, calls = 0, 0
        for tx in w._journal:
            command = tx.command
            if not isinstance(command, MemoryCommand) or not command.command_id.startswith("probe:"):
                continue
            if index >= len(result.groups):
                raise ValueError("recall after completed schedule")
            if (command.actor != result.actor or command.task_id != f"probe:{index}"
                    or command.command_id != f"probe:{index}:{calls}"
                    or command.work_limit != 1 or command.based_on
                    or not isinstance(command.payload, RecallQuery)
                    or command.payload.cues != tuple(card(f"arcana:{n}").ref for n in result.groups[index])
                    or command.payload.context != w.config.context
                    or command.payload.subject is not None or command.payload.relation != "owned_by"
                    or command.payload.visit_limit != 4096):
                raise ValueError("probe schedule does not match engine journal")
            calls += 1
            if tx.job.outcome == WorkStatus.COMPLETED:
                result.published.append(tx.job.result)
                index += 1
        result.index, result.calls = index, calls
        phase = None if result.phase is None else [result.phase.outer, result.phase.inner]
        if b["index"] != index or b["calls"] != calls or b["phase"] != phase:
            raise ValueError("invented probe cursor, calls, or phase")
        return result
