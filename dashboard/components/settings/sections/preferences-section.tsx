"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  Bell,
  CheckCircle2,
  Database,
  ExternalLink,
  Gauge,
  Info,
  LayoutGrid,
  Search,
  SlidersHorizontal,
  Sparkles,
  Table2,
  X,
} from "lucide-react";
import {
  useRadarCapabilities,
  useRadarMutation,
  useRadarRead,
} from "@/components/intent-radar/provider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { NotificationPreferencesPanel } from "@/components/notifications/NotificationPreferencesPanel";
import type { IntentPreferences } from "@/lib/intent-radar";

interface IcpOption {
  id: string;
  name: string;
  status: string;
}

const SUGGESTED_TOPICS = [
  "saas",
  "developer-tools",
  "webhooks",
  "api",
  "crm",
  "automation",
  "analytics",
  "ai-agents",
  "billing",
  "security",
];

function Hint({ text }: { text: string }) {
  return (
    <span
      title={text}
      aria-label={text}
      className="inline-flex cursor-help items-center text-muted-foreground hover:text-foreground"
    >
      <Info size={12} />
    </span>
  );
}

function TagInput({
  id,
  tags,
  placeholder,
  suggestions,
  disabled,
  maxItems = 12,
  onChange,
}: {
  id: string;
  tags: string[];
  placeholder: string;
  suggestions?: string[];
  disabled?: boolean;
  maxItems?: number;
  onChange: (next: string[]) => void;
}) {
  const [input, setInput] = useState("");
  const [focused, setFocused] = useState(false);

  const filteredSuggestions = useMemo(() => {
    if (!suggestions) return [];
    const q = input.trim().toLowerCase();
    return suggestions
      .filter((s) => !tags.includes(s) && (!q || s.toLowerCase().includes(q)))
      .slice(0, 6);
  }, [suggestions, tags, input]);

  function addTag(raw: string) {
    const clean = raw.trim().replace(/,+/g, "");
    if (!clean || tags.includes(clean) || tags.length >= maxItems) {
      setInput("");
      return;
    }
    onChange([...tags, clean]);
    setInput("");
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-1.5 rounded-lg border border-border bg-background px-2.5 py-1.5 focus-within:ring-1 focus-within:ring-primary">
        {tags.map((tag) => (
          <span
            key={tag}
            className="inline-flex items-center gap-1 rounded-md bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary"
          >
            <span>{tag}</span>
            {!disabled && (
              <button
                type="button"
                aria-label={`Remove ${tag}`}
                onClick={() => onChange(tags.filter((t) => t !== tag))}
                className="rounded hover:bg-primary/20 p-0.5 cursor-pointer"
              >
                <X size={11} />
              </button>
            )}
          </span>
        ))}
        <input
          id={id}
          type="text"
          value={input}
          disabled={disabled || tags.length >= maxItems}
          placeholder={tags.length >= maxItems ? `Max ${maxItems} items` : placeholder}
          onFocus={() => setFocused(true)}
          onBlur={() => {
            if (input.trim()) addTag(input);
            setTimeout(() => setFocused(false), 120);
          }}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === ",") {
              e.preventDefault();
              addTag(input);
            } else if (e.key === "Backspace" && !input && tags.length > 0) {
              onChange(tags.slice(0, -1));
            }
          }}
          className="min-w-[140px] flex-1 bg-transparent py-0.5 text-xs text-foreground outline-none placeholder:text-muted-foreground"
        />
      </div>
      {focused && filteredSuggestions.length > 0 && !disabled && (
        <div className="flex flex-wrap items-center gap-1">
          <span className="text-[11px] text-muted-foreground mr-1">Suggestions:</span>
          {filteredSuggestions.map((s) => (
            <button
              key={s}
              type="button"
              onMouseDown={(e) => {
                e.preventDefault();
                addTag(s);
              }}
              className="rounded-md border border-border bg-muted/40 px-2 py-0.5 text-[11px] text-foreground hover:border-primary/40 hover:bg-primary/5 cursor-pointer"
            >
              + {s}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function PreferencesForm({
  initial,
  canManage,
  activeTab,
  onSaved,
}: {
  initial: IntentPreferences;
  canManage: boolean;
  activeTab: string;
  onSaved: (next: IntentPreferences) => void;
}) {
  const icpsQuery = useRadarRead<{ items: IcpOption[] }>("/icps?page_size=100");
  const save = useRadarMutation();

  const [edit, setEdit] = useState<IntentPreferences>(initial);
  const [icpSearch, setIcpSearch] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    setEdit(initial);
  }, [initial]);

  const activeIcps = useMemo(
    () => (icpsQuery.data?.items || []).filter((i) => i.status !== "DELETED"),
    [icpsQuery.data]
  );

  const filteredIcps = useMemo(() => {
    const q = icpSearch.trim().toLowerCase();
    if (!q) return activeIcps;
    return activeIcps.filter((i) => i.name.toLowerCase().includes(q));
  }, [activeIcps, icpSearch]);

  const limitsMeta = initial.limits_meta;
  const maxDailyCalls = limitsMeta?.platform_daily_call_limit ?? 10;
  const maxDailyTokens = limitsMeta?.platform_daily_token_limit ?? 60000;

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setNotice("");
    setError("");
    const safeCalls = Math.max(1, Math.min(maxDailyCalls, Number(edit.analysis_daily_call_limit ?? 3)));
    const safeTokens = Math.max(6000, Math.min(maxDailyTokens, Number(edit.analysis_daily_token_limit ?? 60000)));
    const safeRetention = Math.max(1, Math.min(365, Number(edit.source_retention_days ?? 30)));

    const payload = {
      source_retention_days: safeRetention,
      default_view: edit.default_view || "table",
      min_relevance: Math.max(0, Math.min(100, Number(edit.min_relevance ?? 0))),
      default_icp_id: edit.default_icp_id || null,
      ai_assistance: edit.ai_assistance ?? true,
      analysis_daily_call_limit: safeCalls,
      analysis_daily_token_limit: safeTokens,
      topics: edit.topics || [],
      discovery_keywords: edit.discovery_keywords || [],
      discovery_excluded: edit.discovery_excluded || [],
      alerts_enabled: edit.alerts_enabled ?? true,
      alert_threshold: Math.max(0, Math.min(100, Number(edit.alert_threshold ?? 85))),
      revision: initial.revision,
    };

    try {
      const updated = (await save.mutateAsync({
        path: "/settings",
        method: "PUT",
        body: payload,
      })) as IntentPreferences;
      onSaved(updated);
      setNotice("Workspace research preferences saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save preferences.");
    }
  }

  return (
    <form onSubmit={(e) => void handleSave(e)} className="space-y-4">
      {notice && (
        <div role="status" className="flex items-center gap-2 rounded-xl border border-emerald-500/25 bg-emerald-500/10 px-3.5 py-2.5 text-xs font-medium text-emerald-700 dark:text-emerald-300">
          <CheckCircle2 size={14} className="shrink-0" />
          <span>{notice}</span>
        </div>
      )}
      {error && (
        <div role="alert" className="rounded-xl border border-destructive/25 bg-destructive/5 px-3.5 py-2.5 text-xs text-destructive">
          {error}
        </div>
      )}

      {/* TAB 1: DISCOVERY DEFAULTS */}
      {activeTab === "discovery" && (
        <section className="rounded-xl border border-border bg-card p-5 space-y-5">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/70 pb-3.5">
            <div className="flex items-center gap-2">
              <SlidersHorizontal size={15} className="text-primary" />
              <h3 className="text-sm font-semibold text-foreground">Discovery Defaults</h3>
              <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
                Workspace
              </span>
            </div>
            <span className="text-[11px] text-muted-foreground">
              Applied to new discoveries &amp; monitors · existing snapshots stay unchanged
            </span>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            {/* Default Signal View */}
            <div className="space-y-1.5">
              <div className="flex items-center gap-1.5">
                <span className="text-xs font-medium text-foreground">Default signal view</span>
                <Hint text="Initial layout used when opening Intent Signals." />
              </div>
              <div className="inline-flex rounded-lg border border-border bg-muted/30 p-0.5">
                {[
                  { id: "table", label: "Table", icon: Table2 },
                  { id: "cards", label: "Cards", icon: LayoutGrid },
                ].map(({ id, label, icon: Icon }) => {
                  const active = edit.default_view === id;
                  return (
                    <button
                      key={id}
                      type="button"
                      disabled={!canManage}
                      onClick={() => setEdit({ ...edit, default_view: id as "table" | "cards" })}
                      className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors cursor-pointer ${
                        active
                          ? "bg-card text-foreground shadow-sm"
                          : "text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      <Icon size={13} />
                      {label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* AI-Assisted Discovery */}
            <div className="flex items-center justify-between rounded-lg border border-border/70 bg-muted/15 px-3.5 py-2.5">
              <div className="space-y-0.5 pr-3">
                <div className="flex items-center gap-1.5">
                  <Sparkles size={13} className="text-primary" />
                  <span className="text-xs font-semibold text-foreground">AI-assisted discovery</span>
                  <Hint text="Uses authorized workspace AI to expand queries and summarize evidence when enabled." />
                </div>
                <p className="text-[11px] text-muted-foreground">
                  {edit.ai_assistance !== false ? "Enabled for new runs" : "Disabled (keyword search only)"}
                </p>
              </div>
              <button
                type="button"
                role="switch"
                aria-checked={edit.ai_assistance !== false}
                aria-label="Enable AI-assisted discovery"
                disabled={!canManage}
                onClick={() => setEdit({ ...edit, ai_assistance: !(edit.ai_assistance !== false) })}
                className={`relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors cursor-pointer disabled:opacity-50 ${
                  edit.ai_assistance !== false ? "bg-primary" : "bg-muted-foreground/30"
                }`}
              >
                <span
                  className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform ${
                    edit.ai_assistance !== false ? "translate-x-4.5" : "translate-x-0.5"
                  }`}
                />
              </button>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            {/* Minimum Relevance Slider */}
            <div className="space-y-2 rounded-lg border border-border/70 bg-muted/10 p-3.5">
              <div className="flex items-center justify-between">
                <label htmlFor="pref-min-rel" className="flex items-center gap-1.5 text-xs font-medium text-foreground">
                  Minimum relevance threshold
                  <Hint text="Signals scoring below this threshold are filtered out of default discovery views." />
                </label>
                <span className="rounded-md bg-primary/10 px-2 py-0.5 text-xs font-bold tabular-nums text-primary">
                  {edit.min_relevance}%
                </span>
              </div>
              <input
                id="pref-min-rel"
                type="range"
                min={0}
                max={100}
                step={5}
                disabled={!canManage}
                value={edit.min_relevance}
                onChange={(e) => setEdit({ ...edit, min_relevance: Number(e.target.value) })}
                className="w-full accent-primary cursor-pointer"
              />
              <div className="flex justify-between text-[10px] text-muted-foreground tabular-nums">
                <span>0% (All)</span>
                <span>50%</span>
                <span>100% (Strict)</span>
              </div>
            </div>

            {/* Searchable Default ICP Selector */}
            <div className="space-y-1.5 rounded-lg border border-border/70 bg-muted/10 p-3.5">
              <div className="flex items-center justify-between">
                <label htmlFor="pref-default-icp" className="flex items-center gap-1.5 text-xs font-medium text-foreground">
                  Default Ideal Customer Profile
                  <Hint text="Pre-selected ICP for new discoveries, monitors, and signal scoring." />
                </label>
                <Link href="/intent-radar/ideal-customers" className="text-[11px] font-medium text-primary hover:underline">
                  Manage ICPs
                </Link>
              </div>
              {activeIcps.length > 5 && (
                <div className="relative">
                  <Search size={12} className="absolute left-2.5 top-2 text-muted-foreground" />
                  <input
                    type="text"
                    value={icpSearch}
                    onChange={(e) => setIcpSearch(e.target.value)}
                    placeholder="Filter saved ICPs…"
                    className="h-7 w-full rounded-md border border-border bg-background pl-7 pr-2 text-xs"
                  />
                </div>
              )}
              <select
                id="pref-default-icp"
                disabled={!canManage}
                value={edit.default_icp_id || ""}
                onChange={(e) => setEdit({ ...edit, default_icp_id: e.target.value || null })}
                className="h-8 w-full rounded-lg border border-border bg-background px-2.5 text-xs text-foreground"
              >
                <option value="">No default ICP selected</option>
                {filteredIcps.map((icp) => (
                  <option key={icp.id} value={icp.id}>
                    {icp.name} ({icp.status})
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Preferred Research Topics Tag Input */}
          <div className="space-y-1.5">
            <label htmlFor="pref-topics" className="flex items-center gap-1.5 text-xs font-medium text-foreground">
              Preferred research topics
              <Hint text="Press Enter or comma to add up to 12 topics used to seed new discoveries and monitors." />
            </label>
            <TagInput
              id="pref-topics"
              tags={edit.topics || []}
              placeholder="Type a topic and press Enter…"
              suggestions={SUGGESTED_TOPICS}
              disabled={!canManage}
              onChange={(topics) => setEdit({ ...edit, topics })}
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <label htmlFor="pref-keywords" className="flex items-center gap-1.5 text-xs font-medium text-foreground">
                Default keywords
                <Hint text="Optional default search keywords pre-filled in Advanced Search." />
              </label>
              <TagInput
                id="pref-keywords"
                tags={edit.discovery_keywords || []}
                placeholder="Add keyword…"
                disabled={!canManage}
                onChange={(discovery_keywords) => setEdit({ ...edit, discovery_keywords })}
              />
            </div>

            <div className="space-y-1.5">
              <label htmlFor="pref-excluded" className="flex items-center gap-1.5 text-xs font-medium text-foreground">
                Default exclusions
                <Hint text="Terms automatically excluded from new discoveries." />
              </label>
              <TagInput
                id="pref-excluded"
                tags={edit.discovery_excluded || []}
                placeholder="Add excluded term…"
                disabled={!canManage}
                onChange={(discovery_excluded) => setEdit({ ...edit, discovery_excluded })}
              />
            </div>
          </div>

          {canManage && (
            <div className="flex justify-end border-t border-border/70 pt-3.5">
              <Button type="submit" size="sm" disabled={save.isPending} className="h-8 text-xs">
                {save.isPending ? "Saving…" : "Save Discovery Defaults"}
              </Button>
            </div>
          )}
        </section>
      )}

      {/* TAB 2: NOTIFICATIONS & ALERTS */}
      {activeTab === "notifications" && (
        <div className="space-y-4">
          <NotificationPreferencesPanel />

          {/* Section 3: Alert Sensitivity (Workspace-wide) */}
          <section className="rounded-xl border border-border bg-card p-4 space-y-3.5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <Bell size={15} className="text-primary" />
                <h3 className="text-sm font-semibold text-foreground">Alert Sensitivity</h3>
                <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary">
                  Workspace-wide
                </span>
              </div>
              <button
                type="button"
                role="switch"
                aria-checked={edit.alerts_enabled}
                aria-label="Enable workspace signal alerts"
                disabled={!canManage}
                onClick={() => setEdit({ ...edit, alerts_enabled: !edit.alerts_enabled })}
                className={`relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors cursor-pointer disabled:opacity-50 ${
                  edit.alerts_enabled ? "bg-primary" : "bg-muted-foreground/30"
                }`}
              >
                <span
                  className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform ${
                    edit.alerts_enabled ? "translate-x-4.5" : "translate-x-0.5"
                  }`}
                />
              </button>
            </div>

            <div className="grid gap-3 sm:grid-cols-2 items-center">
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label htmlFor="pref-alert-threshold" className="text-xs font-medium text-foreground">
                    High-relevance alert threshold
                  </label>
                  <span className="rounded-md bg-primary/10 px-2 py-0.5 text-xs font-bold tabular-nums text-primary">
                    {edit.alert_threshold}%
                  </span>
                </div>
                <input
                  id="pref-alert-threshold"
                  type="range"
                  min={0}
                  max={100}
                  step={5}
                  disabled={!canManage || !edit.alerts_enabled}
                  value={edit.alert_threshold}
                  onChange={(e) => setEdit({ ...edit, alert_threshold: Number(e.target.value) })}
                  className="w-full accent-primary cursor-pointer"
                />
              </div>
              <p className="text-[11px] text-muted-foreground leading-relaxed">
                Signals scoring at or above <strong>{edit.alert_threshold}%</strong> generate priority high-intent alerts across this workspace.
              </p>
            </div>

            {canManage && (
              <div className="flex justify-end border-t border-border/70 pt-3">
                <Button type="submit" size="sm" disabled={save.isPending} className="h-8 text-xs">
                  {save.isPending ? "Saving…" : "Save Alert Sensitivity"}
                </Button>
              </div>
            )}
          </section>
        </div>
      )}

      {/* TAB 3: DATA RETENTION */}
      {activeTab === "retention" && (
        <section className="rounded-xl border border-border bg-card p-5 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/70 pb-3.5">
            <div className="flex items-center gap-2">
              <Database size={15} className="text-primary" />
              <h3 className="text-sm font-semibold text-foreground">Data Retention</h3>
              <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
                Workspace
              </span>
            </div>
            <Link
              href="/sources-policy"
              className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
            >
              Retention documentation <ExternalLink size={12} />
            </Link>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 items-start">
            <div className="space-y-1.5">
              <label htmlFor="pref-retention-days" className="flex items-center gap-1.5 text-xs font-medium text-foreground">
                Evidence retention period (days)
                <Hint text="Public source excerpts older than this window are automatically purged by retention workers; your own notes remain preserved." />
              </label>
              <div className="flex items-center gap-2">
                <Input
                  id="pref-retention-days"
                  type="number"
                  min={1}
                  max={365}
                  disabled={!canManage}
                  value={edit.source_retention_days ?? 30}
                  onChange={(e) =>
                    setEdit({
                      ...edit,
                      source_retention_days: Math.max(1, Math.min(365, Number(e.target.value) || 30)),
                    })
                  }
                  className="w-28 h-8 text-xs tabular-nums"
                />
                <div className="flex flex-wrap gap-1">
                  {[7, 14, 30, 90, 180].map((days) => (
                    <button
                      key={days}
                      type="button"
                      disabled={!canManage}
                      onClick={() => setEdit({ ...edit, source_retention_days: days })}
                      className={`rounded-md border px-2 py-1 text-[11px] font-medium cursor-pointer transition-colors ${
                        (edit.source_retention_days ?? 30) === days
                          ? "border-primary bg-primary/10 text-primary"
                          : "border-border bg-muted/20 text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      {days}d
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="rounded-lg border border-border/70 bg-muted/15 p-3.5 space-y-1.5 text-xs text-muted-foreground">
              <p className="font-medium text-foreground">Policy summary</p>
              <p className="leading-relaxed">
                Expired source excerpts are redacted automatically by background retention workers while keeping your workspace notes, opportunities, and audit records intact.
              </p>
              {(edit.source_retention_days ?? 30) > 30 && (
                <p className="text-[11px] text-amber-700 dark:text-amber-300 pt-1">
                  Publisher-specific ceilings (such as shorter feed or YouTube API windows) still take precedence where stricter than {edit.source_retention_days} days.
                </p>
              )}
            </div>
          </div>

          {canManage && (
            <div className="flex justify-end border-t border-border/70 pt-3.5">
              <Button type="submit" size="sm" disabled={save.isPending} className="h-8 text-xs">
                {save.isPending ? "Saving…" : "Save Changes"}
              </Button>
            </div>
          )}
        </section>
      )}

      {/* TAB 4: CAPACITY & LIMITS */}
      {activeTab === "limits" && (
        <section className="rounded-xl border border-border bg-card p-5 space-y-5">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/70 pb-3.5">
            <div className="flex items-center gap-2">
              <Gauge size={15} className="text-primary" />
              <h3 className="text-sm font-semibold text-foreground">Capacity &amp; Limits</h3>
            </div>
            <span className="text-[11px] text-muted-foreground">
              Daily caps reset at 00:00 UTC · cannot exceed plan or platform ceilings
            </span>
          </div>

          {/* Live Daily Usage vs Effective Limit */}
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-lg border border-border/70 bg-muted/15 p-3 space-y-1">
              <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                <span>AI analyses today</span>
                <span className="rounded bg-muted px-1.5 py-0.5 text-[10px]">Daily cap</span>
              </div>
              <p className="text-sm font-bold tabular-nums text-foreground">
                {(limitsMeta?.calls_used_today ?? 0).toLocaleString()} /{" "}
                <span className="text-xs font-normal text-muted-foreground">
                  {(limitsMeta?.effective_daily_call_limit ?? edit.analysis_daily_call_limit ?? 3).toLocaleString()}
                </span>
              </p>
              <p className="text-[11px] text-muted-foreground">
                Ceiling: {maxDailyCalls}/day
              </p>
            </div>

            <div className="rounded-lg border border-border/70 bg-muted/15 p-3 space-y-1">
              <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                <span>AI tokens reserved today</span>
                <span className="rounded bg-muted px-1.5 py-0.5 text-[10px]">Daily cap</span>
              </div>
              <p className="text-sm font-bold tabular-nums text-foreground">
                {(limitsMeta?.tokens_used_today ?? 0).toLocaleString()} /{" "}
                <span className="text-xs font-normal text-muted-foreground">
                  {(limitsMeta?.effective_daily_token_limit ?? Math.min(maxDailyTokens, edit.analysis_daily_token_limit ?? 60000)).toLocaleString()}
                </span>
              </p>
              <p className="text-[11px] text-muted-foreground">
                Ceiling: {maxDailyTokens.toLocaleString()} tokens/day
              </p>
            </div>

            <div className="rounded-lg border border-border/70 bg-muted/15 p-3 space-y-1">
              <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                <span>Plan AI operations</span>
                <span className="rounded bg-primary/10 px-1.5 py-0.5 text-[10px] font-medium text-primary">
                  Plan-imposed
                </span>
              </div>
              <p className="text-sm font-bold tabular-nums text-foreground">
                {limitsMeta?.plan_monthly_ai_calls_limit != null
                  ? `${(limitsMeta.plan_monthly_ai_calls_used ?? 0).toLocaleString()} / ${limitsMeta.plan_monthly_ai_calls_limit.toLocaleString()}`
                  : "See Billing & Usage"}
              </p>
              <Link href="/settings?category=billing&tab=overview" className="text-[11px] font-medium text-primary hover:underline">
                View plan allowances
              </Link>
            </div>
          </div>

          {/* Configurable Daily Safety Caps */}
          <div className="grid gap-4 sm:grid-cols-2 border-t border-border/60 pt-4">
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label htmlFor="pref-daily-calls" className="text-xs font-medium text-foreground">
                  Daily AI analysis limit
                </label>
                <span className="rounded bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-medium text-emerald-700 dark:text-emerald-300">
                  Configurable (1–{maxDailyCalls})
                </span>
              </div>
              <Input
                id="pref-daily-calls"
                type="number"
                min={1}
                max={maxDailyCalls}
                disabled={!canManage}
                value={Math.min(maxDailyCalls, edit.analysis_daily_call_limit ?? 3)}
                onChange={(e) => {
                  const val = Math.max(1, Math.min(maxDailyCalls, Number(e.target.value) || 1));
                  setEdit({ ...edit, analysis_daily_call_limit: val });
                }}
                className="h-8 text-xs tabular-nums"
              />
              <p className="text-[11px] text-muted-foreground">
                Bounds daily AI analysis runs for this workspace without exceeding your plan&apos;s monthly allowance.
              </p>
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label htmlFor="pref-daily-tokens" className="text-xs font-medium text-foreground">
                  Daily AI token safety cap
                </label>
                <span className="rounded bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-medium text-emerald-700 dark:text-emerald-300">
                  Configurable (6k–{Math.round(maxDailyTokens / 1000)}k)
                </span>
              </div>
              <Input
                id="pref-daily-tokens"
                type="number"
                min={6000}
                max={maxDailyTokens}
                step={2000}
                disabled={!canManage}
                value={Math.min(maxDailyTokens, edit.analysis_daily_token_limit ?? maxDailyTokens)}
                onChange={(e) => {
                  const val = Math.max(6000, Math.min(maxDailyTokens, Number(e.target.value) || 6000));
                  setEdit({ ...edit, analysis_daily_token_limit: val });
                }}
                className="h-8 text-xs tabular-nums"
              />
              <p className="text-[11px] text-muted-foreground">
                Maximum reserved AI tokens per UTC day (platform safety ceiling: {maxDailyTokens.toLocaleString()}).
              </p>
            </div>
          </div>

          {canManage && (
            <div className="flex justify-end border-t border-border/70 pt-3.5">
              <Button type="submit" size="sm" disabled={save.isPending} className="h-8 text-xs">
                {save.isPending ? "Saving…" : "Save Limits"}
              </Button>
            </div>
          )}
        </section>
      )}
    </form>
  );
}

export function PreferencesSection({ activeTab }: { activeTab: string }) {
  const capabilities = useRadarCapabilities();
  const prefsQuery = useRadarRead<IntentPreferences>("/settings");

  if (activeTab === "notifications" && prefsQuery.isError) {
    // Allow personal notification preferences even if Intent Radar isn't active yet
    return <NotificationPreferencesPanel />;
  }

  if (prefsQuery.isPending) {
    return (
      <div className="space-y-3" role="status" aria-label="Loading research preferences">
        <div className="h-48 rounded-xl border border-border bg-muted/30 animate-pulse" />
      </div>
    );
  }

  if (prefsQuery.isError || !prefsQuery.data) {
    return (
      <div role="alert" className="rounded-xl border border-border bg-card p-5 space-y-3 text-xs">
        <p className="font-semibold text-foreground">Research preferences require active Intent Radar access</p>
        <p className="text-muted-foreground">
          {prefsQuery.error?.message || "Activate your workspace plan or complete onboarding to configure discovery defaults."}
        </p>
        <Button size="sm" variant="outline" onClick={() => void prefsQuery.refetch()}>
          Retry
        </Button>
      </div>
    );
  }

  const canManage = Boolean(capabilities.data?.can_manage);

  return (
    <PreferencesForm
      initial={prefsQuery.data}
      canManage={canManage}
      activeTab={activeTab}
      onSaved={() => void prefsQuery.refetch()}
    />
  );
}
