"use client";

import { useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  Bookmark,
  Check,
  Info,
  Loader2,
  Play,
  Plus,
  Radio,
  RotateCcw,
  SlidersHorizontal,
  Sparkles,
  Undo2,
  X,
} from "lucide-react";
import {
  INTENT_CATEGORIES,
  type IntentCategory,
  type IntentSearch,
  type SearchStrategy,
  type SourceId,
} from "@/lib/intent-radar";
import { Button } from "@/components/ui/button";
import { Badge } from "../ui";
import { ProviderLogo } from "../provider-logo";
import { useRadarCapabilities, useRadarRead } from "../provider";

export function InlineReviewPanel({
  config,
  onChangeConfig,
  strategy,
  draftInfo,
  originalPrompt,
  canWrite,
  invalid,
  active,
  isPending,
  searchesExhausted,
  planSearches,
  quotaError,
  error,
  onRunDiscovery,
  onEditInAdvanced,
  onRefinePrompt,
  onResetOriginal,
  onUndo,
  canUndo,
  diffSummary,
  onSaveSearch,
  onOpenMonitorWizard,
}: {
  config: IntentSearch;
  onChangeConfig?: (next: IntentSearch) => void;
  strategy: SearchStrategy | null;
  draftInfo: {
    mode: string;
    reason?: string;
    quota_exhausted?: boolean;
    source_warning?: string | null;
  } | null;
  originalPrompt?: string;
  canWrite: boolean;
  invalid: boolean;
  active: boolean;
  isPending: boolean;
  searchesExhausted: boolean;
  planSearches?: { used: number; limit: number; remaining: number };
  quotaError: string;
  error: string;
  onRunDiscovery: () => void;
  onEditInAdvanced: () => void;
  onRefinePrompt?: (refinementText: string) => Promise<void>;
  onResetOriginal?: () => void;
  onUndo?: () => void;
  canUndo?: boolean;
  diffSummary?: string | null;
  onSaveSearch: (name: string, description: string) => Promise<void>;
  onOpenMonitorWizard: () => void;
}) {
  const access = useRadarCapabilities();
  const icps = useRadarRead<{ items: { id: string; name: string }[] }>("/icps");

  const [savingForm, setSavingForm] = useState(false);
  const [saveName, setSaveName] = useState(() => config.keywords.slice(0, 3).join(" · ") || "Saved discovery");
  const [saveDesc, setSaveDesc] = useState("");
  const [savingBusy, setSavingBusy] = useState(false);
  const [savedNotice, setSavedNotice] = useState("");

  // Natural language refinement state
  const [refinementInput, setRefinementInput] = useState("");
  const [refiningBusy, setRefiningBusy] = useState(false);
  const [newKeywordInput, setNewKeywordInput] = useState("");
  const [newExclusionInput, setNewExclusionInput] = useState("");

  const sources = config.sources ?? ["hacker_news"];
  const allAvailableSources = (access.data?.sources || []).map((s) => ({
    id: (s.id || "hacker_news") as SourceId,
    name: s.name,
    state: s.state,
    coverage: s.coverage,
  }));

  const icpName = config.icp_id
    ? icps.data?.items.find((i) => i.id === config.icp_id)?.name || "Selected ICP"
    : "Broad Market (no ICP filter)";

  function handleAddKeyword() {
    const val = newKeywordInput.trim();
    if (!val || config.keywords.includes(val)) return;
    onChangeConfig?.({
      ...config,
      keywords: [...config.keywords, val],
    });
    setNewKeywordInput("");
  }

  function handleRemoveKeyword(kw: string) {
    onChangeConfig?.({
      ...config,
      keywords: config.keywords.filter((k) => k !== kw),
    });
  }

  function handleAddExclusion() {
    const val = newExclusionInput.trim();
    if (!val || config.excluded.includes(val)) return;
    onChangeConfig?.({
      ...config,
      excluded: [...config.excluded, val],
    });
    setNewExclusionInput("");
  }

  function handleRemoveExclusion(ex: string) {
    onChangeConfig?.({
      ...config,
      excluded: config.excluded.filter((k) => k !== ex),
    });
  }

  function handleToggleSource(sourceId: SourceId) {
    const nextSources = sources.includes(sourceId)
      ? sources.filter((s) => s !== sourceId)
      : [...sources, sourceId];
    onChangeConfig?.({
      ...config,
      sources: nextSources,
    });
  }

  function handleToggleCategory(cat: IntentCategory) {
    const nextCats: IntentCategory[] = config.categories.includes(cat)
      ? config.categories.filter((c) => c !== cat)
      : [...config.categories, cat];
    onChangeConfig?.({
      ...config,
      categories: nextCats,
    });
  }

  async function handleExecuteRefinement() {
    const text = refinementInput.trim();
    if (!text || !onRefinePrompt) return;
    setRefiningBusy(true);
    try {
      await onRefinePrompt(text);
      setRefinementInput("");
    } finally {
      setRefiningBusy(false);
    }
  }

  async function handleSave() {
    if (!saveName.trim()) return;
    setSavingBusy(true);
    setSavedNotice("");
    try {
      await onSaveSearch(saveName.trim(), saveDesc.trim());
      setSavingForm(false);
      setSavedNotice("Saved to Saved Searches.");
    } finally {
      setSavingBusy(false);
    }
  }

  const estimatedQueryVolume = sources.length * Math.min(config.result_limit || 20, 20);

  return (
    <section
      id="discovery-strategy-review"
      aria-label="Discovery Strategy Review"
      className="rounded-2xl border-2 border-primary/30 bg-card p-5 sm:p-6 space-y-5 shadow-sm"
    >
      {/* 1. Header with Objective & Mode Badge */}
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-border pb-4">
        <div className="space-y-1 max-w-2xl">
          <div className="flex items-center gap-2">
            <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-primary/15 text-primary">
              <Sparkles size={12} aria-hidden="true" />
            </span>
            <h2 className="text-base font-semibold text-foreground">
              Discovery Strategy Review
            </h2>
            {draftInfo && <Badge>{draftInfo.mode}</Badge>}
          </div>
          <p className="text-xs text-foreground font-medium leading-relaxed">
            {strategy?.objective || originalPrompt || "Surface relevant discussions matching your keywords and sources."}
          </p>
          {strategy?.target_customer_context && (
            <p className="text-[11px] text-muted-foreground">
              Aligned with: {strategy.target_customer_context}
            </p>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button size="sm" variant="outline" onClick={onEditInAdvanced} className="gap-1.5 text-xs">
            <SlidersHorizontal size={13} /> Edit in Advanced Search
          </Button>
        </div>
      </div>

      {/* Explicit AI / Fallback Status */}
      {draftInfo && (
        <div
          role="status"
          className={
            "rounded-xl border p-3.5 text-xs flex items-start gap-2.5 " +
            (draftInfo.mode === "Manual fallback"
              ? "border-amber-500/35 bg-amber-500/10"
              : "border-primary/25 bg-primary/5")
          }
        >
          {draftInfo.mode === "Manual fallback" ? (
            <AlertTriangle size={14} className="text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" aria-hidden="true" />
          ) : (
            <Info size={14} className="text-primary shrink-0 mt-0.5" aria-hidden="true" />
          )}
          <div className="space-y-0.5">
            <p className="font-semibold text-foreground">
              {draftInfo.mode === "Manual fallback"
                ? "Manual Fallback Criteria (AI draft budget exhausted or gateway offline)"
                : "AI-Generated Discovery Strategy"}
            </p>
            <p className="text-muted-foreground">
              {draftInfo.reason || "Review and fine-tune your parameters below. You can refine with natural language or run discovery immediately."}
            </p>
          </div>
        </div>
      )}

      {/* 2. Strategy Review Grid */}
      <div className="grid gap-4 md:grid-cols-2 text-xs">
        {/* Keywords & Phrases */}
        <div className="rounded-xl border border-border/80 bg-muted/20 p-4 space-y-2.5">
          <div className="flex items-center justify-between gap-2">
            <span className="font-semibold text-foreground text-xs">
              Keywords &amp; Phrases ({config.keywords.length})
            </span>
            <span className="text-[11px] text-muted-foreground">Click × to remove</span>
          </div>

          <div className="flex flex-wrap gap-1.5 min-h-[32px]">
            {config.keywords.map((kw) => (
              <span
                key={kw}
                className="inline-flex items-center gap-1 rounded-md bg-primary/10 border border-primary/20 px-2 py-0.5 text-[11px] font-medium text-primary"
              >
                {kw}
                <button
                  type="button"
                  onClick={() => handleRemoveKeyword(kw)}
                  aria-label={`Remove keyword ${kw}`}
                  className="rounded-full p-0.5 hover:bg-primary/20 cursor-pointer"
                >
                  <X size={10} />
                </button>
              </span>
            ))}
            {config.keywords.length === 0 && (
              <span className="text-destructive font-medium text-[11px]">
                Add at least one keyword
              </span>
            )}
          </div>

          <div className="flex items-center gap-1.5 pt-1">
            <input
              type="text"
              value={newKeywordInput}
              onChange={(e) => setNewKeywordInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  handleAddKeyword();
                }
              }}
              placeholder="Add keyword or phrase…"
              className="flex-1 rounded-lg border border-border bg-background px-2.5 py-1 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            />
            <Button size="sm" variant="outline" onClick={handleAddKeyword} className="h-7 px-2 text-xs">
              <Plus size={12} /> Add
            </Button>
          </div>
          {strategy?.keyword_rationale && (
            <p className="text-[11px] text-muted-foreground leading-relaxed pt-1">
              <strong>Rationale:</strong> {strategy.keyword_rationale}
            </p>
          )}
        </div>

        {/* Selected Sources */}
        <div className="rounded-xl border border-border/80 bg-muted/20 p-4 space-y-2.5">
          <div className="flex items-center justify-between gap-2">
            <span className="font-semibold text-foreground text-xs">
              Selected Sources ({sources.length})
            </span>
            <span className="text-[11px] text-muted-foreground">Toggle sources on/off</span>
          </div>

          <div className="flex flex-wrap gap-1.5">
            {allAvailableSources.map((src) => {
              const active = sources.includes(src.id);
              return (
                <button
                  key={src.id}
                  type="button"
                  onClick={() => handleToggleSource(src.id)}
                  aria-pressed={active}
                  className={
                    "inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs font-medium transition-colors cursor-pointer " +
                    (active
                      ? "border-primary bg-primary/10 text-primary font-semibold"
                      : "border-border bg-background text-muted-foreground hover:text-foreground")
                  }
                >
                  <ProviderLogo provider={src.name} size={13} />
                  <span>{src.name}</span>
                  {active && <Check size={11} className="text-primary" />}
                </button>
              );
            })}
          </div>
          {strategy?.source_rationale && (
            <p className="text-[11px] text-muted-foreground leading-relaxed pt-1">
              <strong>Rationale:</strong> {strategy.source_rationale}
            </p>
          )}
        </div>

        {/* Intent Categories */}
        <div className="rounded-xl border border-border/80 bg-muted/20 p-4 space-y-2.5">
          <div className="flex items-center justify-between gap-2">
            <span className="font-semibold text-foreground text-xs">
              Intent Categories
            </span>
            {config.categories.length > 0 && (
              <button
                type="button"
                onClick={() => onChangeConfig?.({ ...config, categories: [] })}
                className="text-[11px] font-medium text-primary hover:underline cursor-pointer"
              >
                Include all
              </button>
            )}
          </div>

          <div className="flex flex-wrap gap-1.5">
            {INTENT_CATEGORIES.map((cat) => {
              const active = config.categories.includes(cat);
              return (
                <button
                  key={cat}
                  type="button"
                  onClick={() => handleToggleCategory(cat)}
                  aria-pressed={active}
                  className={
                    "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] transition-colors cursor-pointer " +
                    (active
                      ? "border-primary bg-primary text-primary-foreground font-medium"
                      : "border-border bg-background text-muted-foreground hover:border-primary/50 hover:text-foreground")
                  }
                >
                  {cat}
                </button>
              );
            })}
          </div>
        </div>

        {/* Exclusions & Scope */}
        <div className="rounded-xl border border-border/80 bg-muted/20 p-4 space-y-2.5">
          <div className="flex items-center justify-between gap-2">
            <span className="font-semibold text-foreground text-xs">
              Negative Exclusions ({config.excluded.length})
            </span>
            <span className="text-[11px] text-muted-foreground">Filter noisy posts</span>
          </div>

          <div className="flex flex-wrap gap-1.5 min-h-[32px]">
            {config.excluded.map((ex) => (
              <span
                key={ex}
                className="inline-flex items-center gap-1 rounded-md bg-destructive/10 border border-destructive/20 px-2 py-0.5 text-[11px] font-medium text-destructive"
              >
                {ex}
                <button
                  type="button"
                  onClick={() => handleRemoveExclusion(ex)}
                  aria-label={`Remove exclusion ${ex}`}
                  className="rounded-full p-0.5 hover:bg-destructive/20 cursor-pointer"
                >
                  <X size={10} />
                </button>
              </span>
            ))}
            {config.excluded.length === 0 && (
              <span className="text-[11px] text-muted-foreground italic">
                No negative exclusions set
              </span>
            )}
          </div>

          <div className="flex items-center gap-1.5 pt-1">
            <input
              type="text"
              value={newExclusionInput}
              onChange={(e) => setNewExclusionInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  handleAddExclusion();
                }
              }}
              placeholder="Exclude term (e.g. job, hiring, tutorial)…"
              className="flex-1 rounded-lg border border-border bg-background px-2.5 py-1 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            />
            <Button size="sm" variant="outline" onClick={handleAddExclusion} className="h-7 px-2 text-xs">
              <Plus size={12} /> Exclude
            </Button>
          </div>
        </div>
      </div>

      {/* 3. Scope, Dates & Quota Impact Card */}
      <div className="rounded-xl border border-border bg-muted/15 p-3.5 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex flex-wrap items-center gap-4 text-muted-foreground">
          <span>
            <strong className="text-foreground">Date Window:</strong>{" "}
            {config.from_date || "Past 30 days"} → {config.to_date || "Today"}
          </span>
          <span>
            <strong className="text-foreground">Min Relevance:</strong> {config.min_relevance || 0}/100
          </span>
          <span>
            <strong className="text-foreground">Result Limit:</strong> {config.result_limit || 20} signals
          </span>
          <span>
            <strong className="text-foreground">ICP Context:</strong> {icpName}
          </span>
        </div>

        <div className="text-[11px] text-muted-foreground">
          {planSearches ? (
            <span>
              Remaining Search Allowance:{" "}
              <strong className="text-foreground font-semibold">{planSearches.remaining}</strong> of {planSearches.limit}
            </span>
          ) : (
            <span>Estimated query volume: ~{estimatedQueryVolume} items</span>
          )}
        </div>
      </div>

      {/* 4. Natural-Language Refine with AI Section (Embedded Directly) */}
      {onRefinePrompt && (
        <div className="rounded-xl border border-primary/20 bg-primary/[0.04] p-4 space-y-3">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
              <Sparkles size={13} className="text-primary" />
              <span>Refine with AI</span>
            </div>
            {canUndo && onUndo && (
              <button
                type="button"
                onClick={onUndo}
                className="inline-flex items-center gap-1 text-[11px] font-medium text-primary hover:underline cursor-pointer"
              >
                <Undo2 size={12} /> Undo Last Refinement
              </button>
            )}
            {onResetOriginal && (
              <button
                type="button"
                onClick={onResetOriginal}
                className="inline-flex items-center gap-1 text-[11px] font-medium text-muted-foreground hover:text-foreground cursor-pointer"
              >
                <RotateCcw size={11} /> Reset to Original
              </button>
            )}
          </div>

          <div className="flex items-center gap-2">
            <input
              type="text"
              value={refinementInput}
              disabled={refiningBusy || !canWrite}
              onChange={(e) => setRefinementInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  void handleExecuteRefinement();
                }
              }}
              placeholder="e.g. 'Narrow to GitHub and Hacker News only', 'Exclude open-source contributors', 'Focus on senior decision makers'…"
              className="flex-1 rounded-lg border border-border bg-background px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            />
            <Button
              size="sm"
              disabled={!refinementInput.trim() || refiningBusy || !canWrite}
              onClick={() => void handleExecuteRefinement()}
              className="h-8 gap-1.5 text-xs shrink-0"
            >
              {refiningBusy ? (
                <>
                  <Loader2 size={13} className="animate-spin" /> Refining…
                </>
              ) : (
                <>
                  <Sparkles size={13} /> Refine
                </>
              )}
            </Button>
          </div>

          {diffSummary && (
            <p className="text-[11px] font-medium text-emerald-700 dark:text-emerald-300">
              {diffSummary}
            </p>
          )}

          {/* Quick refinement suggestions */}
          <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-muted-foreground pt-0.5">
            <span>Suggestions:</span>
            {[
              "Narrow to GitHub & Hacker News",
              "Exclude tutorials & job postings",
              "Focus on VP/CTO decision makers",
              "Increase relevance threshold to 75+",
            ].map((sug) => (
              <button
                key={sug}
                type="button"
                onClick={() => setRefinementInput(sug)}
                className="rounded-full border border-border/80 bg-background px-2.5 py-0.5 text-muted-foreground hover:border-primary/50 hover:text-foreground transition-colors cursor-pointer"
              >
                {sug}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Quota Exhaustion Warning */}
      {(searchesExhausted || quotaError) && (
        <div
          role="alert"
          className="rounded-xl border border-amber-500/40 bg-amber-500/10 p-4 space-y-2 text-xs"
        >
          <div className="flex items-start gap-2.5">
            <AlertTriangle size={15} className="text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <h3 className="font-semibold text-foreground">
                {quotaError
                  ? "Usage Limit Reached"
                  : `Monthly search allowance exhausted (${planSearches?.used}/${planSearches?.limit})`}
              </h3>
              <p className="text-muted-foreground">
                {quotaError ||
                  "You can still review historical runs, saved searches, and existing signals, or upgrade your plan to unlock more searches."}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3 pt-0.5">
            <Link
              href="/settings?category=billing&tab=overview"
              className="text-xs font-semibold text-primary hover:underline"
            >
              View Billing &amp; Usage →
            </Link>
          </div>
        </div>
      )}

      {error && (
        <div role="alert" className="rounded-xl border border-destructive/40 bg-destructive/10 p-3 text-xs text-destructive">
          {error}
        </div>
      )}

      {/* Inline Save Search Form */}
      {savingForm && (
        <div className="rounded-xl border border-border bg-muted/25 p-4 space-y-3">
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs font-semibold text-foreground">Save Reusable Search Configuration</span>
            <button
              type="button"
              onClick={() => setSavingForm(false)}
              className="text-xs text-muted-foreground hover:text-foreground cursor-pointer"
            >
              Cancel
            </button>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="space-y-1 text-xs">
              <span className="font-medium text-muted-foreground">Search name</span>
              <input
                value={saveName}
                maxLength={120}
                onChange={(e) => setSaveName(e.target.value)}
                placeholder="e.g. Q4 CRM Alternative Evaluations"
                className="w-full rounded-lg border border-border bg-card px-3 py-1.5 text-xs text-foreground"
              />
            </label>
            <label className="space-y-1 text-xs">
              <span className="font-medium text-muted-foreground">Description (optional)</span>
              <input
                value={saveDesc}
                maxLength={300}
                onChange={(e) => setSaveDesc(e.target.value)}
                placeholder="Notes on when to run this search"
                className="w-full rounded-lg border border-border bg-card px-3 py-1.5 text-xs text-foreground"
              />
            </label>
          </div>
          <div className="flex items-center justify-between gap-2">
            <span className="text-[11px] text-muted-foreground">
              Saved searches are reusable templates and do not run automatically on a schedule.
            </span>
            <Button size="sm" disabled={!saveName.trim() || savingBusy} onClick={() => void handleSave()}>
              {savingBusy ? "Saving…" : "Save Search"}
            </Button>
          </div>
        </div>
      )}

      {savedNotice && (
        <p className="text-xs font-medium text-emerald-700 dark:text-emerald-300">
          {savedNotice}{" "}
          <Link href="/intent-radar/discover/saved" className="underline">
            View Saved Searches
          </Link>
        </p>
      )}

      {/* 5. Prominent Primary Execution Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
        <div className="flex flex-wrap items-center gap-3">
          <Button
            size="default"
            disabled={invalid || active || isPending || !canWrite}
            onClick={onRunDiscovery}
            className="gap-2 px-5 py-2.5 font-semibold text-sm"
          >
            {active || isPending ? (
              <>
                <Loader2 size={15} className="animate-spin" /> Running Discovery…
              </>
            ) : (
              <>
                <Play size={14} fill="currentColor" /> Run Discovery
              </>
            )}
          </Button>
          <span className="text-[11px] text-muted-foreground">
            Queries {sources.length} source{sources.length === 1 ? "" : "s"} · Uses 1 search allowance
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            disabled={invalid || !canWrite}
            onClick={() => {
              setSaveName(config.keywords.slice(0, 3).join(" · ") || "Saved discovery");
              setSavingForm((v) => !v);
            }}
            className="gap-1.5 text-xs"
          >
            <Bookmark size={13} /> Save as Search
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={invalid || !canWrite}
            onClick={onOpenMonitorWizard}
            className="gap-1.5 text-xs"
          >
            <Radio size={13} /> Save as Monitor
          </Button>
        </div>
      </div>
    </section>
  );
}
