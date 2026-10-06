"""C1 versioned content contracts. These are bounded engineering recipes.

The three accumulation cases begin C1; they do not close the 32-cell ledger.
Legacy CognitiveRequest('integrate') still means IT -> I (Embody).
"""
from dataclasses import dataclass
from types import MappingProxyType
from hle.contracts import Record
from .records import ObjectId, ObjectRef, ObjectVersion, Role, Definition, SourceStatus
from .operations import address
from .operation_records import WRITER
from .particulars import DetailAddress
from .material import attributes
from .institution_records import registry as parent_registry


@dataclass(frozen=True)
class Recipe:
    key: str
    name: str
    origin: str
    destination: str
    steps: tuple[str, ...]
    elements: tuple[str, ...]
    material_units: int = 0
    polarity: str = "accumulation"

    @property
    def ref(self):
        return address("c1.recipe", self.key)


RECIPES = MappingProxyType({r.key: r for r in (
    Recipe("condition-hypothesis-v1", "Theorize", "I", "ITS", ("hypothesize",), ("ni",)),
    Recipe("condition-trial-v1", "Apply", "ITS", "IT", ("instantiate",), ("te",), 3),
    Recipe("condition-retention-v1", "Embody", "IT", "I", ("compare", "retain"), ("te", "ni")),
)})


def definition(recipe):
    return ObjectVersion(recipe.ref, WRITER, "C1 " + recipe.name, (Role.DEFINITION,),
        (Definition("Explicit condition model, paid inspection trial, or evidence-based retention.",
            SourceStatus.ENGINEERING, attributes({
                "key": recipe.key, "route": recipe.name, "origin": recipe.origin,
                "destination": recipe.destination, "polarity": recipe.polarity,
                "steps": ",".join(recipe.steps), "material_units": recipe.material_units,
                "scope": "one actor, exact target identity, one context, condition relation",
            })),))


@dataclass(frozen=True)
class MovementRequest(Record):
    key: str
    actor: ObjectId
    recipe: str
    context: ObjectRef
    cue: ObjectRef
    input: ObjectRef
    evidence: tuple[DetailAddress, ...]
    rule: ObjectRef | None = None
    elements: tuple[str, ...] = ()

    def __post_init__(self):
        super().__post_init__()
        if not self.key.strip() or self.recipe not in RECIPES:
            raise ValueError("named movement and supported versioned C1 recipe required")
        if not self.evidence or len(set(self.evidence)) != len(self.evidence):
            raise ValueError("distinct paid actor evidence required")
        if (self.recipe == "condition-hypothesis-v1") != (self.rule is not None):
            raise ValueError("only hypothesis construction takes an explicit policy definition")
        recipe = RECIPES[self.recipe]
        elements = self.elements or recipe.elements
        if (len(elements) != len(recipe.elements)
                or tuple(e[:1] for e in elements) != tuple(e[:1] for e in recipe.elements)):
            raise ValueError("C1 content steps require their declared Fold function families")


def registry():
    return {**parent_registry(), "MovementRequest": MovementRequest}
