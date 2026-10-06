"""Detached finite conductivity and extension selection; no world or evaluator.

The problem is consensual discharge of identified shared obligations, not merely
moving an item. Current methods are exhaustively tested under this stated law.
Membership revision alone does not authorize taking over an inherited debt.
"""
from .closure_records import LOWER

# Programs have explicit effects. Their labels are never effects themselves.
# These are the complete elected lower protocol repertoire, not an assertion
# that arbitrary possible controllers have been exhausted.
PROGRAMS={
    'native':('transfer_one',),
    'repeat_native':('transfer_all',),
    'sequential_transfer':('transfer_all','retain_individual'),
    'relabel':('rename','use_current','perform_duties'),
    'current_cycle':('use_current','perform_duties'),
    'revise_cohort':('revise_membership','use_current','perform_duties'),
    'drop_departed':('discard_old_duties','use_current','perform_duties'),
    'consent_cycle':('agree_exact_duties','retain_shared','perform_duties'),
    'carry_obligations':('link_inherited_duties','agree_exact_duties','reuse_lower','retain_shared','perform_duties'),
}

def simulate(program,required,current,count=3):
    """Execute a finite permission/obligation transition model.

    'agree' is a candidate voluntary agreement, conditional on independent
    acceptance. The real world must subsequently establish every consent and
    perform every duty; this planner cannot declare that those events happened.
    """
    total=max(1,count);physical=0;settled=0;identity=True;retained=False
    linked=required!='carry';authorized=False;lower_used=required!='carry'
    for operation in program:
        if operation=='transfer_one':physical+=1
        elif operation=='transfer_all':physical+=total
        elif operation=='retain_individual':pass
        elif operation=='rename':pass
        elif operation=='revise_membership':
            # A new cohort's own work is allowed; unchanged old obligation
            # identities still need explicit acceptance by their new assignees.
            authorized=False
        elif operation=='discard_old_duties':identity=False
        elif operation=='use_current':
            retained=bool(set(current)&{'consent_cycle','carry_obligations'})
            authorized=retained and (required!='carry' or 'carry_obligations' in current)
            linked|='carry_obligations' in current
            lower_used|='carry_obligations' in current
        elif operation=='link_inherited_duties':linked=True
        elif operation=='reuse_lower':lower_used='consent_cycle' in current or 'carry_obligations' in current
        elif operation=='agree_exact_duties':authorized=linked
        elif operation=='retain_shared':retained=authorized
        elif operation=='perform_duties':
            if authorized and linked:physical+=total;settled=total
        elif operation=='inspect_again':pass
        else:raise ValueError('unknown finite protocol operation')
    ok=physical>0 if required=='single' else identity and retained and authorized and linked and lower_used and settled==total
    missing=[]
    for name,value in (('same obligation identities',identity),('retained shared procedure',retained),
                       ('exact duty authorization',authorized),('inherited link',linked),('all duties enacted',settled==total)):
        if not value:missing.append(name)
    return bool(ok),'conductive in the finite transition model' if ok else 'missing: '+', '.join(missing)

def conductive(method, required, current):
    return simulate(PROGRAMS[method],required,current)

def search(required, current, limit, duties):
    rows=tuple((m,)+conductive(m,required,current) for m in LOWER[:limit])
    if any(ok for _,ok,_ in rows): return rows,(),(),'horizontal'
    if len(rows)!=len(LOWER): return rows,(),(),'unassessed'
    # Pareto order is declared before evaluation. Redundant inspection is real
    # extra paid work and cannot be chosen just to disguise an absent capacity.
    # Enumerate both constructors before testing sufficiency. An inherited
    # constructor can only reuse a lower organization that actually exists.
    proposals=tuple(candidate for extension in ('consent_cycle','carry_obligations') for candidate in (
        (extension,PROGRAMS[extension],2),(extension+':redundant_check',PROGRAMS[extension]+('inspect_again',),3)))
    candidates=tuple((name,dependencies,duties+int('inspect_again' in program))
                     for name,program,dependencies in proposals if simulate(program,required,current,duties)[0])
    minima=pareto(candidates)
    return rows,candidates,minima,'necessary_in_declared_repertoire' if minima else 'unresolved'

def pareto(candidates):
    return tuple(name for name,dep,work in candidates if not any(
        d<=dep and w<=work and (d<dep or w<work) for other,d,w in candidates if other!=name))

def allocate(obligations, members, start):
    if not members or start not in members: raise ValueError('observed current member holder required')
    offset=members.index(start)
    return tuple((d,members[(offset+i)%len(members)]) for i,d in enumerate(obligations))
