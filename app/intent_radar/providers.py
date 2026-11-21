"""Official public HN API only. Recent Ask HN coverage; no historical search claim."""
import httpx
import asyncio, hashlib, re, time, warnings
from datetime import datetime, timezone
from html import unescape
from typing import Protocol
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
from app.utils.http import SafeAsyncClient

warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)

HOST = 'hacker-news.firebaseio.com'
BASE = 'https://' + HOST + '/v0/'

class Source(Protocol):
    async def fetch(self, offset: int = 0) -> dict: ...

def text(value, limit):
    return re.sub(r'\s+', ' ', BeautifulSoup(str(value or '')[:50000], 'html.parser').get_text(' ', strip=True)).strip()[:limit]

def normalize(item, *, content_kind='story', parent_id=None, depth=0):
    if not isinstance(item, dict) or type(item.get('id')) is not int or not 1 <= item['id'] <= 9223372036854775807: return None
    key = str(item['id'])
    if item.get('deleted') or item.get('dead'): return {'source': 'Hacker News', 'source_record_id': key, 'removed': True}
    if item.get('type') != 'story' or type(item.get('time')) is not int or not item.get('title'): return None
    try: observed = datetime.fromtimestamp(item['time'], timezone.utc).isoformat()
    except (ValueError, OverflowError, OSError): return None
    title=text(item['title'],300);excerpt=text(item.get('text'),3000)
    provenance={'fetch_method':'official_hn','content_kind':content_kind}
    if parent_id:provenance['parent_id']=str(parent_id)
    if depth:provenance['depth']=depth
    metrics={}
    if type(item.get('score')) is int:metrics['score']=item['score']
    if type(item.get('descendants')) is int:metrics['comments']=item['descendants']
    if metrics:provenance['metrics']=metrics
    return {'source': 'Hacker News', 'source_record_id': key, 'source_url': 'https://news.ycombinator.com/item?id=' + key,
            'title': title, 'excerpt': excerpt,'content_fingerprint':hashlib.sha256((title+'\n'+excerpt).encode()).hexdigest(),'provenance':provenance,
            'observed_at': observed, 'retrieved_at': datetime.now(timezone.utc).isoformat(), 'removed': False}

class HackerNews:
    async def fetch(self, offset=0, permit=None, feeds=None, comments=False,limit=20,seen_ids=None,use_updates=False):
        if not 0 <= offset <= 180: raise ValueError('Recent source offset is outside the supported window.')
        started = time.monotonic()
        deadline = started + 24  # leave headroom inside the worker's 28s source deadline
        interrupted = False
        requests = 0
        slowest_read = 0.0
        max_requests = 22 if (feeds is None or feeds == ['ask']) and not comments and not use_updates else 30
        async with SafeAsyncClient(timeout=4, max_bytes=200000, redirect_limit=0, headers={'User-Agent': 'PlaneByte-IntentRadar/2.0 (public API evidence; no posting)'}) as client:
            async def get(path):
                nonlocal requests,slowest_read
                for attempt in range(2):
                    check_started=time.monotonic()
                    if permit and not permit():raise RuntimeError('The job is no longer authorized or active.')
                    if requests >= max_requests or time.monotonic() >= deadline: raise TimeoutError('Source request budget exhausted.')
                    requests += 1
                    response = await asyncio.wait_for(client.get(BASE + path, allowed_host=HOST), timeout=max(.001, deadline-time.monotonic()))
                    slowest_read=max(slowest_read,time.monotonic()-check_started)
                    if response.status_code in (429, 503) and attempt == 0:
                        # Never evade limits; one bounded retry, otherwise record source failure.
                        delay=response.headers.get('Retry-After','1')
                        if not delay.isdigit() or int(delay)>3:raise RuntimeError('Source requests a longer cooldown; retry manually later.')
                        await asyncio.sleep(max(1,int(delay))); continue
                    response.raise_for_status()
                    return response.json()
                raise RuntimeError('Source unavailable')
            names={'ask':'askstories','show':'showstories','new':'newstories','top':'topstories','best':'beststories','jobs':'jobstories'}
            feeds=feeds or ['ask']
            if not 1<=len(feeds)<=6 or any(f not in names for f in feeds):raise ValueError('Unsupported HN feed.')
            batches=[]
            for feed in feeds:
                batch=await get(names[feed]+'.json')
                if not isinstance(batch,list):raise ValueError('Unsupported source response.')
                batches.append([x for x in batch[:200] if type(x) is int and x>0])
            updated_items=[]
            if use_updates and requests < max_requests - 4:
                try:
                    updates=await get('updates.json')
                    if isinstance(updates,dict) and isinstance(updates.get('items'),list):
                        updated_items=[x for x in updates['items'][:30] if type(x) is int and x>0]
                except (httpx.HTTPError,TimeoutError):
                    pass  # Optional updates; never swallow permission/lease failures.
            # Round-robin coverage prevents a large feed from hiding selected feeds.
            from itertools import zip_longest
            ids=list(dict.fromkeys(x for group in zip_longest(*batches) for x in group if x is not None))
            if updated_items:
                seen_set=set(str(x) for x in (seen_ids or []))
                # Re-check updated stories that we previously saw (for edits/deletions/new replies)
                recheck=[x for x in updated_items if str(x) in seen_set][:5]
                ids=list(dict.fromkeys([*recheck, *ids]))
            if seen_ids and not comments and not updated_items:ids=[key for key in ids if str(key) not in set(seen_ids)]
            requested=max(1,min(20,limit));processed=[]
            # A bounded feed *sample*, not a full-text query. Plan root count up front
            # using the measured first round trip (including the authorization check).
            # Each root can entail one story and up to four explicitly requested replies.
            cost=5 if comments else 1
            window=max(1,min(requested,(max_requests-requests)//cost,int((deadline-time.monotonic()-1)/(cost*max(.05,slowest_read)*1.25))))
            results = []
            try:
                for key in ids[offset:offset + window]:
                    if requests>=max_requests and feeds==['ask'] and not comments:raise TimeoutError('Source request budget exhausted.')
                    if time.monotonic() >= deadline or requests>=max_requests:raise TimeoutError('Source window ended.')
                    native=await get(f'item/{key}.json')
                    processed.append(str(key))
                    kind='job' if isinstance(native,dict) and native.get('type')=='job' else 'story'
                    if isinstance(native,dict) and native.get('type')=='job' and 'jobs' in feeds:native={**native,'type':'story'}
                    item = normalize(native, content_kind=kind)
                    if item: results.append(item)
                    if comments and isinstance(native,dict) and item and not item.get('removed'):
                        for child in (native.get('kids') or [])[:2]:
                            if requests>=max_requests or time.monotonic()>=deadline:break
                            reply=await get(f'item/{child}.json')
                            if isinstance(reply,dict) and reply.get('type')=='comment' and reply.get('parent')==key:
                                normalized=normalize({**reply,'type':'story','title':item['title']}, content_kind='comment', parent_id=key, depth=1)
                                if normalized:
                                    normalized['discussion_id']=str(key)
                                    results.append(normalized)
                                # Bounded depth-2 nested reply traversal within shared request cap
                                for grandchild in (reply.get('kids') or [])[:1]:
                                    if requests>=max_requests or time.monotonic()>=deadline:break
                                    nested=await get(f'item/{grandchild}.json')
                                    if isinstance(nested,dict) and nested.get('type')=='comment' and nested.get('parent')==child:
                                        nested_norm=normalize({**nested,'type':'story','title':item['title']}, content_kind='comment', parent_id=child, depth=2)
                                        if nested_norm:
                                            nested_norm['discussion_id']=str(key)
                                            results.append(nested_norm)
                    await asyncio.sleep(.05)
            except (TimeoutError, httpx.TimeoutException):
                if not processed:raise TimeoutError('HN source did not complete an item before the deadline.') from None
                interrupted=True
        return {'items': results, 'requests': requests, 'scanned': len(processed)+sum(x.get('discussion_id') is not None for x in results), 'next_offset': offset + len(processed) if len(ids) > offset + len(processed) else None, **({'status':'PARTIAL','errors':['HN_WINDOW_INCOMPLETE']} if interrupted else {}),'cursor':{'seen_ids':list(dict.fromkeys([*processed,*(seen_ids or [])]))[:600],'updates_checked':bool(updated_items)},
                'planned_roots':window,'requested_root_limit':requested,'processed_roots':len(processed),
                'coverage': f'Official Firebase v0 {", ".join(feeds)}: checked {len(processed)} of {min(window,len(ids[offset:]))} planned story IDs (requested maximum {requested}). Bounded by measured latency and {max_requests} requests. No historical/full-text search.'}

def catalog(c=None):
    from app.intent_radar.connectors import catalog as describe
    return describe(c)
