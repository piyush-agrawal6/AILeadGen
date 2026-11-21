import time,uuid
import pytest
from fastapi import HTTPException
from app.billing import accounts as shared,commercial_usage as usage,subscription_access as access,subscriptions,subscription_sync,owner_starter,overview
from app.platform.context import workspace_scope
from app.platform.workspaces import create_workspace,WorkspaceCreate
from app.api.organization import create_organization
from test_subscription_payment import subscribed,customer,accounts,iso

@pytest.mark.parametrize('enabled,pilot',[(False,False),(True,False),(True,True)])
def test_workspace_creation_never_infers_an_account(subscribed,monkeypatch,enabled,pilot):
    c,s,primary,owner,*_=subscribed
    monkeypatch.setattr(s,'shared_billing_accounts_enabled',enabled);monkeypatch.setattr(s,'shared_billing_owner_pilot',pilot)
    # One eligible account is the original failed regression. Exercise an unrelated owner too.
    for actor,existing in [(owner,primary),('unrelated@example.com',create_organization(c,'unrelated@example.com','Unrelated primary')['organization_id'])]:
        assert shared.admin(c,existing,actor)
        request=WorkspaceCreate(name='Independent secondary',request_id=uuid.uuid4());new=create_workspace(c,actor,request)['organization_id'];c.commit()
        assert create_workspace(c,actor,request)['reused']
        assert c.execute('SELECT account_id FROM billing_workspace_links WHERE workspace_id=?',(new,)).fetchone()[0]==new and new!=existing
        assert not access.product_grant(c,new)
    with pytest.raises(HTTPException):create_workspace(c,'unrelated@example.com',WorkspaceCreate(name='Foreign account selection',billing_account_id=primary,request_id=uuid.uuid4()))
    c.rollback()
    if pilot or not enabled:
        with pytest.raises(HTTPException):create_workspace(c,owner,WorkspaceCreate(name='Outside rollout',billing_account_id=primary,request_id=uuid.uuid4()))
        c.rollback()
    if pilot:
        with pytest.raises(HTTPException):shared.attach_empty(c,primary,new,owner,'test operator','Out of scope')

def test_production_flag_is_fail_closed(monkeypatch):
    from app.config.settings import get_settings
    s=get_settings();monkeypatch.setattr(s,'app_env','production');monkeypatch.setattr(s,'shared_billing_accounts_enabled',True);monkeypatch.setattr(s,'shared_billing_owner_pilot',False)
    assert not shared.enabled(shared.PILOT_CHILD)
    monkeypatch.setattr(s,'shared_billing_owner_pilot',True)
    assert shared.enabled(shared.PILOT_CHILD) and shared.enabled(shared.PILOT_ACCOUNT) and not shared.enabled(str(uuid.uuid4()))

def test_one_contract_shared_idempotent_debits_and_private_billing(subscribed,monkeypatch):
    c,s,primary,actor,state,*_=subscribed;monkeypatch.setattr(s,'shared_billing_accounts_enabled',True)
    with workspace_scope(c,actor,primary):
        contract=subscription_sync.reconcile_subscription(state['id'],'production');c.commit()
        body=WorkspaceCreate(name='Second business',request_id=uuid.uuid4(),billing_account_id=primary);child=create_workspace(c,actor,body)['organization_id'];assert create_workspace(c,actor,body)['reused'];c.commit()
        assert usage.reserve(c,{'searches':2},'same-request');usage.settle(c,'same-request');c.commit()
    with workspace_scope(c,actor,child):
        assert access.require_product(c,child)['id']==contract['id'];summary=subscriptions.summary(c);assert summary['billing_account']['id']==primary and not summary['trial_eligible'] and not summary['can_manage'] and not summary['history']
        with pytest.raises(HTTPException):subscriptions.owner(c)
        for _ in range(2):assert usage.reserve(c,{'searches':3},'same-request');usage.settle(c,'same-request');c.commit()
        with pytest.raises(HTTPException,match='exhausted'):usage.reserve(c,{'searches':1},'over-limit')
        c.rollback();assert c.execute('SELECT COUNT(*) FROM subscription_contracts WHERE organization_id=?',(child,)).fetchone()[0]==0
        with monkeypatch.context() as paused:
            paused.setattr(s,'shared_billing_accounts_enabled',False)
            with pytest.raises(HTTPException) as denied:subscriptions.owner(c)
            assert denied.value.status_code==409
    other=create_organization(c,actor,'Independent billing account')['organization_id'];c.commit()
    assert shared.anchor(c,other)==other and not access.product_grant(c,other)
    with workspace_scope(c,actor,other):
        with pytest.raises(HTTPException):shared.attach_empty(c,other,primary,actor,'isolated DB operator','Must reject existing contract')

def test_shared_development_receipt_keeps_exact_expiry_and_revocation(subscribed,monkeypatch):
    c,s,primary,actor,state,*_=subscribed;stamp=int(time.time());end=stamp+3600;key=str(uuid.uuid4());monkeypatch.setattr(s,'shared_billing_accounts_enabled',True);monkeypatch.setattr(owner_starter,'OWNER',actor);monkeypatch.setattr(s,'owner_starter_grant_id',key)
    state.update(status='canceled',current_period_start_date=iso(stamp-259300),current_period_end_date=iso(stamp-100))
    with workspace_scope(c,actor,primary):
        subscription_sync.reconcile_subscription(state['id'],'production');c.execute('UPDATE user_profiles SET active_organization_id=? WHERE user_id=?',(primary,actor));owner_starter.record(c,primary,key,end=end,reason='QA',administrator='QA');c.commit()
    child=create_organization(c,actor,'Existing owned workspace')['organization_id'];c.commit()
    assert not access.product_grant(c,child);assert shared.attach_empty(c,primary,child,actor,'isolated DB owner','Verify explicit migration');c.commit();assert not shared.attach_empty(c,primary,child,actor,'isolated DB owner','Repeat');c.commit()
    with workspace_scope(c,actor,child):
        g=access.require_product(c,child);assert g['source_kind']=='COMPLIMENTARY' and g['paid_end']==end and g['grant_id']==key
    owner_starter.record(c,primary,key,end=0,reason='QA revocation',administrator='QA',revoke=True);c.commit();assert not access.product_grant(c,primary) and not access.product_grant(c,child)
