"""Clean-profile cost controls and excluded-worker guards."""
import pytest
from fastapi import HTTPException
from app.config.settings import get_settings


@pytest.mark.parametrize('kind',['acquisition','workflow','scan','report'])
def test_disabled_legacy_job_fails_before_database_access(monkeypatch,kind):
    from app.platform.context import job_scope
    monkeypatch.setattr(get_settings(),'lead_engine_available',False)
    class NoDatabase:
        def execute(self,*args):raise AssertionError('Disabled job accessed database')
    with pytest.raises(HTTPException) as error:
        with job_scope(NoDatabase(),kind,'untrusted-id'):pass
    assert error.value.status_code==404


@pytest.mark.parametrize('key,value', [('LEADENGINE_RUN_ID','1'),('LEADENGINE_EMAIL_SYNC','1'),('LEADENGINE_SHEET_EXPORT_ID','x'),('LEADENGINE_CUSTOMER_MAILBOX_ID','x'),('LEADENGINE_AUTOMATION_MODE','inbox-sync')])
def test_clean_worker_rejects_excluded_modes_before_dispatch(monkeypatch,key,value):
    from app.worker import validate_schema_mode
    monkeypatch.setattr(get_settings(),'database_schema_profile','intent-radar-v1')
    monkeypatch.setenv(key,value)
    with pytest.raises(SystemExit,match='unavailable'):validate_schema_mode()


@pytest.mark.parametrize('key',['PLANEBYTE_NOTIFICATION_ID','PLANEBYTE_ACCOUNT_RECOVERY_ID','LEADENGINE_PROFILE_DISCOVERY_ID','LEADENGINE_INTELLIGENCE_JOB_ID'])
def test_clean_worker_accepts_actual_radar_and_mail_dispatch_overrides(monkeypatch,key):
    from app.worker import validate_schema_mode
    monkeypatch.setattr(get_settings(),'database_schema_profile','intent-radar-v1')
    monkeypatch.setenv('LEADENGINE_EMAIL_SYNC','0')
    monkeypatch.setenv('LEADENGINE_RUN_ID','')
    monkeypatch.setenv(key,'synthetic-job')
    validate_schema_mode()


@pytest.mark.asyncio
async def test_no_periodic_database_loops_when_polling_disabled(monkeypatch):
    from app.api import server
    from app.notifications import dispatch
    from app.intent_radar import schedules
    s=get_settings()
    for k,v in {'app_env':'production','database_background_polling_enabled':False,'transactional_mail_enabled':True,'intent_radar_schedules_enabled':True}.items():monkeypatch.setattr(s,k,v)
    monkeypatch.setattr(server,'verify_schema',lambda:None)
    async def forbidden():raise AssertionError('Periodic database polling started')
    monkeypatch.setattr(dispatch,'loop',forbidden);monkeypatch.setattr(schedules,'loop',forbidden)
    async with server.app.router.lifespan_context(server.app):
        import asyncio
        await asyncio.sleep(0)
    assert s.transactional_mail_enabled  # request-triggered delivery remains on


def test_api_pool_can_release_all_idle_connections(monkeypatch):
    from unittest.mock import Mock
    from app.database import postgres
    pool=Mock();constructor=Mock(return_value=pool)
    monkeypatch.setattr('psycopg_pool.ConnectionPool',constructor)
    monkeypatch.setattr(postgres,'_pools',{})
    assert postgres.connection_pool('synthetic-url') is pool
    kwargs=constructor.call_args.kwargs
    assert kwargs['min_size']==0 and kwargs['max_size']==4 and kwargs['max_idle']==30
    assert kwargs['timeout']==8 and kwargs['kwargs']['application_name']=='planebyte-api'
    assert 'check' not in kwargs  # no periodic database health query
