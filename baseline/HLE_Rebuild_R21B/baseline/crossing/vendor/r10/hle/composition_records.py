"""R7 versioned contextual DAG proposal; all prices and semantics are elected."""
from dataclasses import dataclass
from .contracts import (Atom, EvidenceStatus, Kind, MemoryRevision, Moment,
    Observation, Record, Ref, WorkRecord, WorkStatus, WorldEvent)
from .memory_records import MemoryTransaction, RecallHit, text
from .metabolism_records import MetabolicTransaction, ProcessingPolicy, Profile
from .assessment_records import AssessmentTransaction
from .socion_records import AgentPolicy, SocionTransaction
from .world_records import Message, Task, Transaction, WorldConfig

COMPOSITION = Ref(Kind.RULE, "r7.contextual_dag", 1)
FOLD = Ref(Kind.PROCEDURE, "r7.fold", 1)
UNFOLD = Ref(Kind.PROCEDURE, "r7.unfold", 1)


@dataclass(frozen=True)
class Part(Record):
    role: str
    target: Ref
    context: Ref

    def __post_init__(self):
        super().__post_init__(); text(self.role)
        if self.context.kind != Kind.CONTEXT: raise ValueError("context required")


@dataclass(frozen=True)
class FoldDraft(Record):
    key: str
    parts: tuple[Part, ...]
    expected: Ref | None = None

    def __post_init__(self):
        super().__post_init__(); text(self.key)
        if not self.parts or len({(p.role,p.context) for p in self.parts}) != len(self.parts):
            raise ValueError("nonempty distinct role/context pairs required")


@dataclass(frozen=True)
class UnfoldDraft(Record):
    root: Ref
    context: Ref | None
    at: Moment

    def __post_init__(self):
        super().__post_init__()
        if self.context is not None and self.context.kind != Kind.CONTEXT:
            raise ValueError("context or full structural unfold required")


@dataclass(frozen=True)
class CompositionCommand(Record):
    command_id: str
    task_id: str
    actor: Ref
    payload: FoldDraft | UnfoldDraft
    work_limit: int = 64

    def __post_init__(self):
        super().__post_init__(); text(self.command_id); text(self.task_id)
        if self.work_limit < 1: raise ValueError("positive work limit required")


@dataclass(frozen=True)
class CompositionRevision(Record):
    ref: Ref
    owner: Ref
    at: Moment
    parts: tuple[Part, ...]
    previous: Ref | None
    law: Ref = COMPOSITION


@dataclass(frozen=True)
class Edge(Record):
    parent: Ref
    part: Part


@dataclass(frozen=True)
class UnfoldResult(Record):
    ref: Ref
    owner: Ref
    query: UnfoldDraft
    nodes: tuple[Ref, ...]
    edges: tuple[Edge, ...]
    hits: tuple[RecallHit, ...]
    capabilities: tuple[Ref, ...]
    units: int
    truncated: bool = False


@dataclass(frozen=True)
class CompositionJob(Record):
    command: CompositionCommand
    completed: int = 0
    node_paid: int = 0
    frontier: tuple[Ref, ...] = ()
    nodes: tuple[Ref, ...] = ()
    edges: tuple[Edge, ...] = ()
    hits: tuple[RecallHit, ...] = ()
    capabilities: tuple[Ref, ...] = ()
    outcome: WorkStatus = WorkStatus.PENDING
    result: Ref | None = None


@dataclass(frozen=True)
class Expectation(Record):
    subject: Ref
    relation: str
    value: Atom

    def __post_init__(self):
        super().__post_init__(); text(self.relation)


@dataclass(frozen=True)
class DeclareCompositionTest(Record):
    command_id: str
    key: str
    root: Ref
    context: Ref
    claims: tuple[Expectation, ...] = ()
    required_rules: tuple[str, ...] = ()
    max_units: int = 2000

    def __post_init__(self):
        super().__post_init__(); text(self.command_id); text(self.key)
        if (self.context.kind != Kind.CONTEXT or self.max_units < 0
                or not (self.claims or self.required_rules)
                or len({(x.subject,x.relation) for x in self.claims}) != len(self.claims)
                or len(set(self.required_rules)) != len(self.required_rules)):
            raise ValueError("nonempty unique discriminating constraints and nonnegative budget required")
        for rule in self.required_rules: text(rule)


@dataclass(frozen=True)
class CompositionTest(Record):
    ref: Ref
    request: DeclareCompositionTest
    at: Moment


@dataclass(frozen=True)
class AssessCompositions(Record):
    command_id: str
    limit: int = 1

    def __post_init__(self):
        super().__post_init__(); text(self.command_id)
        if self.limit < 1: raise ValueError("positive assessment limit required")


@dataclass(frozen=True)
class UseWitness(Record):
    access: Ref
    account: Ref
    application: Ref
    retained: Ref
    units: int


@dataclass(frozen=True)
class CompositionReport(Record):
    ref: Ref
    test: Ref
    at: Moment
    nodes: tuple[Ref, ...]
    stale: tuple[Ref, ...]
    accesses: tuple[Ref, ...]
    uses: tuple[UseWitness, ...]
    agreement: EvidenceStatus
    capacity: EvidenceStatus
    freshness: EvidenceStatus
    cross_level: EvidenceStatus
    identity: EvidenceStatus
    factual: EvidenceStatus
    path: EvidenceStatus
    usefulness: EvidenceStatus
    factual_counts: tuple[int, int, int]
    closure: EvidenceStatus = EvidenceStatus.UNASSESSED


@dataclass(frozen=True)
class CompositionTransaction(Record):
    command: CompositionCommand | DeclareCompositionTest | AssessCompositions
    event: WorldEvent
    works: tuple[WorkRecord, ...] = ()
    observations: tuple[Observation, ...] = ()
    messages: tuple[Message, ...] = ()
    memories: tuple[MemoryRevision, ...] = ()
    task: Task | None = None
    extra: tuple[CompositionRevision | UnfoldResult | CompositionTest | CompositionReport, ...] = ()
    job: CompositionJob | None = None


@dataclass(frozen=True)
class CompositionCheckpoint(Record):
    schema: str
    config: WorldConfig
    profiles: tuple[Profile, ...]
    policy: ProcessingPolicy
    agents: tuple[AgentPolicy, ...]
    journal: tuple[Transaction | MemoryTransaction | MetabolicTransaction | AssessmentTransaction | SocionTransaction | CompositionTransaction, ...]
