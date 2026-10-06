"""U8 decisions over detached owned input; no world or evaluator access."""
from .shell_policy import facts, FIELDS
from .cognitive_content import grouped


def opportunity(view, target, context, evidence=None):
    known, sources = facts(view, target, context, evidence)
    rows = grouped(view.snapshot.particulars if evidence is None else tuple(view.detail(a) for a in evidence))
    values = {rows[s]["partner"].value for s in sources if "partner" in rows[s]}
    if len(values) == 1:
        known["partner"] = next(iter(values))
    return known, sources


def releasable(known):
    return (all(k in known for k in FIELDS) and known["safe"] and known["available"]
            and (not known["requires_partner"] or known["willing"])
            and not known["approval_required"])


def permits(pattern, target, known, corrections, capacity, load, recalled):
    """Only authorization attributions are presently correctable by this rule."""
    if not releasable(known) or any(e.kind not in ("approval", "obligation") for e in pattern.effects):
        return None
    local = corrections.get((pattern.ref, target))
    if local and local["binding"] in recalled:
        return local["ref"]
    if capacity and capacity["binding"] in recalled and load <= capacity["max_load"]:
        return capacity["ref"]
    return None


def learned_load(examples):
    """Two independent episodes must support each retained simultaneous load."""
    usable = [x for x in examples if x["independent"]]
    if len(usable) < 2 or len({t.identity for x in usable for t in x["targets"]}) < 2:
        return 0
    return sorted((len(x["targets"]) for x in usable), reverse=True)[1]
