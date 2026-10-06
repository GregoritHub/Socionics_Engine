"""Matched causal controls, independent of the sustained lifecycle scheduler."""
from dataclasses import replace
from collections import defaultdict
from hle.contracts import WorkStatus
from hle.language_records import Learn, LanguageCommand, Produce, Speech, Act
from hle.organization_records import Formulate
from hle.metabolism_records import ProcessingPolicy
from hle.model_a import TYPES, ELEMENT
from hle.semantic_records import SemanticPolicy
from tools.r11_workloads import make_world, Driver
from tools.r11_oracle import check_world


def signature(job):
    p=job.route.plan
    return (job.required, None if p is None else (p.path,p.hop_units,p.content_units))


def causal_panel():
    rows=[]; neutral=defaultdict(set)
    for active in sorted(ELEMENT):
        for typed,prices in ((True,True),(True,False),(False,True),(False,False)):
            for tim in TYPES:
                w,actors,(item,)=make_world(fixed_type=tim,active=active,
                    processing_policy=ProcessingPolicy(typed,prices))
                d=Driver(w,work_limit=8); actor=actors[0]
                access=d.acquire(actor,item,'evidence')
                command=LanguageCommand('learn:0','learn',actor,Learn('kept',access),8)
                w.execute(command); partial=w.language_job(actor,'learn')
                bounded=partial.outcome.value
                assert (partial.result is not None)==(partial.required<=8)
                d.operation(actor,command.payload,'learn','language')
                learn=w.language_job(actor,'learn')
                assert w.lexeme(actor,'kept').meaning.patterns[0].subject==0
                learned_active=w.processing_state(actor).active
                speech=Speech('explain',(w.word(actor,'kept',(item,actor)),),(Act('inspect',item),))
                d.operation(actor,Produce(speech),'produce','language')
                produce=w.language_job(actor,'produce')
                d.operation(actor,Formulate(access),'formulate')
                formulate=w.organization_job(actor,'formulate')
                assert formulate.candidate.status=='unresolved' and formulate.candidate.terms is None
                diag=check_world(w)
                if not typed: neutral[(active,prices)].add((signature(learn),signature(produce),signature(formulate)))
                rows.append({'tim':tim,'start':active,'typed':typed,'prices':prices,
                    'learn_required':learn.required,'learn_path':learn.route.plan.path,'bounded_at_8':bounded,
                    'learn_active':learned_active,'produce_required':produce.required,'produce_path':produce.route.plan.path,
                    'formulate_required':formulate.required,'formulate_path':formulate.route.plan.path,
                    'meaning_patterns':[(p.subject,p.owner) for p in w.lexeme(actor,'kept').meaning.patterns],
                    'formulate_status':formulate.candidate.status,'oracle_mismatches':diag['mismatches']})
    assert all(len(v)==1 for v in neutral.values()), 'declared type leaks through neutral routing'
    typed=[r for r in rows if r['typed'] and r['prices'] and r['start']=='ne']
    assert len({r['learn_required'] for r in typed})>1
    assert len({r['bounded_at_8'] for r in typed})>1, 'fixed budget never changes completion'
    assert len({tuple(r['learn_path']) for r in rows if r['tim']=='iee' and r['typed'] and r['prices']})>1
    emissions=[]
    for enabled in (True,False):
        w,actors,(item,)=make_world(fixed_type='iee',semantic_policy=SemanticPolicy(enabled))
        d=Driver(w); actor,receiver=actors[:2]
        d.learn(actor,item,'learn')
        u=d.operation(actor,Produce(Speech('explain',(w.word(actor,'kept',(item,actor)),),
            (Act('inspect',item),))),'produce','language')
        prior=w.processing_state(receiver).active
        obs=d.receive(actor,u,receiver,'send')
        n=w._notice_by_observation[(receiver,obs)]
        j=w._receptions[(receiver,'send:receive')]
        diag=check_world(w)
        emissions.append({'routing_enabled':enabled,'initial':'ne','receiver_before':prior,
            'sender_after_produce':w.processing_state(actor).active,'emitted':n.element,
            'reception_path':j.plan.path,'reception_required':j.plan.required,
            'receiver_after':w.processing_state(receiver).active,'speech':str(w.language_record(actor,u).speech),
            'oracle_mismatches':diag['mismatches']})
    assert emissions[0]['speech']==emissions[1]['speech']
    assert emissions[0]['emitted']=='fe' and emissions[1]['emitted']=='ne'
    assert emissions[0]['receiver_before']==emissions[1]['receiver_before']=='ne'
    assert emissions[0]['reception_path']!=emissions[1]['reception_path']
    assert emissions[0]['reception_required']!=emissions[1]['reception_required']
    return {'rows':rows,'emission_ablation':emissions,'cases':len(rows),
        'neutral_groups':len(neutral),'neutral_groups_passed':all(len(v)==1 for v in neutral.values()),'passed':True}
