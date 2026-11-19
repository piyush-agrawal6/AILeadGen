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
  type IntentCategory,
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
import { DISCOVERY_PRELOAD_KEY } from "./discover/DiscoveryCopilotPanel";
import { DiscoveryHistoryView } from "./discover/DiscoveryHistoryView";
import { DiscoveryRunDetailView } from "./discover/DiscoveryRunDetailView";
import { SavedSearchesView } from "./discover/SavedSearchesView";
import { DiscoverMainPage } from "./discover/DiscoverMainPage";
import { CreateDiscoveryPage } from "./discover/CreateDiscoveryPage";

function UsageReader({ onData }: { onData: (data: UsageData | undefined) => void }) {
  const q = useUsage();
  useEffect(() => {
    onData(q.data);
  }, [q.data, onData]);
  return null;
}

const PRIMARY_INTENT_PRESETS: { label: string; category: IntentCategory }[] = [
  { label: "Purchasing Intent", category: "Purchase consideration" },
  { label: "Vendor Comparison", category: "Product comparison" },
  { label: "Technical Evaluation", category: "Tool / service evaluation" },
  { label: "Dissatisfaction / Churn Risk", category: "Problem / pain point" },
  { label: "General Discussion", category: "General discussion" },
];

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
    <div className="space-y-4">
      {/* 1. Search Terms: Keywords, Suggestions, and Negative Exclusions */}
      <section className="rounded-2xl border border-border bg-card p-5 space-y-4 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <span className="text-[11px] font-semibold uppercase tracking-wider text-primary">
              1 · Search Terms
            </span>
            <h3 className="text-sm font-semibold text-foreground mt-0.5">
              What conversations are you looking for?
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
          label="Primary Search Keywords"
          aliasLabel="Add Keywords"
          value={value.keywords}
          onChange={(keywords) => set({ keywords })}
        />

        <p className="text-[11px] text-muted-foreground leading-relaxed">
          Enter target domain terms, product categories, or tool names (e.g. “CRM alternative”, “SOC 2 compliance”) and press Enter.
        </p>

        {/* Negative Keywords / Exclusions directly accessible */}
        <div className="pt-2 border-t border-border/70">
          <ChipInput
            label="Negative Keywords (Exclusions)"
            value={value.excluded}
            onChange={(excluded) => set({ excluded })}
          />
          <p className="text-[11px] text-muted-foreground mt-1">
            Filter out noise, tutorials, job openings, or irrelevant topics (e.g. “internship”, “homework”, “free tier”).
          </p>
        </div>
      </section>

      {/* 2. Research Sources */}
      <section className="rounded-2xl border border-border bg-card p-5 space-y-3 shadow-sm">
        <div>
          <span className="text-[11px] font-semibold uppercase tracking-wider text-primary">
            2 · Research Sources
          </span>
          <h3 className="text-sm font-semibold text-foreground mt-0.5">
            Where should we search?
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            {compactSourceOptions
              ? "Select authorized sources to scan. Click Configure to customize per-source parameters."
              : "Select one or more available sources. Options appear only for enabled providers."}
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

      {/* 3. Search Intent */}
      <section className="rounded-2xl border border-border bg-card p-5 space-y-3 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <span className="text-[11px] font-semibold uppercase tracking-wider text-primary">
              3 · Search Intent
            </span>
            <h3 className="text-sm font-semibold text-foreground mt-0.5">
              What type of discussions matter?
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
          {PRIMARY_INTENT_PRESETS.map((preset) => {
            const active = value.categories.includes(preset.category);
            return (
              <button
                key={preset.label}
                type="button"
                aria-pressed={active}
                onClick={() =>
                  set({
                    categories: active
                      ? value.categories.filter((c) => c !== preset.category)
                      : [...value.categories, preset.category],
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
                {preset.label}
              </button>
            );
          })}
        </div>

        <p className="text-[11px] text-muted-foreground">
          {value.categories.length === 0
            ? "All intent types included. "
            : `${value.categories.length} selected. `}
          Intent classification ranks discussions by commercial signals and technical evaluation.
        </p>
      </section>

      {/* 4. Collapsible Advanced Filters */}
      <section className="rounded-2xl border border-border bg-card overflow-hidden shadow-sm">
        <button
          type="button"
          aria-expanded={showAdvanced}
          onClick={() => setShowAdvanced((v) => !v)}
          style={{ justifyContent: "space-between" }}
          className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left hover:bg-muted/25 transition-colors cursor-pointer"
        >
          <div className="flex items-center gap-2.5">
            <SlidersHorizontal size={15} className="text-primary shrink-0" aria-hidden="true" />
            <div>
              <span className="text-sm font-semibold text-foreground">
                4 · Advanced Filters
                {advancedCount > 0 && (
                  <span className="ml-2 rounded-full bg-primary/10 px-2 py-0.5 text-[11px] font-semibold text-primary">
                    {advancedCount} active
                  </span>
                )}
              </span>
              <p className="text-xs text-muted-foreground mt-0.5">
                Date window, minimum relevance score, result limit, ICP alignment, and semantic analysis.
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
              <Field
                label="Ideal Customer Profile (ICP)"
                hint={
                  !value.icp_id
                    ? "No profile selected (broad market search)."
                    : "Aligns relevance scoring with your saved workspace ICP."
                }
              >
                <select
                  value={value.icp_id || ""}
                  onChange={(e) => set({ icp_id: e.target.value || null })}
                  className="w-full rounded-lg border border-border bg-background px-3 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  <option value="">No ICP selected (broad discovery)</option>
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
                  className="w-full rounded-lg border border-border bg-background px-3 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </Field>
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              <Field label="Observed from" hint="Optional start date.">
                <input
                  type="date"
                  value={value.from_date || ""}
                  max={value.to_date || undefined}
                  onChange={(e) => set({ from_date: e.target.value || null })}
                  className="w-full rounded-lg border border-border bg-background px-3 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </Field>
              <Field label="Observed until" hint="Optional end date.">
                <input
                  type="date"
                  min={value.from_date || undefined}
                  value={value.to_date || ""}
                  onChange={(e) => set({ to_date: e.target.value || null })}
                  className="w-full rounded-lg border border-border bg-background px-3 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </Field>
              <Field
                label={`Minimum relevance · ${value.min_relevance}/100`}
                hint="Filter out lower-scoring conversation matches."
              >
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={value.min_relevance}
                  onChange={(e) => set({ min_relevance: Number(e.target.value) })}
                  className="w-full mt-2 accent-primary"
                />
              </Field>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <ChipInput
                label="Topics"
                value={value.topics}
                onChange={(topics) => set({ topics })}
              />
              <Field label="Source language">
                <select
                  value={value.language}
                  onChange={(e) =>
                    set({ language: e.target.value as IntentSearch["language"] })
                  }
                  className="w-full rounded-lg border border-border bg-background px-3 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  {["Any / unverified", "en", "es", "fr", "de", "pt", "hi", "ja"].map(
                    (language) => (
                      <option key={language}>{language}</option>
                    )
                  )}
                </select>
              </Field>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

const SUGGESTIONS = [
  "Find engineering leaders evaluating AI code review tools",
  "Track discussions comparing PostgreSQL vs ClickHouse for analytics",
  "Identify SaaS founders migrating from AWS to GCP",
  "Discover teams actively hiring senior Elixir engineers",
] as const;

function NewDiscoveryLoader() {
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

export function DiscoverExperience({ route = "discover" }: { route?: string }) {
  if (route === "discover/new") return <CreateDiscoveryPage />;
  if (route === "discover/saved") return <DiscoverMainPage initialTab="saved" />;
  if (route === "discover/history") return <DiscoverMainPage initialTab="history" />;
  if (route.startsWith("discover/runs/")) {
    const runId = route.split("/")[2];
    if (runId) return <DiscoveryRunDetailView id={runId} />;
  }
  return <DiscoverMainPage initialTab="history" />;
}

function DiscoveryWorkspace({ preferences }: { preferences: IntentPreferences }) {
  const [userChoseMode, setUserChoseMode] = useState(false);
  const [inputMode, setInputMode] = useState<"ai" | "advanced">("ai");
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

  // Refinement history stack for Undo and Reset
  const [originalConfig, setOriginalConfig] = useState<IntentSearch | null>(null);
  const [historyStack, setHistoryStack] = useState<IntentSearch[]>([]);
  const [diffSummary, setDiffSummary] = useState<string | null>(null);

  const [reviewOpen, setReviewOpen] = useState(false);
  const [builderCollapsed, setBuilderCollapsed] = useState(false);
  const [configuringSource, setConfiguringSource] = useState<SourceId | null>(null);

  const [job, setJob] = useState("");
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [finished, setFinished] = useState<IntentJob | null>(null);
  const [wizard, setWizard] = useState(false);
  const [error, setError] = useState("");
  const [quotaError, setQuotaError] = useState("");

  const reviewRef = useRef<HTMLDivElement | null>(null);
  const mutation = useRadarMutation();
  const access = useRadarCapabilities();
  const icps = useRadarRead<{ items: { id: string; name: string }[] }>("/icps");
  const hasQueryClient = Boolean(useContext(QueryClientContext));
  const [usageData, setUsageData] = useState<UsageData | undefined>(undefined);

  // Recover preloaded criteria from History / Saved Searches / URL params
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
          setOriginalConfig(parsed.configuration);
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

  const planSearches = usageData?.usage?.find((u) => u.dimension === "plan_searches");
  const planAiCalls = usageData?.usage?.find((u) => u.dimension === "plan_ai_calls");
  const searchesExhausted = Boolean(
    planSearches && planSearches.limit > 0 && planSearches.remaining === 0
  );
  const aiExhausted = Boolean(
    planAiCalls && planAiCalls.limit > 0 && planAiCalls.remaining === 0
  );

  useEffect(() => {
    if (!userChoseMode && aiExhausted) {
      setInputMode("advanced");
    }
  }, [userChoseMode, aiExhausted]);

  const selectedSources = config.sources ?? ["hacker_news"];
  const invalid =
    !config.keywords.length ||
    !selectedSources.length ||
    Boolean(config.from_date && config.to_date && config.from_date > config.to_date);
  const active = Boolean(job && !finished);

  async function draftWithAi() {
    if (!prompt.trim()) return;
    setError("");
    setQuotaError("");
    setDiffSummary(null);
    try {
      const result = (await mutation.mutateAsync({
        path: "/draft",
        body: {
          prompt: prompt.trim(),
          previous: null,
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

      const newConfig = result.draft.configuration;
      setConfig(newConfig);
      setOriginalConfig(newConfig);
      setHistoryStack([]);
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
      }, 50);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not generate criteria.");
    }
  }

  async function handleRefinePrompt(refinementText: string) {
    if (!refinementText.trim()) return;
    setError("");
    setQuotaError("");
    try {
      // Save current state into undo stack
      setHistoryStack((prev) => [...prev, config]);

      const result = (await mutation.mutateAsync({
        path: "/draft",
        body: {
          prompt: refinementText.trim(),
          previous: config,
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

      const nextConfig = result.draft.configuration;
      setConfig(nextConfig);
      if (result.draft.strategy) setStrategy(result.draft.strategy);
      setDiffSummary(`Refined: applied changes based on “${refinementText.trim()}”.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not refine criteria.");
    }
  }

  function handleUndo() {
    if (!historyStack.length) return;
    const prev = historyStack[historyStack.length - 1];
    setHistoryStack((h) => h.slice(0, -1));
    setConfig(prev);
    setDiffSummary("Reverted to previous strategy criteria.");
  }

  function handleResetOriginal() {
    if (!originalConfig) return;
    setHistoryStack((prev) => [...prev, config]);
    setConfig(originalConfig);
    setDiffSummary("Reset to initial AI-generated criteria.");
  }

  function openInlineReview() {
    if (invalid) {
      setError("Add at least one keyword, select an available source, and check your date range.");
      return;
    }
    setError("");
    setReviewOpen(true);
    setTimeout(() => {
      if (typeof reviewRef.current?.scrollIntoView === "function") {
        reviewRef.current.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    }, 50);
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
        description="Configure, review, run, and refine multi-source discovery across verified developer and community sources."
      />

      <DiscoverNav activeTab="new" />

      {/* Main Single-Column Clean Unified Workspace */}
      <div className="min-w-0 space-y-5">
        {/* Compact Builder Summary Bar when running or viewing results */}
        {builderCollapsed ? (
          <section className="rounded-2xl border border-border bg-card px-5 py-3.5 flex flex-wrap items-center justify-between gap-3 shadow-sm">
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
            {/* Mode Switcher: AI Discovery (Primary/Recommended) vs Advanced Search */}
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <div
                className="inline-flex items-center gap-1.5 rounded-xl border border-border bg-muted/30 p-1"
                role="group"
                aria-label="Discovery mode"
              >
                <button
                  type="button"
                  aria-label="AI Discovery · Describe with AI"
                  aria-pressed={inputMode === "ai"}
                  onClick={() => setInputMode("ai")}
                  className={
                    "inline-flex items-center gap-1.5 rounded-lg px-4 py-2 text-xs font-semibold transition-colors cursor-pointer " +
                    (inputMode === "ai"
                      ? "bg-card text-foreground shadow-sm border border-border/80"
                      : "text-muted-foreground hover:text-foreground")
                  }
                >
                  <Sparkles size={14} className="text-primary" />
                  <span>AI Discovery</span>
                  <span className="ml-1 rounded-full bg-primary/10 px-1.5 py-0.5 text-[10px] font-semibold text-primary">
                    Recommended
                  </span>
                </button>
                <button
                  type="button"
                  aria-label="Advanced Search"
                  aria-pressed={inputMode === "advanced"}
                  onClick={() => setInputMode("advanced")}
                  className={
                    "inline-flex items-center gap-1.5 rounded-lg px-4 py-2 text-xs font-semibold transition-colors cursor-pointer " +
                    (inputMode === "advanced"
                      ? "bg-card text-foreground shadow-sm border border-border/80"
                      : "text-muted-foreground hover:text-foreground")
                  }
                >
                  <SlidersHorizontal size={14} />
                  <span>Advanced Search</span>
                </button>
              </div>

              {inputMode === "ai" && reviewOpen && (
                <button
                  type="button"
                  onClick={() => {
                    setReviewOpen(false);
                    setDraftInfo(null);
                    setStrategy(null);
                    setPrompt("");
                  }}
                  className="text-xs font-medium text-muted-foreground hover:text-foreground cursor-pointer"
                >
                  Start New Prompt
                </button>
              )}
            </div>

            {/* Mode 1: Hero AI Discovery Experience */}
            {inputMode === "ai" && (
              <div className="space-y-5">
                {/* Clean Prompt Input Hero Card (Visible when starting or refining) */}
                <section className="rounded-2xl border border-border bg-card p-5 sm:p-6 space-y-4 shadow-sm">
                  <div className="flex items-center justify-between gap-2">
                    <div>
                      <h2 className="text-base font-semibold text-foreground">
                        What would you like to discover?
                      </h2>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        Describe what you are looking for in natural language. PlaneByte analyzes your search objective, company profile, and ICP to formulate keywords, sources, and noise exclusions.
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
                            AI criteria generation is unavailable until monthly reset. You can still use Advanced Search directly.
                          </p>
                        </div>
                      </div>
                      <div className="flex flex-wrap items-center gap-2 pt-0.5">
                        <Button size="sm" variant="outline" onClick={() => setInputMode("advanced")}>
                          Continue with Advanced Search
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

                  <div className="space-y-2">
                    <textarea
                      rows={3}
                      value={prompt}
                      maxLength={2000}
                      aria-label="What are you looking for?"
                      onChange={(e) => setPrompt(e.target.value)}
                      placeholder="e.g. Find engineering leaders evaluating AI code review tools or comparing GitHub Copilot vs alternatives on Hacker News and GitHub…"
                      className="w-full rounded-xl border border-border bg-background p-3.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary leading-relaxed"
                    />

                    {/* Clickable suggestion chips below input */}
                    <div className="flex flex-wrap items-center gap-1.5 pt-1" aria-label="Example discovery prompts">
                      <span className="text-[11px] font-medium text-muted-foreground mr-1">Examples:</span>
                      {SUGGESTIONS.map((text) => (
                        <button
                          key={text}
                          type="button"
                          onClick={() => setPrompt(text)}
                          className="rounded-full border border-border bg-muted/25 px-2.5 py-1 text-[11px] text-muted-foreground hover:border-primary/50 hover:text-foreground transition-colors cursor-pointer"
                        >
                          {text}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* ICP Alignment Selector (Optional Context) */}
                  {(icps.data?.items.length || 0) > 0 && (
                    <div className="flex flex-wrap items-center gap-3 pt-1">
                      <label className="text-xs font-medium text-muted-foreground">
                        Target ICP:
                      </label>
                      <select
                        value={config.icp_id || ""}
                        onChange={(e) => setConfig((prev) => ({ ...prev, icp_id: e.target.value || null }))}
                        className="rounded-lg border border-border bg-background px-2.5 py-1 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                      >
                        <option value="">All / Broad Market (No ICP constraint)</option>
                        {icps.data?.items.map((icp) => (
                          <option key={icp.id} value={icp.id}>
                            {icp.name}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}

                  <div className="flex flex-wrap items-center gap-3 pt-2 border-t border-border/70">
                    <Button
                      size="default"
                      aria-label="Build Discovery · Generate Criteria"
                      disabled={prompt.trim().length < 5 || mutation.isPending || !access.data?.can_manage}
                      onClick={() => void draftWithAi()}
                      className="gap-2 font-semibold"
                    >
                      {mutation.isPending ? (
                        <>
                          <Loader2 size={15} className="animate-spin" /> Building discovery strategy…
                        </>
                      ) : (
                        <>
                          <Sparkles size={15} /> Build Discovery
                        </>
                      )}
                    </Button>
                    <Button variant="outline" onClick={() => setInputMode("advanced")} className="text-xs">
                      Switch to Advanced Search
                    </Button>
                  </div>

                  {!access.data?.can_manage && (
                    <p className="text-[11px] text-muted-foreground">
                      AI discovery formulation requires workspace owner or administrator role.
                    </p>
                  )}
                </section>
              </div>
            )}

            {/* Mode 2: Simplified 4-Section Advanced Search */}
            {inputMode === "advanced" && (
              <div className="space-y-4">
                <SearchFilters
                  value={config}
                  onChange={setConfig}
                  compactSourceOptions
                  onConfigureSource={setConfiguringSource}
                  onSuggestKeywords={() => {
                    setInputMode("ai");
                    setPrompt(
                      config.keywords.length
                        ? `Find discussions related to: ${config.keywords.join(", ")}`
                        : "Find high-signal B2B conversations based on our workspace profile."
                    );
                  }}
                />

                <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-border bg-card px-5 py-4 shadow-sm">
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
                    <Button
                      onClick={openInlineReview}
                      aria-label="Review Discovery"
                      className="gap-1.5"
                    >
                      Review Discovery <ArrowRight size={15} />
                    </Button>
                    <button
                      type="button"
                      onClick={openInlineReview}
                      aria-label="Review Search"
                      className="sr-only"
                    >
                      Review Search
                    </button>
                  </div>
                </div>
              </div>
            )}
          </>
        )}

        {/* Top-level validation error */}
        {error && !reviewOpen && (
          <div role="alert" className="rounded-xl border border-destructive/40 bg-destructive/10 p-3.5 text-xs text-destructive">
            {error}
          </div>
        )}

        {/* Discovery Strategy Review Card (Unified, editable, embedded natural language refine, prominent Run) */}
        <div ref={reviewRef}>
          {reviewOpen && !builderCollapsed && (
            <InlineReviewPanel
              config={config}
              onChangeConfig={setConfig}
              strategy={strategy}
              draftInfo={draftInfo}
              originalPrompt={prompt}
              canWrite={Boolean(access.data?.can_write)}
              invalid={invalid}
              active={active}
              isPending={mutation.isPending}
              searchesExhausted={searchesExhausted}
              planSearches={planSearches}
              quotaError={quotaError}
              error={error}
              onRunDiscovery={() => void runSearch()}
              onEditInAdvanced={() => {
                setInputMode("advanced");
                setBuilderCollapsed(false);
              }}
              onRefinePrompt={handleRefinePrompt}
              onResetOriginal={handleResetOriginal}
              onUndo={handleUndo}
              canUndo={historyStack.length > 0}
              diffSummary={diffSummary}
              onSaveSearch={saveReusableSearch}
              onOpenMonitorWizard={() => setWizard(true)}
            />
          )}
        </div>

        {/* Inline Live Execution Job Panel */}
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

        {/* Inline Results Table matching standard schema */}
        {finished && (
          <InlineResultsPanel
            discoveryId={activeRunId || finished.discovery_id || null}
            signalIds={resultIds}
            scannedCount={firstResult?.scanned}
            matchedCount={firstResult?.matched ?? resultIds.length}
            coverage={firstResult?.coverage}
            onRefineWithCopilot={() => {
              setBuilderCollapsed(false);
              setReviewOpen(true);
            }}
          />
        )}

        {/* Save as Monitor Wizard Modal */}
        <MonitorWizard
          open={wizard}
          configuration={config}
          onClose={() => setWizard(false)}
        />
      </div>

      {/* Per-Source Configuration Drawer */}
      <SourceConfigDrawer
        sourceId={configuringSource}
        value={config}
        onChange={setConfig}
        onClose={() => setConfiguringSource(null)}
      />
    </div>
  );
}
