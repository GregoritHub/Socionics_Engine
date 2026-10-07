"""C6 engineering contract: goals describe desired effects, never route names."""
from dataclasses import dataclass, fields
import json
from .records import ObjectId, ObjectRef
from hle.contracts import Record
from . import codec
from .crux_shell_records import registry as parent_registry

DIMENSIONS=('personal','material','shared','system')
NAMES=('Contemplate','Express','Share','Theorize','Embody','Act','Coordinate','Organize','Identify','Mobilize','Commune','Institutionalize','Understand','Apply','Educate','Integrate')
PERSPECTIVES=('I','IT','WE','ITS')
FACES=('accumulation','expenditure')

@dataclass(frozen=True)
class SelectionRequest(Record):
    key: str
    actor: ObjectId
    context: ObjectRef
    cue: ObjectRef
    target: ObjectRef
    demand: ObjectRef
    stock: ObjectRef | None = None
    tool: ObjectRef | None = None
    repair_stock: ObjectRef | None = None
    procedure: ObjectRef | None = None
    peer: ObjectId | None = None
    group: ObjectRef | None = None
    limit: int = 128
    alternatives: int = 64
    def __post_init__(self):
        super().__post_init__()
        if not self.key.strip() or type(self.limit) is not int or not 1<=self.limit<=128:
            raise ValueError('named bounded selection required')
        if type(self.alternatives) is not int or not 1<=self.alternatives<=64:
            raise ValueError('one to 64 evaluated bundles per cell')
        if self.peer==self.actor: raise ValueError('distinct peer')

def registry(): return {**parent_registry(),'SelectionRequest':SelectionRequest}
def fields_of(r): return {f.name:getattr(r,f.name) for f in fields(r)}

def dumps(value):
    def enc(x):
        if type(x) in (ObjectRef,ObjectId): return {'$ref':codec.encode(x)}
        if type(x) is tuple: return {'$tuple':[enc(a) for a in x]}
        if type(x) is list: return [enc(a) for a in x]
        if type(x) is dict: return {k:enc(v) for k,v in x.items()}
        if x is None or type(x) in (str,int,bool): return x
        raise ValueError('unsupported C6 audit value '+str(type(x)))
    return json.dumps(enc(value),sort_keys=True,separators=(',',':'))

def loads(text):
    def dec(x):
        if type(x) is dict:
            if set(x)=={'$ref'}: return codec.decode(x['$ref'])
            if set(x)=={'$tuple'}: return tuple(dec(a) for a in x['$tuple'])
            return {k:dec(v) for k,v in x.items()}
        if type(x) is list: return [dec(a) for a in x]
        return x
    return dec(json.loads(text))

def demand_value(d):
    if set(d)!={'kind','weights','commit','scope','amount','collective'} or d['kind']!='need':
        raise ValueError('owned outcome demand required; route instructions are not accepted')
    if len(d['weights'])!=4 or any(type(n) is not int or not 0<=n<=10 for n in d['weights']) or not any(d['weights']):
        raise ValueError('four bounded outcome priorities required')
    if type(d['collective']) is not bool or type(d['commit']) is not bool or d['scope'] not in ('condition','quantity') or type(d['amount']) is not int or not 1<=d['amount']<=1000:
        raise ValueError('explicit urgency, material scope and amount required')
    return d
