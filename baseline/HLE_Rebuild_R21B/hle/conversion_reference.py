"""Independent raw-journal R17 witnesses and work/lineage reconstruction.

Does not call selection, inference, release_view, a monitor, or conversion
internals. In particular, a phase name or correct endpoint is never sufficient.
"""
from .contracts import WorkStatus, Observation
from .world_records import ENERGY, TIME, Credit
from .autonomy_records import WorkshopCommand
from .compensation_records import ReleaseTransaction, DEPENDENCY, REQUIRED, CONFIRMED
from .conversion_records import ConversionTransaction
from .development_contracts import Treatment

def addr(r): return None if r is None else r.key+'@'+str(r.revision)

def evaluate(world):
    records={}; balances={b.actor:(b.energy,b.time) for b in world.config.wallets}
    studies={}; rules={}; capacities={}; uses={}; pending={}; access={}; treatments={}; materials={}
    paid={}; facts={}; errors=[]; rows=[]; returns=[]; choices=[]; trials=[]; recalls=[]; total=0
    successes={}; failures={}; last_context={}; care={}; native={}; original_concepts={}; inspections={}
    worker=world.config.actors[0]
    def check(condition, message):
        if not condition: errors.append(message)
    def local(o,item): return {p.relation:p.object for p in o.content if p.subject==item}
    for tx in world._journal:
        e=tx.event; c=tx.command
        for cause in e.causes: check(cause.event in records,'missing earlier causal event')
        records[e.ref]=e
        for change in e.changes:
            p=change.before or change.after; key=(p.subject,p.relation,p.context)
            check(facts.get(key)==change.before,'physical before mismatch')
            if change.after is None: facts.pop(key,None)
            else: facts[key]=change.after
        for w in tx.works:
            before={a.unit:a.amount for a in w.before};after={a.unit:a.amount for a in w.after}
            charged={a.unit:a.amount for a in w.charged};credit={a.unit:a.amount for a in w.credited}
            check((before[ENERGY],before[TIME])==balances[w.owner],'wallet before mismatch')
            check(all(before[u]+credit.get(u,0)-charged.get(u,0)==after[u] for u in (ENERGY,TIME)),'unbalanced work')
            if type(c) is not Credit: check(all(charged.get(u,0)==w.completed_units for u in (ENERGY,TIME)),'work unit mismatch')
            else: check(credit=={ENERGY:c.energy,TIME:c.time} and not charged,'credit mismatch')
            balances[w.owner]=(after[ENERGY],after[TIME]);total+=charged.get(ENERGY,0);records[w.ref]=w
        for r in tx.observations+tx.messages+tx.memories: records[r.ref]=r
        for attr in ('state','material','treatment','decision','concept','study','candidate','capacity','use'):
            value=getattr(tx,attr,None)
            if value is not None and hasattr(value,'ref'): records[value.ref]=value
        for r in getattr(tx,'parts',()): records[r.ref]=r
        m=getattr(tx,'material',None)
        if m is not None: materials[m.ref]=m
        t=getattr(tx,'treatment',None)
        if t is not None:
            old=treatments.get(t.treating_actor);m=materials.get(t.lineage)
            check(m is not None and m.origin_event in t.source_events and m.owner==t.origin_actor,'material origin lost')
            if old is not None: check(t.previous_revision==old.ref and t.lineage==old.lineage and set(old.source_events)<=set(t.source_events),'treatment history broken')
            check(all(r in records for r in t.selection_evidence+t.work_refs+t.consequences),'treatment source missing')
            treatments[t.treating_actor]=t
        if type(tx) is ConversionTransaction:
            j=tx.job;actor=c.actor;key=(actor,c.task_id);spend=sum(w.completed_units for w in tx.works)
            check(j.paid==paid.get(key,0)+spend and j.paid<=j.plan.required,'conversion paid progression')
            paid[key]=j.paid
            check(all(r in records for r in j.basis),'conversion basis missing')
            emitted=(tx.study,tx.candidate,tx.capacity,tx.use,tx.treatment,tx.concept)
            if e.outcome!=WorkStatus.COMPLETED:
                check(not any(emitted),'unpaid conversion output')
                continue
            check(j.paid==j.plan.required,'completed conversion underfunded')
            op=j.operation;s=studies.get(actor);r=None if s is None or s.candidate is None else rules[s.candidate]
            row={'event':addr(e.ref),'tick':e.when.tick,'operation':op,'units':j.plan.required,
                 'material':None if s is None else addr(s.material)}
            if op=='release':
                st=tx.study;m=materials[st.material];original=records[m.concept_at_origin]
                check(st.concept_origin==m.concept_at_origin and original.owner==actor and DEPENDENCY in original.relations,'release source not original')
                check(st.account_material in records and tx.concept is None and tx.treatment.treatment==Treatment.HOLD,'release substituted or deleted material')
                original_concepts[actor]=original
                row['preserved']=True
            elif op=='context':
                st=tx.study
                check(all(type(records.get(x)) is Observation and records[x].observer==actor for x in st.context_sources),'foreign context')
                check(st.context_sources==j.basis[2:],'context published unprocessed sources')
                values={p.object for x in st.context_sources for p in records[x].content if p.relation==REQUIRED}
                last_context[actor]=values;row['contrasting_conditions']=values=={False,True}
            elif op=='reorganize':
                cand=tx.candidate
                check(last_context.get(actor)=={False,True} and dict(cand.table)=={False:False,True:True},'organization not justified by contrasting terms')
                check(not cand.practice and not cand.covered and tx.capacity is None,'insight awarded practiced capacity')
                check(cand.sources==s.context_sources and cand.material==s.material,'candidate rewrote source')
                successes[actor]=[];failures[actor]=[];row['unfinished']=True
            elif op in ('try','recall'):
                u=tx.use;obs=records[u.terms];f=local(obs,u.item);rr=rules[u.rule]
                check(type(obs) is Observation and obs.observer==actor,'use did not process owned terms')
                check(f.get(REQUIRED)==u.required and dict(rr.table)[f[REQUIRED]]==u.required,'use ignored its rule or terms')
                check(f.get('condition')=='clean' and f.get('owned_by')==actor and f.get('return_due') is True,'unusable application')
                check(u.material==rr.material and u.loan==j.view.loan,'use lineage or scope changed')
                if 'fresh_own_inspection' in rr.preconditions:
                    check(inspections.get((actor,u.item))==u.terms,'learned inspection guard bypassed')
                if op=='recall':
                    cap=capacities.get(actor)
                    check(cap is not None and cap.current and u.capacity==cap.ref and cap.rule==u.rule,'stale or missing retained capacity')
                    check(access.get(actor,world.conversion_policy.material_access),'recall lacked material access')
                    recalls.append({'event':addr(e.ref),'item':u.item.key,'required':u.required,'capacity':addr(u.capacity),'material':addr(u.material)})
                else:
                    check(world.conversion_policy.practice and s.active and not s.paused,'unavailable practice')
                    check(u.rule==s.candidate and u.capacity is None,'trial substituted a retained result')
                    pending[actor]=u
                uses[actor,u.loan]=u
                row.update(item=u.item.key,required=u.required)
            elif op=='reflect':
                u=pending.pop(actor);obs=records[j.result];result=records[obs.source];f=local(obs,u.item)
                check(obs.observer==actor and result.action=='r14.return' and actor in result.actors,'not own return feedback')
                ok=(result.outcome==WorkStatus.COMPLETED and f.get('loan_active') is False
                    and f.get('owned_by')==f.get('return_to') and f.get('condition')=='clean'
                    and f.get(CONFIRMED) is u.required)
                (successes[actor] if ok else failures[actor]).append((obs.ref,u.required,u.loan))
                cand=tx.candidate
                check(cand.practice==tuple(a for a,_,_ in successes[actor]),'practice evidence fabricated')
                check(cand.failures==tuple(a for a,_,_ in failures[actor]),'failed practice erased')
                check(set(cand.covered)=={b for _,b,_ in successes[actor]},'coverage awarded without consequence')
                check(cand.previous==r.ref and cand.table==r.table and tx.capacity is None,'reflection improperly finalized')
                check(cand.preconditions==(r.preconditions if ok else tuple(sorted(set(r.preconditions)|{'fresh_own_inspection'}))),'failed consequence did not revise usable procedure')
                trials.append({'event':addr(e.ref),'item':u.item.key,'loan':addr(u.loan),'required':u.required,
                    'success':ok,'outcome':result.outcome.value,'observation':addr(obs.ref),
                    'native_use':bool(native.get((actor,u.item))),'care':bool(care.get((actor,u.item)))})
                uses.pop((actor,u.loan),None);row.update(covered=list(cand.covered),success=ok)
            elif op=='retain':
                cap=tx.capacity;practice=successes.get(actor,[])
                check({b for _,b,_ in practice}=={False,True} and len({l for _,_,l in practice})>=2,'missing distinct branch practice')
                check(cap.rule==r.ref and cap.material==s.material and cap.practice==r.practice,'capacity lost material or practice')
                check(world.conversion_policy.retention and cap.current and tx.treatment.treatment==Treatment.REOWN,'retention unavailable or externally owned')
                check(all(x in records and records[x].owner==actor for x in cap.acquisition),'unpaid acquisition')
                check(tx.concept is not None and DEPENDENCY not in tx.concept.relations,'concept unchanged at retention')
                row.update(reowned=True,practice=[addr(x) for x in cap.practice])
            elif op=='archive': check(tx.capacity is None and not tx.study.active,'no-retention control retained capacity')
            elif op=='withdraw': check(not tx.capacity.current and tx.capacity.previous==capacities[actor].ref,'withdrawal erased provenance')
            elif op in ('restrict','restore_access'): access[actor]=op=='restore_access'
            if tx.study is not None: studies[actor]=tx.study
            if tx.candidate is not None: rules[tx.candidate.ref]=tx.candidate
            if tx.capacity is not None: capacities[actor]=tx.capacity
            rows.append(row)
        if type(tx) is ReleaseTransaction and tx.decision is not None:
            d=tx.decision;v=d.view;obs=records[v.terms];f=local(obs,v.item)
            expected=DEPENDENCY in records[v.concept].relations if v.concept else False
            st=studies.get(d.owner);u=uses.get((d.owner,v.loan));using=False
            if st is not None:
                expected=DEPENDENCY in original_concepts[d.owner].relations
                if u is not None and u.terms==v.terms and access.get(d.owner,world.conversion_policy.material_access):
                    cap=capacities.get(d.owner)
                    using=((u.capacity is None and st.active and not st.paused and st.candidate==u.rule)
                        or (u.capacity is not None and cap is not None and cap.current and cap.ref==u.capacity))
                    if using: expected=u.required
            check(v.dependency==expected and v.required==f[REQUIRED],'release bypassed material processing')
            if d.owner==worker:
                choices.append({'event':addr(e.ref),'item':v.item.key,'loan':addr(v.loan),'required':v.required,
                    'mode':d.selection.mode,'carrier':None if d.selection.carrier is None else d.selection.carrier.key,
                    'retained_use':using and u.capacity is not None,'practice_use':using and u.capacity is None})
        if type(c) is WorkshopCommand and c.actor==worker:
            if c.operation=='inspect' and e.outcome==WorkStatus.COMPLETED:
                obs=next((o for o in tx.observations if o.observer==c.actor and o.source==e.ref),None)
                if obs is not None: inspections[c.actor,c.inputs[0]]=obs.ref
            if c.operation=='use' and e.outcome==WorkStatus.COMPLETED: native[c.actor,c.inputs[1]]=e.ref
            if c.operation=='clean' and e.outcome==WorkStatus.COMPLETED: care[c.actor,c.inputs[0]]=e.ref
            if c.operation=='return':
                f={rel:p.object for (item,rel,_),p in facts.items() if item==c.inputs[0]}
                returns.append({'event':addr(e.ref),'item':c.inputs[0].key,'outcome':e.outcome.value,
                    'correct':e.outcome==WorkStatus.COMPLETED and f.get('loan_active') is False and f.get('owned_by')==f.get('return_to') and f.get('condition')=='clean',
                    'owner':getattr(f.get('owned_by'),'key',None)})
    check(all(balances[a]==(world._wallets[a].energy,world._wallets[a].time) for a in balances),'final wallet mismatch')
    return {'schema':'r17-independent-v1','passed':not errors,'errors':errors,'events':len(world._journal),
        'work_units':total,'operations':rows,'practice':trials,'recalls':recalls,'choices':choices,'returns':returns,
        'current_capacity':worker in capacities and capacities[worker].current,
        'material_preserved':all(m.ref in records and m.concept_at_origin in records and m.origin_event in records for m in materials.values()),
        'historical_treatment_count':sum(getattr(tx,'treatment',None) is not None for tx in world._journal),
        'clearance':'unassessed; R19 gate not executed'}
