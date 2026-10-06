"""R6 exchange records. Dynamics and prices are explicit experimental policies."""
from dataclasses import dataclass
from .contracts import (EvidenceStatus, Kind, MemoryRevision, Moment, Observation,
    Proposition, Record, Ref, WorkRecord, WorkStatus, WorldEvent)
from .assessment_records import AssessmentTransaction, PhaseEvidence
from .memory_records import MemoryCommand, MemoryTransaction, text
from .metabolism_records import (Account, Application, MetabolicCommand,
    MetabolicTransaction, ProcessingPolicy, ProcessingState, Profile, RoutePlan)
from .world_records import Attempt, Message, Task, Transaction, WorldConfig

SOCION = Ref(Kind.RULE, "r6.participant_policy", 1)
RECEIVE = Ref(Kind.PROCEDURE, "r6.routed_reception", 1)


@dataclass(frozen=True)
class AgentPolicy(Record):
    owner: Ref
    response: str = "adaptive"
    ask: bool = True
    use_lesson: bool = True
    patience: int = 80
    work_limit: int = 64

    def __post_init__(self):
        super().__post_init__()
        if self.response not in ("adaptive", "fresh", "silent") or self.patience < 1 or self.work_limit < 1:
            raise ValueError("invalid participant policy")


@dataclass(frozen=True)
class Goal(Record):
    key: str
    actor: Ref
    item: Ref
    partner: Ref

    def __post_init__(self):
        super().__post_init__(); text(self.key)
        if self.actor == self.partner: raise ValueError("distinct participants required")


@dataclass(frozen=True)
class Notice(Record):
    observation: Ref
    source: Ref
    sender: Ref | None
    kind: str
    claim: Proposition
    reply_to: Ref | None = None
    sender_type: str = "ile"
    element: str = "ne"


@dataclass(frozen=True)
class ReceiveCommand(Record):
    command_id: str
    task_id: str
    actor: Ref
    observation: Ref
    work_limit: int = 64

    def __post_init__(self):
        super().__post_init__(); text(self.command_id); text(self.task_id)
        if self.work_limit < 1: raise ValueError("positive work limit required")


@dataclass(frozen=True)
class Reception(Record):
    ref: Ref
    owner: Ref
    command: ReceiveCommand
    source: Ref
    sender: Ref
    source_position: int
    landing_position: int
    plan: RoutePlan
    completed: int
    outcome: WorkStatus


Action = Attempt | MemoryCommand | MetabolicCommand | ReceiveCommand


@dataclass(frozen=True)
class AgentState(Record):
    ref: Ref
    owner: Ref
    cursor: int = 0
    goals: tuple[Goal, ...] = ()
    goal: Goal | None = None
    phase: str = "idle"
    mode: str = ""
    item: Ref | None = None
    partner: Ref | None = None
    notice: Notice | None = None
    query: Ref | None = None
    received: Ref | None = None
    account: Ref | None = None
    application: Ref | None = None
    lesson: Ref | None = None
    pending: Action | None = None
    waiting: int = 0


@dataclass(frozen=True)
class AgentView(Record):
    state: AgentState
    policy: AgentPolicy
    context: Ref
    now: Moment
    notice: Notice | None
    memory: MemoryRevision | None
    lesson: MemoryRevision | None
    binding: Ref | None
    lesson_binding: Ref | None
    result: Ref | None
    account: Account | None
    application: Application | None
    observations: tuple[Observation, ...]
    pending_status: WorkStatus | None
    energy: int
    time: int


@dataclass(frozen=True)
class AddGoal(Record):
    command_id: str
    goal: Goal


@dataclass(frozen=True)
class ConfigureAgent(Record):
    command_id: str
    policy: AgentPolicy
    reason: str


@dataclass(frozen=True)
class PlanTurn(Record):
    command_id: str
    actor: Ref


@dataclass(frozen=True)
class GoalResult(Record):
    ref: Ref
    owner: Ref
    goal: Goal
    received: Ref | None
    account: Ref
    application: Ref
    retained: Ref


@dataclass(frozen=True)
class DeclareDyad(Record):
    command_id: str
    key: str
    left: Ref
    right: Ref
    item: Ref
    max_units: int = 2000


@dataclass(frozen=True)
class Dyad(Record):
    ref: Ref
    request: DeclareDyad
    at: Moment


@dataclass(frozen=True)
class OpenRound(Record):
    command_id: str
    study: Ref
    key: str


@dataclass(frozen=True)
class RoundStart(Record):
    ref: Ref
    study: Ref
    at: Moment
    owner: Ref
    cursor: int
    left_spent: int
    right_spent: int


@dataclass(frozen=True)
class CloseRound(Record):
    command_id: str
    start: Ref


@dataclass(frozen=True)
class RoundResult(Record):
    ref: Ref
    start: Ref
    study: Ref
    uses: tuple[Ref, ...]
    identity: EvidenceStatus
    path: EvidenceStatus
    meaning: EvidenceStatus
    units: int
    reason: str


@dataclass(frozen=True)
class AssessDyads(Record):
    command_id: str
    limit: int = 1


@dataclass(frozen=True)
class DyadReport(Record):
    ref: Ref
    study: Ref
    rounds: tuple[Ref, ...]
    phases: tuple[PhaseEvidence, ...]
    identity: EvidenceStatus
    path: EvidenceStatus
    meaning: EvidenceStatus
    closure: EvidenceStatus = EvidenceStatus.UNASSESSED


SocialCommand = AddGoal | ConfigureAgent | PlanTurn | ReceiveCommand | DeclareDyad | OpenRound | CloseRound | AssessDyads
SocialExtra = AgentState | Reception | ProcessingState | GoalResult | Dyad | RoundStart | RoundResult | DyadReport


@dataclass(frozen=True)
class SocionTransaction(Record):
    command: SocialCommand
    event: WorldEvent
    works: tuple[WorkRecord, ...] = ()
    observations: tuple[Observation, ...] = ()
    messages: tuple[Message, ...] = ()
    memories: tuple[MemoryRevision, ...] = ()
    task: Task | None = None
    extra: tuple[SocialExtra, ...] = ()


@dataclass(frozen=True)
class SocionCheckpoint(Record):
    schema: str
    config: WorldConfig
    profiles: tuple[Profile, ...]
    policy: ProcessingPolicy
    agents: tuple[AgentPolicy, ...]
    journal: tuple[Transaction | MemoryTransaction | MetabolicTransaction | AssessmentTransaction | SocionTransaction, ...]
