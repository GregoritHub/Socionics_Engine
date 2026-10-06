"""Offline language evidence audit. No participant policy or engine cache reads.

The U4/U9 auditors independently reconstruct debits, physical effects and run
decomposition. This auditor verifies language provenance and supplies only
checked U10 hypotheses to the U9 auditor's explicit extension hook.
"""
from . import codec
from .development_values import attrs
from .records import Account, Occurrence, Role, Relation
from .composition_audit import audit as audit9, _test


def _size(value):
    return 1 + sum(_size(x) for x in value) if type(value) is tuple else 1


def _resolve(body, meanings):
    tag=body[0]
    if tag=="word":
        item=meanings[body[1]]
        if item["status"]!="stable":raise ValueError("interpretation used unstable meaning")
        return item["program"]
    if tag in ("seq","choice"):return tag,tuple(_resolve(x,meanings) for x in body[1])
    if tag=="if":return tag,body[1],_resolve(body[2],meanings),_resolve(body[3],meanings)
    if tag=="because":return tag,body[1],_resolve(body[2],meanings)
    return body


def _trace(program,state):
    if program[0]=="act":return (program[1],)
    if program[0]=="seq":return tuple(a for p in program[1] for a in _trace(p,state))
    if program[0]=="if":return _trace(program[2] if _test(program[1],state) else program[3],state)
    raise ValueError("unsupported lexical demonstration constructor")


def _inline(program,records):
    if program[0]=="call":return _inline(records[program[1]]["program"],records)
    if program[0] in ("seq","choice"):return program[0],tuple(_inline(c,records) for c in program[1])
    if program[0]=="if":return "if",program[1],_inline(program[2],records),_inline(program[3],records)
    return program


def audit(transactions):
    versions,records,read,acquired,extensions={},{},{},{},{}
    counts=dict(language_commits=0,messages=0,interpretations=0,questions=0,
        lexical_versions=0,stable_learned_versions=0,meaning_repairs=0,
        practical_responses=0,refusals=0,explicit_commitments=0,fulfilled_commitments=0)
    for tx in transactions:
        pending={v.ref:v for v in tx.versions}
        for v in tx.versions:
            d=attrs(v)
            if d.get("record_type")!="operation":continue
            if d.get("u10"):
                expected=1+sum(d[k] for k in ("evidence_count","syntax_units","lexical_units","focus_units","sample_units"))
                if d["recall_units"]!=expected:raise ValueError("unpaid language extent")
            if d["status"]!="succeeded":continue
            actor=d["actor"]
            if d["primitive"]=="read":
                receipt=next(x for x in tx.versions if x.ref.identity.namespace=="u4.receipt")
                read.setdefault(actor,set()).add(attrs(receipt)["input.0"])
            if d["primitive"]=="acquire":acquired.setdefault(actor,set()).add(d["procedure"])
            if d.get("u10"):
                counts["language_commits"]+=1
                b=pending[d["binding"]].facet(Account)
                if b.holder!=actor or not set(b.sources)<=read.get(actor,set()):raise ValueError("foreign/unread language source")
        for v in tx.versions:
            ns=v.ref.identity.namespace;d=attrs(v)
            if ns=="u10.surface":
                job=attrs(versions[d["operation"]])
                if job["status"]!="ready" or not job.get("u10"):raise ValueError("unpaid language perspective")
            if not ns.startswith("u10.") or "kind" not in d:continue
            job=attrs(versions[d["operation"]])
            terminal=next((attrs(x) for x in tx.versions if x.previous==d["operation"]),None)
            if (not job.get("u10") or job["status"]!="ready" or not terminal or terminal["status"]!="succeeded"
                    or job["actor"]!=d["actor"] or terminal["binding"]!=d["binding"]):raise ValueError("unpaid language output")
            kind=d["kind"]
            if kind=="message":
                wire=dict(codec.loads(d["payload"]))
                if any(k in wire for k in ("intended","intention","meaning","lexicon","capacity")):
                    raise ValueError("public envelope leaks private semantics")
                if (wire["speaker"],wire["receiver"],wire["ref"],wire["act"])!=(d["actor"],d["receiver"],v.ref,d["act"]):
                    raise ValueError("message envelope mismatch")
                if wire["act"] in ("demonstration","counterexample"):
                    run=records[wire["run"]]
                    if run["actor"]!=d["actor"] or run["events"]!=wire["events"] or (run["status"]=="succeeded")!=(wire["act"]=="demonstration"):
                        raise ValueError("demonstration is not its observed actual run")
                counts["messages"]+=1
                counts["questions"]+=int(wire["act"]=="clarification")
            elif kind=="interpretation":
                if d["message"] not in read.get(d["actor"],set()):raise ValueError("unread message interpretation")
                message=records[d["message"]];wire=dict(codec.loads(message["payload"]))
                if wire["receiver"]!=d["actor"] or wire["speaker"]!=d["speaker"]:raise ValueError("foreign interpretation")
                if d["status"]=="understood" and d["act"] not in ("counterexample","clarification","answer"):
                    meanings={records[r]["term"]:records[r] for r in d["lexical_versions"]}
                    if any(x["actor"]!=d["actor"] or x["partner"]!=d["speaker"] or x["context"]!=d["context"] for x in meanings.values()):
                        raise ValueError("imported speaker dictionary")
                    if _resolve(wire["body"],meanings)!=d["meaning"]:raise ValueError("interpretation differs from own grounded vocabulary")
                counts["interpretations"]+=1
            elif kind=="lexeme":
                counts["lexical_versions"]+=1
                if d["capacity"]:
                    capacity=records[d["capacity"]]
                    if capacity["actor"]!=d["actor"] or capacity["kind"]!="capacity":raise ValueError("coin without owned retained practice")
                    if _inline(capacity["program"],records)!=d["program"]:raise ValueError("coined word differs from retained procedure")
                    runs=[records[r] for r in d["practices"]]
                    if len({dict(r["slots"])["target"].identity for r in runs if r["status"]=="succeeded" and r["actor"]==d["actor"]})<2:
                        raise ValueError("coin stability not demonstrated")
                else:
                    examples=[dict(e) for e in d["examples"]]
                    seen=set();groups={}
                    for e in examples:
                        if set(e["events"]) & seen:raise ValueError("duplicated lexical evidence")
                        seen.update(e["events"])
                        for event in e["events"]:
                            ed=attrs(versions[event])
                            # Own challenge uses the participant's paid native observations.
                            owned=ed["actor"]==d["actor"] and any(attrs(versions[o]).get("event")==event for o in read.get(d["actor"],set()))
                            if event not in read.get(d["actor"],set()) and not owned:raise ValueError("unread lexical demonstration")
                        if e["success"]:groups.setdefault(e["program"],set()).add(e["target"])
                    if d["status"]=="stable":
                        if not groups or any(len(g)<2 for g in groups.values()):raise ValueError("premature stable vocabulary")
                        if len(groups)>1 and not d["split"]:raise ValueError("conflict silently overwritten")
                        for e in examples:
                            state={s:dict(fs) for s,fs in e["initial"]}
                            agrees=_trace(d["program"],state)==_trace(e["program"],state)
                            if agrees!=e["success"]:raise ValueError("stable meaning contradicts its received examples")
                        counts["stable_learned_versions"]+=1
                        if d["split"]:counts["meaning_repairs"]+=1
            elif kind=="candidate":
                interp=records[d["interpretation"]]
                expected=interp["meaning"][2] if interp["meaning"][0]=="because" else interp["meaning"]
                if (job["purpose"]!="respond" or interp["actor"]!=d["actor"] or interp["status"]!="understood"
                        or interp["act"]!="request" or d["program"]!=expected or d["goal"]!=interp["goal"]
                        or not set(d["dependencies"])<=acquired.get(d["actor"],set())):
                    raise ValueError("practical hypothesis bypassed understood request or own acquisition")
                if d["status"]!="hypothesis":raise ValueError("speech granted mastered skill")
                extensions[v.ref]=d
            elif kind=="demand":extensions[v.ref]=d
            elif kind=="response":
                counts["practical_responses"]+=int(d["status"]=="planned")
                counts["refusals"]+=int(d["status"] in ("refused","deferred"))
            elif kind=="commitment":
                if Role.COMMITMENT not in v.roles or v.facet(Relation).predicate!="promised_procedure":raise ValueError("promise lacks common relation")
                if v.previous is None:
                    if job["purpose"]!="send" or d["status"]!="open":raise ValueError("request fabricated consent")
                    counts["explicit_commitments"]+=1
                else:
                    run=records[d["practice"]]
                    promise=records[v.previous]
                    if (job["purpose"]!="settle" or d["status"]!="fulfilled" or run["status"]!="succeeded"
                            or run["actor"]!=d["actor"] or d["observations"]!=run["observations"]
                            or run["goal"]!=promise["goal"] or _inline(records[run["program"]]["program"],records)!=promise["program"]
                            or tuple((s,r.identity) for s,r in run["slots"])!=tuple((s,r.identity) for s,r in promise["slots"])
                            or any(o not in read.get(d["actor"],set()) for o in d["observations"])):
                        raise ValueError("promise fulfilled without actual observed work")
                    counts["fulfilled_commitments"]+=1
            records[v.ref]=d
        # The extension also tracks earlier U9 records in chronological order.
        for v in tx.versions:
            if v.ref.identity.namespace.startswith("u9.") and "kind" in attrs(v):records[v.ref]=attrs(v)
        versions.update(pending)
    result=audit9(transactions,language_records=extensions)
    result.update(counts)
    return result
