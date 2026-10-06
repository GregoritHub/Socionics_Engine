"""Explicitly synthetic sign/control traces; NOT generated runtime behavior.

These fixtures exercise the witnesses independently at the assessment boundary.
They cannot satisfy a gate whose required_run_kind is runtime.
"""
from dataclasses import replace
from .contracts import Ref, Kind
from .crux import Perspective as P, FormalMovement, Route, Polarity
from .shell_records import *


def fixture(sign, positive=True, index=0):
    if sign not in SIGNS: raise ValueError('unknown sign fixture')
    ref = lambda kind, key: Ref(kind, 'fixture:' + key, 1)
    actor = ref(Kind.ENTITY, 'actor'); context = ref(Kind.CONTEXT, 'workshop')
    lineage = ref(Kind.MEMORY, 'material'); loan = ref(Kind.EVENT, 'loan:' + str(index))
    item = ref(Kind.ENTITY, 'item'); start = 100 * index + 1
    expected = Claim(item, 'release_requires_external_confirmation', 'false', context, loan)
    wrong = replace(expected, value='true')
    raw = ref(Kind.MEMORY, 'held:' + str(index)); alt = ref(Kind.MEMORY, 'alternative:' + str(index))
    other = ref(Kind.MEMORY, 'other:' + str(index))
    inner = FormalMovement(Route(P.I, P.I), Polarity.ACCUMULATION)
    outward = FormalMovement(Route(P.I, P.WE), Polarity.EXPENDITURE)
    necessary = FormalMovement(Route(P.I, P.ITS), Polarity.ACCUMULATION)
    evidence = LocalEvidence(ref(Kind.OBSERVATION, 'terms:' + str(index)), actor,
         start, start + 1, ref(Kind.EVENT, 'interpret:' + str(index)), (expected,))
    opportunity = OpportunityEvidence(ref(Kind.DEMAND, 'demand:' + str(index)), 'differentiate',
         ('differentiate',), (raw,), 5, 100, 100, True, (), start, inner, necessary, start+2)
    parts = [ContentPart(raw, lineage, start, (expected,))]
    ops = []
    def op(name, offset, inputs=(), outputs=(), claims=(), target='', movement=outward, domains=(P.I, P.WE)):
        tag = f'{index}:{offset}:{name}'
        ops.append(TraceOperation(ref(Kind.EVENT, tag), start + offset, name, tuple(inputs), tuple(outputs),
             tuple(claims), (ref(Kind.WORK, tag),), 1, (movement,), tuple(domains), target))
    op('hold', 2, outputs=(raw,), movement=inner, domains=(P.I,))
    increase = None; initial = (); prerequisites = ()
    if sign == 'premature_translation':
        prerequisites = ('differentiate',)
        if not positive: op('differentiate', 3, inputs=(raw,), movement=necessary, domains=(P.I, P.ITS))
        chosen = wrong if positive else expected
        parts.append(ContentPart(alt, lineage, start+4, (chosen,)))
        op('translate', 4, inputs=(raw,), outputs=(alt,), claims=(chosen,))
        op('act', 5, inputs=(alt,), claims=(chosen,))
    elif sign == 'forced_placement':
        chosen = wrong if positive else expected
        parts.append(ContentPart(alt, lineage, start+3, (chosen,)))
        op('place', 3, inputs=(raw,), outputs=(alt,), claims=(chosen,))
        op('maintain', 4, inputs=(alt,), claims=(chosen,))
    elif sign == 'new_defensive_structure':
        increase = DemandIncrease(ref(Kind.EVENT, 'increase:' + str(index)), start+3,
                       (('simultaneous_obligations', 1),), (('simultaneous_obligations', 2),),
                       'same parties, context, outcome, duration and resources',
                       'same parties, context, outcome, duration and resources')
        chosen = wrong if positive else expected
        parts.append(ContentPart(alt, lineage, start+4, (chosen,)))
        op('construct', 4, inputs=(raw,), outputs=(alt,), claims=(chosen,), domains=(P.I, P.ITS))
        op('use', 5, inputs=(alt,), claims=(chosen,), domains=(P.ITS, P.IT))
    elif sign == 'residual_fragmentation':
        parts.extend((ContentPart(alt, lineage, start+3, (expected,)),
                      ContentPart(other, lineage, start+3, (wrong,))))
        op('integrate_closed' if positive else 'integrate_open', 3, inputs=(raw,), outputs=(alt, other), domains=(P.I,))
        op('act', 4, inputs=(alt,), claims=(expected,))
        op('act', 5, inputs=(other,), claims=(wrong,))
    else:
        parts.append(ContentPart(alt, lineage, start+3, (wrong,)))
        if positive:
            op('construct', 3, inputs=(raw,), outputs=(alt,), domains=(P.I,))
            op('block', 4, inputs=(alt,), claims=(wrong,), target='differentiate', movement=inner, domains=(P.I,))
        else:
            # Rest has exactly the same scalar route trace as the blocked case;
            # demand is the discriminant, not motion or cancellation.
            opportunity = replace(opportunity, demand=None)
            op('construct', 3, inputs=(raw,), outputs=(alt,), domains=(P.I,))
            op('block', 4, inputs=(alt,), claims=(wrong,), target='differentiate', movement=inner, domains=(P.I,))
    return EngagementTrace(loan, actor, lineage, context, 'iee', 'fixture', start, start+10,
                 opportunity, (evidence,), tuple(parts), tuple(ops), (sign,), prerequisites, initial, increase,
                 endpoint='correct')


def panel():
    from .shell_assessment import JointShellAssessment
    rows = {}
    for sign in SIGNS:
        rows[sign] = {}
        for positive, label in ((True, 'sign'), (False, 'ordinary_control')):
            joint = JointShellAssessment()
            for index in range(3): joint.append(fixture(sign, positive, index))
            rows[sign][label] = joint.report()
    return rows
