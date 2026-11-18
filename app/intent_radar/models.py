from datetime import date
from typing import Annotated, Literal
from uuid import UUID, uuid4
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, model_validator

Category = Literal[
    'Recommendation request',
    'Problem / pain point',
    'Product comparison',
    'Alternative search',
    'Tool / service evaluation',
    'Purchase consideration',
    'Feature request',
    'Competitor activity',
    'Market / technology intelligence',
    'General discussion',
    'Uncertain',
]
SourceId = Literal['hacker_news','stack_exchange','github','youtube','bluesky','discourse','rss','atom']
Term = Annotated[str, Field(min_length=1, max_length=100)]
Language = Literal['en','es','fr','de','pt','hi','ja']

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

class Search(Strict):
    _collection_cursor: dict = PrivateAttr(default_factory=dict)
    keywords: list[Term] = Field(min_length=1, max_length=12)
    excluded: list[Term] = Field(default_factory=list, max_length=12)
    topics: list[Term] = Field(default_factory=list, max_length=12)
    phrases: list[Term] = Field(default_factory=list, max_length=12)
    offerings: str = Field('', max_length=500)
    source: Literal['Hacker News'] = 'Hacker News'
    sources: list[SourceId] = Field(default_factory=lambda:['hacker_news'],min_length=1,max_length=8)
    hn_feeds: list[Literal['ask','show','new','top','best','jobs']] = Field(default_factory=lambda:['ask'],min_length=1,max_length=6)
    hn_comments: bool = False
    sites: list[Term] = Field(default_factory=lambda:['stackoverflow'],max_length=5)
    tags: list[Term] = Field(default_factory=list,max_length=5)
    se_include_answers: bool = False
    se_include_comments: bool = False
    github_kinds: list[Literal['repositories','issues','discussions','pull_requests','releases']] = Field(default_factory=lambda:['issues','discussions'],min_length=1,max_length=5)
    github_repos: list[Term] = Field(default_factory=list,max_length=5)
    github_comments: bool = False
    github_scope: Literal['public','connected'] = 'public'
    youtube_mode: Literal['videos','channels','both'] = 'videos'
    youtube_comments: bool = True
    youtube_channel_ids: list[Term] = Field(default_factory=list,max_length=3)
    bluesky_mode: Literal['search','profiles','feeds'] = 'search'
    bluesky_handles: list[Term] = Field(default_factory=list,max_length=5)
    bluesky_threads: bool = False
    feed_ids: list[UUID] = Field(default_factory=list,max_length=10)
    icp_id: UUID | None = None
    semantic: bool = False
    semantic_criteria: list[Term] = Field(default_factory=list,max_length=12)
    semantic_exclusions: list[Term] = Field(default_factory=list,max_length=12)
    semantic_analysis_limit: int = Field(3,ge=1,le=10)
    summary_language: Language | None = None
    categories: list[Category] = Field(default_factory=list, max_length=11)
    language: Literal['Any / unverified','en','es','fr','de','pt','hi','ja'] = 'Any / unverified'
    geography: Literal['Any / unknown'] = 'Any / unknown'
    from_date: date | None = None
    to_date: date | None = None
    min_relevance: int = Field(0, ge=0, le=100)
    result_limit: int = Field(20, ge=1, le=20)
    @model_validator(mode='after')
    def dates(self):
        if self.from_date and self.to_date and self.from_date > self.to_date: raise ValueError('The start date must not follow the end date.')
        self.sources=list(dict.fromkeys(self.sources))
        self.hn_feeds=list(dict.fromkeys(self.hn_feeds))
        self.github_kinds=list(dict.fromkeys(self.github_kinds))
        self.sites=list(dict.fromkeys(s.casefold() for s in self.sites))
        if (self.semantic_criteria or self.semantic_exclusions or self.summary_language or self.language!='Any / unverified') and not self.semantic:
            raise ValueError('Semantic/language criteria require explicitly approved semantic analysis.')
        return self

class SourceResult(BaseModel):
    """Validated bounded adapter contract; provider metadata is retained."""
    model_config=ConfigDict(extra='allow',strict=True)
    items:list[dict]=Field(max_length=200)
    requests:int=Field(ge=0,le=60)
    scanned:int=Field(ge=0,le=200)
    next_offset:int | None=None
    coverage:str=Field(min_length=1,max_length=2000)
    cursor:dict | None=None
    def __getitem__(self,key):return self.model_dump()[key]
    def get(self,key,default=None):return self.model_dump().get(key,default)
    @model_validator(mode='after')
    def source_records(self):
        for item in self.items:
            if not isinstance(item.get('source_record_id'),str) or type(item.get('removed')) is not bool:raise ValueError('Source identity and removal state required.')
            if not item['removed']:
                for field in ('source_url','title','excerpt','observed_at','retrieved_at'):
                    if not isinstance(item.get(field),str):raise ValueError('Normalized source evidence required.')
                from urllib.parse import urlsplit
                url=urlsplit(item['source_url'])
                if url.scheme not in ('http','https') or not url.hostname or url.username or url.password:raise ValueError('Original source link must be an ordinary public web URL, without credentials.')
                from datetime import datetime
                for field in ('observed_at','retrieved_at'):
                    if datetime.fromisoformat(item[field]).tzinfo is None:raise ValueError('Normalized source timestamps must include their timezone.')
        return self

class Monitor(Strict):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field('', max_length=1000)
    goal: str = Field('', max_length=200)
    configuration: Search
    status: Literal['Draft', 'Active', 'Paused', 'Archived'] = 'Draft'
    request_id: UUID = Field(default_factory=uuid4)
    revision: int | None = Field(None, ge=1)

class Schedule(Strict):
    frequency: Literal['Manual','Daily','12 hours','6 hours'] = 'Manual'
    timezone: str = Field('UTC',max_length=80)
    revision: int = Field(ge=1)

class SourceConfig(Strict):
    name: str = Field(min_length=1,max_length=120)
    family: Literal['rss','discourse','atom']
    endpoint: str = Field(min_length=10,max_length=1000)
    policy_reference: str = Field(min_length=10,max_length=1000)
    attribution: str = Field(min_length=1,max_length=300)
    retention_days: int = Field(7,ge=1,le=30)
    polling_minutes: int = Field(60,ge=60,le=1440)
    enabled: bool = False
    ai_processing_authorized: bool = False
    content_kind: Literal['question','answer','comment','story','job','release','repository','issue','discussion','pull_request','article','paper','video','channel','playlist','post'] | None = None

class AnalysisRequest(Strict):
    icp_id: UUID | None = None
    monitor_id: UUID | None = None
    summary_language: Language | None = None
    force: bool = False
    ignore_default_icp: bool = False

class Feedback(Strict):
    label: Literal['Relevant','Not relevant','Unsure','Wrong intent category','Not a target customer','Too old','Duplicate','Helpful recommendation','Incorrect AI summary']
    note: str = Field('',max_length=1000)
    active: bool = True

class Attribution(Strict):
    author: str = Field('',max_length=100)
    profile_url: str | None = Field(None,max_length=1000)
    license: str = Field('CC BY-SA',max_length=100)
    source: Literal['Stack Exchange','GitHub','YouTube','Bluesky','Hacker News','Approved Discourse','RSS / Atom','Atom'] = 'Stack Exchange'

class Provenance(Strict):
    site: str | None = Field(None,max_length=100)
    tags: list[Term] = Field(default_factory=list,max_length=10)
    updated_at: int | str | None = None
    attribution: Attribution | str | None = None
    fetch_method: Literal['official_api','official_graphql','official_jetstream','public_feed','official_hn','github_webhook'] | None = None
    feed_id: str | None = Field(None,max_length=100)
    feed_name: str | None = Field(None,max_length=120)
    policy_reference: str | None = Field(None,max_length=1000)
    retention_days: int | None = Field(None,ge=1,le=30)
    categories: list[str] = Field(default_factory=list,max_length=10)
    declared_feed_language: str | None = Field(None,max_length=30)
    feed_format: Literal['rss','atom'] | None = None
    feed_authors: list[str] = Field(default_factory=list,max_length=10)
    feed_self_url: str | None = Field(None,max_length=1000)
    published_at: str | None = Field(None,max_length=60)
    observed_time_basis: Literal['published','updated'] | None = None
    content_kind: Literal['question','answer','comment','story','job','release','repository','issue','discussion','pull_request','article','paper','video','channel','playlist','post'] | None = None
    repo: str | None = Field(None,max_length=200)
    channel_id: str | None = Field(None,max_length=100)
    video_id: str | None = Field(None,max_length=60)
    author_handle: str | None = Field(None,max_length=120)
    is_answered: bool | None = None
    accepted_answer_id: int | None = None
    answer_count: int | None = None
    visibility: Literal['public','private_connected'] | None = None
    ai_processing_authorized: bool | None = None
    ai_policy_note: str | None = Field(None,max_length=300)
    parent_id: str | None = Field(None,max_length=120)
    depth: int | None = Field(None,ge=0,le=4)
    metrics: dict[str,int] | None = None


class SearchStrategy(Strict):
    objective: str = Field('', max_length=400)
    target_customer_context: str = Field('', max_length=400)
    keyword_rationale: str = Field('', max_length=500)
    source_rationale: str = Field('', max_length=500)
    exclusions_rationale: str = Field('', max_length=400)
    limitations: list[str] = Field(default_factory=list, max_length=6)


class Discovery(Strict):
    configuration: Search
    monitor_id: UUID | None = None
    request_id: UUID = Field(default_factory=uuid4)
    title: str = Field('', max_length=120)
    original_prompt: str = Field('', max_length=2000)
    search_mode: Literal['ai', 'advanced', 'monitor', 'rerun'] = 'advanced'
    parent_discovery_id: UUID | None = None
    strategy: SearchStrategy | None = None

class SignalUpdate(Strict):
    revision: int = Field(ge=1)
    status: Literal['New', 'In Review', 'Reviewed', 'Qualified', 'Saved', 'Dismissed', 'Needs Review']
    notes: str | None = Field(None, max_length=4000)

class Bulk(Strict):
    ids: list[UUID] = Field(min_length=1, max_length=50)
    action: Literal['save', 'unsave', 'review', 'qualify', 'dismiss', 'opportunity', 'unqualify', 'needs_review']

class OpportunityCreate(Strict):
    priority: Literal['High', 'Medium', 'Low'] = 'Medium'
    notes: str = Field('', max_length=4000)
    next_action: str = Field('Review context', max_length=300)

class OpportunityUpdate(Strict):
    revision: int = Field(ge=1)
    status: Literal['New', 'Reviewing', 'Qualified', 'Saved', 'Dismissed']
    priority: Literal['High', 'Medium', 'Low']
    notes: str = Field('', max_length=4000)
    next_action: str = Field('Review context', max_length=300)
    assigned_to: str | None = Field(None, max_length=254)

class SavedUpdate(Strict):
    revision: int = Field(ge=1)
    collection: str = Field('Inbox', min_length=1, max_length=100)
    tags: list[Term] = Field(default_factory=list, max_length=12)
    notes: str = Field('', max_length=4000)

class Preferences(Strict):
    source_retention_days:int=Field(30,ge=1,le=365)
    default_view: Literal['table', 'cards'] = 'table'
    min_relevance: int = Field(0, ge=0, le=100)
    default_icp_id: UUID | None = None
    ai_assistance: bool = True
    analysis_daily_call_limit: int = Field(3,ge=1,le=10)
    analysis_daily_token_limit: int = Field(100000,ge=6000,le=300000)
    topics: list[Term] = Field(default_factory=list, max_length=12)
    discovery_keywords: list[Term] = Field(default_factory=list, max_length=12)
    discovery_excluded: list[Term] = Field(default_factory=list, max_length=12)
    alerts_enabled: bool = True
    alert_threshold: int = Field(85, ge=0, le=100)
    revision: int = Field(0, ge=0)

class Prompt(Strict):
    prompt: str = Field(min_length=10, max_length=2000)
    previous: Search | None = None
    icp_id: UUID | None = None

class SearchDraft(Strict):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field('', max_length=1000)
    configuration: Search
    strategy: SearchStrategy | None = None

CopilotActionType = Literal[
    'add_keywords',
    'remove_keywords',
    'replace_keywords',
    'add_exclusions',
    'set_intent_categories',
    'select_sources',
    'choose_icp',
    'update_filters',
    'suggest_search_configuration',
]

class CopilotProposal(Strict):
    id: str = Field(min_length=1, max_length=64)
    action: CopilotActionType
    label: str = Field(min_length=1, max_length=120)
    rationale: str = Field('', max_length=400)
    keywords: list[Term] = Field(default_factory=list, max_length=12)
    excluded: list[Term] = Field(default_factory=list, max_length=12)
    phrases: list[Term] = Field(default_factory=list, max_length=12)
    topics: list[Term] = Field(default_factory=list, max_length=12)
    categories: list[Category] = Field(default_factory=list, max_length=11)
    sources: list[SourceId] = Field(default_factory=list, max_length=8)
    icp_id: UUID | None = None
    min_relevance: int | None = Field(None, ge=0, le=100)
    result_limit: int | None = Field(None, ge=1, le=20)
    from_date: date | None = None
    to_date: date | None = None
    configuration: Search | None = None

class CopilotHistoryMessage(Strict):
    role: Literal['user', 'assistant']
    content: str = Field(min_length=1, max_length=1500)

class CopilotRequest(Strict):
    message: str = Field(min_length=1, max_length=1500)
    quick_action: Literal[
        'improve_keywords',
        'suggest_sources',
        'exclude_noise',
        'align_icp',
        'broaden_search',
        'narrow_search',
        'explain_strategy',
        'suggest_search',
        'refine_after_results',
    ] | None = None
    draft: Search | None = None
    original_prompt: str = Field('', max_length=2000)
    icp_id: UUID | None = None
    active_run_id: UUID | None = None
    history: list[CopilotHistoryMessage] = Field(default_factory=list, max_length=10)

class CopilotAiOutput(Strict):
    reply: str = Field(min_length=1, max_length=2000)
    strategy: SearchStrategy | None = None
    proposals: list[CopilotProposal] = Field(default_factory=list, max_length=8)
    warnings: list[str] = Field(default_factory=list, max_length=5)

class RequestKey(Strict):
    request_id: UUID = Field(default_factory=uuid4)
