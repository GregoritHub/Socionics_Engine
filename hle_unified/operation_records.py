"""U4 requests and finite workshop contract. All numerical rules are engineering choices."""
from dataclasses import dataclass
from hle.contracts import Record
from .records import ObjectId, ObjectRef, text_required
from .particulars import DetailAddress, record_registry

WRITER = "u4.native"
LAW = "u4.finite-workshop-v1"
# One prepare quantum followed by this many content/physical quanta.
EXTENTS = {"transfer": 2, "inspect": 2, "use": 2, "care": 3,
           "return": 2, "damage": 2, "repair": 5, "consume": 2,
           "read": 1, "bind": 2, "acquire": 2}
MATERIAL_OPS = frozenset(EXTENTS) - {"read", "bind", "acquire"}
SIGNATURES = {"transfer": ("target", "recipient"), "inspect": ("target",),
              "use": ("target",), "care": ("target", "stock"),
              "return": ("target", "relation"), "damage": ("target",),
              "repair": ("target", "tool", "stock"), "consume": ("stock",)}


@dataclass(frozen=True)
class OperationRequest(Record):
    key: str
    actor: ObjectId
    kind: str
    context: ObjectRef
    participants: tuple[ObjectId, ...] = ()
    evidence: tuple[DetailAddress, ...] = ()
    target: ObjectRef | None = None
    tool: ObjectRef | None = None
    stock: ObjectRef | None = None
    recipient: ObjectId | None = None
    relation: ObjectRef | None = None
    procedure: ObjectRef | None = None
    amount: int = 1
    delivery: str = ""
    binding: ObjectRef | None = None
    practice: ObjectRef | None = None

    def __post_init__(self):
        super().__post_init__()
        text_required(self.key)
        if self.kind not in EXTENTS and self.kind != "procedure":
            raise ValueError("unsupported operation")
        if self.amount < 1:
            raise ValueError("positive integer material amount required")
        if len(set(self.participants)) != len(self.participants) or len(set(self.evidence)) != len(self.evidence):
            raise ValueError("duplicate participant or accessible evidence")


def registry():
    return {**record_registry(), "OperationRequest": OperationRequest}
