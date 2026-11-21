'use client';
import React, { useEffect, useRef, useState } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import Link from 'next/link';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertCircle, Building2, Check, Sparkles, X } from 'lucide-react';
import { request } from '@/lib/intelligence';
import { useWorkspace } from './use-workspace';
import { useProducts } from './use-products';
import { Button } from '@/components/ui/button';
import { companyDraft, companyFieldLabels, type CompanyFields, type CompanyProfile } from './company-profile-types';
import type { Candidate } from './icp-suggestions';
import { SubscriptionPayment } from './subscription-payment';
import {
  extractSmartKeywordsFromCandidate,
  list,
  normalizeWebsite,
  OBJECTIVES,
  ONBOARDING_STEPS,
  parseBackendErrors,
  reviewFailure,
  scrollToFirstError,
  terms,
  validateCompanyDraft,
  validateWebsiteField,
  type CopilotMessage,
  type FieldErrors,
  type Progress,
  type ProposedUpdate,
  type Review,
  type SaveStatus,
  type SourceStatus,
  type State,
  type StepKey
} from './onboarding/types';
import { OnboardingHero } from './onboarding/OnboardingHero';
import { Step1Business } from './onboarding/Step1Business';
import { Step2Profile } from './onboarding/Step2Profile';
import { Step3ICPs } from './onboarding/Step3ICPs';
import { Step4Research } from './onboarding/Step4Research';
import { CopilotPanel } from './onboarding/CopilotPanel';
import { OnboardingCompletion } from './onboarding/OnboardingCompletion';
import './onboarding-ai.css';

async function api<T>(path: string, body?: unknown, method = 'POST') {
  return request<T>('/organization/onboarding' + path, {
    method,
    body: body === undefined ? undefined : JSON.stringify(body)
  });
}

function draftStorageKey(orgId?: string | null) {
  return orgId ? `planebyte:onboarding-draft:${orgId}` : '';
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
        <Sparkles className="pb-spin-gentle text-primary" size={24} />
        <p className="text-sm text-muted-foreground">Loading your saved workspace setup…</p>
      </div>
    );
  }
  return <SetupWorkspace key={org} orgId={org} initial={query.data} onRefresh={() => query.refetch()} />;
}

function SetupWorkspace({
  orgId,
  initial,
  onRefresh
}: {
  orgId?: string | null;
  initial: State;
  onRefresh: () => Promise<unknown>;
}) {
  const client = useQueryClient();
  const workspace = useWorkspace();
  const products = useProducts();
  const [state, setState] = useState(initial);

  const initialView = (): StepKey => {
    if (typeof window !== 'undefined') {
      const requested = new URLSearchParams(window.location.search).get('step');
      if (requested && (['welcome', 'company', 'icp', 'research', 'plan'] as const).includes(requested as 'welcome' | 'company' | 'icp' | 'research' | 'plan')) {
        if (initial.progress.status !== 'COMPLETED' || requested === 'plan') {
          return requested as StepKey;
        }
      }
    }
    if (initial.progress.status === 'COMPLETED') {
      return 'ready';
    }
    const s = initial.progress.current_step;
    if (s === 'REVIEW') return 'research';
    if (['ICP', 'PREFERENCES'].includes(s)) return 'icp';
    if (['COMPANY', 'SERVICES'].includes(s) || initial.progress.preferences.company_review_id) return 'company';
    return 'welcome';
  };

  const [view, setView] = useState<StepKey>(initialView);
  const [draft, setDraft] = useState<CompanyFields>(() => {
    const saved = companyDraft(initial.company);
    if (typeof window === 'undefined') return saved;
    try {
      const raw = window.sessionStorage.getItem(draftStorageKey(orgId));
      if (!raw) return saved;
      const parsed = JSON.parse(raw) as { version?: string | null; draft?: Partial<CompanyFields> };
      if (parsed.version === initial.company.version && parsed.draft) {
        return { ...saved, ...parsed.draft };
      }
    } catch {
      // Ignore storage read errors
    }
    return saved;
  });
  const [objective, setObjective] = useState(
    initial.progress.objectives.find(v => OBJECTIVES.some(([id]) => id === v)) || 'UNDERSTAND_CUSTOMER_NEEDS'
  );
  const [website, setWebsite] = useState(() => {
    if (initial.company.website) return initial.company.website;
    if (typeof window === 'undefined') return '';
    try {
      const raw = window.sessionStorage.getItem(draftStorageKey(orgId));
      if (raw) {
        const parsed = JSON.parse(raw) as { website?: string };
        if (parsed.website) return parsed.website;
      }
    } catch {
      // ignore
    }
    return '';
  });

  const [pending, setPending] = useState(false);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>('idle');
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [notice, setNotice] = useState('');
  const [selectedFields, setSelectedFields] = useState<string[]>([]);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [primary, setPrimary] = useState(0);
  const [expandedICP, setExpandedICP] = useState<number | null>(null);
  const [defaultICP, setDefaultICP] = useState(initial.progress.default_icp_id || '');
  const [keywords, setKeywords] = useState(initial.progress.preferences.research_keywords.join('\n'));
  const [excluded, setExcluded] = useState(initial.progress.preferences.excluded_keywords.join('\n'));
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);

  // Track which fields the user manually edited so late AI completions never overwrite manual input
  const manuallyEditedRef = useRef<Set<keyof CompanyFields>>(new Set());

  const [messages, setMessages] = useState<CopilotMessage[]>([
    {
      id: 'welcome-0',
      role: 'assistant',
      step: initialView(),
      text: 'Ask me to draft or refine your company overview, compare ideal customer segments, or suggest buying-intent phrases and exclusions.'
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

  // Persist unsaved draft in sessionStorage per workspace so refresh preserves user edits
  useEffect(() => {
    if (typeof window === 'undefined' || !orgId) return;
    try {
      window.sessionStorage.setItem(
        draftStorageKey(orgId),
        JSON.stringify({ version: state.company.version, website, draft })
      );
    } catch {
      // ignore storage quota
    }
  }, [orgId, state.company.version, website, draft]);

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
                text: 'Guidance is taking longer than expected. Click Refresh or Retry to check the result.',
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
    enabled: view === 'icp' || view === 'research' || view === 'plan' || view === 'ready',
    retry: false
  });

  const dirty = JSON.stringify(draft) !== JSON.stringify(companyDraft(state.company));
  useEffect(() => {
    if (!dirty) return;
    const warn = (e: BeforeUnloadEvent) => e.preventDefault();
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [dirty]);

  // Hydrate draft from READY website analysis — NEVER overwrite manually edited fields!
  useEffect(() => {
    if (companyReview.data?.status === 'READY' && companyReview.data?.preview?.suggestions) {
      const fingerprint = companyReview.data.id + JSON.stringify(companyReview.data.preview.suggestions);
      if (hydratedCompany.current === fingerprint) return;
      hydratedCompany.current = fingerprint;
      const s = companyReview.data.preview.suggestions;
      const edited = manuallyEditedRef.current;
      setDraft(v => ({
        ...v,
        name:
          !edited.has('name') && (!v.name || (!initial.company.version && v.name === initial.company.name))
            ? s.name || v.name
            : v.name,
        website: !edited.has('website') ? v.website || s.website || normalizeWebsite(website) : v.website,
        description: !edited.has('description') ? v.description || s.description || '' : v.description,
        industry: !edited.has('industry') ? v.industry || s.industry || '' : v.industry,
        positioning: !edited.has('positioning') ? v.positioning || s.positioning || '' : v.positioning,
        specialties: !edited.has('specialties') && !v.specialties?.length ? s.specialties || [] : v.specialties,
        target_customers:
          !edited.has('target_customers') && !v.target_customers?.length ? s.target_customers || [] : v.target_customers,
        target_industries:
          !edited.has('target_industries') && !v.target_industries?.length ? s.target_industries || [] : v.target_industries,
        countries_served:
          !edited.has('countries_served') && !v.countries_served?.length ? s.countries_served || [] : v.countries_served,
        products_services:
          !edited.has('products_services') && !v.products_services?.length ? s.products_services || [] : v.products_services
      }));
      setSelectedFields(Object.keys(s));
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
      if (!keywords.trim() && smart.research.length) setKeywords(smart.research.join('\n'));
      if (!excluded.trim() && smart.excluded.length) setExcluded(smart.excluded.join('\n'));
    }
  }, [icpReview.data?.id, icpReview.data?.preview]);

  // Keep single status authoritative: clear any stale progress notice when job reaches terminal state
  useEffect(() => {
    const active = view === 'icp' ? icpReview.data : view === 'company' ? companyReview.data : null;
    if (!active) return;
    if (active.status === 'FAILED' || active.status === 'CANCELLED') {
      setNotice('');
    } else if (active.status === 'READY' && /generating|researching/i.test(notice)) {
      setNotice('');
    }
  }, [view, icpReview.data?.status, companyReview.data?.status, notice]);

  function progressSaved(next: Progress) {
    setState(v => ({ ...v, progress: next }));
    setSaveStatus('saved');
    void client.invalidateQueries({ queryKey: ['company-onboarding'] });
    void client.invalidateQueries({ queryKey: ['onboarding-progress'] });
  }

  function updateDraft(updater: (prev: CompanyFields) => CompanyFields) {
    setDraft(prev => {
      const next = updater(prev);
      (Object.keys(next) as (keyof CompanyFields)[]).forEach(k => {
        if (JSON.stringify(prev[k]) !== JSON.stringify(next[k])) {
          manuallyEditedRef.current.add(k);
        }
      });
      return next;
    });
    setSaveStatus('idle');
  }

  function clearFieldError(field: string) {
    setFieldErrors(prev => {
      if (!(field in prev)) return prev;
      const next = { ...prev };
      delete next[field];
      return next;
    });
  }

  async function perform(work: () => Promise<void>) {
    if (pending) return;
    setPending(true);
    setSaveStatus('saving');
    setError('');
    setNotice('');
    try {
      await work();
    } catch (e) {
      setSaveStatus('error');
      const parsed = parseBackendErrors((e as Error).message || '');
      if (Object.keys(parsed.fieldErrors).length > 0) {
        setFieldErrors(parsed.fieldErrors);
        scrollToFirstError(parsed.fieldErrors);
      }
      if (parsed.formError) setError(parsed.formError);
    } finally {
      setPending(false);
    }
  }

  async function analyze() {
    const websiteErr = validateWebsiteField(website, true);
    if (websiteErr) {
      const errs = { welcome_website: websiteErr };
      setFieldErrors(errs);
      scrollToFirstError(errs);
      return;
    }
    setFieldErrors({});
    const normWebsite = normalizeWebsite(website);
    setWebsite(normWebsite);
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

  async function prepareICP(revision: number, version = state.company.version, fresh = false) {
    setError('');
    const result = await api<{ review: Review; progress: Progress }>('/recommendations', {
      revision,
      request_id: fresh ? crypto.randomUUID() : id('icps:' + version)
    });
    progressSaved(result.progress);
    client.setQueryData(['onboarding-review', result.review.id], result.review);
    deadline.current = Date.now() + 120000;
    setView('icp');
  }

  async function saveCompany() {
    const normalizedDraft: CompanyFields = {
      ...draft,
      website: draft.website.trim() ? normalizeWebsite(draft.website) : ''
    };
    const errs = validateCompanyDraft(normalizedDraft);
    if (Object.keys(errs).length > 0) {
      setFieldErrors(errs);
      scrollToFirstError(errs);
      return;
    }
    setFieldErrors({});

    await perform(async () => {
      const result = await api<{ company: CompanyProfile; progress: Progress }>(
        '/company',
        {
          revision: progress.revision,
          objective,
          profile: {
            ...normalizedDraft,
            ...Object.fromEntries(
              (['countries_served', 'target_customers', 'target_industries', 'specialties'] as const).map(key => [
                key,
                normalizedDraft[key].map(v => v.trim()).filter(Boolean)
              ])
            ),
            version: state.company.version,
            ...(selectedFields.length && companyId ? { review_id: companyId, reviewed_fields: selectedFields } : {})
          }
        },
        'PUT'
      );

      if (typeof window !== 'undefined' && orgId) {
        try {
          window.sessionStorage.removeItem(draftStorageKey(orgId));
        } catch {
          // ignore
        }
      }
      manuallyEditedRef.current.clear();
      setState(v => ({ ...v, company: result.company, progress: result.progress }));
      setDraft(companyDraft(result.company));
      setSaveStatus('saved');
      client.setQueryData(['organization-profile'], result.company);
      void client.invalidateQueries({ queryKey: ['intelligence-graph'] });
      setView('icp');
      setNotice('Business profile saved.');

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
      setError('Select at least one customer segment to continue.');
      return;
    }
    if (!selected.includes(primary)) {
      setError('Mark one of your included segments as the Primary ICP.');
      return;
    }

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
      setNotice('Ideal customers saved.');
    });
  }

  async function finish(primaryId?: string) {
    const targetId = primaryId || defaultICP;
    if (!targetId) {
      setError('Choose a primary customer profile before continuing.');
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
      setSaveStatus('saved');
      if (state.payment?.required) {
        setNotice(
          state.payment.active
            ? 'Research setup saved. Your verified subscription is already active.'
            : 'Research setup saved. Choose your trial or plan below to activate Intent Radar.'
        );
        setView('plan');
      } else {
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

  async function skipOnboarding() {
    await perform(async () => {
      // Save any valid progress first without fabricating completion
      const { status, can_edit, ...values } = progress;
      void status;
      void can_edit;
      try {
        await api<Progress>(
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
      } catch {
        // Proceed with skip even if partial fields were unchanged
      }
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

  function applyProposedUpdate(msgId: string, updateIndex: number, upd: ProposedUpdate) {
    const asList = Array.isArray(upd.value) ? upd.value.map(v => v.trim()).filter(Boolean) : terms(String(upd.value));
    const asText = Array.isArray(upd.value) ? upd.value.join('\n') : String(upd.value).trim();

    if (upd.target === 'description' || upd.target === 'positioning' || upd.target === 'industry') {
      updateDraft(v => ({ ...v, [upd.target]: asText }));
      clearFieldError(upd.target);
      setNotice(`Applied AI suggestion to ${companyFieldLabels[upd.target]}.`);
    } else if (
      upd.target === 'specialties' ||
      upd.target === 'target_customers' ||
      upd.target === 'target_industries' ||
      upd.target === 'countries_served'
    ) {
      const listKey = upd.target;
      updateDraft(v => ({
        ...v,
        [listKey]: upd.mode === 'append' ? Array.from(new Set([...v[listKey].filter(Boolean), ...asList])) : asList
      }));
      setNotice(`Applied AI suggestion to ${companyFieldLabels[listKey]}.`);
    } else if (upd.target === 'research_keywords') {
      setKeywords(prev =>
        (upd.mode === 'append' ? Array.from(new Set([...terms(prev), ...asList])) : asList).slice(0, 12).join('\n')
      );
      setNotice('Applied AI suggestion to buying-intent research terms.');
    } else if (upd.target === 'excluded_keywords') {
      setExcluded(prev =>
        (upd.mode === 'append' ? Array.from(new Set([...terms(prev), ...asList])) : asList).slice(0, 12).join('\n')
      );
      setNotice('Applied AI suggestion to excluded terms.');
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

  function discardProposedUpdate(msgId: string, updateIndex: number) {
    const key = `${msgId}:${updateIndex}`;
    setMessages(prev =>
      prev.map(m => (m.id === msgId ? { ...m, discardedKeys: [...(m.discardedKeys || []), key] } : m))
    );
  }

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
  const liveSources: SourceStatus[] = state.sources?.length
    ? state.sources
    : [
        { id: 'hacker_news', name: 'Hacker News', state: 'Connected and checked', category: 'Public discussion', coverage: 'Official public API for Ask HN, Show HN, and developer discussions.' },
        { id: 'stack_exchange', name: 'Stack Exchange', state: 'Available to configure', category: 'Public Q&A', coverage: 'Public engineering and technology Q&A sites.' },
        { id: 'github', name: 'GitHub', state: 'Permission required', category: 'Developer ecosystem', coverage: 'Public issues, discussions, and optional OAuth repository signals.' },
        { id: 'bluesky', name: 'Bluesky', state: 'Available to configure', category: 'Public social', coverage: 'Public social posts and live stream discussions.' },
        { id: 'discourse', name: 'Discourse Forums', state: 'Available to configure', category: 'Community', coverage: 'Approved public developer and industry community feeds.' },
        { id: 'rss', name: 'Atom / RSS Feeds', state: 'Available to configure', category: 'Publications', coverage: 'Approved publication, research, and engineering feeds.' }
      ];

  const hasVerifiedAccess = !!(products.data?.intent_radar?.enabled || (state.payment?.required && state.payment?.active));
  const primaryICPName =
    candidates[primary]?.draft?.name ||
    profiles.data?.items.find(p => p.id === defaultICP)?.name ||
    '';

  return (
    <div className="ai-onboarding-shell">
      {view !== 'ready' && (
        <OnboardingHero
          view={view}
          currentStepNum={currentStepNum}
          canEdit={progress.can_edit}
          pending={pending}
          saveStatus={saveStatus}
          onSelectStep={next => {
            if(progress.status==='COMPLETED')return;
            setFieldErrors({});
            setError('');
            setView(next);
          }}
          onSkip={() => void skipOnboarding()}
        />
      )}

      {!progress.can_edit ? (
        <section className="ai-card max-w-2xl mx-auto my-12 text-center p-8 space-y-3">
          <Building2 size={32} className="mx-auto text-muted-foreground" aria-hidden="true" />
          <h2 className="text-xl font-semibold">
            {progress.status === 'COMPLETED' ? 'Your company setup is complete' : 'Your workspace owner is preparing this company'}
          </h2>
          <p className="text-sm text-muted-foreground">
            You can review company details in Settings. Joining a team never overwrites or restarts setup.
          </p>
          <Link href="/settings" className="text-primary underline text-sm inline-flex items-center gap-1 font-medium">
            Open workspace settings →
          </Link>
        </section>
      ) : view === 'ready' ? (
          <OnboardingCompletion
          hasVerifiedAccess={hasVerifiedAccess}
          companyName={state.company.name}
          primaryICPName={primaryICPName}
          researchTermCount={terms(keywords).length || state.progress.preferences.research_keywords.length || 0}
          paymentActive={Boolean(state.payment?.active)}
          contract={state.payment?.contract}
        />
      ) : (
        <div className={view==='plan'?'mx-auto w-full max-w-5xl':'ai-onboarding-grid'}>
          <div className="ai-onboarding-workspace">
            {view === 'welcome' && (
              <Step1Business
                website={website}
                objective={objective}
                pending={pending}
                canAnalyze={state.capabilities.company_analysis}
                fieldErrors={fieldErrors}
                onWebsiteChange={val => {
                  clearFieldError('welcome_website');
                  clearFieldError('website');
                  setWebsite(val);
                }}
                onWebsiteBlur={err => {
                  if (err) setFieldErrors(prev => ({ ...prev, welcome_website: err }));
                  else clearFieldError('welcome_website');
                }}
                onObjectiveChange={setObjective}
                onAnalyze={() => void analyze()}
                onManual={() => void manualMode()}
              />
            )}

            {view === 'company' && (
              <Step2Profile
                draft={draft}
                companyId={companyId}
                companyReview={companyReview}
                pending={pending}
                chatPending={chatPending}
                fieldErrors={fieldErrors}
                onDraftChange={updateDraft}
                onFieldBlur={(field, err) => {
                  if (err) setFieldErrors(prev => ({ ...prev, [field]: err }));
                  else clearFieldError(field);
                }}
                onClearError={clearFieldError}
                onControlReview={action => controlReview('company', action)}
                onAskCopilot={prompt => void askAssistant(prompt)}
                onSave={() => void saveCompany()}
                onBack={() => {
                  setFieldErrors({});
                  setView('welcome');
                }}
              />
            )}

            {view === 'icp' && (
              <Step3ICPs
                icpId={icpId}
                icpReview={icpReview}
                canGenerate={state.capabilities.icp_recommendations}
                candidates={candidates}
                selected={selected}
                primary={primary}
                expandedICP={expandedICP}
                savedProfiles={profiles.data?.items || []}
                defaultICP={defaultICP}
                pending={pending}
                chatPending={chatPending}
                onControlReview={action => controlReview('icp', action)}
                onGenerateFresh={async () => perform(() => prepareICP(progress.revision, state.company.version, true))}
                onSelectCandidate={selectCandidate}
                onSetPrimary={setPrimary}
                onToggleExpand={i => setExpandedICP(expandedICP === i ? null : i)}
                onCandidateNameChange={(i, name) =>
                  setCandidates(rows => rows.map((v, j) => (i === j ? { ...v, draft: { ...v.draft, name } } : v)))
                }
                onCandidateFieldChange={candidateField}
                onGenerateTriggers={i => {
                  setPrimary(i);
                  const cand = candidates[i];
                  const roles = list(cand.draft.criteria.contact.job_titles);
                  void askAssistant(
                    `Generate 3 to 4 concrete buying triggers for the ICP "${cand.draft.name}" (${roles.join(', ')}).`
                  );
                }}
                onManualCreated={created => {
                  setDefaultICP(created.id);
                  void client.invalidateQueries({ queryKey: ['setup-icps'] });
                }}
                onSelectManualDefault={setDefaultICP}
                onAccept={() => void acceptICPs()}
                onContinueManual={() => setView('research')}
                onBack={() => setView('company')}
              />
            )}

            {view === 'research' && (
              <Step4Research
                companyName={state.company.name}
                mainOffering={state.company.products_services.map(v => v.name).join(', ')}
                primaryICPName={primaryICPName}
                keywords={keywords}
                excluded={excluded}
                sources={liveSources}
                pending={pending}
                chatPending={chatPending}
                onKeywordsChange={setKeywords}
                onExcludedChange={setExcluded}
                onAskCopilot={prompt => void askAssistant(prompt)}
                onSave={() => void finish()}
                onBack={() => setView('icp')}
              />
            )}

            {view === 'plan' && (
              <section className="min-w-0 px-1 py-2 sm:px-4" aria-label="Plan and Payment">
                <SubscriptionPayment
                  orgId={orgId||''}
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

            {notice && (
              <div className="ai-notice-box mt-4" role="status">
                <Check size={15} className="text-primary flex-shrink-0" aria-hidden="true" />
                <p>{notice}</p>
              </div>
            )}
            {error && (
              <div className="ai-error-box mt-4" role="alert">
                <AlertCircle size={15} className="text-destructive flex-shrink-0 mt-0.5" aria-hidden="true" />
                <p className="text-xs">{error}</p>
              </div>
            )}
          </div>

          {/* Desktop Persistent Sticky Copilot Column (30-35%, 330-390px) */}
          {view!=='plan'&&<><aside className="ai-copilot-container hidden lg:flex" aria-label="PlaneByte Copilot">
            <CopilotPanel
              companyName={draft.name || state.company.name}
              currentStep={view}
              messages={messages}
              onAsk={askAssistant}
              onApplyUpdate={applyProposedUpdate}
              onDiscardUpdate={discardProposedUpdate}
              pending={chatPending}
              adviceReview={adviceReview.data}
              onRefreshAdvice={() => void adviceReview.refetch()}
              onRetryAdvice={() => void retryAdvice()}
              companyReview={companyReview.data}
              icpReview={icpReview.data}
            />
          </aside>

          {/* Mobile & Tablet Accessible Copilot Drawer */}
          <div className="lg:hidden">
            <button
              type="button"
              className="ai-mobile-dock-btn"
              onClick={() => setMobileDrawerOpen(true)}
              aria-label="Open AI Copilot"
            >
              <Sparkles size={15} aria-hidden="true" />
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
                      <Sparkles size={15} className="text-primary" aria-hidden="true" />
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
                      onDiscardUpdate={discardProposedUpdate}
                      pending={chatPending}
                      adviceReview={adviceReview.data}
                      onRefreshAdvice={() => void adviceReview.refetch()}
                      onRetryAdvice={() => void retryAdvice()}
                      companyReview={companyReview.data}
                      icpReview={icpReview.data}
                    />
                  </div>
                </Dialog.Content>
              </Dialog.Portal>
            </Dialog.Root>
          </div></>}
        </div>
      )}
    </div>
  );
}
