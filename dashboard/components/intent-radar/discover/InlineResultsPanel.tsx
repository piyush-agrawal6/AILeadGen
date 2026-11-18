"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  ArrowUpDown,
  Bookmark,
  BookmarkCheck,
  ExternalLink,
  Eye,
  FileSearch,
  Search,
  Sparkles,
  X,
} from "lucide-react";
import type { IntentSignal } from "@/lib/intent-radar";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState } from "../ui";
import { ProviderLogo } from "../provider-logo";
import { useRadarCapabilities, useRadarMutation, useRadarRead } from "../provider";

const BUYER_INTENT_CATEGORIES = new Set([
  "Recommendation request",
  "Problem / pain point",
  "Product comparison",
  "Alternative search",
  "Tool / service evaluation",
  "Purchase consideration",
  "Feature request",
]);

function classifySignal(sig: IntentSignal): { label: string; tone: "buyer" | "market" } {
  const kind = sig.evidence?.provenance?.content_kind || "";
  if (kind === "release_announcement" || kind === "release" || kind === "research_paper" || kind === "paper") {
    return { label: "Market / Tech Intelligence", tone: "market" };
  }
  if (BUYER_INTENT_CATEGORIES.has(sig.category)) {
    return { label: "Buyer-Intent Signal", tone: "buyer" };
  }
  return { label: "Market / Tech Intelligence", tone: "market" };
}

function formatDate(iso: string): { short: string; full: string } {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return { short: iso, full: iso };
  return {
    short: d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }),
    full: d.toLocaleString(),
  };
}

/** Hydrates a single signal by ID into the table row when only signalIds are available (inline post-run). */
function HydratedSignalRow({
  id,
  searchQuery,
  sourceFilter,
  classFilter,
  onSelect,
  onToggleSave,
  savedOverrides,
  canWrite,
}: {
  id: string;
  searchQuery: string;
  sourceFilter: string;
  classFilter: "all" | "buyer" | "market";
  onSelect: (sig: IntentSignal) => void;
  onToggleSave: (sig: IntentSignal) => void;
  savedOverrides: Record<string, boolean>;
  canWrite: boolean;
}) {
  const query = useRadarRead<IntentSignal>("/signals/" + id);
  if (query.error) {
    return (
      <tr>
        <td colSpan={6} className="px-4 py-3 text-xs text-destructive">
          <ErrorState message={query.error.message} />
        </td>
      </tr>
    );
  }
  if (!query.data) {
    return (
      <tr className="animate-pulse">
        <td colSpan={6} className="px-4 py-3">
          <div className="h-4 w-2/3 rounded bg-muted" />
        </td>
      </tr>
    );
  }
  const sig = query.data;
  const kind = classifySignal(sig);
  if (sourceFilter && sig.source !== sourceFilter) return null;
  if (classFilter === "buyer" && kind.tone !== "buyer") return null;
  if (classFilter === "market" && kind.tone !== "market") return null;
  if (searchQuery) {
    const hay = `${sig.title} ${sig.excerpt} ${sig.source} ${sig.category}`.toLowerCase();
    if (!hay.includes(searchQuery.toLowerCase())) return null;
  }
  const isSaved = savedOverrides[sig.id] ?? sig.saved;
  return (
    <ResultTableRow
      signal={sig}
      isSaved={isSaved}
      canWrite={canWrite}
      onSelect={() => onSelect(sig)}
      onToggleSave={() => onToggleSave(sig)}
    />
  );
}

function ResultTableRow({
  signal,
  isSaved,
  canWrite,
  onSelect,
  onToggleSave,
}: {
  signal: IntentSignal;
  isSaved: boolean;
  canWrite: boolean;
  onSelect: () => void;
  onToggleSave: () => void;
}) {
  const kind = classifySignal(signal);
  const obs = formatDate(signal.observed_at);

  return (
    <tr
      tabIndex={0}
      onClick={onSelect}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelect();
        }
      }}
      className="group cursor-pointer hover:bg-muted/35 focus-visible:outline-none focus-visible:bg-primary/[0.06] transition-colors"
    >
      {/* Discussion / Result */}
      <td className="py-3 pl-4 pr-3 max-w-md">
        <div className="font-semibold text-[13px] text-foreground group-hover:text-primary transition-colors line-clamp-1">
          {signal.title}
        </div>
        {signal.excerpt && (
          <p className="mt-0.5 text-[11px] text-muted-foreground line-clamp-1">
            {signal.excerpt}
          </p>
        )}
      </td>

      {/* Source */}
      <td className="py-3 px-3 whitespace-nowrap">
        <span className="inline-flex items-center gap-1.5 text-xs font-medium text-foreground">
          <ProviderLogo provider={signal.source} size={14} />
          <span>{signal.source}</span>
        </span>
      </td>

      {/* Classification */}
      <td className="py-3 px-3 whitespace-nowrap">
        <div className="flex flex-col items-start gap-0.5">
          <span
            className={
              "rounded-full px-2 py-0.5 text-[10px] font-semibold " +
              (kind.tone === "buyer"
                ? "bg-emerald-500/12 text-emerald-700 dark:text-emerald-300"
                : "bg-sky-500/12 text-sky-700 dark:text-sky-300")
            }
          >
            {kind.label}
          </span>
          <span className="text-[10px] text-muted-foreground pl-0.5">{signal.category}</span>
        </div>
      </td>

      {/* Relevance */}
      <td className="py-3 px-3 whitespace-nowrap text-right">
        <span
          className={
            "inline-block rounded-md px-2 py-0.5 text-xs font-semibold tabular-nums " +
            (signal.score >= 70
              ? "bg-emerald-500/12 text-emerald-700 dark:text-emerald-300"
              : signal.score >= 40
                ? "bg-amber-500/12 text-amber-700 dark:text-amber-300"
                : "bg-muted text-muted-foreground")
          }
        >
          {signal.score}/100
        </span>
      </td>

      {/* Observed */}
      <td className="py-3 px-3 whitespace-nowrap text-xs text-muted-foreground" title={obs.full}>
        {obs.short}
      </td>

      {/* Compact Actions */}
      <td
        className="py-3 pl-2 pr-4 whitespace-nowrap text-right"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") e.stopPropagation();
        }}
      >
        <div className="inline-flex items-center justify-end gap-1">
          <button
            type="button"
            onClick={onSelect}
            aria-label={`View details for ${signal.title}`}
            title="View Details"
            className="inline-flex h-7 items-center gap-1 rounded-md border border-border bg-background px-2 text-[11px] font-medium text-foreground hover:border-primary/50 hover:text-primary cursor-pointer"
          >
            <Eye size={12} /> Details
          </button>
          {canWrite && (
            <button
              type="button"
              onClick={onToggleSave}
              aria-label={isSaved ? `Unsave ${signal.title}` : `Save ${signal.title}`}
              title={isSaved ? "Saved" : "Save signal"}
              className={
                "inline-flex h-7 w-7 items-center justify-center rounded-md border transition-colors cursor-pointer " +
                (isSaved
                  ? "border-primary/40 bg-primary/10 text-primary"
                  : "border-border bg-background text-muted-foreground hover:text-foreground")
              }
            >
              {isSaved ? <BookmarkCheck size={13} /> : <Bookmark size={13} />}
            </button>
          )}
          <a
            href={signal.source_url}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={`Open original source for ${signal.title}`}
            title="Open original source"
            className="inline-flex h-7 w-7 items-center justify-center rounded-md border border-border bg-background text-muted-foreground hover:text-foreground"
          >
            <ExternalLink size={12} />
          </a>
        </div>
      </td>
    </tr>
  );
}

function SignalDetailDrawer({
  signal,
  isSaved,
  canWrite,
  onToggleSave,
  onClose,
}: {
  signal: IntentSignal | null;
  isSaved: boolean;
  canWrite: boolean;
  onToggleSave: () => void;
  onClose: () => void;
}) {
  useEffect(() => {
    if (!signal) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  }, [signal, onClose]);

  if (!signal) return null;
  const kind = classifySignal(signal);
  const obs = formatDate(signal.observed_at);

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-black/45 backdrop-blur-[1px]"
      role="dialog"
      aria-modal="true"
      aria-label={`Signal details: ${signal.title}`}
      onClick={onClose}
    >
      <div
        className="flex h-full w-full max-w-lg flex-col border-l border-border bg-card shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3 border-b border-border px-5 py-4">
          <div className="min-w-0 space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <span
                className={
                  "rounded-full px-2.5 py-0.5 text-[11px] font-semibold " +
                  (kind.tone === "buyer"
                    ? "bg-emerald-500/12 text-emerald-700 dark:text-emerald-300"
                    : "bg-sky-500/12 text-sky-700 dark:text-sky-300")
                }
              >
                {kind.label}
              </span>
              <span className="text-xs text-muted-foreground">{signal.category}</span>
              <span className="text-xs font-semibold text-foreground">{signal.score}/100</span>
            </div>
            <h3 className="text-sm font-semibold text-foreground leading-snug">
              {signal.title}
            </h3>
            <p className="text-xs text-muted-foreground">
              {signal.source} · Observed {obs.full}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close signal details"
            className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground cursor-pointer"
          >
            <X size={16} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-5 text-xs">
          <div className="space-y-1.5">
            <h4 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Observed Excerpt
            </h4>
            <p className="rounded-xl border border-border/80 bg-muted/20 p-3.5 text-[13px] leading-relaxed text-foreground whitespace-pre-wrap break-words">
              {signal.excerpt || "No text excerpt captured for this item."}
            </p>
          </div>

          {signal.evidence && (
            <div className="space-y-2.5">
              <h4 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                Classification Evidence
              </h4>
              {signal.evidence.explanation && (
                <p className="text-foreground leading-relaxed">{signal.evidence.explanation}</p>
              )}
              {signal.evidence.matched_keywords?.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {signal.evidence.matched_keywords.map((kw) => (
                    <span
                      key={kw}
                      className="rounded-md bg-primary/10 px-2 py-0.5 text-[11px] font-medium text-primary"
                    >
                      {kw}
                    </span>
                  ))}
                </div>
              )}
              {signal.evidence.provenance?.repo && (
                <p className="text-muted-foreground">
                  <strong className="text-foreground">Repository:</strong> {signal.evidence.provenance.repo}
                </p>
              )}
              {signal.evidence.provenance?.ai_policy_note && (
                <p className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-2.5 text-[11px] text-amber-800 dark:text-amber-200">
                  {signal.evidence.provenance.ai_policy_note}
                </p>
              )}
            </div>
          )}
        </div>

        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border bg-muted/20 px-5 py-3.5">
          <div className="flex items-center gap-2">
            {canWrite && (
              <Button size="sm" variant={isSaved ? "default" : "outline"} onClick={onToggleSave} className="gap-1.5 text-xs">
                {isSaved ? <BookmarkCheck size={13} /> : <Bookmark size={13} />}
                {isSaved ? "Saved" : "Save Signal"}
              </Button>
            )}
            <a
              href={signal.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-border bg-card px-3 text-xs font-medium text-foreground hover:border-primary/50"
            >
              Open Source <ExternalLink size={12} />
            </a>
          </div>
          <Link
            href={`/intent-radar/signals/${signal.id}`}
            className="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline"
          >
            <FileSearch size={13} /> Inspect Full Evidence
          </Link>
        </div>
      </div>
    </div>
  );
}

export function InlineResultsPanel({
  discoveryId,
  signals,
  signalIds,
  scannedCount,
  matchedCount,
  coverage,
  partialWarning,
  hidePermanentLink = false,
  onRefineWithCopilot,
}: {
  discoveryId?: string | null;
  signals?: IntentSignal[];
  signalIds?: string[];
  scannedCount?: number;
  matchedCount?: number;
  coverage?: string;
  partialWarning?: string | null;
  hidePermanentLink?: boolean;
  onRefineWithCopilot?: () => void;
}) {
  const access = useRadarCapabilities();
  const mutation = useRadarMutation();

  const [searchQuery, setSearchQuery] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [classFilter, setClassFilter] = useState<"all" | "buyer" | "market">("all");
  const [sortBy, setSortBy] = useState<"relevance" | "recency">("relevance");
  const [selectedSignal, setSelectedSignal] = useState<IntentSignal | null>(null);
  const [savedOverrides, setSavedOverrides] = useState<Record<string, boolean>>({});

  const availableSources = useMemo(() => {
    if (!signals) return [];
    return [...new Set(signals.map((s) => s.source))].sort();
  }, [signals]);

  const filteredSignals = useMemo(() => {
    if (!signals) return null;
    const q = searchQuery.trim().toLowerCase();
    const list = signals.filter((sig) => {
      if (sourceFilter && sig.source !== sourceFilter) return false;
      const kind = classifySignal(sig);
      if (classFilter === "buyer" && kind.tone !== "buyer") return false;
      if (classFilter === "market" && kind.tone !== "market") return false;
      if (q) {
        const hay = `${sig.title} ${sig.excerpt} ${sig.source} ${sig.category}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
    return [...list].sort((a, b) => {
      if (sortBy === "recency") {
        return new Date(b.observed_at).getTime() - new Date(a.observed_at).getTime();
      }
      return b.score - a.score;
    });
  }, [signals, searchQuery, sourceFilter, classFilter, sortBy]);

  async function toggleSave(sig: IntentSignal) {
    const currentlySaved = savedOverrides[sig.id] ?? sig.saved;
    setSavedOverrides((prev) => ({ ...prev, [sig.id]: !currentlySaved }));
    try {
      await mutation.mutateAsync({
        path: `/saved/${sig.id}`,
        method: currentlySaved ? "DELETE" : "POST",
      });
    } catch {
      setSavedOverrides((prev) => ({ ...prev, [sig.id]: currentlySaved }));
    }
  }

  const totalCount = matchedCount ?? (signals ? signals.length : signalIds?.length || 0);
  const buyerCount = signals
    ? signals.filter((s) => classifySignal(s).tone === "buyer").length
    : null;
  const marketCount = signals && buyerCount !== null ? signals.length - buyerCount : null;
  const canWrite = Boolean(access.data?.can_write);

  return (
    <section
      aria-label="Discovery Results"
      className="rounded-2xl border border-border bg-card overflow-hidden shadow-sm"
    >
      {/* Compact Header & Toolbar */}
      <div className="p-4 sm:p-5 space-y-3 border-b border-border">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-foreground">
              Discovery Results ({totalCount})
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              {scannedCount !== undefined ? `${scannedCount} scanned · ` : ""}
              {buyerCount !== null && marketCount !== null
                ? `${buyerCount} buyer-intent · ${marketCount} market/tech intelligence`
                : "Retained matches from checked sources."}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {onRefineWithCopilot && (
              <Button size="sm" variant="outline" onClick={onRefineWithCopilot} className="h-8 gap-1.5 text-xs">
                <Sparkles size={13} /> Refine with Copilot
              </Button>
            )}
            {discoveryId && !hidePermanentLink && (
              <Link
                href={`/intent-radar/discover/runs/${discoveryId}`}
                className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-border bg-background px-3 text-xs font-medium text-foreground hover:border-primary/50 hover:text-primary transition-colors"
              >
                Open Run Details
              </Link>
            )}
          </div>
        </div>

        {partialWarning && (
          <div role="status" className="rounded-lg border border-amber-500/35 bg-amber-500/10 px-3 py-2 text-xs text-amber-800 dark:text-amber-200">
            {partialWarning}
          </div>
        )}

        {/* Compact Filter / Sort Controls */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <div className="relative flex-1 min-w-[180px] max-w-xs">
            <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none" />
            <input
              type="search"
              aria-label="Search results"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Filter results…"
              style={{ paddingLeft: "2rem" }}
              className="h-8 w-full rounded-lg border border-border bg-background pr-2.5 text-xs text-foreground"
            />
          </div>

          <div className="inline-flex items-center rounded-lg border border-border bg-muted/25 p-0.5 shrink-0">
            {(
              [
                ["all", "All"],
                ["buyer", "Buyer Intent"],
                ["market", "Market / Tech"],
              ] as const
            ).map(([val, label]) => (
              <button
                key={val}
                type="button"
                onClick={() => setClassFilter(val)}
                className={
                  "rounded-md px-2.5 py-1 text-[11px] font-medium transition-colors cursor-pointer " +
                  (classFilter === val
                    ? "bg-card text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground")
                }
              >
                {label}
              </button>
            ))}
          </div>

          {availableSources.length > 1 && (
            <select
              aria-label="Filter results by source"
              value={sourceFilter}
              onChange={(e) => setSourceFilter(e.target.value)}
              style={{ width: "auto" }}
              className="h-8 rounded-lg border border-border bg-background px-2.5 text-xs text-foreground shrink-0"
            >
              <option value="">All sources</option>
              {availableSources.map((src) => (
                <option key={src} value={src}>{src}</option>
              ))}
            </select>
          )}

          {signals && (
            <div className="ml-auto flex items-center gap-1.5 shrink-0">
              <ArrowUpDown size={12} className="text-muted-foreground" aria-hidden="true" />
              <select
                aria-label="Sort discovery results"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as "relevance" | "recency")}
                style={{ width: "auto" }}
                className="h-8 rounded-lg border border-border bg-background px-2.5 text-xs text-foreground"
              >
                <option value="relevance">Relevance</option>
                <option value="recency">Most recent</option>
              </select>
            </div>
          )}
        </div>
      </div>

      {/* Results Table */}
      {filteredSignals ? (
        filteredSignals.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left text-xs">
              <thead>
                <tr className="border-b border-border bg-muted/25 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  <th scope="col" className="py-2.5 pl-4 pr-3 min-w-[260px]">Discussion / Result</th>
                  <th scope="col" className="py-2.5 px-3 whitespace-nowrap">Source</th>
                  <th scope="col" className="py-2.5 px-3 whitespace-nowrap">Classification</th>
                  <th scope="col" className="py-2.5 px-3 whitespace-nowrap text-right">Relevance</th>
                  <th scope="col" className="py-2.5 px-3 whitespace-nowrap">Observed</th>
                  <th scope="col" className="py-2.5 pl-2 pr-4 whitespace-nowrap text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/80">
                {filteredSignals.map((sig) => (
                  <ResultTableRow
                    key={sig.id}
                    signal={sig}
                    isSaved={savedOverrides[sig.id] ?? sig.saved}
                    canWrite={canWrite}
                    onSelect={() => setSelectedSignal(sig)}
                    onToggleSave={() => void toggleSave(sig)}
                  />
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-6">
            <EmptyState
              title="No matching results"
              description={
                signals && signals.length > 0
                  ? "No results match your current filter. Clear the search or classification filter above."
                  : coverage || "No recent discussions matched your criteria on the checked sources. Use Discovery Copilot to broaden keywords or enable additional sources."
              }
            />
          </div>
        )
      ) : signalIds && signalIds.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left text-xs">
            <thead>
              <tr className="border-b border-border bg-muted/25 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                <th scope="col" className="py-2.5 pl-4 pr-3 min-w-[260px]">Discussion / Result</th>
                <th scope="col" className="py-2.5 px-3 whitespace-nowrap">Source</th>
                <th scope="col" className="py-2.5 px-3 whitespace-nowrap">Classification</th>
                <th scope="col" className="py-2.5 px-3 whitespace-nowrap text-right">Relevance</th>
                <th scope="col" className="py-2.5 px-3 whitespace-nowrap">Observed</th>
                <th scope="col" className="py-2.5 pl-2 pr-4 whitespace-nowrap text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/80">
              {signalIds.map((id) => (
                <HydratedSignalRow
                  key={id}
                  id={id}
                  searchQuery={searchQuery}
                  sourceFilter={sourceFilter}
                  classFilter={classFilter}
                  onSelect={setSelectedSignal}
                  onToggleSave={(sig) => void toggleSave(sig)}
                  savedOverrides={savedOverrides}
                  canWrite={canWrite}
                />
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="p-6">
          <EmptyState
            title="No matching discussions found"
            description="No discussions matched the reviewed criteria on the checked sources. Use Discovery Copilot to broaden keywords, remove exclusions, or enable additional sources."
          />
        </div>
      )}

      {/* Focused Signal Detail Drawer */}
      <SignalDetailDrawer
        signal={selectedSignal}
        isSaved={selectedSignal ? (savedOverrides[selectedSignal.id] ?? selectedSignal.saved) : false}
        canWrite={canWrite}
        onToggleSave={() => selectedSignal && void toggleSave(selectedSignal)}
        onClose={() => setSelectedSignal(null)}
      />
    </section>
  );
}
