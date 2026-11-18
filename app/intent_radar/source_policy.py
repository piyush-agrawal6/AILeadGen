"""Centralized, auditable Source Permission Engine & live connectivity/feed testers.

Enforces provider and publisher capability policies server-side.
Never allows client-supplied flags to bypass unverified external policy gates.
"""
from __future__ import annotations

import time
from urllib.parse import urlsplit
from fastapi import HTTPException

from app.config.settings import get_settings
from app.database.prospects import now
from app.intent_radar import feeds
from app.utils.http import SafeAsyncClient


def _preset_by_endpoint() -> dict[str, dict]:
    return {p['endpoint']: p for p in feeds.CURATED_FEED_PRESETS}


def provider_policy(provider_id: str) -> dict:
    s = get_settings()
    yt_ai = bool(s.intent_radar_youtube_ai_analytics_enabled)
    yt_cross = bool(s.intent_radar_youtube_cross_source_analytics_enabled)

    policies: dict[str, dict] = {
        'hacker_news': {
            'provider_id': 'hacker_news',
            'publisher': 'Y Combinator / Hacker News',
            'authorized_app': 'PlaneByte Intent Radar (Public API Client)',
            'authorization_reference': 'Official Hacker News Firebase v0 Public API (https://github.com/HackerNews/API)',
            'commercial_use_authorized': True,
            'ai_processing_authorized': True,
            'ai_status': 'Authorized',
            'capabilities': {
                'fetch': True,
                'search': True,
                'store': True,
                'display': True,
                'classify': True,
                'summarize': True,
                'analyze_intent': True,
                'derived_metrics': True,
                'monitor': True,
                'export': True,
            },
            'retention_days': 30,
            'attribution_required': 'Original Hacker News permalink and source label',
            'restrictions': ['Recent feed window only (Ask/Show/New/Top/Best/Jobs); no private access or posting.'],
            'missing_approval_note': None,
        },
        'stack_exchange': {
            'provider_id': 'stack_exchange',
            'publisher': 'Stack Exchange Network',
            'authorized_app': 'PlaneByte Intent Radar (Registered API Key)',
            'authorization_reference': 'Official Stack Exchange API v2.3 with server application key; CC BY-SA attribution',
            'commercial_use_authorized': bool(s.intent_radar_stackexchange_enabled),
            'ai_processing_authorized': bool(s.intent_radar_stackexchange_enabled),
            'ai_status': 'Authorized' if s.intent_radar_stackexchange_enabled else 'Restricted',
            'capabilities': {
                'fetch': bool(s.intent_radar_stackexchange_enabled),
                'search': bool(s.intent_radar_stackexchange_enabled),
                'store': bool(s.intent_radar_stackexchange_enabled),
                'display': bool(s.intent_radar_stackexchange_enabled),
                'classify': bool(s.intent_radar_stackexchange_enabled),
                'summarize': bool(s.intent_radar_stackexchange_enabled),
                'analyze_intent': bool(s.intent_radar_stackexchange_enabled),
                'derived_metrics': bool(s.intent_radar_stackexchange_enabled),
                'monitor': bool(s.intent_radar_stackexchange_enabled),
                'export': bool(s.intent_radar_stackexchange_enabled),
            },
            'retention_days': 30,
            'attribution_required': 'CC BY-SA attribution, author link, and original Stack Exchange question URL',
            'restrictions': ['Bounded to configured communities (max 5 per search); respects backoff headers.'],
            'missing_approval_note': None if s.intent_radar_stackexchange_enabled else 'Enable INTENT_RADAR_STACKEXCHANGE_ENABLED after commercial terms verification.',
        },
        'github': {
            'provider_id': 'github',
            'publisher': 'GitHub, Inc.',
            'authorized_app': f"GitHub App: {s.github_app_slug or 'planebyte-intent-radar'} (App ID {s.github_app_id or 'unconfigured'})",
            'authorization_reference': 'GitHub REST & GraphQL APIs with App Installation Token + Workspace-isolated Customer OAuth + HMAC Webhooks',
            'commercial_use_authorized': bool(s.intent_radar_github_enabled),
            'ai_processing_authorized': bool(s.intent_radar_github_enabled),
            'ai_status': 'Authorized' if s.intent_radar_github_enabled else 'Restricted',
            'capabilities': {
                'fetch': bool(s.intent_radar_github_enabled),
                'search': bool(s.intent_radar_github_enabled),
                'store': bool(s.intent_radar_github_enabled),
                'display': bool(s.intent_radar_github_enabled),
                'classify': bool(s.intent_radar_github_enabled),
                'summarize': bool(s.intent_radar_github_enabled),
                'analyze_intent': bool(s.intent_radar_github_enabled),
                'derived_metrics': bool(s.intent_radar_github_enabled),
                'monitor': bool(s.intent_radar_github_enabled),
                'export': bool(s.intent_radar_github_enabled),
            },
            'retention_days': 30,
            'attribution_required': 'Repository full_name, public author handle, and original GitHub URL',
            'restrictions': ['Read-only installation permissions; private repositories require explicit customer GitHub App installation and selection.'],
            'missing_approval_note': None,
        },
        'youtube': {
            'provider_id': 'youtube',
            'publisher': 'Google LLC / YouTube Data API v3',
            'authorized_app': 'PlaneByte Intent Radar (GCP Project querryside)',
            'authorization_reference': 'YouTube API Services Terms & Compliance Dossier (docs/compliance/YOUTUBE_API_COMPLIANCE_DOSSIER.md)',
            'commercial_use_authorized': bool(s.intent_radar_youtube_enabled),
            'ai_processing_authorized': yt_ai,
            'ai_status': 'Authorized' if yt_ai else 'Restricted by YouTube API policy',
            'capabilities': {
                'fetch': bool(s.intent_radar_youtube_enabled),
                'search': bool(s.intent_radar_youtube_enabled and s.intent_radar_youtube_search_enabled),
                'store': bool(s.intent_radar_youtube_enabled),
                'display': bool(s.intent_radar_youtube_enabled),
                'classify': yt_ai,
                'summarize': yt_ai,
                'analyze_intent': yt_ai,
                'derived_metrics': yt_ai and yt_cross,
                'monitor': bool(s.intent_radar_youtube_enabled and s.intent_radar_youtube_monitoring_enabled),
                'export': False,
            },
            'retention_days': 30,
            'attribution_required': 'YouTube source attribution, channel title, and original watch URL (max 30-day retention)',
            'restrictions': [
                'Public video & comment retrieval and human review are active.',
                'Derived AI sentiment/intent scoring and cross-platform AI analytics remain gated OFF pending documented Google YouTube API compliance approval.',
                'Strict 30-day maximum metadata retention enforced automatically.',
            ],
            'missing_approval_note': None if yt_ai else 'Pending written Google YouTube API Services approval for derived AI analytics (INTENT_RADAR_YOUTUBE_AI_ANALYTICS_ENABLED=false).',
        },
        'bluesky': {
            'provider_id': 'bluesky',
            'publisher': 'Bluesky Social PBC (AT Protocol)',
            'authorized_app': 'PlaneByte Intent Radar (Public API + Jetstream v2)',
            'authorization_reference': 'Official Bluesky Public API (api.bsky.app) & Jetstream v2 firehose with delete propagation',
            'commercial_use_authorized': bool(s.intent_radar_bluesky_enabled),
            'ai_processing_authorized': bool(s.intent_radar_bluesky_enabled),
            'ai_status': 'Authorized' if s.intent_radar_bluesky_enabled else 'Restricted',
            'capabilities': {
                'fetch': bool(s.intent_radar_bluesky_enabled),
                'search': bool(s.intent_radar_bluesky_enabled),
                'store': bool(s.intent_radar_bluesky_enabled),
                'display': bool(s.intent_radar_bluesky_enabled),
                'classify': bool(s.intent_radar_bluesky_enabled),
                'summarize': bool(s.intent_radar_bluesky_enabled),
                'analyze_intent': bool(s.intent_radar_bluesky_enabled),
                'derived_metrics': bool(s.intent_radar_bluesky_enabled),
                'monitor': bool(s.intent_radar_bluesky_enabled and s.intent_radar_bluesky_jetstream_enabled),
                'export': bool(s.intent_radar_bluesky_enabled),
            },
            'retention_days': 30,
            'attribution_required': 'Public AT Protocol handle and bsky.app permalink; deletes propagated automatically',
            'restrictions': ['Public posts only; delete events propagate via Jetstream cursor reconciliation.'],
            'missing_approval_note': None,
        },
        'atom': {
            'provider_id': 'atom',
            'publisher': 'Approved Atom 1.0 Publishers (GitHub Releases, arXiv, Verified Feeds)',
            'authorized_app': 'PlaneByte Intent Radar (Bounded RFC 4287 Syndication Reader)',
            'authorization_reference': 'Public Atom 1.0 syndication feeds on platform-approved hosts; classified as Market/Technology Intelligence',
            'commercial_use_authorized': True,
            'ai_processing_authorized': True,
            'ai_status': 'Authorized (per-feed policy enforced)',
            'capabilities': {
                'fetch': True,
                'search': True,
                'store': True,
                'display': True,
                'classify': True,
                'summarize': True,
                'analyze_intent': False,  # Releases & papers are market intelligence, not buyer intent!
                'derived_metrics': True,
                'monitor': True,
                'export': True,
            },
            'retention_days': 14,
            'attribution_required': 'Publisher attribution, feed title, and canonical entry link',
            'restrictions': [
                'Software releases and arXiv research papers are classified as Market / Technology Intelligence — never misrepresented as buyer intent.',
                'YouTube Atom feeds inherit YouTube API policy restrictions (AI analytics gated OFF).',
            ],
            'missing_approval_note': None,
        },
        'discourse': {
            'provider_id': 'discourse',
            'publisher': 'Individual Public Discourse Community Publishers (10 verified communities)',
            'authorized_app': 'PlaneByte Intent Radar (Bounded Public RSS Syndication Reader)',
            'authorization_reference': 'Public Discourse latest.rss syndication with ETag/Last-Modified; commercial LLM analysis requires per-publisher permission',
            'commercial_use_authorized': True,
            'ai_processing_authorized': False,
            'ai_status': 'Restricted (per-publisher LLM approval required)',
            'capabilities': {
                'fetch': True,
                'search': True,
                'store': True,
                'display': True,
                'classify': False,
                'summarize': False,
                'analyze_intent': False,
                'derived_metrics': False,
                'monitor': True,
                'export': False,
            },
            'retention_days': 7,
            'attribution_required': 'Community publisher attribution and original public forum topic URL',
            'restrictions': [
                'Public RSS retrieval, keyword discovery, bookmarking, and human review are active.',
                'Commercial LLM processing remains gated until individual publisher-specific AI-processing approval records are recorded (permissions for one Discourse community do not apply across others).',
            ],
            'missing_approval_note': 'Per-publisher written commercial LLM processing approval records are not present for the 10 Discourse communities (Meta, Node-RED, Vercel, Postman, Shopify Dev, Bubble, Cursor, Make, Retool, n8n).',
        },
        'rss': {
            'provider_id': 'rss',
            'publisher': 'Customer-Configured Approved RSS / Atom Publishers',
            'authorized_app': 'PlaneByte Intent Radar (Bounded Public RSS/Atom Reader)',
            'authorization_reference': 'Operator host allowlist + publisher terms & attribution recorded per feed',
            'commercial_use_authorized': True,
            'ai_processing_authorized': False,
            'ai_status': 'Per-feed policy enforced',
            'capabilities': {
                'fetch': True,
                'search': True,
                'store': True,
                'display': True,
                'classify': False,
                'summarize': False,
                'analyze_intent': False,
                'derived_metrics': False,
                'monitor': True,
                'export': False,
            },
            'retention_days': 7,
            'attribution_required': 'Recorded publisher attribution and canonical item URL',
            'restrictions': [
                'Only platform-approved public HTTPS hosts are accepted (SSRF & XML entity protections enforced).',
                'Custom RSS feeds default to human review unless explicitly authorized by verified publisher policy.',
            ],
            'missing_approval_note': 'Add an approved custom RSS endpoint in Custom Feeds to use this connector.',
        },
    }
    return policies.get(provider_id, policies['rss'])


def list_provider_policies() -> list[dict]:
    order = ('hacker_news', 'stack_exchange', 'github', 'youtube', 'bluesky', 'atom', 'discourse', 'rss')
    return [provider_policy(pid) for pid in order]


def evaluate_feed_policy(feed: dict) -> dict:
    """Authoritative server-side policy decision for a configured or preset feed."""
    s = get_settings()
    endpoint = str(feed.get('endpoint') or '').strip()
    family = str(feed.get('family') or 'rss').strip()
    host = (urlsplit(endpoint).hostname or '').casefold()
    preset = _preset_by_endpoint().get(endpoint)

    # YouTube Atom feeds MUST inherit YouTube API policy gate — never bypass!
    if host in ('www.youtube.com', 'youtube.com', 'm.youtube.com'):
        ai_ok = bool(s.intent_radar_youtube_ai_analytics_enabled)
        return {
            'ai_processing_authorized': ai_ok,
            'ai_status': 'Authorized' if ai_ok else 'Restricted (YouTube API policy)',
            'classification_mode': 'market_intelligence',
            'policy_locked': True,
            'reason': None if ai_ok else 'YouTube Atom feeds inherit YouTube API policy restrictions; derived AI analytics remain gated pending Google approval.',
            'retention_max_days': 30,
        }

    # Verified GitHub release & arXiv Atom feeds -> AI authorized for market/tech intelligence
    if family == 'atom' and (host in ('github.com', 'rss.arxiv.org') or (preset and preset.get('ai_processing_authorized'))):
        return {
            'ai_processing_authorized': True,
            'ai_status': 'Authorized (Market / Tech Intelligence)',
            'classification_mode': 'market_intelligence',
            'policy_locked': bool(preset),
            'reason': None,
            'retention_max_days': 30,
        }

    # Discourse communities -> public RSS retrieval active, commercial LLM gated absent per-publisher approval
    if family == 'discourse':
        ai_ok = bool(preset.get('ai_processing_authorized')) if preset else False
        return {
            'ai_processing_authorized': ai_ok,
            'ai_status': 'Authorized' if ai_ok else 'Restricted (Publisher LLM approval required)',
            'classification_mode': 'community_discussion',
            'policy_locked': True,
            'reason': None if ai_ok else 'Public Discourse RSS retrieval and human review are active; commercial LLM analysis requires verified publisher-specific approval.',
            'retention_max_days': 30,
        }

    # Generic custom RSS feeds default to safe restricted mode (never self-declared)
    return {
        'ai_processing_authorized': False,
        'ai_status': 'Restricted (Human review only)',
        'classification_mode': 'publication',
        'policy_locked': False,
        'reason': 'Custom RSS feeds default to human review; commercial AI processing requires verified publisher license authorization.',
        'retention_max_days': 30,
    }


def can_run_ai_analysis(signal: dict) -> tuple[bool, str | None]:
    """Single runtime enforcement gate consulted by intelligence.analyze()."""
    s = get_settings()
    source = str(signal.get('source') or '')
    provenance = (signal.get('evidence') or {}).get('provenance') or {}
    endpoint = str(provenance.get('feed_self_url') or signal.get('source_url') or '')
    host = (urlsplit(endpoint).hostname or '').casefold()

    if source == 'YouTube' or host in ('www.youtube.com', 'youtube.com', 'm.youtube.com'):
        if not s.intent_radar_youtube_ai_analytics_enabled:
            return False, 'YouTube derived AI analytics require separate YouTube API policy approval; source retrieval and human review remain available.'
    if provenance.get('ai_processing_authorized') is False:
        return False, 'Commercial AI processing is not yet authorized for this feed; original source review remains available.'
    if source == 'Approved Discourse' and provenance.get('ai_processing_authorized') is not True:
        return False, 'Commercial AI processing is not yet authorized for this Discourse community feed; original source review remains available.'
    return True, None


async def test_feed_endpoint(endpoint: str, family: str = 'rss', *, name: str = 'Feed test', attribution: str = 'Public feed', policy_reference: str = 'Public RSS/Atom feed', retention_days: int = 7) -> dict:
    """Safely validate, fetch, and parse a single approved HTTPS feed endpoint without creating signals."""
    from app.intent_radar import connectors
    canonical_url = connectors.approved_endpoint(endpoint)
    if family == 'discourse' and not urlsplit(canonical_url).path.endswith(('.rss', '.atom')):
        raise HTTPException(422, 'Discourse endpoints must be explicitly permitted public .rss or .atom URLs.')

    policy = evaluate_feed_policy({'endpoint': canonical_url, 'family': family})
    started = time.monotonic()
    try:
        async with SafeAsyncClient(timeout=12.0, follow_redirects=False) as client:
            resp = await client.get(
                canonical_url,
                headers={'User-Agent': 'PlaneByte-IntentRadar/3.0 (+https://planebyte.com/sources-policy)', 'Accept': 'application/atom+xml, application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.1'},
            )
        latency_ms = round((time.monotonic() - started) * 1000, 1)
        if resp.status_code >= 400:
            return {
                'ok': False,
                'endpoint': canonical_url,
                'http_status': resp.status_code,
                'latency_ms': latency_ms,
                'checked_at': now(),
                'feed_format': None,
                'entry_count': 0,
                'latest_entry_at': None,
                'sample_titles': [],
                'etag': resp.headers.get('etag'),
                'last_modified': resp.headers.get('last-modified'),
                'policy': policy,
                'error': f'Upstream returned HTTP {resp.status_code}.',
            }
        raw = resp.content
        if len(raw) > feeds.MAX_FEED_BYTES:
            return {
                'ok': False,
                'endpoint': canonical_url,
                'http_status': resp.status_code,
                'latency_ms': latency_ms,
                'checked_at': now(),
                'feed_format': None,
                'entry_count': 0,
                'latest_entry_at': None,
                'sample_titles': [],
                'policy': policy,
                'error': 'Feed response exceeds 2 MB safety limit.',
            }
        cfg = {
            'id': 'probe',
            'name': name or 'Feed probe',
            'family': family,
            'endpoint': canonical_url,
            'attribution': attribution or 'Public publisher',
            'policy_reference': policy_reference or 'Public RSS/Atom feed',
            'retention_days': max(1, min(30, int(retention_days or 7))),
            'ai_processing_authorized': policy['ai_processing_authorized'],
        }
        items = feeds.parse(raw, cfg, connectors.normalized)
        live_items = [x for x in items if not x.get('removed')]
        latest_at = max((x['observed_at'] for x in live_items if x.get('observed_at')), default=None)
        fmt = live_items[0].get('provenance', {}).get('feed_format') if live_items else ('atom' if b'<feed' in raw[:500] else 'rss')
        return {
            'ok': True,
            'endpoint': canonical_url,
            'http_status': resp.status_code,
            'latency_ms': latency_ms,
            'checked_at': now(),
            'feed_format': fmt,
            'entry_count': len(live_items),
            'latest_entry_at': latest_at,
            'sample_titles': [x['title'] for x in live_items[:3]],
            'etag': resp.headers.get('etag'),
            'last_modified': resp.headers.get('last-modified'),
            'policy': policy,
            'error': None,
        }
    except HTTPException:
        raise
    except Exception as exc:
        latency_ms = round((time.monotonic() - started) * 1000, 1)
        return {
            'ok': False,
            'endpoint': canonical_url,
            'http_status': None,
            'latency_ms': latency_ms,
            'checked_at': now(),
            'feed_format': None,
            'entry_count': 0,
            'latest_entry_at': None,
            'sample_titles': [],
            'policy': policy,
            'error': f'{type(exc).__name__}: {str(exc)[:180]}',
        }


async def test_provider_connection(c, provider_id: str) -> dict:
    """Safe, bounded live connectivity verification for a research provider (no discovery quota charged)."""
    from app.intent_radar import connectors
    from app.intent_radar.permissions import context
    context(c, True, True)
    s = get_settings()
    started = time.monotonic()
    checked_at = now()
    policy = provider_policy(provider_id)

    try:
        if provider_id == 'hacker_news':
            async with SafeAsyncClient(timeout=8.0, follow_redirects=False) as client:
                resp = await client.get('https://hacker-news.firebaseio.com/v0/maxitem.json')
            latency = round((time.monotonic() - started) * 1000, 1)
            ok = resp.status_code == 200
            return {'ok': ok, 'provider': provider_id, 'http_status': resp.status_code, 'latency_ms': latency, 'checked_at': checked_at, 'summary': f'Official Hacker News API reachable (latest item #{resp.text.strip()[:16]}).' if ok else f'HTTP {resp.status_code}', 'policy': policy, 'error': None if ok else f'HTTP {resp.status_code}'}

        if provider_id == 'stack_exchange':
            if not s.intent_radar_stackexchange_enabled:
                return {'ok': False, 'provider': provider_id, 'http_status': None, 'latency_ms': 0, 'checked_at': checked_at, 'summary': 'Stack Exchange connector disabled by configuration.', 'policy': policy, 'error': 'STACKEXCHANGE_DISABLED'}
            params = {'site': 'stackoverflow'}
            key_val = s.intent_radar_stackexchange_key.get_secret_value()
            if key_val:
                params['key'] = key_val
            async with SafeAsyncClient(timeout=8.0, follow_redirects=False) as client:
                resp = await client.get('https://api.stackexchange.com/2.3/info', params=params)
            latency = round((time.monotonic() - started) * 1000, 1)
            ok = resp.status_code == 200
            quota = None
            if ok:
                try:
                    quota = resp.json().get('quota_remaining')
                except Exception:
                    pass
            return {'ok': ok, 'provider': provider_id, 'http_status': resp.status_code, 'latency_ms': latency, 'checked_at': checked_at, 'quota_remaining': quota, 'summary': f'Stack Exchange API v2.3 reachable (quota remaining: {quota}).' if ok else f'HTTP {resp.status_code}', 'policy': policy, 'error': None if ok else f'HTTP {resp.status_code}'}

        if provider_id == 'github':
            from app.intent_radar.github_source import connection_status
            from app.intent_radar.github_auth import GitHubAuth
            st = connection_status(c)
            inst_id = st.get('installation_id') or s.github_app_installation_id
            if not (s.intent_radar_github_enabled and s.github_app_id and s.github_app_private_key.get_secret_value() and inst_id):
                return {'ok': False, 'provider': provider_id, 'http_status': None, 'latency_ms': 0, 'checked_at': checked_at, 'summary': 'GitHub App credentials not configured.', 'policy': policy, 'error': 'GITHUB_NOT_CONFIGURED'}
            tok = await GitHubAuth(permit=lambda: True).token(str(inst_id))
            async with SafeAsyncClient(timeout=8.0, follow_redirects=False) as client:
                resp = await client.get('https://api.github.com/rate_limit', headers={'Accept': 'application/vnd.github+json', 'Authorization': f'Bearer {tok}', 'X-GitHub-Api-Version': s.github_api_version})
            latency = round((time.monotonic() - started) * 1000, 1)
            ok = resp.status_code == 200
            core_rem = None
            if ok:
                try:
                    core_rem = (resp.json().get('resources') or {}).get('core', {}).get('remaining')
                except Exception:
                    pass
            return {'ok': ok, 'provider': provider_id, 'http_status': resp.status_code, 'latency_ms': latency, 'checked_at': checked_at, 'quota_remaining': core_rem, 'summary': f"GitHub App token verified ({st.get('account_login') or 'public installation'}; core rate limit remaining: {core_rem})." if ok else f'HTTP {resp.status_code}', 'policy': policy, 'error': None if ok else f'HTTP {resp.status_code}'}

        if provider_id == 'youtube':
            api_key = s.youtube_api_key.get_secret_value()
            if not (s.intent_radar_youtube_enabled and api_key):
                return {'ok': False, 'provider': provider_id, 'http_status': None, 'latency_ms': 0, 'checked_at': checked_at, 'summary': 'YouTube Data API v3 is not configured.', 'policy': policy, 'error': 'YOUTUBE_NOT_CONFIGURED'}
            async with SafeAsyncClient(timeout=8.0, follow_redirects=False) as client:
                resp = await client.get('https://www.googleapis.com/youtube/v3/i18nRegions', params={'part': 'snippet', 'key': api_key})
            latency = round((time.monotonic() - started) * 1000, 1)
            ok = resp.status_code == 200
            return {'ok': ok, 'provider': provider_id, 'http_status': resp.status_code, 'latency_ms': latency, 'checked_at': checked_at, 'summary': 'YouTube Data API v3 key verified (1-unit lightweight check; derived AI analytics gated per policy).' if ok else f'HTTP {resp.status_code}', 'policy': policy, 'error': None if ok else f'HTTP {resp.status_code}'}

        if provider_id == 'bluesky':
            async with SafeAsyncClient(timeout=8.0, follow_redirects=False) as client:
                resp = await client.get(f"{s.bluesky_api_base_url.rstrip('/')}/xrpc/_health")
            latency = round((time.monotonic() - started) * 1000, 1)
            ok = resp.status_code == 200
            return {'ok': ok, 'provider': provider_id, 'http_status': resp.status_code, 'latency_ms': latency, 'checked_at': checked_at, 'summary': 'Bluesky Public API (api.bsky.app) healthy.' if ok else f'HTTP {resp.status_code}', 'policy': policy, 'error': None if ok else f'HTTP {resp.status_code}'}

        if provider_id in ('atom', 'discourse', 'rss'):
            configs = [x for x in connectors.configurations(c) if x.get('family') == provider_id and x.get('enabled')]
            if not configs:
                return {'ok': True, 'provider': provider_id, 'http_status': None, 'latency_ms': 0, 'checked_at': checked_at, 'summary': f'No enabled {provider_id.upper()} feeds configured yet.', 'policy': policy, 'error': None}
            sample = configs[0]
            res = await test_feed_endpoint(sample['endpoint'], provider_id, name=sample['name'], attribution=sample['attribution'], policy_reference=sample['policy_reference'], retention_days=sample['retention_days'])
            return {
                'ok': res['ok'],
                'provider': provider_id,
                'http_status': res['http_status'],
                'latency_ms': res['latency_ms'],
                'checked_at': res['checked_at'],
                'summary': f"Verified {sample['name']} ({res['entry_count']} entries parsed; {len(configs)} enabled feed(s))." if res['ok'] else f"Sample feed {sample['name']} failed: {res['error']}",
                'policy': policy,
                'error': res['error'],
            }

        raise HTTPException(404, f'Unknown research source: {provider_id}')
    except HTTPException:
        raise
    except Exception as exc:
        return {'ok': False, 'provider': provider_id, 'http_status': None, 'latency_ms': round((time.monotonic() - started) * 1000, 1), 'checked_at': checked_at, 'summary': 'Connection check failed.', 'policy': policy, 'error': f'{type(exc).__name__}: {str(exc)[:160]}'}
