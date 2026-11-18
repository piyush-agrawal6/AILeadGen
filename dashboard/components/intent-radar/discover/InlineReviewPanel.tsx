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
  Radio,
  SlidersHorizontal,
  Sparkles,
} from "lucide-react";
import type { IntentSearch, SearchStrategy, SourceId } from "@/lib/intent-radar";
import { Button } from "@/components/ui/button";
import { Badge } from "../ui";
import { useRadarCapabilities, useRadarRead } from "../provider";

export function InlineReviewPanel({
  config,
  strategy,
  draftInfo,
  canWrite,
  invalid,
  active,
  isPending,
  searchesExhausted,
  planSearches,
  quotaError,
  error,
  onRunDiscovery,
  onEditCriteria,
  onImproveWithCopilot,
  onSaveSearch,
  onOpenMonitorWizard,
}: {
  config: IntentSearch;
  strategy: SearchStrategy | null;
  draftInfo: {
    mode: string;
    reason?: string;
    quota_exhausted?: boolean;
    source_warning?: string | null;
  } | null;
  canWrite: boolean;
  invalid: boolean;
  active: boolean;
  isPending: boolean;
  searchesExhausted: boolean;
  planSearches?: { used: number; limit: number; remaining: number };
  quotaError: string;
  error: string;
  onRunDiscovery: () => void;
  onEditCriteria: () => void;
  onImproveWithCopilot: () => void;
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

  const sources = config.sources ?? ["hacker_news"];
  const sourceLabels = sources.map(
    (id) => access.data?.sources.find((s) => (s.id || "hacker_news") === id)?.name || id
  );
  const icpName = config.icp_id
    ? icps.data?.items.find((i) => i.id === config.icp_id)?.name || "Selected ICP"
    : "None (broad market discovery)";

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

  return (
    <section
      id="inline-discovery-review"
      aria-label="Review Search Plan"
      className="rounded-2xl border-2 border-primary/30 bg-card p-5 sm:p-6 space-y-5 shadow-sm"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-primary/15 text-primary">
              <Check size={12} aria-hidden="true" />
            </span>
            <h2 className="text-base font-semibold text-foreground">
              Review Search Criteria
            </h2>
            {draftInfo && <Badge>{draftInfo.mode}</Badge>}
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            Confirm your keywords, sources, and filters before running discovery. Nothing runs until you click Run Search.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button size="sm" variant="outline" onClick={onEditCriteria} className="gap-1.5 text-xs">
            <SlidersHorizontal size={13} /> Edit Criteria
          </Button>
          <Button size="sm" variant="outline" onClick={onImproveWithCopilot} className="gap-1.5 text-xs">
            <Sparkles size={13} /> Improve with Copilot
          </Button>
        </div>
      </div>

      {/* Explicit AI or Fallback Notice */}
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
                ? "Manual Fallback Criteria (AI did not generate this draft)"
                : "AI-Assisted Draft Criteria"}
            </p>
            <p className="text-muted-foreground">
              {draftInfo.reason || "Review these editable criteria before running your search."}
            </p>
          </div>
        </div>
      )}

      {/* AI Search Strategy Card (when present) */}
      {strategy && (
        <div className="rounded-xl border border-primary/20 bg-primary/[0.03] p-4 space-y-3 text-xs">
          <div className="flex items-center gap-1.5 font-semibold text-foreground">
            <Sparkles size={13} className="text-primary" aria-hidden="true" />
            Search Strategy &amp; Rationale
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <span className="text-[11px] font-semibold text-muted-foreground">Objective</span>
              <p className="mt-0.5 text-foreground leading-relaxed">{strategy.objective}</p>
            </div>
            <div>
              <span className="text-[11px] font-semibold text-muted-foreground">Target Context</span>
              <p className="mt-0.5 text-foreground leading-relaxed">{strategy.target_customer_context}</p>
            </div>
            <div>
              <span className="text-[11px] font-semibold text-muted-foreground">Keyword Rationale</span>
              <p className="mt-0.5 text-muted-foreground leading-relaxed">{strategy.keyword_rationale}</p>
            </div>
            <div>
              <span className="text-[11px] font-semibold text-muted-foreground">Source Rationale</span>
              <p className="mt-0.5 text-muted-foreground leading-relaxed">{strategy.source_rationale}</p>
            </div>
          </div>
          {strategy.limitations.length > 0 && (
            <div className="border-t border-border/60 pt-2 text-[11px] text-muted-foreground">
              <strong className="text-foreground">Limitations:</strong> {strategy.limitations.join(" ")}
            </div>
          )}
        </div>
      )}

      {/* Structured Criteria Snapshot */}
      <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 text-xs">
        <div className="rounded-xl border border-border/80 bg-muted/20 p-3.5">
          <dt className="text-muted-foreground">Keywords ({config.keywords.length})</dt>
          <dd className="mt-1.5 flex flex-wrap gap-1.5">
            {config.keywords.length ? (
              config.keywords.map((k) => (
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
          <dt className="text-muted-foreground">Sources ({sourceLabels.length})</dt>
          <dd className="mt-1 font-semibold text-foreground">
            {sourceLabels.length ? sourceLabels.join(", ") : "Select at least one source"}
          </dd>
        </div>

        <div className="rounded-xl border border-border/80 bg-muted/20 p-3.5">
          <dt className="text-muted-foreground">Intent Categories</dt>
          <dd className="mt-1 font-medium text-foreground">
            {config.categories.length ? config.categories.join(", ") : "All conversation types"}
          </dd>
        </div>

        <div className="rounded-xl border border-border/80 bg-muted/20 p-3.5">
          <dt className="text-muted-foreground">Exclusions</dt>
          <dd className="mt-1 font-medium text-foreground">
            {config.excluded.length ? config.excluded.join(", ") : "None"}
          </dd>
        </div>

        <div className="rounded-xl border border-border/80 bg-muted/20 p-3.5">
          <dt className="text-muted-foreground">Window &amp; Limit</dt>
          <dd className="mt-1 font-medium text-foreground">
            {config.from_date || "Any date"} → {config.to_date || "Latest"} · up to {config.result_limit}
            {config.min_relevance > 0 ? ` (≥ ${config.min_relevance}/100)` : ""}
          </dd>
        </div>

        <div className="rounded-xl border border-border/80 bg-muted/20 p-3.5">
          <dt className="text-muted-foreground">Active ICP</dt>
          <dd className="mt-1 font-medium text-foreground">{icpName}</dd>
        </div>
      </dl>

      {/* Search Quota Exhausted Warning */}
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
            <Link
              href="/intent-radar/discover/history"
              className="text-xs font-medium text-muted-foreground hover:text-foreground"
            >
              Browse Discovery History
            </Link>
          </div>
        </div>
      )}

      {error && (
        <div role="alert" className="rounded-xl border border-destructive/40 bg-destructive/10 p-3 text-xs text-destructive">
          {error}
        </div>
      )}

      {/* Inline Save Search Drawer/Form */}
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

      {/* Primary Execution Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
        <div className="flex flex-wrap items-center gap-2">
          <Button
            disabled={invalid || active || isPending || !canWrite}
            onClick={onRunDiscovery}
            className="gap-1.5"
          >
            {active || isPending ? (
              <>
                <Loader2 size={14} className="animate-spin" /> Running Search…
              </>
            ) : (
              <>
                <Play size={14} /> Run Search
              </>
            )}
          </Button>
          <span className="text-[11px] text-muted-foreground">
            Uses 1 search allowance · executes inline on this page
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
            <Bookmark size={13} /> Save Search
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

      {/* Source coverage disclosure */}
      <details className="rounded-xl border border-border/70 bg-muted/15 px-3.5 py-2.5 text-[11px] text-muted-foreground">
        <summary className="font-medium text-foreground cursor-pointer">
          Source coverage &amp; quota transparency
        </summary>
        <div className="mt-2 space-y-1">
          {access.data?.sources
            .filter((s) => sources.includes((s.id || "hacker_news") as SourceId))
            .map((s) => (
              <p key={s.name}>
                <strong className="text-foreground">{s.name}:</strong> {s.coverage} (up to{" "}
                {s.request_limit_per_check || 22} requests/check).
              </p>
            ))}
        </div>
      </details>
    </section>
  );
}
