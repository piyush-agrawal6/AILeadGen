import time,uuid,asyncio
import pytest
from fastapi import HTTPException
from test_subscription_payment import subscribed,customer,accounts,iso
from test_onboarding_ai import setup_client,start
from app.platform.context import workspace_scope
from app.database.connection import db_session

def test_development_receipt_metered_separately_and_revocable(subscribed,monkeypatch):
    from app.billing import owner_starter as grant,subscription_access as access,subscription_sync,subscriptions,commercial_usage,commercial,overview
    c,s,org,actor,state,*_=subscribed;stamp=int(time.time());state.update(status='canceled',current_period_start_date=iso(stamp-259300),current_period_end_date=iso(stamp-100))
    # Disposable verified test account; no mutation of owner production history.
    monkeypatch.setattr(grant,'OWNER',actor);key=str(uuid.uuid4());monkeypatch.setattr(s,'owner_starter_grant_id',key)
    with workspace_scope(c,actor,org):
        original=subscription_sync.reconcile_subscription(state['id'],'production');c.execute('UPDATE user_profiles SET active_organization_id=? WHERE user_id=?',(org,actor));c.commit()
        assert not grant.active(c,org);assert original['status']=='canceled'
        grant.record(c,org,key,end=stamp+86400,reason='Disposable release QA',administrator='isolated operator');c.commit();effective=access.require_product(c,org)
        assert effective['source_kind']=='COMPLIMENTARY' and not access.active(c,org);assert subscriptions.summary(c)['lifecycle']['can_purchase'];assert not grant.active(c,str(uuid.uuid4()))
        cap=commercial.plan('starter')['limits']['searches'];assert commercial_usage.reserve(c,{'searches':cap},'dev-search-budget');c.commit()
        with pytest.raises(HTTPException,match='exhausted'):commercial_usage.reserve(c,{'searches':1},'excess')
        c.rollback();assert overview.overview(c)['access']['kind'].startswith('Complimentary Starter');assert c.execute('SELECT COUNT(*) FROM subscription_payments').fetchone()[0]==0
        grant.record(c,org,key,end=0,reason='test complete',administrator='isolated operator',revoke=True);c.commit()
        with pytest.raises(HTTPException) as denied:access.require_product(c,org)
        assert denied.value.status_code==402 and c.execute('SELECT status FROM subscription_contracts WHERE id=?',(original['id'],)).fetchone()[0]=='canceled'

def test_recovery_dispatches_third_durable_review_after_capacity_returns(setup_client,monkeypatch):
    from app.api.routes import onboarding as routes
    from app.platform import company_discovery_dispatch as dispatch,company_discovery as jobs
    http,_,_,s,org,_=setup_client
    async def defer(key):pass
    monkeypatch.setattr(routes,'launch',defer);keys=[]
    for i in range(3):
        _,result=start(http,revision=i,website='https://example.com/'+str(i));keys.append(result['review']['id'])
    with db_session() as c:
        with workspace_scope(c,'setup@example.test',org):
            assert dispatch._claim(keys[0]) and dispatch._claim(keys[1]) and not dispatch._claim(keys[2])
    # Simulate two fresh worker processes taking their persisted claims, then
    # an independent scheduler invocation with no request or browser context.
    for key in keys[:2]:jobs.execute(key)
    async def restart():
        await dispatch.recover();await asyncio.gather(*tuple(dispatch._tasks))
    asyncio.run(restart());asyncio.run(restart())
    with db_session() as c:
        rows=c.execute('SELECT status,attempts FROM organization_profile_jobs WHERE organization_id=? ORDER BY created_at',(org,)).fetchall()
        assert len(rows)==3 and all(r['status'] in ('READY','FAILED') and r['attempts']==1 for r in rows)
