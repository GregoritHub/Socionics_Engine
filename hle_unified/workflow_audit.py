"""Independent raw workflow reconstruction; never calls execution or selection.

Checks native accounting/material law, scoped access, semantic postconditions,
exact votes, paid handoffs and public retention against immutable raw records.
"""
from .workflow_records import WORKFLOW_RECIPES, definition
from .workflow_reference import expected, schedule, answer, observed_tasks, response_tasks, check_authored, encode, decode
from .selection_audit import audit as inherited_audit, extent as inherited_extent
from .cognitive_audit import audit_extent
from .crux_audit import _access
from .records import Account, Occurrence
from .particulars import DetailAddress
from .material import attrs
from .operations import indexed

def payload(v):
    a=v.facet(Account)
    if a is None:return decode(attrs(v)["payload"])
    if len(a.content)!=1 or a.content[0].relation not in ("c7w.data","payload"): raise ValueError("exact workflow payload required")
    return decode(a.content[0].object)

def extent(d):
    if not d.get("c7w"):return inherited_extent(d)
    r=WORKFLOW_RECIPES[d["recipe_key"]]
    if (d["movement"],d["main"],d["origin"],d["destination"],d["polarity"],d["material_units"],d["route_count"])!=(r.name,r.main,r.origin,r.destination,r.polarity,r.material_units,len(r.steps)):
        raise ValueError("workflow recipe/route differs")
    if tuple(d[f"route.{i}.element"][0] for i in range(d["route_count"]))!=tuple(e[0] for e in r.elements):raise ValueError("workflow Fold families differ")
    audit_extent(dict(d,required=d["required"]-r.material_units))

def contract(d,items,refs,group,owned):
    r=WORKFLOW_RECIPES[d["recipe_key"]];a=r.action;x=items[0];inward=r.polarity=="accumulation"
    kinds={"contemplate":(("intention","stance"),2),"express":(("intention",),1),"theorize":(("intention","personal"),1),
        "embody":(("activity",),1),"act":(("activity",),1),"organize":(("activity",),None),
        "share":(("intention","personal"),3),"coordinate":(("activity",),3),"educate":(("system","rule"),3),"commune":(("shared",),3),
        "identify":(("shared",),2),"understand":(("system","rule"),2),"mobilize":(("shared",),1),"apply":(("system","rule"),1),"integrate":(("system",),2)}
    if a in kinds:
        accepted,count=kinds[a]
        if x["kind"] not in accepted or count is not None and len(items)!=count:raise ValueError("input perspective/schema differs")
        if a in ("contemplate","integrate","organize") and any(v["kind"] not in accepted for v in items):raise ValueError("heterogeneous input")
    if a in ("offer","reply","vote","identify","understand"):
        if len(items)!=2 or refs[1] not in owned:raise ValueError("actor-owned stance missing")
        check_authored(items[1])
    social=a in ("offer","reply","vote","share","coordinate","educate","commune","identify","mobilize","institutionalize") or x["kind"] in ("shared","rule")
    if social and group is None:raise ValueError("actual group absent")
    if group:
        if group["context"]!=d["context"] or len(group["members"])!=2 or d["actor"] not in group["members"] or d["peer"] not in group["members"]:raise ValueError("invalid shared membership")
        if x["kind"] in ("shared","rule") and (x["group"]!=d["group"] or set(x["participants"])!=set(group["members"])):raise ValueError("shared scope differs")
        if any(t[5] not in group["members"] for v in items for t in v.get("tasks",())):raise ValueError("nonparticipant task assignment")
    if a=="offer" and x["kind"] not in {"I":("intention","personal"),"IT":("activity",),"WE":("shared",),"ITS":("system","rule")}[r.origin]:raise ValueError("offer source differs")
    if a=="reply" and (x.get("kind"),x.get("speaker"),x.get("receiver"),x.get("group"))!=("offer",d["peer"],d["actor"],d["group"]):raise ValueError("wrong offer address")
    if a in ("share","coordinate","educate","commune"):
        offer,reply=items[1:]; tasks=response_tasks(x) if x["kind"]=="activity" else x["tasks"]
        if (offer.get("kind"),reply.get("kind"),offer.get("source"),offer.get("speaker"),offer.get("receiver"),reply.get("offer"),reply.get("speaker"),reply.get("receiver"),offer.get("group"),reply.get("group"),offer.get("tasks"))!=(
            "offer","reply",refs[0],d["actor"],d["peer"],refs[1],d["peer"],d["actor"],d["group"],d["group"],tasks):raise ValueError("reciprocal exchange missing")
    if a=="vote" and (x.get("kind"),x.get("status"))!=("rule","draft"):raise ValueError("exact draft absent")
    if a=="institutionalize":
        if inward:
            if len(items)<2 or x["kind"]!="shared" or any(v["kind"]!="activity" or v["outcome"]!="succeeded" or v["actor"] not in group["members"] or v["primitive"] not in {t[1] for t in x["tasks"]} for v in items[1:]):raise ValueError("relevant member practice absent")
        elif (len(items)!=3 or x["kind"]!="rule" or x["status"]!="draft" or {v.get("speaker") for v in items[1:]}!=set(group["members"])
            or any(v.get("kind")!="vote" or v["draft"]!=refs[0] or v["tasks"]!=x["tasks"] or v["group"]!=d["group"] for v in items[1:])):raise ValueError("exact current votes absent")
    if a=="use" and (len(items)!=1 or x["kind"] not in {"I":("personal",),"IT":("activity",),"WE":("shared",),"ITS":("system","rule")}[r.origin]):raise ValueError("unsupported consumer")
    if a=="organize" and (any(v["outcome"]!="succeeded" for v in items) or not inward and any(v.get("owner")!=d["actor"] for v in items)):raise ValueError("unearned organization authority")
    if a=="organize" and len({v["event"] for v in items})!=len(items):raise ValueError("repeated readings counted as actual activities")
    permitted=x.get("consent",True)
    if a=="mobilize" or a=="apply" and x["kind"]=="rule":permitted=x.get("authorized",False)
    if a=="apply" and x["kind"]=="system" and x.get("authority") is not None:permitted=permitted and x["authority"]==d["actor"]
    if d["permitted"]!=permitted:raise ValueError("forged personal/shared authority")
    if r.material_units:
        if not permitted or decode(d["query_completed"])["done"] or d["query_clock"]:raise ValueError("imagined completion or absent assent")
        if a!="act" and not inward:
            first=answer(schedule((x,)),(),0)
            if first is None or (first[1],first[5])!=("care",d["actor"]):raise ValueError("assigned first task absent")
    if a=="act" and x.get("target")!=d["content_target"]:raise ValueError("unobserved equipment revision")

def audit(transactions,access_text):
    txs=tuple(transactions);report=inherited_audit(txs,access_text,extent_check=extent,extended_flags=("c7w",))
    versions={v.ref:v for tx in txs for v in tx.versions};times={v.ref:tx.at.tick for tx in txs for v in tx.versions}
    details,bindings=_access(access_text,versions,times)
    heads={};starts={};prepared={};chains={};outputs={};messages={};used=set();results=[]
    for (actor,_),(p,_) in details.items():
        if p.source.identity.namespace.startswith("c7w."):
            v=versions[p.source]
            if p.source.identity.namespace!="c7w.message" or actor not in indexed(attrs(v),"audience.") or p.address.key!="payload":raise ValueError("private workflow disclosure")
    for tx in txs:
        for event in (v for v in tx.versions if v.ref.identity.namespace=="u4.event" and "workflow_tick" in attrs(v)):
            if attrs(event)["workflow_tick"]!=event.facet(Account).at.tick or event.facet(Account).at!=tx.at:
                raise ValueError("forged activity occurrence time")
        for job in (v for v in tx.versions if attrs(v).get("c7w")):
            d=attrs(job);ident=job.ref.identity;actor=d["actor"];r=WORKFLOW_RECIPES[d["recipe_key"]]
            if ident not in starts:
                if versions[d["recipe"]]!=definition(r):raise ValueError("workflow recipe altered")
                addresses=tuple(DetailAddress(v,d[f"evidence.key.{i}"]) for i,v in enumerate(indexed(d,"evidence.delivery.")))
                paid=[details[actor,a] for a in addresses]
                if len(set(addresses))!=len(addresses) or any(at>=tx.at.tick for _,at in paid):raise ValueError("future or repeated evidence")
                sources=tuple(dict.fromkeys(p.source for p,_ in paid));refs=indexed(d,"source.");items=[];owned=set()
                if not 1<=len(refs)<=8 or len(set(refs))!=len(refs):raise ValueError("invalid workflow input budget")
                for ref in refs:
                    if ref.identity.namespace=="u4.observation":
                        selected=[p for p,_ in paid if p.source==ref];value={p.address.key:p.value for p in selected}
                        if not {"event","outcome","context","primitive","actor","workflow_tick"}<=set(value) or value["context"]!=d["context"] or value.get("target",d["content_target"]).identity!=d["content_target"].identity:raise ValueError("missing scoped actual activity")
                        if value["primitive"] not in ("care","inspect","use","transfer","return"):raise ValueError("unsupported observed primitive")
                        item=dict(value,kind="activity")
                    elif ref in bindings:
                        b,at=bindings[ref]
                        if (b.actor,b.context,b.cue,b.target.identity)!=(actor,d["context"],d["cue"],d["content_target"].identity) or at>=tx.at.tick or heads[ref.identity].ref!=ref:raise ValueError("foreign/stale owned input")
                        if len(b.content)!=1 or b.content[0].relation!="c7w.data" or b.content[0].subject!=b.target or b.content[0].context!=d["context"]:raise ValueError("invalid workflow proposition scope")
                        item=payload(versions[ref]);owned.add(ref)
                        if ref not in outputs:check_authored(item)
                    else:
                        selected=[p for p,_ in paid if p.source==ref and p.address.key=="payload"]
                        if ref not in messages or len(selected)!=1 or actor not in indexed(attrs(versions[ref]),"audience.") or attrs(versions[ref])["context"]!=d["context"]:raise ValueError("unreceived workflow output")
                        item=decode(selected[0].value)
                        if item["target"].identity!=d["content_target"].identity:raise ValueError("foreign message target")
                    origin=messages.get(ref,ref)
                    if origin in outputs and not set(outputs[origin])<=set(indexed(d,"dependency.")):raise ValueError("lost transitive dependency")
                    items.append(item)
                group=None
                if d["group"]:
                    gp=[p for p,_ in paid if p.source==d["group"] and p.address.key=="payload"]
                    if len(gp)!=1 or heads[d["group"].identity].ref!=d["group"]:raise ValueError("unread/stale group")
                    group=decode(gp[0].value)
                contract(d,items,refs,group,owned)
                if r.action=="mobilize" or r.material_units and items[0]["kind"]=="rule":
                    stamp=(actor,messages.get(refs[0],refs[0]))
                    if stamp in used:raise ValueError("reused commitment")
                    used.add(stamp)
                if d["recall_units"]!=1+len(addresses)+sum(1+len(encode(v))//64 for v in items):raise ValueError("unpaid content reading")
                starts[ident]=d;prepared[ident]=(items,sources,group);chains[ident]=[]
            items,sources,group=prepared[ident];chain=chains[ident]
            mutable={"completed","spent","status","failure","result","steps_completed","last_step","binding"}
            if any(d[k]!=v for k,v in starts[ident].items() if k not in mutable):raise ValueError("workflow inputs changed during work")
            threshold=d["recall_units"];thresholds=[]
            for i in range(len(r.steps)):
                threshold+=sum(indexed(d,f"route.{i}.charges."))+d[f"route.{i}.content_units"];thresholds.append(threshold)
            wanted=expected(d,items,r)
            for step in (v for v in tx.versions if v.ref.identity.namespace=="c7w.step"):
                i=len(chain);sd=attrs(step);a=step.facet(Account)
                if (i>=len(r.steps) or sd["index"]!=i or sd["step"]!=r.steps[i] or sd["operation"]!=job.previous or sd["recipe"]!=r.ref
                    or sd["content_kind"]!="c7w" or sd["paid_threshold"]!=thresholds[i] or d["completed"]<thresholds[i]
                    or sd["predecessor"]!=(chain[-1].ref if chain else d["source_input"])
                    or (sd["origin"],sd["destination"],sd["polarity"])!=(d[f"route.{i}.origin"],d[f"route.{i}.destination"],d["polarity"])
                    or a.holder!=actor or a.referent!=d["content_target"] or a.sources!=(sd["predecessor"],*sources)
                    or any(p.subject!=d["content_target"] or p.context!=d["context"] for p in a.content)):
                    raise ValueError("unpaid/disconnected workflow handoff")
                correct=dict(kind="resolved_work",content=encode(wanted)) if r.steps[i].startswith("resolve:") else wanted
                if payload(step)!=correct or chain and wanted!=decode(payload(chain[-1])["content"]):raise ValueError("workflow semantic postcondition differs")
                chain.append(step)
            if len(chain)!=d["steps_completed"] or len(chain)!=sum(v<=d["completed"] for v in thresholds) or d["last_step"]!=(chain[-1].ref if chain else None):raise ValueError("missing paid workflow content")
            if d["status"]=="succeeded":
                if len(chain)!=len(r.steps) or any(heads.get(ref.identity,versions[ref]).ref!=ref for ref in indexed(d,"dependency.")):raise ValueError("stale/incomplete workflow completed")
                final=payload(chain[-1]);output=d["result"]
                if r.material_units:
                    if final["kind"]!="command" or not final["permitted"] or (d["primitive"],d["target"])!=(final["primitive"],final["target"]):raise ValueError("material command bypass")
                    if d["primitive"]=="care" and d["stock"]!=final["stock"] or d["primitive"]=="return" and d["relation"]!=final["relation"] or d["primitive"]=="transfer" and d["recipient"]!=final["peer"]:raise ValueError("material roles bypassed command")
                else:
                    output=d["binding"]
                    if output not in bindings or bindings[output][1]!=tx.at.tick or payload(versions[output])!=final:raise ValueError("retention bypassed workflow")
                    outputs[output]=indexed(d,"dependency.")
                    audience=tuple(group["members"]) if group else (actor,d["peer"]) if d["peer"] else (actor,)
                    for ref in indexed(d,"public."):
                        pd=attrs(versions[ref])
                        if payload(versions[ref])!=final or (pd["operation"],pd["actor"],pd["context"],indexed(pd,"audience."))!=(job.previous,actor,d["context"],audience):raise ValueError("public result/uptake differs")
                        messages[ref]=output
                results.append(dict(recipe=r.key,main=r.main,route=r.name,polarity=r.polarity,spent=d["spent"],output=output,inputs=indexed(d,"source.")))
        heads.update({v.ref.identity:v for v in tx.versions})
    report.update(workflow_attempts=len(starts),workflow_completed=len(results),workflow_main_completed=sum(v["main"] for v in results),
        workflow_steps=sum(len(v) for v in chains.values()),workflow_results=results,workflow_independent_content_check=True)
    return report
