"""Generate a 1018 recovery runtime from the known 1017 production image.

Keep previous product/auth/job implementations. Financial retirement and tenant
authorization are one-way safety boundaries: never roll these back to old writers.
Inputs come from Git objects, never a working .env or customer backup.
"""
import argparse, io, json, subprocess, tarfile
from pathlib import Path
from scripts.prepare_schema_bridge import ROOT,prepare

BASE='ba9b9bbff3da3d464608f514c095ca7e906c213f'
REPO='asia-south1-docker.pkg.dev/querryside/leadengine/'
API=REPO+'api@sha256:fe0f7ae7d395552b3d27d795bccacf112fddc50ec08d7dcb4bf867350d6440eb'
WORKER=REPO+'worker@sha256:8198e5d4ca225432dc4fd8ca6b1df09b99efe47857b13feccdce74cde248618c'
# These callers use the current quota accounting and terminal receipt semantics.
SAFETY=('app/billing','app/api/organization.py','app/api/routes/billing.py',
        'app/api/routes/fixed_term_billing.py','app/intent_radar/schedules.py',
        'app/intent_radar/permissions.py','app/intent_radar/discovery.py',
        'app/intent_radar/intelligence.py','app/notifications/dispatch.py',
        'app/developer/keys.py','app/growth_intelligence/service.py')

def build(folder):
    sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    subprocess.run(['git','merge-base','--is-ancestor',BASE,sha],cwd=ROOT,check=True)
    names=prepare(folder,API,WORKER)
    blob=subprocess.check_output(['git','archive',sha,*SAFETY],cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(blob)) as tar:tar.extractall(folder,filter='data')
    # Preserve the old application in the fallback, but make legacy endpoints
    # and worker entry points unavailable even on a bad recovery configuration.
    for path,marker,insert in (
        ('app/platform/modules.py','def guard_route(path,*,organization_id,role,method=\'GET\',connection=None):',"    if lead_engine_route(path) or path.startswith('/api/experiments'):raise HTTPException(410,'Legacy operations are retired.')"),
        ('app/worker.py','def validate_schema_mode():',"    if get_settings().lead_engine_available or get_settings().database_schema_profile!='intent-radar-v1':raise SystemExit('Recovery worker requires the Radar-only profile.')"),
        ('app/api/server.py','def create_app() -> FastAPI:',"    if get_settings().lead_engine_available or get_settings().database_schema_profile!='intent-radar-v1':raise RuntimeError('Recovery API requires the Radar-only profile.')")):
        old=subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT,text=True)
        if old.count(marker+'\n')!=1:raise ValueError('Unknown baseline: '+path)
        text=old.replace(marker+'\n',marker+'\n'+insert+'\n');compile(text,path,'exec');f=folder/path;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(text)
    for role in ('api','worker'):
        with (folder/('Dockerfile.'+role)).open('a') as f:
            clients=' '.join('/opt/leadengine/app/billing/'+n+'.py' for n in ('payu','payu_v2','provider'))
            f.write(f'LABEL io.planebyte.rollback-base="{BASE}"\nUSER root\nRUN rm -f {clients} /opt/leadengine/lead_engine.py\n')
            f.write('RUN rm -rf /opt/leadengine/app/cli\nUSER 10001:10001\n')
            for path in (*SAFETY,'app/platform/modules.py','app/worker.py','app/api/server.py'):
                f.write(f'COPY --chown=10001:10001 {path} /opt/leadengine/{path}\n')
    proof="""from importlib.util import find_spec
from app.api.server import app
from app.worker import validate_schema_mode
from app.database.connection import db_session
from app.database import intent_profile as p
from app.api.routes.billing import retired
from app.platform.modules import guard_route
from fastapi import HTTPException
import os
assert not any(find_spec(m) for m in ('app.billing.provider','app.billing.payu','app.billing.payu_v2','app.cli'))
for call in (retired, lambda:guard_route('/api/acquisition',organization_id=None,role=None)):
 try:call()
 except HTTPException as e:assert e.status_code==410
 else:raise AssertionError('Missing retirement guard')
os.environ['LEADENGINE_RUN_ID']='1'
try:validate_schema_mode()
except SystemExit:pass
else:raise AssertionError('Retired worker accepted')
with db_session() as c:
 p.migrate(c);assert p.verify(c)==1018 and p.assert_fresh(c)['structure_verified']
"""
    config=folder/'cloudbuild.json';v=json.loads(config.read_text());v['steps'] += [{'name':'gcr.io/cloud-builders/docker','args':['run','-d','--network=cloudbuild','--name','rollback-pg','-e','POSTGRES_PASSWORD=disposable','postgres:18']},{'name':'gcr.io/cloud-builders/docker','entrypoint':'bash','args':['-ec','for i in $(seq 1 30); do docker exec rollback-pg pg_isready -U postgres && exit 0; sleep 1; done; exit 1']}]
    for image in names:v['steps'].append({'name':'gcr.io/cloud-builders/docker','args':['run','--rm','--network=cloudbuild','-e','APP_ENV=test','-e','DATABASE_BACKEND=postgres','-e','DATABASE_SCHEMA_PROFILE=intent-radar-v1','-e','LEAD_ENGINE_AVAILABLE=false','-e','DATABASE_URL=postgresql://postgres:disposable@rollback-pg/postgres','--entrypoint','python',image,'-c',proof]})
    config.write_text(json.dumps(v));return names

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--destination',required=True,type=Path);print(json.dumps(build(parser.parse_args().destination)))
