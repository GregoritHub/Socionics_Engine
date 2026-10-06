"""C2 over the C1 executor: eight self contracts, reciprocal exchange, consumers.

The trusted simulator controls disclosure; receivers still perform paid reads.
No request may import a completed C2 output, agreement, or material effect.
"""
from dataclasses import fields, replace
from . import self_content as sem
from .crux_execution import CruxEngine
from .crux_records import MovementRequest
from .self_records import SelfRouteRequest, SELF_RECIPES, definition, registry
from .crux_content import owned_binding
from .records import (ObjectRef, ObjectVersion, Role, Account, Occurrence, Proposition,
                      TimeScope, ClaimStatus)
from .operations import OperationEngine, address, job_address, record, indexed
from .operation_records import OperationRequest
from .material import attrs, attributes
from .store import next_version
from .cognitive_routes import route, flatten_route
from .compact import seal, unseal


class SelfRouteEngine(CruxEngine):
    SCHEMA="hle-full-crux-c2-engine-v1"

    @staticmethod
    def _registry(): return registry()

    def __init__(self, world, law):
        super().__init__(world,law)
        self._self_outputs={}
        self._self_public={}
        self._self_enacted=set()
        self._self_commitments_used=set()

    @classmethod
    def from_c1(cls,text):
        return cls.restore(seal(cls.SCHEMA,unseal(text,CruxEngine.SCHEMA)))

    def _recipe_for(self,r):
        return SELF_RECIPES[r.recipe] if type(r) is SelfRouteRequest else super()._recipe_for(r)

    def _step_namespace(self,r):
        return "c2.step" if type(r) is SelfRouteRequest else super()._step_namespace(r)

    def _semantic_step(self,name,prepared,previous):
        if "request" in prepared:
            return sem.transform(name,prepared,previous)
        return super()._semantic_step(name,prepared,previous)

    def _declare(self,cid,versions):
        if any(v.ref.identity.namespace.startswith("c2.") for v in versions):
            raise ValueError("C2 generated work and shared meaning cannot be imported")
        return super()._declare(cid,versions)

    def _disclose(self,cid,actor,source,selectors,subject):
        if source.identity.namespace.startswith("c2."):
            d=self._self_public.get(source)
            if d is None or actor not in d["audience"]:
                raise ValueError("C2 internals are private; only scoped messages are deliverable")
            v=self.world.resolve(source)
            allowed={(a.name,("attributes",str(i),"value")) for i,a in enumerate(v.attributes) if a.name=="payload"}
            if subject!=source or any((s.key,s.path) not in allowed for s in selectors):
                raise ValueError("only exact scoped public payload may be delivered")
        return super()._disclose(cid,actor,source,selectors,subject)

    def _read_content(self,view,ref,r,*,authored=False):
        if ref in view._bindings:
            b=owned_binding(view,ref)
            if b.context!=r.context or b.cue!=r.cue or b.target.identity!=r.target.identity:
                raise ValueError("content belongs to another scope or target")
            payloads=[p.object for p in b.content if p.relation=="c2.data"]
            if len(payloads)!=1 or len(b.content)!=1 or any(p.context!=r.context or p.subject!=b.target for p in b.content):
                raise ValueError("one exact scoped typed payload required")
            d=sem.decode(payloads[0])
            if authored: sem.validate(d,r.actor,r.target)
            elif ref not in self._self_outputs:
                sem.validate(d,r.actor,r.target)
            return d,b.particulars
        if authored: raise ValueError("actor-owned retained content required")
        p=[x for x in view.resolve(ref) if x.address.key=="payload"]
        if ref not in self._self_public or len(p)!=1 or self._self_public[ref]["context"]!=r.context:
            raise ValueError("received and paid-read native exchange required")
        d=sem.decode(p[0].value)
        if d.get("target",r.target).identity!=r.target.identity:
            raise ValueError("message target differs")
        return d,(p[0].address,)

    def _group(self,r,view):
        if r.group is None: raise ValueError("actual shared group required")
        g=self._read11(view,r.group,("group",))
        members=g["members"]
        if g["context"]!=r.context or r.actor not in members or r.peer is not None and r.peer not in members:
            raise ValueError("current participating members and matching context required")
        return g

    def _prepare_self(self,r):
        view=self.participant_view(r.actor); recipe=SELF_RECIPES[r.recipe]
        known=self.access._known_refs(r.actor)
        if (r.cue not in self._references or any(x not in known for x in (r.cue,r.context,r.target))
                or Role.CONTEXT not in self.world.resolve(r.context).roles):
            raise ValueError("processed cue, context, and target required")
        details=tuple(view.detail(a) for a in r.evidence)
        if any(x is None for x in details): raise ValueError("unread or foreign evidence")
        p=dict(request=r,data=[],facts=())
        addresses=list(r.evidence); group=None
        if recipe.name=="Act":
            primitive="repair" if recipe.polarity=="accumulation" else "use"
            expected=(r.target,r.tool,r.stock) if primitive=="repair" else (r.target,)
            if None in expected or r.inputs!=expected or primitive=="use" and (r.tool or r.stock):
                raise ValueError("Act input contract differs from material roles")
            base=OperationRequest(r.key,r.actor,primitive,r.context,evidence=r.evidence,
                                  target=r.target,tool=r.tool,stock=r.stock)
            p["material"]=self._compile(base)
        else:
            for ref in r.inputs:
                data,paid=self._read_content(view,ref,r,authored=recipe.name in ("Contemplate","Integrate") or ref==r.input and recipe.name in ("Offer","Reply"))
                p["data"].append(data); addresses.extend(paid)
            if recipe.name=="Contemplate":
                if len(p["data"])<2 or any(d["kind"]!="personal" for d in p["data"]):
                    raise ValueError("compare at least two owned personal contents")
            elif recipe.name=="Integrate":
                if len(p["data"])<2 or any(d["kind"]!="system" for d in p["data"]):
                    raise ValueError("two owned systems required")
                if sum(len(d["nodes"]) for d in p["data"])>16:
                    raise ValueError("combined system exceeds node budget")
            elif recipe.name in ("Offer","Reply","Commune"):
                group=self._group(r,view)
                if recipe.name=="Offer":
                    if len(p["data"])!=1 or p["data"][0]["kind"]!="stance" or r.peer is None:
                        raise ValueError("offer requires own stance and recipient")
                elif recipe.name=="Reply":
                    if len(p["data"])!=2 or p["data"][0]["kind"]!="stance": raise ValueError("own reply stance required")
                    offer=p["data"][1]
                    if (offer.get("kind")!="offer" or offer["receiver"]!=r.actor or offer["speaker"]!=r.peer or offer["group"]!=r.group):
                        raise ValueError("reply needs the exact addressed offer")
                else:
                    if len(p["data"])!=2: raise ValueError("reciprocal offer and reply required")
                    offer,reply=p["data"]
                    if (offer.get("kind")!="offer" or reply.get("kind")!="reply"
                            or (offer["speaker"],offer["receiver"])!=(r.actor,r.peer)
                            or (reply["speaker"],reply["receiver"])!=(r.peer,r.actor)
                            or reply["offer"]!=r.inputs[0] or reply["understood"]!=offer["cap"]
                            or offer["group"]!=r.group or reply["group"]!=r.group):
                        raise ValueError("exact reciprocal understanding required")
            elif recipe.name=="Consume":
                if len(p["data"])!=1: raise ValueError("one consumed result required")
                data=p["data"][0]
                if data["kind"]=="shared":
                    group=self._group(r,view)
                    if r.actor not in data["participants"] or data["group"]!=r.group:
                        raise ValueError("shared content does not authorize this participant")
                if data["kind"] in ("system","reconciled_model","organization"):
                    # Only exact paid-read fields supply concrete conditions.
                    values={x.address.key:x.value for x in details if x.subject==r.target}
                    if values.get("condition") not in ("damaged","serviceable"):
                        raise ValueError("system use requires processed current condition evidence")
                    p["facts"]=(values["condition"],)
                    if data["kind"]=="organization" and data["authority"]!=r.actor:
                        raise ValueError("coupling cannot borrow authority")
        if group is not None:
            addresses.extend(x.address for x in view.resolve(r.group))
        addresses=tuple(dict.fromkeys(addresses))
        sources=tuple(dict.fromkeys(view.detail(a).source for a in addresses))
        p["addresses"],p["sources"]=addresses,sources
        p["data"]=tuple(p["data"])
        p["units"]=1+len(addresses)+sum(1+len(sem.encode(d))//64 for d in p["data"])
        return p

    def _start(self,cid,request):
        if type(request) is not SelfRouteRequest: return super()._start(cid,request)
        r=request; recipe=SELF_RECIPES[r.recipe]
        if (r.actor not in self._profiles or r.actor not in self._wallets
                or (r.actor,r.key) in self._jobs or r.actor in self._locks):
            raise ValueError("funded typed actor, unused key and free processing required")
        p=self._prepare_self(r); view=self.participant_view(r.actor)
        tim=attrs(self.world.resolve(self._profiles[r.actor]))["tim"]
        rows=route(tim,self._cursors[r.actor],r.elements or recipe.elements,
                   recipe.origin,recipe.destination,recipe.polarity)
        base=OperationRequest(r.key,r.actor,"bind",r.context)
        d={f.name:getattr(base,f.name) for f in fields(base) if f.name not in ("participants","evidence")}
        native=p.get("material",{})
        d.update({k:v for k,v in native.items() if not k.startswith(("dependency.","input.","lock.","participant.","evidence."))})
        semantic=sum(sum(row["charges"])+row["content_units"] for row in rows)
        d.update(record_type="operation",primitive=native.get("primitive","bind"),c2=True,
            recipe=recipe.ref,recipe_key=recipe.key,movement=recipe.name,cue=r.cue,
            source_input=r.input,target=r.target,peer=r.peer,group=r.group,demand=r.demand,
            request_evidence_count=len(r.evidence),
            requested_tool=r.tool,requested_stock=r.stock,
            required=p["units"]+semantic+recipe.material_units,completed=0,spent=0,
            recall_units=p["units"],route_prepare=p["units"],route_execute=semantic,
            material_units=recipe.material_units,steps_completed=0,last_step=None,
            origin=recipe.origin,destination=recipe.destination,polarity=recipe.polarity,
            active_start=self._cursors[r.actor],tim=tim,status="pending",failure=None,result=None,
            started_tick=self._now().tick,**flatten_route(rows))
        inherited=[]
        for source in r.inputs:
            owned=self._self_public[source]["binding"] if source in self._self_public else source
            if owned in self._self_outputs: inherited.extend(self._self_outputs[owned][1])
        dependencies=(recipe.ref,self.law,r.context,r.cue,self._profiles[r.actor],*r.inputs,*inherited,
                      *((r.group,) if r.group else ()),*indexed(native,"dependency."))
        # Concrete target may be a historical referent for a model; material
        # operations themselves retain exact current-role dependencies.
        for prefix,values in (("input.",(r.context,r.cue,*r.inputs,*p["sources"])),
                ("source.",r.inputs),("dependency.",tuple(dict.fromkeys(dependencies))),
                ("participant.",(r.actor,)),("lock.",(r.actor,*indexed(native,"lock.")))):
            d.update({prefix+str(i):v for i,v in enumerate(values)})
        for i,a in enumerate(p["addresses"]): d[f"evidence.delivery.{i}"],d[f"evidence.key.{i}"]=a.delivery,a.key
        ref=job_address(r.actor,r.key)
        if not self._can_reserve(d,ref): d["status"]="waiting"
        added=() if recipe.ref.identity in self.world._heads else (definition(recipe),)
        if not added and self.world.resolve(recipe.ref)!=definition(recipe): raise ValueError("immutable recipe mismatch")
        self._batch(cid,r.actor,(*added,record(ref,"Paid C2 "+recipe.name,d)),evidence=tuple(r.inputs))
        self._jobs[r.actor,r.key]=ref
        if d["status"]!="waiting": self._reserve(d,ref)
        self._movement_inputs[ref.identity]=r,p,p["addresses"],p["sources"]
        return ref

    def _public_value(self,r,key,data,audience,operation):
        ref=address("c2.message",r.actor,r.key,key)
        return record(ref,"Scoped C2 exchange",dict(payload=sem.encode(data),operation=operation,
            actor=r.actor,context=r.context,**{"audience."+str(i):a for i,a in enumerate(audience)}))

    def _commit(self,cid,actor,key):
        old,d=self._active(actor,key)
        if not d.get("c2"): return super()._commit(cid,actor,key)
        recipe=SELF_RECIPES[d["recipe_key"]]
        if d["status"]!="ready" or d["steps_completed"]!=len(recipe.steps):
            raise ValueError("fully paid semantic result required")
        r,p,addresses,sources=self._movement_inputs[old.ref.identity]
        last=self.world.resolve(d["last_step"])
        result=sem.decode(self._step_content(last)[2]["payload"])
        if recipe.name=="Act" and result.get("kind")=="material_command":
            if any(result[k]!=d[k] for k in ("primitive","target","tool","stock")):
                raise ValueError("physical execution must consume generated command")
            return OperationEngine._commit(self,cid,actor,key)
        failure=None
        if any(self.world.head(ref.identity).ref!=ref for ref in indexed(d,"dependency.")):
            failure="stale_dependency"
        if recipe.name=="Act": failure="missing_material_command"
        if not self._can_reserve(d,old.ref): failure="reservation_unavailable"
        changed=[]; command=None; public=[]
        if failure is None:
            ref=address("c2.output",actor,key)
            binding=ObjectVersion(ref,old.writer,"Retained C2 "+recipe.name,(Role.INTERPRETATION,),
                (Account(r.target,(Proposition(r.target,"c2.data",sem.encode(result),r.context,TimeScope(self._now(),None)),),
                    self._now(),actor,sources),),occurrence=Occurrence.INTERPRETATION,
                attributes=attributes(dict(cue=r.cue,context=r.context,meaning="C2 "+recipe.name,
                    endorsement=ClaimStatus.TENTATIVE.value,confidence=None,**{"link."+str(i):x for i,x in enumerate(x for x in r.inputs if x in self.participant_view(actor)._bindings)})))
            receipt=record(address("u4.receipt",cid),"Paid C2 retention",dict(actor=actor,operation="bind",work_key=ref.identity.key,
                **{k:d[k] for k in ("required","completed","spent")},**{"input."+str(i):x for i,x in enumerate((ref,*sources))}))
            command=("bind",actor,ref,addresses,receipt.ref)
            self.access.preview(command,{ref:binding,receipt.ref:receipt})
            changed=[binding,receipt]; d["binding"]=ref
            if recipe.name in ("Offer","Reply","Commune"):
                audience=(r.actor,r.peer)
                public.append(self._public_value(r,"exchange",result,audience,old.ref))
            elif recipe.name=="Consume" and result["action"]=="propose":
                public.append(self._public_value(r,"proposal",dict(kind="participation_proposal",amount=result["amount"],
                    source=r.input,group=r.group,target=r.target,speaker=r.actor),result["participants"],old.ref))
            changed.extend(public)
            for i,v in enumerate(public): d["public."+str(i)]=v.ref
        outcome="succeeded" if failure is None else "failed"
        event=self._event(cid,old,outcome)
        d.update(status=outcome,failure=failure,result=event.ref,finished_tick=self._now().tick)
        current=next_version(old,attributes=attributes(d))
        self._batch(cid,actor,(current,*changed,event),evidence=(old.ref,last.ref))
        if command:
            self.access._execute(command)
            self._self_outputs[d["binding"]]=(result,tuple(indexed(d,"dependency.")))
            for v in public: self._self_public[v.ref]=dict(audience=indexed(attrs(v),"audience."),data=result,context=r.context,binding=d["binding"])
        self._jobs[actor,key]=current.ref; self._release(d,old.ref)
        return event.ref

    def _enact(self,cid,actor,key,plan):
        if plan.identity.namespace!="c2.output": return super()._enact(cid,actor,key,plan)
        if plan in self._self_enacted or plan not in self._self_outputs:
            raise ValueError("unused completed C2 decision required")
        b=owned_binding(self.participant_view(actor),plan)
        result,deps=self._self_outputs[plan]
        if result["kind"]!="decision" or result["action"] not in ("inspect","use","repair","care","consume","damage"):
            raise ValueError("this content is a prediction or proposal, not an executable decision")
        if any(self.world.head(x.identity).ref!=x for x in deps): raise ValueError("decision dependencies or authority changed")
        op=result["action"]
        commitment=None
        if op=="consume":
            source=result["source"]
            commitment=self._self_public[source]["binding"] if source in self._self_public else source
            if (actor,commitment) in self._self_commitments_used:
                raise ValueError("this participant already exercised the one-attempt commitment")
        r=OperationRequest(key,actor,op,b.context,evidence=b.particulars,
            target=None if op=="consume" else result["target"],
            tool=result["tool"] if op=="repair" else None,
            stock=result["stock"] if op in ("repair","care","consume") else None,
            amount=result["amount"] if op=="consume" else 1)
        d=self._compile(r); d["c2_consumer"]=plan
        if commitment is not None: d["c2_commitment"]=commitment
        dependencies=tuple(dict.fromkeys((*indexed(d,"dependency."),plan,*deps)))
        d={k:v for k,v in d.items() if not k.startswith("dependency.")}
        d.update({"dependency."+str(i):x for i,x in enumerate(dependencies)})
        ref=job_address(actor,key)
        d["status"]="pending" if self._can_reserve(d,ref) else "waiting"
        self._batch(cid,actor,(record(ref,"C2 downstream material work",d),),evidence=(plan,*indexed(d,"input.")))
        self._jobs[actor,key]=ref
        if d["status"]=="pending": self._reserve(d,ref)
        self._self_enacted.add(plan)
        if commitment is not None: self._self_commitments_used.add((actor,commitment))
        return ref
