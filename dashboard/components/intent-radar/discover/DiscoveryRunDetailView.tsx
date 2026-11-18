"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  Bookmark,
  Loader2,
  Play,
  RotateCcw,
  Sparkles,
} from "lucide-react";
import type { DiscoveryRun, IntentJob } from "@/lib/intent-radar";
import { Button } from "@/components/ui/button";
import { Badge, ErrorState, LoadingSkeleton, PageHeading } from "../ui";
import { useRadarCapabilities, useRadarMutation, useRadarRead } from "../provider";
import { DiscoverNav } from "./DiscoverNav";
import { InlineResultsPanel } from "./InlineResultsPanel";
import { DISCOVERY_PRELOAD_KEY } from "./DiscoveryCopilotPanel";

export function DiscoveryRunDetailView({ id }: { id: string }) {
  const router = useRouter();
  const access = useRadarCapabilities();
  const mutation = useRadarMutation();
  const query = useRadarRead<DiscoveryRun>(`/discoveries/${id}`);
  const [notice, setNotice] = useState("");
  const [err, setErr] = useState("");

  if (query.error) {
    return (
      <div className="ir-page space-y-5">
        <DiscoverNav activeTab="history" />
        <ErrorState message={query.error.message} retry={() => void query.refetch()} />
      </div>
    );
  }
  if (!query.data) {
    return (
      <div className="ir-page space-y-5">
        <DiscoverNav activeTab="history" />
        <LoadingSkeleton />
      </div>
    );
  }

  const run = query.data;

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
    router.push("/intent-radar/discover");
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
      const params = new URLSearchParams();
      if (res.discovery_id) params.set("run", res.discovery_id);
      params.set("job", res.id);
      router.push(`/intent-radar/discover?${params.toString()}`);
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

  return (
    <div className="ir-page space-y-5">
      <div className="flex items-center gap-2 text-xs">
        <Link
          href="/intent-radar/discover/history"
          className="inline-flex items-center gap-1 font-medium text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft size={13} /> Back to Discovery History
        </Link>
      </div>

      <PageHeading
        title={run.title}
        description={`Executed ${new Date(run.created_at).toLocaleString()} · Immutable historical record`}
      />
      <DiscoverNav activeTab="history" />

      {/* Action Bar */}
      <div className="flex flex-wrap items-center gap-2.5">
        {access.data?.can_write && (
          <Button disabled={mutation.isPending} onClick={() => void rerunAsNew()} className="gap-1.5">
            {mutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
            Rerun as New Discovery
          </Button>
        )}
        <Button variant="outline" onClick={reuseAndRefine} className="gap-1.5">
          <RotateCcw size={14} /> Reuse &amp; Refine in Builder
        </Button>
        {access.data?.can_write && (
          <Button variant="outline" disabled={mutation.isPending} onClick={() => void saveSearch()} className="gap-1.5">
            <Bookmark size={14} /> Save as Search
          </Button>
        )}
        {run.parent_discovery_id && (
          <Link
            href={`/intent-radar/discover/runs/${run.parent_discovery_id}`}
            className="ml-auto text-xs font-medium text-primary hover:underline"
          >
            View parent discovery run →
          </Link>
        )}
      </div>

      {notice && (
        <div role="status" className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-2.5 text-xs text-emerald-700 dark:text-emerald-300">
          {notice}
        </div>
      )}
      {err && <ErrorState message={err} />}

      {/* Immutable Criteria & Strategy Snapshot */}
      <section className="rounded-2xl border border-border bg-card p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-semibold text-foreground">Original Criteria Snapshot</h2>
          <div className="flex items-center gap-2">
            <Badge>{run.status}</Badge>
            <Badge>{run.search_mode}</Badge>
          </div>
        </div>

        {run.original_prompt && (
          <div className="rounded-xl border border-border/80 bg-muted/20 p-3.5 text-xs">
            <span className="text-[11px] font-semibold text-muted-foreground">Original prompt</span>
            <p className="mt-1 text-foreground">{run.original_prompt}</p>
          </div>
        )}

        {run.strategy && (
          <div className="rounded-xl border border-primary/20 bg-primary/[0.03] p-4 space-y-2 text-xs">
            <div className="flex items-center gap-1.5 font-semibold text-foreground">
              <Sparkles size={13} className="text-primary" /> Recorded AI Strategy
            </div>
            <p className="text-foreground">{run.strategy.objective}</p>
            <p className="text-muted-foreground">{run.strategy.keyword_rationale}</p>
            <p className="text-muted-foreground">{run.strategy.source_rationale}</p>
          </div>
        )}

        <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 text-xs">
          <div className="rounded-xl border border-border/80 bg-muted/20 p-3">
            <dt className="text-muted-foreground">Keywords</dt>
            <dd className="mt-1 font-medium text-foreground">{run.keywords.join(", ") || "—"}</dd>
          </div>
          <div className="rounded-xl border border-border/80 bg-muted/20 p-3">
            <dt className="text-muted-foreground">Sources</dt>
            <dd className="mt-1 font-medium text-foreground">{run.sources.join(", ")}</dd>
          </div>
          <div className="rounded-xl border border-border/80 bg-muted/20 p-3">
            <dt className="text-muted-foreground">Exclusions</dt>
            <dd className="mt-1 font-medium text-foreground">
              {run.configuration.excluded?.length ? run.configuration.excluded.join(", ") : "None"}
            </dd>
          </div>
          <div className="rounded-xl border border-border/80 bg-muted/20 p-3">
            <dt className="text-muted-foreground">Scan Stats</dt>
            <dd className="mt-1 font-medium text-foreground">
              {run.matched_count} matched · {run.scanned_count} scanned · {run.requests_count} reqs
            </dd>
          </div>
        </dl>

        {/* Per-source execution status */}
        {run.source_runs.length > 0 && (
          <div className="space-y-2">
            <h3 className="text-xs font-semibold text-foreground">Source Execution Summary</h3>
            <div className="grid gap-2 sm:grid-cols-2">
              {run.source_runs.map((sr) => (
                <div key={sr.provider} className="rounded-xl border border-border/70 bg-muted/15 p-3 text-xs space-y-1">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-semibold text-foreground capitalize">{sr.provider.replace("_", " ")}</span>
                    <Badge>{sr.status}</Badge>
                  </div>
                  <p className="text-[11px] text-muted-foreground">
                    {sr.signals_count} matched · {sr.scanned} scanned
                    {sr.requests !== null ? ` · ${sr.requests} requests` : ""}
                  </p>
                  {sr.coverage && <p className="text-[11px] text-muted-foreground">{sr.coverage}</p>}
                </div>
              ))}
            </div>
          </div>
        )}
      </section>

      {/* Retained Signals */}
      <InlineResultsPanel
        discoveryId={run.id}
        signals={run.signals || []}
        scannedCount={run.scanned_count}
        matchedCount={run.matched_count}
        coverage={run.coverage}
        onRefineWithCopilot={reuseAndRefine}
      />
    </div>
  );
}
