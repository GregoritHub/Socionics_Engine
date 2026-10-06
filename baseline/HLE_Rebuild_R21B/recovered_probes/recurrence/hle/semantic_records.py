"""R11 explicit local processing hypotheses and cancellation contract."""
from dataclasses import dataclass
from .contracts import Record, Ref
from .crux import FormalMovement
from .metabolism_records import RoutePlan
from .memory_records import text


@dataclass(frozen=True)
class SemanticPolicy(Record):
    # Fixed session control, not a participant choice to avoid payment.
    enabled: bool = True


@dataclass(frozen=True)
class SemanticRoute(Record):
    family: str
    operation: str
    start_state: Ref
    movement: FormalMovement
    extent: int
    plan: RoutePlan | None


@dataclass(frozen=True)
class CancelSemantic(Record):
    command_id: str
    task_id: str
    actor: Ref
    family: str
    reason: str

    def __post_init__(self):
        super().__post_init__()
        text(self.command_id); text(self.task_id); text(self.reason)
        if self.family not in ('language', 'organization'):
            raise ValueError('known semantic family required')
