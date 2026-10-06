"""U12 participant institutions on the inherited paid collective lifecycle.

The service validates actual membership and permission at commit. Constructive
and response policies receive detached actor views, never evaluator results.
U11 owns all material work. Public change does not edit U7/U8 personal history.
"""
from dataclasses import fields, replace
from . import codec, institution_policy as policy, composition_language as lang
from .records import (ObjectId, ObjectRef, ObjectVersion, Role, Relation, Endpoint,
    TimeScope, Governance, Procedure)
from .material import attrs as raw_attrs, attributes
from .development import record
from .operations import address, job_address, indexed
from .operation_records import OperationRequest, WRITER
from .cognitive_routes import route, flatten_route
from .collective import CollectiveEngine
from .collective_records import CollectiveRequest
from .institution_records import InstitutionRequest, LAW12, registry, world_contract


class InstitutionEngine(CollectiveEngine):
    SCHEMA = "hle-unified-u12-engine-v1"

    @staticmethod
    def _registry(): return registry()

    def __init__(self, world, law):
        super().__init__(world, law)
        self._ballots12, self._assents12, self._practices12 = {}, {}, {}

    def _declare(self, cid, versions):
        if any(v.ref.identity.namespace.startswith("u12.") for v in versions):
            raise ValueError("institutional decisions and history cannot be imported")
        return super()._declare(cid, versions)

    def _public11(self, d):
        result = super()._public11(d)
        if d["ref"].identity.namespace.startswith("u12."):
            for key in ("origin_encounter","patterns","origin_materials","initial","predicted","material_sources"):
                result.pop(key,None)
        return result

    def _value11(self, d):
        value = super()._value11(d)
        if d["kind"] == "group" and "rules" in d:
            value = replace(value,facets=(value.facets[0],Governance(d["rules"],())))
        if d["ref"].identity.namespace.startswith("u12.") and d["kind"] in ("vote","assent"):
            value = replace(value,roles=(Role.RECORD,Role.COMMITMENT),facets=(Relation(
                "institutional_consent", (Endpoint("promisor",ObjectRef(d["owner"],1)),
                    Endpoint("terms",d.get("proposal",d.get("institution")))), True,
                d["context"],TimeScope(self._now(),None),attributes({"choice":d.get("choice","accept"),
                    "permission_active":d.get("permission_active",False)})),))
        if d["ref"].identity.namespace == "u12.institution":
            value = replace(value,roles=(Role.RECORD,),
                facets=(Governance((d["proposal"],),d["votes"]),))
        return value

    def _disclose(self, cid, actor, source, selectors, subject):
        if source.identity.namespace.startswith("u12.") and source != LAW12:
            d = self._records11.get(source)
            if d is None: raise ValueError("institution internals are not public content")
            group = self._heads11.get(d["group"].identity)
            member = group and actor in self._group11(group)["members"]
            allowed = actor == d.get("owner",d["actor"]) or member
            if d["kind"] == "teaching": allowed = actor in (d["actor"],d["receiver"])
            if d["kind"] == "understanding": allowed = actor == d["owner"]
            if not allowed: raise ValueError("public rule disclosure requires membership or own history")
            value = self.world.resolve(source)
            public = {(a.name,("attributes",str(i),"value")) for i,a in enumerate(value.attributes) if a.name=="payload"}
            if subject not in (None,source) or any((s.key,s.path) not in public for s in selectors):
                raise ValueError("only public institutional payload may be disclosed")
        return super()._disclose(cid,actor,source,selectors,subject)

    def _start(self, cid, request):
        if type(request) is not InstitutionRequest: return super()._start(cid,request)
        r,view = request,self.participant_view(request.actor)
        known = self.access._known_refs(r.actor)
        if r.actor not in self._profiles or (r.actor,r.key) in self._jobs or r.actor in self._locks:
            raise ValueError("funded typed actor, unused key and available processing required")
        if r.cue not in self._references or any(x not in known for x in (r.context,r.cue,r.focus)):
            raise ValueError("processed context, cue and focus required")
        if Role.CONTEXT not in self.world.resolve(r.context).roles: raise ValueError("context role required")
        evidence = view.snapshot.particulars
        syntax = sum(1 for _ in self._syntax12((r.slots,r.goal,r.intent,r.peer,r.support,r.encounter)))
        units = 1+len(evidence)+r.limit+syntax
        inward = r.purpose in ("respond","learn","record","assent")
        origin,destination,polarity = ("ITS","WE","accumulation") if inward else ("WE","ITS","expenditure")
        tim = raw_attrs(self.world.resolve(self._profiles[r.actor]))["tim"]
        rows = route(tim,self._cursors[r.actor],("te","si") if inward else ("si","te"),origin,destination,polarity)
        execution = sum(sum(x["charges"])+x["content_units"] for x in rows)
        base = OperationRequest(r.key,r.actor,"bind",r.context)
        d = {f.name:getattr(base,f.name) for f in fields(base) if f.name not in ("participants","evidence")}
        d.update(record_type="operation",primitive="bind",u11=True,u12=True,purpose=r.purpose,
            cue=r.cue,target=r.focus,required=units+execution,completed=0,spent=0,
            recall_units=units,route_prepare=units,route_execute=execution,status="pending",failure=None,result=None,
            evidence_count=len(evidence),visit_budget=r.limit,syntax_units=syntax,
            request=codec.dumps(tuple((f.name,getattr(r,f.name)) for f in fields(r))),
            active_start=self._cursors[r.actor],tim=tim,origin=origin,destination=destination,polarity=polarity,
            started_tick=self._now().tick,**flatten_route(rows))
        sources = tuple(dict.fromkeys(p.source for p in evidence))
        for prefix,values in (("input.",(r.context,r.cue,*sources)),("participant.",(r.actor,)),
            ("lock.",(r.actor,)),("dependency.",(LAW12,self.law,r.cue,self._profiles[r.actor]))):
            d.update({prefix+str(i):x for i,x in enumerate(values)})
        ref = job_address(r.actor,r.key)
        added = () if LAW12.identity in self.world._heads else (world_contract(),)
        if not added and self.world.resolve(LAW12)!=world_contract(): raise ValueError("institution contract mismatch")
        self._batch(cid,r.actor,(*added,record(ref,"Paid institution "+r.purpose,d)),evidence=(r.context,r.cue,*sources))
        self._jobs[r.actor,r.key]=ref
        self._reserve(d,ref)
        self._inputs11[ref.identity]=r,evidence
        return ref

    @staticmethod
    def _syntax12(value):
        yield value
        if type(value) is tuple:
            for item in value: yield from InstitutionEngine._syntax12(item)

    def _new12(self, kind, r, op, **values):
        return dict(ref=address("u12."+kind,r.actor,r.key),kind=kind,actor=r.actor,
                    context=r.context,cue=r.cue,operation=op,owner=r.actor,**values)

    def _read12(self, view, ref, kinds=None, *, current=True):
        d = self._read11(view,ref,kinds,current=current)
        if not ref.identity.namespace.startswith("u12."): raise ValueError("institution record required")
        return d

    def _people12(self, group):
        if any(Role.PERSON not in self.world.head(i).roles for i in group["members"]):
            raise ValueError("U12 electorate requires direct persons; nested authority is unassessed")
        if len(group["members"])<2: raise ValueError("institution requires at least two distinct participants")
        return tuple(sorted(group["members"]))

    def _group_for12(self, r, view, d):
        g = d if d["kind"]=="group" else self._read11(view,self._heads11[d["group"].identity],("group",))
        if (g["context"],g["cue"])!=(r.context,r.cue) or r.actor not in g["members"]:
            raise ValueError("participating member in received current scope required")
        return g

    def _encounter12(self, r, view):
        d = policy.encounter(view,r.encounter,r.context,r.cue)
        if self._last_encounters.get((r.actor,d["target"].identity,r.context,r.cue))!=r.encounter:
            raise ValueError("superseded personal encounter")
        return d

    def _assent12(self, institution, actor):
        ref = self._assents12.get((institution["ref"].identity,actor))
        d = self._current11(ref,("assent",))
        if not d["permission_active"] or d["institution"] != institution["ref"]:
            raise ValueError("active participant assent to these exact public terms required")
        return d

    def _known_practices12(self, view, institution):
        result=[]
        for ref in self._practices12.get(institution["ref"].identity,()):
            # Availability is actor-owned. Hidden practice cannot license maintenance.
            if not view.resolve(ref): continue
            d=self._read12(view,ref,("practice",))
            if d["institution"]==institution["ref"]:result.append(d)
        return tuple(result)

    def _proposal12(self, r, view, op, focus):
        previous = focus if focus["kind"]=="proposal" else None
        institution = (self._read12(view,previous["institution"],("institution",)) if previous and previous["institution"]
                       else focus if focus["kind"]=="institution" else None)
        g = self._group_for12(r,view,focus)
        electorate = self._people12(g)
        enc = self._encounter12(r,view)
        if policy.boundary(enc): raise ValueError("proposal cannot override "+policy.boundary(enc))
        effect = previous["effect"] if previous else r.intent
        if effect != "establish" and (not institution or institution["status"]=="dissolved"):
            raise ValueError("revision needs a live institution")
        if effect == "establish" and any(x.identity.namespace=="u12.institution" for x in g.get("rules",())):
            raise ValueError("one live institution per group in this bounded contract")
        goal = previous["goal"] if previous else institution["goal"] if institution else r.goal
        if not goal or not any(t[:2]==("ge",("field","progress","uses")) and type(t[2]) is int and t[2]>0 for t in goal):
            raise ValueError("material demand must require actual useful work")
        if effect in ("succession","dissolve"):
            # Administrative consent never requires new material performance.
            generated=dict(program=institution["prototype"],symbolic=institution["symbolic"],considered=0)
        else:
            generated = policy.construct(view,r.slots,goal,r.context,r.limit)
            if dict(r.slots)["target"].identity!=enc["target"].identity:
                raise ValueError("proposed material and received encounter disagree")
            self._expand11(generated["program"],g["ref"],view,r.limit)
        gate = policy.authority(enc)
        practice = self._known_practices12(view,institution) if institution else ()
        if effect in ("maintain","succession","dissolve"):
            gate = institution["gate"]
        if effect=="maintain" and (institution["status"]!="trial" or len(practice)<2):
            raise ValueError("maintained rule needs two distinct processed collective practices")
        if effect=="review" and gate==institution["gate"]:
            raise ValueError("no participant-generated change to the public terms")
        successor = r.peer if effect=="succession" and not previous else previous.get("successor") if previous else None
        if effect=="succession" and (successor not in electorate or successor==g["owner"]):
            raise ValueError("succession names a different current participant")
        patterns = indexed(enc,"pattern.")
        dispute_ref=previous.get("dispute") if previous else r.support
        if dispute_ref:
            dispute=self._read12(view,dispute_ref,("dispute",))
            if not institution or dispute["institution"].identity!=institution["ref"].identity or dispute["status"]!="open":
                raise ValueError("open dispute about this institution required")
        reason = "attributed authorization protects shared work" if gate=="approval" else "received safety and acquired work support local checking"
        result = self._new12("proposal",r,op,group=g["ref"],electorate=electorate,
            institution=institution["ref"] if institution else None,effect=effect,gate=gate,goal=goal,
            prototype=generated["program"],symbolic=generated["symbolic"],considered=generated["considered"],
            origin_encounter=r.encounter,patterns=patterns,origin_materials=tuple(self._patterns[x].origin for x in patterns),
            reason=reason,status="offered",supersedes=previous["ref"] if previous else None,
            successor=successor,practices=tuple(x["ref"] for x in practice),target=enc["target"].identity,dispute=dispute_ref)
        result["wording"]=policy.render(result)
        return [result]

    def _derive11(self, r, view, op):
        if type(r) is not InstitutionRequest: return super()._derive11(r,view,op)
        f = self._read11(view,r.focus)
        g = self._group_for12(r,view,f)
        if (f["context"],f["cue"])!=(r.context,r.cue): raise ValueError("institution context mismatch")
        if r.purpose in ("propose","counter"):
            if r.purpose=="counter" and f["kind"]!="proposal": raise ValueError("counterproposal needs public terms")
            return self._proposal12(r,view,op,f)
        if r.purpose=="respond":
            if f["kind"]!="proposal" or f["group"]!=g["ref"] or f["status"]!="offered":
                raise ValueError("open proposal and unchanged electorate required")
            if (f["ref"],r.actor) in self._ballots12: raise ValueError("one response per exact proposal and person")
            choice,reason=policy.decide(view,self._public11(f),self._encounter12(r,view))
            return [self._new12("vote",r,op,group=g["ref"],proposal=f["ref"],choice=choice,reason=reason,
                origin_encounter=r.encounter,permission_active=choice=="accept",status="recorded")]
        if r.purpose=="ratify": return self._ratify12(r,view,op,f,g)
        if r.purpose=="apply": return self._apply12(r,view,op,f,g)
        if r.purpose=="permit":
            if f["kind"]!="application" or f["status"]!="waiting": raise ValueError("open application required")
            institution=self._read12(view,f["institution"],("institution",))
            if r.actor!=institution["steward"] or institution["status"]=="dissolved": raise ValueError("current steward required")
            self._assent12(institution,r.actor)
            return [self._revision11(f,r,op,status="permitted",grantor=r.actor)]
        if r.purpose=="record":
            if f["kind"]!="run" or f["status"]!="succeeded" or "institution" not in f:
                raise ValueError("completed institutional constituent run required")
            institution=self._read12(view,f["institution"],("institution",),current=False)
            observed={p.value for p in view.snapshot.particulars if p.address.key=="event" and type(p.value) is ObjectRef}
            if not set(f["events"])<=observed or len(f["events"])!=len(f["agenda"]):
                raise ValueError("recorder must process all actual constituent results")
            if any(self._records11[x]["run"].identity==f["ref"].identity for x in self._practices12.get(institution["ref"].identity,())):
                raise ValueError("the same work cannot count as repeated practice")
            # Reconstruct only from the recorder's received results, never current truth.
            state,sources,_=lang.snapshot(view,f["slots"])
            state=lang.thaw(state);state["progress"]["uses"]=sum(raw_attrs(self.world.resolve(e))["primitive"]=="use" for e in f["events"])
            if not lang.meets(lang.freeze(state),institution["goal"]): raise ValueError("observed material result misses the public goal")
            return [self._new12("practice",r,op,group=g["ref"],institution=institution["ref"],run=f["ref"],
                events=f["events"],performers=tuple(dict.fromkeys(x[1] for x in f["agenda"])),status="observed",
                material_sources=sources,goal=institution["goal"])]
        if r.purpose=="teach":
            if f["kind"]!="institution" or f["status"]=="dissolved" or r.peer not in g["members"]:
                raise ValueError("live public rule and current learner required")
            self._assent12(f,r.actor)
            return [self._new12("teaching",r,op,group=g["ref"],institution=f["ref"],receiver=r.peer,
                gate=f["gate"],goal=f["goal"],steward=f["steward"],status="sent",wording=f["wording"])]
        if r.purpose=="learn":
            if f["kind"]!="teaching" or f["receiver"]!=r.actor: raise ValueError("own processed lesson required")
            institution=self._read12(view,f["institution"],("institution",))
            if institution["status"]=="dissolved" or any(f[k]!=institution[k] for k in ("gate","goal","steward")):
                raise ValueError("lesson is no longer an exact public rule")
            return [self._new12("understanding",r,op,group=g["ref"],institution=institution["ref"],
                lesson=f["ref"],gate=f["gate"],goal=f["goal"],steward=f["steward"],status="understood")]
        if r.purpose=="assent":
            if f["kind"]!="understanding" or f["owner"]!=r.actor: raise ValueError("own processed understanding required")
            institution=self._read12(view,f["institution"],("institution",))
            if institution["status"]=="dissolved": raise ValueError("institution is dissolved")
            proposal={**institution,"effect":"establish","institution":institution["ref"]}
            choice,reason=policy.decide(view,proposal,self._encounter12(r,view))
            if choice!="accept":
                return [self._new12("refusal",r,op,group=g["ref"],institution=institution["ref"],reason=reason,status=choice)]
            oldref=self._assents12.get((institution["ref"].identity,r.actor))
            if oldref and self._records11[oldref]["permission_active"]: raise ValueError("already assented")
            return [self._new12("assent",r,op,group=g["ref"],institution=institution["ref"],basis=f["ref"],
                permission_active=True,status="open")]
        if r.purpose=="withdraw_assent":
            if f["kind"]!="assent" or f["owner"]!=r.actor or not f["permission_active"]:
                raise ValueError("own active institutional assent required")
            return [self._revision11(f,r,op,permission_active=False)]
        if r.purpose=="withdraw_vote":
            if f["kind"]!="vote" or f["owner"]!=r.actor or not f["permission_active"]:
                raise ValueError("own active proposal consent required")
            proposal=self._current11(f["proposal"],("proposal",))
            if proposal["status"]!="offered":raise ValueError("enacted obligations use assent withdrawal")
            return [self._revision11(f,r,op,permission_active=False,choice="withdrawn",reason="participant_withdrew_consent")]
        if r.purpose=="dispute":
            if f["kind"]!="consequence" or f["bearer"]!=r.actor: raise ValueError("own received consequence required")
            return [self._new12("dispute",r,op,group=g["ref"],institution=f["institution"],
                consequence=f["ref"],bearer=r.actor,reason=f["outcome"],status="open")]
        raise ValueError("unsupported institutional operation")

    def _ratify12(self,r,view,op,p,g):
        if p["kind"]!="proposal" or p["status"]!="offered" or p["group"]!=g["ref"] or p["electorate"]!=self._people12(g):
            raise ValueError("exact current proposal and electorate required")
        votes=[]
        for actor in p["electorate"]:
            vote=self._read12(view,self._ballots12.get((p["ref"],actor)),("vote",))
            if vote["choice"]!="accept": raise ValueError("disagreement prevents collective enactment")
            votes.append(vote["ref"])
        institution=self._read12(view,p["institution"],("institution",)) if p["institution"] else None
        if institution and institution["status"]=="dissolved": raise ValueError("dissolved institution cannot be revised")
        if p["effect"]=="maintain":
            if len(p["practices"])<2: raise ValueError("public maintenance lacks actual repetition")
            for ref in p["practices"]:
                practice=self._read12(view,ref,("practice",))
                if practice["institution"]!=institution["ref"]: raise ValueError("unrelated practice")
        status="trial" if p["effect"]=="establish" else "dissolved" if p["effect"]=="dissolve" else "active" if p["effect"]=="maintain" else institution["status"]
        successor=p["successor"] if p["effect"]=="succession" else g["owner"]
        ref=address("u12.institution",r.actor,r.key) if institution is None else ObjectRef(institution["ref"].identity,institution["ref"].revision+1)
        group=self._revision11(g,r,op,owner=successor,rules=() if status=="dissolved" else (ref,))
        rule=self._new12("institution",r,op,group=group["ref"],steward=successor,proposal=p["ref"],
            votes=tuple(votes),gate=p["gate"],goal=p["goal"],status=status,wording=p["wording"],
            prototype=p["prototype"],symbolic=p["symbolic"],
            predecessor=institution["ref"] if institution else None,practices=p["practices"])
        rule["ref"]=ref;rule["owner"]=g["ref"].identity
        outputs=[group,rule,self._revision11(p,r,op,status="enacted")]
        if p.get("dispute"):
            dispute=self._read12(view,p["dispute"],("dispute",))
            if (p["effect"]=="review" and dispute["reason"]=="approval_wait" and p["gate"]=="self_check") or p["effect"]=="dissolve":
                outputs.append(self._revision11(dispute,r,op,status="resolved",resolution=ref))
        # Every new assent is backed by that person's own exact paid vote.
        for actor,vote in zip(p["electorate"],votes):
            oldref=self._assents12.get((ref.identity,actor))
            if oldref:
                old=self._current11(oldref,("assent",))
                outputs.append(self._revision11(old,r,op,permission_active=False,status="superseded"))
            assent=self._new12("assent",r,op,group=group["ref"],institution=ref,basis=vote,
                permission_active=status!="dissolved",status="open" if status!="dissolved" else "released")
            assent["ref"]=address("u12.assent",actor,r.key);assent["owner"]=actor
            outputs.append(assent)
        return outputs

    def _apply12(self,r,view,op,institution,g):
        if institution["kind"]!="institution" or institution["status"]=="dissolved": raise ValueError("live public rule required")
        assent=self._assent12(institution,r.actor)
        enc=self._encounter12(r,view)
        if not r.slots or dict(r.slots)["target"].identity!=enc["target"].identity:
            raise ValueError("request binds the received encounter's actual target")
        reason=policy.boundary(enc)
        application=None
        if not reason and institution["gate"]=="approval" and r.actor!=institution["steward"]:
            if r.support:
                application=self._read12(view,r.support,("application",))
                if (application["owner"]!=r.actor or application["institution"]!=institution["ref"]
                        or application["status"]!="permitted" or application["target"]!=enc["target"].identity):
                    raise ValueError("fresh own permission for exact rule and target required")
            else: reason="approval_wait"
        if reason:
            result=[]
            if reason=="approval_wait":
                application=self._new12("application",r,op,group=g["ref"],institution=institution["ref"],
                    target=enc["target"].identity,status="waiting",grantor=None)
                result.append(application)
            consequence=self._new12("consequence",r,op,group=g["ref"],institution=institution["ref"],
                bearer=r.actor,target=enc["target"].identity,outcome=reason,rule_cause=institution["proposal"],
                application=application["ref"] if application else None,status="blocked",
                origin_encounter=r.encounter,spent=raw_attrs(self.world.resolve(op))["spent"])
            return [*result,consequence]
        generated=policy.construct(view,r.slots,institution["goal"],r.context,r.limit)
        agenda,deps=self._expand11(generated["program"],g["ref"],view,r.limit)
        run=self._new11("run",r,op,owner=r.actor,group=g["ref"],program=generated["program"],agenda=agenda,
            dependencies=(*deps,institution["ref"],assent["ref"]),source=institution["ref"],mode="aggregate",
            index=0,events=(),status="active",selection=None,institution=institution["ref"],slots=r.slots,
            symbolic=generated["symbolic"],considered=generated["considered"],permission=r.support)
        result=[run]
        if application: result.append(self._revision11(application,r,op,status="consumed",run=run["ref"]))
        return result

    def _commit(self,cid,actor,key):
        ref=super()._commit(cid,actor,key)
        d=self.job_status(actor,key)
        if d.get("u12") and d["status"]=="succeeded":
            for out in indexed(d,"output."):
                row=self._records11[out]
                if row["kind"]=="vote":self._ballots12[row["proposal"],row["owner"]]=out
                if row["kind"]=="assent":self._assents12[row["institution"].identity,row["owner"]]=out
                if row["kind"]=="practice":self._practices12.setdefault(row["institution"].identity,[]).append(out)
        return ref
