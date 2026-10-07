"""Independent FB4.1 composition reconstruction over raw workflow records.

The accepted workflow auditor validates the witness world.  A matched ablation
must be rejected by that ordinary auditor, while this module verifies that the
same paid family was run, exactly one preregistered intermediate effect was
removed, and the fixed downstream answer changed.  No executor, selector,
policy, scheduler, or test fixture is imported here.
"""
import hashlib

from .material import attrs
from .operations import indexed
from .records import Account
from .selection_records import dumps
from .workflow_audit import audit as workflow_audit, payload


FAMILIES = {
    "theorize-apply-embody": {
        "steps": (("tae-theory", "Theorize", "accumulation"),
                  ("tae-apply", "Apply", "expenditure"),
                  ("tae-embody", "Embody", "expenditure")),
        "links": ("direct", "event-observation"),
        "cut": "tae-apply",
    },
    "share-commune-identify": {
        "steps": (("sci-share", "Share", "accumulation"),
                  ("sci-commune", "Commune", "expenditure"),
                  ("sci-identify", "Identify", "expenditure")),
        "links": ("direct", "direct"),
        "cut": "sci-commune",
    },
    "coordinate-mobilize": {
        "steps": (("cm-coordinate", "Coordinate", "expenditure"),
                  ("cm-mobilize", "Mobilize", "expenditure")),
        "links": ("direct",),
        "cut": "cm-mobilize",
    },
    "institutionalize-educate": {
        "steps": (("ie-institutionalize", "Institutionalize", "expenditure"),
                  ("ie-educate", "Educate", "accumulation")),
        "links": ("direct",),
        "cut": "ie-educate",
    },
    "organize-integrate-apply": {
        "steps": (("oia-organize", "Organize", "expenditure"),
                  ("oia-integrate", "Integrate", "expenditure"),
                  ("oia-apply", "Apply", "expenditure")),
        "links": ("direct", "direct"),
        "cut": "oia-apply",
    },
}


def _ref(ref):
    return "%s:%s@%s" % (ref.identity.namespace, ref.identity.key, ref.revision)


def _versions(transactions):
    versions = {}
    heads = {}
    for tx in transactions:
        for version in tx.versions:
            versions[version.ref] = version
            heads[version.ref.identity] = version
    return versions, heads


def _jobs(heads):
    found = {}
    for version in heads.values():
        d = attrs(version)
        if d.get("c7w"):
            found[d["key"]] = (version, d)
    return found


def _outputs(d):
    public = indexed(d, "public.")
    return tuple(x for x in (*public, d.get("binding"), d.get("result")) if x is not None)


def _output(d):
    return _outputs(d)[0]


def _digest(versions, ref):
    version = versions[ref]
    try:
        value = payload(version)
    except (ValueError, KeyError, TypeError):
        value = attrs(version)
    return hashlib.sha256(dumps(value).encode()).hexdigest()


def _decision(versions, jobs, family):
    key = {"theorize-apply-embody": "tae-decision",
           "share-commune-identify": "sci-decision",
           "coordinate-mobilize": "cm-decision",
           "institutionalize-educate": "ie-decision",
           "organize-integrate-apply": "oia-decision"}[family]
    _, d = jobs[key]
    value = payload(versions[d["binding"]])
    return (value.get("next_task"), value.get("next_action"), value.get("responsible"), value.get("feasible"))


def _conflict(versions, jobs, prefix):
    _, source = jobs[prefix + "-origin-conflict"]
    ref = source["binding"]
    value = payload(versions[ref])
    if not value.get("conflicts") or value.get("feasible"):
        raise ValueError("explicit inherited origin conflict missing")
    _, returned = jobs[prefix + "-origin-return"]
    if indexed(returned, "source.") != (ref,):
        raise ValueError("origin return did not consume the exact inherited conflict")
    answer = payload(versions[returned["binding"]])
    if answer.get("next_task") is not None or answer.get("feasible"):
        raise ValueError("origin return erased inherited conflict")
    return {"source": _ref(ref), "digest": _digest(versions, ref),
            "conflicts": tuple(value["conflicts"])}


def _world(transactions, family, require_native):
    transactions = tuple(transactions)
    rejection = None
    try:
        native = workflow_audit(transactions, require_native)
    except ValueError as exc:
        native = None
        rejection = str(exc)
    versions, heads = _versions(transactions)
    jobs = _jobs(heads)
    spec = FAMILIES[family]
    rows = []
    for key, movement, polarity in spec["steps"]:
        if key not in jobs:
            raise ValueError("missing family step " + key)
        _, d = jobs[key]
        if (d["movement"], d["polarity"], d["spent"], d["completed"]) != (movement, polarity, d["required"], d["required"]):
            raise ValueError("unpaid or substituted family step " + key)
        out = _output(d)
        if out not in versions:
            raise ValueError("family intermediate not retained " + key)
        rows.append({"key": key, "movement": movement, "polarity": polarity,
                     "spent": d["spent"], "status": d["status"],
                     "output": _ref(out), "digest": _digest(versions, out)})
    for i, mode in enumerate(spec["links"]):
        _, left = jobs[spec["steps"][i][0]]
        _, right = jobs[spec["steps"][i + 1][0]]
        priors = _outputs(left)
        source = indexed(right, "source.")[0]
        if mode == "direct":
            if source not in priors:
                raise ValueError("equal endpoint substituted for exact generated result")
        else:
            observation = versions[source]
            account = observation.facet(Account)
            if (source.identity.namespace != "u4.observation" or account is None
                    or account.sources != (left["result"],)
                    or attrs(observation).get("event") != left["result"]):
                raise ValueError("exact material event observation handoff missing")
    prefix = spec["steps"][0][0].split("-")[0]
    return {"native": native, "ordinary_rejection": rejection, "rows": rows,
            "decision": _decision(versions, jobs, family),
            "conflict": _conflict(versions, jobs, prefix), "jobs": jobs,
            "versions": versions}


def audit_pair(witness_transactions, witness_access, ablation_transactions, ablation_access, family):
    """Verify one witness/ablation pair; returns JSON-safe evidence."""
    if family not in FAMILIES:
        raise ValueError("unknown composition family")
    witness = _world(witness_transactions, family, witness_access)
    ablation = _world(ablation_transactions, family, ablation_access)
    if witness["native"] is None:
        raise ValueError("ordinary workflow audit rejected family witness")
    if ablation["native"] is not None or not ablation["ordinary_rejection"]:
        raise ValueError("defining-step ablation passed ordinary workflow audit")
    if witness["decision"] == ablation["decision"]:
        raise ValueError("ablation did not change fixed downstream answer")
    wr = witness["rows"]
    ar = ablation["rows"]
    cut = FAMILIES[family]["cut"]
    wi = next(i for i, row in enumerate(wr) if row["key"] == cut)
    if wr[wi]["spent"] != ar[wi]["spent"]:
        raise ValueError("ablation changed declared main cost")
    changed = tuple(w["key"] for w, a in zip(wr, ar) if w["digest"] != a["digest"])
    if cut not in changed:
        raise ValueError("preregistered intermediate effect was not removed")
    if witness["conflict"]["digest"] != ablation["conflict"]["digest"]:
        raise ValueError("matched origin conflict differs")
    return {
        "passed": True,
        "family": family,
        "steps": tuple((r["movement"], r["polarity"]) for r in wr),
        "witness_outputs": tuple(r["digest"] for r in wr),
        "ablation_outputs": tuple(r["digest"] for r in ar),
        "comparison_spent": wr[wi]["spent"],
        "cut": cut,
        "changed_outputs": changed,
        "witness_answer": witness["decision"],
        "ablation_answer": ablation["decision"],
        "ordinary_ablation_rejection": ablation["ordinary_rejection"],
        "origin_conflict": witness["conflict"],
        "exact_generated_handoffs": len(FAMILIES[family]["links"]),
        "participant_replay": False,
    }
