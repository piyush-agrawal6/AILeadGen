"""Rollback to the pre-account product with linked workspaces frozen, never independently payable."""
import argparse,json,subprocess
from pathlib import Path
from scripts.prepare_schema_bridge import prepare,ROOT

GUARD='''from fastapi import HTTPException

def migrated(c):
    n=c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0] or 0
    return n >= (1016 if n>=1000 else 58)

def freeze(c,org):
    if migrated(c) and not c.execute('SELECT 1 FROM billing_workspace_links self WHERE self.workspace_id=? AND self.account_id=self.workspace_id AND NOT EXISTS(SELECT 1 FROM billing_workspace_links child WHERE child.account_id=self.account_id AND child.workspace_id<>self.workspace_id)',(org,)).fetchone():
        raise HTTPException(503,'Shared billing is temporarily paused for maintenance. Do not start another checkout.')

def freeze_creation(c):
    if migrated(c):raise HTTPException(503,'Workspace creation is paused during billing recovery.')
'''

def build(folder,api,worker,baseline):
    names=prepare(folder,api,worker)
    changes={
        'app/platform/context.py':('def workspace_scope(conn, actor, organization_id):','from app.billing.rollback_guard import freeze;freeze(conn,organization_id)'),
        'app/api/organization.py':("def create_organization(c, email, name, *, setup_method='MANUAL'):",'from app.billing.rollback_guard import freeze_creation;freeze_creation(c)'),
        'app/billing/subscriptions.py':('def owner(c):','from app.billing.rollback_guard import freeze;freeze(c,current().organization_id)'),
        'app/billing/fixed_term.py':('def manager(c,org=None):','from app.billing.rollback_guard import freeze;freeze(c,org or current().organization_id)'),
        'app/billing/usage.py':('def capacity_for_workspace(c,org,dimension,current_count):','from app.billing.rollback_guard import freeze;freeze(c,org)'),
    }
    files=['app/billing/rollback_guard.py',*changes];(folder/'app/billing').mkdir(exist_ok=True);(folder/files[0]).write_text(GUARD)
    for path,(marker,guard) in changes.items():
        text=subprocess.check_output(['git','show',baseline+':'+path],cwd=ROOT,text=True);assert text.count(marker+'\n')==1
        tail=text.split(marker+'\n',1)[1];indent=tail[:len(tail)-len(tail.lstrip(' '))];assert indent
        result=text.replace(marker+'\n',marker+'\n'+indent+guard+'\n');compile(result,path,'exec');f=folder/path;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(result)
    for role in ('api','worker'):
        with (folder/('Dockerfile.'+role)).open('a') as f:
            for path in files:f.write(f'COPY --chown=10001:10001 {path} /opt/leadengine/{path}\n')
    proof="""from app.database.connection import db_session
from app.database import intent_profile as p
from app.billing.rollback_guard import freeze,freeze_creation
from fastapi import HTTPException
with db_session() as c:
 p.migrate(c);assert p.verify(c)==1017 and p.assert_fresh(c)['structure_verified']
 for f in (lambda:freeze(c,'unlinked'),lambda:freeze_creation(c)):
  try:f()
  except HTTPException as e:assert e.status_code==503
  else:raise AssertionError('Missing billing rollback fence')
"""
    config=folder/'cloudbuild.json';v=json.loads(config.read_text());v['steps'].extend([{'name':'gcr.io/cloud-builders/docker','args':['run','-d','--network=cloudbuild','--name','billing-qa','-e','POSTGRES_PASSWORD=disposable','postgres:18']},{'name':'gcr.io/cloud-builders/docker','entrypoint':'bash','args':['-ec','for i in $(seq 1 30); do docker exec billing-qa pg_isready -U postgres && exit 0; sleep 1; done; exit 1']}]);
    for image in names:v['steps'].append({'name':'gcr.io/cloud-builders/docker','args':['run','--rm','--network=cloudbuild','-e','APP_ENV=test','-e','DATABASE_BACKEND=postgres','-e','DATABASE_SCHEMA_PROFILE=intent-radar-v1','-e','DATABASE_URL=postgresql://postgres:disposable@billing-qa/postgres','--entrypoint','python',image,'-c',proof]})
    config.write_text(json.dumps(v))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--destination',required=True,type=Path);parser.add_argument('--baseline',required=True);parser.add_argument('--api',required=True);parser.add_argument('--worker',required=True);a=parser.parse_args();build(a.destination,a.api,a.worker,a.baseline)
