"""R18 exact finite work-order, owned learning and shared consequence records."""
from dataclasses import dataclass
from .contracts import (Record, Ref, Kind, WorldEvent, WorkRecord, WorkStatus,
    Observation, MemoryRevision)
from .world_records import Message, Task
from .metabolism_records import RoutePlan, ProcessingState
from .crux import FormalMovement
from .conversion_records import ConversionCheckpoint

CIRCUIT_RULE = Ref(Kind.RULE, 'r18.circuits.v1', 1)
CIRCUIT_WORK = Ref(Kind.PROCEDURE, 'r18.circuits.v1', 1)
ASPECTS = ('ne','si','ni','se','te','ti','fi','fe')

@dataclass(frozen=True)
class WorkOption(Record):
    key: str
    available: bool = True
    condition: str = 'clean'
    observed_epoch: int = 0
    start: int = 2
    ready_at: int = 1
    duration: int = 1
    load: int = 1
    output: int = 4
    cost: int = 1
    claims: tuple[tuple[str,str], ...] = (('station','one'),)
    license: str = 'standard'
    def __post_init__(self):
        super().__post_init__()
        if not self.key or self.condition not in ('clean','dirty') or any(x < 0 for x in
            (self.observed_epoch,self.start,self.ready_at,self.duration,self.load,self.output,self.cost)):
            raise ValueError('invalid work option')
        if self.duration < 1 or self.load < 1 or self.cost < 1: raise ValueError('positive work extent required')

@dataclass(frozen=True)
class CircuitOffer(Record):
    command_id: str
    key: str
    learner: Ref
    partner: Ref
    helper: Ref
    options: tuple[WorkOption,...]
    focus: str
    circuit: int = 0
    epoch: int = 0
    due: int = 6
    budget: int = 3
    credits: int = 3
    minimum_output: int = 3
    def __post_init__(self):
        super().__post_init__()
        if (not self.command_id or not self.key or not self.options or len({x.key for x in self.options})!=len(self.options)
            or self.focus not in ASPECTS or self.circuit not in (0,1) or min(self.epoch,self.due,self.budget,self.credits,self.minimum_output)<0):
            raise ValueError('invalid circuit offer')
        if len({self.learner,self.partner,self.helper})!=3: raise ValueError('distinct participants required')

@dataclass(frozen=True)
class CircuitPolicy(Record):
    correction: str = 'self'
    retention: bool = True
    material_access: bool = True
    def __post_init__(self):
        super().__post_init__()
        if self.correction not in ('self','dual','nondual'): raise ValueError('unknown correction channel')

@dataclass(frozen=True)
class WorkPartner(Record):
    actor: Ref
    licenses: tuple[str,...] = ('standard',)
    unavailable_slots: tuple[int,...] = (9,)
    willing: bool = True
    max_load: int = 3
    helper_available: bool = True

@dataclass(frozen=True)
class CircuitCommand(Record):
    command_id: str
    task_id: str
    actor: Ref
    order: str
    operator: str
    work_limit: int = 256
    aspect: str = ''
    flag: bool = True
    def __post_init__(self):
        super().__post_init__()
        if not self.command_id or not self.task_id or self.work_limit<1 or self.actor.kind!=Kind.ENTITY:
            raise ValueError('invalid circuit command')
        if self.operator not in ('menu','refresh','choose','review','coordinate','organize','apply','inspect','consult','feedback','withdraw','support','boundary'):
            raise ValueError('unknown circuit operation')
        if (self.operator=='withdraw') != (self.aspect in ASPECTS):
            raise ValueError('only withdrawal supplies an aspect')

@dataclass(frozen=True)
class CircuitMessage(Record):
    ref: Ref
    sender: Ref
    recipient: Ref
    order: str
    permissions: tuple[tuple[str,bool],...] = ()
    acknowledgments: tuple[tuple[str,bool],...] = ()
    accepted: bool = False
    source: Ref | None = None

@dataclass(frozen=True)
class CircuitSignal(Record):
    ref: Ref
    observer: Ref
    source: Ref
    order: str
    option: str
    success: bool
    errors: tuple[str,...]
    produced: int
    performer: Ref

@dataclass(frozen=True)
class AspectCapacity(Record):
    ref: Ref
    owner: Ref
    aspect: str
    material: Ref
    failure: Ref
    practice: Ref
    acquisition: tuple[Ref,...]
    dependencies: tuple[Ref,...] = ()
    current: bool = True
    previous: Ref | None = None

@dataclass(frozen=True)
class CircuitAccount(Record):
    ref: Ref
    owner: Ref
    material: Ref
    capacities: tuple[Ref,...]
    # Self-description is derived from retained own practice, never a verdict.
    self_performed: tuple[Ref,...]
    revised_expectations: tuple[Ref,...]
    previous: Ref | None = None

@dataclass(frozen=True)
class CircuitOrder(Record):
    ref: Ref
    offer: CircuitOffer
    bulletin: Ref
    menu: Ref | None = None
    chosen: str | None = None
    stage: int = 0
    uses: tuple[Ref,...] = ()
    provisional: tuple[str,...] = ()
    review: Ref | None = None
    outcome: Ref | None = None
    signal: Ref | None = None
    performer: Ref | None = None
    credited: bool = False
    closed: bool = False
    movements: tuple[FormalMovement,...] = ()
    phase_work: tuple[Ref,...] = ()

@dataclass(frozen=True)
class CircuitJob(Record):
    command: CircuitCommand
    plan: RoutePlan
    basis: tuple[Ref,...]
    version: Ref | None
    signature: tuple[Ref,...]
    paid: int = 0
    outcome: WorkStatus = WorkStatus.PENDING

@dataclass(frozen=True)
class CircuitTransaction(Record):
    command: CircuitCommand | CircuitOffer
    event: WorldEvent
    works: tuple[WorkRecord,...]
    observations: tuple[Observation,...] = ()
    messages: tuple[Message,...] = ()
    memories: tuple[MemoryRevision,...] = ()
    task: Task | None = None
    job: CircuitJob | None = None
    processing: ProcessingState | None = None
    order: CircuitOrder | None = None
    communication: CircuitMessage | None = None
    signal: CircuitSignal | None = None
    capacities: tuple[AspectCapacity,...] = ()
    account: CircuitAccount | None = None
    partner: WorkPartner | None = None
    tentative: tuple[tuple[str,Ref],...] | None = None

@dataclass(frozen=True)
class CircuitCheckpoint(Record):
    schema: str
    base: ConversionCheckpoint
    policy: CircuitPolicy
    partners: tuple[WorkPartner,...]
    seal: str
