"use client";

import { useContext, useEffect, useState } from "react";
import Link from "next/link";
import { QueryClientContext } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowRight,
  Bookmark,
  Check,
  ChevronDown,
  ChevronUp,
  Info,
  Loader2,
  Radio,
  Search,
  SlidersHorizontal,
  Sparkles,
} from "lucide-react";
import {
  emptyIntentSearch,
  INTENT_CATEGORIES,
  type IntentJob,
  type IntentPreferences,
  type IntentSearch,
  type IntentSignal,
  type SourceId,
} from "@/lib/intent-radar";
import { Button } from "@/components/ui/button";
import { useUsage, type UsageData } from "@/components/workspaces/usage";
import { useRadarCapabilities, useRadarMutation, useRadarRead } from "./provider";
import { Badge, EmptyState, ErrorState, Field, LoadingSkeleton, PageHeading } from "./ui";
import { ChipInput, MonitorWizard } from "./monitors";
import { SourceSelection } from "./advanced-controls";
import { JobPanel } from "./jobs";
import { SignalCard } from "./signals";

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
}: {
  value: IntentSearch;
  onChange: (value: IntentSearch) => void;
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
    <div className="space-y-6">
      {/* Decision 1: What are you looking for? */}
      <section className="rounded-2xl border border-border bg-card p-5 space-y-3">
        <div className="flex items-center justify-between gap-2">
          <div>
            <span className="text-[11px] font-semibold uppercase tracking-wider text-primary">
              1 · Search Terms
            </span>
            <h3 className="text-sm font-semibold text-foreground mt-0.5">
              What are you looking for?
            </h3>
          </div>
          <span className="text-[11px] text-muted-foreground">
            {value.keywords.length} / 12 keywords
          </span>
        </div>

        <ChipInput
          label="Keywords"
          value={value.keywords}
          onChange={(keywords) => set({ keywords })}
        />

        <p className="text-[11px] text-muted-foreground leading-relaxed">
          Type a keyword or short phrase and press Enter (or separate with commas). Discussions matching your keywords are scored and ranked by relevance — multiple keywords broaden discovery rather than requiring every term to appear in the same post.
        </p>
      </section>

      {/* Decision 2: Where should we search? */}
      <section className="rounded-2xl border border-border bg-card p-5 space-y-3">
        <div>
          <span className="text-[11px] font-semibold uppercase tracking-wider text-primary">
            2 · Research Sources
          </span>
          <h3 className="text-sm font-semibold text-foreground mt-0.5">
            Where should we search?
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            Select one or more available sources. Source-specific options appear only for the providers you select.
          </p>
        </div>

        <SourceSelection value={value} onChange={onChange} showAdvancedOptions={false} />
      </section>

      {/* Decision 3: What type of conversations matter? */}
      <section className="rounded-2xl border border-border bg-card p-5 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <span className="text-[11px] font-semibold uppercase tracking-wider text-primary">
              3 · Intent Type
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
          Selecting intent categories filters or classifies available evidence — it does not guarantee that a post represents a real buyer.
        </p>
      </section>

      {/* Expandable Advanced Filters */}
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
    <div className="space-y-4">
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
          <dt className="text-muted-foreground">Intent categories</dt>
          <dd className="mt-1 font-medium text-foreground">
            {c.categories.length ? c.categories.join(", ") : "All conversation categories"}
          </dd>
        </div>

        <div className="rounded-xl border border-border/80 bg-muted/20 p-3.5">
          <dt className="text-muted-foreground">Exclusions</dt>
          <dd className="mt-1 font-medium text-foreground">
            {c.excluded.length ? c.excluded.join(", ") : "None"}
          </dd>
        </div>

        <div className="rounded-xl border border-border/80 bg-muted/20 p-3.5">
          <dt className="text-muted-foreground">Date window &amp; limit</dt>
          <dd className="mt-1 font-medium text-foreground">
            {c.from_date || "Any date"} → {c.to_date || "Latest"} · up to {c.result_limit} results
            {c.min_relevance > 0 ? ` (≥ ${c.min_relevance}/100)` : ""}
          </dd>
        </div>

        <div className="rounded-xl border border-border/80 bg-muted/20 p-3.5">
          <dt className="text-muted-foreground">Active ICP</dt>
          <dd className="mt-1 font-medium text-foreground">{icpName}</dd>
        </div>
      </dl>

      <details className="rounded-xl border border-border/80 bg-muted/15 px-4 py-3 text-xs">
        <summary className="font-medium text-foreground cursor-pointer">
          Source coverage &amp; search limitations
        </summary>
        <div className="mt-2.5 space-y-1.5 text-muted-foreground">
          {access.data?.sources
            .filter((s) => sources.includes((s.id || "hacker_news") as SourceId))
            .map((s) => (
              <p key={s.name}>
                <strong className="text-foreground">{s.name}:</strong> {s.coverage} (up to{" "}
                {s.request_limit_per_check || 22} requests per check).
              </p>
            ))}
          <p>
            One manual check consumes 1 search allowance. Saving a monitor stores criteria without executing a one-time search.
          </p>
        </div>
      </details>
    </div>
  );
}

function SearchResult({ id }: { id: string }) {
  const query = useRadarRead<IntentSignal>("/signals/" + id);
  return query.error ? (
    <ErrorState message={query.error.message} />
  ) : query.data ? (
    <SignalCard signal={query.data} />
  ) : (
    <LoadingSkeleton />
  );
}

const SUGGESTIONS = [
  [
    "Tool & vendor comparisons",
    "Find founders comparing CRM or analytics tools on GitHub and Hacker News.",
  ],
  [
    "Engineering pain points",
    "Find engineering teams discussing CI/CD bottlenecks and deployment failures on Stack Exchange.",
  ],
  [
    "Alternative searches",
    "Find SaaS teams looking for alternatives to expensive observability platforms.",
  ],
  [
    "Technical recommendations",
    "Find startup CTOs asking for recommendations on API security and SOC 2 compliance.",
  ],
] as const;

export function DiscoverExperience() {
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
  return <DiscoveryForm preferences={preferences.data} />;
}

function DiscoveryForm({ preferences }: { preferences: IntentPreferences }) {
  const [mode, setMode] = useState<"ai" | "advanced" | "review">("advanced");
  const [prompt, setPrompt] = useState("");
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
  const [job, setJob] = useState("");
  const [finished, setFinished] = useState<IntentJob | null>(null);
  const [wizard, setWizard] = useState(false);
  const [error, setError] = useState("");
  const [quotaError, setQuotaError] = useState("");

  const mutation = useRadarMutation();
  const access = useRadarCapabilities();
  const hasQueryClient = Boolean(useContext(QueryClientContext));
  const [usageData, setUsageData] = useState<UsageData | undefined>(undefined);

  const planSearches = usageData?.usage.find((u) => u.dimension === "plan_searches");
  const planAiCalls = usageData?.usage.find((u) => u.dimension === "plan_ai_calls");
  const searchesExhausted = Boolean(planSearches && planSearches.limit > 0 && planSearches.remaining === 0);
  const aiExhausted = Boolean(planAiCalls && planAiCalls.limit > 0 && planAiCalls.remaining === 0);

  const selectedSources = config.sources ?? ["hacker_news"];
  const invalid =
    !config.keywords.length ||
    !selectedSources.length ||
    Boolean(config.from_date && config.to_date && config.from_date > config.to_date);
  const active = Boolean(job && !finished);

  async function draft() {
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
        draft: { configuration: IntentSearch };
        mode: string;
        fallback_reason?: string;
        quota_exhausted?: boolean;
        source_warning?: string | null;
      };
      setConfig(result.draft.configuration);
      setDraftInfo({
        mode: result.mode,
        reason: result.fallback_reason,
        quota_exhausted: result.quota_exhausted,
        source_warning: result.source_warning,
      });
      setMode("review");
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
        body: { configuration: config, request_id: crypto.randomUUID() },
      })) as IntentJob;
      setJob(result.id);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Discovery could not be started.";
      if (/allowance|exhausted|quota|limit|429/i.test(msg)) {
        setQuotaError(msg);
      } else {
        setError(msg);
      }
    }
  }

  const ids = [
    ...new Set(finished?.items.flatMap((item) => item.result?.signals || []) || []),
  ].slice(0, 20);

  return (
    <div className="ir-page space-y-6">
      {hasQueryClient && <UsageReader onData={setUsageData} />}
      <PageHeading
        title="Discover Conversations"
        description="Find relevant discussions across your approved research sources."
      />

      {/* Mode Switcher */}
      <div
        className="inline-flex flex-wrap items-center gap-1.5 rounded-xl border border-border bg-muted/30 p-1"
        role="group"
        aria-label="Search method"
      >
        <button
          type="button"
          aria-pressed={mode === "ai"}
          onClick={() => setMode("ai")}
          className={
            "inline-flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-xs font-semibold transition-colors cursor-pointer " +
            (mode === "ai"
              ? "bg-card text-foreground shadow-sm border border-border/80"
              : "text-muted-foreground hover:text-foreground")
          }
        >
          <Sparkles size={14} /> Describe with AI
        </button>
        <button
          type="button"
          aria-pressed={mode === "advanced"}
          onClick={() => setMode("advanced")}
          className={
            "inline-flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-xs font-semibold transition-colors cursor-pointer " +
            (mode === "advanced"
              ? "bg-card text-foreground shadow-sm border border-border/80"
              : "text-muted-foreground hover:text-foreground")
          }
        >
          <SlidersHorizontal size={14} /> Advanced Search
        </button>
        {mode === "review" && (
          <button
            type="button"
            aria-pressed
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3.5 py-2 text-xs font-semibold text-primary-foreground"
          >
            <Check size={14} /> Review Search
          </button>
        )}
      </div>

      {/* Mode 1: Describe with AI */}
      {mode === "ai" && (
        <div className="grid gap-5 lg:grid-cols-3">
          <section className="lg:col-span-2 rounded-2xl border border-border bg-card p-6 space-y-4">
            <div className="flex items-center justify-between gap-2">
              <div>
                <h2 className="text-base font-semibold text-foreground">
                  Describe the conversations you want to find
                </h2>
                <p className="text-xs text-muted-foreground mt-0.5">
                  PlaneByte drafts structured search criteria for your review before running any search.
                </p>
              </div>
              <Sparkles size={18} className="text-primary shrink-0" aria-hidden="true" />
            </div>

            {/* Upfront AI Allowance Exhausted Warning */}
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
                      AI criteria generation is unavailable until your allowance resets or your plan upgrades. You can still configure and run manual searches directly.
                    </p>
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-2 pt-0.5">
                  <Button size="sm" variant="outline" onClick={() => setMode("advanced")}>
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
              hint="Mention customer problems, tools, or specific available sources (e.g., GitHub, Stack Exchange, YouTube, Bluesky)."
            >
              <textarea
                rows={4}
                value={prompt}
                maxLength={2000}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Find SaaS founders discussing migration away from legacy analytics tools on GitHub and Hacker News."
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
                onClick={() => void draft()}
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
              <Button variant="outline" onClick={() => setMode("advanced")}>
                Continue with Manual Search
              </Button>
            </div>

            {!access.data?.can_manage && (
              <p className="text-[11px] text-muted-foreground">
                AI criteria generation requires an owner or administrator. Advanced Search is available to all workspace editors.
              </p>
            )}
          </section>

          <aside className="rounded-2xl border border-border bg-card p-5 space-y-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <Radio size={20} aria-hidden="true" />
            </div>
            <div className="space-y-1.5">
              <h3 className="text-sm font-semibold text-foreground">
                AI draft and search execution are separate
              </h3>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Generating criteria uses 1 shared AI operation. Running the search itself uses 1 monthly search allowance — nothing is searched until you review and confirm.
              </p>
            </div>
            <div className="rounded-xl bg-muted/30 p-3 text-xs space-y-1">
              <p className="font-medium text-foreground">Explicit fallback protection</p>
              <p className="text-[11px] text-muted-foreground">
                If AI drafting is unavailable or exhausted, PlaneByte shows a clearly labeled manual fallback and preserves your requested sources without silently switching them.
              </p>
            </div>
          </aside>
        </div>
      )}

      {/* Mode 2: Guided Advanced Search */}
      {mode === "advanced" && (
        <div className="space-y-5">
          <SearchFilters value={config} onChange={setConfig} />

          <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-border bg-card px-5 py-4">
            <button
              type="button"
              onClick={() => {
                setConfig(emptyIntentSearch());
                setDraftInfo(null);
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
                onClick={() => {
                  if (invalid) {
                    setError(
                      "Add at least one keyword, select an available source, and check your date range."
                    );
                  } else {
                    setError("");
                    setMode("review");
                  }
                }}
                className="gap-1.5"
              >
                Review Search <ArrowRight size={15} />
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Mode 3: Review & Run */}
      {mode === "review" && (
        <section className="rounded-2xl border border-border bg-card p-6 space-y-5">
          <div className="flex flex-wrap items-start justify-between gap-3 border-b border-border pb-4">
            <div>
              <h2 className="text-base font-semibold text-foreground">Review Search Criteria</h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                Confirm your keywords, sources, and filters before running a bounded discovery check.
              </p>
            </div>
            <Button variant="outline" size="sm" onClick={() => setMode("advanced")}>
              Edit Search
            </Button>
          </div>

          {/* Explicit AI or Fallback Notice */}
          {draftInfo && (
            <div
              role="status"
              className={
                "rounded-xl border p-4 text-xs space-y-2 " +
                (draftInfo.mode === "Manual fallback"
                  ? "border-amber-500/35 bg-amber-500/10"
                  : "border-primary/25 bg-primary/5")
              }
            >
              <div className="flex items-start gap-2">
                {draftInfo.mode === "Manual fallback" ? (
                  <AlertTriangle
                    size={15}
                    className="text-amber-600 dark:text-amber-400 shrink-0 mt-0.5"
                    aria-hidden="true"
                  />
                ) : (
                  <Sparkles size={15} className="text-primary shrink-0 mt-0.5" aria-hidden="true" />
                )}
                <div className="space-y-1">
                  <p className="font-semibold text-foreground">
                    {draftInfo.mode === "Manual fallback"
                      ? "Manual Fallback Criteria (AI did not generate this draft)"
                      : "AI-Assisted Draft Criteria"}
                  </p>
                  <p className="text-muted-foreground">
                    {draftInfo.reason ||
                      "Review these editable criteria before running your search."}
                  </p>
                  {draftInfo.quota_exhausted && (
                    <Link
                      href="/settings?category=billing&tab=overview"
                      className="inline-block font-semibold text-primary hover:underline pt-0.5"
                    >
                      Review AI allowance in Billing &amp; Usage →
                    </Link>
                  )}
                </div>
              </div>
            </div>
          )}

          <SearchSummary configuration={config} />

          {/* Quota Visibility Before Execution */}
          {planSearches && (
            <div
              className={
                "flex flex-wrap items-center justify-between gap-3 rounded-xl border px-4 py-3 text-xs " +
                (searchesExhausted
                  ? "border-destructive/30 bg-destructive/5 text-destructive"
                  : "border-border bg-muted/20 text-muted-foreground")
              }
            >
              <span className="inline-flex items-center gap-2">
                {searchesExhausted ? (
                  <AlertTriangle size={14} aria-hidden="true" />
                ) : (
                  <Info size={14} aria-hidden="true" />
                )}
                {searchesExhausted ? (
                  <span>
                    <strong>Monthly search allowance exhausted</strong> ({planSearches.used}/
                    {planSearches.limit} used). This check will be blocked until reset or upgrade.
                  </span>
                ) : (
                  <span>
                    Estimated quota impact: <strong>1 monthly search</strong> ({planSearches.remaining}{" "}
                    of {planSearches.limit} remaining).
                  </span>
                )}
              </span>
              <Link
                href="/settings?category=billing&tab=overview"
                className="font-semibold text-primary hover:underline shrink-0"
              >
                Billing &amp; Usage
              </Link>
            </div>
          )}

          <div className="flex flex-wrap items-center gap-3 pt-1">
            <Button
              disabled={invalid || mutation.isPending || active || !access.data?.can_write}
              onClick={() => void runSearch()}
              className="gap-1.5"
            >
              {mutation.isPending ? (
                <>
                  <Loader2 size={14} className="animate-spin" /> Starting search…
                </>
              ) : (
                <>
                  <Search size={14} /> Run Search
                </>
              )}
            </Button>

            <Button
              variant="outline"
              disabled={invalid || !access.data?.can_write || mutation.isPending}
              onClick={() => setWizard(true)}
              className="gap-1.5"
            >
              <Bookmark size={14} /> Save as Monitor
            </Button>

            <Button variant="ghost" size="sm" onClick={() => setMode("ai")}>
              Refine with AI
            </Button>
          </div>
        </section>
      )}

      {/* Distinct Usage Limit Reached State (never disguised as empty results!) */}
      {quotaError && (
        <section
          role="alert"
          className="rounded-2xl border border-destructive/30 bg-destructive/5 p-5 space-y-2.5"
        >
          <div className="flex items-start gap-2.5">
            <AlertTriangle size={17} className="text-destructive shrink-0 mt-0.5" aria-hidden="true" />
            <div className="space-y-1">
              <h3 className="text-sm font-semibold text-destructive">Usage Limit Reached</h3>
              <p className="text-xs text-foreground">{quotaError}</p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3 pt-1">
            <Link
              href="/settings?category=billing&tab=overview"
              className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3.5 py-2 text-xs font-semibold text-primary-foreground"
            >
              Open Billing &amp; Usage <ArrowRight size={13} />
            </Link>
            <Button variant="outline" size="sm" onClick={() => setQuotaError("")}>
              Dismiss
            </Button>
          </div>
        </section>
      )}

      {error && <ErrorState message={error} />}

      {/* Live Execution Progress */}
      {job && <JobPanel key={job} id={job} onComplete={setFinished} />}

      {/* Discovery Results */}
      {finished && (
        <section className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-base font-semibold text-foreground">Search Results</h2>
            <Badge>
              {ids.length} matching {ids.length === 1 ? "discussion" : "discussions"}
            </Badge>
          </div>

          {ids.length > 0 ? (
            <div className="grid gap-4 lg:grid-cols-2">
              {ids.map((id) => (
                <SearchResult key={id} id={id} />
              ))}
            </div>
          ) : finished.status === "FAILED" ? (
            <ErrorState
              message="The search failed before completing provider checks. Review the source error above and retry."
              retry={() => void runSearch()}
            />
          ) : (
            <EmptyState
              title={
                finished.status === "CANCELLED"
                  ? "Search cancelled"
                  : "No matching discussions found"
              }
              description="Providers completed cleanly with no matching items for these terms. Try broadening your keywords, adding another source, or lowering the minimum relevance."
              action={
                <Button variant="outline" size="sm" onClick={() => setMode("advanced")}>
                  Adjust search criteria
                </Button>
              }
            />
          )}
        </section>
      )}

      {wizard && <MonitorWizard configuration={config} open onClose={() => setWizard(false)} />}
    </div>
  );
}
