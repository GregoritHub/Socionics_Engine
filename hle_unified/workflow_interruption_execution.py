"""Native first-step interruption with retained spending and unfinished obligations."""
from .workflow_shell_execution import WorkflowShellEngine
from .workflow_interruption_records import WorkflowInterruptionRequest, registry
from .workflow_records import WORKFLOW_RECIPES
from .shell_records import EncounterRequest
from .shell_policy import facts
from .selection_records import fields_of, dumps
from .operations import address, record, indexed
from .material import attrs
from .compact import seal, unseal

class WorkflowInterruptionEngine(WorkflowShellEngine):
    SCHEMA='hle-full-crux-c7-workflow-interruption-v1'

    @staticmethod
    def _registry(): return registry()

    def __init__(self,world,law):
        super().__init__(world,law)
        self._workflow_interruption_requests={}
        self._workflow_interruptions={}

    @classmethod
    def from_shell(cls,text):
        return cls.restore(seal(cls.SCHEMA,unseal(text,WorkflowShellEngine.SCHEMA)))

    def _declare(self,cid,versions):
        if any(v.ref.identity.namespace.startswith('c7shi.') for v in versions):
            raise ValueError('workflow Shell audit records cannot be authored')
        return super()._declare(cid,versions)

    def _disclose(self,cid,actor,source,selectors,subject):
        if source.identity.namespace.startswith('c7shi.'):
            raise ValueError('workflow Shell audit records are not participant knowledge')
        return super()._disclose(cid,actor,source,selectors,subject)

    def _start(self,cid,r):
        if type(r) is not WorkflowInterruptionRequest:return super()._start(cid,r)
        m=r.movement
        if (m.actor,m.key) in self._jobs:raise ValueError('unused native workflow movement required')
        self._prepare_workflow(m)
        view=self.participant_view(m.actor)
        if facts(view,m.target,m.context,r.evidence)!=facts(view,m.target,m.context):
            raise ValueError('all current received opportunity evidence required')
        q=EncounterRequest(r.key,m.actor,m.target,m.context,m.cue,r.carrier,r.bearer,
            r.evidence,m.recipe.removeprefix('workflow-'),r.demand,r.visit_limit)
        ref=super()._start(cid,q)
        exact=fields_of(m);exact['evidence']=tuple((a.delivery,a.key) for a in m.evidence)
        v=record(address('c7shi.request',m.actor,r.key),'Original workflow obligation',dict(
            actor=m.actor,owner=m.actor,recipe=m.recipe,target=m.target,context=m.context,cue=m.cue,
            carrier=r.carrier,bearer=r.bearer,demand=r.demand,phase=r.phase,
            operation=ref,key=m.key,workflow=dumps(exact)))
        self._batch(cid+':request',m.actor,(v,),evidence=(ref,*m.inputs))
        self._workflow_interruption_requests[m.actor,r.key]=r
        return ref

    def _workflow_interruption_allows(self,decision,route):
        return decision is not None and decision['route']==route

    def _commit(self,cid,actor,key):
        r=self._workflow_interruption_requests.get((actor,key))
        if r is None:return super()._commit(cid,actor,key)
        event=super()._commit(cid,actor,key)
        d=self.job_status(actor,key);m=r.movement;recipe=WORKFLOW_RECIPES[m.recipe]
        enc=d.get('encounter');decision=None if enc is None else attrs(self.world.resolve(enc))
        allowed=self._workflow_interruption_allows(decision,m.recipe.removeprefix('workflow-'))
        child=None;failure=d.get('failure')
        late=decision is not None and decision['base_route']==m.recipe.removeprefix('workflow-') and not allowed
        if allowed or late:
            try:child=super()._start(cid+':movement',m)
            except ValueError as exc:failure='native_validation: '+str(exc)
        if child is not None and late:self._workflow_interruptions[actor,m.key]=(r,enc)
        v=record(address('c7shi.admission',actor,key),'Paid workflow Shell admission',dict(
            request=address('c7shi.request',actor,key),actor=actor,owner=actor,
            operation=self._jobs[actor,key],encounter=enc,requested_recipe=m.recipe,
            origin=recipe.origin,destination=recipe.destination,polarity=recipe.polarity,
            target=m.target,context=m.context,cue=m.cue,carrier=r.carrier,bearer=r.bearer,
            demand=r.demand,phase=r.phase,admitted=allowed,child=child,failure=failure,
            movement_complete=False,actual_result_perspective='I',
            actual_intent=None if decision is None else decision['route'],
            pending_obligation=recipe.destination,admission_spent=d['spent']))
        self._batch(cid+':admission',actor,(v,),evidence=tuple(x for x in (event,enc,child) if x))
        return event

    def _workflow_interrupts(self):return True

    def _advance(self,cid,actor,key,work_limit):
        stop=self._workflow_interruptions.get((actor,key))
        if stop is None or not self._workflow_interrupts():return super()._advance(cid,actor,key,work_limit)
        old,d=self._active(actor,key)
        boundary=d['recall_units']+sum(indexed(d,'route.0.charges.'))+d['route.0.content_units']
        if type(work_limit) is not int or work_limit<1:raise ValueError('positive work limit required')
        ref=super()._advance(cid,actor,key,min(work_limit,boundary-d['completed']))
        current=self.job_status(actor,key)
        if current['steps_completed']<1:return ref
        r,enc=stop
        super()._cancel(cid+':shell-stop',actor,key)
        child=self._jobs[actor,key];decision=attrs(self.world.resolve(enc))
        v=record(address('c7shi.interruption',actor,key),'Interrupted realized workflow',dict(
            admission=address('c7shi.admission',actor,r.key),operation=child,encounter=enc,
            intermediate=current['last_step'],replacement=self.job_status(actor,r.key).get('binding'),
            requested_destination=current['destination'],actual_result_perspective='I',
            requested_polarity=current['polarity'],actual_intent=decision['route'],
            original_obligation_met=False,spent=current['spent']))
        self._batch(cid+':interruption',actor,(v,),evidence=(child,current['last_step'],enc))
        del self._workflow_interruptions[actor,key]
        return child
