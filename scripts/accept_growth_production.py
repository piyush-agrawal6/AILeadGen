"""Bounded production acceptance using existing collected public evidence.

Never starts prospect discovery, creates contacts/campaigns, sends email or
increases quotas. State/request IDs survive reruns. Credentials stay in memory.
"""
import argparse,asyncio,json,uuid
from pathlib import Path
import httpx
from dotenv import dotenv_values
from scripts.accept_beta_production import Acceptance as Base,ROOT,ORIGIN

OUT=ROOT/'data/artifacts/verification/phase4-production'

class Acceptance(Base):
    def __init__(self,origin=ORIGIN):
        OUT.mkdir(parents=True,exist_ok=True,mode=0o700)
        self.file=OUT/('tag-smoke.json' if origin!=ORIGIN else 'state.json')
        self.values=dotenv_values(ROOT/'.env',interpolate=False)
        self.state=json.loads(self.file.read_text()) if self.file.exists() else {}
        self.client=httpx.AsyncClient(base_url=origin,timeout=90,follow_redirects=False)
    def save(self):
        self.file.write_text(json.dumps(self.state,indent=2));self.file.chmod(0o600)
    async def smoke(self):
        capabilities=await self.request('GET','/api/intent-radar/capabilities')
        if not capabilities.get('growth_enabled'):raise RuntimeError('Growth capability is not enabled on this revision.')
        overview=await self.request('GET','/api/intent-radar/growth/overview?days=0')
        if overview['comparison']['market_trend_proven'] is not False:raise RuntimeError('Unverified market claim.')
        if not overview['coverage']['comparable'] and overview['comparison']['percentage_change'] is not None:raise RuntimeError('Unsupported historical growth percentage.')
        self.state['overview']={k:overview[k] for k in ('sample_size','comparison','coverage','as_of')}
        for path in ('/api/intent-radar/growth/themes','/api/intent-radar/growth/research','/api/intent-radar/growth/competitors','/api/intent-radar/growth/watchlists','/api/intent-radar/growth/context'):
            await self.request('GET',path)
        await self.request('GET','/api/intent-radar/growth/overview?days=0',actor='unapproved-growth-check@example.invalid',expected=(401,403))
        safety=await self.request('GET','/api/workflow/safety')
        if safety.get('sending_enabled'):raise RuntimeError('Outbound must remain disabled.')
        self.state['sending_enabled']=False;self.save()
    async def research(self):
        overview=await self.request('GET','/api/intent-radar/growth/overview?days=0')
        if not overview['sample_size']:raise RuntimeError('No genuine collected evidence; do not substitute fixtures.')
        self.state.setdefault('research_request',str(uuid.uuid4()));self.save()
        if not self.state.get('research_id'):
            result=await self.request('POST','/api/intent-radar/growth/research',{'kind':'RESEARCH','title':'PlaneByte owner-reviewed Growth release research','question':'Which customer problems and alternative-seeking patterns are supported by these collected discussions? Identify noncommercial evidence and unknowns.','scope':{'days':0},'request_id':self.state['research_request']})
            self.state['research_id']=result['id'];self.state['research_job']=result['job_id'];self.save()
        for _ in range(14):
            result=await self.request('GET','/api/intent-radar/growth/research/'+self.state['research_id'])
            if result['status'] not in ('RUNNING','QUEUED'):break
            await asyncio.sleep(3)
        self.state['research_status']=result['status'];self.save()
        if result['status']!='COMPLETE' or not result['evidence_current']:raise RuntimeError('Real research did not complete with current evidence.')
        self.state['research_output']={k:result['output'].get(k) for k in ('mode','provider','model','usage','fallback_reason','prompt_version','schema_version')}
        self.state['citation_count']=sum(len(x['citations']) for x in [*result['output'].get('themes',[]),*result['output'].get('findings',[])])
        self.state['ai_research_pass']=result['output'].get('provider')=='VERTEX_AI' and result['output'].get('mode','').startswith('AI semantic') and self.state['citation_count']>0
        saved=await self.request('PATCH','/api/intent-radar/growth/research/'+result['id'],{'saved':True,'revision':result['revision']})
        if not saved['saved_at']:raise RuntimeError('Saving research did not persist.')
        if not self.state.get('note_added'):
            await self.request('POST','/api/intent-radar/growth/research/'+result['id']+'/notes',{'body':'Owner-controlled production release verification. Findings are tentative, cited public-source interpretations; no prospect contact or outreach is authorized by this research.'})
            self.state['note_added']=True;self.save()
        notes=await self.request('GET','/api/intent-radar/growth/research/'+result['id']+'/notes')
        if not notes['items']:raise RuntimeError('Shared research note did not persist.')
        self.state['notes_persisted']=True
        for format in ('json','md','csv'):
            path='/api/intent-radar/growth/research/'+result['id']+'/export/'+format
            # Reuse canonical signed request, but allow the actual export MIME.
            response=await self.export(path)
            self.state.setdefault('exports',{})[format]={'http':response.status_code,'bytes':len(response.content),'attachment':response.headers.get('content-disposition','').startswith('attachment;')}
            if response.status_code!=200 or not response.content:raise RuntimeError('Production export failed.')
        themes=await self.request('GET','/api/intent-radar/growth/themes')
        self.state['themes_returned']=themes['total'];self.save()
    async def export(self,path):
        import time,secrets,hmac,hashlib
        from app.api.security import canonical_request
        stamp=str(int(time.time()));nonce=secrets.token_hex(24);actor='planebyte@gmail.com'
        headers={'X-LE-User':actor,'X-LE-Timestamp':stamp,'X-LE-Nonce':nonce,'X-LE-Signature':hmac.new(self.values['LEADENGINE_API_SIGNING_SECRET'].encode(),canonical_request(stamp,nonce,'GET',path,b'',actor).encode(),hashlib.sha256).hexdigest()}
        return await self.client.get(path,headers=headers)
    async def mcp(self):
        from mcp import Client
        from mcp.client.streamable_http import streamable_http_client
        import httpx2
        issued=await self.request('POST','/api/organization/developer/keys',{'name':'Ephemeral Growth release read acceptance','scopes':['mcp:use','intent:read'],'lifetime_days':1})
        try:
            async with httpx2.AsyncClient(headers={'authorization':'Bearer '+issued['token'],'origin':'https://app.planebyte.com'},timeout=90) as http:
                async with Client(streamable_http_client(ORIGIN+'/api/v1/mcp',http_client=http,terminate_on_close=False),read_timeout_seconds=90) as client:
                    names={tool.name for tool in (await client.list_tools()).tools}
                    expected={'get_market_overview','list_market_themes','get_growth_research','list_growth_watchlists'}
                    if not expected<=names:raise RuntimeError('Growth MCP tools were not discovered.')
                    read=await client.call_tool('get_growth_research',{'id':self.state['research_id']})
                    if read.is_error:raise RuntimeError('Authorized Growth MCP read failed.')
                    denied=await client.call_tool('search_companies',{})
                    if not denied.is_error:raise RuntimeError('Intent-only key accessed company data.')
                    self.state['mcp']={'handshake':True,'growth_tools':sorted(expected),'read_pass':True,'company_scope_denied':True}
        finally:
            await self.request('DELETE','/api/organization/developer/keys/'+issued['key']['id'])
            denied=await self.client.get('/api/v1/intent-radar/growth/overview',headers={'authorization':'Bearer '+issued['token']})
            self.state.setdefault('mcp',{})['revoked_http']=denied.status_code;self.save()
    async def run(self,phase):
        try:await getattr(self,phase)()
        finally:await self.client.aclose()
        print(json.dumps({'phase':phase,'status':'COMPLETED','research_status':self.state.get('research_status'),'ai_research_pass':self.state.get('ai_research_pass'),'mcp':self.state.get('mcp'),'sending_enabled':self.state.get('sending_enabled')}))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['smoke','research','mcp']);parser.add_argument('--origin',default=ORIGIN);args=parser.parse_args()
    if args.origin not in (ORIGIN,'https://growth---leadengine-api-befca7xg4a-el.a.run.app'):raise SystemExit('Only the existing production API and its controlled revision tag are allowed.')
    if args.origin!=ORIGIN and args.phase!='smoke':raise SystemExit('Only read-only smoke checks are allowed on the revision tag.')
    try:asyncio.run(Acceptance(args.origin).run(args.phase))
    except Exception as error:print(json.dumps({'status':'FAILED','error_type':type(error).__name__,'detail':str(error) if isinstance(error,RuntimeError) else 'Inspect restricted acceptance state; no credentials printed.'}));raise SystemExit(1)
