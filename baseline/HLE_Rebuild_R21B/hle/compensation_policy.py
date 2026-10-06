"""Pure local choice: finite alternative enumeration with a paid revision law.

The heuristic minimizes immediate content work, not long-run work or truth error.
Generalizing a co-occurring confirmation into a prerequisite and charging for
reprocessing past supports are explicit experimental assumptions. Neither is a
derived psychological law. Histories, not a defense label, choose the path.
"""
from .compensation_records import ReleaseSelection


def select_release(view, revision_unit):
    if not (view.clean and view.owned and view.due):
        return ReleaseSelection('wait', None, 1, (), 'no currently usable clean, due, owned return opportunity')
    if not view.required and not view.dependency:
        return ReleaseSelection('direct', None, 1, (('direct', 1),), 'current terms and personal relation permit independent release')
    candidates = sorted((c for c in view.carriers if c.actor not in view.refused),
                        key=lambda c: (c.quoted_units, c.actor.key, c.actor.revision))
    # Reconsidering a generalized prerequisite reprocesses its retained support.
    # Accommodation reconstructs the current exception and buys another review.
    revision = 1 + revision_unit * len(view.supports)
    alternatives = [] if view.required else [('reconcile', revision)]
    alternatives.extend(('confirm:' + c.actor.key, 2 + c.quoted_units) for c in candidates)
    if not alternatives:
        return ReleaseSelection('wait', None, 1, (), 'actual required confirmation has no remaining accessible carrier')
    name, cost = min(alternatives, key=lambda row: row[1])
    if name == 'reconcile':
        return ReleaseSelection('reconcile', None, cost, tuple(alternatives),
                                'reprocess owned support and revise the unnecessary prerequisite')
    carrier = next(c for c in candidates if name == 'confirm:' + c.actor.key)
    return ReleaseSelection('confirm', carrier.actor, cost, tuple(alternatives),
                            'lowest immediate work among accessible confirmation and revision alternatives')
