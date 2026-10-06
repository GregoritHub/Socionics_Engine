"""Constructive language and bounded search, using actor data only.

Programs are immutable tagged tuples. They contain no object names, evaluator
labels or executable Python. Calls name exact retained versions. The predictor
is a hypothesis interpreter; only the U4 executor can change physical state.
"""
from . import codec
from .records import Material, Procedure, Relation, ObjectRef
from .operation_records import SIGNATURES

# Atomic affordances, not scenario answers. Explicit input/effect dependencies.
SCHEMAS = {
    "use": {"inputs": (("target", "target"),), "reads": ("target.condition", "target.wear", "target.max_wear", "target.custodian"),
            "writes": ("target.wear", "target.condition", "progress.uses")},
    "care": {"inputs": (("target", "target"), ("stock", "care_stock")), "reads": ("target.condition", "target.wear", "care_stock.available", "care_stock.purpose", "care_stock.owner"),
             "writes": ("target.wear", "care_stock.available", "care_stock.consumed")},
    "repair": {"inputs": (("target", "target"), ("tool", "tool"), ("stock", "repair_stock")),
               "reads": ("target.condition", "tool.condition", "tool.wear", "tool.max_wear", "repair_stock.available", "repair_stock.purpose", "repair_stock.owner"),
               "writes": ("target.condition", "target.wear", "tool.condition", "tool.wear", "repair_stock.available", "repair_stock.consumed")},
    "return": {"inputs": (("target", "target"), ("relation", "relation")),
               "reads": ("target.owner", "target.custodian", "relation.predicate", "relation.status", "relation.borrower", "relation.owner", "relation.item"),
               "writes": ("target.custodian", "relation.status")},
}
SUPPORTED = tuple(sorted(SCHEMAS))
MATERIAL_FIELDS = ("owner", "custodian", "quantity", "condition")


def freeze(state):
    return tuple((slot, tuple(sorted(fields.items()))) for slot, fields in sorted(state.items()))


def thaw(state):
    return {slot: dict(fields) for slot, fields in state}


def signature(state):
    # Identity renaming cannot contribute a solution. Relational identity values
    # are preserved for legitimate owner/item comparisons; search order ignores labels.
    return codec.dumps(tuple((s, tuple((k, v) for k, v in fs if k != "ref")) for s, fs in state))


def operand(value, state):
    if type(value) is tuple:
        if len(value) != 3 or value[0] != "field":
            raise ValueError("invalid field reference")
        return state[value[1]][value[2]]
    return value


def predicate(test, state):
    if type(test) is not tuple or len(test) != 3 or test[0] not in ("eq", "ne", "lt", "le", "gt", "ge"):
        raise ValueError("explicit relational test required")
    a, b = operand(test[1], state), operand(test[2], state)
    if test[0] == "eq": return type(a) is type(b) and a == b
    if test[0] == "ne": return type(a) is not type(b) or a != b
    if type(a) is not int or type(b) is not int:
        raise ValueError("ordered relations require integers")
    return {"lt": a < b, "le": a <= b, "gt": a > b, "ge": a >= b}[test[0]]


def meets(state, goal):
    try:
        return all(predicate(t, thaw(state)) for t in goal)
    except (KeyError, ValueError):
        return False


def size(program):
    if program[0] in ("act", "call"): return 1
    if program[0] in ("seq", "choice"): return 1 + sum(size(p) for p in program[1])
    if program[0] == "if": return 2 + size(program[2]) + size(program[3])
    raise ValueError("unknown constructor")


def dependencies(program):
    if program[0] == "act": return ()
    if program[0] == "call": return (program[1],)
    children = program[1] if program[0] in ("seq", "choice") else program[2:]
    return tuple(dict.fromkeys(r for p in children for r in dependencies(p)))


def validate(program, capacities, visiting=()):
    if type(program) is not tuple or not program:
        raise ValueError("immutable program required")
    kind = program[0]
    if kind == "act":
        if len(program) != 2 or program[1] not in SCHEMAS: raise ValueError("unsupported atomic action")
    elif kind == "call":
        if len(program) != 2 or program[1] not in capacities or program[1] in visiting:
            raise ValueError("missing or cyclic subprocedure")
        validate(capacities[program[1]]["program"], capacities, (*visiting, program[1]))
    elif kind in ("seq", "choice"):
        if len(program) != 2 or type(program[1]) is not tuple or not program[1]: raise ValueError("nonempty children required")
        for p in program[1]: validate(p, capacities, visiting)
    elif kind == "if":
        if len(program) != 4 or len(program[1]) != 3: raise ValueError("condition and two branches required")
        for p in program[2:]: validate(p, capacities, visiting)
    else: raise ValueError("unknown constructor")


def action(state, name, actor):
    """Finite model of acquired U4 affordances; it cannot resolve world heads."""
    s = thaw(state)
    try:
        spec, t = SCHEMAS[name], s["target"]
        for _, role in spec["inputs"]:
            if role != "relation" and s[role]["custodian"] != actor: return None
        if name == "return":
            r = s["relation"]
            if (r["predicate"] != "return_due" or r["status"] != "open" or t["owner"] == actor
                    or r["borrower"] != actor or r["owner"] != t["owner"] or r["item"] != t["ref"].identity): return None
            t["custodian"], r["status"] = t["owner"], "fulfilled"
        else:
            if name in ("care", "repair"):
                stock = s[name + "_stock"]
                if stock["owner"] != actor or stock["purpose"] != name or stock["available"] < 1: return None
                stock["available"] -= 1
                stock["consumed"] += 1
            if name == "repair":
                tool = s["tool"]
                if t["condition"] != "damaged" or tool["condition"] != "serviceable" or tool["wear"] >= tool["max_wear"]: return None
                tool["wear"] += 1
                tool["condition"] = "damaged" if tool["wear"] == tool["max_wear"] else "serviceable"
                t["wear"], t["condition"] = 0, "serviceable"
            elif name == "care":
                if t["condition"] != "serviceable" or t["wear"] < 1: return None
                t["wear"] -= 1
            else:
                if t["condition"] != "serviceable" or t["wear"] >= t["max_wear"]: return None
                t["wear"] += 1
                t["condition"] = "damaged" if t["wear"] == t["max_wear"] else "serviceable"
                s["progress"]["uses"] += 1
        return freeze(s)
    except KeyError:
        return None


def simulate(program, state, actor, capacities, fuel):
    """Bounded hypothesis execution. Returns outcome, primitive trace and fuel.

    Calls and alternatives consume fuel even when unsuccessful. No unbounded
    expansion or exception-as-negative-evidence shortcut is used.
    """
    if fuel < 1: return "budget", state, (), 0
    fuel -= 1
    kind = program[0]
    if kind == "act":
        after = action(state, program[1], actor)
        return ("ok", after, (program[1],), fuel) if after is not None else ("inapplicable", state, (), fuel)
    if kind == "call":
        cap = capacities[program[1]]
        if not meets(state, cap["guard"]): return "inapplicable", state, (), fuel
        return simulate(cap["program"], state, actor, capacities, fuel)
    if kind == "if":
        try: chosen = program[2] if predicate(program[1], thaw(state)) else program[3]
        except (KeyError, ValueError): return "unknown", state, (), fuel
        return simulate(chosen, state, actor, capacities, fuel)
    if kind == "choice":
        for child in program[1]:
            try:
                _, _, used = take_step((child,), state, capacities, fuel)
            except GuardUnavailable:
                fuel -= 1
                continue
            except WorkUnavailable:
                return "budget", state, (), 0
            # Alternatives select by available entry guards. They do not undo
            # an infeasible selected body and silently try a different answer.
            return simulate(child, state, actor, capacities, used)
        return "inapplicable", state, (), fuel
    trace = ()
    for child in program[1]:
        status, state, part, fuel = simulate(child, state, actor, capacities, fuel)
        trace += part
        if status != "ok": return status, state, trace, fuel
    return "ok", state, trace, fuel


class GuardUnavailable(ValueError): pass


class WorkUnavailable(ValueError): pass


def take_step(pending, state, capacities, fuel):
    """Resume a procedure until its next leaf; use the current observed state.

    The immutable residual stack survives between separately paid actions.
    Failed guard probes in alternatives also consume the ticket. Physical
    feasibility is checked by the real executor, with no prediction-as-effect.
    """
    stack = list(pending)
    while stack:
        if fuel < 1: raise WorkUnavailable("continuation needs more funded interpreter work")
        fuel -= 1
        node = stack.pop(0)
        tag = node[0]
        if tag == "act": return node[1], tuple(stack), fuel
        if tag == "seq": stack[:0] = node[1]
        elif tag == "call":
            cap = capacities[node[1]]
            if not meets(state, cap["guard"]): raise GuardUnavailable("outside retained subprocedure guard")
            stack.insert(0, cap["program"])
        elif tag == "if":
            try: branch = node[2] if predicate(node[1], thaw(state)) else node[3]
            except (KeyError, ValueError) as err: raise GuardUnavailable("condition needs received fields") from err
            stack.insert(0, branch)
        elif tag == "choice":
            selected = False
            for child in node[1]:
                try:
                    action_name, rest, remaining = take_step((child,), state, capacities, fuel)
                    return action_name, (*rest, *stack), remaining
                except GuardUnavailable:
                    # Charge the full available probe extent when a nested guard
                    # fails. This conservative rule cannot grant free attempts.
                    fuel -= expanded_size(child, capacities)
                    if fuel < 0: raise WorkUnavailable("alternative guard budget exhausted")
            if not selected: raise GuardUnavailable("no applicable retained alternative")
        else: raise ValueError("unsupported procedure constructor")
    raise GuardUnavailable("no remaining action")


def expanded_size(program, capacities, memo=None):
    """Compute interpreter bound over the retained DAG without expanding it."""
    memo = {} if memo is None else memo
    if program[0] == "act": return 1
    if program[0] == "call":
        ref = program[1]
        if ref not in memo: memo[ref] = expanded_size(capacities[ref]["program"], capacities, memo)
        return 1 + memo[ref]
    children = program[1] if program[0] in ("seq", "choice") else program[2:]
    return 1 + sum(expanded_size(c, capacities, memo) for c in children)


def primitive_names(program, capacities, seen=None):
    seen = set() if seen is None else seen
    if program[0] == "act": return {program[1]}
    if program[0] == "call":
        ref = program[1]
        if ref in seen: return set()
        seen.add(ref)
        return primitive_names(capacities[ref]["program"], capacities, seen)
    children = program[1] if program[0] in ("seq", "choice") else program[2:]
    return set().union(*(primitive_names(c, capacities, seen) for c in children))


def acquired(view, context):
    result = {}
    for use in view.snapshot.acquired:
        if use.context != context: continue
        for p in view.resolve(use.procedure):
            if type(p.value) is Procedure:
                proc = p.value
                for name in SUPPORTED:
                    if proc == Procedure(SIGNATURES[name], (), (), (), "u4." + name + ".v1"):
                        result.setdefault(name, use.procedure)
    return tuple(sorted(result.items()))


def snapshot(view, slots):
    """Latest *processed* material/relational fields, with exact dependencies."""
    result, sources, addresses = {}, [], []
    for slot, initial in slots:
        candidates = {}
        for p in view.snapshot.particulars:
            if p.source.identity == initial.identity:
                values = candidates.setdefault(p.source, {})
                if type(p.value) is Material:
                    values.update({k: getattr(p.value, k) for k in MATERIAL_FIELDS})
                elif type(p.value) is Relation:
                    values.update(predicate=p.value.predicate, **{e.role: e.target.identity for e in p.value.endpoints},
                        **{a.name: a.value for a in p.value.terms})
                elif p.address.key in (*MATERIAL_FIELDS, "wear", "max_wear", "purpose", "consumed", "predicate", "status", "borrower", "item"):
                    values[p.address.key] = p.value
            if p.address.key.startswith("u9.slot.") and p.address.key.endswith(".ref") and type(p.value) is ObjectRef and p.value.identity == initial.identity:
                prefix = p.address.key[:-3]
                values = candidates.setdefault(p.value, {})
                values.update({q.address.key[len(prefix):]: q.value for q in view.resolve(p.source)
                               if q.address.key.startswith(prefix) and q.address.key != p.address.key})
        if not candidates: raise ValueError("material/relational details must be processed")
        current = max(candidates, key=lambda x: x.revision)
        fields = candidates[current]
        fields["ref"] = current
        if "quantity" in fields and fields.get("condition") == "stock":
            fields["available"] = fields["quantity"] - fields["consumed"]
        required = {"predicate", "status", "borrower", "owner", "item"} if slot == "relation" else set(MATERIAL_FIELDS)
        required |= set() if slot == "relation" else ({"purpose", "consumed", "available"} if fields.get("condition") == "stock" else {"wear", "max_wear"})
        if not required <= fields.keys(): raise ValueError("incomplete processed slot fields")
        result[slot] = fields
        for p in view.snapshot.particulars:
            if p.source == current or any(q.value == current and q.address.key.startswith("u9.slot.") for q in view.resolve(p.source)):
                sources.append(p.source); addresses.append(p.address)
    result["progress"] = {"uses": 0}
    return freeze(result), tuple(dict.fromkeys(sources)), tuple(dict.fromkeys(addresses))


def separator(positive, negative):
    """A bounded, explicit feature split; excludes labels and identity fields."""
    a, b = thaw(positive), thaw(negative)
    for slot in sorted(b):
        for field, value in sorted(b[slot].items()):
            if field in ("ref", "owner", "custodian", "quantity", "consumed", "available") or slot == "progress": continue
            if type(value) in (str, int, bool) and field in a.get(slot, {}) and a[slot][field] != value:
                return ("eq", ("field", slot, field), value)
    raise ValueError("no observed distinguishing field; generalization remains unresolved")


def search_ticket(session, primitives, capacities, actor, limit, depth, fuel):
    """Expand at most limit nodes. Preserve both frontier and deferred depth.

    Each queue entry is (state, program-prefix, next-action-index). This retains
    partial node expansion. Existing capacities precede all constructive work.
    """
    s = dict(session)
    if depth < s["depth"]: raise ValueError("search depth cannot shrink")
    queue, deferred = list(s["queue"]), list(s["deferred"])
    if depth > s["depth"]:
        queue += deferred; deferred = []
    s["depth"] = depth
    calls = tuple(("call", ref) for ref in s["repertoire"])
    # An ordered alternative is itself constructible from existing capacities.
    # Each call keeps its learned guard and ownership; no finished answer is supplied.
    options = ((("choice", calls),) if len(calls) > 1 else ()) + calls + tuple(("act", op) for op, _ in primitives)
    visited = set(s["visited"])
    examined, attempts, found = 0, 0, None
    while queue and examined < limit:
        state, prefix, cursor = queue[0]
        if meets(state, s["goal"]) and prefix:
            found = ("seq", prefix); queue.pop(0); break
        if len(prefix) >= depth:
            deferred.append(queue.pop(0)); examined += 1; continue
        if cursor >= len(options):
            queue.pop(0); examined += 1; continue
        option = options[cursor]
        status, after, _, _ = simulate(option, state, actor, capacities, fuel)
        if status == "budget":
            s.update(status="evaluation_budget", queue=tuple(queue), deferred=tuple(deferred),
                visited=tuple(sorted(visited)), considered=s["considered"]+attempts)
            return s, None, attempts
        queue[0] = state, prefix, cursor + 1
        attempts += 1
        if status == "ok":
            sig = signature(after)
            if sig not in visited:
                visited.add(sig); queue.append((after, prefix + (option,), 0))
        # One action consideration is one bounded expansion unit.
        examined += 1
    if found:
        status = "candidate"
    elif queue: status = "ticket_exhausted"
    else: status = "repertoire_exhausted_at_depth" if deferred else "repertoire_exhausted"
    s.update(queue=tuple(queue), deferred=tuple(deferred), visited=tuple(sorted(visited)),
        status=status, considered=s["considered"]+attempts)
    return s, found, attempts
