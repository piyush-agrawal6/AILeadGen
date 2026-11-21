"""Prepare two rollback images using only deployed digests and schema recognition files."""
import argparse,io,json,re,subprocess,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def prepare(folder,api,worker):
    folder=folder.resolve();folder.relative_to((ROOT/'data/artifacts/staging').resolve());folder.mkdir(parents=True,exist_ok=False,mode=0o700)
    rev=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();names=[];steps=[]
    raw=subprocess.check_output(['git','archive',rev,'app/database/intent_migrations','app/database/intent_profile.py'],cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:archive.extractall(folder,filter='data')
    for role,base in [('api',api),('worker',worker)]:
        repo='asia-south1-docker.pkg.dev/querryside/leadengine/'+role
        if not re.fullmatch(re.escape(repo)+r'@sha256:[0-9a-f]{64}',base):raise ValueError('An immutable deployed digest for the matching runtime is required')
        head=max(int(p.name.split('_',1)[0]) for p in (folder/'app/database/intent_migrations').glob('[0-9]*_*.sql'))
        name=repo+f':schema{head}-bridge-'+rev[:10];names.append(name);dockerfile='Dockerfile.'+role
        (folder/dockerfile).write_text('FROM '+base+'\nLABEL io.planebyte.schema-source="'+rev+'"\nCOPY --chown=10001:10001 app/database/intent_migrations /opt/leadengine/app/database/intent_migrations\nCOPY --chown=10001:10001 app/database/intent_profile.py /opt/leadengine/app/database/intent_profile.py\n')
        steps.append({'name':'gcr.io/cloud-builders/docker','args':['build','-f',dockerfile,'-t',name,'.'],'waitFor':['-']})
    (folder/'cloudbuild.json').write_text(json.dumps({'steps':steps,'images':names}));return names

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--destination',type=Path,required=True);p.add_argument('--api',required=True);p.add_argument('--worker',required=True);a=p.parse_args();print(json.dumps(prepare(a.destination,a.api,a.worker)))
