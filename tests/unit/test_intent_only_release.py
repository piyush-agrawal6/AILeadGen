"""Reversible release availability, with persisted Lead Engine data and grants."""
import asyncio
import pytest
from fastapi import HTTPException
from app.api.organization import products
from app.config.settings import get_settings
from app.database.connection import db_session
from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID as INTERNAL
from app.platform import modules, product_help
from app.platform.context import job_scope, workspace_scope
from test_developer_api import developer, issue


def test_hidden_product_denies_legacy_http_and_keys_without_changing_data(developer, monkeypatch):
    http, settings, business, other = developer
    token = issue(http, ['companies:read'])['token']
    with db_session() as c:
        grants = [tuple(r) for r in c.execute('SELECT * FROM organization_products ORDER BY organization_id,product')]
        counts = {table:c.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in ('businesses','prospects','pipeline_runs','organization_memberships')}
        assert products(c, INTERNAL)['LEADGEN']
    monkeypatch.setattr(settings, 'lead_engine_available', False)
    assert http.get('/api/organization/products').json()['lead_engine'] is False
    for path in ('/api/leads','/api/dashboard','/api/settings','/api/markets','/api/verticals','/api/workflow/defaults','/api/automation/targets','/api/email/gmail','/api/assistant/status','/api/qualification/companies/1','/api/sales/tasks','/api/foundation/contacts/1','/api/organization/integrations','/api/organization/developer/approvals'):
        assert http.get(path).status_code == 404, path
    assert http.get('/api/v1/companies',headers={'authorization':'Bearer '+token}).status_code == 404
    assert http.get('/api/organization/profile').status_code == 200
    assert http.get('/api/organization/workspaces').status_code == 200
    with db_session() as c:
        assert [tuple(r) for r in c.execute('SELECT * FROM organization_products ORDER BY organization_id,product')] == grants
        assert {table:c.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in counts} == counts
        with pytest.raises(HTTPException):
            with job_scope(c,'scan',business.run_id): pass
    # Config-only reactivation restores the same records and same credential.
    monkeypatch.setattr(settings, 'lead_engine_available', True)
    assert http.get('/api/v1/companies',headers={'authorization':'Bearer '+token}).json()['items'][0]['id'] == business.id


def test_hidden_workflow_and_outreach_do_not_touch_database_or_provider(monkeypatch):
    monkeypatch.setattr(get_settings(), 'lead_engine_available', False)
    class NoSideEffects:
        def execute(self,*args):raise AssertionError('Unavailable product touched persisted execution state')
    from app.workflows.service import dispatch
    from app.automation.service import outreach_tick, legacy_acquisition_tick
    assert asyncio.run(dispatch(NoSideEffects())) == {'scheduled_runs_started':[]}
    assert outreach_tick(NoSideEffects())['status'] == 'PRODUCT_UNAVAILABLE'
    assert legacy_acquisition_tick(NoSideEffects())['status'] == 'PRODUCT_UNAVAILABLE'
    for path in ('/api/organization/profile','/api/organization/icps','/api/billing/catalog','/api/tracking/u/opaque','/api/intelligence/jobs'):
        assert not modules.lead_engine_route(path)
    assert all(not modules.lead_engine_route(topic['href'].replace('/intent-radar','/api/intent-radar')) for topic in product_help.search('',20))
    assert all(topic['href'] not in ('/campaigns','/find-leads','/leads') for topic in product_help.search('',20))


@pytest.mark.asyncio
async def test_intent_only_official_mcp_lists_radar_tools_and_preserves_shared_access(tmp_path,monkeypatch):
    from test_mcp_protocol import configure
    from app.api.server import create_app
    from app.developer import keys
    import httpx2
    from mcp import Client
    from mcp.client.streamable_http import streamable_http_client
    settings=configure(tmp_path,monkeypatch)
    monkeypatch.setattr(settings,'lead_engine_available',False)
    monkeypatch.setattr(settings,'intent_radar_stage','Beta')
    monkeypatch.setattr(settings,'intent_radar_growth_enabled',True)
    application=create_app()
    async with application.router.lifespan_context(application):
        with db_session() as c:
            c.execute("UPDATE organization_products SET enabled=1 WHERE organization_id=? AND product='INTENT_RADAR'",(INTERNAL,))
            with workspace_scope(c,'owner@example.test',INTERNAL):
                key=keys.create(c,keys.Create(name='Intent-only test',scopes=['intent:read','mcp:use']))
        async with httpx2.AsyncClient(transport=httpx2.ASGITransport(app=application),base_url='http://testserver',headers={'authorization':'Bearer '+key['token']}) as http:
            schema=(await http.get('/api/v1/openapi.json')).json()
            assert schema['info']['title']=='PlaneByte Intent Radar API'
            assert all(path.startswith('/v1/intent-radar/') for path in schema['paths'])
            async with Client(streamable_http_client('http://testserver/api/v1/mcp',http_client=http,terminate_on_close=False),read_timeout_seconds=10) as client:
                tools={tool.name for tool in (await client.list_tools()).tools}
                assert {'search_intent_signals','get_market_overview'} <= tools
                assert not {'search_companies','search_contacts','campaigns','propose_action'} & tools
                found=await client.call_tool('search_intent_signals',{})
                assert not found.is_error and found.structured_content['items']==[]
            assert (await http.get('/api/v1/companies')).status_code==403
            assert (await http.get('/api/intent-radar/overview')).status_code==200
