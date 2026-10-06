"""Independent chronological U11 audit; no engine state or projection functions.

The inherited auditor checks routes, debits and physical effects. This module
rebuilds membership, scoped inventory, consent, decomposition and retention.
"""
from .records import ObjectRef, ObjectId, Composition, Material, Role, Account, Occurrence
from .development_values import attrs
from .operations import indexed
from .language_audit import audit as audit10


def _tree(heads,root):
    groups,people,materials,seen={},{},{},set()
    pending=[(root,())]
    while pending:
        identity,path=pending.pop()
        if identity in path:raise ValueError("audited membership cycle")
        if identity in seen:continue
        seen.add(identity)
        value=heads[identity];part=value.facet(Composition) if identity.namespace=="u11.group" else None
        if part:
            groups[identity]=value
            for i in part.resources:materials[i]=heads[i]
            pending.extend((i,(*path,identity)) for i in part.members)
        else:
            people[identity]=value
            if value.facet(Material):materials[identity]=value
    return groups,people,materials


def _projection(heads,root,scope):
    groups,people,materials=_tree(heads,root)
    deps={v.ref for v in groups.values()}
    if scope=="membership":
        return (("members",tuple(sorted(people))),("member_count",len(people)),("group_count",len(groups))),deps
    quantities,stocks={},{}
    for value in materials.values():
        m=value.facet(Material)
        if m is None:raise ValueError("nonmaterial resource")
        deps.add(value.ref)
        k=m.owner,m.unit;quantities[k]=quantities.get(k,0)+m.quantity
        if m.condition=="stock":
            d=attrs(value);k=m.owner,m.unit,d["purpose"]
            stocks[k]=stocks.get(k,0)+m.quantity-d["consumed"]
    return (("resource_count",len(materials)),
            ("quantities_by_owner_unit",tuple((*k,n) for k,n in sorted(quantities.items()))),
            ("stock_by_owner_unit_purpose",tuple((*k,n) for k,n in sorted(stocks.items())))),deps


def _flatten(program,scope,heads,records):
    result=[];stack=[(p,scope,()) for p in reversed(program)]
    while stack:
        p,g,seen=stack.pop()
        if p[0]=="work":
            if p[1] not in _tree(heads,g)[1] or Role.PERSON not in heads[p[1]].roles:raise ValueError("nonmember assigned work")
            result.append((g,*p[1:]))
        elif p[0]=="call":
            c=records[p[1]]
            if c["kind"]!="capacity" or p[1] in seen or c["group"].identity not in _tree(heads,g)[0]:
                raise ValueError("unsupported collective call")
            stack.extend((child,c["group"].identity,(*seen,p[1])) for child in reversed(c["program"]))
        else:raise ValueError("unrecognized program constructor")
    return tuple(result)


def audit(transactions):
    result=audit10(transactions)
    heads,versions,records,read,acquired,duties={},{},{},{},{},{}
    attempted=set();retained=set()
    counts=dict(collective_commits=0,groups=0,membership_changes=0,accepted_memberships=0,
        scoped_summaries=0,consents=0,withdrawals=0,constituent_attempts=0,
        observed_constituent_results=0,collective_capacities=0,nested_calls=0)
    for tx in transactions:
        pending={v.ref:v for v in tx.versions}
        out={v.ref:attrs(v) for v in tx.versions if v.ref.identity.namespace.startswith("u11.") and "kind" in attrs(v)}
        for value in tx.versions:
            d=attrs(value)
            if d.get("record_type")!="operation":continue
            actor=d["actor"]
            if d.get("u11"):
                if d["recall_units"]!=1+d["evidence_count"]+d["visit_budget"]+d["syntax_units"]:
                    raise ValueError("unpaid coordination extent")
            if value.previous is None and d.get("collective_selection"):
                sel=records[d["collective_selection"]]
                if sel["ref"] in attempted or actor!=sel["owner"] or d["procedure"]!=sel["procedure"]:
                    raise ValueError("repeated or foreign constituent selection")
                if any(d[k]!=v for k,v in sel["roles"]):raise ValueError("physical inputs differ from resolved selection")
                if not set(sel["dependencies"])<=set(indexed(d,"dependency.")):
                    raise ValueError("constituent omitted collective dependencies")
                if (actor,d["procedure"],d["context"]) not in acquired:raise ValueError("unearned individual skill")
                attempted.add(sel["ref"]);counts["constituent_attempts"]+=1
            if d["status"]!="succeeded":continue
            if d["primitive"]=="read":
                receipt=next(x for x in tx.versions if x.ref.identity.namespace=="u4.receipt")
                read.setdefault(actor,set()).add(attrs(receipt)["input.0"])
            if d["primitive"]=="acquire":acquired[actor,d["procedure"],d["context"]]=d["practice"]
            if d.get("collective_selection"):
                if any(heads[dep.identity].ref!=dep for dep in indexed(d,"dependency.")):
                    raise ValueError("constituent committed stale permission or material")
            if d.get("u11"):
                counts["collective_commits"]+=1
                account=pending[d["binding"]].facet(Account)
                if account.holder!=actor or not set(account.sources)<=read.get(actor,set()):
                    raise ValueError("collective processing used unread or foreign sources")
        for ref,d in out.items():
            v=pending[ref];job=attrs(versions[d["operation"]])
            terminal=next((attrs(x) for x in tx.versions if x.previous==d["operation"]),None)
            if not job.get("u11") or job["status"]!="ready" or not terminal or terminal["status"]!="succeeded" or job["actor"]!=d["actor"]:
                raise ValueError("collective output has no completed actor-owned work")
            if not set(d["sources"])<=read.get(d["actor"],set()):raise ValueError("unread collective evidence")
            purpose=job["purpose"];kind=d["kind"]
            if kind=="group":
                part=v.facet(Composition)
                if part is None or (part.members,part.resources,part.boundary,part.summary_dependencies)!=(d["members"],d["resources"],d["boundary"],d["dependencies"]):
                    raise ValueError("collective facet disagrees with its versioned state")
                if v.previous is None:
                    if purpose!="compose" or d["owner"]!=d["actor"] or d["owner"] not in part.members:
                        raise ValueError("group creation lacks creator's own participation")
                    if any(Role.PERSON in heads[i].roles and i!=d["owner"] for i in part.members):
                        raise ValueError("membership imposed without consent")
                    counts["groups"]+=1
                else:
                    old=records[v.previous];added=set(d["members"])-set(old["members"]);removed=set(old["members"])-set(d["members"])
                    if purpose=="join":
                        invites=[x for x in out.values() if x["kind"]=="invitation"]
                        if added!={d["actor"]} or removed or len(invites)!=1:raise ValueError("join changed unrelated membership")
                        invite=invites[0];prior=records[ObjectRef(invite["ref"].identity,invite["ref"].revision-1)]
                        if prior["status"]!="offered" or prior["receiver"]!=d["actor"] or prior["group"].identity!=ref.identity or invite["status"]!="accepted":
                            raise ValueError("joining did not realize its own invitation")
                        counts["accepted_memberships"]+=1
                    elif purpose=="leave":
                        if removed!={d["actor"]} or added or d["actor"]==d["owner"]:raise ValueError("departure erased another member")
                    elif purpose in ("link","unlink"):
                        if d["actor"]!=old["owner"] or any(Role.PERSON in heads[i].roles for i in added|removed):
                            raise ValueError("link bypassed membership consent")
                    elif purpose=="ratify" and job.get("u12"):
                        # U12's independent auditor checks exact ballots and the
                        # permitted successor. It cannot change membership here.
                        if added or removed or d["resources"]!=old["resources"]:
                            raise ValueError("institutional decision changed membership or resources")
                    else:raise ValueError("membership changed outside membership work")
                    if (d["owner"]!=old["owner"] and not (purpose=="ratify" and job.get("u12"))) or d["boundary"]!=old["boundary"]:raise ValueError("membership silently changed authority")
                    counts["membership_changes"]+=1
                overlay={**heads,**{x.ref.identity:x for x in tx.versions}}
                for identity in part.members:
                    if identity.namespace=="u11.group":
                        child=attrs(overlay[identity])
                        if (child["owner"],child["context"],child["cue"])!=(d["owner"],d["context"],d["cue"]):
                            raise ValueError("nested group crossed authority or context")
                _tree(overlay,ref.identity)
            elif kind=="summary":
                public,deps=_projection(heads,d["group"].identity,d["scope"])
                if purpose!="summarize" or d["public"]!=public or set(d["dependencies"])!=deps or d["root"]!=heads[d["group"].identity].ref:
                    raise ValueError("aggregate summary disagrees with retained constituent detail")
                counts["scoped_summaries"]+=1
            elif kind=="plan" or kind=="run" and purpose=="instantiate":
                if d["agenda"]!=_flatten(d["program"],d["group"].identity,heads,records):
                    raise ValueError("collective schedule differs from declared constituent decomposition")
                counts["nested_calls"]+=sum(p[0]=="call" for p in d["program"])
            elif kind=="commitment":
                if v.previous is None:
                    run=records[d["run"]]
                    expected=tuple(i for i,row in enumerate(run["agenda"]) if row[1]==d["owner"])
                    if purpose!="accept" or d["actor"]!=d["owner"] or d["indices"]!=expected or not expected or d["performed"] or not d["permission_active"] or d["status"]!="open":
                        raise ValueError("consent is not the assigned participant's own acceptance")
                    if any((d["owner"],run["agenda"][i][2],d["context"]) not in acquired for i in expected):
                        raise ValueError("joining granted skill")
                    counts["consents"]+=1
                else:
                    prior=records[v.previous]
                    if any(d[k]!=prior[k] for k in ("owner","run","indices")):raise ValueError("obligation meaning changed")
                    if purpose=="withdraw":
                        if d["actor"]!=d["owner"] or d["permission_active"] or d["performed"]!=prior["performed"] or d["status"]!=prior["status"]:
                            raise ValueError("withdrawal erased a real duty or work")
                        counts["withdrawals"]+=1
                    elif purpose=="observe":
                        run=next(x for x in out.values() if x["kind"]=="run")
                        if d["performed"]!=(*prior["performed"],run["index"]-1) or d["status"]!=("fulfilled" if d["performed"]==d["indices"] else "open"):
                            raise ValueError("duty fulfilled without observed assigned performance")
                    else:raise ValueError("duty changed outside acceptance, observation or withdrawal")
                duties[d["run"].identity,d["owner"]]=ref
            elif kind=="selection":
                runref=ObjectRef(d["run"].identity,d["run"].revision-1);run=records[runref]
                row=run["agenda"][run["index"]]
                if run["status"]!="active" or d["worker"]!=row[1] or d["procedure"]!=row[2] or d["index"]!=run["index"]:
                    raise ValueError("selection is not the assigned next work")
                if (d["worker"],d["procedure"],d["context"]) not in acquired:raise ValueError("selection bypassed personal acquisition")
                for worker in set(x[1] for x in run["agenda"]):
                    duty=records[duties[runref.identity,worker]]
                    if not duty["permission_active"] or duty["ref"] not in d["dependencies"]:
                        raise ValueError("selection omitted an assignee's active consent")
                for role,value in d["roles"]:
                    if role in ("target","tool","stock") and value not in read.get(d["worker"],set()):
                        raise ValueError("selection used an unresolved material detail")
            elif kind=="run" and purpose=="observe":
                prior=records[v.previous];selection=records[prior["selection"]]
                event=versions[d["events"][-1]];eventdata=attrs(event);physical=attrs(versions[eventdata["operation"]])
                if physical.get("collective_selection")!=selection["ref"] or eventdata["actor"]!=d["actor"]:
                    raise ValueError("collective observation used an unrelated physical event")
                observed={attrs(versions[x]).get("event") for x in read.get(d["actor"],set()) if versions[x].occurrence==Occurrence.OBSERVATION}
                success=eventdata["outcome"]=="succeeded";index=prior["index"]+int(success)
                status=("succeeded" if index==len(d["agenda"]) else "active") if success else "failed"
                if event.ref not in observed or d["events"]!=(*prior["events"],event.ref) or d["index"]!=index or d["status"]!=status:
                    raise ValueError("run advanced without matching paid observed work")
                counts["observed_constituent_results"]+=1
            elif kind=="capacity":
                run=records[d["practice"]]
                if purpose!="retain" or run["status"]!="succeeded" or d["practice"] in retained or d["owner"]!=run["group"].identity or d["actor"]!=run["owner"]:
                    raise ValueError("unearned or individually owned collective capacity")
                observed={attrs(versions[x]).get("event") for x in read.get(d["actor"],set()) if versions[x].occurrence==Occurrence.OBSERVATION}
                if any(d[k]!=run[k] for k in ("agenda","program","events")) or not set(d["events"])<=observed or len(d["events"])!=len(d["agenda"]):
                    raise ValueError("capacity lacks completed observed constituent work")
                retained.add(d["practice"]);counts["collective_capacities"]+=1
        for value in tx.versions:
            heads[value.ref.identity]=value;versions[value.ref]=value
        records.update(out)
    result.update(counts)
    return result
