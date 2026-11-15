"""Synthetic paid contracts only; these tests do not certify PayU acceptance."""
import json,time,uuid
import pytest
from fastapi import HTTPException
from test_intent_radar import radar,owned
from app.billing import commercial,contracts,commercial_usage as usage
from app.platform.context import workspace_scope
from app.config.settings import get_settings
from app.database.prospects import now

@pytest.fixture
def paid(radar,monkeypatch):
    c,path,org,foreign=radar
    monkeypatch.setattr(get_settings(),'payu_billing_enabled',True)
    monkeypatch.setattr(get_settings(),'payu_mode','test')
    monkeypatch.setattr(get_settings(),'billing_test_workspaces',org)
    key=str(uuid.uuid4());start=int(time.time())-60;end=start+3600
    plan=commercial.plan('starter');plan['version']=commercial.catalog()['version']
    c.execute("INSERT INTO commercial_contracts(id,organization_id,provider,mode,provider_subscription_id,plan_code,catalog_version,plan_json,status,mandate_verified,paid_start,paid_end,verified_at,created_at,updated_at) VALUES(?,?,'payu','test',?,'starter',?,?,'ACTIVE',1,?,?,?,?,?)",(key,org,'fixture-only-'+key,plan['version'],json.dumps(plan),start,end,now(),now(),now()))
    c.execute("INSERT INTO commercial_workspace_slots(organization_id,mode,contract_id) VALUES(?,'test',?)",(org,key));c.commit()
    return c,path,org,foreign,key,start,end

def test_approved_exact_allowances_version_and_unknown_enterprise():
    plans=commercial.catalog()['plans']
    assert [p['limits']['searches'] for p in plans[:3]]==[100,300,600]
    assert [p['limits']['ai_calls'] for p in plans[:3]]==[20,60,120]
    assert [p['limits']['ai_tokens'] for p in plans[:3]]==[600000,1200000,1800000]
    assert [p['limits']['reports'] for p in plans[:3]]==[5,15,30]
    assert [p['limits']['api_requests'] for p in plans[:3]]==[500,2000,5000]
    assert [p['limits']['monitors'] for p in plans[:3]]==[2,5,10]
    assert [p['limits']['monitor_executions'] for p in plans[:3]]==[60,150,300]
    assert [p['limits']['team_members'] for p in plans[:3]]==[1,3,5]
    assert all(p['limits']['monitor_interval_hours']==24 for p in plans[:3])
    assert plans[-1]['limits'] is None

def test_scheduled_search_is_one_search_and_replays_do_not_double_count(paid):
    c,_,org,_,key,start,end=paid
    with workspace_scope(c,'controlled@example.test',org):
        usage.reserve(c,{'searches':1,'monitor_executions':1},'scheduled-1')
        usage.reserve(c,{'searches':1,'monitor_executions':1},'scheduled-1')
        usage.settle(c,'scheduled-1');usage.settle(c,'scheduled-1')
        counts={r['dimension']:(r['reserved'],r['used']) for r in c.execute('SELECT * FROM commercial_usage WHERE organization_id=?',(org,))}
        assert counts=={'searches':(0,1),'monitor_executions':(0,1)}
        usage.reserve(c,{'searches':99},'manual-rest')
        with pytest.raises(HTTPException) as error:usage.reserve(c,{'searches':1},'over')
        assert error.value.status_code==429
        assert c.execute("SELECT COUNT(*) FROM commercial_reservations WHERE operation_id='over'").fetchone()[0]==0

def test_reservation_multidimension_atomic_and_pre_provider_release(paid):
    c,_,org,_,key,start,end=paid
    with workspace_scope(c,'controlled@example.test',org):
        usage.reserve(c,{'ai_calls':1,'ai_tokens':600000},'ai-1')
        with pytest.raises(HTTPException):usage.reserve(c,{'ai_calls':1,'ai_tokens':1},'ai-2')
        assert not c.execute("SELECT 1 FROM commercial_reservations WHERE operation_id='ai-2'").fetchone()
        usage.settle(c,'ai-1',release=True)
        usage.reserve(c,{'ai_calls':1,'ai_tokens':600000},'ai-1')
        usage.settle(c,'ai-1',actual={'ai_calls':1,'ai_tokens':1000})
        assert c.execute("SELECT used FROM commercial_usage WHERE dimension='ai_tokens'").fetchone()[0]==1000
        with pytest.raises(HTTPException):usage.settle(c,'ai-1',release=True)
        with pytest.raises(HTTPException):usage.reserve(c,{'ai_calls':2},'ai-1')

def test_isolation_absent_context_expired_unpaid_and_mode_mismatch(paid,monkeypatch):
    c,_,org,foreign,key,start,end=paid
    with pytest.raises(HTTPException):usage.reserve(c,{'searches':1},'missing')
    with workspace_scope(c,'foreign@example.test',foreign):
        assert not usage.reserve(c,{'searches':1},'foreign')
    with workspace_scope(c,'controlled@example.test',org):
        for column,value in [('status','PAST_DUE'),('mandate_verified',0),('paid_end',int(time.time())-1)]:
            c.execute('SAVEPOINT altered');c.execute('UPDATE commercial_contracts SET '+column+'=? WHERE id=?',(value,key))
            assert not contracts.active(c,org)
            c.execute('ROLLBACK TO altered');c.execute('RELEASE altered')
        monkeypatch.setattr(get_settings(),'payu_mode','live');assert not contracts.active(c,org)
    assert c.execute('SELECT COUNT(*) FROM commercial_usage').fetchone()[0]==0

def test_capacity_daily_frequency_and_subscription_snapshot_survive_catalog_change(paid,monkeypatch):
    c,_,org,_,key,start,end=paid
    with workspace_scope(c,'controlled@example.test',org):
        with pytest.raises(HTTPException):usage.capacity(c,org,'monitors',2)
        with pytest.raises(HTTPException):usage.capacity(c,org,'team_members',1)
        with pytest.raises(HTTPException):usage.interval(c,12)
        usage.interval(c,24)
        monkeypatch.setattr(commercial,'catalog',lambda:{'version':'future','plans':[]})
        assert contracts.snapshot(contracts.active(c,org))['limits']['searches']==100
        usage.reserve(c,{'api_requests':500},'api-total')
        with pytest.raises(HTTPException):usage.reserve(c,{'api_requests':1},'api-extra')


def test_commercial_usage_overview_breaks_out_manual_and_scheduled_without_double_counting(paid):
    from app.billing.overview import overview
    c,_,org,_,_,_,_=paid
    with workspace_scope(c,'controlled@example.test',org):
        usage.reserve(c,{'searches':1},'manual')
        usage.reserve(c,{'searches':1,'monitor_executions':1},'scheduled')
        result=overview(c)
        assert result['access']['commercial_subscription']
        assert result['search_usage']['total_searches']==2
        assert result['search_usage']['manual_searches']==1
        assert result['search_usage']['scheduled_checks']==1
        counters={r['dimension']:r for r in result['usage']}
        assert counters['plan_searches']['remaining']==98
        assert counters['plan_reports']['remaining']==5
        assert counters['plan_ai_calls']['remaining']==20


def test_report_creation_consumes_shared_ai_and_report_allowance_once(paid,monkeypatch):
    from app.growth_intelligence import service,models
    from app.config.settings import get_settings
    c,_,org,_,_,_,_=paid
    monkeypatch.setattr(get_settings(),'intent_radar_growth_enabled',True)
    body=models.Start(kind='REPORT',question='Review the collected discussions',title='Controlled report')
    with workspace_scope(c,'controlled@example.test',org):
        service.start(c,body);service.start(c,body)
        values={r['dimension']:r['reserved'] for r in c.execute('SELECT * FROM commercial_usage WHERE organization_id=?',(org,))}
        assert values=={'reports':1,'ai_calls':1}
        usage.reserve(c,{'ai_calls':19},'other-ai')
        with pytest.raises(HTTPException) as exc:
            service.start(c,models.Start(kind='REPORT',question='A different report',title='Report blocked by AI limit'))
        assert exc.value.status_code==429
        assert c.execute("SELECT COUNT(*) FROM commercial_reservations WHERE dimension='reports'").fetchone()[0]==1


def test_schema46_upgrade_preserves_rows_and_requires47_only_for_payu(radar,monkeypatch,tmp_path):
    from app.database import migrations
    from app.database.connection import get_connection
    c=get_connection(tmp_path/'commercial-upgrade.db');full=migrations.MIGRATIONS
    monkeypatch.setattr(migrations,'MIGRATIONS',full[:46]);migrations.run_migrations(c)
    before={table:c.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in ['organizations','organization_memberships','businesses','email_messages','billing_payments']}
    monkeypatch.setattr(migrations,'MIGRATIONS',full)
    monkeypatch.setattr(get_settings(),'payu_billing_enabled',False);migrations.verify_schema(c)
    monkeypatch.setattr(get_settings(),'payu_billing_enabled',True)
    with pytest.raises(RuntimeError):migrations.verify_schema(c)
    assert migrations.run_migrations(c)==1 and migrations.run_migrations(c)==0
    migrations.verify_schema(c)
    assert all(c.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]==count for table,count in before.items())
    assert c.execute('SELECT COUNT(*) FROM commercial_contracts').fetchone()[0]==0
    c.close()

def test_queued_report_cancellation_refunds_unstarted_shared_capacity(paid,monkeypatch):
    from app.growth_intelligence import service,models
    from app.intelligence import jobs
    c,_,org,*_=paid
    monkeypatch.setattr(get_settings(),'intent_radar_growth_enabled',True)
    with workspace_scope(c,'controlled@example.test',org):
        report=service.start(c,models.Start(kind='REPORT',title='Controlled cancellation'));c.commit()
        assert c.execute("SELECT reserved FROM commercial_usage WHERE dimension='reports'").fetchone()[0]==1
        assert jobs.control(c,report['job_id'],'cancel')['status']=='CANCELLED'
        assert all(r['reserved']==0 and r['used']==0 for r in c.execute('SELECT * FROM commercial_usage'))
        assert c.execute('SELECT COUNT(*) FROM ai_request_usage').fetchone()[0]==0

def test_paused_and_draft_monitors_do_not_consume_active_paid_capacity(paid):
    from app.intent_radar import service,models
    c,_,org,_,_,_,_=paid
    with workspace_scope(c,'controlled@example.test',org):
        for index in range(3):service.save_monitor(c,models.Monitor(name='Draft '+str(index),configuration=models.Search(keywords=['software'])))
        for index in range(2):service.save_monitor(c,models.Monitor(name='Active '+str(index),status='Active',configuration=models.Search(keywords=['software'])))
        with pytest.raises(HTTPException) as exc:service.save_monitor(c,models.Monitor(name='Third active',status='Active',configuration=models.Search(keywords=['software'])))
        assert exc.value.status_code==429
        assert c.execute("SELECT COUNT(*) FROM intent_monitors WHERE status='Draft'").fetchone()[0]==3
