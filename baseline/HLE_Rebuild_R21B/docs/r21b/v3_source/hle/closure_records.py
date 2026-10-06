"""R20 finite shared obligation grammar. Records never award altitude by label."""
from dataclasses import dataclass
from .contracts import Record, Ref, Kind, WorkStatus, WorldEvent, WorkRecord, Observation, MemoryRevision
from .world_records import Message, Task
from .clearance_records import ClearanceCheckpoint

CLOSURE_RULE = Ref(Kind.RULE, 'r20.shared_obligations.v1', 1)
CLOSURE_WORK = Ref(Kind.PROCEDURE, 'r20.shared_obligations.v1', 1)
LOWER = ('native', 'repeat_native', 'sequential_transfer', 'relabel',
         'current_cycle', 'revise_cohort', 'drop_departed')

@dataclass(frozen=True)
class ClosureCommand(Record):
    command_id: str
    task_id: str
    actor: Ref
    operation: str
    inputs: tuple[Ref, ...] = ()
    label: str = ''
    work_limit: int = 256
    search_limit: int = 64
    def __post_init__(self):
        super().__post_init__()
        if not self.command_id or not self.task_id or self.work_limit < 1 or self.search_limit < 0:
            raise ValueError('identified paid work and nonnegative search limit required')
        if self.operation not in ('bind','open','renew','search','propose','review','activate','settle','learn'):
            raise ValueError('unknown closure operation')

@dataclass(frozen=True)
class NativeBinding(Record):
    ref: Ref
    owner: Ref
    root: Ref
    access: Ref
    material: Ref
    capacities: tuple[Ref, ...]
    production: Ref
    conditional_use: Ref
    returned: Ref

@dataclass(frozen=True)
class SharedDemand(Record):
    ref: Ref
    owner: Ref
    binding: Ref
    item: Ref
    members: tuple[Ref, ...]
    # Stable obligation identities survive a change of assignee or cohort.
    obligations: tuple[str, ...]
    parent: Ref | None = None
    previous_terms: str | None = None
    previous_generation: int = 0

@dataclass(frozen=True)
class SearchResult(Record):
    ref: Ref
    owner: Ref
    demand: Ref
    current: tuple[str, ...]
    rows: tuple[tuple[str, bool, str], ...]
    candidates: tuple[tuple[str, int, int], ...]
    equal_minima: tuple[str, ...]
    status: str
    required: str
    # Exact snapshot used in the finite test, not a claim about open grammars.
    unfinished: tuple[str, ...]
    departed: tuple[Ref, ...]

@dataclass(frozen=True)
class SharedPlan(Record):
    ref: Ref
    owner: Ref
    demand: Ref
    root: Ref
    access: Ref
    search: Ref
    operation: str
    identity: str
    generation: int
    terms_digest: str
    members: tuple[Ref, ...]
    assignments: tuple[tuple[str, Ref], ...]
    start: Ref
    state: Ref
    parent_root: Ref

@dataclass(frozen=True)
class SharedVote(Record):
    ref: Ref
    owner: Ref
    plan: Ref
    approved: bool
    reason: str
    state: Ref
    own_units: int
    limit: int

@dataclass(frozen=True)
class SharedActivation(Record):
    ref: Ref
    owner: Ref
    plan: Ref
    votes: tuple[Ref, ...]

@dataclass(frozen=True)
class ClosureResult(Record):
    ref: Ref
    owner: Ref
    plan: Ref
    activation: Ref
    duties: tuple[tuple[str, Ref, Ref], ...]
    root: Ref
    depth: int
    status: str
    predicates: tuple[tuple[str, bool], ...]
    dependencies: tuple[Ref, ...]
    current_states: tuple[Ref, ...]

@dataclass(frozen=True)
class ClosurePacket(Record):
    sender: Ref
    record: SharedPlan | SharedVote
    readable: tuple[Ref, ...] = ()

@dataclass(frozen=True)
class RootGrant(Record):
    ref: Ref
    owner: Ref
    source: Ref
    plan: Ref
    readable: tuple[Ref, ...]

@dataclass(frozen=True)
class ClosureJob(Record):
    command: ClosureCommand
    required: int
    candidate: NativeBinding | SharedDemand | SearchResult | SharedPlan | SharedVote | SharedActivation | ClosureResult | RootGrant
    basis: tuple[Ref, ...]
    paid: int = 0
    outcome: WorkStatus = WorkStatus.PENDING
    result: Ref | None = None

@dataclass(frozen=True)
class ClosureTransaction(Record):
    command: ClosureCommand
    event: WorldEvent
    works: tuple[WorkRecord, ...] = ()
    observations: tuple[Observation, ...] = ()
    messages: tuple[Message, ...] = ()
    memories: tuple[MemoryRevision, ...] = ()
    task: Task | None = None
    extra: tuple[NativeBinding | SharedDemand | SearchResult | SharedPlan | SharedVote | SharedActivation | ClosureResult | RootGrant, ...] = ()
    job: ClosureJob | None = None

@dataclass(frozen=True)
class ClosureCheckpoint(Record):
    schema: str
    base: ClearanceCheckpoint
    seal: str
