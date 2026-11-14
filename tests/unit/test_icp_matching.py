import asyncio,json,uuid
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
from test_people import owned,seed
from app.platform.context import workspace_scope
from app.icp.models import Create,Criteria
from app.icp.service import create
from app.icp.matching import evaluate
from app.intelligence import qualification,jobs,summary
from app.database.models import Business
from app.prospecting.company_facts import extract


def test_weighted_fit_unknown_evidence_and_professional_relevance_are_distinct(owned):
 c,path,org,other=owned
 with workspace_scope(c,'controlled@example.test',org):
  b=seed(c,org)
  p=create(c,Create(name='Evidence-based ICP',status='ACTIVE',criteria={'company':{'countries':['United Kingdom'],'employee_min':10},'contact':{'job_titles':['CTO']},'weights':{'company.countries':5,'company.employee_min':3,'contact.job_titles':2}},request_id=uuid.uuid4()))
  fit=qualification.match(c,b.id,p['id']);assert fit['score']==100 and fit['coverage']==50 and fit['status']=='PARTIAL'
  assert not fit['send_eligibility_evaluated'] and fit['contact_availability_separate']
  facts={'attributes':{'employee_count':{'value':7,'source_url':'https://controlled.example/about'}},'pages':[]}
  fit=evaluate(p,b,facts,{'role':'CTO','source_url':'https://controlled.example/team'})
  assert fit['score']==70 and fit['coverage']==100 and fit['status']=='MISMATCH'
  assert next(item for item in fit['criteria'] if item['field']=='company.employee_min')['source']=='https://controlled.example/about'
  assert qualification.recommendations(c,p['id'])['items'][0]['business_id']==b.id
  assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0
 with workspace_scope(c,'foreign@example.test',other):
  for action in (lambda:qualification.match(c,b.id,p['id']),lambda:qualification.recommendations(c,p['id'])):
   with pytest.raises(HTTPException) as denied:action()
   assert denied.value.status_code==404
 with pytest.raises(HTTPException):qualification.match(c,b.id,p['id'])
 with pytest.raises(ValueError):Criteria.model_validate({'company':{'countries':['India']},'weights':{'made_up.score':10}})
 with pytest.raises(ValueError):Criteria.model_validate({'company':{'countries':['India']},'weights':{'company.countries':0}})


def test_stated_company_attributes_are_not_estimates_or_unrelated_businesses():
 markup='<script type="application/ld+json">'+json.dumps({'@type':'Organization','name':'Controlled company','numberOfEmployees':{'value':42},'address':{'addressLocality':'Bristol','addressCountry':'United Kingdom'},'hasOfferCatalog':{'itemListElement':[{'itemOffered':{'name':'Cloud engineering'}}]}})+'</script>'
 facts=extract({'https://controlled.example/about':markup},'Controlled company')
 assert facts['employee_count']['value']==42 and not facts['employee_count']['independently_verified']
 assert facts['products_services']['value']==['Cloud engineering']
 assert not extract({'https://controlled.example/about':markup},'Unrelated company')
 assert 'revenue' not in facts


def test_cited_ai_summary_uses_shared_gateway_validates_quotes_and_reuses_evidence(owned,monkeypatch):
 from app.config.settings import get_settings
 from app.acquisition import ai
 c,path,org,other=owned;monkeypatch.setattr(get_settings(),'heysow_company_ai_enabled',True)
 provider=AsyncMock();provider.structured.return_value=summary.Proposal(excerpts=[{'source_index':0,'quote':'We provide public business services.'}]);monkeypatch.setattr(ai,'provider',lambda _:provider)
 monkeypatch.setattr(summary.ai_usage,'reserve_company',lambda **kwargs:None)
 with workspace_scope(c,'controlled@example.test',org):
  b=seed(c,org);facts={'pages':[{'url':'https://controlled.example/about','excerpt':'We provide public business services. Based in Bristol.'}]}
  c.execute('UPDATE businesses SET source_tags_json=? WHERE id=?',(json.dumps({'company_intelligence':facts}),b.id));c.commit()
  for _ in range(2):
   job=jobs.create(c,jobs.Start(kind='COMPANY_SUMMARIZE',resource_ids=[str(b.id)]));c.commit();jobs.execute(job['id'],path)
  assert provider.structured.await_count==1 and jobs.detail(c,job['id'])['items'][0]['result']['mode']=='CACHED'
  result=json.loads(c.execute('SELECT source_tags_json FROM businesses WHERE id=?',(b.id,)).fetchone()[0])['company_summary']
  assert result['claims'][0]['source_url']=='https://controlled.example/about' and not result['independently_verified']
  provider.structured.return_value=summary.Proposal(excerpts=[{'source_index':0,'quote':'Invented customers and metrics.'}])
  with pytest.raises(ai.AiOutputError):asyncio.run(summary.generate(c,facts))
  monkeypatch.setattr(get_settings(),'heysow_company_ai_enabled',False)
  assert asyncio.run(summary.generate(c,facts))['reason']=='COMPANY_AI_DISABLED'
  assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0
