export interface DashboardSummaryCards {
  total_businesses: number;
  qualified_leads: number;
  a_plus_leads: number;
  a_leads: number;
  no_website_opportunities: number;
  completed_scans: number;
}

export interface TierCount {
  tier: string;
  count: number;
  percentage: number;
}

export interface ServiceCount {
  service: string;
  count: number;
}

export interface VerticalCount {
  vertical: string;
  count: number;
}

export interface ScoreBucket {
  range: string;
  count: number;
}

export interface RecentScanItem {
  id: number;
  market: string;
  vertical: string;
  status: string;
  target: number;
  qualified: number;
  exported: number;
  started_at?: string | null;
  finished_at?: string | null;
  duration_seconds?: number | null;
  output_file?: string | null;
}

export interface DashboardResponse {
  cards: DashboardSummaryCards;
  tier_distribution: TierCount[];
  recommended_services: ServiceCount[];
  vertical_distribution: VerticalCount[];
  score_distribution: ScoreBucket[];
  recent_scans: RecentScanItem[];
}

export interface ScanSettings {
  exclude_chains: boolean;
  lighthouse_enabled: boolean;
  overture_enabled: boolean;
  osm_enabled: boolean;
  max_pages?: number;
  page_timeout?: number;
  site_timeout?: number;
  http_concurrency?: number;
  crawler_concurrency?: number;
  min_score?: number;
}

export interface ScanCreateRequest {
  market: string;
  vertical: string;
  target: number;
  settings?: ScanSettings;
}

export interface ScanCreateResponse {
  run_id: number;
  status: string;
  message: string;
}

export interface PipelineRunDetail {
  id: number;
  market: string;
  vertical: string;
  target: number;
  started_at?: string | null;
  finished_at?: string | null;
  status: string;
  raw_found: number;
  deduped: number;
  filtered: number;
  websites_processed: number;
  qualified: number;
  exported: number;
  output_file?: string | null;
  error_message?: string | null;
  cancelled_at?: string | null;
  run_configuration?: Record<string, unknown> | null;
  duration_seconds?: number | null;
}

export interface PipelineEventSchema {
  id?: number | null;
  run_id: number;
  timestamp?: string | null;
  stage: string;
  event_type: string;
  message: string;
  completed: number;
  total: number;
  metadata_json?: string | null;
}

export interface LeadListItem {
  id: number;
  run_id?: number | null;
  name: string;
  vertical: string;
  city?: string | null;
  state?: string | null;
  country?: string | null;
  website?: string | null;
  domain?: string | null;
  website_status: string;
  phone?: string | null;
  public_email?: string | null;
  instagram?: string | null;
  facebook?: string | null;
  linkedin?: string | null;
  total_score: number;
  tier: string;
  recommended_service?: string | null;
  performance_score?: number | null;
  seo_score?: number | null;
  calculated_at?: string | null;
}

export interface LeadPaginationResponse {
  items: LeadListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface FindingDetail {
  id: number;
  finding_code: string;
  category: string;
  severity: string;
  title: string;
  description: string;
  evidence?: string | null;
  score_points: number;
}

export interface ContactDetail {
  id: number;
  type: string;
  value: string;
  source_type?: string | null;
  confidence: number;
}

export interface LighthouseMetrics {
  performance_score?: number | null;
  seo_score?: number | null;
  accessibility_score?: number | null;
  best_practices_score?: number | null;
  lcp_ms?: number | null;
  cls?: number | null;
  tbt_ms?: number | null;
  fcp_ms?: number | null;
  speed_index_ms?: number | null;
}

export interface WebsiteProfileDetail {
  http_status?: number | null;
  https_enabled: boolean;
  reachable: boolean;
  redirect_count: number;
  final_url?: string | null;
  html_title?: string | null;
  meta_description?: string | null;
  has_contact_page: boolean;
  has_booking: boolean;
  has_menu: boolean;
  detected_technologies: string[];
  schema_types: string[];
  page_count_crawled: number;
}

export interface LeadScoreBreakdown {
  total: number;
  tier: string;
  website_score: number;
  seo_score: number;
  vertical_score: number;
  contactability_score: number;
  recommended_service: string;
  recommended_angle: string;
  breakdown: Record<string, unknown>;
  calculated_at?: string | null;
}

export interface LeadDetailResponse {
  business: {
    id: number; name: string; vertical: string;
    city?: string | null; state?: string | null; country?: string | null;
    website?: string | null; public_email?: string | null;
    phone?: string | null; normalized_phone?: string | null;
    instagram?: string | null; facebook?: string | null; linkedin?: string | null; x_url?: string | null;
    vertical_validation_status?: string; vertical_validation_reason?: string | null;
    is_chain?: boolean; chain_reason?: string | null;
    source_confidence?: number; source_osm?: boolean; source_overture?: boolean;
  };
  website_status: string;
  score?: LeadScoreBreakdown | null;
  profile?: WebsiteProfileDetail | null;
  lighthouse?: LighthouseMetrics | null;
  findings: FindingDetail[];
  contacts: ContactDetail[];
}

export interface ReportArtifactItem {
  run_id: number;
  market: string;
  vertical: string;
  target: number;
  qualified: number;
  exported: number;
  started_at?: string | null;
  finished_at?: string | null;
  status: string;
  excel_url?: string | null;
  csv_url?: string | null;
  has_excel: boolean;
  has_csv: boolean;
}

export interface GeneralSettings {
  default_target: number;
  default_vertical: string;
  exclude_chains: boolean;
  default_min_tier: string;
}

export interface DiscoverySettings {
  overture_enabled: boolean;
  osm_enabled: boolean;
  nominatim_endpoint: string;
  overpass_endpoint: string;
  candidate_multiplier: number;
}

export interface CrawlerSettings {
  max_pages: number;
  page_timeout_seconds: number;
  max_site_duration_seconds: number;
  http_concurrency: number;
  crawl_concurrency: number;
  max_response_bytes: number;
}

export interface AuditingSettings {
  lighthouse_enabled: boolean;
  lighthouse_concurrency: number;
  lighthouse_timeout_seconds: number;
  quick_audit_enabled: boolean;
  structured_data_detection: boolean;
  technology_detection: boolean;
  vertical_audit_enabled: boolean;
}

export interface ScoringPillarWeight {
  pillar: string;
  max_points: number;
  description: string;
}

export interface ScoringSettings {
  minimum_score: number;
  pillars: ScoringPillarWeight[];
}

export interface AppSettingsSchema {
  general: GeneralSettings;
  discovery: DiscoverySettings;
  crawler: CrawlerSettings;
  auditing: AuditingSettings;
  scoring: ScoringSettings;
}

export interface DiagnosticItem {
  name: string;
  status: string;
  details: string;
  ready: boolean;
}

export interface SystemDoctorResponse {
  overall_status: string;
  diagnostics: DiagnosticItem[];
  api_version: string;
  environment: string;
}

export interface MarketItem {
  query: string;
  city: string;
  state: string;
  country: string;
  country_code: string;
  center_lat: number;
  center_lon: number;
}

export interface VerticalItem {
  key: string;
  display_name: string;
  aliases: string[];
}
