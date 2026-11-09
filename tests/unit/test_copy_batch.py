import asyncio,copy,json,uuid
from unittest.mock import AsyncMock
import pytest
from pydantic import ValidationError
from test_experiment import brief_data
from test_automation import db
from app.experiments import copy_batch as batch,service,content
from app.experiments.plan import TEMPLATES
from app.acquisition import ai
from app.acquisition.config import AcquisitionSettings


def leads(data,count=40,prefix='batch'):
 out=[]
 for i in range(count):
  d=copy.deepcopy(data);d['business']['name']=f'Controlled Company {i:03}';template=TEMPLATES[i%5]
  out.append({'lead_id':str(uuid.uuid5(uuid.NAMESPACE_URL,prefix+str(i))),'campaign_id':'controlled-campaign','analysis_version':'analysis-v1','template_id':template,'data':d})
 return out

class Provider:
 def __init__(self,behavior=None):self.calls=[];self.behavior=behavior
 async def structured(self,instruction,payload,model,**options):
  assert 'untrusted DATA ONLY' in instruction and options['raw_json'] and options['retry_transient'] is False
  assert 'signature' not in payload and 'secret' not in json.dumps(payload).lower()
  self.calls.append(payload)
  if self.behavior:
   failure=self.behavior(payload,len(self.calls))
   if isinstance(failure,Exception):raise failure
   if failure is not None:return failure
  return response(payload)

def response(payload):
 return {'results':[{'lead_id':v['lead_id'],'subject':v['allowed_subjects'][0],'personalized_opening':v['allowed_openings'][0],'finding_1_copy':v['allowed_finding_1'][0],'finding_2_copy':v['allowed_finding_2'][0],'optional_bridge':''} for v in reversed(payload['leads'])]}

def generate(db,data,provider,**options):
 service.setup(db,'owner')
 return asyncio.run(batch.generate_personalized_copy_batch(db,data,'owner',client=provider,**options))

def test_forty_leads_one_call_id_matching_and_completed_copy_cache(db,brief_data):
 items=leads(brief_data);p=Provider();r=generate(db,items,p)
 assert len(p.calls)==1 and len(r['results'])==40 and r['metrics']['ai_generated_leads']==40 and r['metrics']['average_batch_size']==40
 for lead in items:assert not content.email_issues(lead['data'],content.render(lead['data'],lead['template_id'],generation=r['results'][lead['lead_id']]))
 again=generate(db,items,p);assert len(p.calls)==1 and again['metrics']['cache_hits']==40 and all(v['copy_generation_mode']=='CACHED' for v in again['results'].values())
 for v in items:v['analysis_version']='analysis-v2'
 generate(db,items,p);assert len(p.calls)==2


def test_one_bad_model_item_yields_39_good_and_one_safe_fallback(db,brief_data):
 def bad(payload,_):
  r=response(payload);r['results'][0]['finding_1_copy']='Guaranteed10x traffic and invisible in AI';return r
 p=Provider(bad);items=leads(brief_data);r=generate(db,items,p)
 assert r['metrics']['ai_generated_leads']==39 and r['metrics']['deterministic_fallback_leads']==1 and len(p.calls)==1
 fallback=[v for v in r['results'].values() if v['copy_generation_mode']=='DETERMINISTIC'];assert fallback[0]['ai_copy_status']=='AI_COPY_FAILED' and 'Guaranteed' not in str(fallback)


def test_duplicate_unknown_missing_ids_cannot_cross_personalizations(db,brief_data):
 def wrong(payload,_):
  r=response(payload);r['results'][1]=r['results'][0].copy();r['results'].append({**r['results'][0],'lead_id':'unknown'});return r
 r=generate(db,leads(brief_data),Provider(wrong));m=r['metrics']
 assert m['duplicate_ids']==1 and m['missing_ids']==1 and m['unknown_ids']==1 and m['deterministic_fallback_leads']==2


def test_invalid_large_response_gets_one_structured_retry_then20plus20(db,brief_data):
 p=Provider(lambda payload,n:ai.AiOutputError('Truncated synthetic output') if len(payload['leads'])==40 else None)
 r=generate(db,leads(brief_data),p)
 assert [len(v['leads']) for v in p.calls]==[40,40,20,20]
 assert len(r['results'])==40 and r['metrics']['split_batches']==1 and r['metrics']['ai_generated_leads']==40


def test_size_guard_splits_before_calling_provider(db,brief_data,monkeypatch):
 items=leads(brief_data);size=len(json.dumps({'task':'personalize_outreach_copy','template_version':'v1','leads':[batch.wire(v) for v in items]}).encode());monkeypatch.setattr(batch,'MAX_INPUT_BYTES',size*3//4)
 p=Provider();r=generate(db,items,p);assert [len(v['leads']) for v in p.calls]==[20,20] and r['metrics']['split_batches']==1


def test_quota_opens_durable_circuit_no_hammering_and_fallback_continues(db,brief_data):
 p=Provider(lambda *_:ai.AiRateLimited('QUOTA_EXHAUSTED',3600));r=generate(db,leads(brief_data),p)
 assert len(p.calls)==1 and r['metrics']['deterministic_fallback_leads']==40 and batch.status(db)['status']=='DEGRADED'
 next_run=generate(db,leads(brief_data,prefix='next'),p)
 assert len(p.calls)==1 and next_run['metrics']['deterministic_fallback_leads']==40
 assert batch.status(db)['metrics']['quota_errors']==1


def test_transient_retries_are_bounded_then_split(db,brief_data,monkeypatch):
 monkeypatch.setattr(batch.asyncio,'sleep',AsyncMock())
 p=Provider(lambda payload,n:ai.AiTransportError('Timeout') if len(payload['leads'])==40 else None);r=generate(db,leads(brief_data),p)
 assert [len(v['leads']) for v in p.calls]==[40,40,40,20,20] and r['metrics']['ai_generated_leads']==40


def test_minimum_batch_tail_and_bad_evidence_preserve_other_leads(db,brief_data):
 p=Provider();r=generate(db,leads(brief_data,4),p);assert len(p.calls)==0 and r['metrics']['deterministic_fallback_leads']==4
 items=leads(brief_data,prefix='invalid');items[0]['data']['evidence']={};r=generate(db,items,p)
 assert r['results'][items[0]['lead_id']]['needs_review'] and r['metrics']['ai_generated_leads']==39


def test_restart_does_not_repeat_an_uncertain_copy_request(db,brief_data):
 service.setup(db,'owner');items=leads(brief_data,5);fp=batch.key(items[0],'owner')
 db.execute("INSERT INTO acquisition_ai_cache(fingerprint,actor,task,result_json,expires_at,created_at) VALUES(?,'owner',?,?,'2020-01-01','2020-01-01')",(fp,batch.TASK,json.dumps({'_status':'GENERATING','owner':'interrupted'})))
 p=Provider();r=generate(db,items,p)
 assert not p.calls and r['results'][items[0]['lead_id']]['fallback_reason']=='INTERRUPTED_REQUEST'
 assert r['metrics']['deterministic_fallback_leads']==5


def test_single_health_probe_is_one_small_request_and_batch_configuration_is_bounded(db,brief_data):
 p=Provider();r=generate(db,leads(brief_data,1),p,health_probe=True);assert len(p.calls)==1 and r['metrics']['ai_generated_leads']==1
 for n in (1,9,51,100):
  with pytest.raises(ValidationError):AcquisitionSettings(_env_file=None,GEMINI_COPY_BATCH_SIZE=n)
 assert AcquisitionSettings(_env_file=None,GEMINI_COPY_BATCH_SIZE=40).copy_batch_size==40


def test_per_day_quota_metadata_is_sanitized_and_not_retried():
 error=batch.ai.rate_limit_details(json.dumps({'error':{'details':[{'violations':[{'quotaId':'GenerateRequestsPerDayPerProjectPerModel'}]},{'retryDelay':'3600s'}]}}).encode(),{})
 assert error.kind=='QUOTA_EXHAUSTED' and error.retry_after==3600 and 'key' not in str(error).lower()

@pytest.mark.parametrize('http_status',[400,401,402,403,404])
def test_nontransient_provider_rejection_degrades_once_without_splitting(db,brief_data,http_status):
 p=Provider(lambda *_:ai.AiProviderError(http_status));r=generate(db,leads(brief_data),p)
 assert len(p.calls)==1 and r['metrics']['deterministic_fallback_leads']==40
 assert batch.status(db)['status']=='DEGRADED' and not r['metrics'].get('split_batches')
 if http_status==402:assert batch.status(db)['error_code']=='BILLING_OR_CREDIT_REQUIRED'
