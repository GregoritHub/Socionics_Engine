"""Paid, route-aware U7/U8 admission of actual C2-C4 movements.

A completed admission is not a completed movement. Original work is started
only after a current, paid encounter permits it; it still pays every native
semantic/material cost and obeys its own authority and completion contracts.
"""
from .crux_composition_execution import CruxCompositionEngine
from .crux_shell_records import ShellMovementRequest, registry
from .shell_records import EncounterRequest, CRUX_ROUTES
from .operations import address, record, indexed
from .material import attrs
from .compact import seal, unseal
from .shell_policy import facts

class CruxShellEngine(CruxCompositionEngine):
    SCHEMA='hle-full-crux-c5-engine-v1'

    @staticmethod
    def _registry(): return registry()

    def __init__(self,world,law):
        super().__init__(world,law)
        self._shell_movements={}
        self._shell_interruptions={}

    @classmethod
    def from_c4(cls,text):
        return cls.restore(seal(cls.SCHEMA,unseal(text,CruxCompositionEngine.SCHEMA)))

    def _declare(self,cid,versions):
        if any(v.ref.identity.namespace.startswith('c5.') for v in versions):
            raise ValueError('C5 admission evidence cannot be supplied as a draft')
        return super()._declare(cid,versions)

    def _disclose(self,cid,actor,source,selectors,subject):
        if source.identity.namespace.startswith('c5.'):
            raise ValueError('admission receipts are audit records, not participant knowledge')
        return super()._disclose(cid,actor,source,selectors,subject)

    def _start(self,cid,r):
        if type(r) is not ShellMovementRequest: return super()._start(cid,r)
        m=r.movement
        if m.recipe not in CRUX_ROUTES or (m.actor,m.key) in self._jobs:
            raise ValueError('unused native movement in the 32-cell map required')
        # Validate the content opportunity before paying admission. This does
        # not install results, grant capacity or override native validation.
        if hasattr(self,'_prepare_cross') and type(m).__name__=='CrossingRequest': self._prepare_cross(m)
        elif type(m).__name__=='CruxCompositionRequest': self._prepare_composition(m)
        else: self._prepare_self(m)
        view=self.participant_view(m.actor)
        if facts(view,m.target,m.context,r.evidence)!=facts(view,m.target,m.context):
            raise ValueError('all current received opportunity evidence required')
        q=EncounterRequest(r.key,m.actor,m.target,m.context,m.cue,r.carrier,r.bearer,
            r.evidence,m.recipe,r.demand,r.visit_limit)
        ref=super()._start(cid,q)
        request_record=record(address('c5.request',m.actor,r.key),'Original movement obligation',dict(
            actor=m.actor,recipe=m.recipe,target=m.target,context=m.context,cue=m.cue,
            carrier=r.carrier,bearer=r.bearer,demand=r.demand,key=m.key,phase=r.phase,
            **{'input.'+str(i):v for i,v in enumerate(m.inputs)}))
        self._batch(cid+':request',m.actor,(request_record,),evidence=(ref,*m.inputs))
        self._shell_movements[m.actor,r.key]=r
        return ref

    def _commit(self,cid,actor,key):
        r=self._shell_movements.get((actor,key))
        if r is None: return super()._commit(cid,actor,key)
        event=super()._commit(cid,actor,key)
        d=self.job_status(actor,key); m=r.movement; recipe=self._recipe_for(m)
        encounter_ref=d.get('encounter'); child=None; failure=d.get('failure')
        decision=None if encounter_ref is None else attrs(self.world.resolve(encounter_ref))
        admitted=decision is not None and decision['route']==m.recipe
        late=(r.phase=='after_first_step' and decision is not None and decision['base_route']==m.recipe and not admitted)
        if admitted or late:
            try: child=super()._start(cid+':movement',m)
            except ValueError as exc:
                failure='native_validation: '+str(exc)
        if child is not None and late:
            self._shell_interruptions[actor,m.key]=(r,encounter_ref)
        receipt=record(address('c5.admission',actor,key),'Paid situated movement admission',dict(
            request=address('c5.request',actor,key),actor=actor,operation=self._jobs[actor,key],encounter=encounter_ref,
            requested_recipe=m.recipe,origin=recipe.origin,destination=recipe.destination,polarity=recipe.polarity,
            target=m.target,context=m.context,cue=m.cue,carrier=r.carrier,bearer=r.bearer,
            demand=r.demand,phase=r.phase,admitted=admitted,child=child,failure=failure,
            movement_complete=False,actual_result_perspective='I',
            actual_intent=None if decision is None else decision['route'],
            pending_obligation=recipe.destination,admission_spent=d['spent']))
        self._batch(cid+':admission',actor,(receipt,),evidence=tuple(x for x in (event,encounter_ref,child) if x))
        return event

    def _advance(self,cid,actor,key,work_limit):
        stop=self._shell_interruptions.get((actor,key))
        if stop is None: return super()._advance(cid,actor,key,work_limit)
        old,d=self._active(actor,key)
        boundary=d['recall_units']+sum(indexed(d,'route.0.charges.'))+d['route.0.content_units']
        # The first actual semantic handoff survives. A retained attributed
        # authorization/forecast then substitutes its personal response for
        # the requested continuation. No material command is committed.
        if type(work_limit) is not int or work_limit<1: raise ValueError('positive work limit required')
        ref=super()._advance(cid,actor,key,min(work_limit,boundary-d['completed']))
        current=self.job_status(actor,key)
        if current['steps_completed']<1: return ref
        r,enc=stop
        super()._cancel(cid+':shell-stop',actor,key)
        child=self._jobs[actor,key];decision=attrs(self.world.resolve(enc))
        v=record(address('c5.interruption',actor,key),'Interrupted realized movement',dict(
            admission=address('c5.admission',actor,r.key),operation=child,encounter=enc,
            intermediate=current['last_step'],replacement=self.job_status(actor,r.key).get('binding'),
            requested_destination=current['destination'],actual_result_perspective='I',
            requested_polarity=current['polarity'],actual_intent=decision['route'],
            original_obligation_met=False,spent=current['spent']))
        self._batch(cid+':interruption',actor,(v,),evidence=(child,current['last_step'],enc))
        del self._shell_interruptions[actor,key]
        return child
