"""Public evidence only: canonical profiles and conservative activity dates."""
import asyncio
import json
import re
import time
import uuid
from dataclasses import dataclass,asdict
from datetime import datetime,timezone,timedelta
from typing import Protocol
from urllib.parse import urlsplit,urlunsplit,urljoin,unquote
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree
from bs4 import BeautifulSoup
from app.database.prospects import now
from app.utils.http import SafeAsyncClient

DOMAINS={'instagram.com':'INSTAGRAM','facebook.com':'FACEBOOK','fb.com':'FACEBOOK','linkedin.com':'LINKEDIN','x.com':'X','twitter.com':'X','youtube.com':'YOUTUBE','tiktok.com':'TIKTOK','pinterest.com':'PINTEREST','threads.net':'THREADS','threads.com':'THREADS'}
CANONICAL={'INSTAGRAM':'www.instagram.com','FACEBOOK':'www.facebook.com','LINKEDIN':'www.linkedin.com','X':'x.com','YOUTUBE':'www.youtube.com','TIKTOK':'www.tiktok.com','PINTEREST':'www.pinterest.com','THREADS':'www.threads.net'}
IGNORE={'share','sharer','sharer.php','sharearticle','intent','login','signin','signup','accounts','account','help','support','privacy','terms','about','home','explore','search','watch','p','reel','reels','stories','pin','plugins','dialog','ads','business','developers','instagram','facebook','linkedin','twitter','youtube','tiktok','pinterest','threads','settings','hashtag','status','policies'}


def normalize_profile(value):
    try:
        p=urlsplit(str(value).strip());host=(p.hostname or '').lower()
        if p.scheme not in ('http','https') or p.username or p.password or p.port not in (None,80,443):return None
        host=host.removeprefix('www.').removeprefix('m.').removeprefix('mobile.')
        platform=DOMAINS.get(host)
        if not platform:return None
        parts=[unquote(x) for x in p.path.strip('/').split('/') if x]
        if not parts or parts[0].lower() in IGNORE:return None
        if platform=='LINKEDIN':
            if len(parts)!=2 or parts[0].lower() not in ('company','school'):return None
            handle=parts[1];path=parts[0].lower()+'/'+handle.lower()
        elif platform=='YOUTUBE':
            if len(parts)==1 and parts[0].startswith('@'):handle=parts[0][1:];path='@'+handle.lower()
            elif len(parts)==2 and parts[0] in ('channel','c','user'):handle=parts[1];path=parts[0]+'/'+handle
            else:return None
        elif platform=='FACEBOOK' and parts[0].lower()=='pages':
            if len(parts)!=3 or not parts[2].isdigit():return None
            handle=parts[1];path='pages/'+handle+'/'+parts[2]
        else:
            if len(parts)!=1:return None
            handle=parts[0].lstrip('@');path=('@' if platform in ('TIKTOK','THREADS') else '')+handle.lower()
        if len(handle)<2 or len(handle)>100 or handle.lower() in IGNORE or not re.fullmatch(r'[A-Za-z0-9_.-]+',handle):return None
        return {'platform':platform,'profile_url':'https://'+CANONICAL[platform]+'/'+path,'handle':handle}
    except (ValueError,TypeError):return None


def discover_profiles(pages=None,business=None):
    found={}
    def add(value,source,url,confidence):
        profile=normalize_profile(value)
        if not profile:return
        candidate={**profile,'source_type':source,'source_url':url,'confidence':confidence}
        prior=found.get(profile['profile_url'])
        if not prior or (prior['confidence']!='HIGH' and confidence=='HIGH'):found[profile['profile_url']]=candidate
    def walk(node,url):
        if isinstance(node,list):
            for item in node:walk(item,url)
        elif isinstance(node,dict):
            values=node.get('sameAs',[]);values=[values] if isinstance(values,str) else values
            if isinstance(values,list):
                for value in values:
                    if isinstance(value,str):add(value,'JSON_LD_SAME_AS',url,'HIGH')
            for value in node.values():
                if isinstance(value,(dict,list)):walk(value,url)
    for url,html in (pages or {}).items():
        soup=BeautifulSoup(html,'html.parser')
        for script in soup.find_all('script',type='application/ld+json'):
            try:walk(json.loads(script.string or script.get_text()),url)
            except (ValueError,TypeError):pass
        for link in soup.find_all('a',href=True):
            in_brand_area=bool(link.find_parent(['footer','header','nav']))
            source='WEBSITE_FOOTER_HEADER' if in_brand_area else 'CONTACT_ABOUT_PAGE' if re.search(r'/contact|/about',url,re.I) else 'WEBSITE_LINK'
            add(urljoin(url,link['href']),source,url,'HIGH' if in_brand_area or source=='CONTACT_ABOUT_PAGE' else 'MEDIUM')
        for meta in soup.select('meta[property="profile:username"][content],link[rel="me"][href]'):
            if meta.get('href'):add(meta['href'],'PROFILE_METADATA',url,'MEDIUM')
    if business:
        for key in ('instagram','facebook','linkedin','x_url'):
            value=getattr(business,key,None)
            if value:add(value,'OSM_TAG' if business.source_osm else 'OVERTURE_FIELD' if business.source_overture else 'INGESTED_METADATA',None,'MEDIUM')
        try:
            tags=json.loads(business.source_tags or '{}')
            if isinstance(tags,dict):
                for key,value in tags.items():
                    if 'social' in key or any(name in key for name in ('instagram','facebook','linkedin','twitter','youtube','tiktok','pinterest','threads')):
                        if isinstance(value,str):add(value,'SOURCE_TAG',None,'MEDIUM')
                        elif isinstance(value,list):
                            for url in value:
                                if isinstance(url,str):add(url,'OVERTURE_FIELD' if business.source_overture else 'SOURCE_TAG',None,'MEDIUM')
        except (ValueError,TypeError):pass
    return list(found.values())[:24]


@dataclass
class SocialActivityResult:
    status:str='UNKNOWN'
    last_activity_at:str|None=None
    source:str|None=None
    evidence_url:str|None=None
    confidence:str='LOW'
    reason:str='Recent public activity could not be reliably verified.'


class SocialActivityProvider(Protocol):
    async def check(self,profile,budget):...


def timestamp_status(value,current=None,recent=30,active=90):
    try:
        stamp=datetime.fromisoformat(str(value).replace('Z','+00:00'))
        if stamp.tzinfo is None:stamp=stamp.replace(tzinfo=timezone.utc)
        current=current or datetime.now(timezone.utc)
        if stamp>current+timedelta(minutes=5) or stamp.year<1990:return SocialActivityResult()
        days=max(0,(current-stamp).total_seconds()/86400)
        return SocialActivityResult('RECENT' if days<=recent else 'ACTIVE' if days<=active else 'STALE',stamp.isoformat(),confidence='HIGH',reason='Based on an explicit public post timestamp.')
    except (ValueError,TypeError):return SocialActivityResult()


def parse_activity(html,profile,current=None,recent=30,active=90):
    soup=BeautifulSoup(html,'html.parser')
    title=soup.title.get_text(' ',strip=True).lower() if soup.title else ''
    if soup.select('input[type="password"]') or re.search(r'log in|sign in|captcha|access denied|just a moment',title):return SocialActivityResult(reason='Public activity is unavailable behind an access restriction.')
    results=[]
    def walk(node):
        if isinstance(node,list):
            for x in node:walk(x)
        elif isinstance(node,dict):
            types=node.get('@type',[]);types=[types] if isinstance(types,str) else types
            author=node.get('author',{});author=author[0] if isinstance(author,list) and author else author
            author_url=author.get('url') if isinstance(author,dict) else None
            author_profile=normalize_profile(author_url)
            url=node.get('url') or node.get('mainEntityOfPage')
            if isinstance(url,dict):url=url.get('@id')
            if any(t in ('SocialMediaPosting','BlogPosting','VideoObject') for t in types) and author_profile and author_profile['profile_url']==profile['profile_url']:
                try:
                    parsed=urlsplit(url or '')
                    if parsed.scheme in ('http','https') and not parsed.username and (parsed.hostname or '').removeprefix('www.') in DOMAINS:
                        result=timestamp_status(node.get('datePublished') or node.get('uploadDate'),current,recent,active)
                        if result.last_activity_at:result.source='PUBLIC_POST_METADATA';result.evidence_url=url;results.append(result)
                except ValueError:pass
            for x in node.values():
                if isinstance(x,(dict,list)):walk(x)
    for script in soup.find_all('script',type='application/ld+json'):
        try:walk(json.loads(script.string or script.get_text()))
        except (ValueError,TypeError):pass
    return max(results,key=lambda r:datetime.fromisoformat(r.last_activity_at)) if results else SocialActivityResult()


class RequestBudget:
    def __init__(self,maximum=4,timeout=8):self.maximum=maximum;self.used=0;self.timeout=timeout
    async def get(self,client,url,host):
        if self.used>=self.maximum:raise TimeoutError('Social request budget reached')
        self.used+=1
        return await asyncio.wait_for(client.get(url,timeout=self.timeout,allowed_host=host),self.timeout)


class PublicWebSocialActivityProvider:
    async def check(self,profile,budget):
        from app.config.settings import get_settings
        settings=get_settings()
        if profile['platform'] in ('LINKEDIN','X'):return SocialActivityResult(reason='Profile found; no approved activity API or reliable public post evidence is configured.')
        url=profile['profile_url'];p=urlsplit(url);origin=urlunsplit((p.scheme,p.netloc,'','',''))
        try:
            async with SafeAsyncClient(timeout=budget.timeout,follow_redirects=True,redirect_limit=0,max_bytes=600000,headers={"User-Agent":settings.crawler_user_agent}) as client:
                robots=await budget.get(client,origin+'/robots.txt',p.hostname)
                if robots.status_code==200:
                    policy=RobotFileParser();policy.parse(robots.text.splitlines())
                    if not policy.can_fetch(settings.crawler_user_agent,url):return SocialActivityResult(reason='Public activity check is not permitted by robots policy.')
                elif robots.status_code!=404:return SocialActivityResult(reason='Public crawling permission could not be established.')
                response=await budget.get(client,url,p.hostname)
                if response.status_code!=200:return SocialActivityResult(reason='Public access was blocked or unavailable.')
                return parse_activity(response.text,profile,recent=settings.social_activity_recent_days,active=settings.social_activity_active_days)
        except Exception:return SocialActivityResult(reason='Public activity was unavailable within the request or timeout limit.')


class XSocialActivityProvider:
    """Extension point for a legitimately configured official API; no key required."""
    def __init__(self,official_client=None):self.client=official_client
    async def check(self,profile,budget):
        if self.client is None:return SocialActivityResult(reason='Official X activity access is not configured.')
        return await self.client.check_public_activity(profile,budget)


class MetaSocialActivityProvider(XSocialActivityProvider):
    """Official Meta public-business API adapter; disabled without explicit setup."""
    async def check(self,profile,budget):
        if self.client is None:return SocialActivityResult(reason='Official Meta activity access is not configured.')
        return await self.client.check_public_activity(profile,budget)


def presence_summary(profiles):
    if not profiles:return 'NONE'
    states={p.get('activity_status','UNKNOWN') for p in profiles}
    if states&{'RECENT','ACTIVE'}:return 'ACTIVE' if states<={'RECENT','ACTIVE'} else 'PARTIAL'
    return 'STALE' if states=={'STALE'} else 'UNKNOWN'


async def enrich_social(pages,business,enabled=True,activity=True):
    from app.config.settings import get_settings
    s=get_settings();started=time.monotonic();profiles=discover_profiles(pages,business) if enabled else []
    budget=RequestBudget(s.social_profile_max_requests_per_business,s.social_profile_timeout_seconds)
    provider=PublicWebSocialActivityProvider()
    # Per-business requests remain sequential; the pipeline shares a global
    # business semaphore, so both concurrency and total requests are bounded.
    for profile in profiles:
        result=await provider.check(profile,budget) if activity and budget.used<budget.maximum else SocialActivityResult(reason='Activity checking disabled or request budget exhausted.')
        profile.update(activity_status=result.status,last_activity_at=result.last_activity_at,activity_source=result.source,activity_evidence_url=result.evidence_url,activity_checked_at=now() if activity else None,activity_reason=result.reason)
    return profiles,{'enabled':enabled,'requests':budget.used,'seconds':round(time.monotonic()-started,3),'profiles':len(profiles),'verified':sum(p['activity_status']!='UNKNOWN' for p in profiles),'unknown':sum(p['activity_status']=='UNKNOWN' for p in profiles)}


def store_social(conn,business,profiles):
    pid=conn.execute('SELECT prospect_id FROM businesses WHERE id=?',(business.id,)).fetchone()[0]
    if not pid:return
    for p in profiles:
        existing=conn.execute('SELECT id FROM social_profiles WHERE prospect_id=? AND profile_url=?',(pid,p['profile_url'])).fetchone();key=existing[0] if existing else str(uuid.uuid4());stamp=now()
        conn.execute('''INSERT INTO social_profiles(id,prospect_id,platform,profile_url,handle,source_type,source_url,confidence,last_activity_at,activity_status,activity_source,activity_evidence_url,activity_checked_at,activity_reason,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
          ON CONFLICT(prospect_id,profile_url) DO UPDATE SET last_activity_at=COALESCE(excluded.last_activity_at,social_profiles.last_activity_at),activity_status=excluded.activity_status,activity_source=excluded.activity_source,activity_evidence_url=excluded.activity_evidence_url,activity_checked_at=excluded.activity_checked_at,activity_reason=excluded.activity_reason,updated_at=excluded.updated_at''',
          (key,pid,p['platform'],p['profile_url'],p['handle'],p['source_type'],p['source_url'],p['confidence'],p.get('last_activity_at'),p.get('activity_status','UNKNOWN'),p.get('activity_source'),p.get('activity_evidence_url'),p.get('activity_checked_at'),p.get('activity_reason'),stamp,stamp))
        conn.execute('INSERT INTO social_profile_sources(profile_id,business_id,source_type,source_url,confidence) VALUES(?,?,?,?,?) ON CONFLICT DO NOTHING',(key,business.id,p['source_type'],p['source_url'] or '',p['confidence']))
