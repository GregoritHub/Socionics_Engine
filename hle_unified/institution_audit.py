"""Independent chronological public-institution audit over raw transactions.

Does not import the institutional runtime, participant policy or its indexes.
The inherited audit checks personal routes, charges, material and constituent work.
"""
from .records import ObjectRef, Account, Governance, Role
from .development_values import attrs
from .operations import indexed
from .collective_audit import audit as audit11, _flatten


def audit(transactions):
    result=audit11(transactions)
    versions,heads,records,read,ballots,assents={},{},{},{},{},{}
    practiced=set()
    counts=dict(institution_operations=0,proposals=0,generated_attribution_proposals=0,
        votes=0,nonacceptances=0,institutions=0,maintained_rules=0,public_revisions=0,
        successions=0,dissolutions=0,public_consequences=0,institutional_practices=0,
        newcomer_understandings=0,institutional_withdrawals=0,disputes=0)
    for tx in transactions:
        pending={v.ref:v for v in tx.versions}
        rows={v.ref:attrs(v) for v in tx.versions if v.ref.identity.namespace.startswith(("u11.","u12.")) and "kind" in attrs(v)}
        for value in tx.versions:
            job=attrs(value)
            if job.get("record_type")!="operation" or job["status"]!="succeeded":continue
            if job["primitive"]=="read":
                receipt=next(v for v in tx.versions if v.ref.identity.namespace=="u4.receipt")
                read.setdefault(job["actor"],set()).add(attrs(receipt)["input.0"])
            if job.get("u12"):counts["institution_operations"]+=1
        for ref,d in rows.items():
            if not ref.identity.namespace.startswith("u12."):
                if d["kind"]=="group" and pending[ref].previous:
                    job=attrs(versions[d["operation"]])
                    if job.get("u12") and job["purpose"]=="ratify":
                        rules=[x for x in rows.values() if x["kind"]=="institution" and x["group"]==ref]
                        if len(rules)!=1 or rules[0]["steward"]!=d["owner"]:
                            raise ValueError("authority changed without an enacted public institution")
                if d["kind"]=="run" and "institution" in d and pending[ref].previous is None:
                    rule=records[d["institution"]]
                    assent=records[assents[rule["ref"].identity,d["owner"]]]
                    if rule["status"]=="dissolved" or not assent["permission_active"] or assent["institution"]!=rule["ref"]:
                        raise ValueError("institutional run lacks exact voluntary assent")
                    if not {rule["ref"],assent["ref"]}<=set(d["dependencies"]):raise ValueError("run omitted rule or consent dependency")
                    if d["agenda"]!=_flatten(d["program"],d["group"].identity,heads,records):raise ValueError("institutional run changed generated decomposition")
                    if rule["gate"]=="approval" and d["owner"]!=rule["steward"]:
                        permission=records.get(d["permission"])
                        if not permission or permission["status"]!="permitted" or permission["institution"]!=rule["ref"] or permission["owner"]!=d["owner"]:
                            raise ValueError("public authority bypassed")
                continue
            v=pending[ref]
            job=attrs(versions[d["operation"]])
            terminal=next((attrs(x) for x in tx.versions if x.previous==d["operation"]),{})
            if not job.get("u12") or job["status"]!="ready" or terminal.get("status")!="succeeded" or job["actor"]!=d["actor"]:
                raise ValueError("institutional output lacks paid actor operation")
            if not set(d["sources"])<=read.get(d["actor"],set()):raise ValueError("institution used unread or foreign evidence")
            kind,purpose=d["kind"],job["purpose"]
            if kind=="proposal":
                if v.previous:
                    prior=records[v.previous]
                    if purpose!="ratify" or d["status"]!="enacted" or any(d[k]!=prior[k] for k in ("goal","gate","electorate","prototype","effect")):
                        raise ValueError("public proposal terms silently changed")
                    continue
                if purpose not in ("propose","counter") or d["group"]!=heads[d["group"].identity].ref:
                    raise ValueError("proposal has stale electorate")
                group=records[d["group"]]
                if tuple(sorted(group["members"]))!=d["electorate"] or len(d["electorate"])<2:
                    raise ValueError("proposal electorate omitted a participant")
                enc=attrs(versions[d["origin_encounter"]])
                if d["origin_encounter"] not in read[d["actor"]] or enc["actor"]!=d["actor"] or enc["target"].identity!=d["target"]:
                    raise ValueError("proposal attributed to foreign or unread encounter")
                if d["effect"] in ("establish","review") and d["gate"]!=("approval" if enc["approval"] else "self_check"):
                    raise ValueError("proposed authority does not follow participant interpretation")
                if d["patterns"]!=indexed(enc,"pattern."):
                    raise ValueError("public proposal has invented attribution provenance")
                for pat in d["patterns"]:
                    pattern=attrs(versions[pat])
                    if pattern["owner"]!=d["actor"] or pattern["origin"] not in d["origin_materials"]:
                        raise ValueError("lost personal material/carrier chain")
                if d["patterns"] and all(attrs(versions[x])["origin_mode"]=="generated" for x in d["patterns"]):counts["generated_attribution_proposals"]+=1
                counts["proposals"]+=1
            elif kind=="vote":
                p=records[d["proposal"]]
                if v.previous:
                    prior=records[v.previous]
                    if (purpose!="withdraw_vote" or d["actor"]!=prior["owner"] or d["proposal"]!=prior["proposal"]
                            or d["choice"]!="withdrawn" or d["permission_active"]):
                        raise ValueError("proposal consent withdrawn by another actor or silently rewritten")
                    ballots[p["ref"],d["owner"]]=ref
                    continue
                if purpose!="respond" or d["proposal"] not in read[d["actor"]] or d["owner"]!=d["actor"] or d["owner"] not in p["electorate"]:
                    raise ValueError("vote is not participant-owned received consideration")
                if (p["ref"],d["owner"]) in ballots or d["permission_active"]!=(d["choice"]=="accept"):
                    raise ValueError("duplicate or inconsistent consent")
                enc=attrs(versions[d["origin_encounter"]])
                if enc["actor"]!=d["owner"] or d["origin_encounter"] not in read[d["owner"]]:raise ValueError("foreign response evidence")
                unsafe=not enc.get("known.safe") or not enc.get("known.available") or (enc.get("known.requires_partner") and not enc.get("known.willing"))
                if unsafe and d["choice"]!="refuse":raise ValueError("legitimate boundary overwritten")
                if not unsafe and enc["approval"] and p["gate"]=="self_check" and p["effect"] not in ("dissolve","succession") and d["choice"]!="negotiate":
                    raise ValueError("independent participant disagreement suppressed")
                ballots[p["ref"],d["owner"]]=ref
                counts["votes"]+=1;counts["nonacceptances"]+=int(d["choice"]!="accept")
            elif kind=="institution":
                p=records[d["proposal"]];group=records[p["group"]]
                electorate=tuple(sorted(group["members"]))
                expected=tuple(ballots.get((p["ref"],a)) for a in electorate)
                if purpose!="ratify" or p["status"]!="offered" or heads[p["group"].identity].ref!=p["group"] or p["electorate"]!=electorate:
                    raise ValueError("rule enacted against stale public terms or membership")
                if d["votes"]!=expected or any(x is None or records[x]["choice"]!="accept" for x in expected):
                    raise ValueError("rule lacks exact unanimous participant consent")
                if not set(expected)<=read[d["actor"]]:raise ValueError("ratifier did not process participant responses")
                if any(d[k]!=p[k] for k in ("gate","goal","prototype","symbolic")):raise ValueError("enactment changed consented terms")
                newgroup=rows[d["group"]]
                successor=p["successor"] if p["effect"]=="succession" else group["owner"]
                if d["steward"]!=successor or newgroup["owner"]!=successor or newgroup["members"]!=group["members"]:
                    raise ValueError("public authority changed without consented succession")
                governance=pending[d["group"]].facet(Governance)
                if governance.rules!=(() if d["status"]=="dissolved" else (d["ref"],)):
                    raise ValueError("group public rules differ from enacted institution")
                status="trial" if p["effect"]=="establish" else "active" if p["effect"]=="maintain" else "dissolved" if p["effect"]=="dissolve" else records[p["institution"]]["status"]
                if d["status"]!=status:raise ValueError("unearned public maintenance or dissolution")
                if p["effect"]=="maintain":
                    practices=[records[x] for x in p["practices"]]
                    if len({x["run"].identity for x in practices})<2 or any(x["institution"]!=p["institution"] for x in practices):
                        raise ValueError("public rule without repeated actual practice")
                    counts["maintained_rules"]+=1
                counts["institutions"]+=int(v.previous is None)
                counts["public_revisions"]+=int(p["effect"]=="review")
                counts["successions"]+=int(p["effect"]=="succession")
                counts["dissolutions"]+=int(p["effect"]=="dissolve")
            elif kind=="assent":
                if v.previous:
                    old=records[v.previous]
                    if d["owner"]!=old["owner"] or d["institution"]!=old["institution"] or d["permission_active"]:
                        raise ValueError("withdrawal rewrote a commitment")
                    if purpose=="withdraw_assent" and (d["actor"]!=d["owner"] or d["status"]!=old["status"]):
                        raise ValueError("withdrawal erased another person's duty")
                    counts["institutional_withdrawals"]+=int(purpose=="withdraw_assent")
                else:
                    basis=records[d["basis"]]
                    if basis["owner"]!=d["owner"]:raise ValueError("assent assigned without that person's act")
                    if purpose=="ratify":
                        rule=rows[d["institution"]]
                        if basis["kind"]!="vote" or basis["choice"]!="accept" or basis["proposal"]!=rule["proposal"]:
                            raise ValueError("rule commitment has no matching consent")
                    elif purpose=="assent":
                        if basis["kind"]!="understanding" or basis["institution"]!=d["institution"] or d["actor"]!=d["owner"]:
                            raise ValueError("newcomer assent has no received understanding")
                    else:raise ValueError("unsourced institutional commitment")
                assents[d["institution"].identity,d["owner"]]=ref
            elif kind=="consequence":
                rule=records[d["institution"]]
                if purpose!="apply" or d["bearer"]!=d["actor"] or d["rule_cause"]!=rule["proposal"] or d["spent"]!=job["spent"]:
                    raise ValueError("consequence lost actor, cost or public cause")
                if d["outcome"]=="approval_wait" and (rule["gate"]!="approval" or d["actor"]==rule["steward"]):raise ValueError("invented authority burden")
                counts["public_consequences"]+=1
            elif kind=="practice":
                run=records[d["run"]]
                if purpose!="record" or run["status"]!="succeeded" or run["institution"]!=d["institution"] or d["events"]!=run["events"] or run["ref"].identity in practiced:
                    raise ValueError("fabricated or duplicate institutional practice")
                observed={attrs(versions[x]).get("event") for x in read[d["actor"]]}
                if not set(d["events"])<=observed:raise ValueError("practice lacks independently received work")
                practiced.add(run["ref"].identity);counts["institutional_practices"]+=1
            elif kind=="teaching":
                rule=records[d["institution"]]
                if any(d[k]!=rule[k] for k in ("gate","goal","steward")):raise ValueError("teacher transmitted different public terms")
            elif kind=="understanding":
                lesson=records[d["lesson"]]
                if lesson["receiver"]!=d["owner"] or d["lesson"] not in read[d["owner"]] or any(d[k]!=lesson[k] for k in ("gate","goal","steward")):
                    raise ValueError("newcomer gained unprocessed institutional understanding")
                counts["newcomer_understandings"]+=1
            elif kind=="dispute":
                consequence=records[d["consequence"]]
                if v.previous:
                    old=records[v.previous];rule=rows.get(d.get("resolution"))
                    if purpose!="ratify" or not rule or d["bearer"]!=old["bearer"] or d["consequence"]!=old["consequence"] or d["status"]!="resolved":
                        raise ValueError("dispute closed without public change and preserved consequence")
                else:
                    if consequence["bearer"]!=d["actor"] or d["consequence"] not in read[d["actor"]]:raise ValueError("dispute erases or substitutes consequence bearer")
                    counts["disputes"]+=1
            elif kind=="application" and v.previous:
                old=records[v.previous]
                if any(d[k]!=old[k] for k in ("owner","target","institution")):raise ValueError("authorization changed beneficiary or terms")
                rule=records[d["institution"]]
                if purpose=="permit" and (old["status"]!="waiting" or d["status"]!="permitted" or d["actor"]!=rule["steward"]):raise ValueError("unauthorized public permission")
                if purpose=="apply" and (old["status"]!="permitted" or d["status"]!="consumed"):raise ValueError("reused public permission")
        for v in tx.versions:versions[v.ref]=v;heads[v.ref.identity]=v
        records.update(rows)
    result.update(counts)
    return result
