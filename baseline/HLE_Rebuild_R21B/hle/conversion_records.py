"""R17 owned material, provisional organization, paid practice and retained use.

No phase or developmental verdict is a participant input. These records retain
references to particulars; they do not move dates or item facts into Fool's Memory.
"""
from dataclasses import dataclass
from .contracts import Record, Ref, Kind, WorldEvent, WorkRecord, WorkStatus, Observation, MemoryRevision
from .world_records import Message, Task
from .metabolism_records import RoutePlan, ProcessingState
from .compensation_records import ReleaseView
from .concept_records import ConceptState
from .development_contracts import MaterialTreatment
from .reconciliation_records import ReconciliationCheckpoint
from .crux import FormalMovement

CONVERSION_RULE = Ref(Kind.RULE, 'r17.conversion.v1', 1)
CONVERSION_WORK = Ref(Kind.PROCEDURE, 'r17.conversion_work.v1', 1)
SCOPED = ('confirmation', 'depends_on', 'current_accepted_terms')

@dataclass(frozen=True)
class ConversionPolicy(Record):
    material_access: bool = True
    practice: bool = True
    retention: bool = True

@dataclass(frozen=True)
class ConversionCommand(Record):
    command_id: str
    task_id: str
    actor: Ref
    operator: str = 'advance'
    item: Ref | None = None
    work_limit: int = 64
    def __post_init__(self):
        super().__post_init__()
        if not self.command_id.strip() or not self.task_id.strip() or self.actor.kind != Kind.ENTITY or self.work_limit < 1:
            raise ValueError('invalid conversion command')
        if self.operator not in ('release', 'advance', 'recall', 'restrict', 'restore_access', 'withdraw', 'pause', 'resume'):
            raise ValueError('unknown conversion operation')
        if (self.operator == 'recall') != (self.item is not None):
            raise ValueError('only recall names an item; practice follows an owned pending action')

@dataclass(frozen=True)
class ConversionStudy(Record):
    ref: Ref
    owner: Ref
    material: Ref
    concept_origin: Ref
    account_material: Ref
    context_sources: tuple[Ref, ...] = ()
    candidate: Ref | None = None
    active: bool = True
    paused: bool = False

@dataclass(frozen=True)
class ScopeCandidate(Record):
    ref: Ref
    owner: Ref
    material: Ref
    context: Ref
    # An executable finite hypothesis selected from local evidence, not a name.
    table: tuple[tuple[bool, bool], ...]
    sources: tuple[Ref, ...]
    practice: tuple[Ref, ...] = ()
    failures: tuple[Ref, ...] = ()
    covered: tuple[bool, ...] = ()
    previous: Ref | None = None
    preconditions: tuple[str, ...] = ()

@dataclass(frozen=True)
class ConversionUse(Record):
    ref: Ref
    owner: Ref
    material: Ref
    rule: Ref
    capacity: Ref | None
    item: Ref
    loan: Ref
    terms: Ref
    required: bool
    event: Ref

@dataclass(frozen=True)
class ConversionCapacity(Record):
    ref: Ref
    owner: Ref
    material: Ref
    rule: Ref
    acquisition: tuple[Ref, ...]
    practice: tuple[Ref, ...]
    current: bool = True
    previous: Ref | None = None

@dataclass(frozen=True)
class ConversionJob(Record):
    command: ConversionCommand
    operation: str
    plan: RoutePlan
    movements: tuple[FormalMovement, ...]
    basis: tuple[Ref, ...]
    study: Ref | None
    capacity: Ref | None
    accessible: bool
    view: ReleaseView | None = None
    result: Ref | None = None
    paid: int = 0
    outcome: WorkStatus = WorkStatus.PENDING

@dataclass(frozen=True)
class ConversionTransaction(Record):
    command: ConversionCommand
    event: WorldEvent
    works: tuple[WorkRecord, ...]
    observations: tuple[Observation, ...] = ()
    messages: tuple[Message, ...] = ()
    memories: tuple[MemoryRevision, ...] = ()
    task: Task | None = None
    job: ConversionJob | None = None
    processing: ProcessingState | None = None
    study: ConversionStudy | None = None
    candidate: ScopeCandidate | None = None
    capacity: ConversionCapacity | None = None
    use: ConversionUse | None = None
    treatment: MaterialTreatment | None = None
    concept: ConceptState | None = None

@dataclass(frozen=True)
class ConversionCheckpoint(Record):
    schema: str
    base: ReconciliationCheckpoint
    policy: ConversionPolicy
    seal: str
