import json
from types import SimpleNamespace
import httpx,pytest
from fastapi import FastAPI,Request
from fastapi.testclient import TestClient
from app.api.read_cache import ReadCache

@pytest.fixture
def cached_app(monkeypatch):
    import app.api.read_cache as module
    monkeypatch.setattr(module,'get_settings',lambda:SimpleNamespace(upstash_redis_rest_url='https://example.upstash.io',upstash_redis_rest_token='private-token',database_url='postgres://test',database_path='unused'))
    cache=ReadCache();store={};calls=[]
    def redis(request):
        assert request.headers['authorization']=='Bearer private-token'
        args=json.loads(request.content);calls.append(args)
        if args[0]=='GET':result=store.get(args[1])
        elif args[0]=='INCR':store[args[1]]=int(store.get(args[1],0))+1;result=store[args[1]]
        else:
            assert args[0]=='SET' and args[-2]=='EX' and int(args[-1])>0
            store[args[1]]=args[2];result='OK'
        return httpx.Response(200,json={'result':result})
    cache.client=httpx.AsyncClient(transport=httpx.MockTransport(redis))
    app=FastAPI();hits=[]
    @app.middleware('http')
    async def authenticate(request:Request,call_next):
        request.state.user_email=request.headers.get('actor','owner@example.com')
        return await cache.handle(request,call_next)
    @app.get('/api/operations/campaigns')
    def get(request:Request):hits.append(1);return {'actor':request.state.user_email,'count':len(hits)}
    @app.get('/api/acquisition/jobs/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa')
    def progress(request:Request):hits.append(1);return {'actor':request.state.user_email,'count':len(hits)}
    @app.post('/api/operations/campaigns')
    def post():return {'saved':True}
    @app.get('/api/workflow/safety')
    def safety():hits.append(1);return {'count':len(hits)}
    with TestClient(app) as client:yield client,cache,store,hits,calls

def test_identical_read_hits_and_actor_query_isolation(cached_app):
    client,cache,store,hits,calls=cached_app
    a=client.get('/api/operations/campaigns?a=1&b=2')
    b=client.get('/api/operations/campaigns?b=2&a=1')
    assert a.json()==b.json() and len(hits)==1
    assert b.headers['x-le-cache']=='HIT' and b.headers['cache-control']=='private, no-store'
    client.get('/api/operations/campaigns?a=1&b=2',headers={'actor':'viewer@example.com'})
    client.get('/api/operations/campaigns?a=2&b=2')
    assert len(hits)==3
    assert all('owner@example.com' not in str(command[1]) for command in calls)

def test_mutation_invalidates_old_generation(cached_app):
    client,cache,store,hits,calls=cached_app
    client.get('/api/operations/campaigns');client.post('/api/operations/campaigns')
    assert client.get('/api/operations/campaigns').json()['count']==2
    assert any(x[0]=='INCR' for x in calls)

def test_safety_read_and_explicit_refresh_bypass(cached_app):
    client,cache,store,hits,calls=cached_app
    client.get('/api/workflow/safety');client.get('/api/workflow/safety')
    assert not calls
    client.get('/api/operations/campaigns');client.get('/api/operations/campaigns',headers={'cache-control':'no-cache'})
    assert len(hits)==4

def test_redis_outage_falls_back_without_secret_error(cached_app):
    client,cache,store,hits,calls=cached_app
    async def fail(request):return httpx.Response(401,json={'error':'private-token'})
    cache.client=httpx.AsyncClient(transport=httpx.MockTransport(fail))
    a=client.get('/api/operations/campaigns');b=client.get('/api/operations/campaigns')
    assert a.status_code==b.status_code==200 and len(hits)==2
    assert 'private-token' not in json.dumps(cache.health())
    assert cache.health()['state']=='DEGRADED'


def test_acquisition_progress_is_cached_per_actor_and_invalidated(cached_app):
    client,cache,store,hits,calls=cached_app
    path='/api/acquisition/jobs/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
    client.get(path);second=client.get(path)
    assert second.headers['x-le-cache']=='HIT' and len(hits)==1
    client.get(path,headers={'actor':'viewer@example.com'});assert len(hits)==2
    client.post('/api/operations/campaigns');client.get(path);assert len(hits)==3
