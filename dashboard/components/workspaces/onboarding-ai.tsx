"use client";
import React, { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Sparkles, Globe, ArrowRight, Check, RefreshCw, Target, ShieldCheck,
  Plus, X, Send, Network, Radio, Search, ChevronRight, HelpCircle,
  AlertCircle, MessageSquare, Bot, Layers, CheckCircle2, Zap, CreditCard,
  Building2, Users2, Lock, ArrowUpRight
} from 'lucide-react';
import { request } from '@/lib/intelligence';
import { useWorkspace } from './use-workspace';
import { useProducts } from './use-products';
import { Button } from '@/components/ui/button';
import { companyDraft, companyFieldLabels, type CompanyFields, type CompanyProfile } from './company-profile-types';
import { OnboardingICP } from './onboarding-icp';
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

type Preview = {
  suggestions?: Partial<CompanyFields>;
  evidence?: Record<string, { url: string | null; quote: string }[]>;
  warnings?: string[];
  pages_reviewed?: number;
  proposal_id?: string;
  candidates?: Candidate[];
  questions?: string[];
  answer?: string;
  suggestions_list?: string[];
  limitations?: string[];
};

type Review = {
  id: string;
  status: string;
  progress_stage: string;
  preview: Preview | null;
  can_retry: boolean;
  can_apply?: boolean;
};

type State = {
  payment?: { required: boolean; active: boolean };
  progress: Progress;
  company: CompanyProfile;
  reviews: { company?: Review; icp?: Review };
  capabilities: { company_analysis: boolean; icp_recommendations: boolean };
};

type StepKey = 'welcome' | 'company' | 'icp' | 'research' | 'plan' | 'ready';

const ONBOARDING_STEPS = [
  { key: 'welcome' as const, stepNum: 1, title: 'Understand Your Business', short: 'Business' },
  { key: 'company' as const, stepNum: 2, title: 'Review AI Business Profile', short: 'Profile' },
  { key: 'icp' as const, stepNum: 3, title: 'Discover Ideal Customers', short: 'Audience' },
  { key: 'research' as const, stepNum: 4, title: 'Prepare Your Research', short: 'Research' },
  { key: 'plan' as const, stepNum: 5, title: 'Choose Your Plan & Payment', short: 'Plan' },
];

const OBJECTIVES = [
  ['UNDERSTAND_CUSTOMER_NEEDS', 'Discover customer problems', 'Find recurring pain points and unresolved needs in public discussions.'],
  ['MONITOR_BUYING_CONTEXT', 'Find buying-intent conversations', 'Detect active evaluation, vendor comparison, and buying triggers.'],
  ['MONITOR_COMPETITORS', 'Monitor competitors', 'Track mentions, complaints, and migration discussions about alternatives.'],
  ['RESEARCH_MARKETS', 'Research a market', 'Investigate emerging industry topics and category shifts before investing.'],
  ['EXPLORE_OPPORTUNITIES', 'Explore opportunities', 'Surface early unbranded demand and potential partnership signals.']
] as const;

const GROUP_FIELDS: [string, (keyof CompanyFields)[]][] = [
  ['Company overview', ['name', 'website', 'description', 'industry']],
  ['Products & services', ['products_services']],
  ['Positioning', ['positioning', 'specialties']],
  ['Customers & markets', ['target_customers', 'target_industries', 'countries_served']],
];

const GARBAGE_REGEX = /^(\s*idk\s*|\s*xx+\s*|\s*i don'?t know\s*|\s*none\s*|\s*na\s*|\s*n\/a\s*|\s*test\s*|\s*asdf\s*|\s*nothing\s*|\s*\?+\s*|\s*no\s*)$/i;

function isLowQualityValue(val: string): boolean {
  const trimmed = (val || '').trim();
  if (!trimmed) return false;
  return trimmed.length < 3 || GARBAGE_REGEX.test(trimmed);
}
const terms = (value: string) => value.split('\n').map(v => v.trim()).filter(Boolean).slice(0, 12);
const list = (value: unknown): string[] => Array.isArray(value) ? value.filter((v): v is string => typeof v === 'string') : [];
const describe = (value: unknown): string => Array.isArray(value) ? value.map(v => typeof v === 'string' ? v : (v as { name: string; description: string }).name + ' — ' + (v as { description: string }).description).join('\n') : String(value || '');

async function api<T>(path: string, body?: unknown, method = 'POST') {
  return request<T>('/organization/onboarding' + path, {
    method,
    body: body === undefined ? undefined : JSON.stringify(body)
  });
}

export function AIOnboarding() {
  const workspace = useWorkspace(), org = workspace.data?.active_organization_id;
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
        <h1>We couldn’t load your saved setup</h1>
        <p>Your business data has not changed. Check your connection or retry.</p>
        <Button onClick={() => void query.refetch()}>Retry setup</Button>
      </section>
    );
  }
  if (!query.data) {
    return (
      <div className="ai-setup-loading" role="status">
        <Sparkles className="animate-spin text-primary" size={24} />
        <p>Loading your saved workspace setup…</p>
      </div>
    );
  }
  return <SetupWorkspace key={org} initial={query.data} onRefresh={() => query.refetch()} />;
}

function SetupWorkspace({ initial, onRefresh }: { initial: State; onRefresh: () => Promise<unknown> }) {
  const client = useQueryClient(), workspace = useWorkspace(), products = useProducts();
  const [state, setState] = useState(initial);

  const initialView = (): StepKey => {
    if (initial.progress.status === 'COMPLETED') return 'ready';
    const s = initial.progress.current_step;
    if (s === 'REVIEW') return 'research';
    if (['ICP', 'PREFERENCES'].includes(s)) return 'icp';
    if (['COMPANY', 'SERVICES'].includes(s) || initial.progress.preferences.company_review_id) return 'company';
    return 'welcome';
  };

  const [view, setView] = useState<StepKey>(initialView);
  const [draft, setDraft] = useState<CompanyFields>(() => companyDraft(initial.company));
  const [objective, setObjective] = useState(initial.progress.objectives.find(v => OBJECTIVES.some(([id]) => id === v)) || 'UNDERSTAND_CUSTOMER_NEEDS');
  const [website, setWebsite] = useState(initial.company.website);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [selectedFields, setSelectedFields] = useState<string[]>([]);
  const [rejected, setRejected] = useState<string[]>([]);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [primary, setPrimary] = useState(0);
  const [manualICP, setManualICP] = useState(false);
  const [defaultICP, setDefaultICP] = useState(initial.progress.default_icp_id || '');
  const [keywords, setKeywords] = useState(initial.progress.preferences.research_keywords.join('\n'));
  const [excluded, setExcluded] = useState(initial.progress.preferences.excluded_keywords.join('\n'));
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);

  // Assistant Chat State
  const [messages, setMessages] = useState<{ role: 'assistant' | 'user'; text: string; mode?: string }[]>([
    {
      role: 'assistant',
      text: "Welcome to PlaneByte! I'm your AI Onboarding Copilot. Enter your website on the left and I'll analyze your business offerings, value proposition, and discover your highest-intent customer segments."
    }
  ]);
  const [chatQuestion, setChatQuestion] = useState('');
  const [chatPending, setChatPending] = useState(false);

  const requestIds = useRef<Record<string, string>>({});
  const deadline = useRef(Date.now() + 120000);
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
    initialData: initial.reviews.company,
    refetchInterval: q => Date.now() < deadline.current && ['QUEUED', 'RUNNING'].includes(q.state.data?.status || '') ? 2500 : false
  });

  const icpReview = useQuery({
    queryKey: ['onboarding-review', icpId],
    queryFn: ({ signal }) => request<Review>('/organization/onboarding/reviews/' + icpId, { signal }),
    enabled: !!icpId,
    retry: false,
    initialData: initial.reviews.icp,
    refetchInterval: q => Date.now() < deadline.current && ['QUEUED', 'RUNNING'].includes(q.state.data?.status || '') ? 2500 : false
  });

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

  // Load ICP candidates when review is ready
  useEffect(() => {
    if (icpReview.data?.preview?.candidates && icpReview.data.preview.candidates.length > 0) {
      setCandidates(icpReview.data.preview.candidates);
      // Select all 5 candidates by default, with candidate 0 as primary
      const allIndices = icpReview.data.preview.candidates.map((_, i) => i);
      setSelected(allIndices);
      setPrimary(0);

      // Pre-fill keywords from top business needs
      const first = icpReview.data.preview.candidates[0];
      if (first && !keywords.trim()) {
        const extractedTerms = [
          ...list(first.draft.criteria.intent.business_needs),
          ...list(first.draft.criteria.intent.pain_points),
          ...list(first.draft.criteria.intent.buying_signals)
        ].slice(0, 8);
        if (extractedTerms.length) setKeywords(extractedTerms.join('\n'));
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
    await perform(async () => {
      const result = await api<{ review: Review; progress: Progress }>('/analyze', {
        revision: progress.revision,
        website: website.trim().startsWith('http') ? website.trim() : 'https://' + website.trim(),
        objective,
        request_id: id('website:' + website)
      });
      progressSaved(result.progress);
      client.setQueryData(['onboarding-review', result.review.id], result.review);
      deadline.current = Date.now() + 120000;
      setView('company');
      setMessages(prev => [
        ...prev,
        { role: 'user', text: `Analyze my website: ${website}` },
        {
          role: 'assistant',
          text: `Analyzing ${website}... I'm reading public pages and extracting your value proposition, offerings, and target segments. Review the cards on the left as they populate.`
        }
      ]);
    });
  }

  function apply(fields: (keyof CompanyFields)[]) {
    const values = companyReview.data?.preview?.suggestions || {};
    const patch = Object.fromEntries(fields.filter(f => f in values).map(f => [f, values[f]]));
    setDraft(v => ({ ...v, ...patch }));
    setSelectedFields(v => [...new Set([...v, ...Object.keys(patch)])]);
    setNotice('Selected suggestions applied to your draft. Review and approve before saving.');
  }

  function rejectSection(title: string, fields: (keyof CompanyFields)[]) {
    const suggested = companyReview.data?.preview?.suggestions || {};
    const original = companyDraft(state.company);
    setRejected(v => [...v, title]);
    setDraft(v => ({
      ...v,
      ...Object.fromEntries(
        fields
          .filter(f => selectedFields.includes(f) && JSON.stringify(v[f]) === JSON.stringify(suggested[f]))
          .map(f => [f, original[f]])
      )
    }));
    setSelectedFields(v => v.filter(f => !fields.includes(f as keyof CompanyFields)));
    setNotice('Suggestions for ' + title + ' excluded. Your original entries are preserved.');
  }

  async function prepareICP(revision: number, version = state.company.version) {
    const result = await api<{ review: Review; progress: Progress }>('/recommendations', {
      revision,
      request_id: id('icps:' + version)
    });
    progressSaved(result.progress);
    client.setQueryData(['onboarding-review', result.review.id], result.review);
    deadline.current = Date.now() + 120000;
    setNotice('Company profile approved. Discovering 5 ideal customer segments with AI.');
    setView('icp');
    setMessages(prev => [
      ...prev,
      {
        role: 'assistant',
        text: 'Analyzing your offerings and generating 5 distinct Ideal Customer Profiles (ICPs) with specific buyer roles, company tiers, and buying triggers...'
      }
    ]);
  }

  async function saveCompany() {
    // Validate required fields and block garbage placeholders
    if (!draft.name.trim() || draft.name.trim().length < 2 || isLowQualityValue(draft.name)) {
      setError('Please provide a valid company name (at least 2 characters).');
      return;
    }
    if (draft.description && isLowQualityValue(draft.description)) {
      setError('Please provide a meaningful business description so PlaneByte can discover relevant buying signals.');
      return;
    }
    if (!draft.products_services.length || draft.products_services.some(v => !v.name.trim() || isLowQualityValue(v.name))) {
      setError('Please confirm at least one named product or service (minimum 2 characters, no placeholders).');
      return;
    }

    await perform(async () => {
      const result = await api<{ company: CompanyProfile; progress: Progress }>('/company', {
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
      }, 'PUT');

      setState(v => ({ ...v, company: result.company, progress: result.progress }));
      setDraft(companyDraft(result.company));
      client.setQueryData(['organization-profile'], result.company);
      void client.invalidateQueries({ queryKey: ['intelligence-graph'] });
      setView('icp');
      setNotice('Company profile and offerings saved.');

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
        research_keywords: terms(keywords),
        excluded_keywords: terms(excluded)
      });
      progressSaved(result.progress);
      setDefaultICP(result.progress.default_icp_id || '');
      await client.invalidateQueries({ queryKey: ['setup-icps'] });
      void client.invalidateQueries({ queryKey: ['intent-radar'] });
      setView('research');
      setNotice('Customer profiles confirmed.');
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          text: `Great choice! ${candidates[primary]?.draft?.name || 'Primary segment'} is set as your default ICP. Now review your research keywords to power high-intent searches.`
        }
      ]);
    });
  }

  async function finish(primaryId?: string) {
    const targetId = primaryId || defaultICP;
    if (!targetId) {
      setError('A primary customer profile is required to complete onboarding.');
      return;
    }
    await perform(async () => {
      await api('/finish', {
        revision: progress.revision,
        primary_icp_id: targetId,
        research_keywords: terms(keywords),
        excluded_keywords: terms(excluded)
      });
      setNotice('Workspace context saved! Welcome to PlaneByte.');
      setState(v => ({ ...v, progress: { ...v.progress, status: 'COMPLETED' } }));
      setView('ready');
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
      void status; void can_edit;
      const result = await api<Progress>('', {
        ...values,
        objectives: [objective],
        preferences: {
          ...values.preferences,
          research_keywords: terms(keywords),
          excluded_keywords: terms(excluded)
        }
      }, 'PUT');
      progressSaved(result);
      setNotice('Progress saved safely. You can return anytime.');
      await onRefresh();
    });
  }

  async function manualMode() {
    await perform(async () => {
      const { status, can_edit, ...values } = progress;
      void status; void can_edit;
      const next = await api<Progress>('', {
        ...values,
        current_step: 'COMPANY',
        preferences: { ...values.preferences, setup_mode: 'MANUAL' }
      }, 'PUT');
      progressSaved(next);
      setView('company');
    });
  }

  function selectCandidate(index: number, checked: boolean) {
    const next = checked ? [...selected, index] : selected.filter(v => v !== index);
    setSelected(next);
    if (!next.includes(primary) && next.length > 0) setPrimary(next[0]);
    if (!keywords.trim() && checked && candidates[index]) {
      setKeywords(
        terms([
          ...list(candidates[index].draft.criteria.intent.business_needs),
          ...list(candidates[index].draft.criteria.intent.pain_points)
        ].join('\n')).filter(v => v.length <= 100).join('\n')
      );
    }
  }

  // Ask AI Copilot Question
  async function askAssistant(promptText?: string) {
    const q = (promptText || chatQuestion).trim();
    if (!q || chatPending) return;
    setChatPending(true);
    setChatQuestion('');
    setMessages(prev => [...prev, { role: 'user', text: q }]);

    try {
      const reqId = crypto.randomUUID();
      const res = await api<{ answer?: string; mode: string; job: Review | null }>('/assistant', {
        prompt: q,
        request_id: reqId
      });
      if (res.answer) {
        setMessages(prev => [...prev, { role: 'assistant', text: res.answer || '', mode: res.mode }]);
      } else if (res.job) {
        // Poll for advice job
        setMessages(prev => [...prev, { role: 'assistant', text: 'Analyzing your workspace context to give you targeted guidance...', mode: res.mode }]);
        const jobId = res.job.id;
        const checkAdvice = async () => {
          try {
            const adv = await request<Review>('/organization/onboarding/reviews/' + jobId);
            if (adv.status === 'READY' && adv.preview?.answer) {
              setMessages(prev => [
                ...prev.slice(0, -1),
                { role: 'assistant', text: adv.preview?.answer || '', mode: 'AI Guidance' }
              ]);
            } else if (['QUEUED', 'RUNNING'].includes(adv.status)) {
              setTimeout(checkAdvice, 2500);
            }
          } catch {
            // Ignore advice poll error
          }
        };
        setTimeout(checkAdvice, 2500);
      }
    } catch (e) {
      setMessages(prev => [...prev, { role: 'assistant', text: 'I couldn’t complete that guidance request right now. Your saved progress is unchanged.' }]);
    } finally {
      setChatPending(false);
    }
  }

  const currentStepNum = ONBOARDING_STEPS.find(s => s.key === view)?.stepNum || 1;

  return (
    <div className="ai-onboarding-shell">
      {/* Top Header & Horizontal Progress Rail */}
      <header className="ai-onboarding-topbar">
        <div className="ai-onboarding-topbar-brand">
          <div className="ai-brand-badge">
            <Sparkles size={14} className="text-primary" />
            <span>PLANEBYTE SETUP</span>
          </div>
          <h1>{view === 'ready' ? 'Your PlaneByte Workspace is Ready' : 'AI-Guided Onboarding'}</h1>
          <p className="text-sm text-muted-foreground">
            {view === 'welcome' && 'Understand your business and offerings.'}
            {view === 'company' && 'Review and approve your AI-generated company profile.'}
            {view === 'icp' && 'Discover 5 tailored ideal customer profiles (ICPs).'}
            {view === 'research' && 'Set up research keywords and signal sources.'}
            {view === 'plan' && 'Choose your Intent Radar plan or start a 3-day free trial.'}
            {view === 'ready' && 'Your research context is saved and ready for live discovery.'}
          </p>
        </div>

        {view !== 'ready' && progress.can_edit && (
          <div className="ai-onboarding-topbar-actions">
            <Button variant="outline" size="sm" disabled={pending} onClick={() => void saveExit()}>
              Save & Exit
            </Button>
          </div>
        )}
      </header>

      {/* 5-Step Unified Progress Rail (Never wraps on desktop) */}
      <nav aria-label="Onboarding Progress" className="ai-onboarding-rail-container">
        <ol className="ai-onboarding-rail">
          {ONBOARDING_STEPS.map((s) => {
            const isCompleted = currentStepNum > s.stepNum || view === 'ready';
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
                    {isCompleted ? <Check size={13} strokeWidth={3} /> : s.stepNum}
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

      {/* Access Guard for Invited Members without Edit Rights */}
      {!progress.can_edit ? (
        <section className="ai-setup-card max-w-2xl mx-auto my-12 text-center p-8">
          <Building2 size={36} className="mx-auto text-muted-foreground mb-4" />
          <h2 className="text-xl font-bold">
            {progress.status === 'COMPLETED' ? 'Your company setup is complete' : 'Your workspace owner is preparing this company'}
          </h2>
          <p className="text-sm text-muted-foreground my-3">
            You can review the company in Settings. Joining a team does not overwrite or restart its onboarding.
          </p>
          <Link href="/settings" className="text-primary underline text-sm inline-flex items-center gap-1 font-medium">
            Open workspace settings →
          </Link>
        </section>
      ) : (
        /* Responsive 2-Column Application Workspace (60-65% Left, 35-40% Right) */
        <div className="ai-onboarding-grid">
          {/* LEFT: Main Workspace */}
          <main className="ai-onboarding-workspace">
            {/* STEP 1: Understand Your Business */}
            {view === 'welcome' && (
              <section className="ai-card p-6 md:p-8 animate-fade-in">
                <div className="ai-card-badge">
                  <Globe size={18} className="text-primary" />
                  <span>STEP 1 · UNDERSTAND YOUR BUSINESS</span>
                </div>
                <h2 className="text-2xl font-bold tracking-tight mt-2 mb-3">Tell us about your company</h2>
                <p className="text-muted-foreground text-sm mb-6 leading-relaxed">
                  Start with your public website URL. PlaneByte will research your public offerings, positioning, and buyer-intent triggers to build your personalized intelligence engine.
                </p>

                <div className="space-y-5">
                  <label className="block text-sm font-semibold text-foreground">
                    Company website
                    <div className="relative mt-2">
                      <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-muted-foreground">
                        <Globe size={16} />
                      </div>
                      <input
                        type="url"
                        placeholder="https://yourcompany.com"
                        value={website}
                        maxLength={600}
                        onChange={e => setWebsite(e.target.value)}
                        className="ai-input pl-10"
                      />
                    </div>
                    <span className="text-xs text-muted-foreground font-normal mt-1.5 block">
                      Enter a public HTTPS address. We inspect up to 5 public pages honoring publisher robots.txt.
                    </span>
                  </label>

                  <label className="block text-sm font-semibold text-foreground">
                    What is your primary research objective?
                    <select
                      value={objective}
                      onChange={e => setObjective(e.target.value)}
                      className="ai-select mt-2"
                    >
                      {OBJECTIVES.map(([key, label, desc]) => (
                        <option value={key} key={key}>
                          {label} — {desc}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>

                <div className="ai-actions mt-8">
                  <Button
                    size="lg"
                    disabled={pending || !website.trim() || !state.capabilities.company_analysis}
                    onClick={() => void analyze()}
                    className="ai-btn-primary"
                  >
                    <Sparkles size={16} className="mr-2" />
                    {pending ? 'Starting website research…' : 'Analyze my business with AI'}
                  </Button>
                  <Button
                    variant="outline"
                    size="lg"
                    disabled={pending}
                    onClick={() => void manualMode()}
                  >
                    Set up manually
                  </Button>
                </div>

                {!state.capabilities.company_analysis && (
                  <div className="ai-notice-box mt-6" role="alert">
                    <AlertCircle size={16} className="text-amber-500 flex-shrink-0" />
                    <p>AI automated website crawling is unavailable in this environment. Manual setup remains fully available.</p>
                  </div>
                )}
              </section>
            )}

            {/* STEP 2: Review AI Business Profile */}
            {view === 'company' && (
              <section className="ai-card p-6 md:p-8 animate-fade-in">
                <div className="ai-card-badge">
                  <Building2 size={18} className="text-primary" />
                  <span>STEP 2 · REVIEW AI BUSINESS PROFILE</span>
                </div>
                <h2 className="text-2xl font-bold tracking-tight mt-2 mb-2">Review your business profile</h2>
                <p className="text-muted-foreground text-sm mb-6 leading-relaxed">
                  Verify the AI-extracted details below. You can accept sections, edit any field, or add offerings. Your saved profile changes only when you approve.
                </p>

                {/* Real-time Review Status Banner if Job is Running */}
                {companyId && (
                  <ReviewStatusCard
                    query={companyReview}
                    onControl={async action => {
                      await request('/organization/website-reviews/' + companyId + '/control', {
                        method: 'POST',
                        body: JSON.stringify({ action })
                      });
                      deadline.current = Date.now() + 120000;
                      await companyReview.refetch();
                    }}
                  />
                )}

                {/* Evidence-Backed Suggestions Proposal Cards */}
                {companyReview.data?.preview?.suggestions && (
                  <div className="space-y-4 my-6">
                    {GROUP_FIELDS.filter(([title, fields]) => !rejected.includes(title) && fields.some(f => f in companyReview.data!.preview!.suggestions!)).map(([title, fields]) => (
                      <article key={title} className="ai-suggestion-box">
                        <div className="ai-suggestion-box-header">
                          <div>
                            <h3 className="font-semibold text-sm text-foreground">{title}</h3>
                            <span className="ai-badge-evidence">
                              <ShieldCheck size={12} className="text-primary mr-1" />
                              Evidence-supported · Review required
                            </span>
                          </div>
                          <div className="flex gap-2">
                            <Button size="sm" variant="outline" onClick={() => apply(fields)}>
                              Accept this section
                            </Button>
                            <button
                              type="button"
                              className="text-xs text-muted-foreground hover:text-foreground underline"
                              onClick={() => rejectSection(title, fields)}
                            >
                              Reject suggestions
                            </button>
                          </div>
                        </div>

                        <div className="ai-suggestion-fields mt-3 space-y-3">
                          {fields.filter(f => f in companyReview.data!.preview!.suggestions!).map(f => (
                            <div key={f} className="text-xs">
                              <strong className="text-muted-foreground uppercase tracking-wider block mb-1">
                                {companyFieldLabels[f]}
                              </strong>
                              <p className="text-foreground bg-muted/40 p-2.5 rounded-lg border border-border/50 whitespace-pre-wrap font-sans">
                                {describe(companyReview.data!.preview!.suggestions![f])}
                              </p>
                              {companyReview.data?.preview?.evidence?.[f]?.map((proof, i) => (
                                <details key={i} className="ai-evidence-details mt-1.5">
                                  <summary className="text-primary text-[11px] cursor-pointer hover:underline">
                                    View quoted evidence
                                  </summary>
                                  <blockquote className="text-xs text-muted-foreground border-l-2 border-primary pl-3 my-2 italic">
                                    "{proof.quote}"
                                  </blockquote>
                                  {proof.url && (
                                    <a
                                      href={proof.url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="text-xs text-primary underline inline-flex items-center gap-1"
                                    >
                                      Open crawled source ↗
                                    </a>
                                  )}
                                </details>
                              ))}
                            </div>
                          ))}
                        </div>
                      </article>
                    ))}
                  </div>
                )}

                {/* Inline Profile Editor */}
                <details className="ai-setup-editor-wrap mt-6 pt-4 border-t border-border" open>
                  <summary className="font-semibold text-sm text-foreground cursor-pointer flex items-center justify-between mb-4">
                    <span>Edit company details and offerings</span>
                    <span className="text-xs text-primary">Toggle fields</span>
                  </summary>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {(['name', 'website', 'industry', 'description', 'positioning'] as const).map(key => {
                      const isWide = key === 'description' || key === 'positioning';
                      const isInvalid = isLowQualityValue(draft[key]);
                      return (
                        <div key={key} className={isWide ? 'md:col-span-2' : ''}>
                          <label className="block text-xs font-semibold text-foreground mb-1.5">
                            {companyFieldLabels[key]}
                          </label>
                          {key === 'description' || key === 'positioning' ? (
                            <textarea
                              aria-label={companyFieldLabels[key]}
                              rows={3}
                              value={draft[key]}
                              maxLength={1000}
                              onChange={e => setDraft(v => ({ ...v, [key]: e.target.value }))}
                              className={`ai-textarea ${isInvalid ? 'border-destructive' : ''}`}
                              placeholder={key === 'description' ? 'Summarize your business and value proposition...' : 'e.g. Buyer-intent intelligence for high-growth B2B teams.'}
                            />
                          ) : (
                            <input
                              aria-label={companyFieldLabels[key]}
                              value={draft[key]}
                              maxLength={key === 'website' ? 600 : 120}
                              onChange={e => setDraft(v => ({ ...v, [key]: e.target.value }))}
                              className={`ai-input ${isInvalid ? 'border-destructive' : ''}`}
                            />
                          )}
                          {isInvalid && (
                            <p className="text-[11px] text-destructive mt-1 flex items-center gap-1">
                              <AlertCircle size={12} /> Please enter a meaningful description (avoid placeholders like 'idk').
                            </p>
                          )}
                        </div>
                      );
                    })}

                    {(['target_customers', 'target_industries', 'countries_served'] as const).map(key => (
                      <div key={key}>
                        <label className="block text-xs font-semibold text-foreground mb-1.5">
                          {companyFieldLabels[key]}
                        </label>
                        <textarea
                          rows={2}
                          value={draft[key].join('\n')}
                          onChange={e => setDraft(v => ({ ...v, [key]: e.target.value.split('\n') }))}
                          className="ai-textarea"
                          placeholder="One per line..."
                        />
                        <span className="text-[10px] text-muted-foreground block mt-1">One per line. Leave empty for global/unrestricted.</span>
                      </div>
                    ))}
                  </div>

                  {/* Products & Services Sub-Section */}
                  <div className="mt-6 pt-4 border-t border-border">
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="font-semibold text-sm text-foreground">Products & Services</h4>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        disabled={draft.products_services.length >= 20}
                        onClick={() => setDraft(v => ({
                          ...v,
                          products_services: [...v.products_services, { name: '', category: 'Software', description: '' }]
                        }))}
                      >
                        <Plus size={14} className="mr-1" /> Add offering
                      </Button>
                    </div>

                    <div className="space-y-3">
                      {draft.products_services.map((offering, i) => (
                        <div key={i} className="ai-offering-row p-3.5 rounded-xl border border-border bg-muted/30">
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                            <div>
                              <label className="block text-[11px] font-medium text-muted-foreground mb-1">Product Name</label>
                              <input
                                value={offering.name}
                                maxLength={120}
                                onChange={e => setDraft(v => ({
                                  ...v,
                                  products_services: v.products_services.map((o, j) => i === j ? { ...o, name: e.target.value } : o)
                                }))}
                                className="ai-input text-xs"
                                placeholder="e.g. Intent Radar"
                              />
                            </div>
                            <div className="md:col-span-2">
                              <label className="block text-[11px] font-medium text-muted-foreground mb-1">What it does</label>
                              <div className="flex gap-2">
                                <input
                                  value={offering.description}
                                  maxLength={1000}
                                  onChange={e => setDraft(v => ({
                                    ...v,
                                    products_services: v.products_services.map((o, j) => i === j ? { ...o, description: e.target.value } : o)
                                  }))}
                                  className="ai-input text-xs flex-1"
                                  placeholder="Brief description of the offering..."
                                />
                                <button
                                  type="button"
                                  className="text-muted-foreground hover:text-destructive p-2 rounded"
                                  onClick={() => setDraft(v => ({
                                    ...v,
                                    products_services: v.products_services.filter((_, j) => j !== i)
                                  }))}
                                  title="Remove offering"
                                >
                                  <X size={15} />
                                </button>
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </details>

                <div className="ai-actions mt-8">
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
                    {pending ? 'Saving profile…' : progress.preferences.setup_mode === 'AI' && state.capabilities.icp_recommendations ? 'Approve profile & discover ideal customers →' : 'Approve company profile'}
                  </Button>
                  <Button variant="ghost" onClick={() => setView('welcome')}>
                    ← Back to website
                  </Button>
                </div>
              </section>
            )}

            {/* STEP 3: Discover Ideal Customers (5 ICP Recommendations) */}
            {view === 'icp' && (
              <section className="ai-card p-6 md:p-8 animate-fade-in">
                <div className="ai-card-badge">
                  <Users2 size={18} className="text-primary" />
                  <span>STEP 3 · DISCOVER IDEAL CUSTOMERS</span>
                </div>
                <h2 className="text-2xl font-bold tracking-tight mt-2 mb-2">Who could benefit from your offering?</h2>
                <p className="text-muted-foreground text-sm mb-6 leading-relaxed">
                  PlaneByte analyzed your business and identified 5 distinct Ideal Customer Profiles (ICPs). Review their buying triggers and select your primary segment.
                </p>

                {icpId && (
                  <ReviewStatusCard
                    query={icpReview}
                    onControl={async action => {
                      await request('/organization/website-reviews/' + icpId + '/control', {
                        method: 'POST',
                        body: JSON.stringify({ action })
                      });
                      deadline.current = Date.now() + 120000;
                      await icpReview.refetch();
                    }}
                  />
                )}

                {!icpId && state.capabilities.icp_recommendations && (
                  <div className="text-center py-8">
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

                {/* 5 Distinct ICP Cards Grid */}
                {candidates.length > 0 && (
                  <div className="space-y-4 my-6">
                    <div className="flex items-center justify-between text-xs text-muted-foreground px-1">
                      <span>Showing {candidates.length} AI-recommended target segments</span>
                      <span>Primary ICP determines research defaults</span>
                    </div>

                    <div className="grid grid-cols-1 gap-4">
                      {candidates.map((cand, i) => {
                        const isSelected = selected.includes(i);
                        const isPrimary = primary === i && isSelected;
                        return (
                          <article
                            key={i}
                            className={`ai-icp-card p-5 rounded-2xl border transition-all ${isPrimary
                              ? 'border-primary ring-2 ring-primary/20 bg-card shadow-sm'
                              : isSelected
                                ? 'border-border bg-card'
                                : 'border-border/60 bg-muted/20 opacity-75'
                              }`}
                          >
                            <div className="flex flex-wrap items-start justify-between gap-3 pb-3 border-b border-border/50">
                              <div className="flex items-center gap-3">
                                <label className="flex items-center gap-2 cursor-pointer">
                                  <input
                                    type="checkbox"
                                    checked={isSelected}
                                    onChange={e => selectCandidate(i, e.target.checked)}
                                    className="ai-checkbox"
                                  />
                                  <span className="font-bold text-base text-foreground">
                                    {cand.draft.name}
                                  </span>
                                </label>
                                {isPrimary && (
                                  <span className="ai-badge-primary">
                                    ★ Primary Target
                                  </span>
                                )}
                              </div>

                              <label className="flex items-center gap-1.5 text-xs text-muted-foreground cursor-pointer hover:text-foreground">
                                <input
                                  type="radio"
                                  name="primary-segment"
                                  disabled={!isSelected}
                                  checked={isPrimary}
                                  onChange={() => setPrimary(i)}
                                  className="ai-radio"
                                />
                                <span>Set as primary ICP</span>
                              </label>
                            </div>

                            <p className="text-xs text-muted-foreground mt-3 leading-relaxed">
                              {cand.reason}
                            </p>

                            {/* Key Targeting Metadata Badges */}
                            <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                              <div>
                                <span className="font-semibold text-muted-foreground block mb-1">Target Roles</span>
                                <div className="flex flex-wrap gap-1.5">
                                  {list(cand.draft.criteria.contact.job_titles).map((role, idx) => (
                                    <span key={idx} className="ai-tag">{role}</span>
                                  ))}
                                </div>
                              </div>

                              <div>
                                <span className="font-semibold text-muted-foreground block mb-1">Company Sizes</span>
                                <div className="flex flex-wrap gap-1.5">
                                  {list(cand.draft.criteria.company.company_sizes).map((sz, idx) => (
                                    <span key={idx} className="ai-tag">{sz} employees</span>
                                  ))}
                                </div>
                              </div>
                            </div>

                            {/* Intent & Pain Points */}
                            <div className="mt-3.5 pt-3 border-t border-border/40 grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                              <div>
                                <span className="font-semibold text-muted-foreground block mb-1">Customer Needs & Pains</span>
                                <ul className="list-disc pl-4 text-muted-foreground space-y-1">
                                  {list(cand.draft.criteria.intent.business_needs).slice(0, 3).map((need, idx) => (
                                    <li key={idx}>{need}</li>
                                  ))}
                                </ul>
                              </div>
                              <div>
                                <span className="font-semibold text-muted-foreground block mb-1">Buying Triggers & Signals</span>
                                <ul className="list-disc pl-4 text-muted-foreground space-y-1">
                                  {list(cand.draft.criteria.intent.buying_signals).slice(0, 3).map((sig, idx) => (
                                    <li key={idx}>{sig}</li>
                                  ))}
                                </ul>
                              </div>
                            </div>

                            {/* Collapsible Edit Details */}
                            <details className="mt-3 text-xs">
                              <summary className="text-primary cursor-pointer hover:underline">
                                Edit targeting criteria & assumptions
                              </summary>
                              <div className="space-y-3 pt-3">
                                <div>
                                  <label className="block text-[11px] font-semibold text-muted-foreground mb-1">Profile Name</label>
                                  <input
                                    value={cand.draft.name}
                                    maxLength={120}
                                    onChange={e => setCandidates(rows => rows.map((v, j) => i === j ? { ...v, draft: { ...v.draft, name: e.target.value } } : v))}
                                    className="ai-input text-xs"
                                  />
                                </div>
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                  {([
                                    ['company', 'industries', 'Industries'],
                                    ['contact', 'job_titles', 'Buyer Roles'],
                                    ['intent', 'business_needs', 'Business Needs'],
                                    ['intent', 'buying_signals', 'Buying Signals']
                                  ] as const).map(([grp, fld, lbl]) => (
                                    <div key={fld}>
                                      <label className="block text-[11px] font-semibold text-muted-foreground mb-1">{lbl}</label>
                                      <textarea
                                        rows={2}
                                        value={describe(cand.draft.criteria[grp][fld])}
                                        onChange={e => candidateField(i, grp, fld, e.target.value)}
                                        className="ai-textarea text-xs"
                                      />
                                    </div>
                                  ))}
                                </div>
                              </div>
                            </details>
                          </article>
                        );
                      })}
                    </div>
                  </div>
                )}

                <div className="ai-actions mt-8">
                  <Button
                    size="lg"
                    disabled={pending || !selected.length || !selected.includes(primary)}
                    onClick={() => void acceptICPs()}
                    className="ai-btn-primary"
                  >
                    Confirm customer profiles & prepare research →
                  </Button>
                  <Button variant="ghost" onClick={() => setView('company')}>
                    ← Back to business profile
                  </Button>
                </div>
              </section>
            )}

            {/* STEP 4: Prepare Your Research */}
            {view === 'research' && (
              <section className="ai-card p-6 md:p-8 animate-fade-in">
                <div className="ai-card-badge">
                  <Target size={18} className="text-primary" />
                  <span>STEP 4 · PREPARE YOUR RESEARCH</span>
                </div>
                <h2 className="text-2xl font-bold tracking-tight mt-2 mb-2">Configure intent discovery defaults</h2>
                <p className="text-muted-foreground text-sm mb-6 leading-relaxed">
                  Review the high-intent keywords and negative exclusion terms suggested by AI from your customer profiles. These will guide your workspace's discovery monitors.
                </p>

                {/* Workspace Context Review Card */}
                <div className="ai-summary-card p-5 rounded-xl border border-border bg-muted/30 mb-6">
                  <h3 className="font-semibold text-xs text-muted-foreground uppercase tracking-wider mb-3">
                    Configured Workspace Summary
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                    <div>
                      <span className="text-muted-foreground block">Company</span>
                      <strong className="text-foreground text-sm">{state.company.name}</strong>
                    </div>
                    <div>
                      <span className="text-muted-foreground block">Offering</span>
                      <strong className="text-foreground text-sm">
                        {state.company.products_services.map(v => v.name).join(', ') || 'Confirmed'}
                      </strong>
                    </div>
                    <div>
                      <span className="text-muted-foreground block">Primary Target ICP</span>
                      <strong className="text-foreground text-sm text-primary">
                        {candidates[primary]?.draft?.name || profiles.data?.items.find(p => p.id === defaultICP)?.name || 'Selected active segment'}
                      </strong>
                    </div>
                  </div>
                </div>

                {/* Keywords Editor */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-foreground mb-1.5">
                      High-intent research terms
                      <span className="text-muted-foreground font-normal block text-[11px] mt-0.5">
                        Phrases indicating active buying intent or problems (up to 12, one per line).
                      </span>
                    </label>
                    <textarea
                      rows={5}
                      value={keywords}
                      onChange={e => setKeywords(e.target.value)}
                      className="ai-textarea"
                      placeholder="e.g. buyer intent tools&#10;lead scoring alternatives&#10;sales intelligence software"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-foreground mb-1.5">
                      Excluded negative terms
                      <span className="text-muted-foreground font-normal block text-[11px] mt-0.5">
                        Terms that filter out irrelevant noise (up to 12, one per line).
                      </span>
                    </label>
                    <textarea
                      rows={5}
                      value={excluded}
                      onChange={e => setExcluded(e.target.value)}
                      className="ai-textarea"
                      placeholder="e.g. free&#10;crack&#10;internship&#10;student"
                    />
                  </div>
                </div>

                {/* Signal Channel Previews */}
                <div className="mt-6 pt-5 border-t border-border">
                  <h4 className="font-semibold text-xs text-muted-foreground uppercase tracking-wider mb-3">
                    Connected Signal Discovery Channels
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div className="p-3 rounded-lg border border-border bg-card flex items-center gap-2.5 text-xs">
                      <MessageSquare size={16} className="text-primary" />
                      <span>Developer & Tech Discussions</span>
                    </div>
                    <div className="p-3 rounded-lg border border-border bg-card flex items-center gap-2.5 text-xs">
                      <Network size={16} className="text-primary" />
                      <span>Professional Q&A Communities</span>
                    </div>
                    <div className="p-3 rounded-lg border border-border bg-card flex items-center gap-2.5 text-xs">
                      <Zap size={16} className="text-primary" />
                      <span>Public Market Feeds</span>
                    </div>
                  </div>
                </div>

                <div className="ai-actions mt-8">
                  <Button
                    size="lg"
                    disabled={pending}
                    onClick={() => setView('plan')}
                    className="ai-btn-primary"
                  >
                    Continue to plan & payment →
                  </Button>
                  <Button variant="ghost" onClick={() => setView('icp')}>
                    ← Back to ideal customers
                  </Button>
                </div>
              </section>
            )}

            {/* STEP 5: Choose Your Plan & Payment (Creem Live Integration) */}
            {view === 'plan' && (
              <section className="ai-card p-6 md:p-8 animate-fade-in">
                <div className="ai-card-badge">
                  <CreditCard size={18} className="text-primary" />
                  <span>STEP 5 · CHOOSE YOUR PLAN & PAYMENT</span>
                </div>
                <h2 className="text-2xl font-bold tracking-tight mt-2 mb-2">Choose your Intent Radar plan</h2>
                <p className="text-muted-foreground text-sm mb-6 leading-relaxed">
                  Start with a 3-Day Free Trial ($0 today) or choose the monthly plan that fits your growth goals. You can upgrade, downgrade, or cancel anytime.
                </p>

                {/* 3-Day Free Trial Callout Banner */}
                <div className="ai-trial-banner p-5 rounded-2xl border border-primary/40 bg-primary/5 flex flex-wrap items-center justify-between gap-4 mb-8">
                  <div>
                    <span className="ai-badge-primary">RECOMMENDED FOR LAUNCH</span>
                    <h3 className="text-lg font-bold text-foreground mt-1">3-Day Free Trial — $0 Charged Today</h3>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Explore live intent signals, background monitoring, and Growth Intelligence immediately. No commitment.
                    </p>
                  </div>
                  <Button
                    size="lg"
                    disabled={pending}
                    onClick={() => void finish()}
                    className="ai-btn-primary whitespace-nowrap"
                  >
                    Start 3-Day Free Trial & Enter Workspace →
                  </Button>
                </div>

                {/* Creem Live Pricing Cards Grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-5 my-6">
                  {/* Starter Tier */}
                  <article className="ai-pricing-card p-5 rounded-2xl border border-border bg-card flex flex-col justify-between">
                    <div>
                      <h4 className="font-bold text-lg text-foreground">Starter</h4>
                      <p className="text-xs text-muted-foreground mt-1">For founders and early teams.</p>
                      <div className="my-4">
                        <span className="text-3xl font-extrabold text-foreground">$59</span>
                        <span className="text-xs text-muted-foreground"> / month</span>
                      </div>
                      <ul className="text-xs text-muted-foreground space-y-2.5">
                        <li className="flex items-center gap-2"><Check size={14} className="text-primary" /> 100 monthly searches</li>
                        <li className="flex items-center gap-2"><Check size={14} className="text-primary" /> 2 background monitors</li>
                        <li className="flex items-center gap-2"><Check size={14} className="text-primary" /> 20 AI intent operations</li>
                        <li className="flex items-center gap-2"><Check size={14} className="text-primary" /> Growth Intelligence</li>
                        <li className="flex items-center gap-2"><Check size={14} className="text-primary" /> 1 workspace member</li>
                      </ul>
                    </div>
                    <Button
                      variant="outline"
                      className="w-full mt-6"
                      disabled={pending}
                      onClick={() => void finish()}
                    >
                      Choose Starter
                    </Button>
                  </article>

                  {/* Growth Tier (Most Popular) */}
                  <article className="ai-pricing-card p-5 rounded-2xl border-2 border-primary bg-card relative shadow-md flex flex-col justify-between">
                    <span className="ai-badge-popular">MOST POPULAR</span>
                    <div>
                      <h4 className="font-bold text-lg text-foreground">Growth</h4>
                      <p className="text-xs text-muted-foreground mt-1">For active growth teams.</p>
                      <div className="my-4">
                        <span className="text-3xl font-extrabold text-foreground">$149</span>
                        <span className="text-xs text-muted-foreground"> / month</span>
                      </div>
                      <ul className="text-xs text-muted-foreground space-y-2.5">
                        <li className="flex items-center gap-2"><Check size={14} className="text-primary" /> 300 monthly searches</li>
                        <li className="flex items-center gap-2"><Check size={14} className="text-primary" /> 5 background monitors</li>
                        <li className="flex items-center gap-2"><Check size={14} className="text-primary" /> 60 AI intent operations</li>
                        <li className="flex items-center gap-2"><Check size={14} className="text-primary" /> Growth Intelligence</li>
                        <li className="flex items-center gap-2"><Check size={14} className="text-primary" /> 3 workspace members</li>
                        <li className="flex items-center gap-2"><Check size={14} className="text-primary" /> Priority discussion context</li>
                      </ul>
                    </div>
                    <Button
                      className="ai-btn-primary w-full mt-6"
                      disabled={pending}
                      onClick={() => void finish()}
                    >
                      Choose Growth
                    </Button>
                  </article>

                  {/* Scale Tier */}
                  <article className="ai-pricing-card p-5 rounded-2xl border border-border bg-card flex flex-col justify-between">
                    <div>
                      <h4 className="font-bold text-lg text-foreground">Scale</h4>
                      <p className="text-xs text-muted-foreground mt-1">High-capacity market intelligence.</p>
                      <div className="my-4">
                        <span className="text-3xl font-extrabold text-foreground">$379</span>
                        <span className="text-xs text-muted-foreground"> / month</span>
                      </div>
                      <ul className="text-xs text-muted-foreground space-y-2.5">
                        <li className="flex items-center gap-2"><Check size={14} className="text-primary" /> 600 monthly searches</li>
                        <li className="flex items-center gap-2"><Check size={14} className="text-primary" /> 10 background monitors</li>
                        <li className="flex items-center gap-2"><Check size={14} className="text-primary" /> 120 AI intent operations</li>
                        <li className="flex items-center gap-2"><Check size={14} className="text-primary" /> Growth Intelligence</li>
                        <li className="flex items-center gap-2"><Check size={14} className="text-primary" /> 5 workspace members</li>
                        <li className="flex items-center gap-2"><Check size={14} className="text-primary" /> Priority scan & support</li>
                      </ul>
                    </div>
                    <Button
                      variant="outline"
                      className="w-full mt-6"
                      disabled={pending}
                      onClick={() => void finish()}
                    >
                      Choose Scale
                    </Button>
                  </article>
                </div>

                {/* Trust, Guarantee, & Legal Compliance */}
                <div className="mt-8 pt-5 border-t border-border flex flex-wrap items-center justify-between gap-4 text-xs text-muted-foreground">
                  <div className="flex items-center gap-2">
                    <ShieldCheck size={16} className="text-primary" />
                    <span>7-Day Money-Back Guarantee on all subscriptions</span>
                  </div>
                  <div>
                    <span>Secure payments via Creem Live · </span>
                    <Link href="/terms#ai-content" className="text-primary underline">
                      Terms of Service (NSFW Prohibited)
                    </Link>
                  </div>
                </div>

                <div className="ai-actions mt-8">
                  <Button
                    size="lg"
                    disabled={pending}
                    onClick={() => void finish()}
                    className="ai-btn-primary"
                  >
                    Finish setup & enter workspace →
                  </Button>
                  <Button variant="ghost" onClick={() => setView('research')}>
                    ← Back to research setup
                  </Button>
                </div>
              </section>
            )}

            {/* STEP 6: Workspace Ready State */}
            {view === 'ready' && (
              <section className="ai-card p-8 text-center animate-fade-in max-w-2xl mx-auto">
                <div className="w-16 h-16 rounded-full bg-primary/10 text-primary mx-auto flex items-center justify-center mb-4">
                  <CheckCircle2 size={36} />
                </div>
                <h2 className="text-2xl font-bold tracking-tight">Your reviewed context is saved</h2>
                <p className="text-muted-foreground text-sm my-3 leading-relaxed">
                  Your company profile, approved ICPs, and research defaults are actively saved in your workspace. You are ready to start discovering buying intent.
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 my-8 text-left">
                  {products.data?.intent_radar?.enabled ? (
                    [
                      [Search, 'Discover Signals', '/intent-radar/discover'],
                      [Radio, 'Set Up Monitor', '/intent-radar/monitors/new'],
                      [Network, 'Intelligence Graph', '/intent-radar/graph']
                    ].map(([Icon, lbl, href]) => {
                      const I = Icon as typeof Search;
                      return (
                        <Link
                          key={href as string}
                          href={href as string}
                          className="p-4 rounded-xl border border-border bg-card hover:border-primary/50 transition-all flex flex-col justify-between"
                        >
                          <I size={22} className="text-primary mb-3" />
                          <div className="flex items-center justify-between">
                            <span className="font-semibold text-sm">{lbl as string}</span>
                            <ArrowRight size={14} className="text-muted-foreground" />
                          </div>
                        </Link>
                      );
                    })
                  ) : (
                    <div className="col-span-3 text-center">
                      <Link href="/settings" className="text-primary underline text-sm font-semibold">
                        Open workspace settings →
                      </Link>
                    </div>
                  )}
                </div>

                <p className="text-xs text-muted-foreground">
                  Product access follows your workspace enrollment. No extra charges are created without your explicit authorization.
                </p>
              </section>
            )}

            {/* Status Notices & Errors */}
            {notice && (
              <div className="ai-notice-box mt-4 animate-fade-in" role="status">
                <Check size={15} className="text-primary flex-shrink-0" />
                <p>{notice}</p>
              </div>
            )}
            {error && (
              <div className="ai-error-box mt-4 animate-fade-in" role="alert">
                <AlertCircle size={15} className="text-destructive flex-shrink-0" />
                <div>
                  <strong>Setup message</strong>
                  <p>{error}</p>
                </div>
              </div>
            )}
          </main>

          {/* RIGHT: Persistent AI Copilot (Sticky 35-40% on Desktop) */}
          <aside className="ai-copilot-container hidden lg:flex">
            <CopilotPanel
              company={state.company}
              currentStep={view}
              messages={messages}
              onAsk={askAssistant}
              pending={chatPending}
              companyReview={companyReview.data}
              icpReview={icpReview.data}
              onPrepareICP={() => void prepareICP(progress.revision)}
              onAnalyze={() => void analyze()}
            />
          </aside>

          {/* Mobile Bottom Dock Button & Slide-over Drawer */}
          <div className="lg:hidden">
            <button
              type="button"
              className="ai-mobile-dock-btn"
              onClick={() => setMobileDrawerOpen(true)}
              aria-label="Open AI Copilot"
            >
              <Sparkles size={16} />
              <span>AI Copilot</span>
              {(companyReview.data?.status === 'RUNNING' || icpReview.data?.status === 'RUNNING') && (
                <span className="ai-status-dot-pulse" />
              )}
            </button>

            {mobileDrawerOpen && (
              <div className="ai-mobile-drawer-backdrop" onClick={() => setMobileDrawerOpen(false)}>
                <div className="ai-mobile-drawer-sheet" onClick={e => e.stopPropagation()}>
                  <div className="ai-mobile-drawer-header">
                    <div className="flex items-center gap-2">
                      <Sparkles size={16} className="text-primary" />
                      <span className="font-bold text-sm">PlaneByte AI Copilot</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => setMobileDrawerOpen(false)}
                      className="p-1 rounded-md text-muted-foreground hover:text-foreground"
                    >
                      <X size={18} />
                    </button>
                  </div>
                  <div className="flex-1 min-h-0 overflow-y-auto p-4">
                    <CopilotPanel
                      company={state.company}
                      currentStep={view}
                      messages={messages}
                      onAsk={askAssistant}
                      pending={chatPending}
                      companyReview={companyReview.data}
                      icpReview={icpReview.data}
                      onPrepareICP={() => void prepareICP(progress.revision)}
                      onAnalyze={() => void analyze()}
                    />
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// Subcomponent: Persistent AI Copilot Panel
function CopilotPanel({
  company,
  currentStep,
  messages,
  onAsk,
  pending,
  companyReview,
  icpReview,
  onPrepareICP,
  onAnalyze
}: {
  company: CompanyProfile;
  currentStep: StepKey;
  messages: { role: 'assistant' | 'user'; text: string; mode?: string }[];
  onAsk: (q: string) => Promise<void>;
  pending: boolean;
  companyReview?: Review;
  icpReview?: Review;
  onPrepareICP: () => void;
  onAnalyze: () => void;
}) {
  const [inputVal, setInputVal] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView?.({ behavior: 'smooth' });
  }, [messages.length]);

  const stepPromptChips: Record<StepKey, string[]> = {
    welcome: [
      'What details will you research from my site?',
      'How does Intent Radar find buying signals?',
      'What if my product is brand new?'
    ],
    company: [
      'Help polish my business description',
      'Suggest more specific product offerings',
      'Make my positioning statement punchier'
    ],
    icp: [
      'Why did you pick these 5 ICPs?',
      'Which segment has the fastest conversion cycle?',
      'How should I prioritize early outreach?'
    ],
    research: [
      'Suggest 5 high-intent buying signals',
      'What negative keywords should I exclude?',
      'How often do discussions update?'
    ],
    plan: [
      'Which plan fits an early stage B2B startup?',
      'How does the 3-day free trial work?',
      'Can I change my plan later?'
    ],
    ready: [
      'Where should I begin researching signals?',
      'How do I create a background monitor?'
    ]
  };

  const chips = stepPromptChips[currentStep] || [];

  return (
    <div className="ai-copilot-inner flex flex-col h-full">
      {/* Copilot Header */}
      <div className="ai-copilot-header p-4 border-b border-border flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
            <Bot size={16} />
          </div>
          <div>
            <h3 className="font-bold text-xs text-foreground">PlaneByte Copilot</h3>
            <span className="text-[10px] text-muted-foreground block">Workspace Intelligence AI</span>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="ai-status-dot" />
          <span className="text-[11px] font-medium text-muted-foreground">
            {companyReview?.status === 'RUNNING' || icpReview?.status === 'RUNNING' ? 'Analyzing' : 'Ready'}
          </span>
        </div>
      </div>

      {/* Active Job Tracker Card */}
      {(companyReview?.status === 'RUNNING' || icpReview?.status === 'RUNNING') && (
        <div className="m-3 p-3 rounded-xl border border-primary/30 bg-primary/5 animate-pulse">
          <div className="flex items-center gap-2 text-xs font-semibold text-primary">
            <Sparkles size={14} className="animate-spin" />
            <span>
              {companyReview?.status === 'RUNNING'
                ? 'Reading public company pages...'
                : 'Generating 5 ideal customer segments...'}
            </span>
          </div>
          <p className="text-[11px] text-muted-foreground mt-1">
            Running through live AI gateway. You can ask questions while this processes.
          </p>
        </div>
      )}

      {/* Workspace Context Snippet */}
      <div className="ai-copilot-context px-4 py-2 bg-muted/30 border-b border-border/50 text-[11px] flex items-center justify-between">
        <span className="text-muted-foreground truncate">
          Context: <strong>{company.name || 'Your Company'}</strong>
        </span>
        <span className="text-primary font-medium capitalize text-[10px]">
          Step {currentStep}
        </span>
      </div>

      {/* Conversation Thread */}
      <div className="ai-copilot-messages flex-1 min-h-0 overflow-y-auto p-4 space-y-3">
        {messages.map((m, idx) => (
          <div
            key={idx}
            className={`ai-message-bubble ${m.role === 'user' ? 'is-user' : 'is-assistant'}`}
          >
            {m.mode && <span className="ai-message-mode">{m.mode}</span>}
            <p className="text-xs leading-relaxed whitespace-pre-wrap">{m.text}</p>
          </div>
        ))}
        {pending && (
          <div className="ai-message-bubble is-assistant animate-pulse">
            <p className="text-xs text-muted-foreground">Thinking and consulting workspace context…</p>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Contextual Quick Prompt Chips */}
      {chips.length > 0 && (
        <div className="ai-copilot-chips px-4 py-2 border-t border-border/50 bg-muted/20 flex flex-wrap gap-1.5">
          {chips.map((chip, idx) => (
            <button
              key={idx}
              type="button"
              className="ai-chip-btn"
              onClick={() => void onAsk(chip)}
            >
              {chip}
            </button>
          ))}
        </div>
      )}

      {/* Copilot Input Form */}
      <form
        onSubmit={e => {
          e.preventDefault();
          if (inputVal.trim()) {
            void onAsk(inputVal);
            setInputVal('');
          }
        }}
        className="ai-copilot-form p-3 border-t border-border flex items-center gap-2"
      >
        <input
          type="text"
          value={inputVal}
          onChange={e => setInputVal(e.target.value)}
          placeholder="Ask Copilot about your business..."
          className="ai-copilot-input flex-1 text-xs"
          disabled={pending}
        />
        <Button
          type="submit"
          size="sm"
          disabled={pending || !inputVal.trim()}
          className="h-8 px-3"
        >
          <Send size={13} />
        </Button>
      </form>
    </div>
  );
}

// Subcomponent: Real-time Review Status Banner
function ReviewStatusCard({
  query,
  onControl
}: {
  query: { data?: Review; error: Error | null; refetch: () => Promise<unknown> };
  onControl: (action: 'CANCEL' | 'RETRY') => Promise<void>;
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

  const isFailed = review?.status === 'FAILED';
  const isRunning = review?.status === 'RUNNING' || review?.status === 'QUEUED';
  const isReady = review?.status === 'READY';

  return (
    <div className={`ai-job-status-card p-4 rounded-xl border mb-6 ${isFailed ? 'border-destructive/40 bg-destructive/5' : isReady ? 'border-primary/40 bg-primary/5' : 'border-border bg-muted/40'}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <Sparkles size={16} className={`flex-shrink-0 ${isRunning ? 'animate-spin text-primary' : isFailed ? 'text-destructive' : 'text-primary'}`} />
          <div>
            <strong className="text-xs font-semibold text-foreground block">
              {query.error
                ? 'Could not refresh analysis'
                : review?.status === 'QUEUED'
                  ? 'Analysis queued...'
                  : isRunning
                    ? review?.progress_stage === 'READING_WEBSITE'
                      ? 'Reading permitted public pages...'
                      : 'Preparing reviewable recommendations...'
                    : isReady
                      ? 'Analysis ready for review'
                      : review?.status === 'CANCELLED'
                        ? 'Analysis cancelled'
                        : 'Analysis did not complete'}
            </strong>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              {isFailed
                ? 'Retry analysis or continue editing manually. Your saved profile is preserved.'
                : isRunning
                  ? 'Running safely via live worker. You can safely reload or return.'
                  : 'Suggestions generated from crawled facts.'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {review?.can_retry && (
            <Button size="sm" variant="outline" disabled={busy} onClick={() => handleControl('RETRY')}>
              Retry
            </Button>
          )}
          {isRunning && (
            <Button size="sm" variant="ghost" disabled={busy} onClick={() => handleControl('CANCEL')}>
              Cancel
            </Button>
          )}
          <button
            type="button"
            className="text-muted-foreground hover:text-foreground p-1"
            onClick={() => void query.refetch()}
            title="Refresh status"
          >
            <RefreshCw size={13} />
          </button>
        </div>
      </div>
      {ctrlErr && <p className="text-xs text-destructive mt-2">{ctrlErr}</p>}
    </div>
  );
}
