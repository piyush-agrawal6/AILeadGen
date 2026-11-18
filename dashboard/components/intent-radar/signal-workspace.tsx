"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ArrowRight,
  ArrowUpRight,
  Bookmark,
  CheckCheck,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Columns3,
  ExternalLink,
  Eye,
  Filter,
  LayoutGrid,
  List,
  Loader2,
  MoreHorizontal,
  RotateCcw,
  Search,
  Target,
  X,
  XCircle,
} from "lucide-react";
import {
  INTENT_CATEGORIES,
  type IntentMonitor,
  type IntentPage,
  type IntentPreferences,
  type IntentSignal,
  type SignalViewKey,
} from "@/lib/intent-radar";
import { Menu, MenuContent } from "@/components/ui/menu";
import { useRadarCapabilities, useRadarMutation, useRadarRead } from "./provider";
import { EmptyState, ErrorState, LoadingSkeleton, PageHeading } from "./ui";
import { SignalCard, SignalScore } from "./signals";
import { ProviderLogo } from "./provider-logo";
import { SignalQuickDrawer } from "./signals/SignalQuickDrawer";
import { CreateOpportunityModal } from "./signals/CreateOpportunityModal";
import {
  buyingIntentDisplay,
  clearSignalsReturnContext,
  formatObservedDate,
  readSignalsReturnContext,
  saveSignalsReturnContext,
  statusPillClasses,
} from "./signals/signals-context";

type SortKey = "newest" | "oldest" | "score" | "score_asc" | "title";
type DateRangePreset = "" | "7d" | "30d" | "90d";

interface SignalFilterState {
  view: SignalViewKey;
  search: string;
  source: string;
  category: string;
  status: string;
  min_score: number;
  buying_intent: string;
  icp_fit: string;
  monitor_id: string;
  discovery_id: string;
  saved: string;
  range: DateRangePreset;
  from_date: string;
  to_date: string;
  sort: SortKey;
}

const DEFAULT_FILTERS: SignalFilterState = {
  view: "all",
  search: "",
  source: "",
  category: "",
  status: "",
  min_score: 0,
  buying_intent: "",
  icp_fit: "",
  monitor_id: "",
  discovery_id: "",
  saved: "",
  range: "",
  from_date: "",
  to_date: "",
  sort: "newest",
};

const VIEW_TABS: { key: SignalViewKey; label: string; hint?: string }[] = [
  { key: "all", label: "All Signals" },
  { key: "needs_review", label: "Needs Review" },
  {
    key: "high_intent",
    label: "High Intent",
    hint: "Signals with explicit commercial-intent evidence (excludes general chatter & technical releases)",
  },
  { key: "saved", label: "Saved" },
  { key: "qualified", label: "Qualified" },
  { key: "dismissed", label: "Dismissed" },
];

const PAGE_SIZE = 25;

function rangeToFromDate(range: DateRangePreset): string {
  if (!range) return "";
  const days = range === "7d" ? 7 : range === "30d" ? 30 : 90;
  return new Date(Date.now() - days * 86_400_000).toISOString().slice(0, 10);
}

export function SignalsWorkspace() {
  const router = useRouter();
  const params = useSearchParams();

  const [filters, setFilters] = useState<SignalFilterState>(() => {
    const rawView = (params.get("view") || "all") as SignalViewKey;
    const validView: SignalViewKey = VIEW_TABS.some((t) => t.key === rawView) ? rawView : "all";
    const rawSort = (params.get("sort") || "newest") as SortKey;
    const validSort: SortKey = ["newest", "oldest", "score", "score_asc", "title"].includes(rawSort)
      ? rawSort
      : "newest";
    const rawRange = (params.get("range") || "") as DateRangePreset;
    const validRange: DateRangePreset = ["", "7d", "30d", "90d"].includes(rawRange) ? rawRange : "";
    return {
      ...DEFAULT_FILTERS,
      view: validView,
      search: params.get("search") || params.get("q") || "",
      source: params.get("source") || "",
      category: params.get("category") || "",
      status: params.get("status") || "",
      min_score: Math.min(100, Math.max(0, Number(params.get("min_score") || 0) || 0)),
      buying_intent: params.get("buying_intent") || "",
      icp_fit: params.get("icp_fit") || "",
      monitor_id: params.get("monitor_id") || "",
      discovery_id: params.get("discovery_id") || "",
      saved: params.get("saved") || "",
      range: validRange,
      from_date: params.get("from_date") || "",
      to_date: params.get("to_date") || "",
      sort: validSort,
    };
  });

  const [searchInput, setSearchInput] = useState(filters.search);
  const [page, setPage] = useState<number>(() => Math.max(1, Number(params.get("page") || "1") || 1));
  const [displayMode, setDisplayMode] = useState<"table" | "cards" | null>(() => {
    if (typeof window === "undefined") return null;
    try {
      const saved = window.localStorage.getItem("planebyte:signals-view-mode");
      return saved === "table" || saved === "cards" ? saved : null;
    } catch {
      return null;
    }
  });
  const [selected, setSelected] = useState<string[]>([]);
  const [filterOpen, setFilterOpen] = useState(false);
  const [columnsOpen, setColumnsOpen] = useState(false);
  const [visibleCols, setVisibleCols] = useState(() => {
    const fallback = { category: true, buyingIntent: true, observed: true };
    if (typeof window === "undefined") return fallback;
    try {
      const raw = window.localStorage.getItem("planebyte:signals-visible-cols");
      if (!raw) return fallback;
      const parsed = JSON.parse(raw) as Partial<typeof fallback>;
      return {
        category: parsed.category ?? true,
        buyingIntent: parsed.buyingIntent ?? true,
        observed: parsed.observed ?? true,
      };
    } catch {
      return fallback;
    }
  });
  const [openedId, setOpenedId] = useState("");
  const [openedSnapshot, setOpenedSnapshot] = useState<IntentSignal | null>(null);
  const [opportunityTarget, setOpportunityTarget] = useState<IntentSignal | null>(null);
  const [bulkConfirm, setBulkConfirm] = useState<null | "dismiss" | "qualify">(null);
  const [bulkBusyAction, setBulkBusyAction] = useState<string | null>(null);
  const [notice, setNotice] = useState<{
    message: string;
    isError?: boolean;
    undo?: { signalId: string; revision: number; previousStatus: string };
  } | null>(null);

  const filterRef = useRef<HTMLDivElement>(null);
  const columnsRef = useRef<HTMLDivElement>(null);

  // Debounce search input cleanly
  useEffect(() => {
    const id = window.setTimeout(() => {
      setFilters((prev) => {
        if (prev.search === searchInput) return prev;
        setPage(1);
        setSelected([]);
        return { ...prev, search: searchInput };
      });
    }, 250);
    return () => window.clearTimeout(id);
  }, [searchInput]);

  // Close popovers on click outside / Escape
  useEffect(() => {
    if (!filterOpen && !columnsOpen) return;
    function onDocClick(e: MouseEvent) {
      if (filterOpen && filterRef.current && !filterRef.current.contains(e.target as Node)) {
        setFilterOpen(false);
      }
      if (columnsOpen && columnsRef.current && !columnsRef.current.contains(e.target as Node)) {
        setColumnsOpen(false);
      }
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setFilterOpen(false);
        setColumnsOpen(false);
      }
    }
    document.addEventListener("mousedown", onDocClick);
    window.addEventListener("keydown", onKey, true);
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      window.removeEventListener("keydown", onKey, true);
    };
  }, [filterOpen, columnsOpen]);

  // Sync URL query params without pushing noisy history entries
  const currentUrl = useMemo(() => {
    const sp = new URLSearchParams();
    if (filters.view && filters.view !== "all") sp.set("view", filters.view);
    if (filters.search) sp.set("search", filters.search);
    if (filters.source) sp.set("source", filters.source);
    if (filters.category) sp.set("category", filters.category);
    if (filters.status) sp.set("status", filters.status);
    if (filters.min_score > 0) sp.set("min_score", String(filters.min_score));
    if (filters.buying_intent) sp.set("buying_intent", filters.buying_intent);
    if (filters.icp_fit) sp.set("icp_fit", filters.icp_fit);
    if (filters.monitor_id) sp.set("monitor_id", filters.monitor_id);
    if (filters.discovery_id) sp.set("discovery_id", filters.discovery_id);
    if (filters.saved) sp.set("saved", filters.saved);
    if (filters.range) sp.set("range", filters.range);
    if (filters.from_date) sp.set("from_date", filters.from_date);
    if (filters.to_date) sp.set("to_date", filters.to_date);
    if (filters.sort && filters.sort !== "newest") sp.set("sort", filters.sort);
    if (page > 1) sp.set("page", String(page));
    const qs = sp.toString();
    return qs ? `/intent-radar/signals?${qs}` : "/intent-radar/signals";
  }, [filters, page]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (window.location.pathname === "/intent-radar/signals") {
      window.history.replaceState(null, "", currentUrl);
    }
  }, [currentUrl]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      window.localStorage.setItem("planebyte:signals-visible-cols", JSON.stringify(visibleCols));
    } catch {
      // ignore
    }
  }, [visibleCols]);

  useEffect(() => {
    if (typeof window === "undefined" || !displayMode) return;
    try {
      window.localStorage.setItem("planebyte:signals-view-mode", displayMode);
    } catch {
      // ignore
    }
  }, [displayMode]);

  const preferences = useRadarRead<IntentPreferences>("/settings");
  const monitors = useRadarRead<IntentPage<IntentMonitor>>("/monitors?page_size=100");
  const access = useRadarCapabilities();
  const mutation = useRadarMutation();

  const apiQueryString = useMemo(() => {
    const args = new URLSearchParams();
    if (filters.view && filters.view !== "all") args.set("view", filters.view);
    if (filters.search) args.set("search", filters.search);
    if (filters.source) args.set("source", filters.source);
    if (filters.category) args.set("category", filters.category);
    if (filters.status) args.set("status", filters.status);
    if (filters.min_score > 0) args.set("min_score", String(filters.min_score));
    if (filters.buying_intent) args.set("buying_intent", filters.buying_intent);
    if (filters.icp_fit) args.set("icp_fit", filters.icp_fit);
    if (filters.monitor_id) args.set("monitor_id", filters.monitor_id);
    if (filters.discovery_id) args.set("discovery_id", filters.discovery_id);
    if (filters.saved) args.set("saved", filters.saved);
    const effectiveFrom = filters.from_date || rangeToFromDate(filters.range);
    if (effectiveFrom) args.set("from_date", effectiveFrom);
    if (filters.to_date) args.set("to_date", filters.to_date);
    args.set("sort", filters.sort);
    args.set("page", String(page));
    args.set("page_size", String(PAGE_SIZE));
    return args.toString();
  }, [filters, page]);

  const query = useRadarRead<IntentPage<IntentSignal>>(`/signals?${apiQueryString}`);
  const rows = useMemo(() => query.data?.items || [], [query.data?.items]);
  const totalCount = query.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(totalCount / PAGE_SIZE));
  const viewCounts = query.data?.view_counts;
  const display = displayMode || preferences.data?.default_view || "table";
  const canWrite = !!access.data?.can_write;

  // Restore scroll AFTER table data actually renders (not during loading skeleton)
  const scrollRestoredRef = useRef(false);
  useEffect(() => {
    if (scrollRestoredRef.current || !query.data) return;
    scrollRestoredRef.current = true;
    const saved = readSignalsReturnContext();
    if (saved && saved.scrollY > 0) {
      const id = window.requestAnimationFrame(() => {
        window.scrollTo({ top: saved.scrollY, behavior: "auto" });
        clearSignalsReturnContext();
      });
      return () => window.cancelAnimationFrame(id);
    }
  }, [query.data]);

  // Clamp page cleanly if bulk actions or status transitions empty the last page
  useEffect(() => {
    if (query.data && page > totalPages) {
      setPage(totalPages);
    }
  }, [query.data, page, totalPages]);

  const liveOpenedSignal = useMemo(
    () => (openedId ? rows.find((r) => r.id === openedId) || null : null),
    [openedId, rows]
  );

  useEffect(() => {
    if (!openedId) {
      setOpenedSnapshot(null);
    } else if (liveOpenedSignal) {
      setOpenedSnapshot(liveOpenedSignal);
    }
  }, [openedId, liveOpenedSignal]);

  const openedSignal = liveOpenedSignal || (openedId && openedSnapshot?.id === openedId ? openedSnapshot : null);
  const openedIndex = openedId ? rows.findIndex((r) => r.id === openedId) : -1;

  function updateFilters(patch: Partial<SignalFilterState>) {
    setFilters((prev) => ({ ...prev, ...patch }));
    setPage(1);
    setSelected([]);
    setBulkConfirm(null);
  }

  function resetAllFilters() {
    setSearchInput("");
    setFilters({ ...DEFAULT_FILTERS, view: filters.view, sort: filters.sort });
    setPage(1);
    setSelected([]);
    setFilterOpen(false);
  }

  function persistReturnContext() {
    saveSignalsReturnContext({
      returnUrl: currentUrl,
      scrollY: typeof window !== "undefined" ? window.scrollY : 0,
      orderedIds: rows.map((r) => r.id),
    });
  }

  function openFullDetails(signalId: string) {
    persistReturnContext();
    router.push(`/intent-radar/signals/${signalId}`);
  }

  // Active secondary filter chips (excluding view & sort & search)
  const activeFilterChips = useMemo(() => {
    const chips: { key: string; label: string; clear: () => void }[] = [];
    if (filters.source) {
      chips.push({ key: "source", label: `Source: ${filters.source}`, clear: () => updateFilters({ source: "" }) });
    }
    if (filters.category) {
      chips.push({ key: "category", label: `Intent: ${filters.category}`, clear: () => updateFilters({ category: "" }) });
    }
    if (filters.status) {
      chips.push({ key: "status", label: `Status: ${filters.status}`, clear: () => updateFilters({ status: "" }) });
    }
    if (filters.min_score > 0) {
      chips.push({
        key: "min_score",
        label: `Relevance: ${filters.min_score}+`,
        clear: () => updateFilters({ min_score: 0 }),
      });
    }
    if (filters.buying_intent) {
      const biLabels: Record<string, string> = {
        explicit: "Explicit commercial intent",
        possible: "Possible commercial intent",
        none: "No commercial intent",
        insufficient: "Insufficient evidence",
        unassessed: "Not assessed",
      };
      chips.push({
        key: "buying_intent",
        label: `Buying intent: ${biLabels[filters.buying_intent] || filters.buying_intent}`,
        clear: () => updateFilters({ buying_intent: "" }),
      });
    }
    if (filters.icp_fit) {
      chips.push({ key: "icp_fit", label: `ICP fit: ${filters.icp_fit}`, clear: () => updateFilters({ icp_fit: "" }) });
    }
    if (filters.monitor_id) {
      const name = monitors.data?.items.find((m) => m.id === filters.monitor_id)?.name || "Selected monitor";
      chips.push({ key: "monitor_id", label: `Monitor: ${name}`, clear: () => updateFilters({ monitor_id: "" }) });
    }
    if (filters.discovery_id) {
      chips.push({
        key: "discovery_id",
        label: `Discovery run`,
        clear: () => updateFilters({ discovery_id: "" }),
      });
    }
    if (filters.saved) {
      chips.push({
        key: "saved",
        label: filters.saved === "saved" ? "Bookmarked only" : "Not bookmarked",
        clear: () => updateFilters({ saved: "" }),
      });
    }
    if (filters.range) {
      chips.push({
        key: "range",
        label: `Last ${filters.range.replace("d", " days")}`,
        clear: () => updateFilters({ range: "" }),
      });
    }
    if (filters.from_date) {
      chips.push({ key: "from_date", label: `From: ${filters.from_date}`, clear: () => updateFilters({ from_date: "" }) });
    }
    if (filters.to_date) {
      chips.push({ key: "to_date", label: `Until: ${filters.to_date}`, clear: () => updateFilters({ to_date: "" }) });
    }
    return chips;
  }, [filters, monitors.data?.items]);

  const activeFilterCount = activeFilterChips.length;
  const hasAnyFilterOrSearch = activeFilterCount > 0 || Boolean(filters.search) || filters.view !== "all";
  const allVisibleSelected = rows.length > 0 && rows.every((r) => selected.includes(r.id));

  async function runQuickStatus(signal: IntentSignal, nextStatus: string) {
    if (!canWrite || mutation.isPending) return;
    const prevStatus = signal.status;
    try {
      const updated = (await mutation.mutateAsync({
        path: `/signals/${signal.id}`,
        method: "PATCH",
        body: { revision: signal.revision, status: nextStatus },
      })) as IntentSignal | undefined;
      const nextRev = typeof updated?.revision === "number" ? updated.revision : signal.revision + 1;
      if (openedId === signal.id && updated) {
        setOpenedSnapshot(updated);
      }
      setNotice({
        message: `Marked “${signal.title.slice(0, 48)}${signal.title.length > 48 ? "…" : ""}” as ${nextStatus}.`,
        undo: { signalId: signal.id, revision: nextRev, previousStatus: prevStatus },
      });
    } catch (e) {
      setNotice({ message: (e as Error).message || "Could not update signal.", isError: true });
    }
  }

  async function runQuickSave(signal: IntentSignal) {
    if (!canWrite || mutation.isPending) return;
    try {
      const updated = (await mutation.mutateAsync({
        path: `/saved/${signal.id}`,
        method: signal.saved ? "DELETE" : "POST",
      })) as IntentSignal | undefined;
      if (openedId === signal.id && updated) {
        setOpenedSnapshot(updated);
      }
      setNotice({
        message: signal.saved ? "Removed signal from Saved bookmarks." : "Saved signal to bookmarks (review status preserved).",
      });
    } catch (e) {
      setNotice({ message: (e as Error).message || "Could not update bookmark.", isError: true });
    }
  }

  async function runBulkAction(action: "save" | "unsave" | "review" | "qualify" | "dismiss" | "opportunity") {
    if (!canWrite || selected.length === 0 || mutation.isPending) return;
    setBulkConfirm(null);
    setBulkBusyAction(action);
    try {
      const res = (await mutation.mutateAsync({
        path: "/signals/actions",
        body: { ids: selected, action },
      })) as {
        updated?: number;
        already_existed?: number;
        skipped?: { id: string; title?: string; reason: string }[];
      };
      const updated = res?.updated ?? 0;
      const existed = res?.already_existed ?? 0;
      const skipped = res?.skipped || [];
      setSelected([]);
      const actionVerb: Record<string, string> = {
        save: "saved",
        unsave: "removed from saved bookmarks",
        review: "marked Reviewed",
        qualify: "marked Qualified",
        dismiss: "dismissed",
        opportunity: "promoted to Opportunities",
      };
      const parts: string[] = [];
      if (updated > 0) parts.push(`${updated} signal${updated === 1 ? "" : "s"} ${actionVerb[action]}`);
      if (existed > 0) parts.push(`${existed} already linked to an Opportunity`);
      if (skipped.length > 0) {
        const sampleReason = skipped[0]?.reason ? ` (${skipped[0].reason})` : "";
        parts.push(`${skipped.length} skipped${sampleReason}`);
      }
      setNotice({
        message: parts.length ? `${parts.join("; ")}.` : "No changes were required for the selected signals.",
        isError: updated === 0 && existed === 0 && skipped.length > 0,
      });
    } catch (e) {
      setNotice({ message: (e as Error).message || "Bulk action failed.", isError: true });
    } finally {
      setBulkBusyAction(null);
    }
  }

  async function handleUndo() {
    if (!notice?.undo || mutation.isPending) return;
    const { signalId, revision, previousStatus } = notice.undo;
    setNotice(null);
    try {
      await mutation.mutateAsync({
        path: `/signals/${signalId}`,
        method: "PATCH",
        body: { revision, status: previousStatus },
      });
    } catch (e) {
      setNotice({ message: (e as Error).message || "Could not undo — reload to sync latest signal status.", isError: true });
    }
  }

  return (
    <div className="ir-page space-y-5">
      <PageHeading
        title="Intent Signals"
        description="Triage public conversations, evaluate commercial intent with evidence, and promote qualified signals into opportunities."
        actions={
          <Link
            className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-primary px-4 text-xs font-semibold text-primary-foreground hover:opacity-90"
            href="/intent-radar/discover"
          >
            <Search size={14} />
            Discover Intent
          </Link>
        }
      />

      {/* Saved View Tabs */}
      <div
        role="tablist"
        aria-label="Signal views"
        className="flex items-center gap-1 overflow-x-auto border-b border-border pb-px"
      >
        {VIEW_TABS.map((tab) => {
          const active = filters.view === tab.key;
          const count = viewCounts ? viewCounts[tab.key] : undefined;
          return (
              <button
              key={tab.key}
              type="button"
              role="tab"
              aria-selected={active}
              title={tab.hint}
              onClick={() => updateFilters({ view: tab.key })}
              style={{
                border: "none",
                borderBottom: active ? "2px solid var(--primary)" : "2px solid transparent",
                borderRadius: 0,
                background: "transparent",
                boxShadow: "none",
              }}
              className={
                "inline-flex items-center gap-1.5 whitespace-nowrap px-3 py-2.5 text-xs font-medium transition-colors cursor-pointer " +
                (active
                  ? "text-primary font-semibold"
                  : "text-muted-foreground hover:text-foreground")
              }
            >
              <span>{tab.label}</span>
              {typeof count === "number" && (
                <span
                  className={
                    "rounded-full px-1.5 py-0.5 text-[10px] font-semibold tabular-nums " +
                    (active ? "bg-primary/12 text-primary" : "bg-muted text-muted-foreground")
                  }
                >
                  {count.toLocaleString()}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Compact Single-Row Toolbar */}
      <div className="flex flex-wrap items-center gap-2.5">
        {/* Search */}
        <div className="relative flex-1 min-w-[220px] max-w-md">
          <Search
            size={14}
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
            aria-hidden="true"
          />
          <input
            type="search"
            aria-label="Search signals"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search titles, excerpts, sources…"
            style={{ paddingLeft: "2.25rem", paddingRight: searchInput ? "2rem" : undefined }}
            className="h-9 w-full rounded-lg border border-border bg-card text-xs text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none"
          />
          {searchInput && (
            <button
              type="button"
              aria-label="Clear search"
              onClick={() => setSearchInput("")}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground cursor-pointer"
            >
              <X size={13} />
            </button>
          )}
        </div>

        {/* Filters Popover */}
        <div className="relative" ref={filterRef}>
          <button
            type="button"
            aria-expanded={filterOpen}
            aria-haspopup="dialog"
            onClick={() => {
              setFilterOpen((v) => !v);
              setColumnsOpen(false);
            }}
            className={
              "inline-flex h-9 items-center gap-1.5 rounded-lg border px-3 text-xs font-medium transition-colors cursor-pointer " +
              (activeFilterCount > 0 || filterOpen
                ? "border-primary bg-primary/10 text-primary"
                : "border-border bg-card text-foreground hover:bg-muted/50")
            }
          >
            <Filter size={13} />
            <span>Filters</span>
            {activeFilterCount > 0 && (
              <span className="inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-1 text-[10px] font-semibold text-primary-foreground">
                {activeFilterCount}
              </span>
            )}
          </button>

          {filterOpen && (
            <div
              role="dialog"
              aria-label="Filter signals"
              className="absolute left-0 sm:left-auto sm:right-0 z-40 mt-2 w-[310px] sm:w-[440px] rounded-2xl border border-border bg-card p-4 shadow-xl space-y-3.5"
            >
              <div className="flex items-center justify-between border-b border-border/70 pb-2.5">
                <span className="text-xs font-semibold text-foreground">Filter signals</span>
                <button
                  type="button"
                  onClick={resetAllFilters}
                  className="text-[11px] font-medium text-primary hover:underline cursor-pointer"
                >
                  Clear all
                </button>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block space-y-1">
                  <span className="text-[11px] font-medium text-muted-foreground">Source</span>
                  <select
                    aria-label="Filter by source"
                    value={filters.source}
                    onChange={(e) => updateFilters({ source: e.target.value })}
                    className="h-8 w-full rounded-lg border border-border bg-background px-2.5 text-xs text-foreground"
                  >
                    <option value="">All sources</option>
                    {(access.data?.sources || []).map((s) => (
                      <option key={s.name} value={s.name}>
                        {s.name}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="block space-y-1">
                  <span className="text-[11px] font-medium text-muted-foreground">Intent category</span>
                  <select
                    aria-label="Filter by intent category"
                    value={filters.category}
                    onChange={(e) => updateFilters({ category: e.target.value })}
                    className="h-8 w-full rounded-lg border border-border bg-background px-2.5 text-xs text-foreground"
                  >
                    <option value="">All categories</option>
                    {INTENT_CATEGORIES.map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="block space-y-1">
                  <span className="text-[11px] font-medium text-muted-foreground">Review status</span>
                  <select
                    aria-label="Filter by review status"
                    value={filters.status}
                    onChange={(e) => updateFilters({ status: e.target.value })}
                    className="h-8 w-full rounded-lg border border-border bg-background px-2.5 text-xs text-foreground"
                  >
                    <option value="">All statuses</option>
                    {["New", "In Review", "Needs Review", "Reviewed", "Saved", "Qualified", "Dismissed"].map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="block space-y-1">
                  <span className="text-[11px] font-medium text-muted-foreground">Minimum relevance</span>
                  <select
                    aria-label="Filter by minimum relevance"
                    value={filters.min_score}
                    onChange={(e) => updateFilters({ min_score: Number(e.target.value) })}
                    className="h-8 w-full rounded-lg border border-border bg-background px-2.5 text-xs text-foreground"
                  >
                    <option value={0}>Any relevance</option>
                    <option value={50}>50+ relevance</option>
                    <option value={70}>70+ relevance</option>
                    <option value={85}>85+ relevance</option>
                  </select>
                </label>

                <label className="block space-y-1">
                  <span className="text-[11px] font-medium text-muted-foreground">Buying-intent assessment</span>
                  <select
                    aria-label="Filter by buying intent"
                    value={filters.buying_intent}
                    onChange={(e) => updateFilters({ buying_intent: e.target.value })}
                    className="h-8 w-full rounded-lg border border-border bg-background px-2.5 text-xs text-foreground"
                  >
                    <option value="">Any assessment</option>
                    <option value="explicit">Explicit commercial intent</option>
                    <option value="possible">Possible commercial intent</option>
                    <option value="none">No commercial intent</option>
                    <option value="insufficient">Insufficient evidence</option>
                    <option value="unassessed">Not yet assessed</option>
                  </select>
                </label>

                <label className="block space-y-1">
                  <span className="text-[11px] font-medium text-muted-foreground">ICP fit</span>
                  <select
                    aria-label="Filter by ICP fit"
                    value={filters.icp_fit}
                    onChange={(e) => updateFilters({ icp_fit: e.target.value })}
                    className="h-8 w-full rounded-lg border border-border bg-background px-2.5 text-xs text-foreground"
                  >
                    <option value="">Any ICP fit</option>
                    <option value="match">Aligned / Match</option>
                    <option value="possible">Possible fit</option>
                    <option value="mismatch">Mismatch</option>
                    <option value="unassessed">Unassessed</option>
                  </select>
                </label>

                <label className="block space-y-1">
                  <span className="text-[11px] font-medium text-muted-foreground">Date range</span>
                  <select
                    aria-label="Filter by date range"
                    value={filters.range}
                    onChange={(e) =>
                      updateFilters({
                        range: e.target.value as DateRangePreset,
                        from_date: "",
                        to_date: "",
                      })
                    }
                    className="h-8 w-full rounded-lg border border-border bg-background px-2.5 text-xs text-foreground"
                  >
                    <option value="">All time (within retention)</option>
                    <option value="7d">Last 7 days</option>
                    <option value="30d">Last 30 days</option>
                    <option value="90d">Last 90 days</option>
                  </select>
                </label>

                <label className="block space-y-1">
                  <span className="text-[11px] font-medium text-muted-foreground">Monitor</span>
                  <select
                    aria-label="Filter by monitor"
                    value={filters.monitor_id}
                    onChange={(e) => updateFilters({ monitor_id: e.target.value })}
                    className="h-8 w-full rounded-lg border border-border bg-background px-2.5 text-xs text-foreground"
                  >
                    <option value="">All monitors</option>
                    {(monitors.data?.items || []).map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.name}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              <div className="flex justify-end border-t border-border/70 pt-2.5">
                <button
                  type="button"
                  onClick={() => setFilterOpen(false)}
                  className="inline-flex h-8 items-center rounded-lg bg-primary px-3.5 text-xs font-semibold text-primary-foreground hover:opacity-90 cursor-pointer"
                >
                  Apply filters
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Sort */}
        <select
          aria-label="Sort signals"
          value={filters.sort}
          onChange={(e) => updateFilters({ sort: e.target.value as SortKey })}
          style={{ width: "auto" }}
          className="h-9 rounded-lg border border-border bg-card px-3 text-xs font-medium text-foreground"
        >
          <option value="newest">Newest observed</option>
          <option value="score">Highest relevance</option>
          <option value="score_asc">Lowest relevance</option>
          <option value="oldest">Oldest observed</option>
          <option value="title">Title A–Z</option>
        </select>

        {/* Columns visibility */}
        {display === "table" && (
          <div className="relative hidden md:block" ref={columnsRef}>
            <button
              type="button"
              aria-expanded={columnsOpen}
              onClick={() => {
                setColumnsOpen((v) => !v);
                setFilterOpen(false);
              }}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border bg-card px-2.5 text-xs font-medium text-muted-foreground hover:text-foreground cursor-pointer"
            >
              <Columns3 size={13} />
              Columns
            </button>
            {columnsOpen && (
              <div className="absolute right-0 z-40 mt-2 w-48 rounded-xl border border-border bg-card p-3 shadow-lg space-y-2 text-xs">
                <p className="font-semibold text-foreground">Optional columns</p>
                {(
                  [
                    ["category", "Intent category"],
                    ["buyingIntent", "Buying intent"],
                    ["observed", "Observed date"],
                  ] as const
                ).map(([k, label]) => (
                  <label key={k} className="flex items-center gap-2 cursor-pointer text-foreground">
                    <input
                      type="checkbox"
                      checked={visibleCols[k]}
                      onChange={(e) => setVisibleCols((v) => ({ ...v, [k]: e.target.checked }))}
                      className="accent-primary"
                    />
                    {label}
                  </label>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Table / Cards toggle */}
        <div
          className="inline-flex items-center rounded-lg border border-border bg-card p-0.5 ml-auto"
          role="group"
          aria-label="Signal view mode"
        >
          <button
            type="button"
            aria-pressed={display === "table"}
            onClick={() => setDisplayMode("table")}
            className={
              "inline-flex h-8 items-center gap-1 rounded-md px-2.5 text-xs font-medium cursor-pointer " +
              (display === "table" ? "bg-muted text-foreground font-semibold" : "text-muted-foreground hover:text-foreground")
            }
          >
            <List size={14} /> Table
          </button>
          <button
            type="button"
            aria-pressed={display === "cards"}
            onClick={() => setDisplayMode("cards")}
            className={
              "inline-flex h-8 items-center gap-1 rounded-md px-2.5 text-xs font-medium cursor-pointer " +
              (display === "cards" ? "bg-muted text-foreground font-semibold" : "text-muted-foreground hover:text-foreground")
            }
          >
            <LayoutGrid size={14} /> Cards
          </button>
        </div>
      </div>

      {/* Active Filter Chips */}
      {activeFilterChips.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5" aria-label="Active filters">
          {activeFilterChips.map((chip) => (
            <span
              key={chip.key}
              className="inline-flex items-center gap-1.5 rounded-full border border-primary/25 bg-primary/8 px-2.5 py-1 text-[11px] font-medium text-foreground"
            >
              <span>{chip.label}</span>
              <button
                type="button"
                aria-label={`Remove ${chip.label}`}
                onClick={chip.clear}
                className="text-muted-foreground hover:text-foreground cursor-pointer"
              >
                <X size={12} />
              </button>
            </span>
          ))}
          <button
            type="button"
            onClick={resetAllFilters}
            className="text-xs font-medium text-primary hover:underline px-1.5 cursor-pointer"
          >
            Clear all filters
          </button>
        </div>
      )}

      {/* Undo / Status Notice Banner */}
      {notice && (
        <div
          role={notice.isError ? "alert" : "status"}
          className={
            "flex flex-wrap items-center justify-between gap-2 rounded-xl border px-4 py-2.5 text-xs shadow-sm " +
            (notice.isError
              ? "border-destructive/30 bg-destructive/10 text-destructive"
              : "border-border bg-card text-foreground")
          }
        >
          <span>{notice.message}</span>
          <div className="flex items-center gap-2">
            {notice.undo && (
              <button
                type="button"
                onClick={() => void handleUndo()}
                className="inline-flex items-center gap-1 rounded-md border border-primary/40 bg-primary/10 px-2.5 py-1 text-xs font-semibold text-primary hover:bg-primary/15 cursor-pointer"
              >
                <RotateCcw size={12} /> Undo
              </button>
            )}
            <button
              type="button"
              aria-label="Dismiss notice"
              onClick={() => setNotice(null)}
              className="text-muted-foreground hover:text-foreground cursor-pointer"
            >
              <X size={14} />
            </button>
          </div>
        </div>
      )}

      {/* Bulk Selection Bar (explicit page-scope clarity, loading state & role explanation) */}
      {selected.length > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-primary/30 bg-primary/[0.05] px-4 py-2.5">
          <div className="text-xs font-semibold text-foreground flex items-center gap-2">
            {bulkBusyAction && <Loader2 size={13} className="animate-spin text-primary" />}
            <span>
              {bulkBusyAction
                ? `Applying bulk action to ${selected.length} signal${selected.length === 1 ? "" : "s"}…`
                : `${selected.length} selected on this page`}
            </span>
            {!bulkBusyAction && totalCount > rows.length && (
              <span className="font-normal text-muted-foreground">
                (of {totalCount.toLocaleString()} matching signals)
              </span>
            )}
            {!canWrite && (
              <span className="font-normal text-amber-700 dark:text-amber-300">
                · Read-only access (actions disabled)
              </span>
            )}
          </div>

          {bulkConfirm ? (
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="font-medium text-foreground">
                Confirm {bulkConfirm === "dismiss" ? "dismissing" : "qualifying"} {selected.length} signal
                {selected.length === 1 ? "" : "s"}?
              </span>
              <button
                type="button"
                disabled={!canWrite || mutation.isPending}
                onClick={() => void runBulkAction(bulkConfirm)}
                style={{
                  background: bulkConfirm === "dismiss" ? "#dc2626" : "#059669",
                  borderColor: bulkConfirm === "dismiss" ? "#dc2626" : "#059669",
                  color: "#ffffff",
                  padding: "5px 12px",
                  minHeight: "30px",
                }}
                className="inline-flex items-center gap-1 rounded-lg text-xs font-semibold hover:opacity-90 disabled:opacity-50 cursor-pointer"
              >
                {bulkBusyAction ? <Loader2 size={12} className="animate-spin" /> : null}
                Confirm
              </button>
              <button
                type="button"
                disabled={mutation.isPending}
                onClick={() => setBulkConfirm(null)}
                style={{ padding: "5px 10px", minHeight: "30px" }}
                className="inline-flex items-center rounded-lg border border-border bg-background text-xs font-medium text-foreground cursor-pointer"
              >
                Cancel
              </button>
            </div>
          ) : (
            <div className="flex flex-wrap items-center gap-1.5">
              <button
                type="button"
                disabled={!canWrite || mutation.isPending}
                title={!canWrite ? "Read-only workspace access" : undefined}
                onClick={() => void runBulkAction("review")}
                className="inline-flex items-center gap-1 rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs font-medium text-foreground hover:bg-muted disabled:opacity-50 cursor-pointer"
              >
                <CheckCheck size={13} /> Mark Reviewed
              </button>
              <button
                type="button"
                disabled={!canWrite || mutation.isPending}
                title={!canWrite ? "Read-only workspace access" : undefined}
                onClick={() => setBulkConfirm("qualify")}
                className="inline-flex items-center gap-1 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1.5 text-xs font-medium text-emerald-700 dark:text-emerald-300 hover:bg-emerald-500/15 disabled:opacity-50 cursor-pointer"
              >
                <CheckCircle2 size={13} /> Qualify
              </button>
              <button
                type="button"
                disabled={!canWrite || mutation.isPending}
                title={!canWrite ? "Read-only workspace access" : undefined}
                onClick={() => void runBulkAction(filters.view === "saved" ? "unsave" : "save")}
                className="inline-flex items-center gap-1 rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs font-medium text-foreground hover:bg-muted disabled:opacity-50 cursor-pointer"
              >
                <Bookmark size={13} /> {filters.view === "saved" ? "Unsave" : "Save"}
              </button>
              <button
                type="button"
                disabled={!canWrite || mutation.isPending}
                title={!canWrite ? "Read-only workspace access" : undefined}
                onClick={() => void runBulkAction("opportunity")}
                className="inline-flex items-center gap-1 rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs font-medium text-foreground hover:border-primary/50 hover:text-primary disabled:opacity-50 cursor-pointer"
              >
                <Target size={13} /> Create Opportunities
              </button>
              <button
                type="button"
                disabled={!canWrite || mutation.isPending}
                title={!canWrite ? "Read-only workspace access" : undefined}
                onClick={() => setBulkConfirm("dismiss")}
                className="inline-flex items-center gap-1 rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs font-medium text-muted-foreground hover:border-destructive/40 hover:text-destructive disabled:opacity-50 cursor-pointer"
              >
                <XCircle size={13} /> Dismiss
              </button>
              <button
                type="button"
                disabled={mutation.isPending}
                onClick={() => setSelected([])}
                className="ml-1 text-xs font-medium text-muted-foreground hover:text-foreground cursor-pointer"
              >
                Clear
              </button>
            </div>
          )}
        </div>
      )}

      {/* Results Count Strip */}
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>
          {query.error
            ? "Could not load signals — retry below"
            : !query.data
              ? "Loading signals…"
              : totalCount === 0
                ? "0 matching signals"
                : `Showing ${(page - 1) * PAGE_SIZE + 1}–${Math.min(page * PAGE_SIZE, totalCount)} of ${totalCount.toLocaleString()} signals`}
        </span>
        {filters.view === "high_intent" && (
          <span className="hidden sm:inline text-[11px] text-muted-foreground">
            AI-verified explicit intent or rule-based commercial indicators (excludes dismissed &amp; technical releases)
          </span>
        )}
      </div>

      {/* Main Content Area */}
      {query.error ? (
        <ErrorState message={query.error.message} retry={() => void query.refetch()} />
      ) : !query.data ? (
        <LoadingSkeleton />
      ) : rows.length === 0 ? (
        <EmptyState
          title={hasAnyFilterOrSearch ? "No signals match this view or filters" : "No signals collected yet"}
          description={
            hasAnyFilterOrSearch
              ? "Try switching views, broadening your keywords, or clearing active filters."
              : "Run a public-source discovery search or activate a monitor. Matching conversations will appear here for triage."
          }
          icon={Search}
          action={
            hasAnyFilterOrSearch ? (
              <button
                type="button"
                onClick={() => {
                  setSearchInput("");
                  setFilters(DEFAULT_FILTERS);
                  setPage(1);
                }}
                className="inline-flex h-9 items-center rounded-lg border border-border bg-card px-4 text-xs font-semibold text-foreground hover:bg-muted cursor-pointer"
              >
                Reset to All Signals
              </button>
            ) : (
              <Link
                className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-primary px-4 text-xs font-semibold text-primary-foreground hover:opacity-90"
                href="/intent-radar/discover"
              >
                Discover Intent <ArrowRight size={14} />
              </Link>
            )
          }
        />
      ) : display === "cards" ? (
        <div className="grid gap-4 md:grid-cols-2">
          {rows.map((s) => (
            <SignalCard
              key={s.id}
              signal={s}
              onOpen={(id) => setOpenedId(id)}
              selected={selected.includes(s.id)}
              onToggleSelect={(id) =>
                setSelected((prev) =>
                  prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
                )
              }
              onQualify={(sig) => void runQuickStatus(sig, "Qualified")}
              onDismiss={(sig) => void runQuickStatus(sig, "Dismissed")}
              onOpenOpportunity={(sig) => setOpportunityTarget(sig)}
            />
          ))}
        </div>
      ) : (
        <>
          {/* Desktop / Tablet Scalable Data Table */}
          <div className="hidden md:block overflow-x-auto rounded-2xl border border-border bg-card">
            <table className="w-full border-collapse text-left text-xs">
              <thead>
                <tr className="border-b border-border bg-muted/35 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  <th style={{ width: "36px", minWidth: "36px", maxWidth: "36px", padding: "10px 6px 10px 12px" }}>
                    <input
                      type="checkbox"
                      aria-label="Select all signals on this page"
                      checked={allVisibleSelected}
                      onChange={(e) => setSelected(e.target.checked ? rows.map((r) => r.id) : [])}
                      style={{ width: "15px", height: "15px", minWidth: "15px", padding: 0 }}
                      className="accent-primary cursor-pointer"
                    />
                  </th>
                  <th className="min-w-[195px] px-2 py-2.5">Signal</th>
                  <th className="whitespace-nowrap px-2 py-2.5">Source</th>
                  {visibleCols.category && <th className="whitespace-nowrap px-2 py-2.5">Intent</th>}
                  <th className="whitespace-nowrap px-2 py-2.5">Score</th>
                  {visibleCols.buyingIntent && <th className="whitespace-nowrap px-2 py-2.5">Buying Intent</th>}
                  {visibleCols.observed && <th className="whitespace-nowrap px-2 py-2.5">Observed</th>}
                  <th className="whitespace-nowrap px-2 py-2.5">Status</th>
                  <th className="whitespace-nowrap px-2 py-2.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/70">
                {rows.map((s) => {
                  const obs = formatObservedDate(s.observed_at);
                  const buying = buyingIntentDisplay(s);
                  const checked = selected.includes(s.id);
                  return (
                    <tr
                      key={s.id}
                      onClick={() => setOpenedId(s.id)}
                      className={
                        "group cursor-pointer transition-colors hover:bg-muted/35 " +
                        (checked ? "bg-primary/[0.04]" : "")
                      }
                    >
                      <td
                        style={{ width: "36px", minWidth: "36px", maxWidth: "36px", padding: "10px 6px 10px 12px" }}
                        className="align-top"
                        onClick={(e) => e.stopPropagation()}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" || e.key === " ") e.stopPropagation();
                        }}
                      >
                        <input
                          type="checkbox"
                          aria-label={`Select ${s.title}`}
                          checked={checked}
                          onChange={(e) =>
                            setSelected((prev) =>
                              e.target.checked ? [...prev, s.id] : prev.filter((id) => id !== s.id)
                            )
                          }
                          style={{ width: "15px", height: "15px", minWidth: "15px", padding: 0 }}
                          className="mt-0.5 accent-primary cursor-pointer"
                        />
                      </td>

                      <td className="px-2 py-2.5 align-top max-w-[300px]">
                        <div className="space-y-1">
                          <Link
                            href={`/intent-radar/signals/${s.id}`}
                            title={s.title}
                            onClick={(e) => {
                              e.preventDefault();
                              e.stopPropagation();
                              setOpenedId(s.id);
                            }}
                            className="font-semibold text-foreground leading-snug line-clamp-2 group-hover:text-primary transition-colors"
                          >
                            {s.title}
                          </Link>
                          <div className="flex flex-wrap items-center gap-1 text-[11px] text-muted-foreground">
                            {s.saved && (
                              <span className="inline-flex items-center gap-0.5 text-primary font-medium">
                                <Bookmark size={10} fill="currentColor" /> Saved
                              </span>
                            )}
                            {s.opportunity_id && (
                              <span className="inline-flex items-center gap-0.5 text-emerald-700 dark:text-emerald-300 font-medium">
                                <Target size={10} /> Opportunity
                              </span>
                            )}
                            {s.evidence?.matched_keywords?.slice(0, 2).map((kw) => (
                              <span
                                key={kw}
                                className="rounded bg-muted/70 px-1.5 py-0.5 text-[10px] text-muted-foreground"
                              >
                                {kw}
                              </span>
                            ))}
                          </div>
                        </div>
                      </td>

                      <td className="px-2 py-2.5 align-top whitespace-nowrap">
                        <span className="inline-flex items-center gap-1.5 font-medium text-foreground">
                          <ProviderLogo provider={s.source} size={15} />
                          <span>{s.source}</span>
                        </span>
                      </td>

                      {visibleCols.category && (
                        <td className="px-2 py-2.5 align-top">
                          <span
                            title={s.category}
                            className="inline-block max-w-[116px] truncate whitespace-nowrap rounded-full border border-border bg-muted/40 px-2 py-0.5 text-[11px] font-medium text-foreground"
                          >
                            {s.category}
                          </span>
                        </td>
                      )}

                      <td className="px-2 py-2.5 align-top whitespace-nowrap">
                        <SignalScore score={s.score} />
                      </td>

                      {visibleCols.buyingIntent && (
                        <td className="px-2 py-2.5 align-top whitespace-nowrap">
                          <span
                            title={buying.label}
                            className={
                              "inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium " +
                              buying.tone
                            }
                          >
                            {buying.shortLabel}
                          </span>
                        </td>
                      )}

                      {visibleCols.observed && (
                        <td
                          className="px-2 py-2.5 align-top whitespace-nowrap text-muted-foreground tabular-nums"
                          title={obs.full}
                        >
                          {obs.short}
                        </td>
                      )}

                      <td className="px-2 py-2.5 align-top whitespace-nowrap">
                        <span
                          className={
                            "inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-semibold " +
                            statusPillClasses(s.status)
                          }
                        >
                          {s.status}
                        </span>
                      </td>

                      <td
                        className="px-2 py-2.5 align-top whitespace-nowrap text-right"
                        onClick={(e) => e.stopPropagation()}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" || e.key === " ") e.stopPropagation();
                        }}
                      >
                        <div className="inline-flex items-center gap-1">
                          <button
                            type="button"
                            onClick={() => openFullDetails(s.id)}
                            aria-label={`Open full details for ${s.title}`}
                            style={{ padding: "4px 8px" }}
                            className="inline-flex h-7 items-center gap-1 rounded-md border border-border bg-background text-[11px] font-medium text-foreground hover:border-primary/50 hover:text-primary cursor-pointer"
                          >
                            Open <ArrowUpRight size={12} />
                          </button>

                          <Menu.Root>
                            <Menu.Trigger asChild>
                              <button
                                type="button"
                                aria-label={`More actions for ${s.title}`}
                                className="inline-flex h-7 w-7 items-center justify-center rounded-md border border-transparent text-muted-foreground hover:border-border hover:bg-muted hover:text-foreground cursor-pointer"
                              >
                                <MoreHorizontal size={14} />
                              </button>
                            </Menu.Trigger>
                            <MenuContent align="end" className="w-48 p-1 text-xs">
                              <Menu.Item
                                onSelect={() => setOpenedId(s.id)}
                                className="flex w-full items-center gap-2 rounded-md px-2.5 py-1.5 text-left text-xs text-foreground hover:bg-muted cursor-pointer outline-none"
                              >
                                <Eye size={13} /> Quick review
                              </Menu.Item>
                              <Menu.Item
                                onSelect={() => openFullDetails(s.id)}
                                className="flex w-full items-center gap-2 rounded-md px-2.5 py-1.5 text-left text-xs text-foreground hover:bg-muted cursor-pointer outline-none"
                              >
                                <ArrowUpRight size={13} /> Open full details
                              </Menu.Item>
                              <Menu.Separator className="my-1 h-px bg-border/70" />
                              <Menu.Item
                                disabled={!canWrite}
                                onSelect={() => void runQuickStatus(s, "Qualified")}
                                className="flex w-full items-center gap-2 rounded-md px-2.5 py-1.5 text-left text-xs text-emerald-700 dark:text-emerald-300 hover:bg-muted disabled:opacity-50 cursor-pointer outline-none"
                              >
                                <CheckCircle2 size={13} /> Qualify signal
                              </Menu.Item>
                              <Menu.Item
                                disabled={!canWrite}
                                onSelect={() => void runQuickStatus(s, "Reviewed")}
                                className="flex w-full items-center gap-2 rounded-md px-2.5 py-1.5 text-left text-xs text-foreground hover:bg-muted disabled:opacity-50 cursor-pointer outline-none"
                              >
                                <CheckCheck size={13} /> Mark reviewed
                              </Menu.Item>
                              <Menu.Item
                                disabled={!canWrite}
                                onSelect={() => void runQuickSave(s)}
                                className="flex w-full items-center gap-2 rounded-md px-2.5 py-1.5 text-left text-xs text-foreground hover:bg-muted disabled:opacity-50 cursor-pointer outline-none"
                              >
                                <Bookmark size={13} /> {s.saved ? "Remove bookmark" : "Save bookmark"}
                              </Menu.Item>
                              <Menu.Item
                                disabled={!canWrite}
                                onSelect={() => setOpportunityTarget(s)}
                                className="flex w-full items-center gap-2 rounded-md px-2.5 py-1.5 text-left text-xs text-foreground hover:bg-muted disabled:opacity-50 cursor-pointer outline-none"
                              >
                                <Target size={13} /> {s.opportunity_id ? "View opportunity" : "Create opportunity"}
                              </Menu.Item>
                              <Menu.Item
                                disabled={!canWrite}
                                onSelect={() => void runQuickStatus(s, "Dismissed")}
                                className="flex w-full items-center gap-2 rounded-md px-2.5 py-1.5 text-left text-xs text-destructive hover:bg-muted disabled:opacity-50 cursor-pointer outline-none"
                              >
                                <XCircle size={13} /> Dismiss signal
                              </Menu.Item>
                              {s.source_url?.startsWith("http") && (
                                <>
                                  <Menu.Separator className="my-1 h-px bg-border/70" />
                                  <Menu.Item asChild>
                                    <a
                                      href={s.source_url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="flex w-full items-center gap-2 rounded-md px-2.5 py-1.5 text-left text-xs text-muted-foreground hover:bg-muted hover:text-foreground outline-none"
                                    >
                                      <ExternalLink size={13} /> Open original source
                                    </a>
                                  </Menu.Item>
                                </>
                              )}
                            </MenuContent>
                          </Menu.Root>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Mobile Card Fallback (<768px) — Zero Horizontal Overflow */}
          <div className="space-y-3 md:hidden">
            {rows.map((s) => (
              <div key={s.id} className="space-y-1.5">
                <label className="inline-flex items-center gap-2 text-xs text-muted-foreground">
                  <input
                    type="checkbox"
                    checked={selected.includes(s.id)}
                    onChange={(e) =>
                      setSelected((prev) =>
                        e.target.checked ? [...prev, s.id] : prev.filter((id) => id !== s.id)
                      )
                    }
                    className="accent-primary"
                  />
                  Select signal
                </label>
                <SignalCard signal={s} onOpen={(id) => setOpenedId(id)} />
              </div>
            ))}
          </div>
        </>
      )}

      {/* Server-side Pagination */}
      {totalCount > PAGE_SIZE && (
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4 text-xs">
          <span className="text-muted-foreground tabular-nums">
            Page <strong className="text-foreground">{page}</strong> of{" "}
            <strong className="text-foreground">{totalPages.toLocaleString()}</strong>
          </span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => {
                setPage((p) => Math.max(1, p - 1));
                setSelected([]);
              }}
              className="inline-flex h-8 items-center gap-1 rounded-lg border border-border bg-card px-3 text-xs font-medium text-foreground hover:bg-muted disabled:opacity-45 cursor-pointer disabled:cursor-not-allowed"
            >
              <ChevronLeft size={14} /> Previous
            </button>
            <button
              type="button"
              disabled={page >= totalPages}
              onClick={() => {
                setPage((p) => p + 1);
                setSelected([]);
              }}
              className="inline-flex h-8 items-center gap-1 rounded-lg border border-border bg-card px-3 text-xs font-medium text-foreground hover:bg-muted disabled:opacity-45 cursor-pointer disabled:cursor-not-allowed"
            >
              Next <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}

      {/* Focused Single-Column Quick Review Drawer */}
      <SignalQuickDrawer
        signal={openedSignal}
        open={Boolean(openedSignal)}
        onClose={() => setOpenedId("")}
        hasPrev={openedIndex > 0}
        hasNext={openedIndex >= 0 && openedIndex < rows.length - 1}
        onPrev={() => {
          if (openedIndex > 0) setOpenedId(rows[openedIndex - 1].id);
        }}
        onNext={() => {
          if (openedIndex >= 0 && openedIndex < rows.length - 1) setOpenedId(rows[openedIndex + 1].id);
        }}
        onBeforeOpenFull={persistReturnContext}
        onOpenOpportunityModal={(sig) => setOpportunityTarget(sig)}
        onStatusChanged={(sig, prevStatus, nextStatus) =>
          setNotice({
            message: `Marked “${sig.title.slice(0, 48)}${sig.title.length > 48 ? "…" : ""}” as ${nextStatus}.`,
            undo: { signalId: sig.id, revision: sig.revision + 1, previousStatus: prevStatus },
          })
        }
      />

      {/* Controlled Editable Create Opportunity Modal */}
      <CreateOpportunityModal
        signal={opportunityTarget}
        open={Boolean(opportunityTarget)}
        onClose={() => setOpportunityTarget(null)}
        onCreated={() =>
          setNotice({ message: "Opportunity created and linked to this signal." })
        }
      />
    </div>
  );
}
