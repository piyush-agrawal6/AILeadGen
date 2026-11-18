"use client";

import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import * as Dialog from "@radix-ui/react-dialog";
import {
  CheckCircle2,
  Crown,
  Search,
  Shield,
  Trash2,
  UserPlus,
  Users,
} from "lucide-react";
import { request } from "@/lib/intelligence";
import { initials, useWorkspace } from "@/components/workspaces/use-workspace";
import { Invitations } from "@/components/workspaces/invitations";
import { AccessSettings } from "@/components/workspaces/access-settings";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface WorkspaceMember {
  id: string;
  email: string;
  display_name: string;
  avatar_url?: string | null;
  role: "OWNER" | "ADMIN" | "MEMBER" | "VIEWER";
  status: string;
  joined_at?: string;
  is_self?: boolean;
  primary_owner?: boolean;
  can_change_role?: boolean;
  can_remove?: boolean;
}

interface MembersResponse {
  items: WorkspaceMember[];
  total: number;
  seat_used: number;
  seat_limit: number | null;
  caller_role: string;
  can_invite: boolean;
  can_manage_roles: boolean;
}

const ROLE_STYLES: Record<string, string> = {
  OWNER: "bg-primary/10 text-primary border-primary/20",
  ADMIN: "bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/20",
  MEMBER: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/20",
  VIEWER: "bg-muted text-muted-foreground border-border",
};

function formatDate(iso?: string | null) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return "—";
  }
}

const PAGE_SIZE = 10;

function TeamMembersTab({ onSwitchTab }: { onSwitchTab?: (tab: string) => void }) {
  const client = useQueryClient();
  const workspace = useWorkspace();
  const orgId = workspace.data?.active_organization_id || "";

  const membersQuery = useQuery({
    queryKey: ["workspace-members", orgId || "default"],
    queryFn: ({ signal }) => request<MembersResponse>("/organization/members", { signal }),
    retry: false,
  });

  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState<string>("all");
  const [page, setPage] = useState(1);
  const [busyEmail, setBusyEmail] = useState<string | null>(null);
  const [removeTarget, setRemoveTarget] = useState<WorkspaceMember | null>(null);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  const data = membersQuery.data;
  const members = useMemo(() => data?.items || [], [data]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return members.filter((m) => {
      if (roleFilter !== "all" && m.role !== roleFilter) return false;
      if (q && !`${m.display_name} ${m.email} ${m.role}`.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [members, search, roleFilter]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const pageItems = filtered.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

  async function handleRoleChange(member: WorkspaceMember, nextRole: string) {
    setBusyEmail(member.email);
    setNotice("");
    setError("");
    try {
      await request("/foundation/roles", {
        method: "PUT",
        body: JSON.stringify({ email: member.email, role: nextRole }),
      });
      setNotice(`Updated ${member.display_name}'s role to ${nextRole.toLowerCase()}.`);
      await Promise.all([
        membersQuery.refetch(),
        client.invalidateQueries({ queryKey: ["audit"] }),
        client.invalidateQueries({ queryKey: ["account-workspaces"] }),
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update member role.");
    } finally {
      setBusyEmail(null);
    }
  }

  async function confirmRemove() {
    if (!removeTarget) return;
    setBusyEmail(removeTarget.email);
    setNotice("");
    setError("");
    try {
      await request(`/organization/members/${encodeURIComponent(removeTarget.email)}`, {
        method: "DELETE",
      });
      setNotice(`Removed ${removeTarget.display_name} from this workspace.`);
      setRemoveTarget(null);
      await Promise.all([
        membersQuery.refetch(),
        client.invalidateQueries({ queryKey: ["audit"] }),
        client.invalidateQueries({ queryKey: ["account-workspaces"] }),
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not remove workspace member.");
    } finally {
      setBusyEmail(null);
    }
  }

  if (membersQuery.isPending) {
    return (
      <div role="status" className="rounded-xl border border-border bg-card p-6 text-xs text-muted-foreground">
        Loading team members…
      </div>
    );
  }

  if (membersQuery.isError) {
    return (
      <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-destructive/25 bg-destructive/5 p-4 text-xs text-destructive">
        <div className="space-y-0.5">
          <p className="font-semibold">Could not load team members.</p>
          <p className="text-[11px] opacity-90">
            {membersQuery.error instanceof Error
              ? membersQuery.error.message
              : "Please check your connection and try again."}
          </p>
        </div>
        <Button size="sm" variant="outline" onClick={() => void membersQuery.refetch()}>
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
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

      {/* Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-2.5">
        <div className="flex flex-wrap items-center gap-2 flex-1 min-w-[220px]">
          <div className="relative flex-1 max-w-xs">
            <Search size={13} className="absolute left-2.5 top-2.5 text-muted-foreground" />
            <Input
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              placeholder="Search members…"
              className="h-8 pl-8 text-xs"
            />
          </div>
          <select
            aria-label="Filter by role"
            value={roleFilter}
            onChange={(e) => {
              setRoleFilter(e.target.value);
              setPage(1);
            }}
            className="h-8 rounded-lg border border-border bg-background px-2.5 text-xs text-foreground"
          >
            <option value="all">All roles</option>
            <option value="OWNER">Owner</option>
            <option value="ADMIN">Admin</option>
            <option value="MEMBER">Member</option>
            <option value="VIEWER">Viewer</option>
          </select>
        </div>

        <div className="flex items-center gap-2.5">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-muted/30 px-2.5 py-1 text-[11px] font-medium text-muted-foreground tabular-nums">
            <Users size={12} />
            {data?.seat_limit != null
              ? `${data.seat_used} / ${data.seat_limit} seats`
              : `${members.length} ${members.length === 1 ? "member" : "members"}`}
          </span>
          {data?.can_invite && (
            <Button
              size="sm"
              onClick={() => onSwitchTab?.("invitations")}
              className="h-8 text-xs gap-1.5"
            >
              <UserPlus size={13} />
              Invite Teammate
            </Button>
          )}
        </div>
      </div>

      {/* Compact Members Table */}
      <section className="rounded-xl border border-border bg-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse" aria-label="Workspace members">
            <thead className="bg-muted/40 text-[11px] font-semibold text-muted-foreground border-b border-border">
              <tr>
                <th scope="col" className="px-4 py-2.5">Member</th>
                <th scope="col" className="px-4 py-2.5">Email</th>
                <th scope="col" className="px-4 py-2.5">Role</th>
                <th scope="col" className="px-4 py-2.5">Status</th>
                <th scope="col" className="px-4 py-2.5">Joined</th>
                <th scope="col" className="px-4 py-2.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/70">
              {pageItems.map((m) => (
                <tr key={m.email} className="hover:bg-muted/20">
                  <td className="px-4 py-2.5">
                    <div className="flex items-center gap-2.5 min-w-0">
                      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10 text-[11px] font-semibold text-primary">
                        {initials(m.display_name || m.email)}
                      </span>
                      <div className="min-w-0">
                        <span className="font-medium text-foreground truncate block">
                          {m.display_name}
                          {m.is_self && (
                            <span className="ml-1.5 text-[10px] font-normal text-muted-foreground">(You)</span>
                          )}
                        </span>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-2.5 text-muted-foreground font-mono text-[11px]">
                    {m.email}
                  </td>
                  <td className="px-4 py-2.5">
                    {m.can_change_role ? (
                      <select
                        aria-label={`Role for ${m.email}`}
                        disabled={busyEmail === m.email}
                        value={m.role}
                        onChange={(e) => void handleRoleChange(m, e.target.value)}
                        className="h-7 rounded-md border border-border bg-background px-2 text-[11px] font-medium text-foreground"
                      >
                        <option value="OWNER">Owner</option>
                        <option value="ADMIN">Admin</option>
                        <option value="MEMBER">Member</option>
                        <option value="VIEWER">Viewer</option>
                      </select>
                    ) : (
                      <span
                        className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold ${
                          ROLE_STYLES[m.role] || ROLE_STYLES.VIEWER
                        }`}
                      >
                        {m.role === "OWNER" ? <Crown size={10} /> : m.role === "ADMIN" ? <Shield size={10} /> : null}
                        {m.role.charAt(0) + m.role.slice(1).toLowerCase()}
                        {m.primary_owner ? " · Primary" : ""}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2.5">
                    <span className="inline-flex items-center gap-1 text-[11px] text-emerald-700 dark:text-emerald-400">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                      Active
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-muted-foreground tabular-nums">
                    {formatDate(m.joined_at)}
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    {m.can_remove ? (
                      <Button
                        size="sm"
                        variant="ghost"
                        disabled={busyEmail === m.email}
                        onClick={() => setRemoveTarget(m)}
                        aria-label={`Remove ${m.email}`}
                        className="h-7 px-2 text-[11px] text-muted-foreground hover:text-destructive gap-1"
                      >
                        <Trash2 size={12} />
                        Remove
                      </Button>
                    ) : (
                      <span className="text-[11px] text-muted-foreground/60">—</span>
                    )}
                  </td>
                </tr>
              ))}
              {pageItems.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">
                    No matching members found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {totalPages > 1 && (
          <div className="flex items-center justify-between border-t border-border/70 px-4 py-2.5 text-[11px] text-muted-foreground">
            <span>
              Page {safePage} of {totalPages} ({filtered.length} members)
            </span>
            <div className="flex items-center gap-1.5">
              <Button
                size="sm"
                variant="outline"
                disabled={safePage <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="h-7 px-2.5 text-[11px]"
              >
                Previous
              </Button>
              <Button
                size="sm"
                variant="outline"
                disabled={safePage >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                className="h-7 px-2.5 text-[11px]"
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </section>

      {/* Confirm Remove Member Dialog */}
      <Dialog.Root open={Boolean(removeTarget)} onOpenChange={(o) => !o && setRemoveTarget(null)}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40 backdrop-blur-[1px]" />
          <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[calc(100%-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-border bg-card p-5 shadow-xl space-y-4">
            <Dialog.Title className="text-base font-semibold text-foreground">
              Remove {removeTarget?.display_name}?
            </Dialog.Title>
            <Dialog.Description className="text-xs text-muted-foreground leading-relaxed">
              <strong>{removeTarget?.email}</strong> will immediately lose access to this workspace. Their historical audit records and past contributions remain preserved.
            </Dialog.Description>
            <div className="flex justify-end gap-2">
              <Button size="sm" variant="outline" onClick={() => setRemoveTarget(null)}>
                Cancel
              </Button>
              <Button
                size="sm"
                variant="destructive"
                disabled={busyEmail !== null}
                onClick={() => void confirmRemove()}
              >
                {busyEmail ? "Removing…" : "Remove Member"}
              </Button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}

export function TeamSection({
  activeTab,
  onSwitchTab,
}: {
  activeTab: string;
  onSwitchTab?: (tab: string) => void;
}) {
  if (activeTab === "invitations") return <Invitations />;
  if (activeTab === "roles") return <AccessSettings />;
  return <TeamMembersTab onSwitchTab={onSwitchTab} />;
}
