"""Finite requests for paid constructive work; no complete answer input."""
from dataclasses import dataclass
from hle.contracts import Record
from .records import ObjectId, ObjectRef, ObjectVersion, Role, Definition, SourceStatus
from .operations import address
from .operation_records import WRITER
from .material import attributes
from .development_records import registry as parent_registry

LAW9 = address("u9.contract", "constructive-workshop-v1")
PURPOSES = ("notice", "search", "instantiate", "select", "observe", "retain")


def world_contract():
    return ObjectVersion(LAW9, WRITER, "Constructive workshop v1", (Role.DEFINITION,),
        (Definition("Paid finite search over acquired actions, conditional retained procedures and observed consequences.",
            SourceStatus.ENGINEERING, attributes({"law": "u9.constructive-workshop-v1",
                "search": "breadth_first_with_deferred_frontier", "free_mastery": False,
                "initial_guard": "observed_start_condition", "revision": "observed_feature_split"})),))


@dataclass(frozen=True)
class CompositionRequest(Record):
    key: str
    actor: ObjectId
    purpose: str
    context: ObjectRef
    cue: ObjectRef
    slots: tuple[tuple[str, ObjectRef], ...] = ()
    goal: tuple = ()
    focus: ObjectRef | None = None
    item: ObjectRef | None = None
    observation: ObjectRef | None = None
    limit: int = 8
    depth: int = 4

    def __post_init__(self):
        super().__post_init__()
        if not self.key.strip() or self.purpose not in PURPOSES or self.limit < 1 or self.depth < 1:
            raise ValueError("named constructive operation and positive finite limits required")
        if len({s for s, _ in self.slots}) != len(self.slots) or len({r.identity for _, r in self.slots}) != len(self.slots):
            raise ValueError("distinct slot names and object identities required")
        if self.purpose == "notice":
            if "target" not in dict(self.slots) or not self.goal or any((self.focus, self.item, self.observation)):
                raise ValueError("notice takes only accessible slots and a standing goal")
        elif self.focus is None or self.goal or self.slots:
            raise ValueError("continuing work needs an owned output, never a supplied program")
        if (self.purpose == "instantiate") != (self.item is not None):
            raise ValueError("only instantiation selects an owned program")
        if (self.purpose == "observe") != (self.observation is not None):
            raise ValueError("only observed execution takes an observation")


def registry():
    return {**parent_registry(), "CompositionRequest": CompositionRequest}
