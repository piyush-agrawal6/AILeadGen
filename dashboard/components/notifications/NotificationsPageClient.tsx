"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  Bell,
  CheckCheck,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  CreditCard,
  ExternalLink,
  Info,
  MailOpen,
  Radio,
  Search,
  Settings2,
  Shield,
  Sparkles,
  Target,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { request } from "@/lib/intelligence";
import { Button } from "@/components/ui/button";
import type {
  NotificationListResponse,
  WorkspaceNotification,
} from "@/components/layout/notifications";

const CATEGORIES = [
  { id: "all", label: "All" },
  { id: "discovery", label: "Discovery" },
  { id: "signals", label: "Signals" },
  { id: "opportunities", label: "Opportunities" },
  { id: "monitoring", label: "Monitoring" },
  { id: "ai", label: "AI" },
  { id: "billing", label: "Billing" },
  { id: "security", label: "Security" },
] as const;

function iconFor(cat?: string, severity?: string) {
  if (severity === "error") return AlertCircle;
  if (severity === "warning") return AlertTriangle;
  if (severity === "success" && (cat === "discovery" || cat === "opportunities")) return CheckCircle2;
  switch (cat) {
    case "discovery":
      return Search;
    case "signals":
      return Activity;
    case "opportunities":
      return Target;
    case "monitoring":
      return Radio;
    case "ai":
      return Sparkles;
    case "billing":
      return CreditCard;
    case "security":
      return Shield;
    default:
      return Info;
  }
}

function severityStyles(severity?: string, priority?: string) {
  if (severity === "error" || priority === "urgent") {
    return {
      iconBox: "border-destructive/35 bg-destructive/10 text-destructive",
      pill: "border-destructive/30 bg-destructive/10 text-destructive",
      label: "Error",
    };
  }
  if (severity === "warning" || priority === "high") {
    return {
      iconBox: "border-amber-500/35 bg-amber-500/10 text-amber-600 dark:text-amber-400",
      pill: "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300",
      label: "Warning",
    };
  }
  if (severity === "success") {
    return {
      iconBox: "border-emerald-500/35 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
      pill: "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
      label: "Completed",
    };
  }
  return {
    iconBox: "border-border bg-muted/40 text-muted-foreground",
    pill: "border-border bg-muted text-muted-foreground",
    label: "Info",
  };
}

function dateCutoff(range: "all" | "today" | "7d" | "30d"): string | null {
  if (range === "all") return null;
  const d = new Date();
  if (range === "7d") d.setDate(d.getDate() - 7);
  if (range === "30d") d.setDate(d.getDate() - 30);
  return d.toISOString().slice(0, 10);
}

function groupByDate(items: WorkspaceNotification[]): { label: string; items: WorkspaceNotification[] }[] {
  const now = new Date();
  const todayKey = now.toISOString().slice(0, 10);
  const y = new Date(now);
  y.setDate(y.getDate() - 1);
  const yesterdayKey = y.toISOString().slice(0, 10);

  const buckets: Record<"Today" | "Yesterday" | "Earlier", WorkspaceNotification[]> = {
    Today: [],
    Yesterday: [],
    Earlier: [],
  };
  for (const item of items) {
    const day = String(item.created_at || "").slice(0, 10);
    if (day === todayKey) buckets.Today.push(item);
    else if (day === yesterdayKey) buckets.Yesterday.push(item);
    else buckets.Earlier.push(item);
  }
  return (["Today", "Yesterday", "Earlier"] as const)
    .filter((label) => buckets[label].length > 0)
    .map((label) => ({ label, items: buckets[label] }));
}

export function NotificationsPageClient() {
  const client = useQueryClient();
  const [category, setCategory] = useState("all");
  const [status, setStatus] = useState<"all" | "unread" | "read">("all");
  const [severity, setSeverity] = useState<"all" | "error" | "warning" | "success" | "info">("all");
  const [dateRange, setDateRange] = useState<"all" | "today" | "7d" | "30d">("all");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [busy, setBusy] = useState(false);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  const fromDate = dateCutoff(dateRange);

  const query = useQuery({
    queryKey: ["notifications-page", category, status, severity, fromDate, search, page],
    queryFn: () => {
      const qs = new URLSearchParams({
        page: String(page),
        page_size: "25",
        status,
      });
      if (category !== "all") qs.set("category", category);
      if (severity !== "all") qs.set("severity", severity);
      if (fromDate) qs.set("from_date", fromDate);
      if (search.trim()) qs.set("search", search.trim());
      return request<NotificationListResponse>(`/organization/notifications?${qs.toString()}`);
    },
    retry: false,
  });

  const items = useMemo(() => query.data?.items || [], [query.data?.items]);
  const unread = query.data?.unread_count ?? 0;
  const total = query.data?.total ?? 0;
  const categoryCounts = query.data?.category_counts || {};
  const unreadByCategory = query.data?.unread_by_category || {};
  const groups = useMemo(() => groupByDate(items), [items]);
  const hasFilters = category !== "all" || status !== "all" || severity !== "all" || dateRange !== "all" || search.trim() !== "";

  async function syncCaches() {
    await Promise.all([
      client.invalidateQueries({ queryKey: ["notifications-page"] }),
      client.invalidateQueries({ queryKey: ["workspace-notifications"] }),
    ]);
  }

  async function setReadState(id: string, read: boolean) {
    try {
      await request(`/organization/notifications/${id}/${read ? "read" : "unread"}`, { method: "POST" });
      await syncCaches();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not update notification.");
    }
  }

  async function markAllRead() {
    setBusy(true);
    try {
      const qs = category !== "all" ? `?category=${encodeURIComponent(category)}` : "";
      const res = await request<{ marked_read: number }>(`/organization/notifications/read-all${qs}`, {
        method: "POST",
      });
      toast.success(
        res.marked_read > 0
          ? `Marked ${res.marked_read} notification${res.marked_read === 1 ? "" : "s"} as read.`
          : "All matching notifications are already read."
      );
      setSelectedIds([]);
      await syncCaches();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not mark all notifications as read.");
    } finally {
      setBusy(false);
    }
  }

  async function runBulk(action: "read" | "unread") {
    if (!selectedIds.length) return;
    setBusy(true);
    try {
      const res = await request<{ updated: number; failed: string[] }>("/organization/notifications/bulk", {
        method: "POST",
        body: JSON.stringify({ ids: selectedIds, action }),
      });
      toast.success(
        `Marked ${res.updated} notification${res.updated === 1 ? "" : "s"} as ${action}.` +
          (res.failed.length ? ` ${res.failed.length} could not be updated.` : "")
      );
      setSelectedIds([]);
      await syncCaches();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Bulk update failed.");
    } finally {
      setBusy(false);
    }
  }

  function toggleSelect(id: string) {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  function toggleSelectAllPage() {
    const pageIds = items.map((i) => i.id);
    const allSelected = pageIds.length > 0 && pageIds.every((id) => selectedIds.includes(id));
    setSelectedIds(allSelected ? [] : pageIds);
  }

  function clearFilters() {
    setCategory("all");
    setStatus("all");
    setSeverity("all");
    setDateRange("all");
    setSearch("");
    setPage(1);
    setSelectedIds([]);
  }

  const allPageSelected = items.length > 0 && items.every((i) => selectedIds.includes(i.id));

  return (
    <div className="space-y-5 max-w-5xl mx-auto">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <Bell size={20} className="text-primary" aria-hidden="true" />
            <h1 className="text-2xl font-bold tracking-tight text-foreground">Notifications</h1>
            {unread > 0 && (
              <span className="rounded-full bg-primary/10 border border-primary/25 px-2.5 py-0.5 text-xs font-semibold text-primary tabular-nums">
                {unread} unread
              </span>
            )}
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Verified feed of workspace discoveries, signal reviews, monitor runs, AI actions, billing, and security events.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {unread > 0 && (
            <Button
              size="sm"
              variant="outline"
              disabled={busy}
              onClick={() => void markAllRead()}
              className="gap-1.5"
            >
              <CheckCheck size={14} /> {category === "all" ? "Mark all read" : `Mark ${category} read`}
            </Button>
          )}
          <Link
            href="/settings?category=preferences&tab=notifications"
            className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border bg-card px-3 text-xs font-medium text-foreground hover:border-primary/40"
          >
            <Settings2 size={14} /> Notification Preferences
          </Link>
        </div>
      </div>

      {/* Category tabs with accurate counts */}
      <div className="space-y-3">
        <div className="flex flex-wrap items-center gap-1.5" role="tablist" aria-label="Notification categories">
          {CATEGORIES.map((c) => {
            const count = categoryCounts[c.id] ?? 0;
            const catUnread = unreadByCategory[c.id] ?? 0;
            const active = category === c.id;
            return (
              <button
                key={c.id}
                type="button"
                role="tab"
                aria-selected={active}
                onClick={() => {
                  setCategory(c.id);
                  setPage(1);
                  setSelectedIds([]);
                }}
                className={
                  "inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-medium transition-colors cursor-pointer " +
                  (active
                    ? "border-primary/40 bg-primary/10 text-primary font-semibold"
                    : "border-border bg-card text-muted-foreground hover:text-foreground")
                }
              >
                <span>{c.label}</span>
                {count > 0 && (
                  <span
                    className={
                      "rounded-full px-1.5 py-0.2 text-[10px] tabular-nums " +
                      (catUnread > 0
                        ? "bg-primary/15 text-primary font-semibold"
                        : "bg-muted text-muted-foreground")
                    }
                  >
                    {count}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Filter bar */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative flex-1 min-w-[210px] max-w-sm">
            <Search
              size={14}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none"
            />
            <input
              type="search"
              aria-label="Search notifications"
              placeholder="Search titles, details, or events…"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              className="w-full rounded-xl border border-border bg-card pl-8 pr-3 py-2 text-xs text-foreground"
            />
          </div>

          <select
            aria-label="Filter notification status"
            value={status}
            onChange={(e) => {
              setStatus(e.target.value as "all" | "unread" | "read");
              setPage(1);
            }}
            className="rounded-xl border border-border bg-card px-3 py-2 text-xs text-foreground"
          >
            <option value="all">All statuses</option>
            <option value="unread">Unread only</option>
            <option value="read">Read only</option>
          </select>

          <select
            aria-label="Filter notification severity"
            value={severity}
            onChange={(e) => {
              setSeverity(e.target.value as "all" | "error" | "warning" | "success" | "info");
              setPage(1);
            }}
            className="rounded-xl border border-border bg-card px-3 py-2 text-xs text-foreground"
          >
            <option value="all">All severities</option>
            <option value="error">Errors</option>
            <option value="warning">Warnings</option>
            <option value="success">Completed</option>
            <option value="info">Info</option>
          </select>

          <select
            aria-label="Filter notification date range"
            value={dateRange}
            onChange={(e) => {
              setDateRange(e.target.value as "all" | "today" | "7d" | "30d");
              setPage(1);
            }}
            className="rounded-xl border border-border bg-card px-3 py-2 text-xs text-foreground"
          >
            <option value="all">All time</option>
            <option value="today">Today</option>
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
          </select>

          {hasFilters && (
            <Button size="sm" variant="ghost" onClick={clearFilters} className="h-8 gap-1 text-xs">
              <X size={13} /> Reset
            </Button>
          )}
        </div>
      </div>

      {/* Bulk actions bar */}
      {items.length > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-border/80 bg-muted/20 px-3.5 py-2 text-xs">
          <label className="inline-flex items-center gap-2 cursor-pointer text-muted-foreground">
            <input
              type="checkbox"
              checked={allPageSelected}
              onChange={toggleSelectAllPage}
              className="accent-primary"
              aria-label="Select all notifications on this page"
            />
            <span>
              {selectedIds.length > 0
                ? `${selectedIds.length} selected`
                : `Select page (${items.length})`}
            </span>
          </label>
          {selectedIds.length > 0 ? (
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                disabled={busy}
                onClick={() => void runBulk("read")}
                className="h-7 text-xs gap-1"
              >
                <CheckCheck size={12} /> Mark read
              </Button>
              <Button
                size="sm"
                variant="outline"
                disabled={busy}
                onClick={() => void runBulk("unread")}
                className="h-7 text-xs gap-1"
              >
                <MailOpen size={12} /> Mark unread
              </Button>
              <Button
                size="sm"
                variant="ghost"
                disabled={busy}
                onClick={() => setSelectedIds([])}
                className="h-7 text-xs"
              >
                Clear
              </Button>
            </div>
          ) : (
            <span className="text-[11px] text-muted-foreground tabular-nums">
              Showing {items.length} of {total} notification{total === 1 ? "" : "s"}
            </span>
          )}
        </div>
      )}

      {/* Notifications List */}
      {query.isPending ? (
        <div className="space-y-2.5" role="status" aria-label="Loading notifications">
          {[1, 2, 3, 4].map((n) => (
            <div key={n} className="h-20 rounded-2xl border border-border bg-muted/30 animate-pulse" />
          ))}
        </div>
      ) : query.isError ? (
        <div role="alert" className="rounded-2xl border border-destructive/25 bg-destructive/5 p-5 space-y-2">
          <p className="text-sm font-semibold text-destructive">Unable to load notifications</p>
          <p className="text-xs text-muted-foreground">
            {query.error instanceof Error ? query.error.message : "Please retry loading your notification feed."}
          </p>
          <Button size="sm" variant="outline" onClick={() => void query.refetch()}>
            Retry
          </Button>
        </div>
      ) : items.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-border bg-muted/15 p-10 text-center space-y-2">
          <Bell size={24} className="mx-auto text-muted-foreground" aria-hidden="true" />
          <p className="text-sm font-semibold text-foreground">
            {hasFilters ? "No notifications match your filters" : "No notifications yet"}
          </p>
          <p className="text-xs text-muted-foreground">
            New discoveries, high-relevance signals, monitor alerts, AI actions, and account events will appear here.
          </p>
          {hasFilters && (
            <Button size="sm" variant="outline" onClick={clearFilters} className="mt-2">
              Clear filters
            </Button>
          )}
        </div>
      ) : (
        <div className="space-y-5">
          {groups.map((group) => (
            <section key={group.label} className="space-y-2" aria-label={group.label}>
              <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground px-1">
                {group.label}
              </h2>
              <div className="divide-y divide-border rounded-2xl border border-border bg-card overflow-hidden">
                {group.items.map((item) => {
                  const Icon = iconFor(item.category, item.severity);
                  const sev = severityStyles(item.severity, item.priority);
                  const isUnread = !item.read_at;
                  const isSelected = selectedIds.includes(item.id);
                  return (
                    <article
                      key={item.id}
                      className={
                        "flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 transition-colors hover:bg-muted/20 " +
                        (isUnread ? "bg-primary/[0.03]" : "")
                      }
                    >
                      <div className="flex items-start gap-3 min-w-0">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleSelect(item.id)}
                          aria-label={`Select notification ${item.title || item.kind}`}
                          className="mt-2 accent-primary shrink-0"
                        />
                        <div
                          className={
                            "mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl border " +
                            sev.iconBox
                          }
                        >
                          <Icon size={15} aria-hidden="true" />
                        </div>
                        <div className="min-w-0 space-y-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <Link
                              href={item.url || "/intent-radar"}
                              onClick={() => {
                                if (isUnread) void setReadState(item.id, true);
                              }}
                              className="text-sm font-semibold text-foreground hover:text-primary"
                            >
                              {item.title || item.kind}
                            </Link>
                            {item.category && (
                              <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium capitalize text-muted-foreground">
                                {item.category}
                              </span>
                            )}
                            {(item.severity === "error" || item.severity === "warning" || item.severity === "success") && (
                              <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${sev.pill}`}>
                                {sev.label}
                              </span>
                            )}
                            {isUnread && (
                              <span className="h-2 w-2 rounded-full bg-primary" aria-label="Unread" />
                            )}
                          </div>
                          {item.description && (
                            <p className="text-xs text-muted-foreground leading-relaxed">
                              {item.description}
                            </p>
                          )}
                          <p className="text-[11px] text-muted-foreground">
                            {new Date(item.created_at).toLocaleString()}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 shrink-0 pl-7 sm:pl-0">
                        {item.url && (
                          <Link
                            href={item.url}
                            onClick={() => {
                              if (isUnread) void setReadState(item.id, true);
                            }}
                            className="inline-flex h-8 items-center gap-1 rounded-lg border border-border bg-card px-3 text-xs font-medium text-foreground hover:border-primary/40"
                          >
                            Open <ExternalLink size={11} aria-hidden="true" />
                          </Link>
                        )}
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => void setReadState(item.id, isUnread)}
                          className="h-8 text-xs"
                        >
                          {isUnread ? "Mark read" : "Mark unread"}
                        </Button>
                      </div>
                    </article>
                  );
                })}
              </div>
            </section>
          ))}

          {total > 25 && (
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>
                Page {page} · {total} notifications
              </span>
              <div className="flex items-center gap-1.5">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={page <= 1}
                  onClick={() => {
                    setPage((p) => Math.max(1, p - 1));
                    setSelectedIds([]);
                  }}
                  className="h-7 gap-1"
                >
                  <ChevronLeft size={13} /> Prev
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={!query.data?.has_more}
                  onClick={() => {
                    setPage((p) => p + 1);
                    setSelectedIds([]);
                  }}
                  className="h-7 gap-1"
                >
                  Next <ChevronRight size={13} />
                </Button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
