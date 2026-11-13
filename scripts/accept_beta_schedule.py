"""Expedite one owner-controlled monitor's due time to test the real dispatcher.

The saved six-hour policy is retained; no acquisition or outreach is dispatched.
"""
import asyncio,json,subprocess,uuid
from datetime import datetime,timezone
from app.database.postgres import PostgresConnection
from app.platform.context import workspace_scope
from app.database.prospects import now
from scripts.accept_beta_production import Acceptance,OUT
from scripts.deploy_beta_backend import CLI,PROJECT,REGION

async def main():
    a=Acceptance();result={'scope':'One persisted owner-controlled Hacker News monitor; no email or prospect acquisition.'}
    try:
        monitor=await a.request('GET','/api/intent-radar/monitors/'+a.state['monitor_id'])
        if monitor['name']!='Owner-controlled beta acceptance' or monitor['configuration']['sources']!=['hacker_news']:raise RuntimeError('Unexpected acceptance resource.')
        if monitor['schedule'].get('frequency')!='6 hours':
            monitor=await a.request('PUT','/api/intent-radar/monitors/'+monitor['id']+'/schedule',{'frequency':'6 hours','timezone':'Asia/Kolkata','revision':monitor['revision']})
        previous=monitor.get('last_job_id');stamp=now()
        c=PostgresConnection(a.values['DATABASE_URL'],session_bound=True)
        try:
            rows=c.execute("SELECT o.id FROM organizations o JOIN organization_memberships m ON m.organization_id=o.id WHERE o.slug='planebyte' AND o.status='ACTIVE' AND m.user_id=? AND m.role IN ('OWNER','ADMIN') AND m.status='ACTIVE'",('planebyte@gmail.com',)).fetchall()
            if len(rows)!=1:raise RuntimeError('Owner membership is not unique.')
            org=rows[0][0]
            with workspace_scope(c,'planebyte@gmail.com',org):
                if not c.execute("SELECT 1 FROM organization_products WHERE organization_id=? AND product='INTENT_RADAR' AND enabled=1",(org,)).fetchone():raise RuntimeError('Beta grant unavailable.')
                changed=c.execute("UPDATE intent_monitors SET next_run_at=?,updated_at=? WHERE id=? AND organization_id=? AND revision=? AND status='Active' AND next_run_at=?",(stamp,stamp,monitor['id'],org,monitor['revision'],monitor['next_run_at'])).rowcount
                if changed!=1:raise RuntimeError('Controlled monitor changed; no retry override.')
                c.execute('INSERT INTO audit_log(id,actor,action,entity,result,details_json,organization_id,created_at) VALUES(?,?,?,?,?,?,?,?)',(str(uuid.uuid4()),'planebyte@gmail.com','CONTROLLED_SCHEDULE_ACCEPTANCE_DUE','intent-monitor:'+monitor['id'],'SUCCESS',json.dumps({'saved_frequency':'6 hours','reason':'Expedite only this approved acceptance monitor to verify actual scheduler dispatch.'}),org,stamp))
            c.commit()
        except Exception:c.rollback();raise
        finally:c.close()
        r=subprocess.run([CLI,'scheduler','jobs','run','leadengine-intent-radar-dispatch','--project='+PROJECT,'--location='+REGION,'--quiet'],capture_output=True,text=True,timeout=60)
        if r.returncode:raise RuntimeError('Actual scheduler dispatch failed.')
        result.update(scheduler_invoked=True,monitor_id=monitor['id'],saved_frequency='6 hours',expedited_due_only=True)
        for _ in range(16):
            current=await a.request('GET','/api/intent-radar/monitors/'+monitor['id'])
            key=current.get('last_job_id')
            if key and key!=previous:
                job=await a.request('GET','/api/intent-radar/jobs/'+key)
                result.update(scheduled_job_id=key,scheduled_job_status=job['status'],next_run_at=current['next_run_at'])
                if job['status'] in ('COMPLETED','FAILED','CANCELLED'):break
            await asyncio.sleep(4)
        result['pass']=result.get('scheduled_job_status')=='COMPLETED' and result.get('next_run_at','')>stamp
        (OUT/'scheduled-production-acceptance.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
        if not result['pass']:raise RuntimeError('Scheduled execution acceptance incomplete.')
    finally:await a.client.aclose()

if __name__=='__main__':
    try:asyncio.run(main())
    except Exception as error:print(json.dumps({'status':'FAILED','error_type':type(error).__name__,'safe_error':str(error) if isinstance(error,RuntimeError) else 'No credentials printed.'}));raise SystemExit(1)
