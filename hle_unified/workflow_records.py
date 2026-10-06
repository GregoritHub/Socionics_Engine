"""C7 second setting: timed maintenance/handover procedures (engineering v1).

This is an additional finite content language on the native Crux executor.
It changes no formal route, polarity, Model A geometry or old recipe.
"""
from dataclasses import dataclass
from types import MappingProxyType
from hle.contracts import Record
from .crux_records import Recipe
from .crossing_records import PATHS, FACES
from .selection_records import registry as parent_registry
from .records import ObjectId, ObjectRef, ObjectVersion, Role, Definition, SourceStatus
from .particulars import DetailAddress
from .operations import address
from .operation_records import WRITER
from .material import attributes

PATHS = {**PATHS, "Contemplate": ("I", "I", ("ni", "ni")),
    "Act": ("IT", "IT", ("te", "te")), "Commune": ("WE", "WE", ("fi", "fi")),
    "Integrate": ("ITS", "ITS", ("ni", "ni"))}

@dataclass(frozen=True)
class WorkflowRecipe(Recipe):
    action: str = ""
    main: bool = True
    @property
    def ref(self): return address("c7w.recipe", self.key)

def make(key, name, origin, dest, elements, face, action, main=True):
    material = (3 if face == "accumulation" or name == "Act" else 4) if main and dest == "IT" else 0
    steps = (("resolve:" + action,) if len(elements) == 2 else ()) + ("retain:" + action,)
    return WorkflowRecipe(key, name, origin, dest, steps, elements, material, face, action, main)

_recipes = [make("workflow-"+n.lower()+"-"+f+"-v1", n, o, d, es, f, n.lower())
    for n, (o,d,es) in PATHS.items() for f in FACES]
for domain, name in (("personal", "Share"), ("activity", "Coordinate"), ("system", "Educate"), ("shared", "Commune")):
    o,d,es=PATHS[name]
    _recipes.append(make("workflow-offer-"+domain+"-v1",name,o,d,es,"expenditure","offer",False))
_recipes += [make("workflow-reply-v1","Identify","WE","I",("fi",),"accumulation","reply",False),
    make("workflow-vote-v1","Identify","WE","I",("fi",),"expenditure","vote",False)]
for domain,name,origin,elements in (("personal","Contemplate","I",("ni","ni")),
        ("activity","Embody","IT",("te","ni")),("shared","Identify","WE",("fi",)),("system","Understand","ITS",("ni",))):
    _recipes.append(make("workflow-use-"+domain+"-v1",name,origin,"I",elements,"expenditure","use",False))
WORKFLOW_RECIPES=MappingProxyType({r.key:r for r in _recipes})

def definition(r):
    return ObjectVersion(r.ref,WRITER,"Timed workflow "+r.name,(Role.DEFINITION,),
        (Definition("Bounded task precedence, time windows, individual assent and exact exchange; no skill from teaching.",
            SourceStatus.ENGINEERING,attributes(dict(key=r.key,route=r.name,origin=r.origin,destination=r.destination,
                polarity=r.polarity,steps=",".join(r.steps),action=r.action,main=r.main,
                material_units=r.material_units,max_tasks=8,max_inputs=8,max_participants=2,
                slot_duration=1,policy="c7-workflow-v1"))),))

@dataclass(frozen=True)
class WorkflowRequest(Record):
    key: str
    actor: ObjectId
    recipe: str
    context: ObjectRef
    cue: ObjectRef
    inputs: tuple[ObjectRef,...]
    evidence: tuple[DetailAddress,...]
    target: ObjectRef
    stock: ObjectRef | None = None
    relation: ObjectRef | None = None
    peer: ObjectId | None = None
    group: ObjectRef | None = None
    completed: tuple[str,...] = ()
    clock: int = 0
    elements: tuple[str,...] = ()
    def __post_init__(self):
        super().__post_init__()
        if not self.key.strip() or self.recipe not in WORKFLOW_RECIPES: raise ValueError("named workflow recipe required")
        if not 1<=len(self.inputs)<=8 or len(set(self.inputs))!=len(self.inputs): raise ValueError("distinct bounded inputs required")
        if not self.evidence or len(set(self.evidence))!=len(self.evidence): raise ValueError("distinct paid evidence required")
        if not 0<=self.clock<=1000 or len(self.completed)>8 or len(set(self.completed))!=len(self.completed): raise ValueError("bounded hypothetical query required")
        recipe=WORKFLOW_RECIPES[self.recipe]
        if recipe.material_units and (self.completed or self.clock): raise ValueError("a hypothetical query cannot skip physical prerequisites")
        if self.elements and (len(self.elements)!=len(recipe.elements) or tuple(e[0] for e in self.elements)!=tuple(e[0] for e in recipe.elements)):
            raise ValueError("fixed Fold families required")
        if self.peer==self.actor: raise ValueError("distinct peer required")
    @property
    def input(self): return self.inputs[0]

def registry(): return {**parent_registry(),"WorkflowRequest":WorkflowRequest}
