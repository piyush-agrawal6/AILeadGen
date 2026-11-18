from uuid import UUID
from typing import Literal
from pydantic import Field
from app.intent_radar.models import Strict
from app.intent_radar import service


class Search(Strict):
    search: str = Field('', max_length=120)
    page: int = Field(1, ge=1, le=10000)


class SignalSearch(Strict):
    search: str = Field('', max_length=120)
    source: str = Field('', max_length=40)
    category: str = Field('', max_length=50)
    status: str = Field('', max_length=30)
    view: Literal['', 'all', 'needs_review', 'high_intent', 'saved', 'qualified', 'dismissed'] = ''
    min_score: int = Field(0, ge=0, le=100)
    sort: Literal['newest', 'oldest', 'score', 'score_asc', 'title'] = 'newest'
    page: int = Field(1, ge=1, le=10000)


class SignalID(Strict):
    id: UUID


class Empty(Strict):
    pass


# Preserve exact 9-tool contract expected by existing MCP protocol tests.
READ = {
    'search_intent_signals': SignalSearch,
    'list_intent_monitors': Search,
    'get_intent_signal': SignalID,
    'list_intent_opportunities': Search,
    'list_intent_sources': Empty,
    'get_intent_analysis': SignalID,
    'get_intent_run': SignalID,
    'get_intent_source_health': Empty,
    'get_intent_workspace_context': Empty,
}

# Additional read-only Intent Radar tools backed by real workspace endpoints.
EXTENDED_READ = {
    'list_intent_discoveries': Search,
    'get_intent_discovery': SignalID,
    'list_saved_searches': Search,
    'list_intent_icps': Empty,
}

GROWTH_READ = {
    'list_market_themes': Search,
    'get_growth_research': SignalID,
    'get_market_overview': Empty,
    'list_growth_watchlists': Empty,
}


def read(c, name, arguments):
    args = (READ | EXTENDED_READ | GROWTH_READ)[name].model_validate(arguments)
    if name in ('list_market_themes', 'get_growth_research', 'get_market_overview', 'list_growth_watchlists'):
        from app.growth_intelligence import service as growth, analytics, models
        if name == 'list_market_themes':
            return growth.themes(c, search=args.search, page=args.page, size=20)
        if name == 'get_growth_research':
            return growth.detail(c, str(args.id))
        if name == 'get_market_overview':
            return analytics.overview(c, models.Scope())
        return growth.watchlists(c)
    if name == 'get_intent_source_health':
        from app.intent_radar.operations import source_health
        return source_health(c)
    if name == 'get_intent_workspace_context':
        from app.intent_radar.operations import workspace_context
        return workspace_context(c)
    if name == 'list_intent_sources':
        from app.intent_radar.providers import catalog
        return {'items': catalog(c)}
    if name == 'get_intent_analysis':
        from app.intent_radar.intelligence import history
        result = history(c, str(args.id))
        result['items'] = result['items'][:1]
        return result
    if name == 'get_intent_run':
        from app.intent_radar.discovery import owned_job
        return owned_job(c, str(args.id))
    if name == 'list_intent_discoveries':
        from app.intent_radar import discovery_workspace
        return discovery_workspace.list_discoveries(c, search=args.search, page=args.page, page_size=20)
    if name == 'get_intent_discovery':
        from app.intent_radar import discovery_workspace
        return discovery_workspace.get_discovery(c, str(args.id))
    if name == 'list_saved_searches':
        from app.intent_radar import discovery_workspace
        return discovery_workspace.list_saved_searches(c, search=args.search, page=args.page, page_size=20)
    if name == 'list_intent_icps':
        from app.intent_radar.permissions import context
        context(c)
        from app.icp.service import listing
        return listing(c)
    if name == 'get_intent_signal':
        return service.get(c, 'signals', str(args.id))
    if name == 'search_intent_signals':
        return service.listing(
            c,
            'signals',
            page=args.page,
            size=20,
            search=args.search,
            source=args.source,
            category=args.category,
            status=args.status,
            view=args.view,
            min_score=args.min_score,
            sort=args.sort,
        )
    return service.listing(
        c,
        'monitors' if name == 'list_intent_monitors' else 'opportunities',
        size=20,
        page=args.page,
        search=args.search,
    )
