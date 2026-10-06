"""Participant-generated procedures over R8's single causal journal.

Local agreement is never a global knowledge flag. Packets travel through paid R2
channels and R6 reception. Cached practice summaries contain only owned outcomes.
"""
from dataclasses import replace
import hashlib
from .contracts import (ActionRequest, Cause, Kind, Moment, Observation, Proposition,
    Ref, ResourceAmount, TimeScope, WorkRecord, WorkStatus, WorldEvent)
from .semantic_records import SemanticPolicy, CancelSemantic
from .language import LanguageWorld, fingerprint, wire
from .language_records import Act, Interpretation, Pattern, Speech
from .organization_records import *
from .organization_policy import select, action_cost
from .socion_records import Notice
from .world import amounts, memory_key, ref_order
from .world_records import Attempt, ENERGY, TIME, INSPECT, TRANSFER, SEND, MessageDraft, Message, Wallet


def terms_id(terms): return hashlib.sha256(wire(terms).encode()).hexdigest()


def packet(result):
    if result.terms is None or result.kind not in ('proposal','review','agreement','join','exit','dispute'):
        raise ValueError('record has no transmissible organization claim')
    return OrganizationPacket(result.kind,result.owner,result.terms,result.status,result.reason)


class OrganizationWorld(LanguageWorld):
    def __init__(self,config,profiles,policy,agents,organization_policies=None,semantic_policy=SemanticPolicy()):
        self.organization_policies=tuple(OrganizationPolicy(a) for a in config.actors) if organization_policies is None else organization_policies
        if len(self.organization_policies)!=len(config.actors) or {p.owner for p in self.organization_policies}!=set(config.actors):
            raise ValueError('one organization policy per actor required')
        self._organization_policies={p.owner:p for p in self.organization_policies}
        self._organization_jobs={}; self._organization_heads={}; self._organization_outgoing={}
        self._organization_actions={}; self._organization_action_owner={}; self._organization_done={}
        self._organization_pending={}; self._organization_cancelled=set(); self._organization_blocked=set()
        self._practice={a:{} for a in config.actors}; self._practice_indexed=set()
        self._departures={}; self._applicants={}; self._disputed={}
        self.organization_candidate_visits=0
        super().__init__(config,profiles,policy,agents,semantic_policy)
        for r in (ORGANIZATION,ORGANIZE): self._records[r]=r
        for k in self._known.values(): k.update((ORGANIZATION,ORGANIZE))

    def organization_record(self,actor,ref): return self._owned(actor,ref,(OrganizationResult,))
    def organization_job(self,actor,key): return self._organization_jobs.get((actor,key))
    def organization_state(self,actor,identity): return self._organization_heads.get((actor,identity))
    def practices(self,actor): return tuple(self._practice[actor].values())

    def _read_packet(self,actor,ref):
        if type(self._records.get(ref)) is OrganizationResult:
            r=self.organization_record(actor,ref)
            return packet(r)
        obs=self._owned(actor,ref,(Observation,))
        if (actor,ref) not in self._completed_reception: raise ValueError('complete paid Model A reception first')
        message=self._records.get(obs.source)
        if type(message) is not Message or len(obs.content)!=1 or obs.content[0].relation!='r9_wire':
            raise ValueError('delivered organization packet required')
        from .codec import loads
        value=loads(obs.content[0].object)
        if type(value) is not OrganizationPacket or value.sender!=message.sender:
            raise ValueError('authenticated organization packet required')
        return value

    def _state(self,actor,ref):
        r=self.organization_record(actor,ref)
        if r.terms is None or r.kind not in ('agreement','notice','exit','dispute'):
            raise ValueError('local organization state required')
        return r, self.organization_state(actor,r.terms.identity)==r

    def _check_terms(self,actor,terms,access,joining=False):
        _,facts,count,stale=self._access(actor,access)
        lex=self.lexeme(actor,terms.meaning.token)
        policy=self._organization_policies[actor]
        if stale: return 'stale','owned access changed',count
        if lex is None or fingerprint(lex.meaning)!=fingerprint(terms.meaning):
            return 'repair','acquired meaning does not match offered terms',count
        if terms.meaning.patterns!=(Pattern(0,1),) or terms.meaning.arity!=2:
            return 'refused','unsupported responsibility pattern',count
        if terms.item not in self._items or any(m not in self._actors for m in terms.members):
            return 'refused','unknown public referent',count
        if not joining and actor not in terms.members: return 'refused','no consenting seat offered',count
        if self._agent_policies[actor].response=='silent': return 'refused','participant declines',count
        if action_cost(terms.steps)>policy.max_action_cost or len(terms.members)>policy.max_members:
            return 'refused','procedure exceeds own participation limits',count
        owners={owner for item,owner in facts if item==terms.item}
        if not owners: return 'unknown','no retained evidence about shared item',count
        if len(owners)>1: return 'ambiguous','conflicting retained evidence',count
        if not owners.issubset(set(terms.members)): return 'refused','item retained as held outside proposed cohort',count
        return 'accepted','meaning, cohort and evidence independently checked',count

    def _prepare_organization(self,cmd):
        a,p=cmd.actor,cmd.payload
        if a not in self._actors: raise ValueError('unknown participant')
        ref=Ref(Kind.EVIDENCE,'organization:'+memory_key(a,cmd.task_id),1)
        def result(kind,terms,status,reason,sources,previous=None,speech=None,units=1):
            sources=tuple(dict.fromkeys(sources))
            return max(1,units),OrganizationResult(ref,a,kind,terms,status,reason,sources,previous,speech)
        if type(p) is Formulate:
            _,facts,count,stale=self._access(a,p.access)
            old=None; sources=(p.access,)
            if p.state is not None:
                old,current=self._state(a,p.state); sources+=(old.ref,)
                if not current or old.status not in ('active','suspended'):
                    return result('proposal',None,'stale','predecessor unavailable',sources)
            choices=self.practices(a)
            self.organization_candidate_visits+=len(choices)
            blocked=() if old is None else self._disputed.get((a,old.terms.identity),())
            chosen=select(choices,self._organization_policies[a],
                {x.meaning.token:self.lexeme(a,x.meaning.token) for x in choices if self.lexeme(a,x.meaning.token) is not None},old,blocked)
            units=1+count+sum(1+len(x.steps)+len(x.partners) for x in choices)
            if stale or chosen is None:
                return result('proposal',None,'stale' if stale else 'unresolved',
                    'no current, sufficiently supported alternative procedure',sources,units=units)
            members=set(chosen.partners)|{a}
            identity='org:'+memory_key(a,cmd.task_id); generation=1; predecessor=None
            if old is not None:
                identity=old.terms.identity; generation=old.terms.generation+1; predecessor=terms_id(old.terms)
                k=(a,identity)
                exits=self._departures.get(k,{})
                joins=self._applicants.get(k,{})
                members=(set(old.terms.members)-set(exits))|set(joins)
                sources+=tuple(exits.values())+tuple(joins.values())
            if len(members)<2 or len(members)>self._organization_policies[a].max_members or a not in members:
                return result('proposal',None,'unresolved','no admissible recurring cohort',sources,units=units)
            terms=Terms(identity,generation,predecessor,chosen.item,chosen.meaning,chosen.steps,tuple(sorted(members,key=ref_order)))
            status,reason,_=self._check_terms(a,terms,p.access)
            sources+=chosen.examples
            return result('proposal',terms,'proposed' if status=='accepted' else status,
                'selected supported owned practice and voluntary cohort' if status=='accepted' else reason,
                sources,None if old is None else old.ref,units=units+len(members)+len(chosen.steps))
        if type(p) in (ReviewTerms,Join):
            source=p.proposal if type(p) is ReviewTerms else p.offer
            offered=self._read_packet(a,source); t=offered.terms
            permitted=('proposal',) if type(p) is ReviewTerms else ('proposal','agreement')
            if offered.kind not in permitted or offered.status not in ('proposed','active'):
                raise ValueError('usable proposal or membership offer required')
            status,reason,count=self._check_terms(a,t,p.access,type(p) is Join)
            head=self.organization_state(a,t.identity)
            sources=(source,p.access)
            if type(p) is Join:
                if a in t.members: status,reason='refused','already in proposed cohort'
            elif head is not None:
                removed=set(head.terms.members)-set(t.members)
                exits=self._departures.get((a,t.identity),{})
                sources+=tuple(exits.values())
                if (t.predecessor!=terms_id(head.terms) or t.generation!=head.terms.generation+1
                    or head.status not in ('active','suspended') or not removed.issubset(exits)):
                    status,reason='refused','lineage changed or member removed without received departure'
                if t.steps in self._disputed.get((a,t.identity),()):
                    status,reason='refused','disputed procedure has not changed'
            return result('join' if type(p) is Join else 'review',t,status,reason,sources,
                None if head is None else head.ref,units=2+count+len(t.steps)+len(t.members))
        if type(p) is Ratify:
            review=self.organization_record(a,p.review); t=review.terms
            if review.kind!='review' or t is None: raise ValueError('own reviewed terms required')
            votes=[self._read_packet(a,v) for v in p.votes]
            senders=[v.sender for v in votes]+[a]
            head=self.organization_state(a,t.identity)
            current=None if head is None else head.ref
            valid=(review.status=='accepted' and current==review.previous
                and len(senders)==len(set(senders)) and set(senders)==set(t.members)
                and all(v.kind=='review' and v.status=='accepted' and v.terms==t for v in votes))
            # A consent receipt is a permission to install these exact terms. It is
            # not a claim that another member knows all votes or has activated them.
            return result('agreement',t,'active' if valid else 'unagreed',
                'all exact-version member consents locally received' if valid else 'missing, refused, stale or mixed consent',
                (review.ref,)+p.votes,current,units=1+len(t.members)+len(votes))
        if type(p) is Dispute:
            run=self.organization_record(a,p.run)
            if run.kind!='run' or run.terms is None or self.organization_outcome(a,run.ref) not in ('failed','blocked'):
                raise ValueError('own consequential failed or blocked enactment required')
            head=self.organization_state(a,run.terms.identity)
            if head is None or head.terms!=run.terms or head.status not in ('active','suspended'):
                raise ValueError('dispute must concern current local terms')
            events=self._organization_actions.get(run.ref,())
            return result('dispute',run.terms,'suspended','own enacted procedure encountered contrary consequence',
                (run.ref,head.ref)+tuple(e.ref for e in events),head.ref,units=1+len(events))
        old,current=self._state(a,p.state); t=old.terms
        if not current or old.status not in ('active','suspended'):
            return result('run' if type(p) is Perform else 'notice' if type(p) is Attend else 'exit',
                t,'stale','local state is no longer actionable',(old.ref,),old.ref)
        if type(p) is Leave:
            return result('exit',t,'withdrawn',p.reason,(old.ref,),old.ref)
        if type(p) is Attend:
            notice=self._read_packet(a,p.notice)
            if notice.terms!=t: return result('notice',t,'ignored','notice concerns different terms',(old.ref,p.notice),old.ref)
            k=(a,t.identity)
            if notice.kind=='exit' and notice.status=='withdrawn' and notice.sender in t.members:
                remaining=set(t.members)-set(self._departures.get(k,{}))-{notice.sender}
                status='dissolved' if len(remaining)<2 else 'suspended'
                reason='member departure requires newly agreed cohort'
            elif notice.kind=='dispute' and notice.status=='suspended' and notice.sender in t.members:
                status,reason='suspended','received member dispute requires alternative and new consent'
            elif notice.kind=='join' and notice.status=='accepted' and notice.sender not in t.members:
                status,reason=old.status,'checked applicant available for a new proposal'
            else: return result('notice',t,'ignored','notice does not authorize a state change',(old.ref,p.notice),old.ref)
            return result('notice',t,status,reason,(old.ref,p.notice),old.ref,units=2)
        # Perform: bind generic responsibility and cyclic allocation to this member.
        if old.status!='active': return result('run',t,'suspended','local practice suspended',(old.ref,p.access),old.ref)
        if (a,t.identity) in self._organization_pending:
            raise ValueError('an enactment is already unfinished')
        _,facts,count,stale=self._access(a,p.access)
        member=t.members.index(a); recipient=t.members[(member+1)%len(t.members)]
        lex=self.lexeme(a,t.meaning.token)
        if lex is None or fingerprint(lex.meaning)!=fingerprint(t.meaning):
            return result('run',t,'repair','meaning changed since agreement',(old.ref,p.access),old.ref,units=1+count)
        speech=Speech('request',(self.word(a,t.meaning.token,(t.item,a)),),
            tuple(Act(s,t.item,recipient if s=='transfer' else None) for s in t.steps))
        refs,status,reason=self._guard(a,speech,facts)
        if stale: status,reason='stale','owned retained access changed'
        if self._agent_policies[a].response=='silent': status,reason='refused','participant declines this enactment'
        return result('run',t,status,reason,(old.ref,p.access)+refs,old.ref,speech,1+count+len(t.steps))

    def execute(self,cmd):
        if type(cmd) is OrganizationCommand or type(cmd) is CancelSemantic and cmd.family=='organization':
            def prepare():
                extent,result=self._prepare_organization(cmd)
                return extent,result,result.sources
            return self._semantic_execute(cmd,'organization',prepare)
        return super().execute(cmd)

    def send_organization(self,actor,record,recipient,key):
        value=packet(self.organization_record(actor,record))
        prop=Proposition(actor,'r9_wire',wire(value),self.config.context,TimeScope(self.now,None))
        return Attempt(key,key,ActionRequest(actor,SEND,(recipient,),()),MessageDraft((prop,)))

    def organization_outcome(self,actor,ref):
        r=self.organization_record(actor,ref)
        if r.kind!='run': return r.status
        if r.status!='accepted': return r.status
        if ref in self._organization_cancelled: return 'cancelled'
        if ref in self._organization_blocked: return 'blocked'
        events=self._organization_actions.get(ref,())
        if events and events[-1].outcome==WorkStatus.FAILED: return 'failed'
        if self._organization_done.get(ref,0)==len(r.speech.actions): return 'fulfilled'
        return 'pending'

    def next_organization_action(self,actor,ref):
        r=self.organization_record(actor,ref)
        if r.kind!='run' or self.organization_outcome(actor,ref)!='pending': return None
        head=self.organization_state(actor,r.terms.identity)
        if head is None or head.status!='active' or head.terms!=r.terms: return None
        n=self._organization_done.get(ref,0)
        act=r.speech.actions[n]
        task='organization-act:'+ref.key+':'+str(n)
        key=task+':'+str(len(self._organization_actions.get(ref,())))
        return Attempt(key,task,ActionRequest(actor,INSPECT if act.operation=='inspect' else TRANSFER,
            (act.item,)+(() if act.recipient is None else (act.recipient,)),()))

    def _validate_attempt(self,cmd):
        if cmd.command_id.startswith('organization-act:') or cmd.task_id.startswith('organization-act:'):
            target=self._organization_action_owner.get(cmd.command_id)
            if target is None or cmd!=self.next_organization_action(cmd.action.actor,target):
                raise ValueError('organization action differs from current owned plan')
        if cmd.message is not None and any(p.relation=='r9_wire' for p in cmd.message.content):
            if len(cmd.message.content)!=1:
                raise ValueError('one organization packet per envelope')
            p=cmd.message.content[0]
            if (p.subject!=cmd.action.actor or p.context!=self.config.context
                or (cmd.action.actor,p.object) not in self._organization_outgoing):
                raise ValueError('organization packet lacks owned committed origin')
        return super()._validate_attempt(cmd)

    def _index_organization_action(self,r):
        cmd=self.next_organization_action(r.owner,r.ref)
        if cmd is not None: self._organization_action_owner[cmd.command_id]=r.ref

    def _record_practice(self,r,success):
        if r.ref in self._practice_indexed: return
        self._practice_indexed.add(r.ref)
        s=r.speech
        if s is None or len(s.calls)!=1 or not s.actions or s.actions[-1].operation!='transfer': return
        call=s.calls[0]
        if len(call.arguments)!=2 or call.arguments[1]!=r.owner: return
        item=call.arguments[0]
        if any(x.item!=item for x in s.actions) or any(x.operation!='inspect' for x in s.actions[:-1]): return
        definition=(self._records[r.definitions[0]].meaning if type(r) is Interpretation else r.terms.meaning)
        if definition.patterns!=(Pattern(0,1),) or definition.arity!=2: return
        steps=tuple(x.operation for x in s.actions); partner=s.actions[-1].recipient
        k=(item,definition,steps); previous=self._practice[r.owner].get(k)
        p=previous or Practice(item,definition,steps,(),0,0,())
        partners=tuple(sorted(set(p.partners)|({partner} if success else set()),key=ref_order))
        self._practice[r.owner][k]=replace(p,partners=partners,successes=p.successes+int(success),
            failures=p.failures+int(not success),examples=(p.examples+(r.ref,))[-2:])

    def _commit(self,tx):
        extra=tx.extra if type(tx) is OrganizationTransaction else ()
        if any(r.ref in self._records for r in extra): raise ValueError('duplicate organization record')
        key=None if tx.command is None else tx.command.command_id
        target=self._organization_action_owner.get(key)
        language_target=self._language_action_owner.get(key)
        super()._commit(tx)
        for r in extra:
            self._records[r.ref]=r; self._origins[r.ref]=tx.event.ref; self._known[r.owner].add(r.ref)
            if r.terms is not None and r.kind in ('proposal','review','agreement','join','exit','dispute'):
                self._organization_outgoing[(r.owner,wire(packet(r)))]=r.ref
            changes_head=(r.kind=='agreement' and r.status=='active' or r.kind=='exit' and r.status=='withdrawn'
                or r.kind=='dispute' and r.status=='suspended' or r.kind=='notice' and r.status in ('active','suspended','dissolved'))
            if changes_head:
                k=(r.owner,r.terms.identity)
                self._organization_heads[k]=r
                if r.kind=='agreement':
                    self._departures.pop(k,None); self._applicants.pop(k,None); self._disputed.pop(k,None)
                elif r.kind=='dispute': self._disputed.setdefault(k,set()).add(r.terms.steps)
                elif r.kind=='notice':
                    value=self._read_packet(r.owner,r.sources[1])
                    if value.kind=='exit': self._departures.setdefault(k,{})[value.sender]=r.sources[1]
                    elif value.kind=='join': self._applicants.setdefault(k,{})[value.sender]=r.sources[1]
                    elif value.kind=='dispute': self._disputed.setdefault(k,set()).add(r.terms.steps)
                pending=self._organization_pending.get(k)
                if pending is not None and (r.status!='active' or self._records[pending].terms!=r.terms):
                    self._organization_cancelled.add(pending); self._organization_pending.pop(k,None)
            if r.kind=='run' and r.status=='accepted':
                self._organization_pending[(r.owner,r.terms.identity)]=r.ref
                self._index_organization_action(r)
        if type(tx) is OrganizationTransaction:
            self._organization_jobs[(tx.command.actor,tx.command.task_id)]=tx.job
            self._commit_semantic_state(tx,'organization')
        if target is not None:
            r=self._records[target]
            self._organization_actions.setdefault(target,[]).append(tx.event)
            if tx.event.outcome==WorkStatus.COMPLETED:
                self._organization_done[target]=self._organization_done.get(target,0)+1
                if tx.command.action.operation==INSPECT:
                    owners={p.object for o in tx.observations if o.observer==r.owner for p in o.content if p.relation=='owned_by'}
                    if owners!={r.owner}: self._organization_blocked.add(target)
            outcome=self.organization_outcome(r.owner,target)
            if outcome in ('fulfilled','failed','blocked'):
                self._organization_pending.pop((r.owner,r.terms.identity),None)
                self._record_practice(r,outcome=='fulfilled')
            self._index_organization_action(r)
        if language_target is not None:
            r=self._records[language_target]
            outcome=self.language_outcome(r.owner,r.ref)
            if outcome in ('fulfilled','failed'): self._record_practice(r,outcome=='fulfilled')
        for o in tx.observations:
            message=self._records.get(o.source)
            if type(message) is Message and len(o.content)==1 and o.content[0].relation=='r9_wire':
                self._notice_by_observation[(o.observer,o.ref)]=Notice(o.ref,o.source,message.sender,'organization',o.content[0],None,
                    self._profiles[message.sender].tim,self.processing_state(message.sender).active)

    def checkpoint(self):
        from .codec import dumps
        return dumps(OrganizationCheckpoint('hle-r11-organization-v1',self.config,self.profiles,self.policy,self.agents,
            self.organization_policies,tuple(self._journal),self.semantic_policy))

    @classmethod
    def restore(cls,text):
        from .codec import loads
        cp=loads(text)
        if type(cp) is not OrganizationCheckpoint or cp.schema!='hle-r11-organization-v1' or not cp.journal:
            raise ValueError('unsupported or empty organization checkpoint')
        w=cls(cp.config,cp.profiles,cp.policy,cp.agents,cp.organization_policies,cp.semantic_policy)
        if cp.journal[0]!=w._journal[0]: raise ValueError('genesis mismatch')
        for tx in cp.journal[1:]:
            if tx.command is None or tx.command.command_id in w._commands: raise ValueError('missing/duplicate command')
            w.execute(tx.command)
            if w._journal[-1]!=tx: raise ValueError('organization replay mismatch')
        return w
