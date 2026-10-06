"""Independent C4 raw reconstruction; imports no content/execution policy."""
from .crossing_audit import audit as audit_c3, extent as extent_c3, payload, decode, encode
from .crux_audit import _access
from .crux_composition_records import COMPOSITION_RECIPES, definition
from .cognitive_audit import audit_extent
from .operations import indexed
from .material import attrs
from .records import Account, Occurrence
from .particulars import DetailAddress
from . import codec


def extent(d):
    if not d.get("c4"): return extent_c3(d)
    r=COMPOSITION_RECIPES[d["recipe_key"]]
    if (d["movement"],d["origin"],d["destination"],d["polarity"],d["route_count"],d["material_units"])!=(r.name,r.origin,r.destination,r.polarity,2,0):
        raise ValueError("C4 formal contract differs")
    if tuple(d[f"route.{i}.element"][0] for i in range(2))!=tuple(e[0] for e in r.elements): raise ValueError("C4 Fold path differs")
    audit_extent(d)


def expected(d,values,child_rows,operations,depth):
    r=COMPOSITION_RECIPES[d["recipe_key"]]; a=r.action; refs=indexed(d,"source."); x=values[0]
    common=dict(target=d["content_target"],context=d["context"],source=refs[0])
    if a=="renew":
        own=values[1]
        return dict(common,kind="offer",cap=own["cap"],domain="WE",speaker=d["actor"],receiver=d["peer"],
            group=d["group"],question_demand=d["demand"],status="offered",source_kind="shared",consent=own["consent"],prior=refs[0])
    if a=="commune":
        offer,reply=values[1:]; inward=r.polarity=="accumulation"; assents=(offer["consent"],reply["consent"])
        return dict(common,kind="shared",cap=min(offer["cap"],reply["own_cap"]),offered_cap=offer["cap"],
            participants=(d["actor"],d["peer"]),group=d["group"],exchange=refs[1:],prior=refs[0],
            positions=(offer["cap"],reply["own_cap"]),difference=offer["cap"]!=reply["own_cap"],prior_difference=x["difference"],
            assents=assents,authorized=not inward and all(assents),mode="understood" if inward else "commitment",
            status="understood" if inward else ("accepted" if all(assents) else "declined"),competence=False)
    if a=="integrate":
        limits=tuple(v["cap"] for v in values)
        coupled=r.polarity=="expenditure" and all(v.get("authority")==d["actor"] and v["status"]=="governed_arrangement" for v in values)
        return dict(common,kind="model",cap=None if None in limits else min(limits),formula="min(demand, cap, observed_available)",
            components=refs,limits=limits,differences=len(set(limits))>1,
            assumptions=("conjunctive constraints in the same consumable context","component evidence remains historical"),
            uncertain=any(v["uncertain"] for v in values),coupled=coupled,authority=d["actor"] if coupled else None,
            status="governed_arrangement" if coupled else "dependency_model",competence=False)
    if a=="context":
        limits=(x["cap"],values[1]["cap"],values[2]["available"])
        return dict(common,kind="model",cap=None if None in limits else min(limits),formula="min(demand, cap, observed_available)",
            source_context=x["context"],local_evidence=refs[1:],limits=limits,differences=len(set(limits))>1,
            assumptions=("source model is a hypothesis in the destination context","local observation is historical"),
            uncertain=True,authority=None,status="dependency_model",competence=False)
    if a=="parent":
        claims=decode(d["children_payload"]); complete=all(row[2]=="succeeded" and row[7] for row in child_rows)
        return dict(common,kind="nested",children=claims["children"],links=claims["links"],outcomes=child_rows,
            complete=complete,status="complete" if complete else "blocked",depth=depth,operations=operations,
            cited_spending=sum(n for _,n in operations),polarities=tuple(row[6] for row in child_rows),competence=False)
    if a=="release":
        return dict(values[1],source=refs[1],gate=refs[0],gate_satisfied=x["complete"],
            cap=values[1]["cap"] if x["complete"] else None,competence=False)
    raise ValueError("unknown audited composition")


def audit(transactions,access_text,*,extent_check=extent,extended_flags=()):
    txs=tuple(transactions); versions={v.ref:v for tx in txs for v in tx.versions}
    times={v.ref:tx.at.tick for tx in txs for v in tx.versions}
    details,bindings=_access(access_text,versions,times)
    deps={}; public={}; c4_outputs={}; c4_messages={}
    for tx in txs:
        for v in tx.versions:
            z=attrs(v)
            if any(z.get(f) for f in ("c2","c3","c4")) and z.get("status")=="succeeded" and z.get("binding"):
                deps[z["binding"]]=indexed(z,"dependency.")
                public.update({ref:z["binding"] for ref in indexed(z,"public.")})
    starts={}; chains={}; prepared={}; heads={}; results=[]; terminal=[]; renewals=set()
    for tx in txs:
        for job in (v for v in tx.versions if attrs(v).get("c4")):
            d=attrs(job); ident=job.ref.identity; actor=d["actor"]; r=COMPOSITION_RECIPES[d["recipe_key"]]
            if ident not in starts:
                if versions[d["recipe"]]!=definition(r): raise ValueError("altered C4 recipe")
                refs=indexed(d,"source.")
                if not 1<=len(refs)<=8 or len(set(refs))!=len(refs): raise ValueError("invalid C4 inputs")
                addresses=tuple(DetailAddress(z,d[f"evidence.key.{i}"]) for i,z in enumerate(indexed(d,"evidence.delivery.")))
                paid=[details[actor,z] for z in addresses]
                if len(set(addresses))!=len(addresses) or any(at>=tx.at.tick for _,at in paid): raise ValueError("unpaid or future C4 evidence")
                sources=tuple(dict.fromkeys(p.source for p,_ in paid)); values=[]
                for i,ref in enumerate(refs):
                    v=versions[ref]
                    if ref.identity.namespace=="u4.observation":
                        chosen=[p for p,_ in paid if p.source==ref]; fields={p.address.key:p.value for p in chosen}
                        if not {"event","outcome","context","primitive","actor"}<=set(fields) or fields["context"]!=d["context"]:
                            raise ValueError("missing paid scoped observation")
                        value=dict(fields,kind="observation")
                    elif ref in bindings:
                        b,at=bindings[ref]
                        context_ok=b.context!=d["context"] if r.action=="context" and i==0 else b.context==d["context"]
                        if b.actor!=actor or at>=tx.at.tick or not context_ok or b.cue!=d["cue"] or b.target.identity!=d["content_target"].identity or heads[ref.identity].ref!=ref:
                            raise ValueError("wrong C4 owner, context, referent or revision")
                        value=payload(v)
                        if ref not in deps:
                            if set(value)!={"kind","cap","consent"} or value["kind"]!="intention" or type(value["cap"]) is not int or not 0<=value["cap"]<=1000 or type(value["consent"]) is not bool:
                                raise ValueError("fabricated composition content")
                    else:
                        chosen=[p for p,_ in paid if p.source==ref and p.address.key=="payload"]
                        if ref not in public or len(chosen)!=1 or actor not in indexed(attrs(v),"audience.") or attrs(v)["context"]!=d["context"]:
                            raise ValueError("unread or unaddressed composed input")
                        value=decode(chosen[0].value)
                        if value["target"].identity!=d["content_target"].identity: raise ValueError("wrong public referent")
                    values.append(value)
                    origin=public.get(ref,ref)
                    if origin in deps and not set(deps[origin])<=set(indexed(d,"dependency.")): raise ValueError("lost composed authority dependency")
                x=values[0]; a=r.action
                if a=="commune" and r.polarity=="expenditure":
                    stamp=(actor,*refs[1:])
                    if stamp in renewals: raise ValueError("renewal exchange reused across commitments")
                    renewals.add(stamp)
                if d["group"]:
                    fields=[p for p,_ in paid if p.source==d["group"] and p.address.key=="payload"]
                    if len(fields)!=1 or heads[d["group"].identity].ref!=d["group"]: raise ValueError("unread or changed membership")
                    g=decode(fields[0].value)
                    if g["context"]!=d["context"] or len(g["members"])!=2 or actor not in g["members"] or d["peer"] and d["peer"] not in g["members"]:
                        raise ValueError("wrong parent group")
                if a in ("renew","commune"):
                    if not d["group"] or x["kind"]!="shared" or x["group"]!=d["group"] or set(x["participants"])!=set(g["members"]) or not d["peer"]:
                        raise ValueError("missing shared history")
                    if a=="renew":
                        if len(values)!=2 or values[1]["kind"]!="intention": raise ValueError("own renewal stance required")
                    else:
                        if len(values)!=3: raise ValueError("reciprocal renewal required")
                        offer,reply=values[1:]
                        if (offer.get("kind"),offer.get("prior"),offer.get("source"),offer.get("speaker"),offer.get("receiver"),offer.get("group"),
                            reply.get("kind"),reply.get("offer"),reply.get("speaker"),reply.get("receiver"),reply.get("group"),reply.get("understood"),reply.get("answer"))!=(
                            "offer",refs[0],refs[0],actor,d["peer"],d["group"],"reply",refs[1],d["peer"],actor,d["group"],offer["cap"],min(offer["cap"],offer["question_demand"])):
                            raise ValueError("renewal is detached from its prior or answer")
                elif a=="integrate":
                    if len(values)<2 or any(z["kind"]!="model" or z["formula"]!="min(demand, cap, observed_available)" for z in values): raise ValueError("incompatible generated system schemas")
                elif a=="context":
                    if len(values)!=3 or x["kind"]!="model" or values[1]["kind"]!="intention" or values[2]["kind"]!="observation" or values[2]["outcome"]!="succeeded" or "available" not in values[2]:
                        raise ValueError("context transfer lacks local evidence")
                elif a=="release":
                    if len(values)!=2 or x["kind"]!="nested" or values[1]["kind"]!="model" or refs[1] not in bindings or bindings[refs[1]][0].actor!=actor or refs[1] not in {z[1] for z in x["children"]}:
                        raise ValueError("parent cannot grant a foreign or uncited model")
                rows=[]; operations={}; depth=1
                if a=="parent":
                    claims=decode(d["children_payload"]); children=claims["children"]; links=claims["links"]
                    if not 1<=len(children)<=8 or len({c[0].identity for c in children})!=len(children) or refs!=tuple(c[1] for c in children): raise ValueError("invalid child declaration")
                    if len(set(links))!=len(links) or any(not 0<=left<right<len(children) for left,right in links): raise ValueError("invalid child DAG")
                    for (op,out),value in zip(children,values):
                        jd=attrs(versions[op]); fields={p.address.key:p.value for p,_ in paid if p.source==op}
                        if any(k not in fields or fields[k]!=jd.get(k) for k in ("actor","context","status","spent","result")):
                            raise ValueError("child receipt not paid-read")
                        if op.identity.namespace!="u4.operation" or heads[op.identity].ref!=op or jd["actor"]!=actor or jd["context"]!=d["context"] or jd["status"] not in ("succeeded","failed","cancelled") or not any(jd.get(f) for f in ("c1","c2","c3","c4")):
                            raise ValueError("unavailable child terminal evidence")
                        if jd.get("content_target",jd.get("target")).identity!=d["content_target"].identity: raise ValueError("child target differs")
                        if value["kind"]=="observation":
                            if value["event"]!=jd["result"]: raise ValueError("wrong child event")
                        elif out not in (jd.get("binding"),*indexed(jd,"public.")): raise ValueError("wrong child output")
                        if op not in indexed(d,"dependency."): raise ValueError("lost child dependency")
                        fulfilled=jd["status"]=="succeeded" and value.get("complete",True) and value.get("status") not in ("declined","blocked")
                        rows.append((op,out,jd["status"],jd["origin"],jd["destination"],actor,jd["polarity"],fulfilled))
                        operations[op]=jd["spent"]
                        if value["kind"]=="nested":
                            depth=max(depth,value["depth"]+1)
                            for ref,n in value["operations"]:
                                if ref in operations and operations[ref]!=n: raise ValueError("duplicated inconsistent charge")
                                operations[ref]=n
                    if depth>4 or len(operations)>64: raise ValueError("nesting budget exceeded")
                    for left,right in links:
                        ca,cb=children[left],children[right]; da,db=attrs(versions[ca[0]]),attrs(versions[cb[0]])
                        if da["destination"]!=db["origin"] or ca[1] not in indexed(db,"source."): raise ValueError("disconnected child handoff")
                operations=tuple(sorted(operations.items(),key=lambda z:(z[0].identity.namespace,z[0].identity.key,z[0].revision)))
                units=1+len(addresses)+sum(1+len(encode(z))//64 for z in values)+len(operations)
                if d["recall_units"]!=units: raise ValueError("unpaid compositional evidence")
                wanted=expected(d,values,tuple(rows),operations,depth)
                starts[ident]=d; prepared[ident]=(wanted,sources); chains[ident]=[]
            wanted,sources=prepared[ident]; chain=chains[ident]
            mutable={"completed","spent","status","failure","result","steps_completed","last_step","binding"}
            if any(d[k]!=v for k,v in starts[ident].items() if k not in mutable): raise ValueError("changed composition contract")
            threshold=d["recall_units"]; thresholds=[]
            for i in range(2):
                threshold+=sum(indexed(d,f"route.{i}.charges."))+d[f"route.{i}.content_units"]; thresholds.append(threshold)
            for step in (v for v in tx.versions if v.ref.identity.namespace=="c4.step"):
                i=len(chain); sd=attrs(step); acc=step.facet(Account)
                if i>=2 or (sd["index"],sd["step"],sd["operation"],sd["recipe"],sd["content_kind"],sd["paid_threshold"],sd["predecessor"])!=(i,r.steps[i],job.previous,r.ref,"c4",thresholds[i],chain[-1].ref if chain else d["source_input"]): raise ValueError("invalid paid composition handoff")
                if (sd["origin"],sd["destination"],sd["polarity"])!=(d[f"route.{i}.origin"],d[f"route.{i}.destination"],r.polarity) or acc.holder!=actor or acc.referent!=d["content_target"] or acc.sources!=(sd["predecessor"],*sources) or any(p.subject!=d["content_target"] or p.context!=d["context"] for p in acc.content): raise ValueError("composition meaning scope differs")
                correct=dict(kind="composition_work",work=encode(wanted)) if i==0 else decode(payload(chain[-1])["work"])
                if payload(step)!=correct or i==1 and correct!=wanted: raise ValueError("C4 content postcondition differs")
                chain.append(step)
            if len(chain)!=d["steps_completed"] or len(chain)!=sum(t<=d["completed"] for t in thresholds) or d["last_step"]!=(chain[-1].ref if chain else None): raise ValueError("missing paid composition content")
            if d["status"]=="succeeded":
                if len(chain)!=2 or any(heads.get(z.identity,versions[z]).ref!=z for z in indexed(d,"dependency.")): raise ValueError("stale or unfinished composition completed")
                output=d["binding"]; v=versions[output]; acc=v.facet(Account)
                if payload(v)!=wanted or acc.sources!=sources or acc.holder!=actor or acc.referent!=d["content_target"] or any(p.subject!=d["content_target"] or p.context!=d["context"] for p in acc.content) or v.occurrence!=Occurrence.INTERPRETATION:
                    raise ValueError("unjustified composed output")
                if output not in bindings or bindings[output][0].particulars!=tuple(DetailAddress(z,d[f"evidence.key.{i}"]) for i,z in enumerate(indexed(d,"evidence.delivery."))): raise ValueError("composed retention differs from receipt")
                pubs=indexed(d,"public.")
                if len(pubs)!=(1 if r.action in ("renew","commune") else 0): raise ValueError("invented public composition")
                for ref in pubs:
                    pd=attrs(versions[ref]); group=decode(next(p.value for p,_ in [details[actor,z] for z in bindings[output][0].particulars] if p.source==d["group"] and p.address.key=="payload"))
                    if payload(versions[ref])!=wanted or indexed(pd,"audience.")!=group["members"] or pd["actor"]!=actor or pd["context"]!=d["context"] or pd["operation"]!=job.previous:
                        raise ValueError("invalid public C4 handoff")
                    c4_messages[ref]=output
                c4_outputs[output]=indexed(d,"dependency.")
                results.append(dict(recipe=r.key,output=codec.encode(output),spent=d["spent"],complete=wanted.get("complete"),kind=wanted["kind"]))
            if d["status"] in ("succeeded","failed","cancelled"): terminal.append(d["status"])
        for job in (v for v in tx.versions if attrs(v).get("c3") and v.previous is None):
            d=attrs(job)
            if d["recipe_key"]=="apply-expenditure-v1":
                ref=d["source_input"]
                if ref.identity.namespace.startswith("c4."):
                    x=payload(versions[ref])
                    if "coupled" in x and not x["coupled"]: raise ValueError("uncoupled system exercised as authority")
        heads.update({v.ref.identity:v for v in tx.versions})
    report=audit_c3(txs,access_text,extent_check=extent_check,extended_flags=("c4",*extended_flags),validated_outputs=c4_outputs,validated_messages=c4_messages)
    report.update(c4_attempts=len(starts),c4_completed=len(results),c4_steps=sum(len(c) for c in chains.values()),
        c4_results=results,c4_terminals=terminal,c4_independent_content_check=True)
    return report
