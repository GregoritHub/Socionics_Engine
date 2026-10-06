"""Independent declarative C7 workflow oracle. No runtime content imports.

Reconstructs task constraints from records and checks the deterministic serial
schedule. Shares only the immutable specification and generic content codec.
"""
from .crossing_audit import encode, decode
from .records import ObjectId

def check_authored(x):
    if set(x)!={"kind","tasks","consent","hypothetical"} or x["kind"] not in ("intention","stance") or any(type(x[k]) is not bool for k in ("consent","hypothetical")):
        raise ValueError("invalid authored workflow")
    tasks=x["tasks"]
    if type(tasks) is not tuple or not 1<=len(tasks)<=8 or len({t[0] for t in tasks})!=len(tasks): raise ValueError("invalid task identities")
    for t in tasks:
        if (type(t) is not tuple or len(t)!=6 or type(t[0]) is not str or not t[0] or t[1] not in ("care","use","inspect","transfer","return")
            or type(t[2]) is not tuple or len(set(t[2]))!=len(t[2]) or len(t[2])>8 or any(type(p) is not str or not p for p in t[2])
            or type(t[3]) is not int or type(t[4]) is not int or not 0<=t[3]<=t[4]<=1000 or type(t[5]) is not ObjectId):
            raise ValueError("invalid task contract")

def schedule(contents):
    all_rows=[t for value in contents for t in value["tasks"]]
    keys=sorted({t[0] for t in all_rows}); rows=[]; conflict=[key for value in contents for key in value.get("conflicts",())]
    if len(keys)>8: raise ValueError("task budget exceeded")
    for k in keys:
        matches=[t for t in all_rows if t[0]==k]; first=matches[0]
        lo=max(t[3] for t in matches); hi=min(t[4] for t in matches)
        conflict.extend([k] if lo>hi or len({(t[1],t[2],t[5]) for t in matches})!=1 else [])
        rows.append((k,first[1],first[2],lo,hi,first[5]))
    missing=sorted({p for t in rows for p in t[2]}-set(keys))
    chosen=[]; slots=[]; late=[]
    # Candidate constraints expressed against already allocated serial slots.
    for _ in keys:
        completed={k:at+1 for k,at in slots};end=max(completed.values(),default=0)
        ready=[(max(end,t[3],max((completed[p] for p in t[2]),default=0)),t[0],t) for t in rows
            if t[0] not in completed and set(t[2])<=set(completed)]
        if not ready: break
        at,k,t=min(ready,key=lambda z:(z[0],z[1]));chosen.append(k);slots.append((k,at))
        if at>t[4]:late.append(k)
    blocked=tuple(k for k in keys if k not in chosen)
    return dict(tasks=tuple(rows),conflicts=tuple(sorted(set(conflict))),missing=tuple(missing),blocked=blocked,late=tuple(late),
        order=tuple(chosen),slots=tuple(slots),feasible=bool(rows) and not(conflict or missing or blocked or late))

def answer(model,done,clock):
    choices=[t for t in model["tasks"] if t[0] not in done and all(p in done for p in t[2]) and t[3]<=clock<=t[4]] if model.get("feasible") else []
    return sorted(choices,key=lambda t:(t[4],t[0]))[0] if choices else None

def observed_tasks(items):
    actual=sorted((d for d in items if d["outcome"]=="succeeded"),key=lambda v:v["workflow_tick"])
    return tuple((d["primitive"]+"-"+str(i),d["primitive"],() if i==0 else (actual[i-1]["primitive"]+"-"+str(i-1),),0,8,d["actor"]) for i,d in enumerate(actual))

def response_tasks(d):
    if d["outcome"]!="succeeded":return ()
    if not {"condition","wear","custodian"}<=set(d) or type(d["wear"]) is not int or d["wear"]<0:raise ValueError("missing observed maintenance state")
    who=d["custodian"]
    if d["condition"]=="damaged":return (("check","inspect",(),0,8,who),)
    if d["condition"]!="serviceable":raise ValueError("unknown equipment state")
    return (("work","use",(),0,4,who),) if d["wear"]==0 else (("maintain","care",(),0,2,who),("work","use",("maintain",),1,4,who))

def expected(d,items,recipe):
    a=recipe.action;x=items[0];refs=tuple(d["source."+str(i)] for i in range(len(items)));actor=d["actor"]
    inward=d["polarity"]=="accumulation";common=dict(target=d["content_target"],context=d["context"],source=refs[0],competence=False)
    if a=="offer":
        return dict(common,kind="offer",tasks=response_tasks(x) if x["kind"]=="activity" else x["tasks"],stance=refs[1],
            consent=items[1]["consent"],speaker=actor,receiver=d["peer"],group=d["group"],completed=decode(d["query_completed"])["done"],clock=d["query_clock"],
            hypothetical=x.get("hypothetical",False),prior_kind=x["kind"],
            **({"conflicts":x["conflicts"]} if x.get("conflicts") else {}))
    if a=="reply":
        picked=answer(schedule((x,)),x["completed"],x["clock"])
        return dict(common,kind="reply",tasks=items[1]["tasks"],offer=refs[0],speaker=actor,receiver=d["peer"],group=d["group"],understood=x["tasks"],
            answer=picked[0] if picked else None,consent=items[1]["consent"],stance=refs[1],difference=items[1]["tasks"]!=x["tasks"])
    if a=="vote":
        return dict(common,kind="vote",tasks=x["tasks"],draft=refs[0],speaker=actor,group=d["group"],assent=items[1]["consent"] and schedule((x,items[1]))["feasible"])
    if a in ("share","coordinate","educate","commune"):
        offer,reply=items[1:]; merged=schedule((offer,reply));picked=answer(schedule((offer,)),offer["completed"],offer["clock"])
        understood=reply["understood"]==offer["tasks"] and reply["answer"]==(picked[0] if picked else None)
        return dict(common,**merged,kind="shared",participants=(actor,d["peer"]),group=d["group"],exchange=refs[1:],
            assents=(offer["consent"],reply["consent"]),understood=understood,answer=reply["answer"],difference=reply["difference"],teaching=a=="educate",
            status="examined" if inward else "renewed" if a=="commune" else "contribution",authorized=bool(not inward and understood and merged["feasible"] and offer["consent"] and reply["consent"]),hypothetical=offer["hypothetical"])
    if a=="contemplate":
        merged=schedule(items);hyp=any(v["hypothetical"] for v in items)
        return dict(common,**merged,kind="personal",status="differentiated" if inward else "rehearsed",hypothetical=hyp,consent=all(v["consent"] for v in items),
            attention="clarify" if not merged["feasible"] else "test" if hyp else "schedule",authorized=False)
    if a in ("theorize","organize","integrate"):
        merged=schedule((dict(tasks=observed_tasks(items)),) if a=="organize" else items)
        return dict(common,**merged,kind="system",status=("dependency_hypothesis" if a=="organize" else "reconciled" if a=="integrate" else "hypothesis") if inward else ("coupled" if a=="integrate" else "operating" if a=="organize" else "submitted"),
            assumptions=("one shared equipment timeline","unit task slots","observed order is not universal necessity"),test="execute a ready task and compare the actual event",uncertain=True,
            authority=actor if not inward and a in ("organize","integrate") else None,authorized=bool(not inward and a in ("organize","integrate") and merged["feasible"]),hypothetical=a!="organize",samples=refs)
    if a in ("embody","identify","understand"):
        source=dict(tasks=response_tasks(x)) if a=="embody" else x;own=items[1] if len(items)>1 else None
        merged=schedule((source,own) if own else (source,));assent=True if own is None else own["consent"]
        return dict(common,**merged,kind="personal",status="interpretation" if inward else "decision_policy",basis=x["kind"],consent=assent,
            authorized=bool(not inward and assent and merged["feasible"]),hypothetical=x.get("hypothetical",False),attention="schedule" if merged["feasible"] and assent else "clarify")
    if a=="institutionalize":
        if inward:
            return dict(common,**schedule((x,)),kind="rule",status="draft",group=d["group"],participants=x["participants"],practice=refs[1:],votes=(),
                responsibilities=tuple((t[0],t[5],t[3],t[4]) for t in x["tasks"]),authorized=False,authority="two exact current votes",hypothetical=False)
        assent=all(v["assent"] for v in items[1:])
        return dict(x,source=refs[0],status="ratified" if assent else "declined",votes=refs[1:],authorized=assent and x["feasible"])
    if a in ("express","apply","mobilize","act"):
        return dict(common,kind="command",tasks=observed_tasks((x,)) if x["kind"]=="activity" else x["tasks"],
            primitive=("return" if inward else "transfer") if a=="act" else "inspect" if inward else "care",
            stock=d["requested_stock"],relation=d["requested_relation"],peer=d["peer"],mode="readiness" if inward and a!="apply" else "trial" if inward else "performance",permitted=d["permitted"])
    if a=="use":
        source=dict(tasks=response_tasks(x)) if x["kind"]=="activity" else x;model=source if "feasible" in source else schedule((source,))
        done=decode(d["query_completed"])["done"];clock=d["query_clock"];picked=answer(model,done,clock)
        return dict(common,kind="decision",tasks=source["tasks"],completed=done,clock=clock,next_task=picked[0] if picked else None,next_action=picked[1] if picked else None,
            responsible=picked[5] if picked else None,feasible=model.get("feasible",False),authorized=bool(x.get("authorized",False) and picked is not None and picked[5]==actor),
            status="prediction" if x.get("status") not in ("ratified","coupled","decision_policy","operating") else "governed_choice")
    raise ValueError("unknown workflow recipe")
