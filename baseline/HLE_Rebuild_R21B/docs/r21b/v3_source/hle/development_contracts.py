"""R12 version-one developmental boundaries, not a developmental controller.

References share R11's event/memory/work address space. These immutable values
validate local shape and consistency only; R13 must resolve them against the
one runtime journal. They confer no capacity, Shell verdict, or altitude.
"""
from dataclasses import dataclass
from enum import Enum

from .contracts import (Record, Ref, Kind, Moment, TimeScope, WorkStatus,
                        EvidenceStatus, _kind, _text)
from .crux import FormalMovement, Perspective
from .model_a import stack, fields, element


@dataclass(frozen=True, kw_only=True)
class VersionOne(Record):
    schema_version: int = 1

    def __post_init__(self):
        super().__post_init__()
        if self.schema_version != 1:
            raise ValueError("unsupported developmental schema version")


def unique(values):
    if len(set(values)) != len(values):
        raise ValueError("duplicate values or evidence references")


def refs(values, *kinds, required=False):
    unique(values)
    if required and not values:
        raise ValueError("evidence references required")
    for value in values:
        _kind(value, *kinds)


class Origin(str, Enum):
    FIXTURE = "fixture"
    CONSEQUENCE = "consequence"
    PARTICIPANT = "participant"


class Comparison(str, Enum):
    EQUAL = "equal"
    GREATER = "greater"
    LESSER = "lesser"
    INCOMPARABLE = "incomparable"


class Treatment(str, Enum):
    HOLD = "hold"
    REVISE = "revise"
    RESTRICT_ACCESS = "restrict_access"
    EXTERNALIZE = "externalize"
    REOWN = "reown"


class Phase(str, Enum):
    UNASSESSED = "unassessed"
    RELEASE = "release"
    LEADERSHIP = "leadership"
    REVERSION = "reversion"
    REOWNERSHIP = "reownership"


class ShellSign(str, Enum):
    PREMATURE_TRANSLATION = "premature_translation"
    FORCED_PLACEMENT = "forced_placement"
    NEW_DEFENSIVE_STRUCTURE = "new_defensive_structure"
    RESIDUAL_FRAGMENTATION = "residual_fragmentation"
    FORECLOSURE = "foreclosure"


class CapacityStatus(str, Enum):
    CURRENT = "current"
    SUPERSEDED = "superseded"
    WITHDRAWN = "withdrawn"


@dataclass(frozen=True)
class StructuralFingerprint(VersionOne):
    tim: str
    model_a_stack: tuple[str, ...]
    dimensions: tuple[int, ...]

    def __post_init__(self):
        super().__post_init__()
        if self.model_a_stack != stack(self.tim):
            raise ValueError("TIM stack is fixed")
        if self.dimensions != tuple(fields(p)["dimensionality"] for p in range(1, 9)):
            raise ValueError("development cannot change Model A dimensionality")

    @classmethod
    def for_tim(cls, tim):
        return cls(tim, stack(tim), tuple(fields(p)["dimensionality"] for p in range(1, 9)))


@dataclass(frozen=True)
class ResourceEnvelope(VersionOne):
    energy: int
    time: int
    replenishment_rule: Ref | None

    def __post_init__(self):
        super().__post_init__()
        if min(self.energy, self.time) < 0:
            raise ValueError("negative resource envelope")
        if self.replenishment_rule is not None:
            _kind(self.replenishment_rule, Kind.RULE)


@dataclass(frozen=True)
class Requirement(VersionOne):
    """An ordered demand dimension elected in a versioned comparison protocol.

    Larger values impose more of the SAME requirement. Different dimensions
    or mixed increases/decreases do not imply a single difficulty ordering.
    """
    name: str
    magnitude: int

    def __post_init__(self):
        super().__post_init__(); _text(self.name)
        if self.magnitude < 0:
            raise ValueError("negative requirement magnitude")


@dataclass(frozen=True)
class DevelopmentalDemand(VersionOne):
    ref: Ref
    origin: Origin
    origin_events: tuple[Ref, ...]
    discovered_from: tuple[Ref, ...]
    family: str
    comparison_protocol: Ref
    required_outcomes: tuple[str, ...]
    movements: tuple[FormalMovement, ...]
    context: Ref
    participants: tuple[Ref, ...]
    material_lineage: tuple[Ref, ...]
    constraints: tuple[str, ...]
    duration: TimeScope
    resources: ResourceEnvelope
    requirements: tuple[Requirement, ...]
    prior_demand: Ref | None

    def __post_init__(self):
        super().__post_init__(); _kind(self.ref, Kind.DEMAND)
        _kind(self.context, Kind.CONTEXT); _kind(self.comparison_protocol, Kind.PROTOCOL)
        _text(self.family)
        refs(self.origin_events, Kind.EVENT, required=True)
        refs(self.discovered_from, Kind.OBSERVATION, Kind.MEMORY,
             required=self.origin != Origin.FIXTURE)
        refs(self.participants, Kind.ENTITY, required=True)
        refs(self.material_lineage, Kind.MEMORY, required=True)
        unique(self.required_outcomes); unique(self.constraints)
        unique(tuple(r.name for r in self.requirements))
        if not self.required_outcomes or not self.movements or not self.requirements:
            raise ValueError("demand must specify outcome, movement and requirement")
        for value in self.required_outcomes + self.constraints: _text(value)
        if self.prior_demand is not None:
            _kind(self.prior_demand, Kind.DEMAND)
            if self.prior_demand == self.ref:
                raise ValueError("demand cannot compare to itself")


@dataclass(frozen=True)
class DemandComparison(VersionOne):
    current: Ref
    prior: Ref
    relation: Comparison
    changes: tuple[tuple[str, int, int], ...]
    reason: str

    def __post_init__(self):
        super().__post_init__(); _kind(self.current, Kind.DEMAND); _kind(self.prior, Kind.DEMAND)
        _text(self.reason)
        unique(tuple(name for name, _, _ in self.changes))
        if any(min(before, after) < 0 or before == after for _, before, after in self.changes):
            raise ValueError("comparison changes must name real nonnegative changes")


def compare_demands(current, prior):
    """Conservative partial order; no implicit equivalence across contexts.

    A changed resource envelope, outcome, party, lineage, constraint, protocol,
    movement or duration length needs a different declared comparison. Merely
    shifting the start time does not change a finite duration's length.
    """
    if type(current) is not DevelopmentalDemand or type(prior) is not DevelopmentalDemand:
        raise ValueError("versioned demands required")
    def duration(d):
        s = d.duration
        return None if s.end is None else (s.end.tick - s.start.tick, s.end.order - s.start.order)
    same = ("family", "comparison_protocol", "required_outcomes", "movements",
            "context", "participants", "material_lineage", "constraints", "resources")
    a = {r.name: r.magnitude for r in current.requirements}
    b = {r.name: r.magnitude for r in prior.requirements}
    changes = tuple((k, b[k], a[k]) for k in sorted(a.keys() & b.keys()) if a[k] != b[k])
    if (any(getattr(current, k) != getattr(prior, k) for k in same)
            or duration(current) != duration(prior) or a.keys() != b.keys()):
        return DemandComparison(current.ref, prior.ref, Comparison.INCOMPARABLE,
                                changes, "comparison scope changed")
    delta = [a[k] - b[k] for k in a]
    relation = (Comparison.EQUAL if not any(delta) else
                Comparison.GREATER if all(d >= 0 for d in delta) else
                Comparison.LESSER if all(d <= 0 for d in delta) else Comparison.INCOMPARABLE)
    return DemandComparison(current.ref, prior.ref, relation, changes,
                            "componentwise elected requirement order")


@dataclass(frozen=True)
class Opportunity(VersionOne):
    ref: Ref
    actor: Ref
    demand: Ref
    at: Moment
    demand_active: bool
    observation_refs: tuple[Ref, ...]
    interpretation: Ref | None
    available_operator: Ref | None
    required_units: int
    resources: ResourceEnvelope
    blocking_constraints: tuple[str, ...]
    block_position: int
    queue_entered: Moment | None
    eligible_engagements: tuple[Ref, ...]

    def __post_init__(self):
        super().__post_init__(); _kind(self.ref, Kind.EVIDENCE)
        _kind(self.actor, Kind.ENTITY); _kind(self.demand, Kind.DEMAND)
        refs(self.observation_refs, Kind.OBSERVATION)
        refs(self.eligible_engagements, Kind.EVENT)
        if self.interpretation is not None:
            _kind(self.interpretation, Kind.MEMORY, Kind.OBSERVATION)
        if self.available_operator is not None:
            _kind(self.available_operator, Kind.PROCEDURE)
        if self.required_units < 1 or not 1 <= self.block_position <= 8:
            raise ValueError("invalid work requirement or block position")
        if self.queue_entered is not None and self.queue_entered > self.at:
            raise ValueError("queue cannot enter in the future")

    @property
    def eligible(self):
        """Necessary local conditions; eligibility is never a Shell verdict."""
        return (self.demand_active and bool(self.observation_refs)
                and self.interpretation is not None and self.available_operator is not None
                and not self.blocking_constraints
                and min(self.resources.energy, self.resources.time) >= self.required_units)


@dataclass(frozen=True)
class MaterialTreatment(VersionOne):
    ref: Ref
    lineage: Ref
    origin_actor: Ref
    source_events: tuple[Ref, ...]
    treating_actor: Ref
    treatment: Treatment
    carrier: Ref | None
    previous_revision: Ref | None
    selection_evidence: tuple[Ref, ...]
    work_refs: tuple[Ref, ...]
    consequences: tuple[Ref, ...]

    def __post_init__(self):
        super().__post_init__(); _kind(self.ref, Kind.MEMORY); _kind(self.lineage, Kind.MEMORY)
        _kind(self.origin_actor, Kind.ENTITY); _kind(self.treating_actor, Kind.ENTITY)
        refs(self.source_events, Kind.EVENT, required=True)
        refs(self.selection_evidence, Kind.MEMORY, Kind.OBSERVATION)
        refs(self.work_refs, Kind.WORK, required=True); refs(self.consequences, Kind.EVENT)
        if self.carrier is not None: _kind(self.carrier, Kind.ENTITY)
        if self.treatment == Treatment.EXTERNALIZE:
            if self.carrier is None or self.carrier == self.treating_actor or not self.selection_evidence:
                raise ValueError("externalization needs an external carrier and selection evidence")
        if self.treatment == Treatment.REOWN and self.carrier not in (None, self.treating_actor):
            raise ValueError("reownership cannot retain an external carrier")
        if self.previous_revision is not None:
            _kind(self.previous_revision, Kind.MEMORY)
            if self.previous_revision.key != self.ref.key or self.previous_revision.revision + 1 != self.ref.revision:
                raise ValueError("material revisions must continue the same identity")


def validate_material_transition(previous, current):
    """Check provenance once both exact historical revisions are resolved."""
    if type(previous) is not MaterialTreatment or type(current) is not MaterialTreatment:
        raise ValueError("resolved material revisions required")
    if (current.previous_revision != previous.ref or current.lineage != previous.lineage
            or current.origin_actor != previous.origin_actor
            or not set(previous.source_events) <= set(current.source_events)):
        raise ValueError("treatment cannot rewrite material origin or discard its provenance")


@dataclass(frozen=True)
class DevelopmentalWork(VersionOne):
    ref: Ref
    actor: Ref
    demand: Ref
    operator: Ref
    movement: FormalMovement
    inputs: tuple[Ref, ...]
    event_refs: tuple[Ref, ...]
    work_refs: tuple[Ref, ...]
    required_units: int
    paid_units: int
    status: WorkStatus
    outputs: tuple[Ref, ...]

    def __post_init__(self):
        super().__post_init__(); _kind(self.ref, Kind.WORK)
        _kind(self.actor, Kind.ENTITY); _kind(self.demand, Kind.DEMAND)
        _kind(self.operator, Kind.PROCEDURE)
        refs(self.inputs, Kind.MEMORY, Kind.OBSERVATION, required=True)
        refs(self.event_refs, Kind.EVENT); refs(self.work_refs, Kind.WORK)
        refs(self.outputs, Kind.MEMORY, Kind.OBSERVATION, Kind.PROCEDURE)
        if not 0 <= self.paid_units <= self.required_units or self.required_units < 1:
            raise ValueError("invalid cumulative paid work")
        if self.paid_units and (not self.event_refs or not self.work_refs):
            raise ValueError("paid work requires journal and debit references")
        if self.status == WorkStatus.COMPLETED:
            if self.paid_units != self.required_units or not self.outputs:
                raise ValueError("completed work requires full payment and publication")
        elif self.outputs:
            raise ValueError("unfinished work cannot publish usable results")
        if self.status in (WorkStatus.PENDING, WorkStatus.DEFERRED) and self.paid_units:
            raise ValueError("funded cumulative job must be partial or terminal")
        if self.status == WorkStatus.PARTIAL and not 0 < self.paid_units < self.required_units:
            raise ValueError("partial work requires a funded unfinished job")


@dataclass(frozen=True)
class RetainedCapacity(VersionOne):
    ref: Ref
    holder: Ref
    content_aspect: str
    operator: Ref
    binding: Ref
    context: Ref
    material_lineage: tuple[Ref, ...]
    acquisition_work: tuple[Ref, ...]
    practice_events: tuple[Ref, ...]
    dependencies: tuple[Ref, ...]
    status: CapacityStatus
    supersedes: Ref | None

    def __post_init__(self):
        super().__post_init__(); _kind(self.ref, Kind.MEMORY); _kind(self.holder, Kind.ENTITY)
        element(self.content_aspect); _kind(self.operator, Kind.PROCEDURE)
        _kind(self.binding, Kind.BINDING); _kind(self.context, Kind.CONTEXT)
        refs(self.material_lineage, Kind.MEMORY, required=True)
        refs(self.acquisition_work, Kind.WORK, required=True)
        refs(self.practice_events, Kind.EVENT)
        refs(self.dependencies, Kind.MEMORY, Kind.BINDING, Kind.PROCEDURE)
        if self.supersedes is not None:
            _kind(self.supersedes, Kind.MEMORY)
            if self.supersedes.key != self.ref.key or self.supersedes.revision + 1 != self.ref.revision:
                raise ValueError("capacity must supersede its exact preceding revision")


@dataclass(frozen=True)
class ShellEpisode(VersionOne):
    """References to assessment evidence. Construction never runs a detector."""
    ref: Ref
    actor: Ref
    material_lineage: tuple[Ref, ...]
    demands: tuple[Ref, ...]
    signs: tuple[ShellSign, ...]
    mechanism: Ref | None
    opportunities: tuple[Ref, ...]
    trajectory_events: tuple[Ref, ...]
    protocol: Ref
    status: EvidenceStatus
    capacity_revisions: tuple[Ref, ...]
    earlier_episode: Ref | None

    def __post_init__(self):
        super().__post_init__(); _kind(self.ref, Kind.ASSESSMENT); _kind(self.actor, Kind.ENTITY)
        _kind(self.protocol, Kind.PROTOCOL)
        refs(self.material_lineage, Kind.MEMORY, required=True)
        refs(self.demands, Kind.DEMAND, required=True)
        refs(self.opportunities, Kind.EVIDENCE); refs(self.trajectory_events, Kind.EVENT)
        refs(self.capacity_revisions, Kind.MEMORY); unique(self.signs)
        if self.mechanism is not None: _kind(self.mechanism, Kind.RULE, Kind.PROCEDURE)
        if self.earlier_episode is not None: _kind(self.earlier_episode, Kind.ASSESSMENT)
        if self.status == EvidenceStatus.ESTABLISHED:
            if not self.signs or self.mechanism is None or not self.opportunities or not self.trajectory_events:
                raise ValueError("a label cannot establish a Shell")


@dataclass(frozen=True)
class ClosureEvidence(VersionOne):
    ref: Ref
    organization: Ref
    lower_organizations: tuple[Ref, ...]
    demand: Ref
    repertoire: Ref
    repertoire_exhausted: bool
    search_censored: bool
    alternatives_evidence: tuple[Ref, ...]
    retained_lower_evidence: tuple[Ref, ...]
    new_capacity_evidence: tuple[Ref, ...]
    coherence_evidence: tuple[Ref, ...]
    minimality_order: Ref
    equal_minima: tuple[Ref, ...]
    status: EvidenceStatus

    def __post_init__(self):
        super().__post_init__(); _kind(self.ref, Kind.ASSESSMENT)
        _kind(self.organization, Kind.PROCEDURE); _kind(self.demand, Kind.DEMAND)
        _kind(self.repertoire, Kind.PROTOCOL); _kind(self.minimality_order, Kind.PROTOCOL)
        refs(self.lower_organizations, Kind.PROCEDURE, required=True)
        refs(self.equal_minima, Kind.PROCEDURE)
        for values in (self.alternatives_evidence, self.retained_lower_evidence,
                       self.new_capacity_evidence, self.coherence_evidence):
            refs(values, Kind.EVIDENCE, Kind.ASSESSMENT)
        if self.organization in self.lower_organizations:
            raise ValueError("closure cannot contain itself")
        if self.status == EvidenceStatus.ESTABLISHED:
            if (self.search_censored or not self.repertoire_exhausted or not self.alternatives_evidence
                    or not self.retained_lower_evidence or not self.new_capacity_evidence
                    or not self.coherence_evidence):
                raise ValueError("a wrapper or incomplete search cannot establish closure")


@dataclass(frozen=True)
class ResidualObservations(VersionOne):
    """Exact observations, deliberately NOT an elected scalar intensity law."""
    events: tuple[Ref, ...]
    queue_entered: Moment | None
    observed_at: Moment
    eligible_engagements: tuple[Ref, ...]
    canceled_work: tuple[Ref, ...]
    intensity_measurement: Ref | None = None

    def __post_init__(self):
        super().__post_init__(); refs(self.events, Kind.EVENT)
        refs(self.eligible_engagements, Kind.EVENT); refs(self.canceled_work, Kind.WORK)
        if self.queue_entered is not None and self.queue_entered > self.observed_at:
            raise ValueError("negative queue residence")
        if self.intensity_measurement is not None:
            raise ValueError("R12 elects no scalar residual-intensity measurement law")


@dataclass(frozen=True)
class DevelopmentalState(VersionOne):
    actor: Ref
    at: Moment
    gamma: StructuralFingerprint
    organization: Ref
    movement: FormalMovement
    content: tuple[Ref, ...]
    shell_episodes: tuple[Ref, ...]
    phase: Phase
    phase_evidence: tuple[Ref, ...]
    residual: ResidualObservations
    demands: tuple[Ref, ...]
    opportunities: tuple[Ref, ...]
    resources: ResourceEnvelope
    material_lineage: tuple[Ref, ...]
    capacities: tuple[Ref, ...]
    trajectory_events: tuple[Ref, ...]

    def __post_init__(self):
        super().__post_init__(); _kind(self.actor, Kind.ENTITY)
        _kind(self.organization, Kind.PROCEDURE)
        refs(self.content, Kind.MEMORY, Kind.OBSERVATION)
        refs(self.shell_episodes, Kind.ASSESSMENT); refs(self.phase_evidence, Kind.EVENT, Kind.WORK)
        refs(self.demands, Kind.DEMAND); refs(self.opportunities, Kind.EVIDENCE)
        refs(self.material_lineage, Kind.MEMORY); refs(self.capacities, Kind.MEMORY)
        refs(self.trajectory_events, Kind.EVENT)
        if self.phase != Phase.UNASSESSED and not self.phase_evidence:
            raise ValueError("phase names require work/event evidence")
        if self.residual.observed_at != self.at:
            raise ValueError("residual observation belongs to a different state time")
