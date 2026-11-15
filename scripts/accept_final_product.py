"""Bounded release acceptance on the existing owner workspace.

Uses normal production APIs and durable request IDs. No prospect acquisition,
email, payment, quota increase or product grant is performed. One optional HN
check and one report are explicit, separate phases so reruns cannot fan out.
"""
import argparse,hashlib,json,time,uuid
from pathlib import Path
import httpx
from scripts.deploy_product_release import signed,ROOT

OUT=ROOT/'data/artifacts/verification/final-remediation'

class Acceptance:
    def __init__(self,production=False):
        self.release=json.loads((OUT/'staged-release.json').read_text())
        self.source=self.release['source_commit']
        self.environment='production' if production else 'staged'
        self.path=OUT/('production-functional-state.json' if production else 'staged-functional-state.json')
        self.state=json.loads(self.path.read_text()) if self.path.exists() else {'source_commit':self.source,'checks':{},'http':[]}
        if self.state['source_commit']!=self.source:raise RuntimeError('Use the matching release acceptance checkpoint.')
        origin='https://leadengine-api-befca7xg4a-el.a.run.app' if production else 'https://intent-only---leadengine-api-befca7xg4a-el.a.run.app'
        self.client=httpx.Client(base_url=origin,timeout=75,follow_redirects=False)
    def save(self):
        self.path.write_text(json.dumps(self.state,indent=2));self.path.chmod(0o600)
    def request(self,path,method='GET',body=None,expected=(200,201,202),raw=False):
        started=time.monotonic();r=signed(self.client,path,method,body)
        self.state['http'].append({'method':method,'path':path,'http':r.status_code,'seconds':round(time.monotonic()-started,3)})
        self.save()
        if r.status_code not in expected:raise RuntimeError('Controlled API check failed at '+path+' HTTP '+str(r.status_code))
        return r if raw else r.json()
    def identity(self,name):
        return str(uuid.uuid5(uuid.NAMESPACE_URL,'final-product:'+self.source+':'+self.environment+':'+name))
    def counts(self):
        before=self.request('/api/organization/usage')
        body={'prompt':'How many signals have I generated yet?','request_id':self.identity('workspace-count')}
        turn=self.request('/api/intent-radar/assistant/turns','POST',body)
        if turn['job_id'] is not None or turn['output']['mode']!='Workspace data — no AI used':raise RuntimeError('Count question was incorrectly sent to AI.')
        replay=self.request('/api/intent-radar/assistant/turns','POST',body)
        if replay['id']!=turn['id']:raise RuntimeError('Count replay created another conversation.')
        followup=self.request('/api/intent-radar/assistant/turns','POST',{'prompt':'And today?','thread_id':turn['id'],'request_id':self.identity('workspace-count-today')})
        if followup['job_id'] is not None or followup['snapshot']['workspace_read']['period']!='today':raise RuntimeError('Follow-up lost its workspace read context.')
        after=self.request('/api/organization/usage')
        self.state['checks']['deterministic_counts']={'turn':turn['id'],'followup':followup['id'],'snapshot':turn['snapshot']['facts'],'idempotent':True,'ai_jobs_created':False,'provider_requests_delta':after['provider_usage']['requests']-before['provider_usage']['requests']}
        if self.state['checks']['deterministic_counts']['provider_requests_delta']!=0:raise RuntimeError('Provider activity changed during the isolated count acceptance; investigate before attributing usage.')
        self.save()
    def wait_job(self,key):
        deadline=time.monotonic()+360
        while time.monotonic()<deadline:
            job=self.request('/api/intelligence/jobs/'+key)
            if job['status'] not in ('QUEUED','RUNNING'):return job
            time.sleep(2)
        raise RuntimeError('Controlled worker did not finish within six minutes.')
    def research(self):
        body={'kind':'REPORT','title':'Owner-controlled final Growth release review','question':'Summarize only the needs and comparisons explicitly stated in these collected conversations. Cite exact evidence, explain noncommercial context and unknowns. Do not infer buyers, revenue or market-wide demand.','scope':{'days':0},'request_id':self.identity('growth-report')}
        initial=self.request('/api/intent-radar/growth/research','POST',body)
        self.state['report_id']=initial['id'];self.state['report_job_id']=initial['job_id'];self.save()
        job=self.wait_job(initial['job_id'])
        result=self.request('/api/intent-radar/growth/research/'+initial['id'])
        if job['status']!='COMPLETED' or result['status']!='COMPLETE' or not result['evidence_current']:raise RuntimeError('Controlled research did not complete with current evidence.')
        if not job.get('execution_name') or job['execution_name']=='DISPATCHING':raise RuntimeError('No actual cloud worker dispatch was recorded.')
        output=result['output'];citations=[citation for item in [*output.get('themes',[]),*output.get('findings',[])] for citation in item['citations']]
        if output.get('provider')!='VERTEX_AI' or not output.get('mode','').startswith('AI semantic') or not citations:raise RuntimeError('The real provider did not return a validated cited research interpretation.')
        saved=self.request('/api/intent-radar/growth/research/'+result['id'],'PATCH',{'revision':result['revision'],'saved':True})
        if not saved['saved_at']:raise RuntimeError('Saving the report did not persist.')
        formats={}
        for fmt in ('md','csv','json'):
            export=self.request('/api/intent-radar/growth/research/'+result['id']+'/export/'+fmt,raw=True)
            if not export.content or len(export.content)>2_000_000:raise RuntimeError('Controlled export was empty or exceeded its bound.')
            if fmt=='json':export.json()
            formats[fmt]={'bytes':len(export.content),'sha256':hashlib.sha256(export.content).hexdigest(),'mime':export.headers.get('content-type')}
        replay=self.request('/api/intent-radar/growth/research','POST',body)
        if replay['id']!=result['id'] or replay['job_id']!=initial['job_id']:raise RuntimeError('Completed report replay duplicated work.')
        self.state['checks']['research']={'id':result['id'],'job_id':initial['job_id'],'execution_name':job['execution_name'],'status':result['status'],'mode':output['mode'],'provider':output['provider'],'model':output.get('model'),'usage':output.get('usage'),'citations':len(citations),'exports':formats,'replayed_same_job':True}
        self.save()
    def discovery(self):
        config={'keywords':['recommend','looking for'],'sources':['hacker_news'],'hn_feeds':['ask'],'hn_comments':False,'result_limit':5}
        body={'name':'Owner-controlled final source acceptance','description':'One bounded HN check; no automatic schedule or outbound contact.','configuration':config,'request_id':self.identity('manual-monitor'),'status':'Draft'}
        monitor=self.request('/api/intent-radar/monitors','POST',body)
        self.state['manual_monitor_id']=monitor['id'];self.save()
        try:
            monitor=self.request('/api/intent-radar/monitors/'+monitor['id'],'PUT',{**body,'configuration':monitor['configuration'],'revision':monitor['revision'],'status':'Active'})
            monitor=self.request('/api/intent-radar/monitors/'+monitor['id']+'/schedule','PUT',{'frequency':'Manual','timezone':'Asia/Kolkata','revision':monitor['revision']})
            body={'configuration':monitor['configuration'],'monitor_id':monitor['id'],'request_id':self.identity('one-bounded-hn-check')}
            job=self.request('/api/intent-radar/discover','POST',body)
            self.state['discovery_job_id']=job['id'];self.save()
            result=self.wait_job(job['id'])
            if result['status']!='COMPLETED':raise RuntimeError('Real source collection failed; no fixture substituted.')
            details=self.request('/api/intent-radar/jobs/'+job['id'])
            signals=self.request('/api/intent-radar/signals?monitor_id='+monitor['id'])
            self.state['checks']['discovery']={'job_id':job['id'],'status':result['status'],'sources':details.get('sources',[]),'items':details['items'],'bounded_result_limit':5,'signals_returned':signals['total'],'real_outreach':False,'automatic_schedule':False}
            self.save()
        finally:
            latest=self.request('/api/intent-radar/monitors/'+monitor['id'])
            if latest['status']!='Paused':
                self.request('/api/intent-radar/monitors/'+monitor['id'],'PUT',{'name':latest['name'],'description':latest['description'],'goal':latest['goal'],'configuration':latest['configuration'],'status':'Paused','request_id':self.identity('manual-monitor'),'revision':latest['revision']})
            self.state['manual_monitor_paused']=True;self.save()
    def proof(self):
        checks=self.state['checks']
        if not all(name in checks for name in ('deterministic_counts','research')):raise RuntimeError('Required functional phases have not passed.')
        proof={'source_commit':self.source,'critical_failures':[],'worker_verified':True,'research_job':checks['research']['job_id'],'provider':'VERTEX_AI','deterministic_reads_verified':True,'outreach_sent':False,'payment_initiated':False,'real_prospect_contacted':False,'state_file':str(self.path)}
        p=OUT/'staged-functional-acceptance.json';p.write_text(json.dumps(proof,indent=2));p.chmod(0o600);print(json.dumps(proof))

def main():
    p=argparse.ArgumentParser();p.add_argument('phase',choices=('counts','research','discovery','proof'));p.add_argument('--production',action='store_true');args=p.parse_args()
    a=Acceptance(args.production)
    try:getattr(a,args.phase)();print(json.dumps({'phase':args.phase,'status':'PASS','source_commit':a.source}))
    except Exception as error:
        print(json.dumps({'status':'BLOCKED','error_type':type(error).__name__,'detail':str(error) if isinstance(error,RuntimeError) else 'Private diagnostics retained; no credentials disclosed.'}));raise SystemExit(1)
    finally:a.client.close()
if __name__=='__main__':main()
