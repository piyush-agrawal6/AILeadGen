"""Disposable browser fixture, genuine domain APIs, synthetic Google responses only."""
import uuid,os
from pathlib import Path
from email.message import EmailMessage
from email.parser import BytesParser
from email import policy
from datetime import datetime,timezone
import base64
from app.config.settings import get_settings
s=get_settings()
assert s.app_env=='test' and os.environ.get('DATABASE_BACKEND')=='sqlite' and not s.database_url,'Gmail fixture is isolated-test-only.'
path=Path(s.database_path).resolve();root=Path(__file__).resolve().parents[1]
assert path.is_relative_to(root/'data/e2e') and not path.exists()
path.parent.mkdir(parents=True,exist_ok=True)
from app.api.server import app
from app.database.connection import db_session
from app.database.migrations import run_migrations
from app.api.organization import create_organization
from app.platform.context import workspace_scope,current
from app.platform.workspaces import select_workspace
from app.platform.company_profiles import read_profile,save_profile,CompanyUpdate
from app.platform import onboarding
from app.icp import service as icps
from app.icp.models import Create
from app.acquisition import sheets
from app.integrations import gmail
from tests.unit import campaign_fixtures
from tests.workspace_fixtures import workspace_template
deliveries={}

with db_session() as c:
    run_migrations(c)
    for email,name in [('founder@leadengine.example','Synthetic first customer'),('cofounder@leadengine.example','Synthetic second customer')]:
        org=create_organization(c,email,name)['organization_id'];select_workspace(c,email,org)
        with workspace_scope(c,email,org):
            profile=read_profile(c)
            save_profile(c,CompanyUpdate.model_validate({k:v for k,v in profile.items() if k in CompanyUpdate.model_fields}))
            icp=icps.create(c,Create(name='Controlled market',criteria={'company':{'industries':['Dentistry']}},status='ACTIVE',request_id=uuid.uuid4()))
            setup=onboarding.save(c,onboarding.Setup(revision=0,objectives=['FIND_CUSTOMERS'],services=[{'name':'Software engineering'}],default_icp_id=icp['id'],preferences={'geography_mode':'GLOBAL','geography_confirmed':True,'integrations_skipped':True},current_step='REVIEW'))
            onboarding.complete(c,onboarding.Completion(revision=setup['revision']))
            previous=campaign_fixtures.PLANEBYTE_ORGANIZATION_ID
            try:
                campaign_fixtures.PLANEBYTE_ORGANIZATION_ID=org
                cid=campaign_fixtures.campaign(c,'Synthetic Gmail campaign')
                campaign_fixtures.lead(c,cid)
                workspace_template(c)
            finally:campaign_fixtures.PLANEBYTE_ORGANIZATION_ID=previous
    c.execute('UPDATE automation_controls SET email_paused=0')

async def exchange(body):
    assert body.get('code')=='synthetic-gmail-code' or body.get('grant_type')=='refresh_token'
    return {'access_token':'synthetic-browser-gmail-access','refresh_token':'synthetic-browser-gmail-refresh','expires_in':3600,'scope':gmail.SCOPE}
sheets.token_request=exchange
async def request_json(method,url,token,**kwargs):
    from app.platform.context import organization
    assert token=='synthetic-browser-gmail-access'
    if method=='POST':
        assert url=='https://gmail.googleapis.com/gmail/v1/users/me/messages/send'
        message=BytesParser(policy=policy.default).parsebytes(base64.urlsafe_b64decode(kwargs['payload']['raw']))
        assert str(message['To'])=='sandbox@example.test' and current().actor in str(message['From'])
        deliveries.setdefault(organization(),[]).append(message)
        return {'id':'synthetic-delivery-'+str(len(deliveries[organization()]))}
    assert method=='GET','Unexpected synthetic operation'
    if url.endswith('/userinfo'):return {'email':current().actor,'email_verified':True,'sub':'fixture-subject-'+current().actor}
    if url.endswith('/profile'):return {'emailAddress':current().actor,'historyId':'1'}
    if url.endswith('/history'):raise gmail.GmailRejected(404) # deliberate expired-history recovery case
    if url.endswith('/messages'):return {'messages':[{'id':'synthetic-reply'}]} if deliveries.get(organization()) else {'messages':[]}
    if url.endswith('/messages/synthetic-reply'):
        sent=deliveries[organization()][0];message=EmailMessage()
        message['Message-ID']='<synthetic-reply@example.test>';message['From']='sandbox@example.test';message['To']=current().actor
        message['Subject']='Re: Synthetic Gmail conversation';message['References']=sent['Message-ID'];message['In-Reply-To']=sent['Message-ID']
        message['Date']=datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')
        message['Authentication-Results']='mx.google.com; dkim=pass header.d=example.test'
        message.set_content('Synthetic customer reply: please share the reviewed options.')
        return {'raw':base64.urlsafe_b64encode(message.as_bytes()).decode()}
    raise AssertionError('Unexpected synthetic Gmail browser operation')
gmail.request_json=request_json

# Exercise the production owned-run worker with a bounded fixture clock. Global
# automatic sending remains disabled; only explicitly started customer runs tick.
import asyncio
from contextlib import asynccontextmanager
from app.mail import customer
original_lifespan=app.router.lifespan_context
def tick_started_runs():
    with db_session() as c:
        rows=c.execute("SELECT w.* FROM workflow_runs w JOIN customer_gmail_connections g ON g.organization_id=w.organization_id AND g.owner_user_id=w.created_by WHERE w.kind='OUTREACH' AND w.status='RUNNING' LIMIT 5").fetchall()
        for row in rows:
            with workspace_scope(c,row['created_by'],row['organization_id']):customer.advance_run(c,dict(row))
async def fixture_clock():
    for _ in range(180):
        await asyncio.sleep(.5)
        await asyncio.to_thread(tick_started_runs)
@asynccontextmanager
async def lifespan(application):
    async with original_lifespan(application):
        clock=asyncio.create_task(fixture_clock())
        try:yield
        finally:
            clock.cancel();await asyncio.gather(clock,return_exceptions=True)
app.router.lifespan_context=lifespan
