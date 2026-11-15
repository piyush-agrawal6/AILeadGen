"""External official SDK acceptance against the real deployed HTTPS server.

One least-privilege owner-controlled credential, in memory only, revoked finally.
No discovery, inference, outbound message, subscription or payment action occurs.
"""
import asyncio,json,uuid,time
from pathlib import Path
import importlib.metadata
import httpx,httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from scripts.deploy_product_release import signed,ORIGIN
OUT=Path(__file__).resolve().parents[1]/'data/artifacts/verification/final-remediation'

async def exercise(token):
    async with httpx2.AsyncClient(headers={'authorization':'Bearer '+token,'origin':'https://app.planebyte.com'},timeout=60,follow_redirects=True) as http:
        async with Client(streamable_http_client(ORIGIN+'/api/v1/mcp',http_client=http,terminate_on_close=False),read_timeout_seconds=60) as client:
            available=await client.list_tools();names=[x.name for x in available.tools]
            assert 'list_intent_monitors' in names and 'search_intent_signals' in names
            assert 'search_companies' not in names and 'search_contacts' not in names
            result=await client.call_tool('list_intent_monitors',{})
            assert not result.is_error and isinstance(result.structured_content,dict)
            unknown=await client.call_tool('get_intent_signal',{'id':str(uuid.uuid4())})
            assert unknown.is_error
            return {'official_sdk_version':importlib.metadata.version('mcp'),'https_handshake':True,'tool_discovery':True,'tools':names,'authorized_monitor_read':True,'unknown_resource_denied':True,'hidden_lead_tools_absent':True}

def main():
    token=None;key=None;result={'status':'FAILED','credential_values_disclosed':False,'real_outreach_sent':False,'payment_started':False}
    with httpx.Client(base_url=ORIGIN,timeout=60,follow_redirects=False) as c:
        try:
            response=signed(c,'/api/organization/developer/keys','POST',{'name':'Final controlled MCP acceptance','scopes':['mcp:use','intent:read'],'lifetime_days':1})
            if response.status_code!=201:raise RuntimeError('Controlled key creation rejected with HTTP '+str(response.status_code))
            created=response.json();key=created['key']['id'];token=created['token']
            result.update(asyncio.run(exercise(token)));result['status']='PASS'
        except Exception as error:
            result['error_type']=type(error).__name__
        finally:
            if key:
                revoked=signed(c,'/api/organization/developer/keys/'+key,'DELETE')
                result['acceptance_key_revoked']=revoked.status_code==200
                if not result['acceptance_key_revoked']:result['status']='FAILED';result['cleanup_required_key_id']=key
                elif token:
                    check=c.post('/api/v1/mcp',headers={'authorization':'Bearer '+token,'accept':'application/json, text/event-stream'},json={'jsonrpc':'2.0','id':1,'method':'ping'})
                    result['revoked_key_denied']=check.status_code==401
                    if not result['revoked_key_denied']:result['status']='FAILED'
    OUT.mkdir(parents=True,exist_ok=True);path=OUT/'external-mcp-acceptance.json';path.write_text(json.dumps(result,indent=2));path.chmod(0o600)
    print(json.dumps(result));return 0 if result['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
