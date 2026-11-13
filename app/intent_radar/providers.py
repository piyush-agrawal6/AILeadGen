"""Official public HN API only. Recent Ask HN coverage; no historical search claim."""
import asyncio, re, time
from datetime import datetime, timezone
from html import unescape
from typing import Protocol
from bs4 import BeautifulSoup
from app.utils.http import SafeAsyncClient

HOST = 'hacker-news.firebaseio.com'
BASE = 'https://' + HOST + '/v0/'

class Source(Protocol):
    async def fetch(self, offset: int = 0) -> dict: ...

def text(value, limit):
    return re.sub(r'\s+', ' ', BeautifulSoup(str(value or '')[:50000], 'html.parser').get_text(' ', strip=True)).strip()[:limit]

def normalize(item):
    if not isinstance(item, dict) or type(item.get('id')) is not int or not 1 <= item['id'] <= 9223372036854775807: return None
    key = str(item['id'])
    if item.get('deleted') or item.get('dead'): return {'source_record_id': key, 'removed': True}
    if item.get('type') != 'story' or type(item.get('time')) is not int or not item.get('title'): return None
    try: observed = datetime.fromtimestamp(item['time'], timezone.utc).isoformat()
    except (ValueError, OverflowError, OSError): return None
    # Do not collect author names, profiles, external target URLs or comment trees.
    title=text(item['title'],300);excerpt=text(item.get('text'),3000)
    import hashlib
    return {'source': 'Hacker News', 'source_record_id': key, 'source_url': 'https://news.ycombinator.com/item?id=' + key,
            'title': title, 'excerpt': excerpt,'content_fingerprint':hashlib.sha256((title+'\n'+excerpt).encode()).hexdigest(),'provenance':{'fetch_method':'official_hn'},
            'observed_at': observed, 'retrieved_at': datetime.now(timezone.utc).isoformat(), 'removed': False}

class HackerNews:
    async def fetch(self, offset=0, permit=None, feeds=None, comments=False,limit=20,seen_ids=None):
        if not 0 <= offset <= 180: raise ValueError('Recent source offset is outside the supported window.')
        deadline = time.monotonic() + 27
        requests = 0
        async with SafeAsyncClient(timeout=4, max_bytes=200000, redirect_limit=0, headers={'User-Agent': 'PlaneByte-IntentRadar/1.0 (public API evidence; no posting)'}) as client:
            async def get(path):
                nonlocal requests
                for attempt in range(2):
                    if permit and not permit():raise RuntimeError('The job is no longer authorized or active.')
                    if requests >= 22 or time.monotonic() >= deadline: raise TimeoutError('Source request budget exhausted.')
                    requests += 1
                    response = await client.get(BASE + path, allowed_host=HOST)
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
            if not 1<=len(feeds)<=3 or any(f not in names for f in feeds):raise ValueError('Unsupported HN feed.')
            batches=[]
            for feed in feeds:
                batch=await get(names[feed]+'.json')
                if not isinstance(batch,list):raise ValueError('Unsupported source response.')
                batches.append([x for x in batch[:200] if type(x) is int and x>0])
            # Round-robin coverage prevents a large feed from hiding selected feeds.
            from itertools import zip_longest
            ids=list(dict.fromkeys(x for group in zip_longest(*batches) for x in group if x is not None))
            if seen_ids and not comments:ids=[key for key in ids if str(key) not in set(seen_ids)]
            window=max(1,min(20,limit));processed=[]
            results = []
            for key in ids[offset:offset + window]:
                if requests>=22 and feeds==['ask'] and not comments:raise TimeoutError('Source request budget exhausted.')
                if time.monotonic() >= deadline or requests>=22: break
                native=await get(f'item/{key}.json')
                processed.append(str(key))
                if isinstance(native,dict) and native.get('type')=='job' and 'jobs' in feeds:native={**native,'type':'story'}
                item = normalize(native)
                if item: results.append(item)
                if comments and isinstance(native,dict) and item and not item.get('removed'):
                    for child in (native.get('kids') or [])[:2]:
                        if requests>=22:break
                        reply=await get(f'item/{child}.json')
                        if isinstance(reply,dict) and reply.get('type')=='comment' and reply.get('parent')==key:
                            normalized=normalize({**reply,'type':'story','title':item['title']})
                            if normalized:normalized['discussion_id']=str(key);results.append(normalized)
                await asyncio.sleep(.1)
        return {'items': results, 'requests': requests, 'scanned': len(results), 'next_offset': offset + window if len(ids) > offset + window else None,'cursor':{'seen_ids':list(dict.fromkeys([*processed,*(seen_ids or [])]))[:600]},
                'coverage': 'Bounded recent '+', '.join(feeds)+' feeds; maximum 22 requests, depth-one comments only when requested. No historical/full-text search.'}

def catalog(c=None):
    from app.intent_radar.connectors import catalog as describe
    return describe(c)
