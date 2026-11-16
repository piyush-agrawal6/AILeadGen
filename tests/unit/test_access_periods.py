"""Isolated native trial/term enforcement; no external payment or email traffic."""
import json,time,uuid
from datetime import datetime,timezone
import pytest
from fastapi import HTTPException
from test_intent_radar import radar,owned
from app.billing import access_periods,commercial_usage as usage,trials,contracts
from app.platform.context import workspace_scope
from app.config.settings import get_settings
from app.database.prospects import now

@pytest.fixture
def trial(radar,monkeypatch):
    c,path,org,foreign=radar
    monkeypatch.setattr(get_settings(),'heysow_access_periods_enabled',True)
    from app.api.organization import ensure_user
    ensure_user(c,'controlled@example.com')
    c.execute("INSERT INTO organization_memberships(id,organization_id,user_id,role,status,created_at,updated_at) VALUES(?,?,?,'OWNER','ACTIVE',?,?)",(str(uuid.uuid4()),org,'controlled@example.com',now(),now()))
    c.execute('INSERT INTO customer_workspace_access(organization_id,registered_by,created_at) VALUES(?,?,?)',(org,'controlled@example.com',now()))
    result=trials.allocate(c,'controlled@example.com',org);c.commit()
    assert result['trial_started']
    return c,path,org,foreign

def test_trial_exact_limits_atomic_reservation_and_one_time_claim(trial):
    c,_,org,_=trial
    with workspace_scope(c,'controlled@example.com',org):
        assert not trials.allocate(c,'controlled@example.com',org)['trial_started']
        usage.reserve(c,{'searches':5},'five');usage.reserve(c,{'searches':5},'five')
        usage.settle(c,'five');usage.settle(c,'five')
        with pytest.raises(HTTPException) as denied:usage.reserve(c,{'searches':1},'six')
        assert denied.value.status_code==429
        for dim in ('reports','api_requests','monitor_executions'):
            with pytest.raises(HTTPException):usage.reserve(c,{dim:1,'ai_calls':1},dim)
        assert not c.execute("SELECT 1 FROM access_period_reservations WHERE dimension='ai_calls'").fetchone()
        usage.reserve(c,{'ai_calls':3,'ai_tokens':150000},'full-ai')
        with pytest.raises(HTTPException):usage.reserve(c,{'ai_tokens':1},'over-tokens')
        usage.settle(c,'full-ai',release=True)
        usage.reserve(c,{'ai_calls':3,'ai_tokens':150000},'full-ai')
        assert c.execute('SELECT COUNT(*) FROM commercial_usage').fetchone()[0]==0

def test_expiry_fails_closed_preserves_reads_and_settles_existing_reservations(trial):
    from app.intent_radar import service
    c,_,org,_=trial
    with workspace_scope(c,'controlled@example.com',org):
        usage.reserve(c,{'searches':1},'in-flight')
        c.execute("UPDATE access_periods SET status='EXPIRED' WHERE organization_id=?",(org,))
        assert service.listing(c,'signals')['total']==0
        for action in (lambda:usage.reserve(c,{'searches':1},'expired'),lambda:usage.capacity(c,org,'team_members',0),lambda:service.preferences(c,__import__('app.intent_radar.models',fromlist=['Preferences']).Preferences())):
            with pytest.raises(HTTPException) as denied:action()
            assert denied.value.status_code==402
        assert usage.settle(c,'in-flight')
        assert c.execute('SELECT used FROM access_period_usage').fetchone()[0]==1
        assert c.execute('SELECT COUNT(*) FROM launch_trial_claims').fetchone()[0]==1

def test_trial_monitor_and_api_mcp_gate_and_scheduler_filter(trial,monkeypatch):
    from app.intent_radar import service,models,schedules,discovery
    from app.developer import keys
    c,_,org,_=trial
    monkeypatch.setattr(get_settings(),'intent_radar_schedules_enabled',True)
    with workspace_scope(c,'controlled@example.com',org):
        monitor=service.save_monitor(c,models.Monitor(name='Manual trial monitor',configuration=models.Search(keywords=['software']),status='Active'))
        with pytest.raises(HTTPException):service.save_monitor(c,models.Monitor(name='Extra monitor',configuration=models.Search(keywords=['software'])))
        with pytest.raises(HTTPException):usage.capacity(c,org,'team_members',1)
        with pytest.raises(HTTPException) as denied:usage.interval(c,24)
        assert denied.value.status_code==403
        with pytest.raises(HTTPException):keys.scope_access(c,org,['intent:read','mcp:use'])
        job=discovery.create(c,models.Discovery(configuration=models.Search(keywords=['software']),monitor_id=monitor['id']))
        assert job['id']
        values={r['dimension']:r['used'] for r in c.execute('SELECT * FROM access_period_usage')}
        assert values=={'searches':1}
        where,args=schedules.eligible_sql('m','created_by')
        assert c.execute('SELECT m.id FROM intent_monitors m WHERE '+where,args).fetchall()==[]

def test_native_ai_attempts_use_trial_ledger_and_keep_unknown_capacity(trial):
    from app.billing import ai_accounting
    from types import SimpleNamespace
    c,_,org,_=trial;p=SimpleNamespace(usage_connection=c)
    with workspace_scope(c,'controlled@example.com',org):
        usage.reserve(c,{'ai_calls':1},'provider-operation');c.commit()
        with ai_accounting.operation('provider-operation'):
            unknown=ai_accounting.begin_attempt(p,100000)
            with pytest.raises(HTTPException):ai_accounting.begin_attempt(p,100000)
        totals={r['dimension']:(r['reserved'],r['used']) for r in c.execute('SELECT * FROM access_period_usage')}
        assert totals=={'ai_calls':(0,1),'ai_tokens':(100000,0)}
        ai_accounting.complete_attempt(p,unknown,{'input_tokens':100,'output_tokens':20,'thinking_tokens':0})
        assert c.execute("SELECT used FROM access_period_usage WHERE dimension='ai_tokens'").fetchone()[0]==120

def test_absent_foreign_membership_and_expired_trial_never_adopts_other_plan(trial):
    c,_,org,foreign=trial
    with pytest.raises(HTTPException):usage.reserve(c,{'searches':1},'missing')
    with workspace_scope(c,'foreign@example.test',foreign):
        assert contracts.active(c,foreign) is None
        assert not usage.settle(c,'someone-elses-operation')
    c.execute("UPDATE access_periods SET status='REVOKED' WHERE organization_id=?",(org,))
    with workspace_scope(c,'controlled@example.com',org):
        with pytest.raises(HTTPException):usage.reserve(c,{'searches':1},'revoked')
    assert c.execute('SELECT COUNT(*) FROM access_period_reservations').fetchone()[0]==0

def test_native_flag_cannot_disable_quota_after_enrollment(trial,monkeypatch):
    from app.database.migrations import verify_schema
    c,*_=trial
    verify_schema(c)
    monkeypatch.setattr(get_settings(),'heysow_access_periods_enabled',False)
    with pytest.raises(RuntimeError,match='Managed customer'):verify_schema(c)

def test_new_commercial_accounts_cannot_create_beta_workspace_bypass(trial):
    from app.api.organization import create_organization
    c,_,org,_=trial;stamp=now()
    c.execute("INSERT INTO customer_accounts(email,user_id,name,company_name,status,terms_version,verified_at,created_at,updated_at) VALUES(?,?,?,?,'ACTIVE','fixture-terms',?,?,?)",('controlled@example.com','controlled@example.com','Controlled owner','Company',stamp,stamp,stamp))
    other=create_organization(c,'controlled@example.com','Additional company')['organization_id']
    assert access_periods.managed(c,other)
    with workspace_scope(c,'controlled@example.com',other):
        with pytest.raises(HTTPException) as denied:usage.reserve(c,{'ai_calls':1},'no-extra-trial')
        assert denied.value.status_code==402

def test_duration_policy_and_no_unverified_payment_grant(trial):
    c,_,org,_=trial
    leap=int(datetime(2024,2,29,12,tzinfo=timezone.utc).timestamp())
    start,end=access_periods.next_period(c,org,'starter','monthly',stamp=leap)
    assert end-start==30*86400
    start,end=access_periods.next_period(c,org,'starter','yearly',stamp=leap)
    assert datetime.fromtimestamp(end,timezone.utc)==datetime(2025,2,28,12,tzinfo=timezone.utc)
    c.execute("UPDATE access_periods SET source_kind='PAYMENT',mode='test' WHERE organization_id=?",(org,))
    assert access_periods.active(c,org) is None
    with pytest.raises(HTTPException):access_periods.require_current(c,org)
