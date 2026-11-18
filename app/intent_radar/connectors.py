"""Capability-driven authorized connectors, bounded public transport and durable cooldowns."""
import hashlib
import json
import time
import uuid
import logging
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlencode, urlsplit, urlunsplit,parse_qsl
from xml.etree import ElementTree as ET
from typing import Any,Awaitable,Callable,Protocol
from fastapi import HTTPException
from app.config.settings import get_settings
from app.database.connection import db_session
from app.database.prospects import now
from app.intent_radar import models, providers
from app.intent_radar.permissions import context
from app.utils.http import SafeAsyncClient

class SourceLogRedaction(logging.Filter):
    def filter(self,record):
        value=record.getMessage()
        if any(host in value for host in ('api.stackexchange.com','googleapis.com','github.com','bsky.app','bsky.social')):
            record.msg=re.sub(r'([?&](?:key|api_key|access_token|client_secret|token)=)[^&\s]+',r'\1[REDACTED]',value)
            record.args=()
        return True

logging.getLogger('httpx').addFilter(SourceLogRedaction())

class SourceUnavailable(RuntimeError):
    def __init__(self, code, retry_at=None):
        self.code, self.retry_at = code, retry_at
        super().__init__(code)

def cache_fence(permit):
    permit()
    callback=getattr(permit,'fence',None)
    if callback:callback()

def canonical(url):
    p=urlsplit(url)
    if p.scheme!='https' or not p.hostname or p.username or p.password or p.port not in (None,443):raise ValueError('Public HTTPS URLs are required.')
    return urlunsplit(('https',p.hostname,p.path or '/',p.query,''))

def approved_endpoint(url):
    url=canonical(url)
    if any(key.casefold() in {'token','access_token','api_key','key','auth','authorization','password'} for key,_ in parse_qsl(urlsplit(url).query)):
        raise HTTPException(422,'Only public feed endpoints without authentication parameters are supported.')
    host=urlsplit(url).hostname
    if host not in get_settings().intent_radar_approved_feed_hosts.split(';'):raise HTTPException(403,'This source host has not been approved by the platform operator.')
    from app.utils.urls import is_safe_url
    if not is_safe_url(url,check_dns=True):raise HTTPException(422,'Source endpoint is not a public destination.')
    return url

def configurations(c):
    org=context(c).organization_id
    return [{'id':r['id'],**json.loads(r['configuration_json'])} for r in c.execute('SELECT * FROM intent_source_configs WHERE organization_id=? ORDER BY id LIMIT 20',(org,)).fetchall()]

def configure(c,body,key=None):
    ctx=context(c,True,True);endpoint=approved_endpoint(body.endpoint)
    if body.family=='discourse' and not urlsplit(endpoint).path.endswith(('.rss','.atom')):raise HTTPException(422,'This Discourse adapter supports explicitly permitted public RSS/Atom endpoints only.')
    if key and not any(x['id']==key for x in configurations(c)):raise HTTPException(404,'Source configuration not found.')
    if not key and len(configurations(c))>=20:raise HTTPException(429,'Approved feed limit reached.')
    key=key or str(uuid.uuid4())
    c.execute('INSERT INTO intent_source_configs(organization_id,id,configuration_json,updated_at) VALUES(?,?,?,?) ON CONFLICT(organization_id,id) DO UPDATE SET configuration_json=excluded.configuration_json,updated_at=excluded.updated_at',(ctx.organization_id,key,body.model_copy(update={'endpoint':endpoint}).model_dump_json(),now()))
    from app.intent_radar.service import audit
    audit(c,'SOURCE_CONFIGURED',key)
    return {'id':key,**body.model_dump()}

def catalog(c=None):
    s=get_settings();configs=configurations(c) if c else []
    definitions=[('hacker_news','Hacker News','Available','Official public v0 API','https://github.com/HackerNews/API',['recent_feed','bounded_comments'],['feeds','date_local','keywords_local'],22,'Recent Ask/Show/New/Top/Best; jobs opt-in. No historical search.'),
        ('stack_exchange','Stack Exchange','Available' if s.intent_radar_stackexchange_enabled else 'Requires approval','Official API 2.3','https://api.stackexchange.com/docs',['keyword_search'],['sites','tags','date','keywords'],3,'Configured professional communities; bounded question search, not the whole network.'),
        ('discourse','Approved Discourse','Available' if any(x['family']=='discourse' and x['enabled'] for x in configs) else 'Not configured','Approved public RSS/Atom','https://meta.discourse.org',['recent_feed'],['approved_feeds','date_local','keywords_local'],4,'Only configured public topic feeds; no private posts or general forum search.'),
        ('rss','RSS / Atom','Available' if any(x['family']=='rss' and x['enabled'] for x in configs) else 'Not configured','Approved public RSS/Atom','https://www.rssboard.org/rss-specification',['recent_feed'],['approved_feeds','date_local','keywords_local'],4,'Approved publication/community feed windows only; no website crawling.')]
    result=[dict(id=i,name=n,state=state,access=access,documentation=doc,discovery_modes=modes,filters=filters,request_limit_per_check=cap,coverage=coverage,
        category='Public discussion' if i!='rss' else 'Publication',authentication='Optional server application key' if i=='stack_exchange' else 'Public only',
        approved_scope='No posting, private content or author profiling',pagination='Bounded native offset/page; feed snapshot',concurrency=1,
        rate_policy='Durable IP/method cooldown; minimum 60s identical requests' if i=='stack_exchange' else 'Bounded sequential requests; configured polling interval',
        retry_policy='No retry within source job; retry after reported cooldown',attribution='Original link and source; CC BY-SA attribution for Stack Exchange',
        retention='Metadata and permitted excerpts only; feed retention configured up to 30 days',freshness='Source snapshot, no global completeness claim',
        language='Unverified',geography='Unknown',request_cost='No purchased quota; monetary cost unmeasured') for i,n,state,access,doc,modes,filters,cap,coverage in definitions]
    for source in result:
        key=source['id'];source['configured']=source['state']=='Available'
        source['capabilities']=source['discovery_modes']+source['filters']
        source['permission']='Official public API; no private access or posting.' if key=='hacker_news' else 'Owner-approved commercial API terms, site scope and CC BY-SA attribution; optional server application key.' if key=='stack_exchange' else 'Publisher-approved public feed endpoint, terms reference, attribution and retention policy required.'
        source['missing']=[] if source['configured'] else ['INTENT_RADAR_STACKEXCHANGE_ENABLED after commercial approval'] if key=='stack_exchange' else ['An enabled reviewed '+key+' workspace feed configuration']
        if key in ('rss','discourse') and not s.intent_radar_approved_feed_hosts:source['missing'].append('INTENT_RADAR_APPROVED_FEED_HOSTS')
        if key=='hacker_news':source['retry_policy']='At most one short 429/503 retry inside the 22-request budget; longer cooldowns surface as errors.'
    return result

def validate(c,q):
    states={x['id']:x for x in catalog(c)}
    for key in q.sources:
        if states[key]['state']!='Available':raise HTTPException(409,states[key]['name']+': '+states[key]['state'])
    if q.semantic and not q.offerings:raise HTTPException(422,'Semantic candidate collection requires explicit relevant offerings.')
    if q.semantic:context(c,True,True)
    if q.tags and 'stack_exchange' not in q.sources:raise HTTPException(422,'Tag search is supported only by the selected Stack Exchange connector.')
    if q.hn_comments and 'hacker_news' not in q.sources:raise HTTPException(422,'HN comment collection requires Hacker News selection.')
    if 'stack_exchange' in q.sources and (not q.sites or any(site not in get_settings().intent_radar_stackexchange_sites.split(';') for site in q.sites)):raise HTTPException(422,'Select configured Stack Exchange sites.')
    configs={x['id']:x for x in configurations(c)}
    for key in q.feed_ids:
        if str(key) not in configs or not configs[str(key)]['enabled'] or configs[str(key)]['family'] not in q.sources:raise HTTPException(404,'Enabled approved source configuration not found.')
    for family in ('rss','discourse'):
        if family in q.sources and not any(configs.get(str(k),{}).get('family')==family for k in q.feed_ids):raise HTTPException(422,'Select an approved feed for '+family+'.')
    if q.icp_id:
        from app.icp.service import get
        get(c,str(q.icp_id))

def cooldown(key,seconds,state=None):
    """Separate committed reservation survives worker crashes and transaction rollback."""
    with db_session() as c:
        if getattr(c,'backend',None)=='postgres':c.execute('SELECT pg_advisory_xact_lock(691945728)')
        elif not c.in_transaction:c.execute('BEGIN IMMEDIATE')
        stamp=now();row=c.execute('SELECT * FROM intent_provider_limits WHERE id=?',(key,)).fetchone()
        if state is None and row and row['next_request_at']>stamp:raise SourceUnavailable('RATE_LIMITED',row['next_request_at'])
        until=(datetime.now(timezone.utc)+timedelta(seconds=seconds)).isoformat()
        c.execute('INSERT INTO intent_provider_limits(id,next_request_at,state_json) VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET next_request_at=excluded.next_request_at,state_json=excluded.state_json',(key,until,json.dumps(state or {})))

def normalized(source,key,url,title,excerpt,published,**metadata):
    if not published or not title:return None
    try:
        date=datetime.fromtimestamp(published,timezone.utc) if type(published) is int else datetime.fromisoformat(published.replace('Z','+00:00'))
        if date.tzinfo is None:return None
        stamp=date.astimezone(timezone.utc).isoformat()
        from app.intent_radar.feeds import reference
        url=reference(url)
        metadata=models.Provenance.model_validate(metadata).model_dump(exclude_none=True)
    except (ValueError,OverflowError,TypeError):return None
    title=providers.text(title,300);excerpt=providers.text(excerpt,3000)
    return dict(source=source,source_record_id=str(key),source_url=url,title=title,excerpt=excerpt,observed_at=stamp,retrieved_at=now(),removed=False,
        provenance=metadata,content_fingerprint=hashlib.sha256((title+'\n'+excerpt).encode()).hexdigest())

class StackExchange:
    async def fetch(self,c,q,permit):
        org=context(c).organization_id;items=[];requests=0;quota=None;cursor={'sites':{}}
        for site in q.sites:
            old=q._collection_cursor.get('sites',{}).get(site,{})
            permit();params={'site':site,'q':' '.join(q.keywords),'pagesize':max(1,min(20,q.result_limit//max(1,len(q.sources)*len(q.sites)))),'page':old.get('page',1),'sort':'creation','order':'desc','filter':'withbody'}
            if q.tags:params['tagged']=';'.join(q.tags)
            for field,day in (('fromdate',q.from_date),('todate',q.to_date)):
                if day:params[field]=int(datetime.combine(day,datetime.min.time(),timezone.utc).timestamp())+(86399 if field=='todate' else 0)
            fingerprint=hashlib.sha256(json.dumps(params,sort_keys=True).encode()).hexdigest()
            if old.get('since'):params['fromdate']=max(params.get('fromdate',0),int(old['since']))
            fingerprint=hashlib.sha256(json.dumps(params,sort_keys=True).encode()).hexdigest()
            row=c.execute('SELECT result_json FROM intent_source_cache WHERE organization_id=? AND fingerprint=? AND expires_at>?',(org,fingerprint,now())).fetchone()
            if row:
                saved=json.loads(row[0])
                items.extend(saved if isinstance(saved,list) else saved['items'])
                if isinstance(saved,dict):cursor['sites'][site]=saved['cursor']
                continue
            cooldown('stack_exchange:ip',1);cooldown('stack_exchange:search/advanced',1)
            cooldown('stack_exchange:query:'+fingerprint,60)
            key=get_settings().intent_radar_stackexchange_key.get_secret_value()
            if key:params['key']=key
            async with SafeAsyncClient(timeout=5,max_bytes=500000,redirect_limit=0) as client:
                response=await client.get('https://api.stackexchange.com/2.3/search/advanced?'+urlencode(params),allowed_host='api.stackexchange.com');requests+=1
            permit()
            if response.status_code==429:
                delay=response.headers.get('Retry-After','60');cooldown('stack_exchange:search/advanced',min(86400,int(delay)) if delay.isdigit() else 60,{'code':'RATE_LIMITED'})
                raise SourceUnavailable('RATE_LIMITED')
            response.raise_for_status();data=response.json()
            if type(data.get('backoff')) is int:cooldown('stack_exchange:search/advanced',max(1,min(86400,data['backoff'])),{'backoff':data['backoff']})
            quota=data.get('quota_remaining')
            if quota==0:cooldown('stack_exchange:ip',86400,{'quota_remaining':0})
            if data.get('error_id'):raise SourceUnavailable('PROVIDER_ERROR')
            times=[native.get('creation_date',0) for native in data.get('items',[]) if type(native.get('creation_date')) is int]
            newest=max([*times,old.get('newest',0),old.get('since',0)])
            cursor['sites'][site]={'page':params['page']+1 if data.get('has_more') else 1,'since':params.get('fromdate',0) if data.get('has_more') else max(0,newest-120),'newest':newest if data.get('has_more') else 0}
            batch=[]
            for native in data.get('items',[])[:20]:
                if type(native.get('question_id')) is not int:continue
                item=normalized('Stack Exchange',site+':'+str(native['question_id']),native.get('link',''),native.get('title'),native.get('body'),native.get('creation_date'),site=site,tags=native.get('tags',[])[:10],updated_at=native.get('last_activity_date'),
                    attribution={'author':providers.text(native.get('owner',{}).get('display_name'),100),'profile_url':native.get('owner',{}).get('link'),'license':native.get('content_license','CC BY-SA'),'source':'Stack Exchange'},fetch_method='official_api')
                if item:batch.append(item)
            items.extend(batch)
            # No transaction is opened during network calls; caller commits cache safely.
            cache_fence(permit)
            c.execute('INSERT INTO intent_source_cache(organization_id,fingerprint,result_json,expires_at) VALUES(?,?,?,?) ON CONFLICT(organization_id,fingerprint) DO UPDATE SET result_json=excluded.result_json,expires_at=excluded.expires_at',(org,fingerprint,json.dumps({'items':batch,'cursor':cursor['sites'][site]}),(datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat()))
            c.commit()
            if site!=q.sites[-1]:
                import asyncio
                await asyncio.sleep(1.05)
        return {'items':items,'requests':requests,'scanned':len(items),'next_offset':None,'quota_remaining':quota,'cursor':cursor,'coverage':'Official bounded question search with resumable page/date cursors for '+', '.join(q.sites)}

def parse_feed(content,config):
    from app.intent_radar.feeds import parse
    return parse(content,config,normalized)

class Feed:
    async def one(self,c,config,permit,meter):
        org=context(c).organization_id
        permit();url=approved_endpoint(config['endpoint']);fingerprint='feed:'+config['id']
        cached=c.execute('SELECT * FROM intent_source_cache WHERE organization_id=? AND fingerprint=?',(org,fingerprint)).fetchone()
        old=json.loads(cached['result_json']) if cached else {}
        configuration_hash=hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()
        # An approval/endpoint/retention edit cannot reuse evidence or validators
        # collected under a different configuration, even within the cache TTL.
        if old.get('configuration_hash')!=configuration_hash:old={}
        if old and cached['expires_at']>now():return old.get('items',[])
        cooldown('feed:'+hashlib.sha256(url.encode()).hexdigest(),config['polling_minutes']*60)
        headers={k:v for k,v in {'If-None-Match':old.get('etag'),'If-Modified-Since':old.get('last_modified')}.items() if v}
        # Final, explicitly approved endpoints only; no hidden redirect requests.
        async with SafeAsyncClient(timeout=5,max_bytes=500000,redirect_limit=0) as client:
            meter['requests']+=1
            response=await client.get(url,allowed_host=urlsplit(url).hostname,headers=headers)
        permit()
        if response.status_code==304:batch=[{**x,'retrieved_at':now()} for x in old.get('items',[])]
        else:response.raise_for_status();batch=parse_feed(response.content,config)
        cache_fence(permit)
        c.execute('INSERT INTO intent_source_cache(organization_id,fingerprint,result_json,expires_at) VALUES(?,?,?,?) ON CONFLICT(organization_id,fingerprint) DO UPDATE SET result_json=excluded.result_json,expires_at=excluded.expires_at',(org,fingerprint,json.dumps({'items':batch,'configuration_hash':configuration_hash,'etag':response.headers.get('ETag',old.get('etag')),'last_modified':response.headers.get('Last-Modified',old.get('last_modified'))}),(datetime.now(timezone.utc)+timedelta(minutes=config['polling_minutes'])).isoformat()))
        c.commit()
        return batch

    async def fetch(self,c,q,permit,family):
        context(c);items=[];errors=[];meter={'requests':0}
        configs=[x for x in configurations(c) if x['family']==family and x['id'] in list(map(str,q.feed_ids))]
        for config in configs:
            try:items.extend(await self.one(c,config,permit,meter))
            except Exception as exc:
                c.rollback();permit()
                # Invalid execution is never downgraded to an ordinary source error.
                from app.intent_radar.discovery import ExecutionInvalidated
                if isinstance(exc,ExecutionInvalidated):raise
                errors.append({'feed_id':config['id'],'code':getattr(exc,'code','UNAVAILABLE'),'retry_at':getattr(exc,'retry_at',None)})
        seen=q._collection_cursor.get('seen_ids',[])
        ids=lambda item:hashlib.sha256((item['source_record_id']+'\n'+item['content_fingerprint']).encode()).hexdigest()
        candidates=[item for item in items if ids(item) not in seen]
        selected=candidates[:max(1,(q.result_limit+len(q.sources)-1)//len(q.sources))]
        return {'items':selected,'requests':meter['requests'],'scanned':len(items),'next_offset':None,'cursor':{'seen_ids':list(dict.fromkeys([*(ids(item) for item in selected),*seen]))[:600]},'errors':errors,'status':'PARTIAL' if errors and selected else 'UNAVAILABLE' if errors else 'COMPLETE','coverage':'Configured public feed snapshots with incremental observation IDs; no historical search.'+(f' {len(errors)} selected feed(s) failed.' if errors else '')}

class SourceCollector(Protocol):
    def __call__(self,c:Any,q:models.Search,key:str,permit:Callable[[],bool])->Awaitable[models.SourceResult]:...

async def fetch(c:Any,q:models.Search,key:str,permit:Callable[[],bool])->models.SourceResult:
    return models.SourceResult.model_validate(await _fetch(c,q,key,permit))

async def _fetch(c,q,key,permit):
    if key=='hacker_news':
        if q._collection_cursor or len(q.sources)>1 or q.result_limit!=20:return await providers.HackerNews().fetch(permit=permit,feeds=q.hn_feeds,comments=q.hn_comments,limit=max(1,(q.result_limit+len(q.sources)-1)//len(q.sources)),seen_ids=q._collection_cursor.get('seen_ids',[]))
        # Keep Phase 1 transport/testing contract intact for the original default.
        if q.hn_feeds==['ask'] and not q.hn_comments:return await providers.HackerNews().fetch(permit=permit)
        return await providers.HackerNews().fetch(permit=permit,feeds=q.hn_feeds,comments=q.hn_comments)
    if key=='stack_exchange':return await StackExchange().fetch(c,q,permit)
    return await Feed().fetch(c,q,permit,key)
