"""Independent raw C3 reconstruction. No execution or content-policy imports."""
from . import codec
from .self_audit import audit as audit_c2, extent as extent_c2
from .crux_audit import _access
from .cognitive_audit import audit_extent
from .crossing_records import CROSSING_RECIPES, definition
from .records import Account, Occurrence, Material
from .particulars import DetailAddress
from .material import attrs
from .operations import indexed

def decode(text):
    rows=codec.loads(text)
    if type(rows) is not tuple or len(dict(rows))!=len(rows): raise ValueError("invalid typed C3 payload")
    return dict(rows)

def encode(value): return codec.dumps(tuple(sorted(value.items())))

def payload(v):
    account=v.facet(Account)
    if account is None: return decode(attrs(v)["payload"])
    if len(account.content)!=1 or account.content[0].relation not in ("payload","c3.data","c2.data"):
        raise ValueError("exact typed payload required")
    return decode(account.content[0].object)

def extent(d):
    if not d.get("c3"): return extent_c2(d)
    r=CROSSING_RECIPES[d["recipe_key"]]
    if (d["movement"],d["main"],d["origin"],d["destination"],d["polarity"],d["material_units"],d["route_count"])!=(r.name,r.main,r.origin,r.destination,r.polarity,r.material_units,len(r.steps)):
        raise ValueError("crossing contract differs")
    if tuple(d[f"route.{i}.element"][0] for i in range(d["route_count"]))!=tuple(e[0] for e in r.elements):
        raise ValueError("unsupported crossing family")
    audit_extent(dict(d,required=d["required"]-r.material_units))

def numeric(x): return x.get("available") if x["kind"]=="observation" else x.get("cap")
def amount(x,limit): return min(x,limit) if x is not None else 0

def expected(d,inputs,r):
    """Declarative postconditions, reconstructed from received/owned records."""
    actor=d["actor"]; refs=indexed(d,"source."); a=r.action; x=inputs[0]; inward=r.polarity=="accumulation"
    context=dict(target=d["content_target"],context=d["context"],source=refs[0])
    if a=="offer":
        return dict(context,kind="offer",cap=numeric(x),domain=r.origin,speaker=actor,receiver=d["peer"],
            group=d["group"],question_demand=d["demand"],status="offered",source_kind=x["kind"])
    if a=="reply":
        own=inputs[1]
        return dict(context,kind="reply",offer=refs[0],speaker=actor,receiver=d["peer"],group=d["group"],
            understood=numeric(x),answer=amount(numeric(x),x["question_demand"]),own_cap=own["cap"],
            consent=own["consent"],question="none" if own["cap"]==numeric(x) else "capacity_difference")
    if a=="vote":
        return dict(context,kind="vote",draft=refs[0],speaker=actor,group=d["group"],cap=numeric(x),
            assent=inputs[1]["consent"] and numeric(x) is not None and numeric(x)<=inputs[1]["cap"])
    if a in ("share","coordinate","educate"):
        reply=inputs[2]; understood=reply["understood"]
        source_assent=x.get("consent",True)
        return dict(context,kind="shared",cap=min(understood,reply["own_cap"]) if understood is not None else None,
            offered_cap=numeric(x),participants=(actor,d["peer"]),group=d["group"],exchange=(refs[1],refs[2]),
            difference=reply["question"],receiver_answer=reply["answer"],understood=understood,
            assents=(source_assent,reply["consent"]),mode="examined" if inward else "active_contribution",
            authorized=not inward and source_assent and reply["consent"],teaching=a=="educate",competence=False)
    if a=="theorize":
        return dict(context,kind="model",cap=x["cap"],formula="min(demand, cap, observed_available)",
            assumptions=("same context and consumable units","cap is an owned hypothesis"),
            test="compare actual consumption and remaining stock",uncertain=True,
            status="contained_hypothesis" if inward else "submitted_model")
    if a=="organize":
        quantities=tuple(v.get("available") for v in inputs); known=[v for v in quantities if v is not None]
        return dict(context,kind="model",cap=min(known) if known else None,formula="min(demand, cap, observed_available)",
            samples=refs,observed_limits=quantities,assumptions=("observed stock snapshots are historical","current custody still required"),
            dependencies=("available units","owner consent","paid execution"),authority=None if inward else actor,
            status="dependency_model" if inward else "governed_arrangement",uncertain=True)
    if a=="institutionalize":
        if not inward:
            passed=all(v["assent"] for v in inputs[1:])
            return dict(x,source=refs[0],status="ratified" if passed else "declined",votes=refs[1:],authorized=passed)
        return dict(context,kind="rule",cap=numeric(x),group=d["group"],participants=x["participants"],practice=refs[1],
            status="draft",authority="unanimous_exact_votes",votes=(),
            responsibilities=((actor,"pay own participation"),(d["peer"],"pay own participation")),
            enforcement="voluntary governed requests only",authorized=False)
    if a in ("embody","identify","understand"):
        own=inputs[1] if len(inputs)>1 else None; value=numeric(x)
        if own is not None and value is not None: value=min(own["cap"],value)
        return dict(context,kind="personal_policy",cap=value,mode="interpretation" if inward else "decision_policy",
            basis=x["kind"],limits=("this context and consumable units","no practiced competence conferred"),
            stance="declined" if own is not None and not own["consent"] else "accepted",
            consent=True if own is None else own["consent"],tension=False if own is None else numeric(x)!=own["cap"],competence=False)
    if a in ("express","apply","mobilize"):
        primitive="inspect" if inward and a!="apply" else "consume"
        units=amount(numeric(x),d["demand"])
        if a=="apply" and inward: units=min(units,1)
        permission=x.get("consent",True)
        if a=="mobilize" or a=="apply" and x["kind"]=="rule": permission=x.get("authorized",False)
        if a=="apply" and x.get("status")=="governed_arrangement": permission=x["authority"]==actor
        return dict(context,kind="material_command",primitive=primitive,stock=d["requested_stock"],
            amount=units if primitive=="consume" else 1,mode=("trial" if a=="apply" else "preparation") if inward else "performance",
            permitted=permission)
    if a=="use":
        units=amount(numeric(x),d["demand"])
        if d["observed_available"] is not None: units=min(units,d["observed_available"])
        allowed=x.get("consent",True)
        if x["kind"] in ("shared","rule"): allowed=x.get("authorized",False)
        if x.get("mode")=="interpretation" or x.get("status")=="dependency_model": allowed=False
        if x.get("status")=="governed_arrangement": allowed=x["authority"]==actor
        return dict(context,kind="decision",amount=units,cap=numeric(x),demand=d["demand"],status="selected" if allowed else "proposed",
            permitted=allowed,stock=d["requested_stock"],group=d["group"],action="consume" if allowed and units else "none")
    raise ValueError("unknown audited crossing")

def audit(transactions,access_text):
    txs=tuple(transactions)
    report=audit_c2(txs,access_text,extent_check=extent,extended_flags=("c3",))
    versions={v.ref:v for tx in txs for v in tx.versions}; times={v.ref:tx.at.tick for tx in txs for v in tx.versions}
    details,bindings=_access(access_text,versions,times)
    heads={}; starts={}; prepared={}; chains={}; outputs={}; messages={}; used=set(); results=[]; consumers=[]
    for tx in txs:
        for v in tx.versions:
            vd=attrs(v)
            if v.ref.identity.namespace=="u4.observation":
                source=v.facet(Account).sources
                if len(source)!=1: raise ValueError("observation event source absent")
                event=versions[source[0]]; ed=attrs(event)
                if (v.occurrence!=Occurrence.OBSERVATION or event.occurrence!=Occurrence.ACTUAL_EVENT
                    or vd!={k:z for k,z in ed.items() if not k.startswith("participant.")}
                    or v.facet(Account).content!=event.facet(Account).content
                    or v.facet(Account).referent!=event.facet(Account).referent
                    or v.facet(Account).holder not in indexed(ed,"participant.")):
                    raise ValueError("observation rewrites actual event")
            if v.ref.identity.namespace=="u4.event" and vd.get("outcome")=="succeeded" and "available" in vd:
                target=vd.get("stock") or vd.get("target"); material=versions[target]
                if vd["available"]!=material.facet(Material).quantity-attrs(material)["consumed"]:
                    raise ValueError("event stock amount differs from actual material")
        for job in (v for v in tx.versions if attrs(v).get("c3")):
            d=attrs(job); identity=job.ref.identity; actor=d["actor"]; r=CROSSING_RECIPES[d["recipe_key"]]
            if identity not in starts:
                if versions[d["recipe"]]!=definition(r): raise ValueError("altered recipe")
                addresses=tuple(DetailAddress(x,d[f"evidence.key.{i}"]) for i,x in enumerate(indexed(d,"evidence.delivery.")))
                paid=[details[actor,a] for a in addresses]
                if any(t>=tx.at.tick for _,t in paid): raise ValueError("future evidence")
                sources=tuple(dict.fromkeys(p.source for p,_ in paid)); inputs=[]; refs=indexed(d,"source.")
                for ref in refs:
                    value=versions[ref]
                    if ref.identity.namespace=="u4.observation":
                        selected=[p for p,_ in paid if p.source==ref]
                        fields={p.address.key:p.value for p in selected}
                        if not {"event","outcome","context","primitive","actor"}<=set(fields) or fields["context"]!=d["context"]:
                            raise ValueError("unread actual observation")
                        inputs.append(dict(fields,kind="observation"))
                    elif ref in bindings:
                        b,when=bindings[ref]
                        if (b.actor!=actor or when>=tx.at.tick or b.context!=d["context"] or b.cue!=d["cue"]
                            or b.target.identity!=d["content_target"].identity): raise ValueError("foreign or unscoped input")
                        if heads[ref.identity].ref!=ref: raise ValueError("superseded input")
                        item=payload(value)
                        if ref not in outputs and ref.identity.namespace!="c2.output":
                            if (set(item)!={"kind","cap","consent"} or item["kind"]!="intention" or
                                type(item["cap"]) is not int or not 0<=item["cap"]<=1000 or type(item["consent"]) is not bool):
                                raise ValueError("fabricated output or invalid intention")
                        inputs.append(item)
                    else:
                        selected=[p for p,_ in paid if p.source==ref and p.address.key=="payload"]
                        if (ref not in messages or len(selected)!=1 or actor not in indexed(attrs(value),"audience.")
                            or attrs(value)["context"]!=d["context"]): raise ValueError("missing actual public uptake")
                        item=decode(selected[0].value)
                        if item.get("target",d["content_target"]).identity!=d["content_target"].identity: raise ValueError("foreign message target")
                        inputs.append(item)
                    origin=messages.get(ref,ref)
                    if origin in outputs and not set(outputs[origin])<=set(indexed(d,"dependency.")):
                        raise ValueError("lost transitive evidence/authority")
                x=inputs[0]; a=r.action; g=None
                accepted={"express":(("intention",),1),"theorize":(("intention",),1),
                    "embody":(("observation",),1),"organize":(("observation",),None),
                    "share":(("intention",),3),"coordinate":(("observation",),3),"educate":(("model","rule"),3),
                    "identify":(("shared",),2),"understand":(("model","rule"),2),
                    "mobilize":(("shared",),1),"apply":(("model","rule"),1)}
                if a in accepted:
                    kinds,count=accepted[a]
                    if x["kind"] not in kinds or count is not None and len(inputs)!=count:
                        raise ValueError("input perspective/schema differs")
                if a in ("identify","understand","reply","vote") and inputs[1]["kind"]!="intention":
                    raise ValueError("own stance missing")
                if a in ("offer","use"):
                    kinds={"I":("intention","personal_policy"),"IT":("observation",),"WE":("shared",),"ITS":("model","rule")}
                    if len(inputs)!=1 or x["kind"] not in kinds[r.origin]: raise ValueError("source perspective differs")
                if d["group"]:
                    gp=[p for p,_ in paid if p.source==d["group"] and p.address.key=="payload"]
                    if len(gp)!=1 or heads[d["group"].identity].ref!=d["group"]: raise ValueError("unread or stale group")
                    g=decode(gp[0].value)
                    if len(g["members"])!=2 or actor not in g["members"] or d["peer"] and d["peer"] not in g["members"]:
                        raise ValueError("invalid participant process")
                    if x["kind"] in ("shared","rule") and (x["group"]!=d["group"] or set(x["participants"])!=set(g["members"])):
                        raise ValueError("shared process scope differs")
                if a in ("share","coordinate","educate"):
                    offer,reply=inputs[1:]
                    if (offer["kind"],reply["kind"],offer["source"],offer["speaker"],offer["receiver"],reply["offer"],
                        reply["speaker"],reply["receiver"],offer["group"],reply["group"],offer["cap"],reply["understood"],reply["answer"])!=(
                        "offer","reply",refs[0],actor,d["peer"],refs[1],d["peer"],actor,d["group"],d["group"],
                        numeric(x),numeric(x),amount(numeric(x),offer["question_demand"])):
                        raise ValueError("missing defining reciprocal understanding")
                if a=="reply" and (x["kind"],x["speaker"],x["receiver"],x["group"])!=("offer",d["peer"],actor,d["group"]):
                    raise ValueError("reply address differs")
                if a=="vote" and (x["kind"],x["status"])!=("rule","draft"): raise ValueError("vote lacks exact draft")
                if a=="institutionalize":
                    if r.polarity=="expenditure":
                        if (x["kind"]!="rule" or x["status"]!="draft" or len(inputs)!=3
                            or set(v["speaker"] for v in inputs[1:])!=set(g["members"])
                            or any(v["kind"]!="vote" or v["draft"]!=refs[0] or v["group"]!=d["group"] or v["cap"]!=x["cap"] for v in inputs[1:])):
                            raise ValueError("rule lacks exact votes")
                    else:
                        practice=inputs[1]
                        if (x["kind"]!="shared" or practice["kind"]!="observation" or practice["primitive"]!="consume"
                            or practice["outcome"]!="succeeded" or not set(x["participants"])<=set(indexed(attrs(versions[practice["event"]]),"participant."))):
                            raise ValueError("draft lacks actual shared practice")
                if a=="organize" and (any(z["kind"]!="observation" or z["outcome"]!="succeeded" or "available" not in z for z in inputs)
                    or r.polarity=="expenditure" and any(z.get("owner")!=actor for z in inputs)):
                    raise ValueError("organization inferred authority from foreign observation")
                if a=="mobilize" or a=="apply" and x["kind"]=="rule":
                    if not x.get("authorized",False): raise ValueError("missing material assent")
                    stamp=(actor,messages.get(refs[0],refs[0]))
                    if stamp in used: raise ValueError("repeated participation allowance")
                    used.add(stamp)
                stockfields={p.address.key:p.value for p,_ in paid if p.source==d["requested_stock"]}
                observed=(stockfields["quantity"]-stockfields["consumed"]) if "quantity" in stockfields and "consumed" in stockfields else None
                if observed!=d["observed_available"]: raise ValueError("hidden inventory used")
                units=1+len(addresses)+sum(1+len(encode(z))//64 for z in inputs)
                if d["recall_units"]!=units: raise ValueError("unpaid input work")
                starts[identity]=d; prepared[identity]=(inputs,sources,g); chains[identity]=[]
            inputs,sources,g=prepared[identity]; chain=chains[identity]
            mutable={"completed","spent","status","failure","result","steps_completed","last_step","binding","amount"}
            if any(d[k]!=v for k,v in starts[identity].items() if k not in mutable): raise ValueError("changed crossing inputs")
            threshold=d["recall_units"]; thresholds=[]
            for i in range(len(r.steps)):
                threshold+=sum(indexed(d,f"route.{i}.charges."))+d[f"route.{i}.content_units"]; thresholds.append(threshold)
            wanted=expected(d,inputs,r)
            for step in (v for v in tx.versions if v.ref.identity.namespace=="c3.step"):
                i=len(chain); sd=attrs(step); account=step.facet(Account)
                if (i>=len(r.steps) or sd["index"]!=i or sd["step"]!=r.steps[i] or sd["operation"]!=job.previous
                    or sd["recipe"]!=r.ref or sd["content_kind"]!="c3" or sd["paid_threshold"]!=thresholds[i]
                    or d["completed"]<thresholds[i] or sd["predecessor"]!=(chain[-1].ref if chain else d["source_input"])
                    or (sd["origin"],sd["destination"],sd["polarity"])!=(d[f"route.{i}.origin"],d[f"route.{i}.destination"],d["polarity"])
                    or account.holder!=actor or account.referent!=d["content_target"] or account.sources!=(sd["predecessor"],*sources)
                    or any(v.subject!=d["content_target"] or v.context!=d["context"] for v in account.content)):
                    raise ValueError("disconnected or unpaid semantic handoff")
                value=payload(step)
                if r.steps[i].startswith("scope:"): correct=dict(kind="scoped_work",work=encode(wanted))
                elif chain: correct=decode(payload(chain[-1])["work"])
                else: correct=wanted
                if value!=correct or not r.steps[i].startswith("scope:") and value!=wanted:
                    raise ValueError("C3 semantic postcondition differs from accessible evidence")
                chain.append(step)
            if len(chain)!=d["steps_completed"] or len(chain)!=sum(t<=d["completed"] for t in thresholds) or d["last_step"]!=(chain[-1].ref if chain else None):
                raise ValueError("missing paid content")
            if r.material_units and d["amount"]!=(wanted["amount"] if len(chain)==len(r.steps) else 1):
                raise ValueError("amount bypassed paid command")
            if d["status"]=="succeeded":
                if len(chain)!=len(r.steps) or any(heads.get(x.identity,versions[x]).ref!=x for x in indexed(d,"dependency.")):
                    raise ValueError("incomplete or stale crossing completed")
                final=payload(chain[-1]); output=d["result"]
                if r.material_units:
                    if final["kind"]!="material_command" or not final["permitted"] or final["amount"]<1 or d["primitive"]!=final["primitive"]:
                        raise ValueError("physical result bypassed content")
                else:
                    output=d["binding"]
                    if output not in bindings or bindings[output][1]!=tx.at.tick or payload(versions[output])!=final:
                        raise ValueError("retention bypassed content")
                    outputs[output]=indexed(d,"dependency.")
                    for ref in indexed(d,"public."):
                        public=versions[ref]; pd=attrs(public)
                        audience=tuple(g["members"]) if d["group"] else (actor,d["peer"]) if d["peer"] else (actor,)
                        if payload(public)!=final or pd["operation"]!=job.previous or pd["actor"]!=actor or pd["context"]!=d["context"] or indexed(pd,"audience.")!=audience:
                            raise ValueError("public result bypassed scoped work")
                        messages[ref]=output
                results.append(dict(recipe=r.key,main=r.main,route=r.name,polarity=r.polarity,spent=d["spent"],
                    inputs=[codec.encode(x) for x in indexed(d,"source.")],steps=[codec.encode(s.ref) for s in chain],output=codec.encode(output)))
        # Retain provenance from independently audited C2 supporting operations.
        for job in (v for v in tx.versions if attrs(v).get("c2") and attrs(v)["status"]=="succeeded"):
            d=attrs(job)
            if d.get("binding"):
                outputs[d["binding"]]=indexed(d,"dependency.")
                for ref in indexed(d,"public."): messages[ref]=d["binding"]
        for job in (v for v in tx.versions if attrs(v).get("c3_consumer") is not None and v.previous is None):
            d=attrs(job); plan=d["c3_consumer"]
            if plan not in outputs or bindings[plan][0].actor!=d["actor"]: raise ValueError("borrowed decision")
            decision=payload(versions[plan]); stamp=(d["actor"],d["c3_authority"])
            if (decision["kind"]!="decision" or not decision["permitted"] or decision["action"]!="consume"
                or (d["primitive"],d["amount"],d["stock"])!=("consume",decision["amount"],decision["stock"])
                or d["c3_authority"]!=messages.get(decision["source"],decision["source"]) or stamp in used
                or not set((plan,*outputs[plan]))<=set(indexed(d,"dependency."))
                or any(heads[x.identity].ref!=x for x in indexed(d,"dependency."))): raise ValueError("unauthorized downstream use")
            used.add(stamp); consumers.append(codec.encode(plan))
        for job in (v for v in tx.versions if attrs(v).get("c2_commitment") is not None and v.previous is None):
            d=attrs(job); stamp=(d["actor"],d["c2_commitment"])
            if stamp in used: raise ValueError("allowance reused across C2/C3")
            used.add(stamp)
        heads.update({v.ref.identity:v for v in tx.versions})
    report.update(c3_attempts=len(starts),c3_completed=len(results),c3_main_completed=sum(x["main"] for x in results),
        c3_semantic_steps=sum(len(x) for x in chains.values()),c3_results=results,c3_material_consumers=consumers,
        c3_independent_content_check=True)
    return report
