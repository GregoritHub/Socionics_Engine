"""Continuing original material, scoped corrections and explicit refusals."""
from dataclasses import replace
from tests_workflow_interruption.fixtures import *
from hle_unified.workflow_development_audit import audit,require_scoped_correction
from hle_unified.selection_records import fields_of,dumps


def history(worlds=None):
    worlds={} if worlds is None else worlds
    e,p,out=prepared('Theorize','accumulation');original=e.world.resolve(p.origin)
    def save(key):
        assert e.world.resolve(p.origin)==original
        worlds[key]=WorkflowInterruptionEngine.restore(e.checkpoint())
    def run(out_,key):
        q=dict(out_,request=replace(out_['request'],key=key))
        return finish(e,q,key+'-gate')
    d,later=run(out,'initial');assert later=='unavailable';save('01-formed-and-interrupted')
    dev.release8(e,'other-local-release',p,target=SAW2)
    dev.supply8(e,'renewed-same',target=DEVICE)
    d,later=run(out,'same-recurrence');assert later=='unavailable';save('02-other-correction-same-recurrence')
    own=authored(e,'changed-target-intent',target=LOAN)
    r=request(e,'changed','Theorize','accumulation',(own,),target=LOAN)
    changed=dict(request=r,inputs=(own,),extra={})
    dev.supply8(e,'renewed-changed',target=LOAN)
    d,later=run(changed,'changed-recurrence');assert later=='unavailable';save('03-changed-target-recurrence')
    dev.release8(e,'exact-local-release',p,target=DEVICE)
    d,later=run(out,'corrected');assert later=='handover';save('04-exact-correction-and-native-use')
    dev.supply8(e,'changed-after-local',target=LOAN)
    d,later=run(changed,'still-residual');assert later=='unavailable';save('05-other-target-still-residual')
    dev.supply8(e,'external-support',target=LOAN,approved=True)
    d,later=run(changed,'supported');assert later=='handover' and not e._capacities;save('06-supported-without-capacity')
    dev.supply8(e,'support-withdrawn',target=LOAN,approved=False)
    d,later=run(changed,'withdrawn');assert later=='unavailable' and not e._capacities;save('07-withdrawal-recurrence')
    return worlds


def unsupported(effect,worlds=None):
    worlds={} if worlds is None else worlds
    e,p,out=prepared('Theorize','accumulation',effect)
    before=e.checkpoint();worlds['before']=WorkflowInterruptionEngine.restore(before)
    r=dev.request8(e,'unsupported-release','release',p,(out['request'].target,))
    request_data=fields_of(r);request_data['evidence']=tuple((a.delivery,a.key) for a in r.evidence)
    try:e.start('unsupported-release:start',r)
    except ValueError as exc:
        error=str(exc);assert error=='unsupported, incomplete or scaffolded local correction'
    else:raise AssertionError('unsupported correction was permitted')
    assert e.checkpoint()==before
    worlds['after']=WorkflowInterruptionEngine.restore(e.checkpoint())
    d,later=finish(e,out);assert later=='unavailable'
    worlds['still-interrupted']=e
    return worlds,dict(effect=effect,request=dumps(request_data),error=error,checkpoint_unchanged=True)
