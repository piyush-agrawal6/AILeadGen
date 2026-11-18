"""Discovery 2.0 AI search quality evaluation suite across 9 verticals + Copilot & edge cases."""
import asyncio
import uuid
import pytest
from fastapi import HTTPException
from app.acquisition import ai as ai_gateway
from app.config.settings import get_settings
from app.intent_radar import ai, discovery_copilot, models, service
from tests.unit.test_intent_radar import owned, radar, workspace_scope

AVAILABLE_SOURCES = [
    {'id': 'hacker_news', 'name': 'Hacker News', 'state': 'Available', 'ai_processing_authorized': True},
    {'id': 'stack_exchange', 'name': 'Stack Exchange', 'state': 'Available', 'ai_processing_authorized': True},
    {'id': 'github', 'name': 'GitHub', 'state': 'Connected', 'ai_processing_authorized': True},
    {'id': 'youtube', 'name': 'YouTube', 'state': 'Available', 'ai_processing_authorized': False},
    {'id': 'bluesky', 'name': 'Bluesky', 'state': 'Available', 'ai_processing_authorized': True},
]

FORBIDDEN_STANDALONE_FILLER = {
    'all', 'only', 'find', 'recent', 'discussions', 'looking', 'especially',
    'vs', 'compare', 'alternative', 'people', 'software', 'tools', 'platforms',
}

NINE_VERTICAL_PROMPTS = [
    ('saas_agency', 'Find startups looking for a React or Next.js SaaS development agency to build their MVP', {'saas', 'mvp', 'react', 'next.js'}),
    ('crm_erp', 'Find teams comparing Salesforce vs HubSpot or looking for a lightweight CRM alternative', {'salesforce', 'hubspot', 'crm'}),
    ('ai_automation', 'Companies trying to automate customer support workflows with n8n or AI agents', {'n8n', 'workflow', 'automation', 'ai'}),
    ('cybersecurity', 'Engineering leaders dealing with SOC 2 compliance and endpoint security on GitHub and Hacker News', {'soc', 'endpoint', 'security'}),
    ('marketing_agency', 'B2B SaaS teams struggling with demand generation and marketing attribution', {'demand', 'marketing', 'attribution'}),
    ('b2b_software', 'Product teams looking for a usage-based billing or Stripe alternative', {'billing', 'stripe'}),
    ('startup_alternatives', 'Founders switching from Datadog to an open-source observability stack', {'datadog', 'observability'}),
    ('dev_api_issues', 'Developers hitting Stripe webhook timeout or API rate limit errors on Stack Overflow and GitHub', {'stripe', 'webhook', 'rate', 'api'}),
    ('tech_trends', 'Recent discussions on Hacker News about LLM observability and vector database latency', {'llm', 'observability', 'vector', 'latency'}),
]


@pytest.mark.parametrize('vertical,prompt,expected_any', NINE_VERTICAL_PROMPTS)
def test_nine_vertical_search_quality_and_zero_filler_keywords(vertical, prompt, expected_any):
    draft, _warning = ai.fallback(prompt, available_sources=AVAILABLE_SOURCES)
    kws = draft.configuration.keywords
    assert len(kws) >= 1
    lower_kws = [k.casefold() for k in kws]
    # Zero standalone filler words allowed
    for kw in lower_kws:
        assert kw not in FORBIDDEN_STANDALONE_FILLER, f'{vertical} emitted filler keyword {kw!r} in {kws}'
    # At least one concrete domain signal extracted
    joined = ' '.join(lower_kws)
    assert any(tok in joined for tok in expected_any), f'{vertical} missed expected domain terms {expected_any} in {kws}'
    # Structured strategy always populated
    assert draft.strategy is not None
    assert draft.strategy.objective
    assert draft.strategy.keyword_rationale
    assert draft.strategy.source_rationale


def test_validator_strips_standalone_filler_but_preserves_multiword_phrases():
    noisy_draft = models.SearchDraft(
        name='Reviewable intent search',
        description='CRM comparison',
        configuration=models.Search(
            keywords=[
                'all', 'only', 'find', 'recent', 'discussions', 'looking',
                'especially', 'vs', 'compare', 'alternative',
                'CRM alternative', 'Salesforce vs HubSpot',
            ],
            sources=['hacker_news', 'github'],
        ),
    )
    cleaned, warning = discovery_copilot.validate_and_clean_strategy(
        noisy_draft,
        'Search only GitHub for Salesforce vs HubSpot and CRM alternative discussions',
        available_sources=AVAILABLE_SOURCES,
    )
    assert warning is None
    assert cleaned.configuration.keywords == ['CRM alternative', 'Salesforce vs HubSpot']
    # Explicit single-source constraint preserved
    assert cleaned.configuration.sources == ['github']
    assert cleaned.configuration.semantic is False


def test_vague_prompt_grounded_in_company_and_icp_context():
    ctx_data = {
        'company': {
            'name': 'PlaneByte',
            'industry': 'B2B SaaS',
            'products_services': 'Intent Radar, AI workflow automation',
        },
        'selected_icp': {
            'id': str(uuid.uuid4()),
            'name': 'Seed B2B SaaS Founders',
            'pain_points': ['outbound lead generation', 'buyer intent signals'],
            'industries': ['DevTools'],
        },
    }
    draft, _ = ai.fallback('Find people looking for good tools', available_sources=AVAILABLE_SOURCES, context_data=ctx_data)
    joined = ' '.join(draft.configuration.keywords).casefold()
    assert any(tok in joined for tok in ('lead', 'intent', 'workflow', 'devtools', 'saas'))
    assert 'Seed B2B SaaS Founders' in draft.strategy.target_customer_context


def test_copilot_structured_proposals_sanitization_and_quota_exhaustion(radar, monkeypatch):
    c, _path, org, _other = radar

    class FakeProvider:
        async def structured(self, instruction, inputs, schema, **kwargs):
            return models.CopilotAiOutput(
                reply='Tightened keywords and excluded hiring noise.',
                strategy=models.SearchStrategy(
                    objective='Find B2B SaaS teams evaluating CRM alternatives',
                    target_customer_context='B2B SaaS',
                    keyword_rationale='Multiword comparison phrases beat single words.',
                    source_rationale='Hacker News is active for founder evaluations.',
                    exclusions_rationale='Filter out recruiting noise.',
                    limitations=['Recent posts only.'],
                ),
                proposals=[
                    models.CopilotProposal(
                        id='p1',
                        action='add_keywords',
                        label='Add CRM comparison phrases',
                        rationale='High commercial intent.',
                        keywords=['all', 'vs', 'CRM alternative', 'Salesforce vs HubSpot'],
                    ),
                    models.CopilotProposal(
                        id='p2',
                        action='add_exclusions',
                        label='Exclude hiring noise',
                        rationale='Removes job listings.',
                        excluded=['hiring', 'intern'],
                    ),
                    models.CopilotProposal(
                        id='p3',
                        action='select_sources',
                        label='Switch sources',
                        rationale='Includes unavailable source that must be stripped.',
                        sources=['hacker_news', 'youtube'],
                    ),
                    models.CopilotProposal(
                        id='p4',
                        action='choose_icp',
                        label='Foreign ICP must be dropped',
                        rationale='Should be rejected by workspace check.',
                        icp_id=uuid.uuid4(),
                    ),
                ],
                warnings=[],
            )

    monkeypatch.setattr(get_settings(), 'intent_radar_ai_enabled', True)
    monkeypatch.setattr(ai_gateway, 'provider', lambda _c: FakeProvider())

    with workspace_scope(c, 'controlled@example.test', org):
        draft_cfg = models.Search(keywords=['crm'], sources=['hacker_news'])
        req = models.CopilotRequest(
            message='Improve my CRM keywords and exclude hiring posts',
            quick_action='improve_keywords',
            draft=draft_cfg,
        )
        res = asyncio.run(discovery_copilot.copilot(c, req))
        assert res['mode'] == 'AI Copilot'
        assert res['quota_exhausted'] is False
        assert res['draft_fingerprint'] == discovery_copilot.draft_fingerprint(draft_cfg.model_dump(mode='json'))

        by_id = {p['id']: p for p in res['proposals']}
        # Filler tokens ('all', 'vs') stripped; multiword phrases preserved
        assert by_id['p1']['keywords'] == ['CRM alternative', 'Salesforce vs HubSpot']
        assert by_id['p2']['excluded'] == ['hiring', 'intern']
        # Foreign ICP proposal dropped
        assert 'p4' not in by_id
        # Unavailable youtube stripped (not configured in default test workspace)
        assert 'youtube' not in by_id['p3']['sources']
        assert by_id['p3']['sources'] == ['hacker_news']

        # Draft fingerprint changes when user edits draft manually
        edited_cfg = models.Search(keywords=['crm', 'hubspot'], sources=['hacker_news'])
        assert discovery_copilot.draft_fingerprint(edited_cfg.model_dump(mode='json')) != res['draft_fingerprint']

        # Quota exhausted (429): honest response, zero fabricated proposals, no quota bypass
        from app.intent_radar import intelligence
        monkeypatch.setattr(intelligence, 'reserve', lambda _tokens: (_ for _ in ()).throw(HTTPException(429, 'Quota exhausted')))
        req2 = models.CopilotRequest(
            message='Broaden my search for ERP migrations',
            quick_action='broaden_search',
            draft=edited_cfg,
        )
        res_quota = asyncio.run(discovery_copilot.copilot(c, req2))
        assert res_quota['quota_exhausted'] is True
        assert res_quota['mode'] == 'Quota exhausted'
        assert res_quota['proposals'] == []
        assert 'exhausted' in res_quota['reply'].lower()
