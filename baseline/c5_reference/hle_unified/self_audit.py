"""Independent C2 semantic validator over raw transactions and access archive.

No executor, content transformer, runtime indexes, or selector is imported.
The audit checks complete postconditions and reconstructs paid provenance.
"""
from . import codec
from .crux_audit import audit as audit_c1, _access, _extent as extent_c1
from .cognitive_audit import audit_extent
from .self_records import SELF_RECIPES, SELF_NAMES, definition
from .records import Account, ObjectRef, Composition, Occurrence
from .particulars import DetailAddress
from .material import attrs
from .operations import indexed


def decode(text):
    rows=codec.loads(text); result=dict(rows)
    if len(result)!=len(rows): raise ValueError("duplicate audited field")
    return result


def payload(value):
    a=value.facet(Account)
    if a is not None:
        if len(a.content)!=1 or a.content[0].relation not in ("payload","c2.data"):
            raise ValueError("one typed audited payload required")
        return decode(a.content[0].object)
    return decode(attrs(value)["payload"])


def extent(d):
    if not d.get("c2"): return extent_c1(d)
    recipe=SELF_RECIPES[d["recipe_key"]]
    if (d["movement"],d["origin"],d["destination"],d["polarity"],d["material_units"],d["route_count"])!=(recipe.name,recipe.origin,recipe.destination,recipe.polarity,recipe.material_units,len(recipe.steps)):
        raise ValueError("C2 route contract mismatch")
    if tuple(d[f"route.{i}.element"][0] for i in range(d["route_count"]))!=tuple(e[0] for e in recipe.elements):
        raise ValueError("C2 unsupported semantic processing path")
    audit_extent(dict(d,required=d["required"]-recipe.material_units))


def structure(systems):
    # Independently construct all distinct interfaces, then check their partial order.
    rows=tuple(sorted(set(row for s in systems for row in s["nodes"])))
    names=sorted({row[0] for row in rows})
    conflicts=tuple(n for n in names if sum(row[0]==n for row in rows)!=1)
    arcs=set()
    for left in rows:
        for right in rows:
            if left[0]!=right[0]:
                arcs.update((left[0],right[0],x) for x in set(left[2]).intersection(right[1]))
    order=[]; remaining=set(names)
    while remaining:
        candidates=[n for n in sorted(remaining) if all(a not in remaining for a,b,_ in arcs if b==n)]
        if not candidates: break
        for n in candidates: remaining.remove(n); order.append(n)
    external=tuple(sorted(set(x for n in rows for x in n[1])-set(x for n in rows for x in n[2])))
    return dict(nodes=rows,edges=tuple(sorted(arcs)),conflicts=conflicts,cycles=tuple(sorted(remaining)),
                external=external,order=tuple(order),compatible=not conflicts and not remaining)


def expected_step(name,d,inputs,previous,facts):
    refs=indexed(d,"source."); actor=d["actor"]; target=d["target"]
    if name in ("differentiate","rehearse"):
        alternatives=tuple(sorted({x["condition"] for x in inputs if x["condition"] is not None}))
        supported=tuple(sorted({x["condition"] for x in inputs if not x["hypothetical"] and x["condition"] is not None}))
        return dict(kind="differentiation" if name=="differentiate" else "rehearsal",alternatives=alternatives,
            supported=supported,unresolved=len(supported)!=1,hypothetical=any(x["hypothetical"] for x in inputs),sources=refs)
    if name=="retain_meaning": return {**previous,"kind":"meaning","condition":previous["supported"][0] if len(previous["supported"])==1 else None}
    if name=="retain_policy": return {**previous,"kind":"policy","attention":"inspect" if previous["hypothetical"] or previous["unresolved"] else "use",
        "basis":"hypothetical_rehearsal" if previous["hypothetical"] else "owned_comparison"}
    if name in ("prepare_repair","prepare_use"):
        return dict(kind="material_plan",primitive="repair" if name=="prepare_repair" else "use",
                    target=target,tool=d["requested_tool"],stock=d["requested_stock"])
    if name=="material_command": return {**previous,"kind":"material_command"}
    if name=="offer": return dict(kind="offer",speaker=actor,receiver=d["peer"],group=d["group"],target=target,
                                    cap=inputs[0]["cap"],consent=inputs[0]["consent"],stance=refs[0])
    if name=="read_offer": return dict(kind="reading",offer=refs[1],offered=inputs[1]["cap"],cap=inputs[0]["cap"],consent=inputs[0]["consent"],speaker=inputs[1]["speaker"])
    if name=="reply": return dict(kind="reply",speaker=actor,receiver=previous["speaker"],offer=previous["offer"],group=d["group"],target=target,
            cap=previous["cap"],consent=previous["consent"],understood=previous["offered"],stance=refs[0])
    if name in ("clarify","acknowledge"):
        a,b=inputs
        return dict(kind="reciprocal",participants=(a["speaker"],b["speaker"]),group=d["group"],target=target,
            cap=min(a["cap"],b["cap"]),positions=(a["cap"],b["cap"]),difference=a["cap"]!=b["cap"],assents=(a["consent"],b["consent"]),exchange=refs)
    if name in ("shared_meaning","shared_commitment"):
        outward=name=="shared_commitment"; consent=all(previous["assents"])
        return {**previous,"kind":"shared","mode":"commitment" if outward else "understood",
                "authorized":outward and consent,"status":("accepted" if consent else "declined") if outward else "understood"}
    if name in ("reconcile","interfaces"): return dict(kind="reconciliation",sources=refs,**structure(inputs))
    if name in ("retain_system","couple_system"):
        return {**previous,"kind":"organization" if name=="couple_system" else "reconciled_model",
                "coupled":name=="couple_system" and previous["compatible"],"authority":actor}
    if name=="evaluate":
        source=inputs[0]; kind=source["kind"]
        result=dict(kind="evaluation",source=refs[0],content_kind=kind,action="none",amount=0,
                    target=target,tool=d["requested_tool"],stock=d["requested_stock"])
        if kind in ("personal","meaning","policy"):
            result["action"]=(source["attention"] if kind=="policy" else "use" if source.get("condition")=="serviceable" and not source.get("hypothetical",False) else "inspect")
        elif kind=="shared":
            result.update(action="consume" if source["authorized"] else "propose",amount=min(d["demand"],source["cap"]),
                          group=source["group"],participants=source["participants"],status=source["status"])
        else:
            model=structure((source,)) if kind=="system" else source
            have=set(facts); fired=[]
            if model["compatible"]:
                for key in model["order"]:
                    node=next(row for row in model["nodes"] if row[0]==key)
                    if all(x in have for x in node[1]):
                        fired.append(node); have.update(node[2])
            result.update(reachable=tuple(sorted(have)),steps=tuple(n[0] for n in fired),initial_facts=tuple(facts))
            if kind=="organization" and source["coupled"] and fired: result["action"]=fired[0][3]
        return result
    if name=="decide":
        result={**previous,"kind":"decision"}
        if result["amount"]==0 and result["action"] in ("consume","propose"): result["action"]="none"
        return result
    raise ValueError("unknown audited semantic step")


def audit(transactions,access_text,*,extent_check=extent,extended_flags=()):
    transactions=tuple(transactions)
    report=audit_c1(transactions,access_text,extent_check=extent_check,extended_flags=("c2",*extended_flags))
    versions={v.ref:v for tx in transactions for v in tx.versions}
    times={v.ref:tx.at.tick for tx in transactions for v in tx.versions}
    details,bindings=_access(access_text,versions,times)
    starts={}; chains={}; prepared={}; outputs=set(); public=set(); heads={}; results=[]; consumers=[]; commitments=set(); output_deps={}; public_bindings={}
    for tx in transactions:
        for job in (v for v in tx.versions if attrs(v).get("c2")):
            d=attrs(job); identity=job.ref.identity; actor=d["actor"]; recipe=SELF_RECIPES[d["recipe_key"]]
            if identity not in starts:
                if versions[d["recipe"]]!=definition(recipe): raise ValueError("changed C2 recipe")
                addresses=tuple(DetailAddress(x,d[f"evidence.key.{i}"]) for i,x in enumerate(indexed(d,"evidence.delivery.")))
                paid=[details[actor,a] for a in addresses]
                if any(t>=tx.at.tick for _,t in paid): raise ValueError("future C2 evidence")
                sources=tuple(dict.fromkeys(p.source for p,_ in paid)); inputs=[]
                for ref in indexed(d,"source."):
                    if recipe.name=="Act":
                        if ref not in {p.subject for p,_ in paid} and ref not in {p.source for p,_ in paid}:
                            # Other material roles must still have prior paid access.
                            if not any(a==actor and p.source==ref and at<tx.at.tick for (a,_),(p,at) in details.items()):
                                raise ValueError("unknown concrete Act input")
                        continue
                    if ref in bindings:
                        b,when=bindings[ref]
                        if (b.actor!=actor or when>=tx.at.tick or b.context!=d["context"] or b.cue!=d["cue"]
                                or b.target.identity!=d["target"].identity): raise ValueError("C2 input ownership/scope mismatch")
                        if any(other.ref.identity==ref.identity and other.ref.revision>ref.revision and at<tx.at.tick for other,at in bindings.values()):
                            raise ValueError("superseded owned C2 input")
                        inputs.append(payload(versions[ref]))
                    else:
                        candidates=[p for p,_ in paid if p.source==ref and p.address.key=="payload"]
                        if ref not in public or len(candidates)!=1 or actor not in indexed(attrs(versions[ref]),"audience."):
                            raise ValueError("shared result lacks actual addressed paid exchange")
                        inputs.append(decode(candidates[0].value))
                for ref in indexed(d,"source."):
                    origin=public_bindings.get(ref,ref)
                    if origin in output_deps and not set(output_deps[origin])<=set(indexed(d,"dependency.")):
                        raise ValueError("lost transitive content or consent dependency")
                for x in inputs:
                    if x.get("kind")=="system":
                        laws={"repair":(("damaged",),("serviceable",)),"use":(("serviceable",),("used",)),"care":(("worn",),("maintained",)),"damage":(("serviceable",),("damaged",))}
                        if len(x["nodes"])>16 or any(n[4]!=actor or (n[1],n[2])!=laws.get(n[3]) for n in x["nodes"]):
                            raise ValueError("invalid system authority or primitive interface")
                if recipe.name=="Contemplate" and (len(inputs)<2 or any(x["kind"]!="personal" for x in inputs)):
                    raise ValueError("personal comparison input missing")
                if recipe.name=="Integrate" and (len(inputs)<2 or any(x["kind"]!="system" for x in inputs)):
                    raise ValueError("system input missing")
                if d["group"] is not None:
                    g=heads.get(d["group"].identity)
                    gpaid=[p for p,_ in paid if p.source==d["group"] and p.address.key=="payload"]
                    if g is None or g.ref!=d["group"] or len(gpaid)!=1:
                        raise ValueError("unread or stale shared authority")
                    gd=decode(gpaid[0].value)
                    if actor not in gd["members"] or d["peer"] is not None and d["peer"] not in gd["members"]:
                        raise ValueError("missing participant membership")
                if recipe.name=="Reply":
                    offer=inputs[1]
                    if (offer["receiver"],offer["speaker"],offer["group"])!=(actor,d["peer"],d["group"]): raise ValueError("reply address mismatch")
                if recipe.name=="Commune":
                    a,b=inputs
                    if (a["kind"],b["kind"],a["speaker"],b["speaker"],a["receiver"],b["receiver"],b["offer"],b["understood"],a["group"],b["group"])!=("offer","reply",actor,d["peer"],d["peer"],actor,indexed(d,"source.")[0],a["cap"],d["group"],d["group"]):
                        raise ValueError("missing reciprocal content acknowledgment")
                expected_units=1+len(addresses)+sum(1+len(codec.dumps(tuple(sorted(x.items()))))//64 for x in inputs)
                if d["recall_units"]!=expected_units: raise ValueError("C2 input work extent mismatch")
                request_details=[p for p,_ in paid[:d["request_evidence_count"]]]
                fields={p.address.key:p.value for p in request_details if p.subject==d["target"]}
                facts=(fields["condition"],) if "condition" in fields else ()
                starts[identity]=d; chains[identity]=[]; prepared[identity]=inputs,facts,addresses,sources
            start=starts[identity]; chain=chains[identity]; inputs,facts,addresses,sources=prepared[identity]
            mutable={"completed","spent","status","failure","result","steps_completed","last_step","binding"}
            if any(d[k]!=v for k,v in start.items() if k not in mutable): raise ValueError("changed immutable C2 input")
            threshold=d["recall_units"]; thresholds=[]
            for i in range(len(recipe.steps)):
                threshold+=sum(indexed(d,f"route.{i}.charges."))+d[f"route.{i}.content_units"]
                thresholds.append(threshold)
            for step in (v for v in tx.versions if v.ref.identity.namespace=="c2.step"):
                i=len(chain); sd=attrs(step); a=step.facet(Account)
                if (i>=len(recipe.steps) or sd["index"]!=i or sd["step"]!=recipe.steps[i]
                        or sd["operation"]!=job.previous or sd["recipe"]!=recipe.ref
                        or sd["content_kind"]!="c2"
                        or (sd["origin"],sd["destination"],sd["polarity"])!=(d[f"route.{i}.origin"],d[f"route.{i}.destination"],d["polarity"])
                        or sd["paid_threshold"]!=thresholds[i] or d["completed"]<thresholds[i]
                        or sd["predecessor"]!=(d["source_input"] if not chain else chain[-1].ref)
                        or a.holder!=actor or a.referent!=d["target"]
                        or a.sources!=(sd["predecessor"],*sources)
                        or any(p.subject!=d["target"] or p.context!=d["context"] for p in a.content)):
                    raise ValueError("unpaid or disconnected C2 handoff")
                expected=expected_step(recipe.steps[i],d,inputs,None if not chain else payload(chain[-1]),facts)
                if payload(step)!=expected: raise ValueError("C2 semantic postcondition differs from accessible content")
                chain.append(step)
            if len(chain)!=d["steps_completed"] or len(chain)!=sum(t<=d["completed"] for t in thresholds):
                raise ValueError("C2 paid step omitted or duplicated")
            if d["last_step"]!=(chain[-1].ref if chain else None): raise ValueError("C2 final step mismatch")
            if d["status"]=="succeeded":
                if any(heads.get(x.identity,versions[x]).ref!=x for x in indexed(d,"dependency.")):
                    raise ValueError("C2 succeeded with stale dependency")
                if len(chain)!=len(recipe.steps): raise ValueError("incomplete C2 success")
                final=payload(chain[-1]); output=d["result"]
                if recipe.name=="Act":
                    if final.get("kind")!="material_command" or any(final[k]!=d[k] for k in ("primitive","target","tool","stock")):
                        raise ValueError("Act bypassed generated command")
                else:
                    output=d["binding"]
                    if output not in bindings or bindings[output][1]!=tx.at.tick or payload(versions[output])!=final:
                        raise ValueError("C2 retained output bypassed semantic result")
                    outputs.add(output)
                    output_deps[output]=indexed(d,"dependency.")
                    for ref in indexed(d,"public."):
                        message=versions[ref]; md=attrs(message); visible=payload(message)
                        if md["operation"]!=job.previous or md["actor"]!=actor or md["context"]!=d["context"]:
                            raise ValueError("unpaid public result")
                        if recipe.name in ("Offer","Reply","Commune"):
                            if visible!=final or indexed(md,"audience.")!=(actor,d["peer"]): raise ValueError("public exchange content diverged")
                        elif recipe.name=="Consume":
                            if visible.get("amount")!=final["amount"] or visible.get("source")!=final["source"] or final["action"]!="propose": raise ValueError("participation proposal bypassed consumer")
                        public.add(ref); public_bindings[ref]=output
                results.append(dict(movement=recipe.name,polarity=recipe.polarity,paid=d["spent"],output=codec.encode(output),
                    inputs=[codec.encode(x) for x in indexed(d,"source.")],steps=[codec.encode(x.ref) for x in chain],
                    result=codec.encode(tuple(sorted(final.items())))))
        for job in (v for v in tx.versions if attrs(v).get("c2_consumer") is not None and v.previous is None):
            d=attrs(job); source=d["c2_consumer"]
            if source not in outputs or bindings[source][0].actor!=d["actor"]: raise ValueError("downstream action lacks owned decision")
            decision=payload(versions[source]); op=decision["action"]
            if not set((source,*output_deps[source]))<=set(indexed(d,"dependency.")):
                raise ValueError("consumer lost input authority dependencies")
            if any(heads[x.identity].ref!=x for x in indexed(d,"dependency.")):
                raise ValueError("consumer used stale authority or concrete input")
            if decision["kind"]!="decision" or op!=d["primitive"]: raise ValueError("downstream material action ignores decision")
            if op=="consume" and (d["amount"]!=decision["amount"] or d["stock"]!=decision["stock"]): raise ValueError("participation exceeds agreed decision")
            if op!="consume" and d["target"]!=decision["target"]: raise ValueError("consumer changed target")
            if op=="consume":
                authorization=public_bindings.get(decision["source"],decision["source"])
                if d.get("c2_commitment")!=authorization:
                    raise ValueError("consumption lacks exact shared authorization")
            if d.get("c2_commitment") is not None:
                stamp=(d["actor"],d["c2_commitment"])
                if stamp in commitments: raise ValueError("commitment was exercised twice")
                commitments.add(stamp)
            consumers.append(codec.encode(source))
        heads.update({v.ref.identity:v for v in tx.versions})
    report.update(c2_attempts=len(starts),c2_completed=len(results),c2_self_completed=sum(r["movement"] in SELF_NAMES for r in results),
        c2_semantic_steps=sum(len(c) for c in chains.values()),c2_results=results,c2_material_consumers=consumers,
        c2_independent_content_check=True)
    return report
