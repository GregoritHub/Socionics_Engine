"""R19 environmental opportunities and evaluator boundaries; no verdict inputs."""
from dataclasses import dataclass
from .contracts import Record, Ref, Kind, WorldEvent, WorkRecord, Observation, MemoryRevision
from .world_records import Message, Task
from .individuation_records import CircuitCheckpoint

FAMILIES = ('selection', 'temporal', 'obligations')
VARIATIONS = ('equal_renewal', 'increased_requirement', 'changed_context_partner', 'delay_or_changed_testimony')
CASES = ('original',) + tuple(f+'.'+v for f in FAMILIES for v in VARIATIONS)
R19_DUE = Ref(Kind.RULE,'r19.due',1)

@dataclass(frozen=True)
class EpisodeResourceContract(Record):
    """An external, journaled contract selection before episode work begins."""
    command_id: str
    episode_id: str
    regime: str
    seed: int
    protocol_id: str
    protocol_sha256: str

    def __post_init__(self):
        super().__post_init__()
        if (not self.command_id or not self.episode_id or type(self.seed) is not int
                or not self.regime or not self.protocol_id
                or len(self.protocol_sha256) != 64
                or any(c not in '0123456789abcdef' for c in self.protocol_sha256)):
            raise ValueError('explicit versioned episode contract required')

@dataclass(frozen=True)
class ClearanceBoundary(Record):
    command_id: str
    actor: Ref
    operation: str
    case: str = ''
    orders: tuple[str, ...] = ()
    item: Ref | None = None
    def __post_init__(self):
        super().__post_init__()
        if not self.command_id or self.operation not in ('begin','open','close'):
            raise ValueError('invalid evaluation boundary')
        if self.operation == 'open':
            if self.case not in CASES or self.item is None or len(set(self.orders)) != len(self.orders):
                raise ValueError('declared case, unique orders and physical item required')
            if (self.case == 'original') != (not self.orders):
                raise ValueError('held-out cases require work orders; original is the original loan demand')
        elif self.case or self.orders or self.item is not None:
            raise ValueError('only opening supplies case scope')

@dataclass(frozen=True)
class LoanDue(Record):
    command_id: str
    item: Ref
    loan: Ref

@dataclass(frozen=True)
class PartnerShift(Record):
    command_id: str
    actor: Ref
    unavailable_slots: tuple[int, ...]
    def __post_init__(self):
        super().__post_init__()
        if not self.command_id or len(set(self.unavailable_slots)) != len(self.unavailable_slots) or any(n < 0 for n in self.unavailable_slots):
            raise ValueError('invalid external schedule change')

@dataclass(frozen=True)
class WithdrawEvidence(Record):
    command_id: str
    source: Ref
    reason: str
    def __post_init__(self):
        super().__post_init__()
        if not self.command_id or not self.reason.strip(): raise ValueError('explicit withdrawal reason required')

@dataclass(frozen=True)
class OrderDependency(Record):
    command_id: str
    predecessor: str
    successor: str
    def __post_init__(self):
        super().__post_init__()
        if not self.command_id or not self.predecessor or not self.successor or self.predecessor == self.successor:
            raise ValueError('distinct dependency endpoints required')

@dataclass(frozen=True)
class ClearanceTransaction(Record):
    command: ClearanceBoundary | LoanDue | PartnerShift | WithdrawEvidence | OrderDependency | EpisodeResourceContract
    event: WorldEvent
    works: tuple[WorkRecord, ...] = ()
    observations: tuple[Observation, ...] = ()
    messages: tuple[Message, ...] = ()
    memories: tuple[MemoryRevision, ...] = ()
    task: Task | None = None

@dataclass(frozen=True)
class ClearanceCheckpoint(Record):
    schema: str
    base: CircuitCheckpoint
    seal: str
