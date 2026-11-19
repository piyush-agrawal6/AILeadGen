"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  ArrowUpDown,
  Bookmark,
  BookmarkCheck,
  Briefcase,
  ChevronLeft,
  ChevronRight,
  Download,
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
    return { label: "Market Intelligence", tone: "market" };
  }
  if (BUYER_INTENT_CATEGORIES.has(sig.category)) {
    return { label: "Buyer Intent", tone: "buyer" };
  }
  return { label: "Market Intelligence", tone: "market" };
}

function formatRelativeTime(iso: string): string {
  const d = new Date(iso);
  const diff = Date.now() - d.getTime();
  if (Number.isNaN(diff)) return iso;
  if (diff < 60_000) return "just now";
  const mins = Math.floor(diff / 60_000);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days === 1) return "yesterday";
  if (days < 30) return `${days}d ago`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months}mo ago`;
  return `${Math.floor(months / 12)}y ago`;
}

function formatExactDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

/** Hydrates a single signal by ID into the table row when only signalIds are available (inline post-run). */
function HydratedSignalRow({
  id,
  searchQuery,
  sourceFilter,
  classFilter,
  onSelect,
  onToggleSave,
  onConvertToOpportunity,
  convertedIds,
  savedOverrides,
  canWrite,
}: {
  id: string;
  searchQuery: string;
  sourceFilter: string;
  classFilter: "all" | "buyer" | "market";
  onSelect: (sig: IntentSignal) => void;
  onToggleSave: (sig: IntentSignal) => void;
  onConvertToOpportunity: (sig: IntentSignal) => void;
  convertedIds: Set<string>;
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
  const isConverted = convertedIds.has(sig.id);

  return (
    <ResultTableRow
      signal={sig}
      isSaved={isSaved}
      isConverted={isConverted}
      canWrite={canWrite}
      onSelect={() => onSelect(sig)}
      onToggleSave={() => onToggleSave(sig)}
      onConvertToOpportunity={() => onConvertToOpportunity(sig)}
    />
  );
}

function ResultTableRow({
  signal,
  isSaved,
  isConverted,
  canWrite,
  onSelect,
  onToggleSave,
  onConvertToOpportunity,
}: {
  signal: IntentSignal;
  isSaved: boolean;
  isConverted: boolean;
  canWrite: boolean;
  onSelect: () => void;
  onToggleSave: () => void;
  onConvertToOpportunity: () => void;
}) {
  const kind = classifySignal(signal);
  const relTime = formatRelativeTime(signal.observed_at);
  const fullTime = formatExactDate(signal.observed_at);

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
      {/* 1. Conversation: Title, Excerpt, External Source Link */}
      <td className="py-3 pl-4 pr-3 max-w-md">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-[13px] text-foreground group-hover:text-primary transition-colors line-clamp-1">
            {signal.title}
          </span>
          {signal.source_url && (
            <a
              href={signal.source_url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              title="Open original thread"
              className="text-muted-foreground hover:text-foreground shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
            >
              <ExternalLink size={12} />
            </a>
          )}
        </div>
        {signal.excerpt && (
          <p className="mt-0.5 text-[11px] text-muted-foreground line-clamp-1">
            {signal.excerpt}
          </p>
        )}
      </td>

      {/* 2. Source: Provider logo & name */}
      <td className="py-3 px-3 whitespace-nowrap">
        <span className="inline-flex items-center gap-1.5 text-xs font-medium text-foreground">
          <ProviderLogo provider={signal.source} size={14} />
          <span>{signal.source}</span>
        </span>
      </td>

      {/* 3. Relevance: Score pill with color coding */}
      <td className="py-3 px-3 whitespace-nowrap">
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

      {/* 4. Intent: Intent category badge + buyer/market classification */}
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
            {signal.category || kind.label}
          </span>
          <span className="text-[10px] text-muted-foreground pl-0.5">{kind.label}</span>
        </div>
      </td>

      {/* 5. Observed: Relative timestamp with full date tooltip */}
      <td className="py-3 px-3 whitespace-nowrap text-xs text-muted-foreground" title={fullTime}>
        {relTime}
      </td>

      {/* 6. Actions: View Details, Save Signal, Convert to Opportunity */}
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
            title="View full evidence and details"
            className="inline-flex h-7 items-center gap-1 rounded-md border border-border bg-background px-2 text-[11px] font-medium text-foreground hover:border-primary/50 hover:text-primary cursor-pointer"
          >
            <Eye size={12} />
            <span className="hidden sm:inline">Details</span>
          </button>

          {canWrite && (
            <>
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

              <button
                type="button"
                onClick={onConvertToOpportunity}
                disabled={isConverted}
                aria-label={`Convert ${signal.title} to opportunity`}
                title={isConverted ? "Already converted to Opportunity" : "Convert to Opportunity / Add to Leads"}
                className={
                  "inline-flex h-7 items-center gap-1 rounded-md border px-2 text-[11px] font-medium transition-colors cursor-pointer " +
                  (isConverted
                    ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 cursor-default"
                    : "border-border bg-background text-muted-foreground hover:border-primary/50 hover:text-primary")
                }
              >
                <Briefcase size={12} />
                <span className="hidden md:inline">{isConverted ? "Added" : "Convert"}</span>
              </button>
            </>
          )}

          {signal.source_url && (
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
          )}
        </div>
      </td>
    </tr>
  );
}

function SignalDetailDrawer({
  signal,
  isSaved,
  isConverted,
  canWrite,
  onToggleSave,
  onConvertToOpportunity,
  onClose,
}: {
  signal: IntentSignal | null;
  isSaved: boolean;
  isConverted: boolean;
  canWrite: boolean;
  onToggleSave: () => void;
  onConvertToOpportunity: () => void;
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
  const fullTime = formatExactDate(signal.observed_at);

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
              {signal.source} · Observed {fullTime}
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
              <>
                <Button size="sm" variant={isSaved ? "default" : "outline"} onClick={onToggleSave} className="gap-1.5 text-xs">
                  {isSaved ? <BookmarkCheck size={13} /> : <Bookmark size={13} />}
                  {isSaved ? "Saved" : "Save Signal"}
                </Button>
                <Button
                  size="sm"
                  variant={isConverted ? "secondary" : "outline"}
                  disabled={isConverted}
                  onClick={onConvertToOpportunity}
                  className="gap-1.5 text-xs"
                >
                  <Briefcase size={13} />
                  {isConverted ? "Added to Opportunities" : "Convert to Opportunity"}
                </Button>
              </>
            )}
            {signal.source_url && (
              <a
                href={signal.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-border bg-card px-3 text-xs font-medium text-foreground hover:border-primary/50"
              >
                Open Source <ExternalLink size={12} />
              </a>
            )}
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
  const [convertedIds, setConvertedIds] = useState<Set<string>>(new Set());
  const [actionFeedback, setActionFeedback] = useState<string>("");
  const [page, setPage] = useState(1);
  const pageSize = 20;

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
      setActionFeedback(currentlySaved ? "Removed from saved signals." : "Saved signal to research.");
    } catch {
      setSavedOverrides((prev) => ({ ...prev, [sig.id]: currentlySaved }));
      setActionFeedback("Could not update saved status.");
    }
  }

  async function convertToOpportunity(sig: IntentSignal) {
    if (convertedIds.has(sig.id)) return;
    try {
      await mutation.mutateAsync({
        path: `/opportunities/${sig.id}`,
        method: "POST",
        body: { notes: "Created from Discover Results" },
      });
      setConvertedIds((prev) => new Set([...prev, sig.id]));
      setActionFeedback(`Promoted "${sig.title.slice(0, 40)}…" into an Opportunity.`);
    } catch (e) {
      setActionFeedback(e instanceof Error ? e.message : "Could not create opportunity.");
    }
  }

  function exportData(format: "csv" | "json") {
    const target = filteredSignals || signals || [];
    if (!target.length) return;

    if (format === "json") {
      const blob = new Blob([JSON.stringify(target, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `discover-results-${discoveryId || "run"}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } else {
      const headers = ["Title", "Source", "Relevance", "Category", "Observed At", "Source URL"];
      const rows = target.map((s) => [
        JSON.stringify(s.title || ""),
        JSON.stringify(s.source || ""),
        s.score,
        JSON.stringify(s.category || ""),
        JSON.stringify(s.observed_at || ""),
        JSON.stringify(s.source_url || ""),
      ]);
      const csv = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `discover-results-${discoveryId || "run"}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    }
    setActionFeedback(`Exported ${target.length} results as ${format.toUpperCase()}.`);
  }

  const totalCount = matchedCount ?? (signals ? signals.length : signalIds?.length || 0);
  const buyerCount = signals
    ? signals.filter((s) => classifySignal(s).tone === "buyer").length
    : null;
  const marketCount = signals && buyerCount !== null ? signals.length - buyerCount : null;
  const canWrite = Boolean(access.data?.can_write);

  // Pagination slice for filtered signals
  const paginatedSignals = useMemo(() => {
    if (!filteredSignals) return null;
    const start = (page - 1) * pageSize;
    return filteredSignals.slice(start, start + pageSize);
  }, [filteredSignals, page]);

  const totalPages = filteredSignals ? Math.ceil(filteredSignals.length / pageSize) : 1;

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
                ? `${buyerCount} buyer intent · ${marketCount} market intelligence`
                : "Live matches from checked sources."}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {(filteredSignals?.length || 0) > 0 && (
              <div className="inline-flex items-center gap-1">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => exportData("csv")}
                  className="h-8 gap-1 text-xs"
                  title="Export results as CSV"
                >
                  <Download size={12} /> CSV
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => exportData("json")}
                  className="h-8 gap-1 text-xs"
                  title="Export results as JSON"
                >
                  JSON
                </Button>
              </div>
            )}
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

        {actionFeedback && (
          <div role="status" className="rounded-lg border border-primary/30 bg-primary/10 px-3 py-2 text-xs text-primary flex items-center justify-between gap-2">
            <span>{actionFeedback}</span>
            <button
              type="button"
              onClick={() => setActionFeedback("")}
              className="rounded p-0.5 hover:bg-primary/20 text-primary cursor-pointer"
            >
              <X size={12} />
            </button>
          </div>
        )}

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
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setPage(1);
              }}
              placeholder="Filter results…"
              style={{ paddingLeft: "2rem" }}
              className="h-8 w-full rounded-lg border border-border bg-background pr-2.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          <div className="inline-flex items-center rounded-lg border border-border bg-muted/25 p-0.5 shrink-0">
            {(
              [
                ["all", "All"],
                ["buyer", "Buyer Intent"],
                ["market", "Market Intelligence"],
              ] as const
            ).map(([val, label]) => (
              <button
                key={val}
                type="button"
                onClick={() => {
                  setClassFilter(val);
                  setPage(1);
                }}
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
              onChange={(e) => {
                setSourceFilter(e.target.value);
                setPage(1);
              }}
              style={{ width: "auto" }}
              className="h-8 rounded-lg border border-border bg-background px-2.5 text-xs text-foreground shrink-0 focus:outline-none focus:ring-1 focus:ring-primary"
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
                className="h-8 rounded-lg border border-border bg-background px-2.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="relevance">Relevance score</option>
                <option value="recency">Most recent</option>
              </select>
            </div>
          )}
        </div>
      </div>

      {/* Results Table matching requested schema: | Conversation | Source | Relevance | Intent | Observed | Actions | */}
      {paginatedSignals ? (
        paginatedSignals.length > 0 ? (
          <div>
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-left text-xs">
                <thead>
                  <tr className="border-b border-border bg-muted/25 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    <th scope="col" className="py-2.5 pl-4 pr-3 min-w-[260px]">Conversation</th>
                    <th scope="col" className="py-2.5 px-3 whitespace-nowrap">Source</th>
                    <th scope="col" className="py-2.5 px-3 whitespace-nowrap">Relevance</th>
                    <th scope="col" className="py-2.5 px-3 whitespace-nowrap">Intent</th>
                    <th scope="col" className="py-2.5 px-3 whitespace-nowrap">Observed</th>
                    <th scope="col" className="py-2.5 pl-2 pr-4 whitespace-nowrap text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/80">
                  {paginatedSignals.map((sig) => (
                    <ResultTableRow
                      key={sig.id}
                      signal={sig}
                      isSaved={savedOverrides[sig.id] ?? sig.saved}
                      isConverted={convertedIds.has(sig.id)}
                      canWrite={canWrite}
                      onSelect={() => setSelectedSignal(sig)}
                      onToggleSave={() => void toggleSave(sig)}
                      onConvertToOpportunity={() => void convertToOpportunity(sig)}
                    />
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination Controls */}
            {totalPages > 1 && filteredSignals && (
              <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border bg-muted/15 px-4 py-2.5 text-xs text-muted-foreground">
                <span>
                  Showing <strong className="text-foreground">{(page - 1) * pageSize + 1}–{Math.min(page * pageSize, filteredSignals.length)}</strong> of{" "}
                  <strong className="text-foreground">{filteredSignals.length}</strong> results
                </span>
                <div className="flex items-center gap-1.5">
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={page <= 1}
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    className="h-7 px-2.5 text-xs gap-1"
                  >
                    <ChevronLeft size={13} /> Prev
                  </Button>
                  <span className="px-2 text-xs font-medium text-foreground">
                    {page} / {totalPages}
                  </span>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={page >= totalPages}
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    className="h-7 px-2.5 text-xs gap-1"
                  >
                    Next <ChevronRight size={13} />
                  </Button>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="p-6">
            <EmptyState
              title={partialWarning ? "Source check incomplete" : "No matching results"}
              description={
                partialWarning
                  ? partialWarning
                  : signals && signals.length > 0
                    ? "No results match your current filter. Clear the search or classification filter above."
                    : coverage || "No recent discussions matched your criteria on the checked sources. Use AI Discovery to broaden keywords or enable additional sources."
              }
            />
          </div>
        )
      ) : signalIds && signalIds.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left text-xs">
            <thead>
              <tr className="border-b border-border bg-muted/25 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                <th scope="col" className="py-2.5 pl-4 pr-3 min-w-[260px]">Conversation</th>
                <th scope="col" className="py-2.5 px-3 whitespace-nowrap">Source</th>
                <th scope="col" className="py-2.5 px-3 whitespace-nowrap">Relevance</th>
                <th scope="col" className="py-2.5 px-3 whitespace-nowrap">Intent</th>
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
                  onConvertToOpportunity={(sig) => void convertToOpportunity(sig)}
                  convertedIds={convertedIds}
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
            title={partialWarning ? "Source check incomplete" : "No matching discussions found"}
            description={
              partialWarning
                ? partialWarning
                : "No discussions matched the reviewed criteria on the checked sources. Broaden keywords, remove exclusions, or enable additional sources."
            }
          />
        </div>
      )}

      {/* Focused Signal Detail Drawer */}
      <SignalDetailDrawer
        signal={selectedSignal}
        isSaved={selectedSignal ? (savedOverrides[selectedSignal.id] ?? selectedSignal.saved) : false}
        isConverted={selectedSignal ? convertedIds.has(selectedSignal.id) : false}
        canWrite={canWrite}
        onToggleSave={() => selectedSignal && void toggleSave(selectedSignal)}
        onConvertToOpportunity={() => selectedSignal && void convertToOpportunity(selectedSignal)}
        onClose={() => setSelectedSignal(null)}
      />
    </section>
  );
}
