"""Bounded self-route proposals over already paid participant-visible content."""
from itertools import combinations, product, islice
from .workflow_records import WORKFLOW_RECIPES
from .selection_records import NAMES, PERSPECTIVES, dumps
from .cognitive_routes import route

CELLS = (0, 1, 10, 11, 20, 21, 30, 31)

def rank(row):
    return (-row['priority'], -row['preference'], row['effort'], row['cell'], dumps(row['inputs']))

def proposals(s):
    r = s['request']; a = r['actor']; items = s['items']; rows = []
    def kind(*ks): return [x for x in items if x['data']['kind'] in ks]
    for cell in CELLS:
        name = NAMES[cell // 2]; face = ('accumulation', 'expenditure')[cell % 2]
        recipe = WORKFLOW_RECIPES['workflow-' + name.lower() + '-' + face + '-v1']
        if name == 'Contemplate': bundles = combinations(kind('intention', 'stance'), 2)
        elif name == 'Integrate': bundles = combinations(kind('system'), 2)
        elif name == 'Act': bundles = ((x,) for x in kind('activity'))
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
            priority = s['need']['priorities'][PERSPECTIVES.index(recipe.destination)]
            options.append(dict(cell=cell, recipe=recipe.key, inputs=tuple(x['ref'] for x in bundle),
                eligible=bool(good and priority), reason=reason, priority=priority,
                preference=int(s['need']['externalize'] == (face == 'expenditure')), effort=effort))
        best = min(options, key=lambda x: (not x['eligible'], *rank(x))) if options else dict(
            cell=cell, recipe=recipe.key, inputs=(), eligible=False, reason='missing paid content',
            priority=s['need']['priorities'][PERSPECTIVES.index(recipe.destination)],
            preference=int(s['need']['externalize'] == (face == 'expenditure')), effort=effort)
        rows.append(dict(best, examined=min(len(bounded), r['alternatives']), deferred=len(bounded) > r['alternatives']))
    comparison = 1 + len(items) + len(rows) + sum(x['examined'] for x in rows)
    for row in rows:
        if row['eligible'] and min(s['wallet']) < comparison + row['effort']:
            row.update(eligible=False, reason='insufficient paid comparison and estimated child budget')
    return rows

def choose(rows):
    return min((r for r in rows if r['eligible']), key=rank, default=None)
