"""Normal account/outbox code + actual Resend delivery in a NEW isolated DB.

Only the explicitly authorized owner inbox is allowed. Credentials, OTP/reset
tokens and passwords stay in process memory. Provider DELIVERED is distinguished
from independent mailbox retrieval; this is not production signup acceptance.
"""
import argparse,json,os,re,secrets,time,uuid
from pathlib import Path
import httpx
from dotenv import dotenv_values


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--send-authorized-owner-mail',action='store_true');parser.add_argument('--output',required=True);args=parser.parse_args()
    if not args.send_authorized_owner_mail:raise RuntimeError('Explicit owner-mail acceptance required.')
    root=Path(__file__).resolve().parents[1];out=Path(args.output).resolve()
    if not out.is_relative_to(root/'data/artifacts/verification'):raise RuntimeError('Use the private verification directory.')
    os.umask(0o077);out.mkdir(parents=True,exist_ok=False,mode=0o700)
    values=dotenv_values(os.environ.get('PLANEBYTE_OPERATOR_ENV_FILE',str(root/'.env')),interpolate=False)
    if not values.get('RESEND_API_KEY'):raise RuntimeError('Use the existing server credential.')
    os.environ.update(APP_ENV='development',DATABASE_BACKEND='sqlite',DATABASE_URL='',DATABASE_PATH=str(out/'isolated.sqlite'),ALLOWED_USER_EMAILS='local-fixture-owner@example.test',RESEND_API_KEY=values['RESEND_API_KEY'],RESEND_FROM_EMAIL='PlaneByte <accounts@planebyte.com>',LEADENGINE_API_SIGNING_SECRET=secrets.token_urlsafe(48),HEYSOW_TERMS_VERSION='isolated-acceptance-unpublished',TRANSACTIONAL_MAIL_ENABLED='true',HEYSOW_ACCOUNTS_ENABLED='true',HEYSOW_ACCESS_PERIODS_ENABLED='true',HEYSOW_CUSTOMER_ACCESS_ENABLED='true',HEYSOW_PUBLIC_REGISTRATION_ENABLED='true',HEYSOW_WORKSPACE_MANAGEMENT_ENABLED='true',PAYU_BILLING_ENABLED='false',BILLING_ENABLED='false',LEAD_ENGINE_AVAILABLE='false',UPSTASH_REDIS_REST_URL='',UPSTASH_REDIS_REST_TOKEN='')
    from app.database.connection import db_session
    from app.database.migrations import run_migrations
    from app.accounts import service,models,sessions
    from app.notifications import transactional as mail
    from fastapi import HTTPException
    email='contact@planebyte.com';password=secrets.token_urlsafe(32)+'Aa9!'
    proof={'recipient':email,'sender':'accounts@planebyte.com','environment':'isolated local account with actual provider delivery','production_account_changed':False,'production_signup_enabled':False,'mailbox_contents_retrieved':False,'notifications':[]}
    def save():
        p=out/'result.json';p.write_text(json.dumps(proof,indent=2));p.chmod(0o600)
    with db_session() as c:run_migrations(c)
    def decrypt(key):
        with db_session() as c:row=c.execute('SELECT payload_encrypted FROM transactional_notifications WHERE id=?',(key,)).fetchone()
        return json.loads(mail.cipher().decrypt(row[0].encode()))
    def deliver(key):
        mail.deliver(key)
        with db_session() as c:row=c.execute('SELECT status,provider_message_id,purpose,error_code FROM transactional_notifications WHERE id=?',(key,)).fetchone()
        record={'notification_id':key,'provider_id':row['provider_message_id'],'purpose':row['purpose'],'outbox_status':row['status'],'provider_last_event':None};proof['notifications'].append(record);save()
        if row['status']!='ACCEPTED':raise RuntimeError('Normal transactional outbox was not accepted: '+str(row['error_code']))
        deadline=time.monotonic()+120
        with httpx.Client(timeout=15,headers={'Authorization':'Bearer '+values['RESEND_API_KEY']},follow_redirects=False) as client:
            while time.monotonic()<deadline:
                response=client.get('https://api.resend.com/emails/'+row['provider_message_id']);response.raise_for_status();data=response.json()
                if data.get('to')!=[email] or email not in data.get('to',[]):raise RuntimeError('Unexpected acceptance recipient.')
                record['provider_last_event']=data.get('last_event');save()
                if data.get('last_event') in ('delivered','opened','clicked'):
                    print(json.dumps({'purpose':row['purpose'],'provider_status':data['last_event'],'provider_id':row['provider_message_id']}),flush=True);return
                if data.get('last_event') in ('bounced','complained','failed','suppressed'):raise RuntimeError('Provider reported unsuccessful delivery: '+data['last_event'])
                time.sleep(3)
        raise RuntimeError('Provider did not confirm delivery within the bounded acceptance window.')
    receipt=service.begin_signup(models.Signup(email=email,password=password,name='Authorized owner acceptance',company_name='Isolated mail acceptance',terms_version='isolated-acceptance-unpublished',accepted_terms=True,request_id=uuid.uuid4()),'owner-controlled-mail-acceptance')
    code=re.search(r'code is (\d{6})',decrypt(receipt['notification_id'])['text']).group(1)
    bad=service.verify_email(models.Verify(challenge_id=receipt['challenge_id'],capability=receipt['capability'],code='invalid'),'owner-controlled-mail-acceptance');assert bad['verified'] is False
    try:service.resend_verification(models.Resend(challenge_id=receipt['challenge_id'],capability=receipt['capability'],request_id=uuid.uuid4()),'owner-controlled-mail-acceptance')
    except HTTPException as error:assert error.status_code==429
    else:raise RuntimeError('Resend cooldown did not reject immediate retry.')
    deliver(receipt['notification_id'])
    verified=service.verify_email(models.Verify(challenge_id=receipt['challenge_id'],capability=receipt['capability'],code=code),'owner-controlled-mail-acceptance');assert verified['verified']
    assert verified['trial']['limits']['ai_calls']==3 and verified['trial']['limits']['searches']==5
    proof['signup_verified']=True;proof['trial']=verified['trial'];proof['invalid_code_rejected']=True;proof['immediate_resend_rejected']=True;save()
    login=service.login(models.Login(email=email,password=password),'owner-controlled-mail-acceptance');assert login['authenticated']
    request=service.recover(models.Recovery(email=email,request_id=uuid.uuid4()),'owner-controlled-mail-acceptance');key=service.prepare_recovery(request['recovery_request_id'])
    token=decrypt(key)['text'].split('?token=')[1].split('\n')[0]
    deliver(key)
    replacement=secrets.token_urlsafe(32)+'Aa9!';assert service.reset_password(models.Reset(token=token,password=replacement),'owner-controlled-mail-acceptance')['reset']
    assert not service.reset_password(models.Reset(token=token,password=replacement),'owner-controlled-mail-acceptance')['reset']
    with db_session() as c:
        try:sessions.validate(c,email,login['session_token'])
        except HTTPException as error:assert error.status_code==401
        else:raise RuntimeError('Recovery did not revoke the old session.')
        notification=c.execute("SELECT id FROM transactional_notifications WHERE purpose='PASSWORD_CHANGED' ORDER BY created_at DESC LIMIT 1").fetchone()[0]
    assert not service.login(models.Login(email=email,password=password),'owner-controlled-mail-acceptance')['authenticated']
    assert service.login(models.Login(email=email,password=replacement),'owner-controlled-mail-acceptance')['authenticated']
    deliver(notification)
    proof.update(status='PASS',recovery_verified=True,old_session_revoked=True,reset_token_one_use=True,old_password_rejected=True,new_password_accepted=True);save()
    print(json.dumps({'status':'PASS','messages_delivered':len(proof['notifications']),'signup_verified':True,'recovery_verified':True,'production_account_changed':False,'mailbox_contents_retrieved':False}),flush=True)

if __name__=='__main__':
    try:main()
    except Exception as error:
        print(json.dumps({'status':'FAILED','error_type':type(error).__name__,'detail':str(error) if isinstance(error,RuntimeError) else 'Private acceptance metadata retained; secrets withheld.'}));raise SystemExit(1)
