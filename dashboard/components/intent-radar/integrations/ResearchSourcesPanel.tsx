"use client";

import { useState } from "react";
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Loader2,
  Plug,
  Radio,
  RefreshCw,
  Rss,
  Settings2,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Wifi,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useRadarCapabilities, useRadarMutation, useRadarRead } from "../provider";
import { ProviderLogo } from "../provider-logo";
import { SlideOverDrawer } from "./SlideOverDrawer";
import {
  deriveOperationalHealth,
  deriveSourceAvailability,
  type FeedConfig,
  type GitHubStatus,
  type ProviderTestResult,
  type SourceAvailabilityStatus,
  type SourceHealthItem,
  type SourceOperationalHealth,
} from "./types";

const AVAILABILITY_STYLES: Record<SourceAvailabilityStatus, string> = {
  Connected: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/25",
  Available: "bg-blue-500/10 text-blue-700 dark:text-blue-300 border-blue-500/25",
  "No custom feeds": "bg-muted text-muted-foreground border-border",
  "Setup required": "bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/30",
  "Permission required": "bg-muted text-muted-foreground border-border",
  Disabled: "bg-muted text-muted-foreground border-border",
};

const HEALTH_STYLES: Record<SourceOperationalHealth, string> = {
  Healthy: "text-emerald-700 dark:text-emerald-400",
  Degraded: "text-amber-700 dark:text-amber-300",
  Failed: "text-destructive",
  Checking: "text-blue-600 dark:text-blue-400",
  "Not yet checked": "text-muted-foreground",
};

function formatRelativeOrTime(iso: string | null | undefined): string {
  if (!iso) return "Not yet checked";
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function aiBadgeMeta(
  id: string,
  policy?: {
    ai_processing_authorized?: boolean;
    ai_status?: string;
  },
  aiAnalyticsAuthorized?: boolean
): { label: string; tone: "authorized" | "per_feed" | "restricted" } {
  const statusLower = (policy?.ai_status || "").toLowerCase();
  if (statusLower.includes("per-feed")) {
    return { label: "Per-feed AI policy", tone: "per_feed" };
  }
  if (policy?.ai_processing_authorized === true) {
    return { label: "AI Authorized", tone: "authorized" };
  }
  if (policy?.ai_processing_authorized === false) {
    return { label: "AI Restricted", tone: "restricted" };
  }
  if (id === "youtube") {
    return aiAnalyticsAuthorized
      ? { label: "AI Authorized", tone: "authorized" }
      : { label: "AI Restricted", tone: "restricted" };
  }
  if (id === "discourse") return { label: "AI Restricted", tone: "restricted" };
  if (id === "atom" || id === "rss") return { label: "Per-feed AI policy", tone: "per_feed" };
  return { label: "AI Authorized", tone: "authorized" };
}

const CAPABILITY_LABELS: Record<string, string> = {
  fetch: "Fetch",
  search: "Discovery search",
  store: "Signal storage",
  display: "UI display",
  classify: "AI classification",
  summarize: "AI summary",
  analyze_intent: "Buyer intent AI",
  derived_metrics: "Derived metrics",
  monitor: "Monitoring",
  export: "Export",
};

export function ResearchSourcesPanel({
  onOpenFeedsTab,
}: {
  onOpenFeedsTab?: () => void;
}) {
  const access = useRadarCapabilities();
  const healthQuery = useRadarRead<{ items: SourceHealthItem[] }>("/sources/health");
  const githubQuery = useRadarRead<GitHubStatus>("/sources/github/status");
  const configsQuery = useRadarRead<{ items: FeedConfig[] }>("/sources/configurations");
  const mutation = useRadarMutation();

  const [selectedSourceId, setSelectedSourceId] = useState<string | null>(null);
  const [repoSelection, setRepoSelection] = useState<number[] | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, ProviderTestResult>>({});
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  const sources = access.data?.sources || [];
  const healthItems = healthQuery.data?.items || [];
  const configs = configsQuery.data?.items || [];
  const gh = githubQuery.data;

  const findHealth = (sourceId: string) =>
    healthItems.find(
      (h) =>
        h.provider === sourceId ||
        h.provider.replaceAll("_", "") === sourceId.replaceAll("_", "")
    );

  // Real backend-computed overview indicators
  const connectedCount = gh?.status === "CONNECTED" ? 1 : 0;
  const availableCount = sources.filter(
    (s) => s.state === "Available" || s.state === "Connected"
  ).length;
  const enabledFeedsCount = configs.filter((c) => c.enabled).length;
  const aiReadyCount = sources.filter((s) => {
    const id = s.id || "hacker_news";
    const meta = aiBadgeMeta(id, s.policy, s.ai_analytics_authorized);
    return meta.tone === "authorized" || (meta.tone === "per_feed" && configs.some((c) => c.family === id && c.enabled && c.ai_processing_authorized));
  }).length;
  const attentionCount = healthItems.filter(
    (h) => (h.consecutive_failures ?? 0) > 0 || h.state === "FAILED"
  ).length;

  async function testConnection(providerId: string) {
    setBusyAction(`test:${providerId}`);
    setError("");
    setNotice("");
    try {
      const res = (await mutation.mutateAsync({
        path: `/sources/${providerId}/test`,
        method: "POST",
        body: {},
      })) as ProviderTestResult;
      setTestResults((prev) => ({ ...prev, [providerId]: res }));
      if (res.ok) {
        setNotice(`${res.summary}${res.latency_ms != null ? ` (${res.latency_ms} ms)` : ""}`);
      } else {
        setError(res.error || res.summary || `Connection test failed for ${providerId}.`);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not run source connection check.");
    } finally {
      setBusyAction(null);
    }
  }

  async function connectGitHub(mode: "oauth" | "install") {
    setBusyAction(`gh-${mode}`);
    setError("");
    setNotice("");
    try {
      const res = (await mutation.mutateAsync({
        path: "/sources/github/oauth/start",
        method: "POST",
        body: {},
      })) as { authorize_url: string; install_url: string };
      window.location.assign(mode === "install" ? res.install_url : res.authorize_url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start GitHub connection.");
    } finally {
      setBusyAction(null);
    }
  }

  async function disconnectGitHub() {
    setBusyAction("gh-disconnect");
    setError("");
    setNotice("");
    try {
      await mutation.mutateAsync({
        path: "/sources/github/disconnect",
        method: "POST",
        body: {},
      });
      setRepoSelection(null);
      setNotice("GitHub workspace connection disconnected.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not disconnect GitHub.");
    } finally {
      setBusyAction(null);
    }
  }

  async function saveRepos() {
    if (!repoSelection) return;
    setBusyAction("gh-repos");
    setError("");
    setNotice("");
    try {
      await mutation.mutateAsync({
        path: "/sources/github/repositories",
        method: "PUT",
        body: { repository_ids: repoSelection },
      });
      setRepoSelection(null);
      setNotice("Authorized GitHub repositories saved.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not update repository selection.");
    } finally {
      setBusyAction(null);
    }
  }

  async function pollJetstream() {
    setBusyAction("bsky-poll");
    setError("");
    setNotice("");
    try {
      const res = (await mutation.mutateAsync({
        path: "/sources/bluesky/stream-poll",
        method: "POST",
        body: {},
      })) as { status: string; events: number; sequence: number };
      setNotice(
        `Bluesky Jetstream polled: ${res.status} (${res.events} event${res.events === 1 ? "" : "s"}, cursor #${res.sequence}).`
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not poll Bluesky Jetstream.");
    } finally {
      setBusyAction(null);
    }
  }

  const selectedSource = sources.find((s) => (s.id || "hacker_news") === selectedSourceId) || null;
  const selectedHealth = selectedSourceId ? findHealth(selectedSourceId) : null;
  const selectedTest = selectedSourceId ? testResults[selectedSourceId] : null;
  const selectedRepoIds =
    repoSelection ?? (gh?.repositories?.filter((r) => r.selected).map((r) => r.id) || []);

  if (access.isPending) {
    return (
      <div className="space-y-4" role="status" aria-label="Loading research sources">
        <div className="grid gap-3 grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((n) => (
            <div key={n} className="h-20 rounded-xl border border-border bg-muted/30 animate-pulse" />
          ))}
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          {[1, 2, 3, 4].map((n) => (
            <div key={n} className="h-44 rounded-2xl border border-border bg-muted/30 animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (access.isError) {
    return (
      <div role="alert" className="rounded-2xl border border-destructive/25 bg-destructive/5 p-5 space-y-3">
        <p className="text-sm font-semibold text-destructive">
          Research sources could not be loaded
        </p>
        <p className="text-xs text-muted-foreground">{access.error?.message}</p>
        <Button variant="outline" size="sm" onClick={() => void access.refetch()}>
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Compact Integration Overview Strip */}
      <div
        className="grid gap-3 grid-cols-2 lg:grid-cols-4"
        aria-label="Integration overview"
      >
        <div className="rounded-xl border border-border bg-card px-4 py-3">
          <p className="text-[11px] font-medium text-muted-foreground">Connected accounts</p>
          <p className="text-lg font-bold tracking-tight text-foreground mt-0.5 tabular-nums">
            {connectedCount}
          </p>
          <p className="text-[11px] text-muted-foreground truncate">
            {gh?.account_login ? `GitHub · ${gh.account_login}` : "No customer OAuth linked"}
          </p>
        </div>

        <div className="rounded-xl border border-border bg-card px-4 py-3">
          <p className="text-[11px] font-medium text-muted-foreground">Active sources</p>
          <p className="text-lg font-bold tracking-tight text-foreground mt-0.5 tabular-nums">
            {availableCount}
            <span className="text-xs font-normal text-muted-foreground"> / {sources.length}</span>
          </p>
          <p className="text-[11px] text-muted-foreground">
            {aiReadyCount} AI-authorized · {attentionCount > 0 ? `${attentionCount} degraded` : "0 errors"}
          </p>
        </div>

        <div className="rounded-xl border border-border bg-card px-4 py-3">
          <p className="text-[11px] font-medium text-muted-foreground">Enabled feeds</p>
          <p className="text-lg font-bold tracking-tight text-foreground mt-0.5 tabular-nums">
            {enabledFeedsCount}
          </p>
          <p className="text-[11px] text-muted-foreground">
            {onOpenFeedsTab ? (
              <button
                type="button"
                onClick={onOpenFeedsTab}
                className="text-left text-primary font-medium hover:underline cursor-pointer"
              >
                Manage custom feeds →
              </button>
            ) : (
              "Discourse, Atom & RSS feeds"
            )}
          </p>
        </div>

        <div className="rounded-xl border border-border bg-card px-4 py-3">
          <p className="text-[11px] font-medium text-muted-foreground">Operational health</p>
          <p
            className={
              "text-lg font-bold tracking-tight mt-0.5 tabular-nums " +
              (attentionCount > 0
                ? "text-amber-600 dark:text-amber-400"
                : "text-emerald-600 dark:text-emerald-400")
            }
          >
            {attentionCount > 0 ? `${attentionCount} Attention` : "Healthy"}
          </p>
          <p className="text-[11px] text-muted-foreground">
            {attentionCount > 0 ? "Review failing adapter details" : "No active adapter errors"}
          </p>
        </div>
      </div>

      {notice && (
        <div
          role="status"
          className="rounded-xl border border-emerald-500/25 bg-emerald-500/10 px-4 py-2.5 text-xs font-medium text-emerald-700 dark:text-emerald-300 flex items-center gap-2"
        >
          <CheckCircle2 size={14} className="shrink-0" aria-hidden="true" />
          <span>{notice}</span>
        </div>
      )}
      {error && (
        <div
          role="alert"
          className="rounded-xl border border-destructive/25 bg-destructive/5 px-4 py-2.5 text-xs font-medium text-destructive flex items-center gap-2"
        >
          <AlertCircle size={14} className="shrink-0" aria-hidden="true" />
          <span>{error}</span>
        </div>
      )}

      {/* Structured Research Sources Directory */}
      <div className="grid gap-4 sm:grid-cols-2">
        {sources.map((src) => {
          const id = src.id || "hacker_news";
          const health = findHealth(id);
          const liveTest = testResults[id];
          const availability = deriveSourceAvailability(
            src.state,
            gh,
            id,
            src.availability_label
          );
          const opHealth: SourceOperationalHealth = liveTest
            ? liveTest.ok
              ? "Healthy"
              : "Failed"
            : deriveOperationalHealth(health);
          const aiMeta = aiBadgeMeta(id, src.policy, src.ai_analytics_authorized);
          const isFeedFamily = id === "discourse" || id === "atom" || id === "rss";
          const familyFeedCount = isFeedFamily
            ? src.enabled_feeds_count ?? configs.filter((c) => c.family === id && c.enabled).length
            : 0;
          const isTesting = busyAction === `test:${id}`;

          return (
            <article
              key={id}
              data-testid={`source-card-${id}`}
              className="flex flex-col justify-between rounded-2xl border border-border bg-card p-5 space-y-4 hover:border-primary/35 transition-colors"
            >
              <div className="space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-border/80 bg-muted/30 shrink-0">
                      <ProviderLogo provider={id} size={22} />
                    </div>
                    <div className="min-w-0">
                      <h3 className="text-sm font-semibold text-foreground truncate">{src.name}</h3>
                      <p className="text-[11px] text-muted-foreground flex items-center gap-1.5 mt-0.5 flex-wrap">
                        <Activity size={11} className={HEALTH_STYLES[opHealth]} aria-hidden="true" />
                        <span className={HEALTH_STYLES[opHealth]}>{opHealth}</span>
                        {(liveTest?.checked_at || health?.last_success) && (
                          <span>
                            · {formatRelativeOrTime(liveTest?.checked_at || health?.last_success)}
                          </span>
                        )}
                      </p>
                    </div>
                  </div>

                  <span
                    className={`rounded-full border px-2.5 py-0.5 text-[11px] font-semibold shrink-0 ${AVAILABILITY_STYLES[availability]}`}
                  >
                    {availability}
                  </span>
                </div>

                {/* Centralized AI Permission & Source Capability Pill Row */}
                <div className="flex flex-wrap items-center gap-1.5">
                  <span
                    className={
                      "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold " +
                      (aiMeta.tone === "authorized"
                        ? "border-emerald-500/25 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
                        : aiMeta.tone === "per_feed"
                          ? "border-blue-500/25 bg-blue-500/10 text-blue-700 dark:text-blue-300"
                          : "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300")
                    }
                  >
                    {aiMeta.tone === "authorized" ? (
                      <Sparkles size={10} aria-hidden="true" />
                    ) : aiMeta.tone === "per_feed" ? (
                      <ShieldCheck size={10} aria-hidden="true" />
                    ) : (
                      <ShieldAlert size={10} aria-hidden="true" />
                    )}
                    {aiMeta.label}
                  </span>

                  {liveTest && (
                    <span
                      className={
                        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium " +
                        (liveTest.ok
                          ? "border-emerald-500/20 bg-emerald-500/5 text-emerald-700 dark:text-emerald-300"
                          : "border-destructive/25 bg-destructive/5 text-destructive")
                      }
                    >
                      {liveTest.ok
                        ? `Verified${liveTest.latency_ms != null ? ` · ${liveTest.latency_ms}ms` : ""}`
                        : `Check failed`}
                    </span>
                  )}
                </div>

                <p className="text-xs text-muted-foreground leading-relaxed line-clamp-2">
                  {src.coverage}
                </p>

                {/* Provider-specific concise operational facts */}
                <div className="space-y-1.5 text-xs">
                  {id === "github" && gh && (
                    <div className="rounded-xl bg-muted/30 px-3 py-2 space-y-1">
                      {gh.account_login ? (
                        <p className="text-foreground font-medium">
                          Connected account: <span className="font-semibold">{gh.account_login}</span>
                          {gh.installation_id ? ` · Installation #${gh.installation_id}` : ""}
                        </p>
                      ) : (
                        <p className="text-muted-foreground">
                          Public search {gh.public_search_available ? "available" : "unavailable"} · No workspace account connected
                        </p>
                      )}
                      <p className="text-[11px] text-muted-foreground">
                        Webhooks: {gh.webhooks_configured ? "Active (HMAC-SHA256)" : "Not configured"}
                      </p>
                    </div>
                  )}

                  {id === "youtube" && (
                    <div className="rounded-xl bg-muted/30 px-3 py-2 text-[11px] text-muted-foreground flex items-start gap-2">
                      <ShieldAlert size={13} className="text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" aria-hidden="true" />
                      <span>
                        Public video &amp; comment search ready.{" "}
                        {src.ai_analytics_authorized
                          ? "Derived AI analysis authorized."
                          : "Derived AI analysis restricted by YouTube API policy."}
                      </span>
                    </div>
                  )}

                  {id === "bluesky" && health?.stream_health && (
                    <div className="rounded-xl bg-muted/30 px-3 py-2 text-[11px] text-muted-foreground flex items-center justify-between gap-2">
                      <span className="truncate">
                        Jetstream v2: <strong className="text-foreground">{health.stream_health.state}</strong> · Cursor #{health.stream_health.sequence}
                      </span>
                      {access.data?.can_manage && health.stream_health.enabled && (
                        <button
                          type="button"
                          disabled={busyAction !== null}
                          onClick={() => void pollJetstream()}
                          className="text-primary font-semibold hover:underline shrink-0 cursor-pointer disabled:opacity-50"
                        >
                          {busyAction === "bsky-poll" ? "Polling…" : "Poll stream"}
                        </button>
                      )}
                    </div>
                  )}

                  {id === "stack_exchange" && src.configured_sites && (
                    <p className="text-[11px] text-muted-foreground">
                      Official API v2.3 · {src.configured_sites.length} communities configured (up to 5 per search)
                    </p>
                  )}

                  {isFeedFamily && (
                    <p className="text-[11px] text-muted-foreground">
                      {familyFeedCount > 0
                        ? `${familyFeedCount} enabled ${familyFeedCount === 1 ? "feed" : "feeds"} active for discovery & monitoring`
                        : id === "rss"
                          ? "No custom RSS feeds added — Atom & Discourse presets are managed in Custom Feeds"
                          : "No feeds enabled yet — enable presets or add an approved feed"}
                    </p>
                  )}

                  {health?.last_error?.code && !liveTest?.ok && (
                    <p className="text-[11px] text-destructive flex items-center gap-1.5">
                      <AlertCircle size={12} aria-hidden="true" />
                      Last error: {health.last_error.code}
                    </p>
                  )}
                </div>
              </div>

              {/* Action Bar */}
              <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border/70 pt-3">
                <div className="flex flex-wrap items-center gap-2">
                  {id === "github" && access.data?.can_manage && gh && gh.status !== "CONNECTED" ? (
                    <Button
                      size="sm"
                      disabled={busyAction !== null || !gh.oauth_configured}
                      onClick={() => void connectGitHub("oauth")}
                      className="h-8 text-xs gap-1.5"
                    >
                      <Plug size={13} />
                      {busyAction === "gh-oauth" ? "Connecting…" : "Connect GitHub"}
                    </Button>
                  ) : isFeedFamily && onOpenFeedsTab ? (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={onOpenFeedsTab}
                      className="h-8 text-xs gap-1.5"
                    >
                      <Rss size={13} />
                      Manage Feeds
                    </Button>
                  ) : null}

                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setSelectedSourceId(id);
                      setShowAdvanced(false);
                    }}
                    className="h-8 text-xs gap-1.5"
                  >
                    <Settings2 size={13} />
                    {id === "github" && gh?.status === "CONNECTED" ? "Manage Connection" : "Details"}
                  </Button>

                  <Button
                    size="sm"
                    variant="ghost"
                    disabled={busyAction !== null}
                    onClick={() => void testConnection(id)}
                    className="h-8 px-2.5 text-xs gap-1 text-muted-foreground hover:text-foreground"
                    title="Run lightweight live connectivity check"
                  >
                    {isTesting ? (
                      <Loader2 size={12} className="animate-spin" />
                    ) : (
                      <Wifi size={12} />
                    )}
                    {isTesting ? "Testing…" : "Test"}
                  </Button>
                </div>

                {src.documentation?.startsWith("https://") && (
                  <a
                    href={src.documentation}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-[11px] font-medium text-muted-foreground hover:text-primary"
                  >
                    Docs <ExternalLink size={11} />
                  </a>
                )}
              </div>
            </article>
          );
        })}
      </div>

      {/* Self-Contained Slide-Over Source Details & Management Drawer */}
      <SlideOverDrawer
        open={!!selectedSource}
        onClose={() => {
          setSelectedSourceId(null);
          setRepoSelection(null);
        }}
        title={selectedSource?.name || "Source details"}
        subtitle={selectedSource?.coverage || "Review source configuration, policy, and operational health."}
        icon={
          selectedSource ? (
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-border bg-muted/30">
              <ProviderLogo provider={selectedSource.id || selectedSource.name} size={22} />
            </div>
          ) : undefined
        }
      >
        {selectedSource && (() => {
          const id = selectedSource.id || "hacker_news";
          const availability = deriveSourceAvailability(
            selectedSource.state,
            gh,
            id,
            selectedSource.availability_label
          );
          const opHealth: SourceOperationalHealth = selectedTest
            ? selectedTest.ok
              ? "Healthy"
              : "Failed"
            : deriveOperationalHealth(selectedHealth);
          const aiMeta = aiBadgeMeta(id, selectedSource.policy, selectedSource.ai_analytics_authorized);
          const isTesting = busyAction === `test:${id}`;
          const isFeedFamily = id === "discourse" || id === "atom" || id === "rss";
          const familyFeeds = isFeedFamily ? configs.filter((c) => c.family === id) : [];

          return (
            <div className="space-y-5 text-xs">
              {/* Status Pills + Live Test Connection CTA */}
              <div className="rounded-xl border border-border bg-muted/20 p-4 space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={`rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${AVAILABILITY_STYLES[availability]}`}
                    >
                      {availability}
                    </span>
                    <span className={`font-semibold ${HEALTH_STYLES[opHealth]}`}>
                      Health: {opHealth}
                    </span>
                  </div>

                  <Button
                    size="sm"
                    variant="outline"
                    disabled={busyAction !== null}
                    onClick={() => void testConnection(id)}
                    className="h-8 text-xs gap-1.5"
                  >
                    {isTesting ? (
                      <Loader2 size={13} className="animate-spin" />
                    ) : (
                      <Wifi size={13} />
                    )}
                    {isTesting ? "Testing…" : "Test Connection"}
                  </Button>
                </div>

                {selectedTest && (
                  <div
                    role="status"
                    className={
                      "rounded-lg border px-3 py-2.5 space-y-1 " +
                      (selectedTest.ok
                        ? "border-emerald-500/25 bg-emerald-500/10 text-emerald-800 dark:text-emerald-200"
                        : "border-destructive/25 bg-destructive/5 text-destructive")
                    }
                  >
                    <p className="font-semibold">{selectedTest.summary}</p>
                    <p className="text-[11px] opacity-85">
                      {selectedTest.http_status ? `HTTP ${selectedTest.http_status} · ` : ""}
                      {selectedTest.latency_ms != null ? `${selectedTest.latency_ms} ms · ` : ""}
                      {selectedTest.quota_remaining != null
                        ? `Quota remaining: ${selectedTest.quota_remaining} · `
                        : ""}
                      Checked {formatRelativeOrTime(selectedTest.checked_at)}
                    </p>
                  </div>
                )}
              </div>

              {/* Centralized Permissions & AI Processing Policy */}
              <div className="rounded-xl border border-border bg-card p-4 space-y-3">
                <div className="flex items-center justify-between gap-2">
                  <h4 className="font-semibold text-sm text-foreground flex items-center gap-1.5">
                    <ShieldCheck size={14} className="text-primary" /> Permissions &amp; AI Policy
                  </h4>
                  <span
                    className={
                      "rounded-full border px-2 py-0.5 text-[10px] font-semibold " +
                      (aiMeta.tone === "authorized"
                        ? "border-emerald-500/25 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
                        : aiMeta.tone === "per_feed"
                          ? "border-blue-500/25 bg-blue-500/10 text-blue-700 dark:text-blue-300"
                          : "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300")
                    }
                  >
                    {aiMeta.label}
                  </span>
                </div>

                <dl className="grid grid-cols-2 gap-3">
                  <div>
                    <dt className="text-muted-foreground">Commercial use</dt>
                    <dd className="font-medium text-foreground mt-0.5">
                      {selectedSource.policy?.commercial_use_authorized !== false
                        ? "Permitted"
                        : "Restricted"}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">AI processing</dt>
                    <dd className="font-medium text-foreground mt-0.5">
                      {selectedSource.policy?.ai_status || aiMeta.label}
                    </dd>
                  </div>
                  <div className="col-span-2">
                    <dt className="text-muted-foreground">Retention &amp; attribution</dt>
                    <dd className="text-foreground mt-0.5 leading-relaxed">
                      {selectedSource.policy?.retention_days
                        ? `Up to ${selectedSource.policy.retention_days} days retention`
                        : "Workspace retention controls apply"}
                      {selectedSource.policy?.attribution_required
                        ? ` · ${selectedSource.policy.attribution_required}`
                        : ""}
                    </dd>
                  </div>
                </dl>

                {selectedSource.policy?.capabilities && (
                  <div className="space-y-1.5 border-t border-border/70 pt-3">
                    <p className="text-[11px] font-medium text-muted-foreground">
                      Supported capabilities
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {Object.entries(selectedSource.policy.capabilities).map(
                        ([cap, enabled]) => (
                          <span
                            key={cap}
                            className={
                              "rounded-md border px-2 py-0.5 text-[10px] font-medium " +
                              (enabled
                                ? "border-emerald-500/20 bg-emerald-500/5 text-emerald-700 dark:text-emerald-300"
                                : "border-border bg-muted/40 text-muted-foreground line-through")
                            }
                          >
                            {CAPABILITY_LABELS[cap] || cap}
                          </span>
                        )
                      )}
                    </div>
                  </div>
                )}

                {selectedSource.policy?.restrictions &&
                  selectedSource.policy.restrictions.length > 0 && (
                    <ul className="list-disc pl-4 space-y-1 text-[11px] text-muted-foreground border-t border-border/70 pt-3">
                      {selectedSource.policy.restrictions.map((r) => (
                        <li key={r}>{r}</li>
                      ))}
                    </ul>
                  )}

                {selectedSource.policy?.missing_approval_note && (
                  <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-[11px] text-amber-800 dark:text-amber-200 flex items-start gap-2">
                    <ShieldAlert size={14} className="shrink-0 mt-0.5" aria-hidden="true" />
                    <div>
                      <p className="font-semibold">External approval required for AI processing</p>
                      <p className="mt-0.5 leading-relaxed">
                        {selectedSource.policy.missing_approval_note}
                      </p>
                    </div>
                  </div>
                )}
              </div>

              {/* GitHub Workspace Connection Controls */}
              {id === "github" && gh && (
                <div className="rounded-xl border border-border bg-muted/20 p-4 space-y-3">
                  <h4 className="font-semibold text-sm text-foreground">GitHub Workspace Connection</h4>
                  <dl className="grid grid-cols-2 gap-2.5 text-xs">
                    <div>
                      <dt className="text-muted-foreground">Public search</dt>
                      <dd className="font-medium text-foreground mt-0.5">
                        {gh.public_search_available ? "Available" : "Disabled"}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-muted-foreground">Customer OAuth</dt>
                      <dd className="font-medium text-foreground mt-0.5">
                        {gh.oauth_configured ? "Configured" : "Unavailable"}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-muted-foreground">Connected account</dt>
                      <dd className="font-medium text-foreground mt-0.5">
                        {gh.account_login ? `${gh.account_login} (${gh.account_type})` : "Not connected"}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-muted-foreground">Webhooks</dt>
                      <dd className="font-medium text-foreground mt-0.5">
                        {gh.webhooks_configured ? "Active (HMAC-SHA256)" : "Pending webhook secret"}
                      </dd>
                    </div>
                  </dl>

                  {access.data?.can_manage && (
                    <div className="flex flex-wrap gap-2 pt-1">
                      {gh.status !== "CONNECTED" ? (
                        <>
                          <Button
                            size="sm"
                            disabled={busyAction !== null || !gh.oauth_configured}
                            onClick={() => void connectGitHub("oauth")}
                          >
                            {busyAction === "gh-oauth" ? "Connecting…" : "Connect GitHub Account"}
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={busyAction !== null || !gh.oauth_configured}
                            onClick={() => void connectGitHub("install")}
                          >
                            Install GitHub App
                          </Button>
                        </>
                      ) : (
                        <>
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={busyAction !== null}
                            onClick={() => void connectGitHub("install")}
                          >
                            Manage Installation
                          </Button>
                          <Button
                            size="sm"
                            variant="destructive"
                            disabled={busyAction !== null}
                            onClick={() => void disconnectGitHub()}
                          >
                            {busyAction === "gh-disconnect" ? "Disconnecting…" : "Disconnect"}
                          </Button>
                        </>
                      )}
                    </div>
                  )}

                  {gh.status === "CONNECTED" && gh.repositories.length > 0 && (
                    <div className="space-y-2 border-t border-border/70 pt-3">
                      <p className="font-medium text-foreground">
                        Authorized repositories ({selectedRepoIds.length} of {gh.repositories.length} selected)
                      </p>
                      <div className="max-h-48 overflow-y-auto space-y-1.5 pr-1">
                        {gh.repositories.map((repo) => (
                          <label
                            key={repo.id}
                            className="flex items-center justify-between gap-2 rounded-lg border border-border/70 bg-card px-3 py-2 cursor-pointer"
                          >
                            <span className="flex items-center gap-2 min-w-0">
                              <input
                                type="checkbox"
                                disabled={!access.data?.can_manage}
                                checked={selectedRepoIds.includes(repo.id)}
                                onChange={(e) => {
                                  const next = e.target.checked
                                    ? [...selectedRepoIds, repo.id]
                                    : selectedRepoIds.filter((rid) => rid !== repo.id);
                                  setRepoSelection(next);
                                }}
                                className="accent-primary"
                              />
                              <span className="truncate font-mono text-[11px]">{repo.full_name}</span>
                            </span>
                            {repo.private && (
                              <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                                Private
                              </span>
                            )}
                          </label>
                        ))}
                      </div>
                      {access.data?.can_manage && repoSelection && (
                        <Button
                          size="sm"
                          disabled={busyAction !== null}
                          onClick={() => void saveRepos()}
                        >
                          {busyAction === "gh-repos" ? "Saving…" : "Save repository selection"}
                        </Button>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Bluesky Jetstream Controls */}
              {id === "bluesky" && selectedHealth?.stream_health && (
                <div className="rounded-xl border border-border bg-muted/20 p-4 space-y-2.5">
                  <div className="flex items-center justify-between gap-2">
                    <h4 className="font-semibold text-sm text-foreground flex items-center gap-1.5">
                      <Radio size={14} className="text-primary" /> Bluesky Jetstream v2
                    </h4>
                    <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[11px] font-semibold text-primary">
                      {selectedHealth.stream_health.state}
                    </span>
                  </div>
                  <p className="text-muted-foreground">
                    Cursor sequence: <strong>{selectedHealth.stream_health.sequence}</strong> · Last poll:{" "}
                    {formatRelativeOrTime(selectedHealth.stream_health.updated_at)}
                  </p>
                  {access.data?.can_manage && selectedHealth.stream_health.enabled && (
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={busyAction !== null}
                      onClick={() => void pollJetstream()}
                      className="gap-1.5"
                    >
                      <RefreshCw size={13} className={busyAction === "bsky-poll" ? "animate-spin" : ""} />
                      {busyAction === "bsky-poll" ? "Polling stream…" : "Poll Jetstream now"}
                    </Button>
                  )}
                </div>
              )}

              {/* Stack Exchange Configured Communities */}
              {id === "stack_exchange" && selectedSource.configured_sites && (
                <div className="rounded-xl border border-border bg-muted/20 p-4 space-y-2">
                  <h4 className="font-semibold text-sm text-foreground">
                    Configured Stack Exchange Communities ({selectedSource.configured_sites.length})
                  </h4>
                  <div className="flex flex-wrap gap-1.5">
                    {selectedSource.configured_sites.map((site) => (
                      <span
                        key={site}
                        className="rounded-md border border-border bg-card px-2 py-0.5 text-[11px] font-mono text-foreground"
                      >
                        {site}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Feed Family Summary & Quick Jump */}
              {isFeedFamily && (
                <div className="rounded-xl border border-border bg-muted/20 p-4 space-y-2.5">
                  <div className="flex items-center justify-between gap-2">
                    <h4 className="font-semibold text-sm text-foreground">Configured Feeds</h4>
                    <span className="text-[11px] font-medium text-muted-foreground">
                      {familyFeeds.filter((f) => f.enabled).length} enabled / {familyFeeds.length} configured
                    </span>
                  </div>
                  <p className="text-muted-foreground leading-relaxed">
                    {id === "rss" && familyFeeds.length === 0
                      ? "No custom RSS feeds are currently configured. All 20 curated Atom & Discourse presets are managed in the Custom Feeds tab."
                      : "Manage individual feed polling intervals, live endpoint checks, and enable/disable state in Custom Feeds."}
                  </p>
                  {onOpenFeedsTab && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        setSelectedSourceId(null);
                        onOpenFeedsTab();
                      }}
                      className="gap-1.5"
                    >
                      <Rss size={13} /> Open Custom Feeds
                    </Button>
                  )}
                </div>
              )}

              {/* Collapsible Advanced Telemetry Details */}
              <div className="rounded-xl border border-border overflow-hidden">
                <button
                  type="button"
                  aria-expanded={showAdvanced}
                  onClick={() => setShowAdvanced((v) => !v)}
                  className="flex w-full items-center justify-between px-4 py-3 text-left font-medium text-foreground hover:bg-muted/30 cursor-pointer"
                >
                  <span>Advanced operational telemetry</span>
                  {showAdvanced ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
                </button>
                {showAdvanced && (
                  <dl className="grid grid-cols-2 gap-3 border-t border-border p-4 text-xs">
                    <div>
                      <dt className="text-muted-foreground">Last successful sync</dt>
                      <dd className="font-medium text-foreground mt-0.5">
                        {formatRelativeOrTime(selectedHealth?.last_success)}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-muted-foreground">Adapter state</dt>
                      <dd className="font-medium text-foreground mt-0.5">
                        {selectedHealth?.state || "Unchecked"}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-muted-foreground">Daily requests reserved</dt>
                      <dd className="font-medium text-foreground mt-0.5 tabular-nums">
                        {selectedHealth?.daily_requests_reserved ?? 0} /{" "}
                        {selectedHealth?.daily_reservation_limit ?? "—"}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-muted-foreground">Consecutive failures</dt>
                      <dd className="font-medium text-foreground mt-0.5 tabular-nums">
                        {selectedHealth?.consecutive_failures ?? 0}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-muted-foreground">Per-check request cap</dt>
                      <dd className="font-medium text-foreground mt-0.5 tabular-nums">
                        {selectedSource.request_limit_per_check ?? 22} requests
                      </dd>
                    </div>
                  </dl>
                )}
              </div>

              {selectedSource.documentation?.startsWith("https://") && (
                <a
                  href={selectedSource.documentation}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-xs font-medium text-primary hover:underline"
                >
                  <CheckCircle2 size={13} /> Official provider documentation <ExternalLink size={12} />
                </a>
              )}
            </div>
          );
        })()}
      </SlideOverDrawer>
    </div>
  );
}
