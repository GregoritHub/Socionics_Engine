"""Pure finite semantics. Inputs are actor-owned records and processed particulars.

This module cannot access world heads, intentions, evaluators or foreign skills.
The controlled wording is a read-only display of a typed transmitted expression.
"""
from . import composition_language as lang
from .records import ObjectRef


class MeaningGap(ValueError):
    def __init__(self, reason, term=""):
        self.reason, self.term = reason, term
        super().__init__(reason + (":" + term if term else ""))


def units(value):
    return 1 + sum(units(x) for x in value) if type(value) is tuple else 1


def expand(body, lexicon, capacities=None, active=()):
    """Replace local words/calls, preserving constructors and exact conditions."""
    if type(body) is not tuple or not body:
        raise ValueError("typed expression required")
    tag = body[0]
    if tag == "word" and len(body) == 2 and type(body[1]) is str:
        entry = lexicon.get(body[1])
        if not entry: raise MeaningGap("unknown_term", body[1])
        if entry["status"] != "stable": raise MeaningGap(entry["status"] + "_term", body[1])
        return entry["program"]
    if tag == "call" and len(body) == 2:
        if capacities is None or body[1] not in capacities or body[1] in active:
            raise MeaningGap("unavailable_procedure")
        return expand(capacities[body[1]]["program"], lexicon, capacities, (*active, body[1]))
    if tag == "act" and len(body) == 2 and body[1] in lang.SUPPORTED: return body
    if tag in ("seq", "choice") and len(body) == 2 and type(body[1]) is tuple and body[1]:
        return tag, tuple(expand(c, lexicon, capacities, active) for c in body[1])
    if tag == "if" and len(body) == 4:
        validate_test(body[1])
        return tag, body[1], expand(body[2], lexicon, capacities, active), expand(body[3], lexicon, capacities, active)
    if tag == "test" and len(body) == 2:
        validate_test(body[1]); return body
    if tag == "because" and len(body) == 3 and body[1][0] == "test":
        return tag, expand(body[1], lexicon, capacities, active), expand(body[2], lexicon, capacities, active)
    raise ValueError("unsupported communication constructor")


def public_form(body, capacities):
    # Private procedure identities are expressed through their structure.
    if body[0] == "call": return expand(body, {}, capacities)
    if body[0] in ("seq", "choice"): return body[0], tuple(public_form(c, capacities) for c in body[1])
    if body[0] == "if": return "if", body[1], public_form(body[2], capacities), public_form(body[3], capacities)
    if body[0] == "because": return "because", body[1], public_form(body[2], capacities)
    return body


def validate_test(test):
    if type(test) is not tuple or len(test) != 3 or test[0] not in ("eq", "ne", "lt", "le", "gt", "ge"):
        raise ValueError("explicit relation required")
    for operand in test[1:]:
        if type(operand) is tuple:
            if len(operand) != 3 or operand[0] != "field" or not all(type(x) is str for x in operand):
                raise ValueError("invalid field operand")
        elif type(operand) not in (str, int, bool, ObjectRef) and operand is not None:
            from .records import ObjectId
            if type(operand) is not ObjectId: raise ValueError("unsupported literal")


def tests(body):
    if body[0] == "test": return (body[1],)
    if body[0] == "if": return (body[1], *tests(body[2]), *tests(body[3]))
    if body[0] in ("seq", "choice"): return tuple(t for c in body[1] for t in tests(c))
    if body[0] == "because": return (*tests(body[1]), *tests(body[2]))
    return ()


def executable(body):
    return body[2] if body[0] == "because" else body


def exact_target(view, ref):
    data = {p.address.key: p.value for p in view.resolve(ref)}
    required = ("condition", "wear", "max_wear", "owner", "custodian")
    if any(k not in data for k in required): raise MeaningGap("unprocessed_demonstration_target")
    return lang.freeze({"target": {**{k: data[k] for k in required}, "ref": ref}})


def observed_demo(view, wire):
    initial = exact_target(view, wire["target"])
    rows = [{p.address.key: p.value for p in view.resolve(event)} for event in wire["events"]]
    if not rows or len(set(wire["events"])) != len(rows): raise MeaningGap("incomplete_demonstration")
    if any(not row or row.get("event") != ref or row.get("actor") != wire["speaker"]
           or row.get("primitive") not in lang.SUPPORTED for row, ref in zip(rows, wire["events"])):
        raise MeaningGap("unprocessed_demonstration")
    if any(row.get("outcome") != "succeeded" for row in rows[:-1]):
        raise MeaningGap("broken_demonstration_sequence")
    if any(row.get("u9_step") != i for i, row in enumerate(rows)):
        raise MeaningGap("noncontiguous_demonstration")
    run_ids = {row["u9_run"].identity for row in rows}
    if len(run_ids) != 1: raise MeaningGap("unrelated_demonstration_steps")
    success = all(row["outcome"] == "succeeded" for row in rows)
    # Received event projections carry actual fields, never predictions.
    observed = lang.thaw(initial)
    observed["progress"] = {"uses": 0}
    for row in rows:
        if row["outcome"] == "succeeded" and row["primitive"] == "use": observed["progress"]["uses"] += 1
        for key, value in row.items():
            if key.startswith("u9.slot."):
                slot, field = key[8:].split(".", 1)
                observed.setdefault(slot, {})[field] = value
    success = success and lang.meets(lang.freeze(observed), wire["goal"])
    if success != (wire["act"] == "demonstration"):
        raise MeaningGap("demonstration_outcome_conflict")
    return dict(message=wire["ref"], target=wire["target"].identity, initial=initial,
                program=("seq", tuple(("act", row["primitive"]) for row in rows)),
                success=success, events=wire["events"])


def trace_for(program, state):
    tag = program[0]
    if tag == "act": return (program[1],)
    if tag == "seq": return tuple(a for p in program[1] for a in trace_for(p, state))
    if tag == "if": return trace_for(program[2] if lang.predicate(program[1], lang.thaw(state)) else program[3], state)
    raise ValueError("demonstration induction supports sequence and observed splits")


def induce(examples):
    """Two distinct targets per trace; retain unresolved conflicting evidence."""
    positives = [e for e in examples if e["success"]]
    groups = {}
    for e in positives: groups.setdefault(e["program"], []).append(e)
    if not groups or any(len({e["target"] for e in rows}) < 2 for rows in groups.values()):
        return "tentative", None, None
    programs = tuple(groups)
    split = None
    if len(programs) == 1: program = programs[0]
    elif len(programs) == 2:
        old, new = programs
        new_states = [lang.thaw(e["initial"])["target"] for e in groups[new]]
        old_states = [lang.thaw(e["initial"])["target"] for e in groups[old]]
        for field in ("max_wear", "condition", "wear"):
            values = {s[field] for s in new_states}
            if len(values) == 1 and all(s[field] not in values for s in old_states):
                split = ("eq", ("field", "target", field), new_states[0][field]); break
        if split is None: return "ambiguous", None, None
        program = ("if", split, new, old)
    else: return "ambiguous", None, None
    for e in examples:
        if not e["success"] and trace_for(program, e["initial"]) == trace_for(e["program"], e["initial"]):
            return "challenged", None, split
    return "stable", program, split


def render(body):
    """Pure controlled wording; no parsing, state mutation or fluent model."""
    tag = body[0]
    if tag in ("act", "word"): return body[1]
    if tag == "seq": return "; then ".join(render(p) for p in body[1])
    if tag == "choice": return "first applicable: " + " / ".join(render(p) for p in body[1])
    if tag == "if": return "if " + str(body[1]) + ", " + render(body[2]) + "; otherwise " + render(body[3])
    if tag == "test": return str(body[1])
    if tag == "because": return render(body[2]) + " because " + render(body[1])
    if tag == "clarify": return "Please clarify " + str(body[1:])
    if tag == "answer": return "My received evidence says " + str(body[1:])
    return str(body)
