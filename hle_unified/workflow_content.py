"""Participant-visible timed workflow semantics. No store or hidden state.

Task rows: (name, primitive, predecessors, earliest, latest, responsible actor).
Slots are hypothetical local task slots, never simulator ticks or proof of work.
"""
from .self_content import encode, decode
from .records import ObjectId

PRIMITIVES=("inspect","care","use","transfer","return")

def validate_tasks(tasks):
    if type(tasks) is not tuple or not 1<=len(tasks)<=8: raise ValueError("one to eight task rows required")
    ids=[]
    for row in tasks:
        if (type(row) is not tuple or len(row)!=6 or type(row[0]) is not str or not row[0]
            or row[1] not in PRIMITIVES or type(row[2]) is not tuple or len(set(row[2]))!=len(row[2])
            or any(type(v) is not str or not v for v in row[2]) or len(row[2])>8
            or type(row[3]) is not int or type(row[4]) is not int or not 0<=row[3]<=row[4]<=1000
            or type(row[5]) is not ObjectId): raise ValueError("typed task, dependencies, window and responsible actor required")
        ids.append(row[0])
    if len(set(ids))!=len(ids): raise ValueError("duplicate task identity")

def authored(d):
    if set(d)!={"kind","tasks","consent","hypothetical"} or d["kind"] not in ("intention","stance"):
        raise ValueError("only personal intentions/stances may be authored")
    if type(d["consent"]) is not bool or type(d["hypothetical"]) is not bool: raise ValueError("explicit assent and hypothetical status required")
    validate_tasks(d["tasks"])

def reconcile(items):
    by={}; conflicts=[key for item in items for key in item.get("conflicts",())]
    for x in items:
        for row in x["tasks"]: by.setdefault(row[0],[]).append(row)
    if len(by)>8: raise ValueError("combined task budget exceeded")
    rows=[]
    for key, variants in sorted(by.items()):
        first=variants[0]; low=max(v[3] for v in variants); high=min(v[4] for v in variants)
        if any((v[1],v[2],v[5])!=(first[1],first[2],first[5]) for v in variants) or low>high:
            conflicts.append(key)
        rows.append((key,first[1],first[2],low,high,first[5]))
    missing=tuple(sorted({p for row in rows for p in row[2]}-set(by)))
    pending={row[0]:row for row in rows}; order=[]; slots=[]; clock=0; finish={}; late=[]
    while pending:
        ready=[v for v in pending.values() if all(p in finish for p in v[2])]
        if not ready: break
        row=min(ready,key=lambda v:(max(clock,v[3],max((finish[p] for p in v[2]),default=0)),v[0]))
        at=max(clock,row[3],max((finish[p] for p in row[2]),default=0))
        if at>row[4]: late.append(row[0])
        order.append(row[0]);slots.append((row[0],at));finish[row[0]]=at+1;clock=at+1;del pending[row[0]]
    return dict(tasks=tuple(rows),conflicts=tuple(sorted(set(conflicts))),missing=missing,blocked=tuple(sorted(pending)),
        late=tuple(late),order=tuple(order),slots=tuple(slots),feasible=bool(rows) and not(conflicts or missing or pending or late))

def query(model,completed,clock):
    if not model.get("feasible",False): return None
    done=set(completed)
    rows=[v for v in model["tasks"] if v[0] not in done and set(v[2])<=done and v[3]<=clock<=v[4]]
    return min(rows,key=lambda x:(x[4],x[0])) if rows else None

def activity(observations):
    rows=[]; previous=()
    for d in sorted(observations,key=lambda v:v["workflow_tick"]):
        if d["outcome"]!="succeeded": continue
        op=d["primitive"]; key=op+"-"+str(len(rows))
        rows.append((key,op,previous,0,8,d["actor"]));previous=(key,)
    return tuple(rows)

def readiness(observation):
    """A response to an observed outcome, not a repetition of its action label."""
    if observation["outcome"]!="succeeded":return ()
    if not {"condition","wear","custodian"}<=set(observation):raise ValueError("paid condition, wear and custody required")
    actor=observation["custodian"];condition=observation["condition"];wear=observation["wear"]
    if type(wear) is not int or wear<0:raise ValueError("observed physical wear required")
    if condition=="damaged":return (("check","inspect",(),0,8,actor),)
    if condition!="serviceable":raise ValueError("supported equipment condition required")
    if wear:return (("maintain","care",(),0,2,actor),("work","use",("maintain",),1,4,actor))
    return (("work","use",(),0,4,actor),)

def frame(p):
    r=p["request"]; recipe=p["recipe"]; data=p["data"]; x=data[0]; a=recipe.action; inward=recipe.polarity=="accumulation"
    common=dict(target=r.target,context=r.context,source=r.input,competence=False)
    if a=="offer":
        own=data[1]; tasks=x["tasks"] if x["kind"]!="activity" else readiness(x)
        return dict(common,kind="offer",tasks=tasks,stance=r.inputs[1],consent=own["consent"],
            speaker=r.actor,receiver=r.peer,group=r.group,completed=r.completed,clock=r.clock,
            hypothetical=x.get("hypothetical",False),prior_kind=x["kind"],
            **({"conflicts":x["conflicts"]} if x.get("conflicts") else {}))
    if a=="reply":
        own=data[1]; model=reconcile((x,)); answer=query(model,x["completed"],x["clock"])
        return dict(common,kind="reply",tasks=own["tasks"],offer=r.input,speaker=r.actor,receiver=r.peer,group=r.group,
            understood=x["tasks"],answer=None if answer is None else answer[0],consent=own["consent"],stance=r.inputs[1],
            difference=own["tasks"]!=x["tasks"])
    if a=="vote":
        return dict(common,kind="vote",tasks=x["tasks"],draft=r.input,speaker=r.actor,group=r.group,
            assent=data[1]["consent"] and reconcile((x,data[1]))["feasible"])
    if a in ("share","coordinate","educate","commune"):
        offer,reply=data[1:]; base=dict(tasks=offer["tasks"],conflicts=offer.get("conflicts",()))
        merged=reconcile((base,reply)); matched=query(reconcile((base,)),offer["completed"],offer["clock"])
        understood=reply["understood"]==offer["tasks"] and reply["answer"]==(None if matched is None else matched[0])
        return dict(common,**merged,kind="shared",participants=(r.actor,r.peer),group=r.group,
            exchange=r.inputs[1:],assents=(offer["consent"],reply["consent"]),understood=understood,
            answer=reply["answer"],difference=reply["difference"],teaching=a=="educate",
            status="examined" if inward else "renewed" if a=="commune" else "contribution",
            authorized=not inward and understood and merged["feasible"] and offer["consent"] and reply["consent"],
            hypothetical=offer["hypothetical"])
    if a=="contemplate":
        merged=reconcile(data); hypothetical=any(d["hypothetical"] for d in data)
        return dict(common,**merged,kind="personal",status="differentiated" if inward else "rehearsed",
            hypothetical=hypothetical,consent=all(d["consent"] for d in data),
            attention="clarify" if not merged["feasible"] else "test" if hypothetical else "schedule",authorized=False)
    if a in ("theorize","organize","integrate"):
        source=(dict(tasks=activity(data)),) if a=="organize" else data
        merged=reconcile(source)
        return dict(common,**merged,kind="system",status=("dependency_hypothesis" if a=="organize" else "reconciled" if a=="integrate" else "hypothesis") if inward else ("coupled" if a=="integrate" else "operating" if a=="organize" else "submitted"),
            assumptions=("one shared equipment timeline","unit task slots","observed order is not universal necessity"),
            test="execute a ready task and compare the actual event",uncertain=True,
            authority=r.actor if not inward and a in ("organize","integrate") else None,
            authorized=not inward and a in ("organize","integrate") and merged["feasible"],
            hypothetical=a!="organize",samples=r.inputs)
    if a in ("embody","identify","understand"):
        source=dict(tasks=readiness(x)) if a=="embody" else x
        own=data[1] if len(data)>1 else None; merged=reconcile((source,) if own is None else (source,own))
        assent=True if own is None else own["consent"]
        return dict(common,**merged,kind="personal",status="interpretation" if inward else "decision_policy",
            basis=x["kind"],consent=assent,authorized=not inward and assent and merged["feasible"],
            hypothetical=x.get("hypothetical",False),attention="schedule" if merged["feasible"] and assent else "clarify")
    if a=="institutionalize":
        if inward:
            return dict(common,**reconcile((x,)),kind="rule",status="draft",group=r.group,participants=x["participants"],
                practice=r.inputs[1:],votes=(),responsibilities=tuple((v[0],v[5],v[3],v[4]) for v in x["tasks"]),
                authorized=False,authority="two exact current votes",hypothetical=False)
        accepted=all(v["assent"] for v in data[1:])
        return dict(x,source=r.input,status="ratified" if accepted else "declined",votes=r.inputs[1:],authorized=accepted and x["feasible"])
    if a in ("express","apply","mobilize","act"):
        tasks=activity((x,)) if x["kind"]=="activity" else x["tasks"]
        op=("return" if inward else "transfer") if a=="act" else "inspect" if inward else "care"
        return dict(common,kind="command",tasks=tasks,primitive=op,stock=r.stock,relation=r.relation,peer=r.peer,
            mode="readiness" if inward and a!="apply" else "trial" if inward else "performance",permitted=p["permitted"])
    if a=="use":
        source=dict(tasks=readiness(x)) if x["kind"]=="activity" else x
        model=reconcile((source,)) if "feasible" not in source else source
        picked=query(model,r.completed,r.clock)
        return dict(common,kind="decision",tasks=source["tasks"],completed=r.completed,clock=r.clock,
            next_task=None if picked is None else picked[0],next_action=None if picked is None else picked[1],
            responsible=None if picked is None else picked[5],feasible=model.get("feasible",False),
            authorized=x.get("authorized",False) and picked is not None and picked[5]==r.actor,
            status="prediction" if x.get("status") not in ("ratified","coupled","decision_policy","operating") else "governed_choice")
    raise ValueError("unsupported workflow operation")

def transform(name,p,previous):
    if name.startswith("resolve:"):
        result=dict(kind="resolved_work",content=encode(frame(p)))
    elif len(p["recipe"].steps)==2:
        prior=decode(previous[2]["payload"])
        if prior["kind"]!="resolved_work": raise ValueError("exact paid predecessor required")
        result=decode(prior["content"])
    else: result=frame(p)
    return "c7w",p["request"].target,{"payload":encode(result)}
