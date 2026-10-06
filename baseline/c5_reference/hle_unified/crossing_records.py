"""C3 bounded crossing contracts. Recipes are engineering constructions."""
from dataclasses import dataclass
from types import MappingProxyType
from hle.contracts import Record
from .crux_records import Recipe
from .self_records import registry as parent_registry
from .records import ObjectId, ObjectRef, ObjectVersion, Role, Definition, SourceStatus
from .particulars import DetailAddress
from .operations import address
from .operation_records import WRITER
from .material import attributes

PATHS = {
    "Express": ("I", "IT", ("ni", "te")),
    "Share": ("I", "WE", ("fi",)),
    "Theorize": ("I", "ITS", ("ni",)),
    "Embody": ("IT", "I", ("te", "ni")),
    "Coordinate": ("IT", "WE", ("si",)),
    "Organize": ("IT", "ITS", ("te",)),
    "Identify": ("WE", "I", ("fi",)),
    "Mobilize": ("WE", "IT", ("si",)),
    "Institutionalize": ("WE", "ITS", ("fi", "ni")),
    "Understand": ("ITS", "I", ("ni",)),
    "Apply": ("ITS", "IT", ("te",)),
    "Educate": ("ITS", "WE", ("ni", "fi")),
}
FACES = ("accumulation", "expenditure")

@dataclass(frozen=True)
class CrossingRecipe(Recipe):
    action: str = ""
    main: bool = True

    @property
    def ref(self): return address("c3.recipe", self.key)

def make(key, name, origin, destination, elements, face, action, main=True):
    steps = (("scope:" + action,) if len(elements) == 2 else ()) + ("realize:" + action,)
    return CrossingRecipe(key, name, origin, destination, steps, elements,
        3 if main and destination == "IT" else 0, face, action, main)

recipes = [make(n.lower()+"-"+f+"-v1", n, o, d, es, f, n.lower())
           for n,(o,d,es) in PATHS.items() for f in FACES]
for domain, name in (("personal", "Share"), ("observation", "Coordinate"), ("system", "Educate")):
    o,d,es=PATHS[name]
    recipes.append(make("offer-"+domain+"-v1",name,o,d,es,"expenditure","offer",False))
recipes += [make("reply-v1","Identify","WE","I",("fi",),"accumulation","reply",False),
            make("vote-v1","Identify","WE","I",("fi",),"expenditure","vote",False)]
for kind,o,es in (("personal","I",("ni","ni")),("shared","WE",("fi",)),
                  ("system","ITS",("ni",)),("observation","IT",("te","ni"))):
    names={"personal":"Contemplate","shared":"Identify","system":"Understand","observation":"Embody"}
    recipes.append(make("use-"+kind+"-v1",names[kind],o,"I",es,"expenditure","use",False))
CROSSING_RECIPES=MappingProxyType({r.key:r for r in recipes})

def definition(r):
    return ObjectVersion(r.ref,WRITER,"C3 "+r.name,(Role.DEFINITION,),
        (Definition("Scoped allocation/observation transformations; paid receiver uptake and exact consent.",
            SourceStatus.ENGINEERING,attributes(dict(key=r.key,route=r.name,origin=r.origin,
                destination=r.destination,polarity=r.polarity,steps=",".join(r.steps),
                action=r.action,main=r.main,material_units=r.material_units,
                max_inputs=8,max_participants=2,policy="c3-crossings-v1"))),))

@dataclass(frozen=True)
class CrossingRequest(Record):
    key: str
    actor: ObjectId
    recipe: str
    context: ObjectRef
    cue: ObjectRef
    inputs: tuple[ObjectRef,...]
    evidence: tuple[DetailAddress,...]
    target: ObjectRef
    stock: ObjectRef | None = None
    peer: ObjectId | None = None
    group: ObjectRef | None = None
    demand: int = 4
    elements: tuple[str,...] = ()

    def __post_init__(self):
        super().__post_init__()
        if not self.key.strip() or self.recipe not in CROSSING_RECIPES:
            raise ValueError("supported named crossing required")
        if not 1<=len(self.inputs)<=8 or len(set(self.inputs))!=len(self.inputs):
            raise ValueError("one to eight distinct input revisions required")
        if not self.evidence or len(set(self.evidence))!=len(self.evidence):
            raise ValueError("processed distinct evidence required")
        if type(self.demand) is not int or not 1<=self.demand<=1000:
            raise ValueError("bounded positive demand required")
        r=CROSSING_RECIPES[self.recipe]
        if self.elements and (len(self.elements)!=len(r.elements) or
            tuple(x[0] for x in self.elements)!=tuple(x[0] for x in r.elements)):
            raise ValueError("declared Fold families required")
        if self.peer==self.actor: raise ValueError("distinct peer required")

    @property
    def input(self): return self.inputs[0]

def registry(): return {**parent_registry(),"CrossingRequest":CrossingRequest}
