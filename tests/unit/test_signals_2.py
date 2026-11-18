"""Comprehensive unit, workflow, policy, tenant-isolation, and scalability tests for Signals 2.0."""
import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from app.config.settings import get_settings
from app.intent_radar import intelligence, models, service
from app.platform.context import workspace_scope
from test_intent_radar import radar, owned  # noqa: F401 - pytest fixtures


def _insert_signal(
    c,
    org: str,
    *,
    sid: str | None = None,
    source: str = 'Hacker News',
    record_id: str | None = None,
    title: str = 'Looking for a workflow automation tool alternative',
    excerpt: str = 'We are actively evaluating alternatives to replace our legacy CRM workflow tool.',
    category: str = 'Alternative search',
    score: int = 88,
    status: str = 'New',
    observed_at: str | None = None,
    evidence: dict | None = None,
) -> str:
    sid = sid or str(uuid.uuid4())
    record_id = record_id or f'rec:{sid}'
    now_iso = datetime.now(timezone.utc).isoformat()
    obs = observed_at or now_iso
    ev = evidence if evidence is not None else {
        'matched_keywords': ['workflow', 'automation'],
        'matched_topics': ['crm'],
        'intent_phrase': 'looking for',
        'confidence': 'Strong evidence',
        'explanation': 'Matched workflow, automation and the phrase looking for.',
        'observed_text': excerpt,
        'unknown': ['Budget', 'Purchase authority'],
        'penalties': [],
        'purchasing_event_verified': False,
        'provenance': {'fetch_method': 'official_hn', 'content_kind': 'story', 'attribution': {'author': 'founder_x', 'source': source}},
    }
    c.execute(
        'INSERT INTO intent_signals(id,organization_id,source,source_record_id,source_url,title,excerpt,observed_at,retrieved_at,category,score,status,evidence_json) '
        'VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
        (sid, org, source, record_id, f'https://news.ycombinator.com/item?id={record_id}', title, excerpt, obs, now_iso, category, score, status, json.dumps(ev)),
    )
    return sid


def test_signals_2_saved_views_high_intent_strictness_and_filters(radar):
    c, _, org, org_b = radar
    base = datetime.now(timezone.utc)
    with workspace_scope(c, 'controlled@example.test', org):
        # 1. Genuine commercial intent signal
        s_high = _insert_signal(
            c, org,
            source='Hacker News',
            title='Looking for a CRM software alternative for B2B sales',
            excerpt='We are comparing software platforms to replace our current CRM tool.',
            category='Alternative search',
            score=90,
            status='New',
            observed_at=(base - timedelta(hours=2)).isoformat(),
        )
        # 2. High-keyword-score General discussion with NO commercial intent phrase -> must NEVER be in high_intent!
        s_noise = _insert_signal(
            c, org,
            source='Stack Exchange',
            title='Deep dive architecture notes on workflow automation',
            excerpt='Just sharing our internal benchmark numbers on workflow automation queues.',
            category='General discussion',
            score=94,
            status='New',
            observed_at=(base - timedelta(hours=3)).isoformat(),
            evidence={
                'matched_keywords': ['workflow', 'automation'],
                'intent_phrase': None,
                'penalties': [],
                'explanation': 'No explicit intent phrase was found.',
                'provenance': {'fetch_method': 'official_api', 'content_kind': 'question'},
            },
        )
        # 3. Technical release -> Market / technology intelligence -> must NEVER be in high_intent!
        s_release = _insert_signal(
            c, org,
            source='GitHub',
            title='nextjs/next.js v16.5.0 release notes',
            excerpt='Release v16.5.0 includes faster bundling and workflow automation hooks.',
            category='Market / technology intelligence',
            score=65,
            status='Reviewed',
            observed_at=(base - timedelta(hours=4)).isoformat(),
            evidence={
                'matched_keywords': ['workflow', 'automation'],
                'intent_phrase': None,
                'penalties': [],
                'provenance': {'fetch_method': 'github_webhook', 'content_kind': 'release', 'repo': 'vercel/next.js'},
            },
        )
        # 4. Qualified signal
        s_qual = _insert_signal(
            c, org,
            source='Bluesky',
            title='Can anyone recommend a tool for lead routing?',
            excerpt='We need a vendor or platform for multi-workspace lead routing.',
            category='Recommendation request',
            score=82,
            status='Qualified',
            observed_at=(base - timedelta(hours=5)).isoformat(),
        )
        # 5. Dismissed signal
        s_dismissed = _insert_signal(
            c, org,
            source='YouTube',
            title='We are hiring a workflow engineer',
            excerpt='Job opening for workflow engineer.',
            category='General discussion',
            score=25,
            status='Dismissed',
            observed_at=(base - timedelta(hours=6)).isoformat(),
            evidence={'matched_keywords': ['workflow'], 'intent_phrase': None, 'penalties': ['Job advertisement']},
        )
        # Save s_qual via bookmark -> MUST NOT overwrite Qualified status!
        bookmarked = service.bookmark(c, s_qual)
        assert bookmarked['saved'] is True
        assert bookmarked['status'] == 'Qualified'
        c.commit()

        # Verify all view counts and strict view membership
        all_res = service.listing(c, 'signals', view='all', sort='newest')
        assert all_res['total'] == 5
        assert all_res['view_counts'] == {
            'all': 5,
            'needs_review': 2,  # s_high, s_noise
            'high_intent': 2,   # ONLY s_high & s_qual (NOT s_noise score=94, NOT s_release!)
            'saved': 1,         # s_qual
            'qualified': 1,     # s_qual
            'dismissed': 1,     # s_dismissed
        }

        hi = service.listing(c, 'signals', view='high_intent')
        hi_ids = {item['id'] for item in hi['items']}
        assert hi_ids == {s_high, s_qual}
        assert s_noise not in hi_ids
        assert s_release not in hi_ids

        # Unanalyzed signals MUST report buying_intent=None / unassessed (never fabricated!)
        for item in all_res['items']:
            assert item['buying_intent'] is None
            assert item['buying_intent_basis'] == 'unassessed'
            assert item['icp_fit'] == 'Unassessed'

        # Excerpt search works (not just title!)
        excerpt_search = service.listing(c, 'signals', search='multi-workspace lead routing')
        assert [i['id'] for i in excerpt_search['items']] == [s_qual]

        # Combinable filters: source + status + sort
        combo = service.listing(c, 'signals', source='Hacker News', status='New', sort='score')
        assert [i['id'] for i in combo['items']] == [s_high]

    # Cross-workspace isolation (even with Intent Radar enabled on org_b)
    c.execute("UPDATE organization_products SET enabled=1 WHERE organization_id=? AND product='INTENT_RADAR'", (org_b,))
    c.commit()
    with workspace_scope(c, 'foreign@example.test', org_b):
        other = service.listing(c, 'signals')
        assert other['total'] == 0
        assert other['view_counts']['all'] == 0
        with pytest.raises(HTTPException) as not_found:
            service.get(c, 'signals', s_high)
        assert not_found.value.status_code == 404


def test_signals_2_workflow_qualification_opportunity_antidupe_and_activity(radar):
    c, _, org, _ = radar
    with workspace_scope(c, 'controlled@example.test', org):
        sig_id = _insert_signal(
            c, org,
            title='Evaluating CRM software platforms for 2027 rollout',
            excerpt='We are comparing software platforms to replace our legacy CRM vendor next quarter.',
            category='Tool / service evaluation',
            score=89,
            status='New',
        )
        c.commit()

        # 1. Transition to Qualified + add note
        s = service.get(c, 'signals', sig_id)
        updated = service.review(c, sig_id, models.SignalUpdate(revision=s['revision'], status='Qualified', notes='Strong fit for outbound sync'))
        assert updated['status'] == 'Qualified'
        assert updated['notes'] == 'Strong fit for outbound sync'

        # 2. Save bookmark independently -> preserves Qualified status!
        saved = service.bookmark(c, sig_id)
        assert saved['saved'] is True
        assert saved['status'] == 'Qualified'

        # 3. Create opportunity with editable fields -> preserves Qualified status!
        opp = service.opportunity(
            c, sig_id,
            create_body=models.OpportunityCreate(priority='High', notes='Confirmed evaluation thread', next_action='Prepare comparison sheet'),
        )
        assert opp['priority'] == 'High'
        assert opp['notes'] == 'Confirmed evaluation thread'
        assert opp['next_action'] == 'Prepare comparison sheet'
        assert opp['already_existed'] is False

        sig_after_opp = service.get(c, 'signals', sig_id)
        assert sig_after_opp['status'] == 'Qualified'
        assert sig_after_opp['opportunity_id'] == opp['id']
        assert sig_after_opp['opportunity_status'] == opp['status']

        # 4. Calling opportunity creation again MUST NOT duplicate or error!
        opp_again = service.opportunity(c, sig_id)
        assert opp_again['id'] == opp['id']
        assert opp_again['already_existed'] is True
        assert c.execute('SELECT COUNT(*) FROM intent_opportunities WHERE organization_id=? AND signal_id=?', (org, sig_id)).fetchone()[0] == 1

        # 5. Reviewer feedback supports Relevant, Not relevant, Unsure and is reversible
        fb_unsure = intelligence.feedback(c, sig_id, models.Feedback(label='Unsure', note='Need to verify team size', active=True))
        assert fb_unsure['ranking_adjustment'] == 0
        fb_rel = intelligence.feedback(c, sig_id, models.Feedback(label='Relevant', note='Clear buying evaluation', active=True))
        assert fb_rel['ranking_adjustment'] == 5
        fb_off = intelligence.feedback(c, sig_id, models.Feedback(label='Relevant', note='', active=False))
        assert fb_off['ranking_adjustment'] == 0

        # 6. Single signal activity timeline records collected, saved, feedback, opportunity, audit
        detail = service.get(c, 'signals', sig_id)
        kinds = {ev['kind'] for ev in detail['activity']}
        assert {'collected', 'saved', 'feedback', 'opportunity', 'audit'}.issubset(kinds)


def test_signals_2_ai_structured_summary_and_policy_gates(radar, monkeypatch):
    c, _, org, _ = radar
    s = get_settings()
    monkeypatch.setattr(s, 'intent_radar_ai_enabled', True)
    monkeypatch.setattr(s, 'intent_radar_youtube_ai_analytics_enabled', False)
    with workspace_scope(c, 'controlled@example.test', org):
        # YouTube signal MUST remain policy-gated
        yt_id = _insert_signal(
            c, org,
            source='YouTube',
            title='Comparing CRM automation tools in 2026',
            excerpt='We are looking for a CRM tool comparison.',
            evidence={'matched_keywords': ['crm'], 'provenance': {'fetch_method': 'official_api', 'content_kind': 'video'}},
        )
        # Discourse feed without AI permission MUST remain policy-gated
        disc_id = _insert_signal(
            c, org,
            source='Approved Discourse',
            title='Looking for a CRM replacement',
            excerpt='Can anyone recommend a CRM tool?',
            evidence={'matched_keywords': ['crm'], 'provenance': {'fetch_method': 'public_feed', 'ai_processing_authorized': False}},
        )
        c.commit()

        yt_res = asyncio.run(intelligence.analyze(c, yt_id, models.AnalysisRequest()))
        assert yt_res['mode'] == 'Policy gated'
        assert yt_res['structured']['buying_intent'] == 'Insufficient evidence'
        assert 'no ICP selected' in yt_res['structured']['icp_fit']

        disc_res = asyncio.run(intelligence.analyze(c, disc_id, models.AnalysisRequest()))
        assert disc_res['mode'] == 'Policy gated'
        assert 'not yet authorized' in disc_res['fallback_reason']

        # Unit-verify structured_summary for explicit commercial intent vs non-buying release
        sample_sig = service.get(c, 'signals', yt_id)
        explicit_interp = intelligence.Interpretation(
            categories=['Recommendation request'],
            claims=[intelligence.Claim(kind='intent', quote='looking for a CRM tool', interpretation='Author requests CRM tool recommendations.')],
            uncertainty='Moderate',
            review_needed=False,
            summary=intelligence.Claim(kind='summary', quote='Comparing CRM automation tools', interpretation='Comparison of CRM automation platforms.'),
            buyer_problem=intelligence.Claim(kind='intent', quote='looking for a CRM tool', interpretation='Evaluating replacement CRM options.'),
            recommended_research='Compare stated needs with offering',
        )
        scored = intelligence.score(sample_sig, explicit_interp, {'ranking_adjustment': 0, 'explanation': ''})
        struct_no_icp = intelligence.structured_summary(sample_sig, explicit_interp, scored, None)
        assert struct_no_icp['buying_intent'] == 'Explicit commercial intent'
        assert struct_no_icp['icp_fit'] == 'Unassessed — no ICP selected'
        assert 'looking for a CRM tool' in struct_no_icp['source_statements']


def test_signals_2_scalability_benchmarks_up_to_10000_signals(radar):
    """Isolated synthetic benchmark covering 0, 1, 20, 100, 1,000, and 10,000 signals."""
    c, _, org, _ = radar
    # Create the Signals 2.0 composite indexes on isolated SQLite test DB
    c.execute('CREATE INDEX IF NOT EXISTS idx_signals_org_avail_observed ON intent_signals(organization_id, available, observed_at DESC, id DESC)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_signals_org_avail_status_score ON intent_signals(organization_id, available, status, score DESC, id DESC)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_signals_org_avail_source_obs ON intent_signals(organization_id, available, source, observed_at DESC)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_signals_org_avail_cat_obs ON intent_signals(organization_id, available, category, observed_at DESC)')

    base = datetime.now(timezone.utc)
    now_iso = base.isoformat()
    timings: dict[int, dict[str, float]] = {}
    inserted = 0

    def seed_to(target: int):
        nonlocal inserted
        if target <= inserted:
            return
        sources = ('Hacker News', 'GitHub', 'Stack Exchange', 'Bluesky', 'YouTube')
        statuses = ('New', 'Reviewed', 'Qualified', 'Dismissed', 'Needs Review')
        categories = ('Recommendation request', 'Alternative search', 'Problem / pain point', 'General discussion', 'Market / technology intelligence')
        rows = []
        for n in range(inserted, target):
            sid = str(uuid.uuid5(uuid.NAMESPACE_URL, f'sig-bench:{n}'))
            src = sources[n % len(sources)]
            st = statuses[n % len(statuses)]
            cat = categories[n % len(categories)]
            sc = (n * 17) % 101
            obs = (base - timedelta(seconds=n * 15)).isoformat()
            phrase = 'looking for' if cat in ('Recommendation request', 'Alternative search') else None
            ev = json.dumps({'matched_keywords': ['crm'], 'intent_phrase': phrase, 'penalties': [], 'provenance': {'fetch_method': 'official_api'}})
            rows.append((sid, org, src, f'bench:{n}', f'https://example.com/item/{n}', f'Signal bench item #{n} crm evaluation', f'Excerpt for benchmark signal {n}', obs, now_iso, cat, sc, st, ev))
        c.executemany(
            'INSERT INTO intent_signals(id,organization_id,source,source_record_id,source_url,title,excerpt,observed_at,retrieved_at,category,score,status,evidence_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
            rows,
        )
        c.commit()
        inserted = target

    with workspace_scope(c, 'controlled@example.test', org):
        for volume in (0, 1, 20, 100, 1000, 10000):
            seed_to(volume)
            t0 = time.perf_counter()
            page1 = service.listing(c, 'signals', page=1, size=25, sort='newest')
            t_newest = (time.perf_counter() - t0) * 1000

            t1 = time.perf_counter()
            filtered = service.listing(c, 'signals', page=1, size=25, view='high_intent', source='GitHub', sort='score')
            t_filtered = (time.perf_counter() - t1) * 1000

            t2 = time.perf_counter()
            searched = service.listing(c, 'signals', page=1, size=25, search='item #99', sort='newest')
            t_search = (time.perf_counter() - t2) * 1000

            timings[volume] = {
                'newest_ms': round(t_newest, 2),
                'filtered_ms': round(t_filtered, 2),
                'search_ms': round(t_search, 2),
            }
            assert page1['total'] == volume
            assert len(page1['items']) == min(25, volume)
            assert page1['view_counts']['all'] == volume
            assert page1['has_more'] is (volume > 25)
            # Ensure deterministic non-overlapping pagination at high volume
            if volume >= 100:
                page2 = service.listing(c, 'signals', page=2, size=25, sort='newest')
                ids1 = {x['id'] for x in page1['items']}
                ids2 = {x['id'] for x in page2['items']}
                assert ids1.isdisjoint(ids2)
            assert filtered['total'] <= volume
            assert searched['total'] <= volume

    print('SIGNALS_2_BENCHMARK_MS:', json.dumps(timings))
    # Even at 10,000 signals in local SQLite, bounded queries must stay well under 2 seconds
    assert timings[10000]['newest_ms'] < 2000
    assert timings[10000]['filtered_ms'] < 2000
    assert timings[10000]['search_ms'] < 2000
