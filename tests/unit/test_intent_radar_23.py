import asyncio
import json
from datetime import datetime,timezone,timedelta
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
from test_intent_radar import radar,owned,example,source_result,run
from app.intent_radar import connectors,models,service,schedules,providers,discovery
from app.platform.context import workspace_scope
from app.config.settings import get_settings

def test_multisource_partial_and_progressive_dedupe(radar,monkeypatch):
    c,path,org,_=radar
    monkeypatch.setattr(get_settings(),'intent_radar_stackexchange_enabled',True)
    async def fetch(c,q,key,permit):
        permit()
        if key=='stack_exchange':raise connectors.SourceUnavailable('RATE_LIMITED')
        return source_result()
    monkeypatch.setattr(connectors,'fetch',fetch)
    with workspace_scope(c,'controlled@example.test',org):
        q=models.Search(keywords=['website'],sources=['hacker_news','stack_exchange'])
        first=run(c,path,q);result=first['items'][0]['result']
        assert result['coverage_status']=='PARTIAL' and len(result['signals'])==1
        assert result['sources'][1]['status']=='RATE_LIMITED'
        run(c,path,q);assert service.listing(c,'signals')['total']==1
        for table in ('businesses','contact_people','email_messages','workflow_runs'):
            assert c.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]==0

def test_schedule_opt_in_duplicate_dispatch_pause_and_authority(radar,monkeypatch):
    c,path,org,_=radar
    monkeypatch.setattr(get_settings(),'intent_radar_schedules_enabled',True)
    with workspace_scope(c,'controlled@example.test',org):
        m=service.save_monitor(c,models.Monitor(name='Opt in',configuration=models.Search(keywords=['website']),status='Active'))
        assert m['next_run_at'] is None and c.execute('SELECT COUNT(*) FROM intent_discoveries').fetchone()[0]==0
        m=schedules.update(c,m['id'],models.Schedule(frequency='Daily',timezone='Europe/London',revision=m['revision']))
        assert m['next_run_at'] and m['schedule']['frequency']=='Daily'
        c.execute('UPDATE intent_monitors SET next_run_at=? WHERE id=?',( (datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat(),m['id']));c.commit()
        pending=schedules.enqueue_due(c);assert len(pending)==1 and schedules.enqueue_due(c)==[]
        m=service.get(c,'monitors',m['id'])
        service.save_monitor(c,models.Monitor(name=m['name'],configuration=m['configuration'],status='Paused',revision=m['revision']),m['id']);c.commit()
        c.execute('UPDATE intent_monitors SET next_run_at=? WHERE id=?',('2000-01-01',m['id']));c.commit()
        assert schedules.enqueue_due(c)==[]
    c.execute("UPDATE organization_memberships SET status='REVOKED' WHERE organization_id=?",(org,));c.commit()
    assert schedules.enqueue_due(c)==[]

def test_feeds_parse_atom_rss_and_reject_entities():
    config={'id':'feed','name':'Approved','family':'rss','attribution':'Publisher','policy_reference':'Owner reviewed terms','retention_days':7}
    rss=b'<rss><channel><item><guid>one</guid><title>Need a marketing agency</title><link>https://example.com/post</link><pubDate>Tue, 10 Nov 2026 10:00:00 GMT</pubDate><description>&lt;script&gt;evil()&lt;/script&gt; recommendation</description></item></channel></rss>'
    item=connectors.parse_feed(rss,config)[0]
    assert item['source_url']=='https://example.com/post' and '<script>' not in item['excerpt']
    atom=b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>one</id><title>Need design services</title><link href="https://example.com/design"/><updated>2026-11-10T10:00:00Z</updated><summary>Design request</summary></entry></feed>'
    assert len(connectors.parse_feed(atom,config))==1
    for bad in (b'<!DOCTYPE x [<!ENTITY a SYSTEM "file:///etc/passwd">]><rss/>',b'<rss>',b'x'*500001):
        with pytest.raises(ValueError):connectors.parse_feed(bad,config)

def test_provider_configuration_and_ssrf_denials(radar,monkeypatch):
    c,_,org,other=radar
    monkeypatch.setattr(get_settings(),'intent_radar_stackexchange_enabled',False)
    monkeypatch.setattr(get_settings(),'intent_radar_approved_feed_hosts','example.com;127.0.0.1')
    import socket
    monkeypatch.setattr(socket,'getaddrinfo',lambda *args,**kwargs:[(socket.AF_INET,socket.SOCK_STREAM,6,'',('93.184.215.14',443))])
    with workspace_scope(c,'controlled@example.test',org):
        for url in ('http://example.com/feed','https://user:pass@example.com/feed','https://example.com:8080/feed'):
            with pytest.raises(ValueError,match='Public HTTPS URLs are required'):connectors.approved_endpoint(url)
        for url,status,detail in (
            ('https://127.0.0.1/feed',422,'Source endpoint is not a public destination.'),
            ('https://unapproved.example/feed',403,'This source host has not been approved by the platform operator.'),
            ('https://example.com/feed?access_token=synthetic-credential',422,'Only public feed endpoints without authentication parameters are supported.'),
        ):
            with pytest.raises(HTTPException) as denied:connectors.approved_endpoint(url)
            assert (denied.value.status_code,denied.value.detail)==(status,detail)
        assert connectors.approved_endpoint('https://example.com/feed')=='https://example.com/feed'
        monkeypatch.setattr(socket,'getaddrinfo',lambda *args,**kwargs:[(socket.AF_INET,socket.SOCK_STREAM,6,'',('10.0.0.1',443))])
        with pytest.raises(HTTPException) as denied:connectors.approved_endpoint('https://example.com/feed')
        assert (denied.value.status_code,denied.value.detail)==(422,'Source endpoint is not a public destination.')
        assert all(x['state']!='Available' for x in connectors.catalog(c) if x['id']!='hacker_news')
        with pytest.raises(HTTPException) as unavailable:connectors.validate(c,models.Search(keywords=['website'],sources=['rss']))
        assert (unavailable.value.status_code,unavailable.value.detail)==(409,'RSS / Atom: Not configured')
    c.execute("UPDATE organization_memberships SET role='VIEWER' WHERE organization_id=?",(org,));c.commit()
    def unexpected_endpoint(_):raise AssertionError('Authorization must precede URL validation')
    monkeypatch.setattr(connectors,'approved_endpoint',unexpected_endpoint)
    with workspace_scope(c,'controlled@example.test',org):
        with pytest.raises(HTTPException) as forbidden:connectors.configure(c,models.SourceConfig(name='No grant',family='rss',endpoint='https://example.com/feed',policy_reference='Reviewed by owner',attribution='Publisher'))
        assert forbidden.value.status_code==403
        assert c.execute('SELECT COUNT(*) FROM intent_source_configs').fetchone()[0]==0

def test_durable_rate_limit_survives_rollback(radar):
    c,_,org,_=radar
    with workspace_scope(c,'controlled@example.test',org):
        connectors.cooldown('test:method',60)
        with pytest.raises(connectors.SourceUnavailable) as limit:connectors.cooldown('test:method',1)
        assert limit.value.code=='RATE_LIMITED' and limit.value.retry_at
        c.rollback()
        with pytest.raises(connectors.SourceUnavailable):connectors.cooldown('test:method',1)

def test_official_api_application_key_is_redacted_from_transport_logs():
    import logging
    record=logging.LogRecord('httpx',logging.INFO,'',0,'HTTP Request: GET %s',('https://api.stackexchange.com/2.3/search/advanced?site=stackoverflow&key=synthetic-credential&sort=creation',),None)
    assert connectors.SourceLogRedaction().filter(record)
    assert 'synthetic-credential' not in record.getMessage() and '[REDACTED]' in record.getMessage()

def test_stack_exchange_official_shape_cache_and_shared_backoff(radar,monkeypatch):
    import httpx
    c,path,org,_=radar;calls=[]
    monkeypatch.setattr(get_settings(),'intent_radar_stackexchange_enabled',True)
    class Client:
        def __init__(self,**kwargs):assert kwargs['max_bytes']==500000 and kwargs['redirect_limit']==0
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def get(self,url,**kwargs):
            calls.append(url);assert kwargs['allowed_host']=='api.stackexchange.com'
            return httpx.Response(200,json={'quota_remaining':10,'backoff':60,'has_more':True,'items':[{'question_id':123,'title':'Website development recommendation','link':'https://stackoverflow.com/questions/123/test','body':'<p>Need a website partner</p>','creation_date':int(datetime.now(timezone.utc).timestamp()),'owner':{'display_name':'Source attribution only'},'content_license':'CC BY-SA 4.0','tags':['website']}]},request=httpx.Request('GET',url))
    monkeypatch.setattr(connectors,'SafeAsyncClient',Client)
    with workspace_scope(c,'controlled@example.test',org):
        q=models.Search(keywords=['website'],sources=['stack_exchange'])
        first=asyncio.run(connectors.StackExchange().fetch(c,q,lambda:True))
        assert first['quota_remaining']==10 and len(first['items'])==1 and first['items'][0]['provenance']['attribution']['license']=='CC BY-SA 4.0'
        repeated=asyncio.run(connectors.StackExchange().fetch(c,q,lambda:True))
        assert len(calls)==1 and repeated['requests']==0
        with pytest.raises(connectors.SourceUnavailable):asyncio.run(connectors.StackExchange().fetch(c,q.model_copy(update={'keywords':['different']}),lambda:True))

def test_source_withdrawal_and_retention_preserve_notes_and_block_reingestion(radar,monkeypatch):
    c,path,org,_=radar;monkeypatch.setattr(providers.HackerNews,'fetch',AsyncMock(return_value=source_result()))
    with workspace_scope(c,'controlled@example.test',org):
        q=models.Search(keywords=['website']);run(c,path,q);signal=service.listing(c,'signals')['items'][0]
        service.review(c,signal['id'],models.SignalUpdate(revision=signal['revision'],status='Reviewed',notes='Private review survives public removal'));c.commit()
        service.remove_source(c,signal['id']);c.commit();run(c,path,q)
        result=service.get(c,'signals',signal['id'])
        assert not result['available'] and not result['excerpt'] and result['notes']=='Private review survives public removal'

@pytest.mark.parametrize('family',['rss','discourse'])
def test_approved_feeds_partial_failure_etag_and_attribution(radar,monkeypatch,family):
    import httpx,uuid
    c,_,org,_=radar;ids=[str(uuid.uuid4()),str(uuid.uuid4())];requests=[]
    monkeypatch.setattr(connectors,'approved_endpoint',lambda url:url)
    monkeypatch.setattr(connectors,'cooldown',lambda *args,**kwargs:None)
    rss=b'<rss><channel><language>en</language><item><guid>one</guid><title>Need a website agency</title><link>https://example.com/topic/one</link><pubDate>Tue, 10 Nov 2026 10:00:00 GMT</pubDate><description>Recommend a website partner?</description></item></channel></rss>'
    class Client:
        def __init__(self,**kwargs):assert kwargs['redirect_limit']==0
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def get(self,url,**kwargs):
            requests.append((url,kwargs.get('headers',{})))
            code=503 if 'bad' in url else 304 if kwargs.get('headers',{}).get('If-None-Match')=='fixture-etag' else 200
            return httpx.Response(code,content=rss if code==200 else b'',headers={'ETag':'fixture-etag'},request=httpx.Request('GET',url))
    monkeypatch.setattr(connectors,'SafeAsyncClient',Client)
    with workspace_scope(c,'controlled@example.test',org):
        for key,name in zip(ids,['good','bad']):
            cfg=models.SourceConfig(name=name,family=family,endpoint='https://example.com/'+name+'.rss',policy_reference='Synthetic test permission',attribution='Required publisher attribution',enabled=True)
            c.execute('INSERT INTO intent_source_configs VALUES(?,?,?,?)',(org,key,cfg.model_dump_json(),'2026-11-10'))
        c.commit();q=models.Search(keywords=['website'],sources=[family],feed_ids=ids)
        first=asyncio.run(connectors.Feed().fetch(c,q,lambda:True,family))
        assert first['status']=='PARTIAL' and first['requests']==2 and len(first['items'])==1
        assert first['items'][0]['source']==('Approved Discourse' if family=='discourse' else 'RSS / Atom')
        assert first['items'][0]['provenance']['attribution']=='Required publisher attribution'
        assert first['items'][0]['provenance']['declared_feed_language']=='en'
        c.execute('UPDATE intent_source_cache SET expires_at=? WHERE organization_id=?',('2000-01-01',org));c.commit()
        second=asyncio.run(connectors.Feed().fetch(c,q.model_copy(update={'feed_ids':[__import__('uuid').UUID(ids[0])]}),lambda:True,family))
        assert second['status']=='COMPLETE' and len(second['items'])==1
        assert requests[-1][1]['If-None-Match']=='fixture-etag'

def test_feed_approval_edit_cannot_reuse_old_cache_or_etag(radar,monkeypatch):
    import httpx,uuid
    c,_,org,_=radar;requests=[];key=str(uuid.uuid4())
    monkeypatch.setattr(connectors,'approved_endpoint',lambda url:url)
    monkeypatch.setattr(connectors,'cooldown',lambda *args,**kwargs:None)
    class Client:
        def __init__(self,**kwargs):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def get(self,url,**kwargs):
            requests.append((url,kwargs['headers']))
            name='Original' if 'original' in url else 'Replacement'
            xml=f'<rss><channel><item><title>{name} website request</title><link>https://example.com/{name}</link><pubDate>Tue, 10 Nov 2026 10:00:00 GMT</pubDate></item></channel></rss>'
            return httpx.Response(200,content=xml.encode(),headers={'ETag':'old-etag'},request=httpx.Request('GET',url))
    monkeypatch.setattr(connectors,'SafeAsyncClient',Client)
    with workspace_scope(c,'controlled@example.test',org):
        body=models.SourceConfig(name='Approved',family='rss',endpoint='https://example.com/original.rss',policy_reference='Fixture approval',attribution='Publisher',enabled=True)
        first=connectors.configure(c,body);c.commit();key=first['id']
        q=models.Search(keywords=['website'],sources=['rss'],feed_ids=[key])
        original=asyncio.run(connectors.Feed().fetch(c,q,lambda:True,'rss'))
        repeat=asyncio.run(connectors.Feed().fetch(c,q,lambda:True,'rss'))
        assert len(requests)==1 and repeat['items']==original['items']
        connectors.configure(c,body.model_copy(update={'endpoint':'https://example.com/replacement.rss','attribution':'New publisher'}),key);c.commit()
        changed=asyncio.run(connectors.Feed().fetch(c,q,lambda:True,'rss'))
        assert len(requests)==2 and requests[-1]==('https://example.com/replacement.rss',{})
        assert changed['items'][0]['title']=='Replacement website request'
        assert changed['items'][0]['provenance']['attribution']=='New publisher'
