"""Read budgets count statements, not fabricated wall-clock SLAs."""
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
  assert len(q.statements)==3

def test_rank_batches_are_bounded_and_cannot_cross_workspace(radar):
 c,path,org,other=radar
 from fastapi import HTTPException
 import pytest
 with workspace_scope(c,'controlled@example.test',org):
  with pytest.raises(HTTPException):service.ranked_signals(c,[{'organization_id':other,'id':'foreign'}])

def test_summary_does_not_hydrate_preview_lists_or_request_sources(radar,monkeypatch):
 c,path,org,_=radar
 with workspace_scope(c,'controlled@example.test',org):
  monkeypatch.setattr(service,'listing',lambda *args,**kwargs:(_ for _ in ()).throw(AssertionError('No previews in summary')))
  monkeypatch.setattr(operations,'source_health',lambda _:(_ for _ in ()).throw(AssertionError('No provider health in summary')))
  q=Counted(c);result=service.overview(q,include_previews=False)
  assert result['new_signals']==0 and result['preview_state']=='not requested'
  assert 'recent_signals' not in result and len(q.statements)==2


def test_monitor_page_has_constant_query_count(radar):
 c,path,org,_=radar
 with workspace_scope(c,'controlled@example.test',org):
  for index in range(5):service.save_monitor(c,models.Monitor(name='Bounded monitor '+str(index),configuration=models.Search(keywords=['website'])))
  q=Counted(c);result=service.listing(q,'monitors',size=5)
  assert len(result['items'])==5 and len(q.statements)==3
  assert all(r['organization_id']==org and 'fingerprint' not in r for r in result['items'])
