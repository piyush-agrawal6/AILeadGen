"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Bookmark,
  ChevronLeft,
  ChevronRight,
  Compass,
  Edit3,
  Eye,
  Filter,
  MoreHorizontal,
  Play,
  RotateCcw,
  Search,
  SlidersHorizontal,
  Trash2,
  X,
} from "lucide-react";
import type { DiscoveryRun, IntentJob, IntentPage, SourceId } from "@/lib/intent-radar";
import { Button } from "@/components/ui/button";
import { Menu, MenuContent } from "@/components/ui/menu";
import { EmptyState, ErrorState, PageHeading } from "../ui";
import { ProviderLogo } from "../provider-logo";
import { useRadarCapabilities, useRadarMutation, useRadarRead } from "../provider";
import { DiscoverNav } from "./DiscoverNav";
import { DISCOVERY_PRELOAD_KEY } from "./DiscoveryCopilotPanel";

export const DISCOVERY_HISTORY_RETURN_KEY = "planebyte:discovery-history-return";

type DateRangeKey = "" | "7d" | "30d" | "90d";
type SortKey = "newest" | "oldest" | "results_desc" | "results_asc" | "title_asc" | "title_desc";

const SOURCE_LABELS: Record<string, string> = {
  hacker_news: "Hacker News",
  stack_exchange: "Stack Exchange",
  github: "GitHub",
  youtube: "YouTube",
  bluesky: "Bluesky",
  discourse: "Discourse",
  rss: "RSS",
  atom: "Atom",
};

function statusDisplay(status: string, matched: number): { label: string; dot: string; pill: string } {
  const s = status.toUpperCase();
  if (s === "NO_RESULTS" || ((s === "COMPLETED" || s === "COMPLETE") && matched === 0)) {
    return {
      label: "No Results",
      dot: "bg-muted-foreground/70",
      pill: "bg-muted text-muted-foreground",
    };
  }
  if (s === "COMPLETED" || s === "COMPLETE") {
    return {
      label: "Completed",
      dot: "bg-emerald-500",
      pill: "bg-emerald-500/12 text-emerald-700 dark:text-emerald-300",
    };
  }
  if (s === "PARTIAL") {
    return {
      label: "Partial",
      dot: "bg-amber-500",
      pill: "bg-amber-500/12 text-amber-700 dark:text-amber-300",
    };
  }
  if (s === "FAILED") {
    return {
      label: "Failed",
      dot: "bg-destructive",
      pill: "bg-destructive/12 text-destructive",
    };
  }
  if (s === "CANCELLED" || s === "CANCELED") {
    return {
      label: "Canceled",
      dot: "bg-muted-foreground",
      pill: "bg-muted text-muted-foreground",
    };
  }
  return {
    label: s === "QUEUED" ? "Queued" : "Running",
    dot: "bg-blue-500",
    pill: "bg-blue-500/12 text-blue-700 dark:text-blue-300",
  };
}

function formatExecuted(iso: string): { short: string; full: string } {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return { short: iso, full: iso };
  const short = d.toLocaleDateString(undefined, { month: "short", day: "numeric" }) +
    " · " +
    d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
  return { short, full: d.toLocaleString() };
}

function rangeToFromDate(range: DateRangeKey): string {
  if (!range) return "";
  const days = range === "7d" ? 7 : range === "30d" ? 30 : 90;
  const d = new Date(Date.now() - days * 86_400_000);
  return d.toISOString().slice(0, 10);
}

function readInitialUrlState() {
  if (typeof window === "undefined") {
    return { q: "", source: "", status: "", mode: "", results: "", range: "" as DateRangeKey, sort: "newest" as SortKey, page: 1 };
  }
  const sp = new URLSearchParams(window.location.search);
  return {
    q: sp.get("q") || "",
    source: sp.get("source") || "",
    status: sp.get("status") || "",
    mode: sp.get("mode") || "",
    results: sp.get("results") || "",
    range: (sp.get("range") || "") as DateRangeKey,
    sort: (sp.get("sort") || "newest") as SortKey,
    page: Math.max(1, Number(sp.get("page") || "1") || 1),
  };
}

export function DiscoveryHistoryView() {
  const router = useRouter();
  const access = useRadarCapabilities();
  const mutation = useRadarMutation();

  const initial = useMemo(() => readInitialUrlState(), []);
  const [searchInput, setSearchInput] = useState(initial.q);
  const [debouncedSearch, setDebouncedSearch] = useState(initial.q);
  const [source, setSource] = useState(initial.source);
  const [status, setStatus] = useState(initial.status);
  const [mode, setMode] = useState(initial.mode);
  const [resultsFilter, setResultsFilter] = useState(initial.results);
  const [dateRange, setDateRange] = useState<DateRangeKey>(initial.range);
  const [sort, setSort] = useState<SortKey>(initial.sort);
  const [page, setPage] = useState(initial.page);
  const pageSize = 20;

  // Compact Filter Popover state
  const [filterOpen, setFilterOpen] = useState(false);
  const [draftSource, setDraftSource] = useState(source);
  const [draftStatus, setDraftStatus] = useState(status);
  const [draftMode, setDraftMode] = useState(mode);
  const [draftResults, setDraftResults] = useState(resultsFilter);
  const popoverRef = useRef<HTMLDivElement | null>(null);

  // Rename & Delete dialogs
  const [renamingRun, setRenamingRun] = useState<DiscoveryRun | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [deletingRun, setDeletingRun] = useState<DiscoveryRun | null>(null);
  const [viewingConfigRun, setViewingConfigRun] = useState<DiscoveryRun | null>(null);
  const [feedback, setFeedback] = useState("");

  // Debounce search input (250ms)
  useEffect(() => {
    const t = setTimeout(() => {
      setDebouncedSearch(searchInput.trim());
      if (searchInput.trim() !== debouncedSearch) setPage(1);
    }, 250);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchInput]);

  // Restore scroll position if returning from Discovery Details
  useEffect(() => {
    try {
      const raw = sessionStorage.getItem(DISCOVERY_HISTORY_RETURN_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as { scrollY?: number };
        if (typeof parsed.scrollY === "number" && parsed.scrollY > 0) {
          requestAnimationFrame(() => window.scrollTo(0, parsed.scrollY || 0));
        }
      }
    } catch {
      // ignore storage errors
    }
  }, []);

  // Sync URL query params for shareable, recoverable state
  useEffect(() => {
    if (typeof window === "undefined") return;
    const sp = new URLSearchParams();
    if (debouncedSearch) sp.set("q", debouncedSearch);
    if (source) sp.set("source", source);
    if (status) sp.set("status", status);
    if (mode) sp.set("mode", mode);
    if (resultsFilter) sp.set("results", resultsFilter);
    if (dateRange) sp.set("range", dateRange);
    if (sort !== "newest") sp.set("sort", sort);
    if (page > 1) sp.set("page", String(page));
    const qs = sp.toString();
    const nextUrl = `${window.location.pathname}${qs ? `?${qs}` : ""}`;
    if (nextUrl !== window.location.pathname + window.location.search) {
      window.history.replaceState({}, "", nextUrl);
    }
  }, [debouncedSearch, source, status, mode, resultsFilter, dateRange, sort, page]);

  // Close filter popover on outside click / Escape
  useEffect(() => {
    if (!filterOpen) return;
    const onDown = (e: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        setFilterOpen(false);
      }
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setFilterOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    window.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      window.removeEventListener("keydown", onKey);
    };
  }, [filterOpen]);

  const fromDate = rangeToFromDate(dateRange);
  const apiParams = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
    sort,
    ...(debouncedSearch ? { search: debouncedSearch } : {}),
    ...(source ? { source } : {}),
    ...(status ? { status } : {}),
    ...(mode ? { search_mode: mode } : {}),
    ...(resultsFilter ? { has_results: resultsFilter } : {}),
    ...(fromDate ? { from_date: fromDate } : {}),
  });

  const query = useRadarRead<IntentPage<DiscoveryRun>>(`/discoveries?${apiParams.toString()}`);

  const activeFilterChips = [
    source ? { key: "source", label: SOURCE_LABELS[source] || source, clear: () => { setSource(""); setPage(1); } } : null,
    status ? { key: "status", label: statusDisplay(status, status === "NO_RESULTS" ? 0 : 1).label, clear: () => { setStatus(""); setPage(1); } } : null,
    mode ? { key: "mode", label: `Mode: ${mode.toUpperCase()}`, clear: () => { setMode(""); setPage(1); } } : null,
    resultsFilter ? { key: "results", label: resultsFilter === "with_results" ? "With matches" : "No matches", clear: () => { setResultsFilter(""); setPage(1); } } : null,
    dateRange ? { key: "range", label: dateRange === "7d" ? "Last 7 days" : dateRange === "30d" ? "Last 30 days" : "Last 90 days", clear: () => { setDateRange(""); setPage(1); } } : null,
  ].filter(Boolean) as { key: string; label: string; clear: () => void }[];

  const popoverActiveCount = [source, status, mode, resultsFilter].filter(Boolean).length;

  function openRun(id: string) {
    try {
      sessionStorage.setItem(
        DISCOVERY_HISTORY_RETURN_KEY,
        JSON.stringify({
          url: window.location.pathname + window.location.search,
          scrollY: window.scrollY,
        })
      );
    } catch {
      // ignore storage errors
    }
    router.push(`/intent-radar/discover/runs/${id}`);
  }

  function reuseInBuilder(run: DiscoveryRun) {
    try {
      sessionStorage.setItem(
        DISCOVERY_PRELOAD_KEY,
        JSON.stringify({
          configuration: run.configuration,
          original_prompt: run.original_prompt,
          strategy: run.strategy,
          parent_discovery_id: run.id,
          title: run.title,
        })
      );
    } catch {
      // ignore storage errors
    }
    router.push("/intent-radar/discover");
  }

  async function rerunAsNew(run: DiscoveryRun) {
    setFeedback("");
    try {
      const res = (await mutation.mutateAsync({
        path: "/discover",
        body: {
          configuration: run.configuration,
          request_id: crypto.randomUUID(),
          title: run.title,
          original_prompt: run.original_prompt,
          search_mode: "rerun",
          parent_discovery_id: run.id,
          strategy: run.strategy || null,
        },
      })) as IntentJob;
      const sp = new URLSearchParams();
      if (res.discovery_id) sp.set("run", res.discovery_id);
      sp.set("job", res.id);
      router.push(`/intent-radar/discover?${sp.toString()}`);
    } catch (e) {
      setFeedback(e instanceof Error ? e.message : "Could not rerun discovery.");
    }
  }

  async function saveAsSearch(run: DiscoveryRun) {
    setFeedback("");
    try {
      await mutation.mutateAsync({
        path: "/saved-searches",
        body: {
          name: run.title.slice(0, 120),
          description: run.original_prompt.slice(0, 400),
          original_prompt: run.original_prompt,
          configuration: run.configuration,
        },
      });
      setFeedback(`Saved “${run.title}” to Saved Searches.`);
    } catch (e) {
      setFeedback(e instanceof Error ? e.message : "Could not save search.");
    }
  }

  async function confirmRename() {
    if (!renamingRun || !renameValue.trim()) return;
    setFeedback("");
    try {
      await mutation.mutateAsync({
        path: `/discoveries/${renamingRun.id}`,
        method: "PATCH",
        body: { title: renameValue.trim() },
      });
      setRenamingRun(null);
      setFeedback("Discovery title updated.");
      void query.refetch();
    } catch (e) {
      setFeedback(e instanceof Error ? e.message : "Could not rename discovery.");
    }
  }

  async function confirmDelete() {
    if (!deletingRun) return;
    setFeedback("");
    try {
      await mutation.mutateAsync({
        path: `/discoveries/${deletingRun.id}`,
        method: "DELETE",
      });
      setDeletingRun(null);
      setFeedback("Removed discovery from History. Underlying signals remain preserved.");
      void query.refetch();
    } catch (e) {
      setFeedback(e instanceof Error ? e.message : "Could not delete discovery.");
    }
  }

  function clearAllFilters() {
    setSearchInput("");
    setDebouncedSearch("");
    setSource("");
    setStatus("");
    setMode("");
    setResultsFilter("");
    setDateRange("");
    setSort("newest");
    setPage(1);
  }

  const total = query.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const startRow = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const endRow = Math.min(total, page * pageSize);

  return (
    <div className="ir-page space-y-4">
      <PageHeading
        title="Discovery History"
        description="Searchable archive of executed discovery runs with immutable original criteria and retained results."
      />
      <DiscoverNav activeTab="history" />

      {/* Compact Single-Row Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-2.5">
        <div className="flex flex-wrap items-center gap-2 flex-1 min-w-[240px]">
          <div className="relative flex-1 max-w-sm min-w-[200px]">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none" />
            <input
              type="search"
              aria-label="Search discoveries"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Search title, prompt, or keyword…"
              style={{ paddingLeft: "2.25rem" }}
              className="h-9 w-full rounded-lg border border-border bg-card pr-3 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          {/* Compact Filters Popover */}
          <div className="relative" ref={popoverRef}>
            <button
              type="button"
              aria-expanded={filterOpen}
              onClick={() => {
                setDraftSource(source);
                setDraftStatus(status);
                setDraftMode(mode);
                setDraftResults(resultsFilter);
                setFilterOpen((v) => !v);
              }}
              className={
                "inline-flex h-9 items-center gap-1.5 rounded-lg border px-3 text-xs font-medium transition-colors cursor-pointer " +
                (popoverActiveCount > 0
                  ? "border-primary/45 bg-primary/10 text-primary"
                  : "border-border bg-card text-foreground hover:border-primary/40")
              }
            >
              <Filter size={13} aria-hidden="true" />
              <span>Filters</span>
              {popoverActiveCount > 0 && (
                <span className="rounded-full bg-primary px-1.5 py-0.2 text-[10px] font-semibold text-primary-foreground">
                  {popoverActiveCount}
                </span>
              )}
            </button>

            {filterOpen && (
              <div
                role="dialog"
                aria-label="Filter discovery history"
                className="absolute left-0 top-11 z-40 w-72 rounded-xl border border-border bg-card p-4 shadow-xl space-y-3 text-xs"
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-foreground inline-flex items-center gap-1.5">
                    <SlidersHorizontal size={13} /> Filter History
                  </span>
                  <button
                    type="button"
                    onClick={() => setFilterOpen(false)}
                    aria-label="Close filters"
                    className="rounded p-1 text-muted-foreground hover:bg-muted cursor-pointer"
                  >
                    <X size={13} />
                  </button>
                </div>

                <label className="block space-y-1">
                  <span className="text-[11px] font-medium text-muted-foreground">Source</span>
                  <select
                    aria-label="Filter by source"
                    value={draftSource}
                    onChange={(e) => setDraftSource(e.target.value)}
                    className="h-8 w-full rounded-lg border border-border bg-background px-2 text-xs text-foreground"
                  >
                    <option value="">All sources</option>
                    {Object.entries(SOURCE_LABELS).map(([k, v]) => (
                      <option key={k} value={k}>{v}</option>
                    ))}
                  </select>
                </label>

                <label className="block space-y-1">
                  <span className="text-[11px] font-medium text-muted-foreground">Status</span>
                  <select
                    aria-label="Filter by status"
                    value={draftStatus}
                    onChange={(e) => setDraftStatus(e.target.value)}
                    className="h-8 w-full rounded-lg border border-border bg-background px-2 text-xs text-foreground"
                  >
                    <option value="">All statuses</option>
                    <option value="COMPLETED">Completed</option>
                    <option value="NO_RESULTS">No Results</option>
                    <option value="PARTIAL">Partial</option>
                    <option value="RUNNING">Running</option>
                    <option value="FAILED">Failed</option>
                    <option value="CANCELLED">Canceled</option>
                  </select>
                </label>

                <div className="grid grid-cols-2 gap-2">
                  <label className="block space-y-1">
                    <span className="text-[11px] font-medium text-muted-foreground">Search mode</span>
                    <select
                      aria-label="Filter by search mode"
                      value={draftMode}
                      onChange={(e) => setDraftMode(e.target.value)}
                      className="h-8 w-full rounded-lg border border-border bg-background px-2 text-xs text-foreground"
                    >
                      <option value="">Any mode</option>
                      <option value="ai">AI</option>
                      <option value="advanced">Advanced</option>
                      <option value="rerun">Rerun</option>
                      <option value="monitor">Monitor</option>
                    </select>
                  </label>

                  <label className="block space-y-1">
                    <span className="text-[11px] font-medium text-muted-foreground">Results</span>
                    <select
                      aria-label="Filter by result presence"
                      value={draftResults}
                      onChange={(e) => setDraftResults(e.target.value)}
                      className="h-8 w-full rounded-lg border border-border bg-background px-2 text-xs text-foreground"
                    >
                      <option value="">Any</option>
                      <option value="with_results">With matches</option>
                      <option value="no_results">No matches</option>
                    </select>
                  </label>
                </div>

                <div className="flex items-center justify-between border-t border-border pt-2.5">
                  <button
                    type="button"
                    onClick={() => {
                      setDraftSource("");
                      setDraftStatus("");
                      setDraftMode("");
                      setDraftResults("");
                      setSource("");
                      setStatus("");
                      setMode("");
                      setResultsFilter("");
                      setPage(1);
                      setFilterOpen(false);
                    }}
                    className="text-xs font-medium text-muted-foreground hover:text-foreground cursor-pointer"
                  >
                    Clear filters
                  </button>
                  <Button
                    size="sm"
                    onClick={() => {
                      setSource(draftSource);
                      setStatus(draftStatus);
                      setMode(draftMode);
                      setResultsFilter(draftResults);
                      setPage(1);
                      setFilterOpen(false);
                    }}
                    className="h-7 px-3 text-xs"
                  >
                    Apply
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right Controls: Date range, Sort, New Discovery */}
        <div className="flex flex-wrap items-center gap-2 shrink-0">
          <select
            aria-label="Date range"
            value={dateRange}
            onChange={(e) => {
              setDateRange(e.target.value as DateRangeKey);
              setPage(1);
            }}
            style={{ width: "auto" }}
            className="h-9 rounded-lg border border-border bg-card px-2.5 text-xs text-foreground"
          >
            <option value="">Any date</option>
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
            <option value="90d">Last 90 days</option>
          </select>

          <select
            aria-label="Sort discovery history"
            value={sort}
            onChange={(e) => {
              setSort(e.target.value as SortKey);
              setPage(1);
            }}
            style={{ width: "auto" }}
            className="h-9 rounded-lg border border-border bg-card px-2.5 text-xs text-foreground"
          >
            <option value="newest">Newest first</option>
            <option value="oldest">Oldest first</option>
            <option value="results_desc">Most matches</option>
            <option value="results_asc">Fewest matches</option>
            <option value="title_asc">Title A–Z</option>
            <option value="title_desc">Title Z–A</option>
          </select>

          <Button size="sm" onClick={() => router.push("/intent-radar/discover")} className="h-9 gap-1.5 text-xs whitespace-nowrap">
            <Compass size={13} aria-hidden="true" />
            New Discovery
          </Button>
        </div>
      </div>

      {/* Removable Active Filter Chips (only when active) */}
      {activeFilterChips.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 text-xs" aria-label="Active filters">
          {activeFilterChips.map((chip) => (
            <span
              key={chip.key}
              className="inline-flex items-center gap-1 rounded-full border border-primary/30 bg-primary/10 px-2.5 py-0.5 text-[11px] font-medium text-primary"
            >
              {chip.label}
              <button
                type="button"
                onClick={chip.clear}
                aria-label={`Remove ${chip.label} filter`}
                className="rounded-full p-0.5 hover:bg-primary/20 cursor-pointer"
              >
                <X size={11} />
              </button>
            </span>
          ))}
          <button
            type="button"
            onClick={clearAllFilters}
            className="text-[11px] font-medium text-muted-foreground hover:text-foreground px-1.5 cursor-pointer"
          >
            Clear all
          </button>
        </div>
      )}

      {feedback && (
        <div role="status" className="rounded-xl border border-border bg-muted/30 px-4 py-2 text-xs text-foreground">
          {feedback}
        </div>
      )}

      {/* Scalable Data Table */}
      {query.error ? (
        <ErrorState message={query.error.message} retry={() => void query.refetch()} />
      ) : !query.data ? (
        <div className="rounded-2xl border border-border bg-card overflow-hidden">
          <div className="divide-y divide-border">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="flex items-center gap-4 px-4 py-3.5 animate-pulse">
                <div className="h-4 w-1/3 rounded bg-muted" />
                <div className="h-4 w-24 rounded bg-muted" />
                <div className="h-4 w-20 rounded bg-muted" />
                <div className="h-4 w-16 rounded bg-muted ml-auto" />
              </div>
            ))}
          </div>
        </div>
      ) : query.data.items.length === 0 ? (
        <EmptyState
          title={debouncedSearch || activeFilterChips.length > 0 ? "No matching discovery runs" : "No discovery runs yet"}
          description={
            debouncedSearch || activeFilterChips.length > 0
              ? "Try broadening your search text or clearing one or more active filters."
              : "Run a search from New Discovery to build a permanent, searchable table of your research history."
          }
          action={
            debouncedSearch || activeFilterChips.length > 0 ? (
              <Button size="sm" variant="outline" onClick={clearAllFilters}>
                Clear filters
              </Button>
            ) : (
              <Button size="sm" onClick={() => router.push("/intent-radar/discover")}>
                Start New Discovery
              </Button>
            )
          }
        />
      ) : (
        <div className="rounded-2xl border border-border bg-card overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left text-xs">
              <thead>
                <tr className="border-b border-border bg-muted/30 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  <th scope="col" className="py-3 pl-4 pr-3 min-w-[260px]">Discovery</th>
                  <th scope="col" className="py-3 px-3 whitespace-nowrap">Sources</th>
                  <th scope="col" className="py-3 px-3 whitespace-nowrap">Status</th>
                  <th scope="col" className="py-3 px-3 whitespace-nowrap text-right">Results</th>
                  <th scope="col" className="py-3 px-3 whitespace-nowrap">Executed</th>
                  <th scope="col" className="py-3 pl-2 pr-4 text-right w-12">
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/80">
                {query.data.items.map((run) => {
                  const st = statusDisplay(run.status, run.matched_count);
                  const execTime = formatExecuted(run.created_at);
                  const visibleSources = (run.sources || []).slice(0, 2);
                  const extraSources = Math.max(0, (run.sources || []).length - 2);
                  const subtitle = run.original_prompt
                    ? run.original_prompt
                    : run.keywords.slice(0, 4).join(" · ");

                  return (
                    <tr
                      key={run.id}
                      tabIndex={0}
                      onClick={() => openRun(run.id)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          openRun(run.id);
                        }
                      }}
                      className="group cursor-pointer hover:bg-muted/35 focus-visible:outline-none focus-visible:bg-primary/[0.06] transition-colors"
                    >
                      {/* Discovery title + subtitle */}
                      <td className="py-3 pl-4 pr-3 max-w-md">
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="font-semibold text-[13px] text-foreground group-hover:text-primary transition-colors truncate">
                            {run.title}
                          </span>
                          {run.search_mode && run.search_mode !== "advanced" && (
                            <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium uppercase text-muted-foreground shrink-0">
                              {run.search_mode}
                            </span>
                          )}
                        </div>
                        {subtitle && (
                          <p className="mt-0.5 text-[11px] text-muted-foreground truncate">
                            {subtitle}
                          </p>
                        )}
                      </td>

                      {/* Compact Sources */}
                      <td className="py-3 px-3 whitespace-nowrap">
                        <div
                          className="inline-flex items-center gap-1.5"
                          title={(run.sources || []).map((s) => SOURCE_LABELS[s] || s).join(", ")}
                        >
                          {visibleSources.map((src: SourceId) => (
                            <span
                              key={src}
                              className="inline-flex items-center gap-1 rounded-md border border-border/70 bg-background px-2 py-0.5 text-[11px] font-medium text-foreground"
                            >
                              <ProviderLogo provider={SOURCE_LABELS[src] || src} size={12} />
                              <span className="hidden sm:inline">{SOURCE_LABELS[src] || src}</span>
                            </span>
                          ))}
                          {extraSources > 0 && (
                            <span className="rounded-md bg-muted px-1.5 py-0.5 text-[10px] font-semibold text-muted-foreground">
                              +{extraSources}
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Status */}
                      <td className="py-3 px-3 whitespace-nowrap">
                        <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${st.pill}`}>
                          <span className={`h-1.5 w-1.5 rounded-full ${st.dot}`} aria-hidden="true" />
                          {st.label}
                        </span>
                      </td>

                      {/* Results: Matches vs Scanned clearly separated */}
                      <td className="py-3 px-3 whitespace-nowrap text-right">
                        <div className="font-semibold text-foreground">
                          {run.matched_count} {run.matched_count === 1 ? "match" : "matches"}
                        </div>
                        <div className="text-[10px] text-muted-foreground">
                          {run.scanned_count} scanned
                        </div>
                      </td>

                      {/* Executed Timestamp */}
                      <td className="py-3 px-3 whitespace-nowrap text-muted-foreground" title={execTime.full}>
                        {execTime.short}
                      </td>

                      {/* Compact Actions Menu */}
                      <td
                        className="py-3 pl-2 pr-4 text-right whitespace-nowrap"
                        onClick={(e) => e.stopPropagation()}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" || e.key === " ") e.stopPropagation();
                        }}
                      >
                        <div className="inline-flex items-center justify-end gap-1.5">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => openRun(run.id)}
                            className="h-7 px-2.5 text-xs gap-1"
                            title="Open run results and evidence"
                          >
                            <Eye size={12} />
                            <span className="hidden sm:inline">Results</span>
                          </Button>

                          <Menu.Root>
                            <Menu.Trigger asChild>
                              <button
                                type="button"
                                aria-label={`Actions for ${run.title}`}
                                className="inline-flex h-7 w-7 items-center justify-center rounded-lg border border-border bg-card text-muted-foreground hover:bg-muted hover:text-foreground cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                              >
                                <MoreHorizontal size={14} aria-hidden="true" />
                              </button>
                            </Menu.Trigger>
                            <MenuContent align="end" className="w-52 p-1 text-xs">
                              <Menu.Item
                                onSelect={() => openRun(run.id)}
                                className="flex items-center gap-2 rounded-md px-2.5 py-1.5 cursor-pointer hover:bg-muted outline-none"
                              >
                                <Eye size={13} /> Open Results
                              </Menu.Item>
                              <Menu.Item
                                onSelect={() => setViewingConfigRun(run)}
                                className="flex items-center gap-2 rounded-md px-2.5 py-1.5 cursor-pointer hover:bg-muted outline-none"
                              >
                                <SlidersHorizontal size={13} /> View Search Configuration
                              </Menu.Item>
                              <Menu.Item
                                onSelect={() => reuseInBuilder(run)}
                                className="flex items-center gap-2 rounded-md px-2.5 py-1.5 cursor-pointer hover:bg-muted outline-none"
                              >
                                <RotateCcw size={13} /> Open in Builder
                              </Menu.Item>
                              {access.data?.can_write && (
                                <>
                                  <Menu.Item
                                    onSelect={() => void rerunAsNew(run)}
                                    className="flex items-center gap-2 rounded-md px-2.5 py-1.5 cursor-pointer hover:bg-muted outline-none"
                                  >
                                    <Play size={13} /> Rerun Discovery
                                  </Menu.Item>
                                  <Menu.Item
                                    onSelect={() => void saveAsSearch(run)}
                                    className="flex items-center gap-2 rounded-md px-2.5 py-1.5 cursor-pointer hover:bg-muted outline-none"
                                  >
                                    <Bookmark size={13} /> Save as Search
                                  </Menu.Item>
                                  <Menu.Item
                                    onSelect={() => {
                                      setRenamingRun(run);
                                      setRenameValue(run.title);
                                    }}
                                    className="flex items-center gap-2 rounded-md px-2.5 py-1.5 cursor-pointer hover:bg-muted outline-none"
                                  >
                                    <Edit3 size={13} /> Rename
                                  </Menu.Item>
                                  <Menu.Separator className="my-1 h-px bg-border" />
                                  <Menu.Item
                                    onSelect={() => setDeletingRun(run)}
                                    className="flex items-center gap-2 rounded-md px-2.5 py-1.5 cursor-pointer text-destructive hover:bg-destructive/10 outline-none"
                                  >
                                    <Trash2 size={13} /> Delete
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

          {/* Backend-Driven Pagination Footer */}
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border bg-muted/15 px-4 py-2.5 text-xs text-muted-foreground">
            <span>
              Showing <strong className="text-foreground">{startRow}–{endRow}</strong> of{" "}
              <strong className="text-foreground">{total}</strong> discoveries
            </span>
            <div className="flex items-center gap-1.5">
              <Button
                size="sm"
                variant="outline"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="h-7 px-2.5 text-xs gap-1"
              >
                <ChevronLeft size={13} /> Previous
              </Button>
              <span className="px-2 text-xs font-medium text-foreground">
                Page {page} of {totalPages}
              </span>
              <Button
                size="sm"
                variant="outline"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                className="h-7 px-2.5 text-xs gap-1"
              >
                Next <ChevronRight size={13} />
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Rename Modal */}
      {renamingRun && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-4"
          role="dialog"
          aria-modal="true"
          aria-label="Rename discovery"
          onClick={() => setRenamingRun(null)}
        >
          <div
            className="w-full max-w-md rounded-2xl border border-border bg-card p-5 shadow-2xl space-y-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div>
              <h3 className="text-sm font-semibold text-foreground">Rename Discovery</h3>
              <p className="text-xs text-muted-foreground mt-0.5">
                Updates the display title in History. Original search criteria remain immutable.
              </p>
            </div>
            <input
              autoFocus
              value={renameValue}
              maxLength={120}
              onChange={(e) => setRenameValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") void confirmRename();
              }}
              className="h-9 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            />
            <div className="flex justify-end gap-2">
              <Button size="sm" variant="outline" onClick={() => setRenamingRun(null)}>
                Cancel
              </Button>
              <Button size="sm" disabled={!renameValue.trim() || mutation.isPending} onClick={() => void confirmRename()}>
                Save Title
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deletingRun && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-4"
          role="dialog"
          aria-modal="true"
          aria-label="Delete discovery history entry"
          onClick={() => setDeletingRun(null)}
        >
          <div
            className="w-full max-w-md rounded-2xl border border-border bg-card p-5 shadow-2xl space-y-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div>
              <h3 className="text-sm font-semibold text-foreground">Remove from Discovery History?</h3>
              <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                “{deletingRun.title}” will be removed from Discovery History. Any saved or discovered signals remain intact in Signals.
              </p>
            </div>
            <div className="flex justify-end gap-2">
              <Button size="sm" variant="outline" onClick={() => setDeletingRun(null)}>
                Cancel
              </Button>
              <Button size="sm" variant="destructive" disabled={mutation.isPending} onClick={() => void confirmDelete()}>
                Remove Entry
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* View Search Configuration Modal */}
      {viewingConfigRun && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-4 backdrop-blur-[1px]"
          role="dialog"
          aria-modal="true"
          aria-label="Search Configuration"
          onClick={() => setViewingConfigRun(null)}
        >
          <div
            className="w-full max-w-xl rounded-2xl border border-border bg-card p-5 shadow-2xl space-y-4 max-h-[85vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between gap-3 border-b border-border pb-3">
              <div>
                <h3 className="text-sm font-semibold text-foreground">Search Configuration</h3>
                <p className="text-xs text-muted-foreground mt-0.5 truncate max-w-md">
                  {viewingConfigRun.title}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setViewingConfigRun(null)}
                className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground cursor-pointer"
              >
                <X size={15} />
              </button>
            </div>

            <div className="space-y-3.5 text-xs">
              {viewingConfigRun.original_prompt && (
                <div className="rounded-xl border border-border bg-muted/20 p-3">
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Original Search Prompt</span>
                  <p className="mt-1 text-foreground leading-relaxed italic">
                    “{viewingConfigRun.original_prompt}”
                  </p>
                </div>
              )}

              <div>
                <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground block mb-1">Keywords</span>
                <div className="flex flex-wrap gap-1.5">
                  {viewingConfigRun.keywords.map((kw) => (
                    <span key={kw} className="rounded-md bg-primary/10 px-2 py-0.5 text-[11px] font-medium text-primary">
                      {kw}
                    </span>
                  ))}
                </div>
              </div>

              <div>
                <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground block mb-1">Sources Queried</span>
                <div className="flex flex-wrap gap-1.5">
                  {viewingConfigRun.sources.map((src) => (
                    <span key={src} className="inline-flex items-center gap-1.5 rounded-md border border-border bg-background px-2 py-1 text-xs font-medium text-foreground">
                      <ProviderLogo provider={src} size={14} />
                      {SOURCE_LABELS[src] || src}
                    </span>
                  ))}
                </div>
              </div>

              {viewingConfigRun.configuration.excluded?.length > 0 && (
                <div>
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground block mb-1">Negative Exclusions</span>
                  <div className="flex flex-wrap gap-1.5">
                    {viewingConfigRun.configuration.excluded.map((ex) => (
                      <span key={ex} className="rounded-md bg-destructive/10 px-2 py-0.5 text-[11px] font-medium text-destructive">
                        {ex}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              <dl className="grid grid-cols-2 gap-3 pt-1 border-t border-border">
                <div className="rounded-lg border border-border/70 p-2.5">
                  <dt className="text-[10px] uppercase font-semibold text-muted-foreground">Min Relevance</dt>
                  <dd className="text-sm font-semibold text-foreground mt-0.5">{viewingConfigRun.configuration.min_relevance || 0}/100</dd>
                </div>
                <div className="rounded-lg border border-border/70 p-2.5">
                  <dt className="text-[10px] uppercase font-semibold text-muted-foreground">Result Limit</dt>
                  <dd className="text-sm font-semibold text-foreground mt-0.5">{viewingConfigRun.configuration.result_limit || 20}</dd>
                </div>
              </dl>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-border">
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  const run = viewingConfigRun;
                  setViewingConfigRun(null);
                  reuseInBuilder(run);
                }}
                className="gap-1.5 text-xs"
              >
                <RotateCcw size={13} /> Open in Builder
              </Button>
              <Button
                size="sm"
                onClick={() => {
                  const id = viewingConfigRun.id;
                  setViewingConfigRun(null);
                  openRun(id);
                }}
                className="gap-1.5 text-xs"
              >
                <Eye size={13} /> Open Results
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
