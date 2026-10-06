"""Offline U9 raw witness auditor, independent of participant search/policies.

The inherited auditor reconstructs all physical effects and resource debits.
This module checks paid constructive provenance, actor acquisition, executable
step decomposition, observed successes, counterexample lineage and revision.
Exact disclosure-selector validation is supplied separately by full replay.
"""
from .records import Account, Occurrence, Procedure, Material, Relation
from .development_values import attrs
from .operation_audit import audit_transactions
from .cognitive_audit import audit_extent


def _state(value): return {k:dict(v) for k,v in value}


def _test(t, s):
    def get(x): return s[x[1]][x[2]] if type(x) is tuple and x[0] == "field" else x
    op,a,b=t[0],get(t[1]),get(t[2])
    if op=="eq": return type(a) is type(b) and a==b
    if op=="ne": return type(a) is not type(b) or a!=b
    if type(a) is not int or type(b) is not int: raise ValueError("noninteger ordered condition")
    if op=="ge":return a>=b
    if op=="gt":return a>b
    if op=="le":return a<=b
    if op=="lt":return a<b
    raise ValueError("unrecognized relational condition")


def _trace(program, state, records, active=()):
    tag=program[0]
    if tag=="act":return (program[1],)
    if tag=="call":
        ref=program[1]
        if ref in active or ref not in records:raise ValueError("invalid call dependency")
        cap=records[ref]
        if not all(_test(t,state) for t in cap["guard"]):raise ValueError("inapplicable call")
        return _trace(cap["program"],state,records,(*active,ref))
    if tag=="if":return _trace(program[2] if _test(program[1],state) else program[3],state,records,active)
    if tag=="choice":
        for child in program[1]:
            try:return _trace(child,state,records,active)
            except ValueError:pass
        raise ValueError("no applicable alternative")
    if tag!="seq":raise ValueError("unknown program constructor")
    return tuple(a for child in program[1] for a in _trace(child,state,records,active))


def _size(p):
    if p[0] in ("act","call"):return 1
    if p[0]=="if":return 2+_size(p[2])+_size(p[3])
    return 1+sum(_size(c) for c in p[1])


def _next(pending,state,records):
    queue=list(pending)
    while queue:
        p=queue.pop(0);kind=p[0]
        if kind=="act":return p[1],tuple(queue)
        if kind=="seq":queue[:0]=p[1]
        elif kind=="call":
            cap=records[p[1]]
            if not all(_test(t,state) for t in cap["guard"]):raise ValueError("inapplicable call")
            queue.insert(0,cap["program"])
        elif kind=="if":queue.insert(0,p[2] if _test(p[1],state) else p[3])
        elif kind=="choice":
            for child in p[1]:
                try:
                    name,rest=_next((child,),state,records)
                    return name,(*rest,*queue)
                except ValueError:continue
            raise ValueError("no applicable alternative")
        else:raise ValueError("unknown constructor")
    raise ValueError("no step")


def _all_actions(program,records,seen=()):
    if program[0]=="act":return (program[1],)
    if program[0]=="call":
        ref=program[1]
        if ref in seen:raise ValueError("cyclic call")
        return _all_actions(records[ref]["program"],records,(*seen,ref))
    children=program[1] if program[0] in ("seq","choice") else program[2:]
    return tuple(a for c in children for a in _all_actions(c,records,seen))


def _check_observed_state(state,versions):
    for slot,fields in state:
        if slot=="progress":continue
        row=dict(fields);v=versions[row["ref"]];m=v.facet(Material)
        if m:
            expected={k:getattr(m,k) for k in ("owner","custodian","condition","quantity")}
            expected.update(attrs(v))
            if m.condition=="stock":expected["available"]=m.quantity-expected["consumed"]
        else:
            r=v.facet(Relation)
            expected={"predicate":r.predicate,**{e.role:e.target.identity for e in r.endpoints},**{a.name:a.value for a in r.terms}}
        if any(row.get(k)!=value for k,value in expected.items()):
            raise ValueError("run state differs from its referenced material/relational evidence")


def _extent(d):
    audit_extent(d)
    if not d.get("u9"):return
    expected=max(1,d["evidence_count"]+d["field_count"]+d["repertoire_units"]+
        (d["limit"]*(d["field_count"]+d["fuel"]+d["primitive_count"]) if d["purpose"]=="search" else d["fuel"]))
    if d["fuel"]!=d["limit"]*d["depth"]*4 or d["recall_units"]!=expected:
        raise ValueError("unpaid constructive ticket extent")


def audit(transactions, *, language_records=None):
    result=audit_transactions(transactions,extent_check=_extent)
    versions,records,read,acquired,used,observed={},{},{},{},{},set()
    counts=dict(constructive_commits=0,search_tickets=0,candidates=0,retained_procedures=0,
                conditional_revisions=0,physical_steps=0,successful_runs=0,failed_runs=0,
                consequence_demands=0,generalization_demands=0,interrupted_demands=0,constructive_surfaces=0)
    for tx in transactions:
        pending={v.ref:v for v in tx.versions}
        for v in tx.versions:
            d=attrs(v)
            if d.get("record_type")!="operation" or d.get("status")!="succeeded":continue
            actor=d["actor"]
            if d["primitive"]=="read":
                rec=next(x for x in tx.versions if x.ref.identity.namespace=="u4.receipt")
                read.setdefault(actor,set()).add(attrs(rec)["input.0"])
            if d["primitive"]=="acquire":acquired.setdefault(actor,set()).add((d["procedure"],d["context"]))
            if d.get("u9_plan"):
                plan=records[d["u9_plan"]]
                if plan["actor"]!=actor or (plan["procedure"],d["context"]) not in acquired.get(actor,set()):
                    raise ValueError("constructed step bypassed owned acquisition")
                proc=versions[plan["procedure"]].facet(Procedure)
                if proc.executor!="u4."+d["primitive"]+".v1" or d["primitive"]!=plan["primitive"]:
                    raise ValueError("physical step differs from selected procedure")
                if d["u9_plan"] in used:raise ValueError("selected action executed twice")
                used[d["u9_plan"]]=d["result"]
                counts["physical_steps"]+=1
            if d.get("u9"):
                counts["constructive_commits"]+=1
                bind=pending[d["binding"]]
                if bind.facet(Account).holder!=actor or not set(bind.facet(Account).sources)<=read.get(actor,set()):
                    raise ValueError("constructive content has unowned source evidence")
        # Include failed attempts in the exact step-to-event relation.
        for v in tx.versions:
            d=attrs(v)
            if d.get("record_type")=="operation" and d.get("status") in ("failed","cancelled") and d.get("u9_plan"):
                if d["u9_plan"] in used:raise ValueError("selected action attempted twice")
                used[d["u9_plan"]]=d["result"]
        for v in tx.versions:
            ns,d=v.ref.identity.namespace,attrs(v)
            if language_records and v.ref in language_records:
                if d != language_records[v.ref]: raise ValueError("language extension record mismatch")
                records[v.ref] = d
            if ns=="u9.surface":
                if d["operation"] not in versions or attrs(versions[d["operation"]])["status"]!="ready":
                    raise ValueError("unpaid perspective surface")
                counts["constructive_surfaces"]+=1
                continue
            if not ns.startswith("u9.") or "kind" not in d:continue
            job=attrs(versions[d["operation"]])
            terminal=next((attrs(x) for x in tx.versions if x.previous==d["operation"]),None)
            if (not job.get("u9") or job["status"]!="ready" or not terminal or terminal["status"]!="succeeded"
                    or d["actor"]!=job["actor"] or d["binding"]!=terminal["binding"]):
                raise ValueError("unpaid or foreign constructive output")
            kind=d["kind"]
            if kind=="search":
                if job["purpose"]!="search" or d["attempts"]>job["limit"] or d["depth"]!=job["depth"]:
                    raise ValueError("search coverage exceeds paid ticket")
                if v.previous and (d["considered"]-records[v.previous]["considered"]!=d["attempts"] or d["depth"]<records[v.previous]["depth"]):
                    raise ValueError("erased or forged unfinished search")
                if any((p,d["context"]) not in acquired.get(d["actor"],set()) for _,p in d["primitive_dependencies"]):
                    raise ValueError("search invented unacquired operations")
                counts["search_tickets"]+=1
            elif kind=="candidate":
                search=records[d["search"]]
                if job["purpose"]!="search" or search["status"]!="candidate" or d["goal"]!=search["goal"]:
                    raise ValueError("candidate has no paid search")
                trace=_all_actions(d["program"],records)
                if not trace or any(n not in dict(search["primitive_dependencies"]) for n in trace):
                    raise ValueError("candidate supplies unsupported actions")
                if len(d["program"][1])>search["depth"]:raise ValueError("candidate exceeds enumerated depth")
                counts["candidates"]+=1
            elif kind=="plan":
                run=records[d["run"]]
                name,_=_next(run["remaining"],_state(d["state"]),records)
                if job["purpose"]!="select" or d["primitive"]!=name or d["index"]!=run["index"]:
                    raise ValueError("selected action escapes constructed sequence")
            elif kind=="run":
                _check_observed_state(d["state"],{**versions,**pending})
                if v.previous is None:
                    program=records[d["program"]]
                    if d["trace"] or d["index"]!=0 or d["remaining"]!=(program["program"],):
                        raise ValueError("run is not its procedure decomposition")
                elif job["purpose"]=="select":
                    before=records[v.previous]
                    name,remaining=_next(before["remaining"],_state(d["state"]),records)
                    if d["trace"]!=(*before["trace"],name) or d["remaining"]!=remaining:
                        raise ValueError("lost or forged procedure continuation")
                elif job["purpose"]=="observe":
                    before=records[v.previous];event=d["events"][-1];observation=d["observations"][-1]
                    ed=attrs(versions[event]);od=attrs(versions[observation])
                    if (event in observed or observation not in read.get(d["actor"],set())
                            or used.get(before["selected"])!=event or od["event"]!=event
                            or d["events"]!=(*before["events"],event) or d["index"]!=before["index"]+1):
                        raise ValueError("run advanced without fresh observed execution")
                    observed.add(event)
                    expected=_state(before["state"])["progress"]["uses"]+int(ed["outcome"]=="succeeded" and ed["primitive"]=="use")
                    if _state(d["state"])["progress"]["uses"]!=expected:raise ValueError("invented successful use")
                    if d["status"]=="succeeded":
                        if d["remaining"] or d["index"]!=len(d["trace"]) or ed["outcome"]!="succeeded" or not all(_test(t,_state(d["state"])) for t in d["goal"]):
                            raise ValueError("false endpoint success")
                        counts["successful_runs"]+=1
                    if d["status"]=="failed":counts["failed_runs"]+=1
            elif kind=="capacity":
                run=records[d["practice"]];candidate=records[d["candidate"]]
                if (job["purpose"]!="retain" or run["status"]!="succeeded" or candidate["kind"]!="candidate"
                        or run["program"]!=candidate["ref"] or d["observations"]!=run["observations"]
                        or any(o not in read.get(d["actor"],set()) for o in d["observations"])):
                    raise ValueError("retention lacks complete observed actor practice")
                if v.previous:
                    previous=records[v.previous]
                    if (candidate["revises"]!=v.previous or d["previous_capacity"]!=v.previous or d["program"][0]!="if"
                            or not _test(d["split"],_state(candidate["initial"])) or _test(d["split"],_state(previous["example"]))
                            or d["program"][3]!=("call",v.previous)):
                        raise ValueError("revision lost the counterexample or previous procedure")
                    counts["conditional_revisions"]+=1
                counts["retained_procedures"]+=1
            elif kind=="demand" and d.get("origin"):
                origin=records[d["origin"]]
                if origin["status"] not in ("failed","interrupted"):raise ValueError("discrepancy did not arise from observed incomplete work")
                if d["reason"]=="failed_generalization" and origin["failure_kind"]!="observed_counterexample":
                    raise ValueError("cancellation or missing resources mislabeled counterexample")
                counts["generalization_demands" if d["reason"]=="failed_generalization" else "consequence_demands" if d["reason"]=="persistent_consequence" else "interrupted_demands"]+=1
            records[v.ref]=d
        versions.update(pending)
    result.update(counts)
    return result
