"""C4 engineered adapters and bounded parent evidence contract."""
from dataclasses import dataclass
from types import MappingProxyType
from hle.contracts import Record
from .crossing_records import registry as parent_registry
from .crux_records import Recipe
from .records import ObjectId, ObjectRef, ObjectVersion, Role, Definition, SourceStatus
from .particulars import DetailAddress
from .operations import address
from .operation_records import WRITER
from .material import attributes


@dataclass(frozen=True)
class CompositionRecipe(Recipe):
    action: str = ""

    @property
    def ref(self): return address("c4.recipe", self.key)


def recipe(key, name, origin, destination, elements, face, action):
    return CompositionRecipe(key, name, origin, destination,
        ("prepare:"+action, "retain:"+action), elements, 0, face, action)


COMPOSITION_RECIPES = MappingProxyType({r.key:r for r in (
    recipe("commune-offer-v1", "Commune", "WE", "WE", ("fi","fi"), "expenditure", "renew"),
    *(recipe("commune-"+f+"-v1", "Commune", "WE", "WE", ("fi","fi"), f, "commune")
      for f in ("accumulation","expenditure")),
    *(recipe("integrate-"+f+"-v1", "Integrate", "ITS", "ITS", ("ni","ni"), f, "integrate")
      for f in ("accumulation","expenditure")),
    recipe("context-transfer-v1", "Integrate", "ITS", "ITS", ("ni","ni"), "accumulation", "context"),
    recipe("parent-v1", "Integrate", "ITS", "ITS", ("ni","ni"), "accumulation", "parent"),
    recipe("release-v1", "Integrate", "ITS", "ITS", ("ni","ni"), "expenditure", "release"),
)})


@dataclass(frozen=True)
class ChildEvidence(Record):
    operation: ObjectRef
    output: ObjectRef


@dataclass(frozen=True)
class CruxCompositionRequest(Record):
    key: str
    actor: ObjectId
    recipe: str
    context: ObjectRef
    cue: ObjectRef
    inputs: tuple[ObjectRef,...]
    evidence: tuple[DetailAddress,...]
    target: ObjectRef
    peer: ObjectId | None = None
    group: ObjectRef | None = None
    demand: int = 4
    children: tuple[ChildEvidence,...] = ()
    links: tuple[tuple[int,int],...] = ()
    elements: tuple[str,...] = ()

    def __post_init__(self):
        super().__post_init__()
        if not self.key.strip() or self.recipe not in COMPOSITION_RECIPES: raise ValueError("named C4 recipe required")
        if not 1<=len(self.inputs)<=8 or len(set(self.inputs))!=len(self.inputs): raise ValueError("bounded distinct inputs required")
        if not self.evidence or len(set(self.evidence))!=len(self.evidence): raise ValueError("processed evidence required")
        if type(self.demand) is not int or not 1<=self.demand<=1000: raise ValueError("bounded demand required")
        if self.peer==self.actor: raise ValueError("distinct peer required")
        r=COMPOSITION_RECIPES[self.recipe]
        if self.elements and (len(self.elements)!=2 or tuple(e[0] for e in self.elements)!=tuple(e[0] for e in r.elements)):
            raise ValueError("paid Fold return required")
        if r.action=="parent":
            if not 1<=len(self.children)<=8 or len({c.operation.identity for c in self.children})!=len(self.children):
                raise ValueError("one to eight distinct child operations required")
            if self.inputs!=tuple(c.output for c in self.children): raise ValueError("each declared child needs its exact output")
            if len(set(self.links))!=len(self.links) or any(not 0<=a<b<len(self.children) for a,b in self.links):
                raise ValueError("ordered acyclic child links required")
        elif self.children or self.links: raise ValueError("child claims belong to a parent contract")

    @property
    def input(self): return self.inputs[0]


def definition(r):
    return ObjectVersion(r.ref, WRITER, "C4 "+r.action, (Role.DEFINITION,),
        (Definition("Explicit scoped composition and constituent evidence; no borrowed competence.",
            SourceStatus.ENGINEERING, attributes(dict(key=r.key, route=r.name, origin=r.origin,
            destination=r.destination, polarity=r.polarity, action=r.action, steps=",".join(r.steps),
            max_inputs=8, max_children=8, max_depth=4, max_operations=64, policy="c4-composition-v1"))),))


def registry():
    return {**parent_registry(), "CruxCompositionRequest":CruxCompositionRequest, "ChildEvidence":ChildEvidence}
