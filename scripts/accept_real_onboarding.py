"""Explicit real-provider research/setup acceptance in a NEW local database.

Uses ordinary profile/job/ICP services with real crawl and AI. Does not certify
Google/email authentication or the deployed worker. Never points at production,
changes a customer profile, sends mail, starts discovery or creates paid access.
"""
import argparse
import json
import os
import time
import uuid
from pathlib import Path
from dotenv import dotenv_values


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--website',required=True)
    parser.add_argument('--allow-real-provider',action='store_true')
    parser.add_argument('--output',required=True)
    parser.add_argument('--resume',action='store_true')
    args=parser.parse_args()
    if not args.allow_real_provider:raise RuntimeError('Explicit bounded real-provider acceptance required.')
    os.umask(0o077)
    root=Path(__file__).resolve().parents[1];out=Path(args.output).resolve()
    if not out.is_relative_to(root/'data/artifacts/verification'):raise RuntimeError('Use a private verification directory.')
    out.mkdir(parents=True,exist_ok=args.resume,mode=0o700)
    values=dotenv_values(os.environ.get('PLANEBYTE_OPERATOR_ENV_FILE',str(root/'.env')),interpolate=False)
    for key in ('AI_PROVIDER','AI_PRIMARY_PROVIDER','VERTEX_AI_ENABLED','VERTEX_AI_PROJECT_ID','VERTEX_AI_LOCATION','VERTEX_AI_MODEL','GEMINI_API_ENABLED','GEMINI_MODEL','GEMINI_API_KEY','AI_FALLBACK_ENABLED'):
        if values.get(key) is not None:os.environ[key]=values[key]
    os.environ.update(APP_ENV='development',DATABASE_BACKEND='sqlite',DATABASE_URL='',DATABASE_PATH=str(out/'isolated.sqlite'),ALLOWED_USER_EMAILS='onboarding-acceptance@planebyte.com',UPSTASH_REDIS_REST_URL='',UPSTASH_REDIS_REST_TOKEN='',LEAD_ENGINE_AVAILABLE='false',HEYSOW_ACCOUNTS_ENABLED='false',HEYSOW_ACCESS_PERIODS_ENABLED='false',PAYU_BILLING_ENABLED='false',BILLING_ENABLED='false',TRANSACTIONAL_MAIL_ENABLED='false',HEYSOW_SETUP_DIAGNOSTICS_ENABLED='true')
    for key in ('HEYSOW_WORKSPACE_MANAGEMENT_ENABLED','HEYSOW_COMPANY_DISCOVERY_ENABLED','HEYSOW_COMPANY_AI_ENABLED','HEYSOW_ICP_AI_ENABLED'):os.environ[key]='true'
    from app.database.connection import db_session
    from app.database.migrations import run_migrations
    from app.api.organization import create_organization
    from app.platform.context import workspace_scope
    from app.platform import onboarding_ai as setup,company_discovery as jobs
    actor='onboarding-acceptance@planebyte.com';proof={'website':args.website,'environment':'isolated local real-provider acceptance','stages':{},'production_profile_changed':False,'email_sent':False,'payment_initiated':False}
    if args.resume:proof=json.loads((out/'result-private.json').read_text())
    def save():
        path=out/'result-private.json';path.write_text(json.dumps(proof,indent=2));path.chmod(0o600)
    with db_session() as c:
        run_migrations(c)
        org=proof.get('workspace_id') or create_organization(c,actor,'Authorized onboarding acceptance')['organization_id'];c.commit()
    proof['workspace_id']=org;save()
    def stage(kind,key):
        prior=proof['stages'].get(kind)
        if prior and prior['status']=='READY':return prior['preview']
        if prior:
            with db_session() as c:
                with workspace_scope(c,actor,org):jobs.control(c,key,'RETRY');c.commit()
        started=time.monotonic();jobs.execute(key)
        with db_session() as c:
            with workspace_scope(c,actor,org):detail=jobs.detail(c,key)
        if prior:proof.setdefault('prior_attempts',[]).append({'stage':kind,**prior})
        proof['stages'][kind]={'seconds':round(time.monotonic()-started,3),**detail};save()
        print(json.dumps({'stage':kind,'status':detail['status'],'job_id':key,'error_code':detail['error_code'],'seconds':proof['stages'][kind]['seconds']}),flush=True)
        if detail['status']!='READY':raise RuntimeError(kind+' did not produce a ready result; private diagnostics retained.')
        return detail['preview']
    if 'website' in proof['stages']:
        preview=stage('website',proof['stages']['website']['id'])
    else:
        with db_session() as c:
            with workspace_scope(c,actor,org):
                request=setup.analyze(c,setup.Start(revision=0,website=args.website,objective='UNDERSTAND_CUSTOMER_NEEDS',request_id=uuid.uuid4()));c.commit()
        preview=stage('website',request['review']['id'])
    if 'icps' in proof['stages']:
        proposal=stage('icps',proof['stages']['icps']['id'])
    else:
        with db_session() as c:
            with workspace_scope(c,actor,org):
                state=setup.state(c);fields={k:v for k,v in state['company'].items() if k in setup.CompanyUpdate.model_fields};fields.update(preview['suggestions']);fields.update(review_id=request['review']['id'],reviewed_fields=list(preview['suggestions']))
                approved=setup.company(c,setup.SaveCompany(revision=state['progress']['revision'],objective='UNDERSTAND_CUSTOMER_NEEDS',profile=fields));c.commit()
                request=setup.recommendations(c,setup.Recommend(revision=approved['progress']['revision'],request_id=uuid.uuid4()));c.commit()
        proposal=stage('icps',request['review']['id'])
    if 'assistant' in proof['stages']:
        question={'job':{'id':proof['stages']['assistant']['id']}}
    else:
        with db_session() as c:
            with workspace_scope(c,actor,org):
                state=setup.state(c);choices=[{'candidate_index':i,**{k:v for k,v in item['draft'].items() if k in ('name','description','criteria')}} for i,item in enumerate(proposal['candidates'])]
                accepted=setup.accept(c,setup.Accept(revision=state['progress']['revision'],proposal_id=proposal['proposal_id'],candidates=choices,primary_index=0,request_id=uuid.uuid4()));c.commit()
                question=setup.ask(c,setup.Question(prompt='Which customer segment best matches our saved offerings, what pain does it address, and what assumptions should I validate before using Discover?',request_id=uuid.uuid4()));c.commit()
    advice=stage('assistant',question['job']['id'])
    with db_session() as c:
        with workspace_scope(c,actor,org):
            followup=setup.ask(c,setup.Question(prompt='Why prioritize that segment over the others, and what evidence are we still missing?',parent_review_id=question['job']['id'],request_id=uuid.uuid4()));c.commit()
    stage('assistant_followup',followup['job']['id'])
    with db_session() as c:
        with workspace_scope(c,actor,org):
            saved=setup.state(c);completed=setup.finish(c,setup.Finish(revision=saved['progress']['revision'],primary_icp_id=saved['progress']['default_icp_id']));c.commit()
            persisted=setup.state(c)
            prefs=json.loads(c.execute('SELECT configuration_json FROM intent_preferences WHERE organization_id=?',(org,)).fetchone()[0])
            assert completed['status']=='COMPLETED' and prefs['default_icp_id']==persisted['progress']['default_icp_id']
            proof['persisted_company']=persisted['company'];proof['completed']=completed
            proof['provider_usage']=[dict(v) for v in c.execute('SELECT operation,provider,model,status,input_tokens,output_tokens,duration_ms FROM ai_request_usage WHERE organization_id=? ORDER BY created_at',(org,)).fetchall()]
            for table in ('intent_monitors','intent_discoveries','pipeline_runs','email_messages'):assert c.execute('SELECT COUNT(*) FROM '+table+' WHERE organization_id=?',(org,)).fetchone()[0]==0
    proof['status']='PASS';proof['authentication_verified']=False;proof['cloud_dispatch_verified']=False;save()
    print(json.dumps({'status':'PASS','actual_provider_requests':len(proof['provider_usage']),'icps':len(proposal['candidates']),'website_fields':list(preview['suggestions']),'completed':True,'proof':str(out/'result-private.json')}))

if __name__=='__main__':
    try:main()
    except Exception as error:
        print(json.dumps({'status':'FAILED','error_type':type(error).__name__,'detail':str(error) if isinstance(error,RuntimeError) else 'Private diagnostic output retained; credentials withheld.'}));raise SystemExit(1)
