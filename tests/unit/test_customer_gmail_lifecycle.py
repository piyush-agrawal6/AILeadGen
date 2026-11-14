"""B04 closure: owned SQLite, synthetic Gmail only, no SMTP/network delivery."""
import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
from test_customer_gmail import mailbox, connect, approve, seed, payload, OWNER, freeze_customer_clock
from test_customer_integrations import workspace
from app.platform.context import workspace_scope
from app.integrations import gmail, service as connections
from app.mail import customer, service as mail, bounces
from app.config.settings import get_settings


@pytest.mark.parametrize('operation', ['health', 'send', 'sync', 'refresh'])
def test_provider_revocation_removes_all_local_mail_authority(mailbox, monkeypatch, operation):
    c, org, other, path, posts = mailbox
    with workspace_scope(c, OWNER, org):
        row, _ = connect(c); approve(c)
        if operation == 'send':
            _, _, pid = seed(c, org, monkeypatch)
            body = payload(c, pid, row)
        if operation == 'refresh':
            from app.integrations.crypto import open_envelope,seal
            value=open_envelope(row['credentials_ciphertext'],**connections.context(row,'CREDENTIALS'))
            value['expires_at']='2000-01-01T00:00:00+00:00'
            c.execute('UPDATE customer_gmail_connections SET credentials_ciphertext=? WHERE id=?',(seal(value,**connections.context(row,'CREDENTIALS')),row['id']));c.commit()
            monkeypatch.setattr('app.acquisition.sheets.token_request',AsyncMock(return_value={'error':'invalid_grant'}))
        monkeypatch.setattr(gmail, 'api', AsyncMock(side_effect=gmail.GmailRejected(401)))
        if operation == 'send':
            assert mail.send(c, pid, OWNER, body)['status'] == 'FAILED'
        else:
            with pytest.raises(HTTPException):
                if operation == 'health': asyncio.run(gmail.health(c, row['id']))
                elif operation == 'refresh':asyncio.run(connections.access_token(c,row['id'],spec=gmail.spec()))
                else: customer.sync_mailbox(row['account_id'])
        latest = connections.owned(c, row['id'], spec=gmail.spec())
        assert latest['status'] == 'REAUTH_REQUIRED' and latest['credentials_ciphertext'] is None
        assert not customer.policy(c)['sending_approved']
        assert customer.owned_account(c, OWNER, row['account_id'])['status'] == 'DISCONNECTED'
        assert posts == []


def test_changed_provider_identity_requires_reauthentication(mailbox, monkeypatch):
    c, org, _, _, posts = mailbox
    with workspace_scope(c, OWNER, org):
        row, _ = connect(c); approve(c)
        monkeypatch.setattr(gmail, 'api', AsyncMock(return_value={'emailAddress':'foreign@example.test'}))
        with pytest.raises(HTTPException): asyncio.run(gmail.health(c, row['id']))
        assert connections.owned(c, row['id'], spec=gmail.spec())['status'] == 'REAUTH_REQUIRED'
        assert not customer.policy(c)['sending_approved'] and posts == []


def test_expired_sync_lease_rejects_completed_response_and_preserves_cursor(mailbox, monkeypatch):
    from app.database.connection import get_connection
    c, org, _, path, posts = mailbox
    with workspace_scope(c, OWNER, org):
        row, _ = connect(c)
        async def expired(*args, **kwargs):
            second = get_connection(path)
            second.execute("UPDATE customer_gmail_sync SET lease_until='2000-01-01T00:00:00+00:00' WHERE connection_id=?", (row['id'],))
            second.commit(); second.close()
            return [], {'history_id':'999'}
        monkeypatch.setattr(gmail, 'sync_messages', expired)
        with pytest.raises(HTTPException): customer.sync_mailbox(row['account_id'])
        state = c.execute('SELECT * FROM customer_gmail_sync WHERE connection_id=?', (row['id'],)).fetchone()
        assert json.loads(state['cursor_json']) == {} and state['last_success_at'] is None
        assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0] == 0 and posts == []


def test_expired_history_requires_explicit_owned_restart_not_retry(mailbox, monkeypatch):
    c, org, other, path, posts = mailbox
    with workspace_scope(c, OWNER, org):
        row, _ = connect(c)
        c.execute('INSERT INTO customer_gmail_sync(connection_id,organization_id,cursor_json) VALUES(?,?,?)', (row['id'], org, json.dumps({'history_id':'10'}))); c.commit()
        async def api(method, path, token, **kwargs):
            if path == 'profile': return {'emailAddress':OWNER, 'historyId':'20'}
            if path == 'history': raise gmail.GmailRejected(404)
            if path == 'messages': return {'messages':[]}
            raise AssertionError('Unexpected mocked request')
        monkeypatch.setattr(gmail, 'api', api)
        with pytest.raises(HTTPException): customer.sync_mailbox(row['account_id'])
        assert gmail.listing(c)['items'][0]['sync']['last_error_code'] == 'GMAIL_HISTORY_EXPIRED'
        with pytest.raises(HTTPException): customer.retry_sync(c, row['id'], row['revision'])
        assert json.loads(c.execute('SELECT cursor_json FROM customer_gmail_sync WHERE connection_id=?', (row['id'],)).fetchone()[0]) == {'history_id':'10'}
        with pytest.raises(HTTPException): customer.restart_sync(c, row['id'], row['revision'] + 1)
    with workspace_scope(c, OWNER, other):
        with pytest.raises(HTTPException): customer.restart_sync(c, row['id'], row['revision'])
    with workspace_scope(c, OWNER, org):
        assert customer.restart_sync(c, row['id'], row['revision'])['status'] == 'SYNCED'
        assert json.loads(c.execute('SELECT cursor_json FROM customer_gmail_sync WHERE connection_id=?', (row['id'],)).fetchone()[0])['history_id'] == '20'
    assert posts == []


def prepared(c, org, row, monkeypatch):
    from app.api.routes.workflows import Run
    from app.workflows import service as workflows
    from tests.workspace_fixtures import workspace_template
    cid, _, _ = seed(c, org, monkeypatch)
    customer.route_campaign(c, cid, row['account_id'])
    c.execute('UPDATE automation_controls SET email_paused=0'); c.commit()
    options = Run(kind='OUTREACH', campaign_id=cid, account_id=row['account_id'], template_id=workspace_template(c), window_start='00:00', window_end='23:59', recipient_timezone=False).model_dump()
    run = workflows.create(c, options, OWNER); workflows.prepare(c, run['id']); workflows.start(c, run['id']); c.commit()
    return run


def test_worker_pre_reservation_throttle_retries_only_three_times(mailbox, monkeypatch):
    c, org, _, _, posts = mailbox
    freeze_customer_clock(monkeypatch)
    with workspace_scope(c, OWNER, org):
        row, _ = connect(c); approve(c); run = prepared(c, org, row, monkeypatch)
        monkeypatch.setattr(mail, 'send', lambda *args, **kwargs: (_ for _ in ()).throw(HTTPException(429,'Synthetic mailbox limit')))
        for attempt in range(1, 4):
            result = customer.outreach_tick(c, run['id'])
            assert result['status'] == ('RATE_LIMITED' if attempt < 3 else 'NEEDS_REVIEW')
            item = c.execute('SELECT * FROM outreach_run_items WHERE run_id=?', (run['id'],)).fetchone()
            assert item['mail_attempts'] == attempt
            c.execute('UPDATE outreach_run_items SET next_mail_attempt_at=NULL WHERE run_id=?', (run['id'],)); c.commit()
        assert customer.outreach_tick(c, run['id'])['status'] == 'EMPTY'
        assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0] == 0 and posts == []


def test_uncertain_worker_delivery_is_reserved_once_and_needs_review(mailbox, monkeypatch):
    c, org, _, _, posts = mailbox
    freeze_customer_clock(monkeypatch)
    with workspace_scope(c, OWNER, org):
        row, _ = connect(c); approve(c); run = prepared(c, org, row, monkeypatch)
        original = gmail.api; calls = []
        async def api(method, path, token, **kwargs):
            if method == 'POST': calls.append(path); raise TimeoutError('Private ambiguous delivery detail')
            return await original(method, path, token, **kwargs)
        monkeypatch.setattr(gmail, 'api', api)
        assert customer.outreach_tick(c, run['id'])['status'] == 'NEEDS_REVIEW'
        assert customer.outreach_tick(c, run['id'])['status'] == 'EMPTY'
        assert calls == ['messages/send'] and posts == []
        assert c.execute("SELECT COUNT(*) FROM email_messages WHERE status='SENDING'").fetchone()[0] == 1

def test_customer_worker_weekend_gate_preserves_ready_item_without_delivery(mailbox,monkeypatch):
    c,org,_,_,posts=mailbox
    freeze_customer_clock(monkeypatch,datetime(2026,11,14,12,tzinfo=timezone.utc))
    with workspace_scope(c,OWNER,org):
        row,_=connect(c);approve(c);run=prepared(c,org,row,monkeypatch)
        assert customer.outreach_tick(c,run['id'])['status']=='OUTSIDE_BUSINESS_HOURS'
        assert c.execute('SELECT status FROM outreach_run_items WHERE run_id=?',(run['id'],)).fetchone()[0]=='READY'
        assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0 and posts==[]


def test_authenticated_soft_bounces_accumulate_per_tenant_and_hard_suppression_is_sticky(mailbox, monkeypatch):
    c, org, other, _, posts = mailbox
    with workspace_scope(c, OWNER, org):
        row, _ = connect(c); approve(c); _, _, pid = seed(c, org, monkeypatch)
        sent = mail.send(c, pid, OWNER, payload(c, pid, row))
        c.execute("UPDATE email_messages SET test_mode=0,to_address='public@hotel0.example' WHERE id=?", (sent['id'],)); c.commit()
        for number, status in enumerate(['4.2.2','4.2.2','4.2.2','5.1.1','4.2.2']):
            dsn = {'kind':'dsn','message_id':f'<bounce-{number}@example.test>','references':[sent['provider_message_id']],
                   'from':'postmaster@example.test','to':OWNER,'date':datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000'),
                   'authentication':'mx.google.com; dkim=pass header.d=example.test',
                   'recipients':[{'recipient':'public@hotel0.example','action':'failed' if status.startswith('5') else 'delayed','status':status}]}
            assert bounces.process(c, dsn, account_id=row['account_id']) == 1
            assert bounces.process(c, dsn, account_id=row['account_id']) == 0
        assert c.execute('SELECT status FROM customer_mail_suppressions WHERE organization_id=?', (org,)).fetchone()[0] == 'INVALID'
        assert 'public@hotel0.example' not in mail.recipients(c, pid)
    with workspace_scope(c, OWNER, other):
        assert c.execute('SELECT COUNT(*) FROM customer_mail_suppressions WHERE organization_id=?', (other,)).fetchone()[0] == 0
    assert len(posts) == 1 # synthetic transport only

@pytest.mark.parametrize('mode,recipient,live,ready',[('test','sandbox@example.test',False,True),('test','',False,False),('test','sandbox@example.test',True,False),('production','',True,False)])
def test_customer_send_readiness_does_not_advertise_unapproved_modes(mailbox,monkeypatch,mode,recipient,live,ready):
    c,org,_,_,posts=mailbox
    with workspace_scope(c,OWNER,org):
        row,_=connect(c);approve(c)
        s=get_settings()
        monkeypatch.setattr(s,'heysow_customer_mail_mode',mode);monkeypatch.setattr(s,'heysow_customer_mail_test_recipient',recipient);monkeypatch.setattr(s,'heysow_customer_mail_live_approved',live)
        assert customer.can_send(c,customer.owned_account(c,OWNER,row['account_id'])) is ready and posts==[]

def test_sync_cancels_remaining_provider_reads_after_authority_loss(mailbox,monkeypatch):
    c,org,_,_,posts=mailbox;requests=[]
    with workspace_scope(c,OWNER,org):
        row,_=connect(c)
        async def api(method,path,token,**kwargs):
            requests.append(path)
            if path=='profile':return {'emailAddress':OWNER,'historyId':'20'}
            if path=='messages':return {'messages':[{'id':str(n)} for n in range(25)]}
            gmail.disconnect(c,row['id']);c.commit()
            return {'raw':'TWVzc2FnZTogdW5yZWxhdGVk'}
        monkeypatch.setattr(gmail,'api',api)
        with pytest.raises(HTTPException):customer.sync_mailbox(row['account_id'])
        assert len([path for path in requests if path.startswith('messages/')])==1
        assert json.loads(c.execute('SELECT cursor_json FROM customer_gmail_sync WHERE connection_id=?',(row['id'],)).fetchone()[0])=={} and posts==[]

def test_async_mail_bridge_cancels_expensive_work_on_timeout():
    canceled=[]
    async def slow():
        try:await asyncio.sleep(5)
        finally:canceled.append(True)
    with pytest.raises(TimeoutError):customer.run(slow(),timeout=.01)
    assert canceled==[True]
