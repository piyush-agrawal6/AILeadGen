export type OpportunityEligibility={eligible:boolean;intent_quote:string|null;reasons:string[];basis:string;next_step:string;policy_version:string};
export const INTENT_CATEGORIES = ['Recommendation request','Problem / pain point','Product comparison','Alternative search','Tool / service evaluation','Purchase consideration','Feature request','Competitor activity','Market / technology intelligence','General discussion','Uncertain'] as const;
export type IntentCategory = typeof INTENT_CATEGORIES[number];
export type SourceId='hacker_news'|'stack_exchange'|'github'|'youtube'|'bluesky'|'discourse'|'rss'|'atom';
export type IntentSearch = {keywords:string[];excluded:string[];topics:string[];phrases:string[];offerings:string;source:'Hacker News';sources?:SourceId[];hn_feeds?:string[];hn_comments?:boolean;sites?:string[];tags?:string[];se_include_answers?:boolean;se_include_comments?:boolean;github_kinds?:('repositories'|'issues'|'discussions'|'pull_requests'|'releases')[];github_repos?:string[];github_comments?:boolean;github_scope?:'public'|'connected';youtube_mode?:'videos'|'channels'|'both';youtube_comments?:boolean;youtube_channel_ids?:string[];bluesky_mode?:'search'|'profiles'|'feeds';bluesky_handles?:string[];bluesky_threads?:boolean;feed_ids?:string[];icp_id?:string|null;semantic?:boolean;semantic_criteria?:string[];semantic_exclusions?:string[];semantic_analysis_limit?:number;summary_language?:'en'|'es'|'fr'|'de'|'pt'|'hi'|'ja'|null;categories:IntentCategory[];language:'Any / unverified'|'en'|'es'|'fr'|'de'|'pt'|'hi'|'ja';geography:'Any / unknown';from_date:string|null;to_date:string|null;min_relevance:number;result_limit:number};
export const emptyIntentSearch = ():IntentSearch => ({keywords:[],excluded:[],topics:[],phrases:[],offerings:'',source:'Hacker News',categories:[],language:'Any / unverified',geography:'Any / unknown',from_date:null,to_date:null,min_relevance:0,result_limit:20});
export type SignalViewKey = 'all' | 'needs_review' | 'high_intent' | 'saved' | 'qualified' | 'dismissed';
export interface SignalViewCounts {
  all: number;
  needs_review: number;
  high_intent: number;
  saved: number;
  qualified: number;
  dismissed: number;
}
export interface SignalActivityEvent {
  kind: 'collected' | 'saved' | 'analysis' | 'feedback' | 'opportunity' | 'audit' | string;
  title: string;
  detail: string;
  actor: string | null;
  at: string;
}
export interface SignalAnalysisStructured {
  summary: string | null;
  problem: string | null;
  topic_relevance: string | null;
  translated_summary?: string | null;
  translated_problem?: string | null;
  translated_relevance?: string | null;
  buying_intent: 'Explicit commercial intent' | 'Possible commercial intent' | 'No demonstrated commercial intent' | 'Insufficient evidence';
  icp_fit: string;
  recommended_next_step: string;
  source_statements: string[];
  model_inferences: string[];
  unknowns: string[];
}
export interface IntentEvidence {matched_keywords:string[];matched_topics:string[];intent_phrase:string|null;confidence:string;explanation:string;observed_text:string;unknown:string[];penalties?:string[];purchasing_event_verified:false;discovery_id?:string;provenance?:{attribution?:string|{author?:string;profile_url?:string;license?:string;source?:string};declared_feed_language?:string;policy_reference?:string;fetch_method?:string;content_kind?:string;repo?:string;site?:string;feed_name?:string;visibility?:string;retention_days?:number;ai_processing_authorized?:boolean;ai_policy_note?:string}}
export interface IntentSignal {
  opportunity_eligibility?:OpportunityEligibility;
  id:string;title:string;source:string;source_url:string;excerpt:string;observed_at:string;retrieved_at:string;category:IntentCategory;score:number;status:string;notes:string;revision:number;available:number;saved:boolean;evidence:IntentEvidence;monitors:{id:string;name:string}[];
  buying_intent?: 'Explicit commercial intent' | 'Possible commercial intent' | 'No demonstrated commercial intent' | 'Insufficient evidence' | null;
  buying_intent_basis?: 'ai_assessed' | 'unassessed';
  icp_fit?: 'Match' | 'Possible' | 'Mismatch' | 'Unassessed';
  icp_fit_detail?: string;
  has_analysis?: boolean;
  latest_analysis_at?: string | null;
  latest_analysis_summary?: string | null;
  latest_analysis_mode?: string | null;
  opportunity_id?: string | null;
  opportunity_status?: string | null;
  discovery_id?: string | null;
  discovery_title?: string | null;
  feedback_label?: string | null;
  activity?: SignalActivityEvent[];
}
export interface IntentMonitor {id:string;name:string;description:string;goal:string;configuration:IntentSearch;status:'Draft'|'Active'|'Paused'|'Archived';revision:number;created_at:string;last_checked:string|null;last_job_id:string|null;schedule?:{frequency:string;timezone:string};next_run_at?:string|null;signals_count?:number}
export interface IntentOpportunity {
  opportunity_eligibility?: OpportunityEligibility;
  signal?: IntentSignal;
  id: string;
  signal_id: string;
  status: string;
  priority: string;
  notes: string;
  next_action: string;
  assigned_to: string | null;
  revision: number;
  created_at?: string;
  updated_at?: string;
  created_by?: string;
}

export interface OpportunityStatusCounts {
  all: number;
  new: number;
  reviewing: number;
  qualified: number;
  saved: number;
  dismissed: number;
}
export interface IntentSaved {signal?:IntentSignal;signal_id:string;collection:string;tags:string[];notes:string;revision:number}
export interface IntentAlert {id:string;monitor_id:string|null;signal_id:string|null;title:string;description:string;created_at:string;read_at:string|null}
export interface IntentJob {id:string;discovery_id?:string;monitor_id?:string;status:string;error_code:string|null;created_at:string;attempts:number;sources?:{provider:string;status:string;coverage:string;requests:number;scanned:number;retry_at?:string}[];items:{status:string;error_code:string|null;result:{signals?:string[];scanned?:number;matched?:number;requests?:number;coverage?:string}}[]}
export interface IntentLimitsMeta {
  platform_daily_call_limit: number;
  platform_daily_token_limit: number;
  effective_daily_call_limit: number;
  effective_daily_token_limit: number;
  calls_used_today: number;
  tokens_used_today: number;
  reset_at_utc: string;
  plan_monthly_ai_calls_limit?: number | null;
  plan_monthly_ai_calls_used?: number | null;
  plan_monthly_ai_calls_remaining?: number | null;
}
export interface IntentPreferences {discovery_keywords?:string[];discovery_excluded?:string[];default_view:'table'|'cards';min_relevance:number;topics:string[];alerts_enabled:boolean;alert_threshold:number;revision:number;default_icp_id?:string|null;ai_assistance?:boolean;analysis_daily_call_limit?:number;analysis_daily_token_limit?:number;source_retention_days?:number;limits_meta?:IntentLimitsMeta}
export type WorkspaceAccessState = 'ACTIVE' | 'TRIAL_ACTIVE' | 'CANCELED_REMAINING' | 'SETUP_REQUIRED' | 'TRIAL_AVAILABLE' | 'SUBSCRIPTION_REQUIRED' | 'PAYMENT_PENDING' | 'EXPIRED' | 'RESTRICTED';
export interface ProductAccess {billing_enabled?:boolean;organization_id:string|null;lead_engine_available?:boolean;lead_engine:boolean;intent_radar:{enabled:boolean;actions_enabled?:boolean;growth_enabled?:boolean;stage:'Disabled'|'Internal Preview'|'Beta';access_state?:WorkspaceAccessState;onboarding_status?:string|null;setup_deferred?:boolean;subscription_required?:boolean;subscription_active?:boolean;contract_status?:string|null;period_end?:number|null;trial_eligible?:boolean}}
export interface SourcePolicySummary {
  provider_id: string;
  publisher: string;
  authorized_app: string;
  authorization_reference: string;
  commercial_use_authorized: boolean;
  ai_processing_authorized: boolean;
  ai_status: string;
  capabilities: Record<string, boolean>;
  retention_days: number;
  attribution_required: string;
  restrictions: string[];
  missing_approval_note: string | null;
}
export interface IntentCapabilities {stage:string;actions_enabled?:boolean;growth_enabled?:boolean;can_write:boolean;can_manage:boolean;sources:{id?:SourceId;name:string;state:string;availability_label?:string;coverage:string;documentation:string;filters?:string[];request_limit_per_check?:number;configured_sites?:string[];oauth_configured?:boolean;webhooks_configured?:boolean;ai_analytics_authorized?:boolean;jetstream_enabled?:boolean;configured_feeds_count?:number;enabled_feeds_count?:number;policy?:SourcePolicySummary;permission?:string;missing?:string[]}[];usage:{searches_today:number;daily_search_limit:number;monitor_limit:number;automatic_schedules_enabled?:boolean;minimum_schedule_hours?:number}}
export interface IntentPage<T>{items:T[];total:number;page:number;page_size:number;has_more?:boolean;view_counts?:SignalViewCounts;status_counts?:OpportunityStatusCounts}
export interface IntentOverview {new_signals:number;reviewed_signals:number;high_relevance:number;active_monitors:number;saved_opportunities:number;unread_alerts:number;trends:{day:string;volume:number}[];recent_signals:IntentSignal[];monitors:IntentMonitor[];opportunities:IntentOpportunity[];alerts:IntentAlert[]}

export interface SearchStrategy {
  objective: string;
  target_customer_context: string;
  keyword_rationale: string;
  source_rationale: string;
  exclusions_rationale: string;
  limitations: string[];
}

export type CopilotActionType =
  | 'add_keywords'
  | 'remove_keywords'
  | 'replace_keywords'
  | 'add_exclusions'
  | 'set_intent_categories'
  | 'select_sources'
  | 'choose_icp'
  | 'update_filters'
  | 'suggest_search_configuration';

export interface CopilotProposal {
  id: string;
  action: CopilotActionType;
  label: string;
  rationale: string;
  keywords?: string[];
  excluded?: string[];
  phrases?: string[];
  topics?: string[];
  categories?: IntentCategory[];
  sources?: SourceId[];
  icp_id?: string | null;
  min_relevance?: number | null;
  result_limit?: number | null;
  from_date?: string | null;
  to_date?: string | null;
  configuration?: IntentSearch | null;
}

export interface DiscoveryContextSummary {
  context_version: string;
  company_name: string;
  has_company_profile: boolean;
  selected_icp_id: string | null;
  selected_icp_name: string;
  icp_count: number;
  available_source_ids: SourceId[];
  available_source_count: number;
  recent_run_count: number;
  draft_fingerprint: string;
}

export interface CopilotResponse {
  reply: string;
  strategy: SearchStrategy | null;
  proposals: CopilotProposal[];
  warnings: string[];
  mode: string;
  cached: boolean;
  quota_exhausted: boolean;
  fallback_reason: string | null;
  draft_fingerprint: string;
  context_summary?: DiscoveryContextSummary;
}

export interface DiscoverySourceRun {
  provider: string;
  status: string;
  scanned: number;
  requests: number | null;
  coverage: string;
  signals_count: number;
  retry_at?: string | null;
}

export interface DiscoveryRun {
  id: string;
  job_id: string | null;
  title: string;
  original_prompt: string;
  search_mode: 'ai' | 'advanced' | 'monitor' | 'rerun';
  parent_discovery_id: string | null;
  monitor_id: string | null;
  created_by: string;
  created_at: string;
  completed_at: string | null;
  status: string;
  error_code: string | null;
  attempts: number;
  sources: SourceId[];
  keywords: string[];
  matched_count: number;
  scanned_count: number;
  requests_count: number;
  coverage: string;
  configuration: IntentSearch;
  strategy: SearchStrategy | null;
  source_runs: DiscoverySourceRun[];
  signal_ids: string[];
  signals?: IntentSignal[];
}

export interface SavedSearch {
  id: string;
  name: string;
  description: string;
  original_prompt: string;
  configuration: IntentSearch;
  revision: number;
  last_run_discovery_id: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
}
