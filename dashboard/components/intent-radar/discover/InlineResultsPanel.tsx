"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { ArrowUpDown, ExternalLink, Filter, Sparkles } from "lucide-react";
import type { IntentSignal } from "@/lib/intent-radar";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState, LoadingSkeleton } from "../ui";
import { useRadarRead } from "../provider";
import { SignalCard } from "../signals";

const BUYER_INTENT_CATEGORIES = new Set([
  "Recommendation request",
  "Problem / pain point",
  "Product comparison",
  "Alternative search",
  "Tool / service evaluation",
  "Purchase consideration",
  "Feature request",
]);

function signalKindLabel(category: string): { label: string; tone: "buyer" | "market" } {
  if (BUYER_INTENT_CATEGORIES.has(category)) {
    return { label: "Buyer-Intent Signal", tone: "buyer" };
  }
  return { label: "Market / Tech Intelligence", tone: "market" };
}

function SignalByIdItem({
  id,
  sourceFilter,
  classFilter,
}: {
  id: string;
  sourceFilter: string;
  classFilter: string;
}) {
  const query = useRadarRead<IntentSignal>("/signals/" + id);
  if (query.error) return <ErrorState message={query.error.message} />;
  if (!query.data) return <LoadingSkeleton />;
  const sig = query.data;
  if (sourceFilter && sig.source.toLowerCase() !== sourceFilter.toLowerCase()) return null;
  const kind = signalKindLabel(sig.category);
  if (classFilter === "buyer" && kind.tone !== "buyer") return null;
  if (classFilter === "market" && kind.tone !== "market") return null;
  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-2">
        <span
          className={
            "rounded-full px-2.5 py-0.5 text-[10px] font-semibold " +
            (kind.tone === "buyer"
              ? "bg-emerald-500/12 text-emerald-700 dark:text-emerald-300"
              : "bg-sky-500/12 text-sky-700 dark:text-sky-300")
          }
        >
          {kind.label}
        </span>
        <span className="text-[11px] text-muted-foreground">{sig.category}</span>
      </div>
      <SignalCard signal={sig} />
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
  onRefineWithCopilot,
}: {
  discoveryId?: string | null;
  signals?: IntentSignal[];
  signalIds?: string[];
  scannedCount?: number;
  matchedCount?: number;
  coverage?: string;
  onRefineWithCopilot?: () => void;
}) {
  const [sourceFilter, setSourceFilter] = useState("");
  const [classFilter, setClassFilter] = useState<"all" | "buyer" | "market">("all");
  const [sortBy, setSortBy] = useState<"relevance" | "recency">("relevance");

  const availableSources = useMemo(() => {
    if (!signals) return [];
    return [...new Set(signals.map((s) => s.source))].sort();
  }, [signals]);

  const filteredSignals = useMemo(() => {
    if (!signals) return null;
    const list = signals.filter((sig) => {
      if (sourceFilter && sig.source !== sourceFilter) return false;
      const kind = signalKindLabel(sig.category);
      if (classFilter === "buyer" && kind.tone !== "buyer") return false;
      if (classFilter === "market" && kind.tone !== "market") return false;
      return true;
    });
    return [...list].sort((a, b) => {
      if (sortBy === "recency") {
        return new Date(b.observed_at).getTime() - new Date(a.observed_at).getTime();
      }
      return b.score - a.score;
    });
  }, [signals, sourceFilter, classFilter, sortBy]);

  const totalCount = matchedCount ?? (signals ? signals.length : signalIds?.length || 0);
  const buyerCount = signals
    ? signals.filter((s) => signalKindLabel(s.category).tone === "buyer").length
    : null;
  const marketCount = signals && buyerCount !== null ? signals.length - buyerCount : null;

  return (
    <section
      aria-label="Discovery Results"
      className="rounded-2xl border border-border bg-card p-5 sm:p-6 space-y-4"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-foreground">
            Discovery Results ({totalCount})
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            {scannedCount !== undefined ? `${scannedCount} items scanned · ` : ""}
            {buyerCount !== null && marketCount !== null
              ? `${buyerCount} buyer-intent · ${marketCount} market/tech intelligence`
              : "Matches retained from selected sources."}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {onRefineWithCopilot && (
            <Button size="sm" variant="outline" onClick={onRefineWithCopilot} className="gap-1.5 text-xs">
              <Sparkles size={13} /> Refine with Copilot
            </Button>
          )}
          {discoveryId && (
            <Link
              href={`/intent-radar/discover/runs/${discoveryId}`}
              className="inline-flex items-center gap-1 rounded-lg border border-border bg-background px-2.5 py-1.5 text-xs font-medium text-foreground hover:border-primary/50 hover:text-primary transition-colors"
            >
              Permanent run link <ExternalLink size={12} />
            </Link>
          )}
        </div>
      </div>

      {coverage && (
        <p className="rounded-xl bg-muted/30 px-3.5 py-2 text-[11px] text-muted-foreground">
          {coverage}
        </p>
      )}

      {/* Filter & Sort Toolbar */}
      <div className="flex flex-wrap items-center gap-2.5 border-y border-border/80 py-2.5 text-xs">
        <span className="inline-flex items-center gap-1 font-medium text-muted-foreground">
          <Filter size={12} aria-hidden="true" /> Filter:
        </span>

        <div className="inline-flex items-center rounded-lg border border-border bg-muted/25 p-0.5">
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
            className="rounded-lg border border-border bg-card px-2.5 py-1 text-xs text-foreground"
          >
            <option value="">All sources</option>
            {availableSources.map((src) => (
              <option key={src} value={src}>
                {src}
              </option>
            ))}
          </select>
        )}

        {signals && (
          <div className="ml-auto flex items-center gap-1.5">
            <ArrowUpDown size={12} className="text-muted-foreground" aria-hidden="true" />
            <select
              aria-label="Sort discovery results"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as "relevance" | "recency")}
              className="rounded-lg border border-border bg-card px-2.5 py-1 text-xs text-foreground"
            >
              <option value="relevance">Sort: Relevance</option>
              <option value="recency">Sort: Most recent</option>
            </select>
          </div>
        )}
      </div>

      {/* Results List */}
      {filteredSignals ? (
        filteredSignals.length > 0 ? (
          <div className="space-y-4">
            {filteredSignals.map((sig) => {
              const kind = signalKindLabel(sig.category);
              return (
                <div key={sig.id} className="space-y-1.5">
                  <div className="flex items-center gap-2">
                    <span
                      className={
                        "rounded-full px-2.5 py-0.5 text-[10px] font-semibold " +
                        (kind.tone === "buyer"
                          ? "bg-emerald-500/12 text-emerald-700 dark:text-emerald-300"
                          : "bg-sky-500/12 text-sky-700 dark:text-sky-300")
                      }
                    >
                      {kind.label}
                    </span>
                    <span className="text-[11px] text-muted-foreground">{sig.category}</span>
                  </div>
                  <SignalCard signal={sig} />
                </div>
              );
            })}
          </div>
        ) : (
          <EmptyState
            title="No matching discussions for these filters"
            description={
              signals && signals.length > 0
                ? "Try clearing the classification or source filter above."
                : "No recent discussions matched your criteria. Use Discovery Copilot to broaden keywords or add sources."
            }
          />
        )
      ) : signalIds && signalIds.length > 0 ? (
        <div className="space-y-4">
          {signalIds.map((id) => (
            <SignalByIdItem
              key={id}
              id={id}
              sourceFilter={sourceFilter}
              classFilter={classFilter}
            />
          ))}
        </div>
      ) : (
        <EmptyState
          title="No matching discussions found"
          description="No discussions matched the reviewed criteria on the checked sources. Use Discovery Copilot to broaden keywords, remove exclusions, or enable additional sources."
        />
      )}
    </section>
  );
}
