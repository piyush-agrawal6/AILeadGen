"""Real scoped HTTP/worker setup; providers and websites are isolated fixtures."""
import asyncio,json,uuid
from unittest.mock import AsyncMock
import pytest
from fastapi.testclient import TestClient
from app.api.server import app
from app.api.organization import create_organization
from app.config.settings import get_settings
from app.database.connection import db_session
from app.platform.context import workspace_scope
from app.platform import company_autofill as autofill,company_discovery as jobs
from app.icp import builder,ai as icp_ai
from app.acquisition import ai as gateway
from app.acquisition.config import AcquisitionSettings
from test_company_autofill import SOURCE,result as company_result
from test_icp_business_builder import candidate,five_candidates

BASE='/api/organization/onboarding'
OWNER={'x-le-user':'setup@example.test'}
@pytest.fixture
def setup_client(tmp_path,monkeypatch):
    s=get_settings();monkeypatch.setattr(s,'database_path',str(tmp_path/'assisted.db'))
    monkeypatch.setattr(s,'allowed_user_emails','owner@example.test,setup@example.test,other@example.test,viewer@example.test,admin@example.test')
    for flag in ('heysow_workspace_management_enabled','heysow_company_discovery_enabled','heysow_company_ai_enabled','heysow_icp_ai_enabled'):monkeypatch.setattr(s,flag,True)
    cfg=AcquisitionSettings(_env_file=None,VERTEX_AI_ENABLED=True,AI_PRIMARY_PROVIDER='vertex')
    monkeypatch.setattr(autofill,'provider_settings',lambda:cfg);monkeypatch.setattr(icp_ai,'provider_settings',lambda:cfg)
    provider=AsyncMock()
    async def structured(instruction,payload,schema,**kwargs):
        if schema is autofill.Extraction:return company_result()
        if issubclass(schema,builder.Suggestions):return schema(candidates=five_candidates())
        from app.platform.onboarding_ai import Advice
        return Advice(answer='Review whether your offering addresses the suggested audience needs.',source_fields=['description'])
    provider.structured.side_effect=structured;monkeypatch.setattr(gateway,'provider',lambda c:provider)
    crawl=AsyncMock(return_value=[SOURCE]);monkeypatch.setattr(autofill,'collect_sources',crawl)
    from app.api.routes import onboarding as routes,company_discovery as job_routes
    async def launch(key):await asyncio.to_thread(jobs.execute,key)
    monkeypatch.setattr(routes,'launch',launch);monkeypatch.setattr(job_routes,'launch',launch)
    with TestClient(app) as http:
        with db_session() as c:
            org=create_organization(c,'setup@example.test','Evidence Engineering')['organization_id']
            other=create_organization(c,'other@example.test','Other business')['organization_id']
            with workspace_scope(c,'setup@example.test',org):
                from app.platform.memberships import change_role
                change_role(c,'setup@example.test','viewer@example.test','VIEWER');change_role(c,'setup@example.test','admin@example.test','ADMIN')
        yield http,provider,crawl,s,org,other

def start(http,**patch):
    body={'revision':0,'website':'https://example.com','objective':'UNDERSTAND_CUSTOMER_NEEDS','request_id':str(uuid.uuid4()),**patch}
    response=http.post(BASE+'/analyze',headers=OWNER,json=body);assert response.status_code==202,response.text
    return body,response.json()
def approve(http,progress=None):
    state=http.get(BASE+'/assistant-context',headers=OWNER).json();profile=state['company']
    fields={k:v for k,v in profile.items() if k not in ('organization_id','onboarding_status','can_edit')}
    fields.update(description='Custom software for software teams.',countries_served=['United Kingdom'],products_services=[{'name':'Custom applications','description':'Engineering'}])
    response=http.put(BASE+'/company',headers=OWNER,json={'revision':state['progress']['revision'],'objective':'RESEARCH_MARKETS','profile':fields})
    assert response.status_code==200,response.text
    return response.json()

def test_ai_setup_review_resume_approval_shared_defaults_and_completion_without_actions(setup_client):
    http,provider,crawl,s,org,_=setup_client
    initial=http.get(BASE+'/assistant-context',headers=OWNER).json();assert initial['progress']['revision']==0
    body,created=start(http)
    resumed=http.get(BASE+'/assistant-context',headers=OWNER).json();review=resumed['reviews']['company']
    assert review['status']=='READY' and resumed['company']==initial['company']
    replay=http.post(BASE+'/analyze',headers=OWNER,json=body);assert replay.status_code==202,replay.text
    assert replay.json()['progress']['revision']==created['progress']['revision'] and provider.structured.await_count==1
    approved=approve(http);assert approved['progress']['services']==approved['company']['products_services']
    request={'revision':approved['progress']['revision'],'request_id':str(uuid.uuid4())}
    started=http.post(BASE+'/recommendations',headers=OWNER,json=request);assert started.status_code==202,started.text
    repeat=http.post(BASE+'/recommendations',headers=OWNER,json=request);assert repeat.status_code==202,repeat.text
    state=http.get(BASE+'/assistant-context',headers=OWNER).json();proposal=state['reviews']['icp']['preview']
    assert state['reviews']['icp']['status']=='READY',state
    assert len(proposal['candidates'])==5
    assert provider.structured.call_args.args[2].model_json_schema()['properties']['candidates']['minItems']==5
    private=state['reviews']['icp']['id']
    assert http.get(BASE+'/reviews/'+private,headers={'x-le-user':'admin@example.test'}).status_code==404
    assert http.get('/api/organization/website-reviews/'+private,headers={'x-le-user':'admin@example.test'}).status_code==404
    admin=http.get(BASE+'/assistant-context',headers={'x-le-user':'admin@example.test'});assert admin.status_code==200,admin.text
    assert admin.json()['progress']['preferences']['icp_review_id'] is None
    assert http.get('/api/organization/icps',headers=OWNER).json()['total']==0
    choices=[{'candidate_index':i,**{k:v for k,v in item['draft'].items() if k in ('name','description','criteria')}} for i,item in enumerate(proposal['candidates'])]
    accepted=http.post(BASE+'/accept-profiles',headers=OWNER,json={'revision':state['progress']['revision'],'proposal_id':proposal['proposal_id'],'candidates':choices,'primary_index':1,'request_id':str(uuid.uuid4()),'research_keywords':['custom applications'],'excluded_keywords':['jobs']})
    assert accepted.status_code==200,accepted.text
    progress=accepted.json()['progress'];assert progress['default_icp_id']==accepted.json()['profiles'][1]['id']
    finish={'revision':progress['revision'],'primary_icp_id':progress['default_icp_id'],'research_keywords':['application delivery'],'excluded_keywords':['recruitment']}
    completed=http.post(BASE+'/finish',headers=OWNER,json=finish);assert completed.status_code==200,completed.text
    assert http.post(BASE+'/finish',headers=OWNER,json=finish).json()==completed.json()
    assert completed.json()=={'status':'COMPLETED','discovery_started':False,'outreach_started':False}
    with db_session() as c:
        prefs=json.loads(c.execute('SELECT configuration_json FROM intent_preferences WHERE organization_id=?',(org,)).fetchone()[0]);assert prefs['discovery_keywords']==['application delivery'] and prefs['discovery_excluded']==['recruitment'] and prefs['default_icp_id']==progress['default_icp_id']
        for table in ('intent_monitors','intent_discoveries','pipeline_runs','acquisition_jobs','email_messages'):assert c.execute('SELECT COUNT(*) FROM '+table+' WHERE organization_id=?',(org,)).fetchone()[0]==0
        assert c.execute("SELECT COUNT(*) FROM organization_products WHERE organization_id=? AND product='INTENT_RADAR' AND enabled=1",(org,)).fetchone()[0]==0
    assert crawl.await_count==1 and provider.structured.await_count==2

def test_manual_setup_remains_available_without_ai_and_preserves_completed_company(setup_client):
    http,provider,_,s,_,_=setup_client;s.heysow_company_ai_enabled=False;s.heysow_icp_ai_enabled=False
    approved=approve(http);profile=http.post('/api/organization/icps',headers=OWNER,json={'name':'Manual software audience','status':'ACTIVE','criteria':{'company':{'industries':['Software']}},'request_id':str(uuid.uuid4())});assert profile.status_code==201,profile.text
    finish={'revision':approved['progress']['revision'],'primary_icp_id':profile.json()['id']}
    assert http.post(BASE+'/finish',headers=OWNER,json=finish).status_code==200
    before=http.get('/api/organization/profile',headers=OWNER).json()
    assert http.put(BASE+'/company',headers=OWNER,json={'revision':2,'objective':'RESEARCH_MARKETS','profile':{'name':'Overwrite'}}).status_code==409
    assert http.get('/api/organization/profile',headers=OWNER).json()==before;provider.structured.assert_not_called()

def test_scoped_references_viewer_absent_context_and_private_guidance(setup_client):
    http,provider,_,_,org,_=setup_client
    _,started=start(http);key=started['review']['id']
    assert http.get(BASE+'/reviews/'+key,headers={'x-le-user':'other@example.test'}).status_code==404
    assert http.post(BASE+'/analyze',headers={'x-le-user':'viewer@example.test'},json={'revision':1,'website':'https://example.com','objective':'RESEARCH_MARKETS','request_id':str(uuid.uuid4())}).status_code==403
    state=http.get(BASE+'/assistant-context',headers={'x-le-user':'viewer@example.test'}).json();assert not state['progress']['can_edit'] and not state['capabilities']['company_analysis']
    from app.platform import onboarding_ai
    from fastapi import HTTPException
    with db_session() as c:
        with pytest.raises(HTTPException):onboarding_ai.state(c)
    question={'prompt':'What should I review?','request_id':str(uuid.uuid4())}
    advice=http.post(BASE+'/assistant',headers=OWNER,json=question);assert advice.status_code==202,advice.text
    key=advice.json()['job']['id']
    assert http.get(BASE+'/reviews/'+key,headers={'x-le-user':'admin@example.test'}).status_code==404
    assert http.get('/api/organization/website-reviews/'+key,headers={'x-le-user':'admin@example.test'}).status_code==404
    other=http.post(BASE+'/assistant',headers={'x-le-user':'admin@example.test'},json={**question,'request_id':str(uuid.uuid4())});assert other.status_code==202,other.text
    assert other.json()['job']['id']!=key
    before=provider.structured.await_count
    factual=http.post(BASE+'/assistant',headers=OWNER,json={'prompt':'What company details are saved?','request_id':str(uuid.uuid4())})
    assert factual.status_code==202 and factual.json()['job'] is None and provider.structured.await_count==before

def test_failed_review_and_quota_never_mutate_company_and_retry_is_bounded(setup_client):
    http,provider,crawl,s,_,_=setup_client
    provider.structured.side_effect=RuntimeError('private provider error')
    s.heysow_company_ai_daily_limit=2
    before=http.get('/api/organization/profile',headers=OWNER).json();_,job=start(http)
    key=job['review']['id'];review=http.get(BASE+'/reviews/'+key,headers=OWNER).json();assert review['status']=='FAILED' and 'private provider' not in json.dumps(review)
    for _ in range(2):assert http.post('/api/organization/website-reviews/'+key+'/control',headers=OWNER,json={'action':'RETRY'}).status_code==200
    assert http.post('/api/organization/website-reviews/'+key+'/control',headers=OWNER,json={'action':'RETRY'}).status_code==409
    assert http.get('/api/organization/profile',headers=OWNER).json()==before
    assert provider.structured.await_count==2 # daily allowance blocks the third worker attempt

def test_dispatch_claim_is_bounded_recoverable_and_fenced_from_late_acknowledgements(setup_client,monkeypatch):
    http,provider,crawl,s,org,_=setup_client
    from app.api.routes import onboarding as routes
    from app.platform import company_discovery_dispatch as dispatch
    async def no_dispatch(key):pass
    monkeypatch.setattr(routes,'launch',no_dispatch)
    _,created=start(http);key=created['review']['id']
    with db_session() as c:
        with workspace_scope(c,'setup@example.test',org):
            token=dispatch._claim(key);assert token
            assert not dispatch._claim(key)
            c.execute("UPDATE organization_profile_jobs SET lease_expires_at='2000-01-01T00:00:00+00:00' WHERE id=?",(key,));c.commit()
            assert jobs.detail(c,key)['can_retry']
            jobs.control(c,key,'RETRY');c.commit()
            replacement=dispatch._claim(key);assert replacement and replacement!=token
            dispatch._record(key,token,'late-operation')
            assert jobs.owned(c,key)['execution_name']=='DISPATCHING:'+replacement
            c.execute("UPDATE organization_profile_jobs SET status='RUNNING',lease_owner='worker-lease' WHERE id=?",(key,));c.commit()
            dispatch._record(key,replacement,'current-operation')
            assert jobs.owned(c,key)['execution_name']=='current-operation'
    provider.structured.assert_not_called();crawl.assert_not_called()

def test_global_setup_dispatch_capacity_has_a_bounded_queue_without_provider_work(setup_client,monkeypatch):
    http,provider,crawl,s,org,_=setup_client
    from app.api.routes import onboarding as routes
    from app.platform import company_discovery_dispatch as dispatch
    async def no_dispatch(key):pass
    monkeypatch.setattr(routes,'launch',no_dispatch)
    keys=[]
    for i in range(3):
        _,job=start(http,revision=i,website='https://example.com/'+str(i));keys.append(job['review']['id'])
    with db_session() as c:
        with workspace_scope(c,'setup@example.test',org):
            first=dispatch._claim(keys[0]);second=dispatch._claim(keys[1]);assert first and second
            assert not dispatch._claim(keys[2])
            assert jobs.detail(c,keys[2])['status']=='QUEUED' and jobs.detail(c,keys[2])['can_retry']
            dispatch._record(keys[0],first,failed=True)
            assert dispatch._claim(keys[2])
    provider.structured.assert_not_called();crawl.assert_not_called()


def test_qualified_saved_profile_references_are_normalized_but_unknown_fields_fail(setup_client):
    http,provider,_,_,_,_=setup_client
    from app.platform.onboarding_ai import Advice
    from pydantic import ValidationError
    provider.structured.side_effect=None
    provider.structured.return_value=Advice(answer='Review these suggested audience needs against your offering.',source_fields=['saved_company.products_services','saved_company.target_customers'])
    response=http.post(BASE+'/assistant',headers=OWNER,json={'prompt':'What should I review in my customer profiles?','request_id':str(uuid.uuid4())});assert response.status_code==202,response.text
    reviewed=http.get(BASE+'/reviews/'+response.json()['job']['id'],headers=OWNER).json()
    assert reviewed['status']=='READY',reviewed
    assert reviewed['preview']['source_fields']==['products_services','target_customers']
    with pytest.raises(ValidationError):Advice(answer='Unsupported reference should never be accepted.',source_fields=['saved_company.credentials'])
    with pytest.raises(ValidationError):Advice(answer='Nested arbitrary paths should never be accepted.',source_fields=['saved_company.products_services.secret'])


def test_onboarding_requires_five_and_does_not_reuse_shorter_general_proposals(setup_client):
    http,provider,*_=setup_client
    approved=approve(http)
    short=builder.Suggestions(candidates=five_candidates()[:3])
    provider.structured.side_effect=None;provider.structured.return_value=short
    # The optional general builder retains its up-to-five contract. Its cache
    # must never satisfy the exact-five onboarding request.
    general=http.post('/api/organization/icps/suggest',headers=OWNER,json={'mode':'BUSINESS_PROFILE','candidate_count':5})
    assert general.status_code==200,general.text
    started=http.post(BASE+'/recommendations',headers=OWNER,json={'revision':approved['progress']['revision'],'request_id':str(uuid.uuid4())})
    assert started.status_code==202,started.text
    detail=http.get(BASE+'/reviews/'+started.json()['review']['id'],headers=OWNER).json()
    assert detail['status']=='FAILED' and detail['error_code']=='ICP_TOO_FEW_SEGMENTS',detail
    assert detail['preview'] is None
    assert provider.structured.await_count==2
    assert http.get('/api/organization/icps',headers=OWNER).json()['total']==0

def test_exact_suggestion_schema_rejects_short_or_padded_output():
    from pydantic import ValidationError
    schema=builder.exact_suggestions(5)
    with pytest.raises(ValidationError):schema(candidates=five_candidates()[:3])
    complete=schema(candidates=five_candidates())
    assert len(builder._check_suggestions(complete,5,[],exact=True).candidates)==5
    complete.candidates[-1]=complete.candidates[0].model_copy(deep=True)
    with pytest.raises(gateway.AiOutputError,match='ICP_DUPLICATE_SEGMENTS'):
        builder._check_suggestions(complete,5,[],exact=True)
