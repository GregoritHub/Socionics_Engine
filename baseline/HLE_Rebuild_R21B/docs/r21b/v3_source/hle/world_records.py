"""R2 operational records. All dynamics here are engineering choices (W01-W10)."""
from dataclasses import dataclass

from .contracts import (ActionRequest, ClaimStatus, EvidenceStatus, Kind,
    MemoryRevision, Moment, Observation, Proposition, Record, Ref, WorldEvent,
    WorkRecord, WorkStatus)


ENERGY = Ref(Kind.RULE, "r2.energy_quantum", 1)
TIME = Ref(Kind.RULE, "r2.time_quantum", 1)
CHANNEL = Ref(Kind.RULE, "r2.delivery", 1)
BASIS = Ref(Kind.RULE, "r2.cited_input", 1)
PRECONDITION = Ref(Kind.RULE, "r2.ownership_precondition", 1)
CORRECTION = Ref(Kind.RULE, "r2.prospective_correction", 1)
TRANSFER = Ref(Kind.PROCEDURE, "r2.transfer", 1)
INSPECT = Ref(Kind.PROCEDURE, "r2.inspect", 1)
SEND = Ref(Kind.PROCEDURE, "r2.send", 1)
RETAIN = Ref(Kind.PROCEDURE, "r2.retain", 1)
CREDIT = Ref(Kind.PROCEDURE, "r2.external_credit", 1)
COSTS = ((TRANSFER, 2), (INSPECT, 1), (SEND, 1), (RETAIN, 1))


@dataclass(frozen=True)
class Entity(Record):
    ref: Ref
    label: str
    role: str

    def __post_init__(self):
        super().__post_init__()
        if self.ref.kind != Kind.ENTITY or not self.label.strip() or self.role not in ("actor", "object"):
            raise ValueError("invalid entity descriptor")


@dataclass(frozen=True)
class Ownership(Record):
    item: Ref
    owner: Ref


@dataclass(frozen=True)
class Wallet(Record):
    actor: Ref
    energy: int
    time: int

    def __post_init__(self):
        super().__post_init__()
        if self.energy < 0 or self.time < 0:
            raise ValueError("negative wallet")


@dataclass(frozen=True)
class Witness(Record):
    observer: Ref
    item: Ref
    mode: str

    def __post_init__(self):
        super().__post_init__()
        if self.mode not in ("full", "occurrence"):
            raise ValueError("unknown visibility mode")


@dataclass(frozen=True)
class WorldConfig(Record):
    context: Ref
    entities: tuple[Entity, ...]
    actors: tuple[Ref, ...]
    ownership: tuple[Ownership, ...]
    wallets: tuple[Wallet, ...]
    witnesses: tuple[Witness, ...]
    message_links: tuple[tuple[Ref, Ref], ...]

    def __post_init__(self):
        super().__post_init__()
        descriptors = {e.ref: e for e in self.entities}
        if self.context.kind != Kind.CONTEXT or len(descriptors) != len(self.entities):
            raise ValueError("invalid context or duplicate descriptor")
        if not self.actors or len(set(self.actors)) != len(self.actors):
            raise ValueError("actors must be unique and nonempty")
        if any(a not in descriptors or descriptors[a].role != "actor" for a in self.actors):
            raise ValueError("unknown actor")
        by_key = {}
        for e in self.entities:
            by_key.setdefault(e.ref.key, []).append(e)
        for group in by_key.values():
            if sorted(e.ref.revision for e in group) != list(range(1, len(group) + 1)) or len({e.role for e in group}) != 1:
                raise ValueError("descriptor revisions must be consecutive and role preserving")
        if len({a.key for a in self.actors}) != len(self.actors):
            raise ValueError("one active revision per actor")
        items = [o.item for o in self.ownership]
        if len(set(items)) != len(items) or len({i.key for i in items}) != len(items):
            raise ValueError("one ownership slot per object")
        if any(o.item not in descriptors or descriptors[o.item].role != "object" or o.owner not in self.actors for o in self.ownership):
            raise ValueError("invalid ownership")
        if len(self.wallets) != len(self.actors) or {w.actor for w in self.wallets} != set(self.actors):
            raise ValueError("one wallet per actor")
        if len({(w.observer, w.item) for w in self.witnesses}) != len(self.witnesses):
            raise ValueError("duplicate witness rule")
        if any(w.observer not in self.actors or w.item not in items for w in self.witnesses):
            raise ValueError("unknown witness endpoint")
        if len(set(self.message_links)) != len(self.message_links) or any(a not in self.actors or b not in self.actors or a == b for a, b in self.message_links):
            raise ValueError("invalid directed message link")


@dataclass(frozen=True)
class MessageDraft(Record):
    content: tuple[Proposition, ...]


@dataclass(frozen=True)
class MemoryDraft(Record):
    key: str
    content: tuple[Proposition, ...]
    attitude: ClaimStatus
    reason: str

    def __post_init__(self):
        super().__post_init__()
        if not self.key.strip() or not self.reason.strip():
            raise ValueError("memory key and reason required")


@dataclass(frozen=True)
class Attempt(Record):
    command_id: str
    task_id: str
    action: ActionRequest
    message: MessageDraft | None = None
    memory: MemoryDraft | None = None

    def __post_init__(self):
        super().__post_init__()
        if not self.command_id.strip() or not self.task_id.strip():
            raise ValueError("command and task IDs required")


@dataclass(frozen=True)
class Credit(Record):
    command_id: str
    actor: Ref
    energy: int
    time: int
    reason: str

    def __post_init__(self):
        super().__post_init__()
        if not self.command_id.strip() or not self.reason.strip() or self.energy < 0 or self.time < 0:
            raise ValueError("invalid external credit")


@dataclass(frozen=True)
class Correction(Record):
    command_id: str
    target: Ref
    replacement_owner: Ref
    reason: str

    def __post_init__(self):
        super().__post_init__()
        if not self.command_id.strip() or not self.reason.strip() or self.target.kind != Kind.EVENT:
            raise ValueError("invalid record correction")


@dataclass(frozen=True)
class Tick(Record):
    command_id: str

    def __post_init__(self):
        super().__post_init__()
        if not self.command_id.strip():
            raise ValueError("command ID required")


Command = Attempt | Credit | Correction | Tick


@dataclass(frozen=True)
class Task(Record):
    actor: Ref
    key: str
    request: ActionRequest
    message: MessageDraft | None
    memory: MemoryDraft | None
    required: int
    completed: int
    outcome: WorkStatus

    def __post_init__(self):
        super().__post_init__()
        if not 0 <= self.completed <= self.required or self.required < 1:
            raise ValueError("invalid task extent")


@dataclass(frozen=True)
class Message(Record):
    ref: Ref
    sender: Ref
    receiver: Ref
    event: Ref
    at: Moment
    content: tuple[Proposition, ...]
    based_on: tuple[Ref, ...]


@dataclass(frozen=True)
class Transaction(Record):
    command: Command | None
    event: WorldEvent
    works: tuple[WorkRecord, ...]
    observations: tuple[Observation, ...]
    messages: tuple[Message, ...]
    memories: tuple[MemoryRevision, ...]
    task: Task | None


@dataclass(frozen=True)
class Checkpoint(Record):
    schema: str
    config: WorldConfig
    journal: tuple[Transaction, ...]


@dataclass(frozen=True)
class FactCheck(Record):
    claim: Proposition
    at: Moment
    status: EvidenceStatus
    evidence: tuple[Ref, ...]
    dependency_revision: int
    checked_at: Moment
    reason: str
