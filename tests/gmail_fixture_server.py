"""Disposable browser fixture, genuine domain APIs, synthetic Google responses only."""
import uuid,os
from app.config.settings import get_settings
s=get_settings()
assert s.app_env=='test' and os.environ.get('DATABASE_BACKEND')=='sqlite' and not s.database_url,'Gmail fixture is isolated-test-only.'
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

async def exchange(body):
    assert body.get('code')=='synthetic-gmail-code'
    return {'access_token':'synthetic-browser-gmail-access','refresh_token':'synthetic-browser-gmail-refresh','expires_in':3600,'scope':gmail.SCOPE}
sheets.token_request=exchange
async def request_json(method,url,token,**kwargs):
    assert token=='synthetic-browser-gmail-access' and method=='GET','This browser fixture cannot send email.'
    if url.endswith('/userinfo'):return {'email':current().actor,'email_verified':True,'sub':'fixture-subject-'+current().actor}
    if url.endswith('/profile'):return {'emailAddress':current().actor,'historyId':'1'}
    if url.endswith('/messages'):return {'messages':[]}
    raise AssertionError('Unexpected synthetic Gmail browser operation')
gmail.request_json=request_json
