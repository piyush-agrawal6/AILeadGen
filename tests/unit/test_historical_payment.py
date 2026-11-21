import json,time,uuid
import pytest
from pydantic import SecretStr
from fastapi import HTTPException
from test_customer_accounts import customer,accounts,verified
from app.billing import fixed_term,commercial
from app.database.prospects import now
from app.platform.context import workspace_scope

@pytest.fixture
def purchase(customer,monkeypatch):
    c,s=customer;registration,_=verified(c);org=registration['organization_id'];monkeypatch.setattr(s,'billing_test_workspaces',org);return c,s,org,'person@example.com'

def seed_historical_purchase(c,org,actor):
    key=str(uuid.uuid4());stamp=now();start=int(time.time())-1;end=start+86400;plan=json.dumps(dict(commercial.plan('growth'),version='fixture-history'));
    c.execute("INSERT INTO payu_access_orders(id,organization_id,created_by,mode,txn_id,request_id,request_fingerprint,plan_code,interval,plan_json,catalog_version,policy_version,terms_version,terms_accepted_at,currency,subtotal_minor,tax_minor,total_minor,tax_json,expected_json,billing_encrypted,status,creation_started_at,expires_at,created_at,updated_at,period_start,period_end,provider_payment_id,verified_at,verified_json) VALUES(?,?,?,'test',?,?,'fixture','growth','monthly',?,'fixture-history','fixture','fixture',?,'USD',14900,0,14900,'{}','{}','fixture','PAID',?,?,?,?,?,?,'historical-test-reference',?,'{}')",(key,org,actor,key,key,plan,stamp,stamp,end,stamp,stamp,start,end,stamp));
    c.execute("UPDATE access_periods SET status='REPLACED' WHERE organization_id=? AND source_kind='TRIAL'",(org,));c.execute("INSERT INTO access_periods(id,organization_id,source_kind,source_id,plan_code,plan_json,status,paid_start,paid_end,verified_at,mode,created_at,updated_at) VALUES(?,?,'PAYMENT',?,'growth',?,'ACTIVE',?,?,?,'test',?,?)",(str(uuid.uuid4()),org,key,plan,start,end,stamp,stamp,stamp));c.commit();return key

def test_invitation_email_quota_and_verified_recipient_explicit_acceptance(purchase,monkeypatch):
    # This test inspects the pending, encrypted outbox before delivery. The
    # admission fixture otherwise runs in development and consumes the row.
    monkeypatch.setattr('app.notifications.dispatch.enqueue_notification',lambda _:None)
    from app.platform import invitations
    from app.accounts import service as accounts,models as account_models
    from test_customer_accounts import signup,otp
    c,s,org,actor=purchase;s.heysow_invited_registration_enabled=True
    with workspace_scope(c,actor,org):
        from tests.creem_quota_fixture import seed
        seed(c,org,actor,monkeypatch,'growth')
        invite=invitations.create(c,invitations.InviteCreate(email='teammate@example.com'));c.commit()
        assert invite['delivery']=='EMAIL_QUEUED'
        queued=c.execute("SELECT * FROM transactional_notifications WHERE purpose='TEAM_INVITATION'").fetchone()
        from app.notifications import transactional as mail
        payload=json.loads(mail.cipher().decrypt(queued['payload_encrypted'].encode()))
        assert '/accept-invitation#'+invite['token'] in payload['text']
        assert mail.authorized(c,queued)
    s.heysow_public_registration_enabled=False
    registered=accounts.begin_signup(signup(email='teammate@example.com',invitation_token=SecretStr(invite['token'])),'invited-client')
    result=accounts.verify_email(account_models.Verify(challenge_id=registered['challenge_id'],capability=registered['capability'],code=otp(c,registered['challenge_id'])),'invited-client')
    assert result['verified'] and 'organization_id' not in result
    assert c.execute('SELECT COUNT(*) FROM organization_memberships WHERE user_id=?',('teammate@example.com',)).fetchone()[0]==0
    assert c.execute('SELECT COUNT(*) FROM launch_trial_claims').fetchone()[0]==1
    accepted=invitations.respond(c,'teammate@example.com',invitations.InviteRespond(token=invite['token'],action='ACCEPT'));c.commit()
    assert accepted['organization_id']==org
    assert not mail.authorized(c,queued)

def test_trial_does_not_queue_invites_above_one_member(customer):
    from app.platform import invitations
    c,s=customer;registration,_=verified(c);org=registration['organization_id']
    with workspace_scope(c,'person@example.com',org):
        with pytest.raises(HTTPException) as denied:invitations.create(c,invitations.InviteCreate(email='teammate@example.com'))
        assert denied.value.status_code==429
    assert c.execute('SELECT COUNT(*) FROM workspace_invitations').fetchone()[0]==0
    assert c.execute("SELECT COUNT(*) FROM transactional_notifications WHERE purpose='TEAM_INVITATION'").fetchone()[0]==0

def test_historical_order_keeps_its_provider_and_cannot_create_checkout(purchase):
    c,s,org,actor=purchase
    with workspace_scope(c,actor,org):
        key=seed_historical_purchase(c,org,actor)
        history=fixed_term.history(c)
        assert history['items'][0]['provider']=='payu' and not history['checkout_enabled']
        first=fixed_term.refund_request(c,key,fixed_term.RefundRequest(request_id=uuid.uuid4()))
        second=fixed_term.refund_request(c,key,fixed_term.RefundRequest(request_id=uuid.uuid4()))
        assert first['id']==second['id'] and not first['money_refunded']
    from app.api.organization import create_organization
    foreign=create_organization(c,actor,'Separate accounting workspace')['organization_id']
    with workspace_scope(c,actor,foreign):
        with pytest.raises(HTTPException) as denied:fixed_term.owned(c,key)
        assert denied.value.status_code==404
