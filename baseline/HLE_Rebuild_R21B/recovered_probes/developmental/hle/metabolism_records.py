"""R4 executable movement values; numerical dynamics are experimental choices."""
from dataclasses import dataclass
from .contracts import (ActionRequest, Kind, MemoryRevision, MovementRecord,
    Observation, ProcessingStep, Proposition, Record, Ref, WorkRecord,
    WorkStatus, WorldEvent)
from .crux import FormalMovement, Perspective, Polarity, Route
from .memory_records import MemoryTransaction, text
from .model_a import TYPES, ELEMENT
from .world_records import Message, Task, Transaction, WorldConfig

METABOLISM = Ref(Kind.RULE, "r4.realized_processing", 1)
THEORIZE = Ref(Kind.PROCEDURE, "r4.theorize", 1)
APPLY = Ref(Kind.PROCEDURE, "r4.apply", 1)
EMBODY = Ref(Kind.PROCEDURE, "r4.embody", 1)
UNDERSTAND = Ref(Kind.PROCEDURE, "r4.understand", 1)
OPERATIONS = (THEORIZE, APPLY, EMBODY, UNDERSTAND)


@dataclass(frozen=True)
class Profile(Record):
    owner: Ref
    tim: str
    active: str = "ne"
    perspective: Perspective = Perspective.I

    def __post_init__(self):
        super().__post_init__()
        if self.owner.kind != Kind.ENTITY or self.tim not in TYPES or self.active not in ELEMENT:
            raise ValueError("known actor, type and active element required")


@dataclass(frozen=True)
class ProcessingPolicy(Record):
    # Controls are harness configuration, immutable for a session.
    typed_routing: bool = True
    positional_prices: bool = True


@dataclass(frozen=True)
class TheorizeDraft(Record):
    recall: Ref
    item: Ref
    recipient: Ref


@dataclass(frozen=True)
class ApplyDraft(Record):
    account: Ref


@dataclass(frozen=True)
class EmbodyDraft(Record):
    application: Ref
    key: str
    expected: Ref | None = None

    def __post_init__(self):
        super().__post_init__(); text(self.key)


@dataclass(frozen=True)
class UnderstandDraft(Record):
    account: Ref
    key: str
    expected: Ref | None = None

    def __post_init__(self):
        super().__post_init__(); text(self.key)


Payload = TheorizeDraft | ApplyDraft | EmbodyDraft | UnderstandDraft


def operation(payload):
    return {TheorizeDraft: THEORIZE, ApplyDraft: APPLY,
            EmbodyDraft: EMBODY, UnderstandDraft: UNDERSTAND}[type(payload)]


def movement(payload):
    origin, destination, face = {
        TheorizeDraft: (Perspective.I, Perspective.ITS, Polarity.ACCUMULATION),
        ApplyDraft: (Perspective.ITS, Perspective.IT, Polarity.EXPENDITURE),
        EmbodyDraft: (Perspective.IT, Perspective.I, Polarity.ACCUMULATION),
        UnderstandDraft: (Perspective.ITS, Perspective.I, Polarity.ACCUMULATION),
    }[type(payload)]
    return FormalMovement(Route(origin, destination), face)


@dataclass(frozen=True)
class MetabolicCommand(Record):
    command_id: str
    task_id: str
    actor: Ref
    payload: Payload
    work_limit: int = 64

    def __post_init__(self):
        super().__post_init__(); text(self.command_id); text(self.task_id)
        if self.actor.kind != Kind.ENTITY or self.work_limit < 1:
            raise ValueError("actor and positive work limit required")


@dataclass(frozen=True)
class ProcessingState(Record):
    ref: Ref
    owner: Ref
    active: str
    perspective: Perspective
    busy: str | None


@dataclass(frozen=True)
class RoutePlan(Record):
    declared_type: str
    routing_type: str
    path: tuple[str, ...]
    positions: tuple[int, ...]
    support_position: int
    support_index: int
    hop_units: tuple[int, ...]
    content_units: int

    @property
    def required(self): return sum(self.hop_units) + self.content_units


@dataclass(frozen=True)
class Account(Record):
    ref: Ref
    owner: Ref
    item: Ref
    recipient: Ref
    claim: Proposition | None
    evidence: tuple[Ref, ...]
    recall: Ref
    guard: Ref | None
    uncertainty: str


@dataclass(frozen=True)
class Capability(Record):
    ref: Ref
    owner: Ref
    rule: str
    application: Ref
    evidence: tuple[Ref, ...]


@dataclass(frozen=True)
class Enactment(Record):
    ref: Ref
    owner: Ref
    account: Ref
    request: ActionRequest
    observation: Ref
    outcome: WorkStatus


@dataclass(frozen=True)
class Application(Record):
    ref: Ref
    owner: Ref
    account: Ref
    enactments: tuple[Ref, ...]
    observations: tuple[Ref, ...]
    discrepancy: bool
    outcome: WorkStatus


@dataclass(frozen=True)
class MetabolicJob(Record):
    command: MetabolicCommand
    plan: RoutePlan
    basis: tuple[Ref, ...]
    completed_units: int = 0
    action_units: int = 0
    phase: str = "processing"
    action: ActionRequest | None = None
    enactments: tuple[Ref, ...] = ()
    observations: tuple[Ref, ...] = ()
    discrepancy: bool = False
    history: tuple[ProcessingStep, ...] = ()
    attempts: int = 0
    outcome: WorkStatus = WorkStatus.PENDING
    result: Ref | None = None


Extra = ProcessingState | Account | Capability | Enactment | Application | MovementRecord


@dataclass(frozen=True)
class MetabolicTransaction(Record):
    command: MetabolicCommand
    event: WorldEvent
    works: tuple[WorkRecord, ...]
    observations: tuple[Observation, ...]
    messages: tuple[Message, ...]
    memories: tuple[MemoryRevision, ...]
    task: Task | None
    extra: tuple[Extra, ...]
    state: ProcessingState
    job: MetabolicJob


@dataclass(frozen=True)
class MetabolicCheckpoint(Record):
    schema: str
    config: WorldConfig
    profiles: tuple[Profile, ...]
    policy: ProcessingPolicy
    journal: tuple[Transaction | MemoryTransaction | MetabolicTransaction, ...]
