"""Independent small language oracle from journal prefixes, not runtime indexes."""
from hle.language_records import LanguageTransaction, Lexeme, Speech
from hle.composition_records import UnfoldResult
from hle.contracts import ClaimStatus


def guard(journal, actor, speech, access_ref):
    records={}; lexicon={}
    for tx in journal:
        for r in tx.memories: records[r.ref]=r
        for r in getattr(tx,'extra',()):
            records[r.ref]=r
            if type(r) is Lexeme: lexicon[(r.owner,r.meaning.token)]=r
    access=records[access_ref]
    # Resolve exact accessed constituent revisions, independently of production access.
    facts=[]
    for h in access.hits:
        m=records[h.memory]
        if m.claim_status in (ClaimStatus.ENDORSED,ClaimStatus.TENTATIVE):
            facts.extend(m.content[i] for i in h.proposition_indexes)
    expected=[]
    import hashlib
    for c in speech.calls:
        lex=lexicon.get((actor,c.token))
        if lex is None: return 'repair'
        digest=hashlib.sha256(repr((lex.meaning.patterns,lex.meaning.arity)).encode()).hexdigest()
        if digest!=c.fingerprint: return 'repair'
        if len(c.arguments)!=lex.meaning.arity: return 'invalid'
        expected.extend((c.arguments[p.subject],c.arguments[p.owner]) for p in lex.meaning.patterns)
    missing=False; contradicted=False
    for item,owner in expected:
        observed={p.object for p in facts if p.subject==item and p.relation=='owned_by'}
        if len(observed)>1: return 'ambiguous'
        missing |= len(observed)==0
        contradicted |= len(observed)==1 and owner not in observed
    return 'refused' if contradicted else 'unknown' if missing else 'accepted'
