"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import * as Menu from "@radix-ui/react-dropdown-menu";
import {
  AlertCircle,
  Archive,
  ArrowRight,
  BookOpen,
  CalendarClock,
  CheckCircle2,
  Clock,
  Copy,
  Loader2,
  MoreHorizontal,
  Pause,
  Pencil,
  Play,
  Plus,
  Radio,
  Search,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";
import { toast } from "sonner";
import {
  type IntentJob,
  type IntentMonitor,
  type IntentPage,
} from "@/lib/intent-radar";
import { useRadarCapabilities, useRadarMutation, useRadarRead } from "../provider";
import { ErrorState, LoadingSkeleton } from "../ui";
import { ProviderLogo } from "../provider-logo";
import { StatusFilterTabs } from "@/components/ui/tabs";
import { SearchInput } from "@/components/ui/search-input";
import { Button } from "@/components/ui/button";

type StatusTab = "all" | "Active" | "Scheduled" | "Running" | "Paused" | "Draft" | "Archived";

const STATUS_TABS: { id: StatusTab; label: string }[] = [
  { id: "all", label: "All Monitors" },
  { id: "Scheduled", label: "Scheduled" },
  { id: "Active", label: "Active" },
  { id: "Running", label: "Running" },
  { id: "Paused", label: "Paused" },
  { id: "Draft", label: "Drafts" },
  { id: "Archived", label: "Archived" },
];

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
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  } catch {
    return value;
  }
}

function computeStatusBadge(m: IntentMonitor, isJobRunning: boolean, hasError: boolean = false) {
  if (isJobRunning) {
    return {
      label: "Running",
      tone: "border-blue-500/30 bg-blue-500/10 text-blue-700 dark:text-blue-300",
      icon: Loader2,
      animate: true,
    };
  }

  if (m.status === "Archived") {
    return {
      label: "Archived",
      tone: "border-border bg-muted/70 text-muted-foreground",
      icon: Archive,
    };
  }

  if (m.status === "Paused") {
    return {
      label: "Paused",
      tone: "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300",
      icon: Pause,
    };
  }

  if (m.status === "Draft") {
    return {
      label: "Draft",
      tone: "border-border bg-muted/50 text-muted-foreground",
      icon: Clock,
    };
  }

  if (hasError) {
    return {
      label: "Error",
      tone: "border-rose-500/30 bg-rose-500/10 text-rose-700 dark:text-rose-300",
      icon: AlertCircle,
    };
  }

  // Active
  const freq = m.schedule?.frequency;
  if (!freq || freq === "Manual") {
    return {
      label: "Active — On demand",
      tone: "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
      icon: CheckCircle2,
    };
  }

  return {
    label: `Enabled · ${freq}`,
    tone: "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
    icon: CheckCircle2,
  };
}

function nextCheckLabel(m: IntentMonitor): string {
  if (m.status === "Archived") return "Archived";
  if (m.status === "Paused") return "Paused";
  if (m.status === "Draft") return "Not scheduled";
  const freq = m.schedule?.frequency;
  if (!freq || freq === "Manual") return "On demand";
  if (m.next_run_at) return formatDateTime(m.next_run_at);
  return freq;
}

export function MonitorsDashboard() {
  const router = useRouter();
  const [statusFilter, setStatusFilter] = useState<StatusTab>("all");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [runningJobIds, setRunningJobIds] = useState<Record<string, string>>({});
  const [deleteTarget, setDeleteTarget] = useState<IntentMonitor | null>(null);
  const [archiveTarget, setArchiveTarget] = useState<IntentMonitor | null>(null);

  const mutation = useRadarMutation();
  const access = useRadarCapabilities();
  const canWrite = Boolean(access.data?.can_write);

  // Read monitors
  const monitorsQuery = useRadarRead<IntentPage<IntentMonitor>>(
    `/monitors?page_size=50&page=${page}`
  );

  // Read saved searches to support "Start from Saved Search" in empty state
  const savedSearchesQuery = useRadarRead<{ items: { id: string; name: string }[] }>(
    "/saved-searches?page_size=5"
  );

  // Read active jobs to identify running monitors
  const jobsQuery = useRadarRead<{ items: IntentJob[] }>("/jobs");

  const monitors = useMemo(() => monitorsQuery.data?.items || [], [monitorsQuery.data?.items]);
  const totalMonitors = monitorsQuery.data?.total || 0;

  // Active running checks mapping
  const runningMap = useMemo(() => {
    const map: Record<string, string> = { ...runningJobIds };
    (jobsQuery.data?.items || []).forEach((j) => {
      if (j.monitor_id && (j.status === "QUEUED" || j.status === "RUNNING")) {
        map[j.monitor_id] = j.id;
      }
    });
    return map;
  }, [jobsQuery.data?.items, runningJobIds]);

  // Failed checks mapping for Error status
  const failedJobMap = useMemo(() => {
    const map: Record<string, boolean> = {};
    (jobsQuery.data?.items || []).forEach((j) => {
      if (j.monitor_id && j.status === "FAILED") {
        map[j.monitor_id] = true;
      }
    });
    return map;
  }, [jobsQuery.data?.items]);

  // Compute metrics for overview (only shown if meaningful data exists)
  const stats = useMemo(() => {
    let enabled = 0;
    let scheduled = 0;
    let checksRunning = 0;
    let totalMatches = 0;
    let needsAttention = 0;

    monitors.forEach((m) => {
      const isRunning = Boolean(runningMap[m.id]);
      if (m.status === "Active") enabled++;
      if (isRunning) checksRunning++;
      if (m.status === "Active" && m.schedule?.frequency && m.schedule.frequency !== "Manual") {
        scheduled++;
      }
      totalMatches += m.signals_count || 0;
      if (m.status === "Paused" || Boolean(failedJobMap[m.id]) || (!m.schedule?.frequency && m.status === "Draft")) {
        needsAttention++;
      }
    });

    return {
      enabled,
      scheduled,
      checksRunning,
      totalMatches,
      needsAttention,
      hasData: monitors.length > 0,
    };
  }, [monitors, runningMap, failedJobMap]);

  // Filter monitors for table
  const filteredMonitors = useMemo(() => {
    return monitors.filter((m) => {
      // Status filter
      if (statusFilter === "Running") {
        if (!runningMap[m.id]) return false;
      } else if (statusFilter === "Scheduled") {
        if (m.status !== "Active" || !m.schedule?.frequency || m.schedule.frequency === "Manual") return false;
      } else if (statusFilter === "Active") {
        if (m.status !== "Active") return false;
      } else if (statusFilter === "Paused") {
        if (m.status !== "Paused") return false;
      } else if (statusFilter === "Draft") {
        if (m.status !== "Draft") return false;
      } else if (statusFilter === "Archived") {
        if (m.status !== "Archived") return false;
      } else if (statusFilter === "all") {
        // "all" hides archived by default unless explicitly chosen
        if (m.status === "Archived") return false;
      }

      // Search term
      if (search.trim()) {
        const q = search.toLowerCase();
        const inName = m.name.toLowerCase().includes(q);
        const inKeywords = (m.configuration.keywords || []).some((kw) =>
          kw.toLowerCase().includes(q)
        );
        const inDesc = (m.description || m.goal || "").toLowerCase().includes(q);
        if (!inName && !inKeywords && !inDesc) return false;
      }

      return true;
    });
  }, [monitors, statusFilter, search, runningMap]);

  // Dynamic counts for status tabs
  const tabCounts = useMemo(() => {
    const counts: Record<StatusTab, number> = {
      all: monitors.filter((m) => m.status !== "Archived").length,
      Active: monitors.filter((m) => m.status === "Active").length,
      Scheduled: monitors.filter((m) => m.status === "Active" && m.schedule?.frequency && m.schedule.frequency !== "Manual").length,
      Running: monitors.filter((m) => Boolean(runningMap[m.id])).length,
      Paused: monitors.filter((m) => m.status === "Paused").length,
      Draft: monitors.filter((m) => m.status === "Draft").length,
      Archived: monitors.filter((m) => m.status === "Archived").length,
    };
    return counts;
  }, [monitors, runningMap]);

  async function handleRunCheck(m: IntentMonitor) {
    if (!canWrite || mutation.isPending) return;
    try {
      const res = (await mutation.mutateAsync({
        path: "/discover",
        body: {
          monitor_id: m.id,
          configuration: m.configuration,
          request_id: crypto.randomUUID(),
        },
      })) as IntentJob;

      setRunningJobIds((prev) => ({ ...prev, [m.id]: res.id }));
      toast.success(`Check started for "${m.name}".`);
      await monitorsQuery.refetch();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to run check.");
    }
  }

  async function handleTogglePause(m: IntentMonitor) {
    if (!canWrite || mutation.isPending) return;
    const nextStatus = m.status === "Active" ? "Paused" : "Active";
    try {
      await mutation.mutateAsync({
        path: `/monitors/${m.id}`,
        method: "PUT",
        body: {
          name: m.name,
          description: m.description,
          goal: m.goal,
          configuration: m.configuration,
          status: nextStatus,
          revision: m.revision,
        },
      });
      toast.success(`Monitor "${m.name}" set to ${nextStatus}.`);
      await monitorsQuery.refetch();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not update monitor status.");
    }
  }

  async function handleDuplicate(m: IntentMonitor) {
    if (!canWrite || mutation.isPending) return;
    try {
      await mutation.mutateAsync({
        path: `/monitors/${m.id}/duplicate`,
        body: { request_id: crypto.randomUUID() },
      });
      toast.success(`Duplicated "${m.name}".`);
      await monitorsQuery.refetch();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not duplicate monitor.");
    }
  }

  async function handleArchive(m: IntentMonitor, restore = false) {
    if (!canWrite || mutation.isPending) return;
    const nextStatus = restore ? "Draft" : "Archived";
    try {
      await mutation.mutateAsync({
        path: `/monitors/${m.id}`,
        method: "PUT",
        body: {
          name: m.name,
          description: m.description,
          goal: m.goal,
          configuration: m.configuration,
          status: nextStatus,
          revision: m.revision,
        },
      });
      setArchiveTarget(null);
      toast.success(restore ? `Restored "${m.name}" as draft.` : `Archived "${m.name}".`);
      await monitorsQuery.refetch();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not update monitor.");
    }
  }

  async function handleDeleteConfirm() {
    if (!deleteTarget || !canWrite || mutation.isPending) return;
    const id = deleteTarget.id;
    try {
      await mutation.mutateAsync({
        path: `/monitors/${id}`,
        method: "DELETE",
      });
      setDeleteTarget(null);
      toast.success(`Deleted monitor "${deleteTarget.name}".`);
      await monitorsQuery.refetch();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not delete monitor.");
    }
  }

  if (monitorsQuery.error) {
    return (
      <div className="ir-page space-y-4">
        <ErrorState
          message={monitorsQuery.error.message}
          retry={() => void monitorsQuery.refetch()}
        />
      </div>
    );
  }

  if (!monitorsQuery.data) {
    return (
      <div className="ir-page space-y-4">
        <LoadingSkeleton />
      </div>
    );
  }

  const hasZeroMonitorsEver = monitors.length === 0;

  return (
    <div className="ir-page w-full min-w-0 space-y-5">
      {/* 1. Header */}
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-border pb-4">
        <div className="space-y-0.5">
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">
            Monitoring
          </h1>
          <p className="text-xs text-muted-foreground">
            Track important conversations and discover new opportunities automatically.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            href="/help?article=monitors-alerts"
            className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-border bg-card px-3 text-xs font-medium text-foreground hover:border-primary/40 transition-colors"
          >
            <BookOpen size={13} className="text-muted-foreground" />
            <span>Guide</span>
          </Link>

          {canWrite ? (
            <Link
              href="/intent-radar/monitors/new"
              className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-primary px-3 text-xs font-semibold text-primary-foreground shadow-xs hover:bg-primary/90 transition-colors"
            >
              <Plus size={14} />
              <span>Create Monitor</span>
            </Link>
          ) : (
            <span className="text-xs text-muted-foreground border border-border rounded-lg px-2.5 py-1">
              Read-only access
            </span>
          )}
        </div>
      </header>

      {/* 2. Compact Overview Metrics (rendered only when meaningful data exists) */}
      {stats.hasData && (
        <section aria-label="Monitoring metrics overview" className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div
            onClick={() => setStatusFilter("Active")}
            className="rounded-xl border border-border bg-card p-3.5 space-y-1 cursor-pointer hover:border-primary/40 transition-colors"
          >
            <span className="text-[11px] font-medium text-muted-foreground block">
              Enabled Monitors
            </span>
            <div className="flex items-baseline gap-1.5">
              <span className="text-xl font-bold text-foreground tabular-nums">
                {stats.enabled}
              </span>
              <span className="text-[11px] text-muted-foreground">active</span>
            </div>
          </div>

          <div
            onClick={() => setStatusFilter("Scheduled")}
            className="rounded-xl border border-border bg-card p-3.5 space-y-1 cursor-pointer hover:border-primary/40 transition-colors"
          >
            <span className="text-[11px] font-medium text-muted-foreground block">
              Scheduled Checks
            </span>
            <div className="flex items-baseline gap-1.5">
              <span className="text-xl font-bold text-foreground tabular-nums">
                {stats.scheduled}
              </span>
              <span className="text-[11px] text-muted-foreground">cadenced</span>
            </div>
          </div>

          <div className="rounded-xl border border-border bg-card p-3.5 space-y-1">
            <span className="text-[11px] font-medium text-muted-foreground block">
              New Matches
            </span>
            <div className="flex items-baseline gap-1.5">
              <span className="text-xl font-bold text-foreground tabular-nums">
                {stats.totalMatches}
              </span>
              <span className="text-[11px] text-muted-foreground">signals</span>
            </div>
          </div>

          <div
            onClick={() => setStatusFilter("Paused")}
            className="rounded-xl border border-border bg-card p-3.5 space-y-1 cursor-pointer hover:border-primary/40 transition-colors"
          >
            <span className="text-[11px] font-medium text-muted-foreground block">
              Needs Attention
            </span>
            <div className="flex items-baseline gap-1.5">
              <span className="text-xl font-bold text-foreground tabular-nums">
                {stats.needsAttention}
              </span>
              {stats.needsAttention > 0 && (
                <span className="text-[11px] text-amber-600 dark:text-amber-400 font-medium">
                  paused/draft
                </span>
              )}
            </div>
          </div>
        </section>
      )}

      {/* 3. Empty State (if no monitors exist in the entire workspace) */}
      {hasZeroMonitorsEver ? (
        <div className="rounded-2xl border border-border bg-card p-8 sm:p-12 text-center max-w-xl mx-auto space-y-4 my-6 shadow-xs">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl border border-primary/20 bg-primary/10 text-primary">
            <Radio size={22} aria-hidden="true" />
          </div>
          <div className="space-y-1.5">
            <h2 className="text-lg font-semibold text-foreground">
              Start monitoring important conversations
            </h2>
            <p className="text-xs text-muted-foreground max-w-md mx-auto leading-relaxed">
              Create a monitor to check selected sources for new discussions matching your research interests.
            </p>
          </div>
          <div className="flex flex-wrap items-center justify-center gap-2.5 pt-2">
            {canWrite && (
              <Link
                href="/intent-radar/monitors/new"
                className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-primary px-3.5 text-xs font-semibold text-primary-foreground shadow-xs hover:bg-primary/90 transition-colors"
              >
                <span>Create Monitor</span>
                <ArrowRight size={13} />
              </Link>
            )}

            {(savedSearchesQuery.data?.items || []).length > 0 && (
              <Link
                href={`/intent-radar/monitors/new?saved_search_id=${savedSearchesQuery.data?.items[0].id}`}
                className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-border bg-card px-3 text-xs font-medium text-foreground hover:border-primary/40 transition-colors"
              >
                <Sparkles size={13} className="text-primary" />
                <span>Start from Saved Search</span>
              </Link>
            )}
          </div>
        </div>
      ) : (
        <>
          {/* 4. Controls Toolbar: Status Tabs + Search */}
          <div className="flex flex-wrap items-center justify-between gap-3">
            <StatusFilterTabs
              items={STATUS_TABS.map((t) => ({
                id: t.id,
                label: t.label,
                count: tabCounts[t.id],
              }))}
              activeId={statusFilter}
              onChange={(id) => {
                setStatusFilter(id as StatusTab);
                setPage(1);
              }}
            />

            <div className="flex items-center gap-2.5">
              <SearchInput
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setPage(1);
                }}
                onClear={() => {
                  setSearch("");
                  setPage(1);
                }}
                placeholder="Filter by name or keyword…"
                wrapperClassName="min-w-[220px]"
              />
            </div>
          </div>

          {/* 5. Data Table */}
          {filteredMonitors.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border bg-card/50 p-8 text-center space-y-2">
              <Radio size={20} className="mx-auto text-muted-foreground opacity-60" />
              <p className="text-xs font-medium text-foreground">
                {search ? "No monitors match your search query." : `No ${statusFilter.toLowerCase()} monitors found.`}
              </p>
              {search && (
                <button
                  type="button"
                  onClick={() => setSearch("")}
                  className="text-xs text-primary hover:underline font-medium cursor-pointer"
                >
                  Clear search filter
                </button>
              )}
            </div>
          ) : (
            <div className="w-full min-w-0 overflow-x-auto rounded-xl border border-border bg-card shadow-xs">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-border bg-muted/30 text-[11px] uppercase tracking-wide text-muted-foreground select-none">
                  <tr>
                    <th className="px-3.5 py-2.5 font-semibold min-w-[200px]">Monitor</th>
                    <th className="px-3 py-2.5 font-semibold whitespace-nowrap">Status</th>
                    <th className="px-3 py-2.5 font-semibold whitespace-nowrap">Sources</th>
                    <th className="px-3 py-2.5 font-semibold whitespace-nowrap">Schedule</th>
                    <th className="px-3 py-2.5 font-semibold whitespace-nowrap">Last Check</th>
                    <th className="px-3 py-2.5 font-semibold text-right whitespace-nowrap">Matches</th>
                    <th className="px-3.5 py-2.5 font-semibold text-right sticky right-0 bg-muted/95 backdrop-blur-xs z-10 min-w-[155px]">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {filteredMonitors.map((m) => {
                    const isRunning = Boolean(runningMap[m.id]);
                    const hasError = Boolean(failedJobMap[m.id]) && !isRunning;
                    const badge = computeStatusBadge(m, isRunning, hasError);
                    const BadgeIcon = badge.icon;
                    const sources = m.configuration.sources || ["hacker_news"];
                    const sourceNames = sources.map(
                      (sid) => access.data?.sources.find((s) => s.id === sid)?.name || sid
                    );

                    return (
                      <tr key={m.id} className="group hover:bg-muted/15 transition-colors">
                        {/* Monitor column: name + objective */}
                        <td className="px-3.5 py-3 min-w-[200px] max-w-sm">
                          <Link
                            href={`/intent-radar/monitors/${m.id}`}
                            className="font-semibold text-xs text-foreground hover:text-primary transition-colors block truncate"
                            title={m.name}
                          >
                            {m.name}
                          </Link>
                          {(m.goal || m.description) && (
                            <p className="text-[11px] text-muted-foreground truncate mt-0.5" title={m.goal || m.description}>
                              {m.goal || m.description}
                            </p>
                          )}
                        </td>

                        {/* Status column */}
                        <td className="px-3 py-3 whitespace-nowrap">
                          <span
                            className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold ${badge.tone}`}
                          >
                            <BadgeIcon
                              size={11}
                              className={badge.animate ? "animate-spin" : undefined}
                              aria-hidden="true"
                            />
                            <span>{badge.label}</span>
                          </span>
                        </td>

                        {/* Sources column */}
                        <td className="px-3 py-3">
                          <div className="flex flex-wrap items-center gap-1.5">
                            {sourceNames.slice(0, 2).map((name) => (
                              <span
                                key={name}
                                className="inline-flex items-center gap-1 rounded-md border border-border/70 bg-muted/20 px-1.5 py-0.5 text-[11px] text-foreground whitespace-nowrap font-medium"
                              >
                                <ProviderLogo provider={name} size={12} />
                                <span>{name}</span>
                              </span>
                            ))}
                            {sourceNames.length > 2 && (
                              <span className="text-[10px] text-muted-foreground font-medium">
                                +{sourceNames.length - 2}
                              </span>
                            )}
                          </div>
                        </td>

                        {/* Schedule column */}
                        <td className="px-3 py-3 whitespace-nowrap text-muted-foreground font-medium">
                          {m.schedule?.frequency && m.schedule.frequency !== "Manual" ? m.schedule.frequency : "On demand"}
                        </td>

                        {/* Last check column */}
                        <td className="px-3 py-3 whitespace-nowrap text-muted-foreground">
                          {m.last_checked ? formatDateTime(m.last_checked) : "Never run"}
                        </td>

                        {/* Matches column */}
                        <td className="px-3 py-3 text-right tabular-nums whitespace-nowrap font-medium">
                          <Link
                            href={`/intent-radar/signals?monitor_id=${m.id}`}
                            className="font-semibold text-foreground hover:text-primary transition-colors inline-block py-0.5 px-1.5 rounded hover:bg-muted"
                          >
                            {m.signals_count ?? 0}
                          </Link>
                        </td>

                        {/* Actions column - sticky right guarantees no clipping */}
                        <td className="px-3 py-3 text-right whitespace-nowrap sticky right-0 bg-card group-hover:bg-muted/30 transition-colors z-10 min-w-[155px]">
                          <div className="inline-flex items-center justify-end gap-1.5">
                            <button
                              type="button"
                              className="inline-flex h-7 items-center gap-1 rounded-lg bg-primary px-2.5 text-[11px] font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-40 transition-colors cursor-pointer"
                              disabled={!canWrite || mutation.isPending || isRunning || m.status === "Archived"}
                              title={
                                !canWrite
                                  ? "Read-only access"
                                  : isRunning
                                    ? "Check currently running"
                                    : "Run check now"
                              }
                              onClick={() => void handleRunCheck(m)}
                            >
                              {isRunning ? (
                                <Loader2 size={11} className="animate-spin" />
                              ) : (
                                <Play size={11} />
                              )}
                              <span>Run</span>
                            </button>

                            <Link
                              href={`/intent-radar/monitors/${m.id}`}
                              className="inline-flex h-7 items-center rounded-lg border border-border bg-card px-2.5 text-[11px] font-medium text-foreground hover:border-primary/40 transition-colors"
                            >
                              Details
                            </Link>

                            <Menu.Root>
                              <Menu.Trigger
                                className="inline-flex h-7 w-7 items-center justify-center rounded-lg border border-border bg-card text-muted-foreground hover:text-foreground hover:border-primary/40 transition-colors cursor-pointer"
                                aria-label={`Actions for ${m.name}`}
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
                                    onSelect={() => router.push(`/intent-radar/monitors/${m.id}?edit=true`)}
                                  >
                                    <Pencil size={12} className="text-muted-foreground" />
                                    <span>Edit</span>
                                  </Menu.Item>

                                  <Menu.Item
                                    className="flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs text-foreground hover:bg-accent hover:text-accent-foreground cursor-pointer outline-none disabled:opacity-50"
                                    disabled={!canWrite || mutation.isPending || m.status === "Archived"}
                                    onSelect={() => void handleTogglePause(m)}
                                  >
                                    {m.status === "Active" ? (
                                      <>
                                        <Pause size={12} className="text-muted-foreground" />
                                        <span>Pause</span>
                                      </>
                                    ) : (
                                      <>
                                        <Play size={12} className="text-muted-foreground" />
                                        <span>Resume</span>
                                      </>
                                    )}
                                  </Menu.Item>

                                  <Menu.Item
                                    className="flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs text-foreground hover:bg-accent hover:text-accent-foreground cursor-pointer outline-none disabled:opacity-50"
                                    disabled={!canWrite || mutation.isPending}
                                    onSelect={() => void handleDuplicate(m)}
                                  >
                                    <Copy size={12} className="text-muted-foreground" />
                                    <span>Duplicate</span>
                                  </Menu.Item>

                                  <Menu.Separator className="h-px bg-border my-1" />

                                  <Menu.Item
                                    className="flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs text-foreground hover:bg-accent hover:text-accent-foreground cursor-pointer outline-none disabled:opacity-50"
                                    disabled={!canWrite || mutation.isPending}
                                    onSelect={() =>
                                      m.status === "Archived"
                                        ? void handleArchive(m, true)
                                        : setArchiveTarget(m)
                                    }
                                  >
                                    <Archive size={12} className="text-muted-foreground" />
                                    <span>{m.status === "Archived" ? "Restore to Draft" : "Archive"}</span>
                                  </Menu.Item>

                                  <Menu.Item
                                    className="flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs text-destructive hover:bg-destructive/10 cursor-pointer outline-none disabled:opacity-50"
                                    disabled={!canWrite || mutation.isPending}
                                    onSelect={() => setDeleteTarget(m)}
                                  >
                                    <Trash2 size={12} />
                                    <span>Delete</span>
                                  </Menu.Item>
                                </Menu.Content>
                              </Menu.Portal>
                            </Menu.Root>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* 6. Pagination */}
          {totalMonitors > 50 && (
            <div className="flex items-center justify-between text-xs text-muted-foreground pt-2">
              <span>
                Page {page} of {Math.ceil(totalMonitors / 50)}
              </span>
              <div className="flex items-center gap-1.5">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  className="h-7 text-xs"
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page * 50 >= totalMonitors}
                  onClick={() => setPage((p) => p + 1)}
                  className="h-7 text-xs"
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Delete Confirmation Modal */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-2xl border border-border bg-card p-6 shadow-lg space-y-4">
            <div className="flex items-center gap-3 text-destructive">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-destructive/10">
                <Trash2 size={20} />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-foreground">Delete monitor?</h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Are you sure you want to delete &ldquo;{deleteTarget.name}&rdquo;?
                </p>
              </div>
            </div>
            <p className="text-xs text-muted-foreground">
              This permanently removes the monitor configuration from this workspace. Signals previously matched by this monitor will remain in your records.
            </p>
            <div className="flex items-center justify-end gap-2 pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setDeleteTarget(null)}
                disabled={mutation.isPending}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => void handleDeleteConfirm()}
                disabled={mutation.isPending}
              >
                {mutation.isPending ? "Deleting…" : "Delete Monitor"}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Archive Confirmation Modal */}
      {archiveTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-2xl border border-border bg-card p-6 shadow-lg space-y-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-muted text-muted-foreground">
                <Archive size={20} />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-foreground">Archive monitor?</h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Archive &ldquo;{archiveTarget.name}&rdquo;?
                </p>
              </div>
            </div>
            <p className="text-xs text-muted-foreground">
              This pauses all checks and removes the monitor from active lists. You can restore it anytime from the Archived tab.
            </p>
            <div className="flex items-center justify-end gap-2 pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setArchiveTarget(null)}
                disabled={mutation.isPending}
              >
                Cancel
              </Button>
              <Button
                variant="default"
                size="sm"
                onClick={() => void handleArchive(archiveTarget)}
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
