"""Lossless ordered transaction segments for offline historical inspection.

Archives do not delete live work or replace actor access. Each independent gzip
segment and the complete chronological stream have SHA-256 integrity checks.
"""
import gzip
import hashlib
import json
from pathlib import Path
from . import codec
from .records import Transaction, Moment
from .compact import seal, unseal

SCHEMA = 'hle-unified-history-segments-v1'


def write_history(store, directory, segment_size=256):
    if type(segment_size) is not int or segment_size < 1:
        raise ValueError('positive segment size required')
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=False)
    journal = store.journal()
    segments, full = [], hashlib.sha256()
    for start in range(0, len(journal), segment_size):
        records = journal[start:start + segment_size]
        raw = codec.dumps(records).encode()
        full.update(raw)
        name = f'{start:012d}.json.gz'
        data = gzip.compress(raw, compresslevel=9, mtime=0)
        (path / name).write_bytes(data)
        segments.append(dict(name=name, start=start, count=len(records),
                             sha256=hashlib.sha256(data).hexdigest()))
    payload = dict(count=len(journal), segment_size=segment_size,
                   stream_sha256=full.hexdigest(), segments=segments)
    (path / 'manifest.json').write_text(seal(SCHEMA, payload))
    return HistoryArchive(path)


class HistoryArchive:
    def __init__(self, directory):
        self.path = Path(directory)
        self.manifest = unseal((self.path / 'manifest.json').read_text(), SCHEMA)
        d = self.manifest
        if set(d) != {'count', 'segment_size', 'stream_sha256', 'segments'}:
            raise ValueError('invalid history manifest')
        if type(d['count']) is not int or d['count'] < 0 or type(d['segment_size']) is not int or d['segment_size'] < 1:
            raise ValueError('invalid history size')
        cursor = 0
        for row in d['segments']:
            if (set(row) != {'name', 'start', 'count', 'sha256'}
                    or row['start'] != cursor or row['name'] != f'{cursor:012d}.json.gz'
                    or type(row['count']) is not int or not 1 <= row['count'] <= d['segment_size']):
                raise ValueError('invalid segment ordering')
            cursor += row['count']
        if cursor != d['count']:
            raise ValueError('missing history segments')
        self.segments_read = 0

    def segment(self, number):
        row = self.manifest['segments'][number]
        data = (self.path / row['name']).read_bytes()
        if hashlib.sha256(data).hexdigest() != row['sha256']:
            raise ValueError('history segment checksum mismatch')
        raw = gzip.decompress(data)
        values = codec.loads(raw.decode())
        if type(values) is not tuple or len(values) != row['count'] or any(
                type(tx) is not Transaction or tx.at != Moment(row['start'] + i, 0)
                for i, tx in enumerate(values)):
            raise ValueError('history segment sequence mismatch')
        self.segments_read += 1
        return raw, values

    def transaction(self, index):
        if type(index) is not int or not 0 <= index < self.manifest['count']:
            raise ValueError('historical transaction index out of range')
        # Manifests may have a short final segment; starts are authoritative.
        from bisect import bisect_right
        starts = [r['start'] for r in self.manifest['segments']]
        number = bisect_right(starts, index) - 1
        return self.segment(number)[1][index - starts[number]]

    def transactions(self):
        digest = hashlib.sha256()
        for i in range(len(self.manifest['segments'])):
            raw, values = self.segment(i)
            digest.update(raw)
            yield from values
        if digest.hexdigest() != self.manifest['stream_sha256']:
            raise ValueError('complete history digest mismatch')

    def restore(self, store_type):
        store = store_type()
        for tx in self.transactions():
            got = store.commit(tx.key, tx.writer, tx.versions, tx.lineage, actor=tx.actor)
            if codec.dumps(got) != codec.dumps(tx):
                raise ValueError('history replay mismatch')
        return store
