"""Shared references and conditional Fold bridge, never a participant's mastery.

Domain semantics and learning rules are declared finite hypotheses. This module
makes no claim to prove archetypal universality or geometric 4D projection.
"""
from dataclasses import dataclass
from types import MappingProxyType
import hashlib,json
from .cards import CARDS, SUIT_READINGS
from .crux import Perspective as P, Route
from .model_a import ego, position_of, position, jungian

EDGES = MappingProxyType({'f':(P.I,P.WE), 't':(P.IT,P.ITS), 'n':(P.I,P.ITS), 's':(P.IT,P.WE)})
SUITS = MappingProxyType({s:(domain,reading) for s,domain,reading in SUIT_READINGS})
# Exact source terms, with undefined meaning distinct from missing identity.
RANKS = MappingProxyType({c.ref.key:(c.symbol,c.rank,c.folded_location) for c in CARDS})
RELATIONS = (('acceptance','creates','return_condition'),('use','requires','care'),('care','compatible_with','release'))
REFERENCE = MappingProxyType({'id':'concept:entrusted_use@1','relations':RELATIONS,
    'suits':('Coin','Sword','Club'), 'rank_reference':'arcana:5',
    'rank_interpretation_status':'proposed workshop reading: learned rules mediate an accepted agreement; not a complete Hierophant definition',
    'scope':'explicitly accepted loan; no claim that receiving every kind of help creates debt'})
SOURCE_MEANINGS = MappingProxyType({'minor:Wand:10':'Burden','minor:Cup:10':'Fulfillment','minor:Sword:10':'Tragedy','minor:Coin:10':'Security',
    'arcana:19':'Ouranic, Grandiose','arcana:20':'Cthonic, Deep','arcana:21':'Ge, Grounded'})
SEAL = hashlib.sha256(json.dumps({'reference':dict(REFERENCE),'suits':dict(SUITS),'ranks':dict(RANKS),
    'source_meanings':dict(SOURCE_MEANINGS),'edges':dict(EDGES),'learning_version':'r145.v1'},sort_keys=True).encode()).hexdigest()

@dataclass(frozen=True)
class SituatedEdge:
    element: str
    position: tuple[int,int,int]
    seat: int
    family_edge: tuple[P,P]
    route: Route
    type_coordinates: tuple[int,int,int,int]

def bridge(tim, element, origin):
    if element[:1] not in EDGES or element not in ('fi','fe','ti','te','ni','ne','si','se'):
        raise ValueError('known information element required')
    ends=EDGES[element[0]]
    if origin not in ends: raise ValueError('origin is not incident on function family')
    seat=position_of(tim,element)
    return SituatedEdge(element,position(seat),seat,ends,Route(origin,ends[1] if origin==ends[0] else ends[0]),jungian(tim))

def conceptual_path(tim):
    # A two-edge I -> WE -> IT realization, then its return. Row crossing is
    # composed, never silently granted as a primitive or claimed individuation.
    return (bridge(tim,'fi',P.I),bridge(tim,'si',P.WE),bridge(tim,'si',P.IT),bridge(tim,'fi',P.WE))
