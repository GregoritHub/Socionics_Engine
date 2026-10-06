"""R5 declared assays and exact evidence. S01--S09 are operational hypotheses."""
from dataclasses import dataclass
from .contracts import (AssessmentResult, AssessmentSpec, Atom, EvidenceStatus, IdeaCell, Kind,
    MemoryRevision, Moment, Observation, Proposition, Record, Ref, WorkRecord,
    WorldEvent)
from .metabolism_records import (MetabolicCommand, MetabolicTransaction,
    ProcessingPolicy, Profile)
from .memory_records import MemoryTransaction, text
from .world_records import Message, Task, Transaction, WorldConfig
from .crux import Perspective

ASSESS = Ref(Kind.RULE, "r5.assessment", 1)
MATERIAL = Ref(Kind.PROCEDURE, "r5.material_treatment", 1)
FEATURES = ("claim_links", "claim_scope", "capacity_rules", "perspective")


@dataclass(frozen=True)
class Contrast(Record):
    perspective: Perspective
    left: Atom
    right: Atom


@dataclass(frozen=True)
class PhaseEvidence(Record):
    cell: IdeaCell
    status: EvidenceStatus
    evidence: tuple[Ref, ...]
    reason: str


@dataclass(frozen=True)
class Study(Record):
    spec: AssessmentSpec
    actor: Ref
    memory_key: str
    item: Ref
    operations: tuple[Ref, ...]
    max_units: int = 1000
    forbid_discrepancy: bool = False
    recurrence: int = 2
    provenance: str = "controlled_execution"
    contrasts: tuple[Contrast, ...] = ()

    def __post_init__(self):
        super().__post_init__(); text(self.memory_key)
        if (len(self.spec.protocols) != 1 or not self.operations or self.max_units < 1
                or self.recurrence < 2 or len(set(self.spec.identity_features)) != len(self.spec.identity_features)
                or not set(self.spec.identity_features) <= set(FEATURES)
                or self.provenance not in ("controlled_execution", "injected_detector_fixture")):
            raise ValueError("unsupported study/domain/feature or recurrence declaration")
        if (self.spec.state_space != "r5.ownership_agent.v1"
                or self.spec.identity_criterion != Ref(Kind.IDENTITY, "r5.selected_features", 1)
                or self.spec.comparison_rule != Ref(Kind.RULE, "r5.exact", 1)):
            raise ValueError("unsupported state space, feature implementation or comparison rule")
        if len({c.perspective for c in self.contrasts}) != len(self.contrasts):
            raise ValueError("one declared contrast per perspective")

    @property
    def ref(self): return self.spec.ref


@dataclass(frozen=True)
class DeclareStudy(Record):
    command_id: str
    study: Study


@dataclass(frozen=True)
class BeginTrial(Record):
    command_id: str
    key: str
    study: Ref
    demanded: bool
    offer: MetabolicCommand | None = None
    corrective: tuple[Ref, ...] = ()


@dataclass(frozen=True)
class EndTrial(Record):
    command_id: str
    trial: Ref


@dataclass(frozen=True)
class AssessPending(Record):
    command_id: str
    limit: int = 1

    def __post_init__(self):
        super().__post_init__()
        if self.limit < 1: raise ValueError("positive assessment work limit required")


@dataclass(frozen=True)
class Snapshot(Record):
    at: Moment
    memory: Ref | None
    claims: tuple[Proposition, ...]
    capacities: tuple[Ref, ...]
    capacity_rules: tuple[str, ...]
    processing: Ref
    perspective: str
    checks: tuple[EvidenceStatus, ...]
    fact_evidence: tuple[Ref, ...]
    current_delivery: Ref | None


@dataclass(frozen=True)
class Opportunity(Record):
    required: int | None
    affordable: bool
    interpretable: bool
    contradiction: bool
    reason: str


@dataclass(frozen=True)
class TrialStart(Record):
    ref: Ref
    request: BeginTrial
    snapshot: Snapshot
    opportunity: Opportunity
    actor_cursor: int
    item_cursor: int


@dataclass(frozen=True)
class TrialResult(Record):
    ref: Ref
    start: Ref
    study: Ref
    end: Snapshot
    events: tuple[Ref, ...]
    works: tuple[Ref, ...]
    units: int
    completed_operations: tuple[Ref, ...]
    identity: EvidenceStatus
    path: EvidenceStatus
    initiated: bool
    blocked: bool
    reconstruction: bool
    discrepancy: bool
    externalized_action: bool
    successful_capacity_items: tuple[Ref, ...]
    visibility: tuple[str, ...]
    net: tuple[str, ...]
    cancellation: tuple[str, ...]
    recurrence: tuple[tuple[int, int], ...]
    reason: str


@dataclass(frozen=True)
class StudyAggregate(Record):
    ref: Ref
    study: Ref
    trials: int = 0
    blocked_run: int = 0
    reconstruction_run: int = 0
    candidate_seen: bool = False
    corrected_run: int = 0
    capacity_items: tuple[Ref, ...] = ()
    last: Ref | None = None
    failed_return: bool = False


@dataclass(frozen=True)
class StudyReport(Record):
    ref: Ref
    study: Ref
    at: Moment
    snapshot: Snapshot
    results: tuple[AssessmentResult, ...]
    adjudicable: int
    contradicted: int
    unresolved: int
    relevant: int
    delivered: int
    retained: int
    shell: str
    provenance: str
    aggregate: Ref
    phases: tuple[PhaseEvidence, ...] = ()
    closure: EvidenceStatus = EvidenceStatus.UNASSESSED


@dataclass(frozen=True)
class MaterialCommand(Record):
    """Explicit experimental treatment choices; no inferred psychological motive."""
    command_id: str
    actor: Ref
    key: str
    operation: str
    source: Ref

    def __post_init__(self):
        super().__post_init__(); text(self.key)
        if self.operation not in ("generate", "externalize", "express", "reown"):
            raise ValueError("unknown material operation")


@dataclass(frozen=True)
class MaterialState(Record):
    ref: Ref
    owner: Ref
    account: Ref
    treatment: str
    carrier: Ref | None
    previous: Ref | None
    basis: tuple[Ref, ...]


@dataclass(frozen=True)
class CarrierUse(Record):
    ref: Ref
    owner: Ref
    material: Ref
    carrier: Ref | None
    message: Ref | None
    outcome: str


Command = DeclareStudy | BeginTrial | EndTrial | AssessPending | MaterialCommand
Extra = Study | TrialStart | TrialResult | StudyAggregate | StudyReport | MaterialState | CarrierUse


@dataclass(frozen=True)
class AssessmentTransaction(Record):
    command: Command
    event: WorldEvent
    works: tuple[WorkRecord, ...] = ()
    observations: tuple[Observation, ...] = ()
    messages: tuple[Message, ...] = ()
    memories: tuple[MemoryRevision, ...] = ()
    task: Task | None = None
    extra: tuple[Extra, ...] = ()


@dataclass(frozen=True)
class AssessmentCheckpoint(Record):
    schema: str
    config: WorldConfig
    profiles: tuple[Profile, ...]
    policy: ProcessingPolicy
    journal: tuple[Transaction | MemoryTransaction | MetabolicTransaction | AssessmentTransaction, ...]
