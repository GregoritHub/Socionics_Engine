"""C6 paid participant selection followed by the unchanged C5/native executor."""
from dataclasses import replace
from .crux_shell_execution import CruxShellEngine
from .crux_shell_records import ShellMovementRequest
from .selection_records import SelectionRequest,registry,fields_of,dumps,loads,demand_value
from .selection_policy import proposals,choose
from .self_content import decode
from .self_records import SelfRouteRequest
from .crossing_records import CrossingRequest
from .records import ObjectRef
from .particulars import DetailAddress
from .operations import OperationEngine,record,address,job_address
from .operation_records import OperationRequest
from .material import attrs,attributes
from .store import next_version
from .compact import seal,unseal

class SelectionEngine(CruxShellEngine):
    SCHEMA='hle-full-crux-c6-engine-v1'
    @staticmethod
    def _registry(): return registry()
    def __init__(self,world,law):
        super().__init__(world,law);self._selections={}
    @classmethod
    def from_c5(cls,text): return cls.restore(seal(cls.SCHEMA,unseal(text,CruxShellEngine.SCHEMA)))
    def _declare(self,cid,versions):
        if any(v.ref.identity.namespace.startswith('c6.') for v in versions): raise ValueError('C6 evidence cannot be supplied as drafts')
        return super()._declare(cid,versions)
    def _disclose(self,cid,actor,source,selectors,subject):
        if source.identity.namespace.startswith('c6.'): raise ValueError('selection audit is not participant knowledge')
        return super()._disclose(cid,actor,source,selectors,subject)

    def selection_view(self,r):
        """Actor-only values. Never reads material heads, private peer state or outcomes."""
        view=self.participant_view(r.actor)
        b=view._bindings.get(r.demand)
        if b is None or (b.actor,b.context,b.cue,b.target.identity)!=(r.actor,r.context,r.cue,r.target.identity) or len(b.content)!=1 or b.content[0].relation!='c6.need':
            raise ValueError('owned paid demand in this context required')
        need=demand_value(decode(b.content[0].object))
        def latest(ref):
            if ref is None:return None
            ps=view.lookup(subject=ref.identity)
            return max((p.source for p in ps if p.source.identity==ref.identity),key=lambda x:x.revision,default=ref)
        request=fields_of(r)
        for key in ('target','stock','tool','repair_stock','group','procedure'):request[key]=latest(request[key])
        def known(ref): return {} if ref is None else {p.address.key:p.value for p in view.resolve(ref)}
        items=[];foreign=[];scanned=0
        for binding in view.snapshot.bindings:
            if binding.cue!=r.cue or binding.target.identity!=r.target.identity or binding.endorsement.value in ('retracted','disputed'):continue
            if binding.context!=r.context:
                if len(binding.content)==1 and binding.content[0].relation in ('c3.data','c4.data'):
                    z=decode(binding.content[0].object)
                    if z.get('kind')=='model':foreign.append(dict(ref=binding.ref,data=z,binding=True))
                continue
            scanned+=1
            if len(binding.content)==1 and binding.content[0].relation in ('c2.data','c3.data','c4.data'):
                items.append(dict(ref=binding.ref,data=decode(binding.content[0].object),binding=True))
        for p in view.lookup(key='payload'):
            if p.source.identity.namespace not in ('c2.message','c3.message','c4.message'):continue
            d=decode(p.value)
            if d.get('target',r.target).identity==r.target.identity and d.get('context',r.context)==r.context:
                scanned+=1;items.append(dict(ref=p.source,data=d,binding=False))
        for p in view.lookup(key='event'):
            if p.source.identity.namespace!='u4.observation':continue
            d=known(p.source)
            if d.get('context')==r.context and d.get('actor')==r.actor:
                # Consumable observations are scoped to the configured resource;
                # condition practice elsewhere cannot masquerade as local stock.
                target=d.get('target') or d.get('stock')
                if target is not None and (request['stock'] is None or target.identity==request['stock'].identity):
                    scanned+=1;items.append(dict(ref=p.source,data=dict(d,kind='observation'),binding=False))
        items.sort(key=lambda x:dumps(x['ref']))
        unique={x['ref']:x for x in items};items=list(unique.values())
        total=len(items);items=items[:r.limit];foreign.sort(key=lambda x:dumps(x['ref']));foreign_total=len(foreign);foreign=foreign[:r.limit]
        group=known(request['group']).get('payload'); group=decode(group) if group else None
        profile=attrs(self.world.resolve(self._profiles[r.actor]))
        evidence=tuple((p.address.delivery,p.address.key) for p in view.lookup(subject=r.target.identity))
        sources=tuple(dict.fromkeys(p.source for p in view.lookup(subject=r.target.identity)))
        acquired=tuple((a.procedure,a.context,a.receipt) for a in view.snapshot.acquired if a.procedure==request['procedure'] and a.context==r.context)
        return dict(request=request,need=need,items=items,foreign=foreign,foreign_total=foreign_total,total_items=total,truncated=total>r.limit,scanned=scanned,
            target=known(request['target']),stock=known(request['stock']),tool=known(request['tool']),repair_stock=known(request['repair_stock']),group=group,
            acquired=acquired,tim=profile['tim'],profile=self._profiles[r.actor],cursor=self._cursors[r.actor],
            wallet=(self.wallet(r.actor)['energy'],self.wallet(r.actor)['time']),evidence=evidence,sources=sources)

    def _select_policy(self,s):
        rows=proposals(s); return rows,choose(rows)

    def _start(self,cid,r):
        if type(r) is not SelectionRequest:return super()._start(cid,r)
        if r.actor not in self._profiles or r.actor in self._locks or (r.actor,r.key) in self._jobs:raise ValueError('free typed participant and unused selection key required')
        s=self.selection_view(r);rows,selected=self._select_policy(s)
        required=1+s['scanned']+s['foreign_total']+33+sum(x['examined'] for x in rows)
        snapshot=record(address('c6.snapshot',r.actor,r.key),'Participant-accessible selection inputs',dict(payload=dumps(s)))
        ballot=record(address('c6.candidates',r.actor,r.key),'Uncommitted bounded proposals',dict(payload=dumps(rows)))
        d=fields_of(OperationRequest(r.key,r.actor,'bind',r.context));d.pop('participants');d.pop('evidence')
        d.update(record_type='operation',c6=True,primitive='bind',required=required,completed=0,spent=0,status='pending',failure=None,result=None,
            route_prepare=required,route_execute=0,started_tick=self._now().tick,snapshot=snapshot.ref,candidates=ballot.ref,
            scanned=s['scanned'],foreign_count=s['foreign_total'],evaluated=sum(x['examined'] for x in rows),policy='c6-situated-selection-v1',
            **{'participant.0':r.actor,'lock.0':r.actor,'input.0':r.demand,'dependency.0':self.law})
        job=record(job_address(r.actor,r.key),'Paid situated candidate comparison',d)
        self._batch(cid,r.actor,(snapshot,ballot,job),evidence=(r.demand,*s['sources']))
        self._jobs[r.actor,r.key]=job.ref;self._reserve(d,job.ref);self._selections[r.actor,r.key]=(r,s,rows,selected)
        return job.ref

    def _advance(self,cid,actor,key,work_limit):
        if (actor,key) in self._selections:return OperationEngine._advance(self,cid,actor,key,work_limit)
        return super()._advance(cid,actor,key,work_limit)

    def _native_request(self,s,row):
        r=s['request']; name=row['name']; face=row['face']; selfroute=name in ('Contemplate','Act','Commune','Integrate')
        fields=dict(key=r['key']+':movement',actor=r['actor'],recipe=row['recipe'],context=r['context'],cue=r['cue'],target=r['target'],
            inputs=row['inputs'],evidence=tuple(DetailAddress(*a) for a in s['evidence']),demand=s['need']['amount'])
        if name=='Act' and face=='accumulation':fields.update(tool=r['tool'],stock=r['repair_stock'])
        elif name in ('Express','Apply','Mobilize'):fields['stock']=r['stock']
        if name in ('Share','Coordinate','Educate','Identify','Mobilize','Institutionalize','Commune') or any(x['data'].get('kind')=='rule' and x['ref'] in row['inputs'] for x in s['items']):fields['group']=r['group']
        if r['peer'] is not None and name!='Act':fields['peer']=r['peer']
        if row['recipe']=='context-transfer-v1':
            from .crux_composition_records import CruxCompositionRequest
            return CruxCompositionRequest(**fields)
        return (SelfRouteRequest if selfroute else CrossingRequest)(**fields)

    def _commit(self,cid,actor,key):
        if (actor,key) not in self._selections:return super()._commit(cid,actor,key)
        old,d=self._active(actor,key)
        if d['status']!='ready':raise ValueError('paid selection must finish before a choice is enacted')
        r,s,rows,selected=self._selections[actor,key];failure=None
        now=self.selection_view(r)
        if any(now[k]!=s[k] for k in s if k!='wallet'):failure='changed_participant_inputs'
        terminal='failed' if failure else 'succeeded'
        event=self._event(cid,old,terminal);d.update(status=terminal,failure=failure,result=event.ref,finished_tick=self._now().tick)
        current=next_version(old,attributes=attributes(d))
        receipt=() if failure else (record(address('u4.receipt',cid),'Paid selection comparison receipt',dict(actor=actor,operation='bind',work_key=key,required=d['required'],completed=d['completed'],spent=d['spent'],**{'input.0':r.demand})),)
        self._batch(cid,actor,(current,*receipt,event),evidence=(old.ref,));self._jobs[actor,key]=current.ref;self._release(d,old.ref)
        admission=None
        if failure is None and selected is not None:
            movement=self._native_request(s,selected)
            carrier=ObjectRef(r.peer or actor,1)
            evidence=tuple(p.address for p in self.participant_view(actor).snapshot.particulars if p.subject.identity==r.target.identity)
            q=ShellMovementRequest(key+':admission',movement,carrier,ObjectRef(actor,1),evidence,phase='after_first_step')
            try:admission=super()._start(cid+':selected',q)
            except ValueError as exc:failure='native_validation: '+str(exc)
        decision=record(address('c6.decision',actor,key),'Paid choice and exact native launch',dict(operation=current.ref,snapshot=d['snapshot'],candidates=d['candidates'],
            selected=None if selected is None else selected['cell'],recipe=None if selected is None else selected['recipe'],
            admission=admission,failure=failure,spent=d['spent'],status='deferred' if selected is None else 'proposed' if admission is None else 'launched',
            completion_claim=False))
        self._batch(cid+':decision',actor,(decision,),evidence=(current.ref,))
        return event.ref

    def participate(self,cid,r,work_limit=1000000):
        """One bounded scheduler turn; no route ordering or outcome supplied."""
        if (r.actor,r.key) not in self._jobs:self.start(cid+':start',r)
        keys=(r.key,r.key+':admission',r.key+':movement')
        for key in keys:
            if (r.actor,key) not in self._jobs:continue
            d=self.job_status(r.actor,key)
            if d['status'] in ('cancelled','succeeded','failed'):continue
            if d['status']!='ready':self.advance(cid+':work:'+key,r.actor,key,work_limit)
            if self.job_status(r.actor,key)['status']=='ready':self.commit(cid+':commit:'+key,r.actor,key)
            return self.job_status(r.actor,key)
        return None
