"""Model A frames, type coordinates and transported adjacency (M02--M06).

These are conditional structural results, not psychological transition laws.
No numeric cost, learning rule, capacity bound, or preferred path is selected.
"""
from types import MappingProxyType
from .gf2 import Affine, add, dot, vectors

POSITION = MappingProxyType({p: ((p - 1) & 1, ((p - 1) >> 1) & 1,
                                 ((p - 1) >> 2) & 1) for p in range(1, 9)})
BY_POSITION = MappingProxyType({v: p for p, v in POSITION.items()})
ELEMENT = MappingProxyType({
    "si": (0, 0, 0), "ni": (0, 0, 1), "se": (0, 1, 0), "ne": (0, 1, 1),
    "ti": (1, 0, 0), "fi": (1, 0, 1), "te": (1, 1, 0), "fe": (1, 1, 1),
})
BY_ELEMENT = MappingProxyType({v: e for e, v in ELEMENT.items()})
# Named anchors preserved from 5.2.1 pyref/core.py. M03 records this provenance.
EGO = MappingProxyType({
    "iee": ("ne", "fi"), "ile": ("ne", "ti"), "sle": ("se", "ti"),
    "see": ("se", "fi"), "iei": ("ni", "fe"), "ili": ("ni", "te"),
    "sli": ("si", "te"), "sei": ("si", "fe"), "eie": ("fe", "ni"),
    "ese": ("fe", "si"), "lse": ("te", "si"), "lie": ("te", "ni"),
    "eii": ("fi", "ne"), "esi": ("fi", "se"), "lsi": ("ti", "se"),
    "lii": ("ti", "ne"),
})
TYPES = tuple(sorted(EGO))
REININ = MappingProxyType({
    (1,0,0,0): "extraverted/introverted", (0,1,0,0): "intuitive/sensing",
    (0,0,1,0): "logical/ethical", (0,0,0,1): "irrational/rational",
    (1,1,0,0): "carefree/farsighted", (1,0,1,0): "yielding/obstinate",
    (1,0,0,1): "static/dynamic", (0,1,1,0): "democratic/aristocratic",
    (0,1,0,1): "tactical/strategic", (0,0,1,1): "constructivist/emotivist",
    (1,1,1,0): "positivist/negativist", (1,1,0,1): "judicious/decisive",
    (1,0,1,1): "subjectivist/objectivist", (0,1,1,1): "process/result",
    (1,1,1,1): "asking/declaring",
})


def position(p: int) -> tuple[int, int, int]:
    if type(p) is not int or p not in POSITION:
        raise ValueError("position must be an integer 1..8")
    return POSITION[p]


def element(e: str) -> tuple[int, int, int]:
    if type(e) is not str or e not in ELEMENT:
        raise ValueError("unknown information element")
    return ELEMENT[e]


def ego(tim: str) -> tuple[str, str]:
    if type(tim) is not str or tim not in EGO:
        raise ValueError("unknown type")
    return EGO[tim]


def frame(tim: str) -> Affine:
    lead, creative = ego(tim)
    origin = element(lead)
    t = add(origin, element(creative))
    # UMA §4: columns t, S, S+O; S=(0,0,1), O=(0,1,0).
    return Affine(tuple(zip(t, (0,0,1), (0,1,1))), origin)


def stack(tim: str) -> tuple[str, ...]:
    f = frame(tim)
    return tuple(BY_ELEMENT[f(POSITION[p])] for p in range(1, 9))


def element_at(tim: str, p: int) -> str:
    return BY_ELEMENT[frame(tim)(position(p))]


def position_of(tim: str, e: str) -> int:
    return BY_POSITION[frame(tim).inverse()(element(e))]


def fields(p: int) -> dict[str, int | bool | str]:
    a, v, r = position(p)
    strong, bold = int(v == r), 1 ^ a ^ r
    return {"accepting": a == 0, "valued": v == 0,
            "ring": "mental" if r == 0 else "vital",
            "strong": bool(strong), "contact": bool(a ^ v ^ r),
            "bold": bool(bold), "dimensionality": 1 + 2 * strong + bold}


def neighbors(tim: str, e: str) -> tuple[str, ...]:
    f = frame(tim)
    p = f.inverse()(element(e))
    return tuple(sorted(BY_ELEMENT[f(add(p, axis))]
                        for axis in ((1,0,0), (0,1,0), (0,0,1))))


def distance(tim: str, a: str, b: str) -> int:
    f = frame(tim).inverse()
    return sum(add(f(element(a)), f(element(b))))


def shortest_paths(tim: str, a: str, b: str) -> tuple[tuple[str, ...], ...]:
    n = distance(tim, a, b)
    paths = ((a,),)
    for _ in range(n):
        paths = tuple(path + (nxt,) for path in paths for nxt in neighbors(tim, path[-1])
                      if distance(tim, nxt, b) == distance(tim, path[-1], b) - 1)
    return paths


def jungian(tim: str) -> tuple[int, int, int, int]:
    lead, creative = (element(e) for e in ego(tim))
    irrational, rational = (lead, creative) if lead[0] == 0 else (creative, lead)
    return lead[1], irrational[2], 1 ^ rational[2], 1 ^ lead[0]


def character(w: tuple[int, ...], tim: str) -> int:
    if w not in REININ:
        raise ValueError("expected a nonzero four-bit Reinin character")
    return dot(w, jungian(tim))


def club(tim: str) -> str:
    _, n, t, _ = jungian(tim)
    return ("N" if n else "S") + ("T" if t else "F")
