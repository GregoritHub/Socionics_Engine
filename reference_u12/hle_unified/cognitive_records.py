"""U5 requests and source references. Prices and reconciliation are hypotheses."""
from dataclasses import dataclass
from hle.contracts import Record
from hle.cards import CARDS, SUIT_READINGS
from hle.concept_structure import SOURCE_MEANINGS
from .records import (ObjectId, ObjectRef, ObjectVersion, Role, Definition,
                      SourceStatus, Attribute, text_required)
from .operation_records import WRITER, registry as operation_registry
from .particulars import DetailAddress


def reference(key):
    return ObjectRef(ObjectId("u5.reference", key), 1)


def catalog():
    """Labels, ranks and supplied meanings stay distinct from personal accounts."""
    values = []
    ranks = set()
    for suit, domain, reading in SUIT_READINGS:
        values.append(ObjectVersion(reference("suit:" + suit), WRITER, suit,
            (Role.DEFINITION,), (Definition(domain + "; " + reading,
                SourceStatus.SOURCE_DEFINED, (Attribute("domain", domain),
                                             Attribute("ego_reading", reading))),)))
    for card in CARDS:
        rank_key = "rank:" + card.deck + ":" + str(card.rank)
        if rank_key not in ranks:
            ranks.add(rank_key)
            values.append(ObjectVersion(reference(rank_key), WRITER, rank_key,
                (Role.DEFINITION,), (Definition("Printed rank, distinct from folded location",
                    SourceStatus.SOURCE_DEFINED),), attributes=(Attribute("rank", card.rank),
                    Attribute("folded_location", card.folded_location))))
        meaning = SOURCE_MEANINGS.get(card.ref.key)
        values.append(ObjectVersion(reference(card.ref.key), WRITER, card.symbol,
            (Role.DEFINITION,), (Definition(meaning, SourceStatus.SOURCE_DEFINED
                if meaning is not None else SourceStatus.UNSPECIFIED),),
            attributes=(Attribute("rank", reference(rank_key)),
                Attribute("suit", reference("suit:" + card.suit) if card.suit else None),
                Attribute("deck", card.deck), Attribute("folded_location", card.folded_location),
                Attribute("layer", card.layer_label))))
    return tuple(values)


@dataclass(frozen=True)
class CognitiveRequest(Record):
    key: str
    actor: ObjectId
    purpose: str
    context: ObjectRef
    cue: ObjectRef
    target: ObjectRef
    rule: ObjectRef
    evidence: tuple[DetailAddress, ...]
    elements: tuple[str, ...] = ()
    visit_limit: int = 32

    def __post_init__(self):
        super().__post_init__()
        text_required(self.key)
        if self.purpose not in ("plan", "integrate") or self.visit_limit < 1:
            raise ValueError("supported cognitive purpose and positive recall bound required")
        if len(set(self.evidence)) != len(self.evidence) or not self.evidence:
            raise ValueError("distinct accessible evidence required")


def registry():
    return {**operation_registry(), "CognitiveRequest": CognitiveRequest}
