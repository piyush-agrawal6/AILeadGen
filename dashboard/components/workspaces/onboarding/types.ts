import type { CompanyFields, CompanyProfile } from '../company-profile-types';
import type { Candidate } from '../icp-suggestions';

export type Progress = {
  revision: number;
  current_step: string;
  objectives: string[];
  services: CompanyFields['products_services'];
  default_icp_id: string | null;
  preferences: {
    setup_mode: 'MANUAL' | 'AI';
    company_review_id: string | null;
    icp_review_id: string | null;
    research_keywords: string[];
    excluded_keywords: string[];
    setup_deferred?: boolean;
    [key: string]: unknown;
  };
  status: string;
  can_edit: boolean;
};

export type ProposedUpdate = {
  target:
    | 'description'
    | 'positioning'
    | 'industry'
    | 'specialties'
    | 'target_customers'
    | 'target_industries'
    | 'countries_served'
    | 'research_keywords'
    | 'excluded_keywords'
    | 'icp_buying_signals';
  label: string;
  value: string | string[];
  mode?: 'replace' | 'append';
};

export type Preview = {
  suggestions?: Partial<CompanyFields>;
  evidence?: Record<string, { url: string | null; quote: string }[]>;
  sources?: Record<string, { url?: string | null; kind?: string; basis?: string; verified_company_fact?: boolean }>;
  source_url?: string;
  warnings?: string[];
  missing_fields?: string[];
  pages_reviewed?: number;
  proposal_id?: string;
  candidates?: Candidate[];
  questions?: string[];
  answer?: string;
  proposed_updates?: ProposedUpdate[];
  limitations?: string[];
};

export type Review = {
  id: string;
  error_code?: string | null;
  attempt_history?: { attempt: number; stage: string; outcome: string; error_code: string | null; duration_ms: number }[];
  status: string;
  progress_stage: string;
  preview: Preview | null;
  can_retry: boolean;
  can_apply?: boolean;
};

export type SourceStatus = {
  id: string;
  name: string;
  state: string;
  category: string;
  coverage: string;
};

export type PaymentContract = {
  plan_code: string;
  status: string;
  provider: string;
  period_start?: number | null;
  period_end?: number | null;
  trial_start?: number | null;
  trial_end?: number | null;
  next_charge_at?: number | null;
  cancel_confirmed_at?: string | null;
  is_trial?: boolean;
  entitlement_label?: string | null;
};

export type State = {
  private_draft_revision?:number;
  private_draft?:{profile:CompanyFields;objective:string;website:string}|null;
  payment?: { required: boolean; active: boolean; contract?: PaymentContract | null };
  sources?: SourceStatus[];
  progress: Progress;
  company: CompanyProfile;
  reviews: { company?: Review; icp?: Review };
  capabilities: { company_analysis: boolean; icp_recommendations: boolean };
};

export type StepKey = 'welcome' | 'company' | 'icp' | 'research' | 'plan' | 'ready';

export type CopilotMessage = {
  id: string;
  role: 'assistant' | 'user';
  text: string;
  mode?: string;
  step: StepKey;
  updates?: ProposedUpdate[];
  appliedKeys?: string[];
  discardedKeys?: string[];
  isError?: boolean;
  canRetry?: boolean;
};

export type UnifiedJobStatus = 'idle' | 'queued' | 'running' | 'ready' | 'failed' | 'cancelled';

export interface DerivedStatus {
  code: UnifiedJobStatus;
  label: string;
  stageName: string;
  isBusy: boolean;
  isFailed: boolean;
  isSuccess: boolean;
}

export type FieldErrors = Record<string, string>;
export type SaveStatus = 'idle' | 'saving' | 'saved' | 'error';

export const ONBOARDING_STEPS = [
  { key: 'welcome' as const, stepNum: 1, title: 'Your Business', short: 'Business' },
  { key: 'company' as const, stepNum: 2, title: 'Business Profile', short: 'Profile' },
  { key: 'icp' as const, stepNum: 3, title: 'Ideal Customers', short: 'Customers' },
  { key: 'research' as const, stepNum: 4, title: 'Research Setup', short: 'Research' },
  { key: 'plan' as const, stepNum: 5, title: 'Plan & Payment', short: 'Plan' }
];

export const STEP_LABELS: Record<StepKey, string> = {
  welcome: 'Your Business',
  company: 'Business Profile',
  icp: 'Ideal Customers',
  research: 'Research Setup',
  plan: 'Plan & Payment',
  ready: 'Workspace Ready'
};

export const OBJECTIVES = [
  ['UNDERSTAND_CUSTOMER_NEEDS', 'Discover customer problems', 'Find recurring pain points and unresolved needs in public discussions.'],
  ['MONITOR_BUYING_CONTEXT', 'Find buying-intent conversations', 'Detect active evaluation, vendor comparison, and buying triggers.'],
  ['RESEARCH_MARKETS', 'Research market opportunities', 'Investigate emerging industry topics and category shifts before investing.'],
  ['MONITOR_COMPETITORS', 'Track competitors and emerging trends', 'Follow mentions, complaints, and migration discussions about alternatives.'],
  ['EXPLORE_OPPORTUNITIES', 'Explore new opportunities', 'Surface early unbranded demand and potential partnership signals.']
] as const;

const GARBAGE_REGEX = /^(\s*idk\s*|\s*xx+\s*|\s*i don'?t know\s*|\s*none\s*|\s*na\s*|\s*n\/a\s*|\s*test\s*|\s*asdf\s*|\s*nothing\s*|\s*\?+\s*|\s*no\s*)$/i;

export function isLowQualityValue(val: string): boolean {
  const trimmed = (val || '').trim();
  if (!trimmed) return false;
  return trimmed.length < 2 || GARBAGE_REGEX.test(trimmed);
}

export function normalizeWebsite(raw: string): string {
  const trimmed = raw.trim();
  if (!trimmed) return '';
  if (/^https?:\/\//i.test(trimmed)) return trimmed;
  return 'https://' + trimmed;
}

export function validateWebsiteField(raw: string, required = false): string {
  const trimmed = raw.trim();
  if (!trimmed) {
    return required ? 'Enter a valid public website address.' : '';
  }
  if (/\s/.test(trimmed)) {
    return 'Enter a valid public website address without spaces.';
  }
  const normalized = normalizeWebsite(trimmed);
  try {
    const parsed = new URL(normalized);
    if (!['http:', 'https:'].includes(parsed.protocol)) {
      return 'Enter a valid public website address.';
    }
    const host = parsed.hostname.toLowerCase();
    if (
      !host ||
      !host.includes('.') ||
      host === 'localhost' ||
      host.endsWith('.local') ||
      host.endsWith('.internal') ||
      /^\d{1,3}(\.\d{1,3}){3}$/.test(host) ||
      host.startsWith('.') ||
      host.endsWith('.')
    ) {
      return 'Enter a valid public website address.';
    }
    return '';
  } catch {
    return 'Enter a valid public website address.';
  }
}

export function validateCompanyDraft(draft: CompanyFields): FieldErrors {
  const errors: FieldErrors = {};
  const trimmedName = draft.name.trim();
  if (!trimmedName || trimmedName.length < 2 || isLowQualityValue(trimmedName)) {
    errors.name = 'Enter a company name (at least 2 characters).';
  }
  const websiteErr = validateWebsiteField(draft.website, false);
  if (websiteErr) {
    errors.website = websiteErr;
  }
  if (draft.description.trim() && isLowQualityValue(draft.description)) {
    errors.description = 'Enter a meaningful company description.';
  }
  if (!draft.products_services.length) {
    errors.offerings = 'Add at least one product or service so PlaneByte knows what you offer.';
  } else {
    draft.products_services.forEach((item, index) => {
      const n = item.name.trim();
      if (!n || n.length < 2 || isLowQualityValue(n)) {
        errors[`offering-${index}-name`] = 'Enter a clear name for this product or service.';
      }
    });
  }
  return errors;
}

const BACKEND_FIELD_MAP: Record<string, { field: string; message: string }> = {
  website: { field: 'website', message: 'Enter a valid public website address.' },
  name: { field: 'name', message: 'Enter a company name (at least 2 characters).' },
  description: { field: 'description', message: 'Enter a clear company description.' },
  industry: { field: 'industry', message: 'Enter a valid industry.' },
  positioning: { field: 'positioning', message: 'Enter a valid market positioning summary.' },
  products_services: { field: 'offerings', message: 'Check your products and services entries.' }
};

export function parseBackendErrors(rawMessage: string): { fieldErrors: FieldErrors; formError: string } {
  const fieldErrors: FieldErrors = {};
  const parts = rawMessage.split(/[;\n]/).map(s => s.trim()).filter(Boolean);
  const unmatched: string[] = [];

  for (const part of parts) {
    const match = part.match(/^(?:body\.)?(?:profile\.)?([a-z_]+)(?:\.(\d+)\.([a-z_]+))?\s*:\s*(.+)$/i);
    if (match) {
      const rootKey = match[1].toLowerCase();
      const idx = match[2];
      const sub = match[3]?.toLowerCase();
      if (rootKey === 'products_services' && idx !== undefined) {
        fieldErrors[`offering-${idx}-${sub === 'description' ? 'desc' : 'name'}`] =
          sub === 'description'
            ? 'Shorten or refine this offering description.'
            : 'Enter a clear name for this product or service.';
      } else if (BACKEND_FIELD_MAP[rootKey]) {
        fieldErrors[BACKEND_FIELD_MAP[rootKey].field] = BACKEND_FIELD_MAP[rootKey].message;
      } else {
        unmatched.push(match[4].trim());
      }
    } else if (/public http or https website|valid.*website|https?:\/\//i.test(part)) {
      fieldErrors.website = 'Enter a valid public website address.';
    } else {
      unmatched.push(part);
    }
  }

  return {
    fieldErrors,
    formError: Object.keys(fieldErrors).length > 0 ? '' : unmatched.join(' ') || 'Please review the highlighted fields and try again.'
  };
}

export const FIELD_ELEMENT_IDS: Record<string, string> = {
  website: 'onb-company-website',
  welcome_website: 'onboarding-website-url',
  name: 'onb-company-name',
  industry: 'onb-company-industry',
  description: 'onb-company-desc',
  offerings: 'onb-offerings-section',
  positioning: 'onb-positioning',
  specialties: 'onb-specialties',
  target_customers: 'onb-target-customers',
  target_industries: 'onb-target-industries',
  countries_served: 'onb-countries'
};

export function fieldElementId(fieldKey: string): string {
  if (FIELD_ELEMENT_IDS[fieldKey]) return FIELD_ELEMENT_IDS[fieldKey];
  const offMatch = fieldKey.match(/^offering-(\d+)-(name|desc)$/);
  if (offMatch) return `onb-prod-${offMatch[2]}-${offMatch[1]}`;
  return fieldKey;
}

export function scrollToFirstError(errors: FieldErrors, fallbackId?: string) {
  const firstKey = Object.keys(errors)[0];
  const targetId = firstKey ? fieldElementId(firstKey) : fallbackId;
  if (!targetId || typeof document === 'undefined') return;
  const el = document.getElementById(targetId);
  if (!el) return;
  el.scrollIntoView?.({ behavior: 'smooth', block: 'center' });
  if (typeof (el as HTMLElement).focus === 'function') {
    (el as HTMLElement).focus({ preventScroll: true });
  }
}

export function reviewFailure(code?: string | null): string {
  const messages: Record<string, string> = {
    AI_OUTPUT_TRUNCATED: 'The AI response stopped early before finishing. Your saved profile and draft are intact — click Retry.',
    SETUP_STORAGE_UNAVAILABLE: 'The analysis worker could not access required storage. Your draft is preserved — retry shortly.',
    INSUFFICIENT_COMPANY_EVIDENCE: 'Your public pages did not include enough detail to build a full profile. Review the URL or complete the form below.',
    AI_TIMEOUT: 'The AI request timed out. No draft data was lost — click Retry when ready.',
    AI_AUTH_ERROR: 'The AI provider configuration could not be verified. Manual editing remains available.',
    AI_QUOTA_EXCEEDED: 'The AI allowance is currently exhausted. Retry later or continue editing manually.',
    AI_RATE_LIMITED: 'The AI provider is temporarily rate-limiting requests. Wait a moment and click Retry.',
    ICP_UNKNOWN_SERVICE: 'The AI referenced an offering outside your saved services. Review your offerings and regenerate.',
    ICP_DUPLICATE_SEGMENTS: 'The AI returned overlapping segments. Click Retry to generate five distinct customer profiles.',
    ICP_MISSING_BUYING_SIGNALS: 'Some generated customer profiles were missing buying triggers. Click Retry to regenerate.',
    ICP_UNSUPPORTED_CRITERIA: 'The AI returned unsupported targeting criteria. Review your saved target markets and regenerate.',
    SETUP_LIMIT_EXHAUSTED: 'Your setup AI allowance was reached for this request. Click Retry to run cleanly, or continue manually — your saved profile is unchanged.',
    ICP_TOO_FEW_SEGMENTS: 'The AI returned fewer than 5 distinct segments. Click Retry to generate a full set of 5 profiles.',
    ICP_TOO_MANY_SEGMENTS: 'The AI returned too many segments. Click Retry to generate exactly 5 profiles.',
    ICP_VERBOSE_RESPONSE: 'The AI response exceeded length limits. Click Retry for a concise 5-profile set.',
    SETUP_CONTEXT_CHANGED: 'Your saved company profile changed while analysis was running. Start a fresh recommendation.',
    SETUP_ACCESS_REVOKED: 'Workspace permissions changed. An authorized owner or administrator must continue.'
  };
  return (code && messages[code]) || 'The analysis could not complete cleanly. Retry explicitly or continue editing manually — your saved profile is unchanged.';
}

export function deriveJobStatus(job?: Review | null, kind: 'company' | 'icp' = 'company'): DerivedStatus {
  if (!job) return { code: 'idle', label: 'Ready', stageName: 'Ready', isBusy: false, isFailed: false, isSuccess: false };
  if (job.status === 'FAILED') {
    return { code: 'failed', label: 'Needs retry', stageName: 'Analysis did not complete', isBusy: false, isFailed: true, isSuccess: false };
  }
  if (job.status === 'CANCELLED') {
    return { code: 'cancelled', label: 'Cancelled', stageName: 'Analysis cancelled', isBusy: false, isFailed: true, isSuccess: false };
  }
  if (job.status === 'READY') {
    return {
      code: 'ready',
      label: 'Ready',
      stageName: kind === 'icp' ? '5 ideal customer profiles ready for review' : 'Business profile ready for review',
      isBusy: false,
      isFailed: false,
      isSuccess: true
    };
  }
  if (job.status === 'QUEUED') {
    return {
      code: 'queued',
      label: 'Queued',
      stageName: kind === 'icp' ? 'Preparing customer segment discovery' : 'Connecting to your website',
      isBusy: true,
      isFailed: false,
      isSuccess: false
    };
  }
  if (job.status === 'RUNNING') {
    const stage = (job.progress_stage || '').toUpperCase();
    if (stage === 'READING_WEBSITE' || stage === 'RENDERING_WEBSITE') {
      return { code: 'running', label: 'Reading pages', stageName: 'Reading public pages', isBusy: true, isFailed: false, isSuccess: false };
    }
    if (stage === 'CHECKING_EVIDENCE' || stage === 'VALIDATING') {
      return { code: 'running', label: 'Validating', stageName: 'Validating suggested information', isBusy: true, isFailed: false, isSuccess: false };
    }
    if (kind === 'icp') {
      return { code: 'running', label: 'Generating', stageName: 'Identifying 5 distinct customer segments and buying triggers', isBusy: true, isFailed: false, isSuccess: false };
    }
    return { code: 'running', label: 'Analyzing', stageName: 'Identifying products and positioning', isBusy: true, isFailed: false, isSuccess: false };
  }
  return { code: 'idle', label: 'Ready', stageName: 'Ready', isBusy: false, isFailed: false, isSuccess: false };
}

export function formatHonestSourceState(rawState: string): { label: string; tone: 'connected' | 'configurable' | 'permission' | 'unavailable' } {
  const s = (rawState || '').toLowerCase();
  if (s.includes('connected') || s === 'active' || s === 'verified' || s === 'available') {
    return { label: s.includes('connected') ? 'Connected and checked' : 'Available to configure', tone: s.includes('connected') ? 'connected' : 'configurable' };
  }
  if (s.includes('permission') || s.includes('approval') || s.includes('oauth') || s.includes('auth')) {
    return { label: 'Permission required', tone: 'permission' };
  }
  if (s.includes('unavailable') || s.includes('disabled') || s.includes('error') || s.includes('degraded')) {
    return { label: 'Temporarily unavailable', tone: 'unavailable' };
  }
  return { label: 'Available to configure', tone: 'configurable' };
}

export const terms = (value: string) =>
  Array.from(new Set(value.split('\n').map(v => v.trim()).filter(Boolean))).slice(0, 12);

export const list = (value: unknown): string[] =>
  Array.isArray(value) ? value.filter((v): v is string => typeof v === 'string') : [];

export const describe = (value: unknown): string =>
  Array.isArray(value)
    ? value
        .map(v =>
          typeof v === 'string'
            ? v
            : (v as { name: string; description: string }).name + ' — ' + (v as { description: string }).description
        )
        .join('\n')
    : String(value || '');

export const formatUnixDate = (value?: number | null) =>
  value ? new Date(value * 1000).toLocaleDateString(undefined, { dateStyle: 'medium' }) : null;

export function extractSmartKeywordsFromCandidate(cand?: Candidate): { research: string[]; excluded: string[] } {
  if (!cand) return { research: [], excluded: [] };
  const intent = cand.draft.criteria.intent;
  const rawResearch = [
    ...list(intent.buying_signals),
    ...list(intent.pain_points),
    ...list(intent.business_needs)
  ]
    .map(v => v.trim())
    .filter(v => v.length >= 4 && v.length <= 100 && !/^evaluating market demand$/i.test(v));
  const rawExcluded = list(intent.exclusions)
    .map(v => v.trim())
    .filter(v => v.length >= 2 && v.length <= 80);
  return {
    research: Array.from(new Set(rawResearch)).slice(0, 8),
    excluded: Array.from(new Set(rawExcluded)).slice(0, 8)
  };
}
