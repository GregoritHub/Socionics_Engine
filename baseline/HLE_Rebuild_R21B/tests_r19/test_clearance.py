import unittest
from dataclasses import replace
from hle.clearance import ClearanceWorld
from hle.clearance_records import *
from hle.clearance_demo import *
from hle.clearance_reference import compare,evaluate
from hle.individuation_demo import make_offer,run_order
from hle.individuation_records import ASPECTS
from hle.conversion_records import ConversionCommand
from hle.codec import dumps,loads

class ClearanceBehavior(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base=prepared();cls.w=panel(clone(cls.base));cls.a=cls.w.config.actors[0]
        cls.report=cls.w.clearance_report()

    def test_thirteen_real_demands(self):
        self.assertEqual(self.report['status'],'cleared_in_scope')
        self.assertEqual({r['case'] for r in self.report['rows']},set(CASES))
        self.assertTrue(all(r['passed'] for r in self.report['rows']))
        self.assertTrue(all(r['physical_return'] and r['grounded_conditional_return'] for r in self.report['rows']))

    def test_all_five_have_eligible_baseline(self):
        self.assertEqual(set(self.report['baseline_signs'].values()),{3})
        self.assertEqual(self.report['sensitivity'],{'2':True,'3':True,'5':False})
        self.assertTrue(all(v==0 for v in self.report['window_signs'].values()))

    def test_independent_observer(self):
        r=compare(self.w);self.assertTrue(r['passed'],r['errors'])

    def test_same_material_and_revision(self):
        self.assertEqual(len(self.report['capacity_revisions']),9)
        self.assertTrue(all(r['capacity_revisions']==self.report['capacity_revisions'] for r in self.report['rows']))
        self.assertIn(self.report['material'],self.report['support_references'])

    def test_formal_increases_and_incomparability(self):
        for r in self.report['rows']:
            if r['case'].endswith('increased_requirement'):self.assertEqual(r['comparison'],'greater')
            if r['case'].endswith('changed_context_partner'):self.assertEqual(r['comparison'],'incomparable')

    def test_defensive_work_reduced_and_action_resumed(self):
        self.assertGreater(self.report['baseline_defensive_work'],0)
        self.assertEqual(sum(r['account_work']+r['optional_confirmation_work'] for r in self.report['rows']),0)
        self.assertTrue(all(r['return_events'] for r in self.report['rows']))

    def test_two_live_carriers_without_helper_substitution(self):
        self.assertTrue(all(r['two_carriers'] and r['unsupported'] for r in self.report['rows']))
        self.assertEqual({o.offer.partner for k,o in self.w._circuit_orders.items() if k.startswith('r19:')},set(self.w.config.actors[1:]))

    def test_conditioned_confirmation_not_forced_placement(self):
        required=[u for u in self.w._conversion_uses.values() if u.event in self.w._records and u.required]
        self.assertTrue(required)
        self.assertFalse(self.w.shell_monitor.errors)
        self.assertFalse(self.w.account_monitor.errors)

    def test_quiet_time_never_establishes_clearance(self):
        w=clone(self.base);begin(w)
        for i in range(100):w.execute(Tick('silence:'+str(i)))
        self.assertEqual(w.clearance_report()['status'],'incomplete')
        self.assertEqual(w.clearance_report()['rows'],[])

    def test_underthreshold_baseline_does_not_clear(self):
        w=panel(prepared(maintained=1));self.assertEqual(w.clearance_report()['status'],'incomplete')
        self.assertTrue(all(r['passed'] for r in w.clearance_report()['rows']))
        self.assertTrue(compare(w)['passed'])

    def test_suppression_reopens_and_restore_does_not_reuse_counts(self):
        w=clone(self.w);k=key(w,'suppress');fund_command(w,ConversionCommand(k,k,self.a,'restrict'))
        self.assertEqual(w.clearance_report()['status'],'unresolved')
        k=key(w,'restore');fund_command(w,ConversionCommand(k,k,self.a,'restore_access'))
        self.assertEqual(len(w._current_aspects(self.a)),8)
        self.assertEqual(w.clearance_report()['status'],'unresolved')
        self.assertTrue(any(h['status']=='cleared_in_scope' for h in w.clearance_report()['history']))
        self.assertTrue(compare(w)['passed'])

    def test_material_deletion_cannot_clear_or_execute(self):
        w=clone(self.w);material=w._capacities[self.a].material
        del w._records[material]
        self.assertEqual(w.clearance_report()['status'],'unresolved')
        with self.assertRaises(ValueError):w.execute(make_offer(w,'deleted','si'))

    def test_all_eight_capacity_withdrawals_reopen(self):
        for aspect in ASPECTS:
            with self.subTest(aspect=aspect):
                w=clone(self.w);do(w,'',self.a,'withdraw',aspect=aspect)
                self.assertEqual(w.clearance_report()['status'],'unresolved')
                self.assertNotIn(aspect,w._current_aspects(self.a))

    def test_conversion_capacity_withdrawal_reopens(self):
        w=clone(self.w);k=key(w,'withdraw-root');fund_command(w,ConversionCommand(k,k,self.a,'withdraw'))
        self.assertEqual(w.clearance_report()['status'],'unresolved');self.assertFalse(w._current_aspects(self.a))
        self.assertTrue(compare(w)['passed'])

    def test_capacity_practice_evidence_withdrawal(self):
        w=clone(self.w);c=w._aspect_caps[self.a,'si']
        w.execute(WithdrawEvidence(key(w,'withdraw-evidence'),c.practice,'practice observation withdrawn'))
        self.assertEqual(w.clearance_report()['status'],'unresolved');self.assertNotIn('si',w._current_aspects(self.a))
        self.assertTrue(compare(w)['passed'])

    def test_renewal_evidence_withdrawal(self):
        w=clone(self.w);r=w.clearance_monitor.active
        source=next(tx.event.ref for tx in reversed(w._journal) if type(tx.command) is WorkshopCommand and tx.command.operation=='return')
        w.execute(WithdrawEvidence(key(w,'withdraw-return'),source,'return observation invalidated'))
        self.assertEqual(w.clearance_report()['status'],'unresolved');self.assertEqual(len(w._current_aspects(self.a)),8)
        self.assertTrue(compare(w)['passed'])

    def test_original_maintenance_evidence_withdrawal(self):
        w=clone(self.w);t=next(t for t in w.account_monitor.traces if t.lineage==w.clearance_monitor.account_material and t.opportunity.energy>10000)
        w.execute(WithdrawEvidence(key(w,'withdraw-original'),t.operations[-1].event,'historical establishing witness invalidated'))
        self.assertEqual(w.clearance_report()['status'],'unresolved')
        self.assertTrue(compare(w)['passed'])

    def test_unrelated_evidence_does_not_reopen(self):
        w=clone(self.w);e=w.execute(Tick(key(w,'unrelated')))
        w.execute(WithdrawEvidence(key(w,'withdraw-unrelated'),e.ref,'unrelated clock observation'))
        self.assertEqual(w.clearance_report()['status'],'cleared_in_scope');self.assertTrue(compare(w)['passed'])

    def test_one_remaining_carrier_reopens(self):
        w=clone(self.w);peer=w.config.actors[2];k=key(w,'boundary')
        fund_command(w,ReleaseCommand(k,k,peer,'boundary',willingness=False))
        self.assertEqual(w.clearance_report()['status'],'unresolved');self.assertTrue(compare(w)['passed'])

    def test_displacement_to_other_carrier_fails(self):
        w=clone(self.w);a,lender,reviewer=w.config.actors;k=key(w,'boundary')
        fund_command(w,ReleaseCommand(k,k,reviewer,'boundary',willingness=False))
        item=w.clearance_monitor.original_item;borrow(w,item,lender);defensive_return(w,item)
        self.assertEqual(w._treatments[a].carrier,lender)
        self.assertEqual(w.clearance_report()['status'],'unresolved')
        self.assertEqual(w.clearance_report()['recurrence_counts']['forced_placement'],1)
        self.assertTrue(compare(w)['passed'])

    def test_three_real_recurrences_preserve_clearance_history(self):
        w=clone(self.w);old=self.report['historical_positive_assessments'];item=w.clearance_monitor.original_item
        for n in range(3):
            replenish(w);borrow(w,item,w.config.actors[1]);defensive_return(w,item)
            self.assertEqual(w.clearance_report()['status'],'recurrent' if n==2 else 'unresolved')
        r=w.clearance_report();self.assertEqual(set(r['recurrence_counts'].values()),{3})
        self.assertEqual(r['historical_positive_assessments'],old)
        self.assertTrue(any(h['status']=='cleared_in_scope' for h in r['history']))
        self.assertTrue(compare(w)['passed'])

    def test_failed_consequential_return_reopens(self):
        w=clone(self.w);item=w.release.required_items[0];borrow(w,item,w.config.actors[1])
        event=physical(w,self.a,'return',(item,))
        self.assertEqual(event.outcome,WorkStatus.FAILED);self.assertEqual(w.clearance_report()['status'],'unresolved')
        self.assertTrue(compare(w)['passed'])

    def test_changed_partner_refusal_defeats_retained_work(self):
        w=clone(self.w);f=make_offer(w,'renewed-refusal','si',held=True,all_traps=True)
        w.execute(f);do(w,f.key,f.partner,'menu');do(w,f.key,f.learner,'choose')
        do(w,'',f.partner,'boundary',flag=False);finish_order(w,f.key)
        self.assertFalse(w._records[w._circuit_orders[f.key].outcome].success)
        self.assertEqual(w.clearance_report()['status'],'unresolved');self.assertTrue(compare(w)['passed'])

    def test_helper_success_does_not_certify_own_handling(self):
        w=clone(self.base);begin(w);challenge(w,'original');fs,item=challenge(w,'selection.equal_renewal',complete=False)
        f=fs[0];do(w,'',f.helper,'support',flag=True)
        while True:
            c=CircuitController().next(w,f.key,delegate=True)
            if c is None:break
            fund_command(w,c)
        own_return(w,item);w.execute(ClearanceBoundary(key(w,'close'),self.a,'close'))
        row=w.clearance_report()['rows'][-1];self.assertFalse(row['passed']);self.assertFalse(row['own_work'])
        self.assertTrue(compare(w)['passed'])

    def test_withheld_action_and_fake_marker_cannot_clear(self):
        w=clone(self.base);begin(w);challenge(w,'original');fs,item=challenge(w,'selection.equal_renewal',complete=False)
        w.execute(ClearanceBoundary(key(w,'close'),self.a,'close'))
        row=w.clearance_report()['rows'][-1];self.assertFalse(row['physical_return']);self.assertFalse(row['passed'])

    def test_reduced_demand_is_not_counted_as_greater(self):
        w=clone(self.base);begin(w);challenge(w,'original');challenge(w,'selection.equal_renewal')
        replenish(w);case='selection.increased_requirement';f=offers(w,case)[0];f=replace(f,options=(f.options[-1],))
        item=w.clearance_monitor.original_item
        w.execute(ClearanceBoundary(key(w,'open'),self.a,'open',case,(f.key,),item));borrow(w,item,w.config.actors[1])
        w.execute(f);finish_order(w,f.key);own_return(w,item);w.execute(ClearanceBoundary(key(w,'close'),self.a,'close'))
        r=w.clearance_report()['rows'][-1];self.assertEqual(r['comparison'],'lesser');self.assertFalse(r['passed']);self.assertTrue(compare(w)['passed'])

    def test_competing_commitments_use_delivered_own_load(self):
        for case in ('obligations.equal_renewal','obligations.increased_requirement'):
            os=[o for k,o in self.w._circuit_orders.items() if k.startswith('r19:'+case+':')]
            self.assertEqual([next(x for x in o.offer.options if x.key==o.chosen).load for o in os],
                [1,2] if len(os)==2 else [1,1,1])
            self.assertLessEqual(sum(next(x for x in o.offer.options if x.key==o.chosen).load for o in os),3)

    def test_temporal_successor_cannot_run_early(self):
        w=clone(self.base);fs=offers(w,'temporal.equal_renewal')
        w.execute(OrderDependency(key(w,'dep'),fs[0].key,fs[1].key))
        for f in fs:w.execute(f);do(w,f.key,f.partner,'menu')
        with self.assertRaises(ValueError):do(w,fs[1].key,self.a,'choose')

    def test_stale_testimony_without_refresh_changes_outcome(self):
        w=clone(self.base);f=offers(w,'selection.delay_or_changed_testimony')[0]
        w.execute(f);do(w,f.key,f.partner,'menu');w.execute(PartnerShift(key(w,'shift'),f.partner,(4,9)))
        do(w,f.key,self.a,'choose');do(w,f.key,self.a,'apply')
        self.assertFalse(w._records[w._circuit_orders[f.key].outcome].success)
        # In the delivered panel the refreshed menus selected actual slot 6.
        o=self.w._circuit_orders['r19:selection.delay_or_changed_testimony:0']
        self.assertEqual(next(x for x in o.offer.options if x.key==o.chosen).start,6)

    def test_partial_choice_never_publishes(self):
        w=clone(self.base);f=make_offer(w,'partial','si',held=True,all_traps=True)
        w.execute(f);do(w,f.key,f.partner,'menu');c=replace(command(w,f.key,self.a,'choose'),work_limit=1)
        before=w._wallets[self.a];e=w.execute(c)
        self.assertEqual(e.outcome,WorkStatus.PARTIAL);self.assertIsNone(w._circuit_orders[f.key].chosen)
        self.assertEqual(before.energy-w._wallets[self.a].energy,1)
        fund_command(w,replace(c,command_id=c.command_id+':resume',work_limit=256))
        self.assertIsNotNone(w._circuit_orders[f.key].chosen)

    def test_forged_capability_rejected_by_independent_audit(self):
        w=clone(self.w)
        index=next(i for i,t in enumerate(w._journal) if getattr(t,'capacities',()))
        tx=w._journal[index];cap=tx.capacities[0];bad=replace(cap,failure=cap.practice)
        w._journal[index]=replace(tx,capacities=(bad,)+tx.capacities[1:])
        self.assertFalse(evaluate(w)['integrity_passed'])

    def test_duplicate_case_and_changed_identity_rejected(self):
        w=clone(self.w)
        with self.assertRaises(ValueError):w.execute(ClearanceBoundary(key(w,'dup'),self.a,'open','original',(),w.clearance_monitor.original_item))
        with self.assertRaises(ValueError):w.execute(ClearanceBoundary(key(w,'foreign'),w.config.actors[1],'close'))

    def test_native_world_correction_reopens(self):
        from hle.world_records import Correction
        w=clone(self.w);item=w.clearance_monitor.original_item
        target=w._heads[item,'owned_by',w.config.context]
        w.execute(Correction(key(w,'correct'),target,self.a,'prospective ownership correction'))
        self.assertEqual(w.clearance_report()['status'],'unresolved');self.assertTrue(compare(w)['passed'])

    def test_source_event_withdrawal_invalidates_descendant_capacity(self):
        w=clone(self.w);cap=w._aspect_caps[self.a,'si'];source=w._origins[cap.practice]
        w.execute(WithdrawEvidence(key(w,'withdraw-source'),source,'practice event withdrawn'))
        self.assertNotIn('si',w._current_aspects(self.a));self.assertEqual(w.clearance_report()['status'],'unresolved')
        self.assertTrue(compare(w)['passed'])

    def test_active_processing_does_not_scan_history(self):
        class NoScan(list):
            def __iter__(self):raise AssertionError('inactive journal scan')
            def __reversed__(self):raise AssertionError('inactive journal scan')
        costs=[]
        for n in (0,100,1000):
            w=clone(self.w)
            for i in range(n):w.execute(Tick('quiet:'+str(i)))
            f=make_offer(w,'bounded','si',held=True,all_traps=True);w.execute(f);do(w,f.key,f.partner,'menu')
            before=w._wallets[self.a];w._journal=NoScan(w._journal);do(w,f.key,self.a,'choose')
            costs.append(before.energy-w._wallets[self.a].energy)
        self.assertEqual(len(set(costs)),1)

class ReplayIntegrity(unittest.TestCase):
    def test_partial_checkpoint_and_exact_continuation(self):
        w=prepared(maintained=1);begin(w);challenge(w,'original')
        fs,item=challenge(w,'selection.equal_renewal',complete=False);f=fs[0];do(w,f.key,f.partner,'menu')
        c=replace(command(w,f.key,f.learner,'choose'),work_limit=1);w.execute(c)
        cp=w.checkpoint();r=ClearanceWorld.restore(cp);self.assertEqual(r.checkpoint(),cp)
        c=replace(c,command_id=c.command_id+':next',work_limit=256)
        for world in (w,r):fund_command(world,c);finish_order(world,f.key);own_return(world,item);world.execute(ClearanceBoundary('final-close',f.learner,'close'))
        self.assertEqual(w._journal,r._journal);self.assertEqual(w.clearance_report(),r.clearance_report())

    def test_recomputed_checksum_cannot_forge_outcome(self):
        w=prepared(maintained=1);begin(w);challenge(w,'original')
        cp=loads(w.checkpoint());base=cp.base.base.base.base;entries=list(base.journal)
        i=next(i for i,t in enumerate(entries) if type(t.command) is LoanDue)
        entries[i]=replace(entries[i],event=replace(entries[i].event,reason='fabricated consequence'))
        base=replace(base,journal=tuple(entries))
        cp=replace(cp,base=replace(cp.base,base=replace(cp.base.base,base=replace(cp.base.base.base,base=base))))
        with self.assertRaises(ValueError):ClearanceWorld.restore(dumps(cp))

if __name__=='__main__':unittest.main()
