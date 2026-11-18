"""Comprehensive unit/integration tests for all 7 Intent Radar source families."""
import asyncio, hashlib, hmac, json, uuid
from datetime import datetime, timezone
import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException
from pydantic import SecretStr

from app.config.settings import get_settings
from app.intent_radar import connectors, models, service, intelligence
from app.intent_radar.bluesky_source import _apply_jetstream_delete, _apply_jetstream_post
from app.intent_radar.feeds import CURATED_FEED_PRESETS, APPROVED_PRESET_HOSTS
from app.intent_radar.github_source import (
    connection_status,
    start_oauth,
    complete_oauth,
    update_repositories,
    disconnect,
    ingest_webhook,
)
from app.platform.context import workspace_scope
from test_intent_radar import radar, owned  # noqa: F401 - pytest fixtures


def _sign_github(body: bytes, secret: str) -> str:
    return 'sha256=' + hmac.new(secret.encode('utf-8'), body, hashlib.sha256).hexdigest()


def test_catalog_exposes_all_seven_source_families_truthfully(radar, monkeypatch):
    c, _, org, _ = radar
    s = get_settings()
    monkeypatch.setattr(s, 'intent_radar_sources_v2_enabled', True)
    monkeypatch.setattr(s, 'intent_radar_stackexchange_enabled', True)
    monkeypatch.setattr(s, 'intent_radar_stackexchange_sites', 'stackoverflow;serverfault;devops;ai')
    monkeypatch.setattr(s, 'intent_radar_github_enabled', True)
    monkeypatch.setattr(s, 'intent_radar_github_public_search_enabled', True)
    monkeypatch.setattr(s, 'github_app_id', '5786999')
    monkeypatch.setattr(s, 'github_app_installation_id', '182639090')
    monkeypatch.setattr(s, 'github_app_private_key', SecretStr('fake-pem'))
    monkeypatch.setattr(s, 'intent_radar_youtube_enabled', True)
    monkeypatch.setattr(s, 'intent_radar_youtube_search_enabled', True)
    monkeypatch.setattr(s, 'youtube_api_key', SecretStr('fake-yt-key'))
    monkeypatch.setattr(s, 'intent_radar_bluesky_enabled', True)
    monkeypatch.setattr(s, 'intent_radar_bluesky_jetstream_enabled', True)

    with workspace_scope(c, 'controlled@example.test', org):
        items = {x['id']: x for x in connectors.catalog(c)}
        for key in ('hacker_news', 'stack_exchange', 'github', 'youtube', 'bluesky', 'discourse', 'atom', 'rss'):
            assert key in items
        assert items['hacker_news']['state'] == 'Available'
        assert items['stack_exchange']['state'] == 'Available'
        assert items['stack_exchange']['configured_sites'] == ['stackoverflow', 'serverfault', 'devops', 'ai']
        assert items['github']['state'] == 'Available'
        assert items['youtube']['state'] == 'Available'
        assert items['youtube']['ai_analytics_authorized'] is False
        assert items['bluesky']['state'] == 'Available'
        assert items['bluesky']['jetstream_enabled'] is True
        assert items['discourse']['state'] == 'Not configured'
        assert items['atom']['state'] == 'Not configured'


def test_github_oauth_repo_selection_disconnect_and_tenant_isolation(radar, monkeypatch):
    c, _, org_a, org_b = radar
    s = get_settings()
    monkeypatch.setattr(s, 'intent_radar_sources_v2_enabled', True)
    monkeypatch.setattr(s, 'heysow_integration_encryption_key', Fernet.generate_key().decode())
    monkeypatch.setattr(s, 'github_app_client_id', 'Iv23testclient')
    monkeypatch.setattr(s, 'github_app_client_secret', SecretStr('test-client-secret'))
    monkeypatch.setattr(s, 'github_app_slug', 'planebyte-intent-radar')

    async def fake_request(self, path, *, params=None, method='GET', body=None, headers=None):
        if path == '/login/oauth/access_token':
            return {'access_token': 'ghu_test_token', 'refresh_token': 'ghr_test_refresh', 'expires_in': 28800, 'token_type': 'bearer'}
        if path == '/user':
            return {'id': 42, 'login': 'planebytelabs'}
        if path == '/user/installations':
            return {'installations': [{'id': 182639090, 'account': {'login': 'Planebyte-Labs', 'type': 'Organization'}, 'permissions': {'issues': 'read', 'contents': 'read'}}]}
        if path == '/user/installations/182639090/repositories':
            return {'repositories': [
                {'id': 101, 'full_name': 'Planebyte-Labs/private-repo', 'private': True},
                {'id': 102, 'full_name': 'Planebyte-Labs/public-repo', 'private': False},
            ]}
        raise AssertionError(f'Unexpected GitHub request: {path}')

    from app.intent_radar.source_http import JsonClient
    monkeypatch.setattr(JsonClient, 'request', fake_request)

    with workspace_scope(c, 'controlled@example.test', org_a):
        started = start_oauth(c)
        assert 'github.com/login/oauth/authorize' in started['authorize_url']
        assert 'planebyte-intent-radar/installations/new' in started['install_url']
        state = started['authorize_url'].split('state=')[1].split('&')[0]
        c.commit()

        connected = asyncio.run(complete_oauth(c, code='gh-code-123', state=state, installation_id='182639090'))
        assert connected['status'] == 'CONNECTED'
        assert connected['installation_id'] == '182639090'
        assert connected['account_login'] == 'Planebyte-Labs'
        assert len(connected['repositories']) == 2

        # Replay MUST fail with 409
        with pytest.raises(HTTPException) as replay_err:
            asyncio.run(complete_oauth(c, code='gh-code-123', state=state, installation_id='182639090'))
        assert replay_err.value.status_code == 409

        # Repo selection & unauthorized repo rejection
        updated = update_repositories(c, [101])
        assert [r['id'] for r in updated['repositories'] if r['selected']] == [101]
        with pytest.raises(HTTPException) as bad_repo:
            update_repositories(c, [99999])
        assert bad_repo.value.status_code == 403

    # Foreign workspace MUST NOT see org_a's GitHub connection
    foreign_actor = c.execute("SELECT user_id FROM organization_memberships WHERE organization_id=? LIMIT 1", (org_b,)).fetchone()['user_id']
    c.execute("INSERT INTO organization_products(organization_id,product,enabled,created_at,updated_at) VALUES(?,'INTENT_RADAR',1,'2026-11-18T00:00:00+00:00','2026-11-18T00:00:00+00:00') ON CONFLICT(organization_id,product) DO UPDATE SET enabled=1", (org_b,))
    with workspace_scope(c, foreign_actor, org_b):
        assert connection_status(c)['status'] == 'NOT_CONNECTED'

    with workspace_scope(c, 'controlled@example.test', org_a):
        # Disconnect clears installation & encrypted credentials
        disc = disconnect(c)
        assert disc['status'] == 'DISCONNECTED'
        assert disc['installation_id'] is None
        row = c.execute('SELECT credentials_ciphertext FROM intent_github_connections WHERE organization_id=?', (org_a,)).fetchone()
        assert row['credentials_ciphertext'] is None


def test_github_webhook_hmac_dedup_ingestion_and_revocation(radar, monkeypatch):
    c, _, org, _ = radar
    s = get_settings()
    secret = 'whsec_test_github_secret_123'
    monkeypatch.setattr(s, 'intent_radar_sources_v2_enabled', True)
    monkeypatch.setattr(s, 'heysow_integration_encryption_key', Fernet.generate_key().decode())
    monkeypatch.setattr(s, 'intent_radar_github_enabled', True)
    monkeypatch.setattr(s, 'intent_radar_github_public_search_enabled', True)
    monkeypatch.setattr(s, 'intent_radar_github_webhooks_enabled', True)
    monkeypatch.setattr(s, 'github_app_webhook_secret', SecretStr(secret))
    monkeypatch.setattr(s, 'github_app_id', '5786999')
    monkeypatch.setattr(s, 'github_app_installation_id', '182639090')
    monkeypatch.setattr(s, 'github_app_private_key', SecretStr('fake-pem'))

    with workspace_scope(c, 'controlled@example.test', org):
        ts = datetime.now(timezone.utc).isoformat()
        c.execute(
            "INSERT INTO intent_github_connections(id,organization_id,owner_user_id,installation_id,account_login,account_type,status,permissions_json,repositories_json,revision,created_at,updated_at) VALUES(?,?,?,'182639090','Planebyte-Labs','Organization','CONNECTED','{}','[]',1,?,?)",
            (str(uuid.uuid4()), org, 'controlled@example.test', ts, ts),
        )
        service.save_monitor(c, models.Monitor(
            name='GitHub Monitor', status='Active',
            configuration=models.Search(keywords=['crm', 'alternative'], sources=['github'], github_repos=['Planebyte-Labs/app']),
        ))
        c.commit()

        issue_payload = json.dumps({
            'action': 'opened',
            'installation': {'id': 182639090},
            'repository': {'full_name': 'Planebyte-Labs/app', 'private': False},
            'issue': {
                'id': 77701,
                'html_url': 'https://github.com/Planebyte-Labs/app/issues/1',
                'title': 'Looking for a CRM alternative for automation',
                'body': 'We need a better CRM alternative with workflow sync.',
                'created_at': ts,
                'user': {'login': 'founder1', 'html_url': 'https://github.com/founder1'},
                'labels': [{'name': 'enhancement'}],
            },
        }).encode('utf-8')
        with pytest.raises(HTTPException) as bad_sig:
            ingest_webhook(c, raw_body=issue_payload, delivery_id='deliv-1', event_type='issues', signature='sha256=deadbeef')
        assert bad_sig.value.status_code == 401

        sig = _sign_github(issue_payload, secret)
        first = ingest_webhook(c, raw_body=issue_payload, delivery_id='deliv-1', event_type='issues', signature=sig)
        assert first['status'] == 'COMPLETE'
        dup = ingest_webhook(c, raw_body=issue_payload, delivery_id='deliv-1', event_type='issues', signature=sig)
        assert dup['status'] == 'DUPLICATE'

        sigs = service.listing(c, 'signals', source='GitHub')['items']
        assert len(sigs) == 1 and 'CRM alternative' in sigs[0]['title']

        revoke_payload = json.dumps({'action': 'deleted', 'installation': {'id': 182639090}}).encode('utf-8')
        rev = ingest_webhook(c, raw_body=revoke_payload, delivery_id='deliv-2', event_type='installation', signature=_sign_github(revoke_payload, secret))
        assert rev['status'] == 'COMPLETE'
        assert connection_status(c)['status'] == 'REVOKED'


def test_youtube_fair_usage_comments_disabled_and_ai_policy_gate(radar, monkeypatch):
    c, _, org, _ = radar
    s = get_settings()
    monkeypatch.setattr(s, 'intent_radar_sources_v2_enabled', True)
    monkeypatch.setattr(s, 'intent_radar_youtube_enabled', True)
    monkeypatch.setattr(s, 'intent_radar_youtube_search_enabled', True)
    monkeypatch.setattr(s, 'intent_radar_youtube_comments_enabled', True)
    monkeypatch.setattr(s, 'intent_radar_youtube_ai_analytics_enabled', False)
    monkeypatch.setattr(s, 'intent_radar_ai_enabled', True)
    monkeypatch.setattr(s, 'youtube_api_key', SecretStr('fake-yt-key'))
    monkeypatch.setattr(s, 'youtube_workspace_daily_search_limit', 1)

    now_iso = datetime.now(timezone.utc).isoformat()
    from app.intent_radar.source_http import JsonClient, ProviderFailure

    async def fake_yt(self, path, *, params=None, method='GET', body=None, headers=None):
        if path == '/search':
            return {'items': [{'id': {'videoId': 'vid123'}, 'snippet': {'title': 'Looking for workflow automation tool'}}]}
        if path == '/videos':
            return {'items': [{
                'id': 'vid123',
                'snippet': {'title': 'Looking for workflow automation tool', 'description': 'Comparing n8n vs alternatives', 'publishedAt': now_iso, 'channelId': 'ch1', 'channelTitle': 'Tech Reviews'},
                'statistics': {'viewCount': '1200', 'likeCount': '40', 'commentCount': '0'},
            }]}
        if path == '/commentThreads':
            raise ProviderFailure('COMMENTS_DISABLED', status=403)
        raise AssertionError(f'Unexpected YouTube path: {path}')

    monkeypatch.setattr(JsonClient, 'request', fake_yt)
    with workspace_scope(c, 'controlled@example.test', org):
        q = models.Search(keywords=['workflow', 'automation'], sources=['youtube'], youtube_comments=True)
        res = asyncio.run(connectors.fetch(c, q, 'youtube', lambda: True))
        assert len(res.items) == 1
        assert res.items[0]['source'] == 'YouTube'
        assert res.items[0]['provenance']['retention_days'] == 30
        assert res.items[0]['provenance']['ai_processing_authorized'] is False
        assert 'comments disabled' in res.coverage

        c.execute(
            'INSERT INTO intent_signals(id,organization_id,source,source_record_id,source_url,title,excerpt,observed_at,retrieved_at,category,score,evidence_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
            (str(uuid.uuid4()), org, 'YouTube', 'video:vid123', res.items[0]['source_url'], res.items[0]['title'], res.items[0]['excerpt'], now_iso, now_iso, 'Product comparison', 70, json.dumps({'provenance': res.items[0]['provenance'], 'matched_keywords': ['workflow']})),
        )
        sig_id = c.execute("SELECT id FROM intent_signals WHERE organization_id=? AND source='YouTube'", (org,)).fetchone()['id']
        analyzed = asyncio.run(intelligence.analyze(c, sig_id, models.AnalysisRequest()))
        assert analyzed['mode'] == 'Policy gated'
        assert 'YouTube API policy approval' in analyzed['fallback_reason']


def test_bluesky_jetstream_matching_and_delete_propagation(radar, monkeypatch):
    c, _, org, _ = radar
    s = get_settings()
    monkeypatch.setattr(s, 'intent_radar_sources_v2_enabled', True)
    monkeypatch.setattr(s, 'intent_radar_bluesky_enabled', True)
    monkeypatch.setattr(s, 'intent_radar_bluesky_jetstream_enabled', True)
    now_iso = datetime.now(timezone.utc).isoformat()

    with workspace_scope(c, 'controlled@example.test', org):
        mon = service.save_monitor(c, models.Monitor(
            name='Bluesky CRM Monitor', status='Active',
            configuration=models.Search(keywords=['crm'], sources=['bluesky']),
        ))
        c.commit()
        monitors = [{'monitor_id': mon['id'], 'organization_id': org, 'created_by': 'controlled@example.test', 'configuration': mon['configuration'], 'keywords': ['crm'], 'excluded': []}]
        matched = _apply_jetstream_post(c, monitors, did='did:plc:abc123', rkey='post99', text_body='We are looking for a CRM recommendation for our agency.', created_at=now_iso, seq=5001)
        assert matched == 1
        sigs = service.listing(c, 'signals', source='Bluesky')['items']
        assert len(sigs) == 1

        removed = _apply_jetstream_delete(c, did='did:plc:abc123', rkey='post99', seq=5002)
        assert removed >= 2
        sigs_after = service.listing(c, 'signals', source='Bluesky')['items']
        assert len(sigs_after) == 0


def test_atom_release_and_paper_classified_as_market_intelligence_not_buyer(radar, monkeypatch):
    c, _, org, _ = radar
    s = get_settings()
    monkeypatch.setattr(s, 'intent_radar_sources_v2_enabled', True)
    monkeypatch.setattr(s, 'intent_radar_approved_feed_hosts', ';'.join(APPROVED_PRESET_HOSTS))
    assert len([p for p in CURATED_FEED_PRESETS if p['family'] == 'discourse']) == 10
    assert len([p for p in CURATED_FEED_PRESETS if p['family'] == 'atom']) == 10

    import socket
    monkeypatch.setattr(socket, 'getaddrinfo', lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('140.82.121.4', 443))])

    with workspace_scope(c, 'controlled@example.test', org):
        enabled = connectors.enable_preset(c, 'atom-nextjs', enabled=True)
        assert enabled['family'] == 'atom' and enabled['enabled'] is True
        from app.intent_radar import classification, opportunity_policy
        raw = connectors.normalized(
            'Atom', 'atom-nextjs:v16', 'https://github.com/vercel/next.js/releases/tag/v16',
            'Next.js v16.0.0 release', 'New caching APIs and Turbopack updates.', datetime.now(timezone.utc).isoformat(),
            fetch_method='public_feed', feed_format='atom', content_kind='release', ai_processing_authorized=True,
        )
        classified = classification.classify(raw, models.Search(keywords=['next.js'], sources=['atom'], feed_ids=[uuid.UUID(enabled['id'])]))
        assert classified['category'] == 'Market / technology intelligence'
        opp = opportunity_policy.assess({**classified, 'available': 1})
        assert opp['eligible'] is False
        assert any('market/technology intelligence' in r.lower() for r in opp['reasons'])
