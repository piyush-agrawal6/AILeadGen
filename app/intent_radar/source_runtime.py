"""Shared durable source budgets, coalesced requests and scoped response caches."""
import hashlib,json,time,uuid
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
from app.config.settings import get_settings
from app.database.connection import db_session
from app.database.prospects import now
from app.intent_radar.permissions import context
from app.intent_radar.source_http import JsonClient,ProviderFailure

SECRET_PARAMS={'key','api_key','access_token','client_secret','token','password'}

def period(provider,bucket):
    stamp=datetime.now(timezone.utc)
    if provider=='youtube':
        zone=ZoneInfo('America/Los_Angeles');local=stamp.astimezone(zone)
        reset=datetime.combine(local.date()+timedelta(days=1),datetime.min.time(),zone).astimezone(timezone.utc)
        return local.date().isoformat(),reset.isoformat()
    seconds=60 if bucket=='search' else 3600
    start=int(stamp.timestamp())//seconds*seconds
    return str(start),datetime.fromtimestamp(start+seconds,timezone.utc).isoformat()

def reserve(provider,bucket,capacity,*,scope='project',cost=1):
    if capacity<1 or cost<1 or cost>capacity:raise ProviderFailure('PROVIDER_QUOTA_EXHAUSTED')
    key,reset=period(provider,bucket)
    with db_session() as c:
        context(c,True)
        if getattr(c,'backend',None)=='postgres':c.execute('SELECT pg_advisory_xact_lock(691945740)')
        elif not c.in_transaction:c.execute('BEGIN IMMEDIATE')
        row=c.execute('SELECT used,capacity FROM intent_provider_budgets WHERE provider=? AND scope=? AND bucket=? AND period=?',(provider,scope,bucket,key)).fetchone()
        used=row['used'] if row else 0
        if used+cost>capacity:raise ProviderFailure('PROVIDER_QUOTA_EXHAUSTED',retry_at=reset)
        c.execute('INSERT INTO intent_provider_budgets(provider,scope,bucket,period,used,capacity,reset_at,updated_at) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(provider,scope,bucket,period) DO UPDATE SET used=intent_provider_budgets.used+excluded.used,capacity=excluded.capacity,updated_at=excluded.updated_at',(provider,scope,bucket,key,cost,capacity,reset,now()))
    return reset

def observe(provider,headers,*,scope='project',error=None):
    from app.intent_radar.connectors import cooldown
    data={key:headers[key] for key in ('x-ratelimit-limit','x-ratelimit-remaining','x-ratelimit-used','x-ratelimit-reset','x-ratelimit-resource','retry-after') if key in headers}
    if error:data['error_code']=error
    data['observed_at']=now();delay=0
    if data.get('x-ratelimit-remaining')=='0':
        try:delay=max(1,int(data['x-ratelimit-reset'])-int(time.time()))
        except (KeyError,ValueError):delay=60
    if data.get('retry-after','').isdigit():delay=max(delay,min(86400,int(data['retry-after'])))
    cooldown('source-health:'+provider+':'+scope,max(0,min(86400,delay)),data)

def health(c,provider):
    row=c.execute('SELECT next_request_at,state_json FROM intent_provider_limits WHERE id=?',('source-health:'+provider+':project',)).fetchone()
    return {'retry_at':row['next_request_at'],'provider_observation':json.loads(row['state_json'])} if row else {'retry_at':None,'provider_observation':None}

class Gateway:
    """Only provider modules choose public scope; private is the safe default.

    Public callers must use public-only endpoints/filters. Private response bodies
    are additionally encrypted with the existing workspace integration vault.
    """
    def __init__(self,c,provider,base,permit,*,headers=None,public=False,scope_tag='',seconds=25,max_requests=24):
        self.c,self.provider,self.permit=c,provider,permit
        self.org=context(c,True).organization_id
        self.scope='public' if public else 'workspace:'+self.org+(':'+scope_tag if scope_tag else '')
        self.client=JsonClient(base,permit=permit,headers=headers,seconds=seconds,max_requests=max_requests)
        self.cache_hits=0
    def fingerprint(self,path,params,body):
        params={k:v for k,v in (params or {}).items() if k.casefold() not in SECRET_PARAMS}
        return hashlib.sha256(json.dumps([self.provider,self.scope,path,params,body,'source-v2'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    def decode(self,row,fingerprint):
        if row['ciphertext']:
            from app.integrations.crypto import open_envelope
            return open_envelope(row['ciphertext'],organization_id=self.org,connection_id=fingerprint,provider=self.provider,purpose='SOURCE_CACHE')['response']
        return json.loads(row['result_json'])
    def claim(self,fingerprint):
        with db_session() as c:
            context(c,True)
            if getattr(c,'backend',None)=='postgres':c.execute('SELECT pg_advisory_xact_lock(691945741)')
            elif not c.in_transaction:c.execute('BEGIN IMMEDIATE')
            row=c.execute('SELECT * FROM intent_provider_cache WHERE provider=? AND scope=? AND fingerprint=?',(self.provider,self.scope,fingerprint)).fetchone()
            if row and row['state']=='READY' and row['expires_at']>now():return dict(row),None
            if row and row['state']=='FETCHING' and row['lease_until'] and row['lease_until']>now():raise ProviderFailure('PROVIDER_REQUEST_QUEUED',retry_at=row['lease_until'])
            lease=str(uuid.uuid4());until=(datetime.now(timezone.utc)+timedelta(seconds=45)).isoformat()
            c.execute("INSERT INTO intent_provider_cache(provider,scope,fingerprint,result_json,expires_at,state,lease_owner,lease_until,updated_at) VALUES(?,?,?,'{}',?,'FETCHING',?,?,?) ON CONFLICT(provider,scope,fingerprint) DO UPDATE SET state='FETCHING',lease_owner=excluded.lease_owner,lease_until=excluded.lease_until,updated_at=excluded.updated_at",(self.provider,self.scope,fingerprint,now(),lease,until,now()))
            return dict(row) if row else None,lease
    def queue(self,fingerprint,code,retry):
        from app.platform.context import current
        discovery_id=getattr(self.permit,'discovery_id',None)
        if not discovery_id:return
        key=str(uuid.uuid5(uuid.NAMESPACE_URL,self.org+':'+self.provider+':'+discovery_id+':'+fingerprint))
        with db_session() as c:
            context(c,True)
            c.execute("INSERT INTO intent_provider_requests(id,organization_id,actor,provider,discovery_id,monitor_id,fingerprint,state,attempts,retry_at,detail_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,'QUEUED',1,?,?,?,?) ON CONFLICT(id) DO UPDATE SET state='QUEUED',retry_at=excluded.retry_at,detail_json=excluded.detail_json,updated_at=excluded.updated_at",(key,self.org,current().actor,self.provider,discovery_id,getattr(self.permit,'monitor_id',None),fingerprint,retry,json.dumps({'code':code}),now(),now()))
    def store(self,fingerprint,lease,result,ttl,headers):
        from app.intent_radar.connectors import cache_fence
        cache_fence(self.permit)
        encrypted=None;encoded=json.dumps(result)
        if self.scope!='public':
            from app.integrations.crypto import seal
            encrypted=seal({'response':result},organization_id=self.org,connection_id=fingerprint,provider=self.provider,purpose='SOURCE_CACHE');encoded='{}'
        with db_session() as c:
            context(c,True)
            if not c.execute("UPDATE intent_provider_cache SET result_json=?,ciphertext=?,etag=?,last_modified=?,expires_at=?,state='READY',lease_owner=NULL,lease_until=NULL,updated_at=? WHERE provider=? AND scope=? AND fingerprint=? AND lease_owner=?",(encoded,encrypted,headers.get('etag'),headers.get('last-modified'),(datetime.now(timezone.utc)+timedelta(seconds=min(ttl,2592000))).isoformat(),now(),self.provider,self.scope,fingerprint,lease)).rowcount:raise ProviderFailure('PROVIDER_CACHE_LEASE_REPLACED')
    async def request(self,path,*,params=None,method='GET',body=None,ttl=300,bucket='core',capacity=None,cost=1):
        self.permit();fingerprint=self.fingerprint(path,params,body)
        old,lease=self.claim(fingerprint)
        if lease is None:
            self.permit();self.cache_hits+=1;return self.decode(old,fingerprint)
        try:
            # Provider-native cooldown is independent of individual user jobs.
            row=self.c.execute('SELECT next_request_at FROM intent_provider_limits WHERE id=?',('source-health:'+self.provider+':project',)).fetchone()
            if row and row['next_request_at']>now():raise ProviderFailure('PROVIDER_RATE_LIMITED',retry_at=row['next_request_at'])
            default=100 if self.provider=='youtube' and bucket=='search' else 10000 if self.provider=='youtube' else 30 if bucket=='search' else 5000
            reset=reserve(self.provider,bucket,capacity or default,cost=cost)
            conditional={}
            if old and old['state']=='READY':conditional={k:v for k,v in {'If-None-Match':old['etag'],'If-Modified-Since':old['last_modified']}.items() if v}
            result=await self.client.request(path,params=params,method=method,body=body,headers=conditional)
            if result=={'not_modified':True}:
                if not old:raise ProviderFailure('PROVIDER_CACHE_VALIDATOR_INVALID')
                result=self.decode(old,fingerprint)
            self.store(fingerprint,lease,result,ttl,self.client.last_headers)
            observe(self.provider,self.client.last_headers)
            return result
        except BaseException as error:
            with db_session() as c:
                c.execute("UPDATE intent_provider_cache SET state='FAILED',lease_owner=NULL,lease_until=NULL WHERE provider=? AND scope=? AND fingerprint=? AND lease_owner=?",(self.provider,self.scope,fingerprint,lease))
            if isinstance(error,ProviderFailure):
                retry=error.retry_at or (reset if 'QUOTA' in error.code and 'reset' in locals() else None)
                if 'QUOTA' in error.code and not retry:retry=period(self.provider,bucket)[1]
                if retry:self.queue(fingerprint,error.code,retry)
                observe(self.provider,self.client.last_headers,error=error.code)
            raise
