"use client";

import { useMemo, useRef, useState } from "react";
import {
  Check,
  Clock,
  Globe,
  Loader2,
  Plus,
  Rss,
  Search,
  Settings2,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useRadarCapabilities, useRadarMutation, useRadarRead } from "../provider";
import { Modal } from "../ui";
import {
  categorizePreset,
  extractHostname,
  FEED_CATEGORIES,
  type FeedCategoryKey,
  type FeedConfig,
  type FeedFamily,
  type FeedPreset,
} from "./types";

const EMPTY_FORM: FeedConfig = {
  name: "",
  family: "rss",
  endpoint: "",
  policy_reference: "",
  attribution: "",
  retention_days: 7,
  polling_minutes: 60,
  enabled: true,
  ai_processing_authorized: false,
};

function familyLabel(family: FeedFamily): string {
  if (family === "discourse") return "Discourse";
  if (family === "atom") return "Atom";
  return "RSS / Atom";
}

function isMarketIntelligence(contentKind?: string | null, family?: string): boolean {
  return (
    family === "atom" ||
    contentKind === "release_announcement" ||
    contentKind === "research_paper"
  );
}

export function CustomFeedsPanel() {
  const access = useRadarCapabilities();
  const configsQuery = useRadarRead<{ items: FeedConfig[] }>("/sources/configurations");
  const presetsQuery = useRadarRead<{ items: FeedPreset[] }>("/sources/presets");
  const mutation = useRadarMutation();

  const presetSectionRef = useRef<HTMLElement | null>(null);

  // Filters
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<"all" | FeedCategoryKey>("all");
  const [statusFilter, setStatusFilter] = useState<"all" | "enabled" | "disabled">("all");
  const [familyFilter, setFamilyFilter] = useState<"all" | FeedFamily>("all");
  const [permissionFilter, setPermissionFilter] = useState<"all" | "ai_authorized" | "ai_restricted">("all");

  // Per-row pending & feedback states (never disables whole page)
  const [pendingKey, setPendingKey] = useState<string | null>(null);
  const [rowError, setRowError] = useState<{ key: string; message: string } | null>(null);
  const [notice, setNotice] = useState("");

  // Drawer state (for Add custom feed OR Manage existing feed)
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [form, setForm] = useState<FeedConfig>(EMPTY_FORM);
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const [formServerError, setFormServerError] = useState("");
  const [savingForm, setSavingForm] = useState(false);

  const configs = useMemo(() => configsQuery.data?.items || [], [configsQuery.data?.items]);
  const presets = useMemo(() => presetsQuery.data?.items || [], [presetsQuery.data?.items]);
  const canManage = Boolean(access.data?.can_manage);

  const activeFeeds = useMemo(() => configs.filter((c) => c.enabled), [configs]);
  const disabledCustomFeeds = useMemo(() => {
    const presetEndpoints = new Set(presets.map((p) => p.endpoint));
    return configs.filter((c) => !c.enabled && !presetEndpoints.has(c.endpoint));
  }, [configs, presets]);

  const filteredPresets = useMemo(() => {
    const q = search.trim().toLowerCase();
    return presets.filter((p) => {
      if (q && !`${p.name} ${p.endpoint} ${p.attribution} ${p.family}`.toLowerCase().includes(q)) {
        return false;
      }
      if (categoryFilter !== "all" && categorizePreset(p) !== categoryFilter) return false;
      if (statusFilter === "enabled" && !p.enabled) return false;
      if (statusFilter === "disabled" && p.enabled) return false;
      if (familyFilter !== "all" && p.family !== familyFilter) return false;
      if (permissionFilter === "ai_authorized" && !p.ai_processing_authorized) return false;
      if (permissionFilter === "ai_restricted" && p.ai_processing_authorized) return false;
      return true;
    });
  }, [presets, search, categoryFilter, statusFilter, familyFilter, permissionFilter]);

  const groupedPresets = useMemo(() => {
    return FEED_CATEGORIES.map((cat) => ({
      ...cat,
      items: filteredPresets.filter((p) => categorizePreset(p) === cat.key),
    })).filter((group) => group.items.length > 0);
  }, [filteredPresets]);

  function openAddDrawer() {
    setForm(EMPTY_FORM);
    setFormErrors({});
    setFormServerError("");
    setDrawerOpen(true);
  }

  function openManageDrawer(config: FeedConfig) {
    setForm({ ...EMPTY_FORM, ...config });
    setFormErrors({});
    setFormServerError("");
    setDrawerOpen(true);
  }

  function openPresetManage(preset: FeedPreset) {
    const existing = configs.find(
      (c) => c.endpoint === preset.endpoint && c.family === preset.family
    );
    if (existing) {
      openManageDrawer(existing);
    } else {
      openManageDrawer({
        name: preset.name,
        family: preset.family,
        endpoint: preset.endpoint,
        policy_reference: preset.policy_reference,
        attribution: preset.attribution,
        retention_days: 7,
        polling_minutes: 60,
        enabled: preset.enabled,
        ai_processing_authorized: preset.ai_processing_authorized,
        content_kind: preset.content_kind,
      });
    }
  }

  async function togglePreset(preset: FeedPreset) {
    const key = `preset:${preset.preset_id}`;
    if (pendingKey === key) return;
    setPendingKey(key);
    setRowError(null);
    setNotice("");
    try {
      await mutation.mutateAsync({
        path: `/sources/presets/${preset.preset_id}/enable`,
        method: "POST",
        body: { enabled: !preset.enabled },
      });
      setNotice(`${preset.name} ${preset.enabled ? "disabled" : "enabled"}.`);
    } catch (e) {
      setRowError({
        key,
        message: e instanceof Error ? e.message : "Could not update feed status.",
      });
    } finally {
      setPendingKey(null);
    }
  }

  async function toggleConfigEnabled(config: FeedConfig) {
    if (!config.id) return;
    const key = `config:${config.id}`;
    if (pendingKey === key) return;
    setPendingKey(key);
    setRowError(null);
    setNotice("");
    try {
      const { id, ...rest } = config;
      await mutation.mutateAsync({
        path: `/sources/configurations/${id}`,
        method: "PUT",
        body: { ...rest, enabled: !config.enabled },
      });
      setNotice(`${config.name} ${config.enabled ? "disabled" : "enabled"}.`);
    } catch (e) {
      setRowError({
        key,
        message: e instanceof Error ? e.message : "Could not update feed status.",
      });
    } finally {
      setPendingKey(null);
    }
  }

  function validateForm(values: FeedConfig): Record<string, string> {
    const errs: Record<string, string> = {};
    if (values.name.trim().length < 2) errs.name = "Enter a feed name (at least 2 characters).";
    try {
      const parsed = new URL(values.endpoint.trim());
      if (parsed.protocol !== "https:") errs.endpoint = "Only public HTTPS feed URLs are allowed.";
    } catch {
      errs.endpoint = "Enter a valid public HTTPS feed URL.";
    }
    if (values.policy_reference.trim().length < 3) {
      errs.policy_reference = "Record the publisher permission or public terms reference.";
    }
    if (values.attribution.trim().length < 2) {
      errs.attribution = "Enter the required publisher attribution.";
    }
    if (values.retention_days < 1 || values.retention_days > 30) {
      errs.retention_days = "Retention must be between 1 and 30 days.";
    }
    if (values.polling_minutes < 60 || values.polling_minutes > 1440) {
      errs.polling_minutes = "Polling interval must be between 60 and 1,440 minutes.";
    }
    return errs;
  }

  async function saveForm(e: React.FormEvent) {
    e.preventDefault();
    const errs = validateForm(form);
    setFormErrors(errs);
    if (Object.keys(errs).length > 0) return;
    setSavingForm(true);
    setFormServerError("");
    try {
      const { id, ...body } = form;
      await mutation.mutateAsync({
        path: `/sources/configurations${id ? "/" + id : ""}`,
        method: id ? "PUT" : "POST",
        body: {
          ...body,
          name: body.name.trim(),
          endpoint: body.endpoint.trim(),
          policy_reference: body.policy_reference.trim(),
          attribution: body.attribution.trim(),
        },
      });
      setDrawerOpen(false);
      setNotice(`Saved configuration for ${form.name.trim()}.`);
    } catch (err) {
      setFormServerError(
        err instanceof Error ? err.message : "Feed configuration could not be saved."
      );
    } finally {
      setSavingForm(false);
    }
  }

  const hasActiveFilters =
    Boolean(search.trim()) ||
    categoryFilter !== "all" ||
    statusFilter !== "all" ||
    familyFilter !== "all" ||
    permissionFilter !== "all";

  return (
    <div className="space-y-6">
      {/* Clean Header & Intentional Actions */}
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-border pb-4">
        <div>
          <h3 className="text-lg font-semibold tracking-tight text-foreground">Custom Feeds</h3>
          <p className="text-xs sm:text-sm text-muted-foreground mt-0.5 max-w-2xl">
            Discover and monitor approved community discussions, software releases, and research publications.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() =>
              presetSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })
            }
          >
            Browse preset feeds
          </Button>
          {canManage && (
            <Button size="sm" onClick={openAddDrawer} className="gap-1.5">
              <Plus size={14} /> Add custom feed
            </Button>
          )}
        </div>
      </div>

      {notice && (
        <div
          role="status"
          className="rounded-xl border border-emerald-500/25 bg-emerald-500/10 px-4 py-2.5 text-xs font-medium text-emerald-700 dark:text-emerald-300 flex items-center gap-2"
        >
          <Check size={14} aria-hidden="true" />
          <span>{notice}</span>
        </div>
      )}

      {/* 1. Active Feeds Section (always first!) */}
      <section aria-label="Active feeds" className="space-y-3">
        <div className="flex items-center justify-between gap-2">
          <h4 className="text-sm font-semibold text-foreground">
            Active Feeds ({activeFeeds.length})
          </h4>
          <span className="text-[11px] text-muted-foreground">
            Enabled sources available in Discover &amp; Monitors
          </span>
        </div>

        {configsQuery.isPending ? (
          <div className="h-24 rounded-2xl border border-border bg-muted/30 animate-pulse" />
        ) : activeFeeds.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-border bg-muted/15 p-5 text-center space-y-2">
            <Rss size={20} className="mx-auto text-muted-foreground" aria-hidden="true" />
            <p className="text-sm font-medium text-foreground">No feeds enabled yet</p>
            <p className="text-xs text-muted-foreground max-w-md mx-auto">
              Enable a curated community or release feed below, or add an approved HTTPS feed endpoint.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-border rounded-2xl border border-border bg-card overflow-hidden">
            {activeFeeds.map((cfg) => {
              const rowKey = `config:${cfg.id}`;
              const isBusy = pendingKey === rowKey;
              const marketTech = isMarketIntelligence(cfg.content_kind, cfg.family);

              return (
                <div
                  key={cfg.id}
                  className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4"
                >
                  <div className="min-w-0 space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-sm font-semibold text-foreground truncate">
                        {cfg.name}
                      </span>
                      <span className="rounded-full bg-emerald-500/10 border border-emerald-500/25 px-2 py-0.5 text-[10px] font-semibold text-emerald-700 dark:text-emerald-300">
                        Enabled
                      </span>
                      <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
                        {familyLabel(cfg.family)}
                      </span>
                      {marketTech && (
                        <span className="rounded-full bg-violet-500/10 border border-violet-500/20 px-2 py-0.5 text-[10px] font-medium text-violet-700 dark:text-violet-300">
                          Market / Tech Intelligence
                        </span>
                      )}
                    </div>

                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-muted-foreground">
                      <span className="inline-flex items-center gap-1 truncate max-w-[260px]" title={cfg.endpoint}>
                        <Globe size={11} className="shrink-0" aria-hidden="true" />
                        <span className="truncate">{extractHostname(cfg.endpoint)}</span>
                      </span>
                      <span className="inline-flex items-center gap-1">
                        <Clock size={11} aria-hidden="true" />
                        Every {cfg.polling_minutes}m
                      </span>
                      <span>
                        {cfg.ai_processing_authorized
                          ? "AI processing authorized"
                          : "AI processing restricted"}
                      </span>
                    </div>

                    {rowError?.key === rowKey && (
                      <p role="alert" className="text-xs text-destructive pt-1">
                        {rowError.message}
                      </p>
                    )}
                  </div>

                  {canManage && (
                    <div className="flex items-center gap-2 shrink-0">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => openManageDrawer(cfg)}
                        className="h-8 text-xs gap-1"
                      >
                        <Settings2 size={12} /> Manage
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={isBusy}
                        onClick={() => void toggleConfigEnabled(cfg)}
                        className="h-8 text-xs"
                      >
                        {isBusy ? (
                          <>
                            <Loader2 size={12} className="animate-spin mr-1" /> Updating…
                          </>
                        ) : (
                          "Disable"
                        )}
                      </Button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Disabled custom (non-preset) feeds if any */}
        {disabledCustomFeeds.length > 0 && (
          <div className="space-y-2 pt-2">
            <h5 className="text-xs font-semibold text-muted-foreground">
              Paused Custom Feeds ({disabledCustomFeeds.length})
            </h5>
            <div className="divide-y divide-border rounded-xl border border-border bg-card overflow-hidden">
              {disabledCustomFeeds.map((cfg) => {
                const rowKey = `config:${cfg.id}`;
                const isBusy = pendingKey === rowKey;
                return (
                  <div
                    key={cfg.id}
                    className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 text-xs"
                  >
                    <div className="min-w-0">
                      <span className="font-medium text-foreground">{cfg.name}</span>
                      <span className="ml-2 text-muted-foreground">
                        {familyLabel(cfg.family)} · {extractHostname(cfg.endpoint)}
                      </span>
                    </div>
                    {canManage && (
                      <div className="flex items-center gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => openManageDrawer(cfg)}
                          className="h-7 text-xs"
                        >
                          Manage
                        </Button>
                        <Button
                          size="sm"
                          disabled={isBusy}
                          onClick={() => void toggleConfigEnabled(cfg)}
                          className="h-7 text-xs"
                        >
                          {isBusy ? "Enabling…" : "Enable"}
                        </Button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </section>

      {/* 2. Categorized Preset Feed Catalog with Search & Filters */}
      <section ref={presetSectionRef} aria-label="Preset feed catalog" className="space-y-4 pt-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h4 className="text-sm font-semibold text-foreground">
              Preset Feed Catalog ({presets.length})
            </h4>
            <p className="text-xs text-muted-foreground mt-0.5">
              Pre-approved public Discourse forums, official release feeds, and research publications. Release and academic feeds remain Market / Technology Intelligence.
            </p>
          </div>
          {hasActiveFilters && (
            <button
              type="button"
              onClick={() => {
                setSearch("");
                setCategoryFilter("all");
                setStatusFilter("all");
                setFamilyFilter("all");
                setPermissionFilter("all");
              }}
              className="text-xs font-medium text-primary hover:underline cursor-pointer"
            >
              Reset filters
            </button>
          )}
        </div>

        {/* Compact Filter Bar */}
        <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-5 rounded-xl border border-border bg-muted/20 p-3">
          <div className="relative sm:col-span-2 lg:col-span-1">
            <Search
              size={14}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none"
              aria-hidden="true"
            />
            <input
              type="search"
              aria-label="Search preset feeds"
              placeholder="Search feeds…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full rounded-lg border border-border bg-card pl-8 pr-3 py-1.5 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary/25"
            />
          </div>

          <select
            aria-label="Filter by category"
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value as "all" | FeedCategoryKey)}
            className="rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs text-foreground"
          >
            <option value="all">All categories</option>
            {FEED_CATEGORIES.map((c) => (
              <option key={c.key} value={c.key}>
                {c.label}
              </option>
            ))}
          </select>

          <select
            aria-label="Filter by status"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as "all" | "enabled" | "disabled")}
            className="rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs text-foreground"
          >
            <option value="all">All statuses</option>
            <option value="enabled">Enabled</option>
            <option value="disabled">Available (not enabled)</option>
          </select>

          <select
            aria-label="Filter by source type"
            value={familyFilter}
            onChange={(e) => setFamilyFilter(e.target.value as "all" | FeedFamily)}
            className="rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs text-foreground"
          >
            <option value="all">All source types</option>
            <option value="discourse">Discourse</option>
            <option value="atom">Atom</option>
          </select>

          <select
            aria-label="Filter by AI permission"
            value={permissionFilter}
            onChange={(e) =>
              setPermissionFilter(e.target.value as "all" | "ai_authorized" | "ai_restricted")
            }
            className="rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs text-foreground"
          >
            <option value="all">All AI permissions</option>
            <option value="ai_authorized">AI authorized</option>
            <option value="ai_restricted">AI restricted</option>
          </select>
        </div>

        {presetsQuery.isPending ? (
          <div className="space-y-3">
            {[1, 2, 3].map((n) => (
              <div key={n} className="h-16 rounded-xl border border-border bg-muted/30 animate-pulse" />
            ))}
          </div>
        ) : groupedPresets.length === 0 ? (
          <div className="rounded-xl border border-border bg-card p-6 text-center text-xs text-muted-foreground">
            No preset feeds match your current search or filter criteria.
          </div>
        ) : (
          <div className="space-y-5">
            {groupedPresets.map((group) => (
              <div key={group.key} className="space-y-2.5">
                <div>
                  <h5 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    {group.label} ({group.items.length})
                  </h5>
                  <p className="text-[11px] text-muted-foreground">{group.description}</p>
                </div>

                <div className="divide-y divide-border rounded-2xl border border-border bg-card overflow-hidden">
                  {group.items.map((preset) => {
                    const rowKey = `preset:${preset.preset_id}`;
                    const isBusy = pendingKey === rowKey;
                    const marketTech = isMarketIntelligence(preset.content_kind, preset.family);

                    return (
                      <div
                        key={preset.preset_id}
                        className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 px-4 py-3.5 hover:bg-muted/20 transition-colors"
                      >
                        <div className="min-w-0 space-y-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="text-sm font-semibold text-foreground">
                              {preset.name}
                            </span>
                            <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
                              {familyLabel(preset.family)}
                            </span>
                            {preset.enabled ? (
                              <span className="rounded-full bg-emerald-500/10 border border-emerald-500/25 px-2 py-0.5 text-[10px] font-semibold text-emerald-700 dark:text-emerald-300">
                                Enabled
                              </span>
                            ) : !preset.host_approved ? (
                              <span className="rounded-full bg-amber-500/10 border border-amber-500/30 px-2 py-0.5 text-[10px] font-semibold text-amber-700 dark:text-amber-300">
                                Host approval required
                              </span>
                            ) : null}
                          </div>

                          <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1 text-[11px] text-muted-foreground">
                            <span
                              className="truncate max-w-[260px] font-mono text-[11px]"
                              title={preset.endpoint}
                            >
                              {extractHostname(preset.endpoint)}
                            </span>
                            <span>·</span>
                            {preset.ai_processing_authorized ? (
                              <span className="inline-flex items-center gap-1 text-foreground/80">
                                <Sparkles size={11} className="text-primary" aria-hidden="true" />
                                AI processing permitted
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 text-amber-700 dark:text-amber-300">
                                <ShieldAlert size={11} aria-hidden="true" />
                                AI processing restricted
                              </span>
                            )}
                            {marketTech && (
                              <>
                                <span>·</span>
                                <span>Market / Tech Intelligence</span>
                              </>
                            )}
                          </div>

                          {rowError?.key === rowKey && (
                            <p role="alert" className="text-xs text-destructive pt-1">
                              {rowError.message}
                            </p>
                          )}
                        </div>

                        {canManage && (
                          <div className="flex items-center gap-2 shrink-0">
                            <Button
                              size="sm"
                              variant={preset.enabled ? "outline" : "default"}
                              disabled={isBusy || !preset.host_approved}
                              onClick={() => void togglePreset(preset)}
                              className="h-8 text-xs min-w-[78px]"
                            >
                              {isBusy ? (
                                <Loader2 size={13} className="animate-spin" />
                              ) : preset.enabled ? (
                                "Disable"
                              ) : (
                                "Enable"
                              )}
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => openPresetManage(preset)}
                              className="h-8 text-xs"
                            >
                              Manage
                            </Button>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Focused Feed Configuration / Add Custom Feed Drawer */}
      <Modal
        drawer
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
        title={form.id ? `Manage ${form.name}` : "Add custom feed"}
        description="Only platform-approved HTTPS hosts are accepted. Publisher permissions and source attribution are preserved."
      >
        <form onSubmit={(e) => void saveForm(e)} className="space-y-5 pt-2 text-xs">
          {/* Section 1: Feed Details */}
          <div className="space-y-3">
            <h4 className="font-semibold text-sm text-foreground border-b border-border pb-1.5">
              Feed details
            </h4>

            <div className="space-y-1">
              <label htmlFor="feed-name" className="block font-medium text-foreground">
                Feed name
              </label>
              <input
                id="feed-name"
                value={form.name}
                maxLength={120}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="e.g. Postman Community"
                className="w-full rounded-lg border border-border bg-card px-3 py-2 text-xs text-foreground"
              />
              {formErrors.name && (
                <p role="alert" className="text-[11px] text-destructive">
                  {formErrors.name}
                </p>
              )}
            </div>

            <div className="space-y-1">
              <label htmlFor="feed-family" className="block font-medium text-foreground">
                Source type
              </label>
              <select
                id="feed-family"
                value={form.family}
                onChange={(e) =>
                  setForm((f) => ({ ...f, family: e.target.value as FeedFamily }))
                }
                className="w-full rounded-lg border border-border bg-card px-3 py-2 text-xs text-foreground"
              >
                <option value="discourse">Approved Discourse (RSS/Atom)</option>
                <option value="atom">Atom 1.0 Feed (Releases / Research)</option>
                <option value="rss">RSS / Atom Feed</option>
              </select>
            </div>

            <div className="space-y-1">
              <label htmlFor="feed-endpoint" className="block font-medium text-foreground">
                HTTPS feed URL
              </label>
              <input
                id="feed-endpoint"
                type="url"
                value={form.endpoint}
                maxLength={1000}
                onChange={(e) => setForm((f) => ({ ...f, endpoint: e.target.value }))}
                placeholder="https://community.example.com/latest.rss"
                className="w-full rounded-lg border border-border bg-card px-3 py-2 text-xs font-mono text-foreground"
              />
              {formErrors.endpoint && (
                <p role="alert" className="text-[11px] text-destructive">
                  {formErrors.endpoint}
                </p>
              )}
            </div>
          </div>

          {/* Section 2: Usage Authorization */}
          <div className="space-y-3">
            <h4 className="font-semibold text-sm text-foreground border-b border-border pb-1.5">
              Usage authorization
            </h4>

            <div className="space-y-1">
              <label htmlFor="feed-policy" className="block font-medium text-foreground">
                Permission / terms reference
              </label>
              <input
                id="feed-policy"
                value={form.policy_reference}
                maxLength={1000}
                onChange={(e) => setForm((f) => ({ ...f, policy_reference: e.target.value }))}
                placeholder="Public RSS feed terms URL or written approval reference"
                className="w-full rounded-lg border border-border bg-card px-3 py-2 text-xs text-foreground"
              />
              {formErrors.policy_reference && (
                <p role="alert" className="text-[11px] text-destructive">
                  {formErrors.policy_reference}
                </p>
              )}
            </div>

            <div className="space-y-1">
              <label htmlFor="feed-attribution" className="block font-medium text-foreground">
                Required publisher attribution
              </label>
              <input
                id="feed-attribution"
                value={form.attribution}
                maxLength={300}
                onChange={(e) => setForm((f) => ({ ...f, attribution: e.target.value }))}
                placeholder="e.g. Postman Community (public RSS)"
                className="w-full rounded-lg border border-border bg-card px-3 py-2 text-xs text-foreground"
              />
              {formErrors.attribution && (
                <p role="alert" className="text-[11px] text-destructive">
                  {formErrors.attribution}
                </p>
              )}
            </div>

            {/* Read-only policy-enforced AI authorization status (never self-declared) */}
            <div className="rounded-xl border border-border bg-muted/25 px-3.5 py-2.5 space-y-1">
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium text-foreground">AI processing authorization</span>
                <span
                  className={
                    "rounded-full px-2 py-0.5 text-[10px] font-semibold " +
                    (form.ai_processing_authorized
                      ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
                      : "bg-amber-500/10 text-amber-700 dark:text-amber-300")
                  }
                >
                  {form.ai_processing_authorized ? "Authorized by policy" : "Restricted (human review only)"}
                </span>
              </div>
              <p className="text-[11px] text-muted-foreground">
                Commercial AI processing requires verified publisher license authorization and cannot be self-declared here.
              </p>
            </div>
          </div>

          {/* Section 3: Monitoring */}
          <div className="space-y-3">
            <h4 className="font-semibold text-sm text-foreground border-b border-border pb-1.5">
              Monitoring &amp; retention
            </h4>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label htmlFor="feed-polling" className="block font-medium text-foreground">
                  Polling interval (minutes)
                </label>
                <input
                  id="feed-polling"
                  type="number"
                  min={60}
                  max={1440}
                  value={form.polling_minutes}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, polling_minutes: Number(e.target.value) }))
                  }
                  className="w-full rounded-lg border border-border bg-card px-3 py-2 text-xs text-foreground"
                />
                {formErrors.polling_minutes && (
                  <p role="alert" className="text-[11px] text-destructive">
                    {formErrors.polling_minutes}
                  </p>
                )}
              </div>

              <div className="space-y-1">
                <label htmlFor="feed-retention" className="block font-medium text-foreground">
                  Retention (days)
                </label>
                <input
                  id="feed-retention"
                  type="number"
                  min={1}
                  max={30}
                  value={form.retention_days}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, retention_days: Number(e.target.value) }))
                  }
                  className="w-full rounded-lg border border-border bg-card px-3 py-2 text-xs text-foreground"
                />
                {formErrors.retention_days && (
                  <p role="alert" className="text-[11px] text-destructive">
                    {formErrors.retention_days}
                  </p>
                )}
              </div>
            </div>

            <label className="flex items-center gap-2.5 rounded-xl border border-border bg-muted/20 px-3.5 py-2.5 cursor-pointer">
              <input
                type="checkbox"
                checked={form.enabled}
                onChange={(e) => setForm((f) => ({ ...f, enabled: e.target.checked }))}
                className="accent-primary"
              />
              <span className="font-medium text-foreground">
                Enable this feed after host &amp; policy validation
              </span>
            </label>
          </div>

          {formServerError && (
            <div
              role="alert"
              className="rounded-xl border border-destructive/25 bg-destructive/5 px-3.5 py-2.5 text-xs text-destructive"
            >
              {formServerError}
            </div>
          )}

          <div className="flex items-center justify-end gap-2 border-t border-border pt-4">
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={savingForm}
              onClick={() => setDrawerOpen(false)}
            >
              Cancel
            </Button>
            <Button type="submit" size="sm" disabled={savingForm}>
              {savingForm ? (
                <>
                  <Loader2 size={13} className="animate-spin mr-1.5" /> Saving…
                </>
              ) : form.id ? (
                "Save changes"
              ) : (
                "Save custom feed"
              )}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
