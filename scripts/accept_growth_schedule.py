"""Verify one controlled Growth watchlist on the real existing dispatcher.

Only an owned acceptance monitor's due timestamp is expedited. Its six-hour
policy remains intact, and it is paused after completion to avoid duplicate
standing source spending. No contacts, campaigns or emails are created.
"""
import asyncio,json,subprocess,uuid
from app.database.postgres import PostgresConnection
from app.database.prospects import now
from app.platform.context import workspace_scope
from scripts.accept_growth_production import Acceptance,OUT
from scripts.deploy_beta_backend import CLI,PROJECT,REGION

async def main():
    a=Acceptance();proof={'source':'One existing approved Hacker News adapter','no_prospect_acquisition':True,'no_outreach':True}
    try:
        a.state.setdefault('watchlist_request',str(uuid.uuid4()));a.save()
        if not a.state.get('watchlist_id'):
            created=await a.request('POST','/api/intent-radar/growth/watchlists',{'name':'Owner-controlled Growth schedule verification','kind':'Market','keywords':['Ask HN'],'request_id':a.state['watchlist_request']})
            a.state['watchlist_id']=created['monitor']['id'];a.save()
        key=a.state['watchlist_id'];m=await a.request('GET','/api/intent-radar/monitors/'+key)
        if m['name']!='Owner-controlled Growth schedule verification':raise RuntimeError('Unexpected acceptance monitor.')
        configuration={**m['configuration'],'sources':['hacker_news'],'hn_feeds':['ask'],'result_limit':5,'semantic':False}
        body={k:m.get(k,'') for k in ('name','description','goal')}
        m=await a.request('PUT','/api/intent-radar/monitors/'+key,{**body,'configuration':configuration,'status':'Active','revision':m['revision'],'request_id':a.state['watchlist_request']})
        m=await a.request('PUT','/api/intent-radar/monitors/'+key+'/schedule',{'frequency':'6 hours','timezone':'Asia/Kolkata','revision':m['revision']})
        previous=m.get('last_job_id');stamp=now();c=PostgresConnection(a.values['DATABASE_URL'],session_bound=True)
        try:
            org='e5ffc3dc-241e-5558-acd4-84f5fe354ca7'
            with workspace_scope(c,'planebyte@gmail.com',org):
                if not c.execute("SELECT 1 FROM growth_watchlists WHERE organization_id=? AND monitor_id=?",(org,key)).fetchone():raise RuntimeError('Watchlist ownership cannot be verified.')
                if c.execute("UPDATE intent_monitors SET next_run_at=?,updated_at=? WHERE organization_id=? AND id=? AND status='Active' AND revision=? AND next_run_at=?",(stamp,stamp,org,key,m['revision'],m['next_run_at'])).rowcount!=1:raise RuntimeError('Controlled monitor changed; no broad retry override.')
                c.execute('INSERT INTO audit_log(id,actor,action,entity,result,details_json,organization_id,created_at) VALUES(?,?,?,?,?,?,?,?)',(str(uuid.uuid4()),'planebyte@gmail.com','GROWTH_CONTROLLED_DUE_ACCEPTANCE','intent-monitor:'+key,'SUCCESS',json.dumps({'saved_frequency':'6 hours','maximum_results':5,'expedite_only':True}),org,stamp))
            c.commit()
        except Exception:c.rollback();raise
        finally:c.close()
        for _ in range(2):
            result=await asyncio.to_thread(subprocess.run,[CLI,'scheduler','jobs','run','leadengine-intent-radar-dispatch','--project='+PROJECT,'--location='+REGION,'--quiet'],capture_output=True,text=True,timeout=60)
            if result.returncode:raise RuntimeError('Existing scheduler invocation failed.')
        for _ in range(12):
            m=await a.request('GET','/api/intent-radar/monitors/'+key);job_id=m.get('last_job_id')
            if job_id and job_id!=previous:
                job=await a.request('GET','/api/intent-radar/jobs/'+job_id)
                proof.update(monitor_id=key,job_id=job_id,status=job['status'],next_run_at=m.get('next_run_at'))
                if job['status'] in ('COMPLETED','FAILED','CANCELLED'):break
            await asyncio.sleep(3)
        c=PostgresConnection(a.values['DATABASE_URL'],session_bound=True)
        try:
            proof['discoveries_created']=c.execute('SELECT COUNT(*) FROM intent_discoveries WHERE organization_id=? AND monitor_id=? AND created_at>=?',(org,key,stamp)).fetchone()[0]
        finally:c.close()
        proof['pass']=proof.get('status')=='COMPLETED' and proof.get('next_run_at','')>stamp and proof['discoveries_created']==1
        m=await a.request('GET','/api/intent-radar/monitors/'+key)
        body={k:m.get(k,'') for k in ('name','description','goal')}
        paused=await a.request('PUT','/api/intent-radar/monitors/'+key,{**body,'configuration':m['configuration'],'status':'Paused','revision':m['revision'],'request_id':a.state['watchlist_request']})
        proof['acceptance_watchlist_paused']=paused['status']=='Paused'
        (OUT/'scheduled-watchlist.json').write_text(json.dumps(proof,indent=2));print(json.dumps(proof))
        if not proof['pass']:raise RuntimeError('Controlled scheduled watchlist acceptance did not pass.')
    finally:
        # A failed acceptance must not leave a second standing paid/CPU task.
        # Only the persisted, exactly named owner-controlled resource is paused.
        try:
            if a.state.get('watchlist_id'):
                current=await a.request('GET','/api/intent-radar/monitors/'+a.state['watchlist_id'])
                if current['name']=='Owner-controlled Growth schedule verification' and current['status']=='Active':
                    body={k:current.get(k,'') for k in ('name','description','goal')}
                    await a.request('PUT','/api/intent-radar/monitors/'+current['id'],{**body,'configuration':current['configuration'],'status':'Paused','revision':current['revision'],'request_id':a.state['watchlist_request']})
        finally:await a.client.aclose()
if __name__=='__main__':
    try:asyncio.run(main())
    except Exception as error:print(json.dumps({'status':'FAILED','error_type':type(error).__name__,'detail':str(error) if isinstance(error,RuntimeError) else 'Inspect restricted acceptance state; no credentials printed.'}));raise SystemExit(1)
