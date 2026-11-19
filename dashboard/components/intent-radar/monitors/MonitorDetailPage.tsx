"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import * as Menu from "@radix-ui/react-dropdown-menu";
import {
  AlertCircle,
  Archive,
  ArrowLeft,
  ArrowRight,
  CalendarClock,
  CheckCircle2,
  Clock,
  Copy,
  ExternalLink,
  History,
  Loader2,
  MoreHorizontal,
  Pause,
  Pencil,
  Play,
  Radio,
  Sparkles,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";
import {
  type IntentJob,
  type IntentMonitor,
  type IntentPage,
  type IntentSignal,
} from "@/lib/intent-radar";
import { useRadarCapabilities, useRadarMutation, useRadarRead } from "../provider";
import { ErrorState, LoadingSkeleton } from "../ui";
import { ProviderLogo } from "../provider-logo";
import { SignalTable } from "../signals";
import { JobPanel } from "../jobs";
import { PrimaryTabs } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { MonitorBuilderPage } from "./MonitorBuilderPage";

type MonitorTab = "overview" | "history" | "matches";

function formatDateTime(value?: string | null): string {
  if (!value) return "—";
  try {
    const d = new Date(value);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 7) return `${diffDays}d ago`;
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  } catch {
    return value;
  }
}

export function MonitorDetailPage({ id }: { id: string }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const isEditMode = searchParams.get("edit") === "true";

  const [activeTab, setActiveTab] = useState<MonitorTab>("overview");
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState(false);
  const [archiveConfirm, setArchiveConfirm] = useState(false);

  const mutation = useRadarMutation();
  const access = useRadarCapabilities();
  const canWrite = Boolean(access.data?.can_write);

  // Read monitor detail
  const monitorQuery = useRadarRead<IntentMonitor>(`/monitors/${id}`, Boolean(id));

  // Read matched signals for this monitor
  const signalsQuery = useRadarRead<IntentPage<IntentSignal>>(`/signals?monitor_id=${id}&page_size=20`, Boolean(id));

  // Read run history for this monitor
  const historyQuery = useRadarRead<{
    items: {
      id: string;
      created_at: string;
      provider: string | null;
      status: string | null;
      result: {
        requests?: number;
        scanned?: number;
        matched?: number;
        new_signals?: number;
        coverage?: string;
        errors?: string[];
      };
    }[];
  }>(`/monitors/${id}/runs`, Boolean(id));

  const monitor = monitorQuery.data;

  // Run Check
  async function handleRunCheck() {
    if (!monitor || !canWrite || mutation.isPending) return;
    try {
      const res = (await mutation.mutateAsync({
        path: "/discover",
        body: {
          monitor_id: monitor.id,
          configuration: monitor.configuration,
          request_id: crypto.randomUUID(),
        },
      })) as IntentJob;

      setActiveJobId(res.id);
      toast.success(`Check started for "${monitor.name}".`);
      await monitorQuery.refetch();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to run check.");
    }
  }

  // Toggle status
  async function handleToggleStatus() {
    if (!monitor || !canWrite || mutation.isPending) return;
    const nextStatus = monitor.status === "Active" ? "Paused" : "Active";
    try {
      await mutation.mutateAsync({
        path: `/monitors/${monitor.id}`,
        method: "PUT",
        body: {
          name: monitor.name,
          description: monitor.description,
          goal: monitor.goal,
          configuration: monitor.configuration,
          status: nextStatus,
          revision: monitor.revision,
        },
      });
      toast.success(`Monitor set to ${nextStatus}.`);
      await monitorQuery.refetch();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not update monitor status.");
    }
  }

  // Duplicate
  async function handleDuplicate() {
    if (!monitor || !canWrite || mutation.isPending) return;
    try {
      const res = (await mutation.mutateAsync({
        path: `/monitors/${monitor.id}/duplicate`,
        body: { request_id: crypto.randomUUID() },
      })) as IntentMonitor;
      toast.success(`Duplicated monitor.`);
      if (res?.id) {
        router.push(`/intent-radar/monitors/${res.id}`);
      }
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not duplicate monitor.");
    }
  }

  // Archive / Restore
  async function handleArchive(restore = false) {
    if (!monitor || !canWrite || mutation.isPending) return;
    const nextStatus = restore ? "Draft" : "Archived";
    try {
      await mutation.mutateAsync({
        path: `/monitors/${monitor.id}`,
        method: "PUT",
        body: {
          name: monitor.name,
          description: monitor.description,
          goal: monitor.goal,
          configuration: monitor.configuration,
          status: nextStatus,
          revision: monitor.revision,
        },
      });
      setArchiveConfirm(false);
      toast.success(restore ? `Restored "${monitor.name}" to drafts.` : `Archived "${monitor.name}".`);
      await monitorQuery.refetch();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not archive monitor.");
    }
  }

  // Delete
  async function handleDelete() {
    if (!monitor || !canWrite || mutation.isPending) return;
    try {
      await mutation.mutateAsync({
        path: `/monitors/${monitor.id}`,
        method: "DELETE",
      });
      setDeleteConfirm(false);
      toast.success(`Deleted monitor "${monitor.name}".`);
      router.push("/intent-radar/monitors");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not delete monitor.");
    }
  }

  if (monitorQuery.error) {
    return (
      <div className="ir-page space-y-4">
        <Link
          href="/intent-radar/monitors"
          className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft size={14} /> Back to Monitors
        </Link>
        <ErrorState
          message={monitorQuery.error.message}
          retry={() => void monitorQuery.refetch()}
        />
      </div>
    );
  }

  if (!monitor) {
    return (
      <div className="ir-page space-y-4">
        <LoadingSkeleton />
      </div>
    );
  }

  // If URL has ?edit=true, render the full-page builder pre-loaded with this monitor!
  if (isEditMode) {
    return (
      <MonitorBuilderPage
        existing={monitor}
        onClose={() => router.push(`/intent-radar/monitors/${monitor.id}`)}
      />
    );
  }

  const sources = monitor.configuration.sources || ["hacker_news"];
  const sourceNames = sources.map(
    (sid) => access.data?.sources.find((s) => s.id === sid)?.name || sid
  );
  const totalMatches = signalsQuery.data?.total ?? monitor.signals_count ?? 0;
  const isJobRunning = Boolean(activeJobId);

  const freq = monitor.schedule?.frequency || "Manual";
  const statusBadgeTone =
    monitor.status === "Active"
      ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
      : monitor.status === "Paused"
        ? "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300"
        : "border-border bg-muted/60 text-muted-foreground";

  return (
    <div className="ir-page space-y-5">
      {/* 1. Top Navigation Bar */}
      <div className="flex items-center justify-between gap-3 border-b border-border pb-3">
        <Link
          href="/intent-radar/monitors"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft size={13} />
          <span>Back to Monitors</span>
        </Link>

        <div className="flex items-center gap-2">
          {canWrite && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => router.push(`/intent-radar/monitors/${monitor.id}?edit=true`)}
              className="h-7 text-xs gap-1 font-medium"
            >
              <Pencil size={12} />
              <span>Edit Configuration</span>
            </Button>
          )}

          <Menu.Root>
            <Menu.Trigger
              className="inline-flex h-7 w-7 items-center justify-center rounded-lg border border-border bg-card text-muted-foreground hover:text-foreground cursor-pointer"
              aria-label="More options"
            >
              <MoreHorizontal size={13} />
            </Menu.Trigger>
            <Menu.Portal>
              <Menu.Content
                className="z-50 min-w-[150px] rounded-xl border border-border bg-popover p-1 text-popover-foreground shadow-md text-xs space-y-0.5"
                sideOffset={5}
                align="end"
              >
                <Menu.Item
                  className="flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs text-foreground hover:bg-accent hover:text-accent-foreground cursor-pointer outline-none"
                  onSelect={() => void handleDuplicate()}
                >
                  <Copy size={12} className="text-muted-foreground" />
                  <span>Duplicate</span>
                </Menu.Item>

                <Menu.Item
                  className="flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs text-foreground hover:bg-accent hover:text-accent-foreground cursor-pointer outline-none"
                  onSelect={() =>
                    monitor.status === "Archived" ? void handleArchive(true) : setArchiveConfirm(true)
                  }
                >
                  <Archive size={12} className="text-muted-foreground" />
                  <span>{monitor.status === "Archived" ? "Restore to Draft" : "Archive"}</span>
                </Menu.Item>

                <Menu.Separator className="h-px bg-border my-1" />

                <Menu.Item
                  className="flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs text-destructive hover:bg-destructive/10 cursor-pointer outline-none"
                  onSelect={() => setDeleteConfirm(true)}
                >
                  <Trash2 size={12} />
                  <span>Delete</span>
                </Menu.Item>
              </Menu.Content>
            </Menu.Portal>
          </Menu.Root>
        </div>
      </div>

      {/* 2. Top-Level Summary Header (Phase 6.1) */}
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1 min-w-0 max-w-2xl">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground truncate">
              {monitor.name}
            </h1>
            <span
              className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${statusBadgeTone}`}
            >
              {monitor.status === "Active" && freq !== "Manual"
                ? `Enabled · ${freq}`
                : monitor.status === "Active"
                  ? "Enabled · On demand"
                  : monitor.status}
            </span>
          </div>

          <p className="text-xs text-muted-foreground leading-relaxed">
            {monitor.description || monitor.goal || "Tracking relevant public discussions across configured sources."}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {monitor.status === "Active" ? (
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={!canWrite || mutation.isPending}
              onClick={() => void handleToggleStatus()}
              className="h-8 text-xs gap-1 font-medium"
            >
              <Pause size={13} />
              <span>Pause Monitor</span>
            </Button>
          ) : monitor.status === "Paused" ? (
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={!canWrite || mutation.isPending}
              onClick={() => void handleToggleStatus()}
              className="h-8 text-xs gap-1 font-medium"
            >
              <Play size={13} />
              <span>Resume Monitor</span>
            </Button>
          ) : null}

          <Button
            type="button"
            variant="default"
            size="sm"
            disabled={!canWrite || mutation.isPending || isJobRunning || monitor.status === "Archived"}
            onClick={() => void handleRunCheck()}
            className="h-8 text-xs gap-1.5 font-semibold"
          >
            {isJobRunning ? (
              <>
                <Loader2 size={13} className="animate-spin" />
                <span>Checking…</span>
              </>
            ) : (
              <>
                <Play size={13} />
                <span>Run Check</span>
              </>
            )}
          </Button>
        </div>
      </header>

      {/* 3. Compact Operational Metrics Strip */}
      <section aria-label="Operational summary" className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="rounded-xl border border-border bg-card p-3 space-y-1">
          <span className="text-[11px] text-muted-foreground font-medium block">
            Sources Monitored
          </span>
          <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
            {sourceNames.slice(0, 3).map((sname) => (
              <span
                key={sname}
                className="inline-flex items-center gap-1 rounded bg-muted/40 px-1.5 py-0.5 text-[11px] font-medium text-foreground"
              >
                <ProviderLogo provider={sname} size={13} />
                <span>{sname}</span>
              </span>
            ))}
            {sourceNames.length > 3 && (
              <span className="text-[10px] text-muted-foreground font-medium">
                +{sourceNames.length - 3}
              </span>
            )}
          </div>
        </div>

        <div className="rounded-xl border border-border bg-card p-3 space-y-1">
          <span className="text-[11px] text-muted-foreground font-medium block">
            Last Execution
          </span>
          <div className="text-xs font-semibold text-foreground pt-0.5">
            {formatDateTime(monitor.last_checked)}
          </div>
        </div>

        <div className="rounded-xl border border-border bg-card p-3 space-y-1">
          <span className="text-[11px] text-muted-foreground font-medium block">
            Next Scheduled Check
          </span>
          <div className="text-xs font-semibold text-foreground pt-0.5 flex items-center gap-1">
            <CalendarClock size={12} className="text-muted-foreground" />
            <span>
              {monitor.status === "Archived"
                ? "Archived"
                : monitor.status === "Paused"
                  ? "Paused"
                  : monitor.status === "Draft"
                    ? "Not scheduled"
                    : freq === "Manual"
                      ? "On demand"
                      : formatDateTime(monitor.next_run_at) || freq}
            </span>
          </div>
        </div>

        <div className="rounded-xl border border-border bg-card p-3 space-y-1">
          <span className="text-[11px] text-muted-foreground font-medium block">
            Total Matches
          </span>
          <div className="text-xs font-bold text-foreground pt-0.5 tabular-nums">
            {totalMatches} signals
          </div>
        </div>
      </section>

      {/* Active Run Status Banner */}
      {activeJobId && (
        <div className="rounded-xl border border-blue-500/30 bg-blue-500/5 p-4">
          <JobPanel id={activeJobId} />
        </div>
      )}

      {/* 4. Consistent 3 Detail Tabs (Phase 6.2) */}
      <PrimaryTabs
        items={[
          { id: "overview", label: "Overview", icon: Radio },
          { id: "history", label: "Run History", icon: History, count: (historyQuery.data?.items || []).length },
          { id: "matches", label: "Matches", icon: Sparkles, count: totalMatches },
        ]}
        activeId={activeTab}
        onChange={(tabId) => setActiveTab(tabId as MonitorTab)}
      />

      {/* 5. TAB 1: OVERVIEW */}
      {activeTab === "overview" && (
        <div className="space-y-4 pt-1">
          {/* Criteria Summary Card */}
          <section className="rounded-2xl border border-border bg-card p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-border/80 pb-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Search &amp; Filter Criteria
              </h3>
              <button
                type="button"
                onClick={() => router.push(`/intent-radar/monitors/${monitor.id}?edit=true`)}
                className="text-xs text-primary hover:underline font-medium inline-flex items-center gap-1 cursor-pointer"
              >
                <Pencil size={11} />
                <span>Edit criteria</span>
              </button>
            </div>

            <div className="grid gap-4 sm:grid-cols-2 text-xs">
              <div className="space-y-1">
                <span className="text-[11px] font-medium text-muted-foreground block">
                  Search Keywords
                </span>
                <div className="flex flex-wrap gap-1.5 pt-0.5">
                  {(monitor.configuration.keywords || []).map((kw) => (
                    <span
                      key={kw}
                      className="rounded-md border border-border bg-muted/30 px-2 py-0.5 text-xs text-foreground font-medium"
                    >
                      {kw}
                    </span>
                  ))}
                </div>
              </div>

              <div className="space-y-1">
                <span className="text-[11px] font-medium text-muted-foreground block">
                  Negative Excluded Terms
                </span>
                <div className="flex flex-wrap gap-1.5 pt-0.5">
                  {(monitor.configuration.excluded || []).length > 0 ? (
                    monitor.configuration.excluded?.map((ex) => (
                      <span
                        key={ex}
                        className="rounded-md border border-destructive/20 bg-destructive/5 px-2 py-0.5 text-xs text-destructive font-medium"
                      >
                        −{ex}
                      </span>
                    ))
                  ) : (
                    <span className="text-xs text-muted-foreground italic">None configured</span>
                  )}
                </div>
              </div>

              <div className="space-y-1">
                <span className="text-[11px] font-medium text-muted-foreground block">
                  Intent Categories
                </span>
                <div className="flex flex-wrap gap-1.5 pt-0.5">
                  {(monitor.configuration.categories || []).length > 0 ? (
                    monitor.configuration.categories.map((cat) => (
                      <span
                        key={cat}
                        className="rounded-md border border-primary/25 bg-primary/5 px-2 py-0.5 text-xs text-primary font-medium"
                      >
                        {cat}
                      </span>
                    ))
                  ) : (
                    <span className="text-xs text-muted-foreground italic">All conversation types included</span>
                  )}
                </div>
              </div>

              <div className="space-y-1">
                <span className="text-[11px] font-medium text-muted-foreground block">
                  Relevance Threshold
                </span>
                <p className="text-xs font-semibold text-foreground pt-0.5">
                  Minimum {monitor.configuration.min_relevance || 0}/100 relevance score
                </p>
              </div>
            </div>
          </section>

          {/* Schedule & Timing Card */}
          <section className="rounded-2xl border border-border bg-card p-5 space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground border-b border-border/80 pb-2.5">
              Monitoring Schedule &amp; Execution
            </h3>
            <div className="grid gap-3 sm:grid-cols-3 text-xs">
              <div>
                <span className="text-[11px] text-muted-foreground block">Cadence</span>
                <strong className="text-foreground block mt-0.5 font-semibold">
                  {freq}
                </strong>
              </div>
              <div>
                <span className="text-[11px] text-muted-foreground block">Timezone</span>
                <strong className="text-foreground block mt-0.5 font-semibold">
                  {monitor.schedule?.timezone || "UTC"}
                </strong>
              </div>
              <div>
                <span className="text-[11px] text-muted-foreground block">Auto-execution</span>
                <strong className="text-foreground block mt-0.5 font-semibold">
                  {monitor.status === "Active" && freq !== "Manual" ? "Enabled" : "Disabled (Manual only)"}
                </strong>
              </div>
            </div>
          </section>
        </div>
      )}

      {/* 6. TAB 2: RUN HISTORY (Phase 6.2) */}
      {activeTab === "history" && (
        <div className="space-y-3 pt-1">
          {historyQuery.error ? (
            <ErrorState message={historyQuery.error.message} retry={() => void historyQuery.refetch()} />
          ) : !historyQuery.data ? (
            <LoadingSkeleton />
          ) : historyQuery.data.items.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border bg-card/60 p-8 text-center space-y-2">
              <Clock size={20} className="mx-auto text-muted-foreground opacity-60" />
              <p className="text-xs font-medium text-foreground">
                No checks have run for this monitor yet.
              </p>
              <p className="text-[11px] text-muted-foreground max-w-sm mx-auto">
                Click <strong>Run Check</strong> above to start your first research execution.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto rounded-xl border border-border bg-card shadow-xs">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-border bg-muted/30 text-[11px] uppercase tracking-wide text-muted-foreground select-none">
                  <tr>
                    <th className="px-4 py-2.5 font-semibold">Started</th>
                    <th className="px-3 py-2.5 font-semibold">Source</th>
                    <th className="px-3 py-2.5 font-semibold">Status</th>
                    <th className="px-3 py-2.5 font-semibold">Coverage &amp; Errors</th>
                    <th className="px-3 py-2.5 font-semibold text-right">Scanned</th>
                    <th className="px-4 py-2.5 font-semibold text-right">Run Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {historyQuery.data.items.map((run, idx) => {
                    const st = run.status || "Pending";
                    const isErr = ["FAILED", "TIMED_OUT", "UNAVAILABLE", "ERROR"].includes(st.toUpperCase());
                    const isOk = ["COMPLETE", "COMPLETED", "NO_RESULTS"].includes(st.toUpperCase());

                    return (
                      <tr key={`${run.id}:${run.provider}:${idx}`} className="hover:bg-muted/15 transition-colors">
                        <td className="px-4 py-2.5 whitespace-nowrap text-muted-foreground">
                          {formatDateTime(run.created_at)}
                        </td>
                        <td className="px-3 py-2.5 font-semibold text-foreground whitespace-nowrap">
                          {run.provider || "Pending dispatch"}
                        </td>
                        <td className="px-3 py-2.5 whitespace-nowrap">
                          <span
                            className={
                              "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold " +
                              (isErr
                                ? "border-destructive/30 bg-destructive/10 text-destructive"
                                : isOk
                                  ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
                                  : "border-border bg-muted text-muted-foreground")
                            }
                          >
                            {isErr ? (
                              <AlertCircle size={10} aria-hidden="true" />
                            ) : isOk ? (
                              <CheckCircle2 size={10} aria-hidden="true" />
                            ) : null}
                            <span>{st}</span>
                          </span>
                        </td>
                        <td className="px-3 py-2.5 text-muted-foreground max-w-md">
                          <p className="line-clamp-1">{run.result?.coverage || "Source check completed."}</p>
                          {Array.isArray(run.result?.errors) && run.result.errors.length > 0 && (
                            <p className="text-destructive text-[11px] line-clamp-1 mt-0.5">
                              {run.result.errors.join("; ")}
                            </p>
                          )}
                        </td>
                        <td className="px-3 py-2.5 text-right tabular-nums text-muted-foreground whitespace-nowrap">
                          {run.result?.scanned ?? "—"}
                        </td>
                        <td className="px-4 py-2.5 text-right whitespace-nowrap">
                          <Link
                            href={`/intent-radar/discover/runs/${run.id}`}
                            className="inline-flex items-center gap-1 text-primary hover:underline font-medium text-xs"
                          >
                            <span>Inspect</span>
                            <ExternalLink size={10} />
                          </Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* 7. TAB 3: MATCHES (Phase 6.2) */}
      {activeTab === "matches" && (
        <div className="space-y-3 pt-1">
          <div className="flex items-center justify-between gap-2 border-b border-border/80 pb-2">
            <div>
              <h3 className="text-xs font-semibold text-foreground">
                Discovered Signals ({signalsQuery.data?.total || 0})
              </h3>
              <p className="text-[11px] text-muted-foreground">
                Public discussions observed and matched by this monitor.
              </p>
            </div>
            <Link
              href={`/intent-radar/signals?monitor_id=${monitor.id}`}
              className="text-xs font-medium text-primary hover:underline inline-flex items-center gap-1"
            >
              <span>Open in Signals Workspace</span>
              <ArrowRight size={12} />
            </Link>
          </div>

          {signalsQuery.error ? (
            <ErrorState message={signalsQuery.error.message} retry={() => void signalsQuery.refetch()} />
          ) : !signalsQuery.data ? (
            <LoadingSkeleton />
          ) : signalsQuery.data.items.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border bg-card/60 p-8 text-center space-y-2">
              <Sparkles size={20} className="mx-auto text-muted-foreground opacity-60" />
              <p className="text-xs font-medium text-foreground">
                No signals matched this monitor yet.
              </p>
              <p className="text-[11px] text-muted-foreground max-w-sm mx-auto">
                Run a check or broaden your keywords to match more conversations.
              </p>
            </div>
          ) : (
            <SignalTable signals={signalsQuery.data.items} />
          )}
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-2xl border border-border bg-card p-6 shadow-lg space-y-4">
            <div className="flex items-center gap-3 text-destructive">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-destructive/10">
                <Trash2 size={20} />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-foreground">Delete monitor?</h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Are you sure you want to delete &ldquo;{monitor.name}&rdquo;?
                </p>
              </div>
            </div>
            <p className="text-xs text-muted-foreground">
              This action cannot be undone. All scheduled checks for this monitor will be cancelled. Signals previously discovered will remain intact.
            </p>
            <div className="flex items-center justify-end gap-2 pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setDeleteConfirm(false)}
                disabled={mutation.isPending}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => void handleDelete()}
                disabled={mutation.isPending}
              >
                {mutation.isPending ? "Deleting…" : "Delete Monitor"}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Archive Confirmation Modal */}
      {archiveConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-2xl border border-border bg-card p-6 shadow-lg space-y-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-muted text-muted-foreground">
                <Archive size={20} />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-foreground">Archive monitor?</h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Archive &ldquo;{monitor.name}&rdquo;?
                </p>
              </div>
            </div>
            <p className="text-xs text-muted-foreground">
              This pauses all checks and hides it from your active list. You can restore it anytime.
            </p>
            <div className="flex items-center justify-end gap-2 pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setArchiveConfirm(false)}
                disabled={mutation.isPending}
              >
                Cancel
              </Button>
              <Button
                variant="default"
                size="sm"
                onClick={() => void handleArchive(false)}
                disabled={mutation.isPending}
              >
                {mutation.isPending ? "Archiving…" : "Archive Monitor"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
