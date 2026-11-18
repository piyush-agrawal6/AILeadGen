"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Bookmark,
  ExternalLink,
  RotateCcw,
  Search,
  Trash2,
} from "lucide-react";
import type { DiscoveryRun, IntentPage } from "@/lib/intent-radar";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState, LoadingSkeleton, PageHeading } from "../ui";
import { useRadarCapabilities, useRadarMutation, useRadarRead } from "../provider";
import { DiscoverNav } from "./DiscoverNav";
import { DISCOVERY_PRELOAD_KEY } from "./DiscoveryCopilotPanel";

function statusTone(status: string) {
  const s = status.toUpperCase();
  if (s === "COMPLETED" || s === "COMPLETE") return "bg-emerald-500/12 text-emerald-700 dark:text-emerald-300";
  if (s === "PARTIAL") return "bg-amber-500/12 text-amber-700 dark:text-amber-300";
  if (s === "FAILED" || s === "CANCELLED") return "bg-destructive/12 text-destructive";
  return "bg-blue-500/12 text-blue-700 dark:text-blue-300";
}

export function DiscoveryHistoryView() {
  const router = useRouter();
  const access = useRadarCapabilities();
  const mutation = useRadarMutation();

  const [search, setSearch] = useState("");
  const [source, setSource] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState("");

  const params = new URLSearchParams({
    page: String(page),
    page_size: "15",
    ...(search.trim() ? { search: search.trim() } : {}),
    ...(source ? { source } : {}),
    ...(status ? { status } : {}),
  });

  const query = useRadarRead<IntentPage<DiscoveryRun>>(`/discoveries?${params.toString()}`);

  function reuseInBuilder(run: DiscoveryRun) {
    try {
      sessionStorage.setItem(
        DISCOVERY_PRELOAD_KEY,
        JSON.stringify({
          configuration: run.configuration,
          original_prompt: run.original_prompt,
          strategy: run.strategy,
          parent_discovery_id: run.id,
          title: run.title,
        })
      );
    } catch {
      // ignore storage errors
    }
    router.push("/intent-radar/discover");
  }

  async function saveAsSearch(run: DiscoveryRun) {
    setFeedback("");
    try {
      await mutation.mutateAsync({
        path: "/saved-searches",
        body: {
          name: run.title.slice(0, 120),
          description: run.original_prompt.slice(0, 400),
          original_prompt: run.original_prompt,
          configuration: run.configuration,
        },
      });
      setFeedback(`Saved "${run.title}" to Saved Searches.`);
    } catch (e) {
      setFeedback(e instanceof Error ? e.message : "Could not save search.");
    }
  }

  async function handleDelete(id: string) {
    setFeedback("");
    try {
      await mutation.mutateAsync({
        path: `/discoveries/${id}`,
        method: "DELETE",
      });
      setConfirmDeleteId(null);
      setFeedback("Removed run from Discovery History. Underlying signals were preserved.");
      void query.refetch();
    } catch (e) {
      setFeedback(e instanceof Error ? e.message : "Could not delete discovery run.");
    }
  }

  const totalPages = query.data ? Math.max(1, Math.ceil(query.data.total / query.data.page_size)) : 1;

  return (
    <div className="ir-page space-y-5">
      <PageHeading
        title="Discovery History"
        description="Every executed discovery run in this workspace, preserved with its original criteria and retained signals."
      />
      <DiscoverNav activeTab="history" />

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center gap-2.5 rounded-2xl border border-border bg-card p-3.5 text-xs">
        <div className="relative flex-1 min-w-[200px]">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input
            type="search"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            placeholder="Search by title, prompt, or keyword…"
            className="w-full rounded-lg border border-border bg-background pl-8 pr-3 py-1.5 text-xs text-foreground"
          />
        </div>

        <select
          aria-label="Filter by source"
          value={source}
          onChange={(e) => {
            setSource(e.target.value);
            setPage(1);
          }}
          className="rounded-lg border border-border bg-background px-2.5 py-1.5 text-xs text-foreground"
        >
          <option value="">All sources</option>
          <option value="hacker_news">Hacker News</option>
          <option value="stack_exchange">Stack Exchange</option>
          <option value="github">GitHub</option>
          <option value="youtube">YouTube</option>
          <option value="bluesky">Bluesky</option>
          <option value="discourse">Discourse</option>
          <option value="rss">RSS</option>
          <option value="atom">Atom</option>
        </select>

        <select
          aria-label="Filter by status"
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setPage(1);
          }}
          className="rounded-lg border border-border bg-background px-2.5 py-1.5 text-xs text-foreground"
        >
          <option value="">All statuses</option>
          <option value="COMPLETED">Completed</option>
          <option value="PARTIAL">Partial</option>
          <option value="NO_RESULTS">No results</option>
          <option value="RUNNING">Running</option>
          <option value="FAILED">Failed</option>
        </select>
      </div>

      {feedback && (
        <div role="status" className="rounded-xl border border-border bg-muted/30 px-4 py-2.5 text-xs text-foreground">
          {feedback}
        </div>
      )}

      {query.error ? (
        <ErrorState message={query.error.message} retry={() => void query.refetch()} />
      ) : !query.data ? (
        <LoadingSkeleton />
      ) : query.data.items.length === 0 ? (
        <EmptyState
          title="No discovery runs recorded yet"
          description="Run a discovery search from New Discovery to build a permanent, searchable history of your research runs."
        />
      ) : (
        <div className="space-y-3">
          {query.data.items.map((run) => (
            <article
              key={run.id}
              className="rounded-2xl border border-border bg-card p-4 sm:p-5 space-y-3 hover:border-primary/40 transition-colors"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0 flex-1 space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <Link
                      href={`/intent-radar/discover/runs/${run.id}`}
                      className="text-sm font-semibold text-foreground hover:text-primary transition-colors truncate"
                    >
                      {run.title}
                    </Link>
                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${statusTone(run.status)}`}>
                      {run.status}
                    </span>
                    <span className="rounded-full border border-border bg-muted/30 px-2 py-0.5 text-[10px] font-medium uppercase text-muted-foreground">
                      {run.search_mode}
                    </span>
                  </div>
                  {run.original_prompt && (
                    <p className="text-xs text-muted-foreground line-clamp-2">
                      “{run.original_prompt}”
                    </p>
                  )}
                </div>

                <div className="text-right text-[11px] text-muted-foreground shrink-0">
                  <div>{new Date(run.created_at).toLocaleString()}</div>
                  <div className="font-semibold text-foreground mt-0.5">
                    {run.matched_count} matched · {run.scanned_count} scanned
                  </div>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
                {run.sources.map((src) => (
                  <span key={src} className="rounded-md bg-muted px-2 py-0.5 font-medium text-foreground">
                    {src.replace("_", " ")}
                  </span>
                ))}
                {run.keywords.slice(0, 6).map((kw) => (
                  <span key={kw} className="rounded-md bg-primary/10 px-2 py-0.5 font-medium text-primary">
                    {kw}
                  </span>
                ))}
              </div>

              <div className="flex flex-wrap items-center gap-2 border-t border-border/70 pt-3">
                <Link
                  href={`/intent-radar/discover/runs/${run.id}`}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground hover:opacity-95"
                >
                  Open Results <ExternalLink size={12} />
                </Link>
                <Button size="sm" variant="outline" onClick={() => reuseInBuilder(run)} className="gap-1.5 text-xs">
                  <RotateCcw size={12} /> Reuse Criteria
                </Button>
                {access.data?.can_write && (
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={mutation.isPending}
                    onClick={() => void saveAsSearch(run)}
                    className="gap-1.5 text-xs"
                  >
                    <Bookmark size={12} /> Save as Search
                  </Button>
                )}

                {access.data?.can_write && (
                  <div className="ml-auto">
                    {confirmDeleteId === run.id ? (
                      <div className="inline-flex items-center gap-2 text-xs">
                        <span className="text-muted-foreground">Remove history entry? (Signals kept)</span>
                        <Button size="sm" variant="destructive" onClick={() => void handleDelete(run.id)}>
                          Confirm
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => setConfirmDeleteId(null)}>
                          Cancel
                        </Button>
                      </div>
                    ) : (
                      <button
                        type="button"
                        onClick={() => setConfirmDeleteId(run.id)}
                        aria-label={`Delete history entry ${run.title}`}
                        className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs text-muted-foreground hover:bg-destructive/10 hover:text-destructive cursor-pointer"
                      >
                        <Trash2 size={12} /> Delete
                      </button>
                    )}
                  </div>
                )}
              </div>
            </article>
          ))}

          {totalPages > 1 && (
            <div className="flex items-center justify-between pt-2 text-xs text-muted-foreground">
              <span>
                Page {page} of {totalPages} ({query.data.total} runs)
              </span>
              <div className="flex items-center gap-2">
                <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                  Previous
                </Button>
                <Button size="sm" variant="outline" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
                  Next
                </Button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
