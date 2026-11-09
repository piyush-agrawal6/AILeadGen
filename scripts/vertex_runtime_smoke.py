"""Run inside an existing Cloud Run runtime identity; no SMTP or prospect creation."""
import asyncio,json,os
from app.database.connection import get_connection
from app.experiments.copy_batch import generate_personalized_copy_batch,synthetic_leads
from app.config.settings import get_settings
from app.acquisition.config import settings
async def smoke():
 c=get_connection(session_bound=True)
 try:
  s=settings();leads=synthetic_leads(c,1,'Production service identity check');result=await generate_personalized_copy_batch(c,leads,get_settings().allowed_emails[0],health_probe=True,force=True)
  item=result['results'][leads[0]['lead_id']];passed=item.get('copy_provider')=='VERTEX_AI' and result['metrics'].get('vertex_requests')==1 and result['metrics'].get('ai_generated_leads')==1
  proof={'provider':'VERTEX_AI','passed':passed,'project':s.vertex_project,'location':s.vertex_location,'model':s.vertex_model,'authentication':'SERVICE_IDENTITY','cloud_run':bool(os.getenv('CLOUD_RUN_JOB') or os.getenv('K_SERVICE')),'structured_output_valid':passed,'emails_sent':0,'metrics':result['metrics']}
  print(json.dumps(proof),flush=True)
  from app.experiments.service import event
  from app.experiments.plan import EXPERIMENT_ID
  event(c,EXPERIMENT_ID,'VERTEX_RUNTIME_SMOKE',proof);c.commit()
  if not passed:raise SystemExit(1)
 finally:c.close()
if __name__=='__main__':asyncio.run(smoke())
