"""Workflow active interruption; admission-only requests remain unchanged."""
from dataclasses import dataclass
from hle.contracts import Record
from .records import ObjectRef
from .particulars import DetailAddress
from .workflow_records import WorkflowRequest, WORKFLOW_RECIPES
from .workflow_shell_records import registry as parent_registry

@dataclass(frozen=True)
class WorkflowInterruptionRequest(Record):
    key: str
    movement: WorkflowRequest
    carrier: ObjectRef
    bearer: ObjectRef
    evidence: tuple[DetailAddress, ...]
    demand: bool = True
    visit_limit: int = 128
    phase: str = 'after_first_step'

    @property
    def actor(self): return self.movement.actor

    def __post_init__(self):
        super().__post_init__()
        if type(self.movement) is not WorkflowRequest or not WORKFLOW_RECIPES[self.movement.recipe].main:
            raise ValueError('one of the 32 native workflow movements required')
        if not self.key.strip() or self.key==self.movement.key or not self.evidence:
            raise ValueError('distinct admission key and paid opportunity evidence required')
        if self.phase!='after_first_step': raise ValueError('workflow first-step interruption phase required')
        if type(self.demand) is not bool or type(self.visit_limit) is not int or self.visit_limit<1:
            raise ValueError('explicit demand and positive recall bound required')

def registry(): return {**parent_registry(), 'WorkflowInterruptionRequest':WorkflowInterruptionRequest}
