"""U8 finite development language. Thresholds and prices are engineering choices."""
from dataclasses import dataclass
from hle.contracts import Record
from .records import ObjectId, ObjectRef, ObjectVersion, Role, Definition, SourceStatus
from .particulars import DetailAddress
from .operations import address
from .operation_records import WRITER
from .material import attributes
from .shell_records import registry as parent_registry

LAW8 = address("u8.contract", "retained-guarded-response-v1")
PURPOSES = ("release", "respond", "practice", "reorganize", "reown")


def world_contract():
    return ObjectVersion(LAW8, WRITER, "Retained guarded response v1", (Role.DEFINITION,),
        (Definition("Local evidence-based release; repeated independently observed practice; scoped reusable response.",
            SourceStatus.ENGINEERING, attributes({"law": "u8.retained-guarded-response-v1",
                "minimum_independent_episodes": 2, "minimum_targets": 2,
                "organization": "check_opportunity_then_engage", "free_mastery": False})),))


@dataclass(frozen=True)
class DevelopmentRequest(Record):
    key: str
    actor: ObjectId
    purpose: str
    pattern: ObjectRef
    context: ObjectRef
    cue: ObjectRef
    targets: tuple[ObjectRef, ...]
    evidence: tuple[DetailAddress, ...]
    partner: ObjectRef | None = None
    observation: ObjectRef | None = None
    demand: bool = True
    visit_limit: int = 128

    def __post_init__(self):
        super().__post_init__()
        if not self.key.strip() or self.purpose not in PURPOSES or not self.targets:
            raise ValueError("named development operation and nonempty targets required")
        if len(set(self.targets)) != len(self.targets) or len(set(self.evidence)) != len(self.evidence):
            raise ValueError("duplicate targets or evidence")
        if not self.evidence or type(self.demand) is not bool or type(self.visit_limit) is not int or self.visit_limit < 1:
            raise ValueError("processed evidence, explicit demand and positive recall budget required")
        if self.purpose == "release" and len(self.targets) != 1:
            raise ValueError("release is local to one exact target")
        if (self.purpose == "practice") != (self.observation is not None):
            raise ValueError("only practice takes an observed execution")


def registry():
    return {**parent_registry(), "DevelopmentRequest": DevelopmentRequest}
