"""Slow complete offline reference, intentionally independent of live indexes."""
from hle.contracts import CueBinding, Kind, MemoryRevision
from hle.memory_records import MemoryTransaction, RecallHit, Visit


def complete_recall(world, result):
    records, heads, nav = {}, {}, None
    for tx in world.truth.journal():
        if tx.event.when > result.selected_at: break
        for memory in tx.memories: records[memory.ref] = memory
        if type(tx) is MemoryTransaction:
            for b in tx.bindings:
                if b.owner == result.owner:
                    heads.pop(b.ref.key, None)
                    heads[b.ref.key] = b
            for n in tx.navigations:
                if n.owner == result.owner: nav = n
    q = result.query
    selected = []
    for cue in q.cues:
        selected += [b for b in heads.values() if b.cue == cue and b.context == q.context
            and b.scope.start <= q.at and (b.scope.end is None or q.at < b.scope.end)]
    depths = 0 if nav is None else nav.max_hops
    queue, discovered, visited, hits = [], set(), [], []
    for b in selected:
        if b.target not in discovered:
            discovered.add(b.target); queue.append((b.target, None, 0))
    while queue and len(visited) < q.visit_limit:
        ref, parent, depth = queue.pop(0)
        visited.append(Visit(ref, parent, depth))
        m = records[ref]
        positions = []
        for i, p in enumerate(m.content):
            if p.context != q.context or p.scope.start > q.at: continue
            if p.scope.end is not None and q.at >= p.scope.end: continue
            if q.subject is not None and p.subject != q.subject: continue
            if q.relation is not None and p.relation != q.relation: continue
            positions.append(i)
        if positions: hits.append(RecallHit(ref, tuple(positions)))
        if depth < depths:
            for link in m.links:
                if link not in discovered:
                    discovered.add(link); queue.append((link, ref, depth + 1))
    return tuple(b.ref for b in selected), tuple(visited), tuple(hits), bool(queue)


class NoWalkList(list):
    def __iter__(self): raise AssertionError("inactive log traversal")
    def __getitem__(self, index):
        if isinstance(index, slice): raise AssertionError("inactive log slice")
        return super().__getitem__(index)


class NoWalkDict(dict):
    def __iter__(self): raise AssertionError("unrelated record enumeration")
    def keys(self): raise AssertionError("unrelated keys enumeration")
    def values(self): raise AssertionError("unrelated values enumeration")
    def items(self): raise AssertionError("unrelated items enumeration")
