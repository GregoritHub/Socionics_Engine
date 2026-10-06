"""C2 finite content language and paid self-route recipes (engineering v1)."""
from dataclasses import dataclass
from types import MappingProxyType
from hle.contracts import Record
from .records import ObjectId, ObjectRef, ObjectVersion, Role, Definition, SourceStatus
from .particulars import DetailAddress
from .operations import address
from .operation_records import WRITER
from .material import attributes
from .crux_records import Recipe, registry as parent_registry


@dataclass(frozen=True)
class SelfRecipe(Recipe):
    @property
    def ref(self):
        return address("c2.recipe", self.key)


def cell(name, quadrant, element, polarity, steps, material=0):
    return SelfRecipe(name.lower()+"-"+polarity+"-v1", name, quadrant, quadrant,
                      steps, (element, element), material, polarity)


SELF_RECIPES = MappingProxyType({r.key:r for r in (
    cell("Contemplate", "I", "ni", "accumulation", ("differentiate", "retain_meaning")),
    cell("Contemplate", "I", "ni", "expenditure", ("rehearse", "retain_policy")),
    cell("Act", "IT", "te", "accumulation", ("prepare_repair", "material_command"), 6),
    cell("Act", "IT", "te", "expenditure", ("prepare_use", "material_command"), 3),
    cell("Commune", "WE", "fi", "accumulation", ("clarify", "shared_meaning")),
    cell("Commune", "WE", "fi", "expenditure", ("acknowledge", "shared_commitment")),
    cell("Integrate", "ITS", "ni", "accumulation", ("reconcile", "retain_system")),
    cell("Integrate", "ITS", "ni", "expenditure", ("interfaces", "couple_system")),
    SelfRecipe("exchange-offer-v1", "Offer", "I", "WE", ("offer",), ("fi",), 0, "expenditure"),
    SelfRecipe("exchange-reply-v1", "Reply", "WE", "WE", ("read_offer", "reply"), ("fi","fi"), 0, "expenditure"),
    SelfRecipe("content-use-v1", "Consume", "I", "IT", ("evaluate", "decide"), ("ni","te"), 0, "expenditure"),
)})
SELF_NAMES = frozenset(("Contemplate", "Act", "Commune", "Integrate"))


def definition(r):
    return ObjectVersion(r.ref, WRITER, "C2 "+r.name, (Role.DEFINITION,),
        (Definition("Finite paid content work; self-routes use explicit Fold return paths.",
            SourceStatus.ENGINEERING, attributes(dict(key=r.key, route=r.name,
                origin=r.origin, destination=r.destination, polarity=r.polarity,
                steps=",".join(r.steps), material_units=r.material_units,
                policy="c2-paid-return-v1", max_nodes=16, max_participants=2))),))


@dataclass(frozen=True)
class SelfRouteRequest(Record):
    key: str
    actor: ObjectId
    recipe: str
    context: ObjectRef
    cue: ObjectRef
    inputs: tuple[ObjectRef, ...]
    evidence: tuple[DetailAddress, ...]
    target: ObjectRef
    tool: ObjectRef | None = None
    stock: ObjectRef | None = None
    peer: ObjectId | None = None
    group: ObjectRef | None = None
    demand: int = 1
    elements: tuple[str, ...] = ()

    def __post_init__(self):
        super().__post_init__()
        if not self.key.strip() or self.recipe not in SELF_RECIPES:
            raise ValueError("named supported C2 recipe required")
        if not self.inputs or len(set(self.inputs)) != len(self.inputs) or len(self.inputs)>16:
            raise ValueError("one to sixteen distinct exact inputs required")
        if not self.evidence or len(set(self.evidence)) != len(self.evidence):
            raise ValueError("distinct processed evidence required")
        if type(self.demand) is not int or not 1<=self.demand<=1000:
            raise ValueError("bounded positive demand required")
        r=SELF_RECIPES[self.recipe]
        if self.elements and (len(self.elements)!=len(r.elements)
                or tuple(e[0] for e in self.elements)!=tuple(e[0] for e in r.elements)):
            raise ValueError("declared Fold families required; no empty processing path")
        if self.peer == self.actor:
            raise ValueError("reciprocity requires a distinct participant")

    @property
    def input(self):
        return self.inputs[0]


def registry():
    return {**parent_registry(), "SelfRouteRequest":SelfRouteRequest}
