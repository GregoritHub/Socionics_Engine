"""Release evidence checks from raw transactions, independent of the driver."""
from hle.clearance_reference import compare
from hle.closure_reference import compare as closure_compare
from hle.contracts import WorkStatus
from hle.world_records import Credit, ENERGY, TIME
from hle.autonomy_records import WorkshopCommand
from hle.conversion_records import ConversionTransaction
from hle.individuation_records import CircuitTransaction
from hle.reconciliation_records import AccountTransaction
from hle.compensation_records import ReleaseTransaction


def resource_audit(w,allow_credits=False):
    balances={x.actor:{ENERGY:x.energy,TIME:x.time} for x in w.config.wallets}
    charged={a:{ENERGY:0,TIME:0} for a in balances}
    credited={a:{ENERGY:0,TIME:0} for a in balances}
    errors=[];unfinished={};credits=[]
    for tx in w._journal:
        if isinstance(tx.command,Credit):credits.append(tx.event.ref.key)
        for r in tx.works:
            before={x.unit:x.amount for x in r.before};after={x.unit:x.amount for x in r.after}
            debit={x.unit:x.amount for x in r.charged};credit={x.unit:x.amount for x in r.credited}
            if before!=balances[r.owner]:errors.append('wallet predecessor: '+r.ref.key)
            for unit in (ENERGY,TIME):
                if after[unit]!=before[unit]+credit.get(unit,0)-debit.get(unit,0) or after[unit]<0:
                    errors.append('conservation: '+r.ref.key)
                charged[r.owner][unit]+=debit.get(unit,0);credited[r.owner][unit]+=credit.get(unit,0)
            balances[r.owner]=after
        c=tx.command
        j=next((getattr(tx,name,None) for name in ('job','workshop_job','decision_job','task')
                if getattr(tx,name,None) is not None),None)
        actor=getattr(c,'actor',getattr(getattr(c,'action',None),'actor',None))
        task=getattr(c,'task_id',None)
        if actor is not None and task is not None and j is not None:
            k=actor.key+':'+task
            if tx.event.outcome in (WorkStatus.PARTIAL,WorkStatus.DEFERRED):
                required=getattr(j,'required',getattr(getattr(j,'plan',None),'required',None))
                unfinished[k]={'last_event':tx.event.ref.key,'paid':getattr(j,'paid',getattr(j,'completed',None)),
                               'required':required,'status':tx.event.outcome.value}
            else:unfinished.pop(k,None)
    for actor,values in balances.items():
        if (values[ENERGY],values[TIME])!=(w._wallets[actor].energy,w._wallets[actor].time):
            errors.append('final balance: '+actor.key)
    if not allow_credits and credits:errors.append('unexpected allocation')
    return {'passed':not errors,'errors':errors,'credit_events':credits,
            'charged':{a.key:{str(k):v for k,v in values.items()} for a,values in charged.items()},
            'credited':{a.key:{str(k):v for k,v in values.items()} for a,values in credited.items()},
            'unfinished_jobs':unfinished,'unfinished_count':len(unfinished)}


def renewal_audit(w,rows):
    results=[]
    for row in rows:
        events=w._journal[row['start']:row['stop']]
        orders={}
        for tx in events:
            if isinstance(tx,CircuitTransaction) and tx.order is not None:
                orders[tx.order.offer.key]=tx.order
        actual=[orders.get(k) for k in row['orders']]
        own=bool(actual) and all(o is not None and o.closed and o.credited
            and o.performer==o.offer.learner and o.outcome is not None
            and w._records[o.outcome].success and len(o.uses)==8 for o in actual)
        uses=[t.use for t in events if isinstance(t,ConversionTransaction) and t.use is not None
              and t.use.item.key==row['item']]
        returns=[t for t in events if isinstance(t.command,WorkshopCommand)
            and t.command.operation=='return' and t.command.inputs[0].key==row['item']
            and t.event.outcome==WorkStatus.COMPLETED and t.command.actor==w.config.actors[0]]
        defense=sum(r.completed_units for t in events for r in t.works
            if isinstance(t,AccountTransaction) or (isinstance(t,ReleaseTransaction)
                and t.job.view is not None and not t.job.view.required))
        ok=own and bool(uses) and bool(returns) and defense==0
        results.append({**row,'eligible':own and bool(uses),'own_return':bool(returns),
                        'defensive_work':defense,'passed':ok})
    families=[x['case'].split('.')[0] for x in results]
    changes=sum(x!=y for x,y in zip(families,families[1:]))
    return {'passed':len(results)>=100 and changes>=2 and all(r['passed'] for r in results),
            'eligible':sum(x['eligible'] for x in results),'demand_changes':changes,'rows':results}


def audit(w,meta):
    raw=compare(w)
    return {'raw_clearance':raw,'resources':resource_audit(w),
            'sustained':renewal_audit(w,meta['opportunities'])}
