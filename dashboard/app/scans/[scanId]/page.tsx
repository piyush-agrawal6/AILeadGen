"use client";
import { DeleteAction } from "@/components/intelligence/delete-action";

import { useQuery } from "@tanstack/react-query";
import {
AlertCircle,
ArrowRight,
Ban,
CheckCircle2,
Clock,
FileSpreadsheet,
Loader2,
RefreshCw
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import * as React from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card,CardContent,CardHeader,CardTitle } from "@/components/ui/card";
import { cancelScan,getScan,getScanEvents,resumeScan } from "@/lib/api";
import {
formatDate,
formatDuration,
formatNumber,
getStatusBadgeClass,
} from "@/lib/utils";
import type { PipelineEventSchema } from "@/types/api";

const STAGES = [
  { key: "MARKET", label: "Market Resolution" },
  { key: "DISCOVERY", label: "Registry Discovery" },
  { key: "DEDUPLICATION", label: "Normalization & Deduplication" },
  { key: "FILTERING", label: "Quality & Chain Filtering" },
  { key: "PROBE", label: "Website Reachability Probe" },
  { key: "CRAWL", label: "Contact Enrichment & Crawl" },
  { key: "AUDIT", label: "Technical & SEO Audits" },
  { key: "LIGHTHOUSE", label: "Lighthouse Performance Scans" },
  { key: "SCORING", label: "Opportunity Scoring & Ranking" },
  { key: "EXPORT", label: "Finalized XLSX & CSV Exports" },
];

export default function LiveScanPage() {
  const params = useParams();
  const runId = Number(params.scanId);

  const [liveEvents, setLiveEvents] = React.useState<PipelineEventSchema[]>([]);
  const [isCancelling, setIsCancelling] = React.useState(false);
  const [isResuming, setIsResuming] = React.useState(false);

  // Poll scan record
  const { data: scan, isLoading, refetch } = useQuery({
    queryKey: ["scan", runId],
    queryFn: () => getScan(runId),
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data && (data.status === "COMPLETED" || data.status === "FAILED" || data.status === "CANCELLED")) {
        return false;
      }
      return 2000;
    },
  });

  // Setup Server-Sent Events with fallback
  React.useEffect(() => {
    if (!runId) return;

    let eventSource: EventSource | null = null;
    let fallbackInterval: NodeJS.Timeout | null = null;

    try {
      const apiUrl = process.env.NEXT_PUBLIC_LEADENGINE_API_URL || "";
      const streamUrl = `${apiUrl}/api/scans/${runId}/events/stream`;
      eventSource = new EventSource(streamUrl);

      eventSource.addEventListener("pipeline_event", (e) => {
        try {
          const evt: PipelineEventSchema = JSON.parse(e.data);
          setLiveEvents((prev) => {
            if (prev.some((p) => p.id === evt.id)) return prev;
            return [...prev, evt];
          });
        } catch {}
      });

      eventSource.addEventListener("pipeline_finished", () => {
        refetch();
        if (eventSource) eventSource.close();
      });

      eventSource.onerror = () => {
        // Fallback to polling events if SSE disconnects
        if (eventSource) eventSource.close();
        fallbackInterval = setInterval(async () => {
          try {
            const evts = await getScanEvents(runId);
            setLiveEvents(evts);
          } catch {}
        }, 2500);
      };
    } catch {
      fallbackInterval = setInterval(async () => {
        try {
          const evts = await getScanEvents(runId);
          setLiveEvents(evts);
        } catch {}
      }, 2500);
    }

    return () => {
      if (eventSource) eventSource.close();
      if (fallbackInterval) clearInterval(fallbackInterval);
    };
  }, [runId, refetch]);

  // Initial event load
  React.useEffect(() => {
    getScanEvents(runId)
      .then((evts) => {
        if (evts && evts.length > 0) setLiveEvents(evts);
      })
      .catch(() => {});
  }, [runId]);

  const handleCancel = async () => {
    if (!confirm("Are you sure you want to stop this scan?")) return;
    setIsCancelling(true);
    try {
      await cancelScan(runId);
      toast.success("Cancellation requested");
      refetch();
    } catch (err: unknown) {
      toast.error((err instanceof Error ? err.message : "") || "Failed to cancel scan");
    } finally {
      setIsCancelling(false);
    }
  };

  const handleResume = async () => {
    setIsResuming(true);
    try {
      await resumeScan(runId);
      toast.success("Scan resumption queued");
      refetch();
    } catch (err: unknown) {
      toast.error((err instanceof Error ? err.message : "") || "Failed to resume scan");
    } finally {
      setIsResuming(false);
    }
  };

  if (isLoading || !scan) {
    return (
      <div className="flex h-96 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const isRunning = scan.status === "RUNNING" || scan.status === "QUEUED";
  const isFinished = scan.status === "COMPLETED";
  const isFailed = scan.status === "FAILED";
  const isCancelled = scan.status === "CANCELLED";

  // Determine stage completion based on events or scan stats
  const completedStages = new Set<string>();
  if (liveEvents.some((e) => e.stage === "MARKET" && e.event_type === "MARKET_RESOLVED")) completedStages.add("MARKET");
  if (scan.raw_found > 0 || liveEvents.some((e) => e.stage === "DISCOVERY")) completedStages.add("DISCOVERY");
  if (scan.deduped > 0 || liveEvents.some((e) => e.stage === "DEDUPLICATION")) completedStages.add("DEDUPLICATION");
  if (scan.filtered > 0 || liveEvents.some((e) => e.stage === "FILTERING")) completedStages.add("FILTERING");
  if (scan.websites_processed > 0 || liveEvents.some((e) => e.stage === "PROBE" && e.event_type === "HTTP_COMPLETE")) completedStages.add("PROBE");
  if (liveEvents.some((e) => e.stage === "CRAWL" && e.event_type === "CRAWL_COMPLETE")) completedStages.add("CRAWL");
  if (liveEvents.some((e) => e.stage === "AUDIT" && e.event_type === "AUDIT_COMPLETE")) completedStages.add("AUDIT");
  if (liveEvents.some((e) => e.stage === "LIGHTHOUSE" && e.event_type === "LIGHTHOUSE_COMPLETE")) completedStages.add("LIGHTHOUSE");
  if (scan.qualified > 0 || liveEvents.some((e) => e.stage === "SCORING")) completedStages.add("SCORING");
  if (scan.exported > 0 || isFinished) completedStages.add("EXPORT");

  return (
    <div className="space-y-8 max-w-6xl mx-auto">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border pb-6">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-bold tracking-tight text-foreground">
              {scan.market}
            </h2>
            <span
              className={`inline-flex items-center px-2.5 py-0.5 rounded text-xs font-semibold border ${getStatusBadgeClass(
                scan.status
              )}`}
            >
              {scan.status}
            </span>
          </div>
          <p className="text-xs text-muted-foreground mt-1 flex items-center gap-3">
            <span className="capitalize font-medium text-foreground">{scan.vertical}</span>
            <span>•</span>
            <span>Target: <strong className="text-foreground">{scan.target}</strong> leads</span>
            <span>•</span>
            <span>Started: {formatDate(scan.started_at)}</span>
            {scan.duration_seconds && (
              <>
                <span>•</span>
                <span>Runtime: {formatDuration(scan.duration_seconds)}</span>
              </>
            )}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <DeleteAction kind="scan" id={runId} redirect="/scans"/>
          {isRunning && (
            <Button
              variant="destructive"
              size="sm"
              disabled={isCancelling}
              onClick={handleCancel}
              className="gap-1.5 text-xs shadow-sm"
            >
              <Ban className="h-3.5 w-3.5" />
              <span>{isCancelling ? "Cancelling..." : "Cancel Scan"}</span>
            </Button>
          )}

          {(isFailed || isCancelled) && (
            <Button
              variant="outline"
              size="sm"
              disabled={isResuming}
              onClick={handleResume}
              className="gap-1.5 text-xs shadow-sm text-primary border-primary/30 hover:bg-primary/10"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              <span>{isResuming ? "Resuming..." : "Resume Scan"}</span>
            </Button>
          )}

          {scan.qualified > 0 && (
            <Link href={`/leads?run_id=${scan.id}`}>
              <Button size="sm" className="gap-1.5 text-xs shadow-sm bg-primary font-medium">
                <span>View Qualified Leads ({scan.qualified})</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </Button>
            </Link>
          )}
        </div>
      </div>

      {/* Live Metric Counters */}
      <div className="grid gap-3 grid-cols-2 sm:grid-cols-3 lg:grid-cols-6">
        <div className="rounded-lg border border-border bg-card/60 p-3.5">
          <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            Discovered
          </span>
          <div className="text-xl font-bold font-mono text-foreground mt-1">
            {formatNumber(scan.raw_found)}
          </div>
        </div>

        <div className="rounded-lg border border-border bg-card/60 p-3.5">
          <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            Unique Deduplicated
          </span>
          <div className="text-xl font-bold font-mono text-foreground mt-1">
            {formatNumber(scan.deduped)}
          </div>
        </div>

        <div className="rounded-lg border border-border bg-card/60 p-3.5">
          <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            Valid Prospects
          </span>
          <div className="text-xl font-bold font-mono text-foreground mt-1">
            {formatNumber(scan.filtered)}
          </div>
        </div>

        <div className="rounded-lg border border-border bg-card/60 p-3.5">
          <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            Websites Audited
          </span>
          <div className="text-xl font-bold font-mono text-foreground mt-1">
            {formatNumber(scan.websites_processed)}
          </div>
        </div>

        <div className="rounded-lg border border-border bg-card/60 p-3.5">
          <span className="text-[10px] font-medium uppercase tracking-wider text-primary">
            Qualified Leads
          </span>
          <div className="text-xl font-bold font-mono text-primary mt-1">
            {formatNumber(scan.qualified)}
          </div>
        </div>

        <div className="rounded-lg border border-border bg-card/60 p-3.5">
          <span className="text-[10px] font-medium uppercase tracking-wider text-emerald-400">
            Exported
          </span>
          <div className="text-xl font-bold font-mono text-emerald-400 mt-1">
            {formatNumber(scan.exported)}
          </div>
        </div>
      </div>

      {/* Main Grid: Pipeline Stages Checklist & Timeline Activity Log */}
      <div className="grid gap-6 md:grid-cols-5">
        {/* Stages Checklist (2 cols) */}
        <div className="md:col-span-2 space-y-4">
          <Card className="border-border bg-card/60">
            <CardHeader className="p-4 pb-3 border-b border-border">
              <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-semibold">
                Engine Pipeline Progression
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 space-y-3">
              {STAGES.map((st, idx) => {
                const isComplete = completedStages.has(st.key);
                return (
                  <div
                    key={st.key}
                    className={`flex items-center justify-between p-2.5 rounded-md border text-xs transition-colors ${
                      isComplete
                        ? "bg-emerald-500/5 border-emerald-500/20 text-foreground"
                        : "bg-muted/10 border-border text-muted-foreground"
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      <span className="font-mono text-[10px] text-muted-foreground w-4 text-right">
                        {idx + 1}.
                      </span>
                      <span className={isComplete ? "font-semibold text-foreground" : ""}>
                        {st.label}
                      </span>
                    </div>

                    {isComplete ? (
                      <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                    ) : isRunning && idx === completedStages.size ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin text-primary shrink-0" />
                    ) : (
                      <div className="h-2 w-2 rounded-full bg-muted-foreground/30 shrink-0" />
                    )}
                  </div>
                );
              })}
            </CardContent>
          </Card>

          {/* Download Artifacts Card if available */}
          {scan.output_file && (
            <Card className="border-border bg-card/60">
              <CardHeader className="p-4 pb-2 border-b border-border">
                <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-semibold flex items-center gap-1.5">
                  <FileSpreadsheet className="h-3.5 w-3.5 text-emerald-400" />
                  <span>Finalized Artifacts</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="p-4 space-y-2">
                <a
                  href={`/api/scans/${scan.id}/export/xlsx`}
                  target="_blank"
                  rel="noreferrer"
                  className="w-full inline-block"
                >
                  <Button variant="outline" size="sm" className="w-full text-xs gap-2 h-9 border-border">
                    <FileSpreadsheet className="h-3.5 w-3.5 text-emerald-400" />
                    <span>Download Excel Workbook (.xlsx)</span>
                  </Button>
                </a>
                <a
                  href={`/api/scans/${scan.id}/export/csv`}
                  target="_blank"
                  rel="noreferrer"
                  className="w-full inline-block"
                >
                  <Button variant="outline" size="sm" className="w-full text-xs gap-2 h-9 border-border">
                    <span>Download CSV Export (.csv)</span>
                  </Button>
                </a>
              </CardContent>
            </Card>
          )}

          {/* Error Message if Failed */}
          {scan.error_message && (
            <div className="rounded-lg border border-destructive/20 bg-destructive/10 p-4 text-xs">
              <div className="flex items-center gap-2 text-destructive font-semibold">
                <AlertCircle className="h-4 w-4" />
                <span>Execution Error</span>
              </div>
              <p className="mt-1 text-muted-foreground font-mono text-[11px] break-words">
                {scan.error_message}
              </p>
            </div>
          )}
        </div>

        {/* Activity Log Timeline (3 cols) */}
        <div className="md:col-span-3 space-y-4">
          <Card className="border-border bg-card/60 flex flex-col h-[560px]">
            <CardHeader className="p-4 pb-3 border-b border-border flex flex-row items-center justify-between">
              <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-semibold flex items-center gap-2">
                <Clock className="h-3.5 w-3.5 text-muted-foreground" />
                <span>Engine Activity Log</span>
              </CardTitle>
              {isRunning && (
                <span className="flex items-center gap-1 text-[11px] text-primary font-medium">
                  <span className="h-1.5 w-1.5 rounded-full bg-primary animate-ping" />
                  Live Streaming
                </span>
              )}
            </CardHeader>
            <CardContent className="p-4 flex-1 overflow-y-auto space-y-3 font-mono text-[11px]">
              {liveEvents.length === 0 ? (
                <div className="h-full flex items-center justify-center text-muted-foreground text-xs font-sans">
                  Waiting for initial engine events...
                </div>
              ) : (
                liveEvents.map((evt, i) => (
                  <div key={evt.id || i} className="flex items-start gap-2.5 pb-2 border-b border-border/40">
                    <span className="text-muted-foreground/60 shrink-0 text-[10px]">
                      {evt.timestamp ? evt.timestamp.split("T")[1]?.slice(0, 8) : "—"}
                    </span>
                    <span className="px-1.5 py-0.2 rounded bg-muted/50 text-[9px] font-semibold text-muted-foreground shrink-0 uppercase">
                      {evt.stage}
                    </span>
                    <span className="text-foreground leading-relaxed flex-1 font-sans text-xs">
                      {evt.message}
                    </span>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
