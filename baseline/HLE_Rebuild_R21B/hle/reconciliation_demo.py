"""Same R15 physical histories with an additional paid release-account policy."""
from .compensation_demo import world as parent_world, introduce, run
from .reconciliation import ReconciliationWorld
from .reconciliation_records import ReconciliationPolicy


def world(**kwargs):
    policy = kwargs.pop('account_policy',None)
    b = parent_world(**kwargs)
    return ReconciliationWorld(b.config,b.profiles,b.policy,b.agents,b.organization_policies,b.semantic_policy,
           b.workshop,b.autonomy,release=b.release,reviewers=b.reviewers,account_policy=policy)


def case(history=3,renewals=3,**kwargs):
    w = world(history=history,renewals=renewals,**kwargs)
    schedules = [run(w)]; cuts = []
    for i in range(history+renewals):
        cuts.append(len(w._journal)); introduce(w,i); schedules.append(run(w))
    return w, {'history':history,'renewals':renewals,'cuts':cuts,'scheduling':schedules}
