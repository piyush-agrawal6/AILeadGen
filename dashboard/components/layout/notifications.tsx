"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  Bell,
  CheckCheck,
  CheckCircle2,
  CreditCard,
  Radio,
  Search,
  Shield,
  Sparkles,
  Target,
} from "lucide-react";
import { toast } from "sonner";
import { Menu, MenuContent } from "@/components/ui/menu";
import { request } from "@/lib/intelligence";
import { useWorkspace } from "@/components/workspaces/use-workspace";

export type WorkspaceNotification = {
  id: string;
  kind: string;
  category?: string;
  priority?: "low" | "normal" | "high" | "urgent" | string;
  severity?: "error" | "warning" | "success" | "info" | string;
  title?: string;
  description?: string;
  url?: string;
  read_at?: string | null;
  created_at: string;
};

export type NotificationListResponse = {
  items: WorkspaceNotification[];
  unread_count?: number;
  category_counts?: Record<string, number>;
  unread_by_category?: Record<string, number>;
  total?: number;
  page?: number;
  page_size?: number;
  has_more?: boolean;
};

function categoryIcon(cat?: string, severity?: string) {
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
      return Bell;
  }
}

function severityBadgeClass(severity?: string, priority?: string) {
  if (severity === "error" || priority === "urgent") {
    return "border-destructive/35 bg-destructive/10 text-destructive";
  }
  if (severity === "warning" || priority === "high") {
    return "border-amber-500/35 bg-amber-500/10 text-amber-600 dark:text-amber-400";
  }
  if (severity === "success") {
    return "border-emerald-500/35 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400";
  }
  return "border-border bg-muted/40 text-muted-foreground";
}

function relativeTime(iso: string): string {
  try {
    const diff = Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 1000));
    if (diff < 60) return "Just now";
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
  } catch {
    return iso;
  }
}

export function Notifications() {
  const client = useQueryClient();
  const workspace = useWorkspace();
  const orgId = workspace.data?.active_organization_id || "";
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState<"all" | "unread">("all");
  const [busy, setBusy] = useState(false);

  const query = useQuery({
    queryKey: ["workspace-notifications", orgId, tab],
    queryFn: ({ signal }) =>
      request<NotificationListResponse>(
        `/organization/notifications?page=1&page_size=12&status=${tab}`,
        { signal }
      ),
    enabled: Boolean(orgId),
    retry: false,
    refetchInterval: 45000,
    staleTime: 15000,
  });

  const items = query.data?.items || [];
  const unreadCount =
    query.data?.unread_count ?? items.filter((i) => !i.read_at).length;

  async function syncCaches() {
    await Promise.all([
      client.invalidateQueries({ queryKey: ["workspace-notifications"] }),
      client.invalidateQueries({ queryKey: ["notifications-page"] }),
    ]);
  }

  async function markRead(id: string) {
    try {
      await request(`/organization/notifications/${id}/read`, { method: "POST" });
      await syncCaches();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not mark notification as read.");
    }
  }

  async function markAllRead() {
    setBusy(true);
    try {
      const res = await request<{ marked_read: number }>("/organization/notifications/read-all", {
        method: "POST",
      });
      await syncCaches();
      if (res.marked_read > 0) {
        toast.success(`Marked ${res.marked_read} notification${res.marked_read === 1 ? "" : "s"} as read.`);
      }
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not mark all notifications as read.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Menu.Root open={open} onOpenChange={setOpen}>
      <Menu.Trigger asChild>
        <button
          type="button"
          className="shell-icon-button relative"
          aria-label={
            unreadCount > 0
              ? `Workspace notifications (${unreadCount} unread)`
              : "Workspace notifications"
          }
        >
          <Bell size={18} />
          {unreadCount > 0 && (
            <span
              aria-hidden="true"
              className="absolute -top-0.5 -right-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-1 text-[10px] font-bold text-primary-foreground tabular-nums"
            >
              {unreadCount > 99 ? "99+" : unreadCount}
            </span>
          )}
        </button>
      </Menu.Trigger>

      <MenuContent align="end" className="w-96 max-w-[calc(100vw-24px)] p-0 overflow-hidden">
        <div className="flex items-center justify-between border-b border-border px-3.5 py-2.5">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-foreground">Notifications</span>
            {unreadCount > 0 && (
              <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-semibold text-primary tabular-nums">
                {unreadCount} unread
              </span>
            )}
          </div>
          {unreadCount > 0 && (
            <button
              type="button"
              disabled={busy}
              onClick={() => void markAllRead()}
              className="inline-flex items-center gap-1 text-[11px] font-medium text-primary hover:underline cursor-pointer disabled:opacity-50"
            >
              <CheckCheck size={12} /> Mark all read
            </button>
          )}
        </div>

        <div className="flex items-center gap-1 border-b border-border/70 bg-muted/20 px-3 py-1.5" role="tablist" aria-label="Notification filter">
          {(["all", "unread"] as const).map((mode) => (
            <button
              key={mode}
              type="button"
              role="tab"
              aria-selected={tab === mode}
              onClick={() => setTab(mode)}
              className={
                "rounded-md px-2.5 py-1 text-[11px] font-medium transition-colors cursor-pointer " +
                (tab === mode
                  ? "bg-card text-foreground shadow-xs border border-border/80 font-semibold"
                  : "text-muted-foreground hover:text-foreground")
              }
            >
              {mode === "all" ? "All" : `Unread${unreadCount > 0 ? ` (${unreadCount})` : ""}`}
            </button>
          ))}
        </div>

        {query.isPending ? (
          <p role="status" className="p-4 text-xs text-muted-foreground">
            Loading notifications…
          </p>
        ) : query.isError ? (
          <div className="p-4 space-y-2">
            <p role="alert" className="text-xs text-destructive">
              Notifications could not be loaded.
            </p>
            <button
              type="button"
              onClick={() => void query.refetch()}
              className="text-xs font-medium text-primary hover:underline cursor-pointer"
            >
              Retry
            </button>
          </div>
        ) : items.length === 0 ? (
          <div className="p-6 text-center space-y-1">
            <Bell size={18} className="mx-auto text-muted-foreground" aria-hidden="true" />
            <p className="text-xs font-medium text-foreground">
              {tab === "unread" ? "No unread notifications" : "You're all caught up"}
            </p>
            <p className="text-[11px] text-muted-foreground">
              Discovery completions, monitor findings, AI actions, billing, and security events appear here.
            </p>
          </div>
        ) : (
          <div className="max-h-96 overflow-y-auto divide-y divide-border/70">
            {items.map((item) => {
              const Icon = categoryIcon(item.category, item.severity);
              const isUnread = !item.read_at;
              const href = item.url || "/notifications";
              const fallbackTitle =
                item.title ||
                (item.kind === "INVITATION_ACCEPTED"
                  ? "A teammate accepted an invitation"
                  : item.kind === "INVITATION_REJECTED"
                    ? "A teammate declined an invitation"
                    : item.kind === "INTENT_RADAR"
                      ? "Intent Radar activity recorded"
                      : "Workspace activity recorded");

              return (
                <div
                  key={item.id}
                  className={
                    "flex items-start gap-2.5 px-3.5 py-2.5 transition-colors hover:bg-muted/35 " +
                    (isUnread ? "bg-primary/[0.03]" : "")
                  }
                >
                  <div
                    className={
                      "mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border " +
                      severityBadgeClass(item.severity, item.priority)
                    }
                  >
                    <Icon size={13} aria-hidden="true" />
                  </div>
                  <div className="min-w-0 flex-1 space-y-0.5">
                    <div className="flex items-start justify-between gap-2">
                      <Link
                        href={href}
                        onClick={() => {
                          if (isUnread) void markRead(item.id);
                          setOpen(false);
                        }}
                        className="text-xs font-semibold text-foreground hover:text-primary line-clamp-1"
                      >
                        {fallbackTitle}
                      </Link>
                      {isUnread && (
                        <span
                          className="mt-1 h-2 w-2 shrink-0 rounded-full bg-primary"
                          aria-label="Unread"
                        />
                      )}
                    </div>
                    {item.description && (
                      <p className="text-[11px] text-muted-foreground line-clamp-2 leading-snug">
                        {item.description}
                      </p>
                    )}
                    <div className="flex items-center justify-between pt-0.5 text-[10px] text-muted-foreground">
                      <span className="flex items-center gap-1.5">
                        <span>{relativeTime(item.created_at)}</span>
                        {item.category && (
                          <span className="capitalize text-muted-foreground/80">· {item.category}</span>
                        )}
                      </span>
                      {isUnread && (
                        <button
                          type="button"
                          onClick={() => void markRead(item.id)}
                          className="text-primary hover:underline cursor-pointer"
                        >
                          Mark read
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        <div className="flex items-center justify-between border-t border-border bg-muted/20 px-3.5 py-2.5 text-xs">
          <Link
            href="/notifications"
            onClick={() => setOpen(false)}
            className="font-semibold text-primary hover:underline"
          >
            View all notifications
          </Link>
          <Link
            href="/settings?category=preferences&tab=notifications"
            onClick={() => setOpen(false)}
            className="text-muted-foreground hover:text-foreground"
          >
            Preferences
          </Link>
        </div>
      </MenuContent>
    </Menu.Root>
  );
}
