"""Read-only Super-Ego axes and exact load/tilt algebra (CT §7).

DCNH cells label element pairs, never participants. No subtype assignment or
conditioning feedback is implemented. Pole parity requires no tied axis.
"""
from collections.abc import Mapping
from hle import model_a

AXES = ((1, 3), (2, 4), (5, 7), (6, 8))
_CELLS = {(1, 1): 'D', (0, 1): 'C', (1, 0): 'N', (0, 0): 'H'}
_FORMULAS = {'D': ('te', 'fe', 'se'), 'C': ('se', 'ne', 'fe'),
             'N': ('ti', 'fi', 'si'), 'H': ('si', 'ni', 'fi')}


def axis_cells(tim):
    """DCNH core pair on each axis, in AXES order, from CT §7.2 bits."""
    q, e, _ = model_a.element(model_a.ego(tim)[0])
    return tuple(_CELLS[(q ^ a, e ^ a ^ r)] for a, r in ((0, 0), (1, 0), (0, 1), (1, 1)))


def formula_positions(tim, cell):
    model_a.ego(tim)
    if type(cell) is not str or cell not in _FORMULAS:
        raise ValueError('DCNH cell must be D, C, N or H')
    return tuple(sorted(model_a.position_of(tim, e) for e in _FORMULAS[cell]))


def formula_plane(tim, cell):
    positions = formula_positions(tim, cell)
    planes = {bool(model_a.fields(p)['bold']) for p in positions}
    if len(planes) != 1:
        raise ValueError('formula does not lie in one plane')
    return 'external' if planes == {True} else 'internal'


def _field(field):
    if not isinstance(field, Mapping) or len(field) != 8 or any(type(k) is not int for k in field) or set(field) != set(range(1, 9)):
        raise ValueError('field must map exactly the eight integer Model A positions')
    if any(type(field[p]) is not int for p in range(1, 9)):
        raise ValueError('field values must be exact integers')
    return field


def load(field):
    field = _field(field)
    return tuple(field[p] + field[q] for p, q in AXES)


def tilt(field):
    field = _field(field)
    return tuple(field[p] - field[q] for p, q in AXES)


def recover(loads, tilts):
    """Inverse over integer fields; reject nonintegral decompositions."""
    loads, tilts = tuple(loads), tuple(tilts)
    if len(loads) != 4 or len(tilts) != 4 or any(type(x) is not int for x in loads + tilts):
        raise ValueError('four integer loads and four integer tilts required')
    out = {}
    for (p, q), total, diff in zip(AXES, loads, tilts):
        if (total + diff) % 2:
            raise ValueError('load and tilt do not reconstruct integer poles')
        out[p], out[q] = (total + diff) // 2, (total - diff) // 2
    return out


def sign_vector(field):
    """Signs of two-valued field tilts; a tied axis is explicitly zero."""
    field = _field(field)
    if len(set(field.values())) != 2:
        raise ValueError('field must have exactly two distinct integer values')
    return tuple((x > 0) - (x < 0) for x in tilt(field))


def parity(field):
    """0 even, 1 odd; parity of pole signs is undefined for any tied axis."""
    signs = sign_vector(field)
    if 0 in signs:
        raise ValueError('pole parity requires opposite values on every axis')
    return sum(x < 0 for x in signs) % 2
