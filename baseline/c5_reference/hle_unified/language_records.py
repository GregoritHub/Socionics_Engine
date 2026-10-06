"""Finite communication requests; content never grants receipt, consent or skill."""
from dataclasses import dataclass
from hle.contracts import Record
from .records import ObjectId, ObjectRef, ObjectVersion, Role, Definition, SourceStatus
from .operations import address
from .operation_records import WRITER
from .material import attributes
from .composition_records import registry as parent_registry

LAW10 = address("u10.contract", "grounded-workshop-v1")
ACTS = ("statement", "question", "request", "explanation", "intention", "commitment",
        "demonstration", "counterexample")
PURPOSES = ("coin", "send", "interpret", "learn", "respond", "settle", "challenge")


def world_contract():
    return ObjectVersion(LAW10, WRITER, "Grounded communication v1", (Role.DEFINITION,),
        (Definition("Paid situated interpretation and demonstrated, partner-scoped meaning.",
            SourceStatus.ENGINEERING, attributes({"law": "u10.grounded-workshop-v1",
                "distinct_examples": 2, "delivery_is_learning": False,
                "request_is_consent": False, "wording_is_effect": False})),))


@dataclass(frozen=True)
class LanguageRequest(Record):
    key: str
    actor: ObjectId
    purpose: str
    context: ObjectRef
    cue: ObjectRef
    focus: ObjectRef | None = None
    peer: ObjectId | None = None
    act: str = ""
    body: tuple = ()
    slots: tuple[tuple[str, ObjectRef], ...] = ()
    goal: tuple = ()
    term: str = ""
    practice: ObjectRef | None = None

    def __post_init__(self):
        super().__post_init__()
        if not self.key.strip() or self.purpose not in PURPOSES:
            raise ValueError("named grounded language operation required")
        if len({s for s, _ in self.slots}) != len(self.slots):
            raise ValueError("distinct referential slots required")
        if self.purpose == "send":
            if self.peer is None or self.peer == self.actor or self.act not in ACTS:
                raise ValueError("a distinct listener and supported speech act required")
            if self.act in ("demonstration", "counterexample"):
                if self.focus is None or not self.term or self.body or self.slots or self.goal:
                    raise ValueError("demonstration names an owned actual run and a local term")
            elif not self.body or self.focus is not None or self.term:
                raise ValueError("ordinary speech supplies structured content")
        elif self.focus is None or self.peer is not None or self.act or self.body or self.slots or self.goal:
            raise ValueError("continuing language work uses a received or owned reference")
        if self.term and self.purpose not in ("coin", "send"):
            raise ValueError("only coin or demonstration takes a token")
        if (self.purpose == "settle") != (self.practice is not None):
            raise ValueError("settlement requires an owned observed procedure run")
        if len(self.term) > 80 or any(c.isspace() for c in self.term):
            raise ValueError("one finite lexical token required")


def registry():
    return {**parent_registry(), "LanguageRequest": LanguageRequest}
