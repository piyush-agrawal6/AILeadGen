"""Grounding, durable retry history and private conversational context regressions."""
import json
import uuid
import pytest
from app.platform import company_autofill as autofill
from app.acquisition import ai
from app.database.connection import db_session
from app.platform.context import workspace_scope
from test_company_autofill import client,SOURCE,proposal,result,start
from test_onboarding_ai import setup_client,approve,OWNER,BASE


def test_paraphrase_requires_independent_grounding_and_cannot_invent_numeric_claims(client):
    http,provider,*_=client
    extraction=result()
    extraction.fields[1].value='Cloud engineering and web applications are the offerings of Evidence Engineering.'
    provider.structured.side_effect=[extraction,autofill.GroundingReview(decisions=[{'field':'description','supported':True}])]
    created=start(http);detail=http.get('/api/organization/website-reviews/'+created.json()['id']).json()
    assert detail['status']=='READY',detail
    preview=detail['preview'];assert preview['suggestions']['description']==extraction.fields[1].value
    assert preview['sources']['description']['basis']=='AI_INTERPRETATION'
    assert preview['sources']['name']['basis']=='SOURCE_ASSERTION'
    assert preview['sources']['description']['verified_company_fact'] is False
    assert preview['evidence']['description'][0]['quote'] in SOURCE['text']
    assert preview['interpretations']['description']==extraction.fields[1].value
    assert 'country' in preview['unknowns']
    assert provider.structured.await_count==2
    assert provider.structured.call_args.args[1]['claims'][0]['quotes']
    invented=autofill.Extraction(fields=[proposal('description','Evidence Engineering serves 500 clients globally.',SOURCE['text'][:75])])
    rejected=autofill.preview_from_result(invented,[SOURCE],'https://example.com',supported_interpretations=['description'])
    assert 'description' not in rejected['suggestions']


def test_unapproved_paraphrase_and_name_only_preview_fail_instead_of_fake_success(client):
    http,provider,*_=client
    extraction=autofill.Extraction(fields=[proposal('name','Evidence Engineering',SOURCE['text'][:75]),proposal('description','Evidence Engineering guarantees world-leading products.',SOURCE['text'][:75])])
    provider.structured.side_effect=[extraction,autofill.GroundingReview(decisions=[{'field':'description','supported':False}])]
    created=start(http);detail=http.get('/api/organization/website-reviews/'+created.json()['id']).json()
    assert detail['status']=='FAILED' and detail['error_code']=='INSUFFICIENT_COMPANY_EVIDENCE'
    assert detail['preview'] is None


def test_retry_keeps_first_attempt_cause_and_never_exposes_prompts(client):
    http,provider,crawl,s,org,other=client
    s.heysow_setup_diagnostics_enabled=True
    provider.structured.side_effect=ai.AiOutputError('ICP_UNKNOWN_SERVICE')
    created=start(http);key=created.json()['id']
    failed=http.get('/api/organization/website-reviews/'+key).json()
    assert failed['status']=='FAILED' and failed['error_code']=='ICP_UNKNOWN_SERVICE'
    assert failed['attempt_history'][-1]['error_code']=='ICP_UNKNOWN_SERVICE'
    provider.structured.side_effect=None;provider.structured.return_value=result()
    retried=http.post('/api/organization/website-reviews/'+key+'/control',json={'action':'RETRY'});assert retried.status_code==200
    ready=http.get('/api/organization/website-reviews/'+key).json();assert ready['status']=='READY',ready
    assert any(v['attempt']==1 and v['outcome']=='FAILED' and v['error_code']=='ICP_UNKNOWN_SERVICE' for v in ready['attempt_history'])
    assert any(v['attempt']==2 and v['outcome']=='READY' for v in ready['attempt_history'])
    assert http.get('/api/organization/website-reviews/'+key,headers={'x-le-user':'foreign@example.test'}).status_code==404
    assert all(set(v)=={'attempt','stage','outcome','error_code','provider','model','duration_ms','created_at'} for v in ready['attempt_history'])


def test_assistant_uses_private_followup_draft_and_saved_icps_without_saving_draft(setup_client):
    http,provider,crawl,s,org,other=setup_client
    saved=approve(http)['company']
    draft={k:v for k,v in saved.items() if k in autofill.CompanyFields.model_fields};draft['description']='Unsaved workflow automation offering.'
    first=http.post(BASE+'/assistant',headers=OWNER,json={'prompt':'Who could benefit from my company and why?','draft':draft,'request_id':str(uuid.uuid4())})
    assert first.status_code==202,first.text;key=first.json()['job']['id']
    assert http.get(BASE+'/reviews/'+key,headers=OWNER).json()['status']=='READY'
    payload=provider.structured.call_args.args[1]
    assert payload['saved_company']['description']=='Custom software for software teams.'
    assert payload['in_progress_draft']['description']==draft['description'] and payload['conversation']==[]
    second=http.post(BASE+'/assistant',headers=OWNER,json={'prompt':'Which of those needs is strongest and what is unknown?','parent_review_id':key,'draft':draft,'request_id':str(uuid.uuid4())})
    assert second.status_code==202,second.text
    payload=provider.structured.call_args.args[1];assert payload['conversation'][0]['question']=='Who could benefit from my company and why?'
    assert payload['conversation'][0]['answer']
    assert http.get('/api/organization/profile',headers=OWNER).json()['description']==saved['description']
    denied=http.post(BASE+'/assistant',headers={'x-le-user':'admin@example.test'},json={'prompt':'Read that conversation','parent_review_id':key,'request_id':str(uuid.uuid4())})
    assert denied.status_code==404


def test_different_names_do_not_make_duplicate_icp_criteria_distinct():
    from app.icp import builder
    from test_icp_business_builder import candidate
    data=builder.Suggestions(candidates=[candidate('Name '+str(i)) for i in range(3)])
    with pytest.raises(ai.AiOutputError,match='ICP_DUPLICATE_SEGMENTS'):builder._check_suggestions(data,5,[])
    for i,c in enumerate(data.candidates):c.draft.criteria.intent.pain_points=['Customer acquisition','Internal workflows','Product support'][i:i+1]
    assert len(builder._check_suggestions(data,5,[]).candidates)==3
