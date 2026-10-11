"""External evidence verifier: standard library only; imports no engine or fixture."""
from pathlib import Path
import collections, copy, csv, gzip, hashlib, json, sys
ROOT=Path(__file__).resolve().parent

def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)
def checked_envelope(text):
    d=json.loads(text)
    if hashlib.sha256(canonical(d['payload']).encode()).hexdigest()!=d['sha256']:
        raise ValueError('checkpoint envelope checksum mismatch')
    return d['payload']

def raw_versions(checkpoint_text):
    payload=checked_envelope(checkpoint_text)
    world=checked_envelope(payload['world'])
    nodes=world['nodes']; cache={}
    def decode(value):
        if not isinstance(value,list):return value
        if len(value)!=2 or value[0]!='@':raise ValueError('invalid graph reference')
        i=value[1]
        if i in cache:return cache[i]
        node=nodes[i]
        if node[0]=='record':out={'__type__':node[1],**{k:decode(v) for k,v in node[2]}}
        elif node[0]=='tuple':out=[decode(v) for v in node[1]]
        elif node[0]=='enum':out=node[2]
        else:raise ValueError('unknown graph node')
        cache[i]=out;return out
    revisions={}
    for ref_token,base_token,changes in world['versions']:
        ref,base=decode(ref_token),decode(base_token)
        key=canonical(ref)
        if key in revisions:raise ValueError('duplicate version')
        previous={} if base is None else revisions[canonical(base)]
        version={**previous, '__type__':'ObjectVersion', 'ref':ref, 'previous':base,
                 **{name:decode(token) for name,token in changes}}
        revisions[key]=version
    for tx in world['journal']:
        row=decode(tx)
        if not isinstance(row,list) or len(row)!=6:raise ValueError('invalid compact transaction')
        for ref in row[4]:yield revisions[canonical(ref)]

def values(version):
    d={x['name']:x['value'] for x in version['attributes']}
    # The saved schema encodes arrays as explicit length plus integer children.
    for k in sorted([x for x in d if x.endswith('.__length')],key=len,reverse=True):
        prefix=k[:-9];n=d.pop(k);d[prefix]=[d.pop(prefix+'.'+str(i)) for i in range(n)]
    return d

