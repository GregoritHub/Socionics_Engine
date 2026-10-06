"""R16A evidence values. These are evaluator inputs, never participant state.

Generic detector fixtures are explicitly marked. Runtime inputs are made only
by the journal adapter; constructing a trace does not certify a runtime event.
"""
from dataclasses import dataclass
from .contracts import Record, Ref, Kind, _kind
from .crux import FormalMovement, Perspective
from .model_a import TYPES

SIGNS = ('premature_translation', 'forced_placement', 'new_defensive_structure',
         'residual_fragmentation', 'foreclosure')
PROJECTION = Ref(Kind.PROTOCOL, 'r16a.loan_content_projection.v1', 1)
PROTOCOL = Ref(Kind.PROTOCOL, 'r16a.joint_assessment.v1', 1)


@dataclass(frozen=True)
class Claim(Record):
    subject: Ref
    relation: str
    value: str
    context: Ref
    occasion: Ref

    def __post_init__(self):
        super().__post_init__(); _kind(self.context, Kind.CONTEXT)
        if not self.relation.strip(): raise ValueError('claim relation required')

    @property
    def key(self):
        return self.subject, self.relation, self.context, self.occasion


@dataclass(frozen=True)
class LocalEvidence(Record):
    ref: Ref
    owner: Ref
    delivered: int
    interpreted: int | None
    interpretation: Ref | None
    claims: tuple[Claim, ...]

    def __post_init__(self):
        super().__post_init__(); _kind(self.ref, Kind.OBSERVATION, Kind.MEMORY)
        if self.delivered < 0 or (self.interpreted is None) != (self.interpretation is None):
            raise ValueError('interpretation needs both time and evidence')
        if self.interpreted is not None and self.interpreted < self.delivered:
            raise ValueError('interpretation cannot precede delivery')


@dataclass(frozen=True)
class ContentPart(Record):
    ref: Ref
    lineage: Ref
    created: int
    claims: tuple[Claim, ...]

    def __post_init__(self):
        super().__post_init__(); _kind(self.ref, Kind.MEMORY, Kind.OBSERVATION)
        _kind(self.lineage, Kind.MEMORY)
        if self.created < 0: raise ValueError('negative content time')


@dataclass(frozen=True)
class TraceOperation(Record):
    event: Ref
    tick: int
    name: str
    inputs: tuple[Ref, ...]
    outputs: tuple[Ref, ...]
    claims: tuple[Claim, ...]
    work: tuple[Ref, ...]
    units: int
    movements: tuple[FormalMovement, ...]
    domains: tuple[Perspective, ...]
    target: str = ''

    def __post_init__(self):
        super().__post_init__(); _kind(self.event, Kind.EVENT)
        if self.tick < 0 or self.units < 0 or not self.name or not self.domains:
            raise ValueError('invalid operation')
        if len(set(self.domains)) != len(self.domains): raise ValueError('duplicate domain')
        if self.units and not self.work: raise ValueError('paid operation needs work evidence')
        if any(r.kind != Kind.WORK for r in self.work): raise ValueError('work references required')


@dataclass(frozen=True)
class OpportunityEvidence(Record):
    demand: Ref | None
    necessary_operator: str
    available_operators: tuple[str, ...]
    capacity_evidence: tuple[Ref, ...]
    required_units: int | None
    energy: int
    time: int
    selected: bool
    refusal_evidence: tuple[Ref, ...]
    queue_entered: int
    current_movement: FormalMovement | None = None
    required_movement: FormalMovement | None = None
    engaged_at: int | None = None

    def __post_init__(self):
        super().__post_init__()
        if self.demand is not None: _kind(self.demand, Kind.DEMAND)
        if min(self.energy, self.time, self.queue_entered) < 0:
            raise ValueError('negative opportunity resource/time')
        if self.required_units is not None and self.required_units < 1:
            raise ValueError('positive work quote required')
        if self.engaged_at is not None and self.engaged_at < self.queue_entered:
            raise ValueError('engagement cannot precede queue entry')


@dataclass(frozen=True)
class DemandIncrease(Record):
    event: Ref
    tick: int
    before: tuple[tuple[str, int], ...]
    after: tuple[tuple[str, int], ...]
    before_scope: str
    after_scope: str

    def __post_init__(self):
        super().__post_init__(); _kind(self.event, Kind.EVENT)
        if self.tick < 0: raise ValueError('negative demand time')
        for rows in (self.before, self.after):
            if not rows or len(dict(rows)) != len(rows) or any(n < 0 for _, n in rows):
                raise ValueError('distinct nonnegative requirement dimensions required')

    @property
    def greater(self):
        a, b = dict(self.before), dict(self.after)
        return (self.before_scope == self.after_scope and a.keys() == b.keys()
                and all(b[k] >= a[k] for k in a) and any(b[k] > a[k] for k in a))


@dataclass(frozen=True)
class EngagementTrace(Record):
    engagement: Ref
    actor: Ref
    lineage: Ref
    context: Ref
    tim: str
    execution_kind: str
    start: int
    end: int
    opportunity: OpportunityEvidence
    evidence: tuple[LocalEvidence, ...]
    parts: tuple[ContentPart, ...]
    operations: tuple[TraceOperation, ...]
    measured: tuple[str, ...]
    prerequisites: tuple[str, ...] = ()
    initial_structures: tuple[Ref, ...] = ()
    increase: DemandIncrease | None = None
    closed: bool = True
    endpoint: str = 'unassessed'
    projection: Ref = PROJECTION
    protocol: Ref = PROTOCOL

    def __post_init__(self):
        super().__post_init__(); _kind(self.actor, Kind.ENTITY)
        _kind(self.lineage, Kind.MEMORY); _kind(self.context, Kind.CONTEXT)
        if self.projection != PROJECTION or self.protocol != PROTOCOL:
            raise ValueError('unsupported projection or assessment protocol')
        if self.tim not in TYPES or self.execution_kind not in ('fixture', 'runtime'):
            raise ValueError('declared type and evidence origin required')
        if self.start < 0 or self.end < self.start: raise ValueError('invalid window')
        if len(set(self.measured)) != len(self.measured) or any(s not in SIGNS for s in self.measured):
            raise ValueError('unknown or duplicate measurement channel')
        if self.opportunity.queue_entered > self.end: raise ValueError('future queue entry')
        if self.opportunity.engaged_at is not None and not self.start <= self.opportunity.engaged_at <= self.end:
            raise ValueError('engagement time must fall within the observed window')
        for e in self.evidence:
            if e.owner != self.actor or e.delivered > self.end:
                raise ValueError('foreign or future evidence')
            if e.interpreted is not None and e.interpreted > self.end:
                raise ValueError('future interpretation')
        parts = {p.ref: p for p in self.parts}
        if len(parts) != len(self.parts): raise ValueError('repeated part identity')
        if any(p.lineage != self.lineage for p in self.parts):
            raise ValueError('unrelated material cannot be pooled')
        events = set(); last = self.start
        for op in self.operations:
            if op.event in events or not last <= op.tick <= self.end:
                raise ValueError('duplicate or out-of-order operation')
            events.add(op.event); last = op.tick
            if any(r not in parts or parts[r].created > op.tick for r in op.inputs + op.outputs):
                raise ValueError('unresolved or future content part')
        if any(r not in parts or parts[r].created > self.start for r in self.initial_structures):
            raise ValueError('initial structure must exist at the window origin')

    @property
    def scope(self):
        return (self.actor, self.lineage, self.context, self.tim, self.execution_kind,
                self.projection, self.protocol)
