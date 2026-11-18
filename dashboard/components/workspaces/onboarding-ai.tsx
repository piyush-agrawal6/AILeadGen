"use client";
import React, { useEffect, useRef, useState } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import Link from 'next/link';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Sparkles, Globe, ArrowRight, Check, RefreshCw, ShieldCheck,
  Plus, X, Send, Radio, Search, ChevronDown, ChevronUp,
  AlertCircle, Bot, Layers, CheckCircle2, Building2, Users2, Wand2
} from 'lucide-react';
import { request } from '@/lib/intelligence';
import { useWorkspace } from './use-workspace';
import { useProducts } from './use-products';
import { Button } from '@/components/ui/button';
import { companyDraft, companyFieldLabels, type CompanyFields, type CompanyProfile } from './company-profile-types';
import type { Candidate } from './icp-suggestions';
import './onboarding-ai.css';
import { SubscriptionPayment } from './subscription-payment';

type Progress = {
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
    [key: string]: unknown;
  };
  status: string;
  can_edit: boolean;
};

type ProposedUpdate = {
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

type Preview = {
  suggestions?: Partial<CompanyFields>;
  evidence?: Record<string, { url: string | null; quote: string }[]>;
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

type Review = {
  id: string;
  error_code?: string | null;
  attempt_history?: { attempt: number; stage: string; outcome: string; error_code: string | null; duration_ms: number }[];
  status: string;
  progress_stage: string;
  preview: Preview | null;
  can_retry: boolean;
  can_apply?: boolean;
};

type SourceStatus = {
  id: string;
  name: string;
  state: string;
  category: string;
  coverage: string;
};

type PaymentContract = {
  plan_code: string;
  status: string;
  provider: string;
  period_end?: number | null;
  trial_end?: number | null;
  next_charge_at?: number | null;
  cancel_confirmed_at?: string | null;
};

type State = {
  payment?: { required: boolean; active: boolean; contract?: PaymentContract | null };
  sources?: SourceStatus[];
  progress: Progress;
  company: CompanyProfile;
  reviews: { company?: Review; icp?: Review };
  capabilities: { company_analysis: boolean; icp_recommendations: boolean };
};

type StepKey = 'welcome' | 'company' | 'icp' | 'research' | 'plan' | 'ready';

type CopilotMessage = {
  id: string;
  role: 'assistant' | 'user';
  text: string;
  mode?: string;
  step: StepKey;
  updates?: ProposedUpdate[];
  appliedKeys?: string[];
  isError?: boolean;
  canRetry?: boolean;
};

const ONBOARDING_STEPS = [
  { key: 'welcome' as const, stepNum: 1, title: 'Your Business', short: 'Business' },
  { key: 'company' as const, stepNum: 2, title: 'Business Profile', short: 'Profile' },
  { key: 'icp' as const, stepNum: 3, title: 'Ideal Customers', short: 'Customers' },
  { key: 'research' as const, stepNum: 4, title: 'Research Setup', short: 'Research' },
  { key: 'plan' as const, stepNum: 5, title: 'Plan & Payment', short: 'Plan' },
];

const STEP_LABELS: Record<StepKey, string> = {
  welcome: 'Your Business',
  company: 'Business Profile',
  icp: 'Ideal Customers',
  research: 'Research Setup',
  plan: 'Plan & Payment',
  ready: 'Workspace Ready'
};

type UnifiedJobStatus = 'idle' | 'queued' | 'reading_website' | 'analyzing' | 'validating' | 'ready' | 'failed' | 'cancelled';

interface DerivedStatus {
  code: UnifiedJobStatus;
  label: string;
  stageName: string;
  isBusy: boolean;
  isFailed: boolean;
  isSuccess: boolean;
}

function reviewFailure(code?: string | null) {
  const messages: Record<string, string> = {
    AI_OUTPUT_TRUNCATED: 'The provider stopped before completing its structured response. Your saved profile and draft are unchanged. Please retry.',
    SETUP_STORAGE_UNAVAILABLE: 'The analysis worker could not access required storage. Your draft is preserved. Please retry shortly.',
    INSUFFICIENT_COMPANY_EVIDENCE: 'The public pages did not provide enough supported business information. Review the website URL or complete your profile manually.',
    AI_TIMEOUT: 'The AI request exceeded its time limit. No result was saved. Retry when ready.',
    AI_AUTH_ERROR: 'The AI provider rejected the server identity. Please check provider configuration.',
    AI_QUOTA_EXCEEDED: 'The AI allowance is currently exhausted. Retry after reset or continue manually.',
    AI_RATE_LIMITED: 'The AI provider is temporarily rate-limiting requests. Wait a moment and retry.',
    ICP_UNKNOWN_SERVICE: 'The AI referenced an offering outside your saved services. Review your offerings and regenerate.',
    ICP_DUPLICATE_SEGMENTS: 'The AI returned overlapping customer segments. Regenerate to get five distinct segments.',
    ICP_MISSING_BUYING_SIGNALS: 'Some generated customer profiles were missing buying triggers. Click retry to regenerate complete signals.',
    ICP_UNSUPPORTED_CRITERIA: 'The AI returned unsupported targeting criteria. Review your saved markets and regenerate.',
    SETUP_LIMIT_EXHAUSTED: 'Your setup AI allowance was reached for this request. Click Retry to run cleanly, or continue manually — your saved profile is unchanged.',
    ICP_TOO_FEW_SEGMENTS: 'The AI returned fewer than 5 distinct segments. Click Retry to generate a full set of 5 profiles.',
    ICP_TOO_MANY_SEGMENTS: 'The AI returned too many segments. Click Retry to generate exactly 5 profiles.',
    ICP_VERBOSE_RESPONSE: 'The AI response exceeded length limits. Click Retry for a concise 5-profile set.',
    SETUP_CONTEXT_CHANGED: 'Your saved company profile changed while analysis was running. Refresh and generate a fresh recommendation.',
    SETUP_ACCESS_REVOKED: 'Workspace permissions changed. An authorized owner or administrator must continue.'
  };
  return (code && messages[code]) || 'The analysis could not complete cleanly. Retry explicitly or continue editing manually — your saved profile is unchanged.';
}

function deriveJobStatus(job?: Review | null, kind: 'company' | 'icp' = 'company'): DerivedStatus {
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
      label: 'Starting',
      stageName: kind === 'icp' ? 'Preparing customer segment discovery…' : 'Connecting to your website…',
      isBusy: true,
      isFailed: false,
      isSuccess: false
    };
  }
  if (job.status === 'RUNNING') {
    const stage = (job.progress_stage || '').toUpperCase();
    if (stage === 'READING_WEBSITE' || stage === 'RENDERING_WEBSITE') {
      return { code: 'reading_website', label: 'Reading site', stageName: 'Reviewing public pages & offerings…', isBusy: true, isFailed: false, isSuccess: false };
    }
    if (stage === 'CHECKING_EVIDENCE' || stage === 'VALIDATING') {
      return { code: 'validating', label: 'Validating', stageName: 'Validating extracted insights…', isBusy: true, isFailed: false, isSuccess: false };
    }
    if (kind === 'icp') {
      return { code: 'analyzing', label: 'Generating ICPs', stageName: 'Identifying 5 distinct customer segments & buying triggers…', isBusy: true, isFailed: false, isSuccess: false };
    }
    return { code: 'analyzing', label: 'Analyzing', stageName: 'Identifying products, positioning & target markets…', isBusy: true, isFailed: false, isSuccess: false };
  }
  return { code: 'idle', label: 'Ready', stageName: 'Ready', isBusy: false, isFailed: false, isSuccess: false };
}

const OBJECTIVES = [
  ['UNDERSTAND_CUSTOMER_NEEDS', 'Discover customer problems', 'Find recurring pain points and unresolved needs in public discussions.'],
  ['MONITOR_BUYING_CONTEXT', 'Find buying-intent conversations', 'Detect active evaluation, vendor comparison, and buying triggers.'],
  ['MONITOR_COMPETITORS', 'Monitor competitors', 'Track mentions, complaints, and migration discussions about alternatives.'],
  ['RESEARCH_MARKETS', 'Research a market', 'Investigate emerging industry topics and category shifts before investing.'],
  ['EXPLORE_OPPORTUNITIES', 'Explore opportunities', 'Surface early unbranded demand and potential partnership signals.']
] as const;

const SECTION_FIELDS: Record<'overview' | 'offerings' | 'positioning' | 'markets', (keyof CompanyFields)[]> = {
  overview: ['name', 'website', 'industry', 'description'],
  offerings: ['products_services'],
  positioning: ['positioning', 'specialties'],
  markets: ['target_customers', 'target_industries', 'countries_served']
};

const GARBAGE_REGEX = /^(\s*idk\s*|\s*xx+\s*|\s*i don'?t know\s*|\s*none\s*|\s*na\s*|\s*n\/a\s*|\s*test\s*|\s*asdf\s*|\s*nothing\s*|\s*\?+\s*|\s*no\s*)$/i;

function isLowQualityValue(val: string): boolean {
  const trimmed = (val || '').trim();
  if (!trimmed) return false;
  return trimmed.length < 3 || GARBAGE_REGEX.test(trimmed);
}

const terms = (value: string) =>
  Array.from(new Set(value.split('\n').map(v => v.trim()).filter(Boolean))).slice(0, 12);

const list = (value: unknown): string[] =>
  Array.isArray(value) ? value.filter((v): v is string => typeof v === 'string') : [];

const describe = (value: unknown): string =>
  Array.isArray(value)
    ? value
        .map(v =>
          typeof v === 'string'
            ? v
            : (v as { name: string; description: string }).name + ' — ' + (v as { description: string }).description
        )
        .join('\n')
    : String(value || '');

const formatUnixDate = (value?: number | null) =>
  value ? new Date(value * 1000).toLocaleDateString(undefined, { dateStyle: 'medium' }) : null;

function extractSmartKeywordsFromCandidate(cand?: Candidate): { research: string[]; excluded: string[] } {
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

async function api<T>(path: string, body?: unknown, method = 'POST') {
  return request<T>('/organization/onboarding' + path, {
    method,
    body: body === undefined ? undefined : JSON.stringify(body)
  });
}

export function AIOnboarding() {
  const workspace = useWorkspace();
  const org = workspace.data?.active_organization_id;
  const query = useQuery({
    queryKey: ['onboarding-ai', org],
    queryFn: ({ signal }) => request<State>('/organization/onboarding/assistant-context', { signal }),
    enabled: !!org,
    retry: false,
    refetchOnWindowFocus: false
  });

  if (query.error) {
    return (
      <section className="ai-setup-state" role="alert">
        <AlertCircle size={28} className="text-destructive" />
        <h1 className="text-lg font-semibold">We couldn’t load your saved setup</h1>
        <p className="text-sm text-muted-foreground">Your business data has not changed. Check your connection or retry.</p>
        <Button onClick={() => void query.refetch()}>Retry setup</Button>
      </section>
    );
  }
  if (!query.data) {
    return (
      <div className="ai-setup-loading" role="status">
        <Sparkles className="animate-spin text-primary" size={24} />
        <p className="text-sm text-muted-foreground">Loading your saved workspace setup…</p>
      </div>
    );
  }
  return <SetupWorkspace key={org} initial={query.data} onRefresh={() => query.refetch()} />;
}

function SetupWorkspace({ initial, onRefresh }: { initial: State; onRefresh: () => Promise<unknown> }) {
  const client = useQueryClient();
  const workspace = useWorkspace();
  const products = useProducts();
  const [state, setState] = useState(initial);

  const initialView = (): StepKey => {
    if (initial.progress.status === 'COMPLETED') {
      return initial.payment?.required && !initial.payment.active ? 'plan' : 'ready';
    }
    const s = initial.progress.current_step;
    if (s === 'REVIEW') return 'research';
    if (['ICP', 'PREFERENCES'].includes(s)) return 'icp';
    if (['COMPANY', 'SERVICES'].includes(s) || initial.progress.preferences.company_review_id) return 'company';
    return 'welcome';
  };

  const [view, setView] = useState<StepKey>(initialView);
  const [draft, setDraft] = useState<CompanyFields>(() => companyDraft(initial.company));
  const [objective, setObjective] = useState(
    initial.progress.objectives.find(v => OBJECTIVES.some(([id]) => id === v)) || 'UNDERSTAND_CUSTOMER_NEEDS'
  );
  const [website, setWebsite] = useState(initial.company.website);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [selectedFields, setSelectedFields] = useState<string[]>([]);
  const [rejectedSections, setRejectedSections] = useState<string[]>([]);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [primary, setPrimary] = useState(0);
  const [expandedICP, setExpandedICP] = useState<number | null>(null);
  const [defaultICP, setDefaultICP] = useState(initial.progress.default_icp_id || '');
  const [keywords, setKeywords] = useState(initial.progress.preferences.research_keywords.join('\n'));
  const [excluded, setExcluded] = useState(initial.progress.preferences.excluded_keywords.join('\n'));
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);

  // Assistant Chat State — single clean welcome, grouped by step
  const [messages, setMessages] = useState<CopilotMessage[]>([
    {
      id: 'welcome-0',
      role: 'assistant',
      step: initialView(),
      text: "I'm your PlaneByte Setup Copilot. Ask me to refine your business description, sharpen positioning, compare ICPs, or generate high-intent research keywords and exclusions."
    }
  ]);
  const [chatPending, setChatPending] = useState(false);

  const requestIds = useRef<Record<string, string>>({});
  const deadline = useRef(Date.now() + 120000);
  const adviceDeadline = useRef(0);
  const adviceMsgId = useRef('');
  const adviceParent = useRef<string | null>(null);
  const [adviceKey, setAdviceKey] = useState('');
  const progress = state.progress;

  function id(kind: string) {
    return (requestIds.current[kind] ??= crypto.randomUUID());
  }

  const companyId = progress.preferences.company_review_id;
  const icpId = progress.preferences.icp_review_id;

  const companyReview = useQuery({
    queryKey: ['onboarding-review', companyId],
    queryFn: ({ signal }) => request<Review>('/organization/onboarding/reviews/' + companyId, { signal }),
    enabled: !!companyId,
    retry: false,
    initialData: initial.reviews.company?.id === companyId ? initial.reviews.company : undefined,
    refetchInterval: q =>
      Date.now() < deadline.current && ['QUEUED', 'RUNNING'].includes(q.state.data?.status || '') ? 2500 : false
  });

  const icpReview = useQuery({
    queryKey: ['onboarding-review', icpId],
    queryFn: ({ signal }) => request<Review>('/organization/onboarding/reviews/' + icpId, { signal }),
    enabled: !!icpId,
    retry: false,
    initialData: initial.reviews.icp?.id === icpId ? initial.reviews.icp : undefined,
    refetchInterval: q =>
      Date.now() < deadline.current && ['QUEUED', 'RUNNING'].includes(q.state.data?.status || '') ? 2500 : false
  });

  const adviceReview = useQuery({
    queryKey: ['onboarding-advice', adviceKey],
    queryFn: ({ signal }) => request<Review>('/organization/onboarding/reviews/' + adviceKey, { signal }),
    enabled: !!adviceKey,
    retry: false,
    refetchInterval: q =>
      Date.now() < adviceDeadline.current && ['QUEUED', 'RUNNING'].includes(q.state.data?.status || '') ? 2000 : false
  });

  const hydratedCompany = useRef('');
  const hydratedICPs = useRef('');
  const adviceFingerprint = useRef('');

  // Resolve Copilot advice job cleanly
  useEffect(() => {
    const review = adviceReview.data;
    if (!review || review.id !== adviceKey || !['READY', 'FAILED', 'CANCELLED'].includes(review.status)) return;
    const fingerprint = review.id + ':' + review.status + ':' + (review.attempt_history?.length || 0);
    if (adviceFingerprint.current === fingerprint) return;
    adviceFingerprint.current = fingerprint;

    if (review.status === 'READY') {
      adviceParent.current = review.id;
    }

    const answerText =
      review.status === 'READY'
        ? review.preview?.answer || 'No guidance was returned. Your saved context is unchanged.'
        : review.status === 'FAILED'
          ? reviewFailure(review.error_code)
          : 'Guidance cancelled. Your saved context is unchanged.';

    const updates = review.status === 'READY' ? review.preview?.proposed_updates || [] : [];

    setMessages(prev =>
      prev.map(msg =>
        msg.id === adviceMsgId.current
          ? {
              ...msg,
              text: answerText,
              mode: review.status === 'READY' ? 'AI suggestion' : 'Guidance status',
              updates,
              isError: review.status === 'FAILED',
              canRetry: review.status === 'FAILED' && review.can_retry
            }
          : msg
      )
    );
    setChatPending(false);
  }, [adviceReview.data, adviceKey]);

  useEffect(() => {
    if (!adviceReview.error) return;
    setMessages(prev =>
      prev.map(msg =>
        msg.id === adviceMsgId.current
          ? { ...msg, text: 'Could not refresh guidance status. Please retry.', isError: true, canRetry: true }
          : msg
      )
    );
    setChatPending(false);
  }, [adviceReview.error]);

  // Fixed bounded timeout guard: only active for the CURRENT adviceKey and valid future deadline
  useEffect(() => {
    if (!adviceKey || !chatPending) return;
    const remaining = adviceDeadline.current - Date.now();
    if (remaining <= 0) return;
    const targetMsgId = adviceMsgId.current;
    const timer = setTimeout(() => {
      setChatPending(false);
      setMessages(prev =>
        prev.map(msg =>
          msg.id === targetMsgId
            ? {
                ...msg,
                text: 'Guidance is taking longer than expected. Click refresh or retry to check the result.',
                isError: true,
                canRetry: true
              }
            : msg
        )
      );
    }, remaining);
    return () => clearTimeout(timer);
  }, [adviceKey, chatPending]);

  const profiles = useQuery({
    queryKey: ['setup-icps', workspace.data?.active_organization_id],
    queryFn: () => request<{ items: { id: string; name: string; status: string }[] }>('/organization/icps?status=ACTIVE'),
    enabled: view === 'icp' || view === 'research' || view === 'plan',
    retry: false
  });

  const dirty = JSON.stringify(draft) !== JSON.stringify(companyDraft(state.company));
  useEffect(() => {
    if (!dirty) return;
    const warn = (e: BeforeUnloadEvent) => e.preventDefault();
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [dirty]);

  // Auto-populate draft from READY website analysis without overwriting user-saved values
  useEffect(() => {
    if (companyReview.data?.status === 'READY' && companyReview.data?.preview?.suggestions) {
      const fingerprint = companyReview.data.id + JSON.stringify(companyReview.data.preview.suggestions);
      if (hydratedCompany.current === fingerprint) return;
      hydratedCompany.current = fingerprint;
      const s = companyReview.data.preview.suggestions;
      setDraft(v => ({
        ...v,
        name: !v.name || (!initial.company.version && v.name === initial.company.name) ? s.name || v.name : v.name,
        website: v.website || s.website || (website.trim().startsWith('http') ? website.trim() : website.trim() ? 'https://' + website.trim() : ''),
        description: v.description || s.description || '',
        industry: v.industry || s.industry || '',
        positioning: v.positioning || s.positioning || '',
        specialties: v.specialties?.length ? v.specialties : s.specialties || [],
        target_customers: v.target_customers?.length ? v.target_customers : s.target_customers || [],
        target_industries: v.target_industries?.length ? v.target_industries : s.target_industries || [],
        countries_served: v.countries_served?.length ? v.countries_served : s.countries_served || [],
        products_services: v.products_services?.length ? v.products_services : s.products_services || []
      }));
      setSelectedFields(Object.keys(s));
      setNotice('Website research complete. Review your extracted business profile below.');
    }
  }, [companyReview.data?.status, companyReview.data?.id, companyReview.data?.preview?.suggestions]);

  // Hydrate 5 ICP candidates and smart research/exclusion defaults when ready
  useEffect(() => {
    if (icpReview.data?.preview?.candidates && icpReview.data.preview.candidates.length > 0) {
      const fingerprint = icpReview.data.id + ':' + icpReview.data.preview.candidates.length;
      if (hydratedICPs.current === fingerprint) return;
      hydratedICPs.current = fingerprint;
      const listCands = icpReview.data.preview.candidates;
      setCandidates(listCands);
      setSelected(listCands.map((_, i) => i));
      setPrimary(0);

      const smart = extractSmartKeywordsFromCandidate(listCands[0]);
      if (!keywords.trim() && smart.research.length) {
        setKeywords(smart.research.join('\n'));
      }
      if (!excluded.trim() && smart.excluded.length) {
        setExcluded(smart.excluded.join('\n'));
      }
    }
  }, [icpReview.data?.id, icpReview.data?.preview]);

  function progressSaved(next: Progress) {
    setState(v => ({ ...v, progress: next }));
    void client.invalidateQueries({ queryKey: ['company-onboarding'] });
    void client.invalidateQueries({ queryKey: ['onboarding-progress'] });
  }

  async function perform(work: () => Promise<void>) {
    if (pending) return;
    setPending(true);
    setError('');
    setNotice('');
    try {
      await work();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setPending(false);
    }
  }

  async function analyze() {
    if (!website.trim()) {
      setError('Please enter a public HTTPS company website.');
      return;
    }
    const normWebsite = website.trim().startsWith('http') ? website.trim() : 'https://' + website.trim();
    setDraft(v => ({ ...v, website: normWebsite }));
    await perform(async () => {
      const result = await api<{ review: Review; progress: Progress }>('/analyze', {
        revision: progress.revision,
        website: normWebsite,
        objective,
        request_id: id('website:' + normWebsite)
      });
      progressSaved(result.progress);
      client.setQueryData(['onboarding-review', result.review.id], result.review);
      deadline.current = Date.now() + 120000;
      setView('company');
    });
  }

  function applySection(fields: (keyof CompanyFields)[]) {
    const values = companyReview.data?.preview?.suggestions || {};
    const patch = Object.fromEntries(fields.filter(f => f in values).map(f => [f, values[f]]));
    setDraft(v => ({ ...v, ...patch }));
    setSelectedFields(v => [...new Set([...v, ...Object.keys(patch)])]);
    setNotice('AI suggestions applied to your draft. Review and save when ready.');
  }

  function rejectSection(sectionKey: string, fields: (keyof CompanyFields)[]) {
    const suggested = companyReview.data?.preview?.suggestions || {};
    const original = companyDraft(state.company);
    setRejectedSections(v => [...new Set([...v, sectionKey])]);
    setDraft(v => ({
      ...v,
      ...Object.fromEntries(
        fields
          .filter(f => selectedFields.includes(f) && JSON.stringify(v[f]) === JSON.stringify(suggested[f]))
          .map(f => [f, original[f]])
      )
    }));
    setSelectedFields(v => v.filter(f => !fields.includes(f as keyof CompanyFields)));
    setNotice('Section suggestions reverted to your saved values.');
  }

  // Never show stale "Generating..." notice once an authoritative job reaches a terminal state
  useEffect(() => {
    const active = view === 'icp' ? icpReview.data : view === 'company' ? companyReview.data : null;
    if (!active) return;
    if (active.status === 'FAILED' || active.status === 'CANCELLED') {
      setNotice('');
    } else if (active.status === 'READY' && /generating|researching/i.test(notice)) {
      setNotice('');
    }
  }, [view, icpReview.data?.status, companyReview.data?.status, notice]);

  async function prepareICP(revision: number, version = state.company.version, fresh = false) {
    setError('');
    const result = await api<{ review: Review; progress: Progress }>('/recommendations', {
      revision,
      request_id: fresh ? crypto.randomUUID() : id('icps:' + version)
    });
    progressSaved(result.progress);
    client.setQueryData(['onboarding-review', result.review.id], result.review);
    deadline.current = Date.now() + 120000;
    if (result.review.status === 'QUEUED' || result.review.status === 'RUNNING') {
      setNotice('Business profile saved. Generating 5 tailored ideal customer profiles…');
    } else {
      setNotice('');
    }
    setView('icp');
  }

  async function saveCompany() {
    if (!draft.name.trim() || draft.name.trim().length < 2 || isLowQualityValue(draft.name)) {
      setError('Please provide a valid company name (at least 2 characters).');
      return;
    }
    if (draft.description && isLowQualityValue(draft.description)) {
      setError('Please provide a meaningful business description.');
      return;
    }
    if (!draft.products_services.length || draft.products_services.some(v => !v.name.trim() || isLowQualityValue(v.name))) {
      setError('Please confirm at least one named product or service.');
      return;
    }

    await perform(async () => {
      const result = await api<{ company: CompanyProfile; progress: Progress }>(
        '/company',
        {
          revision: progress.revision,
          objective,
          profile: {
            ...draft,
            ...Object.fromEntries(
              (['countries_served', 'target_customers', 'target_industries', 'specialties'] as const).map(key => [
                key,
                draft[key].map(v => v.trim()).filter(Boolean)
              ])
            ),
            version: state.company.version,
            ...(selectedFields.length && companyId ? { review_id: companyId, reviewed_fields: selectedFields } : {})
          }
        },
        'PUT'
      );

      setState(v => ({ ...v, company: result.company, progress: result.progress }));
      setDraft(companyDraft(result.company));
      client.setQueryData(['organization-profile'], result.company);
      void client.invalidateQueries({ queryKey: ['intelligence-graph'] });
      setView('icp');
      setNotice('Company profile saved.');

      if (result.progress.preferences.setup_mode === 'AI' && state.capabilities.icp_recommendations) {
        await prepareICP(result.progress.revision, result.company.version);
      }
    });
  }

  function candidateField(index: number, group: 'company' | 'contact' | 'intent', field: string, value: string) {
    setCandidates(rows =>
      rows.map((row, i) =>
        i === index
          ? {
              ...row,
              draft: {
                ...row.draft,
                criteria: {
                  ...row.draft.criteria,
                  [group]: { ...row.draft.criteria[group], [field]: terms(value) }
                }
              }
            }
          : row
      )
    );
  }

  async function acceptICPs() {
    if (!selected.length) {
      setError('Please select at least one customer profile to continue.');
      return;
    }
    if (!selected.includes(primary)) {
      setError('Please mark one of your selected profiles as the Primary ICP.');
      return;
    }

    // Ensure smart research & exclusion defaults are populated from primary ICP if still blank
    const smart = extractSmartKeywordsFromCandidate(candidates[primary]);
    const finalResearch = keywords.trim() ? terms(keywords) : smart.research;
    const finalExcluded = excluded.trim() ? terms(excluded) : smart.excluded;
    if (!keywords.trim() && finalResearch.length) setKeywords(finalResearch.join('\n'));
    if (!excluded.trim() && finalExcluded.length) setExcluded(finalExcluded.join('\n'));

    await perform(async () => {
      const proposal = icpReview.data?.preview?.proposal_id;
      if (!proposal) return;
      const result = await api<{ progress: Progress; profiles: { id: string }[] }>('/accept-profiles', {
        revision: progress.revision,
        proposal_id: proposal,
        candidates: selected.map(i => ({
          candidate_index: i,
          name: candidates[i].draft.name,
          description: candidates[i].draft.description,
          criteria: candidates[i].draft.criteria
        })),
        primary_index: primary,
        request_id: id('accept:' + proposal),
        research_keywords: finalResearch,
        excluded_keywords: finalExcluded
      });
      progressSaved(result.progress);
      setDefaultICP(result.progress.default_icp_id || '');
      await client.invalidateQueries({ queryKey: ['setup-icps'] });
      void client.invalidateQueries({ queryKey: ['intent-radar'] });
      setView('research');
      setNotice('Customer profiles saved. Review your research setup below.');
    });
  }

  async function finish(primaryId?: string) {
    const targetId = primaryId || defaultICP;
    if (!targetId) {
      setError('A primary customer profile is required to continue.');
      return;
    }
    await perform(async () => {
      await api('/finish', {
        revision: progress.revision,
        primary_icp_id: targetId,
        research_keywords: terms(keywords),
        excluded_keywords: terms(excluded)
      });
      setState(v => ({ ...v, progress: { ...v.progress, status: 'COMPLETED' } }));
      if (state.payment?.required) {
        setNotice(
          state.payment.active
            ? 'Research setup saved. Your existing verified Creem access is recognized below — no additional charge is needed.'
            : 'Research setup saved. Complete your trial or plan activation below to enter Intent Radar.'
        );
        setView('plan');
      } else {
        setNotice('Workspace setup saved.');
        setView('ready');
      }
      await Promise.all([
        client.invalidateQueries({ queryKey: ['account-workspaces'] }),
        client.invalidateQueries({ queryKey: ['plane-products'] }),
        client.invalidateQueries({ queryKey: ['intent-radar'] }),
        client.invalidateQueries({ queryKey: ['intelligence-graph'] })
      ]);
    });
  }

  async function saveExit() {
    await perform(async () => {
      const { status, can_edit, ...values } = progress;
      void status;
      void can_edit;
      const result = await api<Progress>(
        '',
        {
          ...values,
          objectives: [objective],
          preferences: {
            ...values.preferences,
            research_keywords: terms(keywords),
            excluded_keywords: terms(excluded)
          }
        },
        'PUT'
      );
      progressSaved(result);
      setNotice('Progress saved safely. You can return anytime.');
      await onRefresh();
    });
  }

  async function skipOnboarding() {
    await perform(async () => {
      const result = await api<Progress>('/skip', {}, 'POST');
      progressSaved(result);
      await Promise.all([
        client.invalidateQueries({ queryKey: ['account-workspaces'] }),
        client.invalidateQueries({ queryKey: ['plane-products'] }),
        client.invalidateQueries({ queryKey: ['intent-radar'] })
      ]);
      window.location.assign('/intent-radar');
    });
  }

  async function manualMode() {
    await perform(async () => {
      const { status, can_edit, ...values } = progress;
      void status;
      void can_edit;
      const next = await api<Progress>(
        '',
        {
          ...values,
          current_step: 'COMPANY',
          preferences: { ...values.preferences, setup_mode: 'MANUAL' }
        },
        'PUT'
      );
      progressSaved(next);
      setView('company');
    });
  }

  function selectCandidate(index: number, checked: boolean) {
    const next = checked ? [...selected, index] : selected.filter(v => v !== index);
    setSelected(next);
    if (!next.includes(primary) && next.length > 0) setPrimary(next[0]);
  }

  // Apply an AI Copilot proposed update directly into the onboarding form (user-triggered, never silent)
  function applyProposedUpdate(msgId: string, updateIndex: number, upd: ProposedUpdate) {
    const asList = Array.isArray(upd.value) ? upd.value.map(v => v.trim()).filter(Boolean) : terms(String(upd.value));
    const asText = Array.isArray(upd.value) ? upd.value.join('\n') : String(upd.value).trim();

    if (upd.target === 'description' || upd.target === 'positioning' || upd.target === 'industry') {
      setDraft(v => ({ ...v, [upd.target]: asText }));
      setNotice(`Applied AI suggestion to ${companyFieldLabels[upd.target]}. Remember to approve & save.`);
    } else if (
      upd.target === 'specialties' ||
      upd.target === 'target_customers' ||
      upd.target === 'target_industries' ||
      upd.target === 'countries_served'
    ) {
      const listKey = upd.target;
      setDraft(v => ({
        ...v,
        [listKey]: upd.mode === 'append' ? Array.from(new Set([...v[listKey].filter(Boolean), ...asList])) : asList
      }));
      setNotice(`Updated ${companyFieldLabels[listKey]} from Copilot.`);
    } else if (upd.target === 'research_keywords') {
      setKeywords(prev =>
        (upd.mode === 'append' ? Array.from(new Set([...terms(prev), ...asList])) : asList).slice(0, 12).join('\n')
      );
      setNotice('Updated high-intent research phrases from Copilot.');
    } else if (upd.target === 'excluded_keywords') {
      setExcluded(prev =>
        (upd.mode === 'append' ? Array.from(new Set([...terms(prev), ...asList])) : asList).slice(0, 12).join('\n')
      );
      setNotice('Updated negative exclusion terms from Copilot.');
    } else if (upd.target === 'icp_buying_signals' && candidates[primary]) {
      setCandidates(rows =>
        rows.map((row, idx) => {
          if (idx !== primary) return row;
          const existing = list(row.draft.criteria.intent.buying_signals);
          const merged = upd.mode === 'append' ? Array.from(new Set([...existing, ...asList])) : asList;
          return {
            ...row,
            draft: {
              ...row.draft,
              criteria: {
                ...row.draft.criteria,
                intent: { ...row.draft.criteria.intent, buying_signals: merged.slice(0, 10) }
              }
            }
          };
        })
      );
      setNotice(`Updated buying triggers for "${candidates[primary].draft.name}".`);
    }

    const key = `${msgId}:${updateIndex}`;
    setMessages(prev =>
      prev.map(m => (m.id === msgId ? { ...m, appliedKeys: [...(m.appliedKeys || []), key] } : m))
    );
  }

  // Ask AI Copilot Question — sends full step/draft/ICP/keyword context & fixes pending timeout race
  async function askAssistant(promptText: string) {
    const q = promptText.trim();
    if (!q || chatPending) return;

    const userMsgId = crypto.randomUUID();
    const pendingMsgId = crypto.randomUUID();
    adviceMsgId.current = pendingMsgId;
    adviceFingerprint.current = '';
    adviceDeadline.current = Date.now() + 120000;
    setChatPending(true);

    setMessages(prev => [
      ...prev,
      { id: userMsgId, role: 'user', step: view, text: q },
      { id: pendingMsgId, role: 'assistant', step: view, text: 'Reviewing your workspace context…' }
    ]);

    try {
      const res = await api<{ answer?: string; mode: string; job: Review | null }>('/assistant', {
        prompt: q,
        draft,
        parent_review_id: adviceParent.current || undefined,
        current_step: view,
        objective,
        research_keywords: terms(keywords),
        excluded_keywords: terms(excluded),
        selected_icp_names: selected.map(i => candidates[i]?.draft?.name).filter((v): v is string => !!v),
        request_id: crypto.randomUUID()
      });

      if (res.job) {
        adviceDeadline.current = Date.now() + 120000;
        client.setQueryData(['onboarding-advice', res.job.id], res.job);
        setAdviceKey(res.job.id);
      } else {
        setMessages(prev =>
          prev.map(m =>
            m.id === pendingMsgId
              ? { ...m, text: res.answer || 'No guidance was returned. Your saved context is unchanged.', mode: res.mode }
              : m
          )
        );
        setChatPending(false);
      }
    } catch (err) {
      setMessages(prev =>
        prev.map(m => (m.id === pendingMsgId ? { ...m, text: (err as Error).message, isError: true } : m))
      );
      setChatPending(false);
    }
  }

  async function controlReview(kind: 'company' | 'icp', action: 'CANCEL' | 'RETRY') {
    const review = kind === 'icp' ? icpReview : companyReview;
    if (!review.data) return;
    await request('/organization/website-reviews/' + review.data.id + '/control', {
      method: 'POST',
      body: JSON.stringify({ action })
    });
    deadline.current = Date.now() + 120000;
    await review.refetch();
  }

  async function retryAdvice() {
    if (!adviceKey || !adviceReview.data?.can_retry) return;
    try {
      adviceFingerprint.current = '';
      adviceDeadline.current = Date.now() + 120000;
      setChatPending(true);
      await request('/organization/website-reviews/' + adviceKey + '/control', {
        method: 'POST',
        body: JSON.stringify({ action: 'RETRY' })
      });
      await adviceReview.refetch();
    } catch (err) {
      setChatPending(false);
      setError((err as Error).message);
    }
  }

  const currentStepNum = ONBOARDING_STEPS.find(s => s.key === view)?.stepNum || 1;
  const companySuggestions = companyReview.data?.preview?.suggestions || {};
  const companyReady = companyReview.data?.status === 'READY';
  const hasSectionSuggestions = (key: keyof typeof SECTION_FIELDS) =>
    companyReady && !rejectedSections.includes(key) && SECTION_FIELDS[key].some(f => f in companySuggestions);

  const liveSources: SourceStatus[] = state.sources?.length
    ? state.sources
    : [
        { id: 'hacker_news', name: 'Hacker News', state: 'Available', category: 'Public discussion', coverage: 'Official public API — recent Ask, Show & Top discussions.' },
        { id: 'stack_exchange', name: 'Stack Exchange', state: 'Requires approval', category: 'Public discussion', coverage: 'Configured professional Q&A sites when enabled.' },
        { id: 'discourse', name: 'Approved Discourse', state: 'Not configured', category: 'Public discussion', coverage: 'Publisher-approved public forum feeds configured in Settings.' },
        { id: 'rss', name: 'RSS / Atom', state: 'Not configured', category: 'Publication', coverage: 'Approved publication feeds configured in Settings.' }
      ];

  const hasVerifiedAccess = !!(products.data?.intent_radar?.enabled || (state.payment?.required && state.payment?.active));

  return (
    <div className="ai-onboarding-shell">
      {/* Top Hero Band — Reuses actual PlaneByte Dashboard Gradient & Square-Mesh Background */}
      {view !== 'ready' && (
        <div className="pb-onb-hero">
          <div className="pb-onb-hero-inner">
            <header className="ai-onboarding-topbar">
              <div>
                <div className="ai-brand-badge">
                  <Sparkles size={13} />
                  <span>PlaneByte Setup</span>
                </div>
                <h1>
                  {view === 'welcome' && 'Set up your buyer-intent workspace'}
                  {view === 'company' && 'Review your business profile'}
                  {view === 'icp' && 'Choose your ideal customers'}
                  {view === 'research' && 'Fine-tune your research signals'}
                  {view === 'plan' && 'Activate your Intent Radar plan'}
                </h1>
                <p>
                  {view === 'welcome' && 'Share your website and objective — PlaneByte researches your business automatically.'}
                  {view === 'company' && 'Verify what AI discovered about your company, offerings, and target market.'}
                  {view === 'icp' && 'Review 5 AI-tailored buyer segments with concrete buying triggers and choose your primary ICP.'}
                  {view === 'research' && 'Confirm high-intent phrases and negative exclusions that guide live signal discovery.'}
                  {view === 'plan' && 'Start with a 3-day free trial ($0 today) or subscribe directly to enter Intent Radar.'}
                </p>
              </div>

              {progress.can_edit && (
                <div className="flex items-center gap-2 flex-shrink-0">
                  <Button variant="ghost" size="sm" disabled={pending} onClick={() => void skipOnboarding()}>
                    Skip for now
                  </Button>
                  <Button variant="outline" size="sm" disabled={pending} onClick={() => void saveExit()}>
                    Save &amp; Exit
                  </Button>
                </div>
              )}
            </header>

            {/* 5-Step Horizontal Progress Rail */}
            <nav aria-label="Onboarding Progress" className="ai-onboarding-rail-container">
              <ol className="ai-onboarding-rail">
                {ONBOARDING_STEPS.map(s => {
                  const isCompleted = currentStepNum > s.stepNum;
                  const isCurrent = view === s.key;
                  return (
                    <li
                      key={s.key}
                      className={`ai-rail-step ${isCurrent ? 'is-active' : ''} ${isCompleted ? 'is-done' : ''}`}
                      aria-current={isCurrent ? 'step' : undefined}
                    >
                      <button
                        type="button"
                        className="ai-rail-btn"
                        disabled={!isCompleted && !isCurrent}
                        onClick={() => {
                          if (isCompleted) setView(s.key);
                        }}
                      >
                        <span className="ai-rail-indicator">
                          {isCompleted ? <Check size={12} strokeWidth={3} /> : s.stepNum}
                        </span>
                        <span className="ai-rail-label">
                          <span className="ai-rail-num">Step {s.stepNum}</span>
                          <span className="ai-rail-text">{s.title}</span>
                        </span>
                      </button>
                      {s.stepNum < 5 && <div className="ai-rail-divider" aria-hidden="true" />}
                    </li>
                  );
                })}
              </ol>
            </nav>
          </div>
        </div>
      )}

      {/* Read-Only Guard for Invited Non-Admin Members */}
      {!progress.can_edit ? (
        <section className="ai-card max-w-2xl mx-auto my-12 text-center p-8 space-y-3">
          <Building2 size={32} className="mx-auto text-muted-foreground" />
          <h2 className="text-xl font-semibold">
            {progress.status === 'COMPLETED' ? 'Your company setup is complete' : 'Your workspace owner is preparing this company'}
          </h2>
          <p className="text-sm text-muted-foreground">
            You can review the company details in Settings. Joining a team never overwrites or restarts setup.
          </p>
          <Link href="/settings" className="text-primary underline text-sm inline-flex items-center gap-1 font-medium">
            Open workspace settings →
          </Link>
        </section>
      ) : view === 'ready' ? (
        /* FINAL SUCCESS SCREEN (Redesigned Premium Activation Experience) */
        <section className="pb-ready-canvas max-w-4xl mx-auto my-8 animate-fade-in">
          <div className="pb-ready-hero">
            <div className="pb-ready-emblem" aria-hidden="true">
              <CheckCircle2 size={32} />
            </div>
            <div className="ai-brand-badge mb-3">
              <Sparkles size={12} />
              <span>{hasVerifiedAccess ? 'Workspace Activated' : 'Setup Saved'}</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
              {hasVerifiedAccess
                ? "You're all set. Let's discover your next opportunity."
                : 'Your reviewed context is saved'}
            </h1>
            <p className="text-sm text-muted-foreground max-w-xl mx-auto mt-2.5 leading-relaxed">
              {hasVerifiedAccess
                ? `Your ${state.company.name || 'workspace'} intelligence profile, ideal customer segments, and research signals are ready for live buyer-intent discovery.`
                : 'Your company profile, approved ICPs, and research defaults are safely stored. Product access activates once your workspace plan is confirmed.'}
            </p>
          </div>

          <div className="p-6 sm:p-8 space-y-6">
            {/* Compact Confirmation Summary */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5 text-xs">
              <div className="rounded-xl border border-border/80 bg-muted/25 p-3.5">
                <span className="text-muted-foreground flex items-center gap-1.5">
                  <Check size={13} className="text-primary" /> Business Profile
                </span>
                <strong className="block text-sm text-foreground mt-1 truncate">
                  {state.company.name || 'Saved'}
                </strong>
              </div>

              <div className="rounded-xl border border-border/80 bg-muted/25 p-3.5">
                <span className="text-muted-foreground flex items-center gap-1.5">
                  <Check size={13} className="text-primary" /> Ideal Customers
                </span>
                <strong className="block text-sm text-foreground mt-1 truncate">
                  {candidates[primary]?.draft?.name || profiles.data?.items.find(p => p.id === defaultICP)?.name || 'Configured'}
                </strong>
              </div>

              <div className="rounded-xl border border-border/80 bg-muted/25 p-3.5">
                <span className="text-muted-foreground flex items-center gap-1.5">
                  <Check size={13} className="text-primary" /> Research Signals
                </span>
                <strong className="block text-sm text-foreground mt-1">
                  {terms(keywords).length || state.progress.preferences.research_keywords.length || 0} intent phrases ready
                </strong>
              </div>

              <div className="rounded-xl border border-border/80 bg-muted/25 p-3.5">
                <span className="text-muted-foreground flex items-center gap-1.5">
                  <ShieldCheck size={13} className="text-primary" /> Plan Status
                </span>
                <strong className="block text-sm text-foreground mt-1 capitalize">
                  {state.payment?.active && state.payment.contract
                    ? `${state.payment.contract.plan_code} · ${state.payment.contract.status}`
                    : hasVerifiedAccess
                      ? 'Active'
                      : 'Saved context'}
                </strong>
                {state.payment?.contract?.trial_end && state.payment.contract.status === 'trialing' && (
                  <span className="block text-[11px] text-muted-foreground mt-0.5">
                    Trial ends {formatUnixDate(state.payment.contract.trial_end)}
                  </span>
                )}
                {state.payment?.contract?.next_charge_at && state.payment.contract.status === 'active' && (
                  <span className="block text-[11px] text-muted-foreground mt-0.5">
                    Renews {formatUnixDate(state.payment.contract.next_charge_at)}
                  </span>
                )}
              </div>
            </div>

            {/* Max 3 Clear Next-Step Actions */}
            {hasVerifiedAccess ? (
              <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
                <Link
                  href="/intent-radar"
                  className="inline-flex items-center gap-2 rounded-xl bg-primary px-6 py-3 text-sm font-semibold text-primary-foreground shadow-sm hover:opacity-95 transition-opacity"
                >
                  Explore My Dashboard <ArrowRight size={16} />
                </Link>
                <Link
                  href="/intent-radar/discover"
                  className="inline-flex items-center gap-2 rounded-xl border border-border bg-card px-4 py-2.5 text-sm font-medium text-foreground hover:border-primary/50 transition-colors"
                >
                  <Search size={15} className="text-primary" /> Discover Signals
                </Link>
                <Link
                  href="/intent-radar/monitors/new"
                  className="inline-flex items-center gap-2 rounded-xl border border-border bg-card px-4 py-2.5 text-sm font-medium text-foreground hover:border-primary/50 transition-colors"
                >
                  <Radio size={15} className="text-primary" /> Set Up First Monitor
                </Link>
              </div>
            ) : (
              <div className="text-center pt-2">
                <Link href="/settings" className="text-primary underline text-sm font-semibold">
                  Open workspace settings →
                </Link>
              </div>
            )}

            <p className="text-center text-xs text-muted-foreground">
              Manage your plan, company profile, or research monitors anytime in Workspace Settings.
            </p>
          </div>
        </section>
      ) : (
        /* 2-Column Responsive Workspace (63% Left Form, 37% Sticky Copilot) */
        <div className="ai-onboarding-grid">
          <main className="ai-onboarding-workspace">
            {/* STEP 1: YOUR BUSINESS */}
            {view === 'welcome' && (
              <section className="ai-card p-6 md:p-8 space-y-6">
                <div className="space-y-4">
                  <div>
                    <label htmlFor="onboarding-website-url" className="block text-sm font-semibold text-foreground mb-1.5">
                      Company website
                    </label>
                    <div className="relative">
                      <Globe size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none" />
                      <input
                        id="onboarding-website-url"
                        type="url"
                        placeholder="https://yourcompany.com"
                        value={website}
                        maxLength={600}
                        onChange={e => setWebsite(e.target.value)}
                        onKeyDown={e => {
                          if (e.key === 'Enter' && website.trim() && !pending && state.capabilities.company_analysis) {
                            e.preventDefault();
                            void analyze();
                          }
                        }}
                        className="ai-input pl-10"
                      />
                    </div>
                    <p className="text-xs text-muted-foreground mt-1.5">
                      We inspect up to 5 public pages (honoring robots.txt) to extract your offerings, positioning, and audiences.
                    </p>
                  </div>

                  <div>
                    <label htmlFor="onboarding-objective" className="block text-sm font-semibold text-foreground mb-1.5">
                      Primary business objective
                    </label>
                    <select
                      id="onboarding-objective"
                      value={objective}
                      onChange={e => setObjective(e.target.value)}
                      className="ai-select"
                    >
                      {OBJECTIVES.map(([key, label, desc]) => (
                        <option value={key} key={key}>
                          {label} — {desc}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Concise Reassurance Strip */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 border-t border-border/70 text-xs text-muted-foreground">
                  <div className="flex items-start gap-2">
                    <Building2 size={15} className="text-primary flex-shrink-0 mt-0.5" />
                    <span>Extracts products, value proposition &amp; positioning</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <Users2 size={15} className="text-primary flex-shrink-0 mt-0.5" />
                    <span>Builds 5 distinct ICPs with real buying triggers</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <ShieldCheck size={15} className="text-primary flex-shrink-0 mt-0.5" />
                    <span>You review &amp; approve everything before saving</span>
                  </div>
                </div>

                <div className="ai-actions pt-2">
                  <Button
                    size="lg"
                    disabled={pending || !website.trim() || !state.capabilities.company_analysis}
                    onClick={() => void analyze()}
                    className="ai-btn-primary"
                  >
                    <Sparkles size={16} className="mr-2" />
                    {pending ? 'Starting website research…' : 'Analyze my business with AI'}
                  </Button>
                  <Button variant="ghost" size="lg" disabled={pending} onClick={() => void manualMode()}>
                    Set up manually
                  </Button>
                </div>

                {!state.capabilities.company_analysis && (
                  <div className="ai-notice-box" role="alert">
                    <AlertCircle size={16} className="text-amber-500 flex-shrink-0" />
                    <p>AI website analysis is currently unavailable in this environment. Manual setup remains fully available.</p>
                  </div>
                )}
              </section>
            )}

            {/* STEP 2: BUSINESS PROFILE (Clean Editable Sections — Zero Quoted-Evidence or Raw Trace Clutter) */}
            {view === 'company' && (
              <section className="ai-card p-6 md:p-8">
                {companyId && (
                  <ReviewStatusCard
                    kind="company"
                    query={companyReview}
                    onControl={async action => controlReview('company', action)}
                  />
                )}

                {/* Section 1: Company Overview */}
                <div className="pb-onb-section">
                  <div className="pb-onb-section-head">
                    <div className="pb-onb-section-title">
                      <Building2 size={16} className="text-primary" />
                      <span>Company overview</span>
                    </div>
                    {hasSectionSuggestions('overview') && (
                      <div className="flex items-center gap-2">
                        <Button size="sm" variant="outline" onClick={() => applySection(SECTION_FIELDS.overview)}>
                          Accept this section
                        </Button>
                        <button
                          type="button"
                          className="text-xs text-muted-foreground hover:text-foreground underline"
                          onClick={() => rejectSection('overview', SECTION_FIELDS.overview)}
                        >
                          Reject suggestions
                        </button>
                      </div>
                    )}
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <label htmlFor="onb-company-name" className="block text-xs font-semibold text-foreground mb-1.5">
                        {companyFieldLabels['name']}
                      </label>
                      <input
                        id="onb-company-name"
                        aria-label={companyFieldLabels['name']}
                        value={draft.name}
                        maxLength={120}
                        onChange={e => setDraft(v => ({ ...v, name: e.target.value }))}
                        className={`ai-input ${isLowQualityValue(draft.name) ? 'border-destructive' : ''}`}
                        placeholder="e.g. PlaneByte"
                      />
                      {isLowQualityValue(draft.name) && (
                        <p className="text-[11px] text-destructive mt-1">Enter a valid company name.</p>
                      )}
                    </div>

                    <div>
                      <label htmlFor="onb-company-website" className="block text-xs font-semibold text-foreground mb-1.5">
                        {companyFieldLabels['website']}
                      </label>
                      <input
                        id="onb-company-website"
                        aria-label={companyFieldLabels['website']}
                        value={draft.website}
                        maxLength={600}
                        onChange={e => setDraft(v => ({ ...v, website: e.target.value }))}
                        className="ai-input"
                        placeholder="https://yourcompany.com"
                      />
                    </div>

                    <div>
                      <label htmlFor="onb-company-industry" className="block text-xs font-semibold text-foreground mb-1.5">
                        {companyFieldLabels['industry']}
                      </label>
                      <input
                        id="onb-company-industry"
                        aria-label={companyFieldLabels['industry']}
                        value={draft.industry}
                        maxLength={120}
                        onChange={e => setDraft(v => ({ ...v, industry: e.target.value }))}
                        className="ai-input"
                        placeholder="e.g. B2B SaaS · Buyer-Intent Intelligence"
                      />
                      {companyReady && !draft.industry.trim() && (
                        <span className="pb-missing-hint">
                          Not enough information found ·{' '}
                          <button
                            type="button"
                            className="text-primary underline font-medium"
                            disabled={chatPending}
                            onClick={() => void askAssistant('Suggest the best concise industry category for my business based on our description and products.')}
                          >
                            Suggest with AI
                          </button>
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="mt-4">
                    <div className="ai-field-header">
                      <label htmlFor="onb-company-desc" className="text-xs font-semibold text-foreground">
                        {companyFieldLabels['description']}
                      </label>
                      <button
                        type="button"
                        className="ai-improve-btn"
                        disabled={chatPending}
                        onClick={() =>
                          void askAssistant(
                            draft.description.trim()
                              ? `Improve my company description so it clearly communicates what we do and who we help:\n"${draft.description}"`
                              : 'Draft a concise company description based on my offerings and website.'
                          )
                        }
                      >
                        <Wand2 size={11} /> {draft.description.trim() ? 'Improve with AI' : 'Draft with AI'}
                      </button>
                    </div>
                    <textarea
                      id="onb-company-desc"
                      aria-label={companyFieldLabels['description']}
                      rows={3}
                      value={draft.description}
                      maxLength={1000}
                      onChange={e => setDraft(v => ({ ...v, description: e.target.value }))}
                      className={`ai-textarea ${isLowQualityValue(draft.description) ? 'border-destructive' : ''}`}
                      placeholder="Concise overview of your business and the value you deliver…"
                    />
                    {isLowQualityValue(draft.description) && (
                      <p className="text-[11px] text-destructive mt-1">Please enter a meaningful business description.</p>
                    )}
                  </div>
                </div>

                {/* Section 2: What the Company Does (Products & Services) */}
                <div className="pb-onb-section">
                  <div className="pb-onb-section-head">
                    <div className="pb-onb-section-title">
                      <Layers size={16} className="text-primary" />
                      <span>What the company does</span>
                      <span className="text-xs font-normal text-muted-foreground">({draft.products_services.length})</span>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      {hasSectionSuggestions('offerings') && (
                        <>
                          <Button size="sm" variant="outline" onClick={() => applySection(SECTION_FIELDS.offerings)}>
                            Accept this section
                          </Button>
                          <button
                            type="button"
                            className="text-xs text-muted-foreground hover:text-foreground underline"
                            onClick={() => rejectSection('offerings', SECTION_FIELDS.offerings)}
                          >
                            Reject suggestions
                          </button>
                        </>
                      )}
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        disabled={draft.products_services.length >= 20}
                        onClick={() =>
                          setDraft(v => ({
                            ...v,
                            products_services: [...v.products_services, { name: '', category: 'Software', description: '' }]
                          }))
                        }
                      >
                        <Plus size={14} className="mr-1" /> Add offering
                      </Button>
                    </div>
                  </div>

                  {draft.products_services.length === 0 && companyReady && (
                    <div className="pb-missing-hint mb-3">
                      Not enough information found on your website · Add at least one product or service below.
                    </div>
                  )}

                  <div className="space-y-2.5">
                    {draft.products_services.map((offering, i) => (
                      <div key={i} className="grid grid-cols-1 md:grid-cols-12 gap-2.5 items-start rounded-xl bg-muted/25 p-3">
                        <div className="md:col-span-4">
                          <label htmlFor={`onb-prod-name-${i}`} className="block text-[11px] font-medium text-muted-foreground mb-1">
                            Product or service name
                          </label>
                          <input
                            id={`onb-prod-name-${i}`}
                            value={offering.name}
                            maxLength={120}
                            onChange={e =>
                              setDraft(v => ({
                                ...v,
                                products_services: v.products_services.map((o, j) => (i === j ? { ...o, name: e.target.value } : o))
                              }))
                            }
                            className="ai-input text-xs"
                            placeholder="e.g. Intent Radar"
                          />
                        </div>
                        <div className="md:col-span-8">
                          <label htmlFor={`onb-prod-desc-${i}`} className="block text-[11px] font-medium text-muted-foreground mb-1">
                            Core capability &amp; value
                          </label>
                          <div className="flex gap-2">
                            <input
                              id={`onb-prod-desc-${i}`}
                              value={offering.description}
                              maxLength={1000}
                              onChange={e =>
                                setDraft(v => ({
                                  ...v,
                                  products_services: v.products_services.map((o, j) =>
                                    i === j ? { ...o, description: e.target.value } : o
                                  )
                                }))
                              }
                              className="ai-input text-xs flex-1"
                              placeholder="What does this offering help customers achieve?"
                            />
                            <button
                              type="button"
                              className="text-muted-foreground hover:text-destructive p-2 rounded-lg"
                              onClick={() =>
                                setDraft(v => ({
                                  ...v,
                                  products_services: v.products_services.filter((_, j) => j !== i)
                                }))
                              }
                              aria-label="Remove offering"
                            >
                              <X size={15} />
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Section 3: Market Positioning */}
                <div className="pb-onb-section">
                  <div className="pb-onb-section-head">
                    <div className="pb-onb-section-title">
                      <Sparkles size={16} className="text-primary" />
                      <span>Market positioning</span>
                    </div>
                    {hasSectionSuggestions('positioning') && (
                      <div className="flex items-center gap-2">
                        <Button size="sm" variant="outline" onClick={() => applySection(SECTION_FIELDS.positioning)}>
                          Accept this section
                        </Button>
                        <button
                          type="button"
                          className="text-xs text-muted-foreground hover:text-foreground underline"
                          onClick={() => rejectSection('positioning', SECTION_FIELDS.positioning)}
                        >
                          Reject suggestions
                        </button>
                      </div>
                    )}
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <div className="ai-field-header">
                        <label htmlFor="onb-positioning" className="text-xs font-semibold text-foreground">
                          {companyFieldLabels['positioning']}
                        </label>
                        <button
                          type="button"
                          className="ai-improve-btn"
                          disabled={chatPending}
                          onClick={() =>
                            void askAssistant(
                              draft.positioning.trim()
                                ? `Make my positioning statement more specific and differentiated:\n"${draft.positioning}"`
                                : 'Draft a sharp positioning statement based on my company overview and offerings.'
                            )
                          }
                        >
                          <Wand2 size={11} /> {draft.positioning.trim() ? 'Make more specific' : 'Draft with AI'}
                        </button>
                      </div>
                      <textarea
                        id="onb-positioning"
                        aria-label={companyFieldLabels['positioning']}
                        rows={3}
                        value={draft.positioning}
                        maxLength={1000}
                        onChange={e => setDraft(v => ({ ...v, positioning: e.target.value }))}
                        className="ai-textarea"
                        placeholder="How you differentiate and what core problem you solve…"
                      />
                    </div>

                    <div>
                      <div className="ai-field-header">
                        <label htmlFor="onb-specialties" className="text-xs font-semibold text-foreground">
                          {companyFieldLabels['specialties']}
                        </label>
                        {companyReady && !draft.specialties.filter(Boolean).length && (
                          <button
                            type="button"
                            className="ai-improve-btn"
                            disabled={chatPending}
                            onClick={() => void askAssistant('Suggest 4 to 6 specific specialties and differentiators for my business profile.')}
                          >
                            <Wand2 size={11} /> Suggest with AI
                          </button>
                        )}
                      </div>
                      <textarea
                        id="onb-specialties"
                        rows={3}
                        value={draft.specialties.join('\n')}
                        onChange={e => setDraft(v => ({ ...v, specialties: e.target.value.split('\n') }))}
                        className="ai-textarea"
                        placeholder="One per line (e.g. Buyer-Intent Signals, Competitor Tracking)…"
                      />
                      {companyReady && !draft.specialties.filter(Boolean).length && (
                        <span className="pb-missing-hint">Not enough information found on website.</span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Section 4: Target Market */}
                <div className="pb-onb-section">
                  <div className="pb-onb-section-head">
                    <div className="pb-onb-section-title">
                      <Users2 size={16} className="text-primary" />
                      <span>Target market</span>
                    </div>
                    {hasSectionSuggestions('markets') && (
                      <div className="flex items-center gap-2">
                        <Button size="sm" variant="outline" onClick={() => applySection(SECTION_FIELDS.markets)}>
                          Accept this section
                        </Button>
                        <button
                          type="button"
                          className="text-xs text-muted-foreground hover:text-foreground underline"
                          onClick={() => rejectSection('markets', SECTION_FIELDS.markets)}
                        >
                          Reject suggestions
                        </button>
                      </div>
                    )}
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <label htmlFor="onb-target-customers" className="block text-xs font-semibold text-foreground mb-1.5">
                        {companyFieldLabels['target_customers']}
                      </label>
                      <textarea
                        id="onb-target-customers"
                        rows={3}
                        value={draft.target_customers.join('\n')}
                        onChange={e => setDraft(v => ({ ...v, target_customers: e.target.value.split('\n') }))}
                        className="ai-textarea"
                        placeholder="e.g. B2B Founders&#10;Growth Teams"
                      />
                      {companyReady && !draft.target_customers.filter(Boolean).length && (
                        <span className="pb-missing-hint">
                          Not enough information found ·{' '}
                          <button
                            type="button"
                            className="text-primary underline"
                            disabled={chatPending}
                            onClick={() => void askAssistant('Suggest target customer roles and teams for our offerings.')}
                          >
                            Suggest
                          </button>
                        </span>
                      )}
                    </div>

                    <div>
                      <label htmlFor="onb-target-industries" className="block text-xs font-semibold text-foreground mb-1.5">
                        {companyFieldLabels['target_industries']}
                      </label>
                      <textarea
                        id="onb-target-industries"
                        rows={3}
                        value={draft.target_industries.join('\n')}
                        onChange={e => setDraft(v => ({ ...v, target_industries: e.target.value.split('\n') }))}
                        className="ai-textarea"
                        placeholder="e.g. B2B SaaS&#10;Agencies"
                      />
                      {companyReady && !draft.target_industries.filter(Boolean).length && (
                        <span className="pb-missing-hint">
                          Not enough information found ·{' '}
                          <button
                            type="button"
                            className="text-primary underline"
                            disabled={chatPending}
                            onClick={() => void askAssistant('Suggest the top target industries for our products.')}
                          >
                            Suggest
                          </button>
                        </span>
                      )}
                    </div>

                    <div>
                      <label htmlFor="onb-countries" className="block text-xs font-semibold text-foreground mb-1.5">
                        {companyFieldLabels['countries_served']}
                      </label>
                      <textarea
                        id="onb-countries"
                        rows={3}
                        value={draft.countries_served.join('\n')}
                        onChange={e => setDraft(v => ({ ...v, countries_served: e.target.value.split('\n') }))}
                        className="ai-textarea"
                        placeholder="Leave blank for global"
                      />
                      <span className="text-[11px] text-muted-foreground block mt-1">Leave blank for global markets.</span>
                    </div>
                  </div>
                </div>

                {/* Primary Step 2 Action */}
                <div className="ai-actions pt-4 border-t border-border/70">
                  <Button
                    size="lg"
                    disabled={
                      pending ||
                      draft.name.trim().length < 2 ||
                      isLowQualityValue(draft.name) ||
                      !draft.products_services.length ||
                      draft.products_services.some(v => v.name.trim().length < 2 || isLowQualityValue(v.name))
                    }
                    onClick={() => void saveCompany()}
                    className="ai-btn-primary"
                  >
                    {pending
                      ? 'Saving profile…'
                      : progress.preferences.setup_mode === 'AI' && state.capabilities.icp_recommendations
                        ? 'Approve profile & discover ideal customers →'
                        : 'Approve company profile'}
                  </Button>
                  <Button variant="ghost" onClick={() => setView('welcome')}>
                    ← Back to website
                  </Button>
                </div>
              </section>
            )}

            {/* STEP 3: IDEAL CUSTOMERS (5 Compact Expandable ICP Cards with Buying Triggers) */}
            {view === 'icp' && (
              <section className="ai-card p-6 md:p-8 space-y-5">
                {icpId && (
                  <ReviewStatusCard
                    kind="icp"
                    query={icpReview}
                    onControl={async action => controlReview('icp', action)}
                    onFreshRun={async () => perform(() => prepareICP(progress.revision, state.company.version, true))}
                  />
                )}

                {!icpId && state.capabilities.icp_recommendations && (
                  <div className="text-center py-8 space-y-3">
                    <p className="text-sm text-muted-foreground">
                      Ready to identify 5 tailored buyer segments with roles, pain points, and buying triggers.
                    </p>
                    <Button
                      size="lg"
                      disabled={pending}
                      onClick={() => void perform(() => prepareICP(progress.revision))}
                      className="ai-btn-primary"
                    >
                      <Sparkles size={16} className="mr-2" />
                      Generate 5 Ideal Customer Profiles with AI
                    </Button>
                  </div>
                )}

                {candidates.length > 0 && (
                  <div className="space-y-3.5">
                    <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
                      <span>
                        <strong className="text-foreground">{selected.length} of {candidates.length}</strong> segments selected
                      </span>
                      <span>Choose 1 primary ICP to guide your research defaults</span>
                    </div>

                    <div className="space-y-3">
                      {candidates.map((cand, i) => {
                        const isSelected = selected.includes(i);
                        const isPrimary = primary === i && isSelected;
                        const isExpanded = expandedICP === i;
                        const roles = list(cand.draft.criteria.contact.job_titles);
                        const sizes = list(cand.draft.criteria.company.company_sizes);
                        const industries = list(cand.draft.criteria.company.industries);
                        const pains = [...list(cand.draft.criteria.intent.pain_points), ...list(cand.draft.criteria.intent.business_needs)];
                        const signals = list(cand.draft.criteria.intent.buying_signals);

                        return (
                          <article
                            key={i}
                            className={`pb-icp-card ${isPrimary ? 'is-primary' : ''} ${!isSelected ? 'is-unselected' : ''}`}
                          >
                            {/* Collapsed Compact Header */}
                            <div className="flex flex-wrap items-start justify-between gap-3">
                              <div className="flex items-start gap-2.5 min-w-0 flex-1">
                                <input
                                  type="checkbox"
                                  aria-label={`Select ${cand.draft.name}`}
                                  checked={isSelected}
                                  onChange={e => selectCandidate(i, e.target.checked)}
                                  className="ai-checkbox mt-1 flex-shrink-0"
                                />
                                <div className="min-w-0">
                                  <div className="flex flex-wrap items-center gap-2">
                                    <h3 className="font-semibold text-sm sm:text-base text-foreground">{cand.draft.name}</h3>
                                    {isPrimary && <span className="ai-badge-primary">★ Primary ICP</span>}
                                  </div>
                                  <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{cand.reason}</p>
                                </div>
                              </div>

                              <div className="flex items-center gap-3 flex-shrink-0">
                                <label className="flex items-center gap-1.5 text-xs text-muted-foreground cursor-pointer hover:text-foreground">
                                  <input
                                    type="radio"
                                    name="primary-segment"
                                    disabled={!isSelected}
                                    checked={isPrimary}
                                    onChange={() => setPrimary(i)}
                                    className="ai-radio"
                                  />
                                  <span>Primary</span>
                                </label>
                                <button
                                  type="button"
                                  onClick={() => setExpandedICP(isExpanded ? null : i)}
                                  className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
                                >
                                  {isExpanded ? 'Hide edit' : 'Edit'}
                                  {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                                </button>
                              </div>
                            </div>

                            {/* Compact Metadata Tags */}
                            <div className="mt-3 flex flex-wrap gap-1.5">
                              {roles.slice(0, 4).map((role, idx) => (
                                <span key={`r-${idx}`} className="ai-tag">{role}</span>
                              ))}
                              {sizes.slice(0, 2).map((sz, idx) => (
                                <span key={`s-${idx}`} className="ai-tag">{sz} employees</span>
                              ))}
                              {industries.slice(0, 2).map((ind, idx) => (
                                <span key={`i-${idx}`} className="ai-tag">{ind}</span>
                              ))}
                            </div>

                            {/* Pain Points + Buying Triggers Preview */}
                            <div className="mt-3 pt-3 border-t border-border/60 grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                              <div>
                                <span className="font-semibold text-foreground block mb-1">Key pain points &amp; needs</span>
                                <ul className="list-disc pl-4 text-muted-foreground space-y-1">
                                  {pains.slice(0, 3).map((item, idx) => (
                                    <li key={idx}>{item}</li>
                                  ))}
                                </ul>
                              </div>

                              <div>
                                <div className="flex items-center justify-between mb-1">
                                  <span className="font-semibold text-foreground">Buying triggers &amp; signals</span>
                                  {signals.length === 0 && (
                                    <button
                                      type="button"
                                      className="text-[11px] text-primary underline font-medium"
                                      disabled={chatPending}
                                      onClick={() => {
                                        setPrimary(i);
                                        void askAssistant(
                                          `Generate 3 to 4 concrete public buying triggers and buyer-intent signals for the ICP "${cand.draft.name}" (${roles.join(', ')}).`
                                        );
                                      }}
                                    >
                                      Generate with AI
                                    </button>
                                  )}
                                </div>
                                {signals.length > 0 ? (
                                  <ul className="list-disc pl-4 text-muted-foreground space-y-1">
                                    {signals.slice(0, 3).map((sig, idx) => (
                                      <li key={idx}>{sig}</li>
                                    ))}
                                  </ul>
                                ) : (
                                  <p className="text-muted-foreground italic">
                                    No buying triggers returned yet — click Generate with AI or expand Edit to add signals.
                                  </p>
                                )}
                              </div>
                            </div>

                            {/* Expanded Full Editor */}
                            {isExpanded && (
                              <div className="mt-4 pt-4 border-t border-border space-y-3 text-xs">
                                <div>
                                  <label htmlFor={`icp-name-${i}`} className="block text-[11px] font-semibold text-foreground mb-1">
                                    Profile name
                                  </label>
                                  <input
                                    id={`icp-name-${i}`}
                                    value={cand.draft.name}
                                    maxLength={120}
                                    onChange={e =>
                                      setCandidates(rows =>
                                        rows.map((v, j) => (i === j ? { ...v, draft: { ...v.draft, name: e.target.value } } : v))
                                      )
                                    }
                                    className="ai-input text-xs"
                                  />
                                </div>

                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                  {(
                                    [
                                      ['contact', 'job_titles', 'Decision-maker roles'],
                                      ['company', 'industries', 'Target industries'],
                                      ['company', 'company_sizes', 'Company sizes (e.g. 11-50, 51-200)'],
                                      ['company', 'countries', 'Target countries (optional)'],
                                      ['intent', 'business_needs', 'Business needs'],
                                      ['intent', 'pain_points', 'Pain points'],
                                      ['intent', 'buying_signals', 'Buying triggers & intent signals'],
                                      ['intent', 'exclusions', 'Exclusions / disqualifiers']
                                    ] as const
                                  ).map(([grp, fld, lbl]) => (
                                    <div key={fld}>
                                      <label htmlFor={`icp-${i}-${fld}`} className="block text-[11px] font-semibold text-foreground mb-1">
                                        {lbl}
                                      </label>
                                      <textarea
                                        id={`icp-${i}-${fld}`}
                                        rows={2}
                                        value={describe(cand.draft.criteria[grp][fld])}
                                        onChange={e => candidateField(i, grp, fld, e.target.value)}
                                        className="ai-textarea text-xs"
                                        placeholder="One per line…"
                                      />
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                          </article>
                        );
                      })}
                    </div>
                  </div>
                )}

                <div className="ai-actions pt-2">
                  <Button
                    size="lg"
                    disabled={pending || !selected.length || !selected.includes(primary)}
                    onClick={() => void acceptICPs()}
                    className="ai-btn-primary"
                  >
                    Confirm customer profiles &amp; prepare research →
                  </Button>
                  <Button variant="ghost" onClick={() => setView('company')}>
                    ← Back to business profile
                  </Button>
                </div>
              </section>
            )}

            {/* STEP 4: RESEARCH SETUP (Smart Keywords, Negative Exclusions & Honest Source Coverage) */}
            {view === 'research' && (
              <section className="ai-card p-6 md:p-8 space-y-6">
                {/* Compact Context Strip */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 rounded-xl bg-muted/30 p-4 text-xs">
                  <div>
                    <span className="text-muted-foreground block">Company</span>
                    <strong className="text-sm text-foreground">{state.company.name}</strong>
                  </div>
                  <div>
                    <span className="text-muted-foreground block">Offerings</span>
                    <strong className="text-sm text-foreground">
                      {state.company.products_services.map(v => v.name).join(', ') || 'Confirmed'}
                    </strong>
                  </div>
                  <div>
                    <span className="text-muted-foreground block">Primary ICP</span>
                    <strong className="text-sm text-primary">
                      {candidates[primary]?.draft?.name ||
                        profiles.data?.items.find(p => p.id === defaultICP)?.name ||
                        'Active segment'}
                    </strong>
                  </div>
                </div>

                {/* Research Keywords & Context-Sensitive Negative Exclusions */}
                <div className="space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <h3 className="text-sm font-semibold text-foreground">Signal keywords &amp; filters</h3>
                      <p className="text-xs text-muted-foreground">
                        PlaneByte monitors public discussions matching these high-intent phrases and filters out negative terms.
                      </p>
                    </div>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      disabled={chatPending}
                      onClick={() =>
                        void askAssistant(
                          `Generate 6 to 8 specific, realistic high-intent research phrases (avoid vague generic terms) and 5 to 6 context-sensitive negative exclusion keywords for "${state.company.name}" targeting "${candidates[primary]?.draft?.name || 'our primary ICP'}". Return both as ready-to-apply proposed_updates.`
                        )
                      }
                    >
                      <Wand2 size={13} className="mr-1.5" />
                      Generate with AI
                    </Button>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <div className="ai-field-header">
                        <label htmlFor="onboarding-research-keywords" className="text-xs font-semibold text-foreground">
                          High-intent research phrases
                        </label>
                        <button
                          type="button"
                          className="ai-improve-btn"
                          disabled={chatPending}
                          onClick={() =>
                            void askAssistant(
                              'Generate 6 to 8 specific public discussion phrases, problem queries, and tool comparison terms indicating high buying intent for our products and primary ICP.'
                            )
                          }
                        >
                          <Sparkles size={11} /> Refine
                        </button>
                      </div>
                      <textarea
                        id="onboarding-research-keywords"
                        rows={6}
                        value={keywords}
                        onChange={e => setKeywords(e.target.value)}
                        className="ai-textarea"
                        placeholder="One phrase per line (up to 12)&#10;e.g. buyer intent tools for B2B&#10;how to find leads from public discussions"
                      />
                      <span className="text-[11px] text-muted-foreground block mt-1">
                        Up to 12 phrases (one per line). Specific buyer language outperforms generic terms.
                      </span>
                    </div>

                    <div>
                      <div className="ai-field-header">
                        <label htmlFor="onboarding-excluded-keywords" className="text-xs font-semibold text-foreground">
                          Negative / exclusion terms
                        </label>
                        <button
                          type="button"
                          className="ai-improve-btn"
                          disabled={chatPending}
                          onClick={() =>
                            void askAssistant(
                              'Suggest 5 to 7 context-sensitive negative exclusion keywords to filter out irrelevant noise (like student projects, job postings, or unrelated free requests) without blocking real buyers.'
                            )
                          }
                        >
                          <Sparkles size={11} /> Suggest exclusions
                        </button>
                      </div>
                      <textarea
                        id="onboarding-excluded-keywords"
                        rows={6}
                        value={excluded}
                        onChange={e => setExcluded(e.target.value)}
                        className="ai-textarea"
                        placeholder="One term per line (up to 12)&#10;e.g. internship&#10;homework&#10;free crack&#10;hiring"
                      />
                      <span className="text-[11px] text-muted-foreground block mt-1">
                        Up to 12 terms (one per line) to reduce irrelevant noise.
                      </span>
                    </div>
                  </div>
                </div>

                {/* Honest Deployed Source Coverage */}
                <div className="pt-4 border-t border-border/70">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
                    Supported signal sources
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {liveSources.map(src => {
                      const available = src.state === 'Available';
                      return (
                        <div
                          key={src.id}
                          className="rounded-xl border border-border/80 bg-muted/20 p-3 flex items-start justify-between gap-3"
                        >
                          <div className="min-w-0">
                            <div className="flex items-center gap-2">
                              <strong className="text-xs font-semibold text-foreground">{src.name}</strong>
                              <span
                                className={
                                  'rounded-full px-2 py-0.5 text-[10px] font-medium ' +
                                  (available
                                    ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
                                    : 'bg-muted text-muted-foreground')
                                }
                              >
                                {available ? 'Available' : src.state === 'Not configured' ? 'Configurable in Settings' : src.state}
                              </span>
                            </div>
                            <p className="text-[11px] text-muted-foreground mt-1 leading-relaxed">{src.coverage}</p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                <div className="ai-actions pt-2">
                  <Button size="lg" disabled={pending} onClick={() => void finish()} className="ai-btn-primary">
                    {pending ? 'Saving research setup…' : 'Continue to plan & payment →'}
                  </Button>
                  <Button variant="ghost" onClick={() => setView('icp')}>
                    ← Back to ideal customers
                  </Button>
                </div>
              </section>
            )}

            {/* STEP 5: PLAN & PAYMENT (Creem Live Verified Checkout) */}
            {view === 'plan' && (
              <section className="ai-card p-6 md:p-8">
                <SubscriptionPayment
                  embedded
                  onActivated={() => {
                    setState(previous => ({ ...previous, payment: { required: true, active: true } }));
                    setView('ready');
                    void client.invalidateQueries({ queryKey: ['plane-products'] });
                    void onRefresh();
                  }}
                />
              </section>
            )}

            {/* Notices & Errors */}
            {notice && (
              <div className="ai-notice-box mt-4" role="status">
                <Check size={15} className="text-primary flex-shrink-0" />
                <p>{notice}</p>
              </div>
            )}
            {error && (
              <div className="ai-error-box mt-4" role="alert">
                <AlertCircle size={15} className="text-destructive flex-shrink-0 mt-0.5" />
                <div>
                  <strong className="block text-xs">Setup message</strong>
                  <p className="text-xs mt-0.5">{error}</p>
                </div>
              </div>
            )}
          </main>

          {/* RIGHT: Persistent Sticky AI Copilot */}
          <aside className="ai-copilot-container hidden lg:flex">
            <CopilotPanel
              companyName={draft.name || state.company.name}
              currentStep={view}
              messages={messages}
              onAsk={askAssistant}
              onApplyUpdate={applyProposedUpdate}
              pending={chatPending}
              adviceReview={adviceReview.data}
              onRefreshAdvice={() => void adviceReview.refetch()}
              onRetryAdvice={() => void retryAdvice()}
              companyReview={companyReview.data}
              icpReview={icpReview.data}
              onRetryJob={() => {
                const kind = view === 'icp' ? 'icp' : 'company';
                void controlReview(kind, 'RETRY').catch(e => setError((e as Error).message));
              }}
            />
          </aside>

          {/* Mobile Floating Copilot Dock & Accessible Radix Drawer */}
          <div className="lg:hidden">
            <button
              type="button"
              className="ai-mobile-dock-btn"
              onClick={() => setMobileDrawerOpen(true)}
              aria-label="Open AI Copilot"
            >
              <Sparkles size={15} />
              <span>AI Copilot</span>
              {(companyReview.data?.status === 'RUNNING' || icpReview.data?.status === 'RUNNING' || chatPending) && (
                <span className="ai-status-dot-pulse" />
              )}
            </button>

            <Dialog.Root open={mobileDrawerOpen} onOpenChange={setMobileDrawerOpen}>
              <Dialog.Portal>
                <Dialog.Overlay className="ai-mobile-drawer-backdrop" />
                <Dialog.Content className="ai-mobile-drawer-sheet" aria-describedby={undefined}>
                  <div className="ai-mobile-drawer-header">
                    <div className="flex items-center gap-2">
                      <Sparkles size={15} className="text-primary" />
                      <Dialog.Title className="font-semibold text-sm">PlaneByte AI Copilot</Dialog.Title>
                    </div>
                    <Dialog.Close asChild>
                      <button
                        type="button"
                        aria-label="Close AI Copilot"
                        className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground"
                      >
                        <X size={18} />
                      </button>
                    </Dialog.Close>
                  </div>
                  <div className="flex-1 min-h-0 flex flex-col">
                    <CopilotPanel
                      companyName={draft.name || state.company.name}
                      currentStep={view}
                      messages={messages}
                      onAsk={askAssistant}
                      onApplyUpdate={applyProposedUpdate}
                      pending={chatPending}
                      adviceReview={adviceReview.data}
                      onRefreshAdvice={() => void adviceReview.refetch()}
                      onRetryAdvice={() => void retryAdvice()}
                      companyReview={companyReview.data}
                      icpReview={icpReview.data}
                      onRetryJob={() => {
                        const kind = view === 'icp' ? 'icp' : 'company';
                        void controlReview(kind, 'RETRY').catch(e => setError((e as Error).message));
                      }}
                    />
                  </div>
                </Dialog.Content>
              </Dialog.Portal>
            </Dialog.Root>
          </div>
        </div>
      )}
    </div>
  );
}

// Persistent AI Copilot Panel
function CopilotPanel({
  companyName,
  currentStep,
  messages,
  onAsk,
  onApplyUpdate,
  pending,
  adviceReview,
  onRefreshAdvice,
  onRetryAdvice,
  companyReview,
  icpReview,
  onRetryJob
}: {
  companyName: string;
  currentStep: StepKey;
  messages: CopilotMessage[];
  onAsk: (q: string) => Promise<void>;
  onApplyUpdate: (msgId: string, idx: number, upd: ProposedUpdate) => void;
  pending: boolean;
  adviceReview?: Review;
  onRefreshAdvice: () => void;
  onRetryAdvice: () => void;
  companyReview?: Review;
  icpReview?: Review;
  onRetryJob: () => void;
}) {
  const [inputVal, setInputVal] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView?.({ behavior: 'smooth' });
  }, [messages.length, pending]);

  const activeKind: 'company' | 'icp' = currentStep === 'icp' ? 'icp' : 'company';
  const activeJob = activeKind === 'icp' ? icpReview : companyReview;
  const jobStatus = deriveJobStatus(activeJob, activeKind);

  const stepPromptChips: Record<StepKey, string[]> = {
    welcome: [
      'What details will you research from my site?',
      'How does Intent Radar find buying signals?'
    ],
    company: [
      'Improve my company description',
      'Make my positioning more specific',
      'Suggest target industries'
    ],
    icp: [
      'Which of these 5 ICPs should I prioritize?',
      'Explain the difference between these segments',
      'Generate buying triggers for my primary ICP'
    ],
    research: [
      'Generate high-intent research keywords',
      'What negative keywords should I exclude?',
      'Make the targeting more focused'
    ],
    plan: [
      'Which plan fits an early-stage B2B team?',
      'How does the 3-day free trial work?'
    ],
    ready: ['Where should I begin discovering signals?']
  };

  const chips = stepPromptChips[currentStep] || [];

  return (
    <div className="ai-copilot-inner flex flex-col h-full">
      {/* Header */}
      <div className="ai-copilot-header px-4 py-3.5 border-b border-border flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-white/80 dark:bg-muted text-[#6b56a6] dark:text-[#c4b5fd] border border-border/70 flex items-center justify-center shadow-sm">
            <Bot size={16} />
          </div>
          <div>
            <h3 className="font-semibold text-xs text-foreground leading-tight">PlaneByte Copilot</h3>
            <span className="text-[10px] text-muted-foreground block">Contextual Setup Assistant</span>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          <span
            className={`ai-status-dot ${
              pending || jobStatus.isBusy ? 'is-busy' : jobStatus.isFailed ? 'is-failed' : 'is-ready'
            }`}
          />
          <span className="text-[11px] font-medium text-muted-foreground">
            {pending ? 'Thinking' : jobStatus.label}
          </span>
        </div>
      </div>

      {/* Live Job Progress or Failure Banner (synced to single source of truth) */}
      {jobStatus.isBusy && (
        <div className="mx-3 mt-3 p-3 rounded-xl border border-primary/25 bg-primary/[0.04]">
          <div className="flex items-center gap-2 text-xs font-semibold text-primary">
            <Sparkles size={13} className="animate-spin flex-shrink-0" />
            <span>{jobStatus.stageName}</span>
          </div>
          <div className="pb-progress-bar">
            <div className="pb-progress-bar-fill" />
          </div>
        </div>
      )}

      {jobStatus.isFailed && (
        <div className="mx-3 mt-3 p-3 rounded-xl border border-destructive/30 bg-destructive/5 space-y-1.5">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-destructive">
            <AlertCircle size={13} />
            <span>{jobStatus.stageName}</span>
          </div>
          <p className="text-[11px] text-muted-foreground leading-relaxed">
            {reviewFailure(activeJob?.error_code)}
          </p>
          {activeJob?.can_retry && (
            <button type="button" className="ai-chat-action-btn mt-1" onClick={onRetryJob}>
              <RefreshCw size={11} /> Retry analysis
            </button>
          )}
        </div>
      )}

      {/* Subtle Context Bar */}
      <div className="px-4 py-2 bg-muted/25 border-b border-border/60 text-[11px] flex items-center justify-between gap-2">
        <span className="text-muted-foreground truncate">
          Workspace: <strong className="text-foreground">{companyName || 'Your Company'}</strong>
        </span>
        <span className="text-primary font-medium text-[10px] flex-shrink-0">
          {STEP_LABELS[currentStep]}
        </span>
      </div>

      {/* Scrollable Conversation Thread Grouped by Step */}
      <div className="ai-copilot-messages flex-1 min-h-0 overflow-y-auto p-4 space-y-3">
        {messages.map((m, idx) => {
          const prevStep = idx > 0 ? messages[idx - 1].step : null;
          const showStepDivider = idx > 0 && prevStep !== m.step;
          return (
            <React.Fragment key={m.id}>
              {showStepDivider && (
                <div className="flex items-center gap-2 py-1 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                  <span className="h-px flex-1 bg-border/70" />
                  <span>{STEP_LABELS[m.step]}</span>
                  <span className="h-px flex-1 bg-border/70" />
                </div>
              )}
              <div className={`ai-message-bubble ${m.role === 'user' ? 'is-user' : 'is-assistant'}`}>
                {m.mode && <span className="ai-message-mode">{m.mode}</span>}
                <p className="text-xs leading-relaxed whitespace-pre-wrap">{m.text}</p>

                {/* Actionable Apply-to-Form Controls */}
                {m.role === 'assistant' && m.updates && m.updates.length > 0 && (
                  <div className="mt-2.5 pt-2.5 border-t border-border/60 space-y-2">
                    {m.updates.map((upd, uIdx) => {
                      const applied = m.appliedKeys?.includes(`${m.id}:${uIdx}`);
                      const previewText = Array.isArray(upd.value) ? upd.value.join(' · ') : upd.value;
                      return (
                        <div key={uIdx} className="rounded-lg bg-background/80 border border-border/70 p-2 space-y-1.5">
                          <p className="text-[11px] text-muted-foreground line-clamp-3">{previewText}</p>
                          <button
                            type="button"
                            disabled={applied}
                            className={`ai-chat-action-btn ${applied ? 'is-applied' : ''}`}
                            onClick={() => onApplyUpdate(m.id, uIdx, upd)}
                          >
                            {applied ? (
                              <>
                                <Check size={12} /> Applied to form
                              </>
                            ) : (
                              <>
                                <Wand2 size={12} /> {upd.label || 'Apply to form'}
                              </>
                            )}
                          </button>
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* Inline Retry Control on Failed Guidance */}
                {m.role === 'assistant' && m.isError && (
                  <div className="mt-2 flex items-center gap-2">
                    {(m.canRetry || adviceReview?.can_retry) && (
                      <button type="button" className="ai-chat-action-btn" onClick={onRetryAdvice}>
                        <RefreshCw size={11} /> Retry guidance
                      </button>
                    )}
                    <button type="button" className="text-[11px] text-muted-foreground underline" onClick={onRefreshAdvice}>
                      Refresh
                    </button>
                  </div>
                )}
              </div>
            </React.Fragment>
          );
        })}

        {pending && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground px-1">
            <Sparkles size={13} className="animate-spin text-primary" />
            <span>Drafting contextual guidance…</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Compact Contextual Suggestion Chips */}
      {chips.length > 0 && (
        <div className="px-3.5 py-2.5 border-t border-border/60 bg-muted/15 flex flex-wrap gap-1.5">
          {chips.map((chip, idx) => (
            <button
              key={idx}
              type="button"
              disabled={pending}
              className="ai-chip-btn"
              onClick={() => void onAsk(chip)}
            >
              {chip}
            </button>
          ))}
        </div>
      )}

      {/* Stable Composer */}
      <form
        onSubmit={e => {
          e.preventDefault();
          if (inputVal.trim() && !pending) {
            void onAsk(inputVal);
            setInputVal('');
          }
        }}
        className="p-3 border-t border-border flex items-center gap-2 bg-card"
      >
        <input
          type="text"
          aria-label="Ask Copilot about your business"
          value={inputVal}
          onChange={e => setInputVal(e.target.value)}
          placeholder="Ask Copilot to refine or suggest…"
          className="ai-copilot-input flex-1 text-xs"
          disabled={pending}
        />
        <Button
          type="submit"
          size="sm"
          aria-label="Send question to Copilot"
          disabled={pending || !inputVal.trim()}
          className="h-8 px-3"
        >
          <Send size={13} />
        </Button>
      </form>
    </div>
  );
}

// Clean Customer-Facing Review Progress & Status Card (NO raw technical traces or attempt tables)
function ReviewStatusCard({
  kind,
  query,
  onControl,
  onFreshRun
}: {
  kind: 'company' | 'icp';
  query: { data?: Review; error: Error | null; refetch: () => Promise<unknown> };
  onControl: (action: 'CANCEL' | 'RETRY') => Promise<void>;
  onFreshRun?: () => Promise<void>;
}) {
  const [busy, setBusy] = useState(false);
  const [ctrlErr, setCtrlErr] = useState('');
  const review = query.data;

  async function handleControl(action: 'CANCEL' | 'RETRY') {
    setBusy(true);
    setCtrlErr('');
    try {
      await onControl(action);
    } catch (e) {
      setCtrlErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (!review && !query.error) return null;

  const derived = deriveJobStatus(review, kind);
  const isFailed = derived.isFailed;
  const isRunning = derived.isBusy;
  const isReady = derived.isSuccess;

  return (
    <div
      className={`pb-progress-card ${isRunning ? 'is-busy' : isFailed ? 'is-failed' : isReady ? 'is-ready' : ''}`}
      role={isFailed ? 'alert' : 'status'}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2.5 min-w-0">
          {isFailed ? (
            <AlertCircle size={16} className="text-destructive flex-shrink-0 mt-0.5" />
          ) : isReady ? (
            <CheckCircle2 size={16} className="text-primary flex-shrink-0 mt-0.5" />
          ) : (
            <Sparkles size={16} className="animate-spin text-[#6b56a6] dark:text-[#c4b5fd] flex-shrink-0 mt-0.5" />
          )}
          <div className="min-w-0">
            <strong className="text-xs font-semibold text-foreground block">
              {query.error ? 'Could not refresh status' : derived.stageName}
            </strong>
            <p className="text-[11px] text-muted-foreground mt-0.5 leading-relaxed">
              {isFailed
                ? reviewFailure(review?.error_code)
                : isRunning
                  ? 'You can safely stay on this page or return later — progress is saved automatically.'
                  : kind === 'icp'
                    ? 'Review the 5 tailored buyer segments below and mark your primary ICP.'
                    : 'Extracted from your public website. Edit any field before approving.'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1.5 flex-shrink-0">
          {review?.can_retry && (
            <Button size="sm" variant="outline" disabled={busy} onClick={() => void handleControl('RETRY')}>
              Retry
            </Button>
          )}
          {isFailed && !review?.can_retry && onFreshRun && (
            <Button
              size="sm"
              variant="outline"
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                setCtrlErr('');
                try {
                  await onFreshRun();
                } catch (e) {
                  setCtrlErr((e as Error).message);
                } finally {
                  setBusy(false);
                }
              }}
            >
              Retry with fresh run
            </Button>
          )}
          {isRunning && (
            <Button size="sm" variant="ghost" disabled={busy} onClick={() => void handleControl('CANCEL')}>
              Cancel
            </Button>
          )}
          <button
            type="button"
            className="text-muted-foreground hover:text-foreground p-1.5 rounded-lg"
            onClick={() => void query.refetch()}
            aria-label="Refresh status"
          >
            <RefreshCw size={13} />
          </button>
        </div>
      </div>

      {isRunning && (
        <div className="pb-progress-bar">
          <div className="pb-progress-bar-fill" />
        </div>
      )}

      {ctrlErr && <p className="text-xs text-destructive mt-2">{ctrlErr}</p>}
    </div>
  );
}
