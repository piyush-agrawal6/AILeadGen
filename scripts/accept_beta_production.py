"""Explicit bounded production acceptance; no prospects, campaigns or email sends."""
import argparse,asyncio,hashlib,hmac,json,secrets,time,uuid
from pathlib import Path
import httpx
from dotenv import dotenv_values
from app.api.security import canonical_request
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/artifacts/verification/beta-activation-20261113'
ORIGIN='https://leadengine-api-befca7xg4a-el.a.run.app'
STATE=OUT/'controlled-production-state.json'

class Acceptance:
    def __init__(self):
        self.values=dotenv_values(ROOT/'.env',interpolate=False)
        self.state=json.loads(STATE.read_text()) if STATE.exists() else {}
        self.client=httpx.AsyncClient(base_url=ORIGIN,timeout=90,follow_redirects=False)
    def save(self):
        STATE.write_text(json.dumps(self.state,indent=2));STATE.chmod(0o600)
    async def request(self,method,path,body=None,actor='planebyte@gmail.com',expected=(200,201,202)):
        raw=json.dumps(body,separators=(',',':')).encode() if body is not None else b''
        stamp=str(int(time.time()));nonce=secrets.token_hex(24)
        headers={'X-LE-User':actor,'X-LE-Timestamp':stamp,'X-LE-Nonce':nonce,'Content-Type':'application/json','X-LE-Signature':hmac.new(self.values['LEADENGINE_API_SIGNING_SECRET'].encode(),canonical_request(stamp,nonce,method,path,raw,actor).encode(),hashlib.sha256).hexdigest()}
        start=time.monotonic();response=await self.client.request(method,path,content=raw,headers=headers)
        self.state.setdefault('http_checks',[]).append({'method':method,'path':path,'http':response.status_code,'seconds':round(time.monotonic()-start,2)})
        self.save()
        if response.status_code not in expected:raise RuntimeError('Controlled request failed: '+method+' '+path+' HTTP '+str(response.status_code))
        return response.json()
    async def smoke(self):
        for path in ('/api/organization/workspaces','/api/organization/products','/api/intent-radar/capabilities','/api/workflow/safety','/api/email/account'):
            d=await self.request('GET',path)
            if path.endswith('/safety') and d.get('sending_enabled'):raise RuntimeError('Sending must remain disabled.')
            if path.endswith('/capabilities'):self.state['radar']={'enabled':d.get('enabled'),'stage':d.get('stage')}
            if path.endswith('/account'):self.state['mail_account']={k:d.get(k) for k in ('provider','status','sending_enabled','sync_enabled')}
        await self.request('GET','/api/organization/workspaces',actor='unapproved-owner-check@example.invalid',expected=(401,403))
        self.state['vertex']=await self.request('POST','/api/acquisition/providers/vertex/test')
        self.state['gmail_health']=await self.request('POST','/api/email/health')
        self.save()
    async def discovery(self):
        config={'keywords':['Ask HN'],'sources':['hacker_news'],'hn_feeds':['ask'],'result_limit':5}
        if not self.state.get('monitor_id'):
            self.state.setdefault('monitor_request',str(uuid.uuid4()));self.save()
            m=await self.request('POST','/api/intent-radar/monitors',{'name':'Owner-controlled beta acceptance','description':'Bounded real public-source release verification; no prospect acquisition or outreach.','configuration':config,'status':'Active','request_id':self.state['monitor_request']})
            self.state['monitor_id']=m['id'];self.state['configuration']=m['configuration'];self.save()
        if not self.state.get('job_id'):
            self.state.setdefault('discovery_request',str(uuid.uuid4()));self.save()
            job=await self.request('POST','/api/intent-radar/discover',{'configuration':self.state['configuration'],'monitor_id':self.state['monitor_id'],'request_id':self.state['discovery_request']})
            self.state['job_id']=job['id'];self.save()
        for _ in range(12):
            job=await self.request('GET','/api/intent-radar/jobs/'+self.state['job_id'])
            if job['status'] in ('COMPLETED','FAILED','CANCELLED','NEEDS_REVIEW'):break
            await asyncio.sleep(3)
        self.state['discovery_status']=job['status'];self.save()
        if job['status']!='COMPLETED':raise RuntimeError('Real bounded discovery did not complete.')
        signals=await self.request('GET','/api/intent-radar/signals?monitor_id='+self.state['monitor_id'])
        self.state['signals_returned']=signals['total'];self.save()
        if not signals['items']:raise RuntimeError('No matching genuine source signal; do not substitute fixtures.')
        signal=signals['items'][0];self.state['signal_id']=signal['id'];self.save()
        await self.request('POST','/api/intent-radar/saved/'+signal['id'])
        opportunity=await self.request('POST','/api/intent-radar/opportunities/'+signal['id']);self.state['opportunity_id']=opportunity['id'];self.save()
        preferences=await self.request('GET','/api/intent-radar/settings');preferences['ai_assistance']=True
        await self.request('PUT','/api/intent-radar/settings',preferences)
        analysis=await self.request('POST','/api/intent-radar/signals/'+signal['id']+'/analysis',{'monitor_id':self.state['monitor_id']})
        self.state['analysis']={k:analysis.get(k) for k in ('mode','provider','model','cached','reason','id')};self.save()
    async def mcp(self):
        from mcp import Client
        from mcp.client.streamable_http import streamable_http_client
        import httpx2
        key=await self.request('POST','/api/organization/developer/keys',{'name':'Ephemeral production MCP acceptance','scopes':['mcp:use','intent:read'],'lifetime_days':1})
        key_id=key['key']['id']
        try:
            async with httpx2.AsyncClient(headers={'authorization':'Bearer '+key['token'],'origin':'https://app.planebyte.com'},timeout=70) as http:
                async with Client(streamable_http_client(ORIGIN+'/api/v1/mcp',http_client=http,terminate_on_close=False),read_timeout_seconds=75) as client:
                    tools=await client.list_tools();result=await client.call_tool('list_intent_sources',{})
                    self.state['mcp']={'handshake':True,'tool_count':len(tools.tools),'read_error':result.is_error};self.save()
        finally:
            await self.request('DELETE','/api/organization/developer/keys/'+key_id)
            denied=await self.client.get('/api/v1/companies',headers={'authorization':'Bearer '+key['token']})
            self.state.setdefault('mcp',{})['revoked_http']=denied.status_code;self.save()
    async def run(self,phase):
        try:await getattr(self,phase)()
        finally:await self.client.aclose()
        print(json.dumps({'phase':phase,'status':'COMPLETED','summary':{k:v for k,v in self.state.items() if k not in ('http_checks','configuration')}},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['smoke','discovery','mcp']);args=p.parse_args()
    try:asyncio.run(Acceptance().run(args.phase))
    except Exception as error:print(json.dumps({'status':'FAILED','error_type':type(error).__name__,'safe_error':str(error) if isinstance(error,RuntimeError) else 'No credentials printed.'}));raise SystemExit(1)
