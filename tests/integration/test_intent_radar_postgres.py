"""Phase 2/3 acceptance on disposable PostgreSQL schemas, never public/production."""
import asyncio
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
from test_postgres import postgres,pytestmark
from test_intent_radar import source_result
from app.api.organization import create_organization
from app.config.settings import get_settings
from app.database.migrations import run_migrations
from app.database.postgres import PostgresConnection
from app.platform.context import workspace_scope
from app.intent_radar import connectors,discovery,intelligence,models,service,schedules
from app.intelligence import jobs

@pytest.fixture
def pg_radar(postgres,monkeypatch):
    c=postgres;run_migrations(c);s=get_settings()
    monkeypatch.setattr(s,'intent_radar_stage','Beta')
    monkeypatch.setattr(s,'intent_radar_schedules_enabled',True)
    monkeypatch.setattr(s,'allowed_user_emails','radar-pg@example.test')
    org=create_organization(c,'radar-pg@example.test','Owned radar')['organization_id']
    other=create_organization(c,'radar-pg@example.test','Foreign radar')['organization_id']
    c.execute("UPDATE organization_onboarding SET status='COMPLETED' WHERE organization_id IN (?,?)",(org,other))
    c.execute("UPDATE organization_products SET enabled=1 WHERE product='INTENT_RADAR' AND organization_id IN (?,?)",(org,other));c.commit()
    @contextmanager
    def session(path=None):
        db=PostgresConnection(s.database_url,schema=c.schema)
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback();raise
        finally:db.close()
    from app.platform import ai_usage,provider_usage
    from app.intent_radar import operations
    for module in (jobs,connectors,intelligence,schedules,ai_usage,provider_usage,operations):monkeypatch.setattr(module,'db_session',session)
    return c,org,other

def test_postgres_radar_scheduling_dedupe_quota_recovery_and_isolation(pg_radar,monkeypatch):
    c,org,other=pg_radar
    monkeypatch.setattr(connectors,'fetch',AsyncMock(return_value=source_result()))
    with workspace_scope(c,'radar-pg@example.test',org):
        q=models.Search(keywords=['website'])
        m=service.save_monitor(c,models.Monitor(name='Scheduled',configuration=q,status='Active'));c.commit()
        schedules.update(c,m['id'],models.Schedule(frequency='Daily',revision=m['revision']));c.commit()
        c.execute("UPDATE intent_monitors SET next_run_at='2000-01-01' WHERE id=?",(m['id'],));c.commit()
        pending=schedules.enqueue_due(c);assert len(pending)==1 and schedules.enqueue_due(c)==[]
        jobs.execute(pending[0]['id']);assert discovery.owned_job(c,pending[0]['id'])['status']=='COMPLETED'
        signal=service.listing(c,'signals')['items'][0]
        job=discovery.create(c,models.Discovery(configuration=q));c.commit()
        c.execute("UPDATE intelligence_jobs SET status='RUNNING',attempts=1,lease_owner='lost',lease_until='2000-01-01' WHERE id=?",(job['id'],))
        c.execute("UPDATE intelligence_job_items SET status='PROCESSING' WHERE job_id=?",(job['id'],));c.commit()
        async def launch(key):await asyncio.to_thread(jobs.execute,key)
        monkeypatch.setattr('app.intelligence.dispatch.launch',launch)
        asyncio.run(schedules.tick())
        assert discovery.owned_job(c,job['id'])['status']=='COMPLETED'
        assert discovery.owned_job(c,job['id'])['attempts']==2
        assert service.listing(c,'signals')['total']==1
        monkeypatch.setattr(get_settings(),'intent_radar_daily_searches',1)
        with pytest.raises(HTTPException) as denied:discovery.create(c,models.Discovery(configuration=q))
        assert denied.value.status_code==429;c.rollback()
    with workspace_scope(c,'radar-pg@example.test',other):
        assert service.listing(c,'signals')['total']==0
        with pytest.raises(HTTPException) as denied:service.bookmark(c,signal['id'])
        assert denied.value.status_code==404;c.rollback()
    for table in ('businesses','contact_people','email_messages','workflow_runs'):
        assert c.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]==0

@pytest.mark.parametrize('change',['source','lease','cancel'])
def test_postgres_radar_final_fence_blocks_revoked_response(pg_radar,monkeypatch,change):
    c,org,_=pg_radar
    monkeypatch.setattr(connectors,'approved_endpoint',lambda url:url)
    with workspace_scope(c,'radar-pg@example.test',org):
        body=models.SourceConfig(name='Approved',family='rss',endpoint='https://example.com/feed',policy_reference='Synthetic PG approval',attribution='Publisher',enabled=True)
        feed=connectors.configure(c,body);c.commit()
        job=discovery.create(c,models.Discovery(configuration=models.Search(keywords=['website'],sources=['rss'],feed_ids=[feed['id']])));c.commit()
        async def revoked(db,q,key,permit):
            second=PostgresConnection(get_settings().database_url,schema=c.schema)
            try:
                if change=='source':second.execute('UPDATE intent_source_configs SET configuration_json=? WHERE id=?',(body.model_copy(update={'enabled':False}).model_dump_json(),feed['id']))
                elif change=='lease':second.execute("UPDATE intelligence_jobs SET lease_owner='replacement' WHERE id=?",(job['id'],))
                else:second.execute("UPDATE intelligence_jobs SET status='CANCELLED' WHERE id=?",(job['id'],))
                second.commit()
            finally:second.close()
            connectors.cache_fence(permit)
            raise AssertionError('Revoked execution crossed persistence fence')
        monkeypatch.setattr(connectors,'fetch',revoked)
        jobs.execute(job['id'])
        for table in ('intent_signals','intent_alerts','intent_source_cache'):
            assert c.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]==0

def test_postgres_recovered_source_checkpoint_is_not_fetched_again(pg_radar,monkeypatch):
    c,org,_=pg_radar
    transport=AsyncMock(return_value=source_result())
    monkeypatch.setattr(connectors,'fetch',transport)
    with workspace_scope(c,'radar-pg@example.test',org):
        job=discovery.create(c,models.Discovery(configuration=models.Search(keywords=['website'])));c.commit();jobs.execute(job['id'])
        assert transport.call_count==1
        c.execute("UPDATE intelligence_jobs SET status='RUNNING',attempts=1,lease_owner='crashed-worker',lease_until='2000-01-01' WHERE id=? AND organization_id=?",(job['id'],org))
        c.execute("UPDATE intelligence_job_items SET status='PROCESSING' WHERE job_id=?",(job['id'],));c.commit()
        jobs.execute(job['id'])
        restored=discovery.owned_job(c,job['id'])
        assert restored['status']=='COMPLETED' and restored['attempts']==2
        assert transport.call_count==1
        assert service.listing(c,'signals')['total']==1
        assert restored['sources'][0]['signals']

def test_postgres_radar_analysis_cache_feedback_and_durable_budget(pg_radar,monkeypatch):
    c,org,_=pg_radar
    monkeypatch.setattr(get_settings(),'intent_radar_ai_enabled',True)
    monkeypatch.setattr(connectors,'fetch',AsyncMock(return_value=source_result()))
    output=intelligence.Interpretation(categories=['Recommendation request'],claims=[intelligence.Claim(kind='intent',quote='recommend a website development partner?',interpretation='Explicit recommendation request')])
    mock=AsyncMock(return_value=output)
    monkeypatch.setattr('app.acquisition.ai.provider',lambda db:SimpleNamespace(structured=mock,last_provider='SYNTHETIC',last_model='fixture'))
    with workspace_scope(c,'radar-pg@example.test',org):
        service.preferences(c,models.Preferences(analysis_daily_call_limit=1));c.commit()
        job=discovery.create(c,models.Discovery(configuration=models.Search(keywords=['website'])));c.commit();jobs.execute(job['id'])
        signal=service.listing(c,'signals')['items'][0]
        first=asyncio.run(intelligence.analyze(c,signal['id'],models.AnalysisRequest()));c.commit()
        assert first['mode']=='AI interpretation'
        intelligence.feedback(c,signal['id'],models.Feedback(label='Not relevant'));c.commit()
        repeat=asyncio.run(intelligence.analyze(c,signal['id'],models.AnalysisRequest()))
        assert repeat['cached'] and mock.await_count==1
        assert repeat['scoring']['overall']==first['scoring']['overall']-10
        with pytest.raises(HTTPException) as denied:intelligence.reserve()
        assert denied.value.status_code==429
        assert c.execute('SELECT calls FROM intent_analysis_usage').fetchone()[0]==1

def test_postgres_completion_migration_and_scoped_retention_preserve_history(pg_radar,monkeypatch):
    import json
    c,org,other=pg_radar
    monkeypatch.setattr(connectors,'fetch',AsyncMock(return_value=source_result()))
    with workspace_scope(c,'radar-pg@example.test',org):
        job=discovery.create(c,models.Discovery(configuration=models.Search(keywords=['website'])));c.commit();jobs.execute(job['id'])
        signal=service.listing(c,'signals')['items'][0]
        service.bookmark(c,signal['id']);c.execute("UPDATE intent_saved_signals SET notes='Private customer research' WHERE organization_id=?",(org,))
        evidence={**signal['evidence'],'provenance':{'retention_days':1}}
        c.execute('UPDATE intent_signals SET retrieved_at=?,evidence_json=? WHERE organization_id=? AND id=?',('2000-01-01T00:00:00+00:00',json.dumps(evidence),org,signal['id']));c.commit()
        assert service.expire_content(c)['expired_source_items']==1;c.commit()
        assert service.saved(c)['items'][0]['notes']=='Private customer research'
        assert discovery.owned_job(c,job['id'])['status']=='COMPLETED'
    with workspace_scope(c,'radar-pg@example.test',other):
        assert service.listing(c,'signals')['total']==0
        assert c.execute('SELECT COUNT(*) FROM intent_retention_cursors WHERE organization_id=?',(other,)).fetchone()[0]==0

def test_postgres_actual_provider_aggregation_and_fallback_usage(pg_radar):
    import time
    from app.platform.provider_usage import record,reported,summary
    c,org,other=pg_radar
    provider=SimpleNamespace(config=SimpleNamespace(model_pricing_json='{}',primary_provider='vertex'),model='fixture',provider_name='GEMINI_API',usage_connection=c)
    with workspace_scope(c,'radar-pg@example.test',org):
        record(provider,reported({'usageMetadata':{'promptTokenCount':12,'candidatesTokenCount':3,'cachedContentTokenCount':2}}),'SUCCEEDED',time.monotonic())
        record(provider,reported({}),'FAILED',time.monotonic());c.commit()
        usage=summary(c)
        assert usage['requests']==2 and usage['input_tokens_reported']==12 and usage['cached_tokens_reported']==2
        assert usage['unreported_requests']==1 and usage['estimated_cost_usd'] is None and usage['items'][0]['fallback']==1
    with workspace_scope(c,'radar-pg@example.test',other):assert summary(c)['requests']==0

def test_postgres_global_source_reservations_serialize_across_workspaces(pg_radar,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from app.intent_radar import operations
    from app.database.connection import db_session
    c,org,other=pg_radar
    monkeypatch.setattr(get_settings(),'intent_radar_global_daily_searches',1)
    def reserve(target):
        # operations.db_session is fixture-scoped to this isolated schema.
        with operations.db_session() as connection:
            with workspace_scope(connection,'radar-pg@example.test',target):
                try:operations.reserve_source('hacker_news');return 'RESERVED'
                except HTTPException as exc:assert exc.status_code==429;return 'DENIED'
    with ThreadPoolExecutor(max_workers=2) as workers:results=list(workers.map(reserve,[org,other]))
    assert sorted(results)==['DENIED','RESERVED']
    assert c.execute('SELECT SUM(reserved_requests) FROM intent_source_usage').fetchone()[0]==22


def test_postgres_overview_trend_alias_and_empty_workspace_are_valid(pg_radar,monkeypatch):
    """The deployed overview must execute on PostgreSQL, not just SQLite."""
    c,org,other=pg_radar
    monkeypatch.setattr(connectors,'fetch',AsyncMock(return_value=source_result()))
    with workspace_scope(c,'radar-pg@example.test',org):
        assert service.overview(c)['trends']==[]
        job=discovery.create(c,models.Discovery(configuration=models.Search(keywords=['website'])));c.commit();jobs.execute(job['id'])
        result=service.overview(c)
        assert result['new_signals']==1
        assert len(result['trends'])==1 and result['trends'][0]['volume']==1
        assert len(result['trends'][0]['day'])==10
        assert len(result['recent_signals'])==1
    with workspace_scope(c,'radar-pg@example.test',other):
        assert service.overview(c)['trends']==[]
