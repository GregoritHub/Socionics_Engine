"""Bounded self-route proposals over already paid participant-visible content."""
from itertools import combinations, product, islice
from .workflow_records import WORKFLOW_RECIPES
from .selection_records import NAMES, PERSPECTIVES, dumps
from .cognitive_routes import route
from .workflow_content import reconcile, query, readiness

CELLS = (0, 1, 10, 11, 20, 21, 30, 31)

def rank(row):
    return (-row['priority'], -row['preference'], -row.get('coverage', 0), row['effort'], row['cell'], dumps(row['inputs']))

CROSSING_CELLS = tuple(sorted((*CELLS, 2, 3, 6, 7, 8, 9, 14, 15, 24, 25, 26, 27)))
SOCIAL_NAMES = ('Share', 'Coordinate', 'Identify', 'Mobilize', 'Institutionalize', 'Educate')

def proposals(s, cells=CELLS):
    r = s['request']; a = r['actor']; items = s['items']; rows = []
    social_policy = s.get('policy') in ('c7-workflow-selection-v3', 'c7-workflow-selection-v4')
    def kind(*ks): return [x for x in items if x['data']['kind'] in ks]
    for cell in cells:
        name = NAMES[cell // 2]; face = ('accumulation', 'expenditure')[cell % 2]
        recipe = WORKFLOW_RECIPES['workflow-' + name.lower() + '-' + face + '-v1']
        if name == 'Contemplate': bundles = combinations(kind('intention', 'stance'), 2)
        elif name == 'Integrate': bundles = combinations(kind('system'), 2)
        elif name in ('Act', 'Embody'): bundles = ((x,) for x in kind('activity'))
        elif name == 'Express': bundles = ((x,) for x in kind('intention'))
        elif name == 'Theorize': bundles = ((x,) for x in kind('intention', 'personal'))
        elif name == 'Apply': bundles = ((x,) for x in kind('system', 'rule'))
        elif name == 'Understand': bundles = product(kind('system', 'rule'), kind('intention', 'stance'))
        elif name == 'Organize':
            observations = tuple(kind('activity'))
            bundles = (observations,) if observations else ()
        elif name in ('Share', 'Coordinate', 'Educate'):
            kinds = {'Share': ('intention', 'personal'), 'Coordinate': ('activity',), 'Educate': ('system', 'rule')}[name]
            bundles = ((x, o, q) for x, o, q in product(kind(*kinds), kind('offer'), kind('reply'))
                if o['data'].get('source') == x['ref'] and q['data'].get('offer') == o['ref'])
        elif name == 'Identify': bundles = product(kind('shared'), kind('intention', 'stance'))
        elif name == 'Mobilize': bundles = ((x,) for x in kind('shared'))
        elif name == 'Institutionalize':
            if face == 'accumulation':
                observations = tuple(kind('activity'))
                bundles = ((x, *observations) for x in kind('shared')) if observations else ()
            else:
                bundles = ((x, *votes) for x in kind('rule') for votes in combinations(kind('vote'), 2)
                    if all(v['data'].get('draft') == x['ref'] for v in votes))
        else:
            bundles = ((x, o, q) for x, o, q in product(kind('shared'), kind('offer'), kind('reply'))
                if o['data'].get('source') == x['ref'] and q['data'].get('offer') == o['ref'])
        bounded = list(islice(bundles, r['alternatives'] + 1)); options = []
        effort = sum(sum(x['charges']) + x['content_units'] for x in route(
            s['tim'], s['cursor'], recipe.elements, recipe.origin, recipe.destination, face)) + recipe.material_units
        for bundle in bounded[:r['alternatives']]:
            good = True; reason = 'paid compatible ' + name.lower() + ' content'
            if len({t[0] for x in bundle for t in x['data'].get('tasks', ())}) > 8:
                good = False; reason = 'combined task bound exceeded'
            if name == 'Act':
                x = bundle[0]['data']; t = s['target']
                good = x.get('target') == r['target'] and t.get('custodian') == a and r['peer'] is not None
                if face == 'accumulation':
                    good = good and t.get('owner') == r['peer'] and r['relation'] is not None and bool(s['relation'])
                else: good = good and t.get('owner') == a
                reason = 'observed equipment and paid custody roles' if good else 'missing observed custody or return relation'
            if name == 'Commune':
                x, o, q = (v['data'] for v in bundle); g = s['group']; members = () if g is None else g.get('members', ())
                good = (bool(g) and g.get('context') == r['context'] and len(members) == 2
                    and set(members) == {a, r['peer']} and x.get('group') == r['group']
                    and set(x.get('participants', ())) == set(members)
                    and (o.get('speaker'), o.get('receiver'), q.get('speaker'), q.get('receiver')) == (a, r['peer'], r['peer'], a)
                    and o.get('group') == q.get('group') == r['group'] and o.get('tasks') == x['tasks']
                    and all(t[5] in members for z in (x, o, q) for t in z.get('tasks', ())))
                reason = 'exact paid two-member exchange' if good else 'missing exact reciprocal scope'
            if name in ('Express', 'Theorize', 'Embody', 'Organize', 'Understand', 'Apply'):
                good = good and crossing_applicable(s, name, face, bundle)
                reason = 'paid crossing prerequisites' if good else 'missing paid crossing prerequisite'
            if name in SOCIAL_NAMES:
                good = good and social_applicable(s, name, face, bundle)
                reason = 'paid scoped social prerequisites' if good else 'missing paid social prerequisite'
            if s.get('policy') == 'c7-workflow-selection-v4' and r.get('procedure') is not None and recipe.material_units:
                good = good and name in ('Express', 'Apply', 'Mobilize') and (face == 'accumulation' or bool(s['acquired']))
                reason = 'paid named care prerequisite' if good else 'missing acquired care or incompatible material means'
            priority = s['need']['priorities'][PERSPECTIVES.index(recipe.destination)]
            options.append(dict(cell=cell, recipe=recipe.key, inputs=tuple(x['ref'] for x in bundle),
                eligible=bool(good and priority), reason=reason, priority=priority,
                preference=int(s['need']['externalize'] == (face == 'expenditure')), effort=effort))
            if social_policy: options[-1]['coverage'] = len(bundle)
        best = min(options, key=lambda x: (not x['eligible'], *rank(x))) if options else dict(
            cell=cell, recipe=recipe.key, inputs=(), eligible=False, reason='missing paid content',
            priority=s['need']['priorities'][PERSPECTIVES.index(recipe.destination)],
            preference=int(s['need']['externalize'] == (face == 'expenditure')), effort=effort)
        if social_policy and not options: best['coverage'] = 0
        rows.append(dict(best, examined=min(len(bounded), r['alternatives']), deferred=len(bounded) > r['alternatives']))
    comparison = 1 + len(items) + len(rows) + sum(x['examined'] for x in rows)
    for row in rows:
        if row['eligible'] and min(s['wallet']) < comparison + row['effort']:
            row.update(eligible=False, reason='insufficient paid comparison and estimated child budget')
    return rows

def choose(rows):
    return min((r for r in rows if r['eligible']), key=rank, default=None)


def social_applicable(s, name, face, bundle):
    r = s['request']; a = r['actor']; g = s['group']; values = [v['data'] for v in bundle]; x = values[0]
    members = () if not g else g.get('members', ())
    if (not g or g.get('context') != r['context'] or len(members) != 2 or set(members) != {a, r['peer']}
        or any(t[5] not in members for v in values for t in v.get('tasks', ()))): return False
    if x['kind'] in ('shared', 'rule') and (x.get('group') != r['group'] or set(x.get('participants', ())) != set(members)): return False
    if name in ('Share', 'Coordinate', 'Educate'):
        o, q = values[1:]; tasks = readiness(x) if x['kind'] == 'activity' else x['tasks']
        return ((o.get('source'), q.get('offer')) == (bundle[0]['ref'], bundle[1]['ref'])
            and (o.get('speaker'), o.get('receiver'), q.get('speaker'), q.get('receiver')) == (a, r['peer'], r['peer'], a)
            and o.get('group') == q.get('group') == r['group'] and o.get('tasks') == tasks)
    if name == 'Identify': return True
    if name == 'Mobilize':
        return x.get('authorized', False) and crossing_applicable(s, 'Express', face, bundle)
    if face == 'accumulation':
        observations = values[1:]
        return (len({v['event'] for v in observations}) == len(observations)
            and all(v['outcome'] == 'succeeded' and v['actor'] in members
                and v['primitive'] in {t[1] for t in x['tasks']} for v in observations))
    return (x.get('status') == 'draft' and {v.get('speaker') for v in values[1:]} == set(members)
        and all(v.get('draft') == bundle[0]['ref'] and v.get('tasks') == x['tasks']
            and v.get('group') == r['group'] for v in values[1:]))


def crossing_applicable(s, name, face, bundle):
    """Visible prerequisites only; actual native admission and commit still decide."""
    r=s['request'];a=r['actor'];data=[v['data'] for v in bundle];x=data[0]
    if x['kind']=='rule' or s['group'] is not None:
        g=s['group'];members=() if not g else g.get('members',())
        if (not g or g.get('context')!=r['context'] or len(members)!=2 or set(members)!={a,r['peer']}
            or any(t[5] not in members for v in data for t in v.get('tasks',()))): return False
        if x['kind']=='rule' and (x.get('group')!=r['group'] or set(x.get('participants',()))!=set(members)):return False
    if name=='Organize':
        return (len({v['event'] for v in data})==len(data) and all(v['outcome']=='succeeded' for v in data)
            and (face=='accumulation' or all(v.get('owner')==a for v in data)))
    if name not in ('Express','Apply'):return True
    permitted=x.get('consent',True)
    if name=='Apply':
        if x['kind']=='rule':permitted=x.get('authorized',False)
        elif x.get('authority') is not None:permitted=permitted and x['authority']==a
    if not permitted:return False
    if face=='accumulation':return True
    first=query(reconcile((x,)),(),0);t=s['target'];stock=s['stock']
    return bool(first and (first[1],first[5])==('care',a) and r['stock'] is not None and stock
        and t.get('custodian')==a and t.get('condition')=='serviceable' and t.get('wear',0)>0
        and stock.get('owner')==a and stock.get('custodian')==a)
