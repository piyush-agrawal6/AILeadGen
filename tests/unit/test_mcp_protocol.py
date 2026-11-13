"""Real official SDK client -> Streamable HTTP -> SDK server -> owned services."""
import uuid
import pytest
import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from app.config.settings import get_settings
from app.api.server import create_app
from app.database.connection import db_session
from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID as INTERNAL
from app.database.models import PipelineRun,Business
from app.database.repositories import PipelineRunRepository,BusinessRepository
from app.database.prospects import ProspectRepository
from app.platform.context import workspace_scope
from app.api.organization import create_organization
from app.developer import keys


def configure(tmp_path,monkeypatch):
 monkeypatch.setenv('MCP_ALLOWED_HOSTS','testserver')
 monkeypatch.setenv('MCP_ALLOWED_ORIGINS','http://testserver')
 settings=get_settings();monkeypatch.setattr(settings,'database_path',str(tmp_path/'mcp.db'));monkeypatch.setattr(settings,'allowed_user_emails','owner@example.test,foreign@example.test');monkeypatch.setattr(settings,'heysow_developer_api_enabled',True);monkeypatch.setattr(settings,'heysow_mcp_enabled',True);monkeypatch.setattr(settings,'heysow_workspace_management_enabled',True)
 monkeypatch.setattr(settings,'mcp_allowed_hosts','testserver');monkeypatch.setattr(settings,'mcp_allowed_origins','http://testserver')
 return settings

def seed():
 with db_session() as c:
  other=create_organization(c,'foreign@example.test','Other MCP company')['organization_id'];c.execute("UPDATE organization_onboarding SET status='COMPLETED' WHERE organization_id=?",(other,))
  with workspace_scope(c,'owner@example.test',INTERNAL):
   run=PipelineRun(market='Bristol',vertical='dentists',target=1);PipelineRunRepository(c).create(run,organization=INTERNAL);b=Business(name='Controlled MCP company',normalized_name='controlled mcp company',vertical='dentists',run_id=run.id);BusinessRepository(c).insert(b);ProspectRepository(c).observe(b,organization=INTERNAL)
   first=keys.create(c,keys.Create(name='Controlled MCP client',scopes=['mcp:use','companies:read','lists:write']))
  with workspace_scope(c,'foreign@example.test',other):second=keys.create(c,keys.Create(name='Foreign MCP client',scopes=['mcp:use','companies:read','contacts:read']))
 return b,first,second

@pytest.mark.asyncio
async def test_real_mcp_sdk_client_discovers_tools_reads_and_requires_gui_approval(tmp_path,monkeypatch):
 configure(tmp_path,monkeypatch);application=create_app()
 async with application.router.lifespan_context(application):
  b,key,_=seed()
  async with httpx2.AsyncClient(transport=httpx2.ASGITransport(app=application),base_url='http://testserver',headers={'authorization':'Bearer '+key['token']},timeout=15) as http:
   async with Client(streamable_http_client('http://testserver/api/v1/mcp',http_client=http,terminate_on_close=False),read_timeout_seconds=10) as client:
    available=await client.list_tools();assert 'search_companies' in [tool.name for tool in available.tools]
    found=await client.call_tool('search_companies',{'search':'Controlled MCP'});assert not found.is_error and found.structured_content['items'][0]['id']==b.id
    denied=await client.call_tool('search_contacts',{});assert denied.is_error and 'contacts:read' in denied.content[0].text
    request=str(uuid.uuid4());args={'kind':'create_list','arguments':{'name':'Reviewed MCP list'},'request_id':request}
    proposed=await client.call_tool('propose_action',args);assert not proposed.is_error
    proposal=proposed.structured_content;assert proposal['status']=='PENDING'
    again=await client.call_tool('propose_action',args);assert again.structured_content['id']==proposal['id']
    with db_session() as c:assert c.execute('SELECT COUNT(*) FROM lead_lists').fetchone()[0]==0
    approved=await http.post('/api/organization/developer/approvals/'+proposal['id'],json={'decision':'approve'});assert approved.status_code==200
    status=await client.call_tool('proposal_status',{'id':proposal['id']});assert status.structured_content['status']=='APPLIED'
    assert (await http.post('/api/organization/developer/approvals/'+proposal['id'],json={'decision':'approve'})).status_code==200
   with db_session() as c:
    assert c.execute('SELECT COUNT(*) FROM lead_lists').fetchone()[0]==1
    assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0
    assert c.execute("SELECT COUNT(*) FROM audit_log WHERE action='MCP_TOOL'").fetchone()[0]>=5
   assert (await http.delete('/api/organization/developer/keys/'+key['key']['id'])).status_code==200
   assert (await http.post('/api/v1/mcp',json={})).status_code==401

@pytest.mark.asyncio
async def test_mcp_foreign_ids_disabled_scope_and_rebinding_are_denied(tmp_path,monkeypatch):
 settings=configure(tmp_path,monkeypatch);application=create_app()
 async with application.router.lifespan_context(application):
  b,key,foreign=seed()
  async with httpx2.AsyncClient(transport=httpx2.ASGITransport(app=application),base_url='http://testserver',headers={'authorization':'Bearer '+foreign['token']},timeout=15) as http:
   async with Client(streamable_http_client('http://testserver/api/v1/mcp',http_client=http,terminate_on_close=False),read_timeout_seconds=10) as client:
    found=await client.call_tool('search_companies',{});assert found.structured_content['items']==[]
    denied=await client.call_tool('company_details',{'business_id':b.id});assert denied.is_error and 'not found' in denied.content[0].text.lower()
   rebinding=await http.post('/api/v1/mcp',headers={'host':'untrusted.example','accept':'application/json, text/event-stream'},json={'jsonrpc':'2.0','id':1,'method':'ping'});assert rebinding.status_code==421
   bad_origin=await http.post('/api/v1/mcp',headers={'origin':'https://untrusted.example','accept':'application/json, text/event-stream'},json={'jsonrpc':'2.0','id':2,'method':'ping'});assert bad_origin.status_code==403
   monkeypatch.setattr(settings,'heysow_mcp_enabled',False)
   assert (await http.post('/api/v1/mcp',json={})).status_code==503

@pytest.mark.asyncio
async def test_radar_sdk_reads_nine_tool_contract_and_denies_disabled_product(tmp_path,monkeypatch):
 settings=configure(tmp_path,monkeypatch)
 monkeypatch.setattr(settings,'intent_radar_stage','Beta');monkeypatch.setattr(settings,'intent_radar_schedules_enabled',False)
 application=create_app()
 async with application.router.lifespan_context(application):
  with db_session() as c:
   c.execute("UPDATE organization_products SET enabled=1 WHERE organization_id=? AND product='INTENT_RADAR'",(INTERNAL,))
   with workspace_scope(c,'owner@example.test',INTERNAL):key=keys.create(c,keys.Create(name='Radar SDK client',scopes=['mcp:use','intent:read']))
  async with httpx2.AsyncClient(transport=httpx2.ASGITransport(app=application),base_url='http://testserver',headers={'authorization':'Bearer '+key['token']},timeout=15) as http:
   async with Client(streamable_http_client('http://testserver/api/v1/mcp',http_client=http,terminate_on_close=False),read_timeout_seconds=10) as client:
    from app.intent_radar.tools import READ
    available={tool.name for tool in (await client.list_tools()).tools};assert set(READ)<=available and len(READ)==9
    health=await client.call_tool('get_intent_source_health',{});assert not health.is_error and len(health.structured_content['items'])==4
    workspace=await client.call_tool('get_intent_workspace_context',{});assert not workspace.is_error and workspace.structured_content['organization_id']==INTERNAL
    assert 'credentials' not in workspace.structured_content
    denied=await client.call_tool('search_contacts',{});assert denied.is_error
    with db_session() as c:c.execute("UPDATE organization_products SET enabled=0 WHERE organization_id=? AND product='INTENT_RADAR'",(INTERNAL,))
    denied=await client.call_tool('get_intent_source_health',{});assert denied.is_error
