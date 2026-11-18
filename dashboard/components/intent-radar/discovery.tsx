"use client";

import { useContext, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { QueryClientContext } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowRight,
  Check,
  ChevronDown,
  ChevronUp,
  Loader2,
  SlidersHorizontal,
  Sparkles,
} from "lucide-react";
import {
  emptyIntentSearch,
  INTENT_CATEGORIES,
  type IntentJob,
  type IntentPreferences,
  type IntentSearch,
  type SearchStrategy,
  type SourceId,
} from "@/lib/intent-radar";
import { Button } from "@/components/ui/button";
import { useUsage, type UsageData } from "@/components/workspaces/usage";
import { useRadarCapabilities, useRadarMutation, useRadarRead } from "./provider";
import { ErrorState, Field, LoadingSkeleton, PageHeading } from "./ui";
import { ChipInput, MonitorWizard } from "./monitors";
import { SourceSelection } from "./advanced-controls";
import { JobPanel } from "./jobs";
import { DiscoverNav } from "./discover/DiscoverNav";
import { SourceConfigDrawer } from "./discover/SourceConfigDrawer";
import { InlineReviewPanel } from "./discover/InlineReviewPanel";
import { InlineResultsPanel } from "./discover/InlineResultsPanel";
import {
  DISCOVERY_PRELOAD_KEY,
  DiscoveryCopilotPanel,
  type CopilotQuickAction,
} from "./discover/DiscoveryCopilotPanel";
import { DiscoveryHistoryView } from "./discover/DiscoveryHistoryView";
import { DiscoveryRunDetailView } from "./discover/DiscoveryRunDetailView";
import { SavedSearchesView } from "./discover/SavedSearchesView";

function UsageReader({ onData }: { onData: (data: UsageData | undefined) => void }) {
  const q = useUsage();
  useEffect(() => {
    onData(q.data);
  }, [q.data, onData]);
  return null;
}

export function SearchFilters({
  value,
  onChange,
  onSuggestKeywords,
  onConfigureSource,
  compactSourceOptions = false,
}: {
  value: IntentSearch;
  onChange: (value: IntentSearch) => void;
  onSuggestKeywords?: () => void;
  onConfigureSource?: (sourceId: SourceId) => void;
  compactSourceOptions?: boolean;
}) {
  const [showAdvanced, setShowAdvanced] = useState(false);
  const icps = useRadarRead<{ items: { id: string; name: string }[] }>("/icps");
  const set = (patch: Partial<IntentSearch>) => onChange({ ...value, ...patch });

  const advancedCount = [
    value.excluded.length > 0,
    value.topics.length > 0,
    value.phrases.length > 0,
    Boolean(value.offerings.trim()),
    Boolean(value.icp_id),
    Boolean(value.from_date || value.to_date),
    value.min_relevance > 0,
    value.result_limit !== 20,
    Boolean(value.semantic),
  ].filter(Boolean).length;

  return (
    <div className="space-y-5">
      {/* 1. Search Terms */}
      <section className="rounded-2xl border border-border bg-card p-5 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <span className="text-[11px] font-semibold uppercase tracking-wider text-primary">
              1 · Search Terms
            </span>
            <h3 className="text-sm font-semibold text-foreground mt-0.5">
              What are you looking for?
            </h3>
          </div>
          <div className="flex items-center gap-2.5">
            {onSuggestKeywords && (
              <button
                type="button"
                onClick={onSuggestKeywords}
                className="inline-flex items-center gap-1 rounded-full border border-primary/35 bg-primary/10 px-2.5 py-1 text-[11px] font-semibold text-primary hover:bg-primary/15 transition-colors cursor-pointer"
              >
                <Sparkles size={11} aria-hidden="true" />
                Suggest keywords
              </button>
            )}
            <span className="text-[11px] text-muted-foreground">
              {value.keywords.length} / 12 keywords
            </span>
          </div>
        </div>

        <ChipInput
          label="Keywords"
          value={value.keywords}
          onChange={(keywords) => set({ keywords })}
        />

        <p className="text-[11px] text-muted-foreground leading-relaxed">
          Enter specific domain terms or short phrases (e.g. “CRM alternative”, “SOC 2 compliance”) and press Enter. Multiple keywords broaden discovery and rank discussions by relevance.
        </p>
      </section>

      {/* 2. Research Sources */}
      <section className="rounded-2xl border border-border bg-card p-5 space-y-3">
        <div>
          <span className="text-[11px] font-semibold uppercase tracking-wider text-primary">
            2 · Research Sources
          </span>
          <h3 className="text-sm font-semibold text-foreground mt-0.5">
            Where should we search?
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            {compactSourceOptions
              ? "Select one or more available sources. Click Configure on any selected source to adjust its options."
              : "Select one or more available sources. Source-specific options appear only for the providers you select."}
          </p>
        </div>

        <SourceSelection
          value={value}
          onChange={onChange}
          showAdvancedOptions={false}
          compactOptions={compactSourceOptions}
          onConfigureSource={onConfigureSource}
        />
      </section>

      {/* 3. Research Intent */}
      <section className="rounded-2xl border border-border bg-card p-5 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <span className="text-[11px] font-semibold uppercase tracking-wider text-primary">
              3 · Research Intent
            </span>
            <h3 className="text-sm font-semibold text-foreground mt-0.5">
              What type of conversations matter?
            </h3>
          </div>
          {value.categories.length > 0 && (
            <button
              type="button"
              onClick={() => set({ categories: [] })}
              className="text-xs font-medium text-primary hover:underline cursor-pointer"
            >
              Include all types
            </button>
          )}
        </div>

        <div className="flex flex-wrap gap-2" role="group" aria-label="Intent categories">
          {INTENT_CATEGORIES.map((category) => {
            const active = value.categories.includes(category);
            return (
              <button
                key={category}
                type="button"
                aria-pressed={active}
                onClick={() =>
                  set({
                    categories: active
                      ? value.categories.filter((c) => c !== category)
                      : [...value.categories, category],
                  })
                }
                className={
                  "inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors cursor-pointer " +
                  (active
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-border bg-card text-foreground hover:border-primary/50")
                }
              >
                {active && <Check size={12} aria-hidden="true" />}
                {category}
              </button>
            );
          })}
        </div>

        <p className="text-[11px] text-muted-foreground">
          {value.categories.length === 0
            ? "All conversation types included. "
            : `${value.categories.length} selected. `}
          Selecting intent categories classifies available evidence — it does not guarantee a post represents an active buyer.
        </p>
      </section>

      {/* Collapsible Advanced Filters */}
      <section className="rounded-2xl border border-border bg-card overflow-hidden">
        <button
          type="button"
          aria-expanded={showAdvanced}
          onClick={() => setShowAdvanced((v) => !v)}
          className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left hover:bg-muted/25 transition-colors cursor-pointer"
        >
          <div className="flex items-center gap-2.5">
            <SlidersHorizontal size={15} className="text-primary shrink-0" aria-hidden="true" />
            <div>
              <span className="text-sm font-semibold text-foreground">
                Advanced Filters
                {advancedCount > 0 && (
                  <span className="ml-2 rounded-full bg-primary/10 px-2 py-0.5 text-[11px] font-semibold text-primary">
                    {advancedCount} active
                  </span>
                )}
              </span>
              <p className="text-xs text-muted-foreground mt-0.5">
                Exclusions, topics, ICP alignment, date window, relevance threshold, result limit, and semantic analysis.
              </p>
            </div>
          </div>
          {showAdvanced ? (
            <ChevronUp size={16} className="text-muted-foreground shrink-0" />
          ) : (
            <ChevronDown size={16} className="text-muted-foreground shrink-0" />
          )}
        </button>

        {showAdvanced && (
          <div className="border-t border-border p-5 space-y-5">
            <div className="grid gap-4 sm:grid-cols-2">
              <ChipInput
                label="Excluded keywords"
                value={value.excluded}
                onChange={(excluded) => set({ excluded })}
              />
              <ChipInput
                label="Topics"
                value={value.topics}
                onChange={(topics) => set({ topics })}
              />
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <ChipInput
                label="Intent phrases"
                value={value.phrases}
                onChange={(phrases) => set({ phrases })}
              />
              <Field label="Relevant offerings" hint="Optional products or services for relevance matching.">
                <input
                  value={value.offerings}
                  maxLength={500}
                  placeholder="e.g. B2B intent monitoring, API security"
                  onChange={(e) => set({ offerings: e.target.value })}
                />
              </Field>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <Field
                label="Ideal Customer Profile (ICP)"
                hint={
                  !value.icp_id
                    ? "No ideal customer profile selected. You can search without one."
                    : "Aligns relevance scoring with your saved workspace ICP."
                }
              >
                <select
                  value={value.icp_id || ""}
                  onChange={(e) => set({ icp_id: e.target.value || null })}
                >
                  <option value="">No ideal customer profile selected</option>
                  {icps.data?.items.map((i) => (
                    <option key={i.id} value={i.id}>
                      {i.name}
                    </option>
                  ))}
                </select>
              </Field>

              <Field
                label="Result limit"
                hint="Maximum matching signals returned (1–20 across selected sources)."
              >
                <input
                  type="number"
                  min={1}
                  max={20}
                  value={value.result_limit}
                  onChange={(e) =>
                    set({ result_limit: Math.min(20, Math.max(1, Number(e.target.value))) })
                  }
                />
              </Field>
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              <Field
                label="Observed from"
                hint="Feed sources narrow retrieved snapshots; Stack Exchange supports native API date filters."
              >
                <input
                  type="date"
                  value={value.from_date || ""}
                  max={value.to_date || undefined}
                  onChange={(e) => set({ from_date: e.target.value || null })}
                />
              </Field>
              <Field label="Observed until">
                <input
                  type="date"
                  min={value.from_date || undefined}
                  value={value.to_date || ""}
                  onChange={(e) => set({ to_date: e.target.value || null })}
                />
              </Field>
              <Field
                label={`Minimum relevance · ${value.min_relevance}/100`}
                hint="Prioritizes results; not a verified purchase probability."
              >
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={value.min_relevance}
                  onChange={(e) => set({ min_relevance: Number(e.target.value) })}
                />
              </Field>
            </div>

            <div className="rounded-xl border border-border/80 bg-muted/15 p-4 space-y-3">
              <label className="inline-flex items-center gap-2 text-xs font-medium text-foreground cursor-pointer">
                <input
                  type="checkbox"
                  checked={!!value.semantic}
                  onChange={(e) => set({ semantic: e.target.checked })}
                  className="accent-primary"
                />
                Include ambiguous intent candidates for human-requested semantic analysis
              </label>
              <p className="text-[11px] text-muted-foreground">
                Requires relevant offerings. Candidates are reviewed separately with grounded evidence.
              </p>

              {value.semantic && (
                <div className="grid gap-3 sm:grid-cols-2 pt-2">
                  <ChipInput
                    label="Positive semantic criteria"
                    value={value.semantic_criteria || []}
                    onChange={(semantic_criteria) => set({ semantic_criteria })}
                  />
                  <ChipInput
                    label="Semantic exclusions"
                    value={value.semantic_exclusions || []}
                    onChange={(semantic_exclusions) => set({ semantic_exclusions })}
                  />
                  <Field label="Max AI ranking candidates (1–10)">
                    <input
                      type="number"
                      min={1}
                      max={10}
                      value={value.semantic_analysis_limit || 3}
                      onChange={(e) =>
                        set({
                          semantic_analysis_limit: Math.max(
                            1,
                            Math.min(10, Number(e.target.value))
                          ),
                        })
                      }
                    />
                  </Field>
                  <Field label="Source language">
                    <select
                      value={value.language}
                      onChange={(e) =>
                        set({ language: e.target.value as IntentSearch["language"] })
                      }
                    >
                      {["Any / unverified", "en", "es", "fr", "de", "pt", "hi", "ja"].map(
                        (language) => (
                          <option key={language}>{language}</option>
                        )
                      )}
                    </select>
                  </Field>
                </div>
              )}
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

export function SearchSummary({ configuration: c }: { configuration: IntentSearch }) {
  const access = useRadarCapabilities();
  const icps = useRadarRead<{ items: { id: string; name: string }[] }>("/icps");
  const sources = c.sources ?? ["hacker_news"];
  const sourceLabels = sources.map(
    (id) => access.data?.sources.find((s) => (s.id || "hacker_news") === id)?.name || id
  );
  const icpName = c.icp_id
    ? icps.data?.items.find((i) => i.id === c.icp_id)?.name || "Selected ICP"
    : "None (searching without an ICP)";

  return (
    <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 text-xs">
      <div className="rounded-xl border border-border/80 bg-muted/20 p-3.5">
        <dt className="text-muted-foreground">Search keywords</dt>
        <dd className="mt-1 flex flex-wrap gap-1.5">
          {c.keywords.length ? (
            c.keywords.map((k) => (
              <span
                key={k}
                className="rounded-md bg-primary/10 px-2 py-0.5 text-[11px] font-medium text-primary"
              >
                {k}
              </span>
            ))
          ) : (
            <span className="text-destructive font-medium">Add at least one keyword</span>
          )}
        </dd>
      </div>
      <div className="rounded-xl border border-border/80 bg-muted/20 p-3.5">
        <dt className="text-muted-foreground">Selected sources ({sourceLabels.length})</dt>
        <dd className="mt-1 font-semibold text-foreground">
          {sourceLabels.length ? sourceLabels.join(", ") : "Select at least one source"}
        </dd>
      </div>
      <div className="rounded-xl border border-border/80 bg-muted/20 p-3.5">
        <dt className="text-muted-foreground">Active ICP</dt>
        <dd className="mt-1 font-medium text-foreground">{icpName}</dd>
      </div>
    </dl>
  );
}

const SUGGESTIONS = [
  [
    "CRM & tool comparisons",
    "Find teams comparing Salesforce vs HubSpot or looking for a lightweight CRM alternative on Hacker News and GitHub.",
  ],
  [
    "Engineering & API pain points",
    "Find developers hitting Stripe webhook timeouts or API rate limit errors on Stack Exchange and GitHub.",
  ],
  [
    "Alternative searches",
    "Find SaaS teams switching away from Datadog to an open-source observability stack.",
  ],
  [
    "Compliance & security",
    "Find startup CTOs asking for recommendations on SOC 2 compliance and endpoint security.",
  ],
] as const;

export function DiscoverExperience({ route = "discover" }: { route?: string }) {
  if (route === "discover/history") return <DiscoveryHistoryView />;
  if (route === "discover/saved") return <SavedSearchesView />;
  if (route.startsWith("discover/runs/")) {
    const runId = route.split("/")[2];
    if (runId) return <DiscoveryRunDetailView id={runId} />;
  }

  const preferences = useRadarRead<IntentPreferences>("/settings");
  if (preferences.error) {
    return (
      <ErrorState
        message={preferences.error.message}
        retry={() => void preferences.refetch()}
      />
    );
  }
  if (!preferences.data) return <LoadingSkeleton />;
  return <DiscoveryWorkspace preferences={preferences.data} />;
}

function DiscoveryWorkspace({ preferences }: { preferences: IntentPreferences }) {
  const [inputMode, setInputMode] = useState<"ai" | "advanced">("advanced");
  const [prompt, setPrompt] = useState("");
  const [draftTitle, setDraftTitle] = useState("");
  const [parentDiscoveryId, setParentDiscoveryId] = useState<string | null>(null);
  const [strategy, setStrategy] = useState<SearchStrategy | null>(null);
  const [config, setConfig] = useState<IntentSearch>(() => ({
    ...emptyIntentSearch(),
    keywords: preferences.discovery_keywords || [],
    excluded: preferences.discovery_excluded || [],
    topics: preferences.topics,
    min_relevance: preferences.min_relevance,
    icp_id: preferences.default_icp_id || null,
  }));
  const [draftInfo, setDraftInfo] = useState<{
    mode: string;
    reason?: string;
    quota_exhausted?: boolean;
    source_warning?: string | null;
  } | null>(null);

  const [reviewOpen, setReviewOpen] = useState(false);
  const [builderCollapsed, setBuilderCollapsed] = useState(false);
  const [configuringSource, setConfiguringSource] = useState<SourceId | null>(null);
  const [mobileCopilotOpen, setMobileCopilotOpen] = useState(false);
  const [copilotTrigger, setCopilotTrigger] = useState<{
    action: CopilotQuickAction;
    message: string;
    nonce: number;
  } | null>(null);

  const [job, setJob] = useState("");
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [finished, setFinished] = useState<IntentJob | null>(null);
  const [wizard, setWizard] = useState(false);
  const [error, setError] = useState("");
  const [quotaError, setQuotaError] = useState("");

  const reviewRef = useRef<HTMLDivElement | null>(null);
  const mutation = useRadarMutation();
  const access = useRadarCapabilities();
  const hasQueryClient = Boolean(useContext(QueryClientContext));
  const [usageData, setUsageData] = useState<UsageData | undefined>(undefined);

  // Recover preloaded criteria (from History / Saved Searches) or URL active run/job on refresh
  useEffect(() => {
    try {
      const raw = sessionStorage.getItem(DISCOVERY_PRELOAD_KEY);
      if (raw) {
        sessionStorage.removeItem(DISCOVERY_PRELOAD_KEY);
        const parsed = JSON.parse(raw) as {
          configuration?: IntentSearch;
          original_prompt?: string;
          strategy?: SearchStrategy | null;
          parent_discovery_id?: string | null;
          title?: string;
        };
        if (parsed.configuration) {
          setConfig(parsed.configuration);
          setReviewOpen(true);
        }
        if (parsed.original_prompt) setPrompt(parsed.original_prompt);
        if (parsed.strategy) setStrategy(parsed.strategy);
        if (parsed.parent_discovery_id) setParentDiscoveryId(parsed.parent_discovery_id);
        if (parsed.title) setDraftTitle(parsed.title);
      }
    } catch {
      // ignore storage errors
    }

    if (typeof window !== "undefined") {
      const sp = new URLSearchParams(window.location.search);
      const urlJob = sp.get("job");
      const urlRun = sp.get("run");
      if (urlJob && urlRun) {
        setJob(urlJob);
        setActiveRunId(urlRun);
        setBuilderCollapsed(true);
      }
    }
  }, []);

  const planSearches = usageData?.usage.find((u) => u.dimension === "plan_searches");
  const planAiCalls = usageData?.usage.find((u) => u.dimension === "plan_ai_calls");
  const searchesExhausted = Boolean(
    planSearches && planSearches.limit > 0 && planSearches.remaining === 0
  );
  const aiExhausted = Boolean(
    planAiCalls && planAiCalls.limit > 0 && planAiCalls.remaining === 0
  );

  const selectedSources = config.sources ?? ["hacker_news"];
  const invalid =
    !config.keywords.length ||
    !selectedSources.length ||
    Boolean(config.from_date && config.to_date && config.from_date > config.to_date);
  const active = Boolean(job && !finished);

  function triggerCopilot(action: CopilotQuickAction, message: string) {
    setCopilotTrigger({ action, message, nonce: Date.now() });
    if (typeof window !== "undefined" && window.innerWidth < 1024) {
      setMobileCopilotOpen(true);
    }
  }

  function openInlineReview() {
    if (invalid) {
      setError(
        "Add at least one keyword, select an available source, and check your date range."
      );
      return;
    }
    setError("");
    setReviewOpen(true);
    setTimeout(() => {
      if (typeof reviewRef.current?.scrollIntoView === "function") {
        reviewRef.current.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    }, 30);
  }

  async function draftWithAi() {
    setError("");
    setQuotaError("");
    try {
      const result = (await mutation.mutateAsync({
        path: "/draft",
        body: {
          prompt,
          previous: draftInfo ? config : null,
          icp_id: config.icp_id || null,
        },
      })) as {
        draft: {
          name?: string;
          configuration: IntentSearch;
          strategy?: SearchStrategy | null;
        };
        mode: string;
        fallback_reason?: string;
        quota_exhausted?: boolean;
        source_warning?: string | null;
      };
      setConfig(result.draft.configuration);
      if (result.draft.name) setDraftTitle(result.draft.name);
      if (result.draft.strategy) setStrategy(result.draft.strategy);
      setDraftInfo({
        mode: result.mode,
        reason: result.fallback_reason,
        quota_exhausted: result.quota_exhausted,
        source_warning: result.source_warning,
      });
      setReviewOpen(true);
      setTimeout(() => {
        if (typeof reviewRef.current?.scrollIntoView === "function") {
          reviewRef.current.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }
      }, 30);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not generate criteria.");
    }
  }

  async function runSearch() {
    if (invalid) {
      setError("Add at least one keyword, select an available source, and check your date range.");
      return;
    }
    setError("");
    setQuotaError("");
    setFinished(null);
    try {
      const result = (await mutation.mutateAsync({
        path: "/discover",
        body: {
          configuration: config,
          request_id: crypto.randomUUID(),
          title: draftTitle || config.keywords.slice(0, 3).join(" · "),
          original_prompt: prompt,
          search_mode: parentDiscoveryId ? "rerun" : inputMode,
          parent_discovery_id: parentDiscoveryId,
          strategy: strategy || null,
        },
      })) as IntentJob;
      setJob(result.id);
      if (result.discovery_id) setActiveRunId(result.discovery_id);
      setBuilderCollapsed(true);

      // Persist active run/job in URL without page reload for refresh recovery
      if (typeof window !== "undefined" && result.discovery_id) {
        const nextUrl = new URL(window.location.href);
        nextUrl.searchParams.set("job", result.id);
        nextUrl.searchParams.set("run", result.discovery_id);
        window.history.replaceState({}, "", nextUrl.toString());
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Discovery could not be started.";
      if (/allowance|exhausted|quota|limit|429/i.test(msg)) {
        setQuotaError(msg);
      } else {
        setError(msg);
      }
    }
  }

  async function saveReusableSearch(name: string, description: string) {
    await mutation.mutateAsync({
      path: "/saved-searches",
      body: {
        name,
        description,
        original_prompt: prompt,
        configuration: config,
      },
    });
  }

  const resultIds = [
    ...new Set(finished?.items.flatMap((item) => item.result?.signals || []) || []),
  ].slice(0, 20);
  const firstResult = finished?.items[0]?.result;

  return (
    <div className="ir-page space-y-5">
      {hasQueryClient && <UsageReader onData={setUsageData} />}

      <PageHeading
        title="Discover Conversations"
        description="Configure, review, run, and refine multi-source discovery inline with your context-aware Copilot."
      />

      <DiscoverNav
        activeTab="new"
        showCopilotButton
        onOpenMobileCopilot={() => setMobileCopilotOpen(true)}
      />

      {/* Two-column Desktop Split (~70% Main Workspace / ~30% Sticky Right Copilot) */}
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px] xl:grid-cols-[minmax(0,1fr)_390px] items-start">
        {/* Main Continuous Workflow Column */}
        <div className="min-w-0 space-y-5">
          {/* Compact Expandable Builder Summary Bar when running/viewing results */}
          {builderCollapsed ? (
            <section className="rounded-2xl border border-border bg-card px-5 py-3.5 flex flex-wrap items-center justify-between gap-3">
              <div className="min-w-0 space-y-1">
                <div className="flex flex-wrap items-center gap-1.5 text-xs">
                  <span className="font-semibold text-foreground">Active Search Criteria:</span>
                  {config.keywords.slice(0, 4).map((k) => (
                    <span
                      key={k}
                      className="rounded-md bg-primary/10 px-2 py-0.5 text-[11px] font-medium text-primary"
                    >
                      {k}
                    </span>
                  ))}
                  {config.keywords.length > 4 && (
                    <span className="text-[11px] text-muted-foreground">
                      +{config.keywords.length - 4} more
                    </span>
                  )}
                </div>
                <p className="text-[11px] text-muted-foreground">
                  Sources: {selectedSources.join(", ")} · Limit: {config.result_limit}
                </p>
              </div>
              <Button
                size="sm"
                variant="outline"
                onClick={() => setBuilderCollapsed(false)}
                className="gap-1.5 text-xs shrink-0"
              >
                <SlidersHorizontal size={13} /> Edit Search Criteria
              </Button>
            </section>
          ) : (
            <>
              {/* Shared-State Mode Switcher (Describe with AI <-> Advanced Search) */}
              <div
                className="inline-flex flex-wrap items-center gap-1.5 rounded-xl border border-border bg-muted/30 p-1"
                role="group"
                aria-label="Search method"
              >
                <button
                  type="button"
                  aria-pressed={inputMode === "ai"}
                  onClick={() => setInputMode("ai")}
                  className={
                    "inline-flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-xs font-semibold transition-colors cursor-pointer " +
                    (inputMode === "ai"
                      ? "bg-card text-foreground shadow-sm border border-border/80"
                      : "text-muted-foreground hover:text-foreground")
                  }
                >
                  <Sparkles size={14} /> Describe with AI
                </button>
                <button
                  type="button"
                  aria-pressed={inputMode === "advanced"}
                  onClick={() => setInputMode("advanced")}
                  className={
                    "inline-flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-xs font-semibold transition-colors cursor-pointer " +
                    (inputMode === "advanced"
                      ? "bg-card text-foreground shadow-sm border border-border/80"
                      : "text-muted-foreground hover:text-foreground")
                  }
                >
                  <SlidersHorizontal size={14} /> Advanced Search
                </button>
              </div>

              {/* Mode 1: Describe with AI */}
              {inputMode === "ai" && (
                <section className="rounded-2xl border border-border bg-card p-5 sm:p-6 space-y-4">
                  <div className="flex items-center justify-between gap-2">
                    <div>
                      <h2 className="text-base font-semibold text-foreground">
                        Describe the conversations you want to find
                      </h2>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        PlaneByte drafts structured search criteria and strategy inline for your review before running any search.
                      </p>
                    </div>
                    <Sparkles size={18} className="text-primary shrink-0" aria-hidden="true" />
                  </div>

                  {aiExhausted && (
                    <div
                      role="status"
                      className="rounded-xl border border-amber-500/35 bg-amber-500/10 p-4 space-y-2.5 text-xs"
                    >
                      <div className="flex items-start gap-2">
                        <AlertTriangle
                          size={15}
                          className="text-amber-600 dark:text-amber-400 shrink-0 mt-0.5"
                          aria-hidden="true"
                        />
                        <div>
                          <p className="font-semibold text-foreground">
                            Shared AI operations allowance exhausted ({planAiCalls?.used}/{planAiCalls?.limit})
                          </p>
                          <p className="text-muted-foreground mt-0.5">
                            AI criteria generation is unavailable until reset or plan upgrade. You can still configure and run manual searches directly.
                          </p>
                        </div>
                      </div>
                      <div className="flex flex-wrap items-center gap-2 pt-0.5">
                        <Button size="sm" variant="outline" onClick={() => setInputMode("advanced")}>
                          Continue with Manual Search
                        </Button>
                        <Link
                          href="/settings?category=billing&tab=overview"
                          className="text-xs font-semibold text-primary hover:underline px-2"
                        >
                          View Billing &amp; Usage →
                        </Link>
                      </div>
                    </div>
                  )}

                  <Field
                    label="What are you looking for?"
                    hint="Mention customer problems, competitors, tools, or specific available sources (e.g. GitHub, Stack Exchange, Hacker News, Bluesky)."
                  >
                    <textarea
                      rows={4}
                      value={prompt}
                      maxLength={2000}
                      onChange={(e) => setPrompt(e.target.value)}
                      placeholder="Find B2B SaaS teams comparing Salesforce vs HubSpot or looking for a lightweight CRM alternative on Hacker News and GitHub."
                      className="w-full rounded-xl border border-border bg-card p-3 text-sm text-foreground"
                    />
                  </Field>

                  <div className="flex flex-wrap gap-2" aria-label="Prompt ideas">
                    {SUGGESTIONS.map(([label, text]) => (
                      <button
                        key={label}
                        type="button"
                        onClick={() => setPrompt(text)}
                        className="rounded-full border border-border bg-muted/25 px-3 py-1 text-xs text-muted-foreground hover:border-primary/50 hover:text-foreground transition-colors cursor-pointer"
                      >
                        {label}
                      </button>
                    ))}
                  </div>

                  <div className="flex flex-wrap items-center gap-3 pt-1">
                    <Button
                      disabled={prompt.trim().length < 10 || mutation.isPending || !access.data?.can_manage}
                      onClick={() => void draftWithAi()}
                      className="gap-1.5"
                    >
                      {mutation.isPending ? (
                        <>
                          <Loader2 size={14} className="animate-spin" /> Preparing criteria…
                        </>
                      ) : (
                        <>
                          <Sparkles size={14} />{" "}
                          {draftInfo ? "Refine Search Criteria" : "Generate Criteria"}
                        </>
                      )}
                    </Button>
                    <Button variant="outline" onClick={() => setInputMode("advanced")}>
                      Switch to Advanced Search
                    </Button>
                  </div>

                  {!access.data?.can_manage && (
                    <p className="text-[11px] text-muted-foreground">
                      AI criteria generation requires an owner or administrator. Advanced Search and Copilot refinement are available to workspace editors.
                    </p>
                  )}
                </section>
              )}

              {/* Mode 2: Simplified 3-Section Advanced Search */}
              {inputMode === "advanced" && (
                <div className="space-y-4">
                  <SearchFilters
                    value={config}
                    onChange={setConfig}
                    compactSourceOptions
                    onConfigureSource={setConfiguringSource}
                    onSuggestKeywords={() =>
                      triggerCopilot(
                        "improve_keywords",
                        prompt.trim()
                          ? `Suggest high-signal keywords for: ${prompt.trim()}`
                          : "Suggest high-signal B2B discovery keywords based on my workspace profile and ICP."
                      )
                    }
                  />

                  <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-border bg-card px-5 py-4">
                    <button
                      type="button"
                      onClick={() => {
                        setConfig(emptyIntentSearch());
                        setDraftInfo(null);
                        setStrategy(null);
                        setParentDiscoveryId(null);
                        setReviewOpen(false);
                        setError("");
                      }}
                      className="text-xs font-medium text-muted-foreground hover:text-foreground cursor-pointer"
                    >
                      Reset filters
                    </button>

                    <div className="flex items-center gap-3">
                      {invalid && (
                        <span className="text-xs text-muted-foreground">
                          {!config.keywords.length
                            ? "Add at least 1 keyword"
                            : !selectedSources.length
                              ? "Select at least 1 source"
                              : "Check date range"}
                        </span>
                      )}
                      <Button onClick={openInlineReview} className="gap-1.5">
                        Review Search <ArrowRight size={15} />
                      </Button>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}

          {/* Top-level validation error (e.g. clicking Review Search with 0 keywords) */}
          {error && !reviewOpen && (
            <div role="alert" className="rounded-xl border border-destructive/40 bg-destructive/10 p-3.5 text-xs text-destructive">
              {error}
            </div>
          )}

          {/* Inline Review Panel (Expands in-place — NEVER navigates away!) */}
          <div ref={reviewRef}>
            {reviewOpen && !builderCollapsed && (
              <InlineReviewPanel
                config={config}
                strategy={strategy}
                draftInfo={draftInfo}
                canWrite={Boolean(access.data?.can_write)}
                invalid={invalid}
                active={active}
                isPending={mutation.isPending}
                searchesExhausted={searchesExhausted}
                planSearches={planSearches}
                quotaError={quotaError}
                error={error}
                onRunDiscovery={() => void runSearch()}
                onEditCriteria={() => {
                  setInputMode("advanced");
                  setBuilderCollapsed(false);
                }}
                onImproveWithCopilot={() =>
                  triggerCopilot(
                    "improve_keywords",
                    "Review my current search draft and suggest sharper keywords, exclusions, or source improvements."
                  )
                }
                onSaveSearch={saveReusableSearch}
                onOpenMonitorWizard={() => setWizard(true)}
              />
            )}
          </div>

          {/* Inline Live Execution Panel */}
          {job && (
            <JobPanel
              id={job}
              onComplete={(doneJob) => {
                setFinished(doneJob);
                if (doneJob.discovery_id && !activeRunId) {
                  setActiveRunId(doneJob.discovery_id);
                }
              }}
            />
          )}

          {/* Inline Results Panel */}
          {finished && (
            <InlineResultsPanel
              discoveryId={activeRunId || finished.discovery_id || null}
              signalIds={resultIds}
              scannedCount={firstResult?.scanned}
              matchedCount={firstResult?.matched ?? resultIds.length}
              coverage={firstResult?.coverage}
              onRefineWithCopilot={() =>
                triggerCopilot(
                  "refine_after_results",
                  "Analyze my latest discovery run and suggest keyword, exclusion, or source refinements to improve relevance."
                )
              }
            />
          )}

          {/* Optional Save as Monitor Wizard */}
          <MonitorWizard
            open={wizard}
            configuration={config}
            onClose={() => setWizard(false)}
          />
        </div>

        {/* Sticky Right Discovery Copilot (~30%) + Mobile Slide-over Drawer */}
        <DiscoveryCopilotPanel
          draft={config}
          originalPrompt={prompt}
          activeRunId={activeRunId}
          aiExhausted={aiExhausted}
          canWrite={Boolean(access.data?.can_write)}
          externalTrigger={copilotTrigger}
          onClearExternalTrigger={() => setCopilotTrigger(null)}
          onApplyDraft={(next) => {
            setConfig(next);
            setError("");
          }}
          onUpdateStrategy={(nextStrategy) => setStrategy(nextStrategy)}
          mobileOpen={mobileCopilotOpen}
          onCloseMobile={() => setMobileCopilotOpen(false)}
        />
      </div>

      {/* Per-Source Configure Drawer */}
      <SourceConfigDrawer
        sourceId={configuringSource}
        value={config}
        onChange={setConfig}
        onClose={() => setConfiguringSource(null)}
      />
    </div>
  );
}
