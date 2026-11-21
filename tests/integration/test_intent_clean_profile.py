"""Clean-profile acceptance uses disposable LOCAL schemas, never Neon customer data."""
import asyncio
import hashlib
import hmac
import json
import re
import time
import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import SecretStr

from test_postgres import postgres,pytestmark
from app.config.settings import get_settings
from app.database import intent_profile
from app.database.migrations import run_migrations,verify_schema
from app.platform.context import workspace_scope


@pytest.fixture
def clean(postgres,monkeypatch):
    s=get_settings()
    monkeypatch.setenv('DATABASE_BACKEND','postgres')
    for name,value in {'database_schema_profile':'intent-radar-v1','database_schema':postgres.schema,
                       'lead_engine_available':False,'database_background_polling_enabled':False}.items():
        monkeypatch.setattr(s,name,value)
    assert run_migrations(postgres)==len(intent_profile.migrations())
    assert intent_profile.assert_fresh(postgres)['customer_and_application_records']==0
    postgres.commit()
    return postgres,s


def test_clean_profile_has_no_customer_seeds_preserves_structure_and_rejects_drift(clean):
    c,s=clean
    assert run_migrations(c)==0
    assert verify_schema(c)==intent_profile.migrations()[-1][0]
    assert not c.execute("SELECT 1 FROM pg_tables WHERE schemaname=? AND tablename IN ('email_messages','contacts','experiments','scan_markets')",(c.schema,)).fetchone()
    c.execute('ALTER TABLE customer_accounts ADD COLUMN unreviewed TEXT')
    with pytest.raises(RuntimeError,match='columns, indexes or constraints'):
        intent_profile.assert_fresh(c)
    c.rollback()
    c.execute("UPDATE schema_migrations SET checksum='changed' WHERE version=1001")
    with pytest.raises(RuntimeError,match='checksum'):verify_schema(c)
    c.rollback()
    assert intent_profile.assert_fresh(c)['structure_verified']


def test_clean_real_router_uses_shared_health_without_legacy_preferences(clean):
    from datetime import datetime,timedelta,timezone
    from app.acquisition.ai_router import AIProviderRouter
    from app.acquisition.config import AcquisitionSettings
    from test_ai_router import Stub,Result
    c,s=clean
    config=AcquisitionSettings(_env_file=None,AI_PRIMARY_PROVIDER='vertex',VERTEX_AI_ENABLED=True,VERTEX_AI_MODEL='configured-model')
    vertex=Stub('VERTEX_AI');router=AIProviderRouter(config,c=c,providers=[vertex])
    assert not c.execute("SELECT 1 FROM pg_tables WHERE schemaname=? AND tablename='acquisition_preferences'",(c.schema,)).fetchone()
    assert asyncio.run(router.structured('rules',{},Result)).answer=='valid'
    expiry=(datetime.now(timezone.utc)+timedelta(minutes=4)).isoformat()
    router.record(vertex,'DEGRADED','RATE_LIMITED',expiry)
    # A different worker must honor at least the provider's minimum backoff.
    # Existing PostgreSQL REAL storage conservatively rounds up (<=128s here).
    fresh=AIProviderRouter(config,c=c,providers=[vertex])
    saved=datetime.fromisoformat(fresh.states()['VERTEX_AI']['retry_after'])
    assert 0<=(saved-datetime.fromisoformat(expiry)).total_seconds()<128
    c.execute('INSERT INTO provider_rate_limits(provider,next_request_at) VALUES(?,?)',('nominatim',123.0));c.commit()
    fresh.record(vertex,'READY')
    assert fresh.states()['VERTEX_AI']['retry_after'] is None
    assert c.execute('SELECT next_request_at FROM provider_rate_limits WHERE provider=?',('nominatim',)).fetchone()[0]==123.0


def test_clean_profile_migration_failure_rolls_back_every_object(postgres,monkeypatch):
    monkeypatch.setattr(get_settings(),'lead_engine_available',False)
    original=intent_profile.migrations()
    monkeypatch.setattr(intent_profile,'migrations',lambda:original[:1]+[(1002,'broken.sql','SELECT nonexistent_migration_function();','test')])
    with pytest.raises(Exception):intent_profile.migrate(postgres)
    assert not postgres.execute('SELECT 1 FROM pg_tables WHERE schemaname=?',(postgres.schema,)).fetchone()


def test_clean_profile_refuses_existing_legacy_schema_without_changes(postgres,monkeypatch):
    run_migrations(postgres)
    before=postgres.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    before_version=postgres.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]
    monkeypatch.setattr(get_settings(),'lead_engine_available',False)
    with pytest.raises(RuntimeError,match='legacy or unrelated'):intent_profile.migrate(postgres)
    assert postgres.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]==before_version
    assert postgres.execute('SELECT COUNT(*) FROM users').fetchone()[0]==before


def test_clean_additive_webhook_upgrade_preserves_existing_customer_rows(postgres,monkeypatch):
    from app.api.organization import create_organization
    monkeypatch.setattr(get_settings(),'lead_engine_available',False)
    monkeypatch.setattr(get_settings(),'database_schema_profile','intent-radar-v1')
    c=postgres
    c.execute('CREATE TABLE schema_migrations(version INTEGER PRIMARY KEY,name TEXT NOT NULL,checksum TEXT NOT NULL,applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)')
    for n,name,sql,digest in intent_profile.migrations()[:4]:
        with c.raw.cursor() as cursor:cursor.execute(sql.replace('__PLANEBYTE_SCHEMA__','"'+c.schema+'"'),prepare=False)
        c.execute('INSERT INTO schema_migrations(version,name,checksum) VALUES(?,?,?)',(n,name,digest))
    assert verify_schema(c)==1004
    org=create_organization(c,'a@example.com','Retained isolated customer')['organization_id'];c.commit()
    before=[dict(r) for r in c.execute('SELECT * FROM organization_memberships').fetchall()]
    assert run_migrations(c)==len(intent_profile.migrations())-4 and verify_schema(c)==intent_profile.migrations()[-1][0] and run_migrations(c)==0
    assert [dict(r) for r in c.execute('SELECT * FROM organization_memberships').fetchall()]==before
    assert c.execute('SELECT id FROM organizations WHERE id=?',(org,)).fetchone()
    assert c.execute('SELECT COUNT(*) FROM subscription_provider_events').fetchone()[0]==0


def _native_settings(s,monkeypatch):
    values={'app_env':'development','auth_disabled_local':False,'allowed_user_emails':'operator@example.net',
            'heysow_accounts_enabled':True,'heysow_access_periods_enabled':True,'heysow_customer_access_enabled':True,
            'heysow_public_registration_enabled':True,'heysow_workspace_management_enabled':True,
            'heysow_terms_version':'isolated-clean-profile-terms','heysow_google_admission_client_id':'synthetic-google-client',
            'api_signing_secret':'isolated-clean-profile-signing-secret-over-thirty-two-characters',
            'transactional_mail_enabled':True,'resend_api_key':SecretStr('synthetic-only'),
            'resend_from_email':'PlaneByte <accounts@planebyte.com>','intent_radar_stage':'Beta',
            'heysow_company_discovery_enabled':True,'heysow_company_ai_enabled':True,'heysow_icp_ai_enabled':True,
            'heysow_icp_ai_daily_limit':3,'intent_radar_growth_enabled':True}
    for name,value in values.items():monkeypatch.setattr(s,name,value)
    from app.accounts import policy
    monkeypatch.setattr(policy,'mailbox_domain_available',lambda _:True)


def _signup(c,email):
    from app.accounts import models,service,sessions
    from app.notifications import transactional as mail
    body=models.Signup(email=email,password='Isolated profile acceptance passphrase 739!',name='Local fixture',company_name='Local fixture company',terms_version=get_settings().heysow_terms_version,accepted_terms=True,request_id=uuid.uuid4())
    receipt=service.begin_signup(body,'local-clean-profile')
    encoded=c.execute('SELECT payload_encrypted FROM transactional_notifications WHERE authority_id=?',(receipt['challenge_id'],)).fetchone()[0];c.commit()
    # Only a synthetic LOCAL test challenge is decoded. No production OTP or
    # credential is read, generated on behalf of the owner, or exported.
    code=re.search(r'code is (\d{6})',json.loads(mail.cipher().decrypt(encoded.encode()))['text']).group(1)
    verified=service.verify_email(models.Verify(challenge_id=receipt['challenge_id'],capability=receipt['capability'],code=code),'local-clean-profile')
    assert verified['verified'] and verified['trial']['expires_at']-verified['trial']['starts_at']==604800
    session=sessions.exchange(c,verified['login_ticket']);c.commit()
    return verified,session


def test_clean_native_otp_recovery_google_trial_and_tenant_isolation(clean,monkeypatch):
    c,s=clean;_native_settings(s,monkeypatch)
    from app.accounts import service,models,sessions
    from app.notifications import transactional as mail
    from app.billing import commercial_usage
    owner,session=_signup(c,'owner@example.com')
    foreign,_=_signup(c,'foreign@example.org')
    assert owner['organization_id']!=foreign['organization_id']
    with workspace_scope(c,'owner@example.com',owner['organization_id']):
        assert commercial_usage.reserve(c,{'searches':5},'approved-trial-five');c.commit()
        with pytest.raises(HTTPException) as denied:commercial_usage.reserve(c,{'searches':1},'sixth')
        assert denied.value.status_code==429;c.rollback()
    with pytest.raises(HTTPException):
        with workspace_scope(c,'owner@example.com',foreign['organization_id']):pass
    c.rollback()
    request=service.recover(models.Recovery(email='owner@example.com',request_id=uuid.uuid4()),'local-clean-profile')
    notification=service.prepare_recovery(request['recovery_request_id'])
    encrypted=c.execute('SELECT payload_encrypted FROM transactional_notifications WHERE id=?',(notification,)).fetchone()[0];c.commit()
    token=json.loads(mail.cipher().decrypt(encrypted.encode()))['text'].split('?token=')[1].split('\n')[0]
    reset=models.Reset(token=token,password='Another isolated acceptance passphrase 740!')
    assert service.reset_password(reset,'local-clean-profile')['reset']
    assert not service.reset_password(reset,'local-clean-profile')['reset']
    with pytest.raises(HTTPException):sessions.validate(c,'owner@example.com',session['session_token'])
    c.rollback()
    assert service.login(models.Login(email='owner@example.com',password='Another isolated acceptance passphrase 740!'),'local-clean-profile')['authenticated']
    from app.platform import admission
    from test_account_admission import claim
    body=claim(email='google@example.net').model_copy(update={'terms_version':s.heysow_terms_version})
    google=admission.admit(c,body,actor=body.email,broker_verified=True);c.commit()
    assert google['status']=='ACTIVE'
    assert c.execute('SELECT COUNT(*) FROM customer_accounts').fetchone()[0]==3
    assert c.execute('SELECT COUNT(*) FROM launch_trial_claims').fetchone()[0]==3


def test_clean_signed_native_onboarding_worker_and_dashboard(clean,monkeypatch):
    c,s=clean;_native_settings(s,monkeypatch)
    verified,session=_signup(c,'owner@example.com');actor='owner@example.com';org=verified['organization_id']
    from app.acquisition import ai as gateway
    from app.acquisition.config import AcquisitionSettings
    from app.platform import company_autofill as autofill,company_discovery as jobs
    from app.icp import builder,ai as icp_ai
    from app.platform.onboarding_ai import Advice
    from test_company_autofill import SOURCE,result
    from test_icp_business_builder import five_candidates
    config=AcquisitionSettings(_env_file=None,VERTEX_AI_ENABLED=True,AI_PRIMARY_PROVIDER='vertex')
    monkeypatch.setattr(autofill,'provider_settings',lambda:config);monkeypatch.setattr(icp_ai,'provider_settings',lambda:config)
    async def structured(instruction,payload,schema,**kwargs):
        if schema is autofill.Extraction:return result()
        if issubclass(schema,builder.Suggestions):return schema(candidates=five_candidates())
        return Advice(answer='Synthetic provider interpretation of saved offerings.',source_fields=['description'])
    provider=AsyncMock();provider.structured.side_effect=structured;monkeypatch.setattr(gateway,'provider',lambda _:provider)
    monkeypatch.setattr(autofill,'collect_sources',AsyncMock(return_value=[SOURCE]))
    from app.api.routes import onboarding as routes
    async def launch(key):await asyncio.to_thread(jobs.execute,key)
    monkeypatch.setattr(routes,'launch',launch)
    from app.api.server import app
    from app.api.security import canonical_request
    def request(client,method,path,body=None):
        raw=json.dumps(body,separators=(',',':')).encode() if body is not None else b''
        stamp=str(int(time.time()));nonce=str(uuid.uuid4());client_id='c'*64
        signature=hmac.new(s.api_signing_secret.encode(),canonical_request(stamp,nonce,method,path,raw,actor,session['session_token'],client_id).encode(),hashlib.sha256).hexdigest()
        r=client.request(method,path,content=raw,headers={'content-type':'application/json','x-le-user':actor,'x-le-timestamp':stamp,'x-le-nonce':nonce,'x-le-signature':signature,'x-le-session':session['session_token'],'x-le-client':client_id})
        assert r.status_code<400,r.text
        return r.json()
    base='/api/organization/onboarding'
    with TestClient(app) as client:
        started=request(client,'POST',base+'/analyze',{'revision':0,'website':'https://example.com','objective':'RESEARCH_MARKETS','request_id':str(uuid.uuid4())})
        state=request(client,'GET',base+'/assistant-context');assert state['reviews']['company']['status']=='READY'
        from app.platform.company_profiles import CompanyUpdate
        profile={k:v for k,v in state['company'].items() if k in CompanyUpdate.model_fields}
        profile.update(description='Custom software for software teams.',countries_served=['United Kingdom'],products_services=[{'name':'Custom applications','description':'Engineering'}])
        saved=request(client,'PUT',base+'/company',{'revision':state['progress']['revision'],'objective':'RESEARCH_MARKETS','profile':profile})
        request(client,'POST',base+'/recommendations',{'revision':saved['progress']['revision'],'request_id':str(uuid.uuid4())})
        state=request(client,'GET',base+'/assistant-context');proposal=state['reviews']['icp']['preview'];assert len(proposal['candidates'])==5
        choices=[{'candidate_index':i,**{k:v for k,v in item['draft'].items() if k in ('name','description','criteria')}} for i,item in enumerate(proposal['candidates'])]
        accepted=request(client,'POST',base+'/accept-profiles',{'revision':state['progress']['revision'],'proposal_id':proposal['proposal_id'],'candidates':choices,'primary_index':0,'request_id':str(uuid.uuid4()),'research_keywords':['Custom applications'],'excluded_keywords':['jobs']})
        request(client,'POST',base+'/finish',{'revision':accepted['progress']['revision'],'primary_icp_id':accepted['progress']['default_icp_id'],'research_keywords':['Custom applications'],'excluded_keywords':['jobs']})
        summary=request(client,'GET','/api/intent-radar/overview/summary');details=request(client,'GET','/api/intent-radar/overview')
        assert summary['new_signals']==details['new_signals']==0
        assert request(client,'GET','/api/intent-radar/capabilities')['enabled']
        advice=request(client,'POST',base+'/assistant',{'prompt':'Which saved offering supports this audience?','request_id':str(uuid.uuid4())})
        assert request(client,'GET',base+'/reviews/'+advice['job']['id'])['status']=='READY'
    assert c.execute('SELECT COUNT(*) FROM ideal_customer_profiles WHERE organization_id=?',(org,)).fetchone()[0]==5


@pytest.fixture
def clean_radar(clean,monkeypatch):
    from test_intent_radar_postgres import pg_radar
    return pg_radar.__wrapped__(clean[0],monkeypatch)


def test_clean_growth_discovery_exports_and_isolation(clean_radar,monkeypatch):
    from test_growth_postgres import test_postgres_growth_persistence_scoping_revision_exports_and_existing_history as check
    check(clean_radar,monkeypatch)


def test_clean_assistant_scoped_history_and_usage(clean_radar,monkeypatch):
    from test_growth_postgres import test_postgres_assistant_real_reservation_private_history_and_recovery as check
    check(clean_radar,monkeypatch)

def test_clean_radar_review_dispatch_and_dataset_matrix(clean_radar,monkeypatch):
    from urllib.parse import urlsplit,parse_qs
    import httpx
    from cryptography.fernet import Fernet
    from app.acquisition import sheets
    from app.acquisition.config import AcquisitionSettings
    from app.integrations import radar_sheets,sheet_exports,service as oauth
    from app.intent_radar import exports,discovery,models,connectors,service
    from app.intelligence import jobs
    from test_intent_radar import source_result
    c,org,other=clean_radar;s=get_settings();actor='radar-pg@example.test'
    for k,v in {'heysow_workspace_management_enabled':True,'heysow_customer_integrations_enabled':True,'heysow_integration_encryption_key':Fernet.generate_key().decode()}.items():monkeypatch.setattr(s,k,v)
    monkeypatch.setattr('app.acquisition.config.settings',lambda:AcquisitionSettings(_env_file=None,AUTH_GOOGLE_ID='offline',AUTH_GOOGLE_SECRET='offline',GOOGLE_SHEETS_REDIRECT_URI='http://localhost/acquisition/sheets/callback'))
    monkeypatch.setattr(sheets,'token_request',AsyncMock(return_value={'access_token':'offline','refresh_token':'offline','scope':oauth.WRITE_SCOPE,'expires_in':3600}));monkeypatch.setattr(connectors,'fetch',AsyncMock(return_value=source_result()))
    with workspace_scope(c,actor,org):
        spec=radar_sheets.oauth_spec();link=oauth.authorize(c,spec=spec,write=True)['authorization_url'];state=parse_qs(urlsplit(link).query)['state'][0];conn=asyncio.run(oauth.connect(c,state,'fixture-code',spec=spec));query=models.Search(keywords=['website']);m=service.save_monitor(c,models.Monitor(name='Controlled monitor',configuration=query,status='Active'));job=discovery.create(c,models.Discovery(configuration=query,monitor_id=m['id']));c.commit();jobs.execute(job['id'])
        signal=service.listing(c,'signals')['items'][0];service.bookmark(c,signal['id']);op=service.opportunity(c,signal['id']);did=c.execute('SELECT id FROM intent_discoveries WHERE organization_id=?',(org,)).fetchone()[0];c.commit()
        for dataset,args in [('discovery',{'parent':did}),('monitor',{'parent':m['id']}),('saved',{'list_filters':{'collection':'Inbox'}}),('opportunities',{'list_filters':{'search':'website'}}),('signals',{'ids':[signal['id']]})]:
            snap=exports.snapshot(c,exports.Selection(dataset=dataset,**args));assert len(snap['records'])==1 and snap['records'][0]['signal_id']==signal['id'];assert exports.serialize(snap,'pdf').startswith(b'%PDF')
        draft=radar_sheets.Draft(selection=exports.Selection(dataset='opportunities',ids=[op['id']]),spreadsheet='isolated-provider-sheet',sheet='Acceptance',request_id=uuid.uuid4());review=radar_sheets.stage(c,conn['id'],draft,prior=[],expected_target="'Acceptance'!A1:J2");sheet_exports.approve(c,review['id'],review['fingerprint'],'OVERWRITE_REVIEWED_RANGE');c.commit()
    cells=[]
    async def receiver(request):
        if request.method=='PUT':
            cells.extend(json.loads(request.content)['values'])
            return httpx.Response(200,json={'updatedCells':sum(map(len,cells))})
        if request.method=='GET' and request.url.params['valueRenderOption']=='FORMULA':return httpx.Response(200,json={'range':review['target_range'],'values':cells})
        assert request.method=='GET' and cells
        return httpx.Response(200,json={'values':cells})
    asyncio.run(sheet_exports.execute(review['id'],transport=httpx.MockTransport(receiver)))
    with workspace_scope(c,actor,org):assert sheet_exports.owned(c,review['id'])['status']=='COMPLETED'
    with workspace_scope(c,actor,other):
        with pytest.raises(HTTPException):sheet_exports.owned(c,review['id'])


def test_clean_dashboard_summary_and_retention(clean_radar,monkeypatch):
    from test_growth_postgres import test_postgres_overview_summary_matches_scoped_counts_and_retention as check
    check(clean_radar,monkeypatch)
