import asyncio
import sqlite3
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
from pydantic import BaseModel
from app.database.migrations import run_migrations
from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID as INTERNAL
from app.api.organization import create_organization
from app.platform.context import workspace_scope
from app.acquisition.preferences import load,save
from app.acquisition.ai import cached


class Result(BaseModel):
    answer:str


@pytest.fixture
def tenants():
    c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row;run_migrations(c)
    actor=c.execute('SELECT created_by_user_id FROM organizations WHERE id=?',(INTERNAL,)).fetchone()[0]
    other=create_organization(c,actor,'Second acquisition workspace')['organization_id']
    yield c,actor,other
    c.close()


def test_preferences_and_budget_controls_do_not_cross_workspaces(tenants):
    c,actor,other=tenants
    with pytest.raises(HTTPException):load(c)
    with workspace_scope(c,actor,INTERNAL):
        save(c,actor,{'enabled':{'firecrawl':False},'budgets':{'max_searches':2},'ai_providers':{'secret':'not a workspace preference'}})
        assert load(c)=={'enabled':{'firecrawl':False},'budgets':{'max_searches':2}}
    with workspace_scope(c,actor,other):
        assert load(c)=={}
        save(c,actor,{'enabled':{'firecrawl':True},'budgets':{'max_searches':4}})
    with workspace_scope(c,actor,INTERNAL):assert load(c)['enabled']['firecrawl'] is False
    assert c.execute('SELECT COUNT(*) FROM organization_acquisition_preferences').fetchone()[0]==2


def test_same_actor_same_input_never_reuses_another_workspaces_ai_cache(tenants):
    c,actor,other=tenants;calls=[]
    async def produce():calls.append(1);return Result(answer='Controlled output '+str(len(calls)))
    async def run():
        with pytest.raises(HTTPException):await cached(c,actor,'ICP_PREVIEW',{'prompt':'same'},produce,Result)
        assert not calls
        with workspace_scope(c,actor,INTERNAL):
            first,hit=await cached(c,actor,'ICP_PREVIEW',{'prompt':'same'},produce,Result);assert not hit
            again,hit=await cached(c,actor,'ICP_PREVIEW',{'prompt':'same'},produce,Result);assert hit and again==first
        with workspace_scope(c,actor,other):
            second,hit=await cached(c,actor,'ICP_PREVIEW',{'prompt':'same'},produce,Result);assert not hit and second!=first
            c.execute('UPDATE acquisition_ai_cache SET expires_at=? WHERE organization_id=?',('2000-01-01',INTERNAL));c.commit()
            await cached(c,actor,'ICP_PREVIEW',{'prompt':'another'},produce,Result)
            assert c.execute('SELECT COUNT(*) FROM acquisition_ai_cache WHERE organization_id=?',(INTERNAL,)).fetchone()[0]==1
    asyncio.run(run())
    assert len(calls)==3


def test_customer_cannot_use_internal_sheets_connection_even_with_same_actor(tenants,monkeypatch):
    c,actor,other=tenants
    from app.acquisition import sheets
    network=AsyncMock();monkeypatch.setattr(sheets,'token_request',network)
    with workspace_scope(c,actor,other):
        with pytest.raises(HTTPException):sheets.start(c,actor)
        with pytest.raises(HTTPException):asyncio.run(sheets.connect(c,actor,'state','code'))
        with pytest.raises(HTTPException):asyncio.run(sheets.access_token(c,actor))
    network.assert_not_called()


def test_internal_archive_domain_guard_cannot_be_enabled_for_customer(tenants,monkeypatch):
    c,actor,other=tenants
    from app.platform import modules
    monkeypatch.setattr(modules,'legacy_enabled',lambda:True)
    with workspace_scope(c,actor,INTERNAL):modules.require_legacy()
    with workspace_scope(c,actor,other):
        with pytest.raises(HTTPException) as denied:modules.require_legacy()
        assert denied.value.status_code==404


def test_customer_copy_generation_cannot_touch_internal_cache_or_provider(tenants):
    c,actor,other=tenants
    from app.experiments.copy_batch import generate_personalized_copy_batch
    provider=AsyncMock()
    with workspace_scope(c,actor,other):
        before=c.total_changes
        with pytest.raises(HTTPException):asyncio.run(generate_personalized_copy_batch(c,[],actor,client=provider))
        assert c.total_changes==before
    provider.assert_not_called()
