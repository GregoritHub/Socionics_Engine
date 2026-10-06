"""Immutable, versioned boundary values for R2--R5 (E02--E09).

Validation here is local shape/consistency validation, not referential integrity,
authorization, inference, accounting execution, memory retrieval, or assessment.
Every reference includes a revision; historical meaning must resolve that revision.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
from enum import Enum
from functools import lru_cache
from types import UnionType
from typing import get_args, get_origin, get_type_hints

from .crux import FormalMovement, Perspective


@lru_cache(maxsize=None)
def _hints(cls):
    return get_type_hints(cls)


def _typed(value, hint) -> bool:
    origin, args = get_origin(hint), get_args(hint)
    if origin is UnionType:
        return any(_typed(value, part) for part in args)
    if origin is tuple:
        return type(value) is tuple and (all(_typed(v, args[0]) for v in value)
            if len(args) == 2 and args[1] is Ellipsis
            else len(value) == len(args) and all(_typed(v, h) for v, h in zip(value, args)))
    return type(value) is hint


class Record:
    def __post_init__(self):
        for field in fields(self):
            if not _typed(getattr(self, field.name), _hints(type(self))[field.name]):
                raise ValueError(f"{type(self).__name__}.{field.name}: wrong type or mutable value")


def _text(value: str):
    if not value.strip():
        raise ValueError("required text cannot be blank")


class Kind(str, Enum):
    ENTITY = "entity"
    CONTEXT = "context"
    EVENT = "event"
    MESSAGE = "message"
    OBSERVATION = "observation"
    MEMORY = "memory"
    CUE = "cue"
    BINDING = "binding"
    CURSOR = "cursor"
    PROCEDURE = "procedure"
    DEMAND = "demand"
    MOVEMENT = "movement"
    WORK = "work"
    RULE = "rule"
    IDENTITY = "identity"
    PROTOCOL = "protocol"
    ASSESSMENT = "assessment"
    EVIDENCE = "evidence"


@dataclass(frozen=True)
class Ref(Record):
    kind: Kind
    key: str
    revision: int

    def __post_init__(self):
        super().__post_init__(); _text(self.key)
        if self.revision < 1:
            raise ValueError("revision must be positive")


def _kind(ref: Ref, *kinds: Kind):
    if ref.kind not in kinds:
        raise ValueError(f"wrong reference kind {ref.kind}: expected {kinds}")


@dataclass(frozen=True, order=True)
class Moment(Record):
    tick: int
    order: int

    def __post_init__(self):
        super().__post_init__()
        if self.tick < 0 or self.order < 0:
            raise ValueError("logical time must be nonnegative")


@dataclass(frozen=True)
class TimeScope(Record):
    """Half-open [start,end); end=None declares an open-ended claim scope."""
    start: Moment
    end: Moment | None

    def __post_init__(self):
        super().__post_init__()
        if self.end is not None and self.end <= self.start:
            raise ValueError("time scope must have positive extent")


Atom = Ref | str | int | bool


@dataclass(frozen=True)
class Proposition(Record):
    """Shared vocabulary for world facts and beliefs; contains no truth verdict."""
    subject: Ref
    relation: str
    object: Atom
    context: Ref
    scope: TimeScope

    def __post_init__(self):
        super().__post_init__(); _text(self.relation); _kind(self.context, Kind.CONTEXT)


@dataclass(frozen=True)
class Change(Record):
    before: Proposition | None
    after: Proposition | None

    def __post_init__(self):
        super().__post_init__()
        if self.before is None and self.after is None:
            raise ValueError("change needs a before or after proposition")


@dataclass(frozen=True)
class Cause(Record):
    event: Ref
    rule: Ref

    def __post_init__(self):
        super().__post_init__(); _kind(self.event, Kind.EVENT); _kind(self.rule, Kind.RULE)


class WorkStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    PARTIAL = "partial"
    DEFERRED = "deferred"
    FAILED = "failed"


@dataclass(frozen=True)
class WorldEvent(Record):
    ref: Ref
    when: Moment
    actors: tuple[Ref, ...]
    objects: tuple[Ref, ...]
    action: str
    context: Ref
    changes: tuple[Change, ...]
    causes: tuple[Cause, ...]
    work: tuple[Ref, ...]
    outcome: WorkStatus
    reason: str
    corrects: Ref | None = None

    def __post_init__(self):
        super().__post_init__(); _kind(self.ref, Kind.EVENT); _kind(self.context, Kind.CONTEXT)
        _text(self.action); _text(self.reason)
        for ref in self.actors + self.objects: _kind(ref, Kind.ENTITY)
        for ref in self.work: _kind(ref, Kind.WORK)
        if self.corrects is not None: _kind(self.corrects, Kind.EVENT)
        if any(c.event == self.ref for c in self.causes) or self.corrects == self.ref:
            raise ValueError("an event cannot cause or correct itself")


@dataclass(frozen=True)
class Observation(Record):
    ref: Ref
    observer: Ref
    source: Ref
    source_time: Moment
    delivered_at: Moment
    content: tuple[Proposition, ...]
    channel_rule: Ref
    visibility: str
    uncertainty: str

    def __post_init__(self):
        super().__post_init__(); _kind(self.ref, Kind.OBSERVATION)
        _kind(self.observer, Kind.ENTITY); _kind(self.source, Kind.EVENT, Kind.MESSAGE)
        _kind(self.channel_rule, Kind.RULE); _text(self.visibility); _text(self.uncertainty)
        if self.delivered_at < self.source_time:
            raise ValueError("delivery cannot precede source time")


class ClaimStatus(str, Enum):
    TENTATIVE = "tentative"
    ENDORSED = "endorsed"
    DISPUTED = "disputed"
    RETRACTED = "retracted"
    # These are the holder's attitudes, never evaluator truth values.


@dataclass(frozen=True)
class MemoryRevision(Record):
    ref: Ref
    owner: Ref
    retained_at: Moment
    content: tuple[Proposition, ...]
    links: tuple[Ref, ...]
    observations: tuple[Ref, ...]
    derived_from: tuple[Ref, ...]
    claim_status: ClaimStatus
    capabilities: tuple[Ref, ...]
    replaces: Ref | None
    reason: str

    def __post_init__(self):
        super().__post_init__(); _kind(self.ref, Kind.MEMORY); _kind(self.owner, Kind.ENTITY)
        _text(self.reason)
        for ref in self.observations: _kind(ref, Kind.OBSERVATION)
        for ref in self.capabilities: _kind(ref, Kind.PROCEDURE)
        if self.ref.revision == 1:
            if self.replaces is not None: raise ValueError("first revision cannot replace a revision")
        elif self.replaces != Ref(Kind.MEMORY, self.ref.key, self.ref.revision - 1):
            raise ValueError("memory revisions must reference the previous version")


@dataclass(frozen=True)
class CueDescriptor(Record):
    """Cue/card identity, rank and location are distinct; no content lives here.

    Deck-specific card catalog validation is R3. A generic cue may have no rank
    or fold. The Fool is permitted as a cue, with no numbered folded location.
    """
    ref: Ref
    symbol: str
    deck: str | None
    suit: str | None
    rank: int | None
    folded_location: int | None
    layer_label: str | None

    def __post_init__(self):
        super().__post_init__(); _kind(self.ref, Kind.CUE); _text(self.symbol)
        if self.rank is not None and self.rank < 0: raise ValueError("rank cannot be negative")
        if self.folded_location is not None and not 1 <= self.folded_location <= 9:
            raise ValueError("the declared nine-location fold uses 1..9")


@dataclass(frozen=True)
class CueBinding(Record):
    ref: Ref
    owner: Ref
    cue: Ref
    context: Ref
    target: Ref
    scope: TimeScope
    learned_from: tuple[Ref, ...]

    def __post_init__(self):
        super().__post_init__(); _kind(self.ref, Kind.BINDING); _kind(self.owner, Kind.ENTITY)
        _kind(self.cue, Kind.CUE); _kind(self.context, Kind.CONTEXT)
        _kind(self.target, Kind.MEMORY)


@dataclass(frozen=True)
class CursorState(Record):
    ref: Ref
    owner: Ref
    current_cues: tuple[Ref, ...]
    policy: Ref | None
    practice_evidence: tuple[Ref, ...]

    def __post_init__(self):
        super().__post_init__(); _kind(self.ref, Kind.CURSOR); _kind(self.owner, Kind.ENTITY)
        for ref in self.current_cues: _kind(ref, Kind.CUE)
        if self.policy is not None: _kind(self.policy, Kind.PROCEDURE)


@dataclass(frozen=True)
class ResourceAmount(Record):
    """Nonnegative integer quanta; a versioned rule defines each unit (E05)."""
    unit: Ref
    amount: int

    def __post_init__(self):
        super().__post_init__(); _kind(self.unit, Kind.RULE)
        if self.amount < 0: raise ValueError("resource amount cannot be negative")


@dataclass(frozen=True)
class WorkRecord(Record):
    """One attempted operation and its actual resource charge, including failure."""
    ref: Ref
    owner: Ref
    operation: Ref
    before: tuple[ResourceAmount, ...]
    credited: tuple[ResourceAmount, ...]
    charged: tuple[ResourceAmount, ...]
    after: tuple[ResourceAmount, ...]
    required_units: int
    completed_units: int
    outcome: WorkStatus
    reason: str

    def __post_init__(self):
        super().__post_init__(); _kind(self.ref, Kind.WORK); _kind(self.owner, Kind.ENTITY)
        _kind(self.operation, Kind.PROCEDURE); _text(self.reason)
        maps = []
        for amounts in (self.before, self.credited, self.charged, self.after):
            mapping = {a.unit: a.amount for a in amounts}
            if len(mapping) != len(amounts): raise ValueError("duplicate resource unit")
            maps.append(mapping)
        before, credit, charge, after = maps
        units = set(before) | set(credit) | set(charge) | set(after)
        if not units or set(before) != units or set(after) != units:
            raise ValueError("before and after must declare all resource units, including zero")
        if any(before[u] + credit.get(u, 0) - charge.get(u, 0) != after[u] for u in units):
            raise ValueError("resource conservation failed")
        if self.required_units < 1 or not 0 <= self.completed_units <= self.required_units:
            raise ValueError("invalid work extent")
        if self.outcome == WorkStatus.COMPLETED and self.completed_units != self.required_units:
            raise ValueError("completed status and work extent disagree")
        if self.outcome == WorkStatus.PARTIAL and not 0 < self.completed_units < self.required_units:
            raise ValueError("partial work must be started and unfinished")
        if self.outcome in (WorkStatus.PENDING, WorkStatus.DEFERRED) and self.completed_units != 0:
            raise ValueError("performed work must be reported as partial or failed")


@dataclass(frozen=True)
class ProcessingStep(Record):
    order: int
    operation: Ref
    inputs: tuple[Ref, ...]
    outputs: tuple[Ref, ...]
    work: Ref

    def __post_init__(self):
        super().__post_init__(); _kind(self.operation, Kind.PROCEDURE); _kind(self.work, Kind.WORK)
        if self.order < 0: raise ValueError("step order must be nonnegative")


@dataclass(frozen=True)
class MovementRecord(Record):
    ref: Ref
    holon: Ref
    demand: Ref | None
    formal: FormalMovement
    operation: Ref
    preconditions: tuple[Proposition, ...]
    content: tuple[Ref, ...]
    history: tuple[ProcessingStep, ...]
    outcome: WorkStatus
    retained: tuple[Ref, ...]
    reason: str

    def __post_init__(self):
        super().__post_init__(); _kind(self.ref, Kind.MOVEMENT); _kind(self.holon, Kind.ENTITY)
        _kind(self.operation, Kind.PROCEDURE); _text(self.reason)
        if self.demand is not None: _kind(self.demand, Kind.DEMAND)
        if tuple(s.order for s in self.history) != tuple(range(len(self.history))):
            raise ValueError("processing history must preserve consecutive order")
        if self.outcome != WorkStatus.PENDING and not self.history:
            raise ValueError("attempted movement needs a processing witness, including deferral")
        for ref in self.retained: _kind(ref, Kind.MEMORY, Kind.PROCEDURE, Kind.BINDING)


class EvidenceStatus(str, Enum):
    ESTABLISHED = "established"
    FAILED = "failed"
    UNASSESSED = "unassessed"


class Dimension(str, Enum):
    FACTUAL_AGREEMENT = "factual_agreement"
    IDENTITY_RETURN = "identity_return"
    PATH_CONDITIONS = "path_conditions"
    RETAINED_CAPACITY = "retained_capacity"


class IdeaPhase(str, Enum):
    INITIATE = "initiate"
    DEFINE = "define"
    ENGAGE = "engage"
    ALIGN = "align"


@dataclass(frozen=True)
class IdeaCell(Record):
    """Phase × perspective; a different type from Crux's origin × destination."""
    phase: IdeaPhase
    perspective: Perspective


@dataclass(frozen=True)
class ProtocolSpec(Record):
    ref: Ref
    transform: Ref
    return_policy: Ref
    domain: str
    resource_conditions: str
    path_conditions: tuple[str, ...]

    def __post_init__(self):
        super().__post_init__(); _kind(self.ref, Kind.PROTOCOL)
        _kind(self.transform, Kind.PROCEDURE); _kind(self.return_policy, Kind.PROCEDURE)
        _text(self.domain); _text(self.resource_conditions)


@dataclass(frozen=True)
class AssessmentSpec(Record):
    ref: Ref
    declared_at: Moment
    state_space: str
    identity_criterion: Ref
    identity_features: tuple[str, ...]
    protocols: tuple[ProtocolSpec, ...]
    comparison_rule: Ref
    scope: str
    composition_claim: str

    def __post_init__(self):
        super().__post_init__(); _kind(self.ref, Kind.ASSESSMENT)
        _kind(self.identity_criterion, Kind.IDENTITY); _kind(self.comparison_rule, Kind.RULE)
        _text(self.state_space); _text(self.scope); _text(self.composition_claim)
        if not self.identity_features or not self.protocols:
            raise ValueError("assessment must predeclare features and protocols")
        for f in self.identity_features: _text(f)
        if len({p.ref for p in self.protocols}) != len(self.protocols):
            raise ValueError("protocol family contains duplicates")


@dataclass(frozen=True)
class AssessmentResult(Record):
    spec: Ref
    protocol: Ref
    dimension: Dimension
    status: EvidenceStatus
    evidence: tuple[Ref, ...]
    tested_sequences: tuple[tuple[Ref, ...], ...]
    reason: str

    def __post_init__(self):
        super().__post_init__(); _kind(self.spec, Kind.ASSESSMENT); _kind(self.protocol, Kind.PROTOCOL)
        _text(self.reason)
        if self.status != EvidenceStatus.UNASSESSED and not self.evidence:
            raise ValueError("assessed result requires a witness")
        for seq in self.tested_sequences:
            if not seq: raise ValueError("tested protocol sequence cannot be empty")
            for ref in seq: _kind(ref, Kind.PROTOCOL)


@dataclass(frozen=True)
class ActionRequest(Record):
    actor: Ref
    operation: Ref
    inputs: tuple[Ref, ...]
    based_on: tuple[Ref, ...]

    def __post_init__(self):
        super().__post_init__(); _kind(self.actor, Kind.ENTITY); _kind(self.operation, Kind.PROCEDURE)
        for ref in self.based_on: _kind(ref, Kind.OBSERVATION, Kind.MEMORY, Kind.MOVEMENT)


@dataclass(frozen=True)
class ParticipantInput(Record):
    actor: Ref
    at: Moment
    observations: tuple[Observation, ...]
    own_memories: tuple[MemoryRevision, ...]
    available: tuple[ResourceAmount, ...]
    demands: tuple[Ref, ...]

    def __post_init__(self):
        super().__post_init__(); _kind(self.actor, Kind.ENTITY)
        if any(o.observer != self.actor or o.delivered_at > self.at for o in self.observations):
            raise ValueError("undelivered or other-observer input")
        if any(m.owner != self.actor or m.retained_at > self.at for m in self.own_memories):
            raise ValueError("future or other-owner memory input")
        for ref in self.demands: _kind(ref, Kind.DEMAND)
