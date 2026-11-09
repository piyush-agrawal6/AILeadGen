import asyncio,json
from types import SimpleNamespace
from unittest.mock import AsyncMock
import httpx,pytest
from pydantic import BaseModel
from test_automation import db
from app.acquisition import ai
from app.acquisition.config import AcquisitionSettings
from app.acquisition.vertex import VertexAIProvider,vertex_schema
from app.acquisition.ai_router import AIProviderRouter
from test_copy_batch import leads,Provider,response
from test_experiment import brief_data
from app.experiments.copy_batch import generate_personalized_copy_batch,status
from app.experiments import service
class Result(BaseModel):answer:str
class Stub:
 def __init__(self,name,error=None):self.provider_name=name;self.model='configured-model';self.error=error;self.calls=0
 async def structured(self,*args,**kw):
  self.calls+=1
  if self.error:raise self.error
  return Result(answer='valid')
def config():return AcquisitionSettings(_env_file=None,AI_PRIMARY_PROVIDER='vertex',VERTEX_AI_ENABLED=True,VERTEX_AI_PROJECT_ID='querryside',VERTEX_AI_MODEL='configured-model',GEMINI_API_KEY='fixture-key')

def test_vertex_first_failure_uses_same_request_on_gemini_after_bounded_retry(db,monkeypatch):
 monkeypatch.setattr(asyncio,'sleep',AsyncMock());v=Stub('VERTEX_AI',ai.AiProviderError(503));g=Stub('GEMINI_API');r=AIProviderRouter(config(),c=db,providers=[v,g])
 assert asyncio.run(r.structured('rules',{'lead_ids':['a']},Result)).answer=='valid'
 assert v.calls==3 and g.calls==1 and r.last_provider=='GEMINI_API' and r.metrics['gemini_fallback_requests']==1
 assert r.states()['VERTEX_AI']['status']=='DEGRADED' and r.states()['GEMINI_API']['status']=='READY'


def test_vertex_success_never_calls_fallback_and_model_is_configured(db):
 v=Stub('VERTEX_AI');g=Stub('GEMINI_API');r=AIProviderRouter(config(),c=db,providers=[v,g])
 asyncio.run(r.structured('rules',{},Result));assert v.calls==1 and g.calls==0 and r.last_model=='configured-model'


def test_application_bug_or_internal_schema_does_not_trigger_provider_fallback(db):
 v=Stub('VERTEX_AI',TypeError('Programming exception'));g=Stub('GEMINI_API');r=AIProviderRouter(config(),c=db,providers=[v,g])
 with pytest.raises(TypeError):asyncio.run(r.structured('rules',{},Result))
 assert g.calls==0
 v.error=ai.AiProviderError(400)
 with pytest.raises(ai.AiApplicationError):asyncio.run(r.structured('rules',{},Result))
 assert g.calls==0


def test_both_providers_unavailable_use_deterministic_without_split_or_hammer(db,brief_data):
 service.setup(db,'owner');v=Stub('VERTEX_AI',ai.AiRateLimited('QUOTA_EXHAUSTED',3600));g=Stub('GEMINI_API',ai.AiProviderError(402));router=AIProviderRouter(config(),c=db,providers=[v,g]);items=leads(brief_data)
 result=asyncio.run(generate_personalized_copy_batch(db,items,'owner',client=router))
 assert v.calls==g.calls==1 and result['metrics']['deterministic_fallback_leads']==40 and not result['metrics'].get('split_batches')
 assert result['metrics']['vertex_requests']==1 and result['metrics']['gemini_requests']==1
 assert all(r['copy_provider']=='DETERMINISTIC' for r in result['results'].values())
 again=asyncio.run(generate_personalized_copy_batch(db,leads(brief_data,prefix='more'),'owner',client=router));assert v.calls==g.calls==1 and again['metrics']['deterministic_fallback_leads']==40


def test_schema_wire_is_supported_and_adc_headers_never_use_api_key(monkeypatch):
 requests=[]
 def transport(request):
  requests.append(request);body=json.loads(request.content);schema=body['generationConfig']['responseSchema'];assert '$defs' not in json.dumps(schema) and 'responseMimeType' in body['generationConfig'];assert 'x-goog-api-key' not in request.headers;assert request.headers['Authorization']=='Bearer ephemeral-fixture-token'
  return httpx.Response(200,json={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'{"answer":"valid"}'}]}}]})
 monkeypatch.setenv('APP_ENV','test');creds=SimpleNamespace(valid=True,token='ephemeral-fixture-token')
 p=VertexAIProvider(config(),httpx.MockTransport(transport),credentials=creds);assert asyncio.run(p.structured('rules',{},Result)).answer=='valid'
 assert 'projects/querryside/locations/global/publishers/google/models/configured-model' in str(requests[0].url)


def test_production_vertex_rejects_credential_file_environment(monkeypatch):
 monkeypatch.setenv('APP_ENV','production');monkeypatch.setenv('GOOGLE_APPLICATION_CREDENTIALS','forbidden-key.json')
 with pytest.raises(ai.AiAuthError):VertexAIProvider(config()).access_token()


def test_vertex_model_setting_does_not_silently_substitute():
 from app.acquisition.config import AcquisitionSettings
 s=AcquisitionSettings(_env_file=None,VERTEX_AI_ENABLED=True,VERTEX_AI_MODEL='owner-selected-model')
 assert VertexAIProvider(s).model=='owner-selected-model'


def test_real_batch_vertices_metadata_and_same_fallback_batch(db,brief_data):
 class CopyStub:
  def __init__(self,name,error=None):self.provider_name=name;self.model='configured-model';self.error=error;self.sizes=[]
  async def structured(self,instruction,payload,model,**kw):
   self.sizes.append(len(payload['leads']))
   if self.error:raise self.error
   return response(payload)
 service.setup(db,'owner');v=CopyStub('VERTEX_AI',ai.AiRateLimited());g=CopyStub('GEMINI_API');r=AIProviderRouter(config(),c=db,providers=[v,g])
 result=asyncio.run(generate_personalized_copy_batch(db,leads(brief_data),'owner',client=r));assert v.sizes==g.sizes==[40]
 assert all(x['copy_provider']=='GEMINI_API' and x['copy_generation_mode']=='AI_BATCH' for x in result['results'].values())
 assert result['metrics']['gemini_fallback_requests']==1


def test_disabled_fallback_never_silently_promotes_secondary():
 s=AcquisitionSettings(_env_file=None,AI_PRIMARY_PROVIDER='vertex',VERTEX_AI_ENABLED=False,AI_FALLBACK_ENABLED=False,GEMINI_API_KEY='fixture')
 r=AIProviderRouter(s)
 assert r.providers==[]
 with pytest.raises(ai.AiProvidersUnavailable):asyncio.run(r.structured('rules',{},Result))


def test_content_rejection_is_a_provider_error_not_an_internal_bug(db):
 from app.acquisition.ai_router import normalized_error
 v=Stub('VERTEX_AI',ai.AiContentRejected('Provider rejection'));g=Stub('GEMINI_API');r=AIProviderRouter(config(),c=db,providers=[v,g])
 assert asyncio.run(r.structured('rules',{},Result)).answer=='valid'
 assert v.calls==1 and g.calls==1 and normalized_error(ai.AiContentRejected())=='CONTENT_REJECTED'


def test_source_settings_ignore_internal_provider_metadata_and_preserve_it_on_save(db):
 from types import SimpleNamespace
 from app.api.routes.acquisition import status,save_preferences,Preferences
 import json
 from app.platform.context import current
 request=SimpleNamespace(state=SimpleNamespace(user_email=current().actor,organization_id=current().organization_id))
 router=AIProviderRouter(config(),c=db,providers=[]);router.record(Stub('VERTEX_AI'),'READY');before=router.states()
 assert status(request,db)['preferences']['enabled']['ai']
 saved=Preferences(enabled={'ai':False,'firecrawl':True,'import':True,'sheets':True});save_preferences(saved,request,db)
 assert router.states()==before and status(request,db)['preferences']['enabled']['ai'] is False
 from pydantic import ValidationError
 with pytest.raises(ValidationError):Preferences.model_validate({'ai_providers':{'VERTEX_AI':{'status':'READY'}}})
