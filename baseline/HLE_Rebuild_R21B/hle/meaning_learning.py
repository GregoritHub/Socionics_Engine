"""Bounded participant calculations, with no World or evaluator input.

Cards supply addresses. Consequences supply samples. A three-sample majority
and least-used allocation are engineering choices, not source-defined meanings.
Proposals become usable only after the caller completes paid Write and Bind.
R13 invokes these calculations under declared paid processing before Write/Bind.
The sample rule remains an engineering hypothesis, not a psychological law.
"""
from dataclasses import dataclass
import json

from .codec import canonical, decode, encode
from .contracts import ClaimStatus, MemoryRevision, Proposition, Ref, TimeScope, WorkStatus
from .memory_records import WriteDraft
from .world_records import INSPECT, TRANSFER


@dataclass(frozen=True)
class PersonalMeaning:
    ref: Ref
    owner: Ref
    cue: Ref
    context: Ref
    scene: str
    samples: tuple[tuple[bool, Ref], ...]
    check: bool
    guard_memory: Ref | None
    encounters: int


def read_meaning(memory, actor):
    if type(memory) is not MemoryRevision or memory.owner != actor:
        raise ValueError("meaning must be an owned retained memory")
    fields = {p.relation: p.object for p in memory.content}
    required = {"meaning.scene", "meaning.samples", "meaning.check", "meaning.guard", "meaning.encounters"}
    if set(fields) != required or len(memory.content) != len(required):
        raise ValueError("malformed meaning memory")
    cue, context = memory.content[0].subject, memory.content[0].context
    if any(p.subject != cue or p.context != context for p in memory.content):
        raise ValueError("mixed cue/context in meaning")
    samples = tuple((x[0], decode(x[1])) for x in json.loads(fields["meaning.samples"]))
    if not 1 <= len(samples) <= 3 or any(type(x) is not bool or r not in memory.links for x, r in samples):
        raise ValueError("meaning sample lacks an exact retained link")
    check = 2 * sum(x for x, _ in samples) >= len(samples)
    if fields["meaning.check"] is not check:
        raise ValueError("meaning expectation disagrees with retained samples")
    guard = fields["meaning.guard"]
    if guard == "none": guard = None
    elif not isinstance(guard, Ref) or guard not in memory.links:
        raise ValueError("meaning guard lacks an exact retained link")
    return PersonalMeaning(memory.ref, actor, cue, context, fields["meaning.scene"], samples,
                   check, guard, fields["meaning.encounters"])


def allocate(cues, assignments):
    """Only already published owned associations affect slot occupancy."""
    counts = {cue: sum(value == cue for value in assignments.values()) for cue in cues}
    return min(cues, key=lambda cue: (counts[cue], cues.index(cue)))


def experienced_unavailability(actor, item, first_action, observation):
    """Consequence relative to the transfer demand, not the post-transfer owner.

In this fixture the genuinely retained starting belief is self-ownership.
Use the first inspection or transfer receipt: successful transfer leaves the
recipient owning the object, which must NOT be mislearned as prior unavailability.
"""
    if first_action.owner != actor or observation.observer != actor or first_action.observation != observation.ref:
        raise ValueError("experience must be this actor's matching delivered receipt")
    if first_action.request.inputs[0] != item:
        raise ValueError("experience concerns a different demand")
    if first_action.request.operation == TRANSFER:
        if first_action.outcome not in (WorkStatus.COMPLETED, WorkStatus.FAILED):
            raise ValueError("partial action is not a completed experience")
        return first_action.outcome == WorkStatus.FAILED
    if first_action.request.operation == INSPECT:
        values = [p.object for p in observation.content if p.subject == item and p.relation == "owned_by"]
        if len(values) != 1: raise ValueError("inspection must deliver one ownership result")
        return values[0] != actor
    raise ValueError("unsupported experience grammar")


def learn(actor, cue, context, scene, previous, memory, unavailable, key, expected, at):
    if memory.owner != actor or type(unavailable) is not bool:
        raise ValueError("only complete owned experience may update meaning")
    if previous is not None and (previous.owner != actor or previous.context != context or previous.scene != scene or previous.cue != cue):
        raise ValueError("previous meaning belongs to another owner/context/cue")
    samples = (() if previous is None else previous.samples) + ((unavailable, memory.ref),)
    samples = samples[-3:]
    guard = None if previous is None else previous.guard_memory
    # Only a real R4 Embody output can carry a usable capability; no insertion.
    if memory.capabilities: guard = memory.ref
    links = tuple(dict.fromkeys(tuple(r for _, r in samples) + (() if guard is None else (guard,))))
    values = (
        ("meaning.scene", scene),
        ("meaning.samples", canonical([[b, encode(r)] for b, r in samples])),
        ("meaning.check", 2 * sum(b for b, _ in samples) >= len(samples)),
        ("meaning.guard", "none" if guard is None else guard),
        ("meaning.encounters", 1 if previous is None else previous.encounters + 1),
    )
    content = tuple(Proposition(cue, relation, value, context, TimeScope(at, None)) for relation, value in values)
    return WriteDraft(key, content, links, ClaimStatus.TENTATIVE, expected,
        "tentative contextual expectation from the last three owned action consequences")


def describe(meaning):
    if meaning is None: return None
    return {"ref": encode(meaning.ref), "cue": meaning.cue.key, "context": meaning.context.key,
            "scene": meaning.scene, "samples": [b for b, _ in meaning.samples],
            "experience_refs": [encode(r) for _, r in meaning.samples], "check": meaning.check,
            "guard_memory": None if meaning.guard_memory is None else encode(meaning.guard_memory),
            "encounters": meaning.encounters}
