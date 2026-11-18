"use client";

import { useMemo, useState } from "react";
import {
  AlertCircle,
  ArrowUpDown,
  Check,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock,
  Globe,
  Loader2,
  Lock,
  Plus,
  Rss,
  Search,
  Settings2,
  ShieldAlert,
  Sparkles,
  Trash2,
  Wifi,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useRadarCapabilities, useRadarMutation, useRadarRead } from "../provider";
import { ProviderLogo } from "../provider-logo";
import { SlideOverDrawer } from "./SlideOverDrawer";
import {
  categorizeFeed,
  categorizePreset,
  extractHostname,
  FEED_CATEGORIES,
  type FeedCategoryKey,
  type FeedConfig,
  type FeedFamily,
  type FeedPreset,
  type FeedTestResult,
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

const PAGE_SIZE = 10;

type FeedsTabKey = "my_feeds" | "catalog" | "add";
type SortColumn = "name" | "category" | "status" | "ai";
type SortDirection = "asc" | "desc";

interface UnifiedFeedRow {
  rowKey: string;
  id?: string;
  name: string;
  endpoint: string;
  attribution: string;
  family: FeedFamily;
  category: FeedCategoryKey;
  content_kind?: string | null;
  polling_minutes: number;
  enabled: boolean;
  configured: boolean;
  host_approved: boolean;
  ai_processing_authorized: boolean;
  isToggling: boolean;
  isTesting: boolean;
  testResult?: FeedTestResult;
  errorMessage?: string;
  onManage: () => void;
  onToggle: () => void;
  onTest?: () => void;
}

function FeedsDataTable({
  rows,
  totalCount,
  page,
  totalPages,
  onPageChange,
  sortCol,
  sortDir,
  onSort,
  selectable = false,
  selectedIds = [],
  allOnPageSelected = false,
  onToggleAll,
  onToggleSelect,
  canManage,
  tableLabel,
}: {
  rows: UnifiedFeedRow[];
  totalCount: number;
  page: number;
  totalPages: number;
  onPageChange: (nextPage: number) => void;
  sortCol: SortColumn | null;
  sortDir: SortDirection;
  onSort: (col: SortColumn) => void;
  selectable?: boolean;
  selectedIds?: string[];
  allOnPageSelected?: boolean;
  onToggleAll?: () => void;
  onToggleSelect?: (id: string, checked: boolean) => void;
  canManage: boolean;
  tableLabel: string;
}) {
  const statusPill = (row: UnifiedFeedRow) => {
    if (!row.host_approved) {
      return {
        label: "Host approval required",
        cls: "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300",
      };
    }
    if (row.enabled) {
      return {
        label: "Enabled",
        cls: "border-emerald-500/25 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
      };
    }
    if (!row.configured) {
      return {
        label: "Available",
        cls: "border-blue-500/25 bg-blue-500/10 text-blue-700 dark:text-blue-300",
      };
    }
    return {
      label: "Disabled",
      cls: "border-border bg-muted text-muted-foreground",
    };
  };

  const renderSortHeader = (col: SortColumn, label: string) => (
    <button
      type="button"
      onClick={() => onSort(col)}
      className={
        "inline-flex items-center gap-1 hover:text-foreground transition-colors cursor-pointer " +
        (sortCol === col ? "text-foreground" : "text-muted-foreground")
      }
      aria-label={`Sort by ${label}`}
    >
      <span>{label}</span>
      <ArrowUpDown size={11} className={sortCol === col ? "opacity-100" : "opacity-45"} aria-hidden="true" />
      {sortCol === col && (
        <span className="sr-only">{sortDir === "asc" ? "ascending" : "descending"}</span>
      )}
    </button>
  );

  return (
    <>
      {/* Desktop Scalable Table */}
      <div className="hidden md:block overflow-x-auto rounded-2xl border border-border bg-card">
        <table aria-label={tableLabel} className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="border-b border-border bg-muted/35 text-[11px] font-semibold text-muted-foreground">
              {selectable && canManage && (
                <th className="w-9 px-2.5 py-2.5">
                  <input
                    type="checkbox"
                    aria-label="Select all feeds on page"
                    checked={allOnPageSelected}
                    onChange={onToggleAll}
                    className="accent-primary"
                  />
                </th>
              )}
              <th className="px-2.5 py-2.5">{renderSortHeader("name", "Feed")}</th>
              <th className="px-2.5 py-2.5">{renderSortHeader("category", "Category & Type")}</th>
              <th className="px-2.5 py-2.5">{renderSortHeader("status", "Status")}</th>
              <th className="px-2.5 py-2.5">{renderSortHeader("ai", "AI Policy")}</th>
              <th className="px-2.5 py-2.5 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {rows.map((row) => {
              const badge = statusPill(row);
              const isSelected = Boolean(row.id && selectedIds.includes(row.id));

              return (
                <tr key={row.rowKey} className="hover:bg-muted/20 transition-colors">
                  {selectable && canManage && (
                    <td className="px-2.5 py-2.5 align-middle">
                      <input
                        type="checkbox"
                        aria-label={`Select ${row.name}`}
                        checked={isSelected}
                        onChange={(e) => {
                          if (row.id && onToggleSelect) onToggleSelect(row.id, e.target.checked);
                        }}
                        className="accent-primary"
                      />
                    </td>
                  )}
                  <td className="px-2.5 py-2.5 align-middle max-w-[240px]">
                    <div className="flex items-center gap-2 min-w-0">
                      <div className="flex h-7 w-7 items-center justify-center rounded-lg border border-border bg-muted/30 shrink-0">
                        <ProviderLogo provider={resolveLogoHint(row)} size={15} />
                      </div>
                      <div className="min-w-0">
                        <p className="font-semibold text-foreground truncate">{row.name}</p>
                        <p
                          className="text-[11px] text-muted-foreground font-mono truncate"
                          title={row.endpoint}
                        >
                          {extractHostname(row.endpoint)} · {row.polling_minutes}m
                        </p>
                        {row.testResult && (
                          <p
                            className={
                              "text-[10px] mt-0.5 " +
                              (row.testResult.ok
                                ? "text-emerald-700 dark:text-emerald-300"
                                : "text-destructive")
                            }
                          >
                            {row.testResult.ok
                              ? `HTTP ${row.testResult.http_status} · ${row.testResult.entry_count} entries · ${row.testResult.latency_ms}ms`
                              : row.testResult.error || "Feed test failed"}
                          </p>
                        )}
                        {row.errorMessage && (
                          <p role="alert" className="text-[10px] text-destructive mt-0.5">
                            {row.errorMessage}
                          </p>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-2.5 py-2.5 align-middle whitespace-nowrap">
                    <p className="text-foreground font-medium">{categoryLabel(row.category)}</p>
                    <p className="text-[11px] text-muted-foreground">
                      {familyLabel(row.family)}
                      {isMarketIntelligence(row.content_kind, row.family) ? " · Market / Tech" : ""}
                    </p>
                  </td>
                  <td className="px-2.5 py-2.5 align-middle whitespace-nowrap">
                    <span
                      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold ${badge.cls}`}
                    >
                      {badge.label}
                    </span>
                  </td>
                  <td className="px-2.5 py-2.5 align-middle whitespace-nowrap">
                    {row.ai_processing_authorized ? (
                      <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/25 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-700 dark:text-emerald-300">
                        <Sparkles size={10} aria-hidden="true" /> AI Authorized
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[10px] font-semibold text-amber-700 dark:text-amber-300">
                        <ShieldAlert size={10} aria-hidden="true" /> AI Restricted
                      </span>
                    )}
                  </td>
                  <td className="px-2.5 py-2.5 align-middle text-right whitespace-nowrap">
                    <div className="inline-flex items-center justify-end gap-1">
                      {row.onTest && (
                        <Button
                          size="sm"
                          variant="ghost"
                          disabled={row.isTesting || row.isToggling}
                          onClick={row.onTest}
                          className="h-7 px-2 text-[11px] gap-1"
                        >
                          {row.isTesting ? (
                            <Loader2 size={11} className="animate-spin" />
                          ) : (
                            <Wifi size={11} />
                          )}
                          Test
                        </Button>
                      )}
                      {canManage && (
                        <>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={row.onManage}
                            className="h-7 px-2 text-[11px] gap-1"
                          >
                            <Settings2 size={11} /> Manage
                          </Button>
                          <Button
                            size="sm"
                            variant={row.enabled ? "outline" : "default"}
                            disabled={row.isToggling || !row.host_approved}
                            onClick={row.onToggle}
                            className="h-7 px-2.5 text-[11px] min-w-[62px]"
                          >
                            {row.isToggling ? (
                              <Loader2 size={11} className="animate-spin" />
                            ) : row.enabled ? (
                              "Disable"
                            ) : (
                              "Enable"
                            )}
                          </Button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Mobile Compact Cards */}
      <div className="md:hidden divide-y divide-border rounded-2xl border border-border bg-card overflow-hidden">
        {rows.map((row) => {
          const badge = statusPill(row);
          return (
            <div key={row.rowKey} className="p-4 space-y-2.5">
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2.5 min-w-0">
                  <ProviderLogo provider={resolveLogoHint(row)} size={18} />
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-foreground truncate">{row.name}</p>
                    <p className="text-[11px] font-mono text-muted-foreground truncate">
                      {extractHostname(row.endpoint)} · {row.polling_minutes}m
                    </p>
                  </div>
                </div>
                <span
                  className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold shrink-0 ${badge.cls}`}
                >
                  {badge.label}
                </span>
              </div>

              <div className="flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
                <span>{categoryLabel(row.category)}</span>
                <span>·</span>
                <span>{familyLabel(row.family)}</span>
                <span>·</span>
                <span>{row.ai_processing_authorized ? "AI Authorized" : "AI Restricted"}</span>
              </div>

              {row.testResult && (
                <p
                  className={
                    "text-[11px] " +
                    (row.testResult.ok
                      ? "text-emerald-700 dark:text-emerald-300"
                      : "text-destructive")
                  }
                >
                  {row.testResult.ok
                    ? `HTTP ${row.testResult.http_status} · ${row.testResult.entry_count} entries (${row.testResult.latency_ms} ms)`
                    : row.testResult.error || "Feed test failed"}
                </p>
              )}

              {row.errorMessage && (
                <p role="alert" className="text-[11px] text-destructive">
                  {row.errorMessage}
                </p>
              )}

              <div className="flex flex-wrap items-center gap-2 pt-1">
                {row.onTest && (
                  <Button
                    size="sm"
                    variant="ghost"
                    disabled={row.isTesting || row.isToggling}
                    onClick={row.onTest}
                    className="h-7 px-2 text-xs gap-1"
                  >
                    <Wifi size={12} /> {row.isTesting ? "Testing…" : "Test"}
                  </Button>
                )}
                {canManage && (
                  <>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={row.onManage}
                      className="h-7 text-xs gap-1"
                    >
                      <Settings2 size={12} /> Manage
                    </Button>
                    <Button
                      size="sm"
                      variant={row.enabled ? "outline" : "default"}
                      disabled={row.isToggling || !row.host_approved}
                      onClick={row.onToggle}
                      className="h-7 text-xs"
                    >
                      {row.isToggling ? "…" : row.enabled ? "Disable" : "Enable"}
                    </Button>
                  </>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between text-xs text-muted-foreground pt-1">
          <span>
            Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, totalCount)} of{" "}
            {totalCount} feeds
          </span>
          <div className="flex items-center gap-1.5">
            <Button
              size="sm"
              variant="outline"
              disabled={page <= 1}
              onClick={() => onPageChange(Math.max(1, page - 1))}
              className="h-7 px-2 text-xs gap-1"
            >
              <ChevronLeft size={13} /> Prev
            </Button>
            <span className="px-2 tabular-nums">
              Page {page} of {totalPages}
            </span>
            <Button
              size="sm"
              variant="outline"
              disabled={page >= totalPages}
              onClick={() => onPageChange(Math.min(totalPages, page + 1))}
              className="h-7 px-2 text-xs gap-1"
            >
              Next <ChevronRight size={13} />
            </Button>
          </div>
        </div>
      )}
    </>
  );
}

function familyLabel(family: FeedFamily | string): string {
  if (family === "discourse") return "Discourse";
  if (family === "atom") return "Atom";
  return "RSS / Atom";
}

function categoryLabel(key: FeedCategoryKey): string {
  return FEED_CATEGORIES.find((c) => c.key === key)?.label || "Developer Updates";
}

function isMarketIntelligence(contentKind?: string | null, family?: string): boolean {
  return (
    family === "atom" ||
    contentKind === "release_announcement" ||
    contentKind === "research_paper"
  );
}

function resolveLogoHint(feed: { name: string; endpoint: string; family: string }): string {
  const lower = `${feed.name} ${feed.endpoint}`.toLowerCase();
  if (lower.includes("github.com") && lower.includes("vscode")) return "vscode";
  if (lower.includes("github.com")) return "github";
  if (lower.includes("youtube.com")) return "youtube";
  return feed.family === "discourse" ? "discourse" : feed.family === "atom" ? "atom" : "rss";
}

function formatTime(iso: string | null | undefined): string {
  if (!iso) return "—";
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

export function CustomFeedsPanel() {
  const access = useRadarCapabilities();
  const configsQuery = useRadarRead<{ items: FeedConfig[] }>("/sources/configurations");
  const presetsQuery = useRadarRead<{ items: FeedPreset[] }>("/sources/presets");
  const mutation = useRadarMutation();

  const configs = useMemo(() => configsQuery.data?.items || [], [configsQuery.data?.items]);
  const presets = useMemo(() => presetsQuery.data?.items || [], [presetsQuery.data?.items]);
  const canManage = Boolean(access.data?.can_manage);

  const presetEndpoints = useMemo(
    () => new Set(presets.map((p) => `${p.family}:${p.endpoint}`)),
    [presets]
  );

  // Sub-tab state: defaults to "my_feeds" when feeds exist, or "catalog" when empty
  const [selectedTab, setSelectedTab] = useState<FeedsTabKey | null>(null);
  const activeTab: FeedsTabKey = selectedTab ?? (configs.length > 0 ? "my_feeds" : "catalog");

  // Shared search & filter state
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<"all" | FeedCategoryKey>("all");
  const [statusFilter, setStatusFilter] = useState<"all" | "enabled" | "disabled">("all");
  const [familyFilter, setFamilyFilter] = useState<"all" | FeedFamily>("all");
  const [permissionFilter, setPermissionFilter] = useState<
    "all" | "ai_authorized" | "ai_restricted"
  >("all");
  const [sortCol, setSortCol] = useState<SortColumn | null>(null);
  const [sortDir, setSortDir] = useState<SortDirection>("asc");
  const [page, setPage] = useState(1);

  function handleSort(col: SortColumn) {
    if (sortCol === col) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortCol(col);
      setSortDir("asc");
    }
    setPage(1);
  }

  // Bulk selection state for My Feeds
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [bulkConfirm, setBulkConfirm] = useState<{ enabled: boolean; count: number } | null>(null);

  // Per-row pending, test results & feedback states
  const [pendingKey, setPendingKey] = useState<string | null>(null);
  const [rowError, setRowError] = useState<{ key: string; message: string } | null>(null);
  const [feedTestResults, setFeedTestResults] = useState<Record<string, FeedTestResult>>({});
  const [notice, setNotice] = useState("");

  // Manage Drawer state
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerForm, setDrawerForm] = useState<FeedConfig>(EMPTY_FORM);
  const [drawerIsPreset, setDrawerIsPreset] = useState(false);
  const [drawerErrors, setDrawerErrors] = useState<Record<string, string>>({});
  const [drawerServerError, setDrawerServerError] = useState("");
  const [drawerTestResult, setDrawerTestResult] = useState<FeedTestResult | null>(null);
  const [savingDrawer, setSavingDrawer] = useState(false);
  const [testingDrawer, setTestingDrawer] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  // Add Custom Feed tab state
  const [addForm, setAddForm] = useState<FeedConfig>(EMPTY_FORM);
  const [addErrors, setAddErrors] = useState<Record<string, string>>({});
  const [addServerError, setAddServerError] = useState("");
  const [addTestResult, setAddTestResult] = useState<FeedTestResult | null>(null);
  const [savingAdd, setSavingAdd] = useState(false);
  const [testingAdd, setTestingAdd] = useState(false);

  // KPI metrics
  const enabledCount = useMemo(() => configs.filter((c) => c.enabled).length, [configs]);
  const aiAuthorizedCount = useMemo(
    () => configs.filter((c) => c.enabled && c.ai_processing_authorized).length,
    [configs]
  );
  const aiRestrictedCount = useMemo(
    () => configs.filter((c) => c.enabled && !c.ai_processing_authorized).length,
    [configs]
  );

  // Lookup map so Browse Feed Catalog stays strictly synchronized with workspace configs
  const configByKey = useMemo(() => {
    const map = new Map<string, FeedConfig>();
    for (const c of configs) {
      map.set(`${c.family}:${c.endpoint}`, c);
    }
    return map;
  }, [configs]);

  function sortItems<T>(
    items: T[],
    getKey: (item: T) => { name: string; category: FeedCategoryKey; enabled: boolean; configured: boolean; ai: boolean }
  ): T[] {
    if (!sortCol) return items;
    const mult = sortDir === "asc" ? 1 : -1;
    return [...items].sort((a, b) => {
      const ka = getKey(a);
      const kb = getKey(b);
      if (sortCol === "category") {
        const cmp = categoryLabel(ka.category).localeCompare(categoryLabel(kb.category));
        if (cmp !== 0) return cmp * mult;
      } else if (sortCol === "status") {
        const rank = (x: typeof ka) => (x.enabled ? 0 : x.configured ? 1 : 2);
        const cmp = rank(ka) - rank(kb);
        if (cmp !== 0) return cmp * mult;
      } else if (sortCol === "ai") {
        const cmp = Number(kb.ai) - Number(ka.ai);
        if (cmp !== 0) return cmp * mult;
      }
      return ka.name.localeCompare(kb.name) * mult;
    });
  }

  // Filtered & Sorted My Feeds
  const filteredConfigs = useMemo(() => {
    const q = search.trim().toLowerCase();
    const matched = configs.filter((c) => {
      if (q && !`${c.name} ${c.endpoint} ${c.attribution} ${c.family}`.toLowerCase().includes(q)) {
        return false;
      }
      if (categoryFilter !== "all" && categorizeFeed(c) !== categoryFilter) return false;
      if (statusFilter === "enabled" && !c.enabled) return false;
      if (statusFilter === "disabled" && c.enabled) return false;
      if (familyFilter !== "all" && c.family !== familyFilter) return false;
      if (permissionFilter === "ai_authorized" && !c.ai_processing_authorized) return false;
      if (permissionFilter === "ai_restricted" && c.ai_processing_authorized) return false;
      return true;
    });
    return sortItems(matched, (c) => ({
      name: c.name,
      category: categorizeFeed(c),
      enabled: c.enabled,
      configured: true,
      ai: Boolean(c.ai_processing_authorized),
    }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [configs, search, categoryFilter, statusFilter, familyFilter, permissionFilter, sortCol, sortDir]);

  const totalPages = Math.max(1, Math.ceil(filteredConfigs.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const paginatedConfigs = useMemo(
    () => filteredConfigs.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE),
    [filteredConfigs, safePage]
  );

  // Filtered & Sorted Catalog Presets (deduplicated & synced with live workspace configs)
  const filteredPresets = useMemo(() => {
    const q = search.trim().toLowerCase();
    const matched = presets.filter((p) => {
      const linked = configByKey.get(`${p.family}:${p.endpoint}`);
      const isEnabled = linked ? linked.enabled : p.enabled;
      const aiAllowed = linked ? linked.ai_processing_authorized : p.ai_processing_authorized;
      if (q && !`${p.name} ${p.endpoint} ${p.attribution} ${p.family}`.toLowerCase().includes(q)) {
        return false;
      }
      if (categoryFilter !== "all" && categorizePreset(p) !== categoryFilter) return false;
      if (statusFilter === "enabled" && !isEnabled) return false;
      if (statusFilter === "disabled" && isEnabled) return false;
      if (familyFilter !== "all" && p.family !== familyFilter) return false;
      if (permissionFilter === "ai_authorized" && !aiAllowed) return false;
      if (permissionFilter === "ai_restricted" && aiAllowed) return false;
      return true;
    });
    return sortItems(matched, (p) => {
      const linked = configByKey.get(`${p.family}:${p.endpoint}`);
      return {
        name: p.name,
        category: categorizePreset(p),
        enabled: linked ? linked.enabled : p.enabled,
        configured: Boolean(linked || p.configured),
        ai: Boolean(linked ? linked.ai_processing_authorized : p.ai_processing_authorized),
      };
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [presets, configByKey, search, categoryFilter, statusFilter, familyFilter, permissionFilter, sortCol, sortDir]);

  const catalogTotalPages = Math.max(1, Math.ceil(filteredPresets.length / PAGE_SIZE));
  const catalogSafePage = Math.min(page, catalogTotalPages);
  const paginatedPresets = useMemo(
    () => filteredPresets.slice((catalogSafePage - 1) * PAGE_SIZE, catalogSafePage * PAGE_SIZE),
    [filteredPresets, catalogSafePage]
  );

  const hasActiveFilters =
    Boolean(search.trim()) ||
    categoryFilter !== "all" ||
    statusFilter !== "all" ||
    familyFilter !== "all" ||
    permissionFilter !== "all";

  function resetFilters() {
    setSearch("");
    setCategoryFilter("all");
    setStatusFilter("all");
    setFamilyFilter("all");
    setPermissionFilter("all");
    setPage(1);
  }

  function openManageDrawer(config: FeedConfig) {
    setDrawerForm({ ...EMPTY_FORM, ...config });
    setDrawerIsPreset(presetEndpoints.has(`${config.family}:${config.endpoint}`));
    setDrawerErrors({});
    setDrawerServerError("");
    setDrawerTestResult(config.id ? feedTestResults[config.id] || null : null);
    setConfirmDelete(false);
    setDrawerOpen(true);
  }

  function openPresetManage(preset: FeedPreset) {
    const existing = configs.find(
      (c) => c.endpoint === preset.endpoint && c.family === preset.family
    );
    if (existing) {
      openManageDrawer(existing);
    } else {
      setDrawerForm({
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
        policy: preset.policy,
      });
      setDrawerIsPreset(true);
      setDrawerErrors({});
      setDrawerServerError("");
      setDrawerTestResult(null);
      setConfirmDelete(false);
      setDrawerOpen(true);
    }
  }

  function validateFeed(values: FeedConfig): Record<string, string> {
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

  async function togglePreset(preset: FeedPreset) {
    const key = `preset:${preset.preset_id}`;
    if (pendingKey === key) return;
    const currentEnabled =
      configByKey.get(`${preset.family}:${preset.endpoint}`)?.enabled ?? preset.enabled;
    setPendingKey(key);
    setRowError(null);
    setNotice("");
    try {
      await mutation.mutateAsync({
        path: `/sources/presets/${preset.preset_id}/enable`,
        method: "POST",
        body: { enabled: !currentEnabled },
      });
      setNotice(`${preset.name} ${currentEnabled ? "disabled" : "enabled"}.`);
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
      const { id, policy: _p, ...rest } = config;
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

  async function testConfigRow(config: FeedConfig) {
    if (!config.id) return;
    const key = `test:${config.id}`;
    if (pendingKey === key) return;
    setPendingKey(key);
    setRowError(null);
    setNotice("");
    try {
      const res = (await mutation.mutateAsync({
        path: `/sources/configurations/${config.id}/test`,
        method: "POST",
        body: {},
      })) as FeedTestResult;
      setFeedTestResults((prev) => ({ ...prev, [config.id!]: res }));
      if (res.ok) {
        setNotice(`${config.name}: HTTP ${res.http_status} · ${res.entry_count} entries parsed (${res.latency_ms} ms).`);
      } else {
        setRowError({ key: `config:${config.id}`, message: res.error || "Feed endpoint test failed." });
      }
    } catch (e) {
      setRowError({
        key: `config:${config.id}`,
        message: e instanceof Error ? e.message : "Feed endpoint test failed.",
      });
    } finally {
      setPendingKey(null);
    }
  }

  async function runBulkToggle(enabled: boolean) {
    if (selectedIds.length === 0) return;
    setPendingKey("bulk");
    setNotice("");
    setRowError(null);
    try {
      const res = (await mutation.mutateAsync({
        path: "/sources/configurations/bulk",
        method: "POST",
        body: { ids: selectedIds, enabled },
      })) as { updated: number; enabled: boolean };
      setSelectedIds([]);
      setBulkConfirm(null);
      setNotice(`${res.updated} feed${res.updated === 1 ? "" : "s"} ${enabled ? "enabled" : "disabled"}.`);
    } catch (e) {
      setRowError({
        key: "bulk",
        message: e instanceof Error ? e.message : "Bulk feed update failed.",
      });
    } finally {
      setPendingKey(null);
    }
  }

  async function testDrawerEndpoint() {
    setTestingDrawer(true);
    setDrawerServerError("");
    try {
      const res = drawerForm.id
        ? ((await mutation.mutateAsync({
            path: `/sources/configurations/${drawerForm.id}/test`,
            method: "POST",
            body: {},
          })) as FeedTestResult)
        : ((await mutation.mutateAsync({
            path: "/sources/feeds/test",
            method: "POST",
            body: {
              family: drawerForm.family,
              endpoint: drawerForm.endpoint.trim(),
              name: drawerForm.name.trim(),
            },
          })) as FeedTestResult);
      setDrawerTestResult(res);
      if (drawerForm.id) {
        setFeedTestResults((prev) => ({ ...prev, [drawerForm.id!]: res }));
      }
    } catch (err) {
      setDrawerServerError(
        err instanceof Error ? err.message : "Could not test feed endpoint."
      );
    } finally {
      setTestingDrawer(false);
    }
  }

  async function saveDrawerForm(e: React.FormEvent) {
    e.preventDefault();
    const errs = validateFeed(drawerForm);
    setDrawerErrors(errs);
    if (Object.keys(errs).length > 0) return;
    setSavingDrawer(true);
    setDrawerServerError("");
    try {
      const { id, policy: _p, ...body } = drawerForm;
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
      setNotice(`Saved configuration for ${drawerForm.name.trim()}.`);
    } catch (err) {
      setDrawerServerError(
        err instanceof Error ? err.message : "Feed configuration could not be saved."
      );
    } finally {
      setSavingDrawer(false);
    }
  }

  async function deleteDrawerFeed() {
    if (!drawerForm.id) return;
    setSavingDrawer(true);
    setDrawerServerError("");
    try {
      await mutation.mutateAsync({
        path: `/sources/configurations/${drawerForm.id}`,
        method: "DELETE",
      });
      setDrawerOpen(false);
      setConfirmDelete(false);
      setNotice(`Removed custom feed "${drawerForm.name}".`);
    } catch (err) {
      setDrawerServerError(err instanceof Error ? err.message : "Could not delete feed.");
    } finally {
      setSavingDrawer(false);
    }
  }

  async function testAddUrl() {
    const endpoint = addForm.endpoint.trim();
    if (!endpoint) {
      setAddErrors((prev) => ({ ...prev, endpoint: "Enter an HTTPS feed URL to test." }));
      return;
    }
    setTestingAdd(true);
    setAddServerError("");
    setAddTestResult(null);
    try {
      const res = (await mutation.mutateAsync({
        path: "/sources/feeds/test",
        method: "POST",
        body: {
          family: addForm.family,
          endpoint,
          name: addForm.name.trim(),
        },
      })) as FeedTestResult;
      setAddTestResult(res);
    } catch (err) {
      setAddServerError(
        err instanceof Error ? err.message : "Feed URL validation failed."
      );
    } finally {
      setTestingAdd(false);
    }
  }

  async function saveAddForm(e: React.FormEvent) {
    e.preventDefault();
    const errs = validateFeed(addForm);
    setAddErrors(errs);
    if (Object.keys(errs).length > 0) return;
    setSavingAdd(true);
    setAddServerError("");
    try {
      const { id: _id, policy: _p, ...body } = addForm;
      await mutation.mutateAsync({
        path: "/sources/configurations",
        method: "POST",
        body: {
          ...body,
          name: body.name.trim(),
          endpoint: body.endpoint.trim(),
          policy_reference: body.policy_reference.trim(),
          attribution: body.attribution.trim(),
        },
      });
      setNotice(`Added custom feed "${addForm.name.trim()}".`);
      setAddForm(EMPTY_FORM);
      setAddTestResult(null);
      setSelectedTab("my_feeds");
    } catch (err) {
      setAddServerError(
        err instanceof Error ? err.message : "Could not save custom feed."
      );
    } finally {
      setSavingAdd(false);
    }
  }

  const allOnPageSelected =
    paginatedConfigs.length > 0 &&
    paginatedConfigs.every((c) => c.id && selectedIds.includes(c.id));

  function togglePageSelection() {
    const pageIds = paginatedConfigs.map((c) => c.id).filter(Boolean) as string[];
    if (allOnPageSelected) {
      setSelectedIds((prev) => prev.filter((id) => !pageIds.includes(id)));
    } else {
      setSelectedIds((prev) => Array.from(new Set([...prev, ...pageIds])));
    }
  }

  return (
    <div className="space-y-5">
      {/* Header + Compact 3-Tab Switcher */}
      <div className="space-y-3 border-b border-border pb-4">
        <div>
          <h3 className="text-lg font-semibold tracking-tight text-foreground">Custom Feeds</h3>
          <p className="text-xs sm:text-sm text-muted-foreground mt-0.5 max-w-2xl">
            Manage workspace Discourse, Atom, and RSS feeds with live endpoint testing and centralized AI policy enforcement.
          </p>
        </div>

        <div
          role="tablist"
          aria-label="Custom feeds sections"
          className="inline-flex rounded-xl border border-border bg-muted/50 p-1 w-fit max-w-full overflow-x-auto"
        >
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "my_feeds"}
            onClick={() => {
              setSelectedTab("my_feeds");
              setPage(1);
            }}
            className={
              "rounded-lg px-3 py-1.5 text-xs font-medium whitespace-nowrap transition-all cursor-pointer " +
              (activeTab === "my_feeds"
                ? "bg-card text-foreground shadow-sm font-semibold"
                : "text-muted-foreground hover:text-foreground")
            }
          >
            My Feeds ({configs.length})
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "catalog"}
            onClick={() => {
              setSelectedTab("catalog");
              setPage(1);
            }}
            className={
              "rounded-lg px-3 py-1.5 text-xs font-medium whitespace-nowrap transition-all cursor-pointer " +
              (activeTab === "catalog"
                ? "bg-card text-foreground shadow-sm font-semibold"
                : "text-muted-foreground hover:text-foreground")
            }
          >
            Browse Feed Catalog ({presets.length})
          </button>
          {canManage && (
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === "add"}
              onClick={() => setSelectedTab("add")}
              className={
                "rounded-lg px-3 py-1.5 text-xs font-medium whitespace-nowrap transition-all inline-flex items-center gap-1 cursor-pointer " +
                (activeTab === "add"
                  ? "bg-card text-foreground shadow-sm font-semibold"
                  : "text-muted-foreground hover:text-foreground")
              }
            >
              <Plus size={12} /> Add Custom Feed
            </button>
          )}
        </div>
      </div>

      {/* Compact KPI Summary */}
      <div className="grid gap-3 grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border border-border bg-card px-4 py-2.5">
          <p className="text-[11px] font-medium text-muted-foreground">Enabled feeds</p>
          <p className="text-lg font-bold tracking-tight text-foreground tabular-nums">
            {enabledCount}
            <span className="text-xs font-normal text-muted-foreground"> / {configs.length}</span>
          </p>
        </div>
        <div className="rounded-xl border border-border bg-card px-4 py-2.5">
          <p className="text-[11px] font-medium text-muted-foreground">AI-authorized feeds</p>
          <p className="text-lg font-bold tracking-tight text-emerald-600 dark:text-emerald-400 tabular-nums">
            {aiAuthorizedCount}
          </p>
        </div>
        <div className="rounded-xl border border-border bg-card px-4 py-2.5">
          <p className="text-[11px] font-medium text-muted-foreground">AI-restricted feeds</p>
          <p className="text-lg font-bold tracking-tight text-amber-600 dark:text-amber-400 tabular-nums">
            {aiRestrictedCount}
          </p>
        </div>
        <div className="rounded-xl border border-border bg-card px-4 py-2.5">
          <p className="text-[11px] font-medium text-muted-foreground">Curated catalog</p>
          <p className="text-lg font-bold tracking-tight text-foreground tabular-nums">
            {presets.length}
          </p>
        </div>
      </div>

      {notice && (
        <div
          role="status"
          className="rounded-xl border border-emerald-500/25 bg-emerald-500/10 px-4 py-2.5 text-xs font-medium text-emerald-700 dark:text-emerald-300 flex items-center gap-2"
        >
          <Check size={14} className="shrink-0" aria-hidden="true" />
          <span>{notice}</span>
        </div>
      )}

      {rowError?.key === "bulk" && (
        <div
          role="alert"
          className="rounded-xl border border-destructive/25 bg-destructive/5 px-4 py-2.5 text-xs font-medium text-destructive"
        >
          {rowError.message}
        </div>
      )}

      {/* Shared Search & Filter Toolbar for My Feeds and Catalog */}
      {activeTab !== "add" && (
        <div className="space-y-2">
          <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-5 rounded-xl border border-border bg-muted/20 p-3">
            <div className="relative sm:col-span-2 lg:col-span-1">
              <Search
                size={14}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none"
                aria-hidden="true"
              />
              <input
                type="search"
                aria-label="Search feeds"
                placeholder="Search feeds…"
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setPage(1);
                }}
                style={{ paddingLeft: "2.25rem" }}
                className="w-full rounded-lg border border-border bg-card pr-3 py-1.5 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary/25"
              />
            </div>

            <select
              aria-label="Filter by category"
              value={categoryFilter}
              onChange={(e) => {
                setCategoryFilter(e.target.value as "all" | FeedCategoryKey);
                setPage(1);
              }}
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
              onChange={(e) => {
                setStatusFilter(e.target.value as "all" | "enabled" | "disabled");
                setPage(1);
              }}
              className="rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs text-foreground"
            >
              <option value="all">All statuses</option>
              <option value="enabled">Enabled</option>
              <option value="disabled">Disabled / Not enabled</option>
            </select>

            <select
              aria-label="Filter by source type"
              value={familyFilter}
              onChange={(e) => {
                setFamilyFilter(e.target.value as "all" | FeedFamily);
                setPage(1);
              }}
              className="rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs text-foreground"
            >
              <option value="all">All source types</option>
              <option value="discourse">Discourse</option>
              <option value="atom">Atom</option>
              <option value="rss">RSS</option>
            </select>

            <select
              aria-label="Filter by AI permission"
              value={permissionFilter}
              onChange={(e) => {
                setPermissionFilter(e.target.value as "all" | "ai_authorized" | "ai_restricted");
                setPage(1);
              }}
              className="rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs text-foreground"
            >
              <option value="all">All AI permissions</option>
              <option value="ai_authorized">AI authorized</option>
              <option value="ai_restricted">AI restricted</option>
            </select>
          </div>

          {hasActiveFilters && (
            <div className="flex justify-end">
              <button
                type="button"
                onClick={resetFilters}
                className="text-xs font-medium text-primary hover:underline cursor-pointer"
              >
                Reset filters
              </button>
            </div>
          )}
        </div>
      )}

      {/* =================================================================
          TAB 1: MY FEEDS (Scalable Paginated Table + Bulk Actions)
      ================================================================== */}
      {activeTab === "my_feeds" && (
        <section aria-label="My feeds" className="space-y-3">
          {/* Bulk Actions Bar */}
          {canManage && selectedIds.length > 0 && (
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-primary/30 bg-primary/5 px-4 py-2.5 text-xs">
              <span className="font-semibold text-foreground">
                {selectedIds.length} feed{selectedIds.length === 1 ? "" : "s"} selected
              </span>
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={pendingKey === "bulk"}
                  onClick={() => setBulkConfirm({ enabled: true, count: selectedIds.length })}
                  className="h-7 text-xs"
                >
                  Enable selected
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={pendingKey === "bulk"}
                  onClick={() => setBulkConfirm({ enabled: false, count: selectedIds.length })}
                  className="h-7 text-xs"
                >
                  Disable selected
                </Button>
                <button
                  type="button"
                  onClick={() => {
                    setSelectedIds([]);
                    setBulkConfirm(null);
                  }}
                  className="text-muted-foreground hover:text-foreground px-2 cursor-pointer"
                >
                  Clear
                </button>
              </div>
            </div>
          )}

          {bulkConfirm && (
            <div
              role="alertdialog"
              aria-label="Confirm bulk feed change"
              className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3.5 flex flex-wrap items-center justify-between gap-3 text-xs"
            >
              <span className="text-foreground font-medium">
                {bulkConfirm.enabled ? "Enable" : "Disable"} {bulkConfirm.count} selected feed
                {bulkConfirm.count === 1 ? "" : "s"}?
              </span>
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  disabled={pendingKey === "bulk"}
                  onClick={() => void runBulkToggle(bulkConfirm.enabled)}
                  className="h-7 text-xs"
                >
                  {pendingKey === "bulk" ? "Updating…" : "Confirm"}
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setBulkConfirm(null)}
                  className="h-7 text-xs"
                >
                  Cancel
                </Button>
              </div>
            </div>
          )}

          {configsQuery.isPending ? (
            <div className="h-36 rounded-2xl border border-border bg-muted/30 animate-pulse" />
          ) : configsQuery.isError ? (
            <div role="alert" className="rounded-2xl border border-destructive/25 bg-destructive/5 p-5 space-y-2.5 text-xs">
              <p className="font-semibold text-destructive">Configured feeds could not be loaded</p>
              <p className="text-muted-foreground">{configsQuery.error?.message || "Please retry."}</p>
              <Button size="sm" variant="outline" onClick={() => void configsQuery.refetch()}>
                Retry
              </Button>
            </div>
          ) : configs.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-border bg-muted/15 p-8 text-center space-y-2.5">
              <Rss size={22} className="mx-auto text-muted-foreground" aria-hidden="true" />
              <p className="text-sm font-medium text-foreground">No feeds configured yet</p>
              <p className="text-xs text-muted-foreground max-w-md mx-auto">
                Browse the curated feed catalog to enable verified Discourse, release, and research feeds, or add your own approved HTTPS feed.
              </p>
              <div className="flex justify-center gap-2 pt-1">
                <Button size="sm" onClick={() => { setSelectedTab("catalog"); setPage(1); }}>
                  Browse Feed Catalog
                </Button>
                {canManage && (
                  <Button size="sm" variant="outline" onClick={() => setSelectedTab("add")}>
                    Add Custom Feed
                  </Button>
                )}
              </div>
            </div>
          ) : filteredConfigs.length === 0 ? (
            <div className="rounded-xl border border-border bg-card p-6 text-center text-xs text-muted-foreground">
              No configured feeds match your search or filter criteria.
            </div>
          ) : (
            <FeedsDataTable
              tableLabel="My feeds"
              rows={paginatedConfigs.map((cfg) => {
                const rowKey = `config:${cfg.id || cfg.endpoint}`;
                return {
                  rowKey,
                  id: cfg.id,
                  name: cfg.name,
                  endpoint: cfg.endpoint,
                  attribution: cfg.attribution,
                  family: cfg.family,
                  category: categorizeFeed(cfg),
                  content_kind: cfg.content_kind,
                  polling_minutes: cfg.polling_minutes,
                  enabled: cfg.enabled,
                  configured: true,
                  host_approved: true,
                  ai_processing_authorized: Boolean(cfg.ai_processing_authorized),
                  isToggling: pendingKey === rowKey,
                  isTesting: pendingKey === `test:${cfg.id}`,
                  testResult: cfg.id ? feedTestResults[cfg.id] : undefined,
                  errorMessage: rowError?.key === rowKey ? rowError.message : undefined,
                  onManage: () => openManageDrawer(cfg),
                  onToggle: () => void toggleConfigEnabled(cfg),
                  onTest: cfg.id ? () => void testConfigRow(cfg) : undefined,
                };
              })}
              totalCount={filteredConfigs.length}
              page={safePage}
              totalPages={totalPages}
              onPageChange={setPage}
              sortCol={sortCol}
              sortDir={sortDir}
              onSort={handleSort}
              selectable
              selectedIds={selectedIds}
              allOnPageSelected={allOnPageSelected}
              onToggleAll={togglePageSelection}
              onToggleSelect={(id, checked) =>
                setSelectedIds((prev) =>
                  checked ? [...prev, id] : prev.filter((item) => item !== id)
                )
              }
              canManage={canManage}
            />
          )}
        </section>
      )}

      {/* =================================================================
          TAB 2: BROWSE FEED CATALOG (Unified Scalable Table Matching My Feeds)
      ================================================================== */}
      {activeTab === "catalog" && (
        <section aria-label="Preset feed catalog" className="space-y-3">
          {presetsQuery.isPending ? (
            <div className="h-36 rounded-2xl border border-border bg-muted/30 animate-pulse" />
          ) : presetsQuery.isError ? (
            <div role="alert" className="rounded-2xl border border-destructive/25 bg-destructive/5 p-5 space-y-2.5 text-xs">
              <p className="font-semibold text-destructive">Feed catalog could not be loaded</p>
              <p className="text-muted-foreground">{presetsQuery.error?.message || "Please retry."}</p>
              <Button size="sm" variant="outline" onClick={() => void presetsQuery.refetch()}>
                Retry
              </Button>
            </div>
          ) : filteredPresets.length === 0 ? (
            <div className="rounded-xl border border-border bg-card p-6 text-center text-xs text-muted-foreground">
              No catalog feeds match your current search or filter criteria.
            </div>
          ) : (
            <FeedsDataTable
              tableLabel="Browse feed catalog"
              rows={paginatedPresets.map((preset) => {
                const rowKey = `preset:${preset.preset_id}`;
                const linked = configByKey.get(`${preset.family}:${preset.endpoint}`);
                const isEnabled = linked ? linked.enabled : preset.enabled;
                const aiAllowed = linked
                  ? linked.ai_processing_authorized
                  : preset.ai_processing_authorized;
                return {
                  rowKey,
                  id: linked?.id,
                  name: preset.name,
                  endpoint: preset.endpoint,
                  attribution: preset.attribution,
                  family: preset.family,
                  category: categorizePreset(preset),
                  content_kind: preset.content_kind,
                  polling_minutes: linked?.polling_minutes ?? 60,
                  enabled: isEnabled,
                  configured: Boolean(linked || preset.configured),
                  host_approved: preset.host_approved,
                  ai_processing_authorized: Boolean(aiAllowed),
                  isToggling: pendingKey === rowKey,
                  isTesting: Boolean(linked?.id && pendingKey === `test:${linked.id}`),
                  testResult: linked?.id ? feedTestResults[linked.id] : undefined,
                  errorMessage: rowError?.key === rowKey ? rowError.message : undefined,
                  onManage: () => openPresetManage(preset),
                  onToggle: () => void togglePreset(preset),
                };
              })}
              totalCount={filteredPresets.length}
              page={catalogSafePage}
              totalPages={catalogTotalPages}
              onPageChange={setPage}
              sortCol={sortCol}
              sortDir={sortDir}
              onSort={handleSort}
              canManage={canManage}
            />
          )}
        </section>
      )}

      {/* =================================================================
          TAB 3: ADD CUSTOM FEED (Guided Form + Live Endpoint Test)
      ================================================================== */}
      {activeTab === "add" && canManage && (
        <section
          aria-label="Add custom feed"
          className="rounded-2xl border border-border bg-card p-5 max-w-2xl space-y-5"
        >
          <div>
            <h4 className="text-sm font-semibold text-foreground">Add Approved Custom Feed</h4>
            <p className="text-xs text-muted-foreground mt-0.5">
              Enter a public HTTPS RSS, Atom, or Discourse feed URL. PlaneByte validates host permissions, blocks private network endpoints, prevents duplicate URLs, and evaluates AI processing policy server-side.
            </p>
          </div>

          <form onSubmit={(e) => void saveAddForm(e)} className="space-y-4 text-xs">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1">
                <label htmlFor="add-feed-name" className="block font-medium text-foreground">
                  Feed name
                </label>
                <input
                  id="add-feed-name"
                  value={addForm.name}
                  maxLength={120}
                  onChange={(e) => setAddForm((f) => ({ ...f, name: e.target.value }))}
                  placeholder="e.g. FastAPI Releases"
                  className="w-full rounded-lg border border-border bg-card px-3 py-2 text-xs text-foreground"
                />
                {addErrors.name && (
                  <p role="alert" className="text-[11px] text-destructive">
                    {addErrors.name}
                  </p>
                )}
              </div>

              <div className="space-y-1">
                <label htmlFor="add-feed-family" className="block font-medium text-foreground">
                  Source type
                </label>
                <select
                  id="add-feed-family"
                  value={addForm.family}
                  onChange={(e) =>
                    setAddForm((f) => ({ ...f, family: e.target.value as FeedFamily }))
                  }
                  className="w-full rounded-lg border border-border bg-card px-3 py-2 text-xs text-foreground"
                >
                  <option value="rss">RSS / Atom Feed</option>
                  <option value="atom">Atom 1.0 Feed (Releases / Research)</option>
                  <option value="discourse">Approved Discourse (RSS/Atom)</option>
                </select>
              </div>
            </div>

            <div className="space-y-1">
              <label htmlFor="add-feed-endpoint" className="block font-medium text-foreground">
                HTTPS feed URL
              </label>
              <div className="flex flex-col sm:flex-row gap-2">
                <input
                  id="add-feed-endpoint"
                  type="url"
                  value={addForm.endpoint}
                  maxLength={1000}
                  onChange={(e) => {
                    setAddForm((f) => ({ ...f, endpoint: e.target.value }));
                    setAddTestResult(null);
                  }}
                  placeholder="https://github.com/org/repo/releases.atom"
                  className="flex-1 rounded-lg border border-border bg-card px-3 py-2 text-xs font-mono text-foreground"
                />
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  disabled={testingAdd}
                  onClick={() => void testAddUrl()}
                  className="h-9 text-xs gap-1.5 shrink-0"
                >
                  {testingAdd ? <Loader2 size={13} className="animate-spin" /> : <Wifi size={13} />}
                  {testingAdd ? "Testing…" : "Test Feed URL"}
                </Button>
              </div>
              {addErrors.endpoint && (
                <p role="alert" className="text-[11px] text-destructive">
                  {addErrors.endpoint}
                </p>
              )}
            </div>

            {addTestResult && (
              <div
                role="status"
                className={
                  "rounded-xl border p-3.5 space-y-2 " +
                  (addTestResult.ok
                    ? "border-emerald-500/25 bg-emerald-500/10 text-emerald-800 dark:text-emerald-200"
                    : "border-destructive/25 bg-destructive/5 text-destructive")
                }
              >
                <p className="font-semibold flex items-center gap-1.5">
                  {addTestResult.ok ? <CheckCircle2 size={14} /> : <AlertCircle size={14} />}
                  {addTestResult.ok
                    ? `Endpoint reachable (HTTP ${addTestResult.http_status})`
                    : addTestResult.error || "Feed test failed"}
                </p>
                {addTestResult.ok && (
                  <>
                    <p className="text-[11px] opacity-85">
                      Format: {addTestResult.feed_format || "RSS/Atom"} · {addTestResult.entry_count}{" "}
                      entries · {addTestResult.latency_ms} ms · Latest:{" "}
                      {formatTime(addTestResult.latest_entry_at)}
                    </p>
                    {addTestResult.sample_titles.length > 0 && (
                      <ul className="list-disc pl-4 text-[11px] opacity-90 space-y-0.5">
                        {addTestResult.sample_titles.map((t) => (
                          <li key={t} className="truncate">
                            {t}
                          </li>
                        ))}
                      </ul>
                    )}
                    {addTestResult.policy && (
                      <p className="text-[11px] font-medium pt-1 border-t border-emerald-500/20">
                        Server AI policy:{" "}
                        {addTestResult.policy.ai_processing_authorized
                          ? addTestResult.policy.ai_status
                          : `${addTestResult.policy.ai_status}${addTestResult.policy.reason ? ` — ${addTestResult.policy.reason}` : ""}`}
                      </p>
                    )}
                  </>
                )}
              </div>
            )}

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1">
                <label htmlFor="add-feed-policy" className="block font-medium text-foreground">
                  Permission / terms reference
                </label>
                <input
                  id="add-feed-policy"
                  value={addForm.policy_reference}
                  maxLength={1000}
                  onChange={(e) => setAddForm((f) => ({ ...f, policy_reference: e.target.value }))}
                  placeholder="Public feed terms URL or approval record"
                  className="w-full rounded-lg border border-border bg-card px-3 py-2 text-xs text-foreground"
                />
                {addErrors.policy_reference && (
                  <p role="alert" className="text-[11px] text-destructive">
                    {addErrors.policy_reference}
                  </p>
                )}
              </div>

              <div className="space-y-1">
                <label htmlFor="add-feed-attribution" className="block font-medium text-foreground">
                  Required publisher attribution
                </label>
                <input
                  id="add-feed-attribution"
                  value={addForm.attribution}
                  maxLength={300}
                  onChange={(e) => setAddForm((f) => ({ ...f, attribution: e.target.value }))}
                  placeholder="e.g. FastAPI (GitHub Releases Atom)"
                  className="w-full rounded-lg border border-border bg-card px-3 py-2 text-xs text-foreground"
                />
                {addErrors.attribution && (
                  <p role="alert" className="text-[11px] text-destructive">
                    {addErrors.attribution}
                  </p>
                )}
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1">
                <label htmlFor="add-feed-polling" className="block font-medium text-foreground">
                  Polling interval (minutes)
                </label>
                <input
                  id="add-feed-polling"
                  type="number"
                  min={60}
                  max={1440}
                  value={addForm.polling_minutes}
                  onChange={(e) =>
                    setAddForm((f) => ({ ...f, polling_minutes: Number(e.target.value) }))
                  }
                  className="w-full rounded-lg border border-border bg-card px-3 py-2 text-xs text-foreground"
                />
                {addErrors.polling_minutes && (
                  <p role="alert" className="text-[11px] text-destructive">
                    {addErrors.polling_minutes}
                  </p>
                )}
              </div>

              <div className="space-y-1">
                <label htmlFor="add-feed-retention" className="block font-medium text-foreground">
                  Retention (days)
                </label>
                <input
                  id="add-feed-retention"
                  type="number"
                  min={1}
                  max={30}
                  value={addForm.retention_days}
                  onChange={(e) =>
                    setAddForm((f) => ({ ...f, retention_days: Number(e.target.value) }))
                  }
                  className="w-full rounded-lg border border-border bg-card px-3 py-2 text-xs text-foreground"
                />
                {addErrors.retention_days && (
                  <p role="alert" className="text-[11px] text-destructive">
                    {addErrors.retention_days}
                  </p>
                )}
              </div>
            </div>

            {addServerError && (
              <div
                role="alert"
                className="rounded-xl border border-destructive/25 bg-destructive/5 px-3.5 py-2.5 text-xs text-destructive"
              >
                {addServerError}
              </div>
            )}

            <div className="flex flex-wrap items-center gap-2 pt-2">
              <Button type="submit" size="sm" disabled={savingAdd}>
                {savingAdd ? "Saving…" : "Save custom feed"}
              </Button>
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => setSelectedTab(configs.length > 0 ? "my_feeds" : "catalog")}
              >
                Cancel
              </Button>
            </div>
          </form>
        </section>
      )}

      {/* =================================================================
          SELF-CONTAINED SLIDE-OVER FEED MANAGE DRAWER
      ================================================================== */}
      <SlideOverDrawer
        open={drawerOpen}
        onClose={() => {
          setDrawerOpen(false);
          setConfirmDelete(false);
        }}
        title={drawerForm.id ? `Manage ${drawerForm.name}` : "Configure feed"}
        subtitle="Test live endpoint health, adjust polling & retention, and review server-enforced AI processing permissions."
        icon={
          <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-border bg-muted/30">
            <ProviderLogo provider={resolveLogoHint(drawerForm)} size={18} />
          </div>
        }
      >
        <form onSubmit={(e) => void saveDrawerForm(e)} className="space-y-5 text-xs">
          {/* Live Endpoint Test Banner */}
          <div className="rounded-xl border border-border bg-muted/20 p-4 space-y-3">
            <div className="flex items-center justify-between gap-2">
              <div>
                <p className="font-semibold text-foreground">Live Endpoint Verification</p>
                <p className="text-[11px] text-muted-foreground">
                  Checks HTTPS reachability, RSS/Atom parsing, latency, and cache headers.
                </p>
              </div>
              <Button
                type="button"
                size="sm"
                variant="outline"
                disabled={testingDrawer}
                onClick={() => void testDrawerEndpoint()}
                className="h-8 text-xs gap-1.5 shrink-0"
              >
                {testingDrawer ? (
                  <Loader2 size={13} className="animate-spin" />
                ) : (
                  <Wifi size={13} />
                )}
                {testingDrawer ? "Testing…" : "Test Endpoint"}
              </Button>
            </div>

            {drawerTestResult && (
              <div
                role="status"
                className={
                  "rounded-lg border p-3 space-y-1.5 " +
                  (drawerTestResult.ok
                    ? "border-emerald-500/25 bg-emerald-500/10 text-emerald-800 dark:text-emerald-200"
                    : "border-destructive/25 bg-destructive/5 text-destructive")
                }
              >
                <p className="font-semibold">
                  {drawerTestResult.ok
                    ? `Endpoint healthy (HTTP ${drawerTestResult.http_status})`
                    : drawerTestResult.error || "Feed test failed"}
                </p>
                {drawerTestResult.ok && (
                  <>
                    <p className="text-[11px] opacity-85">
                      HTTP {drawerTestResult.http_status} · {drawerTestResult.feed_format || "RSS/Atom"} ·{" "}
                      {drawerTestResult.entry_count} entries · {drawerTestResult.latency_ms} ms
                    </p>
                    <p className="text-[11px] opacity-85">
                      Latest entry: {formatTime(drawerTestResult.latest_entry_at)} · ETag:{" "}
                      {drawerTestResult.etag ? "Yes" : "No"} · Last-Modified:{" "}
                      {drawerTestResult.last_modified ? "Yes" : "No"}
                    </p>
                    {drawerTestResult.sample_titles.length > 0 && (
                      <ul className="list-disc pl-4 text-[11px] opacity-90 space-y-0.5 pt-1">
                        {drawerTestResult.sample_titles.map((title) => (
                          <li key={title} className="truncate">
                            {title}
                          </li>
                        ))}
                      </ul>
                    )}
                  </>
                )}
              </div>
            )}
          </div>

          {/* Feed Details */}
          <div className="space-y-3">
            <h4 className="font-semibold text-sm text-foreground border-b border-border pb-1.5">
              Feed configuration
            </h4>

            <div className="space-y-1">
              <label htmlFor="drawer-feed-name" className="block font-medium text-foreground">
                Display name
              </label>
              <input
                id="drawer-feed-name"
                value={drawerForm.name}
                maxLength={120}
                onChange={(e) => setDrawerForm((f) => ({ ...f, name: e.target.value }))}
                className="w-full rounded-lg border border-border bg-card px-3 py-2 text-xs text-foreground"
              />
              {drawerErrors.name && (
                <p role="alert" className="text-[11px] text-destructive">
                  {drawerErrors.name}
                </p>
              )}
            </div>

            <div className="space-y-1">
              <div className="flex items-center justify-between gap-2">
                <label htmlFor="drawer-feed-endpoint" className="font-medium text-foreground">
                  HTTPS feed URL
                </label>
                {drawerIsPreset && (
                  <span className="inline-flex items-center gap-1 text-[10px] font-medium text-muted-foreground">
                    <Lock size={10} /> Curated preset URL
                  </span>
                )}
              </div>
              <input
                id="drawer-feed-endpoint"
                type="url"
                value={drawerForm.endpoint}
                readOnly={drawerIsPreset}
                onChange={(e) => setDrawerForm((f) => ({ ...f, endpoint: e.target.value }))}
                className={
                  "w-full rounded-lg border border-border px-3 py-2 text-xs font-mono " +
                  (drawerIsPreset
                    ? "bg-muted/40 text-muted-foreground cursor-not-allowed"
                    : "bg-card text-foreground")
                }
              />
              {drawerErrors.endpoint && (
                <p role="alert" className="text-[11px] text-destructive">
                  {drawerErrors.endpoint}
                </p>
              )}
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1">
                <label htmlFor="drawer-feed-polling" className="block font-medium text-foreground">
                  Polling interval (minutes)
                </label>
                <input
                  id="drawer-feed-polling"
                  type="number"
                  min={60}
                  max={1440}
                  value={drawerForm.polling_minutes}
                  onChange={(e) =>
                    setDrawerForm((f) => ({ ...f, polling_minutes: Number(e.target.value) }))
                  }
                  className="w-full rounded-lg border border-border bg-card px-3 py-2 text-xs text-foreground"
                />
                {drawerErrors.polling_minutes && (
                  <p role="alert" className="text-[11px] text-destructive">
                    {drawerErrors.polling_minutes}
                  </p>
                )}
              </div>

              <div className="space-y-1">
                <label htmlFor="drawer-feed-retention" className="block font-medium text-foreground">
                  Retention (days)
                </label>
                <input
                  id="drawer-feed-retention"
                  type="number"
                  min={1}
                  max={30}
                  value={drawerForm.retention_days}
                  onChange={(e) =>
                    setDrawerForm((f) => ({ ...f, retention_days: Number(e.target.value) }))
                  }
                  className="w-full rounded-lg border border-border bg-card px-3 py-2 text-xs text-foreground"
                />
                {drawerErrors.retention_days && (
                  <p role="alert" className="text-[11px] text-destructive">
                    {drawerErrors.retention_days}
                  </p>
                )}
              </div>
            </div>

            <label className="flex items-center gap-2.5 rounded-xl border border-border bg-muted/15 px-3 py-2.5 cursor-pointer">
              <input
                type="checkbox"
                checked={drawerForm.enabled}
                onChange={(e) => setDrawerForm((f) => ({ ...f, enabled: e.target.checked }))}
                className="accent-primary"
              />
              <span className="font-medium text-foreground">
                Enabled for Discovery searches &amp; Scheduled Monitors
              </span>
            </label>
          </div>

          {/* Usage Authorization & Server-Enforced AI Policy */}
          <div className="space-y-3">
            <h4 className="font-semibold text-sm text-foreground border-b border-border pb-1.5">
              Policy &amp; AI Processing
            </h4>

            <div className="rounded-xl border border-border bg-muted/25 px-3.5 py-3 space-y-1.5">
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium text-foreground">AI processing authorization</span>
                <span
                  className={
                    "rounded-full border px-2 py-0.5 text-[10px] font-semibold " +
                    (drawerForm.ai_processing_authorized
                      ? "border-emerald-500/25 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
                      : "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300")
                  }
                >
                  {drawerForm.ai_processing_authorized ? "Authorized" : "Restricted"}
                </span>
              </div>
              <p className="text-[11px] text-muted-foreground leading-relaxed">
                {drawerForm.policy?.reason ||
                  (drawerForm.ai_processing_authorized
                    ? "Verified feed terms allow automated AI summarization and scoring."
                    : "Automated LLM processing is restricted until publisher terms are explicitly approved. Public discovery and manual review remain active.")}
              </p>
            </div>

            <div className="space-y-1">
              <label htmlFor="drawer-feed-policy" className="block font-medium text-foreground">
                Permission / terms reference
              </label>
              <input
                id="drawer-feed-policy"
                value={drawerForm.policy_reference}
                maxLength={1000}
                onChange={(e) => setDrawerForm((f) => ({ ...f, policy_reference: e.target.value }))}
                className="w-full rounded-lg border border-border bg-card px-3 py-2 text-xs text-foreground"
              />
              {drawerErrors.policy_reference && (
                <p role="alert" className="text-[11px] text-destructive">
                  {drawerErrors.policy_reference}
                </p>
              )}
            </div>

            <div className="space-y-1">
              <label htmlFor="drawer-feed-attribution" className="block font-medium text-foreground">
                Required publisher attribution
              </label>
              <input
                id="drawer-feed-attribution"
                value={drawerForm.attribution}
                maxLength={300}
                onChange={(e) => setDrawerForm((f) => ({ ...f, attribution: e.target.value }))}
                className="w-full rounded-lg border border-border bg-card px-3 py-2 text-xs text-foreground"
              />
              {drawerErrors.attribution && (
                <p role="alert" className="text-[11px] text-destructive">
                  {drawerErrors.attribution}
                </p>
              )}
            </div>
          </div>

          {drawerServerError && (
            <div
              role="alert"
              className="rounded-xl border border-destructive/25 bg-destructive/5 px-3.5 py-2.5 text-xs text-destructive"
            >
              {drawerServerError}
            </div>
          )}

          {/* Save & Delete Actions */}
          <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border pt-4">
            <div className="flex items-center gap-2">
              <Button type="submit" size="sm" disabled={savingDrawer}>
                {savingDrawer ? "Saving…" : "Save changes"}
              </Button>
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => setDrawerOpen(false)}
              >
                Cancel
              </Button>
            </div>

            {drawerForm.id && !drawerIsPreset && (
              <div>
                {!confirmDelete ? (
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    onClick={() => setConfirmDelete(true)}
                    className="h-8 text-xs text-destructive hover:text-destructive gap-1"
                  >
                    <Trash2 size={13} /> Delete feed
                  </Button>
                ) : (
                  <div className="flex items-center gap-1.5">
                    <Button
                      type="button"
                      size="sm"
                      variant="destructive"
                      disabled={savingDrawer}
                      onClick={() => void deleteDrawerFeed()}
                      className="h-8 text-xs"
                    >
                      Confirm delete
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      onClick={() => setConfirmDelete(false)}
                      className="h-8 text-xs"
                    >
                      Keep
                    </Button>
                  </div>
                )}
              </div>
            )}
          </div>
        </form>
      </SlideOverDrawer>
    </div>
  );
}
