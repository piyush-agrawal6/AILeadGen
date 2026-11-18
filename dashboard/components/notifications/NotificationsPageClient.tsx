"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  Bell,
  CheckCheck,
  ChevronLeft,
  ChevronRight,
  CreditCard,
  Radio,
  Search,
  Settings2,
  Shield,
  Sparkles,
  Target,
} from "lucide-react";
import { toast } from "sonner";
import { request } from "@/lib/intelligence";
import { Button } from "@/components/ui/button";
import type { NotificationListResponse } from "@/components/layout/notifications";

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

function iconFor(cat?: string) {
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
      return Bell;
  }
}

export function NotificationsPageClient() {
  const client = useQueryClient();
  const [category, setCategory] = useState("all");
  const [status, setStatus] = useState<"all" | "unread" | "read">("all");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [busy, setBusy] = useState(false);

  const query = useQuery({
    queryKey: ["notifications-page", category, status, search, page],
    queryFn: () => {
      const qs = new URLSearchParams({
        page: String(page),
        page_size: "20",
        status,
      });
      if (category !== "all") qs.set("category", category);
      if (search.trim()) qs.set("search", search.trim());
      return request<NotificationListResponse>(`/organization/notifications?${qs.toString()}`);
    },
    retry: false,
  });

  async function markRead(id: string) {
    try {
      await request(`/organization/notifications/${id}/read`, { method: "POST" });
      await Promise.all([
        client.invalidateQueries({ queryKey: ["notifications-page"] }),
        client.invalidateQueries({ queryKey: ["workspace-notifications"] }),
      ]);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not update notification.");
    }
  }

  async function markAllRead() {
    setBusy(true);
    try {
      const res = await request<{ marked_read: number }>("/organization/notifications/read-all", {
        method: "POST",
      });
      toast.success(
        res.marked_read > 0
          ? `Marked ${res.marked_read} notification${res.marked_read === 1 ? "" : "s"} as read.`
          : "All notifications are already read."
      );
      await Promise.all([
        client.invalidateQueries({ queryKey: ["notifications-page"] }),
        client.invalidateQueries({ queryKey: ["workspace-notifications"] }),
      ]);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not mark all notifications as read.");
    } finally {
      setBusy(false);
    }
  }

  const items = query.data?.items || [];
  const unread = query.data?.unread_count ?? 0;
  const total = query.data?.total ?? 0;

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Bell size={20} className="text-primary" aria-hidden="true" />
            <h1 className="text-2xl font-bold tracking-tight text-foreground">Notifications</h1>
            {unread > 0 && (
              <span className="rounded-full bg-primary/10 border border-primary/25 px-2.5 py-0.5 text-xs font-semibold text-primary tabular-nums">
                {unread} unread
              </span>
            )}
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            History of workspace discoveries, signal reviews, monitoring findings, AI actions, billing events, and security updates.
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
              <CheckCheck size={14} /> Mark all read
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

      {/* Filter Bar */}
      <div className="space-y-3">
        <div className="flex flex-wrap items-center gap-1.5" role="tablist" aria-label="Notification categories">
          {CATEGORIES.map((c) => (
            <button
              key={c.id}
              type="button"
              role="tab"
              aria-selected={category === c.id}
              onClick={() => {
                setCategory(c.id);
                setPage(1);
              }}
              className={
                "rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors cursor-pointer " +
                (category === c.id
                  ? "border-primary/40 bg-primary/10 text-primary font-semibold"
                  : "border-border bg-card text-muted-foreground hover:text-foreground")
              }
            >
              {c.label}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <div className="relative flex-1 min-w-[220px] max-w-md">
            <Search
              size={14}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none"
            />
            <input
              type="search"
              aria-label="Search notifications"
              placeholder="Search notifications…"
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
        </div>
      </div>

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
          <Button size="sm" variant="outline" onClick={() => void query.refetch()}>
            Retry
          </Button>
        </div>
      ) : items.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-border bg-muted/15 p-10 text-center space-y-2">
          <Bell size={24} className="mx-auto text-muted-foreground" aria-hidden="true" />
          <p className="text-sm font-semibold text-foreground">No notifications match your filters</p>
          <p className="text-xs text-muted-foreground">
            New discoveries, high-relevance signals, monitor alerts, and account events will appear here.
          </p>
        </div>
      ) : (
        <>
          <div className="divide-y divide-border rounded-2xl border border-border bg-card overflow-hidden">
            {items.map((item) => {
              const Icon = iconFor(item.category);
              const isUnread = !item.read_at;
              const isHigh = item.priority === "high" || item.priority === "urgent";
              return (
                <article
                  key={item.id}
                  className={
                    "flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 transition-colors hover:bg-muted/20 " +
                    (isUnread ? "bg-primary/[0.03]" : "")
                  }
                >
                  <div className="flex items-start gap-3 min-w-0">
                    <div
                      className={
                        "mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl border " +
                        (isHigh
                          ? "border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400"
                          : "border-border bg-muted/40 text-muted-foreground")
                      }
                    >
                      <Icon size={15} aria-hidden="true" />
                    </div>
                    <div className="min-w-0 space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <Link
                          href={item.url || "/intent-radar"}
                          onClick={() => {
                            if (isUnread) void markRead(item.id);
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
                        {isHigh && (
                          <span className="rounded-full bg-amber-500/10 border border-amber-500/30 px-2 py-0.5 text-[10px] font-semibold text-amber-700 dark:text-amber-300 capitalize">
                            {item.priority}
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

                  <div className="flex items-center gap-2 shrink-0">
                    {item.url && (
                      <Link
                        href={item.url}
                        onClick={() => {
                          if (isUnread) void markRead(item.id);
                        }}
                        className="inline-flex h-8 items-center rounded-lg border border-border bg-card px-3 text-xs font-medium text-foreground hover:border-primary/40"
                      >
                        Open
                      </Link>
                    )}
                    {isUnread && (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => void markRead(item.id)}
                        className="h-8 text-xs"
                      >
                        Mark read
                      </Button>
                    )}
                  </div>
                </article>
              );
            })}
          </div>

          {total > 20 && (
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>
                Page {page} · {total} notifications
              </span>
              <div className="flex items-center gap-1.5">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  className="h-7 gap-1"
                >
                  <ChevronLeft size={13} /> Prev
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={!query.data?.has_more}
                  onClick={() => setPage((p) => p + 1)}
                  className="h-7 gap-1"
                >
                  Next <ChevronRight size={13} />
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
