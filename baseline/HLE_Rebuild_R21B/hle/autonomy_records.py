"""R14 finite workshop and participant-selection contracts (engineering choices)."""
from dataclasses import dataclass
from .contracts import (Ref,Kind,Moment,Proposition,Observation,MemoryRevision,Record,
    WorkStatus,WorkRecord,WorldEvent,ResourceAmount)
from .development_contracts import VersionOne,DevelopmentalDemand
from .memory_records import MemoryCommand,RecallResult
from .socion_records import ReceiveCommand,AgentPolicy
from .world_records import Attempt,Transaction,WorldConfig,Message,Task
from .content_records import JournalEntry
from .metabolism_records import Profile,ProcessingPolicy,ProcessingState,RoutePlan
from .organization_records import OrganizationPolicy
from .semantic_records import SemanticPolicy

POLICY_RULE=Ref(Kind.RULE,'r14.local_selection',1)
DOMAIN_RULE=Ref(Kind.RULE,'r14.workshop_physics',1)
POLICY_WORK=Ref(Kind.PROCEDURE,'r14.consider',1)
DEMAND_PROTOCOL=Ref(Kind.PROTOCOL,'r14.generated_requirement.v1',1)
PACKET_REL='r14.workshop_packet.v1'
INTENT_REL='r14.standing_intention'
FACTS=('workshop_kind','role','owned_by','condition','loan_active','return_to','borrower','return_due','r14.skill')
PRIMITIVES=('inspect','use','clean','lend','return')

@dataclass(frozen=True)
class WorkshopConfig(VersionOne):
    conditions: tuple[tuple[Ref,str], ...] = ()
    wear_after_use: bool = True
    due_after_use: bool = True
    def __post_init__(self):
        super().__post_init__()
        if len({r for r,_ in self.conditions})!=len(self.conditions):raise ValueError('duplicate condition')
        if any(r.kind!=Kind.ENTITY or s not in ('clean','dirty','raw','ready') for r,s in self.conditions):raise ValueError('unsupported material condition')

@dataclass(frozen=True)
class AutonomyPolicy(VersionOne):
    owner: Ref
    intentions: tuple[str,...] = ('prepare_owned_workpieces','care_for_used_tools','honor_accepted_loans')
    primitives: tuple[str,...] = PRIMITIVES
    may_lend: bool = True
    may_ask: bool = True
    reserve: int = 0
    work_limit: int = 64
    def __post_init__(self):
        super().__post_init__()
        if self.owner.kind!=Kind.ENTITY or self.work_limit<1 or self.reserve<0:raise ValueError('invalid participant policy')
        if any(x not in ('prepare_owned_workpieces','care_for_used_tools','honor_accepted_loans') for x in self.intentions):raise ValueError('unknown standing intention')
        if len(set(self.primitives))!=len(self.primitives) or any(x not in PRIMITIVES for x in self.primitives):raise ValueError('invalid primitive repertoire')

@dataclass(frozen=True)
class WorkshopPacket(VersionOne):
    kind: str
    item: Ref
    topic: str = ''
    accept_return: bool = False
    explanation: tuple[Proposition,...] = ()
    def __post_init__(self):
        super().__post_init__()
        if self.kind not in ('loan_request','help','lesson','refusal') or self.item.kind!=Kind.ENTITY:raise ValueError('invalid workshop packet')
        if self.kind=='loan_request' and not self.accept_return:raise ValueError('loan request requires explicit return consent')
        if self.kind=='lesson' and (self.topic!='use' or not self.explanation):raise ValueError('finite supported lesson required')

@dataclass(frozen=True)
class WorkshopCommand(VersionOne):
    command_id: str
    task_id: str
    actor: Ref
    operation: str
    inputs: tuple[Ref,...]
    based_on: tuple[Ref,...] = ()
    request: Ref | None = None
    work_limit: int = 64
    def __post_init__(self):
        super().__post_init__()
        if not self.command_id.strip() or not self.task_id.strip() or self.actor.kind!=Kind.ENTITY or self.operation not in PRIMITIVES or self.work_limit<1:raise ValueError('invalid workshop command')
        if len(set(self.based_on))!=len(self.based_on):raise ValueError('duplicate basis')

Pending=WorkshopCommand | MemoryCommand | ReceiveCommand | Attempt

@dataclass(frozen=True)
class WorkshopJob(VersionOne):
    command: WorkshopCommand
    required: int
    paid: int=0
    outcome: WorkStatus=WorkStatus.PENDING
    def __post_init__(self):
        super().__post_init__()
        if not 0<=self.paid<=self.required:raise ValueError('invalid work progress')

@dataclass(frozen=True)
class MemoryPointer(VersionOne):
    key: str
    item: Ref
    memory: Ref
    binding: Ref | None = None

@dataclass(frozen=True)
class LocalRequest(VersionOne):
    observation: Ref
    sender: Ref
    packet: WorkshopPacket
    memory: Ref | None = None

@dataclass(frozen=True)
class ObservationPatch(VersionOne):
    key: str
    item: Ref
    content: tuple[Proposition,...]
    observation: Ref
    sender: Ref | None = None

@dataclass(frozen=True)
class DemandRecord(VersionOne):
    specification: DevelopmentalDemand
    owner: Ref
    item: Ref
    status: str
    reason: str
    def __post_init__(self):
        super().__post_init__()
        if self.status not in ('active','resolved','unresolved','waiting','refused','resource_limited'):raise ValueError('invalid demand status')

@dataclass(frozen=True)
class DemandSketch(VersionOne):
    family: str
    item: Ref
    material: tuple[Ref,...]
    observations: tuple[Ref,...]
    goal: str
    units: int
    priority: int

@dataclass(frozen=True)
class LocalDecision(VersionOne):
    kind: str
    reason: str
    demands: tuple[DemandSketch,...] = ()
    need_count: int = 0
    discrepancy_count: int = 0
    pressure_units: int = 0
    repeated_unsuccessful_attempts: int = 0

@dataclass(frozen=True)
class AutonomyState(VersionOne):
    ref: Ref
    owner: Ref
    cursor: int=0
    initialized: bool=False
    phase: str='observe'
    pending: Pending | None=None
    patches: tuple[ObservationPatch,...]=()
    catalog: tuple[MemoryPointer,...]=()
    requests: tuple[LocalRequest,...]=()
    active_notice: LocalRequest | None=None
    handled: tuple[Ref,...]=()
    asked: tuple[str,...]=()
    attempts: tuple[str,...]=()
    last_access: Ref | None=None
    dirty: bool=True
    decision: LocalDecision | None=None
    discrepancies: int=0
    failures: int=0
    failed_targets: tuple[str,...]=()
    def __post_init__(self):
        super().__post_init__()
        if self.cursor<0 or self.owner.kind!=Kind.ENTITY or self.ref.kind!=Kind.CURSOR:raise ValueError('invalid local state')

@dataclass(frozen=True)
class LocalView(VersionOne):
    state: AutonomyState
    policy: AutonomyPolicy
    now: Moment
    context: Ref
    observation: Observation | None
    sender: Ref | None
    packet: WorkshopPacket | None
    head: MemoryRevision | None
    binding: Ref | None
    pending_status: WorkStatus | None
    result: Ref | None
    memories: tuple[MemoryRevision,...]
    recall: RecallResult | None
    energy: int
    time: int
    # Only source addresses of this participant's own remembered observations.
    origins: tuple[tuple[Ref,Ref],...]=()
    access_valid: bool=True

@dataclass(frozen=True)
class AutonomyTurn(VersionOne):
    command_id: str
    task_id: str
    actor: Ref
    work_limit: int=64
    def __post_init__(self):
        super().__post_init__()
        if not self.command_id.strip() or not self.task_id.strip() or self.work_limit<1 or self.actor.kind!=Kind.ENTITY:raise ValueError('invalid turn')

@dataclass(frozen=True)
class ViewSnapshot(VersionOne):
    """Exact addresses into the shared journal, not another copy of memory."""
    state: Ref
    now: Moment
    observation: Ref | None
    head: Ref | None
    binding: Ref | None
    pending_status: WorkStatus | None
    result: Ref | None
    memories: tuple[tuple[Ref,tuple[int,...]],...]
    recall: Ref | None
    energy: int
    time: int
    access_valid: bool=True


@dataclass(frozen=True)
class AutonomyJob(VersionOne):
    command: AutonomyTurn
    snapshot: ViewSnapshot
    plan: RoutePlan
    paid: int=0
    outcome: WorkStatus=WorkStatus.PENDING
    def __post_init__(self):
        super().__post_init__()
        if not 0<=self.paid<=self.plan.required:raise ValueError('invalid decision progress')

@dataclass(frozen=True)
class AutonomousTransaction(VersionOne):
    command: WorkshopCommand | AutonomyTurn
    event: WorldEvent
    works: tuple[WorkRecord,...]=()
    observations: tuple[Observation,...]=()
    messages: tuple[Message,...]=()
    memories: tuple[MemoryRevision,...]=()
    task: Task | None=None
    workshop_job: WorkshopJob | None=None
    decision_job: AutonomyJob | None=None
    participant: AutonomyState | None=None
    processing: ProcessingState | None=None
    demands: tuple[DemandRecord,...]=()

@dataclass(frozen=True)
class AutonomousCheckpoint(VersionOne):
    schema: str
    config: WorldConfig
    profiles: tuple[Profile,...]
    policy: ProcessingPolicy
    agents: tuple[AgentPolicy,...]
    organization_policies: tuple[OrganizationPolicy,...]
    semantic_policy: SemanticPolicy
    workshop: WorkshopConfig
    autonomy: tuple[AutonomyPolicy,...]
    journal: tuple[JournalEntry | AutonomousTransaction,...]
