"""R9 elected finite organization grammar and exact local protocol records."""
from dataclasses import dataclass
from .contracts import (Record, Ref, Kind, MemoryRevision, Observation, WorkRecord,
    WorkStatus, WorldEvent)
from .memory_records import text, MemoryTransaction
from .metabolism_records import ProcessingPolicy, Profile, MetabolicTransaction, ProcessingState
from .semantic_records import SemanticPolicy, SemanticRoute, CancelSemantic
from .assessment_records import AssessmentTransaction
from .socion_records import AgentPolicy, SocionTransaction
from .composition_records import CompositionTransaction
from .language_records import Meaning, Speech, LanguageTransaction
from .world_records import WorldConfig, Transaction, Message, Task

ORGANIZATION = Ref(Kind.RULE, 'r9.local_agreement', 1)
ORGANIZE = Ref(Kind.PROCEDURE, 'r9.organization_work', 1)

@dataclass(frozen=True)
class OrganizationPolicy(Record):
    owner: Ref
    max_action_cost: int = 8
    max_members: int = 8
    minimum_support: int = 2
    def __post_init__(self):
        super().__post_init__()
        if self.max_action_cost < 1 or self.max_members < 2 or self.minimum_support < 2:
            raise ValueError('positive cost, at least two members and two demonstrations required')

@dataclass(frozen=True)
class Terms(Record):
    identity: str
    generation: int
    predecessor: str | None
    item: Ref
    meaning: Meaning
    steps: tuple[str, ...]
    members: tuple[Ref, ...]
    def __post_init__(self):
        super().__post_init__(); text(self.identity)
        if self.generation < 1 or (self.generation == 1) != (self.predecessor is None):
            raise ValueError('versioned lineage required')
        if not self.steps or self.steps[-1] != 'transfer' or any(s != 'inspect' for s in self.steps[:-1]):
            raise ValueError('inspection prefix followed by one transfer required')
        if len(self.members) < 2 or len(set(self.members)) != len(self.members):
            raise ValueError('distinct membership cohort required')

@dataclass(frozen=True)
class OrganizationPacket(Record):
    kind: str
    sender: Ref
    terms: Terms
    status: str
    reason: str

@dataclass(frozen=True)
class Formulate(Record):
    access: Ref
    state: Ref | None = None

@dataclass(frozen=True)
class ReviewTerms(Record):
    proposal: Ref
    access: Ref

@dataclass(frozen=True)
class Ratify(Record):
    review: Ref
    votes: tuple[Ref, ...]

@dataclass(frozen=True)
class Join(Record):
    offer: Ref
    access: Ref

@dataclass(frozen=True)
class Attend(Record):
    state: Ref
    notice: Ref

@dataclass(frozen=True)
class Leave(Record):
    state: Ref
    reason: str
    def __post_init__(self):
        super().__post_init__(); text(self.reason)

@dataclass(frozen=True)
class Dispute(Record):
    run: Ref

@dataclass(frozen=True)
class Perform(Record):
    state: Ref
    access: Ref

@dataclass(frozen=True)
class OrganizationCommand(Record):
    command_id: str
    task_id: str
    actor: Ref
    payload: Formulate | ReviewTerms | Ratify | Join | Attend | Leave | Dispute | Perform
    work_limit: int = 64
    def __post_init__(self):
        super().__post_init__(); text(self.command_id); text(self.task_id)
        if self.work_limit < 1: raise ValueError('positive work limit required')

@dataclass(frozen=True)
class OrganizationResult(Record):
    ref: Ref
    owner: Ref
    kind: str
    terms: Terms | None
    status: str
    reason: str
    sources: tuple[Ref, ...]
    previous: Ref | None = None
    speech: Speech | None = None

@dataclass(frozen=True)
class OrganizationJob(Record):
    command: OrganizationCommand
    required: int
    candidate: OrganizationResult
    paid: int = 0
    outcome: WorkStatus = WorkStatus.PENDING
    result: Ref | None = None
    route: SemanticRoute | None = None

@dataclass(frozen=True)
class OrganizationTransaction(Record):
    command: OrganizationCommand | CancelSemantic
    event: WorldEvent
    works: tuple[WorkRecord, ...] = ()
    observations: tuple[Observation, ...] = ()
    messages: tuple[Message, ...] = ()
    memories: tuple[MemoryRevision, ...] = ()
    task: Task | None = None
    extra: tuple[OrganizationResult, ...] = ()
    job: OrganizationJob | None = None
    state: ProcessingState | None = None

@dataclass(frozen=True)
class OrganizationCheckpoint(Record):
    schema: str
    config: WorldConfig
    profiles: tuple[Profile, ...]
    policy: ProcessingPolicy
    agents: tuple[AgentPolicy, ...]
    organization_policies: tuple[OrganizationPolicy, ...]
    journal: tuple[Transaction | MemoryTransaction | MetabolicTransaction | AssessmentTransaction | SocionTransaction | CompositionTransaction | LanguageTransaction | OrganizationTransaction, ...]

    semantic_policy: SemanticPolicy = SemanticPolicy()

@dataclass(frozen=True)
class Practice(Record):
    """Derived incremental summary; every counted endpoint remains in the journal."""
    item: Ref
    meaning: Meaning
    steps: tuple[str, ...]
    partners: tuple[Ref, ...]
    successes: int
    failures: int
    examples: tuple[Ref, ...]
