"""Formal route grammar (C01--C04), with no realized content operators.

A route inverse is an endpoint operation: it does not undo world effects,
recover discarded content, refund work, or establish an IDEA return.
"""
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType


class Perspective(str, Enum):
    I = "I"
    IT = "IT"
    WE = "WE"
    ITS = "ITS"


class Polarity(str, Enum):
    ACCUMULATION = "accumulation"
    EXPENDITURE = "expenditure"


CODE = MappingProxyType({Perspective.I: 0, Perspective.IT: 1,
                         Perspective.WE: 2, Perspective.ITS: 3})
# Source convention, Crux v6 §5. Rows are origins, columns destinations.
_ROWS = (("Contemplate", "Express", "Share", "Theorize"),
         ("Embody", "Act", "Coordinate", "Organize"),
         ("Identify", "Mobilize", "Commune", "Institutionalize"),
         ("Understand", "Apply", "Educate", "Integrate"))
ROUTE_NAMES = MappingProxyType({(a, b): _ROWS[CODE[a]][CODE[b]]
                               for a in Perspective for b in Perspective})


@dataclass(frozen=True)
class Route:
    origin: Perspective
    destination: Perspective

    def __post_init__(self):
        if type(self.origin) is not Perspective or type(self.destination) is not Perspective:
            raise ValueError("route endpoints must be Perspective labels")

    @property
    def name(self) -> str:
        return ROUTE_NAMES[self.origin, self.destination]

    @property
    def displacement(self) -> int:
        return CODE[self.origin] ^ CODE[self.destination]

    def then(self, following: "Route") -> "Route":
        """Temporal order: this route, then following (not Affine.compose order)."""
        if type(following) is not Route or self.destination != following.origin:
            raise ValueError("routes are not composable")
        return Route(self.origin, following.destination)

    def inverse(self) -> "Route":
        return Route(self.destination, self.origin)


@dataclass(frozen=True)
class FormalMovement:
    route: Route
    polarity: Polarity

    def __post_init__(self):
        if type(self.route) is not Route or type(self.polarity) is not Polarity:
            raise ValueError("expected a Route and Polarity")

    @property
    def bits(self) -> int:
        return (CODE[self.route.origin] << 3) | (CODE[self.route.destination] << 1) | int(
            self.polarity == Polarity.EXPENDITURE)


def routes() -> tuple[Route, ...]:
    return tuple(Route(a, b) for a in Perspective for b in Perspective)


def movements() -> tuple[FormalMovement, ...]:
    return tuple(FormalMovement(r, p) for r in routes() for p in Polarity)
