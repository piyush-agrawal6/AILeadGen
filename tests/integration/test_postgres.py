"""Opt-in tests against real PostgreSQL, isolated in a disposable schema."""
import os
import sys
from pathlib import Path
# Integration-only invocations also need the shared deterministic unit fixtures.
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"unit"))
import uuid
import pytest
import psycopg
from psycopg import sql
from app.config.settings import get_settings
from app.database.postgres import PostgresConnection
from app.database.migrations import run_migrations, verify_schema, MIGRATIONS
from app.database.models import Business, PipelineRun, PipelineRunEvent
from app.database.repositories import BusinessRepository, PipelineRunRepository, PipelineRunEventRepository
from app.database.prospects import ProspectRepository
from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID
from tests.workspace_fixtures import bind_internal_workspace
from app.platform.context import current
from starlette.requests import Request


def workspace_request():
    context = current()
    return Request({'type':'http','state':{'organization_id':context.organization_id,'user_email':context.actor}})

pytestmark = pytest.mark.skipif(os.environ.get("RUN_POSTGRES_TESTS") != "1", reason="Set RUN_POSTGRES_TESTS=1 for real PostgreSQL integration")


def test_real_postgres_permanent_deletion(owned_postgres,monkeypatch):
    from unittest.mock import Mock
    from app.api.services.deletion import preview,delete
    c=owned_postgres;run_migrations(c)
    run=PipelineRun(market='Deletion QA',vertical='dentists',target=5,status='COMPLETED');PipelineRunRepository(c).create(run, organization=PLANEBYTE_ORGANIZATION_ID)
    b=Business(name='Postgres deletion QA',normalized_name='postgres deletion qa',vertical='dentists',run_id=run.id,website='https://delete-qa.invalid');BusinessRepository(c).insert(b)
    ProspectRepository(c).observe(b, organization=PLANEBYTE_ORGANIZATION_ID);c.commit()
    monkeypatch.setattr('app.api.services.deletion.artifact_storage',lambda:Mock())
    p=preview(c,'scan',str(run.id));c.commit()
    assert delete(c,'scan',str(run.id),'DELETE',p['token'],'a@example.com')['deleted']
    assert c.execute('SELECT COUNT(*) FROM businesses').fetchone()[0]==0
    assert c.execute('SELECT COUNT(*) FROM prospects').fetchone()[0]==0
    assert c.execute('SELECT COUNT(*) FROM pipeline_runs').fetchone()[0]==0


@pytest.fixture
def postgres(monkeypatch):
    monkeypatch.setattr(get_settings(), "allowed_user_emails", "a@example.com")
    url = get_settings().database_url
    assert url, "DATABASE_URL is required"
    schema = "leadengine_test_" + uuid.uuid4().hex
    admin = psycopg.connect(url, autocommit=True)
    admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    conn = None
    try:
        conn = PostgresConnection(url, schema=schema)
        yield conn
    finally:
        if conn:
            conn.close()
        admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
        admin.close()


@pytest.fixture
def owned_postgres(postgres, request):
    run_migrations(postgres)
    bind_internal_workspace(postgres, request)
    return postgres


def test_postgres_onboarding_new_saved_resume_complete_and_history(postgres):
    from app.api.organization import create_organization
    from app.platform.context import workspace_scope
    from app.platform import onboarding as setup
    from app.platform.company_profiles import read_profile,save_profile,CompanyUpdate
    from app.icp import service as icps
    from app.icp.models import Create
    from fastapi import HTTPException
    run_migrations(postgres);c=postgres
    actor='onboarding@example.com';org=create_organization(c,actor,'PostgreSQL onboarding customer')['organization_id']
    foreign=create_organization(c,'foreign@example.com','Other onboarding customer')['organization_id']
    with workspace_scope(c,actor,org):
        assert setup.read(c)['revision']==0 and setup.read(c)['services']==[]
        saved=setup.save(c,setup.Setup(revision=0,objectives=['FIND_CUSTOMERS'],services=[{'name':'Archived service'}],current_step='SERVICES'));c.commit()
        assert setup.read(c)['services'][0]['name']=='Archived service'
        with pytest.raises(HTTPException) as incomplete:setup.complete(c,setup.Completion(revision=1))
        assert incomplete.value.status_code==422
        profile=read_profile(c)
        save_profile(c,CompanyUpdate.model_validate({k:v for k,v in profile.items() if k in CompanyUpdate.model_fields}))
        assert read_profile(c)['version'] is not None
        icp=icps.create(c,Create(name='Saved target',criteria={'company':{'industries':['Software']}},status='ACTIVE',request_id=uuid.uuid4()))
        body=setup.Setup(revision=1,objectives=['FIND_CUSTOMERS'],services=[{'name':'Current service','description':'Source-confirmed service'}],default_icp_id=icp['id'],preferences={'geography_mode':'SELECTED','countries':['Germany'],'geography_confirmed':True,'integrations_skipped':True},current_step='REVIEW')
        final=setup.save(c,body);c.commit()
        resumed=setup.read(c);assert resumed['revision']==2 and resumed['services'][0]['name']=='Current service'
        assert resumed['default_icp_id']==icp['id']
        with pytest.raises(HTTPException) as stale:setup.save(c,body)
        assert stale.value.status_code==409
        done=setup.complete(c,setup.Completion(revision=final['revision']));c.commit()
        assert done=={'status':'COMPLETED','discovery_started':False,'outreach_started':False}
        assert setup.complete(c,setup.Completion(revision=2))==done
        assert setup.read(c)['status']=='COMPLETED'
        assert c.execute('SELECT COUNT(*) FROM organization_services WHERE organization_id=?',(org,)).fetchone()[0]==2
        assert c.execute("SELECT COUNT(*) FROM audit_log WHERE action='ONBOARDING_COMPLETED' AND organization_id=?",(org,)).fetchone()[0]==1
    with workspace_scope(c,'foreign@example.com',foreign):assert setup.read(c)['revision']==0 and setup.read(c)['services']==[]
    with pytest.raises(HTTPException):setup.read(c)
    for table in ('pipeline_runs','acquisition_jobs','email_messages'):assert c.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]==0


def test_postgres_gated_invitation_account_admission_and_explicit_membership(postgres,monkeypatch):
    from app.platform import admission,invitations
    from app.platform.context import workspace_scope
    from app.api.organization import create_organization
    from test_account_admission import claim
    from fastapi import HTTPException
    c=postgres;run_migrations(c);s=get_settings()
    for key,value in {'heysow_customer_access_enabled':True,'heysow_public_registration_enabled':False,'heysow_invited_registration_enabled':True,'heysow_google_admission_client_id':'synthetic-google-client','heysow_terms_version':'synthetic-review-version'}.items():monkeypatch.setattr(s,key,value)
    owner='a@example.com';org=create_organization(c,owner,'PostgreSQL invited customer')['organization_id']
    with workspace_scope(c,owner,org):invite=invitations.create(c,invitations.InviteCreate(email='invited@example.com',role='VIEWER'))
    c.commit();body=claim(email=invite['email'],invitation_token=invite['token'])
    admitted=admission.admit(c,body,actor=body.email,broker_verified=True);c.commit()
    assert admitted['workspace_required'] and admission.access(c,body.email)
    assert c.execute('SELECT COUNT(*) FROM organization_memberships WHERE user_id=?',(body.email,)).fetchone()[0]==0
    accepted=invitations.respond(c,body.email,invitations.InviteRespond(token=invite['token'],action='ACCEPT'));c.commit()
    assert accepted['organization_id']==org
    with workspace_scope(c,body.email,org):assert c.execute('SELECT role FROM organization_memberships WHERE user_id=? AND organization_id=?',(body.email,org)).fetchone()[0]=='VIEWER'
    s.heysow_terms_version='new-synthetic-version'
    with pytest.raises(HTTPException):
        with workspace_scope(c,body.email,org):pass
    renewed=body.model_copy(update={'terms_version':s.heysow_terms_version,'acceptance_nonce':str(uuid.uuid4())})
    assert admission.admit(c,renewed,actor=body.email,broker_verified=True)['existing'];c.commit()
    assert admission.access(c,body.email)
    assert c.execute('SELECT COUNT(*) FROM account_terms_acceptances WHERE user_id=?',(body.email,)).fetchone()[0]==2


def test_postgres_customer_summary_strict_scope_and_no_internal_metadata(postgres):
    from app.api.organization import create_organization,complete_onboarding
    from app.platform.context import workspace_scope
    from app.automation.views import customer_summary
    from app.api.schemas.automation import CustomerSummary
    from test_automation_summary import seed_summary
    from fastapi import HTTPException
    c=postgres;run_migrations(c);actor='summary@example.com'
    org=create_organization(c,actor,'Owned summary')['organization_id'];other=create_organization(c,actor,'Other summary')['organization_id']
    complete_onboarding(c,org);complete_onboarding(c,other)
    seed_summary(c,org);seed_summary(c,other,manual=4,queued=2)
    c.execute("INSERT INTO automation_runs(day,status,started_at,target,error_code) VALUES('2026-11-08','FAILED','2026-11-08T00:00:00+00:00',987,'POSTGRES_INTERNAL_MARKER')");c.commit()
    for target,count in ((org,1),(other,4)):
        with workspace_scope(c,actor,target):
            data=CustomerSummary.model_validate(customer_summary(c,target)).model_dump()
            assert data['today']['manual']==count and 'POSTGRES_INTERNAL_MARKER' not in str(data)
            assert set(data)=={'today','environment','contact_counts','queue'}
            with pytest.raises(HTTPException):customer_summary(c,other if target==org else org)


@pytest.mark.parametrize('role',['OWNER','ADMIN','MEMBER','VIEWER'])
def test_postgres_onboarding_roles_recheck_revocation(postgres,role):
    from app.api.organization import create_organization
    from app.platform.context import workspace_scope
    from app.platform.memberships import change_role
    from app.platform import onboarding as setup
    from fastapi import HTTPException
    c=postgres;run_migrations(c);owner='owner@pg-setup.example';actor='role@pg-setup.example'
    org=create_organization(c,owner,'Role-isolated setup')['organization_id']
    with workspace_scope(c,owner,org):change_role(c,owner,actor,role)
    with workspace_scope(c,actor,org):
        assert setup.read(c)['can_edit']==(role in ('OWNER','ADMIN'))
        if role in ('MEMBER','VIEWER'):
            with pytest.raises(HTTPException) as denied:setup.save(c,setup.Setup(revision=0))
            assert denied.value.status_code==403
        else:assert setup.save(c,setup.Setup(revision=0))['revision']==1
        c.execute("UPDATE organization_memberships SET status='REVOKED' WHERE user_id=? AND organization_id=?",(actor,org))
        with pytest.raises(HTTPException) as revoked:setup.read(c)
        assert revoked.value.status_code==403


def test_postgres_google_admission_concurrent_identity_and_nonce_are_idempotent(postgres,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from app.platform import admission
    from app.api.organization import create_organization
    from app.platform.context import workspace_scope
    from test_account_admission import claim
    c=postgres;run_migrations(c);s=get_settings()
    for key,value in {'heysow_customer_access_enabled':True,'heysow_public_registration_enabled':True,'heysow_google_admission_client_id':'synthetic-google-client','heysow_terms_version':'synthetic-review-version'}.items():monkeypatch.setattr(s,key,value)
    body=claim();c.commit()
    def register():
        other=PostgresConnection(s.database_url,schema=c.schema)
        try:
            result=admission.admit(other,body,actor=body.email,broker_verified=True);other.commit();return result
        finally:other.close()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=[future.result(timeout=8) for future in (pool.submit(register),pool.submit(register))]
    assert all(row['status']=='ACTIVE' for row in results)
    assert c.execute('SELECT COUNT(*) FROM account_admissions').fetchone()[0]==1
    assert c.execute('SELECT COUNT(*) FROM account_terms_acceptances').fetchone()[0]==1
    assert c.execute('SELECT COUNT(*) FROM organization_memberships WHERE user_id=?',(body.email,)).fetchone()[0]==0
    org=create_organization(c,body.email,'Owned admitted customer')['organization_id']
    with workspace_scope(c,body.email,org):assert current().organization_id==org
    c.execute("UPDATE account_admissions SET status='SUSPENDED' WHERE user_id=?",(body.email,));c.commit()
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        with workspace_scope(c,body.email,org):pass


def test_postgres_admission_upgrade_preserves_existing_workspace_data(postgres,monkeypatch):
    import app.database.migrations as migrations
    c=postgres;full=migrations.MIGRATIONS
    monkeypatch.setattr(migrations,'MIGRATIONS',full[:-1]);run_migrations(c)
    existing=[dict(row) for row in c.execute('SELECT * FROM organization_services ORDER BY id').fetchall()]
    memberships=[dict(row) for row in c.execute('SELECT * FROM organization_memberships ORDER BY id').fetchall()]
    assert existing and memberships
    monkeypatch.setattr(migrations,'MIGRATIONS',full)
    assert run_migrations(c)==1 and run_migrations(c)==0
    assert [dict(row) for row in c.execute('SELECT * FROM organization_services ORDER BY id').fetchall()]==existing
    assert [dict(row) for row in c.execute('SELECT * FROM organization_memberships ORDER BY id').fetchall()]==memberships
    assert c.execute('SELECT COUNT(*) FROM account_admissions').fetchone()[0]==0


def test_real_postgres_repositories_and_shared_workflow(postgres,request):
    conn = postgres
    assert run_migrations(conn) == len(MIGRATIONS)
    assert run_migrations(conn) == 0
    verify_schema(conn)
    bind_internal_workspace(conn,request)
    from app.platform.memberships import change_role
    change_role(conn,current().actor,"b@example.com","MEMBER")
    runs = PipelineRunRepository(conn)
    run = PipelineRun(market="Austin", vertical="dentists", target=5)
    run_id = runs.create(run, organization=PLANEBYTE_ORGANIZATION_ID)
    business = Business(name="Independent Dental", normalized_name="independent dental", vertical="dentists", city="Austin", run_id=run_id, website="https://independent.example")
    BusinessRepository(conn).insert(business)
    assert BusinessRepository(conn).get_by_id(business.id).name == business.name
    repo = ProspectRepository(conn)
    prospect_id = repo.observe(business, organization=PLANEBYTE_ORGANIZATION_ID)
    repo.workflow(prospect_id, "a@example.com", lead_status="SHORTLISTED", assigned_to="b@example.com")
    repo.add_note(prospect_id, "b@example.com", "Public booking flow needs work.")
    event = PipelineRunEvent(run_id=run_id, stage="TEST", event_type="TEST", message="Persisted across processes")
    PipelineRunEventRepository(conn).create(event)
    conn.commit()
    dossier = repo.dossier(business.id)
    assert dossier["assigned_to"] == "b@example.com"
    assert dossier["lead_status"] == "SHORTLISTED"
    assert dossier["notes"][0]["created_by"] == "b@example.com"
    assert PipelineRunEventRepository(conn).list_by_run(run_id)[0].message == event.message
    assert BusinessRepository(conn).search_leads()[1] == 1
    run.status = "COMPLETED"
    runs.update(run)
    conn.commit()
    assert runs.get_by_id(run_id).status == "COMPLETED"
    # Phase 3.5 is additive: existing assignment and notes survive LOST, while
    # report versions belong to the same canonical prospect on PostgreSQL.
    repo.workflow(prospect_id,"a@example.com",lead_status="LOST")
    from app.reports.service import create_report
    first=create_report(conn,business.id,prospect_id,'a@example.com')
    assert create_report(conn,business.id,prospect_id,'a@example.com')['id']==first['id']
    conn.execute("UPDATE client_reports SET status='READY' WHERE id=?",(first['id'],))
    second=create_report(conn,business.id,prospect_id,'a@example.com')
    conn.commit()
    assert first['version']==1 and second['version']==2
    assert repo.dossier(business.id)['lead_status']=='LOST'
    assert repo.dossier(business.id)['notes'][0]['body']=='Public booking flow needs work.'


def test_worker_session_lock_survives_commit_and_releases_on_close():
    url=get_settings().database_url
    first=PostgresConnection(url,session_bound=True)
    second=PostgresConnection(url,session_bound=True)
    lock=int(uuid.uuid4().hex[:7],16)
    try:
        assert first.execute('SELECT pg_try_advisory_lock(6919444,?)',(lock,)).fetchone()[0]
        first.commit()
        assert not second.execute('SELECT pg_try_advisory_lock(6919444,?)',(lock,)).fetchone()[0]
        second.commit();first.close();first=None
        assert second.execute('SELECT pg_try_advisory_lock(6919444,?)',(lock,)).fetchone()[0]
    finally:
        if first:first.close()
        second.close()


def test_real_postgres_schema9_views_and_target_storage(owned_postgres):
    """Disposable-schema acceptance only; production public schema is untouched."""
    from app.automation.service import reconcile
    from app.automation.views import search
    from app.automation.settings import save_targets,effective_settings
    c=owned_postgres;run_migrations(c)
    run=PipelineRun(market='Controlled London',vertical='dentists',target=1);PipelineRunRepository(c).create(run, organization=PLANEBYTE_ORGANIZATION_ID)
    b=Business(name='Controlled permanent lead',normalized_name='controlled permanent lead',vertical='dentists',city='London',country='United Kingdom',phone='+442055501234',website='https://controlled.invalid',run_id=run.id,processing_status='QUALIFIED')
    BusinessRepository(c).insert(b);pid=ProspectRepository(c).observe(b, organization=PLANEBYTE_ORGANIZATION_ID)
    reconcile(c)
    page=search(c,{'country':'United Kingdom','email_availability':'no'},'manual',1,25)
    assert page['total']==1 and page['items'][0]['prospect_id']==pid and page['counts']['today']==1
    save_targets(c,{'daily_qualified_lead_target':3,'daily_email_target':2,'max_hour':2,'max_day':5},'system');c.commit()
    assert effective_settings(c).daily_qualified_lead_target==3


def test_real_postgres_enabled_queue_duplicate_claim(owned_postgres,monkeypatch):
    from unittest.mock import Mock
    from datetime import datetime,timezone
    from app.automation import service as automation
    from app.mail import service as mail
    from app.mail.config import MailSettings
    from app.database.prospects import now
    c=owned_postgres;run_migrations(c)
    config=MailSettings(_env_file=None,EMAIL_PROVIDER='hostinger',EMAIL_SEND_MODE='test',EMAIL_TEST_RECIPIENT='contact@planebyte.com',EMAIL_SENDING_ENABLED=True,AUTO_EMAIL_ENABLED=True,MAX_EMAILS_PER_DAY=100,DAILY_EMAIL_TARGET=100)
    monkeypatch.setattr(automation,'mail_settings',lambda:config);monkeypatch.setattr(mail,'mail_settings',lambda:config)
    monkeypatch.setattr(automation,'business_hours',lambda *args:True)
    transport=Mock();monkeypatch.setattr(mail,'provider',lambda:transport)
    from campaign_fixtures import campaign,qualify
    cid=campaign(c)
    run=PipelineRun(market='Controlled',vertical='dentists',target=1,status='COMPLETED');PipelineRunRepository(c).create(run, organization=PLANEBYTE_ORGANIZATION_ID)
    b=Business(name='Controlled queue',normalized_name='controlled queue',vertical='dentists',city='London',run_id=run.id,website='https://controlled.invalid',public_email='contact@planebyte.com',processing_status='QUALIFIED')
    c.execute('UPDATE pipeline_runs SET campaign_id=? WHERE id=?',(cid,run.id))
    BusinessRepository(c).insert(b);qualify(c,b);pid=ProspectRepository(c).observe(b, organization=PLANEBYTE_ORGANIZATION_ID)
    c.execute("INSERT INTO contacts(business_id,contact_type,contact_value,source_url,is_valid,is_public_business_contact) VALUES(?,'email',?,?,1,1)",(b.id,b.public_email,b.website+'/contact'))
    c.execute("INSERT INTO business_intelligence(business_id,prospect_id,classification_version,business_scale,scale_reason,scale_confidence,footprint_json,commercial_fit,commercial_reason,created_at) VALUES(?,?,'qa','SMALL_GROUP','fixture',1,'{}','HIGH','fixture',?)",(b.id,pid,now()))
    c.execute("INSERT INTO findings(business_id,finding_code,category,severity,title,description) VALUES(?,'qa','SEO','LOW','Controlled finding','Stored controlled finding')",(b.id,))
    c.execute('UPDATE automation_controls SET email_paused=0');automation.reconcile(c);c.commit()
    import json
    from datetime import datetime,timezone
    from app.mail.templates import seed
    seed(c)
    c.execute("INSERT INTO workflow_runs(id,name,kind,status,configuration_json,created_by,created_at,requested,request_key,campaign_id,organization_id) VALUES('pg-explicit','Controlled','OUTREACH','RUNNING',?,'system',?,1,'pg-explicit',?,?)",(json.dumps({'campaign_id':cid,'pitch_types':['WEBSITE'],'max_hour':10,'max_day':100,'window_start':'00:00','window_end':'23:59','recipient_timezone':False}),now(),cid,PLANEBYTE_ORGANIZATION_ID))
    queued='pg-explicit-message'
    payload={'campaign_id':cid,'pitch_types':['WEBSITE'],'to_address':'contact@planebyte.com','subject':'Controlled transport','body_text':'Controlled transport fixture','confirmation':'SEND','idempotency_key':queued,'message_type':'MANUAL_REPLY'}
    payload['preview_token']=mail.preview(c,pid,'system',payload)['preview_token']
    c.execute("INSERT INTO outreach_run_items(id,run_id,prospect_id,business_id,status,payload_json,idempotency_key,created_at,updated_at,organization_id) VALUES('pg-item','pg-explicit',?,?,'READY',?,?,?,?,?)",(pid,b.id,json.dumps(payload),queued,now(),now(),PLANEBYTE_ORGANIZATION_ID));automation.reconcile(c);c.commit()
    monkeypatch.setattr(automation,'utc_now',lambda:datetime(2026,11,2,10,tzinfo=timezone.utc))
    assert automation.outreach_tick(c,execution_id='pg-explicit')['status']=='SENT'

    # A restarted independent DB connection sees the same durable spacing guard.
    second=PostgresConnection(get_settings().database_url,schema=c.schema)
    try:assert automation.outreach_tick(second,execution_id='pg-explicit')['status']=='PAUSED_OR_WAITING'
    finally:second.close()
    assert transport.send_message.call_count==1
    assert c.execute("SELECT COUNT(*) FROM email_messages WHERE status='SENT'").fetchone()[0]==1


def test_real_postgres_legacy_company_alias_rediscovery(owned_postgres):
    c=owned_postgres;run_migrations(c);ids=[]
    for city in ('London','Bristol'):
        run=PipelineRun(market=city,vertical='home_services',target=1);PipelineRunRepository(c).create(run, organization=PLANEBYTE_ORGANIZATION_ID)
        b=Business(name='Controlled alias company',normalized_name='controlled alias company',vertical='home_services',city=city,domain='controlled-alias.invalid',website='https://controlled-alias.invalid',public_email='contact@controlled-alias.invalid',run_id=run.id)
        BusinessRepository(c).insert(b);ids.append(ProspectRepository(c).observe(b, organization=PLANEBYTE_ORGANIZATION_ID))
        if city=='London':c.execute("DELETE FROM business_identities WHERE evidence_type IN ('COMPANY_DOMAIN','COMPANY_EMAIL')")
    assert ids[0]==ids[1]
    assert c.execute('SELECT COUNT(*) FROM prospects').fetchone()[0]==1
    assert c.execute('SELECT COUNT(*) FROM prospect_observations').fetchone()[0]==2
    assert c.execute("SELECT COUNT(*) FROM business_identities WHERE evidence_type IN ('COMPANY_DOMAIN','COMPANY_EMAIL')").fetchone()[0]==2


def test_manual_schedule_duplicate_dispatch_and_schema10_preserves_rows(owned_postgres,monkeypatch):
    import asyncio,json
    from app.workflows import service
    from app.api.routes.workflows import Run,Schedule,save_schedule
    from app.mail.config import MailSettings
    c=owned_postgres;run_migrations(c)
    assert c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]==len(MIGRATIONS)
    settings=MailSettings(_env_file=None,AUTO_SCAN_ENABLED=True)
    monkeypatch.setattr(service,'mail_settings',lambda:settings)
    calls=[]
    async def start(*args):calls.append(args)
    monkeypatch.setattr('app.api.services.scan_manager.scan_manager.executor.start',start)
    r=Run(name='Disposable schema scan',kind='SCAN',scan_source='OVERTURE',target=2)
    schedule=Schedule(name='Disposable schedule',configuration=r,enabled=False,timezone='Europe/London',frequency='daily',start_at='2026-01-01T06:00:00+00:00')
    sid=save_schedule(c,schedule,current().actor)['id']
    c.execute("UPDATE automation_schedules SET enabled=1,next_run_at='2026-01-01T06:00:00+00:00' WHERE id=?",(sid,));c.execute('UPDATE automation_controls SET scan_paused=0');c.commit()
    assert len(asyncio.run(service.dispatch(c))['scheduled_runs_started'])==1
    assert asyncio.run(service.dispatch(c))['scheduled_runs_started']==[]
    assert len(calls)==1
    assert c.execute('SELECT COUNT(*) FROM automation_schedule_runs').fetchone()[0]==1
    workflow=c.execute('SELECT id FROM workflow_runs').fetchone()[0]
    assert service.detail(c,workflow)['scans'][0]['status']=='QUEUED'
    assert run_migrations(c)==0


def test_campaign_schema11_preserves_history_and_legacy_intent(postgres,monkeypatch):
    from test_campaign_outreach import migration_preservation
    migration_preservation(postgres,monkeypatch)


def test_campaign_operations_postgres_audience_and_messages(owned_postgres):
    from campaign_fixtures import campaign,lead
    from app.workflows.campaigns import audience,campaign_summary
    from app.api.routes import operations
    from app.api.routes.workflows import Run
    from app.workflows import service
    from test_campaign_outreach import message
    c=owned_postgres;run_migrations(c);cid=campaign(c,'Postgres audience')
    b,pid=lead(c,cid,800);lead(c,cid,801,email=False)
    assert audience(c,cid)['qualified']==2
    from tests.workspace_fixtures import workspace_template
    r=service.create(c,Run(kind='OUTREACH',template_id=workspace_template(c),campaign_id=cid,max_day=1).model_dump(),current().actor)
    assert service.detail(c,r['id'])['items_total']==2
    message(c,pid);c.commit()
    result=operations.messages(request=workspace_request(),search='',campaign_id=cid,pitch='',status='',engagement='',reply_state='',sender='',direction='OUTBOUND',created_from='',created_to='',page=1,page_size=25,c=c)
    # Unlinked legacy fixture message remains visible globally, never relabeled as campaign outreach.
    assert result['total']==0
    result=operations.messages(request=workspace_request(),search='',campaign_id='',pitch='',status='',engagement='',reply_state='',sender='',direction='OUTBOUND',created_from='',created_to='',page=1,page_size=25,c=c)
    assert result['total']==1
    assert campaign_summary(c,cid)['total_accounted']==2
    assert operations.views(workspace_request(),c)==[]


def test_foundation_postgres_review_queries(owned_postgres):
    from app.workflows.quality import quality,reviews
    c=owned_postgres;run_migrations(c)
    assert quality(c)['master_leads']==0
    assert reviews(c,search='owner',size=1)['total']==0


def test_source_policies_and_diagnostics_postgres(owned_postgres,monkeypatch):
    import asyncio,json,uuid
    from app.acquisition import service
    from app.acquisition.models import ProcessingOptions
    from app.acquisition.imports import normalize_row
    from app.acquisition.pipeline import prepare_import_batch
    from app.api.routes.foundation import intelligence,qualification
    from app.workflows.campaigns import audience
    c=owned_postgres;run_migrations(c)
    processing=ProcessingOptions();job=service.create_job(c,'FILE_IMPORT',current().actor,str(uuid.uuid4()),{'processing':processing.model_dump()},{})
    cid=service.create_campaign(c,job['id'],'Disposable trusted source',target=2)
    rows=[]
    for name in ('Northstar','Harbour'):
        b=normalize_row({'company_name':name+' Advisory','email':'office@'+name.lower()+'.test','vertical':'Consulting'},processing,'FILE_IMPORT')
        b.source_tags=json.dumps({'field_sources':{'email':{'verification':'OWNER_PROVIDED','value':b.public_email}}});rows.append(b)
    prepare_import_batch(c,job['id'],'controlled',rows,processing);c.commit()
    assert service.refresh_counts(c,job['id'])['qualified_imported']==2
    assert audience(c,cid)['qualified']==2
    result=intelligence(cid,workspace_request(),c);assert result['processing_mode']=='Trusted Import' and result['funnel']['qualified_imported']==2
    assert qualification(workspace_request(),cid,reason='',page=1,page_size=1,c=c)['total']==2
    assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0


@pytest.fixture
def postgres_sheet_export(owned_postgres,monkeypatch):
    """Real independent worker sessions; Google OAuth and writes stay synthetic."""
    import asyncio
    from contextlib import contextmanager
    from urllib.parse import urlsplit,parse_qs
    from unittest.mock import AsyncMock
    from cryptography.fernet import Fernet
    from app.integrations import service,sheet_exports as exports
    from app.acquisition import sheets
    from app.acquisition.config import AcquisitionSettings
    from app.sales import collections
    c=owned_postgres;org=current().organization_id
    monkeypatch.setattr(get_settings(),'heysow_workspace_management_enabled',True)
    monkeypatch.setattr(get_settings(),'heysow_customer_integrations_enabled',True)
    monkeypatch.setattr(get_settings(),'heysow_integration_encryption_key',Fernet.generate_key().decode())
    monkeypatch.setattr('app.acquisition.config.settings',lambda:AcquisitionSettings(_env_file=None,AUTH_GOOGLE_ID='fixture-client',AUTH_GOOGLE_SECRET='fixture-secret',GOOGLE_SHEETS_REDIRECT_URI='https://example.test/acquisition/sheets/callback'))
    state=parse_qs(urlsplit(service.authorize(c,write=True)['authorization_url']).query)['state'][0]
    monkeypatch.setattr(sheets,'token_request',AsyncMock(return_value={'access_token':'synthetic-export-access','refresh_token':'synthetic-export-refresh','scope':service.WRITE_SCOPE,'expires_in':3600}))
    connection=asyncio.run(service.connect(c,state,'controlled-code'))
    run=PipelineRun(market='Controlled city',vertical='dentists',target=2);PipelineRunRepository(c).create(run,organization=org)
    companies=[]
    for name in ('=Controlled export company','Other available company'):
        company=Business(name=name,normalized_name=name.casefold(),vertical='dentists',run_id=run.id,public_email='public@controlled.example')
        BusinessRepository(c).insert(company);ProspectRepository(c).observe(company,organization=org);companies.append(company)
    group=collections.save(c,collections.Named(name='Private export selection'));collections.change_members(c,group['id'],[company.id for company in companies]);c.commit()
    body=exports.Export(list_id=group['id'],spreadsheet='controlled-sheet-id',sheet="Owner's companies",request_id=uuid.uuid4())
    @contextmanager
    def session(path=None):
        worker=PostgresConnection(get_settings().database_url,schema=c.schema)
        try:
            yield worker
            worker.commit()
        except BaseException:
            worker.rollback()
            raise
        finally:worker.close()
    monkeypatch.setattr(exports,'db_session',session)
    return c,connection,body,companies


@pytest.mark.parametrize('kind',['csv','sheets'])
def test_postgres_export_refuses_unavailable_company_without_partial_output(postgres_sheet_export,kind):
    from fastapi import HTTPException
    from app.integrations import sheet_exports as exports
    from app.api.routes.sales import export_list
    c,connection,body,companies=postgres_sheet_export
    # Preserve the canonical member/history while simulating absent company evidence.
    c.execute('UPDATE businesses SET prospect_id=NULL WHERE id=?',(companies[0].id,));c.commit()
    with pytest.raises(HTTPException) as unavailable:
        if kind=='csv':export_list(str(body.list_id),conn=c)
        else:exports.stage(c,connection['id'],body)
    assert unavailable.value.status_code==409
    assert c.execute('SELECT COUNT(*) FROM organization_sheet_exports').fetchone()[0]==0
    assert c.execute('SELECT COUNT(*) FROM lead_list_members').fetchone()[0]==2


def test_postgres_sheet_export_company_becoming_unavailable_during_snapshot_is_safe(postgres_sheet_export,monkeypatch):
    from fastapi import HTTPException
    from app.integrations import sheet_exports as exports
    from app.sales import collections
    c,connection,body,companies=postgres_sheet_export
    detail=collections.detail
    def changed(*args,**kwargs):
        result=detail(*args,**kwargs)
        other=PostgresConnection(get_settings().database_url,schema=c.schema)
        try:
            other.execute('UPDATE businesses SET run_id=NULL WHERE id=?',(companies[0].id,));other.commit()
        finally:other.close()
        return result
    monkeypatch.setattr(collections,'detail',changed)
    with pytest.raises(HTTPException) as unavailable:exports.stage(c,connection['id'],body)
    assert unavailable.value.status_code==409
    assert c.execute('SELECT COUNT(*) FROM organization_sheet_exports').fetchone()[0]==0


def test_postgres_csv_export_preserves_formula_safety_and_denies_foreign_workspace(postgres_sheet_export):
    import csv,io
    from concurrent.futures import ThreadPoolExecutor
    from fastapi import HTTPException
    from app.api.routes.sales import export_list
    from app.api.organization import create_organization
    from app.platform.context import workspace_scope
    c,_,body,_=postgres_sheet_export
    response=export_list(str(body.list_id),conn=c)
    rows=list(csv.reader(io.StringIO(response.body.decode())))
    assert len(rows)==3 and rows[1][1]=="'=Controlled export company"
    assert response.headers['cache-control']=='private, no-store'
    actor=current().actor;other_org=create_organization(c,actor,'Foreign export workspace')['organization_id'];c.commit()
    def foreign():
        other=PostgresConnection(get_settings().database_url,schema=c.schema)
        try:
            with workspace_scope(other,actor,other_org):
                with pytest.raises(HTTPException) as denied:export_list(str(body.list_id),conn=other)
                assert denied.value.status_code==404
        finally:other.close()
    with ThreadPoolExecutor(max_workers=1) as pool:pool.submit(foreign).result(timeout=8)


def test_postgres_export_duplicate_workers_reserve_once(postgres_sheet_export):
    import asyncio,json,threading
    from concurrent.futures import ThreadPoolExecutor
    import httpx
    from app.integrations import sheet_exports as exports
    c,connection,body,_=postgres_sheet_export
    job=exports.stage(c,connection['id'],body);exports.approve(c,job['id'],job['review_digest'],'OVERWRITE_REVIEWED_RANGE');c.commit()
    started=threading.Event();release=threading.Event();calls=[]
    def receive(request):
        calls.append(json.loads(request.content));started.set();assert release.wait(8)
        return httpx.Response(200,json={'updatedCells':24})
    transport=httpx.MockTransport(receive)
    with ThreadPoolExecutor(max_workers=1) as pool:
        first=pool.submit(lambda:asyncio.run(exports.execute(job['id'],transport=transport)))
        try:
            assert started.wait(8)
            asyncio.run(exports.execute(job['id'],transport=transport))
        finally:release.set()
        first.result(timeout=8)
    assert len(calls)==1 and calls[0]['values'][1][0].startswith('=')
    result=exports.owned(c,job['id']);assert result['status']=='COMPLETED' and result['attempts']==1


def test_postgres_export_stale_worker_cannot_write_after_reviewed_lease_recovery(postgres_sheet_export,monkeypatch):
    import asyncio,threading
    from concurrent.futures import ThreadPoolExecutor
    import httpx
    from app.integrations import service,sheet_exports as exports
    c,connection,body,_=postgres_sheet_export
    job=exports.stage(c,connection['id'],body);exports.approve(c,job['id'],job['review_digest'],'OVERWRITE_REVIEWED_RANGE');c.commit()
    paused=threading.Event();release=threading.Event();calls=[];access=service.access_token;main=threading.current_thread()
    async def delayed(db,key):
        result=await access(db,key)
        if threading.current_thread() is not main:
            paused.set();assert release.wait(8)
        return result
    monkeypatch.setattr(service,'access_token',delayed)
    def receive(request):calls.append(1);return httpx.Response(200,json={'updatedCells':24})
    transport=httpx.MockTransport(receive)
    with ThreadPoolExecutor(max_workers=1) as pool:
        stale=pool.submit(lambda:asyncio.run(exports.execute(job['id'],transport=transport)))
        try:
            assert paused.wait(8)
            c.execute("UPDATE organization_sheet_exports SET lease_until='2000-01-01T00:00:00+00:00' WHERE id=?",(job['id'],));c.commit()
            exports.retry(c,job['id'],job['review_digest'],'OVERWRITE_REVIEWED_RANGE');c.commit()
            asyncio.run(exports.execute(job['id'],transport=transport))
        finally:release.set()
        stale.result(timeout=8)
    result=exports.owned(c,job['id']);assert result['status']=='COMPLETED' and result['attempts']==2
    assert len(calls)==1


def test_postgres_export_global_worker_limit_keeps_third_job_queued(postgres_sheet_export):
    import asyncio,threading
    from concurrent.futures import ThreadPoolExecutor
    import httpx
    from app.integrations import sheet_exports as exports
    c,connection,body,_=postgres_sheet_export;jobs=[]
    for _ in range(3):
        job=exports.stage(c,connection['id'],body.model_copy(update={'request_id':uuid.uuid4()}));exports.approve(c,job['id'],job['review_digest'],'OVERWRITE_REVIEWED_RANGE');jobs.append(job)
    c.commit();started=threading.Event();release=threading.Event();guard=threading.Lock();calls=[]
    def receive(request):
        with guard:
            calls.append(1)
            if len(calls)==2:started.set()
        assert release.wait(8)
        return httpx.Response(200,json={'updatedCells':24})
    transport=httpx.MockTransport(receive)
    with ThreadPoolExecutor(max_workers=2) as pool:
        active=[pool.submit(lambda key=job['id']:asyncio.run(exports.execute(key,transport=transport))) for job in jobs[:2]]
        try:
            assert started.wait(8)
            asyncio.run(exports.execute(jobs[2]['id'],transport=transport))
            queued=exports.owned(c,jobs[2]['id']);assert queued['status']=='QUEUED' and queued['attempts']==0
        finally:release.set()
        for worker in active:worker.result(timeout=8)
    assert len(calls)==2
    asyncio.run(exports.execute(jobs[2]['id'],transport=httpx.MockTransport(lambda request:httpx.Response(200,json={'updatedCells':24}))))
    assert exports.owned(c,jobs[2]['id'])['status']=='COMPLETED'


@pytest.mark.parametrize('condition',['expired_lease','active_lease','exhausted','expired_review'])
def test_postgres_export_crash_recovery_requires_review_and_respects_bounds(postgres_sheet_export,condition):
    import asyncio,json
    import httpx
    from fastapi import HTTPException
    from app.integrations import sheet_exports as exports
    c,connection,body,_=postgres_sheet_export
    job=exports.stage(c,connection['id'],body);exports.approve(c,job['id'],job['review_digest'],'OVERWRITE_REVIEWED_RANGE')
    attempts=3 if condition=='exhausted' else 1
    lease='2099-01-01T00:00:00+00:00' if condition=='active_lease' else '2000-01-01T00:00:00+00:00'
    c.execute("UPDATE organization_sheet_exports SET status='RUNNING',attempts=?,lease_owner='lost-worker',lease_until=? WHERE id=?",(attempts,lease,job['id']))
    if condition=='expired_review':c.execute("UPDATE organization_sheet_exports SET expires_at='2000-01-01T00:00:00+00:00' WHERE id=?",(job['id'],))
    c.commit();calls=[]
    def receive(request):calls.append(json.loads(request.content));return httpx.Response(200,json={'updatedCells':24})
    transport=httpx.MockTransport(receive)
    asyncio.run(exports.execute(job['id'],transport=transport));assert calls==[]
    if condition!='expired_lease':
        with pytest.raises(HTTPException) as denied:exports.retry(c,job['id'],job['review_digest'],'OVERWRITE_REVIEWED_RANGE')
        assert denied.value.status_code==409
    else:
        with pytest.raises(HTTPException):exports.retry(c,job['id'],'0'*64,'OVERWRITE_REVIEWED_RANGE')
        exports.retry(c,job['id'],job['review_digest'],'OVERWRITE_REVIEWED_RANGE');c.commit()
        asyncio.run(exports.execute(job['id'],transport=transport))
        result=exports.owned(c,job['id']);assert result['status']=='COMPLETED' and result['attempts']==2
        assert len(calls)==1 and calls[0]['range']==job['target_range']
    assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0


def test_postgres_webhook_independent_reservation_and_final_attempt_recovery(owned_postgres,monkeypatch):
    import asyncio,threading
    from contextlib import contextmanager
    from concurrent.futures import ThreadPoolExecutor
    import httpx
    from cryptography.fernet import Fernet
    from app.webhooks import service,worker
    from app.platform.context import job_scope
    c=owned_postgres;org=current().organization_id
    monkeypatch.setattr(get_settings(),'heysow_webhooks_enabled',True)
    monkeypatch.setattr(get_settings(),'heysow_integration_encryption_key',Fernet.generate_key().decode())
    key=service.save(c,service.Endpoint(name='Private recovery receiver',url='https://receiver.example.com/events',topics=['company.created']))['endpoint']['id']
    run=PipelineRun(market='Controlled city',vertical='dentists',target=1);PipelineRunRepository(c).create(run,organization=org)
    company=Business(name='Private webhook company',normalized_name='private webhook company',vertical='dentists',run_id=run.id)
    BusinessRepository(c).insert(company);ProspectRepository(c).observe(company,organization=org);c.commit()
    delivery=service.history(c,key)['items'][0]['id'];c.commit()
    @contextmanager
    def session(path=None):
        other=PostgresConnection(get_settings().database_url,schema=c.schema)
        try:
            yield other
            other.commit()
        finally:other.close()
    monkeypatch.setattr(worker,'db_session',session)
    started=threading.Event();release=threading.Event();calls=[]
    def receive(request):calls.append(1);started.set();assert release.wait(8);return httpx.Response(204)
    transport=httpx.MockTransport(receive)
    def deliver():
        with session() as other:
            with job_scope(other,'webhook',key):return asyncio.run(worker.deliver(other,key,delivery,transport))
    with ThreadPoolExecutor(max_workers=1) as pool:
        first=pool.submit(deliver)
        try:
            assert started.wait(8)
            assert deliver()=='NOT_DUE'
        finally:release.set()
        assert first.result(timeout=8)=='DELIVERED'
    assert len(calls)==1
    c.execute("UPDATE webhook_deliveries SET status='DELIVERING',attempts=5,lease_owner='lost-worker',lease_until='2000-01-01T00:00:00+00:00' WHERE id=?",(delivery,));c.commit()
    asyncio.run(worker.execute_async(key,transport=transport))
    result=service.history(c,key)['items'][0]
    assert result['status']=='FAILED' and result['last_error_code']=='DELIVERY_OUTCOME_UNKNOWN'
    assert result['attempts']==5 and len(calls)==1


def test_firecrawl_no_email_counter_uses_bound_like_pattern(owned_postgres):
    import uuid
    from app.acquisition import service
    from app.acquisition.worker import record_no_email
    c=owned_postgres;run_migrations(c)
    job=service.create_job(c,'FIRECRAWL',current().actor,str(uuid.uuid4()),{},{});service.create_campaign(c,job['id'],'Disposable no-email discovery',target=5)
    record_no_email(c,job['id'],'https://no-email-one.invalid')
    record_no_email(c,job['id'],'https://no-email-one.invalid')
    record_no_email(c,job['id'],'https://no-email-two.invalid')
    counts=service.refresh_counts(c,job['id']);assert counts['no_email']==2 and counts['qualified']==0
    assert c.execute('SELECT COUNT(*) FROM businesses').fetchone()[0]==0
    assert c.execute('SELECT COUNT(*) FROM website_profiles').fetchone()[0]==0
    assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0


def test_real_postgres_experiment_additive_attribution_and_schedules(postgres,monkeypatch,request):
 import json
 from app.database import migrations
 from campaign_fixtures import campaign,lead
 from app.experiments import service,runtime
 c=postgres;full=list(migrations.MIGRATIONS)
 monkeypatch.setattr(migrations,'MIGRATIONS',full[:13]);run_migrations(c);cid=campaign(c);b,pid=lead(c,cid,8811)
 c.execute("UPDATE scan_campaigns SET status='RUNNING' WHERE id=?",(cid,));c.commit()
 before={table:[dict(r) for r in c.execute('SELECT * FROM '+table).fetchall()] for table in ('scan_campaigns','prospects','businesses','automation_controls')}
 monkeypatch.setattr(migrations,'MIGRATIONS',full);assert run_migrations(c)==len(full)-13;assert run_migrations(c)==0
 for table,rows in before.items():
  after=[dict(r) for r in c.execute('SELECT * FROM '+table).fetchall()]
  assert len(after)==len(rows)
  assert [{key:row[key] for key in original} for row,original in zip(after,rows)]==rows
 bind_internal_workspace(c,request)
 monkeypatch.setattr(get_settings(),'heysow_internal_experiments_enabled',True)
 service.setup(c,'owner');service.setup(c,'owner');runtime.create_schedules(c,service.EXPERIMENT_ID,'owner');runtime.create_schedules(c,service.EXPERIMENT_ID,'owner');c.commit()
 assert c.execute('SELECT copy_started_at,copy_attempts FROM experiment_members LIMIT 1').fetchone() is None
 assert c.execute('SELECT COUNT(*) FROM experiment_segments').fetchone()[0]==25
 assert c.execute('SELECT COUNT(*) FROM automation_schedules').fetchone()[0]==50
 assert service.get(c)['status']=='SETUP'
 assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0
 from app.experiments.analytics import dashboard
 d=dashboard(c);assert d['totals']['target']==2500 and d['totals']['sent']==0 and d['provider_capacity']['remaining_is_counted_not_provider_guaranteed']
 assert {json.loads(r[0])['scan_source'] for r in c.execute('SELECT configuration_json FROM automation_schedules').fetchall()}=={'OVERTURE','FIRECRAWL'}


def test_real_postgres_vertex_copy_cache_circuit_and_attribution(owned_postgres,monkeypatch):
 monkeypatch.setattr(get_settings(),"heysow_internal_experiments_enabled",True)
 import asyncio,json
 from app.experiments import service
 from app.experiments.copy_batch import synthetic_leads,generate_personalized_copy_batch,status
 from app.acquisition.ai_router import AIProviderRouter
 from app.acquisition.config import AcquisitionSettings
 from app.acquisition import ai
 c=owned_postgres;run_migrations(c);service.setup(c,'owner');c.commit()
 class Provider:
  def __init__(self,name,error=None):self.provider_name=name;self.model='configured-model';self.error=error;self.calls=0
  async def structured(self,instruction,payload,model,**kw):
   self.calls+=1
   if self.error:raise self.error
   return {'results':[{'lead_id':v['lead_id'],'subject':v['allowed_subjects'][0],'personalized_opening':v['allowed_openings'][0],'finding_1_copy':v['allowed_finding_1'][0],'finding_2_copy':v['allowed_finding_2'][0],'optional_bridge':''} for v in reversed(payload['leads'])]}
 s=AcquisitionSettings(_env_file=None,AI_PRIMARY_PROVIDER='vertex',VERTEX_AI_ENABLED=True,GEMINI_API_KEY='fixture')
 v=Provider('VERTEX_AI');g=Provider('GEMINI_API');router=AIProviderRouter(s,c=c,providers=[v,g]);inputs=synthetic_leads(c,5)
 first=asyncio.run(generate_personalized_copy_batch(c,inputs,'owner',client=router));assert first['metrics']['ai_generated_leads']==5 and all(r['copy_provider']=='VERTEX_AI' for r in first['results'].values())
 second=asyncio.run(generate_personalized_copy_batch(c,inputs,'owner',client=router));assert second['metrics']['cache_hits']==5 and v.calls==1 and g.calls==0
 v.error=ai.AiRateLimited('QUOTA_EXHAUSTED',3600);g.error=ai.AiProviderError(402)
 failed=asyncio.run(generate_personalized_copy_batch(c,synthetic_leads(c,5),'owner',client=router));assert failed['metrics']['deterministic_fallback_leads']==5
 assert router.states()['VERTEX_AI']['status']=='DEGRADED' and router.states()['GEMINI_API']['status']=='DEGRADED'
 assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0
 assert c.execute("SELECT COUNT(*) FROM acquisition_ai_cache WHERE task=?",('PERSONALIZED_COPY_BATCH_V2',)).fetchone()[0]==10


def concurrent_connections(c, operation):
    """Independent transactions, not a shared connection disguised as concurrency."""
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from fastapi import HTTPException
    barrier=Barrier(2)
    c.commit()
    def run(index):
        db=PostgresConnection(get_settings().database_url,schema=c.schema)
        try:
            barrier.wait(timeout=5)
            result=operation(db,index)
            db.commit()
            return result
        except HTTPException as error:
            db.rollback()
            return error.status_code
        finally:db.close()
    with ThreadPoolExecutor(max_workers=2) as pool:
        return list(pool.map(run,range(2)))


def test_postgres_concurrent_workspace_creation_has_one_owner_and_request(owned_postgres):
    from app.platform.workspaces import create_workspace,WorkspaceCreate
    c=owned_postgres
    body=WorkspaceCreate(name='Concurrent company',request_id=uuid.uuid4())
    def create(db,index):return create_workspace(db,'new-owner@example.com',body)
    results=concurrent_connections(c,create)
    assert len({result['organization_id'] for result in results})==1
    assert sorted(result['reused'] for result in results)==[False,True]
    org=results[0]['organization_id']
    assert c.execute('SELECT COUNT(*) FROM workspace_creation_requests WHERE organization_id=?',(org,)).fetchone()[0]==1
    assert c.execute("SELECT COUNT(*) FROM organization_memberships WHERE organization_id=? AND role='OWNER' AND status='ACTIVE'",(org,)).fetchone()[0]==1
    assert c.execute('SELECT COUNT(*) FROM prospects WHERE organization_id=?',(org,)).fetchone()[0]==0


def test_postgres_concurrent_self_demotion_preserves_last_owner(owned_postgres):
    from app.platform.context import workspace_scope
    from app.platform.memberships import change_role
    c=owned_postgres;org=current().organization_id
    change_role(c,current().actor,'second-owner@example.com','OWNER')
    actors=[current().actor,'second-owner@example.com']
    def demote(db,index):
        with workspace_scope(db,actors[index],org):
            change_role(db,actors[index],actors[index],'MEMBER')
            return 'SAVED'
    results=concurrent_connections(c,demote)
    assert sorted(map(str,results))==['409','SAVED']
    assert c.execute("SELECT COUNT(*) FROM organization_memberships WHERE organization_id=? AND role='OWNER' AND status='ACTIVE'",(org,)).fetchone()[0]==1


def test_postgres_concurrent_invitation_acceptance_grants_once(owned_postgres):
    from app.platform import invitations as inv
    c=owned_postgres;org=current().organization_id
    invitation=inv.create(c,inv.InviteCreate(email='recipient@example.com',role='VIEWER'))
    def accept(db,index):return inv.respond(db,'recipient@example.com',inv.InviteRespond(token=invitation['token'],action='ACCEPT'))
    results=concurrent_connections(c,accept)
    assert len([item for item in results if isinstance(item,dict) and item['status']=='ACCEPTED'])==1
    assert results.count(409)==1
    assert c.execute("SELECT COUNT(*) FROM organization_memberships WHERE organization_id=? AND user_id='recipient@example.com'",(org,)).fetchone()[0]==1
    assert c.execute("SELECT COUNT(*) FROM workspace_notifications WHERE organization_id=? AND entity_id=? AND kind='INVITATION_ACCEPTED'",(org,invitation['id'])).fetchone()[0]==1


def test_postgres_concurrent_icp_edits_preserve_one_revision(owned_postgres):
    from app.icp import service
    from app.icp.models import Create,Update
    from app.platform.context import workspace_scope
    c=owned_postgres;org=current().organization_id;actor=current().actor
    profile=service.create(c,Create(name='Dental practices',criteria={'company':{'industries':['Dentistry']}},request_id=uuid.uuid4()))
    body={key:profile[key] for key in ('name','description','criteria','status','revision')}
    def update(db,index):
        with workspace_scope(db,actor,org):
            return service.update(db,str(profile['id']),Update.model_validate({**body,'name':'Concurrent draft '+str(index)}))
    results=concurrent_connections(c,update)
    assert results.count(409)==1
    assert len([item for item in results if isinstance(item,dict) and item['revision']==2])==1
    assert c.execute('SELECT COUNT(*) FROM icp_versions WHERE icp_id=? AND organization_id=?',(str(profile['id']),org)).fetchone()[0]==2
    assert c.execute('SELECT COUNT(*) FROM pipeline_runs').fetchone()[0]==0
    assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0


def test_postgres_concurrent_domain_proof_reserves_one_dns_call(owned_postgres,monkeypatch):
    import asyncio
    from threading import Event,Lock
    from app.platform import domains
    from app.platform.context import workspace_scope
    c=owned_postgres;org=current().organization_id;actor=current().actor
    proof=domains.challenge(c,domains.DomainCreate(domain='example.com'))
    calls=[];lock=Lock();release=Event()
    def resolve(name):
        with lock:calls.append(name)
        release.wait(timeout=1)
        return [proof['record_value']]
    monkeypatch.setattr(domains,'_resolve',resolve)
    def verify(db,index):
        with workspace_scope(db,actor,org):return asyncio.run(domains.verify(db,proof['id']))
    results=concurrent_connections(c,verify)
    release.set()
    assert results.count(429)==1
    assert len([item for item in results if isinstance(item,dict) and item['status']=='VERIFIED'])==1
    assert calls==['_heysow-verify.example.com']
    row=c.execute('SELECT status,attempts FROM organization_domains WHERE id=? AND organization_id=?',(proof['id'],org)).fetchone()
    assert row['status']=='VERIFIED' and row['attempts']==1


def test_postgres_restricted_preupgrade_backup_restores_and_migrates(postgres,tmp_path,monkeypatch):
    import subprocess
    from app.database import migrations
    from app.platform.context import workspace_scope
    from app.mail import contacted
    c=postgres;all_migrations=migrations.MIGRATIONS
    monkeypatch.setattr(migrations,'MIGRATIONS',all_migrations[:22]);run_migrations(c)
    owner=c.execute('SELECT created_by_user_id FROM organizations WHERE id=?',(PLANEBYTE_ORGANIZATION_ID,)).fetchone()[0]
    with workspace_scope(c,owner,PLANEBYTE_ORGANIZATION_ID):
        contacted.record(c,message_id='restore-history',email='retained@example.com',sent_at='2026-11-06T00:00:00+00:00')
    tables=('organizations','organization_memberships','organization_settings','contacted_recipients','organization_onboarding')
    before={table:[dict(row) for row in c.execute('SELECT * FROM '+table).fetchall()] for table in tables};c.commit()
    tools=Path(os.environ.get('HEYSOW_PG_TEST_BIN',str(Path(__file__).resolve().parents[2]/'data/artifacts/postgres-local/install/bin')))
    assert (tools/'pg_dump').is_file() and (tools/'psql').is_file(), 'Provide official PostgreSQL client tools for restore acceptance'
    from psycopg.conninfo import conninfo_to_dict
    parameters=conninfo_to_dict(get_settings().database_url)
    names={'dbname':'PGDATABASE','host':'PGHOST','hostaddr':'PGHOSTADDR','port':'PGPORT','user':'PGUSER','password':'PGPASSWORD','sslmode':'PGSSLMODE','sslrootcert':'PGSSLROOTCERT','sslcert':'PGSSLCERT','sslkey':'PGSSLKEY','channel_binding':'PGCHANNELBINDING','connect_timeout':'PGCONNECT_TIMEOUT','options':'PGOPTIONS'}
    assert set(parameters)<=set(names), 'Explicit PostgreSQL client environment mapping required'
    # Connection credentials remain in process memory, never CLI arguments/logs.
    environment={key:value for key,value in os.environ.items() if not key.startswith('PG')}
    environment.update({names[key]:value for key,value in parameters.items()})
    backup=tmp_path/'before.sql'
    with backup.open('wb') as output:
        result=subprocess.run([str(tools/'pg_dump'),'--no-owner','--no-acl','--schema='+c.schema],env=environment,stdout=output,stderr=subprocess.PIPE,timeout=30)
    assert result.returncode==0, 'Disposable schema backup failed'
    backup.chmod(0o600)
    restored_schema='leadengine_restore_'+uuid.uuid4().hex
    restored_sql=tmp_path/'restore.sql';restored_sql.write_text(backup.read_text().replace(c.schema,restored_schema));restored_sql.chmod(0o600)
    # Apply only the dump of this random test schema in another random schema.
    result=subprocess.run([str(tools/'psql'),'--no-psqlrc','--set=ON_ERROR_STOP=1','--single-transaction','--file='+str(restored_sql)],env=environment,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
    assert result.returncode==0, 'Isolated schema restore failed'
    restored=PostgresConnection(get_settings().database_url,schema=restored_schema)
    try:
        assert restored.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]==22
        for table,rows in before.items():assert [dict(row) for row in restored.execute('SELECT * FROM '+table).fetchall()]==rows
        monkeypatch.setattr(migrations,'MIGRATIONS',all_migrations)
        assert run_migrations(c)==len(all_migrations)-22
        assert run_migrations(restored)==len(all_migrations)-22
        assert run_migrations(restored)==0
        verify_schema(restored)
        for table,rows in before.items():assert [dict(row) for row in restored.execute('SELECT * FROM '+table).fetchall()]==rows
    finally:
        restored.close()
        with psycopg.connect(get_settings().database_url,autocommit=True) as admin:
            admin.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(restored_schema)))


@pytest.fixture
def customer_connection(postgres,monkeypatch):
    import asyncio
    from cryptography.fernet import Fernet
    from unittest.mock import AsyncMock
    from app.acquisition.config import AcquisitionSettings
    from app.acquisition import sheets
    from app.integrations import service
    from app.api.organization import create_organization
    from app.platform.context import workspace_scope
    from urllib.parse import urlsplit,parse_qs
    settings=get_settings();monkeypatch.setattr(settings,'heysow_workspace_management_enabled',True);monkeypatch.setattr(settings,'heysow_customer_integrations_enabled',True)
    monkeypatch.setattr(settings,'heysow_integration_encryption_key',Fernet.generate_key().decode())
    provider_config=AcquisitionSettings(_env_file=None,AUTH_GOOGLE_ID='fixture-client',AUTH_GOOGLE_SECRET='fixture-secret')
    monkeypatch.setattr('app.acquisition.config.settings',lambda:provider_config)
    run_migrations(postgres);actor='customer-pg@example.com'
    monkeypatch.setattr(settings,'allowed_user_emails','a@example.com,'+actor)
    org=create_organization(postgres,actor,'Customer connection')['organization_id'];postgres.commit()
    tokens={'access_token':'pg-controlled-access','refresh_token':'pg-controlled-refresh','expires_in':3600,'scope':sheets.SCOPE}
    with workspace_scope(postgres,actor,org):
        authorization=service.authorize(postgres);postgres.commit()
        state=parse_qs(urlsplit(authorization['authorization_url']).query)['state'][0]
        monkeypatch.setattr(sheets,'token_request',AsyncMock(return_value=tokens))
        connected=asyncio.run(service.connect(postgres,state,'controlled-code'));postgres.commit()
    return postgres,org,actor,connected['id'],tokens


def test_postgres_customer_connection_failure_replay_and_disconnect(customer_connection,monkeypatch):
    import asyncio
    from unittest.mock import AsyncMock
    from urllib.parse import urlsplit,parse_qs
    from fastapi import HTTPException
    from app.acquisition import sheets
    from app.integrations import service
    from app.platform.context import workspace_scope
    c,org,actor,key,tokens=customer_connection
    with workspace_scope(c,actor,org):
        state=parse_qs(urlsplit(service.authorize(c)['authorization_url']).query)['state'][0];c.commit()
        provider=AsyncMock(side_effect=sheets.SheetsUnavailable('controlled failure'));monkeypatch.setattr(sheets,'token_request',provider)
        with pytest.raises(HTTPException) as failed:asyncio.run(service.connect(c,state,'controlled-code'))
        assert failed.value.status_code==503
        with pytest.raises(HTTPException):asyncio.run(service.connect(c,state,'controlled-code'))
        assert provider.call_count==1 and service.owned(c,key)['last_error_code']=='OAUTH_UNAVAILABLE'
        # Failed reconnection preserves the preceding valid connection.
        assert service.owned(c,key)['status']=='CONNECTED'
        service.disconnect(c,key);c.commit()
        assert service.owned(c,key)['credentials_ciphertext'] is None
        assert c.execute('SELECT COUNT(*) FROM acquisition_google_connections').fetchone()[0]==0


def test_postgres_customer_refresh_lease_concurrency_and_error_cooldown(customer_connection,monkeypatch):
    import asyncio
    from unittest.mock import AsyncMock
    from threading import Event
    from fastapi import HTTPException
    from app.acquisition import sheets
    from app.integrations import service
    from app.integrations.crypto import seal
    from app.platform.context import workspace_scope
    c,org,actor,key,tokens=customer_connection
    def expire():
        with workspace_scope(c,actor,org):
            row=service.owned(c,key);value=service.token_value(tokens);value['expires_at']='2000-01-01T00:00:00+00:00'
            c.execute('UPDATE organization_integrations SET credentials_ciphertext=? WHERE id=? AND organization_id=?',(seal(value,**service.context(row,'CREDENTIALS')),key,org));c.commit()
    expire();calls=[];release=Event()
    async def refresh(payload):calls.append(payload);release.wait(timeout=1);return {**tokens,'access_token':'pg-renewed-access'}
    monkeypatch.setattr(sheets,'token_request',refresh)
    def access(db,index):
        with workspace_scope(db,actor,org):return asyncio.run(service.access_token(db,key))[0]
    results=concurrent_connections(c,access);release.set()
    assert results.count(429)==1 and results.count('pg-renewed-access')==1 and len(calls)==1
    expire();provider=AsyncMock(side_effect=sheets.SheetsUnavailable('controlled outage'));monkeypatch.setattr(sheets,'token_request',provider)
    with workspace_scope(c,actor,org):
        with pytest.raises(HTTPException) as failed:asyncio.run(service.access_token(c,key))
        assert failed.value.status_code==503
        with pytest.raises(HTTPException) as cooldown:asyncio.run(service.access_token(c,key))
        assert cooldown.value.status_code==429 and provider.call_count==1
        assert service.owned(c,key)['last_error_code']=='TOKEN_REFRESH_UNAVAILABLE'


def test_postgres_saved_search_contact_and_enrichment_records(owned_postgres,monkeypatch):
    """Exercise new SQL through the real adapter, not SQLite cursor semantics."""
    import asyncio,json
    from app.prospecting import searches
    from app.people import service as people
    from app.intelligence import jobs,dispatch
    c=owned_postgres;org=current().organization_id
    search_body=searches.SaveSearch(name='Controlled global search',configuration={'kind':'SCAN','countries':['United States','United Kingdom'],'verticals':['dentists']})
    search=searches.save(c,search_body)
    assert searches.save(c,search_body)['id']==search['id']
    assert searches.list_searches(c)['total']==1
    run=PipelineRun(market='Bristol',vertical='dentists',target=1)
    PipelineRunRepository(c).create(run,organization=org)
    b=Business(name='Controlled company',normalized_name='controlled company',vertical='dentists',run_id=run.id,website='https://controlled.example')
    BusinessRepository(c).insert(b);ProspectRepository(c).observe(b,organization=org)
    person=people.save(c,b.id,people.Person(name='Avery Example',role='CTO',work_email='avery@controlled.example'))
    assert people.note(c,person['id'],'Reviewed public evidence')['notes'][0]['body']=='Reviewed public evidence'
    assert people.get(c,person['id'])['lists']==[]
    job=jobs.create(c,jobs.Start(kind='CONTACT_VERIFY',resource_ids=[person['id']]))
    assert jobs.detail(c,job['id'])['counts']=={'QUEUED':1}
    dispatched=[]
    async def launch(key):dispatched.append(key)
    monkeypatch.setattr(dispatch,'launch',launch);asyncio.run(dispatch.dispatch_owned(c));assert dispatched==[job['id']]
    c.execute("UPDATE intelligence_jobs SET status='RUNNING',lease_owner='controlled-lease' WHERE id=?",(job['id'],))
    row=jobs.owned(c,job['id']);item=jobs.detail(c,job['id'])['items'][0]
    monkeypatch.setattr('app.people.verification.check',lambda email:{'state':'MX_AVAILABLE','recipient_delivery_verified':False,'mx_available':True})
    result=asyncio.run(jobs.run_item(c,row,item,job['configuration']))
    assert result['state']=='MX_AVAILABLE' and not result['recipient_delivery_verified']
    person=people.get(c,person['id']);assert person['checked_at'] and person['revision']==2
    changed=people.save(c,b.id,people.Person(name=person['name'],work_email='new@controlled.example',revision=2),person['id'])
    assert changed['checked_at'] is None and changed['verification_state']=='UNKNOWN'
    assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0


def test_postgres_assistant_approval_and_private_history(owned_postgres,monkeypatch):
    import asyncio
    from app.assistant import service,tools
    from app.intelligence import jobs
    from unittest.mock import AsyncMock
    c=owned_postgres;monkeypatch.setattr(get_settings(),'heysow_lead_assistant_enabled',True)
    provider=AsyncMock();provider.structured.return_value=service.Plan(proposed_actions=[{'kind':'save_search','arguments':{'name':'Postgres reviewed search','configuration':{'kind':'SCAN'}}}])
    monkeypatch.setattr('app.acquisition.ai.provider',lambda _:provider);monkeypatch.setattr('app.platform.ai_usage.reserve',lambda *a,**k:None)
    turn=service.create(c,service.Turn(prompt='Suggest a saved search with no scan'))
    assert asyncio.run(service.process(c,turn['id']))['status']=='COMPLETE'
    detail=service.detail(c,turn['conversation_id']);action=detail['turns'][0]['actions'][0]
    assert service.listing(c)['items'][0]['id']==turn['conversation_id']
    assert service.action(c,action['id'],'approve')['status']=='APPLIED'
    assert service.action(c,action['id'],'approve')['status']=='APPLIED'
    assert c.execute('SELECT COUNT(*) FROM discovery_searches').fetchone()[0]==1
    assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0


def test_postgres_sales_lists_and_tasks_preserve_history(owned_postgres):
    from app.sales import collections,tasks
    c=owned_postgres;org=current().organization_id
    run=PipelineRun(market='Controlled city',vertical='dentists',target=1);PipelineRunRepository(c).create(run,organization=org)
    b=Business(name='Controlled sales company',normalized_name='controlled sales company',vertical='dentists',run_id=run.id);BusinessRepository(c).insert(b);ProspectRepository(c).observe(b,organization=org)
    listing=collections.save(c,collections.Named(name='Postgres sales list'));collections.change_members(c,listing['id'],[b.id])
    assert collections.detail(c,listing['id'])['company_count']==1
    assert collections.listing(c)['items'][0]['member_count']==1
    collections.archive(c,listing['id'],collections.get(c,listing['id'])['revision'])
    assert collections.detail(c,listing['id'])['company_count']==1 and collections.listing(c)['total']==0
    task=tasks.create(c,tasks.Task(business_id=b.id,title='Review company',task_type='REVIEW',due_at='2026-12-01T09:00:00Z'))
    assert tasks.listing(c)['items'][0]['title']=='Review company'
    assert tasks.update(c,task['id'],1,'COMPLETED')['revision']==2
    assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0


def test_postgres_reviewed_icp_provenance_snapshot_and_task_edits(owned_postgres,monkeypatch):
    import json
    from app.icp import builder,service as profiles
    from app.icp.ai import Draft
    from app.icp.models import Create
    from app.sales import tasks
    from app.workflows import service as workflows
    from app.api.routes.workflows import Run
    c=owned_postgres;org=current().organization_id
    monkeypatch.setattr(builder.ai,'status',lambda c:{'enabled':True,'configured':True})
    draft=Draft(name='Controlled prospects',criteria={'company':{'countries':['GB'],'industries':['Dentistry']}})
    output=builder.Suggestions(candidates=[builder.Candidate(draft=draft,reason='Owner-described dental targeting for review.')])
    receipt=builder._persist(c,'AI_ASSISTED',{'prompt':'Find dental clinics in the UK.'},output,False);c.commit()
    duplicate=builder._persist(c,'AI_ASSISTED',{'prompt':'Find dental clinics in the UK.'},output,True)
    assert duplicate['proposal_id']==receipt['proposal_id']
    profile=profiles.create(c,Create(**draft.model_dump(exclude={'status'}),status='ACTIVE',request_id=uuid.uuid4(),ai_proposal_id=receipt['proposal_id']))
    assert profile['generation_source']=='AI_ASSISTED'
    workflow=workflows.create(c,Run(kind='SCAN',icp_id=profile['id']).model_dump(mode='json'),current().actor)
    assert json.loads(workflow['configuration_json'])['icp_snapshot']['revision']==1
    run=PipelineRun(market='Controlled city',vertical='dentists',target=1);PipelineRunRepository(c).create(run,organization=org)
    business=Business(name='Controlled edit company',normalized_name='controlled edit company',vertical='dentists',run_id=run.id)
    BusinessRepository(c).insert(business);ProspectRepository(c).observe(business,organization=org)
    task=tasks.create(c,tasks.Task(business_id=business.id,title='Review company',task_type='REVIEW',due_at='2026-12-01T09:00:00Z'))
    edited=tasks.update(c,task['id'],1,changes={'priority':'HIGH','assigned_to':current().actor})
    assert edited['priority']=='HIGH' and edited['revision']==2
    assert tasks.listing(c,priority='HIGH',view='MY')['total']==1
    assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0


def test_postgres_scoped_keys_rate_windows_and_mcp_proposals(owned_postgres,monkeypatch):
    from app.developer import keys,approvals
    c=owned_postgres;monkeypatch.setattr(get_settings(),'heysow_developer_api_enabled',True);monkeypatch.setattr(get_settings(),'heysow_mcp_enabled',True)
    issued=keys.create(c,keys.Create(name='Postgres protocol client',scopes=['companies:read','mcp:use','lists:write']))
    grant=keys.authenticate(c,'Bearer '+issued['token']);marker=keys._grant.set(grant)
    try:
        request=uuid.uuid4();proposal=approvals.propose(c,'create_list',{'name':'Postgres reviewed protocol list'},request)
        assert approvals.propose(c,'create_list',{'name':'Postgres reviewed protocol list'},request)['id']==proposal['id']
        assert approvals.status(c,proposal['id'])['status']=='PENDING'
        assert approvals.listing(c)['items'][0]['id']==proposal['id']
        assert approvals.decide(c,proposal['id'],'approve')['status']=='APPLIED'
        assert approvals.decide(c,proposal['id'],'approve')['status']=='APPLIED'
        assert c.execute('SELECT COUNT(*) FROM lead_lists').fetchone()[0]==1
    finally:keys._grant.reset(marker)
    rotated=keys.rotate(c,issued['key']['id'])
    from fastapi import HTTPException
    with pytest.raises(HTTPException):keys.authenticate(c,'Bearer '+issued['token'])
    assert keys.authenticate(c,'Bearer '+rotated['token']).organization_id==current().organization_id
    assert all('token_hash' not in row for row in keys.listing(c)['items'])
    assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0


def test_postgres_signed_webhook_outbox_lease_and_signature(owned_postgres,monkeypatch):
    import asyncio,json
    import httpx
    from cryptography.fernet import Fernet
    from app.webhooks import service,worker
    c=owned_postgres;org=current().organization_id
    monkeypatch.setattr(get_settings(),'heysow_webhooks_enabled',True)
    monkeypatch.setattr(get_settings(),'heysow_integration_encryption_key',Fernet.generate_key().decode())
    created=service.save(c,service.Endpoint(name='Controlled PostgreSQL receiver',url='https://receiver.example.com/events',topics=['company.created']))
    key=created['endpoint']['id'];secret=created['signing_secret']
    run=PipelineRun(market='Controlled city',vertical='dentists',target=1);PipelineRunRepository(c).create(run,organization=org)
    company=Business(name='Controlled webhook company',normalized_name='controlled webhook company',vertical='dentists',run_id=run.id)
    BusinessRepository(c).insert(company);ProspectRepository(c).observe(company,organization=org);c.commit()
    item=service.history(c,key)['items'][0];calls=[]
    def receive(request):
        assert request.headers['X-PlaneByte-Signature']==service.signature(secret,request.headers['X-PlaneByte-Timestamp'],request.content)
        assert json.loads(request.content)['workspace_id']==org;calls.append(1);return httpx.Response(204)
    transport=httpx.MockTransport(receive)
    assert asyncio.run(worker.deliver(c,key,item['id'],transport))=='DELIVERED'
    assert asyncio.run(worker.deliver(c,key,item['id'],transport))=='NOT_DUE'
    assert len(calls)==1 and service.history(c,key)['items'][0]['attempts']==1
    assert secret not in json.dumps(service.listing(c))


def test_postgres_reviewed_customer_sheet_export_snapshot_and_worker(owned_postgres,monkeypatch):
    import asyncio,json
    from contextlib import contextmanager
    from urllib.parse import urlsplit,parse_qs
    from unittest.mock import AsyncMock
    import httpx
    from cryptography.fernet import Fernet
    from app.integrations import service,sheet_exports as exports
    from app.acquisition import sheets
    from app.acquisition.config import AcquisitionSettings
    from app.sales import collections
    c=owned_postgres;org=current().organization_id
    monkeypatch.setattr(get_settings(),'heysow_workspace_management_enabled',True);monkeypatch.setattr(get_settings(),'heysow_customer_integrations_enabled',True)
    monkeypatch.setattr(get_settings(),'heysow_integration_encryption_key',Fernet.generate_key().decode())
    monkeypatch.setattr('app.acquisition.config.settings',lambda:AcquisitionSettings(_env_file=None,AUTH_GOOGLE_ID='fixture-client',AUTH_GOOGLE_SECRET='fixture-secret',GOOGLE_SHEETS_REDIRECT_URI='https://example.test/acquisition/sheets/callback'))
    authorization=service.authorize(c,write=True);state=parse_qs(urlsplit(authorization['authorization_url']).query)['state'][0]
    monkeypatch.setattr(sheets,'token_request',AsyncMock(return_value={'access_token':'synthetic-pg-access','refresh_token':'synthetic-pg-refresh','scope':service.WRITE_SCOPE,'expires_in':3600}))
    connection=asyncio.run(service.connect(c,state,'controlled-code'));c.commit()
    run=PipelineRun(market='Controlled city',vertical='dentists',target=1);PipelineRunRepository(c).create(run,organization=org)
    company=Business(name='Controlled export company',normalized_name='controlled export company',vertical='dentists',run_id=run.id,public_email='public@controlled.example')
    BusinessRepository(c).insert(company);ProspectRepository(c).observe(company,organization=org);c.commit()
    group=collections.save(c,collections.Named(name='PostgreSQL export selection'));collections.change_members(c,group['id'],[company.id]);c.commit()
    body=exports.Export(list_id=group['id'],spreadsheet='controlled-sheet-id',sheet='Companies',request_id=uuid.uuid4())
    job=exports.stage(c,connection['id'],body);assert exports.stage(c,connection['id'],body)['id']==job['id'];exports.approve(c,job['id'],job['review_digest'],'OVERWRITE_REVIEWED_RANGE');c.commit()
    @contextmanager
    def session(path=None):
        yield c
        c.commit()
    monkeypatch.setattr(exports,'db_session',session);calls=[]
    def receive(request):
        calls.append(1);assert json.loads(request.content)['values'][1][0]=='Controlled export company'
        return httpx.Response(200,json={'updatedCells':16})
    transport=httpx.MockTransport(receive);asyncio.run(exports.execute(job['id'],transport=transport));asyncio.run(exports.execute(job['id'],transport=transport))
    assert exports.owned(c,job['id'])['status']=='COMPLETED' and len(calls)==1
    assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0

def test_commercial_monthly_atomicity_and_retry_under_postgres(postgres,monkeypatch):
    from fastapi import HTTPException
    import concurrent.futures,json,time,threading
    from app.billing import commercial,commercial_usage,contracts
    from app.platform.context import workspace_scope
    from app.database.prospects import now
    c=postgres;run_migrations(c);org=PLANEBYTE_ORGANIZATION_ID
    owner=c.execute('SELECT created_by_user_id FROM organizations WHERE id=?',(org,)).fetchone()[0]
    from tests.creem_quota_fixture import seed
    settings=get_settings();seed(c,org,owner,monkeypatch)
    barrier=threading.Barrier(2)
    def spend(operation,amount):
        conn=PostgresConnection(settings.database_url,schema=c.schema)
        try:
            with workspace_scope(conn,owner,org):
                barrier.wait(timeout=15);commercial_usage.reserve(conn,{'searches':amount},operation);conn.commit();return 'RESERVED'
        except HTTPException as error:
            conn.rollback()
            if error.status_code==429:return 'QUOTA'
            raise
        finally:conn.close()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda op:spend(op,60),('a','b')))
    assert sorted(results)==['QUOTA','RESERVED']
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:spend('same-retry',1),range(2)))
    assert results==['RESERVED','RESERVED']
    assert c.execute("SELECT reserved FROM subscription_usage WHERE organization_id=? AND dimension='searches'",(org,)).fetchone()[0]==61
    assert c.execute('SELECT COUNT(*) FROM subscription_reservations WHERE organization_id=?',(org,)).fetchone()[0]==2


def test_commercial_upgrade_preserves_existing_postgres_rows_and_billing_history(postgres,monkeypatch):
    import app.database.migrations as migrations
    c=postgres;full=migrations.MIGRATIONS
    monkeypatch.setattr(migrations,'MIGRATIONS',full[:46]);run_migrations(c)
    tables=[r[0] for r in c.execute("SELECT tablename FROM pg_tables WHERE schemaname=? ORDER BY tablename",(c.schema,)).fetchall()]
    def fingerprints():
        import hashlib,json
        return {t:hashlib.sha256(json.dumps(sorted([json.dumps(dict(r),sort_keys=True,default=str) for r in c.execute('SELECT * FROM "'+t+'"').fetchall()])).encode()).hexdigest() for t in tables if t!='schema_migrations'}
    before=fingerprints();monkeypatch.setattr(migrations,'MIGRATIONS',full)
    assert run_migrations(c)==len(full)-46 and run_migrations(c)==0
    assert fingerprints()==before
    assert c.execute('SELECT COUNT(*) FROM commercial_contracts').fetchone()[0]==0


def test_transaction_configuration_is_reapplied_after_commit_and_rollback(postgres):
    c=postgres
    assert c.execute('SELECT current_schema()').fetchone()[0]==c.schema
    c.execute("SELECT set_config('TimeZone','Asia/Kolkata',true)")
    c.commit()
    assert c.execute('SELECT current_schema(),current_setting(\'TimeZone\'),current_setting(\'statement_timeout\')').fetchone()[0]==c.schema
    assert c.execute("SELECT current_setting('TimeZone')").fetchone()[0]=='UTC'
    c.rollback()
    row=c.execute("SELECT current_schema(),current_setting('TimeZone') timezone,current_setting('statement_timeout') timeout").fetchone()
    assert row[0]==c.schema and row['timezone']=='UTC' and row['timeout']=='30s'
    with pytest.raises(Exception):c.execute('SELECT missing_column FROM missing_table')
    c.rollback()
    assert c.execute('SELECT 1').fetchone()[0]==1
