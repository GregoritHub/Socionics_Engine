"""Common supplied adapter over completed recall only; no world or Truth access."""
from hle.contracts import ActionRequest, ClaimStatus
from hle.world_records import INSPECT, TRANSFER


def decide(actor, recipient, item, results, selected_memories):
    memories = {m.ref: m for m in selected_memories}
    evidence = {}
    for result in results:
        for hit in result.hits:
            memory = memories[hit.memory]
            if memory.claim_status in (ClaimStatus.RETRACTED, ClaimStatus.DISPUTED):
                continue
            for index in hit.proposition_indexes:
                prop = memory.content[index]
                if prop.subject == item and prop.relation == "owned_by":
                    evidence[(memory.ref, index)] = prop
    latest = max((p.scope.start for p in evidence.values()), default=None)
    selected = [(ref, p) for (ref, _), p in evidence.items() if p.scope.start == latest]
    owners = {p.object for _, p in selected}
    owner = next(iter(owners)) if len(owners) == 1 else None
    if any(result.truncated for result in results):
        owner = None
    basis = tuple(dict.fromkeys(ref for ref, _ in selected))
    action = ActionRequest(actor, TRANSFER, (item, recipient), basis) if owner == actor else ActionRequest(actor, INSPECT, (item,), basis)
    return owner, action


def permitted(session):
    results = session.results()
    refs = tuple(dict.fromkeys(h.memory for r in results for h in r.hits))
    view, _ = session.world.select_input(session.actor, memories=refs)
    # Deliberately exclude inbox observations from the adapter input.
    return results, view.own_memories
