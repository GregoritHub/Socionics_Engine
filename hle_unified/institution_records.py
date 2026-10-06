"""U12 generic public work operations; institutional terms are runtime outputs."""
from dataclasses import dataclass
from hle.contracts import Record
from .records import ObjectId, ObjectRef, ObjectVersion, Role, Definition, SourceStatus
from .operations import address
from .operation_records import WRITER
from .material import attributes
from .collective_records import registry as parent_registry

LAW12 = address("u12.contract", "participant-institutions-v1")
PURPOSES = ("propose", "respond", "counter", "ratify", "apply", "permit", "record",
            "teach", "learn", "assent", "withdraw_assent", "withdraw_vote", "dispute")
INTENTS = ("establish", "review", "maintain", "succession", "dissolve")


def world_contract():
    return ObjectVersion(LAW12, WRITER, "Participant institution contract v1", (Role.DEFINITION,),
        (Definition("Situated proposals, exact unanimous consent, repeated observed practice and public revision.",
            SourceStatus.ENGINEERING, attributes({"minimum_members":2,"minimum_practices":2,
                "personal_correction_erases_rule":False,"teaching_grants_skill":False,
                "physical_law":"unchanged U4; collective service is voluntary"})),))


@dataclass(frozen=True)
class InstitutionRequest(Record):
    key: str
    actor: ObjectId
    purpose: str
    context: ObjectRef
    cue: ObjectRef
    focus: ObjectRef
    encounter: ObjectRef | None = None
    slots: tuple = ()
    goal: tuple = ()
    intent: str = "establish"
    peer: ObjectId | None = None
    support: ObjectRef | None = None
    limit: int = 128

    def __post_init__(self):
        super().__post_init__()
        if not self.key.strip() or self.purpose not in PURPOSES or self.intent not in INTENTS:
            raise ValueError("named institution operation and supported intent required")
        if type(self.limit) is not int or self.limit < 1:
            raise ValueError("positive paid search/inspection budget required")
        if self.purpose in ("propose","counter","respond","apply","assent") and self.encounter is None:
            raise ValueError("current actor-owned processed encounter required")
        if self.purpose not in ("propose","counter","apply") and (self.slots or self.goal):
            raise ValueError("unexpected task binding or material goal")
        if self.purpose == "propose" and self.intent == "establish" and not self.goal:
            raise ValueError("a material demand, not a supplied institution, starts proposal work")
        if self.goal and (self.purpose != "propose" or self.intent != "establish"):
            raise ValueError("revisions preserve the material task identity")
        if self.slots and (len(dict(self.slots)) != len(self.slots) or "target" not in dict(self.slots)):
            raise ValueError("unique grounded slots including a target required")
        if self.purpose == "teach" and self.peer is None:
            raise ValueError("teaching names its learner")
        if self.purpose == "propose" and (self.intent == "succession") != (self.peer is not None):
            raise ValueError("only succession proposal names a new steward")


def registry():
    return {**parent_registry(), "InstitutionRequest":InstitutionRequest}
