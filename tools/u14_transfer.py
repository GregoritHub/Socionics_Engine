"""New declared compositions, receiver-owned learning and nested performance."""
from pathlib import Path
from u14_support import *


def language_case(case,out):
    from tests_u10 import fixtures as f
    from hle_unified.language_audit import audit
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    write_json(out/'case.json',case)
    e,t=f.teacher10(f.setup10(tim=case['tim']))
    _,unknown=f.request10(e,t['entry'],prefix='unknown')
    questions=[x for x in e.language_view(f.BOB) if x['kind']=='message' and x['act']=='clarification']
    checks={'unknown_term_has_clarification':bool(questions)}
    f.deliver10(e,questions[-1]);f.work10(e,'hear-question','interpret',focus=questions[-1]['ref'])
    runs=t['runs'][::(-1 if case['reverse_demonstrations'] else 1)]
    learned=f.teach10(e,t['entry'],runs)
    checks['own_lexical_learning']=bool(learned)
    body=('seq',(('word',t['entry']['term']),)+tuple(x for _ in range(case['extra_cycles']) for x in (('act','use'),('act','care'))))
    goal=(('ge',('field','progress','uses'),1+case['extra_cycles']),*f.GOAL[1:])
    message,interpreted=f.request10(e,t['entry'],'bob-composed',prefix='new-composition',body=body,goal=goal)
    response=f.response10(e,interpreted)
    run=f.enact_response10(e,response,prefix='receiver',steps=1)
    cp=e.checkpoint();save_gzip(out/'partial.checkpoint.json.gz',cp)
    clone=f.LanguageEngine.restore(cp)
    completed=[]
    for x in (e,clone):completed.append(f.continue10(x,run,prefix='receiver-continued'))
    checks['partial_message_work_replays']=e.checkpoint()==clone.checkpoint() and completed[0]==completed[1]
    checks['novel_composition_is_enacted']=completed[0]['status']=='succeeded' and len(completed[0]['events'])>=2*(1+case['extra_cycles'])
    artifact=keep_engine(out,'final',e,audit)
    result=dict(case=case,passed=all(checks.values()),checks=checks,artifact=artifact)
    write_json(out/'summary.json',result);return result


def nesting_case(case,out):
    from tests_u11 import fixtures as f
    from hle_unified.collective_audit import audit
    out=Path(out);out.mkdir(parents=True,exist_ok=False);write_json(out/'case.json',case)
    e=f.setup11(tim=case['tim'],train_eve=True)
    child=f.repair_group(e)
    primitive=(f.step(f.ALICE,'repair',target=f.SHARED,tool=f.ref('u11-kit-alice'),stock=f.ref('u11-repair-alice')),)
    plan=f.proposed(e,child,primitive,'child-plan')
    performed=f.finish(e,f.instantiate(e,plan,'child-run'),'child-work')
    capacity=f.work(e,'retain-child','retain',focus=performed['ref'])[0]
    f.expose(e,f.ALICE,e.world.head(f.SHARED.identity).ref)
    event=f.perform(e,f.OperationRequest('renew',f.ALICE,'damage',f.ROOM,target=e.world.head(f.SHARED.identity).ref,
        evidence=f.evidence(e,f.ALICE,e.world.head(f.SHARED.identity).ref)))
    f.receive(e,event,f.ALICE,'renew')
    receiver=f.EVE if case['receiver']=='eve' else f.BOB
    care=f.ref('u11-care-'+receiver.key)
    root=f.group(e,'parent',members=(child['ref'],),resources=(e.world.head(f.SHARED.identity).ref,care))
    root=f.join(e,root,actor=receiver)
    program=(('call',capacity['ref']),f.step(f.ALICE,'transfer',target=f.SHARED,recipient=receiver))+tuple(
        x for _ in range(case['cycles']) for x in (f.step(receiver,'use',target=f.SHARED),f.step(receiver,'care',target=f.SHARED,stock=care)))
    plan=f.proposed(e,root,program,'parent-plan')
    run=f.instantiate(e,plan,'parent-run')
    run=f.perform_step(e,run,'nested-first')
    cp=e.checkpoint();save_gzip(out/'partial.checkpoint.json.gz',cp)
    clone=f.CollectiveEngine.restore(cp)
    results=[f.finish(x,run,'nested-rest') for x in (e,clone)]
    retained=f.work(e,'retained-parent','retain',focus=results[0]['ref'])[0]
    f.work(clone,'retained-parent','retain',focus=results[1]['ref'])
    checks=dict(nested_constituents_performed=results[0]['status']=='succeeded' and len(results[0]['events'])==2+2*case['cycles'],
        restored_nested_work_exact=e.checkpoint()==clone.checkpoint(),
        group_capacity_owned_by_group=retained['owner']==root['ref'].identity,
        individual_ownership_preserved=e.world.head(f.SHARED.identity).facet(f.Material).owner==receiver)
    artifact=keep_engine(out,'final',e,audit)
    result=dict(case=case,passed=all(checks.values()),checks=checks,artifact=artifact)
    write_json(out/'summary.json',result);return result
