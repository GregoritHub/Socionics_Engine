"""C5 explicit situated admission; does not claim autonomous route selection."""
from dataclasses import dataclass
from hle.contracts import Record
from .records import ObjectRef
from .particulars import DetailAddress
from .self_records import SelfRouteRequest
from .crossing_records import CrossingRequest
from .crux_composition_records import CruxCompositionRequest, registry as parent_registry

@dataclass(frozen=True)
class ShellMovementRequest(Record):
    key: str
    movement: SelfRouteRequest | CrossingRequest | CruxCompositionRequest
    carrier: ObjectRef
    bearer: ObjectRef
    evidence: tuple[DetailAddress, ...]
    demand: bool = True
    visit_limit: int = 128
    phase: str = "admission"

    @property
    def actor(self): return self.movement.actor

    def __post_init__(self):
        super().__post_init__()
        if self.phase not in ("admission","after_first_step"): raise ValueError("explicit application phase required")
        if type(self.movement) not in (SelfRouteRequest,CrossingRequest,CruxCompositionRequest):
            raise ValueError('native C2/C3/C4 movement required')
        if not self.key.strip() or self.key==self.movement.key or not self.evidence:
            raise ValueError('distinct admission key and processed opportunity evidence required')
        if type(self.demand) is not bool or type(self.visit_limit) is not int or self.visit_limit<1:
            raise ValueError('explicit demand and positive recall budget required')

def registry(): return {**parent_registry(), 'ShellMovementRequest':ShellMovementRequest}
