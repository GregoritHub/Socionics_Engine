"""Prospective C7 workflow outcome demand; no route instruction in requests."""
from dataclasses import dataclass
from hle.contracts import Record
from .records import ObjectId, ObjectRef
from .workflow_records import registry as parent_registry
from .selection_records import fields_of, dumps, loads

@dataclass(frozen=True)
class WorkflowSelectionRequest(Record):
    key: str
    actor: ObjectId
    context: ObjectRef
    cue: ObjectRef
    target: ObjectRef
    demand: ObjectRef
    accessible: tuple[ObjectRef, ...]
    stock: ObjectRef | None = None
    relation: ObjectRef | None = None
    peer: ObjectId | None = None
    group: ObjectRef | None = None
    alternatives: int = 64

    def __post_init__(self):
        super().__post_init__()
        if not self.key.strip() or not 1 <= len(self.accessible) <= 8 or len(set(self.accessible)) != len(self.accessible):
            raise ValueError('named selection and one to eight distinct accessible references required')
        if type(self.alternatives) is not int or not 1 <= self.alternatives <= 64 or self.peer == self.actor:
            raise ValueError('bounded alternatives and distinct peer required')

def demand_value(d):
    if set(d) != {'kind', 'priorities', 'externalize'} or d['kind'] != 'workflow_need':
        raise ValueError('outcome demand cannot carry a route or recipe')
    if (type(d['priorities']) is not tuple or len(d['priorities']) != 4
        or any(type(x) is not int or not 0 <= x <= 10 for x in d['priorities'])
        or not any(d['priorities']) or type(d['externalize']) is not bool):
        raise ValueError('four integer outcome priorities and externalization preference required')
    return d

def registry():
    return {**parent_registry(), 'WorkflowSelectionRequest': WorkflowSelectionRequest}
