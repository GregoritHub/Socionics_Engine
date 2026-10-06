"""R15 finite release-learning hypotheses and exact material provenance.

No record contains a assignable Shell, clearance, diagnosis or altitude verdict.
"""
from dataclasses import dataclass
from .contracts import (Record, Ref, Kind, Observation, MemoryRevision, WorkRecord,
                        WorldEvent, WorkStatus)
from .world_records import Message, Task
from .metabolism_records import RoutePlan, ProcessingState
from .concept_records import ConceptState, ConceptCheckpoint, ConceptAddress
from .development_contracts import MaterialTreatment
from .crux import FormalMovement

RELEASE_RULE = Ref(Kind.RULE, 'r15.release_learning.v1', 1)
RELEASE_WORK = Ref(Kind.PROCEDURE, 'r15.release_processing.v1', 1)
DEPENDENCY = ('release', 'requires', 'external_confirmation')
REQUIRED = 'r15.review_required'
CONFIRMED = 'r15.confirmed'
QUOTE = 'r15.review_units'
WIRE = 'r15.release_packet.v1'


@dataclass(frozen=True)
class ReleaseConfig(Record):
    required_items: tuple[Ref, ...] = ()
    revision_unit: int = 6

    def __post_init__(self):
        super().__post_init__()
        if self.revision_unit < 0 or len(set(self.required_items)) != len(self.required_items):
            raise ValueError('invalid release domain or revision work law')
        if any(r.kind != Kind.ENTITY for r in self.required_items):
            raise ValueError('item references required')


@dataclass(frozen=True)
class ReviewPolicy(Record):
    owner: Ref
    may_review: bool = True
    review_units: int = 2

    def __post_init__(self):
        super().__post_init__()
        if self.owner.kind != Kind.ENTITY or self.review_units < 1:
            raise ValueError('invalid review policy')


@dataclass(frozen=True)
class CarrierOption(Record):
    actor: Ref
    evidence: tuple[Ref, ...]
    quoted_units: int


@dataclass(frozen=True)
class ReleaseView(Record):
    owner: Ref
    item: Ref
    loan: Ref
    terms: Ref
    required: bool
    clean: bool
    due: bool
    owned: bool
    concept: Ref | None
    dependency: bool
    supports: tuple[Ref, ...]
    carriers: tuple[CarrierOption, ...]
    refused: tuple[Ref, ...]
    prior_treatment: Ref | None


@dataclass(frozen=True)
class ReleaseSelection(Record):
    mode: str
    carrier: Ref | None
    extent: int
    alternatives: tuple[tuple[str, int], ...]
    reason: str


@dataclass(frozen=True)
class ReleaseDecision(Record):
    ref: Ref
    owner: Ref
    view: ReleaseView
    selection: ReleaseSelection
    material: Ref | None
    treatment: Ref | None


@dataclass(frozen=True)
class TensionMaterial(Record):
    ref: Ref
    owner: Ref
    reference: Ref
    address: ConceptAddress
    constraint: tuple[str, str, str]
    origin_event: Ref
    concept_at_origin: Ref
    evidence_at_origin: tuple[Ref, ...]


@dataclass(frozen=True)
class ReleasePacket(Record):
    kind: str
    item: Ref
    loan: Ref
    decision: Ref
    request: Ref | None = None
    approved: bool = False
    required: bool = False
    material: Ref | None = None
    reason: str = ''

    def __post_init__(self):
        super().__post_init__()
        if self.kind not in ('request', 'response') or self.item.kind != Kind.ENTITY or self.loan.kind != Kind.EVENT:
            raise ValueError('invalid release packet')
        if self.kind == 'response' and self.request is None:
            raise ValueError('a response must name its exact request')


@dataclass(frozen=True)
class ReleaseCommand(Record):
    command_id: str
    task_id: str
    actor: Ref
    operator: str
    item: Ref | None = None
    source: Ref | None = None
    willingness: bool | None = None
    work_limit: int = 64

    def __post_init__(self):
        super().__post_init__()
        if not self.command_id.strip() or not self.task_id.strip() or self.actor.kind != Kind.ENTITY or self.work_limit < 1:
            raise ValueError('invalid release command')
        if self.operator not in ('consider', 'enact', 'review', 'assimilate', 'boundary', 'announce'):
            raise ValueError('unknown release operator')
        if self.operator == 'consider' and (self.item is None or self.source is not None):
            raise ValueError('consider needs an item, never a supplied defense or answer')
        if self.operator in ('enact', 'review', 'assimilate') and self.source is None:
            raise ValueError('exact source required')
        if (self.operator == 'boundary') != (self.willingness is not None):
            raise ValueError('willingness belongs only to boundary declaration')


@dataclass(frozen=True)
class ReleaseJob(Record):
    command: ReleaseCommand
    plan: RoutePlan
    movements: tuple[FormalMovement, ...]
    view: ReleaseView | None
    selection: ReleaseSelection | None
    basis: tuple[Ref, ...]
    previous: Ref | None
    paid: int = 0
    outcome: WorkStatus = WorkStatus.PENDING


@dataclass(frozen=True)
class ReleaseTransaction(Record):
    command: ReleaseCommand
    event: WorldEvent
    works: tuple[WorkRecord, ...]
    observations: tuple[Observation, ...] = ()
    messages: tuple[Message, ...] = ()
    memories: tuple[MemoryRevision, ...] = ()
    task: Task | None = None
    job: ReleaseJob | None = None
    processing: ProcessingState | None = None
    material: TensionMaterial | None = None
    treatment: MaterialTreatment | None = None
    decision: ReleaseDecision | None = None
    concept: ConceptState | None = None


@dataclass(frozen=True)
class CompensationCheckpoint(Record):
    schema: str
    base: ConceptCheckpoint
    release: ReleaseConfig
    reviewers: tuple[ReviewPolicy, ...]
    journal: tuple
    reference_seal: str
    imported_prefix: int = 0
