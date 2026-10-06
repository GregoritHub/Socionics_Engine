"""U7 experimental pattern language, separate from evaluator classifications."""
from dataclasses import dataclass
from hle.contracts import Record
from .records import ObjectId, ObjectRef, ObjectVersion, Role, Definition, SourceStatus
from .particulars import DetailAddress
from .operations import address
from .operation_records import WRITER
from .material import attributes
from .autonomy_records import registry as parent_registry

KINDS = ("obligation", "salience", "forecast", "exclude_route", "approval")
LAW7 = address("u7.contract", "situated-patterns-v1")


def world_contract():
    return ObjectVersion(LAW7, WRITER, "Situated pattern operations v1", (Role.DEFINITION,),
        (Definition("Paid contextual attribution and encounter; no correction or mastery awarded.",
            SourceStatus.ENGINEERING, attributes({"law": "u7.situated-patterns-v1",
                "effect_cost": 1, "generated_effect": "approval", "recurrence_minimum": 2})),))


@dataclass(frozen=True)
class Effect(Record):
    kind: str
    route: str = "*"
    amount: int = 1

    def __post_init__(self):
        super().__post_init__()
        if self.kind not in KINDS or not self.route.strip() or not -20 <= self.amount <= 20:
            raise ValueError("registered effect, route and bounded amount required")
        if self.amount == 0 or (self.kind != "salience" and self.amount < 0):
            raise ValueError("nonzero salience or positive deformation amount required")


@dataclass(frozen=True)
class PatternPolicy(Record):
    actor: ObjectId
    generate: bool = True
    threshold: int = 2

    def __post_init__(self):
        super().__post_init__()
        if not 2 <= self.threshold <= 16:
            raise ValueError("bounded recurrence threshold required")


@dataclass(frozen=True)
class Pattern(Record):
    ref: ObjectRef
    owner: ObjectId
    origin: ObjectRef
    context: ObjectRef
    cue: ObjectRef
    trigger: ObjectRef
    effects: tuple[Effect, ...]
    evidence: tuple[ObjectRef, ...]
    origin_mode: str

    def __post_init__(self):
        super().__post_init__()
        if not self.effects or not self.evidence or self.origin_mode not in ("generated", "injected_fixture"):
            raise ValueError("explicit pattern origin and supported content required")


@dataclass(frozen=True)
class EncounterRequest(Record):
    key: str
    actor: ObjectId
    target: ObjectRef
    context: ObjectRef
    cue: ObjectRef
    carrier: ObjectRef
    bearer: ObjectRef
    evidence: tuple[DetailAddress, ...]
    route: str = "engage"
    demand: bool = True
    visit_limit: int = 32

    def __post_init__(self):
        super().__post_init__()
        if not self.key.strip() or self.route not in ("engage", "inspect") or self.visit_limit < 1:
            raise ValueError("encounter key, executable intent and positive recall bound required")
        if len(set(self.evidence)) != len(self.evidence):
            raise ValueError("duplicate encounter evidence")


@dataclass(frozen=True)
class PatternSeed(Record):
    """Simulator-only detector fixture. Never described as generated history."""
    actor: ObjectId
    context: ObjectRef
    cue: ObjectRef
    trigger: ObjectRef
    origin: ObjectRef
    effects: tuple[Effect, ...]
    evidence: tuple[DetailAddress, ...]


def registry():
    return {**parent_registry(), **{c.__name__: c for c in
        (Effect, PatternPolicy, Pattern, EncounterRequest, PatternSeed)}}
