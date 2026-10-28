export type Opportunity = "WEBSITE" | "SEO" | "SECURITY";
export interface SocialProfile { platform:string; profile_url:string; handle?:string; activity_status?:string; last_activity_at?:string|null; activity_reason?:string; activity_evidence_url?:string|null; source_type?:string; confidence?:string }

export type LeadStatus = "NEW" | "SHORTLISTED" | "READY_TO_CONTACT" | "FOLLOW_UP" | "MEETING" | "PROPOSAL" | "CONTACTED" | "REPLIED" | "NOT_INTERESTED" | "DO_NOT_CONTACT" | "WON" | "LOST";

export const STATUSES: LeadStatus[] = ["NEW", "SHORTLISTED", "READY_TO_CONTACT", "FOLLOW_UP", "MEETING", "PROPOSAL", "CONTACTED", "REPLIED", "NOT_INTERESTED", "DO_NOT_CONTACT", "WON", "LOST"];

export interface City { id: string; display_name: string; lookup_name: string; country: string; country_code: string; priority: number }

export interface Country { country: string; country_code: string; cities: City[] }

export interface CampaignConfig { cities: string[]; verticals: string[]; opportunities: Opportunity[]; quality: "maximum_volume" | "balanced" | "high_intent"; business_scales: string[]; results: "new" | "include_previous" | "all"; target: number; lighthouse_enabled: boolean; social_enrichment_enabled?:boolean; social_activity_enabled?:boolean; request_id: string; fixture?: boolean }

export interface ChildRun { id: number; market: string; vertical: string; target: number; status: string; raw_found: number; qualified: number; exported: number; started_at?: string; finished_at?: string; error_message?: string }

export interface Campaign { id: string; created_by: string; status: string; created_at: string; completed_at?: string; configuration: CampaignConfig; target_total: number; runs: ChildRun[]; counters: { raw_found: number; qualified: number; exported: number }; progress: Record<string, number>; opportunities: { website: number; seo: number; security: number } }

export interface Evidence { code: string; points: number; detail: string }

export interface OpportunityScores { website_opportunity_score: number | null; seo_opportunity_score: number | null; security_opportunity_score: number | null; primary_opportunity: Opportunity | null; secondary_opportunity: Opportunity | null; contactability_level: string; scoring_version: string; evidence: Record<Opportunity, Evidence[]> }

export type ReportStatus = "QUEUED" | "GENERATING" | "READY" | "FAILED";
export interface ClientReport { id:string; prospect_id:string; business_id:number; business_name:string; status:ReportStatus; version:number; created_at:string; created_by:string; ready_report_id?:string|null; error_message?:string|null }
export interface IntelligenceLead extends Partial<OpportunityScores> { social_profiles?:SocialProfile[]; commercial_fit?:string; social_presence_status?:string; latest_report_id?:string|null; latest_report_status?:ReportStatus|null; ready_report_id?:string|null; report_version?:number|null; id: number; prospect_id: string | null; name: string; city: string; country: string; vertical: string; website: string | null; domain: string | null; phone: string | null; public_email: string | null; lead_status: LeadStatus; assigned_to: string | null; business_scale: string | null; first_seen_at: string | null; last_seen_at: string | null; times_discovered: number | null }

export interface Note { id: string; body: string; created_by: string; created_at: string }

export interface Workspace { social_profiles?:SocialProfile[]; intelligence?:{commercial_fit:string;commercial_reason:string;scale_reason:string;classification_version:string;social_presence_status:string}|null; id: string; lead_status: LeadStatus; assigned_to: string | null; first_seen_at: string; last_seen_at: string; times_discovered: number; business_scale: string; scale_reason: string; notes: Note[]; opportunity: OpportunityScores | null }

export interface User { id: string; email: string; display_name: string }

export interface LeadPage { items: IntelligenceLead[]; page: number; page_size: number; total: number; total_pages: number }

export interface Overview { total_leads: number; assessed_leads: number; unassessed_leads: number; new_leads: number; high_intent: number; website: number; seo: number; security: number; uncontacted: number; running_campaigns: number; statuses: { lead_status: string; count: number }[]; markets: { city: string; vertical: string; count: number }[] }

export async function request<T>(path: string, options?: RequestInit): Promise<T> {

  const response = await fetch(`/api${path}`, { ...options, headers: { "Content-Type": "application/json", ...options?.headers } });

  if (!response.ok) {

    const data = await response.json().catch(() => ({}));

    throw new Error(typeof data.detail === "string" ? data.detail : response.status === 401 ? "Sign in to continue." : "This request could not be completed. Check the selection and retry.");

  }

  return response.json() as Promise<T>;

}

export const label = (value: string) => value.replaceAll("_", " ").toLowerCase().replace(/\b\w/g, letter => letter.toUpperCase());

