"""U11 coordination on the U10 authoritative lifecycle and exact object graph.

This is a trusted simulator service. Policies receive participant_view(), never
world heads, job diagnostics, projection caches or another actor's work records.
"""
from copy import deepcopy
from dataclasses import fields, replace
from . import codec, nesting
from .records import (ObjectId, ObjectRef, ObjectVersion, Role, Composition, Governance,
    Relation, Endpoint, TimeScope, Attribute, Material, Procedure, Account, Occurrence,
    Lineage, ChangeKind, Definition, Proposition, ClaimStatus)
from .material import attrs as raw_attrs, attributes
from .store import next_version
from .development import record
from .development_values import attrs
from .operations import address, job_address, indexed
from .operation_records import OperationRequest, WRITER, SIGNATURES
from .cognitive_routes import route, flatten_route, progress
from .grounded_language import LanguageEngine
from .collective_records import CollectiveRequest, LAW11, registry, world_contract


class CollectiveEngine(LanguageEngine):
    SCHEMA = "hle-unified-u11-engine-v1"

    @staticmethod
    def _registry(): return registry()

    def __init__(self, world, law):
        super().__init__(world, law)
        self._inputs11, self._records11, self._heads11, self._used11 = {}, {}, {}, set()
        self._duties11 = {}

    def _declare(self, cid, versions):
        if any(v.ref.identity.namespace.startswith("u11.") for v in versions):
            raise ValueError("collective work, membership and capacity cannot be imported")
        return super()._declare(cid, versions)

    def _batch(self, cid, actor, versions, *, evidence=(), material=()):
        # U2 requires distinct lineage when the composition facet changes.
        edges = []
        for value in versions:
            kind, inputs = ChangeKind.CREATE, ()
            if value.previous is not None:
                old = self.world.resolve(value.previous)
                kind, inputs = ChangeKind.REVISE, (value.previous,)
                if old.definition != value.definition or old.facet(Definition) != value.facet(Definition):
                    kind = ChangeKind.DEFINITION
                elif old.facet(Composition) != value.facet(Composition):
                    kind = ChangeKind.MEMBERSHIP
            if value.ref in material: kind = ChangeKind.MATERIAL
            edges.append(Lineage(kind, inputs, (value.ref,), evidence, "U4 common operation lifecycle",
                                 self.law if kind == ChangeKind.MATERIAL else None))
        return self.world.commit("u4:"+cid, WRITER, tuple(versions), tuple(edges), actor=actor)

    def _public11(self, d):
        # Dependencies and physical selection plans stay on the simulator side.
        return {k:v for k,v in d.items() if k not in
                ("sources", "operation", "dependencies", "visits", "request", "evidence")}

    def _value11(self, d):
        value = record(d["ref"], "Collective "+d["kind"],
                       {**d, "payload":codec.dumps(tuple(sorted(self._public11(d).items())))})
        if d["kind"] == "group":
            value = replace(value, roles=(Role.RECORD, Role.COLLECTIVE), facets=(
                Composition(d["members"], d["boundary"], d["resources"], d["dependencies"]), Governance()))
        elif d["kind"] == "commitment":
            value = replace(value, roles=(Role.RECORD, Role.COMMITMENT), facets=(
                Relation("collective_work_due", (Endpoint("promisor", ObjectRef(d["owner"],1)),
                    Endpoint("collective",d["group"]), Endpoint("run",d["run"])),
                    True,d["context"],TimeScope(self._now(),None),attributes(
                        {"status":d["status"],"permission_active":d["permission_active"]})),))
        elif d["kind"] in ("plan", "capacity"):
            value = replace(value, roles=(Role.RECORD,Role.PROCEDURE), facets=(
                Procedure((),(),(),(),"u11.constituent-work.v1"),))
        return value

    def _current11(self, ref, kinds=None):
        d = self._records11.get(ref)
        if d is None or self._heads11.get(ref.identity) != ref or kinds and d["kind"] not in kinds:
            raise ValueError("current collective record required")
        return d

    def _read11(self, view, ref, kinds=None, *, current=True):
        d = self._current11(ref,kinds) if current else self._records11[ref]
        if kinds and d["kind"] not in kinds: raise ValueError("wrong collective record kind")
        rows = [p for p in view.resolve(ref) if p.address.key == "payload"]
        if len(rows) != 1 or dict(codec.loads(rows[0].value)) != self._public11(d):
            raise ValueError("exact collective content must be delivered and processed")
        return d

    def _group11(self, ref):
        return self._current11(ref,("group",))

    def _member11(self, group, actor, limit):
        return actor in nesting.walk(self.world,group.identity,limit)["leaves"]

    def _manage11(self, group, actor):
        d=self._group11(group)
        if d["owner"] != actor or actor not in d["members"]:
            raise ValueError("active coordinator required")
        return d

    def _disclose(self,cid,actor,source,selectors,subject):
        if source.identity.namespace.startswith("u11.") and source != LAW11:
            d=self._records11.get(source)
            if d is None or d["kind"] == "selection":
                raise ValueError("selection internals are not a public aggregate")
            invited=d["kind"]=="invitation" and d["receiver"]==actor
            group=d["ref"] if d["kind"]=="group" else d.get("group")
            current_group=self._heads11.get(group.identity) if group else None
            owner=d.get("owner",d["actor"])==actor
            member=current_group and self._member11(current_group,actor,100000)
            if not (invited or owner or member): raise ValueError("collective disclosure needs membership or own history")
            value=self.world.resolve(source)
            allowed={(a.name,("attributes",str(i),"value")) for i,a in enumerate(value.attributes) if a.name=="payload"}
            if subject not in (None,source) or any((s.key,s.path) not in allowed for s in selectors):
                raise ValueError("only the scoped public payload is deliverable")
        return super()._disclose(cid,actor,source,selectors,subject)

    def _new11(self,kind,r,op,*,prior=None,**values):
        ref=address("u11."+kind,r.actor,r.key) if prior is None else ObjectRef(prior.identity,prior.revision+1)
        return dict(ref=ref,kind=kind,actor=r.actor,context=r.context,cue=r.cue,operation=op,**values)

    def _revision11(self,d,r,op,**changes):
        return {**d, "ref":ObjectRef(d["ref"].identity,d["ref"].revision+1),
                "actor":r.actor,"operation":op,**changes}

    def _start(self,cid,request):
        if type(request) is not CollectiveRequest: return super()._start(cid,request)
        r=request
        view=self.participant_view(r.actor)
        known=self.access._known_refs(r.actor)
        if r.actor not in self._profiles or (r.actor,r.key) in self._jobs or r.actor in self._locks:
            raise ValueError("funded typed actor, unused key and available processing required")
        if r.cue not in self._references or any(x not in known for x in (r.context,r.cue)):
            raise ValueError("processed context and stable cue required")
        if Role.CONTEXT not in self.world.resolve(r.context).roles: raise ValueError("context role required")
        if r.focus and r.focus not in known: raise ValueError("focus must be received")
        evidence=view.snapshot.particulars
        units=1+len(evidence)+r.limit+nesting.syntax_size((r.program,r.members,r.resources))
        inward=r.purpose in ("summarize","observe","retain")
        origin,destination,polarity=("ITS","WE","accumulation") if inward else ("WE","ITS","expenditure")
        tim=raw_attrs(self.world.resolve(self._profiles[r.actor]))["tim"]
        rows=route(tim,self._cursors[r.actor],("te","si") if inward else ("si","te"),origin,destination,polarity)
        execution=sum(sum(row["charges"])+row["content_units"] for row in rows)
        base=OperationRequest(r.key,r.actor,"bind",r.context)
        d={f.name:getattr(base,f.name) for f in fields(base) if f.name not in ("participants","evidence")}
        d.update(record_type="operation",primitive="bind",u11=True,purpose=r.purpose,contract=LAW11,
            cue=r.cue,target=r.focus or r.context,required=units+execution,completed=0,spent=0,
            recall_units=units,route_prepare=units,route_execute=execution,status="pending",failure=None,result=None,
            evidence_count=len(evidence),visit_budget=r.limit,syntax_units=nesting.syntax_size((r.program,r.members,r.resources)),
            active_start=self._cursors[r.actor],tim=tim,origin=origin,destination=destination,polarity=polarity,
            started_tick=self._now().tick,**flatten_route(rows))
        sources=tuple(dict.fromkeys(p.source for p in evidence))
        for prefix,values in (("input.",(r.context,r.cue,*sources)),("participant.",(r.actor,)),
                              ("lock.",(r.actor,)),("dependency.",(LAW11,self.law,r.cue,self._profiles[r.actor]))):
            d.update({prefix+str(i):v for i,v in enumerate(values)})
        ref=job_address(r.actor,r.key)
        added=() if LAW11.identity in self.world._heads else (world_contract(),)
        if not added and self.world.resolve(LAW11)!=world_contract(): raise ValueError("collective contract mismatch")
        self._batch(cid,r.actor,(*added,record(ref,"Paid collective "+r.purpose,d)),evidence=(r.context,r.cue,*sources))
        self._jobs[r.actor,r.key]=ref
        self._reserve(d,ref)
        self._inputs11[ref.identity]=r,evidence
        return ref

    def _advance(self,cid,actor,key,work_limit):
        ref=super()._advance(cid,actor,key,work_limit)
        d=raw_attrs(self.world.resolve(ref))
        if d.get("u11"): self._cursors[actor]=progress(d)[0]
        return ref

    def _expand11(self,program,group,view,limit,*,read_calls=True):
        graph=nesting.walk(self.world,group.identity,limit)
        agenda,dependencies,visits=[],set(v.ref for v in graph["groups"].values()),0
        pending=[(part,group,()) for part in reversed(program)]
        while pending:
            part,scope,ancestors=pending.pop();visits+=1
            if visits>limit: raise ValueError("procedure expansion budget exhausted")
            if type(part) is not tuple or not part: raise ValueError("structured collective step required")
            if part[0]=="call" and len(part)==2:
                cap=self._read11(view,part[1],("capacity",),current=False) if read_calls else self._records11[part[1]]
                if cap["kind"]!="capacity" or part[1] in ancestors: raise ValueError("invalid or recursive collective call")
                child=cap["group"].identity
                sub=nesting.walk(self.world,scope.identity,limit)
                if child not in sub["groups"]: raise ValueError("called capacity is outside the nested boundary")
                child_ref=self.world.head(child).ref
                dependencies.add(part[1])
                pending.extend((p,child_ref,ancestors+(part[1],)) for p in reversed(cap["program"]))
            elif part[0]=="work" and len(part)==4:
                _,worker,procedure,roles=part
                if type(worker) is not ObjectId or type(procedure) is not ObjectRef or type(roles) is not tuple:
                    raise ValueError("work names worker, primitive and role identities")
                if not self._member11(scope,worker,limit): raise ValueError("worker is outside this collective")
                if Role.PERSON not in self.world.head(worker).roles: raise ValueError("actual person performs primitive work")
                if len(dict(roles))!=len(roles): raise ValueError("duplicate work role")
                p=self.world.resolve(procedure).facet(Procedure)
                name=next((n for n in SIGNATURES if p and p.executor=="u4."+n+".v1"),None)
                if name is None or p.inputs!=SIGNATURES[name] or p.steps or p.preconditions or p.effects:
                    raise ValueError("collective work requires a supported primitive definition")
                if set(dict(roles))!=set(SIGNATURES[name]) or any(type(i) is not ObjectId for _,i in roles):
                    raise ValueError("work roles must match the primitive")
                scope_graph=nesting.walk(self.world,scope.identity,limit)
                for role,identity in roles:
                    if role in ("target","tool","stock") and identity not in scope_graph["resources"]:
                        raise ValueError("work material lies outside the declared resource boundary")
                agenda.append((scope.identity,worker,procedure,roles))
                dependencies.add(procedure)
            else: raise ValueError("unsupported collective procedure constructor")
        if not agenda: raise ValueError("empty collective work cannot demonstrate capacity")
        return tuple(agenda),tuple(sorted(dependencies))

    def _derive11(self,r,view,op):
        f=None if r.focus is None else self._read11(view,r.focus)
        if f and (f["context"],f["cue"])!=(r.context,r.cue): raise ValueError("collective context mismatch")
        if r.purpose=="compose":
            known=self.access._known_refs(r.actor)
            if any(x not in known for x in (*r.members,*r.resources)): raise ValueError("received members and resources required")
            for item in r.members:
                v=self.world.resolve(item)
                if Role.PERSON in v.roles and item.identity!=r.actor: raise ValueError("person must accept an invitation")
                if v.facet(Composition):
                    child=self._manage11(item,r.actor)
                    if (child["context"],child["cue"])!=(r.context,r.cue):raise ValueError("child crosses the contextual boundary")
            if any(self.world.resolve(x).facet(Material) is None for x in r.resources): raise ValueError("material resource required")
            d=self._new11("group",r,op,owner=r.actor,members=tuple(dict.fromkeys((r.actor,*(x.identity for x in r.members)))),
                resources=tuple(x.identity for x in r.resources),boundary=r.boundary,status="active",
                dependencies=tuple(dict.fromkeys((*r.members,*r.resources))))
            nesting.walk(self.world,d["ref"].identity,r.limit,overrides={d["ref"].identity:self._value11(d)})
            return [d]
        if r.purpose=="invite":
            g=self._manage11(r.focus,r.actor)
            if ObjectRef(r.peer,1) not in self.access._known_refs(r.actor) or Role.PERSON not in self.world.head(r.peer).roles:
                raise ValueError("known person required")
            if r.peer in g["members"]: raise ValueError("already a direct member")
            return [self._new11("invitation",r,op,owner=r.actor,receiver=r.peer,group=g["ref"],status="offered")]
        if r.purpose=="join":
            if f["kind"]!="invitation" or f["receiver"]!=r.actor or f["status"]!="offered": raise ValueError("own open invitation required")
            g=self._group11(self._heads11[f["group"].identity])
            if r.actor in g["members"]: raise ValueError("already joined")
            return [self._revision11(g,r,op,members=(*g["members"],r.actor)),self._revision11(f,r,op,status="accepted")]
        if r.purpose=="leave":
            g=self._group11(r.focus)
            if r.actor not in g["members"] or g["owner"]==r.actor: raise ValueError("only a direct non-coordinator member may leave in U11")
            return [self._revision11(g,r,op,members=tuple(m for m in g["members"] if m!=r.actor))]
        if r.purpose in ("link","unlink"):
            g=self._manage11(r.focus,r.actor)
            known=self.access._known_refs(r.actor)
            if any(x not in known for x in (*r.members,*r.resources)): raise ValueError("received membership content required")
            for item in r.members:
                v=self.world.resolve(item)
                if Role.PERSON in v.roles: raise ValueError("people use invitation or departure operations")
                if v.facet(Composition):
                    child=self._manage11(item,r.actor)
                    if (child["context"],child["cue"])!=(r.context,r.cue):raise ValueError("child crosses the contextual boundary")
            if any(self.world.resolve(x).facet(Material) is None for x in r.resources): raise ValueError("material resource required")
            change={}
            for key,values in (("members",r.members),("resources",r.resources)):
                ids=tuple(x.identity for x in values)
                if r.purpose=="link": change[key]=tuple(dict.fromkeys((*g[key],*ids)))
                else: change[key]=tuple(i for i in g[key] if i not in ids)
            d=self._revision11(g,r,op,**change,dependencies=tuple(dict.fromkeys((*r.members,*r.resources))))
            if d["members"]==g["members"] and d["resources"]==g["resources"]: raise ValueError("no membership change")
            nesting.walk(self.world,d["ref"].identity,r.limit,overrides={d["ref"].identity:self._value11(d)})
            return [d]
        if r.purpose=="summarize":
            self._group11(r.focus)
            if not self._member11(r.focus,r.actor,r.limit): raise ValueError("aggregate inspection requires membership")
            p=nesting.project(self.world,r.focus.identity,r.scope,r.limit,use_cache=r.mode=="aggregate")
            identity=address("u11.summary",r.focus.identity,r.scope).identity
            prior=self._heads11.get(identity)
            d=self._new11("summary",r,op,group=r.focus,owner=r.actor,status="observed",**p)
            d["ref"]=ObjectRef(identity,1 if prior is None else prior.revision+1)
            return [d]
        if r.purpose=="plan":
            self._manage11(r.focus,r.actor)
            agenda,deps=self._expand11(r.program,r.focus,view,r.limit)
            return [self._new11("plan",r,op,owner=r.actor,group=r.focus,program=r.program,
                agenda=agenda,dependencies=deps,status="proposed")]
        if r.purpose=="instantiate":
            if f["kind"] not in ("plan","capacity"): raise ValueError("a program or retained collective capacity is required")
            group=self._heads11[f["group"].identity]
            self._manage11(group,r.actor)
            agenda,deps=self._expand11(f["program"],group,view,r.limit)
            # Detailed mode explicitly expands at instantiation; aggregate mode
            # retains its calls. Both dispatch the same mandatory leaf work.
            return [self._new11("run",r,op,owner=r.actor,group=group,program=f["program"],agenda=agenda,
                dependencies=deps,source=f["ref"],mode=r.mode,index=0,events=(),status="active",selection=None)]
        if r.purpose=="accept":
            if f["kind"]!="run" or f["status"]!="active": raise ValueError("active collective run required")
            indices=tuple(i for i,row in enumerate(f["agenda"]) if row[1]==r.actor)
            if not indices or (f["ref"].identity,r.actor) in self._duties11: raise ValueError("one consent per assigned participant and run")
            for i in indices:
                scope,worker,proc,_=f["agenda"][i]
                if not self._member11(self._heads11[scope],worker,r.limit) or not view.can_use(proc,r.context):
                    raise ValueError("membership does not supply this participant's own practiced skill")
            return [self._new11("commitment",r,op,owner=r.actor,group=f["group"],run=f["ref"],
                indices=indices,performed=(),permission_active=True,status="open")]
        if r.purpose=="withdraw":
            if f["kind"]!="commitment" or f["owner"]!=r.actor or f["status"]!="open" or not f["permission_active"]:
                raise ValueError("own unfinished consent required")
            return [self._revision11(f,r,op,permission_active=False)]
        if r.purpose=="select":
            if f["kind"]!="run" or f["status"]!="active": raise ValueError("active run awaiting a constituent step required")
            scope,worker,procedure,roles=f["agenda"][f["index"]]
            if worker!=r.actor: raise ValueError("only the assigned worker selects its action")
            if any(self.world.head(dep.identity).ref!=dep for dep in f["dependencies"]): raise ValueError("collective structure changed; instantiate again")
            # Every assignee must explicitly accept before any part is enacted.
            duties=[]
            for assignee in dict.fromkeys(row[1] for row in f["agenda"]):
                dutyref=self._duties11.get((f["ref"].identity,assignee))
                duty=self._current11(dutyref,("commitment",))
                if not duty["permission_active"]: raise ValueError("participant consent is withdrawn")
                duties.append(dutyref)
            if not view.can_use(procedure,r.context): raise ValueError("own acquired procedure required")
            inputs,evidence={},[]
            for role,identity in roles:
                if role in ("target","tool","stock"):
                    ref,addresses=nesting.observed_material(view,identity,stock=role=="stock")
                    inputs[role]=ref;evidence.extend(addresses)
                elif role=="recipient":
                    if ObjectRef(identity,1) not in self.access._known_refs(r.actor): raise ValueError("recipient not received")
                    inputs[role]=identity
                else:
                    ref=nesting.observed_ref(view,identity)
                    inputs[role]=ref;evidence.extend(p.address for p in view.resolve(ref))
            selection=self._new11("selection",r,op,owner=r.actor,group=f["group"],run=f["ref"],index=f["index"],
                worker=r.actor,procedure=procedure,roles=tuple(sorted(inputs.items())),
                evidence=tuple(dict.fromkeys(evidence)),dependencies=(*f["dependencies"],*duties),status="prepared")
            # DetailAddress values are serialized explicitly at the record boundary.
            selection["evidence"]=tuple((a.delivery,a.key) for a in selection["evidence"])
            newrun=self._revision11(f,r,op,status="awaiting_work",selection=selection["ref"])
            selection["run"]=newrun["ref"]
            return [selection,newrun]
        if r.purpose=="observe":
            if f["kind"]!="run" or f["status"]!="awaiting_work": raise ValueError("run awaits constituent observation")
            selection=self._records11[f["selection"]]
            if selection["worker"]!=r.actor: raise ValueError("performer must process its own result")
            obs=self.world.resolve(r.observation)
            if obs.occurrence!=Occurrence.OBSERVATION or obs.facet(Account).holder!=r.actor:
                raise ValueError("actor-owned observation required")
            received={p.address.key:p.value for p in view.resolve(r.observation)}
            eventref=received.get("event")
            if eventref is None or not obs.facet(Account).sources or eventref!=obs.facet(Account).sources[0]:
                raise ValueError("observation must be read before collective settlement")
            event=raw_attrs(self.world.resolve(eventref))
            physical=raw_attrs(self.world.resolve(event["operation"]))
            if physical.get("collective_selection")!=selection["ref"] or event["actor"]!=r.actor:
                raise ValueError("result does not realize this constituent selection")
            success=event["outcome"]=="succeeded"
            nextindex=f["index"]+int(success)
            status=("succeeded" if nextindex==len(f["agenda"]) else "active") if success else "failed"
            run=self._revision11(f,r,op,index=nextindex,events=(*f["events"],eventref),status=status,selection=None)
            results=[run]
            if success:
                duty=self._current11(self._duties11[f["ref"].identity,r.actor],("commitment",))
                performed=(*duty["performed"],f["index"])
                results.append(self._revision11(duty,r,op,performed=performed,
                    status="fulfilled" if performed==duty["indices"] else "open"))
            return results
        if r.purpose=="retain":
            if f["kind"]!="run" or f["status"]!="succeeded" or f["owner"]!=r.actor:
                raise ValueError("coordinator needs a completed collective performance")
            received={p.value for p in view.snapshot.particulars if p.address.key=="event" and type(p.value) is ObjectRef}
            if not set(f["events"])<=received: raise ValueError("coordinator has not processed every actual result")
            if any(d["kind"]=="capacity" and d.get("practice")==f["ref"] for d in self._records11.values()):
                raise ValueError("collective practice already retained")
            return [self._new11("capacity",r,op,owner=f["group"].identity,group=f["group"],program=f["program"],
                agenda=f["agenda"],practice=f["ref"],events=f["events"],dependencies=f["dependencies"],status="retained")]
        raise ValueError("unsupported collective purpose")

    def _commit(self,cid,actor,key):
        old,d=self._active(actor,key)
        if not d.get("u11"): return super()._commit(cid,actor,key)
        if d["status"]!="ready": raise ValueError("full paid coordination required")
        r,snapshot=self._inputs11[old.ref.identity]
        view=self.participant_view(actor)
        failure=None;outputs=[]
        if view.snapshot.particulars!=snapshot: failure="received_evidence_changed"
        elif any(self.world.head(ref.identity).ref!=ref for ref in indexed(d,"dependency.")): failure="stale_dependency"
        else:
            try: outputs=self._derive11(r,view,old.ref)
            except (ValueError,KeyError,TypeError,IndexError) as error:
                failure="collective_precondition_unavailable"
                # This diagnostic is never delivered through a participant view.
                d["diagnostic"]=str(error)
        event=self._event(cid,old,"succeeded" if failure is None else "failed")
        sources=tuple(dict.fromkeys(p.source for p in snapshot))
        for o in outputs: o["sources"]=sources
        extra=[];command=None
        if failure is None:
            bref=address("u11.binding",actor,key)
            binding=ObjectVersion(bref,WRITER,"Retained collective coordination",(Role.INTERPRETATION,),
                (Account(r.context,(Proposition(r.context,"u11."+r.purpose,"completed",r.context,
                    TimeScope(self._now(),None)),),self._now(),actor,sources),),occurrence=Occurrence.INTERPRETATION,
                attributes=attributes({"cue":r.cue,"context":r.context,"meaning":"collective "+r.purpose,
                    "endorsement":ClaimStatus.ENDORSED.value,"confidence":None}))
            receipt=record(address("u4.receipt",cid),"Paid collective processing receipt",{
                "actor":actor,"operation":"bind","work_key":bref.identity.key,
                **{k:d[k] for k in ("required","completed","spent")},
                **{"input."+str(i):x for i,x in enumerate((bref,*sources))}})
            command=("bind",actor,bref,tuple(p.address for p in snapshot),receipt.ref)
            self.access.preview(command,{bref:binding,receipt.ref:receipt})
            extra.extend((binding,receipt))
            for i in range(d["route_count"]):
                extra.append(record(address("u11.surface",actor,key,i),"Collective perspective realization",{
                    "actor":actor,"operation":old.ref,"content":outputs[-1]["ref"],"binding":bref,
                    "origin":d[f"route.{i}.origin"],"destination":d[f"route.{i}.destination"]}))
            d["binding"]=bref
        d.update(status="succeeded" if failure is None else "failed",failure=failure,result=event.ref,finished_tick=self._now().tick,
                 **{"output."+str(i):o["ref"] for i,o in enumerate(outputs)})
        current=next_version(old,attributes=attributes(d))
        self._batch(cid,actor,(current,*(self._value11(o) for o in outputs),*extra,event),evidence=(old.ref,))
        self._jobs[actor,key]=current.ref
        self._release(d,old.ref)
        if command:self.access._execute(command)
        for o in outputs:
            self._records11[o["ref"]]=deepcopy(o);self._heads11[o["ref"].identity]=o["ref"]
            if o["kind"]=="commitment": self._duties11[o["run"].identity,o["owner"]]=o["ref"]
        return event.ref

    def _enact(self,cid,actor,key,plan):
        if plan.identity.namespace!="u11.selection": return super()._enact(cid,actor,key,plan)
        s=self._current11(plan,("selection",))
        if s["owner"]!=actor or plan in self._used11: raise ValueError("own unused selection required")
        run=self._current11(s["run"],("run",))
        if run["selection"]!=plan or run["status"]!="awaiting_work": raise ValueError("run no longer awaits this selection")
        from .particulars import DetailAddress
        values=dict(s["roles"])
        participants=tuple(dict.fromkeys((run["owner"],*(v for k,v in s["roles"] if k=="recipient"))))
        r=OperationRequest(key,actor,"procedure",s["context"],procedure=s["procedure"],participants=participants,
            evidence=tuple(DetailAddress(*a) for a in s["evidence"]),**values)
        data=self._compile(r)
        deps=tuple(dict.fromkeys((*indexed(data,"dependency."),*s["dependencies"],run["ref"])))
        data.update(collective_selection=plan,collective_run=run["ref"],collective_index=s["index"])
        for i,dep in enumerate(deps): data["dependency."+str(i)]=dep
        data["input."+str(len(indexed(data,"input.")))]=plan
        ref=job_address(actor,key)
        data["status"]="pending" if self._can_reserve(data,ref) else "waiting"
        self._batch(cid,actor,(record(ref,"Collective constituent work",data),),evidence=indexed(data,"input."))
        self._jobs[actor,key]=ref;self._used11.add(plan)
        if data["status"]=="pending": self._reserve(data,ref)
        return ref
