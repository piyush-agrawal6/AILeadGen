"""B04 acceptance: synthetic Google/Gmail only, no credentials or real deliveries."""
import asyncio,base64,json,uuid
from datetime import datetime,timezone
from email import policy
from email.parser import BytesParser
from urllib.parse import parse_qs,urlsplit
from unittest.mock import AsyncMock,Mock
import pytest
from fastapi import HTTPException
from app.config.settings import get_settings
from app.platform.context import workspace_scope,current
from app.platform.memberships import change_role
from app.integrations import gmail,service as connections
from app.integrations.crypto import seal,open_envelope
from app.acquisition import sheets
from app.mail import service as mail,customer,bounces
from test_customer_integrations import workspace,OWNER
ORIGINAL_TOKEN_REQUEST=sheets.token_request

def freeze_customer_clock(monkeypatch,at=None):
    """Exercise worker outcomes during explicit business time, not wall time."""
    stamp=at or datetime(2026,11,16,12,tzinfo=timezone.utc)
    class Clock(datetime):
        @classmethod
        def now(cls,tz=None):return stamp.astimezone(tz) if tz else stamp.replace(tzinfo=None)
    monkeypatch.setattr(customer,'datetime',Clock)

@pytest.fixture
def mailbox(workspace,monkeypatch):
    c,first,second,path=workspace;s=get_settings();posts=[]
    for key,value in {'heysow_customer_gmail_enabled':True,'heysow_customer_gmail_redirect_uri':'https://example.test/settings/integrations/gmail-callback',
        'heysow_customer_mail_sending_enabled':True,'heysow_customer_mail_mode':'test','heysow_customer_mail_live_approved':False,
        'heysow_customer_mail_test_recipient':'sandbox@example.com','heysow_customer_mail_schedules_enabled':False}.items():monkeypatch.setattr(s,key,value)
    tokens={'access_token':'synthetic-gmail-access','refresh_token':'synthetic-gmail-refresh','expires_in':3600,'scope':gmail.SCOPE}
    monkeypatch.setattr(sheets,'token_request',AsyncMock(return_value=tokens))
    async def http(method,url,token,**kwargs):
        assert token=='synthetic-gmail-access'
        if url.endswith('/userinfo'):return {'email':current().actor,'email_verified':True,'sub':'subject-'+current().actor}
        if url.endswith('/profile'):return {'emailAddress':current().actor,'historyId':'10'}
        if method=='POST' and url.endswith('/messages/send'):
            posts.append(kwargs['payload']);return {'id':'delivery-'+str(len(posts))}
        if url.endswith('/messages'):return {'messages':[]}
        if url.endswith('/history'):return {'history':[],'historyId':'10'}
        raise AssertionError('Unexpected synthetic provider operation')
    monkeypatch.setattr(gmail,'request_json',http)
    monkeypatch.setattr(mail,'provider',Mock(side_effect=AssertionError('Internal transport must never serve a customer')))
    yield c,first,second,path,posts

def connect(c):
    result=connections.authorize(c,spec=gmail.spec());query=parse_qs(urlsplit(result['authorization_url']).query);c.commit()
    connection=asyncio.run(connections.connect(c,query['state'][0],'synthetic-google-code',spec=gmail.spec()));c.commit()
    return connections.owned(c,connection['id'],spec=gmail.spec()),query

def seed(c,org,monkeypatch):
    import campaign_fixtures as fixtures
    monkeypatch.setattr(fixtures,'PLANEBYTE_ORGANIZATION_ID',org)
    campaign=fixtures.campaign(c);business,pid=fixtures.lead(c,campaign)
    c.commit();return campaign,business,pid

def approve(c,maximum=50):
    p=customer.policy(c)
    result=customer.save_policy(c,customer.PolicyUpdate(revision=p['revision'],max_hour=min(10,maximum),max_day=maximum,confirmation='APPROVE_SENDING'));c.commit();return result

def payload(c,pid,row,campaign=None):
    body={'account_id':row['account_id'],'campaign_id':campaign,'to_address':'public@hotel0.example','subject':'Company conversation',
        'body_text':'Hello team, a reviewed conversation about your company.','track_opens':False,'track_clicks':False,'preview_nonce':str(uuid.uuid4()),
        'idempotency_key':str(uuid.uuid4()),'confirmation':'SEND','message_type':'FIRST_CONTACT'}
    body['preview_token']=mail.preview(c,pid,current().actor,body,allow_disabled=True)['preview_token'];c.commit();return body

def test_disabled_customer_gmail_fails_before_database_or_transport(monkeypatch):
    monkeypatch.setattr(get_settings(),'heysow_customer_gmail_enabled',False);c=Mock()
    for action in (lambda:gmail.listing(c),lambda:connections.authorize(c,spec=gmail.spec()),lambda:customer.sync_owned_account('foreign')):
        with pytest.raises(HTTPException) as blocked:action()
        assert blocked.value.status_code==503
    c.execute.assert_not_called()

def test_connection_scope_encryption_health_and_workspace_denial(mailbox):
    c,first,second,path,posts=mailbox
    with workspace_scope(c,OWNER,first):
        row,query=connect(c)
        assert set(query['scope'][0].split())==set(gmail.SCOPE.split()) and query['code_challenge_method']==['S256']
        assert 'synthetic' not in str(row) and query['state'][0] not in str(c.execute('SELECT * FROM customer_gmail_oauth_states').fetchall())
        assert row['email_address']==OWNER and row['owner_user_id']==OWNER
        assert asyncio.run(gmail.health(c,row['id']))['sending']=='READY';c.commit()
        with pytest.raises(HTTPException):asyncio.run(connections.connect(c,query['state'][0],'synthetic-google-code',spec=gmail.spec()))
    with workspace_scope(c,OWNER,second):
        with pytest.raises(HTTPException) as denied:asyncio.run(gmail.health(c,row['id']))
        assert denied.value.status_code==404
        other,_=connect(c)
        assert other['account_id']!=row['account_id']
        c.execute('UPDATE customer_gmail_connections SET credentials_ciphertext=? WHERE id=?',(row['credentials_ciphertext'],other['id']));c.commit()
        with pytest.raises(HTTPException):asyncio.run(connections.access_token(c,other['id'],spec=gmail.spec()))
    assert posts==[] and c.execute('SELECT COUNT(*) FROM organization_integrations').fetchone()[0]==0
    assert c.execute("SELECT COUNT(*) FROM email_accounts WHERE id='gmail-primary'").fetchone()[0]==0

@pytest.mark.parametrize('failure',['foreign_identity','unverified','broad_scope','expired','other_member'])
def test_oauth_rejects_foreign_identity_permissions_and_stale_authority(mailbox,monkeypatch,failure):
    c,first,second,path,posts=mailbox
    with workspace_scope(c,OWNER,first):
        result=connections.authorize(c,spec=gmail.spec());state=parse_qs(urlsplit(result['authorization_url']).query)['state'][0]
        if failure=='expired':c.execute("UPDATE customer_gmail_oauth_states SET expires_at='2000-01-01T00:00:00+00:00'")
        if failure=='broad_scope':monkeypatch.setattr(sheets,'token_request',AsyncMock(return_value={'access_token':'synthetic-gmail-access','refresh_token':'synthetic-gmail-refresh','scope':gmail.SCOPE+' https://mail.google.com/'}))
        if failure in ('foreign_identity','unverified'):
            original=gmail.request_json
            async def rejected(method,url,token,**kwargs):
                if url.endswith('/userinfo'):return {'email':OWNER if failure=='unverified' else 'other@example.com','email_verified':failure!='unverified','sub':'foreign-subject'}
                return await original(method,url,token,**kwargs)
            monkeypatch.setattr(gmail,'request_json',rejected)
        if failure=='other_member':c.execute("UPDATE organization_memberships SET role='VIEWER' WHERE organization_id=? AND user_id=?",(first,OWNER))
        c.commit()
        with pytest.raises(HTTPException):asyncio.run(connections.connect(c,state,'synthetic-code',spec=gmail.spec()))
        assert c.execute('SELECT COUNT(*) FROM email_accounts').fetchone()[0]==0
    assert posts==[]

def test_disconnect_cannot_be_resurrected_and_reconnect_removes_approval(mailbox,monkeypatch):
    c,first,second,path,posts=mailbox
    with workspace_scope(c,OWNER,first):
        row,_=connect(c);approve(c)
        result=connections.authorize(c,spec=gmail.spec());state=parse_qs(urlsplit(result['authorization_url']).query)['state'][0];c.commit()
        original=sheets.token_request
        async def canceled(body):
            gmail.disconnect(c,row['id']);c.commit();return await original(body)
        monkeypatch.setattr(sheets,'token_request',canceled)
        with pytest.raises(HTTPException):asyncio.run(connections.connect(c,state,'synthetic-code',spec=gmail.spec()))
        assert connections.owned(c,row['id'],spec=gmail.spec())['credentials_ciphertext'] is None
        assert not customer.policy(c)['sending_approved']
        monkeypatch.setattr(sheets,'token_request',original);new,_=connect(c)
        assert new['account_id']==row['account_id'] and new['revision']>row['revision']
        assert not customer.policy(c)['sending_approved'] and posts==[]

def test_refresh_single_flight_keeps_rotated_tokens_private(mailbox,monkeypatch):
    from app.database.connection import get_connection
    c,first,second,path,posts=mailbox
    with workspace_scope(c,OWNER,first):
        row,_=connect(c);value=open_envelope(row['credentials_ciphertext'],**connections.context(row,'CREDENTIALS'));value['expires_at']='2000-01-01T00:00:00+00:00'
        c.execute('UPDATE customer_gmail_connections SET credentials_ciphertext=? WHERE id=?',(seal(value,**connections.context(row,'CREDENTIALS')),row['id']));c.commit();calls=[]
        async def refresh(body):
            calls.append(body)
            other=get_connection(path)
            try:
                with workspace_scope(other,OWNER,first):
                    with pytest.raises(HTTPException) as busy:await connections.access_token(other,row['id'],spec=gmail.spec())
                    assert busy.value.status_code==429
            finally:other.close()
            return {'access_token':'rotated-access','refresh_token':'rotated-refresh','scope':gmail.SCOPE,'expires_in':3600}
        monkeypatch.setattr(sheets,'token_request',refresh)
        assert asyncio.run(connections.access_token(c,row['id'],spec=gmail.spec()))[0]=='rotated-access'
        stored=connections.owned(c,row['id'],spec=gmail.spec())
        assert open_envelope(stored['credentials_ciphertext'],**connections.context(stored,'CREDENTIALS'))['refresh_token']=='rotated-refresh'
        assert len(calls)==1 and 'rotated' not in str(gmail.listing(c))

def test_reviewed_send_uses_owned_gmail_limits_and_durable_idempotency(mailbox,monkeypatch):
    c,first,second,path,posts=mailbox
    with workspace_scope(c,OWNER,first):
        row,_=connect(c);cid,b,pid=seed(c,first,monkeypatch)
        body=payload(c,pid,row)
        with pytest.raises(HTTPException) as unapproved:mail.send(c,pid,OWNER,body)
        assert unapproved.value.status_code==503 and posts==[]
        approve(c);body=payload(c,pid,row)
        with pytest.raises(HTTPException):mail.send(c,pid,OWNER,{**body,'body_text':'Changed after review'})
        sent=mail.send(c,pid,OWNER,body)
        assert sent['status']=='SENT' and len(posts)==1
        mime=BytesParser(policy=policy.default).parsebytes(base64.urlsafe_b64decode(posts[0]['raw']))
        assert OWNER in str(mime['From']) and 'PlaneByte' not in str(mime['From']) and str(mime['To'])=='sandbox@example.com'
        persisted=c.execute('SELECT * FROM email_messages WHERE id=?',(sent['id'],)).fetchone()
        assert persisted['organization_id']==first and persisted['account_id']==row['account_id'] and persisted['provider_delivery_id']=='delivery-1'
        assert mail.send(c,pid,OWNER,body)['duplicate_prevented'] and len(posts)==1
        c.execute("UPDATE customer_mail_policies SET next_send_at=NULL WHERE organization_id=?",(first,));c.commit()
        approve(c,1);fresh=payload(c,pid,row)
        with pytest.raises(HTTPException) as limit:mail.send(c,pid,OWNER,fresh)
        assert limit.value.status_code==429 and len(posts)==1
        c.rollback()
    with workspace_scope(c,OWNER,second):
        with pytest.raises(HTTPException):mail.send(c,pid,OWNER,body)
    assert len(posts)==1

def test_campaign_route_and_preview_are_bound_to_mailbox_revision(mailbox,monkeypatch):
    c,first,second,path,posts=mailbox
    with workspace_scope(c,OWNER,first):
        row,_=connect(c);cid,b,pid=seed(c,first,monkeypatch);approve(c)
        with pytest.raises(HTTPException):payload(c,pid,row,cid)
        customer.route_campaign(c,cid,row['account_id']);c.commit();body=payload(c,pid,row,cid)
        connect(c)
        approve(c)
        with pytest.raises(HTTPException) as stale:mail.send(c,pid,OWNER,body)
        assert stale.value.status_code==409
        change_role(c,OWNER,'viewer@example.com','VIEWER');c.commit()
    with workspace_scope(c,'viewer@example.com',first):
        assert not gmail.listing(c)['can_connect']
        with pytest.raises(HTTPException):customer.owned_account(c,'viewer@example.com',row['account_id'])
    with workspace_scope(c,OWNER,second):
        with pytest.raises(HTTPException):customer.route_campaign(c,cid,row['account_id'])
    assert posts==[]

def test_uncertain_send_is_not_retried_and_provider_errors_are_redacted(mailbox,monkeypatch):
    c,first,second,path,posts=mailbox
    with workspace_scope(c,OWNER,first):
        row,_=connect(c);cid,b,pid=seed(c,first,monkeypatch);approve(c);body=payload(c,pid,row)
        original=gmail.request_json;calls=[]
        async def uncertain(method,url,token,**kwargs):
            if method=='POST':calls.append(url);raise TimeoutError('private-provider-message-must-not-leak')
            return await original(method,url,token,**kwargs)
        monkeypatch.setattr(gmail,'request_json',uncertain)
        result=mail.send(c,pid,OWNER,body)
        assert result['status']=='SENDING' and 'private-provider' not in str(result)
        assert mail.send(c,pid,OWNER,body)['duplicate_prevented'] and len(calls)==1

def test_owned_reply_sync_is_deduplicated_and_preserves_foreign_workspace(mailbox,monkeypatch):
    c,first,second,path,posts=mailbox
    with workspace_scope(c,OWNER,first):
        row,_=connect(c);cid,b,pid=seed(c,first,monkeypatch);approve(c);sent=mail.send(c,pid,OWNER,payload(c,pid,row))
        incoming={'message_id':'<reply@example.com>','from':'sandbox@example.com','to':OWNER,'subject':'Re: conversation','body_text':'Thanks',
            'references':[sent['provider_message_id']],'in_reply_to':sent['provider_message_id'],'date':datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000'),
            'authentication':'mx.google.com; dkim=pass header.d=example.com'}
        monkeypatch.setattr(gmail,'sync_messages',AsyncMock(return_value=([incoming],{'history_id':'11'})))
        assert customer.sync_mailbox(row['account_id'])['received']==1
        assert customer.sync_mailbox(row['account_id'])['received']==0
        assert c.execute("SELECT COUNT(*) FROM email_messages WHERE direction='INBOUND' AND organization_id=?",(first,)).fetchone()[0]==1
        assert c.execute('SELECT unread_replies FROM prospect_sales WHERE prospect_id=?',(pid,)).fetchone()[0]==1
    with workspace_scope(c,OWNER,second):
        other,_=connect(c)
        assert customer.sync_mailbox(other['account_id'])['received']==0
        assert c.execute("SELECT COUNT(*) FROM email_messages WHERE direction='INBOUND' AND organization_id=?",(second,)).fetchone()[0]==0

def test_api_is_gated_and_never_accepts_client_workspace_or_returns_tokens(mailbox,monkeypatch):
    from fastapi.testclient import TestClient
    from app.api.server import app
    from app.platform.workspaces import select_workspace
    c,first,second,path,posts=mailbox;select_workspace(c,OWNER,first);c.commit()
    with TestClient(app) as client:
        result=client.post('/api/email/gmail/authorize');assert result.status_code==200,result.text
        assert result.headers['cache-control']=='private, no-store'
        state=parse_qs(urlsplit(result.json()['authorization_url']).query)['state'][0]
        assert client.post('/api/email/gmail/connect',json={'state':state,'code':'synthetic-code','organization_id':second}).status_code==422
        connected=client.post('/api/email/gmail/connect',json={'state':state,'code':'synthetic-code'});assert connected.status_code==200,connected.text
        assert not any(marker in connected.text for marker in ('synthetic-gmail','ciphertext','google_subject'))
        assert client.get('/api/email/account').json()['email_address']==OWNER
        assert client.put('/api/email/gmail/policy',json={'revision':0,'max_hour':5,'max_day':50,'confirmation':'APPROVE_SENDING'}).status_code==403
        monkeypatch.setattr(get_settings(),'heysow_customer_gmail_enabled',False)
        assert client.post('/api/email/gmail/authorize').status_code==503
        assert client.get('/api/email/gmail').status_code==503
    assert posts==[]

def test_customer_worker_routes_owned_run_and_never_retries_uncertain_delivery(mailbox,monkeypatch):
    from app.api.routes.workflows import Run
    from app.workflows import service as workflows
    from tests.workspace_fixtures import workspace_template
    c,first,second,path,posts=mailbox
    freeze_customer_clock(monkeypatch)
    with workspace_scope(c,OWNER,first):
        row,_=connect(c);cid,b,pid=seed(c,first,monkeypatch);approve(c)
        customer.route_campaign(c,cid,row['account_id']);c.execute('UPDATE automation_controls SET email_paused=0');c.commit()
        options=Run(kind='OUTREACH',campaign_id=cid,account_id=row['account_id'],template_id=workspace_template(c),window_start='00:00',window_end='23:59',recipient_timezone=False).model_dump()
        run=workflows.create(c,options,OWNER);workflows.prepare(c,run['id']);c.commit()
        item=c.execute('SELECT * FROM outreach_run_items WHERE run_id=?',(run['id'],)).fetchone()
        assert item['status']=='READY',item['error']
        assert json.loads(item['payload_json'])['account_id']==row['account_id']
        workflows.start(c,run['id']);c.commit()
        assert customer.outreach_tick(c,run['id'])['status']=='SENT'
        assert customer.outreach_tick(c,run['id'])['status']=='EMPTY'
        assert len(posts)==1 and c.execute('SELECT COUNT(*) FROM automation_email_queue').fetchone()[0]==0
        customer.advance_run(c,workflows.row(c,run['id']))
        assert workflows.row(c,run['id'])['status']=='COMPLETED'
    with workspace_scope(c,OWNER,second):
        assert customer.outreach_tick(c,run['id'])['status']=='NO_EXPLICIT_RUN'
    assert len(posts)==1

def test_customer_preparation_never_auto_approves_manual_outreach_or_resumes_paused_runs(mailbox,monkeypatch):
    from app.api.routes.workflows import Run
    from app.workflows import service as workflows
    from tests.workspace_fixtures import workspace_template
    c,first,second,path,posts=mailbox
    with workspace_scope(c,OWNER,first):
        row,_=connect(c);cid,b,pid=seed(c,first,monkeypatch);approve(c);customer.route_campaign(c,cid,row['account_id'])
        options=Run(kind='OUTREACH',campaign_id=cid,account_id=row['account_id'],template_id=workspace_template(c)).model_dump()
        run=workflows.create(c,options,OWNER);c.execute("UPDATE workflow_runs SET status='PREPARING' WHERE id=?",(run['id'],));c.commit()
        customer.advance_run(c,{'id':run['id'],'created_by':'forged@example.com'})
        assert workflows.row(c,run['id'])['status']=='DRAFT'
        c.execute("UPDATE workflow_runs SET status='PAUSED' WHERE id=?",(run['id'],));c.commit()
        customer.advance_run(c,{'id':run['id']})
        assert workflows.row(c,run['id'])['status']=='PAUSED' and posts==[]

def test_bounces_and_tracking_preferences_are_independent_for_the_same_recipient(mailbox,monkeypatch):
    from app.mail import tracking
    from app.api.routes.mail import TrackingPreferences,update_tracking
    c,first,second,path,posts=mailbox
    for org in (first,second):
        with workspace_scope(c,OWNER,org):
            row,_=connect(c);cid,b,pid=seed(c,org,monkeypatch);approve(c);sent=mail.send(c,pid,OWNER,payload(c,pid,row))
            # Synthetic stored production-shaped delivery; no transport sends to this address.
            c.execute("UPDATE email_messages SET test_mode=0,to_address='public@hotel0.example' WHERE id=?",(sent['id'],))
            dsn={'kind':'dsn','message_id':'<dsn-'+org+'@example.com>','references':[sent['provider_message_id']],
                'recipients':[{'recipient':'public@hotel0.example','action':'failed','status':'5.1.1'}],
                'from':'postmaster@example.com','to':OWNER,'date':datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000'),
                'authentication':'mx.google.com; dkim=pass header.d=example.com'}
            assert bounces.process(c,dsn,account_id=row['account_id'])==1
            assert bounces.process(c,dsn,account_id=row['account_id'])==0
            assert 'public@hotel0.example' not in mail.recipients(c,pid)
            if org==first:update_tracking(TrackingPreferences(track_opens=True,track_clicks=False),c)
            else:assert not tracking.preferences(c)['track_opens']
            c.commit()
    assert c.execute('SELECT COUNT(*) FROM customer_mail_suppressions').fetchone()[0]==2
    assert c.execute('SELECT COUNT(*) FROM email_address_suppressions').fetchone()[0]==0

def test_new_customer_identity_and_admin_owner_cannot_be_taken_over(mailbox,monkeypatch):
    from app.api.organization import create_organization
    c,first,second,path,posts=mailbox;other_actor='other-customer@example.com'
    admit_customer(c,other_actor,monkeypatch)
    other=create_organization(c,other_actor,'Distinct customer')['organization_id'];c.commit()
    with workspace_scope(c,OWNER,first):row,_=connect(c)
    with workspace_scope(c,other_actor,other):
        own,_=connect(c)
        assert own['email_address']==other_actor and own['account_id']!=row['account_id']
        with pytest.raises(HTTPException):customer.owned_account(c,other_actor,row['account_id'])
    admit_customer(c,'administrator@example.com',monkeypatch)
    with workspace_scope(c,OWNER,first):
        change_role(c,OWNER,'administrator@example.com','ADMIN');c.commit()
    with workspace_scope(c,'administrator@example.com',first):
        assert not gmail.listing(c)['can_connect']
        with pytest.raises(HTTPException):connections.authorize(c,spec=gmail.spec())
    assert posts==[]

def admit_customer(c,actor,monkeypatch):
    from app.platform import admission
    from test_account_admission import claim
    s=get_settings()
    for key,value in {'heysow_customer_access_enabled':True,'heysow_public_registration_enabled':True,
        'heysow_terms_version':'synthetic-review-version','heysow_google_admission_client_id':'synthetic-google-client'}.items():monkeypatch.setattr(s,key,value)
    body=claim(email=actor,subject='subject-'+actor)
    admission.admit(c,body,actor=actor,broker_verified=True);c.commit()
    monkeypatch.setattr(s,'heysow_public_registration_enabled',False)

def test_active_admitted_admin_is_preserved_but_removed_terms_disabled_or_suspended_access_fails_closed(mailbox,monkeypatch):
    c,first,second,path,posts=mailbox;actor='admitted-admin@example.com'
    admit_customer(c,actor,monkeypatch)
    with workspace_scope(c,OWNER,first):change_role(c,OWNER,actor,'ADMIN');c.commit()
    with workspace_scope(c,actor,first):
        assert connections.manager(c)==first
        # Auth remains closed to new users while this existing admitted admin works.
        assert not get_settings().heysow_public_registration_enabled
        c.execute("UPDATE account_admissions SET status='SUSPENDED' WHERE user_id=?",(actor,));c.commit()
        with pytest.raises(HTTPException) as suspended:connections.manager(c)
        assert suspended.value.status_code==403
        c.execute("UPDATE account_admissions SET status='ACTIVE',terms_version='old-synthetic-version' WHERE user_id=?",(actor,));c.commit()
        with pytest.raises(HTTPException):connections.manager(c)
        c.execute('UPDATE account_admissions SET terms_version=? WHERE user_id=?',(get_settings().heysow_terms_version,actor));c.commit()
        monkeypatch.setattr(get_settings(),'heysow_customer_access_enabled',False)
        with pytest.raises(HTTPException):connections.manager(c)
        monkeypatch.setattr(get_settings(),'heysow_customer_access_enabled',True)
        assert connections.manager(c)==first
        c.execute("UPDATE organization_memberships SET status='REVOKED' WHERE user_id=? AND organization_id=?",(actor,first));c.commit()
        with pytest.raises(HTTPException):connections.manager(c)
    assert posts==[]

def test_scoped_sync_worker_cannot_rebind_to_another_customer(mailbox):
    c,first,second,path,posts=mailbox
    with workspace_scope(c,OWNER,second):foreign,_=connect(c)
    with workspace_scope(c,OWNER,first):
        with pytest.raises(HTTPException) as denied:customer.sync_owned_account(foreign['account_id'])
        assert denied.value.status_code==404
    assert posts==[]

def test_retry_resumes_saved_cursor_and_stops_after_three_transient_failures(mailbox,monkeypatch):
    c,first,second,path,posts=mailbox
    with workspace_scope(c,OWNER,first):
        row,_=connect(c)
        c.execute("INSERT INTO customer_gmail_sync(connection_id,organization_id,cursor_json,attempts) VALUES(?,?,?,3)",(row['id'],first,json.dumps({'history_id':'15'})));c.commit()
        provider=AsyncMock(return_value=([],{'history_id':'16'}));monkeypatch.setattr(gmail,'sync_messages',provider)
        assert customer.sync_mailbox(row['account_id'])['status']=='RETRY_DEFERRED';provider.assert_not_called()
        assert customer.retry_sync(c,row['id'],row['revision'])['status']=='SYNCED'
        assert provider.call_args.args[2]=={'history_id':'15'}
        provider.reset_mock();provider.side_effect=TimeoutError('private-sync-error')
        for attempt in range(3):
            with pytest.raises(HTTPException):customer.sync_mailbox(row['account_id'])
            c.execute('UPDATE customer_gmail_sync SET next_attempt_at=NULL WHERE connection_id=?',(row['id'],));c.commit()
        assert customer.sync_mailbox(row['account_id'])['status']=='RETRY_DEFERRED'
        state=c.execute('SELECT * FROM customer_gmail_sync WHERE connection_id=?',(row['id'],)).fetchone()
        assert state['attempts']==3 and json.loads(state['cursor_json'])=={'history_id':'16'}
        assert provider.call_count==3 and 'private-sync-error' not in str(dict(state))

def test_disconnect_during_reply_fetch_cannot_persist_inbound_or_revive_cursor(mailbox,monkeypatch):
    c,first,second,path,posts=mailbox
    with workspace_scope(c,OWNER,first):
        row,_=connect(c)
        async def canceled(*args,**kwargs):
            gmail.disconnect(c,row['id']);c.commit()
            return [],{'history_id':'999'}
        monkeypatch.setattr(gmail,'sync_messages',canceled)
        with pytest.raises(HTTPException):customer.sync_mailbox(row['account_id'])
        state=c.execute('SELECT * FROM customer_gmail_sync WHERE connection_id=?',(row['id'],)).fetchone()
        assert json.loads(state['cursor_json'])=={}
        assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0

def test_naive_token_expiry_is_rejected_as_reconnect_not_a_type_error(mailbox):
    c,first,second,path,posts=mailbox
    with workspace_scope(c,OWNER,first):
        row,_=connect(c);value=open_envelope(row['credentials_ciphertext'],**connections.context(row,'CREDENTIALS'))
        value['expires_at']='2030-01-01T00:00:00'
        c.execute('UPDATE customer_gmail_connections SET credentials_ciphertext=? WHERE id=?',(seal(value,**connections.context(row,'CREDENTIALS')),row['id']));c.commit()
        with pytest.raises(HTTPException) as invalid:asyncio.run(connections.access_token(c,row['id'],spec=gmail.spec()))
        assert invalid.value.status_code==409 and posts==[]

def test_revoked_google_grant_marks_refresh_reauthentication_without_exposing_error_body(mailbox,monkeypatch):
    import httpx
    c,first,second,path,posts=mailbox
    with workspace_scope(c,OWNER,first):
        row,_=connect(c);value=open_envelope(row['credentials_ciphertext'],**connections.context(row,'CREDENTIALS'))
        value['expires_at']='2000-01-01T00:00:00+00:00'
        c.execute('UPDATE customer_gmail_connections SET credentials_ciphertext=? WHERE id=?',(seal(value,**connections.context(row,'CREDENTIALS')),row['id']));c.commit()
        # Exercise the original bounded token HTTP function through MockTransport.
        real_client=httpx.AsyncClient
        def client(**kwargs):return real_client(**kwargs,transport=httpx.MockTransport(lambda request:httpx.Response(400,json={'error':'invalid_grant','error_description':'private-token-error'})))
        monkeypatch.setattr(httpx,'AsyncClient',client)
        monkeypatch.setattr(sheets,'token_request',ORIGINAL_TOKEN_REQUEST)
        monkeypatch.setenv('ACQUISITION_TEST_ALLOW_PROVIDER_NETWORK','1')
        with pytest.raises(HTTPException) as denied:asyncio.run(connections.access_token(c,row['id'],spec=gmail.spec()))
        current_row=connections.owned(c,row['id'],spec=gmail.spec())
        assert current_row['status']=='REAUTH_REQUIRED' and current_row['credentials_ciphertext'] is None
        assert 'private-token-error' not in str(denied.value.detail) and posts==[]

def test_gmail_history_large_records_are_drained_without_cursor_loss(mailbox,monkeypatch):
    c,first,second,path,posts=mailbox;calls=[]
    with workspace_scope(c,OWNER,first):
        async def api(method,path,token,**kwargs):
            calls.append(path)
            if path=='profile':return {'emailAddress':OWNER,'historyId':'50'}
            if path=='history':return {'history':[{'messagesAdded':[{'message':{'id':'id'+str(i)}} for i in range(35)]}],'historyId':'55'}
            return {'raw':base64.urlsafe_b64encode(b'Message-ID: <not-a-reply@example.com>\r\n\r\nUnrelated email').decode()}
        monkeypatch.setattr(gmail,'api',api)
        _,cursor=asyncio.run(gmail.sync_messages('synthetic-token',set(),{'history_id':'10'}))
        assert cursor['history_id']=='10' and len(cursor['pending_ids'])==10
        assert len([path for path in calls if path.startswith('messages/')])==25
        _,final=asyncio.run(gmail.sync_messages('synthetic-token',set(),cursor))
        assert final['history_id']=='50' and final['pending_ids']==[]
        assert calls.count('history')==1 and len([path for path in calls if path.startswith('messages/')])==35
