"""FB4.2 bounded accountability for exact workflow child operations."""
from dataclasses import dataclass
from hle.contracts import Record
from .crux_records import Recipe
from .workflow_records import registry as parent_registry
from .records import ObjectId, ObjectRef, ObjectVersion, Role, Definition, SourceStatus
from .particulars import DetailAddress
from .operations import address
from .operation_records import WRITER
from .material import attributes


@dataclass(frozen=True)
class WorkflowParentRecipe(Recipe):
    action: str = "parent"
    @property
    def ref(self): return address("c7n.recipe", self.key)


PARENT_RECIPE = WorkflowParentRecipe(
    "workflow-parent-v1", "Integrate", "ITS", "ITS",
    ("review:children", "retain:parent"), ("ni", "ni"), 0,
    "accumulation", "parent")


@dataclass(frozen=True)
class WorkflowChildEvidence(Record):
    operation: ObjectRef
    output: ObjectRef


@dataclass(frozen=True)
class WorkflowParentRequest(Record):
    key: str
    actor: ObjectId
    recipe: str
    context: ObjectRef
    cue: ObjectRef
    children: tuple[WorkflowChildEvidence, ...]
    evidence: tuple[DetailAddress, ...]
    target: ObjectRef
    links: tuple[tuple[int, int], ...] = ()
    group: ObjectRef | None = None
    elements: tuple[str, ...] = ()

    def __post_init__(self):
        super().__post_init__()
        if not self.key.strip() or self.recipe != PARENT_RECIPE.key:
            raise ValueError("named workflow parent recipe required")
        if not 1 <= len(self.children) <= 8 or len({c.operation.identity for c in self.children}) != len(self.children):
            raise ValueError("one to eight distinct child operations required")
        if len({c.output for c in self.children}) != len(self.children):
            raise ValueError("distinct exact child outputs required")
        if not self.evidence or len(set(self.evidence)) != len(self.evidence):
            raise ValueError("distinct paid evidence required")
        if len(set(self.links)) != len(self.links) or any(not 0 <= a < b < len(self.children) for a, b in self.links):
            raise ValueError("ordered acyclic child links required")
        if self.elements and (len(self.elements) != 2 or tuple(x[0] for x in self.elements) != ("n", "n")):
            raise ValueError("paid Integrate Fold return required")

    @property
    def inputs(self): return tuple(c.output for c in self.children)
    @property
    def input(self): return self.children[0].output


def definition():
    r = PARENT_RECIPE
    return ObjectVersion(r.ref, WRITER, "C7 bounded workflow parent", (Role.DEFINITION,),
        (Definition("Exact same-owner workflow child evidence; no competence or authority from summary.",
            SourceStatus.ENGINEERING, attributes(dict(key=r.key, route=r.name, origin=r.origin,
            destination=r.destination, polarity=r.polarity, action=r.action, steps=",".join(r.steps),
            max_children=8, max_depth=4, max_operations=64, policy="c7-workflow-parent-v1"))),))


def registry():
    return {**parent_registry(), "WorkflowParentRequest": WorkflowParentRequest,
            "WorkflowChildEvidence": WorkflowChildEvidence}
