"""Five separate R16A hypotheses over local demand, content and actual work.

This does not infer a sign from an OIG signature. Positive witnesses require
independent content/action evidence. Missing measurement channels stay unknown.
Reports describe a finite historical window, never clearance or development.
"""
from dataclasses import is_dataclass
from enum import Enum
from .contracts import Ref
from .crux import Perspective
from .development_structure import LensContent, QUOTIENTS, quotient, observe_trajectory
from .shell_records import SIGNS


def reftext(ref):
    return None if ref is None else f'{ref.kind.value}:{ref.key}@{ref.revision}'


def json_value(value):
    if isinstance(value, Ref): return reftext(value)
    if isinstance(value, Enum): return value.value
    if is_dataclass(value):
        return {k: json_value(getattr(value, k)) for k in value.__dataclass_fields__}
    if isinstance(value, dict): return {str(k): json_value(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)): return [json_value(v) for v in value]
    if isinstance(value, (set, frozenset)): return sorted(json_value(v) for v in value)
    return value


def opportunity_status(trace):
    o = trace.opportunity
    if o.demand is None: return 'no_demand'
    if o.refusal_evidence: return 'legitimate_refusal'
    if o.engaged_at is None: return 'unknown_engagement_time'
    if not any(e.delivered <= o.engaged_at for e in trace.evidence): return 'no_delivery'
    if not any(e.interpreted is not None and e.interpreted <= o.engaged_at for e in trace.evidence):
        return 'not_interpreted_at_engagement'
    known = constraints(trace, o.engaged_at)
    used = {c.key for op in trace.operations for c in op.claims} | {c.key for p in trace.parts for c in p.claims}
    if not known.keys() & used: return 'no_unambiguous_scoped_constraint'
    if not o.capacity_evidence or o.necessary_operator not in o.available_operators:
        return 'unavailable_operation'
    if o.required_units is None: return 'unknown_work_quote'
    if min(o.energy, o.time) < o.required_units: return 'insufficient_resources'
    if not o.selected: return 'ordinary_scheduling_delay'
    if not trace.closed: return 'open_engagement'
    return 'eligible'


def constraints(trace, tick):
    """Contradictory usable evidence stays ambiguous, not evaluator-selected."""
    values = {}
    for e in trace.evidence:
        if e.interpreted is not None and e.interpreted <= tick:
            for c in e.claims:
                if c.context == trace.context and c.occasion == trace.engagement:
                    values.setdefault(c.key, set()).add(c.value)
    return {k: next(iter(v)) for k, v in values.items() if len(v) == 1}


def conflicts(trace, claims, tick):
    known = constraints(trace, tick)
    return tuple(c for c in claims if c.key in known and c.value != known[c.key])


def projected_path(trace):
    """Declared content projection, not a universal archetypal correspondence.

Domains name realized operations. Foreign representatives are the stable
material lineage of used parts conflicting with accessible interpreted terms.
Correct physical endpoints do not erase earlier conflict observations.
"""
    parts = {p.ref: p for p in trace.parts}
    path = [LensContent((Perspective.I,), (), trace.context, trace.projection)]
    for op in trace.operations:
        claims = op.claims + tuple(c for r in op.inputs + op.outputs for c in parts[r].claims)
        foreign = (trace.lineage,) if conflicts(trace, claims, op.tick) else ()
        path.append(LensContent(op.domains, foreign, trace.context, trace.projection))
    return tuple(path)


class OIGAccumulator:
    """Twelve equality-class indexes; no all-pairs recurrence materialization."""
    def __init__(self, tim):
        self.tim = tim; self.count = 0; self.scope = None
        self.first = {}; self.last = {}; self.visible = set()
        self.classes = {q: {} for q in QUOTIENTS}; self.visits = 0

    def append(self, content):
        scope = content.context, content.projection_contract
        if self.scope is not None and self.scope != scope: raise ValueError('OIG scope changed')
        self.scope = scope
        for q in QUOTIENTS:
            value = quotient(self.tim, content, q); self.visits += 1
            if q in self.last and self.last[q] != value: self.visible.add(q)
            self.first.setdefault(q, value); self.last[q] = value
            self.classes[q].setdefault(value, []).append(self.count)
        self.count += 1

    def result(self):
        if not self.count: raise ValueError('empty OIG observation')
        net = {q for q in QUOTIENTS if self.first[q] != self.last[q]}
        return {'V': frozenset(self.visible), 'N': frozenset(net),
                'K': frozenset(self.visible - net),
                'R': {q: tuple(tuple(g) for g in self.classes[q].values()) for q in QUOTIENTS}}


def oig_json(result):
    return {k: sorted('/'.join(q) for q in result[k]) for k in ('V', 'N', 'K')} | {
        'R': {'/'.join(q): [list(g) for g in result['R'][q]] for q in QUOTIENTS}}


def _witness(trace, sign):
    ops = trace.operations; parts = {p.ref: p for p in trace.parts}
    paid = lambda op: op.units > 0 and bool(op.work) and bool(op.movements)
    bad = lambda op: conflicts(trace, op.claims, op.tick)
    if sign == 'premature_translation':
        if not trace.prerequisites: return None, 'required distinction is unspecified'
        done = set()
        for op in ops:
            if op.name in ('translate', 'spend') and paid(op) and bad(op):
                held = any(x.name == 'hold' and x.tick < op.tick and set(x.outputs) & set(op.inputs) and paid(x) for x in ops)
                if held and not set(trace.prerequisites) <= done:
                    # A consequence must actually reuse the substituted output.
                    use = next((x for x in ops if x.tick > op.tick and x.name in ('act', 'place', 'use')
                                and set(x.inputs) & set(op.outputs) and paid(x) and bad(x)), None)
                    if use: return (op, use), 'held content substituted before its required distinction and used against correction'
            if paid(op): done.add(op.name)
        return (), 'no consequential premature substitution witnessed'
    if sign == 'forced_placement':
        for op in ops:
            if op.name == 'place' and paid(op) and bad(op):
                use = next((x for x in ops if x.tick > op.tick and x.name in ('maintain', 'use', 'act')
                            and paid(x) and bad(x)
                            and set(x.inputs) & (set(op.inputs) | set(op.outputs))), None)
                if use: return (op, use), 'incompatible placement maintained after interpreted evidence'
        return (), 'no maintained incompatible placement witnessed'
    if sign == 'new_defensive_structure':
        inc = trace.increase
        if inc is None: return None, 'comparable demand increase is not measured'
        if not inc.greater: return (), 'demand is equal, lesser or incomparable'
        for op in ops:
            fresh = [r for r in op.outputs if r not in trace.initial_structures and parts[r].created == op.tick]
            if op.name == 'construct' and op.tick > inc.tick and fresh and paid(op):
                use = next((x for x in ops if x.tick > op.tick and x.name in ('use', 'block')
                            and set(x.inputs) & set(fresh) and paid(x) and bad(x)), None)
                if use: return (op, use), 'new post-increase structure used to maintain the challenged relation'
        return (), 'no new post-increase maintaining structure witnessed'
    if sign == 'residual_fragmentation':
        closed = [op for op in ops if op.name == 'integrate_closed' and paid(op)]
        if not closed:
            if any(op.name == 'integrate_open' for op in ops): return (), 'unfinished integration is explicitly retained as unresolved'
            return None, 'an integration attempt is not measured'
        for integration in closed:
            uses = [x for x in ops if x.tick > integration.tick and x.name in ('act', 'use', 'place')
                    and set(x.inputs) & set(integration.outputs) and paid(x)]
            for i, left in enumerate(uses):
                for right in uses[i+1:]:
                    distinct = set(left.inputs) - set(right.inputs)
                    conflict = any(a.key == b.key and a.value != b.value for a in left.claims for b in right.claims)
                    if distinct and conflict: return (integration, left, right), 'different parts of one integrated lineage drive incompatible same-scope actions'
        return (), 'no consequential fragmentation after the declared integration'
    if sign == 'foreclosure':
        o = trace.opportunity
        if o.required_movement is None or o.current_movement is None:
            return None, 'necessary and current movements are not both measured'
        if o.required_movement == o.current_movement: return (), 'necessary movement is already current'
        starts = [x for x in ops if x.name == 'start' and x.target == o.necessary_operator and paid(x)
                  and o.required_movement in x.movements]
        if starts: return (), 'necessary movement initiated'
        block = next((x for x in ops if x.name == 'block' and x.target == o.necessary_operator
                      and x.inputs and paid(x) and bad(x)), None)
        if block: return (block,), 'paid maintaining rule prevents the selected available movement from initiating'
        return None, 'non-initiation has no independently witnessed maintaining mechanism'
    raise ValueError('unknown sign')


def assess_engagement(trace):
    status = opportunity_status(trace); path = projected_path(trace)
    acc = OIGAccumulator(trace.tim)
    for content in path: acc.append(content)
    signs = {}
    for sign in SIGNS:
        if sign not in trace.measured:
            witness, reason = None, 'runtime witness channel not implemented' if trace.execution_kind == 'runtime' else 'channel not measured'
        elif status != 'eligible': witness, reason = None, status
        else: witness, reason = _witness(trace, sign)
        signs[sign] = {'observation': 'unassessed' if witness is None else 'positive' if witness else 'negative',
                       'reason': reason, 'events': [] if not witness else [reftext(x.event) for x in witness],
                       'work': [] if not witness else [reftext(r) for x in witness for r in x.work]}
    return {'engagement': reftext(trace.engagement), 'execution_kind': trace.execution_kind,
            'actor': reftext(trace.actor), 'lineage': reftext(trace.lineage),
            'window': [trace.start, trace.end], 'queue_residence': trace.end - trace.opportunity.queue_entered,
            'opportunity': status, 'endpoint': trace.endpoint, 'signs': signs,
            'oig': oig_json(acc.result()), 'oig_samples': len(path), 'oig_visits': acc.visits}


class JointShellAssessment:
    """One material scope; each distinct eligible engagement contributes once."""
    def __init__(self, threshold=3):
        if type(threshold) is not int or threshold < 1: raise ValueError('positive threshold required')
        self.threshold = threshold; self.scope = None; self._rows = {}; self._traces = {}
        self._counts = {s: {'positive': 0, 'negative': 0, 'unassessed': 0} for s in SIGNS}

    def append(self, trace):
        if self.scope is not None and self.scope != trace.scope: raise ValueError('assessment scope changed')
        if trace.engagement in self._rows: raise ValueError('engagement already counted')
        self.scope = trace.scope
        row = assess_engagement(trace); self._rows[trace.engagement] = row; self._traces[trace.engagement] = trace
        for s in SIGNS: self._counts[s][row['signs'][s]['observation']] += 1
        return row

    def report(self):
        signs = {}
        for s, count in self._counts.items():
            n = count['positive']
            state = 'established_in_window' if n >= self.threshold else 'candidate' if n else 'not_observed' if count['negative'] else 'unassessed'
            signs[s] = dict(count, status=state, threshold=self.threshold)
        return {'scope': None if self.scope is None else json_value(self.scope), 'signs': signs,
                'distinct_engagements': len(self._rows), 'engagements': json_value(list(self._rows.values())),
                'clearance': 'unassessed; absence or an endpoint cannot certify R19 clearance',
                'coherence': 'failed_in_window' if any(c['positive'] for c in self._counts.values()) else 'unassessed'}

    def reference_oig_matches(self):
        return all(row['oig'] == oig_json(observe_trajectory(t.tim, projected_path(t)))
                   for key, row in self._rows.items() for t in (self._traces[key],))
