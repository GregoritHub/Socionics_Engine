"""R16B paid release-account work. Participant records contain no Shell verdict."""
from dataclasses import dataclass
from .contracts import Record, Ref, Kind, WorldEvent, WorkRecord, WorkStatus, Observation, MemoryRevision
from .world_records import Message, Task
from .metabolism_records import RoutePlan, ProcessingState
from .compensation_records import ReleaseView, CompensationCheckpoint
from .concept_records import ConceptState
from .crux import FormalMovement

AUDIT_RULE = Ref(Kind.RULE, 'r16b.release_account.v1', 1)
AUDIT_WORK = Ref(Kind.PROCEDURE, 'r16b.reconciliation_work.v1', 1)
AUDIT_WIRE = 'r16b.account_packet.v1'

@dataclass(frozen=True)
class ReconciliationPolicy(Record):
    distinction_unit: int = 6
    scaffold_unit: int = 6
    guard_unit: int = 1
    cross_check: bool = False
    willing: bool = True
    def __post_init__(self):
        super().__post_init__()
        if min(self.distinction_unit, self.scaffold_unit, self.guard_unit) < 0:
            raise ValueError('nonnegative work coefficients required')

@dataclass(frozen=True)
class AccountPart(Record):
    ref: Ref
    lineage: Ref
    owner: Ref
    item: Ref
    loan: Ref
    role: str
    requires: bool
    basis: tuple[Ref, ...]

@dataclass(frozen=True)
class AccountPacket(Record):
    kind: str
    owner: Ref
    item: Ref
    loan: Ref
    requires: bool
    complete: bool
    first_notice: Ref | None = None
    obligations: int = 1

@dataclass(frozen=True)
class AccountState(Record):
    ref: Ref
    owner: Ref
    item: Ref
    loan: Ref
    terms: Ref
    concept: Ref
    lineage: Ref
    done: tuple[str, ...] = ()
    parts: tuple[Ref, ...] = ()
    notice: Ref | None = None
    reply: Ref | None = None
    complete: bool = False
    permission: bool | None = None
    closed: bool = False

@dataclass(frozen=True)
class AccountCommand(Record):
    command_id: str
    task_id: str
    actor: Ref
    item: Ref | None = None
    source: Ref | None = None
    work_limit: int = 64
    def __post_init__(self):
        super().__post_init__()
        if not self.command_id.strip() or not self.task_id.strip() or self.actor.kind != Kind.ENTITY or self.work_limit < 1:
            raise ValueError('invalid account command')
        if (self.item is None) == (self.source is None):
            raise ValueError('advance an item or answer an exact delivered notice')

@dataclass(frozen=True)
class AccountJob(Record):
    command: AccountCommand
    operation: str
    plan: RoutePlan
    movements: tuple[FormalMovement, ...]
    view: ReleaseView | None
    prior: Ref | None
    basis: tuple[Ref, ...]
    correction_quote: int
    paid: int = 0
    outcome: WorkStatus = WorkStatus.PENDING

@dataclass(frozen=True)
class AccountTransaction(Record):
    command: AccountCommand
    event: WorldEvent
    works: tuple[WorkRecord, ...]
    observations: tuple[Observation, ...] = ()
    messages: tuple[Message, ...] = ()
    memories: tuple[MemoryRevision, ...] = ()
    task: Task | None = None
    job: AccountJob | None = None
    processing: ProcessingState | None = None
    state: AccountState | None = None
    parts: tuple[AccountPart, ...] = ()
    concept: ConceptState | None = None

@dataclass(frozen=True)
class ReconciliationCheckpoint(Record):
    schema: str
    base: CompensationCheckpoint
    account_policy: ReconciliationPolicy
    seal: str
