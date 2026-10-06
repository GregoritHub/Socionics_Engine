"""R13 versioned commands over the full continuing OrganizationWorld journal."""
from dataclasses import dataclass
from .contracts import Record, Ref, Kind, Moment, Observation, MemoryRevision, WorkRecord, WorkStatus, WorldEvent
from .development_contracts import VersionOne
from .memory_records import WriteDraft, MemoryTransaction
from .metabolism_records import Profile, ProcessingPolicy, ProcessingState, RoutePlan, MetabolicTransaction
from .assessment_records import AssessmentTransaction
from .socion_records import AgentPolicy, SocionTransaction
from .composition_records import CompositionTransaction
from .language_records import LanguageTransaction
from .organization_records import OrganizationPolicy, OrganizationTransaction
from .semantic_records import SemanticPolicy
from .world_records import WorldConfig, Transaction, Message, Task

CONTENT_RULE = Ref(Kind.RULE, 'r13.content_and_meaning.v1', 1)
CONTENT_WORK = Ref(Kind.PROCEDURE, 'r13.content_processing.v1', 1)
MEANING_WORK = Ref(Kind.PROCEDURE, 'r13.meaning_revision.v1', 1)
WIRE = 'experiment.content.v1'  # Existing finite wire identity is preserved.
MEANING_PROPOSAL = 'r13.meaning_proposal.v1'
DONE = (WorkStatus.COMPLETED, WorkStatus.FAILED)


def _command(command):
    if not command.command_id.strip() or not command.task_id.strip() or command.actor.kind != Kind.ENTITY:
        raise ValueError('actor and nonblank command/task identity required')


@dataclass(frozen=True)
class ContentCommand(VersionOne):
    command_id: str
    task_id: str
    actor: Ref
    operator: str
    sources: tuple[Ref, ...]
    access: Ref | None = None
    work_limit: int = 64

    def __post_init__(self):
        super().__post_init__(); _command(self)
        if not self.operator or self.work_limit < 1 or len(set(self.sources)) != len(self.sources):
            raise ValueError('unique sources and positive work limit required')
        if self.access is not None and self.access.kind != Kind.EVIDENCE:
            raise ValueError('paid recall evidence required')


@dataclass(frozen=True)
class MeaningCommand(VersionOne):
    command_id: str
    task_id: str
    actor: Ref
    cue: Ref
    context: Ref
    scene: str
    experience: Ref
    application: Ref
    access: Ref
    key: str
    expected: Ref | None = None
    work_limit: int = 64

    def __post_init__(self):
        super().__post_init__(); _command(self)
        if self.cue.kind != Kind.CUE or self.context.kind != Kind.CONTEXT or self.experience.kind != Kind.MEMORY:
            raise ValueError('cue, context, retained experience required')
        if self.access.kind != Kind.EVIDENCE or not self.scene or not self.key or self.work_limit < 1:
            raise ValueError('paid contextual access and named scene/key required')
        if self.expected is not None and self.expected.kind != Kind.MEMORY:
            raise ValueError('exact preceding meaning revision required')


@dataclass(frozen=True)
class CancelDevelopment(VersionOne):
    command_id: str
    task_id: str
    actor: Ref
    reason: str

    def __post_init__(self):
        super().__post_init__(); _command(self)
        if not self.reason.strip(): raise ValueError('reason required')


@dataclass(frozen=True)
class DevelopmentJob(VersionOne):
    command: ContentCommand | MeaningCommand
    started_at: Moment
    plan: RoutePlan
    candidate: str | WriteDraft
    sources: tuple[Ref, ...]
    dependencies: tuple[Ref, ...]
    paid: int = 0
    outcome: WorkStatus = WorkStatus.PENDING
    result: Ref | None = None

    def __post_init__(self):
        super().__post_init__()
        if not 0 <= self.paid <= self.plan.required: raise ValueError('invalid paid progress')
        if (self.result is not None) != (self.outcome == WorkStatus.COMPLETED):
            raise ValueError('only completed work publishes a result')


@dataclass(frozen=True)
class DevelopmentTransaction(Record):
    command: ContentCommand | MeaningCommand | CancelDevelopment
    event: WorldEvent
    works: tuple[WorkRecord, ...]
    observations: tuple[Observation, ...]
    state: ProcessingState
    job: DevelopmentJob
    messages: tuple[Message, ...] = ()
    memories: tuple[MemoryRevision, ...] = ()
    task: Task | None = None


JournalEntry = (Transaction | MemoryTransaction | MetabolicTransaction | AssessmentTransaction |
                SocionTransaction | CompositionTransaction | LanguageTransaction | OrganizationTransaction |
                DevelopmentTransaction)


@dataclass(frozen=True)
class DevelopmentCheckpoint(VersionOne):
    schema: str
    config: WorldConfig
    profiles: tuple[Profile, ...]
    policy: ProcessingPolicy
    agents: tuple[AgentPolicy, ...]
    organization_policies: tuple[OrganizationPolicy, ...]
    semantic_policy: SemanticPolicy
    journal: tuple[JournalEntry, ...]
