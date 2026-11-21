"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  AlertTriangle,
  ArrowLeft,
  Bookmark,
  ChevronDown,
  ChevronUp,
  Edit3,
  Loader2,
  MoreHorizontal,
  Play,
  RotateCcw,
  SlidersHorizontal,
  Sparkles,
  Trash2,
} from "lucide-react";
import type { DiscoveryRun, IntentJob } from "@/lib/intent-radar";
import { Button } from "@/components/ui/button";
import { Menu, MenuContent } from "@/components/ui/menu";
import { ErrorState, LoadingSkeleton } from "../ui";
import { ProviderLogo } from "../provider-logo";
import { useRadarCapabilities, useRadarMutation, useRadarRead } from "../provider";
import { InlineResultsPanel } from "./InlineResultsPanel";
import { DISCOVERY_PRELOAD_KEY } from "./DiscoveryCopilotPanel";
import { DISCOVERY_HISTORY_RETURN_KEY } from "./DiscoveryHistoryView";

const SOURCE_LABELS: Record<string, string> = {
  hacker_news: "Hacker News",
  stack_exchange: "Stack Exchange",
  github: "GitHub",
  youtube: "YouTube",
  bluesky: "Bluesky",
  discourse: "Discourse",
  rss: "RSS",
  atom: "Atom",
};

function statusLabel(status: string, matched: number): { text: string; tone: string } {
  const s = status.toUpperCase();
  if (s === "NO_RESULTS" || ((s === "COMPLETED" || s === "COMPLETE") && matched === 0)) {
    return { text: "No Results", tone: "bg-muted text-muted-foreground" };
  }
  if (s === "COMPLETED" || s === "COMPLETE") {
    return { text: "Completed", tone: "bg-emerald-500/12 text-emerald-700 dark:text-emerald-300" };
  }
  if (s === "PARTIAL") {
    return { text: "Partial", tone: "bg-amber-500/12 text-amber-700 dark:text-amber-300" };
  }
  if (s === "FAILED") {
    return { text: "Failed", tone: "bg-destructive/12 text-destructive" };
  }
  return { text: status, tone: "bg-blue-500/12 text-blue-700 dark:text-blue-300" };
}

export function DiscoveryRunDetailView({ id }: { id: string }) {
  const router=useRouter();
  const access = useRadarCapabilities();
  const mutation = useRadarMutation();
  const query = useRadarRead<DiscoveryRun>(`/discoveries/${id}`);
  const icps = useRadarRead<{ items: { id: string; name: string }[] }>("/icps");

  const [configOpen, setConfigOpen] = useState(false);
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const [renaming, setRenaming] = useState(false);
  const [renameTitle, setRenameTitle] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [notice, setNotice] = useState("");
  const [err, setErr] = useState("");

  function handleBackToHistory() {
    let target = "/intent-radar/discover";
    try {
      const raw = sessionStorage.getItem(DISCOVERY_HISTORY_RETURN_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as { url?: string };
        if (parsed.url && (parsed.url.startsWith("/intent-radar/discover/history") || parsed.url.startsWith("/intent-radar/discover"))) {
          target = parsed.url;
        }
      }
    } catch {
      // fallback cleanly
    }
    router.push(target);
  }

  if (query.error) {
    return (
      <div className="ir-page space-y-4">
        <div>
          <Button variant="outline" size="sm" onClick={handleBackToHistory} className="gap-1.5">
            <ArrowLeft size={14} aria-hidden="true" />
            Back to Discovery History
          </Button>
        </div>
        <ErrorState message={query.error.message} retry={() => void query.refetch()} />
      </div>
    );
  }

  if (!query.data) {
    return (
      <div className="ir-page space-y-4">
        <div>
          <Button variant="outline" size="sm" onClick={handleBackToHistory} className="gap-1.5">
            <ArrowLeft size={14} aria-hidden="true" />
            Back to Discovery History
          </Button>
        </div>
        <LoadingSkeleton />
      </div>
    );
  }

  const run = query.data;
  const st = statusLabel(run.status, run.matched_count);
  const icpName = run.configuration.icp_id
    ? icps.data?.items.find((i) => i.id === run.configuration.icp_id)?.name || "Workspace ICP"
    : "None";

  const failedSources = run.source_runs.filter((sr) => !["COMPLETE", "NO_RESULTS"].includes(sr.status));
  const partialWarning =
    failedSources.length > 0
      ? `Partial completion: ${failedSources.map((s) => `${SOURCE_LABELS[s.provider] || s.provider} (${s.status})`).join(", ")}. Results from completed sources are shown below.`
      : null;

  function reuseAndRefine() {
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
    router.push("/intent-radar/discover/new");
  }

  async function rerunAsNew() {
    setErr("");
    setNotice("");
    try {
      const res = (await mutation.mutateAsync({
        path: "/discover",
        body: {
          configuration: run.configuration,
          request_id: crypto.randomUUID(),
          title: run.title,
          original_prompt: run.original_prompt,
          search_mode: "rerun",
          parent_discovery_id: run.id,
          strategy: run.strategy || null,
        },
      })) as IntentJob;
      const targetRunId = res.discovery_id || res.id;
      router.push(`/intent-radar/discover/runs/${targetRunId}`);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not start linked rerun.");
    }
  }

  async function saveSearch() {
    setErr("");
    setNotice("");
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
      setNotice("Saved to Saved Searches.");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not save search.");
    }
  }

  async function handleRename() {
    if (!renameTitle.trim()) return;
    setErr("");
    try {
      await mutation.mutateAsync({
        path: `/discoveries/${run.id}`,
        method: "PATCH",
        body: { title: renameTitle.trim() },
      });
      setRenaming(false);
      setNotice("Discovery renamed.");
      void query.refetch();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not rename discovery.");
    }
  }

  async function handleDelete() {
    setErr("");
    try {
      await mutation.mutateAsync({
        path: `/discoveries/${run.id}`,
        method: "DELETE",
      });
      handleBackToHistory();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not delete discovery.");
    }
  }

  return (
    <div className="ir-page space-y-5">
      {/* A. Prominent, Reliable Back Navigation */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={handleBackToHistory}
          className="gap-1.5 text-xs font-semibold focus-visible:ring-2 focus-visible:ring-primary"
        >
          <ArrowLeft size={14} aria-hidden="true" />
          Back to Discovery History
        </Button>

        {run.parent_discovery_id && (
          <Link
            href={`/intent-radar/discover/runs/${run.parent_discovery_id}`}
            className="text-xs font-medium text-primary hover:underline"
          >
            View parent discovery →
          </Link>
        )}
      </div>

      {/* B. Compact Discovery Header */}
      <header className="flex flex-wrap items-start justify-between gap-4 border-b border-border pb-4">
        <div className="min-w-0 flex-1 space-y-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-xl font-semibold tracking-tight text-foreground break-words">
              {run.title}
            </h1>
            <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${st.tone}`}>
              {st.text}
            </span>
            <span className="rounded-md border border-border bg-muted/40 px-2 py-0.5 text-[10px] font-semibold uppercase text-muted-foreground">
              {run.search_mode}
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
            <span>Executed {new Date(run.created_at).toLocaleString()}</span>
            <span>·</span>
            <div className="inline-flex flex-wrap items-center gap-1.5">
              {run.sources.map((src) => (
                <span key={src} className="inline-flex items-center gap-1 text-foreground font-medium">
                  <ProviderLogo provider={SOURCE_LABELS[src] || src} size={13} />
                  {SOURCE_LABELS[src] || src}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Grouped Compact Actions */}
        <div className="flex flex-wrap items-center gap-2 shrink-0">
          {access.data?.can_write && (
            <Button size="sm" disabled={mutation.isPending} onClick={() => void rerunAsNew()} className="gap-1.5 text-xs">
              {mutation.isPending ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />}
              Rerun
            </Button>
          )}
          <Button size="sm" variant="outline" onClick={reuseAndRefine} className="gap-1.5 text-xs">
            <RotateCcw size={13} /> Reuse &amp; Refine
          </Button>
          {access.data?.can_write && (
            <Button size="sm" variant="outline" disabled={mutation.isPending} onClick={() => void saveSearch()} className="gap-1.5 text-xs">
              <Bookmark size={13} /> Save Search
            </Button>
          )}
          {access.data?.can_write && (
            <Menu.Root>
              <Menu.Trigger asChild>
                <Button size="sm" variant="outline" aria-label="More discovery actions" className="h-8 w-8 p-0">
                  <MoreHorizontal size={14} />
                </Button>
              </Menu.Trigger>
              <MenuContent align="end" className="w-44 p-1 text-xs">
                <Menu.Item
                  onSelect={() => {
                    setRenameTitle(run.title);
                    setRenaming(true);
                  }}
                  className="flex items-center gap-2 rounded-md px-2.5 py-1.5 cursor-pointer hover:bg-muted outline-none"
                >
                  <Edit3 size={13} /> Rename Discovery
                </Menu.Item>
                <Menu.Separator className="my-1 h-px bg-border" />
                <Menu.Item
                  onSelect={() => setConfirmDelete(true)}
                  className="flex items-center gap-2 rounded-md px-2.5 py-1.5 cursor-pointer text-destructive hover:bg-destructive/10 outline-none"
                >
                  <Trash2 size={13} /> Delete from History
                </Menu.Item>
              </MenuContent>
            </Menu.Root>
          )}
        </div>
      </header>

      {notice && (
        <div role="status" className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-2 text-xs text-emerald-700 dark:text-emerald-300">
          {notice}
        </div>
      )}
      {err && <ErrorState message={err} />}

      {/* Failed / Incomplete Sources Banner with Retry Action */}
      {failedSources.length > 0 && (
        <div className="rounded-xl border border-amber-500/35 bg-amber-500/10 p-3.5 space-y-2 text-xs text-amber-900 dark:text-amber-100">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2 font-semibold">
              <AlertTriangle size={14} className="text-amber-600 dark:text-amber-400" />
              <span>Source Execution Notice</span>
            </div>
            {access.data?.can_write && (
              <Button
                size="sm"
                variant="outline"
                disabled={mutation.isPending||!run.job_id||run.attempts>=3||!['PARTIAL','FAILED'].includes(run.status)}
                onClick={async()=>{try{await mutation.mutateAsync({path:`/jobs/${run.job_id}/retry`});await query.refetch();setNotice('Recovery requested for the original discovery.')}catch(e){setErr(e instanceof Error?e.message:'Retry unavailable.')}}
                className="h-7 text-xs bg-background/80 hover:bg-background border-amber-500/40 text-amber-900 dark:text-amber-100 font-semibold cursor-pointer"
              >
                Retry Failed Sources
              </Button>
            )}
          </div>
          <p className="leading-relaxed text-amber-800 dark:text-amber-200">
            {failedSources.map((s) =>
              s.provider === "hacker_news" && s.status === "TIMED_OUT"
                ? "Hacker News could not complete this check. No reliable result count is available for this source."
                : `${SOURCE_LABELS[s.provider] || s.provider} could not complete this check (${s.status}).`
            ).join(" ")}
          </p>
        </div>
      )}

      {/* C. Compact 4-Metric Execution Summary (Zero duplication) */}
      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-xl border border-border bg-card px-4 py-3">
          <dt className="text-[11px] font-medium text-muted-foreground">Matching Results</dt>
          <dd className="mt-0.5 text-lg font-semibold text-foreground tabular-nums">{run.matched_count}</dd>
        </div>
        <div className="rounded-xl border border-border bg-card px-4 py-3">
          <dt className="text-[11px] font-medium text-muted-foreground">Items Scanned</dt>
          <dd className="mt-0.5 text-lg font-semibold text-foreground tabular-nums">{run.scanned_count??'Unknown'}</dd>
        </div>
        <div className="rounded-xl border border-border bg-card px-4 py-3">
          <dt className="text-[11px] font-medium text-muted-foreground">Sources Checked</dt>
          <dd className="mt-0.5 text-lg font-semibold text-foreground tabular-nums">
            {run.source_runs.length}
          </dd>
        </div>
        <div className="rounded-xl border border-border bg-card px-4 py-3">
          <dt className="text-[11px] font-medium text-muted-foreground">API Requests</dt>
          <dd className="mt-0.5 text-lg font-semibold text-foreground tabular-nums">{run.requests_count??'Unknown'}</dd>
        </div>
      </dl>

      {/* F. Primary Focus: Table-Based Discovery Results */}
      <InlineResultsPanel
        discoveryId={run.id}
        signals={run.signals || []}
        scannedCount={run.scanned_count??undefined}
        matchedCount={run.matched_count}
        coverage={run.coverage}
        partialWarning={partialWarning}
        hidePermanentLink
        onRefineWithCopilot={reuseAndRefine}
      />

      {/* D. Compact Expandable Search Configuration (Immutable Snapshot) */}
      <section className="rounded-2xl border border-border bg-card overflow-hidden">
        <button
          type="button"
          aria-expanded={configOpen}
          onClick={() => setConfigOpen((v) => !v)}
          style={{ justifyContent: "space-between" }}
          className="flex w-full items-center justify-between gap-3 px-5 py-3.5 text-left hover:bg-muted/25 transition-colors cursor-pointer"
        >
          <div className="flex items-center gap-2 min-w-0">
            <SlidersHorizontal size={14} className="text-primary shrink-0" />
            <span className="text-sm font-semibold text-foreground">Search Configuration</span>
            <span className="text-xs text-muted-foreground truncate">
              · {run.keywords.length} keywords · {run.sources.length} sources · Immutable snapshot
            </span>
          </div>
          {configOpen ? <ChevronUp size={15} className="text-muted-foreground" /> : <ChevronDown size={15} className="text-muted-foreground" />}
        </button>

        {configOpen && (
          <div className="border-t border-border p-5 space-y-4 text-xs">
            {run.original_prompt && (
              <div className="rounded-xl border border-border/70 bg-muted/20 p-3">
                <span className="text-[11px] font-semibold text-muted-foreground">Original Objective</span>
                <p className="mt-1 text-foreground leading-relaxed">{run.original_prompt}</p>
              </div>
            )}

            {run.strategy && (
              <div className="rounded-xl border border-primary/20 bg-primary/[0.03] p-3.5 space-y-1.5">
                <div className="inline-flex items-center gap-1.5 font-semibold text-foreground">
                  <Sparkles size={13} className="text-primary" /> Recorded AI Strategy
                </div>
                <p className="text-foreground">{run.strategy.objective}</p>
                <p className="text-muted-foreground">{run.strategy.keyword_rationale}</p>
                <p className="text-muted-foreground">{run.strategy.source_rationale}</p>
              </div>
            )}

            <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              <div>
                <dt className="text-[11px] text-muted-foreground">Keywords</dt>
                <dd className="mt-1 flex flex-wrap gap-1">
                  {run.keywords.map((k) => (
                    <span key={k} className="rounded-md bg-primary/10 px-2 py-0.5 text-[11px] font-medium text-primary">
                      {k}
                    </span>
                  ))}
                </dd>
              </div>
              <div>
                <dt className="text-[11px] text-muted-foreground">Exclusions</dt>
                <dd className="mt-1 font-medium text-foreground">
                  {run.configuration.excluded?.length ? run.configuration.excluded.join(", ") : "None"}
                </dd>
              </div>
              <div>
                <dt className="text-[11px] text-muted-foreground">Intent Categories</dt>
                <dd className="mt-1 font-medium text-foreground">
                  {run.configuration.categories?.length ? run.configuration.categories.join(", ") : "All types"}
                </dd>
              </div>
              <div>
                <dt className="text-[11px] text-muted-foreground">ICP Used</dt>
                <dd className="mt-1 font-medium text-foreground">{icpName}</dd>
              </div>
              <div>
                <dt className="text-[11px] text-muted-foreground">Date Window &amp; Limit</dt>
                <dd className="mt-1 font-medium text-foreground">
                  {run.configuration.from_date || "Any"} → {run.configuration.to_date || "Latest"} · Limit {run.configuration.result_limit}
                </dd>
              </div>
              <div>
                <dt className="text-[11px] text-muted-foreground">Minimum Relevance</dt>
                <dd className="mt-1 font-medium text-foreground">{run.configuration.min_relevance || 0}/100</dd>
              </div>
            </dl>
          </div>
        )}
      </section>

      {/* E. Compact Expandable Source Execution Table */}
      {run.source_runs.length > 0 && (
        <section className="rounded-2xl border border-border bg-card overflow-hidden">
          <button
            type="button"
            aria-expanded={sourcesOpen}
            onClick={() => setSourcesOpen((v) => !v)}
            style={{ justifyContent: "space-between" }}
            className="flex w-full items-center justify-between gap-3 px-5 py-3.5 text-left hover:bg-muted/25 transition-colors cursor-pointer"
          >
            <div className="flex items-center gap-2 min-w-0">
              <span className="text-sm font-semibold text-foreground">Source Execution Details</span>
              <span className="text-xs text-muted-foreground">
                · {run.source_runs.length} {run.source_runs.length === 1 ? "provider" : "providers"}
              </span>
            </div>
            {sourcesOpen ? <ChevronUp size={15} className="text-muted-foreground" /> : <ChevronDown size={15} className="text-muted-foreground" />}
          </button>

          {sourcesOpen && (
            <div className="border-t border-border overflow-x-auto">
              <table className="w-full border-collapse text-left text-xs">
                <thead>
                  <tr className="border-b border-border bg-muted/25 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    <th scope="col" className="py-2.5 pl-5 pr-3">Provider</th>
                    <th scope="col" className="py-2.5 px-3">Status</th>
                    <th scope="col" className="py-2.5 px-3 text-right">Checked</th>
                    <th scope="col" className="py-2.5 px-3 text-right">Matches</th>
                    <th scope="col" className="py-2.5 pl-3 pr-5">Coverage / Notes</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/80">
                  {run.source_runs.map((sr) => (
                    <tr key={sr.provider}>
                      <td className="py-2.5 pl-5 pr-3 font-medium text-foreground whitespace-nowrap">
                        <span className="inline-flex items-center gap-1.5">
                          <ProviderLogo provider={SOURCE_LABELS[sr.provider] || sr.provider} size={13} />
                          {SOURCE_LABELS[sr.provider] || sr.provider}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 whitespace-nowrap">
                        <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-semibold text-foreground">
                          {sr.status}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-right tabular-nums text-muted-foreground">{sr.scanned??'Unknown'}</td>
                      <td className="py-2.5 px-3 text-right tabular-nums font-semibold text-foreground">{sr.signals_count}</td>
                      <td className="py-2.5 pl-3 pr-5 text-muted-foreground">{sr.coverage || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {/* Rename Modal */}
      {renaming && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-4"
          role="dialog"
          aria-modal="true"
          aria-label="Rename discovery"
          onClick={() => setRenaming(false)}
        >
          <div className="w-full max-w-md rounded-2xl border border-border bg-card p-5 shadow-2xl space-y-4" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-sm font-semibold text-foreground">Rename Discovery</h3>
            <input
              autoFocus
              value={renameTitle}
              maxLength={120}
              onChange={(e) => setRenameTitle(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") void handleRename();
              }}
              className="h-9 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground"
            />
            <div className="flex justify-end gap-2">
              <Button size="sm" variant="outline" onClick={() => setRenaming(false)}>Cancel</Button>
              <Button size="sm" disabled={!renameTitle.trim() || mutation.isPending} onClick={() => void handleRename()}>Save</Button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {confirmDelete && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-4"
          role="dialog"
          aria-modal="true"
          aria-label="Delete discovery"
          onClick={() => setConfirmDelete(false)}
        >
          <div className="w-full max-w-md rounded-2xl border border-border bg-card p-5 shadow-2xl space-y-4" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-sm font-semibold text-foreground">Remove from Discovery History?</h3>
            <p className="text-xs text-muted-foreground leading-relaxed">
              This hides “{run.title}” from Discovery History. Stored signals remain intact.
            </p>
            <div className="flex justify-end gap-2">
              <Button size="sm" variant="outline" onClick={() => setConfirmDelete(false)}>Cancel</Button>
              <Button size="sm" variant="destructive" disabled={mutation.isPending} onClick={() => void handleDelete()}>Remove</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
