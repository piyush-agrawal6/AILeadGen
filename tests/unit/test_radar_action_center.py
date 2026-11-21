import uuid
from datetime import datetime,timezone,timedelta
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
from app.config.settings import get_settings
from app.platform.context import workspace_scope
from app.intent_radar import actions,models,service,providers
from test_prospecting_only import owned
from test_intent_radar import radar,run,source_result


def test_review_followup_once_record_outcome_and_deny_foreign(radar,monkeypatch):
    c,path,org,other=radar;actor='controlled@example.test';monkeypatch.setattr(providers.HackerNews,'fetch',AsyncMock(return_value=source_result()))
    with workspace_scope(c,actor,org):
        with pytest.raises(HTTPException) as disabled:actions.listing(c,None,25,0)
        assert disabled.value.status_code==404
        monkeypatch.setattr(get_settings(),'radar_actions_enabled',True)
        run(c,path,models.Search(keywords=['website']));signal=service.listing(c,'signals')['items'][0];op=service.opportunity(c,signal['id']);c.commit()
        draft=actions.Draft(request_id=uuid.uuid4(),opportunity_id=op['id'],title='Review evidence',description='Internal follow-up.',owner=actor,priority='high',due_at=datetime.now(timezone.utc)+timedelta(days=1))
        row=actions.prepare(c,draft);assert actions.prepare(c,draft)['id']==row['id'] and row['task_status'] is None
        with pytest.raises(HTTPException):actions.prepare(c,draft.model_copy(update={'title':'Different'}))
        with pytest.raises(HTTPException):actions.decide(c,row['id'],'approve',actions.Approval(digest='0'*64))
        approve=actions.Approval(digest=row['digest']);key=row['id']
        for _ in range(2):assert actions.decide(c,key,'approve',approve)['task_status']=='OPEN'
        c.commit();assert c.execute('select count(*) from radar_followups').fetchone()[0]==1
        assert actions.complete(c,key,actions.Outcome(note='Reviewed by owner'))['task_status']=='DONE';c.commit()
        assert len(actions.listing(c,'DONE',25,0)['items'])==1
        pending=actions.prepare(c,draft.model_copy(update={'request_id':uuid.uuid4()}));c.execute('update intent_signals set available=0 where id=?',(signal['id'],));c.commit()
        with pytest.raises(HTTPException):actions.decide(c,pending['id'],'approve',actions.Approval(digest=pending['digest']))
        c.rollback()
    c.execute("UPDATE organization_products SET enabled=1 WHERE organization_id=? AND product='INTENT_RADAR'",(other,));c.commit()
    with workspace_scope(c,'foreign@example.test',other):
        assert not actions.listing(c,None,25,0)['items']
        with pytest.raises(HTTPException) as absent:actions.complete(c,key,actions.Outcome(note='foreign'))
        assert absent.value.status_code==404
