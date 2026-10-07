"""Paid situated admission for exact native workflow content, without new laws."""
from .workflow_selection_execution import WorkflowFinalSelectionEngine
from .workflow_shell_records import WorkflowShellRequest, registry
from .workflow_records import WORKFLOW_RECIPES
from .shell_records import EncounterRequest
from .shell_policy import facts
from .selection_records import fields_of, dumps
from .operations import address, record
from .material import attrs
from .compact import seal, unseal

class WorkflowShellEngine(WorkflowFinalSelectionEngine):
    SCHEMA='hle-full-crux-c7-workflow-shell-v1'

    @staticmethod
    def _registry(): return registry()

    def __init__(self,world,law):
        super().__init__(world,law)
        self._workflow_shell_requests={}

    @classmethod
    def from_selection(cls,text):
        return cls.restore(seal(cls.SCHEMA,unseal(text,WorkflowFinalSelectionEngine.SCHEMA)))

    def _declare(self,cid,versions):
        if any(v.ref.identity.namespace.startswith('c7sh.') for v in versions):
            raise ValueError('workflow Shell audit records cannot be authored')
        return super()._declare(cid,versions)

    def _disclose(self,cid,actor,source,selectors,subject):
        if source.identity.namespace.startswith('c7sh.'):
            raise ValueError('workflow Shell audit records are not participant knowledge')
        return super()._disclose(cid,actor,source,selectors,subject)

    def _start(self,cid,r):
        if type(r) is not WorkflowShellRequest:return super()._start(cid,r)
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
        v=record(address('c7sh.request',m.actor,r.key),'Original workflow obligation',dict(
            actor=m.actor,owner=m.actor,recipe=m.recipe,target=m.target,context=m.context,cue=m.cue,
            carrier=r.carrier,bearer=r.bearer,demand=r.demand,phase=r.phase,
            operation=ref,key=m.key,workflow=dumps(exact)))
        self._batch(cid+':request',m.actor,(v,),evidence=(ref,*m.inputs))
        self._workflow_shell_requests[m.actor,r.key]=r
        return ref

    def _workflow_shell_allows(self,decision,route):
        return decision is not None and decision['route']==route

    def _commit(self,cid,actor,key):
        r=self._workflow_shell_requests.get((actor,key))
        if r is None:return super()._commit(cid,actor,key)
        event=super()._commit(cid,actor,key)
        d=self.job_status(actor,key);m=r.movement;recipe=WORKFLOW_RECIPES[m.recipe]
        enc=d.get('encounter');decision=None if enc is None else attrs(self.world.resolve(enc))
        allowed=self._workflow_shell_allows(decision,m.recipe.removeprefix('workflow-'))
        child=None;failure=d.get('failure')
        if allowed:
            try:child=super()._start(cid+':movement',m)
            except ValueError as exc:failure='native_validation: '+str(exc)
        v=record(address('c7sh.admission',actor,key),'Paid workflow Shell admission',dict(
            request=address('c7sh.request',actor,key),actor=actor,owner=actor,
            operation=self._jobs[actor,key],encounter=enc,requested_recipe=m.recipe,
            origin=recipe.origin,destination=recipe.destination,polarity=recipe.polarity,
            target=m.target,context=m.context,cue=m.cue,carrier=r.carrier,bearer=r.bearer,
            demand=r.demand,phase=r.phase,admitted=allowed,child=child,failure=failure,
            movement_complete=False,actual_result_perspective='I',
            actual_intent=None if decision is None else decision['route'],
            pending_obligation=recipe.destination,admission_spent=d['spent']))
        self._batch(cid+':admission',actor,(v,),evidence=tuple(x for x in (event,enc,child) if x))
        return event
