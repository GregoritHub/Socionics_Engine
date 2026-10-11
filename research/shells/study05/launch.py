"""Reproduce Study 05 outside the checkout; never patches the working engine."""
import argparse,hashlib,io,json,os,shutil,subprocess,sys,tarfile,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
BASE='ab674a36e9234dcbf46634367bfc2b42b8b3cd18'
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repository',type=Path,default=HERE.parents[2])
    p.add_argument('--evidence',type=Path,required=True,help='Shell_Native_Evidence_05.zip from Library')
    p.add_argument('--output',type=Path,required=True,help='New directory outside repository')
    p.add_argument('--smoke',action='store_true',help='Run seven IEE fresh-pattern cases only')
    a=p.parse_args();repo=a.repository.resolve();out=a.output.resolve()
    if out==repo or repo in out.parents:raise ValueError('output must be outside repository')
    if out.exists():raise ValueError('output must be new; retain prior attempts')
    evidence=json.loads((HERE/'evidence.json').read_text())
    if hashlib.sha256(a.evidence.read_bytes()).hexdigest()!=evidence['sha256']:raise ValueError('evidence ZIP checksum mismatch')
    archive=subprocess.check_output(['git','-C',str(repo),'archive',BASE])
    out.mkdir(parents=True);source=out/'shell_study_01/source';source.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(archive)) as t:
        # Pinned repository archive only; reject absolute paths and traversal.
        for m in t.getmembers():
            if m.name.startswith('/') or '..' in Path(m.name).parts or m.issym() or m.islnk():raise ValueError('unsafe source archive member')
        t.extractall(source,filter='data')
    study=out/'shell_native_05';study.mkdir();engine=study/'engine';shutil.copytree(source,engine)
    subprocess.run(['patch','--batch','--fuzz=0','-p1','-i',str(HERE/'engine_v2.patch')],cwd=engine,check=True)
    for name in ('run.py','common.py','audit_v2.py','independent_wire.py'):shutil.copy(HERE/name,study/name)
    with zipfile.ZipFile(a.evidence) as z:
        for tim in ('iee','sli'):
            for arm in ('local','reowned'):
                name=f'shell_precision_02/inputs/{tim}_{arm}.json.gz';dest=out/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(name))
    plan=[('total','fresh_pattern','iee',False)] if a.smoke else [(l,f,t,False) for l in ('total','unfamiliar') for f in ('historical','fresh_pattern','fresh_scope') for t in ('iee','sli')]+[('total','historical',t,True) for t in ('iee','sli')]
    for load,fresh,tim,reference in plan:
        env=dict(os.environ);env.pop('SHELL_ENGINE',None);env.update(SHELL_LOAD_RULE=load,SHELL_FRESH_RULE=fresh)
        if reference:env['SHELL_ENGINE']=str(source)
        tag='reference' if reference else load+'-'+fresh
        with (study/f'{tag}-{tim}.log').open('w') as log:
            subprocess.run([sys.executable,'-B',str(study/'run.py'),'--type',tim,'--tag',tag],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        print(tag,tim,'passed',flush=True)
    if a.smoke:
        d=study/'attempt_02/total-fresh_pattern/iee';read=lambda n:json.loads((d/(n+'.json')).read_text())
        assert len(list(d.glob('*.json.gz')))==7
        assert not read('observed-old')['accepted'] and read('observed-old')['unchanged']
        assert read('observed-fresh')['accepted'] and read('unobserved-old')['accepted']
        assert not read('mixed')['response']['completed_demand'] and not read('novel3')['response']['completed_demand']
        result={'passed':True,'scope':'packaging smoke, seven IEE total/fresh_pattern native outcomes; exact checkpoint restores in driver. Not a rerun of full 98-case audit.'}
        (out/'validation.json').write_text(json.dumps(result,indent=2))
    else:subprocess.run([sys.executable,'-B',str(study/'audit_v2.py')],check=True)
if __name__=='__main__':main()
