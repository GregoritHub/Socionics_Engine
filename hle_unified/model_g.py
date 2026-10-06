"""Read-only CT §6 structure over the sealed Model A carrier.

Positions accepted by grade/partners/sign are Model A positions. ``describe``
accepts a Model G position. Names are source transcriptions, not an equivalence
of the two theories or a pricing/selection rule. Internal spine remains open.
"""
from hle import model_a

_G_TO_A = (1, 8, 3, 6, 2, 5, 4, 7)
_NAMES = ('Leading', 'Creative', 'Role-playing', 'Launching', 'Demonstrative',
          'Manipulative', 'Braking', 'Controlling')
_BLOCKS = ('Social mission', 'Social adaptation', 'Creative self-realization',
           'Inflation')
_GRADES = ('pessimum', 'minimum', 'optimum', 'maximum')


def g_to_a(g_position):
    model_a.position(g_position)
    return _G_TO_A[g_position - 1]


def a_to_g(a_position):
    model_a.position(a_position)
    return _G_TO_A.index(a_position) + 1


def grade(a_position):
    a, v, r = model_a.position(a_position)
    return 2 * (1 ^ v ^ (a & r)) + (1 ^ r)


def block_partner(a_position):
    a, v, r = model_a.position(a_position)
    return model_a.BY_POSITION[(1 ^ a, 1 ^ a ^ v ^ r, 1 ^ r)]


def grade_partner(a_position):
    a, v, r = model_a.position(a_position)
    return model_a.BY_POSITION[(1 ^ a, v ^ r, r)]


def label(tim):
    return 'positivist' if model_a.character((1, 1, 1, 0), tim) else 'negativist'


def sign(tim, a_position):
    _, _, r = model_a.position(a_position)
    return '+' if bool(model_a.character((1, 1, 1, 0), tim)) != bool(r) else '-'


def describe(tim, g_position):
    """Return fresh derived attributes; never reads or writes a participant."""
    p = g_to_a(g_position)
    f = model_a.fields(p)
    return dict(type=tim, g_position=g_position, a_position=p,
                element=model_a.element_at(tim, p), name=_NAMES[g_position - 1],
                block=_BLOCKS[(g_position - 1) // 2],
                leading_driven='leading' if f['strong'] else 'driven',
                stable_unstable='stable' if f['accepting'] else 'unstable',
                external_internal='external' if f['bold'] else 'internal',
                grade=grade(p), grade_name=_GRADES[grade(p)],
                sign=sign(tim, p), label=label(tim),
                block_partner_a=block_partner(p), grade_partner_a=grade_partner(p))


def spine(tim):
    """Only the two source-directed links; no inferred internal-plane dynamics."""
    return tuple((p, model_a.element_at(tim, p)) for p in (6, 1, 8))
