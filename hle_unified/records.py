"""Immutable U2 boundary records, reusing the baseline's strict Record checks.

Identity is namespace/key; revisions and definition bindings are always exact.
All dynamics, material units, and lifecycle choices here are engineering rules.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from hle.contracts import Record, Moment, TimeScope, ClaimStatus, EvidenceStatus


def text_required(value):
    if not value.strip():
        raise ValueError("blank identifier or required text")


@dataclass(frozen=True, order=True)
class ObjectId(Record):
    namespace: str
    key: str

    def __post_init__(self):
        super().__post_init__()
        text_required(self.namespace)
        text_required(self.key)


@dataclass(frozen=True, order=True)
class ObjectRef(Record):
    identity: ObjectId
    revision: int

    def __post_init__(self):
        super().__post_init__()
        if self.revision < 1:
            raise ValueError("revision must be positive")


Atom = ObjectRef | ObjectId | str | int | bool | None


@dataclass(frozen=True)
class Attribute(Record):
    name: str
    value: Atom

    def __post_init__(self):
        super().__post_init__()
        text_required(self.name)


@dataclass(frozen=True)
class Proposition(Record):
    subject: ObjectRef
    relation: str
    object: Atom
    context: ObjectRef
    scope: TimeScope

    def __post_init__(self):
        super().__post_init__()
        text_required(self.relation)


class Role(str, Enum):
    DEFINITION = "definition"
    MATERIAL = "material"
    PERSON = "person"
    CONTEXT = "context"
    CONCEPT = "concept"
    PROCEDURE = "procedure"
    RELATION = "relation"
    COMMITMENT = "commitment"
    COLLECTIVE = "collective"
    EVENT = "event"
    OBSERVATION = "observation"
    CLAIM = "claim"
    INTERPRETATION = "interpretation"
    ATTITUDE = "attitude"
    ASSESSMENT = "assessment"
    RECORD = "record"


class Occurrence(str, Enum):
    ACTUAL_EVENT = "actual_event"
    OBSERVATION = "observation"
    REMEMBERED_CLAIM = "remembered_claim"
    HYPOTHETICAL = "hypothetical_continuation"
    INTERPRETATION = "interpretation"


class SourceStatus(str, Enum):
    SOURCE_DEFINED = "source_defined"
    ENGINEERING = "engineering_choice"
    UNSPECIFIED = "unspecified"
    LEGACY = "legacy_preserved"


class Lifecycle(str, Enum):
    ACTIVE = "active"
    RETIRED = "retired"


@dataclass(frozen=True)
class Definition(Record):
    meaning: str | None
    source_status: SourceStatus
    constraints: tuple[Attribute, ...] = ()
    operations: tuple[ObjectRef, ...] = ()

    def __post_init__(self):
        super().__post_init__()
        if self.source_status == SourceStatus.UNSPECIFIED and self.meaning is not None:
            raise ValueError("unspecified meaning must remain None")
        if self.meaning is not None:
            text_required(self.meaning)
        if len({p.name for p in self.constraints}) != len(self.constraints):
            raise ValueError("duplicate definition constraint")


@dataclass(frozen=True)
class Material(Record):
    owner: ObjectId
    custodian: ObjectId
    quantity: int
    unit: ObjectRef
    condition: str

    def __post_init__(self):
        super().__post_init__()
        if self.quantity < 1:
            raise ValueError("material quantity must be positive integer quanta")
        text_required(self.condition)


@dataclass(frozen=True)
class Concept(Record):
    propositions: tuple[Proposition, ...]


@dataclass(frozen=True)
class Procedure(Record):
    inputs: tuple[str, ...]
    preconditions: tuple[Proposition, ...]
    steps: tuple[ObjectRef, ...]
    effects: tuple[Proposition, ...]
    executor: str | None = None

    def __post_init__(self):
        super().__post_init__()
        if len(set(self.inputs)) != len(self.inputs):
            raise ValueError("duplicate procedure input")
        for name in self.inputs:
            text_required(name)
        if self.executor is not None:
            text_required(self.executor)


@dataclass(frozen=True)
class Endpoint(Record):
    role: str
    target: ObjectRef

    def __post_init__(self):
        super().__post_init__()
        text_required(self.role)


@dataclass(frozen=True)
class Relation(Record):
    predicate: str
    endpoints: tuple[Endpoint, ...]
    directed: bool
    context: ObjectRef
    scope: TimeScope
    terms: tuple[Attribute, ...] = ()

    def __post_init__(self):
        super().__post_init__()
        text_required(self.predicate)
        if len(self.endpoints) < 2 or len({p.role for p in self.endpoints}) != len(self.endpoints):
            raise ValueError("relation needs distinct named participant roles")
        if len({p.name for p in self.terms}) != len(self.terms):
            raise ValueError("duplicate relation term")


@dataclass(frozen=True)
class Composition(Record):
    members: tuple[ObjectId, ...]
    boundary: str
    resources: tuple[ObjectId, ...] = ()
    summary_dependencies: tuple[ObjectRef, ...] = ()

    def __post_init__(self):
        super().__post_init__()
        text_required(self.boundary)
        for values in (self.members, self.resources, self.summary_dependencies):
            if len(set(values)) != len(values):
                raise ValueError("duplicate composition member, resource or dependency")


@dataclass(frozen=True)
class Memory(Record):
    owner: ObjectId
    entries: tuple[ObjectRef, ...] = ()


@dataclass(frozen=True)
class Agency(Record):
    owner: ObjectId
    acquired: tuple[ObjectRef, ...] = ()


@dataclass(frozen=True)
class Governance(Record):
    rules: tuple[ObjectRef, ...] = ()
    obligations: tuple[ObjectRef, ...] = ()


@dataclass(frozen=True)
class Account(Record):
    referent: ObjectRef | None
    content: tuple[Proposition, ...]
    at: Moment
    holder: ObjectId | None = None
    sources: tuple[ObjectRef, ...] = ()


@dataclass(frozen=True)
class Attitude(Record):
    holder: ObjectId
    target: ObjectRef
    endorsement: ClaimStatus
    confidence_percent: int | None = None

    def __post_init__(self):
        super().__post_init__()
        if self.confidence_percent is not None and not 0 <= self.confidence_percent <= 100:
            raise ValueError("confidence must be 0..100 or unspecified")


@dataclass(frozen=True)
class Assessment(Record):
    target: ObjectRef
    dimension: str
    result: EvidenceStatus
    evidence: tuple[ObjectRef, ...]
    reason: str

    def __post_init__(self):
        super().__post_init__()
        text_required(self.dimension)
        text_required(self.reason)
        if self.result != EvidenceStatus.UNASSESSED and not self.evidence:
            raise ValueError("assessed result requires evidence")


# Typed legacy syntax preserves every field, enum, tuple and exact Ref; it does
# not interpret unknown record families as material facts or grant capabilities.
@dataclass(frozen=True)
class LegacyEnum(Record):
    tag: str
    value: str | int | bool


@dataclass(frozen=True)
class LegacyTuple(Record):
    items: tuple[LegacyValue, ...]


@dataclass(frozen=True)
class LegacyField(Record):
    name: str
    value: LegacyValue


@dataclass(frozen=True)
class LegacyRecord(Record):
    tag: str
    fields: tuple[LegacyField, ...]

    def __post_init__(self):
        super().__post_init__()
        if len({f.name for f in self.fields}) != len(self.fields):
            raise ValueError("duplicate legacy field")


LegacyValue = ObjectRef | LegacyEnum | LegacyTuple | LegacyRecord | str | int | bool | None


@dataclass(frozen=True)
class LegacyPayload(Record):
    value: LegacyValue


Facet = (Definition | Material | Concept | Procedure | Relation | Composition |
         Memory | Agency | Governance | Account | Attitude | Assessment | LegacyPayload)


@dataclass(frozen=True)
class ObjectVersion(Record):
    ref: ObjectRef
    writer: str
    label: str
    roles: tuple[Role, ...]
    facets: tuple[Facet, ...] = ()
    definition: ObjectRef | None = None
    previous: ObjectRef | None = None
    occurrence: Occurrence | None = None
    lifecycle: Lifecycle = Lifecycle.ACTIVE
    attributes: tuple[Attribute, ...] = ()

    def __post_init__(self):
        super().__post_init__()
        text_required(self.writer)
        text_required(self.label)
        if not self.roles or len(set(self.roles)) != len(self.roles):
            raise ValueError("roles must be nonempty and unique")
        if len({type(f) for f in self.facets}) != len(self.facets):
            raise ValueError("duplicate capability state")
        if len({a.name for a in self.attributes}) != len(self.attributes):
            raise ValueError("duplicate attribute")
        expected = None if self.ref.revision == 1 else ObjectRef(self.ref.identity, self.ref.revision - 1)
        if self.previous != expected:
            raise ValueError("revision must pin its immediate predecessor")
        legacy = self.facet(LegacyPayload) is not None
        if legacy:
            if self.writer != "legacy.r21b" or len(self.facets) != 1:
                raise ValueError("legacy compatibility payloads have one authoritative writer")
            return
        required = {Role.DEFINITION: Definition, Role.MATERIAL: Material,
                    Role.CONCEPT: Concept, Role.PROCEDURE: Procedure,
                    Role.RELATION: Relation, Role.COMMITMENT: Relation,
                    Role.COLLECTIVE: Composition, Role.EVENT: Account,
                    Role.OBSERVATION: Account, Role.CLAIM: Account,
                    Role.INTERPRETATION: Account, Role.ATTITUDE: Attitude,
                    Role.ASSESSMENT: Assessment}
        for role in self.roles:
            if role in required and self.facet(required[role]) is None:
                raise ValueError(f"missing state for {role.value}")
        for role, cls in required.items():
            if cls not in (Relation, Account) and self.facet(cls) is not None and role not in self.roles:
                raise ValueError(f"capability requires role {role.value}")
        if self.facet(Relation) is not None and not {Role.RELATION, Role.COMMITMENT}.intersection(self.roles):
            raise ValueError("relation state requires a relation role")
        expected_role = {Occurrence.ACTUAL_EVENT: Role.EVENT, Occurrence.OBSERVATION: Role.OBSERVATION,
                         Occurrence.REMEMBERED_CLAIM: Role.CLAIM, Occurrence.HYPOTHETICAL: Role.CLAIM,
                         Occurrence.INTERPRETATION: Role.INTERPRETATION}
        if (self.occurrence is None) != (self.facet(Account) is None):
            raise ValueError("account requires explicit occurrence status")
        if self.occurrence is not None and expected_role[self.occurrence] not in self.roles:
            raise ValueError("role and occurrence disagree")
        if self.occurrence is not None and set(self.roles).intersection({Role.EVENT, Role.OBSERVATION, Role.CLAIM, Role.INTERPRETATION}) != {expected_role[self.occurrence]}:
            raise ValueError("one occurrence role per account")
        if self.facet(Account) is not None:
            if self.occurrence != Occurrence.ACTUAL_EVENT and self.facet(Account).holder is None:
                raise ValueError("situated account requires a holder")
        for cls in (Memory, Agency):
            if self.facet(cls) is not None and self.facet(cls).owner != self.ref.identity:
                raise ValueError("personal capabilities belong to this instance")

    def facet(self, cls):
        return next((f for f in self.facets if type(f) is cls), None)


class ChangeKind(str, Enum):
    CREATE = "create"
    REVISE = "revise"
    DEFINITION = "changed_definition"
    MEMBERSHIP = "membership"
    TRANSFER = "transfer"
    DIVIDE = "division"
    COMBINE = "combination"
    REPLACE = "replacement"
    MATERIAL = "paid_material_effect"


@dataclass(frozen=True)
class Lineage(Record):
    kind: ChangeKind
    inputs: tuple[ObjectRef, ...]
    outputs: tuple[ObjectRef, ...]
    evidence: tuple[ObjectRef, ...]
    reason: str
    rule: ObjectRef | None = None

    def __post_init__(self):
        super().__post_init__()
        text_required(self.reason)
        if not self.outputs or len(set(self.inputs)) != len(self.inputs) or len(set(self.outputs)) != len(self.outputs):
            raise ValueError("lineage must have distinct inputs and outputs")


@dataclass(frozen=True)
class Transaction(Record):
    key: str
    at: Moment
    writer: str
    actor: ObjectId | None
    versions: tuple[ObjectVersion, ...]
    lineage: tuple[Lineage, ...]

    def __post_init__(self):
        super().__post_init__()
        text_required(self.key)
        text_required(self.writer)
        if not self.versions or not self.lineage:
            raise ValueError("transaction must have versions and causal lineage")


@dataclass(frozen=True)
class Checkpoint(Record):
    schema: str
    journal: tuple[Transaction, ...]
