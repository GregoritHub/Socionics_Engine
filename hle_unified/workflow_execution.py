"""Timed workflow content on the shared C7/C6 native paid execution stack.

No side simulator: native wallets, memory receipts, exact access, material
operations, reservations, checkpoints and Model A steps remain authoritative.
Second-setting scheduling/Shell selection is not asserted by this extension.
"""
from dataclasses import fields, replace
from .selection_execution import SelectionEngine
from .workflow_records import WorkflowRequest, WORKFLOW_RECIPES, definition, registry
from . import workflow_content as sem
from .crux_content import owned_binding
from .records import ObjectVersion, Role, Account, Occurrence, Proposition, TimeScope, ClaimStatus
from .operations import OperationEngine, record, address, job_address, indexed
from .operation_records import OperationRequest
from .material import attrs, attributes
from .store import next_version
from .cognitive_routes import route, flatten_route
from .compact import seal, unseal

class WorkflowEngine(SelectionEngine):
    SCHEMA="hle-full-crux-c7-workflow-v1"
    @staticmethod
    def _registry(): return registry()
    def __init__(self,world,law):
        super().__init__(world,law)
        self._workflow_outputs={}; self._workflow_public={}; self._workflow_used=set()
    def _recipe_for(self,r): return WORKFLOW_RECIPES[r.recipe] if type(r) is WorkflowRequest else super()._recipe_for(r)
    def _step_namespace(self,r): return "c7w.step" if type(r) is WorkflowRequest else super()._step_namespace(r)
    def _semantic_step(self,name,p,previous):
        return sem.transform(name,p,previous) if p.get("c7w") else super()._semantic_step(name,p,previous)
    def _event(self,cid,job,outcome,changed=()):
        event=super()._event(cid,job,outcome,changed)
        # Chronology is a delivered occurrence time, not hidden journal access.
        return replace(event,attributes=attributes(dict(attrs(event),workflow_tick=event.facet(Account).at.tick)))
    def _declare(self,cid,versions):
        if any(v.ref.identity.namespace.startswith("c7w.") for v in versions): raise ValueError("workflow evidence cannot be imported")
        return super()._declare(cid,versions)
    def _disclose(self,cid,actor,source,selectors,subject):
        if source.identity.namespace.startswith("c7w."):
            m=self._workflow_public.get(source)
            if m is None or actor not in m["audience"]: raise ValueError("addressed workflow message required")
            v=self.world.resolve(source)
            allowed={(a.name,("attributes",str(i),"value")) for i,a in enumerate(v.attributes) if a.name=="payload"}
            if subject!=source or any((s.key,s.path) not in allowed for s in selectors): raise ValueError("public payload only")
        return super()._disclose(cid,actor,source,selectors,subject)

    def _read_workflow(self,view,ref,r):
        if ref.identity.namespace=="u4.observation":
            items=view.resolve(ref); d={p.address.key:p.value for p in items}
            if not {"event","outcome","context","primitive","actor","workflow_tick"}<=set(d): raise ValueError("paid actual event reading required")
            value=self.world.resolve(ref); event=self.world.resolve(d["event"])
            if (value.facet(Account).sources!=(event.ref,) or event.occurrence!=Occurrence.ACTUAL_EVENT
                or event.ref.identity.namespace!="u4.event" or d["context"]!=r.context
                or d.get("target",r.target).identity!=r.target.identity or d["primitive"] not in sem.PRIMITIVES):
                raise ValueError("observed target, event or activity scope differs")
            return dict(d,kind="activity"),tuple(p.address for p in items)
        if ref in view._bindings:
            b=owned_binding(view,ref)
            if (b.context,b.cue,b.target.identity)!=(r.context,r.cue,r.target.identity) or len(b.content)!=1:
                raise ValueError("owned scoped workflow input required")
            if b.content[0].relation!="c7w.data" or b.content[0].subject!=b.target or b.content[0].context!=r.context: raise ValueError("typed scoped workflow proposition required")
            d=sem.decode(b.content[0].object)
            if ref not in self._workflow_outputs: sem.authored(d)
            return d,b.particulars
        m=self._workflow_public.get(ref); items=[p for p in view.resolve(ref) if p.address.key=="payload"]
        if m is None or len(items)!=1 or r.actor not in m["audience"] or m["context"]!=r.context:
            raise ValueError("paid addressed native workflow uptake required")
        d=sem.decode(items[0].value)
        if d["target"].identity!=r.target.identity: raise ValueError("message target differs")
        return d,(items[0].address,)

    def _prepare_workflow(self,r):
        recipe=WORKFLOW_RECIPES[r.recipe]; a=recipe.action; view=self.participant_view(r.actor)
        known=self.access._known_refs(r.actor)
        if r.cue not in self._references or any(x not in known for x in (r.context,r.cue,r.target)):
            raise ValueError("processed cue, context, target required")
        if Role.CONTEXT not in self.world.resolve(r.context).roles: raise ValueError("context required")
        if any(view.detail(x) is None for x in r.evidence): raise ValueError("unread or foreign evidence")
        addresses=list(r.evidence); data=[]
        for ref in r.inputs:
            value,paid=self._read_workflow(view,ref,r);data.append(value);addresses.extend(paid)
        x=data[0]; inward=recipe.polarity=="accumulation"
        accepted={"contemplate":(("intention","stance"),2),"express":(("intention",),1),"theorize":(("intention","personal"),1),
            "embody":(("activity",),1),"act":(("activity",),1),"organize":(("activity",),None),
            "share":(("intention","personal"),3),"coordinate":(("activity",),3),"educate":(("system","rule"),3),
            "commune":(("shared",),3),"identify":(("shared",),2),"understand":(("system","rule"),2),
            "mobilize":(("shared",),1),"apply":(("system","rule"),1),"integrate":(("system",),2)}
        if a in accepted:
            kinds,count=accepted[a]
            if x["kind"] not in kinds or count is not None and len(data)!=count: raise ValueError("workflow input contract differs")
        if a in ("contemplate","integrate","organize") and any(v["kind"] not in accepted[a][0] for v in data):
            raise ValueError("heterogeneous workflow input")
        if a in ("reply","vote","identify","understand","offer"):
            if len(data)!=2: raise ValueError("source plus own stance required")
            sem.authored(data[1])
            if r.inputs[1] not in view._bindings: raise ValueError("assent must belong to this actor")
        social=a in ("offer","reply","vote","share","coordinate","educate","commune","identify","mobilize","institutionalize") or x["kind"] in ("shared","rule")
        group=None
        if social or r.group:
            group=self._group(r,view)
            if len(group["members"])!=2 or r.peer not in group["members"]: raise ValueError("two current addressed members required")
            addresses.extend(p.address for p in view.resolve(r.group))
            if x["kind"] in ("shared","rule") and (x["group"]!=r.group or set(x["participants"])!=set(group["members"])):
                raise ValueError("shared membership or scope changed")
            if any(t[5] not in group["members"] for v in data for t in v.get("tasks",())):
                raise ValueError("shared tasks require current participating assignees")
        if a=="offer":
            kinds={"I":("intention","personal"),"IT":("activity",),"WE":("shared",),"ITS":("system","rule")}
            if x["kind"] not in kinds[recipe.origin]: raise ValueError("offer source perspective differs")
        if a=="reply" and (x.get("kind"),x.get("speaker"),x.get("receiver"),x.get("group"))!=("offer",r.peer,r.actor,r.group):
            raise ValueError("exact addressed offer required")
        if a in ("share","coordinate","educate","commune"):
            offer,reply=data[1:]; tasks=x["tasks"] if x["kind"]!="activity" else sem.readiness(x)
            if (offer.get("kind"),reply.get("kind"),offer.get("source"),offer.get("speaker"),offer.get("receiver"),
                reply.get("offer"),reply.get("speaker"),reply.get("receiver"),offer.get("group"),reply.get("group"),offer.get("tasks"))!=(
                "offer","reply",r.input,r.actor,r.peer,r.inputs[1],r.peer,r.actor,r.group,r.group,tasks):
                raise ValueError("exact reciprocal exchange required")
        if a=="vote" and (x.get("kind"),x.get("status"))!=("rule","draft"): raise ValueError("exact draft required")
        if a=="institutionalize":
            if inward:
                if (len(data)<2 or x["kind"]!="shared" or any(v["kind"]!="activity" or v["outcome"]!="succeeded" for v in data[1:])
                    or any(v["actor"] not in group["members"] or v["primitive"] not in {t[1] for t in x["tasks"]} for v in data[1:])):
                    raise ValueError("shared expectation and actual relevant member practice required")
            elif (len(data)!=3 or x["kind"]!="rule" or x["status"]!="draft"
                or {v.get("speaker") for v in data[1:]}!=set(group["members"])
                or any(v.get("kind")!="vote" or v["draft"]!=r.input or v["tasks"]!=x["tasks"] or v["group"]!=r.group for v in data[1:])):
                raise ValueError("two exact current member votes required")
        if a=="use" and (len(data)!=1 or x["kind"] not in {"I":("personal",),"IT":("activity",),"WE":("shared",),"ITS":("system","rule")}[recipe.origin]):
            raise ValueError("native output consumer required")
        if a=="organize" and (any(v["outcome"]!="succeeded" for v in data)
            or not inward and any(v.get("owner")!=r.actor for v in data)):
            raise ValueError("observed successful activity and own operating authority required")
        if a=="organize" and len({v["event"] for v in data})!=len(data):
            raise ValueError("repeated readings are not distinct actual activities")
        permitted=x.get("consent",True)
        if a=="mobilize" or a=="apply" and x["kind"]=="rule": permitted=x.get("authorized",False)
        if a=="apply" and x["kind"]=="system" and x.get("authority") is not None: permitted=permitted and x["authority"]==r.actor
        if recipe.material_units:
            if not permitted: raise ValueError("personal assent and shared authority required")
            if a!="act" and not inward:
                model=sem.reconcile((x,)); first=sem.query(model,(),0)
                if first is None or first[1]!="care" or first[5]!=r.actor: raise ValueError("currently assigned first care task required")
            for ref in (r.target,r.stock,r.relation):
                if ref is not None:
                    if ref not in known: raise ValueError("processed material roles required")
                    addresses.extend(p.address for p in view.resolve(ref))
        if a=="act" and x.get("target")!=r.target: raise ValueError("Act requires current observed equipment")
        addresses=tuple(dict.fromkeys(addresses)); sources=tuple(dict.fromkeys(view.detail(v).source for v in addresses))
        return dict(c7w=True,request=r,recipe=recipe,data=tuple(data),addresses=addresses,sources=sources,group=group,permitted=permitted,
            units=1+len(addresses)+sum(1+len(sem.encode(v))//64 for v in data))

    def _start(self,cid,r):
        if type(r) is not WorkflowRequest: return super()._start(cid,r)
        if r.actor not in self._profiles or (r.actor,r.key) in self._jobs or r.actor in self._locks: raise ValueError("available funded typed actor required")
        p=self._prepare_workflow(r); recipe=p["recipe"]; native={}
        if recipe.material_units:
            primitive=("return" if recipe.polarity=="accumulation" else "transfer") if recipe.name=="Act" else ("inspect" if recipe.polarity=="accumulation" else "care")
            base=OperationRequest(r.key,r.actor,primitive,r.context,participants=() if r.peer is None else (r.peer,),evidence=r.evidence,
                target=r.target,stock=r.stock if primitive=="care" else None,recipient=r.peer if primitive=="transfer" else None,
                relation=r.relation if primitive=="return" else None)
            native=self._compile(base)
            if recipe.action=="mobilize" or p["data"][0]["kind"]=="rule":
                stamp=(r.actor,self._workflow_public.get(r.input,{}).get("binding",r.input))
                if stamp in self._workflow_used: raise ValueError("one-attempt commitment already spent")
            else: stamp=None
        else: base=OperationRequest(r.key,r.actor,"bind",r.context);stamp=None
        d={f.name:getattr(base,f.name) for f in fields(base) if f.name not in ("participants","evidence")}
        d.update({k:v for k,v in native.items() if not k.startswith(("input.","dependency.","participant.","lock.","evidence."))})
        tim=attrs(self.world.resolve(self._profiles[r.actor]))["tim"]
        rows=route(tim,self._cursors[r.actor],r.elements or recipe.elements,recipe.origin,recipe.destination,recipe.polarity)
        execution=sum(sum(row["charges"])+row["content_units"] for row in rows)
        d.update(record_type="operation",primitive=native.get("primitive","bind"),c7w=True,recipe=recipe.ref,recipe_key=recipe.key,
            movement=recipe.name,main=recipe.main,cue=r.cue,content_target=r.target,source_input=r.input,peer=r.peer,group=r.group,
            requested_stock=r.stock,requested_relation=r.relation,query_completed=sem.encode(dict(done=r.completed)),query_clock=r.clock,
            permitted=p["permitted"],request_evidence_count=len(r.evidence),required=p["units"]+execution+recipe.material_units,
            completed=0,spent=0,recall_units=p["units"],route_prepare=p["units"],route_execute=execution,material_units=recipe.material_units,
            steps_completed=0,last_step=None,origin=recipe.origin,destination=recipe.destination,polarity=recipe.polarity,
            active_start=self._cursors[r.actor],tim=tim,status="pending",failure=None,result=None,started_tick=self._now().tick,**flatten_route(rows))
        inherited=[]
        for ref in r.inputs:
            owned=self._workflow_public.get(ref,{}).get("binding",ref)
            if owned in self._workflow_outputs: inherited.extend(self._workflow_outputs[owned][1])
        deps=tuple(dict.fromkeys((recipe.ref,self.law,r.context,r.cue,self._profiles[r.actor],*r.inputs,*inherited,
            *((r.group,) if r.group else ()),*indexed(native,"dependency."))))
        for prefix,values in (("input.",(r.context,r.cue,*r.inputs,*p["sources"])),("source.",r.inputs),("dependency.",deps),
            ("participant.",indexed(native,"participant.") or (r.actor,)),("lock.",(r.actor,*indexed(native,"lock.")))):
            d.update({prefix+str(i):v for i,v in enumerate(values)})
        for i,v in enumerate(p["addresses"]): d[f"evidence.delivery.{i}"],d[f"evidence.key.{i}"]=v.delivery,v.key
        ref=job_address(r.actor,r.key)
        if not self._can_reserve(d,ref): d["status"]="waiting"
        added=() if recipe.ref.identity in self.world._heads else (definition(recipe),)
        if not added and self.world.resolve(recipe.ref)!=definition(recipe): raise ValueError("immutable workflow recipe differs")
        self._batch(cid,r.actor,(*added,record(ref,"Paid workflow "+recipe.name,d)),evidence=r.inputs)
        self._jobs[r.actor,r.key]=ref;self._movement_inputs[ref.identity]=r,p,p["addresses"],p["sources"]
        if d["status"]!="waiting": self._reserve(d,ref)
        if stamp is not None: self._workflow_used.add(stamp)
        return ref

    def _commit(self,cid,actor,key):
        old,d=self._active(actor,key)
        if not d.get("c7w"): return super()._commit(cid,actor,key)
        r,p,addresses,sources=self._movement_inputs[old.ref.identity];recipe=p["recipe"]
        if d["status"]!="ready" or d["steps_completed"]!=len(recipe.steps): raise ValueError("fully paid workflow steps required")
        last=self.world.resolve(d["last_step"]);result=sem.decode(self._step_content(last)[2]["payload"])
        if recipe.material_units and result.get("kind")=="command" and result.get("permitted"):
            if (result["primitive"],result["target"],result["stock"],result["relation"],result["peer"])!=(d["primitive"],r.target,r.stock,r.relation,r.peer):
                raise ValueError("material execution must consume exact generated command")
            return OperationEngine._commit(self,cid,actor,key)
        failure="missing_material_command" if recipe.material_units else None
        if any(self.world.head(v.identity).ref!=v for v in indexed(d,"dependency.")): failure="stale_dependency"
        if not self._can_reserve(d,old.ref): failure="reservation_unavailable"
        changed=[];command=None;public=None
        if failure is None:
            ref=address("c7w.output",actor,key)
            binding=ObjectVersion(ref,old.writer,"Retained workflow "+recipe.name,(Role.INTERPRETATION,),
                (Account(r.target,(Proposition(r.target,"c7w.data",sem.encode(result),r.context,TimeScope(self._now(),None)),),self._now(),actor,sources),),
                occurrence=Occurrence.INTERPRETATION,attributes=attributes(dict(cue=r.cue,context=r.context,meaning="Timed workflow "+recipe.name,
                    endorsement=ClaimStatus.TENTATIVE.value,confidence=None,**{"link."+str(i):v for i,v in enumerate(x for x in r.inputs if x in self.participant_view(actor)._bindings)})))
            receipt=record(address("u4.receipt",cid),"Paid workflow retention",dict(actor=actor,operation="bind",work_key=ref.identity.key,
                **{k:d[k] for k in ("required","completed","spent")},**{"input."+str(i):v for i,v in enumerate((ref,*sources))}))
            command=("bind",actor,ref,addresses,receipt.ref); self.access.preview(command,{ref:binding,receipt.ref:receipt})
            changed=[binding,receipt];d["binding"]=ref
            if recipe.destination=="WE" or recipe.action in ("offer","reply","vote","institutionalize") or (recipe.destination=="ITS" and recipe.polarity=="expenditure"):
                audience=tuple(p["group"]["members"]) if p["group"] else (actor,r.peer) if r.peer else (actor,)
                public=record(address("c7w.message",actor,key),"Scoped workflow exchange",dict(payload=sem.encode(result),actor=actor,
                    operation=old.ref,context=r.context,**{"audience."+str(i):v for i,v in enumerate(audience)}))
                changed.append(public);d["public.0"]=public.ref
        outcome="succeeded" if failure is None else "failed";event=self._event(cid,old,outcome)
        d.update(status=outcome,failure=failure,result=event.ref,finished_tick=self._now().tick)
        current=next_version(old,attributes=attributes(d));self._batch(cid,actor,(current,*changed,event),evidence=(old.ref,last.ref))
        if command:
            self.access._execute(command);self._workflow_outputs[d["binding"]]=(result,indexed(d,"dependency."))
            if public: self._workflow_public[public.ref]=dict(binding=d["binding"],context=r.context,audience=indexed(attrs(public),"audience."))
        self._jobs[actor,key]=current.ref;self._release(d,old.ref)
        return event.ref
