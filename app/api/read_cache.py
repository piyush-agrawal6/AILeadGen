"""Authenticated read acceleration only. PostgreSQL remains the source of truth."""
import asyncio,hashlib,json,time
import re
from collections import OrderedDict,Counter
from urllib.parse import parse_qsl,urlsplit
import httpx
from starlette.responses import Response
from app.config.settings import get_settings

# Explicit allowlist: never cache eligibility, previews, sending, provider health,
# tracking, unsubscribe, inbox content, exports or authorization decisions.
READS={
    '/api/workflow/dashboard':10,'/api/operations/campaigns':15,
    '/api/operations/dashboard':10,
    '/api/operations/runs':10,'/api/operations/messages':10,
    '/api/operations/reports':15,'/api/operations/schedules':15,
    '/api/automation/master-leads':10,'/api/intelligence/overview':15,
    '/api/intelligence/leads':10,'/api/verticals':300,
    '/api/markets':300,'/api/workflow/defaults':60,
    '/api/settings':60,'/api/foundation/countries':86400,
    '/api/foundation/locations':86400,
}
MAX_BODY=512_000

class ReadCache:
    def __init__(self,*,allow_test_network=False):
        self.allow_test_network=allow_test_network
        self.client=None;self.failed_until=0;self.local=OrderedDict();self.locks={};self.metrics=Counter();self.generation=0;self.last_success=None

    def configuration(self):
        s=get_settings();url=s.upstash_redis_rest_url.rstrip('/')
        if getattr(s,'app_env',None)=='test' and not self.allow_test_network:return None
        parsed=urlsplit(url)
        if not(url and s.upstash_redis_rest_token):return None
        if parsed.scheme!='https' or not parsed.hostname or not parsed.hostname.endswith('.upstash.io') or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path:
            return None
        namespace=hashlib.sha256((s.database_url or s.database_path).encode()).hexdigest()[:16]
        return url,s.upstash_redis_rest_token,'leadengine:reads:v1:'+namespace

    async def command(self,*args):
        cfg=self.configuration()
        if not cfg or time.monotonic()<self.failed_until:return None
        try:
            if self.client is None:self.client=httpx.AsyncClient(timeout=httpx.Timeout(.6,connect=.3),limits=httpx.Limits(max_connections=12,max_keepalive_connections=6))
            r=await self.client.post(cfg[0],json=list(args),headers={'Authorization':'Bearer '+cfg[1]})
            r.raise_for_status();body=r.json()
            if 'error' in body:raise ValueError('Redis command rejected')
            from datetime import datetime,timezone
            self.last_success=datetime.now(timezone.utc).isoformat()
            return body['result']
        except (httpx.HTTPError,ValueError,KeyError):
            self.metrics['errors']+=1;self.failed_until=time.monotonic()+30
            # Cache failure never blocks access to live database state.
            return None

    async def invalidate(self):
        self.local.clear();self.generation+=1
        cfg=self.configuration()
        if cfg:await self.command('INCR',cfg[2]+':generation')

    async def handle(self,request,call_next):
        path=request.url.path;ttl=READS.get(path,0)
        if re.fullmatch(r'/api/operations/campaigns/[a-f0-9-]{36}(?:/leads)?',path):ttl=10
        if re.fullmatch(r'/api/foundation/campaigns/[a-f0-9-]{36}/(?:intelligence|comparison)',path):ttl=10
        if re.fullmatch(r'/api/acquisition/jobs/[a-f0-9-]{36}',path):ttl=5
        # Successful writes invalidate all read models; no scanning of Redis keys.
        if request.method not in ('GET','HEAD','OPTIONS'):
            response=await call_next(request)
            if response.status_code<400 and path not in ('/api/workflow/eligible','/api/foundation/repeat'):await self.invalidate()
            return response
        if request.method!='GET' or not ttl or request.headers.get('cache-control')=='no-cache':return await call_next(request)
        cfg=self.configuration()
        # Disabled means genuinely disabled; no hidden stale local fallback.
        if not cfg or time.monotonic()<self.failed_until:return await call_next(request)
        generation=await self.command('GET',cfg[2]+':generation')
        if time.monotonic()<self.failed_until:return await call_next(request)
        # Preserve repeated-parameter order (FastAPI uses the last value).
        # Organization context is part of the identity: tenant responses must
        # never be served across companies, even for the same user account.
        identity=[request.state.user_email,getattr(request.state,'organization_id',None),path,sorted(parse_qsl(request.url.query,keep_blank_values=True),key=lambda item:item[0]),generation or '0']
        key=cfg[2]+':'+hashlib.sha256(json.dumps(identity,separators=(',',':')).encode()).hexdigest()
        if key not in self.locks:
            if len(self.locks)>=128:return await call_next(request)
            self.locks[key]=[asyncio.Lock(),0]
        entry=self.locks[key];entry[1]+=1
        try:
            async with entry[0]:
                cached=await self.command('GET',key)
                if cached:
                    try:
                        body=json.loads(cached)
                        if isinstance(body,dict) and isinstance(body.get('body'),str):
                            self.metrics['hits']+=1
                            return Response(body['body'],media_type='application/json',headers={'Cache-Control':'private, no-store','X-LE-Cache':'HIT'})
                    except (ValueError,TypeError):pass
                self.metrics['misses']+=1
                started=time.monotonic();response=await call_next(request)
                if response.status_code!=200 or 'application/json' not in response.headers.get('content-type','') or response.headers.get('set-cookie'):return response
                # Only allowlisted JSON responses are buffered; streams/PDFs bypass.
                parts=[];size=0
                async for chunk in response.body_iterator:
                    parts.append(chunk);size+=len(chunk)
                raw=b''.join(parts)
                if size<=MAX_BODY:
                    try:
                        text=raw.decode('utf-8');json.loads(text)
                        await self.command('SET',key,json.dumps({'body':text},separators=(',',':')),'EX',ttl)
                    except (UnicodeError,ValueError):pass
                headers=dict(response.headers);headers.update({'Cache-Control':'private, no-store','X-LE-Cache':'MISS','Server-Timing':f'origin;dur={(time.monotonic()-started)*1000:.1f}'})
                return Response(raw,status_code=response.status_code,headers=headers,background=response.background)
        finally:
            entry[1]-=1
            if entry[1]==0:self.locks.pop(key,None)

    def health(self):
        return {'configured':bool(self.configuration()),'state':'DEGRADED' if time.monotonic()<self.failed_until else 'READY' if self.last_success else 'CONFIGURED' if self.configuration() else 'DISABLED','last_success_at':self.last_success,'process_counters':dict(self.metrics),'operational_ttl_seconds':15,'reference_ttl_seconds':86400,'safety_decisions_cached':False}

    async def close(self):
        if self.client:await self.client.aclose();self.client=None

read_cache=ReadCache()
