"""Paid, owned participant semantics over R7. No Truth access in interpretation."""
from dataclasses import replace
import hashlib
from .composition import ComposedWorld
from .semantic import SemanticRouting
from .semantic_records import SemanticPolicy, CancelSemantic
from .metabolism_records import MetabolicCommand
from .composition_records import CompositionRevision, UnfoldResult
from .contracts import (ActionRequest, Cause, ClaimStatus, Kind, MemoryRevision,
    Moment, Observation, Proposition, Ref, ResourceAmount, TimeScope, WorkRecord,
    WorkStatus, WorldEvent)
from .language_records import (Act, Intend, Interpret, Interpretation, LANGUAGE,
    LANGUAGE_WORK, LanguageCheckpoint, LanguageCommand, LanguageJob,
    LanguageTransaction, Learn, Lexeme, Meaning, Pattern, Produce, Speech,
    Utterance, WordUse)
from .memory import in_scope
from .socion_records import Notice
from .world import amounts, memory_key
from .world_records import Attempt, ENERGY, INSPECT, Message, MessageDraft, SEND, TIME, TRANSFER, Wallet


def fingerprint(meaning):
    # Labels deliberately excluded: identical acquired structure has identical meaning.
    return hashlib.sha256(repr((meaning.patterns,meaning.arity)).encode()).hexdigest()


def abstract(facts, token):
    slots={}; patterns=[]
    for item,owner in facts:
        for ref in (item,owner):
            if ref not in slots: slots[ref]=len(slots)
        p=Pattern(slots[item],slots[owner])
        if p not in patterns: patterns.append(p)
    return Meaning(token,tuple(patterns),len(slots))


def wire(value):
    from .codec import dumps
    return dumps(value)


def speech_units(s): return 1+len(s.calls)+sum(len(c.arguments) for c in s.calls)+len(s.actions)


class LanguageWorld(SemanticRouting, ComposedWorld):
    def __init__(self,config,profiles,policy,agents,semantic_policy=SemanticPolicy()):
        if type(semantic_policy) is not SemanticPolicy: raise ValueError("semantic policy required")
        self.semantic_policy=semantic_policy; self._semantic_owners={}
        self._lexicon={}; self._language_jobs={}; self._language_sends={}
        self._language_actions={}; self._language_action_owner={}
        self._outgoing={}; self._expectations={a:[] for a in config.actors}
        super().__init__(config,profiles,policy,agents)
        for r in (LANGUAGE,LANGUAGE_WORK): self._records[r]=r
        for known in self._known.values(): known.update((LANGUAGE,LANGUAGE_WORK))

    def lexeme(self,actor,token): return self._lexicon.get((actor,token))
    def language_record(self,actor,ref): return self._owned(actor,ref,(Lexeme,Utterance,Interpretation))
    def language_job(self,actor,key): return self._language_jobs.get((actor,key))

    def word(self,actor,token,arguments):
        lex=self.lexeme(actor,token)
        if lex is None: raise ValueError('unlearned word')
        return WordUse(token,fingerprint(lex.meaning),arguments)

    def _access(self,actor,ref):
        access=self._owned(actor,ref,(UnfoldResult,))
        if access.query.context != self.config.context:
            raise ValueError('world-context access required for this action language')
        facts=[]; count=0; stale=False
        for node in access.nodes:
            record=self._owned(actor,node,(MemoryRevision,CompositionRevision))
            if type(record) is CompositionRevision:
                stale |= self._composition_heads.get(node.key)!=record
            else:
                stale |= self._memory_heads[actor].get(node.key)!=record
        for hit in access.hits:
            memory=self.read_revision(actor,hit.memory)
            count+=len(memory.content)
            if memory.claim_status not in (ClaimStatus.ENDORSED,ClaimStatus.TENTATIVE): continue
            for i in hit.proposition_indexes:
                p=memory.content[i]
                if not in_scope(p.scope,self.now): stale=True; continue
                if p.relation=='owned_by' and p.subject in self._items and p.object in self._actors:
                    facts.append((p.subject,p.object))
        return access,tuple(facts),count,stale

    def _delivered(self,actor,ref):
        observation=self._owned(actor,ref,(Observation,))
        if (actor,ref) not in self._completed_reception:
            raise ValueError('complete paid Model A reception first')
        if len(observation.content)!=1 or observation.content[0].relation!='r8_wire':
            raise ValueError('language envelope required')
        from .codec import loads
        try: value=loads(observation.content[0].object)
        except (ValueError,TypeError,KeyError): value=None
        message=self._records.get(observation.source)
        if type(message) is not Message: raise ValueError('delivered message required')
        return value,message

    def _definitions(self,actor,speech):
        refs=[]
        for call in speech.calls:
            lex=self.lexeme(actor,call.token)
            if lex is None or fingerprint(lex.meaning)!=call.fingerprint:
                return (), 'repair', 'unknown or changed meaning: '+call.token
            if len(call.arguments)!=lex.meaning.arity:
                return (), 'invalid', 'arity mismatch'
            if any(r not in self._known[actor] for r in call.arguments):
                return (), 'invalid', 'inaccessible argument'
            refs.append(lex.ref)
        for act in speech.actions:
            if act.item not in self._items or act.recipient is not None and act.recipient not in self._actors:
                return (), 'invalid', 'unknown action referent'
        return tuple(refs),None,None

    def _guard(self,actor,speech,facts):
        refs,status,reason=self._definitions(actor,speech)
        if status: return refs,status,reason
        values={}
        for item,owner in facts: values.setdefault(item,set()).add(owner)
        unknown=False; false=False
        for call,ref in zip(speech.calls,refs):
            for p in self._records[ref].meaning.patterns:
                item,owner=call.arguments[p.subject],call.arguments[p.owner]
                if item not in self._items or owner not in self._actors:
                    return refs,'invalid','argument role mismatch'
                seen=values.get(item,set())
                if len(seen)>1: return refs,'ambiguous','conflicting retained ownership'
                unknown |= not seen
                false |= bool(seen) and owner not in seen
        if false: return refs,'refused','retained evidence contradicts condition'
        if unknown: return refs,'unknown','condition lacks retained evidence'
        return refs,'accepted','all conditions supported by owned retained evidence'

    def _prepare(self,cmd,when):
        actor,p=cmd.actor,cmd.payload
        if actor not in self._actors: raise ValueError('unknown actor')
        ref=Ref(Kind.EVIDENCE,'language:'+memory_key(actor,cmd.task_id),1)
        if type(p) is Learn:
            access,facts,count,stale=self._access(actor,p.access)
            current=self.lexeme(actor,p.token)
            reason='stale access' if stale else 'no acquired ownership structure' if not facts else None
            meaning=None if reason else abstract(facts,p.token)
            source=None
            if p.observation is not None:
                value,message=self._delivered(actor,p.observation); source=p.observation
                if type(value) is not Meaning or value.token!=p.token:
                    reason='invalid teaching envelope'
                elif meaning is None or (value.patterns,value.arity)!=(meaning.patterns,meaning.arity):
                    reason='teaching pattern does not match independently retained structure'
                else: meaning=value
            if (None if current is None else current.ref)!=p.expected: reason='lexicon predecessor changed'
            required=1+count+(0 if meaning is None else len(meaning.patterns))
            if reason:
                result=Interpretation(ref,actor,source or p.access,p.access,None,'repair',(),reason)
            else:
                lref=Ref(Kind.MEMORY,'lexeme:'+memory_key(actor,p.token),1 if current is None else current.ref.revision+1)
                result=Lexeme(lref,actor,meaning,p.access,p.expected,source)
            return required,result,(p.access,)+(() if source is None else (source,))
        if type(p) is Produce:
            refs,status,reason=self._definitions(actor,p.speech)
            if status: raise ValueError(reason)
            return speech_units(p.speech),Utterance(ref,actor,p.speech,refs),refs
        access,facts,count,stale=self._access(actor,p.access)
        if type(p) is Interpret:
            speech,message=self._delivered(actor,p.observation)
            source=p.observation; debtor=message.sender
        else:
            utterance=self._owned(actor,p.utterance,(Utterance,))
            if utterance.speech.mode!='commit' or not self._language_sends.get(utterance.ref):
                raise ValueError('intention requires an actually transmitted own commitment')
            speech=utterance.speech; source=utterance.ref; debtor=actor
        refs=(); status='invalid'; reason='not a speech envelope'
        if type(speech) is Speech:
            refs,status,reason=self._guard(actor,speech,facts)
            if stale: status,reason='stale','retained access has changed; revise and access explicitly'
            if status=='accepted' and self._agent_policies[actor].response=='silent':
                status,reason='refused','participant response policy refuses'
            if status=='accepted' and speech.mode=='commit' and type(p) is Interpret:
                status,reason='expected','speaker commitment retained; fulfillment not established'
        else: speech=None
        result=Interpretation(ref,actor,source,p.access,speech,status,refs,reason,
            debtor if speech is not None and speech.mode=='commit' else None)
        return 1+count+(0 if speech is None else speech_units(speech)),result,(source,p.access)

    def execute(self,cmd):
        if type(cmd) is LanguageCommand or type(cmd) is CancelSemantic and cmd.family=='language':
            return self._semantic_execute(cmd,'language',lambda: self._prepare(cmd,Moment(len(self._journal),0)))
        if type(cmd) is MetabolicCommand and cmd.actor in self._semantic_owners and cmd.command_id not in self._commands:
            raise ValueError('semantic work must finish before an R4 movement')
        return super().execute(cmd)

    def send_language(self,actor,record,recipient,key):
        value=self._owned(actor,record,(Lexeme,Utterance))
        payload=value.meaning if type(value) is Lexeme else value.speech
        # Wire shares semantics only. Provenance stays local and indexed by exact send.
        prop=Proposition(actor,'r8_wire',wire(payload),self.config.context,TimeScope(self.now,None))
        return Attempt(key,key,ActionRequest(actor,SEND,(recipient,),()),MessageDraft((prop,)))

    def next_language_action(self,actor,interpretation):
        value=self._owned(actor,interpretation,(Interpretation,))
        if value.status!='accepted' or value.speech is None: return None
        events=self._language_actions.get(interpretation,())
        if events and events[-1].outcome==WorkStatus.FAILED: return None
        done=sum(e.outcome==WorkStatus.COMPLETED for e in events)
        if done==len(value.speech.actions): return None
        act=value.speech.actions[done]
        task='language-act:'+interpretation.key+':'+str(done)
        command=task+':'+str(len(events))
        inputs=(act.item,)+(() if act.recipient is None else (act.recipient,))
        # Delivered observation is an R2-permitted physical action basis.
        basis=(value.source,) if value.source.kind==Kind.OBSERVATION else ()
        return Attempt(command,task,ActionRequest(actor,INSPECT if act.operation=='inspect' else TRANSFER,inputs,basis))

    def expectations(self,actor):
        return tuple(self._expectations[actor])

    def language_outcome(self,actor,interpretation):
        value=self._owned(actor,interpretation,(Interpretation,))
        events=self._language_actions.get(interpretation,())
        if value.status!='accepted': return value.status
        if events and events[-1].outcome==WorkStatus.FAILED: return 'failed'
        if sum(e.outcome==WorkStatus.COMPLETED for e in events)==len(value.speech.actions): return 'fulfilled'
        return 'pending'

    def _commit(self,tx):
        extra=tx.extra if type(tx) is LanguageTransaction else ()
        if any(r.ref in self._records for r in extra): raise ValueError('duplicate language record')
        # Recognize only the exact next action authorized by an accepted owned plan.
        target=self._language_action_owner.get(tx.command.command_id) if tx.command is not None else None
        super()._commit(tx)
        for r in extra:
            self._records[r.ref]=r; self._origins[r.ref]=tx.event.ref; self._known[r.owner].add(r.ref)
            if type(r) is Lexeme: self._lexicon[(r.owner,r.meaning.token)]=r
            if type(r) is Interpretation and r.status=='accepted': self._index_next(r)
            if type(r) is Interpretation and r.status=='expected': self._expectations[r.owner].append(r.ref)
        if type(tx) is LanguageTransaction:
            self._language_jobs[(tx.command.actor,tx.command.task_id)]=tx.job
            self._commit_semantic_state(tx,'language')
        if target is not None:
            record=self._records[target]
            self._language_actions[target]=self._language_actions.get(target,())+(tx.event,)
            self._index_next(record)
        for m in tx.messages:
            if len(m.content)!=1 or m.content[0].relation!='r8_wire': continue
            # Only own retained output can be linked as an issued commitment.
            for r in self._outgoing.get((m.sender,m.content[0].object),()):
                self._language_sends.setdefault(r,[]).append(m.ref)
        for r in extra:
            if type(r) in (Lexeme,Utterance):
                self._outgoing.setdefault((r.owner,wire(r.meaning if type(r) is Lexeme else r.speech)),[]).append(r.ref)
        for o in tx.observations:
            m=self._records.get(o.source)
            if type(m) is Message and len(o.content)==1 and o.content[0].relation=='r8_wire':
                n=Notice(o.ref,o.source,m.sender,'language',o.content[0],None,
                    self._profiles[m.sender].tim,self.processing_state(m.sender).active)
                self._notice_by_observation[(o.observer,o.ref)]=n

    def _index_next(self,record):
        cmd=self.next_language_action(record.owner,record.ref)
        if cmd is not None: self._language_action_owner[cmd.command_id]=record.ref

    def _validate_attempt(self,cmd):
        target=self._language_action_owner.get(cmd.command_id)
        if target is not None and cmd!=self.next_language_action(cmd.action.actor,target):
            raise ValueError('language action differs from accepted plan')
        return super()._validate_attempt(cmd)

    def checkpoint(self):
        from .codec import dumps
        return dumps(LanguageCheckpoint('hle-r11-language-v1',self.config,self.profiles,self.policy,self.agents,tuple(self._journal),self.semantic_policy))

    @classmethod
    def restore(cls,text):
        from .codec import loads
        cp=loads(text)
        if type(cp) is not LanguageCheckpoint or cp.schema!='hle-r11-language-v1' or not cp.journal:
            raise ValueError('unsupported or empty language checkpoint')
        w=cls(cp.config,cp.profiles,cp.policy,cp.agents,cp.semantic_policy)
        if cp.journal[0]!=w._journal[0]: raise ValueError('genesis mismatch')
        for tx in cp.journal[1:]:
            if tx.command is None or tx.command.command_id in w._commands: raise ValueError('missing/duplicate command')
            w.execute(tx.command)
            if w._journal[-1]!=tx: raise ValueError('language replay mismatch')
        return w
