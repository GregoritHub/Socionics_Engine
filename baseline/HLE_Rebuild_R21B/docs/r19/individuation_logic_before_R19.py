"""Finite task semantics. No world, type, relation, complex or evaluator inputs."""
from .individuation_records import ASPECTS

def constraints(offer, option, permissions, acknowledgments):
    claims = {}
    for key,value in option.claims: claims.setdefault(key,set()).add(value)
    return {
        'ne': option.available,
        'si': option.condition=='clean' and option.observed_epoch==offer.epoch,
        'ni': option.start>=option.ready_at and option.start+option.duration<=offer.due,
        'se': option.load<=offer.budget,
        'te': option.cost<=offer.credits and option.output>=offer.minimum_output,
        'ti': all(len(values)==1 for values in claims.values()),
        'fi': permissions.get(option.key,False),
        'fe': acknowledgments.get(option.key,False),
    }

def select(offer, menu, guards):
    """A guard changes admissibility; an absent guard leaves the old assumption.

    Prefer lower cost then earlier finish, preserving offered order on ties.
    This rule never reads a hidden current capacity or a desired answer key.
    """
    found=[]
    for i,o in enumerate(offer.options):
        c=constraints(offer,o,dict(menu.permissions),dict(menu.acknowledgments))
        if all(c[a] for a in guards): found.append((o.cost,o.start+o.duration,i,o))
    return min(found,key=lambda x:x[:3])[-1].key if found else None

def infer(offer, menu, signal):
    """Eliminate unconditional feasibility only from an observed failure.

    Failure names are concrete work-order constraints, not developmental or
    correctness labels supplied by an external evaluator.
    """
    if signal.success: return ()
    option=next((x for x in offer.options if x.key==signal.option),None)
    if option is None: return ()
    visible=constraints(offer,option,dict(menu.permissions),dict(menu.acknowledgments))
    return tuple(a for a in ASPECTS if a in signal.errors and not visible[a])
