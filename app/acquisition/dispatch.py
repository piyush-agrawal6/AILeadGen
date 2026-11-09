"""Separate Cloud Run job and capacity: no changes to the Overture/mail dispatcher."""
import asyncio,uuid
from app.config.settings import get_settings
from app.acquisition.config import settings
from app.database.connection import db_session
from app.acquisition.service import job,event

_tasks=set()
def run_job(jid):
    import google.auth
    from google.auth.transport.requests import AuthorizedSession
    s=get_settings();credentials,_=google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform']);client=AuthorizedSession(credentials)
    response=client.post(f'https://run.googleapis.com/v2/projects/{s.gcp_project_id}/locations/{s.gcp_region}/jobs/{settings().job_name}:run',json={'overrides':{'taskCount':1,'containerOverrides':[{'env':[{'name':'LEADENGINE_ACQUISITION_JOB_ID','value':jid}]}]}},timeout=25)
    if response.status_code>=400:raise RuntimeError('Acquisition job dispatch failed (HTTP '+str(response.status_code)+').')
    return response.json().get('name','accepted')

async def launch(jid):
    """Invoked after route transaction commits, never before its source becomes durable."""
    with db_session() as c:
        r=job(c,jid)
        if r['status']!='QUEUED' or r['execution_name']:return
        changed=c.execute("UPDATE acquisition_jobs SET execution_name='DISPATCHING' WHERE id=? AND status='QUEUED' AND execution_name IS NULL",(jid,)).rowcount
        if not changed:return
    try:
        if get_settings().app_env=='production':
            operation=await asyncio.to_thread(run_job,jid)
            with db_session() as c:c.execute('UPDATE acquisition_jobs SET execution_name=? WHERE id=?',(operation,jid))
        else:
            from app.acquisition.worker import execute
            task=asyncio.create_task(asyncio.to_thread(execute,jid));_tasks.add(task);task.add_done_callback(_tasks.discard)
    except Exception:
        with db_session() as c:
            c.execute("UPDATE acquisition_jobs SET status='FAILED',error_code='ACQUISITION_DISPATCH_FAILED',execution_name=NULL WHERE id=?",(jid,));event(c,jid,'FAILED','Acquisition dispatch failed. Existing scans and outreach are unaffected; retry this source explicitly.')
