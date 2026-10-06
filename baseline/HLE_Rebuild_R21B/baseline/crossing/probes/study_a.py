"""Matched, declared policy reconstruction; not the missing original probe."""
from .common import *
from hle.organization_records import Formulate, Join, Attend, Perform
from hle.model_a import TYPES


def restoration(w,m,identity,practice_rounds=6):
    before=snapshot(w)
    runs=[]
    for n in range(practice_rounds):
        a=MEMBERS[n%3]
        r=m.call('restore:practice:'+str(n),lambda:perform(w,a,identity,'restore:practice:'+str(n)))
        runs.append(w.organization_outcome(a,r))
    after_practice=snapshot(w)
    p=m.call('restore:unearned_formulate',lambda:propose(w,DARA,'restore:unearned'))
    unearned=w.organization_record(DARA,p)
    control_before=snapshot(w)
    try:
        # Test the engine packet guard, not the demo helper's assumptions.
        w.send_organization(DARA,p,ALICE,'restore:unearned:send')
        unearned_error=None
    except ValueError as e:
        unearned_error=str(e)
    assert snapshot(w)==control_before
    no_seat=w.organization_state(DARA,identity) is None
    access=m.call('restore:access',lambda:acquire(w,DARA,(BOX,),'restore:access'))
    offer=m.call('restore:offer',lambda:send(w,ALICE,w.organization_state(ALICE,identity).ref,DARA,'restore:offer'))
    join=m.call('restore:join',lambda:org(w,DARA,Join(offer,access),'restore:join'))
    for a in MEMBERS:
        notice=m.call('restore:notice:'+a.key,lambda:send(w,DARA,join,a,'restore:notice:'+a.key))
        m.call('restore:attend:'+a.key,lambda:org(w,a,Attend(w.organization_state(a,identity).ref,notice),'restore:attend:'+a.key))
    after_attend=snapshot(w)
    attend_no_seat=w.organization_state(DARA,identity) is None
    p=m.call('restore:propose',lambda:propose(w,ALICE,'restore:propose',w.organization_state(ALICE,identity).ref))
    m.call('restore:agree',lambda:agree(w,ALICE,p,'restore:agree'))
    after_agreement=snapshot(w)
    restored_runs=[]
    for n,a in enumerate(ACTORS):
        r=m.call('restore:run:'+a.key,lambda:perform(w,a,identity,'restore:run:'+str(n)))
        restored_runs.append({'actor':a.key,'outcome':w.organization_outcome(a,r),'box_owner':owner(w)})
    return {'practice_outcomes':runs,'practice_spent':delta(before,after_practice),
        'unearned_formulation_status':unearned.status,'unearned_formulation_reason':unearned.reason,
        'unearned_agreement_error':unearned_error,'no_seat_before':no_seat,'no_seat_after_attend':attend_no_seat,
        'join_status':w.organization_record(DARA,join).status,
        'application_and_controls_spent':delta(after_practice,after_attend),
        'successor_agreement_spent':delta(after_attend,after_agreement),
        'total_before_new_runs':delta(before,after_agreement),
        'members':[a.key for a in w.organization_state(DARA,identity).terms.members],
        'new_runs':restored_runs,'new_runs_spent':delta(after_agreement,snapshot(w))}


def policy_case(policy,extractor_type='eii',restore=False,covered=None,patience=2):
    w,m,identity=prepared(('lse','iee','lsi',extractor_type))
    before=snapshot(w)
    rounds=[]; attempts=[]; empty=0; stop=None
    for n in range(12):
        payoff=0
        if stop is None and policy!='quiet':
            for a in MEMBERS:
                if covered is not None:
                    response='ignore' if a.key in covered else 'yield'
                else:
                    response=('ignore' if policy=='Q4' or policy=='Q2' and a==ALICE else
                        'reply' if policy=='Q3' else 'yield')
                x=ask(w,m,a,f'round:{n+1}:ask:{a.key}',response)
                x['round']=n+1;attempts.append(x);payoff+=x['payoff']
            empty=empty+1 if payoff==0 else 0
            if empty>=patience: stop=n+1
        a=MEMBERS[n%3]
        r=m.call('round:'+str(n+1)+':organization',lambda:perform(w,a,identity,'round:'+str(n+1)+':organization'))
        rounds.append({'round':n+1,'payoff':payoff,'worker':a.key,'outcome':w.organization_outcome(a,r),'box_owner':owner(w)})
    result={'policy':policy,'extractor_type':extractor_type,'covered':covered,'patience':patience,'rounds':12,
        'setup_spent':{a:20000-before[a][0] for a in before},'assay_spent':delta(before,snapshot(w)),
        'stop_round':stop,'attempt_count':len(attempts),'box_owner':owner(w),
        'fulfilled_organization_runs':sum(x['outcome']=='fulfilled' for x in rounds),
        'fulfilled_transfers_to_extractor':sum(x['outcome']=='fulfilled' for x in attempts),
        'delivered_replies':sum(x['reply_delivered'] for x in attempts),
        'round_log':rounds,'attempt_log':attempts}
    if restore: result['restoration']=restoration(w,m,identity)
    result['ledger']=m.rows
    return result


def run():
    cases=[policy_case(q,restore=q=='Q4') for q in ('Q1','Q2','Q3','Q4')]
    quiet=policy_case('quiet')
    sensitivity=[]
    for patience in (1,4):
        c=policy_case('Q4',patience=patience);c.pop('ledger');sensitivity.append(c)
    w,m,identity=prepared()
    no_rebuild=restoration(w,m,identity,practice_rounds=0)
    no_rebuild['ledger']=m.rows
    # Exhaust all subsets, so coverage is not confounded with which member refuses.
    from itertools import combinations
    coverage=[]
    for n in range(4):
        for subset in combinations([a.key for a in MEMBERS],n):
            c=policy_case('coverage',covered=list(subset))
            c.pop('ledger');coverage.append(c)
    single=[]
    for t in TYPES:
        for a in MEMBERS:
            w,m,identity=prepared(('lse','iee','lsi',t))
            row=ask(w,m,a,'extension:ask','yield')
            row['extractor_type']=t;row['ledger']=m.rows;single.append(row)
    full=[]
    for t in TYPES:
        c=policy_case('Q1',t);c.pop('ledger');full.append(c)
    return {'study_kind':'matched reconstruction, not original A script',
        'cases':cases,'quiet_baseline':quiet,'stop_sensitivity':sensitivity,
        'restoration_without_extra_practice':no_rebuild,
        'coverage_subsets':coverage,'extractor_single_ask':single,'extractor_full_q1':full}
