"""Tests for Discovery 2.0 persistent history, immutability, reruns, saved searches, and tenant isolation."""
import asyncio
import uuid
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
from app.intent_radar import discovery, discovery_workspace, models, providers, service
from tests.unit.test_intent_radar import owned, radar, source_result, workspace_scope


def _run_discovery(c, path, body: models.Discovery):
    from app.intelligence import jobs
    job = discovery.create(c, body)
    c.commit()
    jobs.execute(job['id'], path)
    return discovery.owned_job(c, job['id']), job['discovery_id']


def test_discovery_history_persistence_immutability_rerun_and_soft_delete(radar, monkeypatch):
    c, path, org, other = radar
    c.execute("UPDATE organization_products SET enabled=1 WHERE organization_id=? AND product='INTENT_RADAR'", (other,))
    c.commit()
    monkeypatch.setattr(providers.HackerNews, 'fetch', AsyncMock(return_value=source_result()))

    with workspace_scope(c, 'controlled@example.test', org):
        # 1. Execute an AI-mode discovery with title, prompt, and structured strategy
        strategy = models.SearchStrategy(
            objective='Find teams needing a website redesign',
            target_customer_context='B2B agencies',
            keyword_rationale='Focused on website demand',
            source_rationale='Hacker News Ask HN',
            exclusions_rationale='None',
            limitations=['Recent discussions only'],
        )
        first_body = models.Discovery(
            configuration=models.Search(keywords=['website'], phrases=['looking for']),
            title='Website Redesign Demand',
            original_prompt='Find founders looking for website redesign help',
            search_mode='ai',
            strategy=strategy,
        )
        job1, run1_id = _run_discovery(c, path, first_body)
        assert job1['status'] == 'COMPLETED'
        assert job1['discovery_id'] == run1_id

        # 2. Verify history listing & detail retain immutable metadata, criteria, strategy, and signals
        hist = discovery_workspace.list_discoveries(c)
        assert hist['total'] == 1
        item = hist['items'][0]
        assert item['id'] == run1_id
        assert item['title'] == 'Website Redesign Demand'
        assert item['original_prompt'] == 'Find founders looking for website redesign help'
        assert item['search_mode'] == 'ai'
        assert item['matched_count'] >= 1

        detail = discovery_workspace.get_discovery(c, run1_id)
        assert detail['strategy']['objective'] == 'Find teams needing a website redesign'
        assert len(detail['signals']) >= 1
        original_signal_id = detail['signals'][0]['id']

        # 3. Rerun with modified keywords creates a NEW linked discovery without mutating run 1
        rerun_body = models.Discovery(
            configuration=models.Search(keywords=['website', 'agency'], excluded=['intern']),
            title='Website Redesign Demand (Refined)',
            original_prompt='Find founders looking for website redesign help',
            search_mode='rerun',
            parent_discovery_id=uuid.UUID(run1_id),
        )
        job2, run2_id = _run_discovery(c, path, rerun_body)
        assert job2['status'] == 'COMPLETED'
        assert run2_id != run1_id

        detail1_after = discovery_workspace.get_discovery(c, run1_id)
        assert detail1_after['keywords'] == ['website']
        assert detail1_after['configuration']['excluded'] == []

        detail2 = discovery_workspace.get_discovery(c, run2_id)
        assert detail2['parent_discovery_id'] == run1_id
        assert detail2['keywords'] == ['website', 'agency']

        # 4. Filtering by search term, source, and status works
        assert discovery_workspace.list_discoveries(c, search='Refined')['total'] == 1
        assert discovery_workspace.list_discoveries(c, source='hacker_news')['total'] == 2
        assert discovery_workspace.list_discoveries(c, source='github')['total'] == 0
        assert discovery_workspace.list_discoveries(c, status='COMPLETED')['total'] == 2

        # 5. Soft delete removes run 1 from history but preserves underlying signals
        deleted = discovery_workspace.delete_discovery(c, run1_id)
        assert deleted['deleted'] is True
        c.commit()
        assert discovery_workspace.list_discoveries(c)['total'] == 1
        with pytest.raises(HTTPException) as exc:
            discovery_workspace.get_discovery(c, run1_id)
        assert exc.value.status_code == 404
        # Signal remains intact!
        preserved = service.get(c, 'signals', original_signal_id)
        assert preserved['id'] == original_signal_id

    # 6. Cross-workspace tenant isolation: org B cannot see, delete, or parent-link org A's runs
    with workspace_scope(c, 'foreign@example.test', other):
        assert discovery_workspace.list_discoveries(c)['total'] == 0
        with pytest.raises(HTTPException) as exc_get:
            discovery_workspace.get_discovery(c, run2_id)
        assert exc_get.value.status_code == 404
        with pytest.raises(HTTPException) as exc_del:
            discovery_workspace.delete_discovery(c, run2_id)
        assert exc_del.value.status_code == 404
        with pytest.raises(HTTPException) as exc_parent:
            discovery.create(c, models.Discovery(
                configuration=models.Search(keywords=['website']),
                parent_discovery_id=uuid.UUID(run2_id),
            ))
        assert exc_parent.value.status_code == 404


def test_saved_searches_crud_separate_from_monitors_and_isolated(radar):
    c, _path, org, other = radar
    c.execute("UPDATE organization_products SET enabled=1 WHERE organization_id=? AND product='INTENT_RADAR'", (other,))
    c.commit()
    with workspace_scope(c, 'controlled@example.test', org):
        created = discovery_workspace.save_search(c, discovery_workspace.SavedSearchInput(
            name='CRM Alternatives Watch',
            description='Teams evaluating CRM replacements',
            original_prompt='Find startups looking for a CRM alternative',
            configuration=models.Search(keywords=['CRM alternative', 'HubSpot'], excluded=['hiring']),
        ))
        c.commit()
        assert created['revision'] == 1
        # Must NOT create an intent_monitor
        assert service.listing(c, 'monitors')['total'] == 0

        # Update with revision check
        updated = discovery_workspace.save_search(c, discovery_workspace.SavedSearchInput(
            name='CRM Alternatives Watch v2',
            description='Updated',
            original_prompt='Find startups looking for a CRM alternative',
            configuration=models.Search(keywords=['CRM alternative', 'Salesforce vs HubSpot']),
            revision=1,
        ), created['id'])
        c.commit()
        assert updated['revision'] == 2
        assert updated['name'] == 'CRM Alternatives Watch v2'

        # Stale revision rejected with 409
        with pytest.raises(HTTPException) as exc_stale:
            discovery_workspace.save_search(c, discovery_workspace.SavedSearchInput(
                name='Stale overwrite',
                configuration=models.Search(keywords=['CRM alternative']),
                revision=1,
            ), created['id'])
        assert exc_stale.value.status_code == 409

        # Duplicate creates independent copy
        copy = discovery_workspace.duplicate_saved_search(c, created['id'])
        c.commit()
        assert copy['id'] != created['id']
        assert copy['name'].endswith('(copy)')
        assert discovery_workspace.list_saved_searches(c)['total'] == 2
        assert discovery_workspace.list_saved_searches(c, search='copy')['total'] == 1

        # Delete
        discovery_workspace.delete_saved_search(c, copy['id'])
        c.commit()
        assert discovery_workspace.list_saved_searches(c)['total'] == 1

    # Cross-workspace isolation
    with workspace_scope(c, 'foreign@example.test', other):
        assert discovery_workspace.list_saved_searches(c)['total'] == 0
        with pytest.raises(HTTPException) as exc_other:
            discovery_workspace.delete_saved_search(c, created['id'])
        assert exc_other.value.status_code == 404
        with pytest.raises(HTTPException) as exc_dup:
            discovery_workspace.duplicate_saved_search(c, created['id'])
        assert exc_dup.value.status_code == 404


def test_discovery_history_sorting_pagination_rename_and_clean_titles(radar, monkeypatch):
    c, path, org, other = radar
    c.execute("UPDATE organization_products SET enabled=1 WHERE organization_id=? AND product='INTENT_RADAR'", (other,))
    c.commit()
    monkeypatch.setattr(providers.HackerNews, 'fetch', AsyncMock(return_value=source_result()))

    # Verify clean deterministic title derivation without filler words
    assert discovery_workspace._derive_title({'keywords': ['next.js']}) == 'Next.js Research'
    assert discovery_workspace._derive_title({'keywords': ['recent', 'discussions', 'webhook']}) == 'Webhook Research'
    assert discovery_workspace._derive_title({'keywords': ['crm']}, '', 'Find recent discussions about CRM replacement options') == 'CRM replacement options'

    with workspace_scope(c, 'controlled@example.test', org):
        # Insert 3 runs with distinct titles, modes, and result counts
        _, id_a = _run_discovery(c, path, models.Discovery(
            configuration=models.Search(keywords=['website']),
            title='Alpha Website Audit',
            search_mode='ai',
        ))
        # Second run with no matching keyword (0 results)
        _, id_b = _run_discovery(c, path, models.Discovery(
            configuration=models.Search(keywords=['unmatchedtokenxyz']),
            title='Beta Zero Match Run',
            search_mode='advanced',
        ))
        _, id_c = _run_discovery(c, path, models.Discovery(
            configuration=models.Search(keywords=['website']),
            title='Charlie Website Followup',
            search_mode='rerun',
            parent_discovery_id=uuid.UUID(id_a),
        ))

        # Sorting: title_asc & title_desc
        asc = discovery_workspace.list_discoveries(c, sort='title_asc')
        assert [x['title'] for x in asc['items']] == ['Alpha Website Audit', 'Beta Zero Match Run', 'Charlie Website Followup']
        desc = discovery_workspace.list_discoveries(c, sort='title_desc')
        assert [x['title'] for x in desc['items']] == ['Charlie Website Followup', 'Beta Zero Match Run', 'Alpha Website Audit']

        # Sorting: results_desc puts matched runs first, 0-match last
        by_res = discovery_workspace.list_discoveries(c, sort='results_desc')
        assert by_res['items'][-1]['id'] == id_b
        assert by_res['items'][-1]['matched_count'] == 0

        # Filtering: search_mode & has_results
        assert discovery_workspace.list_discoveries(c, search_mode='ai')['total'] == 1
        assert discovery_workspace.list_discoveries(c, has_results='with_results')['total'] == 2
        assert discovery_workspace.list_discoveries(c, has_results='no_results')['total'] == 1

        # Pagination across pages
        p1 = discovery_workspace.list_discoveries(c, page=1, page_size=2, sort='title_asc')
        p2 = discovery_workspace.list_discoveries(c, page=2, page_size=2, sort='title_asc')
        assert len(p1['items']) == 2 and p1['has_more'] is True and p1['total'] == 3
        assert len(p2['items']) == 1 and p2['has_more'] is False

        # Rename updates display title without mutating immutable configuration_json
        renamed = discovery_workspace.rename_discovery(c, id_b, 'Renamed Zero-Match Investigation')
        c.commit()
        assert renamed['title'] == 'Renamed Zero-Match Investigation'
        detail_b = discovery_workspace.get_discovery(c, id_b)
        assert detail_b['title'] == 'Renamed Zero-Match Investigation'
        assert detail_b['keywords'] == ['unmatchedtokenxyz']

    # Foreign workspace cannot rename
    with workspace_scope(c, 'foreign@example.test', other):
        with pytest.raises(HTTPException) as exc_ren:
            discovery_workspace.rename_discovery(c, id_b, 'Hijack')
        assert exc_ren.value.status_code == 404
