"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import * as Menu from "@radix-ui/react-dropdown-menu";
import {
  AlertCircle,
  Archive,
  ArrowLeft,
  ArrowRight,
  BookOpen,
  CalendarClock,
  CheckCircle2,
  Copy,
  ExternalLink,
  MoreHorizontal,
  Pause,
  Pencil,
  Play,
  Plus,
  Radio,
  Search,
} from "lucide-react";
import { toast } from "sonner";
import {
  emptyIntentSearch,
  type IntentJob,
  type IntentMonitor,
  type IntentPage,
  type IntentPreferences,
  type IntentSignal,
} from "@/lib/intent-radar";
import { useRadarCapabilities, useRadarMutation, useRadarRead } from "./provider";
import { Badge, EmptyState, ErrorState, LoadingSkeleton, Modal, PageHeading } from "./ui";
import { MonitorWizard } from "./wizard";
import { JobPanel } from "./jobs";
import { SignalTable } from "./signals";
import { ProviderLogo } from "./provider-logo";
import { ScheduleControls } from "./advanced-controls";

function statusTone(status: IntentMonitor["status"]): string {
  switch (status) {
    case "Active":
      return "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300";
    case "Paused":
      return "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300";
    case "Draft":
      return "border-border bg-muted text-muted-foreground";
    default:
      return "border-border bg-muted/60 text-muted-foreground";
  }
}

function formatDateTime(value?: string | null): string {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return value;
  }
}

function nextCheckLabel(m: IntentMonitor): string {
  if (m.status !== "Active") return m.status === "Paused" ? "Paused" : "Not scheduled";
  if (m.next_run_at) return formatDateTime(m.next_run_at);
  const freq = m.schedule?.frequency;
  if (!freq || freq === "Manual") return "On demand";
  return freq;
}

export function ManagedMonitorCard({ monitor: m }: { monitor: IntentMonitor }) {
  const mutation = useRadarMutation();
  const access = useRadarCapabilities();
  const [job, setJob] = useState<string | null>(null);
  const [archive, setArchive] = useState(false);
  const [error, setError] = useState("");
  const disabled = !access.data?.can_write || mutation.isPending;

  async function updateStatus(value: IntentMonitor["status"]) {
    setError("");
    try {
      await mutation.mutateAsync({
        path: "/monitors/" + m.id,
        method: "PUT",
        body: {
          name: m.name,
          description: m.description,
          goal: m.goal,
          configuration: m.configuration,
          status: value,
          revision: m.revision,
        },
      });
      setArchive(false);
      toast.success(`Monitor updated to ${value}.`);
    } catch (e) {
      const msg = (e as Error).message;
      setError(msg);
      toast.error(msg);
    }
  }

  async function runCheck() {
    setError("");
    try {
      const result = (await mutation.mutateAsync({
        path: "/discover",
        body: {
          monitor_id: m.id,
          configuration: m.configuration,
          request_id: crypto.randomUUID(),
        },
      })) as IntentJob;
      setJob(result.id);
      toast.success(`Started check for "${m.name}".`);
    } catch (e) {
      const msg = (e as Error).message;
      setError(msg);
      toast.error(msg);
    }
  }

  const selected = m.configuration.sources || ["hacker_news"];
  const sourceNames = selected.map(
    (id) => access.data?.sources.find((s) => s.id === id)?.name || id
  );

  return (
    <section className="rounded-2xl border border-border bg-card p-5 space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1.5 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${statusTone(m.status)}`}>
              {m.status}
            </span>
            <span className="text-xs text-muted-foreground">
              Created {new Date(m.created_at).toLocaleDateString()}
            </span>
          </div>
          <p className="text-sm text-muted-foreground">
            {m.description || m.goal || "Saved search criteria tracking relevant public discussions."}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            className="ir-primary inline-flex items-center gap-1.5"
            aria-label="Run manual check"
            disabled={disabled || m.status !== "Active"}
            title={
              !access.data?.can_write
                ? "You need write access to run monitor checks."
                : m.status !== "Active"
                  ? "Activate or resume this monitor to run a check."
                  : "Run an immediate check"
            }
            onClick={() => void runCheck()}
          >
            <Play size={14} /> Run Check
          </button>
          <button
            type="button"
            className="ir-button inline-flex items-center gap-1.5"
            disabled={disabled || m.status === "Archived"}
            onClick={() => void updateStatus(m.status === "Active" ? "Paused" : "Active")}
          >
            {m.status === "Active" ? <Pause size={14} /> : <Play size={14} />}
            {m.status === "Active" ? "Pause" : m.status === "Paused" ? "Resume" : "Activate"}
          </button>
          <button
            type="button"
            className="ir-button inline-flex items-center gap-1.5"
            disabled={disabled}
            onClick={() => (m.status === "Archived" ? void updateStatus("Draft") : setArchive(true))}
          >
            <Archive size={14} />
            {m.status === "Archived" ? "Restore" : "Archive"}
          </button>
        </div>
      </div>

      {/* Criteria & metrics summary */}
      <div className="grid gap-3 sm:grid-cols-4 rounded-xl border border-border/80 bg-muted/20 p-3.5 text-xs">
        <div>
          <span className="text-[11px] text-muted-foreground block">Sources</span>
          <div className="mt-1 flex flex-wrap items-center gap-1.5">
            {sourceNames.map((name) => (
              <span key={name} className="inline-flex items-center gap-1 font-medium text-foreground">
                <ProviderLogo provider={name} size={15} />
                {name}
              </span>
            ))}
          </div>
        </div>
        <div>
          <span className="text-[11px] text-muted-foreground block">Last checked</span>
          <strong className="mt-1 block text-foreground">{formatDateTime(m.last_checked)}</strong>
        </div>
        <div>
          <span className="text-[11px] text-muted-foreground block">Next check</span>
          <strong className="mt-1 block text-foreground">{nextCheckLabel(m)}</strong>
        </div>
        <div>
          <span className="text-[11px] text-muted-foreground block">Matched signals</span>
          <div className="mt-1 flex items-center gap-2">
            <strong className="text-foreground tabular-nums">{m.signals_count ?? "—"}</strong>
            <Link className="text-primary hover:underline" href={"/intent-radar/signals?monitor_id=" + m.id}>
              Open in Signals
            </Link>
          </div>
        </div>
      </div>

      {/* Keywords */}
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="text-[11px] font-medium text-muted-foreground mr-1">Keywords:</span>
        {m.configuration.keywords.map((k) => (
          <span
            key={k}
            className="rounded-md border border-border bg-muted/35 px-2 py-0.5 text-xs text-foreground"
          >
            {k}
          </span>
        ))}
        {(m.configuration.excluded || []).map((ex) => (
          <span
            key={`ex-${ex}`}
            className="rounded-md border border-destructive/20 bg-destructive/5 px-2 py-0.5 text-xs text-destructive"
          >
            −{ex}
          </span>
        ))}
      </div>

      <ScheduleControls monitor={m} />

      {error && <ErrorState message={error} />}
      {job && <JobPanel id={job} />}
      {m.last_job_id && !job && (
        <details className="rounded-xl border border-border/70 bg-muted/15 px-3.5 py-2 text-xs">
          <summary className="cursor-pointer font-medium text-foreground">
            Last check job status
          </summary>
          <div className="pt-2">
            <JobPanel id={m.last_job_id} />
          </div>
        </details>
      )}

      <Modal
        open={archive}
        onOpenChange={setArchive}
        title="Archive this monitor?"
        description="This removes the monitor from your active list. Its discovered signals and run history remain intact, and you can restore it anytime."
      >
        <div className="ir-actions">
          <button type="button" onClick={() => setArchive(false)}>
            Cancel
          </button>
          <button
            type="button"
            className="ir-primary"
            disabled={mutation.isPending}
            onClick={() => void updateStatus("Archived")}
          >
            Archive monitor
          </button>
        </div>
      </Modal>
    </section>
  );
}

function MonitorRunHistory({ id }: { id: string }) {
  const history = useRadarRead<{
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
  }>("/monitors/" + id + "/runs");

  return (
    <section className="rounded-2xl border border-border bg-card p-5 space-y-3">
      <div className="flex items-center justify-between gap-2">
        <div>
          <h2 className="text-base font-semibold text-foreground">Run history & source health</h2>
          <p className="text-xs text-muted-foreground">
            Latest 100 source-run records for this monitor. Open any run for full evidence and error diagnostics.
          </p>
        </div>
        <Link
          href="/settings?category=integrations&tab=sources"
          className="text-xs font-medium text-primary hover:underline"
        >
          Source health
        </Link>
      </div>

      {history.error ? (
        <ErrorState message={history.error.message} retry={() => void history.refetch()} />
      ) : !history.data ? (
        <LoadingSkeleton />
      ) : history.data.items.length === 0 ? (
        <p className="rounded-xl border border-dashed border-border p-6 text-center text-xs text-muted-foreground">
          No checks have run for this monitor yet. Use <strong>Run Check</strong> above to start one.
        </p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-border">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-border bg-muted/30 text-[11px] uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="px-3.5 py-2.5 font-medium">Run time</th>
                <th className="px-3.5 py-2.5 font-medium">Source</th>
                <th className="px-3.5 py-2.5 font-medium">Status</th>
                <th className="px-3.5 py-2.5 font-medium">Coverage & errors</th>
                <th className="px-3.5 py-2.5 font-medium text-right">Scanned</th>
                <th className="px-3.5 py-2.5 font-medium text-right">Run details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {history.data.items.map((run, index) => {
                const st = run.status || "Pending";
                const isErr = ["FAILED", "TIMED_OUT", "UNAVAILABLE", "ERROR"].includes(st.toUpperCase());
                const isOk = ["COMPLETE", "COMPLETED", "NO_RESULTS"].includes(st.toUpperCase());
                return (
                  <tr key={`${run.id}:${run.provider}:${index}`} className="hover:bg-muted/20">
                    <td className="px-3.5 py-2.5 whitespace-nowrap text-muted-foreground">
                      {formatDateTime(run.created_at)}
                    </td>
                    <td className="px-3.5 py-2.5 font-medium text-foreground whitespace-nowrap">
                      {run.provider || "Pending dispatch"}
                    </td>
                    <td className="px-3.5 py-2.5 whitespace-nowrap">
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
                          <AlertCircle size={11} aria-hidden="true" />
                        ) : isOk ? (
                          <CheckCircle2 size={11} aria-hidden="true" />
                        ) : null}
                        {st}
                      </span>
                    </td>
                    <td className="px-3.5 py-2.5 text-muted-foreground max-w-md">
                      <p className="line-clamp-2">
                        {run.result?.coverage || "No completed source coverage yet."}
                      </p>
                      {Array.isArray(run.result?.errors) && run.result.errors.length > 0 && (
                        <p className="text-destructive mt-0.5 line-clamp-1">
                          {run.result.errors.join("; ")}
                        </p>
                      )}
                    </td>
                    <td className="px-3.5 py-2.5 text-right tabular-nums text-muted-foreground whitespace-nowrap">
                      {run.result?.scanned ?? "—"}
                    </td>
                    <td className="px-3.5 py-2.5 text-right whitespace-nowrap">
                      <Link
                        href={`/intent-radar/discover/runs/${run.id}`}
                        className="inline-flex items-center gap-1 text-primary hover:underline font-medium"
                      >
                        Inspect <ExternalLink size={11} aria-hidden="true" />
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export function MonitorsExperience({ route }: { route: string }) {
  const router = useRouter();
  const [tab, setTabValue] = useState("Current");
  const [search, setSearchValue] = useState("");
  const [learn, setLearn] = useState(false);
  const [editing, setEditing] = useState(false);
  const [page, setPage] = useState(1);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [archiveTarget, setArchiveTarget] = useState<IntentMonitor | null>(null);

  const mutation = useRadarMutation();
  const setTab = (value: string) => {
    setTabValue(value);
    setPage(1);
  };
  const setSearch = (value: string) => {
    setSearchValue(value);
    setPage(1);
  };

  const preferences = useRadarRead<IntentPreferences>("/settings", route === "monitors/new");
  const query = useRadarRead<IntentPage<IntentMonitor>>(
    "/monitors?page_size=20&page=" + page + "&status=" + tab + "&search=" + encodeURIComponent(search)
  );
  const id = route.startsWith("monitors/") && route !== "monitors/new" ? route.split("/")[1] : "";
  const detail = useRadarRead<IntentMonitor>("/monitors/" + id, !!id);
  const related = useRadarRead<IntentPage<IntentSignal>>("/signals?monitor_id=" + id, !!id);
  const access = useRadarCapabilities();

  if (query.error || detail.error) {
    return (
      <ErrorState
        message={(query.error || detail.error)!.message}
        retry={() => void query.refetch()}
      />
    );
  }
  if (!query.data || (id && !detail.data)) return <LoadingSkeleton />;

  const monitors = query.data.items;
  const canWrite = Boolean(access.data?.can_write);
  const showEmptyWorkspaceState = !id && monitors.length === 0 && !search.trim() && tab === "Current";

  async function runMonitorCheck(m: IntentMonitor) {
    try {
      const result = (await mutation.mutateAsync({
        path: "/discover",
        body: {
          monitor_id: m.id,
          configuration: m.configuration,
          request_id: crypto.randomUUID(),
        },
      })) as IntentJob;
      setActiveJobId(result.id);
      toast.success(`Started check for "${m.name}".`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not start monitor check.");
    }
  }

  async function changeMonitorStatus(m: IntentMonitor, nextStatus: IntentMonitor["status"]) {
    try {
      await mutation.mutateAsync({
        path: "/monitors/" + m.id,
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
      toast.success(`Monitor "${m.name}" set to ${nextStatus}.`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not update monitor.");
    }
  }

  async function duplicateMonitor(m: IntentMonitor) {
    try {
      await mutation.mutateAsync({
        path: "/monitors/" + m.id + "/duplicate",
        body: { request_id: crypto.randomUUID() },
      });
      toast.success(`Duplicated "${m.name}".`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not duplicate monitor.");
    }
  }

  return (
    <div className="ir-page space-y-5">
      {id && detail.data ? (
        <>
          <div className="flex items-center justify-between gap-2">
            <Link
              href="/intent-radar/monitors"
              className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground"
            >
              <ArrowLeft size={14} /> Back to Monitors
            </Link>
            <div className="flex items-center gap-2">
              <button
                type="button"
                className="ir-button inline-flex items-center gap-1.5"
                disabled={!canWrite}
                onClick={() => setEditing(true)}
              >
                <Pencil size={14} /> Edit Monitor
              </button>
            </div>
          </div>
          <PageHeading
            title={detail.data.name}
            description="Monitor configuration, run history, source health, and matched signals."
          />
          <ManagedMonitorCard monitor={{ ...detail.data, signals_count: related.data?.total }} />
          <MonitorRunHistory id={id} />
          <section className="space-y-3">
            <div className="ir-section-heading">
              <h2>Matched signals ({related.data?.total ?? 0})</h2>
              <Link className="ir-link" href={`/intent-radar/signals?monitor_id=${id}`}>
                Open full Signals view <ArrowRight size={14} />
              </Link>
            </div>
            <SignalTable signals={related.data?.items || []} />
          </section>
        </>
      ) : (
        <>
          <PageHeading
            title="Monitors"
            description="Track recurring topics across approved sources with scheduled or on-demand checks."
            actions={
              <div className="flex items-center gap-2">
                <Link className="ir-button" href="/help?article=monitors-alerts">
                  <BookOpen size={15} /> Guide
                </Link>
                {canWrite ? (
                  <Link className="ir-button ir-primary" href="/intent-radar/monitors/new">
                    <Plus size={16} /> Create Monitor
                  </Link>
                ) : (
                  <Badge>Read-only access</Badge>
                )}
              </div>
            }
          />

          {activeJobId && <JobPanel id={activeJobId} />}

          {showEmptyWorkspaceState ? (
            <div className="rounded-2xl border border-border bg-card p-8 sm:p-10 text-center max-w-2xl mx-auto space-y-4">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl border border-primary/20 bg-primary/10 text-primary">
                <Radio size={22} aria-hidden="true" />
              </div>
              <div className="space-y-1.5">
                <h2 className="text-lg font-semibold text-foreground">
                  No monitors configured yet
                </h2>
                <p className="text-sm text-muted-foreground max-w-md mx-auto">
                  Save keywords, intent categories, and sources as a monitor to track recurring buyer discussions automatically or on demand.
                </p>
              </div>
              <div className="flex flex-wrap items-center justify-center gap-2.5 pt-1">
                {canWrite && (
                  <Link className="ir-button ir-primary" href="/intent-radar/monitors/new">
                    Create Monitor <ArrowRight size={15} />
                  </Link>
                )}
                <button type="button" className="ir-button" onClick={() => setLearn(true)}>
                  <BookOpen size={15} /> How monitors work
                </button>
                <button
                  type="button"
                  className="text-xs font-medium text-muted-foreground hover:text-foreground px-2 py-1.5 cursor-pointer"
                  onClick={() => setTab("Archived")}
                >
                  View archived
                </button>
              </div>
            </div>
          ) : (
            <>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-wrap items-center gap-1.5" role="tablist" aria-label="Monitor status">
                  {["Current", "Active", "Paused", "Draft", "Archived"].map((t) => (
                    <button
                      key={t}
                      type="button"
                      role="tab"
                      aria-selected={tab === t}
                      onClick={() => setTab(t)}
                      className={
                        "rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors cursor-pointer " +
                        (tab === t
                          ? "border-primary/40 bg-primary/10 text-primary font-semibold"
                          : "border-border bg-card text-muted-foreground hover:text-foreground")
                      }
                    >
                      {t}
                    </button>
                  ))}
                </div>
                <div className="flex items-center gap-2.5">
                  <div className="relative min-w-[210px]">
                    <Search
                      size={14}
                      className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none"
                    />
                    <input
                      type="search"
                      aria-label="Search monitors"
                      value={search}
                      placeholder="Find a monitor…"
                      onChange={(e) => setSearch(e.target.value)}
                      className="w-full rounded-xl border border-border bg-card pl-8 pr-3 py-1.5 text-xs text-foreground"
                    />
                  </div>
                  <span className="text-xs text-muted-foreground tabular-nums whitespace-nowrap">
                    {query.data.total} monitor{query.data.total === 1 ? "" : "s"}
                  </span>
                </div>
              </div>

              {monitors.length === 0 ? (
                <EmptyState
                  title={
                    search
                      ? "No monitors match your search"
                      : `No ${tab.toLowerCase()} monitors`
                  }
                  description={
                    search
                      ? "Try another monitor name or clear your search filter."
                      : "Monitors with this status will appear here."
                  }
                  action={
                    search ? (
                      <button type="button" onClick={() => setSearch("")}>
                        Clear search
                      </button>
                    ) : tab !== "Current" ? (
                      <button type="button" onClick={() => setTab("Current")}>
                        Back to Current monitors
                      </button>
                    ) : undefined
                  }
                  icon={Radio}
                />
              ) : (
                <div className="overflow-x-auto rounded-2xl border border-border bg-card">
                  <table className="w-full text-left text-xs">
                    <thead className="border-b border-border bg-muted/30 text-[11px] uppercase tracking-wide text-muted-foreground">
                      <tr>
                        <th className="px-4 py-3 font-medium">Monitor &amp; criteria</th>
                        <th className="px-3 py-3 font-medium">Status</th>
                        <th className="px-3 py-3 font-medium">Sources</th>
                        <th className="px-3 py-3 font-medium">Last checked</th>
                        <th className="px-3 py-3 font-medium">Next check</th>
                        <th className="px-3 py-3 font-medium text-right">Matches</th>
                        <th className="px-4 py-3 font-medium text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {monitors.map((m) => {
                        const sources = m.configuration.sources || ["hacker_news"];
                        const sourceNames = sources.map(
                          (sid) => access.data?.sources.find((s) => s.id === sid)?.name || sid
                        );
                        return (
                          <tr key={m.id} className="hover:bg-muted/20 transition-colors">
                            <td className="px-4 py-3 max-w-xs">
                              <Link
                                href={`/intent-radar/monitors/${m.id}`}
                                className="font-semibold text-sm text-foreground hover:text-primary block truncate"
                              >
                                {m.name}
                              </Link>
                              <div className="mt-1 flex flex-wrap gap-1">
                                {(m.configuration.keywords || []).slice(0, 3).map((kw) => (
                                  <span
                                    key={kw}
                                    className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground"
                                  >
                                    {kw}
                                  </span>
                                ))}
                                {(m.configuration.keywords || []).length > 3 && (
                                  <span className="text-[10px] text-muted-foreground px-1">
                                    +{(m.configuration.keywords || []).length - 3}
                                  </span>
                                )}
                              </div>
                            </td>
                            <td className="px-3 py-3 whitespace-nowrap">
                              <span
                                className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold ${statusTone(m.status)}`}
                              >
                                {m.status}
                              </span>
                            </td>
                            <td className="px-3 py-3">
                              <div className="flex flex-wrap items-center gap-1.5">
                                {sourceNames.slice(0, 2).map((name) => (
                                  <span
                                    key={name}
                                    className="inline-flex items-center gap-1 rounded-md border border-border/70 bg-muted/25 px-1.5 py-0.5 text-[11px] text-foreground whitespace-nowrap"
                                  >
                                    <ProviderLogo provider={name} size={13} />
                                    {name}
                                  </span>
                                ))}
                                {sourceNames.length > 2 && (
                                  <span className="text-[10px] text-muted-foreground">
                                    +{sourceNames.length - 2}
                                  </span>
                                )}
                              </div>
                            </td>
                            <td className="px-3 py-3 whitespace-nowrap text-muted-foreground">
                              {formatDateTime(m.last_checked)}
                            </td>
                            <td className="px-3 py-3 whitespace-nowrap text-muted-foreground">
                              <span className="inline-flex items-center gap-1">
                                <CalendarClock size={12} aria-hidden="true" />
                                {nextCheckLabel(m)}
                              </span>
                            </td>
                            <td className="px-3 py-3 text-right tabular-nums whitespace-nowrap">
                              <Link
                                href={`/intent-radar/signals?monitor_id=${m.id}`}
                                className="font-semibold text-foreground hover:text-primary"
                              >
                                {m.signals_count ?? 0}
                              </Link>
                            </td>
                            <td className="px-4 py-3 text-right whitespace-nowrap">
                              <div className="inline-flex items-center justify-end gap-1.5">
                                <button
                                  type="button"
                                  className="inline-flex h-7 items-center gap-1 rounded-lg bg-primary px-2.5 text-[11px] font-medium text-primary-foreground hover:opacity-90 disabled:opacity-45 cursor-pointer"
                                  disabled={!canWrite || mutation.isPending || m.status !== "Active"}
                                  title={
                                    !canWrite
                                      ? "Read-only workspace access"
                                      : m.status !== "Active"
                                        ? "Activate this monitor to run checks"
                                        : "Run check now"
                                  }
                                  onClick={() => void runMonitorCheck(m)}
                                >
                                  <Play size={11} /> Run
                                </button>
                                <Link
                                  href={`/intent-radar/monitors/${m.id}`}
                                  className="inline-flex h-7 items-center rounded-lg border border-border bg-card px-2.5 text-[11px] font-medium text-foreground hover:border-primary/40"
                                >
                                  Details
                                </Link>
                                <Menu.Root>
                                  <Menu.Trigger
                                    className="inline-flex h-7 w-7 items-center justify-center rounded-lg border border-border bg-card text-muted-foreground hover:text-foreground cursor-pointer"
                                    aria-label={"Actions for " + m.name}
                                  >
                                    <MoreHorizontal size={14} />
                                  </Menu.Trigger>
                                  <Menu.Portal>
                                    <Menu.Content className="ir-menu" sideOffset={6} collisionPadding={12}>
                                      <Menu.Item
                                        className="ir-menu-item"
                                        disabled={!canWrite || mutation.isPending || m.status === "Archived"}
                                        onSelect={() =>
                                          void changeMonitorStatus(
                                            m,
                                            m.status === "Active" ? "Paused" : "Active"
                                          )
                                        }
                                      >
                                        {m.status === "Active" ? <Pause size={14} /> : <Play size={14} />}
                                        {m.status === "Active"
                                          ? "Pause"
                                          : m.status === "Paused"
                                            ? "Resume"
                                            : "Activate"}
                                      </Menu.Item>
                                      <Menu.Item
                                        className="ir-menu-item"
                                        disabled={!canWrite || mutation.isPending}
                                        onSelect={() => void duplicateMonitor(m)}
                                      >
                                        <Copy size={14} /> Duplicate
                                      </Menu.Item>
                                      <Menu.Item
                                        className="ir-menu-item"
                                        disabled={!canWrite || mutation.isPending}
                                        onSelect={() =>
                                          m.status === "Archived"
                                            ? void changeMonitorStatus(m, "Draft")
                                            : setArchiveTarget(m)
                                        }
                                      >
                                        <Archive size={14} />
                                        {m.status === "Archived" ? "Restore draft" : "Archive"}
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

              {query.data.total > 20 && (
                <nav className="ir-pagination" aria-label="Monitor pages">
                  <span>
                    Page {page} of {Math.ceil(query.data.total / 20)}
                  </span>
                  <button type="button" disabled={page <= 1} onClick={() => setPage(page - 1)}>
                    Previous
                  </button>
                  <button
                    type="button"
                    disabled={page * 20 >= query.data.total}
                    onClick={() => setPage(page + 1)}
                  >
                    Next
                  </button>
                </nav>
              )}
            </>
          )}
        </>
      )}

      {((route === "monitors/new" && preferences.data) || editing) && (
        <MonitorWizard
          existing={detail.data}
          configuration={
            preferences.data
              ? {
                  ...emptyIntentSearch(),
                  keywords: preferences.data.discovery_keywords || [],
                  excluded: preferences.data.discovery_excluded || [],
                  topics: preferences.data.topics,
                  min_relevance: preferences.data.min_relevance ?? 0,
                  icp_id: preferences.data.default_icp_id || null,
                }
              : undefined
          }
          open
          onClose={() => {
            if (route === "monitors/new") router.push("/intent-radar/monitors");
            else setEditing(false);
          }}
        />
      )}

      {route === "monitors/new" && preferences.error && (
        <ErrorState message={preferences.error.message} retry={() => void preferences.refetch()} />
      )}

      <Modal
        open={Boolean(archiveTarget)}
        onOpenChange={(open) => {
          if (!open) setArchiveTarget(null);
        }}
        title="Archive this monitor?"
        description="This removes the monitor from your active list. Its signals and run history remain intact, and you can restore it later."
      >
        <div className="ir-actions">
          <button type="button" onClick={() => setArchiveTarget(null)}>
            Cancel
          </button>
          <button
            type="button"
            className="ir-primary"
            disabled={mutation.isPending}
            onClick={() => archiveTarget && void changeMonitorStatus(archiveTarget, "Archived")}
          >
            Archive monitor
          </button>
        </div>
      </Modal>

      <Modal
        open={learn}
        onOpenChange={setLearn}
        title="How monitors work"
        description="A monitor saves your keywords, sources, and intent filters so you can track fresh public conversations continuously."
      >
        <ol className="ir-source-limits">
          <li>Define keywords, exclusions, and approved sources for the buyer problems you track.</li>
          <li>Run an immediate check anytime or configure a recurring schedule inside the monitor details view.</li>
          <li>Review new matched signals, inspect source evidence, and promote qualified signals to Opportunities.</li>
        </ol>
        <p className="text-xs text-muted-foreground">
          Saving, duplicating, or editing a monitor will not trigger an unrequested check until you run one or enable a schedule.
        </p>
        {canWrite && (
          <Link className="ir-button ir-primary" href="/intent-radar/monitors/new">
            Create Monitor
          </Link>
        )}
      </Modal>
    </div>
  );
}
