"""Finite C2 transformations. Only supplied, actor-accessible inputs are used.

No store, evaluator, global selector, or implicit physical truth. Models use
bounded procedure interfaces: (node, requires, produces, primitive, authority).
"""
from . import codec


def encode(data):
    return codec.dumps(tuple(sorted(data.items())))


def decode(text):
    values=codec.loads(text)
    if type(values) is not tuple or any(type(v) is not tuple or len(v)!=2 for v in values):
        raise ValueError("typed key/value content required")
    result=dict(values)
    if len(result)!=len(values): raise ValueError("duplicate content field")
    return result


def validate(data, actor, target):
    kind=data.get("kind")
    if kind=="personal":
        if set(data)!={"kind","condition","hypothetical"} or data["condition"] not in ("serviceable","damaged",None) or type(data["hypothetical"]) is not bool:
            raise ValueError("scoped personal condition and hypothetical flag required")
    elif kind=="stance":
        if set(data)!={"kind","cap","consent"} or type(data["cap"]) is not int or not 0<=data["cap"]<=1000 or type(data["consent"]) is not bool:
            raise ValueError("bounded personal cap and explicit assent required")
    elif kind=="system":
        if set(data)!={"kind","nodes"} or not 1<=len(data["nodes"])<=16:
            raise ValueError("bounded procedure-interface system required")
        for row in data["nodes"]:
            if (type(row) is not tuple or len(row)!=5 or not row[0]
                    or type(row[1]) is not tuple or type(row[2]) is not tuple
                    or not row[1] or not row[2] or any(type(x) is not str or not x for x in (*row[1],*row[2]))
                    or row[3] not in ("repair","use","care","damage") or row[4]!=actor):
                raise ValueError("exact interface and actor authority required")
            laws={"repair":(("damaged",),("serviceable",)), "use":(("serviceable",),("used",)), "care":(("worn",),("maintained",)), "damage":(("serviceable",),("damaged",))}
            if (row[1],row[2])!=laws[row[3]]:
                raise ValueError("interface must match the declared primitive law")
    else:
        raise ValueError("unsupported authored C2 content kind")


def graph(systems):
    variants={}
    for system in systems:
        for row in system["nodes"]:
            variants.setdefault(row[0],set()).add(row)
    conflicts=tuple(sorted(k for k,v in variants.items() if len(v)>1))
    nodes=tuple(sorted(row for key,values in variants.items() for row in values))
    if len(nodes)>16: raise ValueError("combined system exceeds declared node budget")
    edges=tuple(sorted((a[0],b[0],fact) for a in nodes for b in nodes if a[0]!=b[0]
                       for fact in a[2] if fact in b[1]))
    # Kahn traversal retains external prerequisites and detects closed loops.
    pending={r[0] for r in nodes}; order=[]
    while pending:
        ready=sorted(k for k in pending if not any(b==k and a in pending for a,b,_ in edges))
        if not ready: break
        order.extend(ready); pending.difference_update(ready)
    produced={f for row in nodes for f in row[2]}
    external=tuple(sorted({f for row in nodes for f in row[1]}-produced))
    return dict(nodes=nodes,edges=edges,conflicts=conflicts,cycles=tuple(sorted(pending)),
                external=external,order=tuple(order),compatible=not conflicts and not pending)


def reachable(data, facts):
    have=set(facts); fired=[]
    if data.get("compatible",False):
        for key in data["order"]:
            row=next(n for n in data["nodes"] if n[0]==key)
            if set(row[1])<=have:
                fired.append(row); have.update(row[2])
    return tuple(sorted(have)),tuple(fired)


def transform(name, p, previous=None):
    r=p["request"]; target=r.target
    prev={} if previous is None else decode(previous[2]["payload"])
    data=p.get("data",())
    if name in ("differentiate","rehearse"):
        alternatives=tuple(sorted({d["condition"] for d in data if d["condition"] is not None}))
        supported=tuple(sorted({d["condition"] for d in data if not d["hypothetical"] and d["condition"] is not None}))
        result=dict(kind="differentiation" if name=="differentiate" else "rehearsal",
            alternatives=alternatives, supported=supported, unresolved=len(supported)!=1,
            hypothetical=any(d["hypothetical"] for d in data), sources=r.inputs)
    elif name=="retain_meaning":
        result={**prev,"kind":"meaning","condition":prev["supported"][0] if len(prev["supported"])==1 else None}
    elif name=="retain_policy":
        # Rehearsal changes attention; it does not turn a possibility into a fact.
        result={**prev,"kind":"policy","attention":"inspect" if prev["hypothetical"] or prev["unresolved"] else "use",
                "basis":"hypothetical_rehearsal" if prev["hypothetical"] else "owned_comparison"}
    elif name in ("prepare_repair","prepare_use"):
        result=dict(kind="material_plan",primitive="repair" if name=="prepare_repair" else "use",
                    target=r.target,tool=r.tool,stock=r.stock)
    elif name=="material_command":
        result={**prev,"kind":"material_command"}
    elif name=="offer":
        result=dict(kind="offer",speaker=r.actor,receiver=r.peer,group=r.group,
                    target=r.target,cap=data[0]["cap"],consent=data[0]["consent"],stance=r.input)
    elif name=="read_offer":
        result=dict(kind="reading",offer=r.inputs[1],offered=data[1]["cap"],
                    cap=data[0]["cap"],consent=data[0]["consent"],speaker=data[1]["speaker"])
    elif name=="reply":
        result=dict(kind="reply",speaker=r.actor,receiver=prev["speaker"],offer=prev["offer"],
            group=r.group,target=r.target,cap=prev["cap"],consent=prev["consent"],
            understood=prev["offered"],stance=r.input)
    elif name in ("clarify","acknowledge"):
        offer,reply=data
        result=dict(kind="reciprocal",participants=(offer["speaker"],reply["speaker"]),
            group=r.group,target=r.target,cap=min(offer["cap"],reply["cap"]),
            positions=(offer["cap"],reply["cap"]),difference=offer["cap"]!=reply["cap"],
            assents=(offer["consent"],reply["consent"]),exchange=r.inputs)
    elif name in ("shared_meaning","shared_commitment"):
        result={**prev,"kind":"shared","mode":"understood" if name=="shared_meaning" else "commitment",
            "authorized":name=="shared_commitment" and all(prev["assents"]),
            "status":"understood" if name=="shared_meaning" else ("accepted" if all(prev["assents"]) else "declined")}
    elif name in ("reconcile","interfaces"):
        result=dict(kind="reconciliation",sources=r.inputs,**graph(data))
    elif name in ("retain_system","couple_system"):
        result={**prev,"kind":"organization" if name=="couple_system" else "reconciled_model",
            "coupled":name=="couple_system" and prev["compatible"],"authority":r.actor}
    elif name=="evaluate":
        source=data[0]; kind=source["kind"]
        result=dict(kind="evaluation",source=r.input,content_kind=kind,action="none",amount=0,
                    target=r.target,tool=r.tool,stock=r.stock)
        if kind in ("personal","meaning","policy"):
            result["action"]=(source["attention"] if kind=="policy" else
                ("use" if source.get("condition")=="serviceable" and not source.get("hypothetical",False) else "inspect"))
        elif kind=="shared":
            result.update(action="consume" if source["authorized"] else "propose",
                          amount=min(r.demand,source["cap"]),group=source["group"],
                          participants=source["participants"],status=source["status"])
        elif kind in ("system","reconciled_model","organization"):
            model=graph((source,)) if kind=="system" else source
            facts=tuple(p["facts"])
            all_facts,steps=reachable(model,facts)
            result.update(reachable=all_facts,steps=tuple(n[0] for n in steps),initial_facts=facts)
            if kind=="organization" and source["coupled"] and steps:
                result["action"]=steps[0][3]
        else: raise ValueError("no downstream consumer for this content")
    elif name=="decide":
        result={**prev,"kind":"decision"}
        if result["amount"]==0 and result["action"] in ("consume","propose"):
            result["action"]="none"
    else:
        raise ValueError("unsupported semantic step")
    return "c2",target,{"payload":encode(result)}
