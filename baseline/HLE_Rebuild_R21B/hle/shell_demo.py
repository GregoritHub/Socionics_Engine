"""The unchanged R15 environmental panel with a live, isolated observer."""
from .compensation_demo import world as make_r15, run, introduce, fund_command
from .compensation_records import ReleaseCommand
from .shell_runtime import ShellAssessmentWorld


def case(history=3, renewals=3, gated_history=True, refusal=False, **kwargs):
    seed = make_r15(history=history, renewals=renewals, gated_history=gated_history, **kwargs)
    w = ShellAssessmentWorld(seed.config, seed.profiles, seed.policy, seed.agents,
                seed.organization_policies, seed.semantic_policy, seed.workshop, seed.autonomy,
                release=seed.release, reviewers=seed.reviewers)
    schedule = [run(w)]; cuts = []
    for i in range(history + renewals):
        if refusal and i == history:
            for actor in w.config.actors[1:]:
                key = 'boundary:' + actor.key
                fund_command(w, ReleaseCommand(key, key, actor, 'boundary', willingness=False, work_limit=256))
        cuts.append(len(w._journal)); introduce(w, i); schedule.append(run(w))
    return w, {'history': history, 'renewals': renewals, 'gated_history': gated_history,
               'refusal': refusal, 'cuts': cuts, 'scheduling': schedule}


def signatures(w):
    from .shell_assessment import assess_engagement, reftext
    out = []
    for t in w.shell_monitor.traces:
        row = assess_engagement(t)
        out.append({'engagement': reftext(t.engagement), 'opportunity': row['opportunity'],
                    'placement': row['signs']['forced_placement']['observation'],
                    'events': row['signs']['forced_placement']['events'], 'endpoint': row['endpoint'],
                    'work_units': sum(op.units for op in t.operations), 'oig': row['oig']})
    return out
