import asyncio
import sqlite3
from unittest.mock import Mock
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from app.database.migrations import run_migrations
from app.api.organization import create_organization,membership_role
from app.platform.context import workspace_scope
from app.platform import domains


@pytest.fixture
def tenants():
    c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row;run_migrations(c)
    org=create_organization(c,'domain-owner@example.test','Domain company')['organization_id']
    other=create_organization(c,'foreign@example.test','Foreign company')['organization_id']
    yield c,org,other
    c.close()


def test_dns_challenge_requires_exact_owned_proof_and_never_grants_membership(tenants,monkeypatch):
    c,org,other=tenants
    with workspace_scope(c,'domain-owner@example.test',org):
        challenge=domains.challenge(c,domains.DomainCreate(domain='EXAMPLE.COM.'))
        assert challenge['domain']=='example.com'
        assert challenge['record_value'] not in str(dict(c.execute('SELECT * FROM organization_domains').fetchone()))
    resolver=Mock(return_value=[challenge['record_value']]);monkeypatch.setattr(domains,'_resolve',resolver)
    with workspace_scope(c,'foreign@example.test',other):
        with pytest.raises(HTTPException) as foreign:asyncio.run(domains.verify(c,challenge['id']))
        assert foreign.value.status_code==404
    resolver.assert_not_called()
    with workspace_scope(c,'domain-owner@example.test',org):
        result=asyncio.run(domains.verify(c,challenge['id']));assert result['status']=='VERIFIED'
        assert domains.listing(c)['items'][0]['status']=='VERIFIED'
        assert asyncio.run(domains.verify(c,challenge['id']))==result
        domains.revoke(c,challenge['id'])
        assert domains.listing(c)['items'][0]['status']=='REVOKED'
    assert resolver.call_count==1
    assert membership_role(c,'foreign@example.test',org) is None


def test_pending_dns_is_throttled_and_old_tokens_do_not_verify_rotated_challenge(tenants,monkeypatch):
    c,org,_=tenants
    with workspace_scope(c,'domain-owner@example.test',org):
        first=domains.challenge(c,domains.DomainCreate(domain='example.com'))
        resolver=Mock(return_value=['unrelated']);monkeypatch.setattr(domains,'_resolve',resolver)
        assert asyncio.run(domains.verify(c,first['id']))['status']=='PENDING'
        with pytest.raises(HTTPException) as throttled:asyncio.run(domains.verify(c,first['id']))
        assert throttled.value.status_code==429 and resolver.call_count==1
        c.execute("UPDATE organization_domains SET updated_at='2000-01-01T00:00:00+00:00'")
        second=domains.challenge(c,domains.DomainCreate(domain='example.com'))
        assert first['id']==second['id'] and first['record_value']!=second['record_value']
        resolver.return_value=[first['record_value']]
        assert asyncio.run(domains.verify(c,second['id']))['status']=='PENDING'
        assert c.execute('SELECT attempts FROM organization_domains').fetchone()[0]==1


@pytest.mark.parametrize('value',['localhost','127.0.0.1','http://example.com','example.com/path','a@company.com','co.uk','company.local','company.com:443'])
def test_domain_normalization_rejects_nonpublic_or_non_domain_inputs(value):
    with pytest.raises(ValidationError):domains.DomainCreate(domain=value)


def test_dns_failure_does_not_verify_and_still_consumes_bounded_attempt(tenants,monkeypatch):
    c,org,_=tenants
    with workspace_scope(c,'domain-owner@example.test',org):
        challenge=domains.challenge(c,domains.DomainCreate(domain='example.com'))
        monkeypatch.setattr(domains,'_resolve',Mock(side_effect=RuntimeError('resolver unavailable')))
        with pytest.raises(HTTPException) as failed:asyncio.run(domains.verify(c,challenge['id']))
        assert failed.value.status_code==503
        row=c.execute('SELECT status,attempts FROM organization_domains').fetchone()
        assert row['status']=='PENDING' and row['attempts']==1


def test_domain_api_gate_proof_and_no_cross_workspace_lookup(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from app.api.server import app
    from app.config.settings import get_settings
    from app.database.connection import db_session
    settings=get_settings();monkeypatch.setattr(settings,'database_path',str(tmp_path/'domains-api.db'))
    monkeypatch.setattr(settings,'allowed_user_emails','owner@example.test,foreign@example.test')
    monkeypatch.setattr(settings,'heysow_workspace_management_enabled',False)
    with TestClient(app) as client:
        assert client.get('/api/organization/domains').status_code==503
        monkeypatch.setattr(settings,'heysow_workspace_management_enabled',True)
        with db_session() as c:create_organization(c,'foreign@example.test','Other company')
        created=client.post('/api/organization/domains',json={'domain':'example.com'});assert created.status_code==201,created.text
        assert created.headers['cache-control']=='no-store'
        value=created.json();resolver=Mock(return_value=[value['record_value']]);monkeypatch.setattr(domains,'_resolve',resolver)
        assert client.post('/api/organization/domains/'+value['id']+'/verify',headers={'x-le-user':'foreign@example.test'}).status_code==404
        resolver.assert_not_called()
        verified=client.post('/api/organization/domains/'+value['id']+'/verify');assert verified.status_code==200,verified.text
        assert verified.json()['status']=='VERIFIED'
        listed=client.get('/api/organization/domains').json();assert listed['items'][0]['status']=='VERIFIED'
        assert 'challenge_hash' not in str(listed) and value['record_value'] not in str(listed)
