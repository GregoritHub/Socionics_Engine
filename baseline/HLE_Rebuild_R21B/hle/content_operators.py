"""Finite content contracts, detached from world state and type labels.

The Ne/Fi names below are experimental operationalizations, not definitions of
human functions. Learning eliminates hypotheses using observed demonstration
traces; a condition name or desired test answer never enters these functions.
"""

SEARCH = {
    "first": lambda offered: offered[:1],
    "last": lambda offered: offered[-1:],
    "all": lambda offered: offered[:],
}
BOUNDARY = {
    "ignore": lambda offered, accepts: offered[:],
    "respect": lambda offered, accepts: [x for x in offered if x in accepts],
    "reverse": lambda offered, accepts: [x for x in offered if x not in accepts],
}
ASPECT = {
    "task": "fi", "search_demo": "ne", "boundary_demo": "fi",
    "search_rule": "ti", "boundary_rule": "ti", "options": "ne",
    "admissible": "fi", "plan": "te", "training": "ti",
}
TARGET = {
    "demonstrate_search": "ne", "demonstrate_boundary": "fi",
    "infer_search": "ti", "infer_boundary": "ti", "search": "ne",
    "relate": "fi", "prepare": "te", "hold": "fe",
}


def validate(body):
    """Check the closed grammar before publishing or routing a packet."""
    if type(body) is not dict or body.get("kind") not in ASPECT:
        raise ValueError("unknown content kind")
    def identifiers(value):
        return type(value) is list and all(type(x) is str and x for x in value) and len(set(value)) == len(value)
    kind = body["kind"]
    if kind in ("training", "search_demo", "boundary_demo"):
        cases = body.get("cases")
        valid = type(cases) is list and bool(cases)
        for case in cases if valid else ():
            valid = valid and type(case) is dict and identifiers(case.get("offered")) and bool(case["offered"])
            valid = valid and identifiers(case.get("accepts")) and set(case["accepts"]) <= set(case["offered"])
            if kind != "training":
                valid = valid and identifiers(case.get("result")) and set(case["result"]) <= set(case["offered"])
    elif kind.endswith("_rule"):
        valid = body.get("program") in (SEARCH if kind == "search_rule" else BOUNDARY)
    elif kind == "task":
        valid = (type(body.get("key")) is str and bool(body["key"]) and identifiers(body.get("offered"))
                 and bool(body["offered"]) and identifiers(body.get("accepts"))
                 and set(body["accepts"]) <= set(body["offered"])
                 and type(body.get("recipient")) is str and bool(body["recipient"]))
    else:
        valid = type(body.get("task")) is str and bool(body["task"])
        if kind in ("options", "admissible"):
            valid = valid and identifiers(body.get("items"))
        else:
            valid = valid and (body.get("item") is None or type(body["item"]) is str)
            valid = valid and type(body.get("recipient")) is str and bool(body["recipient"])
    if not valid:
        raise ValueError("invalid finite content structure")
    return body


def one(values, kind, optional=False):
    found = [v for v in values if v["kind"] == kind]
    if optional and not found:
        return None
    if len(found) != 1:
        raise ValueError(f"exactly one {kind} input required")
    return found[0]


def infer(demo, family):
    hypotheses = SEARCH if family == "search" else BOUNDARY
    survivors = []
    for name, operation in hypotheses.items():
        if all(operation(c["offered"]) == c["result"] if family == "search"
               else operation(c["offered"], c["accepts"]) == c["result"]
               for c in demo["cases"]):
            survivors.append(name)
    if len(survivors) != 1:
        raise ValueError("demonstrations do not identify a unique rule")
    return {"kind": family + "_rule", "program": survivors[0]}


def transform(operator, values):
    """Return new content and declared work extent using ONLY explicit inputs."""
    if operator.startswith("demonstrate_"):
        family = operator.removeprefix("demonstrate_")
        training = one(values, "training")
        cases = []
        for case in training["cases"]:
            result = (SEARCH["all"](case["offered"]) if family == "search"
                      else BOUNDARY["respect"](case["offered"], case["accepts"]))
            cases.append(dict(case, result=result))
        return {"kind": family + "_demo", "cases": cases}, sum(len(c["offered"]) for c in cases)
    if operator.startswith("infer_"):
        family = operator.removeprefix("infer_")
        demo = one(values, family + "_demo")
        return infer(demo, family), 3 * sum(len(c["offered"]) for c in demo["cases"])
    if operator == "hold":
        if len(values) != 1:
            raise ValueError("hold requires one content object")
        return values[0], 1
    task = one(values, "task")
    if operator == "search":
        rule = one(values, "search_rule", optional=True)
        program = "first" if rule is None else rule["program"]
        options = SEARCH[program](task["offered"])
        return {"kind": "options", "task": task["key"], "items": options}, len(task["offered"])
    if operator == "relate":
        options = one(values, "options")
        if options["task"] != task["key"]:
            raise ValueError("options belong to another demand")
        rule = one(values, "boundary_rule", optional=True)
        program = "ignore" if rule is None else rule["program"]
        items = BOUNDARY[program](options["items"], task["accepts"])
        return {"kind": "admissible", "task": task["key"], "items": items}, max(1, len(options["items"]))
    if operator == "prepare":
        related = one(values, "admissible")
        if related["task"] != task["key"]:
            raise ValueError("constraints belong to another demand")
        return {"kind": "plan", "task": task["key"], "item": next(iter(related["items"]), None),
                "recipient": task["recipient"]}, 1
    raise ValueError("unknown content operator")

# R13 bounded semantic hypotheses. The old nine-kind grammar is preserved.
_LEGACY_VALIDATE, _LEGACY_TRANSFORM = validate, transform
ASPECT.update({
    'alternatives': 'ne', 'condition': 'si', 'consent': 'fi', 'means': 'te',
    'temporal': 'ni', 'commitments': 'se', 'distinctions': 'ti',
    'shared_request': 'fe', 'acknowledgment': 'fe',
    **{'result_' + ie: ie for ie in ('ne','si','fi','te','ni','se','ti','fe')},
})
TARGET.update({'content_' + ie: ie for ie in ('ne','si','fi','te','ni','se','ti','fe')})
INPUT_KIND = {'ne':'alternatives', 'si':'condition', 'fi':'consent', 'te':'means',
              'ni':'temporal', 'se':'commitments', 'ti':'distinctions', 'fe':'shared_request'}


def _ids(value):
    return type(value) is list and all(type(x) is str and x for x in value) and len(set(value)) == len(value)


def _num(value): return type(value) is int and value >= 0


def validate(body):
    if type(body) is not dict: raise ValueError('content object required')
    kind = body.get('kind')
    if kind in ('training','search_demo','boundary_demo','search_rule','boundary_rule','task','options','admissible','plan'):
        _LEGACY_VALIDATE(body)
        fields = {'training':{'kind','cases'}, 'search_demo':{'kind','cases'}, 'boundary_demo':{'kind','cases'},
                  'search_rule':{'kind','program'},'boundary_rule':{'kind','program'},
                  'task':{'kind','key','offered','accepts','recipient'}, 'options':{'kind','task','items'},
                  'admissible':{'kind','task','items'},'plan':{'kind','task','item','recipient'}}[kind]
        if set(body) != fields: raise ValueError('undeclared content field')
        if kind in ('training','search_demo','boundary_demo'):
            expected = {'offered','accepts'} | (set() if kind=='training' else {'result'})
            if any(set(c)!=expected for c in body['cases']): raise ValueError('undeclared case field')
        return body
    if type(body.get('task')) is not str or not body['task']: raise ValueError('task identity required')
    if kind == 'alternatives':
        valid = set(body)=={'kind','task','offered','permitted'} and _ids(body.get('offered')) and _ids(body.get('permitted')) and set(body['permitted'])<=set(body['offered'])
    elif kind == 'condition':
        valid = (set(body)=={'kind','task','value','low','high','observed_at','now','budget','cost'}
                 and all(_num(body[k]) for k in ('value','low','high','observed_at','now','budget','cost'))
                 and body['low']<=body['high'] and body['observed_at']<=body['now'])
    elif kind == 'consent':
        valid = set(body)=={'kind','task','partner','offered','accepts','consented'} and _ids(body['offered']) and _ids(body['accepts']) and set(body['accepts'])<=set(body['offered']) and type(body['partner']) is str and bool(body['partner']) and type(body['consented']) is bool
    elif kind in ('means','commitments'):
        rows=body.get('rows')
        valid = set(body)=={'kind','task','rows','budget'} and _num(body['budget']) and type(rows) is list
        if valid:
            valid=all(type(r) is dict and set(r)=={'id','cost','authorized','ready'} and type(r['id']) is str and r['id'] and _num(r['cost']) and type(r['authorized']) is bool and type(r['ready']) is bool for r in rows)
            valid=valid and len({r['id'] for r in rows})==len(rows)
    elif kind == 'temporal':
        edges=body.get('edges')
        valid=set(body)=={'kind','task','nodes','edges','ready_at','now'} and _ids(body['nodes']) and type(edges) is list and _num(body['now'])
        if valid:
            ready=body['ready_at']
            valid=type(ready) is list and all(type(r) is list and len(r)==2 and type(r[0]) is str and r[0] in body['nodes'] and _num(r[1]) for r in ready)
            valid=valid and len(ready)==len(body['nodes']) and len({r[0] for r in ready})==len(ready)
        if valid: valid=all(type(e) is list and len(e)==2 and all(type(x) is str and x in body['nodes'] for x in e) for e in edges)
    elif kind == 'distinctions':
        rows=body.get('assertions')
        valid=set(body)=={'kind','task','assertions'} and type(rows) is list and all(type(r) is list and len(r)==2 and all(type(x) is str and x for x in r) for r in rows)
    elif kind == 'shared_request':
        valid=set(body)=={'kind','task','required'} and _ids(body['required']) and bool(body['required'])
    elif kind == 'acknowledgment':
        valid=set(body)=={'kind','task','sender','accepted'} and type(body['sender']) is str and bool(body['sender']) and type(body['accepted']) is bool
    elif kind in {'result_'+ie for ie in INPUT_KIND}:
        expected={'kind','task','items','valid','spent'} | ({'schedule'} if kind=='result_ni' else set())
        valid=set(body)==expected and _ids(body['items']) and type(body['valid']) is bool and _num(body['spent'])
        if valid and kind=='result_ni':
            valid=type(body['schedule']) is list and all(type(r) is list and len(r)==2 and type(r[0]) is str and _num(r[1]) for r in body['schedule'])
            valid=valid and [r[0] for r in body['schedule']]==body['items']
    else: valid=False
    if not valid: raise ValueError('invalid R13 bounded content contract')
    return body


def transform(operator, values):
    for value in values: validate(value)
    if not operator.startswith('content_'):
        return _LEGACY_TRANSFORM(operator,values)
    ie=operator.removeprefix('content_')
    if ie not in INPUT_KIND: raise ValueError('unknown semantic operation')
    b=one(values,INPUT_KIND[ie]); items=[]; ok=True; spent=0; schedule=[]
    if ie=='ne': items=[x for x in b['offered'] if x in b['permitted']]; extent=len(b['offered'])
    elif ie=='si':
        ok=b['low']<=b['value']<=b['high'] and b['cost']<=b['budget'] and b['observed_at']==b['now']; extent=4
    elif ie=='fi':
        ok=b['consented']; items=[x for x in b['offered'] if x in b['accepts']] if ok else []; extent=len(b['offered'])
    elif ie in ('te','se'):
        for r in b['rows']:
            if r['authorized'] and r['ready'] and spent+r['cost']<=b['budget']:
                items.append(r['id']); spent+=r['cost']
        extent=len(b['rows']); ok=bool(items)
    elif ie=='ni':
        todo=list(b['nodes'])
        while todo:
            ready=[n for n in todo if all(a in items for a,z in b['edges'] if z==n)]
            if not ready: ok=False; break
            items.extend(ready); todo=[n for n in todo if n not in ready]
        times={}; observed=dict(b['ready_at'])
        for n in items:
            times[n]=max([b['now'],observed[n]]+[times[a]+1 for a,z in b['edges'] if z==n])
            schedule.append([n,times[n]])
        extent=len(b['nodes'])+len(b['edges'])+len(b['ready_at'])
    elif ie=='ti':
        grouped={}
        for k,v in b['assertions']: grouped.setdefault(k,set()).add(v)
        ok=all(len(v)==1 for v in grouped.values()); items=sorted(k for k,v in grouped.items() if len(v)==1); extent=len(b['assertions'])
    else:
        acks=[v for v in values if v['kind']=='acknowledgment']
        if any(a['task']!=b['task'] for a in acks) or len({a['sender'] for a in acks})!=len(acks): raise ValueError('mixed or duplicate acknowledgments')
        items=[a['sender'] for a in acks if a['accepted'] and a['sender'] in b['required']]
        ok=set(items)==set(b['required']); extent=len(b['required'])+len(acks)
    result={'kind':'result_'+ie,'task':b['task'],'items':items,'valid':ok,'spent':spent}
    if ie=='ni': result['schedule']=schedule
    return validate(result),max(1,extent)
