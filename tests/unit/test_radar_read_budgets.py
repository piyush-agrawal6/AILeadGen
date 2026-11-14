"""Read budgets are SQL round trips, not fabricated wall-clock SLAs."""
import asyncio
from unittest.mock import AsyncMock
from test_intent_radar import radar,owned,source_result,run
from app.platform.context import workspace_scope
from app.intent_radar import service,models,providers,operations
class Counted:
 def __init__(self,c):self.c=c;self.statements=[]
 def __getattr__(self,k):return getattr(self.c,k)
 def execute(self,sql,args=()):self.statements.append(sql);return self.c.execute(sql,args)
def test_read_budgets_and_no_source_checks_in_overview(radar,monkeypatch,record_property):
 c,path,org,_=radar
 monkeypatch.setattr(providers.HackerNews,'fetch',AsyncMock(return_value=source_result()))
 with workspace_scope(c,'controlled@example.test',org):
  run(c,path,models.Search(keywords=['website']));q=Counted(c)
  health=operations.source_health(q);assert len(health['items'])==4
  record_property('source_health_sql',len(q.statements));assert len(q.statements)<=7
  monkeypatch.setattr(operations,'source_health',lambda _:(_ for _ in ()).throw(AssertionError('Overview must not block on source health')))
  q=Counted(c);value=service.overview(q)
  record_property('overview_sql',len(q.statements));assert value['new_signals']==1
  assert len(q.statements)<=40

def test_rank_batches_are_bounded_and_cannot_cross_workspace(radar):
 c,path,org,other=radar
 from fastapi import HTTPException
 import pytest
 with workspace_scope(c,'controlled@example.test',org):
  with pytest.raises(HTTPException):service.ranked_signals(c,[{'organization_id':other,'id':'foreign'}])
