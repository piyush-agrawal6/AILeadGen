"""Bounded real-provider acceptance in an explicitly isolated clean schema.

Never runs against public/customer schemas. No auth, payment or outreach test
is implied by this AI-pipeline check. The existing worker identity and providers
are used; results remain in the isolated schema for independent retrieval.
"""
import argparse,json,re,time,uuid
from app.config.settings import get_settings
from app.database.connection import db_session
from app.database.migrations import verify_schema
from app.api.organization import create_organization
from app.platform.context import workspace_scope
from app.platform import onboarding_ai as setup,company_discovery as jobs
from app.billing import subscription_access
from app.database.prospects import now


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--website',required=True);args=parser.parse_args()
    settings=get_settings()
    if settings.database_schema_profile!='intent-radar-v1' or not re.fullmatch(r'onboarding_acceptance_[a-f0-9]{12}',settings.database_schema):
        raise RuntimeError('An explicitly isolated clean acceptance schema is required')
    # These overrides apply only to this non-customer test execution/schema.
    # Public authentication and billing configuration are never changed.
    actor='contact@planebyte.com'
    settings.allowed_user_emails=actor;settings.heysow_accounts_enabled=False
    settings.transactional_mail_enabled=False
    proof={'website':args.website,'schema':settings.database_schema,'status':'RUNNING','stages':{},
           'real_provider':True,'customer_schema_changed':False,'authentication_tested':False,
           'payment_initiated':False,'messages_sent':False}

    def persist():
        with db_session() as c:
            c.execute("INSERT INTO intent_worker_health(worker_id,last_tick_at,state,detail_json) VALUES('onboarding-acceptance',?,?,?) ON CONFLICT(worker_id) DO UPDATE SET last_tick_at=excluded.last_tick_at,state=excluded.state,detail_json=excluded.detail_json",(now(),proof['status'],json.dumps(proof)))

    with db_session() as c:
        verify_schema(c)
        if c.execute('SELECT COUNT(*) FROM organizations').fetchone()[0]:raise RuntimeError('Acceptance schema must begin empty; do not repeat uncertain provider work')
        org=create_organization(c,actor,'PlaneByte real-provider acceptance')['organization_id']
        subscription_access.enroll(c,actor,org)
    proof['organization_id']=org;persist()

    def execute(stage,key):
        started=time.monotonic();jobs.execute(key)
        with db_session() as c:
            with workspace_scope(c,actor,org):detail=jobs.detail(c,key)
        proof['stages'][stage]={**detail,'elapsed_seconds':round(time.monotonic()-started,3)};persist()
        print(json.dumps({'stage':stage,'job_id':key,'status':detail['status'],'error_code':detail['error_code']}),flush=True)
        if detail['status']!='READY':raise RuntimeError(stage+' failed: '+str(detail['error_code']))
        return detail['preview']

    try:
        with db_session() as c:
            with workspace_scope(c,actor,org):
                started=setup.analyze(c,setup.Start(revision=0,website=args.website,objective='UNDERSTAND_CUSTOMER_NEEDS',request_id=uuid.uuid4()))
        preview=execute('website',started['review']['id'])
        fields=preview['suggestions']
        assert len(fields.get('description',''))>=40 and fields.get('products_services') and fields.get('positioning'), 'Meaningful description, offerings and positioning required'
        with db_session() as c:
            with workspace_scope(c,actor,org):
                state=setup.state(c);values={k:v for k,v in state['company'].items() if k in setup.CompanyUpdate.model_fields}
                values.update(fields);values.update(review_id=started['review']['id'],reviewed_fields=list(fields))
                saved=setup.company(c,setup.SaveCompany(revision=state['progress']['revision'],objective='UNDERSTAND_CUSTOMER_NEEDS',profile=values));c.commit()
                created=setup.recommendations(c,setup.Recommend(revision=saved['progress']['revision'],request_id=uuid.uuid4()))
        proposal=execute('icps',created['review']['id']);assert len(proposal['candidates'])==5
        with db_session() as c:
            with workspace_scope(c,actor,org):
                state=setup.state(c)
                choices=[{'candidate_index':i,**{k:v for k,v in item['draft'].items() if k in ('name','description','criteria')}} for i,item in enumerate(proposal['candidates'])]
                accepted=setup.accept(c,setup.Accept(revision=state['progress']['revision'],proposal_id=proposal['proposal_id'],candidates=choices,primary_index=0,request_id=uuid.uuid4()));c.commit()
                before=setup.read_profile(c)
                draft={k:v for k,v in before.items() if k in setup.CompanyFields.model_fields}
                draft['positioning']='Proposed focus for review: founder-led product teams.'
                question=setup.ask(c,setup.Question(prompt='Which saved offerings and reviewed ICP best fit our business? Explain the customer need. My UNSAVED draft proposes a focus on founder-led product teams: distinguish this draft from saved facts and suggest an edit to review. Do not claim an edit was saved.',draft=draft,request_id=uuid.uuid4()))
        advice=execute('copilot',question['job']['id']);assert len(advice['answer'])>=40
        with db_session() as c:
            with workspace_scope(c,actor,org):
                assert setup.read_profile(c)==before,'Copilot must never silently save a draft'
                state=setup.state(c);edit={k:v for k,v in before.items() if k in setup.CompanyUpdate.model_fields}
                edit['description']=before['description']+' Review note: targeting suggestions require validation.'
                edited=setup.company(c,setup.SaveCompany(revision=state['progress']['revision'],objective='UNDERSTAND_CUSTOMER_NEEDS',profile=edit));c.commit()
                assert setup.read_profile(c)['description']==edit['description']
                facts=setup.ask(c,setup.Question(prompt='What company details are saved?',request_id=uuid.uuid4()))
                assert facts['job'] is None and 'Review note:' in facts['answer']
                proof.update(status='PASS',persisted_company=setup.read_profile(c),icp_count=c.execute('SELECT COUNT(*) FROM ideal_customer_profiles WHERE organization_id=?',(org,)).fetchone()[0],
                    copilot_did_not_save_draft=True,explicit_profile_edit_persisted=True,saved_context_synchronized=True,
                    provider_usage=[dict(r) for r in c.execute('SELECT operation,provider,model,status,input_tokens,output_tokens,duration_ms FROM ai_request_usage WHERE organization_id=? ORDER BY created_at',(org,)).fetchall()])
                assert proof['icp_count']==5 and all(r['provider']=='VERTEX_AI' and r['status']=='SUCCEEDED' for r in proof['provider_usage'])
        persist();print(json.dumps({'status':'PASS','icps':5,'provider_requests':len(proof['provider_usage']),'schema':settings.database_schema}),flush=True)
    except Exception as error:
        proof.update(status='FAILED',error_type=type(error).__name__);persist()
        raise


if __name__=='__main__':main()
