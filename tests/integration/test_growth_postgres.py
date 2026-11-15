"""Growth service uses actual disposable PostgreSQL schemas, never production."""
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
from test_intent_radar_postgres import pg_radar,postgres,pytestmark
from test_intent_radar import source_result
from app.config.settings import get_settings
from app.platform.context import workspace_scope
from app.intent_radar import discovery,models as radar_models,connectors
from app.growth_intelligence import analytics,models,service,exports
from app.intelligence import jobs

def test_postgres_growth_persistence_scoping_revision_exports_and_existing_history(pg_radar,monkeypatch):
    c,org,other=pg_radar
    monkeypatch.setattr(get_settings(),'intent_radar_growth_enabled',True)
    monkeypatch.setattr(get_settings(),'intent_radar_ai_enabled',False)
    monkeypatch.setattr(connectors,'fetch',AsyncMock(return_value=source_result()))
    with workspace_scope(c,'radar-pg@example.test',org):
        discovered=discovery.create(c,radar_models.Discovery(configuration=radar_models.Search(keywords=['website'])));c.commit();jobs.execute(discovered['id'])
        assert analytics.overview(c,models.Scope())['sample_size']==1
        body=models.Start(title='PostgreSQL owned research')
        research=service.start(c,body);c.commit();jobs.execute(research['job_id'])
        result=service.detail(c,research['id']);assert result['status']=='COMPLETE'
        assert result['export_available'] and result['output']['mode'].startswith('Lexical')
        assert service.start(c,body)['id']==research['id']
        assert exports.render(c,research['id'],'csv')[0]
        theme=service.themes(c)['items'][0]
        saved=service.update_theme(c,theme['id'],models.ThemeUpdate(revision=theme['revision'],saved=True));c.commit()
        assert saved['saved_at']
        with pytest.raises(HTTPException):service.update_theme(c,theme['id'],models.ThemeUpdate(revision=theme['revision']))
        c.rollback()
    with workspace_scope(c,'radar-pg@example.test',other):
        with pytest.raises(HTTPException) as denied:exports.render(c,research['id'],'json')
        assert denied.value.status_code==404
        assert not service.listing(c)['items']

def test_postgres_assistant_real_reservation_private_history_and_recovery(pg_radar,monkeypatch):
    from types import SimpleNamespace
    from app.intent_radar import assistant
    c,org,other=pg_radar
    monkeypatch.setattr(get_settings(),'intent_radar_growth_enabled',True)
    monkeypatch.setattr(get_settings(),'intent_radar_ai_enabled',True)
    async def structured(instruction,payload,schema,**kwargs):
        ref=next(r for r in payload['references'] if r['id'].startswith('help:'))
        return schema(blocks=[{'kind':'Guidance','text':ref['text'][:100],'citations':[{'reference':ref['id'],'quote':ref['text'][:150]}]}])
    monkeypatch.setattr(assistant.ai,'provider',lambda _:SimpleNamespace(structured=structured,last_provider='SYNTHETIC'))
    with workspace_scope(c,'radar-pg@example.test',org):
        body=assistant.Turn(prompt='How can I review source evidence?')
        turn=assistant.start(c,body);c.commit();jobs.execute(turn['job_id'])
        result=service.detail(c,turn['id']);assert result['status']=='COMPLETE'
        assert assistant.start(c,body)['id']==turn['id']
        assert len(assistant.listing(c)['items'])==1 and len(assistant.history(c,turn['id'])['turns'])==1
        assert service.listing(c)['total']==0
        assert c.execute('SELECT calls FROM intent_analysis_usage WHERE organization_id=?',(org,)).fetchone()[0]==1
    with workspace_scope(c,'radar-pg@example.test',other):
        assert not assistant.listing(c)['items']
        with pytest.raises(HTTPException):assistant.history(c,turn['id'])

def test_postgres_assistant_count_reads_are_ai_free_and_do_not_create_jobs(pg_radar,monkeypatch):
    from app.intent_radar import assistant
    c,org,other=pg_radar
    monkeypatch.setattr(get_settings(),'intent_radar_growth_enabled',True)
    monkeypatch.setattr(assistant.ai,'provider',lambda _:(_ for _ in ()).throw(AssertionError('Counts must not infer')))
    with workspace_scope(c,'radar-pg@example.test',org):
        before=c.execute('SELECT COUNT(*) FROM intelligence_jobs').fetchone()[0]
        body=assistant.Turn(prompt='How many signals have I generated yet?')
        result=assistant.start(c,body);c.commit()
        assert result['job_id'] is None and result['snapshot']['facts']['stored_conversations']==0
        assert assistant.start(c,body)['id']==result['id']
        followup=assistant.start(c,assistant.Turn(prompt='And today?',thread_id=result['id']));c.commit()
        assert followup['snapshot']['facts']['date_basis']=='original publication date'
        assert len(assistant.history(c,result['id'])['turns'])==2
        assert c.execute('SELECT COUNT(*) FROM intelligence_jobs').fetchone()[0]==before
        assert c.execute('SELECT COUNT(*) FROM intent_analysis_usage').fetchone()[0]==0
    with workspace_scope(c,'radar-pg@example.test',other):
        with pytest.raises(HTTPException):assistant.history(c,result['id'])

def test_postgres_overview_summary_matches_scoped_counts_and_retention(pg_radar,monkeypatch):
    from app.intent_radar import service
    c,org,other=pg_radar
    monkeypatch.setattr(connectors,'fetch',AsyncMock(return_value=source_result()))
    with workspace_scope(c,'radar-pg@example.test',org):
        discovered=discovery.create(c,radar_models.Discovery(configuration=radar_models.Search(keywords=['website'])));c.commit();jobs.execute(discovered['id'])
        summary=service.overview(c,include_previews=False)
        assert summary['new_signals']==1 and summary['trends'][0]['volume']==1
        assert summary['operations']['jobs_by_status']==[{'status':'COMPLETED','count':1}]
        service.preferences(c,radar_models.Preferences(source_retention_days=1));c.commit()
        c.execute("UPDATE intent_signals SET retrieved_at='2000-01-01T00:00:00+00:00' WHERE organization_id=?",(org,));c.commit()
        assert service.overview(c,include_previews=False)['new_signals']==0
        assert service.listing(c,'signals')['total']==0
    with workspace_scope(c,'radar-pg@example.test',other):
        summary=service.overview(c,include_previews=False)
        assert summary['new_signals']==0 and summary['trends']==[] and summary['operations']['jobs_by_status']==[]


def test_postgres_overview_snapshot_equivalence_retention_and_tenant_scope(pg_radar):
    from test_overview_snapshot import snapshot_contract
    c,org,other=pg_radar
    snapshot_contract(c,org,other,'radar-pg@example.test')
