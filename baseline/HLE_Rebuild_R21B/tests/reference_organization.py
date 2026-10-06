"""Offline journal oracle for exact consent and physical outcome linkage.

Independent of OrganizationWorld indexes and policy/guard helpers. This is a
bounded protocol/action oracle, not an independent implementation of all R9.
"""
from hle.codec import loads
from hle.contracts import Observation, WorkStatus
from hle.organization_records import OrganizationTransaction, OrganizationResult, Ratify
from hle.world_records import Attempt


def consent(journal,actor,agreement):
    records={}
    head=None
    for tx in journal:
        for r in tx.observations: records[r.ref]=r
        if type(tx) is not OrganizationTransaction: continue
        for r in tx.extra:
            if r.ref==agreement:
                command=tx.command.payload
                if type(command) is not Ratify: return False
                review=records[command.review]
                if review.owner!=actor or review.status!='accepted' or review.previous!=head: return False
                voters=[actor]
                for ref in command.votes:
                    o=records.get(ref)
                    if type(o) is not Observation or o.observer!=actor or len(o.content)!=1: return False
                    value=loads(o.content[0].object)
                    if value.kind!='review' or value.status!='accepted' or value.terms!=review.terms: return False
                    voters.append(value.sender)
                return len(voters)==len(set(voters)) and set(voters)==set(review.terms.members)
            records[r.ref]=r
            if r.owner==actor and r.terms is not None and (
                r.kind=='agreement' and r.status=='active' or r.kind=='exit' and r.status=='withdrawn'
                or r.kind=='dispute' and r.status=='suspended' or r.kind=='notice' and r.status in ('active','suspended','dissolved')):
                # This oracle is used on one-organization fixtures.
                head=r.ref
    raise ValueError('agreement absent')


def actions(journal,run):
    prefix='organization-act:'+run.key+':'
    return tuple((tx.command.action.actor,tx.command.action.operation.key,
        tx.command.action.inputs,tx.event.outcome.value,
        sum(v.amount for work in tx.works for v in work.charged if v.unit.key=='r2.energy_quantum'))
        for tx in journal if type(tx.command) is Attempt and tx.command.task_id.startswith(prefix))
