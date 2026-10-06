"""Twenty-four bounded crossing realizations on the shared paid executor.

Private meanings, received fields, reciprocal uptake, exact votes and physical
authority stay distinct. No completed output can be supplied through declare.
"""
from dataclasses import fields
from .self_execution import SelfRouteEngine
from .crossing_records import CrossingRequest, CROSSING_RECIPES, definition, registry
from . import crossing_content as sem
from .crux_content import owned_binding
from .records import ObjectVersion, Role, Account, Occurrence, Proposition, TimeScope, ClaimStatus
from .operations import OperationEngine, address, job_address, record, indexed
from .operation_records import OperationRequest
from .material import attrs, attributes
from .store import next_version
from .cognitive_routes import route, flatten_route
from .compact import seal, unseal

class CrossingEngine(SelfRouteEngine):
    SCHEMA="hle-full-crux-c3-engine-v1"
    @staticmethod
    def _registry(): return registry()

    def __init__(self,world,law):
        super().__init__(world,law)
        self._cross_outputs={}; self._cross_public={}; self._cross_used=set()

    @classmethod
    def from_c2(cls,text):
        return cls.restore(seal(cls.SCHEMA,unseal(text,SelfRouteEngine.SCHEMA)))

    def _recipe_for(self,r):
        return CROSSING_RECIPES[r.recipe] if type(r) is CrossingRequest else super()._recipe_for(r)

    def _step_namespace(self,r):
        return "c3.step" if type(r) is CrossingRequest else super()._step_namespace(r)

    def _semantic_step(self,name,p,previous):
        return sem.transform(name,p,previous) if p.get("c3") else super()._semantic_step(name,p,previous)

    def _semantic_command(self,d,kind,target,values):
        if kind=="c3":
            result=sem.decode(values["payload"])
            if result.get("kind")=="material_command":
                if result["primitive"]!=d["primitive"] or result["stock"]!=d["requested_stock"]:
                    raise ValueError("generated command differs from reserved physical roles")
                d["amount"]=result["amount"]
        return super()._semantic_command(d,kind,target,values)

    def _declare(self,cid,versions):
        if any(v.ref.identity.namespace.startswith("c3.") for v in versions):
            raise ValueError("C3 results, votes and intermediate work cannot be imported")
        return super()._declare(cid,versions)

    def _disclose(self,cid,actor,source,selectors,subject):
        if source.identity.namespace.startswith("c3."):
            m=self._cross_public.get(source)
            if m is None or actor not in m["audience"]:
                raise ValueError("only addressed C3 messages may be disclosed")
            value=self.world.resolve(source)
            allowed={(a.name,("attributes",str(i),"value")) for i,a in enumerate(value.attributes) if a.name=="payload"}
            if subject!=source or any((s.key,s.path) not in allowed for s in selectors):
                raise ValueError("only exact public payload may be disclosed")
        return super()._disclose(cid,actor,source,selectors,subject)

    def _read_cross(self,view,ref,r):
        if ref.identity.namespace=="u4.observation":
            items=view.resolve(ref)
            d={p.address.key:p.value for p in items}
            if not {"event","outcome","context","primitive","actor"}<=set(d):
                raise ValueError("received and paid-read actual observation required")
            obs=self.world.resolve(ref)
            ev=self.world.resolve(d["event"])
            if (obs.facet(Account).sources!=(d["event"],) or ev.occurrence!=Occurrence.ACTUAL_EVENT
                or ev.ref.identity.namespace!="u4.event" or d["context"]!=r.context):
                raise ValueError("actual scoped event provenance required")
            return dict(d,kind="observation"),tuple(p.address for p in items)
        if ref in view._bindings:
            b=owned_binding(view,ref)
            if b.context!=r.context or b.cue!=r.cue or b.target.identity!=r.target.identity:
                raise ValueError("owned content scope differs")
            if len(b.content)!=1 or b.content[0].relation not in ("c3.data","c2.data"):
                raise ValueError("one typed content payload required")
            prop=b.content[0]
            if prop.subject!=b.target or prop.context!=r.context: raise ValueError("invalid proposition scope")
            d=sem.decode(prop.object)
            if ref not in self._cross_outputs and ref not in self._self_outputs: sem.intention(d)
            return d,b.particulars
        messages=self._cross_public if ref in self._cross_public else self._self_public
        m=messages.get(ref)
        values=[p for p in view.resolve(ref) if p.address.key=="payload"]
        if m is None or len(values)!=1 or m["context"]!=r.context or r.actor not in m["audience"]:
            raise ValueError("addressed paid-read native output required")
        d=sem.decode(values[0].value)
        if d.get("target",r.target).identity!=r.target.identity: raise ValueError("message target differs")
        return d,(values[0].address,)

    def _prepare_cross(self,r):
        recipe=CROSSING_RECIPES[r.recipe]; a=recipe.action; view=self.participant_view(r.actor)
        known=self.access._known_refs(r.actor)
        if r.cue not in self._references or any(x not in known for x in (r.cue,r.context,r.target)) or Role.CONTEXT not in self.world.resolve(r.context).roles:
            raise ValueError("processed cue, context and target required")
        paid=[view.detail(x) for x in r.evidence]
        if any(x is None for x in paid): raise ValueError("unread or foreign evidence")
        data=[]; addresses=list(r.evidence)
        for ref in r.inputs:
            d,extra=self._read_cross(view,ref,r); data.append(d); addresses.extend(extra)
        x=data[0]; face=recipe.polarity
        social=a in ("share","coordinate","educate","offer","reply","vote","institutionalize","identify","mobilize")
        if x["kind"] in ("shared","rule"): social=True
        group=None
        if social or r.group is not None:
            group=self._group(r,view)
            if len(group["members"])!=2: raise ValueError("C3 exchange requires exactly two members")
            if r.peer is None and a in ("share","coordinate","educate","offer","reply","institutionalize"):
                raise ValueError("addressed peer required")
            addresses.extend(p.address for p in view.resolve(r.group))
            if x["kind"] in ("shared","rule") and (x["group"]!=r.group or set(x["participants"])!=set(group["members"])):
                raise ValueError("shared scope or membership differs")
        source_assent=True
        if a in ("express","theorize"):
            if len(data)!=1: raise ValueError("one owned intention required")
            sem.intention(x)
        elif a in ("embody","organize"):
            if (a=="embody" and len(data)!=1) or any(d["kind"]!="observation" for d in data):
                raise ValueError("actual observations required")
            if a=="organize" and (any(d["outcome"]!="succeeded" or "available" not in d for d in data)
                or face=="expenditure" and any(d.get("owner")!=r.actor for d in data)):
                raise ValueError("observed stock and own authority required")
        elif a in ("identify","understand"):
            expected=("shared",) if a=="identify" else ("model","rule")
            if len(data)!=2 or x["kind"] not in expected: raise ValueError("source and own stance required")
            sem.intention(data[1])
        elif a in ("apply","mobilize"):
            expected=("model","rule") if a=="apply" else ("shared",)
            if len(data)!=1 or x["kind"] not in expected: raise ValueError("generated model or shared intention required")
        elif a=="offer":
            kinds={"I":("intention",),"IT":("observation",),"ITS":("model","rule")}
            if len(data)!=1 or x["kind"] not in kinds[recipe.origin]: raise ValueError("offer source perspective differs")
        elif a=="reply":
            if (len(data)!=2 or x["kind"]!="offer" or x["receiver"]!=r.actor
                or x["speaker"]!=r.peer or x["group"]!=r.group): raise ValueError("exact addressed offer required")
            sem.intention(data[1])
        elif a=="vote":
            if len(data)!=2 or x["kind"]!="rule" or x["status"]!="draft": raise ValueError("exact draft and own assent required")
            sem.intention(data[1])
        elif a in ("share","coordinate","educate"):
            kinds={"share":("intention",),"coordinate":("observation",),"educate":("model","rule")}
            if len(data)!=3 or x["kind"] not in kinds[a]: raise ValueError("source plus actual exchange required")
            offer,reply=data[1:]
            if (offer.get("kind"),reply.get("kind"),offer.get("source"),offer.get("speaker"),offer.get("receiver"),
                reply.get("offer"),reply.get("speaker"),reply.get("receiver"),offer.get("group"),reply.get("group"),
                offer.get("cap"),reply.get("understood"),reply.get("answer")) != (
                "offer","reply",r.input,r.actor,r.peer,r.inputs[1],r.peer,r.actor,r.group,r.group,
                sem.cap(x),sem.cap(x),sem.bounded(sem.cap(x),offer.get("question_demand",0))):
                raise ValueError("actual reciprocal understanding differs from source")
            source_assent=x.get("consent",True)
        elif a=="institutionalize":
            if face=="accumulation":
                if (len(data)!=2 or x["kind"]!="shared" or data[1]["kind"]!="observation"
                    or data[1]["outcome"]!="succeeded" or data[1]["primitive"]!="consume"):
                    raise ValueError("shared expectation and witnessed practice required")
                ev=self.world.resolve(data[1]["event"])
                if not set(x["participants"])<=set(indexed(attrs(ev),"participant.")):
                    raise ValueError("practice must involve the shared participants")
            else:
                if len(data)!=3 or x["kind"]!="rule" or x["status"]!="draft": raise ValueError("draft plus two exact votes required")
                votes=data[1:]
                if (set(d.get("speaker") for d in votes)!=set(group["members"])
                    or any(d.get("kind")!="vote" or d["draft"]!=r.input or d["cap"]!=x["cap"] or d["group"]!=r.group for d in votes)):
                    raise ValueError("unanimous process requires each exact participant vote")
        elif a=="use":
            kinds={"I":("intention","personal_policy"),"IT":("observation",),
                "WE":("shared",),"ITS":("model","rule")}
            if len(data)!=1 or x["kind"] not in kinds[recipe.origin]: raise ValueError("consumer perspective/schema differs")
        else: raise ValueError("unknown operation")
        material_assent=x.get("consent",True)
        if a=="mobilize": material_assent=x.get("authorized",False)
        if a=="apply" and x["kind"]=="rule": material_assent=x.get("authorized",False)
        if a=="apply" and x.get("status")=="governed_arrangement": material_assent=x["authority"]==r.actor
        if recipe.material_units and (r.stock is None or not material_assent):
            raise ValueError("actual readiness/performance requires stock and explicit participation authority")
        if r.stock is not None:
            if r.stock not in known: raise ValueError("processed current stock required")
            addresses.extend(p.address for p in view.resolve(r.stock))
        available=None
        fields_={p.address.key:p.value for p in view.resolve(r.stock)} if r.stock else {}
        if "quantity" in fields_ and "consumed" in fields_: available=fields_["quantity"]-fields_["consumed"]
        addresses=tuple(dict.fromkeys(addresses))
        sources=tuple(dict.fromkeys(view.detail(a).source for a in addresses))
        return dict(c3=True,request=r,recipe=recipe,data=tuple(data),addresses=addresses,sources=sources,
            source_assent=source_assent,material_assent=material_assent,available=available,
            units=1+len(addresses)+sum(1+len(sem.encode(d))//64 for d in data))

    def _dependencies_cross(self,ref):
        for messages,outputs in ((self._cross_public,self._cross_outputs),(self._self_public,self._self_outputs)):
            owned=messages[ref]["binding"] if ref in messages else ref
            if owned in outputs: return outputs[owned][1]
        return ()

    def _authority_cross(self,ref):
        for public in (self._cross_public,self._self_public):
            if ref in public: return public[ref]["binding"]
        return ref

    def _used_cross(self,stamp):
        return stamp in self._cross_used or stamp in self._self_commitments_used

    def _spend_cross(self,stamp):
        self._cross_used.add(stamp)
        if stamp[1] in self._self_outputs:
            self._self_commitments_used.add(stamp)

    def _start(self,cid,r):
        if type(r) is not CrossingRequest: return super()._start(cid,r)
        if r.actor not in self._profiles or r.actor not in self._wallets or (r.actor,r.key) in self._jobs or r.actor in self._locks:
            raise ValueError("funded actor, unused key and free processing required")
        p=self._prepare_cross(r); recipe=p["recipe"]
        native={}; stamp=None
        if recipe.material_units:
            # Reserve physical roles, but obtain the command only from the paid
            # semantic result. Amount is installed and checked at commit.
            primitive="inspect" if recipe.polarity=="accumulation" and recipe.action!="apply" else "consume"
            base=OperationRequest(r.key,r.actor,primitive,r.context,evidence=r.evidence,
                target=r.stock if primitive=="inspect" else None,stock=r.stock if primitive=="consume" else None)
            native=self._compile(base)
            if recipe.action=="mobilize" or p["data"][0]["kind"]=="rule":
                stamp=(r.actor,self._authority_cross(r.input))
                if self._used_cross(stamp): raise ValueError("participation allowance already attempted")
        else: base=OperationRequest(r.key,r.actor,"bind",r.context)
        d={f.name:getattr(base,f.name) for f in fields(base) if f.name not in ("participants","evidence")}
        d.update({k:v for k,v in native.items() if not k.startswith(("input.","dependency.","participant.","lock.","evidence."))})
        tim=attrs(self.world.resolve(self._profiles[r.actor]))["tim"]
        rows=route(tim,self._cursors[r.actor],r.elements or recipe.elements,recipe.origin,recipe.destination,recipe.polarity)
        execution=sum(sum(x["charges"])+x["content_units"] for x in rows)
        d.update(record_type="operation",primitive=native.get("primitive","bind"),c3=True,recipe=recipe.ref,
            recipe_key=recipe.key,movement=recipe.name,main=recipe.main,cue=r.cue,source_input=r.input,
            content_target=r.target,requested_stock=r.stock,peer=r.peer,group=r.group,demand=r.demand,
            request_evidence_count=len(r.evidence),source_assent=p["source_assent"],material_assent=p["material_assent"],
            observed_available=p["available"],required=p["units"]+execution+recipe.material_units,completed=0,spent=0,
            recall_units=p["units"],route_prepare=p["units"],route_execute=execution,material_units=recipe.material_units,
            steps_completed=0,last_step=None,origin=recipe.origin,destination=recipe.destination,polarity=recipe.polarity,
            active_start=self._cursors[r.actor],tim=tim,status="pending",failure=None,result=None,
            started_tick=self._now().tick,**flatten_route(rows))
        deps=(recipe.ref,self.law,r.cue,r.context,self._profiles[r.actor],*r.inputs,
            *(v for ref in r.inputs for v in self._dependencies_cross(ref)),
            *((r.group,) if r.group else ()),*indexed(native,"dependency."))
        if recipe.action=="use" and r.stock: deps=(*deps,r.stock)
        for prefix,values in (("input.",(r.context,r.cue,*r.inputs,*p["sources"])),("source.",r.inputs),
            ("dependency.",tuple(dict.fromkeys(deps))),("participant.",(r.actor,)),("lock.",(r.actor,*indexed(native,"lock.")))):
            d.update({prefix+str(i):v for i,v in enumerate(values)})
        for i,v in enumerate(p["addresses"]): d[f"evidence.delivery.{i}"],d[f"evidence.key.{i}"]=v.delivery,v.key
        ref=job_address(r.actor,r.key)
        if not self._can_reserve(d,ref): d["status"]="waiting"
        added=() if recipe.ref.identity in self.world._heads else (definition(recipe),)
        if not added and self.world.resolve(recipe.ref)!=definition(recipe): raise ValueError("immutable recipe differs")
        self._batch(cid,r.actor,(*added,record(ref,"Paid C3 "+recipe.name,d)),evidence=r.inputs)
        self._jobs[r.actor,r.key]=ref
        self._movement_inputs[ref.identity]=r,p,p["addresses"],p["sources"]
        if d["status"]!="waiting": self._reserve(d,ref)
        if stamp is not None: self._spend_cross(stamp)
        return ref

    def _commit(self,cid,actor,key):
        old,d=self._active(actor,key)
        if not d.get("c3"): return super()._commit(cid,actor,key)
        recipe=CROSSING_RECIPES[d["recipe_key"]]
        if d["status"]!="ready" or d["steps_completed"]!=len(recipe.steps): raise ValueError("fully paid crossing required")
        r,p,addresses,sources=self._movement_inputs[old.ref.identity]
        last=self.world.resolve(d["last_step"]); result=sem.decode(self._step_content(last)[2]["payload"])
        if recipe.material_units and result.get("kind")=="material_command" and result["permitted"] and result["amount"]>0:
            if result["primitive"]!=d["primitive"] or result["stock"]!=r.stock:
                raise ValueError("actual work must consume its generated command")
            if result["amount"]!=d["amount"]: raise ValueError("material amount bypassed its generated command")
            return OperationEngine._commit(self,cid,actor,key)
        failure="missing_material_command" if recipe.material_units else None
        if any(self.world.head(x.identity).ref!=x for x in indexed(d,"dependency.")): failure="stale_dependency"
        if not self._can_reserve(d,old.ref): failure="reservation_unavailable"
        changed=[]; command=None; public=None
        if failure is None:
            ref=address("c3.output",actor,key)
            binding=ObjectVersion(ref,old.writer,"Retained C3 "+recipe.name,(Role.INTERPRETATION,),
                (Account(r.target,(Proposition(r.target,"c3.data",sem.encode(result),r.context,TimeScope(self._now(),None)),),
                    self._now(),actor,sources),),occurrence=Occurrence.INTERPRETATION,
                attributes=attributes(dict(cue=r.cue,context=r.context,meaning="C3 "+recipe.name,
                    endorsement=ClaimStatus.TENTATIVE.value,confidence=None,
                    **{"link."+str(i):x for i,x in enumerate(x for x in r.inputs if x in self.participant_view(actor)._bindings)})))
            receipt=record(address("u4.receipt",cid),"Paid C3 retention",dict(actor=actor,operation="bind",work_key=ref.identity.key,
                **{k:d[k] for k in ("required","completed","spent")},**{"input."+str(i):x for i,x in enumerate((ref,*sources))}))
            command=("bind",actor,ref,addresses,receipt.ref)
            self.access.preview(command,{ref:binding,receipt.ref:receipt})
            changed=[binding,receipt]; d["binding"]=ref
            publish=recipe.action in ("offer","reply","vote","share","coordinate","educate","institutionalize") or (
                recipe.action in ("theorize","organize") and recipe.polarity=="expenditure") or (recipe.action=="use" and r.group)
            if publish:
                audience=(actor,r.peer) if r.peer else (actor,)
                if r.group: audience=tuple(self._group(r,self.participant_view(actor))["members"])
                public=record(address("c3.message",actor,key),"Scoped C3 public result",dict(payload=sem.encode(result),
                    actor=actor,operation=old.ref,context=r.context,**{"audience."+str(i):a for i,a in enumerate(audience)}))
                changed.append(public); d["public.0"]=public.ref
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

    def _enact(self,cid,actor,key,plan):
        if plan.identity.namespace!="c3.output": return super()._enact(cid,actor,key,plan)
        b=owned_binding(self.participant_view(actor),plan)
        result,deps=self._cross_outputs[plan]
        if result["kind"]!="decision" or result["action"]!="consume" or not result["permitted"]:
            raise ValueError("a proposal or draft is not performance authority")
        source=result["source"]; source_stamp=self._authority_cross(source)
        if self._used_cross((actor,source_stamp)) or self._used_cross((actor,plan)):
            raise ValueError("one-attempt decision or participation already used")
        if any(self.world.head(x.identity).ref!=x for x in deps): raise ValueError("stale content or authority")
        r=OperationRequest(key,actor,"consume",b.context,evidence=b.particulars,stock=result["stock"],amount=result["amount"])
        d=self._compile(r); all_deps=tuple(dict.fromkeys((*indexed(d,"dependency."),plan,*deps)))
        d={k:v for k,v in d.items() if not k.startswith("dependency.")}
        d.update({"dependency."+str(i):x for i,x in enumerate(all_deps)})
        d.update(c3_consumer=plan,c3_authority=source_stamp)
        ref=job_address(actor,key); d["status"]="pending" if self._can_reserve(d,ref) else "waiting"
        self._batch(cid,actor,(record(ref,"C3 downstream material use",d),),evidence=(plan,*indexed(d,"input.")))
        self._jobs[actor,key]=ref
        if d["status"]=="pending": self._reserve(d,ref)
        self._spend_cross((actor,plan)); self._spend_cross((actor,source_stamp))
        return ref
