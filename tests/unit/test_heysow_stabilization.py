"""Real migrated SQLite, real memberships, no external providers or sends."""
import json
import sqlite3
from types import SimpleNamespace
import uuid
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from app.api.organization import create_organization
from app.api.permissions import role,authorize
from app.database.migrations import run_migrations
from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID as INTERNAL
from app.database.models import Business,PipelineRun
from app.database.repositories import BusinessRepository,PipelineRunRepository
from app.database.prospects import ProspectRepository,identity_keys
from app.platform.context import workspace_scope,current,organization,job_scope,require_internal_mailbox
from app.mail import contacted,service as mail

@pytest.fixture
def tenants():
    c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row
    run_migrations(c)
    owner=c.execute('SELECT created_by_user_id FROM organizations WHERE id=?',(INTERNAL,)).fetchone()[0]
    other=create_organization(c,'second@example.test','Second Company')['organization_id']
    yield c,owner,other
    c.close()


def test_context_requires_membership_and_resets_even_after_error(tenants):
    c,owner,other=tenants
    with pytest.raises(HTTPException):current()
    with pytest.raises(HTTPException):
        with workspace_scope(c,owner,other):pass
    with workspace_scope(c,owner,INTERNAL):
        assert organization()==INTERNAL
        with pytest.raises(HTTPException):organization(other)
        with pytest.raises(HTTPException):
            with workspace_scope(c,'second@example.test',other):pass
    with pytest.raises(HTTPException):current()
    c.execute("UPDATE organization_memberships SET status='REVOKED' WHERE user_id=?",(owner,))
    with pytest.raises(HTTPException):role(c,owner,INTERNAL)
    with pytest.raises(HTTPException):
        with workspace_scope(c,owner,INTERNAL):pass


def test_registry_requires_context_and_never_accepts_another_tenant_override(tenants):
    c,owner,other=tenants
    with pytest.raises(HTTPException):contacted.lookup(c,'published@example.test')
    with workspace_scope(c,owner,INTERNAL):
        contacted.record(c,message_id='internal-1',email='published@example.test',sent_at='2026-11-05T00:00:00+00:00')
        assert contacted.lookup(c,'published@example.test')['send_count']==1
        with pytest.raises(HTTPException):contacted.lookup(c,'published@example.test',organization_id=other)
        with pytest.raises(HTTPException):contacted.record(c,message_id='bad',email='published@example.test',sent_at='2026-11-05T00:00:00+00:00',organization_id=other)
    with workspace_scope(c,'second@example.test',other):
        assert contacted.lookup(c,'published@example.test') is None
        contacted.record(c,message_id='other-1',email='published@example.test',sent_at='2026-11-05T01:00:00+00:00')
        assert contacted.lookup(c,'published@example.test')['organization_id']==other
    assert c.execute('SELECT COUNT(*) FROM contacted_recipients').fetchone()[0]==2


def test_customer_mailbox_is_not_configured_and_provider_never_touched(tenants,monkeypatch):
    c,owner,other=tenants
    from app.config.settings import get_settings
    monkeypatch.setattr(get_settings(),'heysow_customer_gmail_enabled',False)
    transport=Mock();monkeypatch.setattr(mail,'provider',transport)
    with workspace_scope(c,'second@example.test',other):
        from app.api.routes.mail import email_account
        result=email_account(SimpleNamespace(state=SimpleNamespace(organization_id=other)),c)
        assert result['status']=='NOT_CONFIGURED' and not result['can_send'] and result['email_address'] is None
        # The new customer mailbox path is explicitly disabled (503); calling
        # internal sync from a foreign workspace still fails ownership (409).
        operations=((lambda:mail.account(c,'second@example.test'),503),(lambda:mail.sync_mailbox(),409),(lambda:mail.send(c,'unowned','second@example.test',{}),503))
        for operation,status in operations:
            with pytest.raises(HTTPException) as err:operation()
            assert err.value.status_code==status
    transport.assert_not_called()
    assert c.execute('SELECT COUNT(*) FROM email_accounts').fetchone()[0]==0


def test_identity_aliases_are_stable_independently_in_each_workspace(tenants):
    c,owner,other=tenants;found=[]
    for actor,org in ((owner,INTERNAL),('second@example.test',other)):
        with workspace_scope(c,actor,org):
            pids=[]
            for _ in range(2):
                run=PipelineRun(market='Bristol',vertical='dentists',target=1)
                PipelineRunRepository(c).create(run,organization=org)
                b=Business(run_id=run.id,name='Same Company',normalized_name='same company',vertical='dentists',external_overture_id='same-source-id')
                BusinessRepository(c).insert(b)
                pids.append(ProspectRepository(c).observe(b,organization=org))
            assert pids[0]==pids[1];found.append(pids[0])
    assert found[0]!=found[1]
    assert c.execute('SELECT COUNT(*) FROM prospects').fetchone()[0]==2
    assert c.execute('PRAGMA foreign_key_check').fetchall()==[]


def test_jobs_persist_ownership_and_reject_cross_scope_or_revoked_owner(tenants):
    c,owner,other=tenants
    from app.acquisition.service import create_job,create_campaign,job
    with workspace_scope(c,owner,INTERNAL):
        r=create_job(c,'FILE_IMPORT',owner,str(uuid.uuid4()),{}, {'filename':'synthetic.csv'})
        cid=create_campaign(c,r['id'],'Synthetic campaign',target=1)
        assert r['organization_id']==INTERNAL
        assert c.execute('SELECT organization_id FROM scan_campaigns WHERE id=?',(cid,)).fetchone()[0]==INTERNAL
    with job_scope(c,'acquisition',r['id']):assert organization()==INTERNAL
    with workspace_scope(c,'second@example.test',other):
        with pytest.raises(HTTPException):job(c,r['id'])
        with pytest.raises(HTTPException):
            with job_scope(c,'acquisition',r['id']):pass
    c.execute("UPDATE organization_memberships SET status='REVOKED' WHERE user_id=?",(owner,))
    with pytest.raises(HTTPException):
        with job_scope(c,'acquisition',r['id']):pass


def test_migration_retains_preexisting_history_and_is_repeatable(monkeypatch):
    from app.database import migrations
    all_migrations=migrations.MIGRATIONS
    c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row
    monkeypatch.setattr(migrations,'MIGRATIONS',all_migrations[:15])
    run_migrations(c)
    stamp='2026-11-01T00:00:00+00:00'
    c.execute('INSERT INTO prospects(id,first_seen_at,last_seen_at,updated_at,lead_status) VALUES(?,?,?,?,?)',('historical',stamp,stamp,stamp,'DO_NOT_CONTACT'))
    c.execute('INSERT INTO contacted_recipients(id,organization_id,normalized_email,original_email,first_sent_at,last_sent_at,send_count,unsubscribed,do_not_contact,source,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',('history','planebyte','old@example.test','old@example.test',stamp,stamp,2,1,1,'HISTORICAL',stamp,stamp))
    before={t:c.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in ('prospects','contacted_recipients','scan_markets')}
    monkeypatch.setattr(migrations,'MIGRATIONS',all_migrations)
    assert run_migrations(c)==len(all_migrations)-15
    assert run_migrations(c)==0
    assert before=={t:c.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in before}
    p=c.execute('SELECT organization_id,lead_status FROM prospects WHERE id=?',('historical',)).fetchone()
    assert tuple(p)==(INTERNAL,'DO_NOT_CONTACT')
    old=c.execute('SELECT organization_id,send_count,unsubscribed,do_not_contact FROM contacted_recipients WHERE id=?',('history',)).fetchone()
    assert tuple(old)==(INTERNAL,2,1,1)
    assert c.execute('PRAGMA foreign_key_check').fetchall()==[]
    c.close()


def test_api_ownership_viewer_denial_and_revoked_primary_account(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from app.api.server import app
    from app.config.settings import get_settings
    from app.database.connection import db_session
    settings=get_settings()
    monkeypatch.setattr(settings,'database_path',str(tmp_path/'api-owned.db'))
    monkeypatch.setattr(settings,'allowed_user_emails','first@example.test,second@example.test')
    monkeypatch.setattr(settings,'app_env','test')
    with TestClient(app) as client:
        with db_session() as c:
            other=create_organization(c,'second@example.test','Second API Company')['organization_id']
            c.execute("UPDATE organization_products SET enabled=1 WHERE organization_id=? AND product='LEADGEN'",(other,))
            from app.api.organization import complete_onboarding
            complete_onboarding(c,other)
            with workspace_scope(c,'second@example.test',other):
                run=PipelineRun(market='Bristol',vertical='dentists',target=1)
                PipelineRunRepository(c).create(run,organization=other)
                b=Business(run_id=run.id,name='Owned Dental',normalized_name='owned dental',vertical='dentists')
                BusinessRepository(c).insert(b);pid=ProspectRepository(c).observe(b,organization=other)
        # Legacy read APIs must be just as isolated as workflow mutations.
        for endpoint in (f'/api/leads/{b.id}',f'/api/leads/{b.id}/report'):
            assert client.get(endpoint,headers={'x-le-user':'first@example.test'}).status_code==404
        assert client.get('/api/leads',headers={'x-le-user':'first@example.test'}).json()['total']==0
        assert client.get(f'/api/leads/{b.id}',headers={'x-le-user':'second@example.test'}).status_code==200
        assert client.get('/api/leads',headers={'x-le-user':'second@example.test'}).json()['total']==1
        endpoint=f'/api/leads/{b.id}/workflow' 
        denied=client.patch(endpoint,json={'lead_status':'SHORTLISTED'},headers={'x-le-user':'first@example.test'})
        assert denied.status_code==404
        allowed=client.patch(endpoint,json={'lead_status':'SHORTLISTED'},headers={'x-le-user':'second@example.test'})
        assert allowed.status_code==200,allowed.text
        with db_session() as c:
            c.execute("UPDATE organization_memberships SET role='VIEWER' WHERE organization_id=?",(other,))
        assert client.patch(endpoint,json={'lead_status':'CONTACTED'},headers={'x-le-user':'second@example.test'}).status_code==403
        with db_session() as c:
            c.execute("UPDATE organization_memberships SET status='REVOKED' WHERE user_id='first@example.test'")
            assert c.execute('SELECT lead_status FROM prospects WHERE id=?',(pid,)).fetchone()[0]=='SHORTLISTED'
        assert client.get('/api/verticals',headers={'x-le-user':'first@example.test'}).status_code==403


def test_workspace_settings_do_not_share_the_legacy_singleton(tenants):
    from app.api.organization import workspace_settings,save_workspace_settings
    c,owner,other=tenants
    with workspace_scope(c,owner,INTERNAL):
        save_workspace_settings(c,INTERNAL,{'automation':{'max_hour':5}},owner)
    with workspace_scope(c,'second@example.test',other):
        save_workspace_settings(c,other,{'automation':{'max_hour':2}},'second@example.test')
    assert workspace_settings(c,INTERNAL)['automation']['max_hour']==5
    assert workspace_settings(c,other)['automation']['max_hour']==2
    assert c.execute('SELECT COUNT(*) FROM organization_settings').fetchone()[0]==2
    assert c.execute('PRAGMA foreign_key_check').fetchall()==[]


def test_schedule_upsert_cannot_transfer_workspace_ownership(tenants):
    from app.api.routes.workflows import save_schedule,Schedule,Run
    from datetime import datetime,timedelta,timezone
    c,owner,other=tenants
    body=Schedule(name='Scoped schedule',enabled=False,frequency='once',timezone='UTC',start_at=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat(),configuration=Run(kind='SCAN',scan_source='OVERTURE'))
    with workspace_scope(c,owner,INTERNAL):
        sid=save_schedule(c,body,owner)['id']
    with workspace_scope(c,'second@example.test',other):
        with pytest.raises(HTTPException) as error:
            save_schedule(c,body,'second@example.test',sid=sid)
        assert error.value.status_code==404
    assert c.execute('SELECT organization_id FROM automation_schedules WHERE id=?',(sid,)).fetchone()[0]==INTERNAL
    assert c.execute('SELECT COUNT(*) FROM pipeline_runs').fetchone()[0]==0


def test_membership_role_changes_are_scoped_and_protect_last_owner(tenants):
    from app.platform.memberships import change_role
    from app.api.organization import membership_role
    c,owner,other=tenants
    with workspace_scope(c,owner,INTERNAL):
        with pytest.raises(HTTPException) as error:change_role(c,owner,owner,'VIEWER')
        assert error.value.status_code==409
        change_role(c,owner,'second@example.test','OPERATOR')
        assert membership_role(c,'second@example.test',INTERNAL)=='MEMBER'
        assert membership_role(c,'second@example.test',other)=='OWNER'
        with pytest.raises(HTTPException):change_role(c,'second@example.test',owner,'VIEWER')
        change_role(c,owner,'second@example.test','OWNER')
        change_role(c,owner,owner,'ADMIN')
        assert membership_role(c,owner,INTERNAL)=='ADMIN'
        assert c.execute("SELECT COUNT(*) FROM audit_log WHERE action='MEMBERSHIP_ROLE_CHANGED' AND organization_id=?",(INTERNAL,)).fetchone()[0]==3
    with workspace_scope(c,'second@example.test',other):
        with pytest.raises(HTTPException):change_role(c,owner,'second@example.test','VIEWER')
        assert membership_role(c,'second@example.test',other)=='OWNER'


def test_quality_and_contact_review_are_scoped_even_without_explicit_arguments(tenants):
    from app.workflows.quality import contacts,quality,reviews
    c,owner,other=tenants;records=[]
    for actor,org in ((owner,INTERNAL),('second@example.test',other)):
        with workspace_scope(c,actor,org):
            run=PipelineRun(market='Bristol',vertical='dentists',target=1)
            PipelineRunRepository(c).create(run,organization=org)
            b=Business(run_id=run.id,name='Private Company',normalized_name='private company',vertical='dentists',public_email='published@controlled.test')
            BusinessRepository(c).insert(b);pid=ProspectRepository(c).observe(b,organization=org);records.append(pid)
            assert quality(c)['master_leads']==1
            assert contacts(c,pid)['contacts'][0]['contact_value']=='published@controlled.test'
    with workspace_scope(c,'second@example.test',other):
        with pytest.raises(HTTPException):contacts(c,records[0])
        with pytest.raises(HTTPException):quality(c,INTERNAL)
        assert reviews(c)['total']==0
    with pytest.raises(HTTPException):quality(c)


def test_merge_and_identity_resolution_cannot_cross_workspaces(tenants):
    from app.workflows.duplicates import merge,resolution_key
    c,owner,other=tenants;records=[];company=None
    for actor,org in ((owner,INTERNAL),('second@example.test',other)):
        with workspace_scope(c,actor,org):
            run=PipelineRun(market='Bristol',vertical='dentists',target=1)
            PipelineRunRepository(c).create(run,organization=org)
            company=Business(run_id=run.id,name='Controlled Company',normalized_name='controlled company',vertical='dentists')
            BusinessRepository(c).insert(company);records.append(ProspectRepository(c).observe(company,organization=org))
    assert resolution_key(company,INTERNAL)!=resolution_key(company,other)
    with workspace_scope(c,owner,INTERNAL):
        before=c.total_changes
        with pytest.raises(HTTPException) as error:merge(c,records[0],records[1],owner)
        assert error.value.status_code==404 and c.total_changes==before
    assert c.execute('SELECT COUNT(*) FROM prospects').fetchone()[0]==2


def test_contact_domain_check_rejects_foreign_records_before_dns(tenants,monkeypatch):
    from app.platform.contact_verification import validate_domain
    c,owner,other=tenants
    with workspace_scope(c,'second@example.test',other):
        run=PipelineRun(market='Bristol',vertical='dentists',target=1)
        PipelineRunRepository(c).create(run,organization=other)
        b=Business(run_id=run.id,name='Contact owner',normalized_name='contact owner',vertical='dentists')
        BusinessRepository(c).insert(b);ProspectRepository(c).observe(b,organization=other)
        cur=c.execute("INSERT INTO contacts(business_id,contact_type,contact_value,source_url,is_public_business_contact,is_valid) VALUES(?,'email','published@controlled.test','https://controlled.test/contact',1,0)",(b.id,))
        contact_id=cur.lastrowid
    lookup=Mock(return_value=('MX',True));monkeypatch.setattr('app.enrichment.dns.check_email_dns',lookup)
    with workspace_scope(c,owner,INTERNAL):
        changes=c.total_changes
        with pytest.raises(HTTPException):validate_domain(c,contact_id)
        assert c.total_changes==changes
        lookup.assert_not_called()
    with workspace_scope(c,'second@example.test',other):
        result=validate_domain(c,contact_id)
        assert result['domain_validated'] is True and result['recipient_delivery_verified'] is False
        assert result['email_state']=='PUBLICLY_PUBLISHED'
        assert c.execute("SELECT COUNT(*) FROM audit_log WHERE action='CONTACT_DOMAIN_CHECKED' AND organization_id=?",(other,)).fetchone()[0]==1
    lookup.assert_called_once()
