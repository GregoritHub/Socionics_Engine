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
