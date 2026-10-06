"""U11 bounded coordination requests. Every numerical rule is an engineering choice."""
from dataclasses import dataclass
from hle.contracts import Record
from .records import ObjectId, ObjectRef, ObjectVersion, Role, Definition, SourceStatus
from .operations import address
from .operation_records import WRITER
from .material import attributes
from .language_records import registry as parent_registry

LAW11 = address("u11.contract", "nested-workshop-v1")
PURPOSES = ("compose", "invite", "join", "leave", "link", "unlink", "plan", "accept",
            "withdraw", "instantiate", "select", "observe", "retain", "summarize")


def world_contract():
    return ObjectVersion(LAW11, WRITER, "Nested collective workshop v1", (Role.DEFINITION,),
        (Definition("Acyclic overlapping membership, scoped projections and observed constituent work.",
            SourceStatus.ENGINEERING, attributes({"law":"u11.nested-workshop-v1",
                "membership_is_skill":False, "summary_is_permission":False,
                "effects":"paid constituent operations", "history":"exact"})),))


@dataclass(frozen=True)
class CollectiveRequest(Record):
    key: str
    actor: ObjectId
    purpose: str
    context: ObjectRef
    cue: ObjectRef
    focus: ObjectRef | None = None
    members: tuple[ObjectRef, ...] = ()
    resources: tuple[ObjectRef, ...] = ()
    peer: ObjectId | None = None
    program: tuple = ()
    boundary: str = ""
    scope: str = "inventory"
    observation: ObjectRef | None = None
    mode: str = "aggregate"
    limit: int = 128

    def __post_init__(self):
        super().__post_init__()
        if not self.key.strip() or self.purpose not in PURPOSES or self.limit < 1:
            raise ValueError("named supported coordination and positive visit budget required")
        if self.mode not in ("aggregate", "detailed") or self.scope not in ("inventory", "membership"):
            raise ValueError("unsupported projection or execution mode")
        if (self.purpose == "compose") != (self.focus is None):
            raise ValueError("composition creates a group; other work names an exact focus")
        if (self.purpose == "compose") != bool(self.boundary.strip()):
            raise ValueError("new composites require an explicit boundary")
        if self.purpose not in ("compose", "link", "unlink") and (self.members or self.resources):
            raise ValueError("unexpected membership payload")
        if (self.purpose == "invite") != (self.peer is not None):
            raise ValueError("invitation names its receiver")
        if (self.purpose == "plan") != bool(self.program):
            raise ValueError("only a proposed collective program supplies steps")
        if (self.purpose == "observe") != (self.observation is not None):
            raise ValueError("observing constituent work requires a delivered observation")
        for values in (self.members, self.resources):
            if len({r.identity for r in values}) != len(values):
                raise ValueError("duplicate member or resource identity")


def registry():
    return {**parent_registry(), "CollectiveRequest":CollectiveRequest}
