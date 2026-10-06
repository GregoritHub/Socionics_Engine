"""Pure participant choices over detached owned summaries, never simulator Truth.

All selection laws here are implementation choices, not derived Socionics laws.
The supplied combinators are current-holder responsibility and cyclic allocation.
The participant elects an experienced guarded action sequence and its cohort.
"""
from .language import fingerprint
from .language_records import Pattern


def action_cost(steps): return sum(1 if s == 'inspect' else 2 for s in steps)


def select(practices, policy, lexicon, prior=None, blocked_steps=()):
    candidates=[]
    for p in practices:
        if p.successes < policy.minimum_support or p.successes - 2*p.failures <= 0:
            continue
        if action_cost(p.steps) > policy.max_action_cost: continue
        lex=lexicon.get(p.meaning.token)
        if lex is None or fingerprint(lex.meaning) != fingerprint(p.meaning): continue
        if p.meaning.patterns != (Pattern(0,1),) or p.meaning.arity != 2: continue
        if prior is not None:
            if p.item != prior.terms.item: continue
            if p.steps in blocked_steps:
                # A dispute is not cleared by renaming the same failed procedure.
                continue
        candidates.append(p)
    if not candidates: return None
    return min(candidates,key=lambda p:(-(p.successes-2*p.failures),action_cost(p.steps),
        p.item.key,p.item.revision,p.steps,p.meaning.token))
