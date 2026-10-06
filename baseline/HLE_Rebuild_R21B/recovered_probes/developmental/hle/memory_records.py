"""Exact R3 operation values. Search and revision are experimental policies."""
from dataclasses import dataclass
from .contracts import (ClaimStatus, CueBinding, CursorState, Kind, MemoryRevision,
    Moment, Observation, Proposition, Record, Ref, TimeScope, WorkRecord,
    WorkStatus, WorldEvent)
from .world_records import Message, Task, Transaction, WorldConfig

STORE = Ref(Kind.PROCEDURE, "r3.write", 1)
BIND = Ref(Kind.PROCEDURE, "r3.bind", 1)
DECLARE = Ref(Kind.PROCEDURE, "r3.context", 1)
CONFIGURE = Ref(Kind.PROCEDURE, "r3.cursor", 1)
ACK = Ref(Kind.PROCEDURE, "r3.acknowledge", 1)
RECALL = Ref(Kind.PROCEDURE, "r3.recall", 1)
LINKED = Ref(Kind.PROCEDURE, "r3.contextual_breadth_first", 1)
MEMORY_RULE = Ref(Kind.RULE, "r3.memory_operations", 1)
OPERATIONS = (STORE, BIND, DECLARE, CONFIGURE, ACK, RECALL, LINKED)


def text(value):
    if not value.strip():
        raise ValueError("nonblank text required")


@dataclass(frozen=True)
class WriteDraft(Record):
    key: str
    content: tuple[Proposition, ...]
    links: tuple[Ref, ...]
    attitude: ClaimStatus
    expected: Ref | None
    reason: str

    def __post_init__(self):
        super().__post_init__(); text(self.key); text(self.reason)
        if any(r.kind != Kind.MEMORY for r in self.links) or len(set(self.links)) != len(self.links):
            raise ValueError("unique exact memory links required")
        if self.expected is not None and self.expected.kind != Kind.MEMORY:
            raise ValueError("memory predecessor required")


@dataclass(frozen=True)
class BindDraft(Record):
    key: str
    cue: Ref
    context: Ref
    target: Ref
    scope: TimeScope
    expected: Ref | None = None

    def __post_init__(self):
        super().__post_init__(); text(self.key)
        if (self.cue.kind != Kind.CUE or self.context.kind != Kind.CONTEXT
                or self.target.kind != Kind.MEMORY
                or self.expected is not None and self.expected.kind != Kind.BINDING):
            raise ValueError("invalid binding reference kinds")


@dataclass(frozen=True)
class ContextDraft(Record):
    key: str
    label: str

    def __post_init__(self):
        super().__post_init__(); text(self.key); text(self.label)


@dataclass(frozen=True)
class CursorDraft(Record):
    cues: tuple[Ref, ...]
    policy: Ref | None
    max_hops: int
    expected: Ref | None = None

    def __post_init__(self):
        super().__post_init__()
        if self.max_hops < 0 or self.policy not in (None, LINKED):
            raise ValueError("unsupported navigation setting")
        if self.policy is None and self.max_hops != 0:
            raise ValueError("unmanaged cursor uses direct cues only")
        if self.expected is not None and self.expected.kind != Kind.CURSOR:
            raise ValueError("cursor predecessor required")


@dataclass(frozen=True)
class AckDraft(Record):
    expected: int
    through: int

    def __post_init__(self):
        super().__post_init__()
        if not 0 <= self.expected <= self.through:
            raise ValueError("invalid inbox acknowledgement")


@dataclass(frozen=True)
class RecallQuery(Record):
    cues: tuple[Ref, ...]
    context: Ref
    at: Moment
    subject: Ref | None = None
    relation: str | None = None
    visit_limit: int = 64

    def __post_init__(self):
        super().__post_init__()
        if not self.cues or len(set(self.cues)) != len(self.cues) or any(r.kind != Kind.CUE for r in self.cues):
            raise ValueError("nonempty unique cue sequence required")
        if self.context.kind != Kind.CONTEXT or self.visit_limit < 1:
            raise ValueError("context and positive visit limit required")
        if self.relation is not None: text(self.relation)


Payload = WriteDraft | BindDraft | ContextDraft | CursorDraft | AckDraft | RecallQuery


@dataclass(frozen=True)
class MemoryCommand(Record):
    command_id: str
    task_id: str
    actor: Ref
    payload: Payload
    based_on: tuple[Ref, ...] = ()
    work_limit: int = 64

    def __post_init__(self):
        super().__post_init__(); text(self.command_id); text(self.task_id)
        if self.actor.kind != Kind.ENTITY or self.work_limit < 1 or len(set(self.based_on)) != len(self.based_on):
            raise ValueError("invalid memory command")


@dataclass(frozen=True)
class MemoryContext(Record):
    ref: Ref
    owner: Ref
    label: str


@dataclass(frozen=True)
class Navigation(Record):
    cursor: CursorState
    max_hops: int

    @property
    def ref(self): return self.cursor.ref

    @property
    def owner(self): return self.cursor.owner


@dataclass(frozen=True)
class InboxState(Record):
    ref: Ref
    owner: Ref
    after: int


@dataclass(frozen=True)
class Visit(Record):
    memory: Ref
    parent: Ref | None
    depth: int


@dataclass(frozen=True)
class RecallHit(Record):
    memory: Ref
    proposition_indexes: tuple[int, ...]


@dataclass(frozen=True)
class RecallResult(Record):
    ref: Ref
    owner: Ref
    query: RecallQuery
    selected_at: Moment
    navigation: Ref | None
    max_hops: int
    bindings: tuple[Ref, ...]
    visited: tuple[Visit, ...]
    hits: tuple[RecallHit, ...]
    truncated: bool


@dataclass(frozen=True)
class MemoryJob(Record):
    command: MemoryCommand
    completed_units: int
    outcome: WorkStatus
    selected_at: Moment | None = None
    navigation: Ref | None = None
    max_hops: int = 0
    bindings: tuple[Ref, ...] = ()
    frontier: tuple[Visit, ...] = ()
    visited: tuple[Visit, ...] = ()
    hits: tuple[RecallHit, ...] = ()
    truncated: bool = False
    result: Ref | None = None


@dataclass(frozen=True)
class MemoryTransaction(Record):
    command: MemoryCommand
    event: WorldEvent
    works: tuple[WorkRecord, ...]
    observations: tuple[Observation, ...]
    messages: tuple[Message, ...]
    memories: tuple[MemoryRevision, ...]
    task: Task | None
    bindings: tuple[CueBinding, ...]
    contexts: tuple[MemoryContext, ...]
    navigations: tuple[Navigation, ...]
    inboxes: tuple[InboxState, ...]
    recalls: tuple[RecallResult, ...]
    job: MemoryJob


@dataclass(frozen=True)
class MemoryCheckpoint(Record):
    schema: str
    config: WorldConfig
    journal: tuple[Transaction | MemoryTransaction, ...]


def operation(payload):
    return {WriteDraft: STORE, BindDraft: BIND, ContextDraft: DECLARE,
            CursorDraft: CONFIGURE, AckDraft: ACK, RecallQuery: RECALL}[type(payload)]


def write_cost(payload):
    if type(payload) is WriteDraft:
        return 1 + len(payload.content) + len(payload.links)
    return 2 if type(payload) is BindDraft else 1
