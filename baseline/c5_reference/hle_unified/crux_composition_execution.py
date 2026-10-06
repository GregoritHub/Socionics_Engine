"""Paid compositional handoffs and bounded nested accountability.

Parent statements cite exact children. They are evidence organizations, not
substitutes for a child's knowledge, authority, work, or material effects.
"""
from dataclasses import fields, replace
from .crossing_execution import CrossingEngine
from .crux_composition_records import CruxCompositionRequest, COMPOSITION_RECIPES, definition, registry
from . import crux_composition_content as sem
from .crossing_content import intention
from .crux_content import owned_binding
from .records import ObjectVersion, Role, Account, Occurrence, Proposition, TimeScope, ClaimStatus
from .operations import address, job_address, record, indexed
from .operation_records import OperationRequest
from .material import attrs, attributes
from .store import next_version
from .cognitive_routes import route, flatten_route
from .compact import seal, unseal


class CruxCompositionEngine(CrossingEngine):
    SCHEMA="hle-full-crux-c4-engine-v1"

    def __init__(self,world,law):
        super().__init__(world,law)
        self._renewals_used=set()

    @staticmethod
    def _registry(): return registry()

    @classmethod
    def from_c3(cls,text): return cls.restore(seal(cls.SCHEMA,unseal(text,CrossingEngine.SCHEMA)))

    def _recipe_for(self,r):
        return COMPOSITION_RECIPES[r.recipe] if type(r) is CruxCompositionRequest else super()._recipe_for(r)

    def _step_namespace(self,r):
        return "c4.step" if type(r) is CruxCompositionRequest else super()._step_namespace(r)

    def _semantic_step(self,name,p,previous):
        return sem.transform(name,p,previous) if p.get("c4") else super()._semantic_step(name,p,previous)

    def _declare(self,cid,versions):
        if any(v.ref.identity.namespace.startswith("c4.") for v in versions):
            raise ValueError("composition outputs and evidence cannot be imported")
        return super()._declare(cid,versions)

    def _disclose(self,cid,actor,source,selectors,subject):
        if source.identity.namespace.startswith("c4."):
            m=self._cross_public.get(source)
            if m is None or actor not in m["audience"]: raise ValueError("only addressed composition outputs may be disclosed")
            value=self.world.resolve(source)
            allowed={(a.name,("attributes",str(i),"value")) for i,a in enumerate(value.attributes) if a.name=="payload"}
            if subject!=source or any((s.key,s.path) not in allowed for s in selectors): raise ValueError("public payload only")
        return super()._disclose(cid,actor,source,selectors,subject)

    def _read_cross(self,view,ref,r):
        if not ref.identity.namespace.startswith("c4."): return super()._read_cross(view,ref,r)
        if ref in view._bindings:
            b=owned_binding(view,ref)
            if ref not in self._cross_outputs or (b.context,b.cue,b.target.identity)!=(r.context,r.cue,r.target.identity):
                raise ValueError("owned generated composition in exact scope required")
            return sem.decode(b.content[0].object),b.particulars
        m=self._cross_public.get(ref); paid=[p for p in view.resolve(ref) if p.address.key=="payload"]
        if m is None or r.actor not in m["audience"] or len(paid)!=1 or m["context"]!=r.context:
            raise ValueError("addressed paid composition uptake required")
        d=sem.decode(paid[0].value)
        if d["target"].identity!=r.target.identity: raise ValueError("wrong composition referent")
        return d,(paid[0].address,)

    def _prepare_cross(self,r):
        p=super()._prepare_cross(r)
        x=p["data"][0]
        if (p["recipe"].action=="apply" and p["recipe"].polarity=="expenditure"
            and "coupled" in x and not x["coupled"]):
            raise ValueError("uncoupled composed constraints authorize trials only")
        return p

    def _prepare_composition(self,r):
        recipe=COMPOSITION_RECIPES[r.recipe]; a=recipe.action; view=self.participant_view(r.actor)
        known=self.access._known_refs(r.actor)
        if r.cue not in self._references or any(x not in known for x in (r.cue,r.context,r.target)) or Role.CONTEXT not in self.world.resolve(r.context).roles:
            raise ValueError("processed context, referent and cue required")
        if any(view.detail(x) is None for x in r.evidence): raise ValueError("unread or foreign evidence")
        addresses=list(r.evidence); data=[]
        for i,ref in enumerate(r.inputs):
            scoped=r
            if a=="context" and i==0:
                b=owned_binding(view,ref)
                if b.context==r.context: raise ValueError("context transfer must name a different destination")
                scoped=replace(r,context=b.context)
            d,extra=self._read_cross(view,ref,scoped); data.append(d); addresses.extend(extra)
        x=data[0]; group=None
        if r.group is not None or a in ("renew","commune"):
            group=self._group(r,view)
            if len(group["members"])!=2: raise ValueError("bounded two-member group required")
            addresses.extend(p.address for p in view.resolve(r.group))
        if a in ("renew","commune"):
            if x["kind"]!="shared" or r.peer is None or x["group"]!=r.group or set(x["participants"])!=set(group["members"]):
                raise ValueError("existing actual shared meaning and exact participants required")
            if a=="renew":
                if len(data)!=2: raise ValueError("shared prior and own stance required")
                intention(data[1])
            else:
                if len(data)!=3: raise ValueError("shared prior plus renewed reciprocal exchange required")
                offer,reply=data[1:]
                if ((offer.get("kind"),offer.get("prior"),offer.get("source"),offer.get("speaker"),offer.get("receiver"),
                     offer.get("group"),reply.get("kind"),reply.get("offer"),reply.get("speaker"),reply.get("receiver"),
                     reply.get("group"),reply.get("understood"),reply.get("answer")) !=
                    ("offer",r.input,r.input,r.actor,r.peer,r.group,"reply",r.inputs[1],r.peer,r.actor,r.group,
                     offer.get("cap"),min(offer["cap"],offer["question_demand"]))):
                    raise ValueError("renewal must address this exact shared history")
        elif a=="integrate":
            if len(data)<2 or any(z["kind"]!="model" or z["formula"]!="min(demand, cap, observed_available)" for z in data):
                raise ValueError("two compatible generated conditional models required")
        elif a=="context":
            if len(data)!=3 or x["kind"]!="model": raise ValueError("model, local intention and actual local observation required")
            intention(data[1]); obs=data[2]
            if obs["kind"]!="observation" or obs["outcome"]!="succeeded" or "available" not in obs:
                raise ValueError("successful local stock observation required")
        elif a=="release":
            if len(data)!=2 or x["kind"]!="nested" or data[1]["kind"]!="model": raise ValueError("parent evidence and an owned model required")
            owned_binding(view,r.inputs[1])
            if r.inputs[1] not in {c[1] for c in x["children"]}: raise ValueError("release model must be an exact declared child output")
        elif a!="parent": raise ValueError("unknown composition")
        rows=[]; operations={}; depth=1
        if a=="parent":
            for child,value in zip(r.children,data):
                job=self.world.resolve(child.operation); d=attrs(job)
                # This bounded contract certifies the parent's own child work.
                # Other actors contribute through paid public exchange; no raw
                # private job or competence is borrowed across participants.
                fields_={z.address.key:z.value for z in view.resolve(child.operation)}
                required=("actor","context","status","spent","result")
                if any(k not in fields_ or fields_[k]!=d.get(k) for k in required): raise ValueError("paid exact child receipt required")
                addresses.extend(z.address for z in view.resolve(child.operation))
                if (job.ref.identity.namespace!="u4.operation" or self.world.head(job.ref.identity).ref!=job.ref
                    or d["actor"]!=r.actor or d["context"]!=r.context or not any(d.get(f) for f in ("c1","c2","c3","c4"))
                    or d["status"] not in ("succeeded","failed","cancelled")):
                    raise ValueError("current terminal owned movement required")
                if d.get("content_target",d.get("target")).identity!=r.target.identity: raise ValueError("child referent differs")
                if value["kind"]=="observation":
                    if value["event"]!=d["result"]: raise ValueError("child event differs")
                elif child.output not in (d.get("binding"),*indexed(d,"public.")):
                    raise ValueError("output does not belong to declared child")
                fulfilled=d["status"]=="succeeded" and value.get("complete",True) and value.get("status") not in ("declined","blocked")
                rows.append((child.operation,child.output,d["status"],d["origin"],d["destination"],d["actor"],d["polarity"],fulfilled))
                operations[child.operation]=d["spent"]
                if value["kind"]=="nested":
                    depth=max(depth,value["depth"]+1)
                    for ref,spent in value["operations"]:
                        if ref in operations and operations[ref]!=spent: raise ValueError("inconsistent descendant charge")
                        operations[ref]=spent
            if depth>4 or len(operations)>64: raise ValueError("declared nesting budget exceeded")
            for left,right in r.links:
                ca,cb=r.children[left],r.children[right]
                da,db=(attrs(self.world.resolve(c.operation)) for c in (ca,cb))
                if da["destination"]!=db["origin"]: raise ValueError("incompatible formal endpoints")
                if ca.output not in indexed(db,"source."):
                    raise ValueError("endpoint equality does not establish an actual content handoff")
        addresses=tuple(dict.fromkeys(addresses)); sources=tuple(dict.fromkeys(view.detail(z).source for z in addresses))
        operations=tuple(sorted(operations.items(),key=lambda z:(z[0].identity.namespace,z[0].identity.key,z[0].revision)))
        return dict(c4=True,request=r,recipe=recipe,data=tuple(data),addresses=addresses,sources=sources,
            child_rows=tuple(rows),operations=operations,depth=depth,
            units=1+len(addresses)+sum(1+len(sem.encode(z))//64 for z in data)+len(operations))

    def _start(self,cid,r):
        if type(r) is not CruxCompositionRequest: return super()._start(cid,r)
        if r.actor not in self._profiles or r.actor not in self._wallets or (r.actor,r.key) in self._jobs or r.actor in self._locks:
            raise ValueError("funded actor, unused key and free processing required")
        p=self._prepare_composition(r); recipe=p["recipe"]
        renewal=(r.actor,*r.inputs[1:]) if recipe.action=="commune" and recipe.polarity=="expenditure" else None
        if renewal is not None and renewal in self._renewals_used:
            raise ValueError("renewal exchange already attempted; a new exchange is required")
        base=OperationRequest(r.key,r.actor,"bind",r.context)
        d={f.name:getattr(base,f.name) for f in fields(base) if f.name not in ("participants","evidence")}
        tim=attrs(self.world.resolve(self._profiles[r.actor]))["tim"]
        rows=route(tim,self._cursors[r.actor],r.elements or recipe.elements,recipe.origin,recipe.destination,recipe.polarity)
        execution=sum(sum(x["charges"])+x["content_units"] for x in rows)
        d.update(record_type="operation",primitive="bind",c4=True,recipe=recipe.ref,recipe_key=recipe.key,
            movement=recipe.name,cue=r.cue,source_input=r.input,content_target=r.target,peer=r.peer,group=r.group,
            demand=r.demand,request_evidence_count=len(r.evidence),required=p["units"]+execution,
            completed=0,spent=0,recall_units=p["units"],route_prepare=p["units"],route_execute=execution,
            material_units=0,steps_completed=0,last_step=None,origin=recipe.origin,destination=recipe.destination,
            polarity=recipe.polarity,active_start=self._cursors[r.actor],tim=tim,status="pending",failure=None,result=None,
            children_payload=sem.encode(dict(children=tuple((c.operation,c.output) for c in r.children),links=r.links)),
            started_tick=self._now().tick,**flatten_route(rows))
        deps=tuple(dict.fromkeys((recipe.ref,self.law,r.cue,r.context,self._profiles[r.actor],*r.inputs,
            *(v for ref in r.inputs for v in self._dependencies_cross(ref)),
            *(c.operation for c in r.children),*((r.group,) if r.group else ()))))
        for prefix,values in (("input.",(r.context,r.cue,*r.inputs,*p["sources"])),("source.",r.inputs),
            ("dependency.",deps),("participant.",(r.actor,)),("lock.",(r.actor,))):
            d.update({prefix+str(i):v for i,v in enumerate(values)})
        for i,z in enumerate(p["addresses"]): d[f"evidence.delivery.{i}"],d[f"evidence.key.{i}"]=z.delivery,z.key
        ref=job_address(r.actor,r.key)
        added=() if recipe.ref.identity in self.world._heads else (definition(recipe),)
        if not added and self.world.resolve(recipe.ref)!=definition(recipe): raise ValueError("immutable composition recipe differs")
        self._batch(cid,r.actor,(*added,record(ref,"Paid C4 "+recipe.action,d)),evidence=r.inputs)
        if renewal is not None: self._renewals_used.add(renewal)
        self._jobs[r.actor,r.key]=ref; self._movement_inputs[ref.identity]=r,p,p["addresses"],p["sources"]
        self._reserve(d,ref)
        return ref

    def _commit(self,cid,actor,key):
        old,d=self._active(actor,key)
        if not d.get("c4"): return super()._commit(cid,actor,key)
        recipe=COMPOSITION_RECIPES[d["recipe_key"]]
        if d["status"]!="ready" or d["steps_completed"]!=2: raise ValueError("fully paid composition required")
        r,p,addresses,sources=self._movement_inputs[old.ref.identity]
        last=self.world.resolve(d["last_step"]); result=sem.decode(self._step_content(last)[2]["payload"])
        failure="stale_dependency" if any(self.world.head(z.identity).ref!=z for z in indexed(d,"dependency.")) else None
        changed=[]; command=None; public=None
        if failure is None:
            ref=address("c4.output",actor,key)
            binding=ObjectVersion(ref,old.writer,"Retained C4 "+recipe.action,(Role.INTERPRETATION,),
                (Account(r.target,(Proposition(r.target,"c4.data",sem.encode(result),r.context,TimeScope(self._now(),None)),),
                    self._now(),actor,sources),),occurrence=Occurrence.INTERPRETATION,
                attributes=attributes(dict(cue=r.cue,context=r.context,meaning="C4 "+recipe.action,
                    endorsement=ClaimStatus.TENTATIVE.value,confidence=None,
                    **{"link."+str(i):z for i,z in enumerate(z for z in r.inputs if z in self.participant_view(actor)._bindings)})))
            receipt=record(address("u4.receipt",cid),"Paid C4 retention",dict(actor=actor,operation="bind",work_key=ref.identity.key,
                **{k:d[k] for k in ("required","completed","spent")},**{"input."+str(i):z for i,z in enumerate((ref,*sources))}))
            command=("bind",actor,ref,addresses,receipt.ref)
            self.access.preview(command,{ref:binding,receipt.ref:receipt}); changed=[binding,receipt]; d["binding"]=ref
            if recipe.action in ("renew","commune"):
                audience=tuple(self._group(r,self.participant_view(actor))["members"])
                public=record(address("c4.message",actor,key),"Addressed C4 result",dict(payload=sem.encode(result),
                    actor=actor,operation=old.ref,context=r.context,**{"audience."+str(i):z for i,z in enumerate(audience)}))
                changed.append(public); d["public.0"]=public.ref
        # A successful review can retain a blocked child outcome. Its own paid
        # review succeeded; its declared parent outcome is explicitly incomplete.
        outcome="succeeded" if failure is None else "failed"
        event=self._event(cid,old,outcome)
        d.update(status=outcome,failure=failure,result=event.ref,finished_tick=self._now().tick)
        current=next_version(old,attributes=attributes(d))
        self._batch(cid,actor,(current,*changed,event),evidence=(old.ref,last.ref))
        if command:
            self.access._execute(command); self._cross_outputs[d["binding"]]=(result,indexed(d,"dependency."))
            if public: self._cross_public[public.ref]=dict(binding=d["binding"],context=r.context,audience=indexed(attrs(public),"audience."))
        self._jobs[actor,key]=current.ref; self._release(d,old.ref)
        return event.ref
