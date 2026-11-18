"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import * as Dialog from "@radix-ui/react-dialog";
import {
  CheckCircle2,
  ChevronRight,
  Download,
  FileText,
  Filter,
  Search,
  Shield,
  X,
  XCircle,
} from "lucide-react";
import { request } from "@/lib/intelligence";
import { useWorkspace } from "@/components/workspaces/use-workspace";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface AuditRecord {
  id: string;
  actor: string;
  action: string;
  entity: string;
  result: string;
  details?: Record<string, unknown> | null;
  created_at: string;
}

interface AuditPage {
  items: AuditRecord[];
  total: number;
  page: number;
  page_size: number;
}

const ACTION_LABELS: Record<string, string> = {
  ORGANIZATION_CREATED: "Created workspace",
  ORGANIZATION_RENAMED: "Renamed workspace",
  WORKSPACE_SELECTED: "Switched active workspace",
  MEMBERSHIP_ROLE_CHANGED: "Changed member role",
  MEMBERSHIP_REMOVED: "Removed workspace member",
  MEMBERSHIP_LEFT: "Left workspace",
  INVITATION_CREATED: "Sent workspace invitation",
  INVITATION_RESENT: "Resent workspace invitation",
  INVITATION_REVOKED: "Revoked invitation",
  INVITATION_ACCEPTED: "Accepted invitation",
  INVITATION_REJECTED: "Declined invitation",
  COMPANY_PROFILE_UPDATED: "Updated company profile",
  DOMAIN_CHALLENGE_CREATED: "Created DNS verification challenge",
  DOMAIN_OWNERSHIP_VERIFIED: "Verified domain ownership",
  DOMAIN_VERIFICATION_REVOKED: "Revoked domain verification",
  ONBOARDING_PROGRESS_SAVED: "Saved onboarding progress",
  ONBOARDING_COMPLETED: "Completed workspace onboarding",
  ONBOARDING_DEFERRED: "Deferred workspace onboarding",
  ICP_CREATED: "Created Ideal Customer Profile",
  ICP_UPDATED: "Updated Ideal Customer Profile",
  ICP_PRIMARY_SET: "Set default ICP",
  ICP_DELETED: "Deleted Ideal Customer Profile",
  INTENT_RADAR_PREFERENCES_SAVED: "Updated research preferences",
  INTENT_RADAR_MONITOR_SAVED: "Saved monitor configuration",
  INTENT_RADAR_DISCOVERY_REQUESTED: "Started discovery search",
  INTENT_RADAR_SIGNAL_REVIEWED: "Reviewed intent signal",
  INTENT_RADAR_BOOKMARK_UPDATED: "Updated Research Library item",
  INTENT_RADAR_OPPORTUNITY_UPDATED: "Updated opportunity",
  INTENT_RADAR_SCHEDULE_UPDATED: "Updated monitor schedule",
  INTENT_RADAR_SOURCE_CONFIGURED: "Configured custom feed source",
  INTENT_RADAR_SOURCE_DELETED: "Removed custom feed source",
  INTENT_RADAR_SOURCE_BULK_TOGGLED: "Bulk-updated custom feeds",
  INTENT_RADAR_GITHUB_CONNECTED: "Connected GitHub App",
  INTENT_RADAR_GITHUB_REPOSITORIES_UPDATED: "Updated GitHub repositories",
  INTENT_RADAR_GITHUB_DISCONNECTED: "Disconnected GitHub App",
  API_KEY_CREATED: "Created Developer API key",
  API_KEY_REVOKED: "Revoked Developer API key",
  BILLING_CREATED: "Started subscription checkout",
  BILLING_CANCELLATION_REQUESTED: "Requested renewal cancellation",
};

function humanizeAction(code: string): string {
  if (ACTION_LABELS[code]) return ACTION_LABELS[code];
  if (code.startsWith("AI_AGENT_")) {
    return `AI Assistant · ${code.replace("AI_AGENT_", "").replace(/_/g, " ").toLowerCase()}`;
  }
  if (code.startsWith("PUT ") || code.startsWith("POST ") || code.startsWith("DELETE ")) {
    const [method, path] = code.split(" ");
    return `${method} ${path?.replace("/api/", "") || ""}`;
  }
  return code
    .replace(/^INTENT_RADAR_/, "")
    .replace(/_/g, " ")
    .toLowerCase()
    .replace(/^\w/, (c) => c.toUpperCase());
}

function formatTarget(entity: string): string {
  if (!entity) return "—";
  const parts = entity.split(":");
  if (parts.length === 2) {
    const [kind, id] = parts;
    const shortId = id.length > 14 ? `${id.slice(0, 8)}…${id.slice(-4)}` : id;
    return `${kind} · ${shortId}`;
  }
  return entity.length > 26 ? `${entity.slice(0, 24)}…` : entity;
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

const ROLE_MATRIX = [
  {
    role: "Owner",
    scope: "Full workspace control: billing & subscriptions, role assignments, member removal, workspace rename, API keys, integrations, and audit exports.",
  },
  {
    role: "Admin",
    scope: "Manage integrations, custom feeds, company profile, domains, research preferences, invitations, member removal (non-admin), and audit logs.",
  },
  {
    role: "Member",
    scope: "Run discoveries, review signals, manage opportunities, monitors, ICPs, Research Library, and use the AI Assistant within plan quotas.",
  },
  {
    role: "Viewer",
    scope: "Read-only access to workspace signals, discoveries, reports, and personal notification preferences.",
  },
];

export function AccessSettings() {
  const workspace = useWorkspace();
  const orgId = workspace.data?.active_organization_id || "";

  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [actionFilter, setActionFilter] = useState("all");
  const [resultFilter, setResultFilter] = useState("all");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [selectedEvent, setSelectedEvent] = useState<AuditRecord | null>(null);

  const queryParams = new URLSearchParams({
    page: String(page),
    page_size: "20",
  });
  if (search.trim()) queryParams.set("search", search.trim());
  if (actionFilter !== "all") queryParams.set("action", actionFilter);
  if (resultFilter !== "all") queryParams.set("result", resultFilter);
  if (fromDate) queryParams.set("from_date", fromDate);
  if (toDate) queryParams.set("to_date", toDate);

  const auditQuery = useQuery({
    queryKey: ["audit", orgId || "default", queryParams.toString()],
    queryFn: ({ signal }) =>
      request<AuditPage>(`/foundation/audit?${queryParams.toString()}`, { signal }),
    retry: false,
  });

  const exportParams = new URLSearchParams(queryParams);
  exportParams.delete("page");
  exportParams.delete("page_size");

  const hasFilters = Boolean(search || actionFilter !== "all" || resultFilter !== "all" || fromDate || toDate);

  function clearFilters() {
    setSearch("");
    setActionFilter("all");
    setResultFilter("all");
    setFromDate("");
    setToDate("");
    setPage(1);
  }

  const items = auditQuery.data?.items || [];
  const total = auditQuery.data?.total || 0;
  const totalPages = Math.max(1, Math.ceil(total / 20));

  return (
    <div className="space-y-5">
      {/* Compact Role Permissions Summary */}
      <section className="rounded-xl border border-border bg-card p-4 space-y-3">
        <div className="flex items-center gap-2">
          <Shield size={15} className="text-primary" />
          <h3 className="text-sm font-semibold text-foreground">Role Permissions</h3>
        </div>
        <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-4">
          {ROLE_MATRIX.map((r) => (
            <div key={r.role} className="rounded-lg border border-border/70 bg-muted/15 p-3 space-y-1">
              <p className="text-xs font-semibold text-foreground">{r.role}</p>
              <p className="text-[11px] text-muted-foreground leading-relaxed">{r.scope}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Audit Log Section */}
      <section className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 className="text-sm font-semibold text-foreground">Workspace Audit Log</h3>
            <p className="text-[11px] text-muted-foreground">
              Immutable security &amp; operational activity history for this workspace.
            </p>
          </div>
          {!auditQuery.isError && (
            <div className="flex items-center gap-1.5">
              <a
                href={`/api/foundation/audit/export?format=csv&${exportParams.toString()}`}
                className="inline-flex h-7 items-center gap-1 rounded-md border border-border bg-card px-2.5 text-[11px] font-medium text-foreground shadow-sm hover:bg-accent transition-colors"
              >
                <Download size={12} />
                Export CSV
              </a>
              <a
                href={`/api/foundation/audit/export?format=json&${exportParams.toString()}`}
                className="inline-flex h-7 items-center gap-1 rounded-md border border-border bg-card px-2.5 text-[11px] font-medium text-foreground shadow-sm hover:bg-accent transition-colors"
              >
                <FileText size={12} />
                JSON
              </a>
            </div>
          )}
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-2 rounded-xl border border-border bg-card p-3">
          <div className="relative flex-1 min-w-[180px]">
            <Search size={12} className="absolute left-2.5 top-2.5 text-muted-foreground" />
            <Input
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              placeholder="Search actor, activity, or target…"
              className="h-8 pl-7 text-xs"
            />
          </div>

          <select
            aria-label="Filter by activity"
            value={actionFilter}
            onChange={(e) => {
              setActionFilter(e.target.value);
              setPage(1);
            }}
            className="h-8 rounded-lg border border-border bg-background px-2.5 text-xs text-foreground"
          >
            <option value="all">All activities</option>
            <option value="MEMBERSHIP">Team &amp; roles</option>
            <option value="INVITATION">Invitations</option>
            <option value="COMPANY_PROFILE">Company profile</option>
            <option value="DOMAIN">Domains</option>
            <option value="INTENT_RADAR">Intent Radar</option>
            <option value="API_KEY">Developer API</option>
            <option value="BILLING">Billing</option>
          </select>

          <select
            aria-label="Filter by result"
            value={resultFilter}
            onChange={(e) => {
              setResultFilter(e.target.value);
              setPage(1);
            }}
            className="h-8 rounded-lg border border-border bg-background px-2.5 text-xs text-foreground"
          >
            <option value="all">All results</option>
            <option value="SUCCESS">Success</option>
            <option value="FAILED">Failed / Rejected</option>
          </select>

          <input
            type="date"
            aria-label="From date"
            value={fromDate}
            onChange={(e) => {
              setFromDate(e.target.value);
              setPage(1);
            }}
            className="h-8 rounded-lg border border-border bg-background px-2 text-xs text-foreground"
          />
          <input
            type="date"
            aria-label="To date"
            value={toDate}
            onChange={(e) => {
              setToDate(e.target.value);
              setPage(1);
            }}
            className="h-8 rounded-lg border border-border bg-background px-2 text-xs text-foreground"
          />

          {hasFilters && (
            <Button size="sm" variant="ghost" onClick={clearFilters} className="h-8 px-2 text-xs gap-1 text-muted-foreground">
              <X size={12} /> Clear
            </Button>
          )}
        </div>

        {/* Clean Audit Table (No Overlap, Proper Column Widths) */}
        {auditQuery.isPending ? (
          <div className="h-56 rounded-xl border border-border bg-muted/30 animate-pulse" />
        ) : auditQuery.isError ? (
          <div role="alert" className="rounded-xl border border-border bg-card p-5 text-xs space-y-1.5">
            <p className="font-semibold text-foreground">Audit history requires Owner or Administrator access</p>
            <p className="text-muted-foreground">
              {auditQuery.error instanceof Error ? auditQuery.error.message : "Could not load audit history."}
            </p>
          </div>
        ) : (
          <div className="rounded-xl border border-border bg-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[680px] text-left text-xs border-collapse" aria-label="Workspace audit log">
                <thead className="bg-muted/40 text-[11px] font-semibold text-muted-foreground border-b border-border">
                  <tr>
                    <th scope="col" className="px-3.5 py-2.5 w-36 whitespace-nowrap">Time</th>
                    <th scope="col" className="px-3.5 py-2.5 w-44">Actor</th>
                    <th scope="col" className="px-3.5 py-2.5">Activity</th>
                    <th scope="col" className="px-3.5 py-2.5 w-40">Target</th>
                    <th scope="col" className="px-3.5 py-2.5 w-24 whitespace-nowrap">Result</th>
                    <th scope="col" className="px-3.5 py-2.5 w-20 text-right">Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/70">
                  {items.map((ev) => {
                    const isSuccess = ev.result === "SUCCESS";
                    return (
                      <tr
                        key={ev.id}
                        onClick={() => setSelectedEvent(ev)}
                        className="hover:bg-muted/25 cursor-pointer transition-colors"
                      >
                        <td className="px-3.5 py-2.5 text-[11px] text-muted-foreground whitespace-nowrap tabular-nums">
                          {formatTime(ev.created_at)}
                        </td>
                        <td className="px-3.5 py-2.5 max-w-[176px]">
                          <span className="block truncate text-foreground" title={ev.actor}>
                            {ev.actor}
                          </span>
                        </td>
                        <td className="px-3.5 py-2.5 font-medium text-foreground">
                          <span className="block truncate max-w-[260px]" title={ev.action}>
                            {humanizeAction(ev.action)}
                          </span>
                        </td>
                        <td className="px-3.5 py-2.5 max-w-[160px]">
                          <span
                            className="block truncate font-mono text-[11px] text-muted-foreground"
                            title={ev.entity}
                          >
                            {formatTarget(ev.entity)}
                          </span>
                        </td>
                        <td className="px-3.5 py-2.5 whitespace-nowrap">
                          <span
                            className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold whitespace-nowrap ${
                              isSuccess
                                ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/20"
                                : "bg-destructive/10 text-destructive border-destructive/20"
                            }`}
                          >
                            {isSuccess ? <CheckCircle2 size={10} /> : <XCircle size={10} />}
                            {isSuccess ? "Success" : "Failed"}
                          </span>
                        </td>
                        <td className="px-3.5 py-2.5 text-right whitespace-nowrap">
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedEvent(ev);
                            }}
                            aria-label={`View details for ${humanizeAction(ev.action)}`}
                            className="inline-flex items-center gap-0.5 text-[11px] font-medium text-primary hover:underline cursor-pointer"
                          >
                            View <ChevronRight size={12} />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                  {items.length === 0 && (
                    <tr>
                      <td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">
                        <Filter className="mx-auto mb-2 h-5 w-5 opacity-40" />
                        No audit events match the selected filters.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            <div className="flex items-center justify-between border-t border-border/70 px-4 py-2.5 text-[11px] text-muted-foreground">
              <span>
                Showing page {page} of {totalPages} ({total.toLocaleString()} events)
              </span>
              <div className="flex items-center gap-1.5">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  className="h-7 px-2.5 text-[11px]"
                >
                  Previous
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  className="h-7 px-2.5 text-[11px]"
                >
                  Next
                </Button>
              </div>
            </div>
          </div>
        )}
      </section>

      {/* Event Detail Side Drawer */}
      <Dialog.Root open={Boolean(selectedEvent)} onOpenChange={(o) => !o && setSelectedEvent(null)}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-50 bg-black/35 backdrop-blur-[1px]" />
          <Dialog.Content className="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col border-l border-border bg-card shadow-2xl">
            <div className="flex items-start justify-between gap-3 border-b border-border px-5 py-4">
              <div className="min-w-0">
                <Dialog.Title className="text-sm font-semibold text-foreground">
                  {selectedEvent ? humanizeAction(selectedEvent.action) : "Event details"}
                </Dialog.Title>
                <Dialog.Description className="text-[11px] text-muted-foreground mt-0.5">
                  {selectedEvent ? formatTime(selectedEvent.created_at) : ""}
                </Dialog.Description>
              </div>
              <Dialog.Close asChild>
                <button className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted" aria-label="Close details">
                  <X size={16} />
                </button>
              </Dialog.Close>
            </div>

            {selectedEvent && (
              <div className="flex-1 overflow-y-auto p-5 space-y-4 text-xs">
                <dl className="grid grid-cols-2 gap-3 rounded-xl border border-border bg-muted/15 p-3.5">
                  <div>
                    <dt className="text-[11px] text-muted-foreground">Actor</dt>
                    <dd className="font-medium text-foreground break-all mt-0.5">{selectedEvent.actor}</dd>
                  </div>
                  <div>
                    <dt className="text-[11px] text-muted-foreground">Result</dt>
                    <dd className="font-semibold text-foreground mt-0.5">{selectedEvent.result}</dd>
                  </div>
                  <div className="col-span-2">
                    <dt className="text-[11px] text-muted-foreground">Raw event code</dt>
                    <dd className="font-mono text-[11px] text-foreground break-all mt-0.5">
                      {selectedEvent.action}
                    </dd>
                  </div>
                  <div className="col-span-2">
                    <dt className="text-[11px] text-muted-foreground">Target identifier</dt>
                    <dd className="font-mono text-[11px] text-foreground break-all mt-0.5">
                      {selectedEvent.entity}
                    </dd>
                  </div>
                  <div className="col-span-2">
                    <dt className="text-[11px] text-muted-foreground">Audit record ID</dt>
                    <dd className="font-mono text-[11px] text-muted-foreground break-all mt-0.5">
                      {selectedEvent.id}
                    </dd>
                  </div>
                </dl>

                {selectedEvent.details && Object.keys(selectedEvent.details).length > 0 && (
                  <div className="space-y-1.5">
                    <h4 className="text-xs font-semibold text-foreground">Event metadata</h4>
                    <pre className="overflow-x-auto rounded-xl border border-border bg-muted/30 p-3 font-mono text-[11px] text-foreground leading-relaxed">
                      {JSON.stringify(selectedEvent.details, null, 2)}
                    </pre>
                  </div>
                )}

                <details className="rounded-xl border border-border bg-muted/10 p-3">
                  <summary className="cursor-pointer text-xs font-medium text-muted-foreground">
                    Full raw audit record
                  </summary>
                  <pre className="mt-2 overflow-x-auto font-mono text-[11px] text-foreground leading-relaxed">
                    {JSON.stringify(selectedEvent, null, 2)}
                  </pre>
                </details>
              </div>
            )}
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}
