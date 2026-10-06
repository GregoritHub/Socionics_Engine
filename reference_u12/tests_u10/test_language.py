import unittest
from dataclasses import replace
from tests_u10.fixtures import *
from hle_unified.language_audit import audit
from hle_unified.development import record


class MeaningCircuit(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.e,cls.d=circuit10()

    def test_unknown_term_generates_delivered_question(self):
        self.assertEqual(self.d["unknown"]["status"],"clarification")
        self.assertEqual(self.d["unknown"]["reason"],"unknown_term")
        self.assertEqual(self.d["question"]["meaning"][0],"clarify")

    def test_two_distinct_demonstrations_stabilize(self):
        self.assertEqual([x["status"] for x in self.d["learned"]],["tentative","stable"])
        self.assertEqual(self.d["learned"][-1]["program"],self.d["teacher"]["entry"]["program"])

    def test_speech_does_not_copy_teacher_capacity(self):
        self.assertFalse(any(x["kind"]=="capacity" for x in self.e.composition_view(BOB)))
        self.assertTrue(all(x["actor"]==BOB for x in self.e.composition_view(BOB)))

    def test_received_composition_changes_material_behavior(self):
        run=self.d["first"]
        self.assertEqual(run["trace"],("repair","use","care"))
        self.assertEqual(run["status"],"succeeded")
        self.assertEqual(attrs(self.e.world.head(ref("bob-first-care").identity))["consumed"],1)
        self.assertEqual(attrs(self.e.world.head(ref("bob-first-repair").identity))["consumed"],1)

    def test_novel_combination_of_known_word_and_actions_executes(self):
        run=self.d["composed"]
        self.assertEqual(run["trace"],("repair","use","care","use","care"))
        self.assertEqual(thaw(run["state"])["progress"]["uses"],2)
        self.assertEqual(run["status"],"succeeded")

    def test_failure_is_real_and_preserved(self):
        run=self.d["failed"]
        self.assertEqual(run["status"],"failed")
        self.assertEqual(run["failure_kind"],"observed_counterexample")
        self.assertEqual(self.e.world.head(ref("bob-fragile").identity).facet(Material).condition,"damaged")
        self.assertEqual(attrs(self.e.world.head(ref("bob-fragile-care").identity))["consumed"],0)

    def test_counterexample_challenges_instead_of_agreeing(self):
        self.assertEqual(self.d["challenged"]["status"],"challenged")
        self.assertIsNone(self.d["challenged"]["program"])
        self.assertEqual(self.d["report_received"]["assessment"],"contradicted")

    def test_repair_needs_stable_observed_distinction(self):
        entries=self.d["revision"]["learned"]
        self.assertEqual([x["status"] for x in entries],["tentative","stable"])
        self.assertEqual(entries[-1]["split"],("eq",("field","target","max_wear"),1))
        self.assertEqual(entries[-1]["ref"].identity,self.d["learned"][0]["ref"].identity)

    def test_later_fragile_and_ordinary_returns_differ(self):
        fragile,ordinary=self.d["returns"]
        self.assertEqual(fragile["trace"],("repair","use","repair"))
        self.assertEqual(ordinary["trace"],("repair","use","care"))
        self.assertEqual((fragile["status"],ordinary["status"]),("succeeded","succeeded"))

    def test_historical_meaning_remains_exact(self):
        old=self.d["learned"][-1]
        self.assertEqual(unpack(self.e.world.resolve(old["ref"]))["program"],old["program"])
        self.assertEqual(self.d["first"]["trace"],("repair","use","care"))

    def test_raw_accounting_and_language_lineage(self):
        result=audit(self.e.world.journal())
        self.assertTrue(result["passed"])
        self.assertEqual(result["meaning_repairs"],1)
        self.assertEqual(result["charged_energy"],result["charged_time"])
        self.assertGreater(result["practical_responses"],3)

    def test_forged_practical_meaning_fails_raw_audit(self):
        rows=list(self.e.world.journal())
        for i,tx in enumerate(rows):
            candidates=[v for v in tx.versions if v.ref.identity.namespace=="u10.candidate"]
            if not candidates:continue
            old=candidates[0];d=unpack(old);d["program"]=("act","use")
            forged=replace(old,attributes=record(old.ref,old.label,d).attributes)
            rows[i]=replace(tx,versions=tuple(forged if v.ref==old.ref else v for v in tx.versions));break
        with self.assertRaises(ValueError):audit(rows)


class CommunicationControls(unittest.TestCase):
    def test_one_success_cannot_coin_vocabulary(self):
        e,cap=trained9(setup10())
        perform(e,LanguageRequest("early",ALICE,"coin",ROOM,CUE5,focus=cap["ref"]),limit=100000)
        self.assertEqual(e.job_status(ALICE,"early")["status"],"failed")
        self.assertFalse(e.language_view(ALICE))

    def test_delivery_alone_is_not_understanding(self):
        e,t=teacher10();slots=reveal10(e,"bob-first",actor=ALICE)
        m=work10(e,"send-unread","send",peer=BOB,act="request",body=("word",t["entry"]["term"]),slots=slots,goal=GOAL)[-1]
        deliver10(e,m,read=False)
        with self.assertRaises(ValueError):e.start("read-required",LanguageRequest("no-read",BOB,"interpret",ROOM,CUE5,focus=m["ref"]))
        self.assertEqual(e.language_view(BOB),())

    def test_wording_and_intention_are_distinct_from_interpretation(self):
        e,t=teacher10();m,i=request10(e,t["entry"])
        intention=next(x for x in e.language_view(ALICE) if x["kind"]=="intention" and x["message"]==m["ref"])
        self.assertEqual(intention["meaning"],t["entry"]["program"])
        self.assertEqual(dict(codec.loads(m["payload"]))["body"],("word",t["entry"]["term"]))
        self.assertEqual(i["meaning"],())

    def test_private_intention_cannot_be_disclosed_to_listener(self):
        e,t=teacher10();m,_=request10(e,t["entry"])
        intention=next(x for x in e.language_view(ALICE) if x["kind"]=="intention")
        with self.assertRaises(ValueError):show(e,BOB,intention["ref"])
        with self.assertRaises(ValueError):show(e,EVE,m["ref"])

    def test_message_metadata_does_not_leak_speaker_sources(self):
        e,t=teacher10();m,_=request10(e,t["entry"])
        v=e.world.resolve(m["ref"])
        i=next(i for i,a in enumerate(v.attributes) if a.name=="sources.0")
        with self.assertRaises(ValueError):e.disclose("private-metadata",BOB,m["ref"],(Selector("sources.0","detail",("attributes",str(i),"value")),))

    def test_unread_demonstration_cannot_teach(self):
        e,t=teacher10()
        m=work10(e,"demo","send",peer=BOB,act="demonstration",focus=t["runs"][0]["ref"],term=t["entry"]["term"])[0]
        deliver10(e,m)
        perform(e,LanguageRequest("learn",BOB,"learn",ROOM,CUE5,focus=m["ref"]),limit=100000)
        self.assertEqual(e.job_status(BOB,"learn")["status"],"failed")
        self.assertEqual(e.language_view(BOB),())

    def test_repeated_same_events_cannot_stabilize(self):
        e,t=teacher10();teach10(e,t["entry"],t["runs"][:1])
        m=work10(e,"duplicate-demo","send",peer=BOB,act="demonstration",focus=t["runs"][0]["ref"],term=t["entry"]["term"])[0]
        deliver10(e,m)
        perform(e,LanguageRequest("duplicate-learn",BOB,"learn",ROOM,CUE5,focus=m["ref"]),limit=100000)
        self.assertEqual(e.job_status(BOB,"duplicate-learn")["status"],"failed")
        self.assertEqual(e._lex(BOB,ROOM,ALICE)[t["entry"]["term"]]["status"],"tentative")

    def test_partial_processing_publishes_no_interpretation(self):
        e,t=teacher10();slots=reveal10(e,"bob-first",actor=ALICE)
        m=work10(e,"partial-message","send",peer=BOB,act="request",body=("word",t["entry"]["term"]),slots=slots,goal=GOAL)[-1]
        deliver10(e,m)
        r=LanguageRequest("partial",BOB,"interpret",ROOM,CUE5,focus=m["ref"])
        e.start("partial-start",r);before=e.wallet(BOB)
        e.advance("partial-work",BOB,"partial",1)
        self.assertEqual(e.language_view(BOB),())
        self.assertEqual(e.wallet(BOB)["energy"],before["energy"]-1)
        with self.assertRaises(ValueError):e.commit("premature",BOB,"partial")
        other=LanguageEngine.restore(e.checkpoint())
        for engine in (e,other):
            engine.advance("finish-partial",BOB,"partial",100000)
            engine.commit("partial-commit",BOB,"partial")
        self.assertEqual(e.checkpoint(),other.checkpoint())

    def test_new_received_fact_invalidates_paid_partial_work(self):
        e,t=teacher10();slots=reveal10(e,"bob-first",actor=ALICE)
        m=work10(e,"stale-message","send",peer=BOB,act="request",body=("word",t["entry"]["term"]),slots=slots,goal=GOAL)[-1]
        deliver10(e,m)
        e.start("stale-start",LanguageRequest("stale",BOB,"interpret",ROOM,CUE5,focus=m["ref"]))
        e.advance("stale-paid",BOB,"stale",1)
        show(e,BOB,ref("bob-safe"))
        e.advance("stale-finish",BOB,"stale",100000)
        e.commit("stale-commit",BOB,"stale")
        self.assertEqual(e.job_status(BOB,"stale")["status"],"failed")
        self.assertGreater(e.job_status(BOB,"stale")["spent"],1)

    def test_unpracticed_listener_does_not_get_skill_from_speech(self):
        e,t=teacher10(setup10(train_bob=False))
        _,i=request10(e,t["entry"],body=t["entry"]["program"])
        r=response10(e,i)
        self.assertEqual((r["status"],r["reason"]),("refused","own_practice_required"))
        self.assertEqual(e.participant_view(BOB).snapshot.acquired,())

    def test_request_creates_no_automatic_promise_or_material_effect(self):
        e,t=teacher10();teach10(e,t["entry"],t["runs"])
        _,i=request10(e,t["entry"]);r=response10(e,i)
        self.assertEqual(r["status"],"planned")
        self.assertFalse(any(x["kind"]=="commitment" for a in (ALICE,BOB) for x in e.language_view(a)))
        self.assertEqual(e.world.head(ref("bob-first").identity).facet(Material).condition,"damaged")

    def test_permission_refusal_uses_receiver_evidence(self):
        e,t=teacher10();slots=reveal10(e,"counter",actor=ALICE);reveal10(e,"counter",actor=BOB)
        m=work10(e,"foreign-request","send",peer=BOB,act="request",body=t["entry"]["program"],slots=slots,goal=GOAL)[-1]
        deliver10(e,m);i=work10(e,"foreign-interpret","interpret",actor=BOB,focus=m["ref"])[0]
        self.assertEqual(response10(e,i)["reason"],"received_permission_or_resource_limit")

    def test_hidden_material_change_cannot_supply_meaning(self):
        states=[]
        for maximum in (1,2,7):
            e,t=teacher10(setup10(hidden_max=maximum));m,i=request10(e,t["entry"])
            states.append((e.participant_view(BOB).snapshot,i,e.wallet(BOB)))
        self.assertEqual(states[0],states[1]);self.assertEqual(states[1],states[2])

    def test_rendering_is_pure(self):
        e,t=teacher10();before=e.checkpoint()
        wording=sem.render(t["entry"]["program"])
        self.assertIn("repair",wording);self.assertIn("care",wording)
        self.assertEqual(e.checkpoint(),before)

    def test_language_records_cannot_be_imported(self):
        e,t=teacher10()
        with self.assertRaises(ValueError):e.declare("forged-lexeme",(e.world.resolve(t["entry"]["ref"]),))

    def test_unearned_other_actor_term_is_unknown(self):
        e,t=teacher10();teach10(e,t["entry"],t["runs"])
        self.assertEqual(e._lex(BOB,ROOM,BOB),{})
        self.assertEqual(e._lex(EVE,ROOM,ALICE),{})

    def test_adoption_preserves_u9_and_grants_no_language(self):
        prior,c=trained9();e=LanguageEngine.adopt(prior)
        self.assertEqual(e.composition_view(ALICE),prior.composition_view(ALICE))
        self.assertEqual(e.language_view(ALICE),())
        self.assertEqual(e.world.checkpoint(),prior.world.checkpoint())

    def test_context_is_not_implicitly_shared(self):
        e,t=teacher10();m,_=request10(e,t["entry"])
        other=ref("other-context")
        e.declare("new-context",(ObjectVersion(other,WRITER,"Other room",(Role.CONTEXT,)),))
        show(e,BOB,other)
        with self.assertRaises(ValueError):e.start("wrong-context",LanguageRequest("wrong",BOB,"interpret",other,CUE5,focus=m["ref"]))

    def test_mid_execution_restore_preserves_actual_effect_and_remainder(self):
        e,t=teacher10();_,i=request10(e,t["entry"],body=t["entry"]["program"])
        response=response10(e,i);run=enact_response10(e,response,steps=1)
        other=LanguageEngine.restore(e.checkpoint())
        for engine in (e,other):continue10(engine,run)
        self.assertEqual(e.checkpoint(),other.checkpoint())

    def test_response_cannot_be_repeated_to_duplicate_work(self):
        e,t=teacher10();_,i=request10(e,t["entry"],body=t["entry"]["program"])
        response10(e,i)
        perform(e,LanguageRequest("repeat-response",BOB,"respond",ROOM,CUE5,focus=i["ref"]),limit=100000)
        self.assertEqual(e.job_status(BOB,"repeat-response")["status"],"failed")

    def test_cancellation_preserves_cost_without_creating_meaning(self):
        e,t=teacher10();m,_=request10(e,t["entry"])
        prior=e.language_view(BOB);wallet=e.wallet(BOB)
        e.start("cancel-start",LanguageRequest("cancelled",BOB,"interpret",ROOM,CUE5,focus=m["ref"]))
        e.advance("cancel-work",BOB,"cancelled",1)
        e.cancel("cancel-end",BOB,"cancelled")
        self.assertEqual(e.language_view(BOB),prior)
        self.assertEqual(e.wallet(BOB)["energy"],wallet["energy"]-1)

    def test_arbitrary_word_spelling_does_not_supply_its_meaning(self):
        e,t=teacher10()
        alias=work10(e,"alias","coin",focus=t["capacity"]["ref"],term="wrong_answer_999")[0]
        learned=teach10(e,alias,t["runs"])
        self.assertEqual(learned[-1]["program"],t["entry"]["program"])

    def test_invalid_goal_relation_is_rejected_without_a_message(self):
        e,t=teacher10();slots=reveal10(e,"bob-first",actor=ALICE)
        perform(e,LanguageRequest("bad-goal",ALICE,"send",ROOM,CUE5,peer=BOB,act="request",body=t["entry"]["program"],
            slots=slots,goal=(("eq",("field","target","hidden_truth"),True),)),limit=100000)
        self.assertEqual(e.job_status(ALICE,"bad-goal")["status"],"failed")


class SpeechActs(unittest.TestCase):
    def test_statement_disagreement_and_question_answer(self):
        e=setup10();slots=reveal10(e,"bob-first",actor=ALICE);reveal10(e,"bob-first",actor=BOB)
        for act,truth in (("statement","serviceable"),("question","damaged")):
            body=("test",("eq",("field","target","condition"),truth))
            m=work10(e,act+"-send","send",peer=BOB,act=act,body=body,slots=slots)[-1]
            deliver10(e,m);i=work10(e,act+"-interpret","interpret",actor=BOB,focus=m["ref"])[0]
            self.assertEqual(i["assessment"],"contradicted" if act=="statement" else "supported")
            reply=work10(e,act+"-answer","respond",actor=BOB,focus=i["ref"])[-1]
            deliver10(e,reply)
            received=work10(e,act+"-receive","interpret",focus=reply["ref"])[0]
            self.assertEqual(received["meaning"][0],"answer")
        self.assertEqual(e.world.head(ref("bob-first").identity).facet(Material).condition,"damaged")

    def test_explanation_and_intention_use_grounded_structure(self):
        e,t=teacher10();slots=reveal10(e,"bob-first",actor=ALICE);reveal10(e,"bob-first",actor=BOB)
        for act in ("explanation","intention"):
            body=t["entry"]["program"]
            if act=="explanation":body=("because",("test",("eq",("field","target","condition"),"damaged")),body)
            m=work10(e,act+"-send","send",peer=BOB,act=act,body=body,slots=slots,goal=GOAL)[-1]
            deliver10(e,m);i=work10(e,act+"-interpret","interpret",actor=BOB,focus=m["ref"])[0]
            self.assertEqual(i["meaning"],body)
            self.assertEqual(i["status"],"understood")
        self.assertEqual(e.world.head(ref("bob-first").identity).facet(Material).condition,"damaged")

    def test_explicit_commitment_needs_actual_observed_fulfillment(self):
        e,t=teacher10();_,i=request10(e,t["entry"],"bob-promise",body=t["entry"]["program"])
        slots=reveal10(e,"bob-promise",actor=BOB)
        promise=next(x for x in work10(e,"promise","send",actor=BOB,peer=ALICE,act="commitment",body=i["meaning"],slots=slots,goal=GOAL) if x["kind"]=="commitment")
        response=response10(e,i);run=enact_response10(e,response)
        fulfilled=work10(e,"settle","settle",actor=BOB,focus=promise["ref"],practice=run["ref"])[0]
        self.assertEqual(fulfilled["status"],"fulfilled")
        self.assertEqual(fulfilled["ref"].revision,2)
        self.assertTrue(audit(e.world.journal())["passed"])

    def test_past_performance_cannot_fulfill_new_promise(self):
        e,t=teacher10();_,i=request10(e,t["entry"],body=t["entry"]["program"])
        response=response10(e,i);run=enact_response10(e,response)
        promise=next(x for x in work10(e,"late-promise","send",actor=BOB,peer=ALICE,act="commitment",body=i["meaning"],slots=run["slots"],goal=GOAL) if x["kind"]=="commitment")
        perform(e,LanguageRequest("false-settle",BOB,"settle",ROOM,CUE5,focus=promise["ref"],practice=run["ref"]),limit=100000)
        self.assertEqual(e.job_status(BOB,"false-settle")["status"],"failed")

    def test_conditions_and_relations_compose_with_known_actions(self):
        e,t=teacher10();_,i=request10(e,t["entry"],body=("if",("eq",("field","target","owner"),("field","target","custodian")),t["entry"]["program"],("act","use")))
        response=response10(e,i);run=enact_response10(e,response)
        self.assertEqual(run["status"],"succeeded")


class InductionBoundary(unittest.TestCase):
    def example(self,target,program,maximum):
        return dict(target=ref(target).identity,program=program,success=True,
            initial=freeze({"target":{"max_wear":maximum,"condition":"damaged","wear":maximum}}))

    def test_indistinguishable_conflicting_examples_remain_ambiguous(self):
        a=("seq",(("act","repair"),("act","use"),("act","care")))
        b=("seq",(("act","repair"),("act","use"),("act","repair")))
        xs=[self.example(str(i),a if i<2 else b,3) for i in range(4)]
        status,program,split=sem.induce(xs)
        self.assertEqual((status,program,split),("ambiguous",None,None))
        with self.assertRaises(sem.MeaningGap):sem.expand(("word","term"),{"term":{"status":status,"program":program}})

    def test_naming_cannot_create_a_distinguishing_feature(self):
        a=("seq",(("act","use"),));b=("seq",(("act","care"),))
        xs=[self.example(name,p,3) for name,p in (("correct",a),("true",a),("wrong",b),("false",b))]
        self.assertEqual(sem.induce(xs)[0],"ambiguous")

    def test_unsupported_action_is_not_a_new_affordance(self):
        with self.assertRaises(ValueError):sem.expand(("act","teleport"),{})


if __name__=="__main__":unittest.main()
