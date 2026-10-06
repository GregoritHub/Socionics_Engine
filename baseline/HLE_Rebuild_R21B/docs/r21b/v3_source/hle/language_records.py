"""R8 finite compositional language; elected semantics, immutable provenance."""
from dataclasses import dataclass
from .contracts import (Record, Ref, Kind, Moment, MemoryRevision, Observation,
    WorkRecord, WorkStatus, WorldEvent)
from .memory_records import text, MemoryTransaction
from .metabolism_records import ProcessingPolicy, Profile, MetabolicTransaction, ProcessingState
from .semantic_records import SemanticPolicy, SemanticRoute, CancelSemantic
from .assessment_records import AssessmentTransaction
from .socion_records import AgentPolicy, SocionTransaction
from .composition_records import CompositionTransaction
from .world_records import WorldConfig, Transaction, Message, Task

LANGUAGE = Ref(Kind.RULE, 'r8.language', 1)
LANGUAGE_WORK = Ref(Kind.PROCEDURE, 'r8.semantic_work', 1)

@dataclass(frozen=True)
class Pattern(Record):
    subject: int
    owner: int
    def __post_init__(self):
        super().__post_init__()
        if min(self.subject,self.owner)<0: raise ValueError('nonnegative argument slots required')

@dataclass(frozen=True)
class Meaning(Record):
    token: str
    patterns: tuple[Pattern, ...]
    arity: int
    def __post_init__(self):
        super().__post_init__(); text(self.token)
        slots={i for p in self.patterns for i in (p.subject,p.owner)}
        if not self.patterns or len(set(self.patterns))!=len(self.patterns) or slots!=set(range(self.arity)):
            raise ValueError('nonempty unique pattern with contiguous slots required')

@dataclass(frozen=True)
class WordUse(Record):
    token: str
    fingerprint: str
    arguments: tuple[Ref, ...]
    def __post_init__(self):
        super().__post_init__(); text(self.token); text(self.fingerprint)

@dataclass(frozen=True)
class Act(Record):
    operation: str
    item: Ref
    recipient: Ref | None = None
    def __post_init__(self):
        super().__post_init__()
        if self.operation not in ('inspect','transfer') or (self.operation=='transfer')!=(self.recipient is not None):
            raise ValueError('invalid action grammar')

@dataclass(frozen=True)
class Speech(Record):
    mode: str
    calls: tuple[WordUse, ...]
    actions: tuple[Act, ...]
    def __post_init__(self):
        super().__post_init__()
        if self.mode not in ('request','explain','commit') or not self.calls or not self.actions:
            raise ValueError('nonempty supported speech required')

@dataclass(frozen=True)
class Learn(Record):
    token: str
    access: Ref
    observation: Ref | None = None
    expected: Ref | None = None

@dataclass(frozen=True)
class Produce(Record):
    speech: Speech

@dataclass(frozen=True)
class Interpret(Record):
    observation: Ref
    access: Ref

@dataclass(frozen=True)
class Intend(Record):
    utterance: Ref
    access: Ref

@dataclass(frozen=True)
class LanguageCommand(Record):
    command_id: str
    task_id: str
    actor: Ref
    payload: Learn | Produce | Interpret | Intend
    work_limit: int = 64
    def __post_init__(self):
        super().__post_init__(); text(self.command_id); text(self.task_id)
        if self.work_limit<1: raise ValueError('positive work limit required')

@dataclass(frozen=True)
class Lexeme(Record):
    ref: Ref
    owner: Ref
    meaning: Meaning
    access: Ref
    previous: Ref | None
    source: Ref | None

@dataclass(frozen=True)
class Utterance(Record):
    ref: Ref
    owner: Ref
    speech: Speech
    definitions: tuple[Ref, ...]

@dataclass(frozen=True)
class Interpretation(Record):
    ref: Ref
    owner: Ref
    source: Ref
    access: Ref
    speech: Speech | None
    status: str
    definitions: tuple[Ref, ...]
    reason: str
    debtor: Ref | None = None

@dataclass(frozen=True)
class LanguageJob(Record):
    command: LanguageCommand
    required: int
    candidate: Lexeme | Utterance | Interpretation
    paid: int = 0
    outcome: WorkStatus = WorkStatus.PENDING
    result: Ref | None = None
    route: SemanticRoute | None = None

@dataclass(frozen=True)
class LanguageTransaction(Record):
    command: LanguageCommand | CancelSemantic
    event: WorldEvent
    works: tuple[WorkRecord, ...] = ()
    observations: tuple[Observation, ...] = ()
    messages: tuple[Message, ...] = ()
    memories: tuple[MemoryRevision, ...] = ()
    task: Task | None = None
    extra: tuple[Lexeme | Utterance | Interpretation, ...] = ()
    job: LanguageJob | None = None
    state: ProcessingState | None = None

@dataclass(frozen=True)
class LanguageCheckpoint(Record):
    schema: str
    config: WorldConfig
    profiles: tuple[Profile, ...]
    policy: ProcessingPolicy
    agents: tuple[AgentPolicy, ...]
    journal: tuple[Transaction | MemoryTransaction | MetabolicTransaction | AssessmentTransaction | SocionTransaction | CompositionTransaction | LanguageTransaction, ...]
    semantic_policy: SemanticPolicy = SemanticPolicy()

