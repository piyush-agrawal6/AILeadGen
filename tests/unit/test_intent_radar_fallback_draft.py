"""Tests for deterministic AI draft fallback keyword quality and source constraint preservation."""
from app.intent_radar import ai


AVAILABLE_CATALOG = [
    {'id': 'hacker_news', 'state': 'Available'},
    {'id': 'stack_exchange', 'state': 'Available'},
    {'id': 'github', 'state': 'Connected'},
    {'id': 'youtube', 'state': 'Available'},
    {'id': 'bluesky', 'state': 'Available'},
]


def test_fallback_strips_meaningless_stopwords_and_preserves_explicit_available_sources():
    draft, warning = ai.fallback(
        'Find recent discussions especially on GitHub and YouTube about Kubernetes observability latency',
        available_sources=AVAILABLE_CATALOG,
    )
    assert warning is None
    assert draft.configuration.sources == ['github', 'youtube']
    for bad in ('recent', 'discussions', 'especially', 'find', 'github', 'youtube'):
        assert bad not in draft.configuration.keywords
    assert 'kubernetes' in draft.configuration.keywords
    assert 'observability' in draft.configuration.keywords


def test_fallback_never_silently_switches_unavailable_requested_source_to_hacker_news():
    draft, warning = ai.fallback(
        'Search Reddit and LinkedIn for recent discussions about SOC2 compliance automation',
        available_sources=AVAILABLE_CATALOG,
    )
    assert warning is not None
    assert 'Reddit' in warning and 'LinkedIn' in warning
    assert draft.configuration.sources == []
    assert 'hacker_news' not in draft.configuration.sources
    assert 'recent' not in draft.configuration.keywords
    assert 'discussions' not in draft.configuration.keywords
    assert 'soc2' in draft.configuration.keywords
