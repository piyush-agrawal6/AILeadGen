"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { SlidersHorizontal, Bell, ShieldCheck, Cpu, Check, AlertCircle, Save } from "lucide-react";
import type { IntentPreferences } from "@/lib/intent-radar";
import { useRadarRead, useRadarMutation, useRadarCapabilities } from "@/components/intent-radar/provider";
import { ChipInput } from "@/components/intent-radar/monitors";
import { NotificationPreferencesPanel } from "@/components/notifications/NotificationPreferencesPanel";
import { Button } from "@/components/ui/button";

export function PreferencesSection({ activeTab }: { activeTab: string }) {
  const query = useRadarRead<IntentPreferences>("/settings");

  if (query.isPending) {
    return <p role="status" className="text-sm text-muted-foreground">Loading workspace preferences…</p>;
  }

  if (query.error || !query.data) {
    return (
      <div role="alert" className="rounded-xl border border-destructive/20 bg-destructive/5 p-4 text-sm text-destructive">
        <p>Preferences could not be loaded: {query.error?.message || "Unknown error"}</p>
        <Button variant="outline" size="sm" className="mt-3" onClick={() => void query.refetch()}>
          Retry
        </Button>
      </div>
    );
  }

  return <PreferencesForm initial={query.data} activeTab={activeTab} />;
}

function PreferencesForm({ initial, activeTab }: { initial: IntentPreferences; activeTab: string }) {
  const [edit, setEdit] = useState(initial);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");
  const mutation = useRadarMutation();
  const access = useRadarCapabilities();
  const icps = useRadarRead<{ items: { id: string; name: string }[] }>("/icps");

  const dirty = JSON.stringify(edit) !== JSON.stringify(initial);
  const disabled = mutation.isPending || !access.data?.can_manage;

  const set = (patch: Partial<IntentPreferences>) => {
    setEdit((v) => ({ ...v, ...patch }));
    setSaved(false);
  };

  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  async function handleSave() {
    setError("");
    try {
      const result = (await mutation.mutateAsync({
        path: "/settings",
        method: "PUT",
        body: edit,
      })) as IntentPreferences;
      setEdit(result);
      setSaved(true);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b pb-4">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">Research Preferences</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Configure signal discovery parameters, alert triggers, data retention, and daily safety caps.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {saved && (
            <span className="flex items-center gap-1.5 text-xs font-medium text-emerald-600 dark:text-emerald-400">
              <Check size={14} /> Saved
            </span>
          )}
          {dirty && (
            <span className="rounded-full bg-amber-500/10 px-2.5 py-0.5 text-xs font-medium text-amber-700 dark:text-amber-400 border border-amber-500/20">
              Unsaved changes
            </span>
          )}
          <Button
            size="sm"
            disabled={disabled || !dirty}
            onClick={() => void handleSave()}
            className="gap-2"
          >
            <Save size={14} />
            {mutation.isPending ? "Saving…" : "Save preferences"}
          </Button>
        </div>
      </div>

      {error && (
        <div role="alert" className="flex items-center gap-2 rounded-lg border border-destructive/20 bg-destructive/5 p-3 text-sm text-destructive">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* Discovery Tab */}
      {activeTab === "discovery" && (
        <div className="space-y-6">
          <div className="rounded-xl border bg-card p-6 space-y-5">
            <h3 className="text-base font-semibold">Signal Discovery Defaults</h3>

            <div className="space-y-2">
              <label htmlFor="pref-view" className="text-sm font-medium">Default Signal View</label>
              <select
                id="pref-view"
                className="control w-full sm:max-w-md"
                disabled={disabled}
                value={edit.default_view}
                onChange={(e) => set({ default_view: e.target.value as IntentPreferences["default_view"] })}
              >
                <option value="table">Table — dense and fast for team review</option>
                <option value="cards">Cards — detailed preview with conversational context</option>
              </select>
              <p className="text-xs text-muted-foreground">Sets the default display mode on Intent Radar and search results.</p>
            </div>

            <div className="space-y-2">
              <ChipInput
                label="Preferred Research Topics"
                value={edit.topics}
                onChange={(topics) => set({ topics })}
              />
              <p className="text-xs text-muted-foreground">Topics highlight high-priority keywords across public discussion feeds.</p>
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <label htmlFor="pref-relevance" className="text-sm font-medium">
                  Default Minimum Relevance Threshold
                </label>
                <span className="rounded-md bg-muted px-2 py-0.5 text-xs font-semibold tabular-nums">
                  {edit.min_relevance} / 100
                </span>
              </div>
              <input
                id="pref-relevance"
                disabled={disabled}
                type="range"
                min={0}
                max={100}
                value={edit.min_relevance}
                onChange={(e) => set({ min_relevance: Number(e.target.value) })}
                className="w-full accent-primary"
              />
              <p className="text-xs text-muted-foreground">
                Signals below this threshold are deprioritized during initial discovery review.
              </p>
            </div>

            <div className="space-y-2">
              <label htmlFor="pref-icp" className="text-sm font-medium">Default Target ICP</label>
              <select
                id="pref-icp"
                className="control w-full sm:max-w-md"
                disabled={disabled}
                value={edit.default_icp_id || ""}
                onChange={(e) => set({ default_icp_id: e.target.value || null })}
              >
                <option value="">No default ICP (manual selection)</option>
                {icps.data?.items?.map((i) => (
                  <option key={i.id} value={i.id}>
                    {i.name}
                  </option>
                ))}
              </select>
              <p className="text-xs text-muted-foreground">Pre-selects an ICP filter when creating monitors or running discovery searches.</p>
            </div>

            <label className="flex items-start gap-3 pt-2 cursor-pointer">
              <input
                disabled={disabled}
                type="checkbox"
                checked={edit.ai_assistance ?? true}
                onChange={(e) => set({ ai_assistance: e.target.checked })}
                className="mt-1 accent-primary"
              />
              <div>
                <span className="text-sm font-medium">Enable AI Assistance in Discovery</span>
                <p className="text-xs text-muted-foreground">
                  Provides automatic intent classification, excerpt summarization, and buying trigger insights when the AI gateway is enabled.
                </p>
              </div>
            </label>
          </div>
        </div>
      )}

      {/* Notifications Tab */}
      {activeTab === "notifications" && (
        <div className="space-y-6">
          <div className="rounded-xl border bg-card p-6 space-y-5">
            <h3 className="text-base font-semibold">In-App Alerts</h3>

            <label className="flex items-start gap-3 cursor-pointer">
              <input
                disabled={disabled}
                type="checkbox"
                checked={edit.alerts_enabled}
                onChange={(e) => set({ alerts_enabled: e.target.checked })}
                className="mt-1 accent-primary"
              />
              <div>
                <span className="text-sm font-medium">In-app notifications for new monitor matches</span>
                <p className="text-xs text-muted-foreground">
                  Generates workspace alert items whenever active background monitors discover relevant conversations.
                </p>
              </div>
            </label>

            <div className="space-y-2">
              <label htmlFor="pref-alert-thresh" className="text-sm font-medium">
                High-Relevance Alert Threshold (0–100)
              </label>
              <input
                id="pref-alert-thresh"
                disabled={disabled}
                type="number"
                min={0}
                max={100}
                className="control w-32"
                value={edit.alert_threshold}
                onChange={(e) => set({ alert_threshold: Math.min(100, Math.max(0, Number(e.target.value))) })}
              />
              <p className="text-xs text-muted-foreground">
                Signals scoring at or above this threshold are flagged with the high-relevance badge in the notification center.
              </p>
            </div>

            <div className="pt-2">
              <Link className="inline-flex text-xs font-medium text-primary hover:underline" href="/notifications">
                Open full Notifications Center →
              </Link>
            </div>
          </div>
          <NotificationPreferencesPanel />
        </div>
      )}

      {/* Retention Tab */}
      {activeTab === "retention" && (
        <div className="space-y-6">
          <div className="rounded-xl border bg-card p-6 space-y-5">
            <h3 className="text-base font-semibold">Evidence Retention & Compliance</h3>

            <div className="space-y-2">
              <label htmlFor="pref-retention" className="text-sm font-medium">
                Public Evidence Retention (Days)
              </label>
              <input
                id="pref-retention"
                disabled={disabled}
                type="number"
                min={1}
                max={365}
                className="control w-32"
                value={edit.source_retention_days ?? 30}
                onChange={(e) => set({ source_retention_days: Number(e.target.value) })}
              />
              <p className="text-xs text-muted-foreground">
                Applies across all monitored sources. Shorter publisher policy limits take precedence automatically.
              </p>
            </div>

            <div className="rounded-lg bg-muted/30 p-4 space-y-2 text-xs text-muted-foreground leading-relaxed">
              <h4 className="font-semibold text-foreground">Workspace Data Privacy Rules</h4>
              <ul className="list-disc pl-4 space-y-1.5">
                <li>Captured evidence includes only permitted public titles, excerpts, source attribution, and timestamps.</li>
                <li>No private communications or private community scraping is ever performed.</li>
                <li>Archiving a monitor keeps historical evidence intact; deleting bookmarks does not destroy underlying signals.</li>
                <li>Expired signals are purged by automated background retention workers. Personal team notes are preserved.</li>
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Limits & Capacity Tab */}
      {activeTab === "limits" && (
        <div className="space-y-6">
          <div className="rounded-xl border bg-card p-6 space-y-5">
            <div>
              <h3 className="text-base font-semibold">Daily Safety Caps</h3>
              <p className="mt-1 text-xs text-muted-foreground">
                These daily guardrails prevent runaway automated requests. They operate independently of monthly subscription allowances.
              </p>
            </div>

            <div className="space-y-2">
              <label htmlFor="pref-daily-calls" className="text-sm font-medium">
                Daily Analysis Call Limit
              </label>
              <input
                id="pref-daily-calls"
                disabled={disabled}
                type="number"
                min={1}
                max={10}
                className="control w-32"
                value={edit.analysis_daily_call_limit ?? 1}
                onChange={(e) => set({ analysis_daily_call_limit: Number(e.target.value) })}
              />
              <p className="text-xs text-muted-foreground">Maximum automated deep analysis runs permitted per day.</p>
            </div>

            <div className="space-y-2">
              <label htmlFor="pref-daily-tokens" className="text-sm font-medium">
                Daily Reserved AI Token Cap
              </label>
              <input
                id="pref-daily-tokens"
                disabled={disabled}
                type="number"
                min={6000}
                max={300000}
                step={1000}
                className="control w-48"
                value={edit.analysis_daily_token_limit ?? 60000}
                onChange={(e) => set({ analysis_daily_token_limit: Number(e.target.value) })}
              />
              <p className="text-xs text-muted-foreground">
                Safety ceiling for model request token allocation per 24-hour cycle.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
