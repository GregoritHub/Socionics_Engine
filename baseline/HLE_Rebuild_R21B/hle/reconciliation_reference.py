"""Offline R16B fold without live adapters, sign predicates or participant policy.

Reads committed statements and effects, authenticates references and costs,
reconstructs four witnesses and the twelve quotient paths independently.
"""
from .reconciliation_records import AccountTransaction, AccountPart
from .compensation_records import REQUIRED,ReleaseTransaction,DEPENDENCY,WIRE
from .autonomy_records import WorkshopCommand
from .contracts import WorkStatus
from .world_records import ENERGY, TIME
from .crux import Perspective as P, Polarity
from .concept_structure import conceptual_path
from .processing import _route_geometry
from .development_structure import LensContent, observe_trajectory
from .shell_records import PROJECTION
from .shell_assessment import reftext, oig_json
from .codec import loads


def reference(world):
    records = {}; facts = {}; demands = {}; accounts = {}; units = {}; results = []; errors = []
    profiles = {p.owner:p.tim for p in world.profiles}
    for tx in world._journal:
        e = tx.event; cmd = tx.command
        for change in e.changes:
            p=change.after or change.before;key=p.subject,p.relation,p.context
            if facts.get(key)!=change.before:errors.append('fact predecessor mismatch')
            if change.after is None:facts.pop(key,None)
            else:facts[key]=change.after
        for r in (e,)+tx.works+tx.observations+tx.messages+tx.memories: records[r.ref] = r
        for name in ('state','concept','decision','material','treatment'):
            r = getattr(tx,name,None)
            if r is not None and hasattr(r,'ref'): records[r.ref] = r
        for d in getattr(tx,'demands',()):
            if d.specification.family == 'return_commitment': demands[d.owner,d.item] = d
        if cmd is not None and hasattr(cmd,'task_id') and hasattr(cmd,'actor'):
            key = cmd.actor,cmd.task_id
            units[key] = units.get(key,0)+sum(w.completed_units for w in tx.works)
        if type(tx) is AccountTransaction:
            j = tx.job; key = cmd.actor,cmd.task_id
            n = sum(w.completed_units for w in tx.works)
            if units[key] != j.paid or j.paid > j.plan.required: errors.append('payment mismatch')
            if e.outcome != WorkStatus.COMPLETED and any((tx.parts,tx.state,tx.messages,tx.concept)):
                errors.append('unfunded publication')
            # Quote independently from fixed structural tariff and local support count.
            active = j.plan.path[0]; cost = 0
            extent = 1+world.account_policy.distinction_unit*(0 if j.view is None else len(j.view.supports))
            for edge in conceptual_path(j.plan.routing_type):
                path,seats,support,at,hops,price = _route_geometry(j.plan.routing_type,active,edge.element,Polarity.ACCUMULATION,world.policy.positional_prices)
                cost += sum(hops)+extent*price; active = path[-1]
            if cost != j.correction_quote: errors.append('correction quote mismatch')
            for p in tx.parts:
                if any(r not in records for r in p.basis): errors.append('missing part source')
                if p.owner != cmd.actor or p.item != cmd.item: errors.append('part owner or referent mismatch')
                if p.role == 'origin' and p.ref != p.lineage: errors.append('bad origin')
                if p.role != 'origin' and p.lineage not in records: errors.append('missing origin')
                records[p.ref] = p
            if e.outcome != WorkStatus.COMPLETED or tx.state is None: continue
            s = tx.state; v = j.view; k = s.owner,s.loan; op = j.operation
            if op == 'hold':
                obs = records[v.terms]; terms = {p.relation:p.object for p in obs.content if p.subject == v.item and p.context == world.config.context}
                concept = records[v.concept]; d = demands.get((s.owner,s.item))
                wallet = {r.unit:r.amount for r in tx.works[-1].after}
                status = 'eligible'
                if d is None: status = 'no_demand'
                elif obs.observer != s.owner or obs.delivered_at.tick > e.when.tick: status = 'no_delivery'
                elif not concept.practiced: status = 'unavailable_operation'
                elif min(wallet[ENERGY],wallet[TIME]) < cost: status = 'insufficient_resources'
                accounts[k] = {'item':s.item,'lineage':s.lineage,'required':terms[REQUIRED], 'status':status,
                    'rows':[],'parts':{},'path':[LensContent((P.I,),(),world.config.context,PROJECTION)],'units':0,'placed':False,'placement':False}
            b = accounts[k]
            for p in tx.parts: b['parts'][p.ref] = p
            def part(role):
                return next((records[r] for r in reversed(s.parts) if records[r].role == role),None)
            inputs = []; output = [p for p in tx.parts if p.role != 'origin']; domains = (P.I,); claim = None
            if op in ('summarize','separate'): inputs = [part('held')]; claim = part('policy').requires
            elif op == 'integrate': inputs = [part('policy')]
            elif op in ('notify_terms','notify_policy'):
                inputs = [b['parts'][r] for r in tx.messages[0].based_on if r in b['parts']]
                packet = loads(tx.messages[0].content[0].object); claim = packet.requires; domains = (P.I,P.WE)
            elif op in ('wrapper','scaffold'): inputs = [part('policy_component')]; claim = part('structure').requires
            elif op == 'apply': inputs = [part('structure')]; claim = not s.permission
            elif op == 'guard': inputs = [part('structure')]; claim = part('structure').requires
            elif op == 'separate_late': inputs = [part('structure')]; claim = v.required
            if op in ('separate','separate_late','scaffold'): domains = (P.IT,P.I)
            conflicting = any(p.requires != b['required'] for p in inputs+output) or (claim is not None and claim != b['required'])
            b['path'].append(LensContent(domains,(b['lineage'],) if conflicting else (),world.config.context,PROJECTION))
            b['units'] += units[key]
            row = {'op':op,'tick':e.when.tick,'event':reftext(e.ref),'inputs':{p.ref for p in inputs},
                   'outputs':{p.ref for p in output},'claim':claim,'complete':s.complete}
            if op == 'receive':
                packet = loads(records[s.reply].content[0].object)
                row['increase'] = packet.kind == 'challenge' and packet.obligations > 1
            b['rows'].append(row)
            if op == 'decline': b['status'] = 'legitimate_refusal'
            if op in ('guard','separate_late') and b['status'] != 'legitimate_refusal':
                # Actual funding at the selected correction/block opportunity.
                first = next(x for x in world._journal if type(x) is AccountTransaction and x.command.actor == cmd.actor and x.command.task_id == cmd.task_id)
                wallet = {r.unit:r.amount for r in first.works[0].before}
                b['status'] = 'eligible' if min(wallet[ENERGY],wallet[TIME]) >= cost else 'insufficient_resources'
        if type(tx) is ReleaseTransaction and e.outcome == WorkStatus.COMPLETED:
            d = tx.decision
            if d is None and cmd.operator == 'enact': d = records[cmd.source]
            if d is None and cmd.operator in ('review','assimilate'):
                packet = loads(next(p.object for p in records[cmd.source].content if p.relation == WIRE))
                d = records[packet.decision]
            if d is not None and (d.owner,d.view.loan) in accounts:
                b = accounts[d.owner,d.view.loan];v=d.view;domains=(P.I,);bad=v.dependency and not v.required
                if cmd.operator=='enact' and d.selection.mode=='confirm':
                    domains=(P.I,P.WE);b['placed']=bad
                elif cmd.operator=='enact':bad=False
                elif cmd.operator=='review':domains=(P.IT,P.WE);bad=b['placed']
                elif cmd.operator=='assimilate':
                    current=records.get(tx.job.view.concept)
                    kept=current is not None and DEPENDENCY in current.relations
                    if b['placed'] and kept and not v.required:b['placement']=True
                    bad=b['placed'] or (kept and not v.required)
                b['path'].append(LensContent(domains,(b['lineage'],) if bad else (),world.config.context,PROJECTION))
                b['units']+=units[cmd.actor,cmd.task_id]
        if type(cmd) is WorkshopCommand and cmd.operation == 'return' and e.outcome == WorkStatus.COMPLETED:
            keys = [k for k,b in accounts.items() if k[0] == cmd.actor and b['item'] == cmd.inputs[0]]
            for k in keys:
                b = accounts.pop(k); rows = b['rows']; required = b['required']; observations = {}
                b['path'].append(LensContent((P.IT,),(),world.config.context,PROJECTION))
                b['units']+=units[cmd.actor,cmd.task_id]
                observations['forced_placement']='positive' if b['placement'] else 'negative'
                translated = [r for r in rows if r['op'] == 'summarize' and r['claim'] != required
                              and not any(x['op'] == 'separate' and x['tick'] < r['tick'] for x in rows)]
                premature = any(x['op'] == 'notify_policy' and x['tick'] > t['tick'] and x['inputs'] & t['outputs'] and x['claim'] != required
                                for t in translated for x in rows)
                observations['premature_translation'] = 'positive' if premature else 'negative'
                increases = [r for r in rows if r.get('increase')]
                constructions = [r for r in rows if r['op'] in ('wrapper','scaffold') and any(i['tick'] < r['tick'] for i in increases)]
                defensive = any(x['op'] in ('apply','guard') and x['tick'] > c['tick'] and x['inputs'] & c['outputs'] and x['claim'] != required
                                for c in constructions for x in rows)
                observations['new_defensive_structure'] = 'unassessed' if not increases else 'positive' if defensive else 'negative'
                integrated = [r for r in rows if r['op'] == 'integrate' and r['complete']]
                notes = [r for r in rows if r['op'] in ('notify_terms','notify_policy')]
                fragmented = any(a['tick'] > i['tick'] and z['tick'] > a['tick'] and a['inputs'] & i['outputs'] and z['inputs'] & i['outputs']
                                 and a['inputs']-z['inputs'] and a['claim'] != z['claim'] for i in integrated for a in notes for z in notes)
                observations['residual_fragmentation'] = 'positive' if fragmented else 'negative' if any(r['op'] == 'integrate' for r in rows) else 'unassessed'
                observations['foreclosure'] = ('negative' if any(r['op'] == 'separate_late' for r in rows) else
                    'positive' if any(r['op'] == 'guard' and r['inputs'] and r['claim'] != required for r in rows) else 'unassessed')
                if b['status'] != 'eligible': observations = {s:'unassessed' for s in observations}
                physical={r:facts[b['item'],r,world.config.context].object for r in ('condition','loan_active','owned_by','return_to')}
                endpoint='correct' if physical['condition']=='clean' and physical['loan_active'] is False and physical['owned_by']==physical['return_to'] else 'failed'
                results.append({'engagement':reftext(k[1]),'opportunity':b['status'],'signs':observations,
                     'work_units':b['units'],'endpoint':endpoint,'oig':oig_json(observe_trajectory(profiles[k[0]],b['path']))})
    return {'engagements':results,'errors':errors}


def compare(world):
    ref = reference(world); errors = list(ref['errors'])
    # This boundary only compares outputs; the independent fold above does not
    # consume traces, derived material indexes, policy or detector functions.
    live = {row['engagement']:row for g in world.account_report()['groups'] for row in g['engagements']}
    work = {reftext(t.engagement):sum(op.units for op in t.operations) for t in world.account_monitor.traces}
    if set(live) != {r['engagement'] for r in ref['engagements']}: errors.append('engagement mismatch')
    for r in ref['engagements']:
        a = live.get(r['engagement'],{})
        if work.get(r['engagement'])!=r['work_units']:errors.append(r['engagement']+': work units')
        for field in ('opportunity','endpoint','oig'):
            if a.get(field) != r[field]: errors.append(r['engagement']+': '+field)
        for sign,value in r['signs'].items():
            if a.get('signs',{}).get(sign,{}).get('observation') != value: errors.append(r['engagement']+': '+sign)
    return {'passed':not errors,'errors':errors,'reference':ref}
