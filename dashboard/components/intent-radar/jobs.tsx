"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Loader2,
  RefreshCw,
  XCircle,
} from "lucide-react";
import type { IntentJob } from "@/lib/intent-radar";
import { Button } from "@/components/ui/button";
import { useRadarMutation, useRadarRead, useRadarRefresh } from "./provider";
import { ErrorState } from "./ui";

function humanJobState(job: IntentJob, matched: number): { label: string; tone: string } {
  const s = (job.status || "").toUpperCase();
  if (s === "QUEUED") return { label: "Queued", tone: "bg-blue-500/10 text-blue-700 dark:text-blue-300 border-blue-500/25" };
  if (s === "RUNNING") return { label: "Running", tone: "bg-blue-500/10 text-blue-700 dark:text-blue-300 border-blue-500/25" };
  if (s === "PARTIAL") return { label: "Partially Completed", tone: "bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/30" };
  if (s === "FAILED") return { label: "Failed", tone: "bg-destructive/10 text-destructive border-destructive/25" };
  if (s === "CANCELLED") return { label: "Cancelled", tone: "bg-muted text-muted-foreground border-border" };
  if (s === "COMPLETED" || s === "COMPLETE") {
    return matched === 0
      ? { label: "No Results", tone: "bg-muted text-muted-foreground border-border" }
      : { label: "Completed", tone: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/25" };
  }
  return { label: job.status, tone: "bg-muted text-muted-foreground border-border" };
}

export function JobPanel({
  id,
  onComplete,
}: {
  id: string;
  onComplete?: (job: IntentJob) => void;
}) {
  const query = useRadarRead<IntentJob>("/jobs/" + id);
  const mutation = useRadarMutation();
  const refresh = useRadarRefresh();
  const started = useRef(0);
  const complete = useRef("");
  const { refetch, dataUpdatedAt } = query;
  const active = Boolean(query.data && ["QUEUED", "RUNNING"].includes(query.data.status));

  useEffect(() => {
    started.current = Date.now();
  }, [id]);

  useEffect(() => {
    if (active && Date.now() - started.current < 180000) {
      const timer = setTimeout(() => {
        void refetch();
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [active, dataUpdatedAt, refetch]);

  useEffect(() => {
    if (active) {
      complete.current = "";
      return;
    }
    if (query.data && complete.current !== id) {
      complete.current = id;
      refresh();
      onComplete?.(query.data);
    }
  }, [query.data, active, id, refresh, onComplete]);

  if (query.error) return <ErrorState message={query.error.message} />;
  if (!query.data) {
    return (
      <div
        role="status"
        className="flex items-center gap-2 rounded-2xl border border-border bg-card p-5 text-xs text-muted-foreground"
      >
        <Loader2 size={15} className="animate-spin text-primary" aria-hidden="true" />
        Loading discovery execution status…
      </div>
    );
  }

  const job = query.data;
  const result = job.items[0]?.result;
  const matched = result?.matched ?? 0;
  const scanned = result?.scanned ?? 0;
  const requests = result?.requests ?? 0;
  const badge = humanJobState(job, matched);

  return (
    <section
      className="rounded-2xl border border-border bg-card p-5 space-y-4"
      aria-label="Discovery progress"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          {active ? (
            <Loader2 size={17} className="animate-spin text-primary shrink-0" aria-hidden="true" />
          ) : job.status === "FAILED" ? (
            <XCircle size={17} className="text-destructive shrink-0" aria-hidden="true" />
          ) : job.status === "PARTIAL" ? (
            <AlertTriangle size={17} className="text-amber-600 dark:text-amber-400 shrink-0" aria-hidden="true" />
          ) : (
            <CheckCircle2 size={17} className="text-emerald-600 dark:text-emerald-400 shrink-0" aria-hidden="true" />
          )}
          <div>
            <h3 className="text-sm font-semibold text-foreground">
              {active ? "Checking selected research sources…" : "Discovery execution summary"}
            </h3>
            <p className="text-xs text-muted-foreground">
              {result?.coverage ||
                "Bounded checks of your selected authorized sources. Per-source status updates as providers complete."}
            </p>
          </div>
        </div>

        <span className={`rounded-full border px-2.5 py-0.5 text-xs font-semibold ${badge.tone}`}>
          {badge.label}
        </span>
      </div>

      {/* Live Metrics */}
      <dl className="grid grid-cols-3 gap-3 text-center">
        <div className="rounded-xl bg-muted/25 px-3 py-2.5">
          <dt className="text-[11px] text-muted-foreground">Items checked</dt>
          <dd className="text-lg font-bold tabular-nums text-foreground">{scanned}</dd>
        </div>
        <div className="rounded-xl bg-muted/25 px-3 py-2.5">
          <dt className="text-[11px] text-muted-foreground">Matching discussions</dt>
          <dd className="text-lg font-bold tabular-nums text-foreground">{matched}</dd>
        </div>
        <div className="rounded-xl bg-muted/25 px-3 py-2.5">
          <dt className="text-[11px] text-muted-foreground">Source requests</dt>
          <dd className="text-lg font-bold tabular-nums text-foreground">{requests}</dd>
        </div>
      </dl>

      {/* Per-source status breakdown */}
      {!!job.sources?.length && (
        <ul className="divide-y divide-border rounded-xl border border-border overflow-hidden text-xs">
          {job.sources.map((s) => (
            <li
              key={s.provider}
              className="flex flex-wrap items-center justify-between gap-2 px-3.5 py-2.5 bg-muted/10"
            >
              <div className="min-w-0">
                <span className="font-semibold text-foreground capitalize">
                  {s.provider.replaceAll("_", " ")}
                </span>
                <span className="ml-2 text-muted-foreground">{s.coverage}</span>
                {s.retry_at && (
                  <span className="ml-2 text-amber-700 dark:text-amber-300">
                    Retry after {new Date(s.retry_at).toLocaleTimeString()}
                  </span>
                )}
              </div>
              <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-semibold text-foreground shrink-0">
                {s.status}
              </span>
            </li>
          ))}
        </ul>
      )}

      {job.items.some((i) => i.error_code) && (
        <ErrorState
          message={
            "Source or authorization failure: " +
            job.items.find((i) => i.error_code)?.error_code +
            ". No substitute results were created."
          }
        />
      )}

      <div className="flex flex-wrap items-center gap-2 pt-1">
        {active && (
          <Button
            size="sm"
            variant="outline"
            disabled={mutation.isPending}
            onClick={() => mutation.mutate({ path: "/jobs/" + id + "/cancel" })}
          >
            Cancel check
          </Button>
        )}
        {["PARTIAL", "FAILED"].includes(job.status) && job.attempts < 3 && (
          <Button
            size="sm"
            disabled={mutation.isPending}
            onClick={() => mutation.mutate({ path: "/jobs/" + id + "/retry" })}
          >
            Retry bounded check
          </Button>
        )}
        <Button
          size="sm"
          variant="ghost"
          onClick={() => void query.refetch()}
          className="gap-1.5 text-muted-foreground"
        >
          <RefreshCw size={13} /> Refresh status
        </Button>
        <Link
          href="/intent-radar/signals"
          className="ml-auto text-xs font-semibold text-primary hover:underline"
        >
          Review stored signals →
        </Link>
      </div>
    </section>
  );
}
