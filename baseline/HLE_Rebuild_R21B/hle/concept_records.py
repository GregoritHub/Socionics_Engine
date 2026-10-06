"""R14.5 immutable conceptual records; particulars remain referenced evidence."""
from dataclasses import dataclass
from .contracts import Record, Ref, Kind, WorkStatus, WorkRecord, WorldEvent, Observation, MemoryRevision
from .metabolism_records import ProcessingState, RoutePlan
from .world_records import Message, Task
from .crux import FormalMovement
from .autonomy_records import AutonomousCheckpoint, AutonomousTransaction
from .content_records import JournalEntry

CONCEPT_RULE = Ref(Kind.RULE, 'r145.conceptual_integration.v1', 1)
CONCEPT_WORK = Ref(Kind.PROCEDURE, 'r145.conceptual_work.v1', 1)
ENTRUSTED = Ref(Kind.IDENTITY, 'concept:entrusted_use', 1)

@dataclass(frozen=True)
class ConceptAddress(Record):
    folded_position: int
    file: str
    depth: int
    apex: Ref
    cue: Ref
    def __post_init__(self):
        super().__post_init__()
        if not 1 <= self.folded_position <= 9 or self.depth < 0 or self.apex.kind != Kind.CONTEXT or self.cue.kind != Kind.CUE:
            raise ValueError('invalid conceptual address')

@dataclass(frozen=True)
class ConceptState(Record):
    ref: Ref
    owner: Ref
    reference: Ref
    context: Ref
    address: ConceptAddress
    relations: tuple[tuple[str,str,str], ...]
    tensions: tuple[str, ...]
    evidence: tuple[Ref, ...]  # delta only; prior preserves the historical chain
    previous: Ref | None
    practiced: bool = False

@dataclass(frozen=True)
class ConceptCommand(Record):
    command_id: str
    task_id: str
    actor: Ref
    operator: str
    sources: tuple[Ref, ...] = ()
    recipient: Ref | None = None
    item: Ref | None = None
    work_limit: int = 64
    def __post_init__(self):
        super().__post_init__()
        if not self.command_id.strip() or not self.task_id.strip() or self.actor.kind != Kind.ENTITY or self.work_limit < 1:
            raise ValueError('invalid conceptual command')
        if self.operator not in ('integrate','teach','supply','revoke') or len(set(self.sources)) != len(self.sources):
            raise ValueError('invalid conceptual operator or duplicate source')
        if self.operator in ('teach','supply') and (self.recipient is None or self.recipient == self.actor):
            raise ValueError('a distinct recipient is required')
        if self.operator == 'supply' and self.item is None: raise ValueError('supply is scoped to one item')

@dataclass(frozen=True)
class ConceptJob(Record):
    command: ConceptCommand
    plan: RoutePlan
    previous: Ref | None
    movements: tuple[FormalMovement, ...]
    paid: int = 0
    outcome: WorkStatus = WorkStatus.PENDING

@dataclass(frozen=True)
class ConceptTransaction(Record):
    command: ConceptCommand
    event: WorldEvent
    works: tuple[WorkRecord, ...]
    observations: tuple[Observation, ...] = ()
    messages: tuple[Message, ...] = ()
    memories: tuple[MemoryRevision, ...] = ()
    task: Task | None = None
    job: ConceptJob | None = None
    processing: ProcessingState | None = None
    concept: ConceptState | None = None

@dataclass(frozen=True)
class ConceptCheckpoint(Record):
    schema: str
    base: AutonomousCheckpoint
    journal: tuple[JournalEntry | AutonomousTransaction | ConceptTransaction, ...]
    migration_prefix: int = 0
    reference_seal: str = ''
