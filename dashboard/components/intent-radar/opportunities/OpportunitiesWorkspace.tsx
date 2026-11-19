"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  ArrowLeft,
  ArrowRight,
  ChevronLeft,
  ChevronRight,
  Loader2,
  MoreHorizontal,
  Pencil,
  RefreshCw,
  Search,
  SlidersHorizontal,
  Target,
  Trash2,
  UserCheck,
  UserX,
  X,
} from "lucide-react";
import type { IntentOpportunity, IntentPage } from "@/lib/intent-radar";
import { useRadarCapabilities, useRadarMutation, useRadarRead } from "../provider";
import { EmptyState, ErrorState, LoadingSkeleton } from "../ui";
import { ProviderLogo } from "../provider-logo";
import { OpportunityDetail } from "./OpportunityDetail";
import { OpportunityModal } from "./OpportunityModal";
import { request } from "@/lib/intelligence";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { StatusFilterTabs } from "@/components/ui/tabs";

type StatusTab = "all" | "New" | "Reviewing" | "Qualified" | "Saved" | "Dismissed";
type SortOption = "newest" | "updated" | "priority" | "oldest";

interface TeamMember {
  id: string;
  email: string;
  display_name: string;
  role: string;
}

const STATUS_TABS: { key: StatusTab; label: string }[] = [
  { key: "all", label: "All" },
  { key: "New", label: "New" },
  { key: "Reviewing", label: "Reviewing" },
  { key: "Qualified", label: "Qualified" },
  { key: "Saved", label: "Saved" },
  { key: "Dismissed", label: "Dismissed" },
];

const PRIORITY_STYLES: Record<string, string> = {
  High: "bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/25",
  Medium: "bg-blue-500/10 text-blue-700 dark:text-blue-300 border-blue-500/25",
  Low: "bg-muted text-muted-foreground border-border",
};

const STATUS_STYLES: Record<string, string> = {
  New: "bg-blue-500/10 text-blue-700 dark:text-blue-300 border-blue-500/20",
  Reviewing: "bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/20",
  Qualified: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/20",
  Saved: "bg-primary/10 text-primary border-primary/20",
  Dismissed: "bg-muted text-muted-foreground border-border",
};

const COMMON_SOURCES = [
  "GitHub",
  "Hacker News",
  "YouTube",
  "Bluesky",
  "Stack Exchange",
  "Discourse Communities",
  "RSS Feeds",
  "Atom Feeds",
];

function formatUpdated(iso?: string | null) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    if (diffHours < 1) return "Just now";
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 7) return `${diffDays}d ago`;
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  } catch {
    return "—";
  }
}

export function OpportunitiesWorkspace({ id }: { id?: string } = {}) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const access = useRadarCapabilities();
  const mutation = useRadarMutation();
  const canWrite = Boolean(access.data?.can_write);

  // If a specific opportunity ID is passed, render dedicated CRM Details view
  const detailQuery = useRadarRead<IntentOpportunity>(`/opportunities/${id}`, Boolean(id));

  const [statusTab, setStatusTab] = useState<StatusTab>(() => {
    const s = searchParams.get("status") || "all";
    return STATUS_TABS.some((t) => t.key === s) ? (s as StatusTab) : "all";
  });
  const [search, setSearch] = useState(() => searchParams.get("search") || "");
  const [priorityFilter, setPriorityFilter] = useState(() => searchParams.get("priority") || "");
  const [sourceFilter, setSourceFilter] = useState(() => searchParams.get("source") || "");
  const [assigneeFilter, setAssigneeFilter] = useState(() => searchParams.get("assigned_to") || "");
  const [sort, setSort] = useState<SortOption>(() => {
    const s = searchParams.get("sort") || "newest";
    return ["newest", "updated", "priority", "oldest"].includes(s)
      ? (s as SortOption)
      : "newest";
  });
  const [page, setPage] = useState<number>(() => Math.max(1, Number(searchParams.get("page") || "1") || 1));

  // Edit / Action State
  const [activeMenuId, setActiveMenuId] = useState<string | null>(null);
  const [editingOpp, setEditingOpp] = useState<IntentOpportunity | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<IntentOpportunity | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [filterPopoverOpen, setFilterPopoverOpen] = useState(false);

  const menuRef = useRef<HTMLDivElement>(null);
  const filterPopoverRef = useRef<HTMLDivElement>(null);

  // Fetch workspace members for assignee filtering
  const membersQuery = useQuery({
    queryKey: ["workspace-members"],
    queryFn: ({ signal }) =>
      request<{ items: TeamMember[] }>("/organization/members", { signal }),
    retry: false,
    enabled: !id,
  });

  // Debounced search query parameter
  const [debouncedSearch, setDebouncedSearch] = useState(search);
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 250);
    return () => clearTimeout(timer);
  }, [search]);

  // Construct URLSearchParams
  const queryString = useMemo(() => {
    const sp = new URLSearchParams();
    if (statusTab !== "all") sp.set("status", statusTab);
    if (debouncedSearch.trim()) sp.set("search", debouncedSearch.trim());
    if (priorityFilter) sp.set("priority", priorityFilter);
    if (sourceFilter) sp.set("source", sourceFilter);
    if (assigneeFilter) sp.set("assigned_to", assigneeFilter);
    if (sort !== "newest") sp.set("sort", sort);
    sp.set("page", String(page));
    sp.set("page_size", "25");
    return sp.toString();
  }, [statusTab, debouncedSearch, priorityFilter, sourceFilter, assigneeFilter, sort, page]);

  const listQuery = useRadarRead<IntentPage<IntentOpportunity>>(
    `/opportunities?${queryString}`,
    !id,
  );

  // Sync browser URL
  useEffect(() => {
    if (typeof window === "undefined" || id) return;
    const cleanQs = queryString ? `?${queryString}` : "";
    window.history.replaceState(null, "", `/intent-radar/opportunities${cleanQs}`);
  }, [queryString, id]);

  // Close 3-dot menu on click outside
  useEffect(() => {
    if (!activeMenuId) return;
    function onDocClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setActiveMenuId(null);
      }
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [activeMenuId]);

  // Close filter popover on click outside
  useEffect(() => {
    if (!filterPopoverOpen) return;
    function onDocClick(e: MouseEvent) {
      if (filterPopoverRef.current && !filterPopoverRef.current.contains(e.target as Node)) {
        setFilterPopoverOpen(false);
      }
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [filterPopoverOpen]);

  // Detail View Route
  if (id) {
    if (detailQuery.error) {
      return (
        <div className="ir-page space-y-4">
          <Link
            href="/intent-radar/opportunities"
            className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-border bg-card px-3 text-xs font-semibold text-foreground hover:border-primary/50"
          >
            <ArrowLeft size={14} /> Back to Opportunities
          </Link>
          <ErrorState
            message={detailQuery.error.message}
            retry={() => void detailQuery.refetch()}
          />
        </div>
      );
    }
    if (!detailQuery.data) {
      return (
        <div className="ir-page space-y-4">
          <Link
            href="/intent-radar/opportunities"
            className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-border bg-card px-3 text-xs font-semibold text-foreground hover:border-primary/50"
          >
            <ArrowLeft size={14} /> Back to Opportunities
          </Link>
          <LoadingSkeleton />
        </div>
      );
    }
    return (
      <div className="ir-page">
        <OpportunityDetail
          key={detailQuery.data.id}
          opportunity={detailQuery.data}
          canWrite={canWrite}
          onUpdate={async (patch) => {
            await mutation.mutateAsync({
              path: `/opportunities/${detailQuery.data.id}`,
              method: "PATCH",
              body: patch,
            });
            await detailQuery.refetch();
          }}
          onDelete={async (oppId) => {
            await mutation.mutateAsync({
              path: `/opportunities/${oppId}`,
              method: "DELETE",
            });
          }}
        />
      </div>
    );
  }

  // List View Operations
  const items = listQuery.data?.items || [];
  const total = listQuery.data?.total ?? 0;
  const statusCounts = listQuery.data?.status_counts;
  const totalPages = Math.max(1, Math.ceil(total / 25));
  const hasActiveFilters = Boolean(
    statusTab !== "all" ||
      search ||
      priorityFilter ||
      sourceFilter ||
      assigneeFilter ||
      sort !== "newest",
  );

  function clearFilters() {
    setStatusTab("all");
    setSearch("");
    setDebouncedSearch("");
    setPriorityFilter("");
    setSourceFilter("");
    setAssigneeFilter("");
    setSort("newest");
    setPage(1);
  }

  async function handleUpdateOpportunity(patch: {
    revision: number;
    status: string;
    priority: string;
    notes: string;
    next_action: string;
    assigned_to: string | null;
  }) {
    if (!editingOpp) return;
    await mutation.mutateAsync({
      path: `/opportunities/${editingOpp.id}`,
      method: "PATCH",
      body: patch,
    });
    setEditingOpp(null);
    setNotice("Opportunity updated.");
    await listQuery.refetch();
  }

  async function handleQuickStatusChange(opp: IntentOpportunity, nextStatus: string) {
    if (!canWrite) return;
    setActiveMenuId(null);
    try {
      await mutation.mutateAsync({
        path: `/opportunities/${opp.id}`,
        method: "PATCH",
        body: {
          revision: opp.revision,
          status: nextStatus,
          priority: opp.priority,
          notes: opp.notes,
          next_action: opp.next_action,
          assigned_to: opp.assigned_to,
        },
      });
      setNotice(`Updated status to ${nextStatus}.`);
      await listQuery.refetch();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not update status.");
    }
  }

  async function handleQuickPriorityChange(opp: IntentOpportunity, nextPriority: string) {
    if (!canWrite) return;
    setActiveMenuId(null);
    try {
      await mutation.mutateAsync({
        path: `/opportunities/${opp.id}`,
        method: "PATCH",
        body: {
          revision: opp.revision,
          status: opp.status,
          priority: nextPriority,
          notes: opp.notes,
          next_action: opp.next_action,
          assigned_to: opp.assigned_to,
        },
      });
      setNotice(`Updated priority to ${nextPriority}.`);
      await listQuery.refetch();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not update priority.");
    }
  }

  async function confirmDeleteOpportunity() {
    if (!deleteTarget) return;
    const oppId = deleteTarget.id;
    try {
      await mutation.mutateAsync({
        path: `/opportunities/${oppId}`,
        method: "DELETE",
      });
      setDeleteTarget(null);
      setNotice("Opportunity deleted.");
      await listQuery.refetch();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not delete opportunity.");
    }
  }

  const members = membersQuery.data?.items || [];

  return (
    <div className="ir-page space-y-4">
      {/* Header */}
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-border/70 pb-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">
            Opportunities
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Manage qualified conversations and turn them into actionable opportunities.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            href="/intent-radar/signals"
            className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-border bg-card px-3 text-xs font-semibold text-foreground hover:border-primary/50 hover:text-primary transition-colors"
          >
            <Activity size={13} />
            Review Signals
          </Link>
          <Link
            href="/intent-radar/discover"
            className="ir-button ir-primary inline-flex h-8 items-center gap-1.5 text-xs font-semibold"
          >
            <Search size={13} />
            Discover Intent
          </Link>
        </div>
      </header>

      {/* Notice Banner */}
      {notice && (
        <div
          role="status"
          className="flex items-center justify-between gap-2 rounded-xl border border-emerald-500/25 bg-emerald-500/10 px-4 py-2.5 text-xs font-medium text-emerald-700 dark:text-emerald-300"
        >
          <span>{notice}</span>
          <button
            type="button"
            onClick={() => setNotice(null)}
            className="text-muted-foreground hover:text-foreground cursor-pointer"
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* Status Workflow Tabs with Exact Real Counts */}
      <StatusFilterTabs
        items={STATUS_TABS.map((tab) => {
          const count =
            statusCounts &&
            (tab.key === "all"
              ? statusCounts.all
              : tab.key === "New"
                ? statusCounts.new
                : tab.key === "Reviewing"
                  ? statusCounts.reviewing
                  : tab.key === "Qualified"
                    ? statusCounts.qualified
                    : tab.key === "Saved"
                      ? statusCounts.saved
                      : statusCounts.dismissed);
          return {
            id: tab.key,
            label: tab.label,
            count: typeof count === "number" ? count : undefined,
          };
        })}
        activeId={statusTab}
        onChange={(id) => {
          setStatusTab(id as StatusTab);
          setPage(1);
        }}
      />

      {/* Compact Horizontal Filter & Search Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-2.5 rounded-xl border border-border bg-card p-2.5">
        <div className="flex flex-wrap items-center gap-2 flex-1 min-w-[240px]">
          {/* Search Box */}
          <div className="relative flex-1 min-w-[220px]">
            <Search size={13} className="absolute left-2.5 top-2.5 text-muted-foreground" />
            <Input
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              placeholder="Search opportunities, notes, actions…"
              className="h-8 pl-8 text-xs"
            />
            {search && (
              <button
                type="button"
                onClick={() => {
                  setSearch("");
                  setPage(1);
                }}
                className="absolute right-2.5 top-2 text-muted-foreground hover:text-foreground"
                aria-label="Clear search"
              >
                <X size={12} />
              </button>
            )}
          </div>

          {/* Filters Popover for Secondary Filters: Priority, Source, Assignee */}
          <div className="relative" ref={filterPopoverRef}>
            <button
              type="button"
              onClick={() => setFilterPopoverOpen(!filterPopoverOpen)}
              className={`inline-flex h-8 items-center gap-1.5 rounded-lg border px-3 text-xs font-medium transition-colors cursor-pointer ${
                priorityFilter || sourceFilter || assigneeFilter
                  ? "border-primary/50 bg-primary/10 text-primary font-semibold"
                  : "border-border bg-background text-foreground hover:bg-muted"
              }`}
            >
              <SlidersHorizontal size={13} />
              <span>Filters</span>
              {(priorityFilter || sourceFilter || assigneeFilter) && (
                <span className="flex h-4 w-4 items-center justify-center rounded-full bg-primary text-[10px] text-primary-foreground">
                  {(priorityFilter ? 1 : 0) + (sourceFilter ? 1 : 0) + (assigneeFilter ? 1 : 0)}
                </span>
              )}
            </button>

            {filterPopoverOpen && (
              <div className="absolute right-0 sm:left-0 top-full mt-1.5 z-40 w-72 rounded-xl border border-border bg-popover p-3.5 shadow-xl space-y-3.5 text-xs animate-in fade-in-50">
                <div className="flex items-center justify-between border-b border-border/80 pb-2">
                  <span className="font-semibold text-foreground">Filters</span>
                  {(priorityFilter || sourceFilter || assigneeFilter) && (
                    <button
                      type="button"
                      onClick={() => {
                        setPriorityFilter("");
                        setSourceFilter("");
                        setAssigneeFilter("");
                        setPage(1);
                      }}
                      className="text-[11px] font-medium text-primary hover:underline cursor-pointer"
                    >
                      Reset All
                    </button>
                  )}
                </div>

                {/* Priority Filter */}
                <div className="space-y-1">
                  <label className="text-[11px] font-medium text-muted-foreground block">
                    Priority
                  </label>
                  <select
                    aria-label="Filter by priority"
                    value={priorityFilter}
                    onChange={(e) => {
                      setPriorityFilter(e.target.value);
                      setPage(1);
                    }}
                    className="w-full h-8 rounded-lg border border-border bg-background px-2.5 text-xs text-foreground cursor-pointer focus:border-primary focus:outline-none"
                  >
                    <option value="">All Priorities</option>
                    <option value="High">High Priority</option>
                    <option value="Medium">Medium Priority</option>
                    <option value="Low">Low Priority</option>
                  </select>
                </div>

                {/* Source Filter */}
                <div className="space-y-1">
                  <label className="text-[11px] font-medium text-muted-foreground block">
                    Source Platform
                  </label>
                  <select
                    aria-label="Filter by source"
                    value={sourceFilter}
                    onChange={(e) => {
                      setSourceFilter(e.target.value);
                      setPage(1);
                    }}
                    className="w-full h-8 rounded-lg border border-border bg-background px-2.5 text-xs text-foreground cursor-pointer focus:border-primary focus:outline-none"
                  >
                    <option value="">All Sources</option>
                    {COMMON_SOURCES.map((src) => (
                      <option key={src} value={src}>
                        {src}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Assignee Filter */}
                <div className="space-y-1">
                  <label className="text-[11px] font-medium text-muted-foreground block">
                    Assigned Owner
                  </label>
                  <select
                    aria-label="Filter by assignee"
                    value={assigneeFilter}
                    onChange={(e) => {
                      setAssigneeFilter(e.target.value);
                      setPage(1);
                    }}
                    className="w-full h-8 rounded-lg border border-border bg-background px-2.5 text-xs text-foreground cursor-pointer focus:border-primary focus:outline-none"
                  >
                    <option value="">All Assignees</option>
                    <option value="unassigned">Unassigned</option>
                    {members.map((m) => (
                      <option key={m.email} value={m.email}>
                        {m.display_name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Sort Option */}
          <select
            aria-label="Sort opportunities"
            value={sort}
            onChange={(e) => setSort(e.target.value as SortOption)}
            className="h-8 rounded-lg border border-border bg-background px-2.5 text-xs text-foreground cursor-pointer focus:border-primary focus:outline-none"
          >
            <option value="newest">Sort: Newest</option>
            <option value="updated">Sort: Recently Updated</option>
            <option value="priority">Sort: Priority</option>
            <option value="oldest">Sort: Oldest</option>
          </select>

          {hasActiveFilters && (
            <Button
              size="sm"
              variant="ghost"
              onClick={clearFilters}
              className="h-8 px-2 text-xs text-muted-foreground hover:text-foreground gap-1"
            >
              <X size={12} /> Clear
            </Button>
          )}
        </div>
      </div>

      {/* Active Filter Chips Strip */}
      {hasActiveFilters && (
        <div className="flex flex-wrap items-center justify-between gap-2 px-1 text-xs">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-[11px] font-medium text-muted-foreground mr-1">Active filters:</span>
            {search && (
              <span className="inline-flex items-center gap-1 rounded-md border border-border bg-muted/40 px-2 py-0.5 text-xs text-foreground">
                <span>Search: &ldquo;{search}&rdquo;</span>
                <button
                  type="button"
                  onClick={() => {
                    setSearch("");
                    setPage(1);
                  }}
                  className="text-muted-foreground hover:text-foreground cursor-pointer"
                >
                  <X size={11} />
                </button>
              </span>
            )}
            {statusTab !== "all" && (
              <span className="inline-flex items-center gap-1 rounded-md border border-border bg-muted/40 px-2 py-0.5 text-xs text-foreground">
                <span>Status: {statusTab}</span>
                <button
                  type="button"
                  onClick={() => {
                    setStatusTab("all");
                    setPage(1);
                  }}
                  className="text-muted-foreground hover:text-foreground cursor-pointer"
                >
                  <X size={11} />
                </button>
              </span>
            )}
            {priorityFilter && (
              <span className="inline-flex items-center gap-1 rounded-md border border-border bg-muted/40 px-2 py-0.5 text-xs text-foreground">
                <span>Priority: {priorityFilter}</span>
                <button
                  type="button"
                  onClick={() => {
                    setPriorityFilter("");
                    setPage(1);
                  }}
                  className="text-muted-foreground hover:text-foreground cursor-pointer"
                >
                  <X size={11} />
                </button>
              </span>
            )}
            {sourceFilter && (
              <span className="inline-flex items-center gap-1 rounded-md border border-border bg-muted/40 px-2 py-0.5 text-xs text-foreground">
                <span>Source: {sourceFilter}</span>
                <button
                  type="button"
                  onClick={() => {
                    setSourceFilter("");
                    setPage(1);
                  }}
                  className="text-muted-foreground hover:text-foreground cursor-pointer"
                >
                  <X size={11} />
                </button>
              </span>
            )}
            {assigneeFilter && (
              <span className="inline-flex items-center gap-1 rounded-md border border-border bg-muted/40 px-2 py-0.5 text-xs text-foreground">
                <span>
                  Assignee:{" "}
                  {assigneeFilter === "unassigned"
                    ? "Unassigned"
                    : members.find((m) => m.email === assigneeFilter)?.display_name || assigneeFilter}
                </span>
                <button
                  type="button"
                  onClick={() => {
                    setAssigneeFilter("");
                    setPage(1);
                  }}
                  className="text-muted-foreground hover:text-foreground cursor-pointer"
                >
                  <X size={11} />
                </button>
              </span>
            )}
            {sort !== "newest" && (
              <span className="inline-flex items-center gap-1 rounded-md border border-border bg-muted/40 px-2 py-0.5 text-xs text-foreground">
                <span>Sort: {sort}</span>
                <button
                  type="button"
                  onClick={() => {
                    setSort("newest");
                    setPage(1);
                  }}
                  className="text-muted-foreground hover:text-foreground cursor-pointer"
                >
                  <X size={11} />
                </button>
              </span>
            )}
            <button
              type="button"
              onClick={clearFilters}
              className="text-[11px] font-semibold text-primary hover:underline ml-1 cursor-pointer"
            >
              Clear all
            </button>
          </div>

          <span className="text-[11px] text-muted-foreground tabular-nums">
            {total} {total === 1 ? "opportunity" : "opportunities"}
          </span>
        </div>
      )}

      {/* Main Table View */}
      {listQuery.isPending ? (
        <div role="status" className="rounded-2xl border border-border bg-card p-8 text-xs text-muted-foreground text-center">
          <Loader2 size={18} className="animate-spin mx-auto mb-2 text-primary" />
          Loading opportunities…
        </div>
      ) : listQuery.isError ? (
        <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-destructive/25 bg-destructive/5 p-5 text-xs text-destructive">
          <span>{listQuery.error.message || "Could not load opportunities."}</span>
          <Button size="sm" variant="outline" onClick={() => void listQuery.refetch()}>
            <RefreshCw size={12} className="mr-1" /> Retry
          </Button>
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          icon={Target}
          title={hasActiveFilters ? "No opportunities match your filters" : "No opportunities created yet"}
          description={
            hasActiveFilters
              ? "Try switching tabs, clearing keywords, or resetting your filter criteria."
              : "Review high-intent signals and promote promising discussions into actionable opportunities."
          }
          action={
            hasActiveFilters ? (
              <Button size="sm" variant="outline" onClick={clearFilters}>
                Clear filters
              </Button>
            ) : (
              <Link className="ir-button ir-primary text-xs" href="/intent-radar/signals">
                Explore Intent Signals <ArrowRight size={14} className="ml-1" />
              </Link>
            )
          }
        />
      ) : (
        <section className="rounded-2xl border border-border bg-card overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse" aria-label="Opportunities list">
              <thead className="bg-muted/40 text-[11px] font-semibold text-muted-foreground border-b border-border">
                <tr>
                  <th scope="col" className="px-4 py-2.5 min-w-[260px] max-w-sm">
                    Opportunity
                  </th>
                  <th scope="col" className="px-4 py-2.5 w-36 whitespace-nowrap">
                    Source
                  </th>
                  <th scope="col" className="px-4 py-2.5 w-24 whitespace-nowrap">
                    Priority
                  </th>
                  <th scope="col" className="px-4 py-2.5 w-28 whitespace-nowrap">
                    Status
                  </th>
                  <th scope="col" className="px-4 py-2.5 w-40">
                    Assigned To
                  </th>
                  <th scope="col" className="px-4 py-2.5 w-28 whitespace-nowrap">
                    Updated
                  </th>
                  <th scope="col" className="px-4 py-2.5 text-right w-24 whitespace-nowrap">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/70">
                {items.map((opp) => {
                  const signal = opp.signal;
                  const priorityClass = PRIORITY_STYLES[opp.priority] || PRIORITY_STYLES.Medium;
                  const statusClass = STATUS_STYLES[opp.status] || STATUS_STYLES.New;
                  const isMenuOpen = activeMenuId === opp.id;

                  return (
                    <tr
                      key={opp.id}
                      onClick={() => router.push(`/intent-radar/opportunities/${opp.id}`)}
                      className="hover:bg-muted/25 cursor-pointer transition-colors group"
                    >
                      {/* Opportunity Title & Next Action */}
                      <td className="px-4 py-3">
                        <div className="space-y-1">
                          <Link
                            href={`/intent-radar/opportunities/${opp.id}`}
                            className="font-semibold text-foreground line-clamp-2 leading-snug group-hover:text-primary transition-colors"
                            title={signal?.title || "Opportunity"}
                            onClick={(e) => e.stopPropagation()}
                          >
                            {signal?.title || "Opportunity"}
                          </Link>
                          {opp.next_action && (
                            <p className="text-[11px] text-muted-foreground truncate" title={opp.next_action}>
                              Next: {opp.next_action}
                            </p>
                          )}
                        </div>
                      </td>

                      {/* Source */}
                      <td className="px-4 py-3">
                        {signal?.source ? (
                          <span className="inline-flex items-center gap-1.5 text-foreground font-medium whitespace-nowrap">
                            <ProviderLogo provider={signal.source} size={16} />
                            <span className="truncate">{signal.source}</span>
                          </span>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </td>

                      {/* Priority */}
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span
                          className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold ${priorityClass}`}
                        >
                          {opp.priority}
                        </span>
                      </td>

                      {/* Status */}
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span
                          className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold ${statusClass}`}
                        >
                          {opp.status}
                        </span>
                      </td>

                      {/* Assigned Reviewer */}
                      <td className="px-4 py-3">
                        {opp.assigned_to ? (
                          <span
                            className="inline-flex items-center gap-1 text-xs text-foreground font-medium truncate max-w-[150px]"
                            title={opp.assigned_to}
                          >
                            <UserCheck size={12} className="text-primary shrink-0" />
                            <span className="truncate">{opp.assigned_to.split("@")[0]}</span>
                          </span>
                        ) : (
                          <span className="text-[11px] text-muted-foreground/70 italic flex items-center gap-1">
                            <UserX size={11} /> Unassigned
                          </span>
                        )}
                      </td>

                      {/* Updated Date */}
                      <td className="px-4 py-3 text-muted-foreground whitespace-nowrap tabular-nums">
                        {formatUpdated(opp.updated_at || opp.created_at)}
                      </td>

                      {/* Action Menu */}
                      <td className="px-4 py-3 text-right whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                        <div className="relative inline-flex items-center gap-1">
                          <Link
                            href={`/intent-radar/opportunities/${opp.id}`}
                            className="inline-flex h-7 items-center rounded-md border border-border bg-card px-2.5 text-[11px] font-medium text-foreground hover:bg-muted transition-colors"
                          >
                            Open
                          </Link>

                          {/* 3-Dot Dropdown */}
                          <div className="relative">
                            <button
                              type="button"
                              aria-label={`Actions for opportunity ${opp.id}`}
                              onClick={() =>
                                setActiveMenuId((prev) => (prev === opp.id ? null : opp.id))
                              }
                              className="inline-flex h-7 w-7 items-center justify-center rounded-md border border-border bg-card text-muted-foreground hover:text-foreground hover:bg-muted cursor-pointer"
                            >
                              <MoreHorizontal size={14} />
                            </button>

                            {isMenuOpen && (
                              <div
                                ref={menuRef}
                                className="absolute right-0 top-8 z-50 w-48 rounded-xl border border-border bg-card p-1.5 shadow-xl text-xs space-y-0.5"
                              >
                                <button
                                  type="button"
                                  onClick={() => router.push(`/intent-radar/opportunities/${opp.id}`)}
                                  className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left text-foreground hover:bg-muted cursor-pointer"
                                >
                                  <Target size={13} className="text-primary" /> View Details
                                </button>
                                {canWrite && (
                                  <button
                                    type="button"
                                    onClick={() => {
                                      setActiveMenuId(null);
                                      setEditingOpp(opp);
                                    }}
                                    className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left text-foreground hover:bg-muted cursor-pointer"
                                  >
                                    <Pencil size={13} /> Edit Opportunity
                                  </button>
                                )}
                                {signal?.id && (
                                  <Link
                                    href={`/intent-radar/signals/${signal.id}`}
                                    className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left text-foreground hover:bg-muted"
                                  >
                                    <Activity size={13} /> View Original Signal
                                  </Link>
                                )}
                                <div className="border-t border-border/70 my-1" />
                                {canWrite && (
                                  <>
                                    <div className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                                      Quick Priority
                                    </div>
                                    {(["High", "Medium", "Low"] as const).map((pr) => (
                                      <button
                                        key={pr}
                                        type="button"
                                        disabled={opp.priority === pr}
                                        onClick={() => void handleQuickPriorityChange(opp, pr)}
                                        className={`flex w-full items-center gap-2 rounded-md px-2 py-1 text-left text-[11px] cursor-pointer ${
                                          opp.priority === pr
                                            ? "font-semibold text-primary"
                                            : "text-foreground hover:bg-muted"
                                        }`}
                                      >
                                        <span className="h-1.5 w-1.5 rounded-full bg-current" />
                                        {pr} Priority
                                      </button>
                                    ))}
                                    <div className="border-t border-border/70 my-1" />
                                    <div className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                                      Quick Status
                                    </div>
                                    {(["New", "Reviewing", "Qualified", "Saved", "Dismissed"] as const).map(
                                      (st) => (
                                        <button
                                          key={st}
                                          type="button"
                                          disabled={opp.status === st}
                                          onClick={() => void handleQuickStatusChange(opp, st)}
                                          className={`flex w-full items-center gap-2 rounded-md px-2 py-1 text-left text-[11px] cursor-pointer ${
                                            opp.status === st
                                              ? "font-semibold text-primary"
                                              : "text-foreground hover:bg-muted"
                                          }`}
                                        >
                                          <span className="h-1.5 w-1.5 rounded-full bg-current" />
                                          {st}
                                        </button>
                                      ),
                                    )}
                                    <div className="border-t border-border/70 my-1" />
                                    <button
                                      type="button"
                                      onClick={() => {
                                        setActiveMenuId(null);
                                        setDeleteTarget(opp);
                                      }}
                                      className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left text-destructive hover:bg-destructive/10 cursor-pointer"
                                    >
                                      <Trash2 size={13} /> Delete Opportunity
                                    </button>
                                  </>
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination Strip */}
          <div className="flex items-center justify-between border-t border-border/70 px-4 py-3 text-xs text-muted-foreground">
            <span>
              Showing {(page - 1) * 25 + 1}–{Math.min(page * 25, total)} of {total.toLocaleString()} opportunities
            </span>
            <div className="flex items-center gap-1.5">
              <Button
                size="sm"
                variant="outline"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="h-7 px-2.5 text-xs"
              >
                <ChevronLeft size={13} className="mr-1" /> Previous
              </Button>
              <span className="px-2 font-medium text-foreground">
                Page {page} of {totalPages}
              </span>
              <Button
                size="sm"
                variant="outline"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                className="h-7 px-2.5 text-xs"
              >
                Next <ChevronRight size={13} className="ml-1" />
              </Button>
            </div>
          </div>
        </section>
      )}

      {/* Edit Details Modal */}
      <OpportunityModal
        opportunity={editingOpp}
        open={Boolean(editingOpp)}
        onOpenChange={(o) => !o && setEditingOpp(null)}
        canWrite={canWrite}
        onSave={handleUpdateOpportunity}
      />

      {/* Delete Confirmation Modal */}
      {deleteTarget && (
        <div
          role="alertdialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-[1px] p-4"
        >
          <div className="w-full max-w-md rounded-2xl border border-border bg-card p-5 shadow-2xl space-y-4 text-xs">
            <h3 className="text-base font-semibold text-foreground">
              Delete Opportunity?
            </h3>
            <p className="text-muted-foreground leading-relaxed">
              Are you sure you want to delete this opportunity? The underlying public intent signal and its review history will remain intact.
            </p>
            <div className="flex items-center justify-end gap-2 pt-1">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setDeleteTarget(null)}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => void confirmDeleteOpportunity()}
              >
                Delete
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
