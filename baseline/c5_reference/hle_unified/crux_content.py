"""Pure C1 transformations. No store, selector, hidden state, or audit input.

The executor calls one step only when its paid threshold is reached. A later
step takes the previous committed/generated content, never a precomputed answer.
"""
from . import codec
from .records import ClaimStatus, Definition, Occurrence, ObjectRef


def owned_binding(view, ref):
    binding = view._bindings.get(ref)
    if binding is None or view._heads.get(ref.identity) != binding:
        raise ValueError("current actor-owned retained input required")
    return binding


def model(view, ref):
    b = owned_binding(view, ref)
    if ref.identity.namespace != "c1.model":
        raise ValueError("retained C1 model required")
    values = {p.relation.removeprefix("c1."): p.object for p in b.content}
    expected = {"expected", "test", "relation", "status", "on_serviceable", "on_damaged", "default"}
    if (set(values) != expected or len(b.content) != len(expected)
            or values["test"] != "inspect" or values["relation"] != "condition"
            or values["expected"] not in (None, "damaged", "serviceable")
            or any(p.context != b.context or p.subject != b.target for p in b.content)):
        raise ValueError("exact scoped C1 model contract required")
    return b, values


def prepare(view, request):
    """Validate/collect accessible inputs; no semantic answer is computed here."""
    b = owned_binding(view, request.input)
    if (b.context, b.cue) != (request.context, request.cue):
        raise ValueError("input belongs to another content scope")
    details = tuple(view.detail(a) for a in request.evidence)
    if any(p is None for p in details):
        raise ValueError("undelivered, unread or foreign input")
    if request.recipe == "condition-hypothesis-v1":
        definitions = [p.value for p in view.resolve(request.rule) if type(p.value) is Definition]
        if len(definitions) != 1:
            raise ValueError("one processed policy definition required")
        rule = {a.name: a.value for a in definitions[0].constraints}
        if (rule.get("relation") != "condition" or rule.get("default") != "inspect"
                or rule.get('when."damaged"') != "inspect" or rule.get('when."serviceable"') != "use"):
            raise ValueError("C1 finite condition policy required")
        return {"binding": b, "rule": rule}
    b, values = model(view, request.input)
    if request.recipe == "condition-trial-v1":
        return {"binding": b, "model": values}
    sources = {p.source for p in details}
    if len(sources) != 1 or any(p.occurrence != Occurrence.OBSERVATION for p in details):
        raise ValueError("one coherent processed observation required")
    observed = {p.address.key: p.value for p in details}
    if (len(observed) != len(details) or observed.get("primitive") != "inspect"
            or observed.get("outcome") != "succeeded" or observed.get("model") != request.input
            or observed.get("context") != request.context
            or type(observed.get("target")) is not ObjectRef
            or observed["target"].identity != b.target.identity
            or observed["target"].revision < b.target.revision
            or observed.get("condition") not in ("damaged", "serviceable")
            or type(observed.get("event")) is not ObjectRef):
        raise ValueError("observation must describe this model's actual trial in its scope")
    return {"binding": b, "model": values, "observed": observed}


def transform(step, prepared, previous=None):
    """Return (kind, target, values). Values are plain typed proposition atoms."""
    b = prepared["binding"]
    if step == "hypothesize":
        candidates = tuple(p.object for p in b.content if p.subject == b.target
            and p.context == b.context and p.relation == "condition" and p.scope.end is None)
        if b.endorsement in (ClaimStatus.RETRACTED, ClaimStatus.DISPUTED):
            candidates = ()
        unique = {codec.dumps(v): v for v in candidates}
        expected = next(iter(unique.values())) if len(unique) == 1 else None
        if expected not in (None, "damaged", "serviceable"):
            raise ValueError("condition language cannot interpret this value")
        rule = prepared["rule"]
        return "model", b.target, {"expected": expected, "relation": "condition", "test": "inspect",
            "status": "tentative" if expected is not None else "unknown",
            "on_serviceable": rule['when."serviceable"'], "on_damaged": rule['when."damaged"'],
            "default": rule["default"]}
    if step == "instantiate":
        m = prepared["model"]
        return "trial", b.target, {"primitive": m["test"], "expected": m["expected"],
            "relation": m["relation"], "model": b.ref}
    if step == "compare":
        m, o = prepared["model"], prepared["observed"]
        comparison = "untested" if m["expected"] is None else (
            "supported_in_case" if m["expected"] == o["condition"] else "contradicted_in_case")
        return "assessment", o["target"], {"expected": m["expected"], "observed": o["condition"],
            "comparison": comparison, "event": o["event"]}
    if step == "retain":
        if previous is None or previous[0] != "assessment":
            raise ValueError("retention must consume its preceding comparison")
        _, target, assessment = previous
        observed = assessment["observed"]
        if observed not in (None, "damaged", "serviceable"):
            raise ValueError("unsupported assessment result")
        return "personal", target, {"condition": observed,
            "status": "supported" if observed is not None else "unknown",
            "tension": assessment["comparison"]}
    raise ValueError("unknown semantic recipe step")
