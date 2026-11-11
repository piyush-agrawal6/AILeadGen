"""Permanent regressions for source/context drift found by the product audit."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from test_intent_radar import radar, owned, run, source_result
from app.config.settings import get_settings
from app.database.connection import get_connection
from app.intent_radar import ai, intelligence, models, providers, service
from app.platform.context import workspace_scope


def test_draft_revocation_during_gateway_never_writes_cache(radar, monkeypatch):
    c, path, org, _ = radar
    monkeypatch.setattr(get_settings(), 'intent_radar_ai_enabled', True)

    async def structured(*args, **kwargs):
        second = get_connection(path)
        second.execute("UPDATE organization_memberships SET status='REVOKED' WHERE organization_id=?", (org,))
        second.commit()
        second.close()
        return models.SearchDraft(name='Reviewed proposal', configuration=models.Search(keywords=['website']))

    monkeypatch.setattr('app.acquisition.ai.provider', lambda c: SimpleNamespace(structured=structured))
    with workspace_scope(c, 'controlled@example.test', org):
        with pytest.raises(HTTPException) as denied:
            asyncio.run(ai.draft(c, models.Prompt(prompt='Find website development recommendations')))
        assert denied.value.status_code == 403
    assert c.execute("SELECT COUNT(*) FROM acquisition_ai_cache WHERE task='INTENT_RADAR_DRAFT_V2'").fetchone()[0] == 0


def test_monitor_edit_during_analysis_never_returns_or_persists_stale_context(radar, monkeypatch):
    c, path, org, _ = radar
    monkeypatch.setattr(get_settings(), 'intent_radar_ai_enabled', True)
    monkeypatch.setattr(providers.HackerNews, 'fetch', AsyncMock(return_value=source_result()))
    with workspace_scope(c, 'controlled@example.test', org):
        monitor = service.save_monitor(c, models.Monitor(name='Context test', configuration=models.Search(keywords=['website']), status='Active'))
        from app.intent_radar import discovery
        from app.intelligence import jobs
        job = discovery.create(c, models.Discovery(configuration=monitor['configuration'], monitor_id=monitor['id']))
        c.commit()
        jobs.execute(job['id'], path)
        signal = service.listing(c, 'signals')['items'][0]

        async def structured(*args, **kwargs):
            second = get_connection(path)
            second.execute('UPDATE intent_monitors SET revision=revision+1 WHERE organization_id=? AND id=?', (org, monitor['id']))
            second.commit()
            second.close()
            return intelligence.Interpretation(categories=['General discussion'])

        monkeypatch.setattr('app.acquisition.ai.provider', lambda c: SimpleNamespace(structured=structured))
        with pytest.raises(HTTPException) as denied:
            asyncio.run(intelligence.analyze(c, signal['id'], models.AnalysisRequest(monitor_id=monitor['id'])))
        assert denied.value.status_code == 409
        assert c.execute('SELECT COUNT(*) FROM intent_analyses').fetchone()[0] == 0


def test_analysis_cache_identity_includes_vertex_project_and_location(monkeypatch):
    from test_intent_radar import example
    from app.acquisition.config import AcquisitionSettings
    config = AcquisitionSettings(_env_file=None)
    monkeypatch.setattr('app.acquisition.config.settings', lambda: config)
    original = intelligence.input_hash(example(), {}, None)
    config.vertex_project = 'another-approved-project'
    assert intelligence.input_hash(example(), {}, None) != original
    changed = intelligence.input_hash(example(), {}, None)
    config.vertex_location = 'us-central1'
    assert intelligence.input_hash(example(), {}, None) != changed


@pytest.mark.parametrize('title,excerpt', [
    ('Open-source messaging software alternatives', 'General discussion comparing tools; no purchase plans.'),
    ('CoderPad reports a security breach', 'A security advisory about software and developer tools.'),
    ('Show HN: A new alternative software tool', 'Check out my new product.'),
    ('A software company is hiring engineers', 'A public job opening, not a vendor request.'),
    ('Our invoicing software is frustrating', 'We are not looking to buy anything.'),
    ('Comparison of software alternatives', 'An industry news analysis of software tools.'),
])
def test_topical_noncommercial_content_does_not_get_high_intent(title, excerpt):
    from test_intent_radar import example
    from app.intent_radar.classification import classify
    signal = classify({**example(), 'title': title, 'excerpt': excerpt}, models.Search(keywords=['software','tool','alternative','security','invoicing']))
    assert signal is not None
    assert signal['score'] <= 60 and signal['category'] == 'General discussion'
    assert not signal['evidence']['intent_phrase']


@pytest.mark.parametrize('title', [
    'Can anyone recommend software for our business?',
    'We are comparing software alternatives for our team',
    'Looking for an alternative to our current software vendor',
])
def test_explicit_vendor_requests_remain_distinct_from_general_discussion(title):
    from test_intent_radar import example
    from app.intent_radar.classification import classify
    signal = classify({**example(), 'title': title, 'excerpt': 'Our team wants recommendations for a replacement.'}, models.Search(keywords=['software']))
    assert signal is not None and signal['category'] != 'General discussion'
    assert signal['evidence']['intent_phrase']


def test_each_read_only_radar_tool_returns_owned_records_and_rejects_foreign_ids(radar, monkeypatch):
    from app.intent_radar import tools
    c, path, org, other = radar
    monkeypatch.setattr(providers.HackerNews, 'fetch', AsyncMock(return_value=source_result()))
    c.execute("UPDATE organization_products SET enabled=1 WHERE organization_id=? AND product='INTENT_RADAR'", (other,))
    c.commit()
    with workspace_scope(c, 'controlled@example.test', org):
        monitor = service.save_monitor(c, models.Monitor(name='Tool contracts', configuration=models.Search(keywords=['website']), status='Active'))
        job = run(c, path, models.Search(keywords=['website']), monitor['id'])
        signal = service.listing(c, 'signals')['items'][0]
        opportunity = service.opportunity(c, signal['id'])
        cases = {
            'search_intent_signals': {'search':'website'},
            'list_intent_monitors': {},
            'get_intent_signal': {'id':signal['id']},
            'list_intent_opportunities': {},
            'list_intent_sources': {},
            'get_intent_analysis': {'id':signal['id']},
            'get_intent_run': {'id':job['id']},
        }
        assert set(cases)==set(tools.READ)
        for tool, arguments in cases.items():
            output = tools.read(c, tool, arguments)
            assert isinstance(output, dict)
            if tool in ('search_intent_signals','list_intent_monitors','list_intent_opportunities'):
                assert output['total']==1
            if tool=='list_intent_sources':assert len(output['items'])==4
            if tool=='get_intent_signal':assert output['id']==signal['id']
            if tool=='get_intent_run':assert output['id']==job['id']
            if tool=='get_intent_analysis':assert output['items']==[]
        assert service.get(c, 'opportunities', opportunity['id'])['signal_id']==signal['id']
    with workspace_scope(c, 'foreign@example.test', other):
        for tool in ('get_intent_signal','get_intent_analysis','get_intent_run'):
            with pytest.raises(HTTPException) as denied:
                tools.read(c, tool, cases[tool])
            assert denied.value.status_code==404
        with pytest.raises(HTTPException) as denied:service.get(c, 'opportunities', opportunity['id'])
        assert denied.value.status_code==404


def test_process_restart_recovers_committed_source_without_duplicate_fetch(radar, monkeypatch):
    import os
    import subprocess
    import sys
    import time
    from app.intent_radar import discovery
    c, path, org, _ = radar
    monkeypatch.setattr(get_settings(), 'intent_radar_stackexchange_enabled', True)
    with workspace_scope(c, 'controlled@example.test', org):
        queued=discovery.create(c, models.Discovery(configuration=models.Search(keywords=['website'],sources=['hacker_news','stack_exchange'])))
        c.commit()
        descriptor=c.execute('SELECT id FROM intent_discoveries WHERE organization_id=?', (org,)).fetchone()['id']
    code = '''
import asyncio,sys,time
from app.config.settings import get_settings
from app.intent_radar import connectors,providers
from app.intelligence import jobs
s=get_settings();s.app_env='test';s.database_path=sys.argv[1];s.intent_radar_stage='Beta';s.intent_radar_stackexchange_enabled=True;s.allowed_user_emails='controlled@example.test,foreign@example.test'
async def fetch(c,q,key,permit):
    permit()
    if key=='hacker_news' and sys.argv[3]=='resume':raise RuntimeError('Completed HN source must never be refetched on recovery')
    if key=='stack_exchange' and sys.argv[3]=='crash':await asyncio.sleep(120)
    raw=providers.normalize({'id':998881 if key=='hacker_news' else 998882,'type':'story','time':int(time.time()),'title':'Can anyone recommend website software for our business?','text':'Looking for a website development partner.'})
    if key=='stack_exchange':raw.update(source='Stack Exchange',source_url='https://stackoverflow.com/questions/998882')
    return {'items':[raw],'requests':1,'scanned':1,'next_offset':None,'coverage':'SYNTHETIC process restart transport','synthetic':True}
connectors.fetch=fetch
jobs.execute(sys.argv[2],sys.argv[1])
'''
    env={**os.environ,'APP_ENV':'test','DATABASE_BACKEND':'sqlite','DATABASE_URL':'','EMAIL_SENDING_ENABLED':'false'}
    process=subprocess.Popen([sys.executable,'-c',code,str(path),queued['id'],'crash'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    try:
        for _ in range(200):
            result=c.execute("SELECT status FROM intent_source_runs WHERE organization_id=? AND discovery_id=? AND provider='hacker_news'", (org,descriptor)).fetchone()
            if result and result['status']=='COMPLETE':break
            if process.poll() is not None:pytest.fail('Crash worker exited before checkpoint: '+process.stderr.read().decode())
            time.sleep(.05)
        else:pytest.fail('First source did not durably checkpoint before simulated crash')
    finally:
        process.kill();process.wait(timeout=5)
    # Controllable lease clock, only this isolated owned job.
    c.execute("UPDATE intelligence_jobs SET lease_until='2000-01-01' WHERE id=? AND organization_id=?", (queued['id'],org));c.commit()
    restarted=subprocess.run([sys.executable,'-c',code,str(path),queued['id'],'resume'],env=env,capture_output=True,text=True,timeout=30)
    assert restarted.returncode==0, restarted.stderr
    with workspace_scope(c,'controlled@example.test',org):
        job=discovery.owned_job(c,queued['id'])
        assert job['status']=='COMPLETED' and job['attempts']==2
        assert {r['status'] for r in job['sources']}=={'COMPLETE'}
        assert service.listing(c,'signals')['total']==2
