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
