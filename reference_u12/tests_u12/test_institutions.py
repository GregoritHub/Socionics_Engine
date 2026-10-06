import unittest
from dataclasses import replace
from .fixtures import *
from hle_unified.institution_audit import audit
from hle_unified.institution_policy import payload
from hle_unified.records import Governance
from hle_unified.operations import address


def trial(**kwargs):
    e,g=setup12(**kwargs);rule,p=establish12(e,g,kwargs.get("domain","tool"))
    return e,rule,p


def mutate(e,ref,**changes):
    rows=list(e.world.journal())
    for i,tx in enumerate(rows):
        if any(v.ref==ref for v in tx.versions):
            d={**e._records11[ref],**changes}
            rows[i]=replace(tx,versions=tuple(e._value11(d) if v.ref==ref else v for v in tx.versions))
    return tuple(rows)


class GenerationTests(unittest.TestCase):
    def test_proposal_is_constructed_without_finished_rule_input(self):
        e,g=setup12();p=propose12(e,g)
        self.assertEqual(p["gate"],"approval");self.assertEqual(p["symbolic"],("seq",(("act","use"),("act","care"))))
        self.assertGreater(p["considered"],0);self.assertTrue(p["patterns"])
        self.assertEqual(e.pattern_view(ALICE)[0].origin_mode,"generated")
        self.assertFalse(g.get("rules"));self.assertTrue(audit(e.world.journal())["passed"])

    def test_matched_history_ablation_changes_proposed_authority(self):
        with_pattern,g=setup12();without,h=setup12(patterns=())
        p=propose12(with_pattern,g);q=propose12(without,h)
        self.assertEqual((p["gate"],q["gate"]),("approval","self_check"))
        self.assertEqual(p["prototype"],q["prototype"]);self.assertFalse(q["patterns"])

    def test_goal_and_material_change_construct_different_work(self):
        e,g=setup12(patterns=())
        slots=slots12(e,ALICE);target=dict(slots)["target"]
        perform(e,OperationRequest("damage",ALICE,"damage",ROOM,target=target,evidence=evidence(e,ALICE,target)))
        p=propose12(e,g)
        self.assertEqual(p["symbolic"],("seq",(("act","repair"),("act","use"),("act","care"))))

    def test_second_material_context_has_same_causal_contract(self):
        e,d=active12(domain="pump")
        self.assertEqual(d["institution"]["status"],"active")
        self.assertTrue(audit(e.world.journal())["passed"])

    def test_missing_skill_or_search_budget_produces_no_rule(self):
        e,g=setup12();g=join(e,g,EVE,"join-eve")
        op12(e,"unpracticed","propose",actor=EVE,focus=g["ref"],slots=slots12(e,EVE),goal=GOAL,expect=False)
        op12(e,"tiny-search","propose",focus=g["ref"],slots=slots12(e,ALICE),goal=GOAL,limit=1,expect=False)
        self.assertFalse(any(d["kind"]=="institution" for d in e._records11.values()))

    def test_unsafe_refusal_is_preserved_without_shell_label(self):
        e,g=setup12(patterns=());p=propose12(e,g)
        encounter12(e,"danger",BOB,safe=False)
        vote=op12(e,"boundary","respond",actor=BOB,focus=p["ref"])[0]
        self.assertEqual((vote["choice"],vote["reason"]),("refuse","received_threat"))
        self.assertFalse(e.pattern_view(BOB));self.assertTrue(audit(e.world.journal())["passed"])

    def test_actual_requirement_and_partner_refusal_remain_boundaries(self):
        for key,flags,reason in (("requirement",dict(approval_required=True),"actual_requirement"),
                                 ("partner",dict(requires_partner=True,willing=False),"partner_refusal")):
            with self.subTest(key=key):
                e,g=setup12(patterns=());p=propose12(e,g)
                encounter12(e,key,BOB,**flags)
                v=op12(e,key+"-vote","respond",actor=BOB,focus=p["ref"])[0]
                self.assertEqual((v["choice"],v["reason"]),("refuse",reason))

    def test_unread_proposal_cannot_be_considered(self):
        e,g=setup12();p=propose12(e,g)
        with self.assertRaises(ValueError):op12(e,"unread","respond",actor=BOB,focus=p["ref"],read=False)
        self.assertNotIn((p["ref"],BOB),e._ballots12)

    def test_public_message_does_not_disclose_private_attribution(self):
        e,g=setup12();p=propose12(e,g);expose12(e,BOB,p["ref"])
        wire=payload(e.participant_view(BOB),p["ref"])
        for key in ("origin_encounter","patterns","origin_materials","operation","sources"):self.assertNotIn(key,wire)
        self.assertIn("permission",wire["wording"])
        value=e.world.resolve(p["ref"])
        selector=next(Selector(a.name,"detail",("attributes",str(i),"value")) for i,a in enumerate(value.attributes) if a.name=="origin_encounter")
        with self.assertRaises(ValueError):e.disclose("private-leak",BOB,p["ref"],(selector,))

    def test_hidden_fact_change_does_not_change_participant_proposal(self):
        a,g=setup12();b=InstitutionEngine.restore(a.checkpoint())
        supply(b,"unseen",actor=ALICE,target=ref("u12-tool-alice"),safe=False,deliver=False)
        self.assertEqual(a.participant_view(ALICE).snapshot,b.participant_view(ALICE).snapshot)
        p=propose12(a,g);q=propose12(b,g)
        for field in ("gate","prototype","reason","electorate","goal"):self.assertEqual(p[field],q[field])


class ConsentAndPracticeTests(unittest.TestCase):
    def test_consent_can_be_withdrawn_before_ratification(self):
        e,g=setup12();p=propose12(e,g);vote12(e,p)
        vote=e._ballots12[p["ref"],BOB]
        withdrawn=op12(e,"withdraw-vote","withdraw_vote",actor=BOB,focus=vote)[0]
        for x in e._ballots12.values():expose12(e,ALICE,x)
        op12(e,"no-longer-consented","ratify",focus=p["ref"],expect=False)
        self.assertEqual(withdrawn["choice"],"withdrawn");self.assertTrue(audit(e.world.journal())["passed"])

    def test_one_member_cannot_enact_missing_consent(self):
        e,g=setup12();p=propose12(e,g);vote12(e,p,actors=(ALICE,))
        op12(e,"alone","ratify",focus=p["ref"],expect=False)
        self.assertFalse(any(d["kind"]=="institution" for d in e._records11.values()))

    def test_responses_cannot_be_reused_for_another_proposal(self):
        e,g=setup12();p=propose12(e,g);vote12(e,p)
        q=propose12(e,g,"different-proposal")
        op12(e,"foreign-votes","ratify",focus=q["ref"],expect=False)
        self.assertFalse(any(d["kind"]=="institution" for d in e._records11.values()))

    def test_duplicate_response_is_rejected(self):
        e,g=setup12();p=propose12(e,g);vote12(e,p)
        op12(e,"duplicate","respond",actor=BOB,focus=p["ref"],expect=False)
        self.assertEqual(len(e._ballots12),2)

    def test_membership_change_invalidates_old_electorate(self):
        e,g=setup12();p=propose12(e,g);vote12(e,p)
        g=join(e,g,EVE,"new-person")
        for ref_ in e._ballots12.values():expose12(e,ALICE,ref_)
        op12(e,"old-electorate","ratify",focus=p["ref"],expect=False)
        self.assertEqual(len(e._group11(g["ref"])["members"]),3)

    def test_rule_requires_repeated_actual_work_for_maintenance(self):
        e,rule,p=trial()
        op12(e,"unearned","propose",focus=rule["ref"],intent="maintain",slots=slots12(e,ALICE),expect=False)
        run,pr=practice12(e,rule,"once");expose12(e,ALICE,pr["ref"])
        op12(e,"only-one","propose",focus=rule["ref"],intent="maintain",slots=slots12(e,ALICE),expect=False)
        op12(e,"repeat-same","record",focus=run["ref"],expect=False)
        self.assertEqual(len(e._practices12[rule["ref"].identity]),1)

    def test_paid_observed_repetition_creates_public_rule(self):
        e,d=active12();a=audit(e.world.journal())
        self.assertEqual((a["institutions"],a["maintained_rules"],a["institutional_practices"]),(1,1,2))
        self.assertEqual(e.world.head(d["institution"]["group"].identity).facet(Governance).rules,(d["institution"]["ref"],))
        self.assertEqual(d["practices"][0]["performers"],(ALICE,))

    def test_approval_wait_has_cost_cause_and_bearer(self):
        e,rule,p=trial();material=e.world.head(ref("u12-tool-bob").identity)
        app,c=op12(e,"wait","apply",actor=BOB,focus=rule["ref"],slots=slots12(e,BOB))
        self.assertEqual((c["bearer"],c["outcome"],c["rule_cause"]),(BOB,"approval_wait",p["ref"]))
        self.assertGreater(c["spent"],0);self.assertEqual(material,e.world.head(material.ref.identity))
        self.assertTrue(audit(e.world.journal())["passed"])

    def test_exact_permission_can_be_used_once(self):
        e,rule,p=trial()
        app,c=op12(e,"wait","apply",actor=BOB,focus=rule["ref"],slots=slots12(e,BOB))
        granted=op12(e,"permit","permit",focus=app["ref"])[0]
        run,practice=practice12(e,rule,"permitted-work",actor=BOB,support=granted["ref"])
        op12(e,"reuse","apply",actor=BOB,focus=rule["ref"],slots=slots12(e,BOB),support=granted["ref"],expect=False)
        self.assertEqual(run["status"],"succeeded");self.assertTrue(audit(e.world.journal())["passed"])

    def test_other_member_cannot_grant_stewards_permission(self):
        e,rule,p=trial()
        app,c=op12(e,"wait","apply",actor=BOB,focus=rule["ref"],slots=slots12(e,BOB))
        op12(e,"self-permit","permit",actor=BOB,focus=app["ref"],expect=False)
        self.assertEqual(e._heads11[app["ref"].identity],app["ref"])

    def test_personal_correction_does_not_edit_public_rule(self):
        e,d=active12();rule=d["institution"];old=e.world.resolve(rule["ref"])
        correct12(e,ALICE)
        self.assertEqual(old,e.world.head(rule["ref"].identity))
        p=propose12(e,rule,"revision",intent="review");vs=vote12(e,p,"responses")
        self.assertEqual([v["choice"] for v in vs],["accept","negotiate"])
        for v in vs:expose12(e,ALICE,v["ref"])
        op12(e,"blocked-amendment","ratify",focus=p["ref"],expect=False)
        self.assertEqual(old,e.world.head(rule["ref"].identity))

    def test_collective_correction_changes_actual_later_work(self):
        e,d=active12();rule,_,_,vs=corrected_public12(e,d)
        run,practice=practice12(e,rule,"after-revision",actor=BOB)
        self.assertEqual(rule["gate"],"self_check");self.assertEqual(run["status"],"succeeded")
        self.assertEqual(e._records11[d["institution"]["ref"]]["gate"],"approval")
        self.assertTrue(audit(e.world.journal())["passed"])

    def test_received_delay_changes_a_corrected_participants_next_response(self):
        e,rule,p=trial(patterns=(ALICE,))
        app,c=op12(e,"delay","apply",actor=BOB,focus=rule["ref"],slots=slots12(e,BOB));expose12(e,BOB,c["ref"])
        run,pr=practice12(e,rule,"one");expose12(e,ALICE,pr["ref"])
        run,pr=practice12(e,rule,"two");expose12(e,ALICE,pr["ref"])
        q=propose12(e,rule,"maintain",intent="maintain")
        v=op12(e,"learned-refusal","respond",actor=BOB,focus=q["ref"])[0]
        self.assertEqual((v["choice"],v["reason"]),("negotiate","received_avoidable_delay"))


class ContinuityTests(unittest.TestCase):
    def test_dissolution_does_not_require_new_material_search(self):
        e,rule,p=trial(patterns=())
        proposal=op12(e,"dissolution","propose",focus=rule["ref"],intent="dissolve")[0]
        self.assertEqual(proposal["considered"],0)
        vote12(e,proposal,"votes");closed=ratify12(e,proposal,"closed")
        self.assertEqual(closed["status"],"dissolved");self.assertTrue(audit(e.world.journal())["passed"])

    def test_collective_revision_resolves_dispute_and_keeps_consequence(self):
        e,d=active12();rule=d["institution"]
        app,c=op12(e,"delay","apply",actor=BOB,focus=rule["ref"],slots=slots12(e,BOB))
        dispute=op12(e,"dispute","dispute",actor=BOB,focus=c["ref"])[0];d["dispute"]=dispute["ref"]
        changed,_,_,_=corrected_public12(e,d)
        settled=e._records11[e._heads11[dispute["ref"].identity]]
        self.assertEqual((settled["status"],settled["resolution"]),("resolved",changed["ref"]))
        self.assertEqual(e._records11[c["ref"]],c);self.assertEqual(settled["bearer"],BOB)
        self.assertTrue(audit(e.world.journal())["passed"])

    def test_succession_and_founder_departure_preserve_active_institution(self):
        e,d=active12(patterns=());rule=d["institution"]
        p=propose12(e,rule,"succession",intent="succession",peer=BOB);vote12(e,p,"succession-votes")
        new=ratify12(e,p,"new-steward")
        g=work(e,"founder-leaves","leave",focus=new["group"])[0]
        run,pr=practice12(e,new,"continuing-service",actor=BOB)
        self.assertEqual(g["owner"],BOB);self.assertNotIn(ALICE,g["members"])
        self.assertEqual(run["status"],"succeeded");self.assertTrue(audit(e.world.journal())["passed"])

    def test_newcomer_teaching_and_assent_do_not_grant_skill(self):
        e,d=active12(patterns=());rule=d["institution"]
        g=join(e,e._records11[e._heads11[rule["group"].identity]],EVE,"newcomer")
        lesson=op12(e,"teach","teach",focus=rule["ref"],peer=EVE)[0]
        learned=op12(e,"learn","learn",actor=EVE,focus=lesson["ref"])[0]
        assent=op12(e,"assent","assent",actor=EVE,focus=learned["ref"])[0]
        self.assertTrue(assent["permission_active"])
        self.assertFalse(e.participant_view(EVE).can_use(ref("u11-primitive-use"),ROOM))
        op12(e,"no-skill","apply",actor=EVE,focus=rule["ref"],slots=slots12(e,EVE),expect=False)
        train(e,EVE,("use","care"));run,pr=practice12(e,rule,"own-practice",actor=EVE)
        self.assertEqual(run["status"],"succeeded");self.assertTrue(audit(e.world.journal())["passed"])

    def test_joining_alone_does_not_assent_to_public_rule(self):
        e,rule,p=trial(patterns=());join(e,e._records11[e._heads11[rule["group"].identity]],EVE,"new")
        op12(e,"no-assent","apply",actor=EVE,focus=rule["ref"],slots=slots12(e,EVE),expect=False)
        self.assertNotIn((rule["ref"].identity,EVE),e._assents12)

    def test_teaching_cannot_be_read_as_another_persons_understanding(self):
        e,rule,p=trial();lesson=op12(e,"teach","teach",focus=rule["ref"],peer=BOB)[0]
        op12(e,"foreign-learner","learn",focus=lesson["ref"],expect=False)

    def test_dispute_records_actual_bearer_without_erasing_rule(self):
        e,rule,p=trial();app,c=op12(e,"delay","apply",actor=BOB,focus=rule["ref"],slots=slots12(e,BOB))
        dispute=op12(e,"dispute","dispute",actor=BOB,focus=c["ref"])[0]
        self.assertEqual(dispute["bearer"],BOB);self.assertEqual(e._heads11[rule["ref"].identity],rule["ref"])
        op12(e,"foreign-dispute","dispute",focus=c["ref"],expect=False)
        self.assertTrue(audit(e.world.journal())["passed"])

    def test_assent_withdrawal_blocks_ready_work_preserving_cost_and_duty(self):
        e,rule,p=trial(patterns=())
        run=op12(e,"run","apply",focus=rule["ref"],slots=slots12(e,ALICE))[0]
        work(e,"consent","accept",focus=run["ref"])
        selection,run=select(e,run,"next")
        e.enact("enact",ALICE,"physical",selection["ref"]);e.advance("pay",ALICE,"physical",100000)
        before=e.wallet(ALICE)["energy"];assent=e._assents12[rule["ref"].identity,ALICE]
        withdrawn=op12(e,"withdraw","withdraw_assent",focus=assent)[0]
        e.commit("commit",ALICE,"physical")
        self.assertEqual(e.job_status(ALICE,"physical")["failure"],"stale_dependency")
        self.assertLess(e.wallet(ALICE)["energy"],before);self.assertEqual(withdrawn["status"],"open")
        self.assertEqual(e._records11[e._duties11[run["ref"].identity,ALICE]]["status"],"open")

    def test_dissolution_preserves_outstanding_work_and_history(self):
        e,rule,p=trial(patterns=())
        run=op12(e,"run","apply",focus=rule["ref"],slots=slots12(e,ALICE))[0]
        duty=work(e,"consent","accept",focus=run["ref"])[0]
        p=propose12(e,rule,"dissolve",intent="dissolve");vote12(e,p,"dissolve-votes")
        closed=ratify12(e,p,"dissolved")
        self.assertEqual(closed["status"],"dissolved");self.assertEqual(e._records11[duty["ref"]]["status"],"open")
        op12(e,"after","apply",focus=closed["ref"],slots=slots12(e,ALICE),expect=False)
        work(e,"old-work","select",focus=run["ref"],expect=False)
        self.assertTrue(audit(e.world.journal())["passed"])


class IntegrityTests(unittest.TestCase):
    def test_partial_proposal_restores_and_continues_exactly(self):
        e,g=setup12();slots=slots12(e,ALICE)
        r=InstitutionRequest("partial",ALICE,"propose",ROOM,CUE5,g["ref"],encounter=current_encounter(e,ALICE),slots=slots,goal=GOAL)
        e.start("start",r);e.advance("part",ALICE,"partial",7);restored=InstitutionEngine.restore(e.checkpoint())
        for engine in (e,restored):engine.advance("rest",ALICE,"partial",100000);engine.commit("commit",ALICE,"partial")
        self.assertEqual(e.checkpoint(),restored.checkpoint())

    def test_changed_actor_evidence_invalidates_paid_proposal(self):
        e,g=setup12();r=InstitutionRequest("pending",ALICE,"propose",ROOM,CUE5,g["ref"],encounter=current_encounter(e,ALICE),slots=slots12(e,ALICE),goal=GOAL)
        e.start("start",r);e.advance("part",ALICE,"pending",7);expose12(e,ALICE,BOB_CARE)
        e.advance("rest",ALICE,"pending",100000);e.commit("commit",ALICE,"pending")
        self.assertEqual(e.job_status(ALICE,"pending")["failure"],"received_evidence_changed")

    def test_exhaustion_retains_partial_work_without_proposal(self):
        e,g=setup12(budget=30000)
        r=InstitutionRequest("exhausted",ALICE,"propose",ROOM,CUE5,g["ref"],encounter=current_encounter(e,ALICE),slots=slots12(e,ALICE),goal=GOAL,limit=1000000)
        e.start("start",r);e.advance("spend",ALICE,"exhausted",10000000)
        self.assertEqual(e.wallet(ALICE)["energy"],0);self.assertEqual(e.job_status(ALICE,"exhausted")["status"],"partial")
        self.assertFalse(any(d["kind"]=="proposal" for d in e._records11.values()))

    def test_cancelled_institutional_work_preserves_spending(self):
        e,g=setup12();r=InstitutionRequest("cancel",ALICE,"propose",ROOM,CUE5,g["ref"],encounter=current_encounter(e,ALICE),slots=slots12(e,ALICE),goal=GOAL)
        e.start("start",r);e.advance("part",ALICE,"cancel",11);before=e.wallet(ALICE)["energy"]
        e.cancel("cancel",ALICE,"cancel")
        self.assertEqual(e.wallet(ALICE)["energy"],before);self.assertEqual(e.job_status(ALICE,"cancel")["spent"],11)
        self.assertTrue(audit(e.world.journal())["passed"])

    def test_u11_adoption_preserves_history_and_continued_work(self):
        e=setup11();other=InstitutionEngine.adopt(e)
        self.assertEqual(e.world.checkpoint(),other.world.checkpoint());self.assertEqual(e.access.checkpoint(),other.access.checkpoint())
        for engine in (e,other):repair_group(engine)
        self.assertEqual(e.world.checkpoint(),other.world.checkpoint());self.assertEqual(e.access.checkpoint(),other.access.checkpoint())

    def test_all_types_keep_lawful_routes_and_different_costs(self):
        from hle.model_a import TYPES
        prices=set()
        for tim in TYPES:
            with self.subTest(tim=tim):
                e,g=setup12(patterns=(),tim=tim);propose12(e,g)
                self.assertTrue(audit(e.world.journal())["passed"])
                prices.add(e.job_status(ALICE,"proposal")["route_execute"])
        self.assertGreater(len(prices),1)

    def test_independent_raw_audit_rejects_unconsented_rule(self):
        e,rule,p=trial()
        with self.assertRaises(ValueError):audit(mutate(e,rule["ref"],gate="self_check"))

    def test_independent_raw_audit_rejects_wrong_consequence_bearer(self):
        e,rule,p=trial();app,c=op12(e,"delay","apply",actor=BOB,focus=rule["ref"],slots=slots12(e,BOB))
        with self.assertRaises(ValueError):audit(mutate(e,c["ref"],bearer=EVE))

    def test_generated_history_cannot_be_minted_as_a_declaration(self):
        e,g=setup12()
        forged=record(address("u12.institution","forged"),"Forged rule",{"status":"active"})
        with self.assertRaises(ValueError):e.declare("forged",(forged,))

    def test_modified_checkpoint_is_rejected(self):
        from hle_unified.compact import seal,unseal
        e,rule,p=trial();data=unseal(e.checkpoint(),e.SCHEMA);data["access"]="tampered"
        with self.assertRaises(ValueError):InstitutionEngine.restore(seal(e.SCHEMA,data))


if __name__=="__main__":unittest.main()
