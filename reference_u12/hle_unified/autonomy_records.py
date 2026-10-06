"""U6 finite engineering contract; no psychological/clinical validity claim."""
from dataclasses import dataclass
from hle.contracts import Record
from .records import ObjectId, ObjectRef, Definition, SourceStatus, ObjectVersion, Role
from .material import attributes
from .operations import address
from .operation_records import WRITER
from .cognitive_records import registry as cognitive_registry

LAW6 = address("u6.contract", "continuing-finite-workshop-v1")


def world_contract():
    return ObjectVersion(LAW6, WRITER, "Continuing finite workshop v1", (Role.DEFINITION,),
        (Definition("Bounded anticipation and continuing participant opportunities; no energy or material regeneration.",
            SourceStatus.ENGINEERING, attributes({"law": "u6.continuing-finite-workshop-v1",
                "attention_cost": 1, "forecast_node_cost": 1, "rest_cost": 1,
                "rest_fatigue_reduction": 30, "energy_regeneration": 0,
                "time_regeneration": 0, "skill_from_needs": False})),))


@dataclass(frozen=True)
class AutonomyConfig(Record):
    actor: ObjectId
    context: ObjectRef
    cue: ObjectRef
    rule: ObjectRef
    target: ObjectRef
    tool: ObjectRef | None = None
    stock: ObjectRef | None = None
    care: ObjectRef | None = None
    procedure: ObjectRef | None = None
    partner: ObjectId | None = None
    explore_target: ObjectRef | None = None
    goal_uses: int = 2
    work_limit: int = 8
    horizon: int = 2
    max_nodes: int = 8
    visit_limit: int = 32
    failure_limit: int = 2
    fatigue_limit: int = 60
    boredom_limit: int = 2
    urgency_after: int = 80
    threat_limit: int = 3
    anticipation: bool = True

    def __post_init__(self):
        super().__post_init__()
        if self.horizon not in (1, 2) or not 1 <= self.max_nodes <= 16:
            raise ValueError("explicit bounded forecast coverage required")
        if any(getattr(self, k) < 1 for k in ("work_limit", "visit_limit", "failure_limit",
                "fatigue_limit", "boredom_limit", "urgency_after", "threat_limit")) or self.goal_uses < 0:
            raise ValueError("positive scheduling limits and nonnegative standing demand required")


@dataclass(frozen=True)
class AutonomyState(Record):
    actor: ObjectId
    target: ObjectRef
    phase: str = "idle"
    active: str = ""
    active_kind: str = ""
    resume_phase: str = "idle"
    paused: str = ""
    paused_kind: str = ""
    plan: ObjectRef | None = None
    forecast: ObjectRef | None = None
    prediction: ObjectRef | None = None
    await_event: ObjectRef | None = None
    await_operation: ObjectRef | None = None
    await_target: ObjectRef | None = None
    observed: ObjectRef | None = None
    last_action: str = ""
    last_signature: str = ""
    seen: tuple[ObjectRef, ...] = ()
    offers_at_ask: tuple[ObjectRef, ...] = ()
    turns: int = 0
    uses: int = 0
    failures: int = 0
    fatigue: int = 0
    energy_mark: int = 0
    time_mark: int = 0
    monotony: int = 0
    pressure: int = 0
    fear: int = 0
    scarcity: int = 0
    boredom: int = 0
    explored: bool = False
    asked: bool = False
    switched: bool = False
    stopped: bool = False
    decision: str = ""
    reason: str = ""
    wait_kind: str = ""
    wait_ref: ObjectRef | None = None
    wait_resources: tuple[ObjectRef, ...] = ()


@dataclass(frozen=True)
class ForecastRequest(Record):
    key: str
    actor: ObjectId
    plan: ObjectRef
    config: AutonomyConfig

    def __post_init__(self):
        super().__post_init__()
        if not self.key.strip() or self.actor != self.config.actor:
            raise ValueError("owned forecast and operation key required")


def registry():
    return {**cognitive_registry(), **{c.__name__: c for c in
        (AutonomyConfig, AutonomyState, ForecastRequest)}}
