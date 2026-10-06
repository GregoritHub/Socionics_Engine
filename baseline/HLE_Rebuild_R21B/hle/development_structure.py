"""Exact R12 structural checks on R11 coordinates and recovered OIG lenses.

OIG inputs are declared quotient representatives. Mapping arbitrary runtime
content into them is NOT supplied by this module. No Shell detector lives here.
"""
from dataclasses import dataclass
from itertools import product
from types import MappingProxyType

from .contracts import Ref, Kind, _kind
from .crux import Perspective
from .development_contracts import VersionOne, refs, unique
from .gf2 import add
from .model_a import position, BY_POSITION, element_at, TYPES
from .relations import ESTAFETTE

FUNCTION_EDGES = MappingProxyType({
    "f": frozenset((Perspective.I, Perspective.WE)),
    "t": frozenset((Perspective.IT, Perspective.ITS)),
    "n": frozenset((Perspective.I, Perspective.ITS)),
    "s": frozenset((Perspective.IT, Perspective.WE)),
})
PORTAGES = MappingProxyType({"n": (0, 1, 0), "cp": (0, 0, 1), "a": (0, 1, 1)})
QUOTIENTS = tuple(product(("dom", "access", "route", "top"), ("unpaired", "paired", "top")))


def portage(seat, name):
    if name not in PORTAGES:
        raise ValueError("unknown portage")
    return BY_POSITION[add(position(seat), PORTAGES[name])]


def lap(seat):
    return BY_POSITION[ESTAFETTE(position(seat))]


@dataclass(frozen=True)
class LensContent(VersionOne):
    domains: tuple[Perspective, ...]
    foreign: tuple[Ref, ...]
    context: Ref
    projection_contract: Ref

    def __post_init__(self):
        super().__post_init__(); unique(self.domains)
        refs(self.foreign, Kind.MEMORY, Kind.OBSERVATION)
        _kind(self.context, Kind.CONTEXT); _kind(self.projection_contract, Kind.PROTOCOL)


def quotient(tim, content, lens):
    if tim not in TYPES or type(content) is not LensContent or lens not in QUOTIENTS:
        raise ValueError("declared TIM, content and quotient required")
    reach = frozenset(p for p in range(1, 9)
                      if FUNCTION_EDGES[element_at(tim, p)[0]] & frozenset(content.domains))
    d = {"dom": frozenset(content.domains), "access": reach,
         "route": (1 in reach, 2 in reach), "top": None}[lens[0]]
    f = {"unpaired": frozenset(content.foreign), "paired": bool(content.foreign), "top": None}[lens[1]]
    return d, f


def observe_trajectory(tim, path):
    """Bounded offline reference; never called by an ordinary runtime tick.

    R is represented as equality partitions, not every recurrence pair. K is
    a set difference. Identical quiet paths provide no demand information.
    """
    if not path or any(type(c) is not LensContent for c in path):
        raise ValueError("nonempty declared path required")
    if any((c.context, c.projection_contract) != (path[0].context, path[0].projection_contract) for c in path):
        raise ValueError("quotient scope must stay fixed within an observation")
    columns = {q: [quotient(tim, c, q) for c in path] for q in QUOTIENTS}
    visibility = frozenset(q for q, values in columns.items()
                           if any(a != b for a, b in zip(values, values[1:])))
    net = frozenset(q for q, values in columns.items() if values[0] != values[-1])
    recurrence = {}
    for q, values in columns.items():
        groups = {}
        for index, value in enumerate(values):
            groups.setdefault(value, []).append(index)
        recurrence[q] = tuple(tuple(indices) for indices in groups.values())
    return {"V": visibility, "N": net, "K": visibility - net, "R": recurrence}
