"use client";

import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import * as Dialog from "@radix-ui/react-dialog";
import {
  Check,
  CheckCircle2,
  Copy,
  Mail,
  RefreshCw,
  Trash2,
  UserPlus,
  X,
} from "lucide-react";
import { request } from "@/lib/intelligence";
import { useWorkspace } from "./use-workspace";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type Invite = {
  id: string;
  email: string;
  role: string;
  status: string;
  invited_by: string;
  created_at: string;
  expires_at: string;
  responded_at?: string | null;
};

type Page = {
  items: Invite[];
  total: number;
  page: number;
  page_size: number;
  can_invite_admin: boolean;
};

type Created = {
  id: string;
  email: string;
  role: string;
  status: string;
  expires_at: string;
  token: string;
  delivery: string;
};

const STATUS_STYLE: Record<string, string> = {
  PENDING: "bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/20",
  ACCEPTED: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/20",
  EXPIRED: "bg-muted text-muted-foreground border-border",
  REVOKED: "bg-destructive/10 text-destructive border-destructive/20",
  REJECTED: "bg-muted text-muted-foreground border-border",
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

export function Invitations() {
  const client = useQueryClient();
  const workspace = useWorkspace();
  const orgId = workspace.data?.active_organization_id || "";

  const [page, setPage] = useState(1);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("MEMBER");
  const [pending, setPending] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [created, setCreated] = useState<Created | null>(null);
  const [copied, setCopied] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  const list = useQuery({
    queryKey: ["workspace-invitations", orgId || "default", page],
    queryFn: ({ signal }) => request<Page>(`/organization/invitations?page=${page}`, { signal }),
    retry: false,
  });

  const inviteUrl =
    created && typeof window !== "undefined"
      ? `${window.location.origin}/accept-invitation#${created.token}`
      : "";

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (pending) return;
    setPending(true);
    setError("");
    setNotice("");
    try {
      const res = await request<Created>("/organization/invitations", {
        method: "POST",
        body: JSON.stringify({ email: email.trim(), role }),
      });
      setCreated(res);
      setEmail("");
      setDialogOpen(false);
      setNotice(
        res.delivery === "EMAIL_QUEUED"
          ? `Invitation email sent to ${res.email}.`
          : `Invitation created for ${res.email}. Share the one-time acceptance link below.`
      );
      await list.refetch();
      await client.invalidateQueries({ queryKey: ["audit"] });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not send invitation.");
    } finally {
      setPending(false);
    }
  }

  async function handleResend(inv: Invite) {
    setBusyId(inv.id);
    setError("");
    setNotice("");
    try {
      const res = await request<Created>(`/organization/invitations/${inv.id}/resend`, {
        method: "POST",
      });
      setCreated(res);
      setNotice(
        res.delivery === "EMAIL_QUEUED"
          ? `Resent invitation email to ${res.email} (expires in 7 days).`
          : `Regenerated invitation link for ${res.email}.`
      );
      await list.refetch();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not resend invitation.");
    } finally {
      setBusyId(null);
    }
  }

  async function handleRevoke(inv: Invite) {
    setBusyId(inv.id);
    setError("");
    setNotice("");
    try {
      await request(`/organization/invitations/${inv.id}`, { method: "DELETE" });
      if (created?.id === inv.id) setCreated(null);
      setNotice(`Revoked invitation for ${inv.email}.`);
      await list.refetch();
      await client.invalidateQueries({ queryKey: ["audit"] });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not revoke invitation.");
    } finally {
      setBusyId(null);
    }
  }

  async function copyLink() {
    if (!inviteUrl) return;
    try {
      await navigator.clipboard.writeText(inviteUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // ignore clipboard errors
    }
  }

  if (list.isPending) {
    return <div className="h-44 rounded-xl border border-border bg-muted/30 animate-pulse" />;
  }

  if (list.isError) {
    return (
      <div role="alert" className="rounded-xl border border-border bg-card p-5 text-xs space-y-2">
        <p className="font-semibold text-foreground">Workspace invitations require Owner or Admin access</p>
        <p className="text-muted-foreground">
          {list.error instanceof Error ? list.error.message : "Could not load invitations."}
        </p>
      </div>
    );
  }

  const items = list.data?.items || [];
  const totalPages = Math.max(1, Math.ceil((list.data?.total || 0) / (list.data?.page_size || 25)));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-foreground">Workspace Invitations</h3>
          <p className="text-[11px] text-muted-foreground">
            Invited teammates must sign in with their matching verified email and explicitly accept.
          </p>
        </div>
        <Button
          size="sm"
          onClick={() => {
            setError("");
            setDialogOpen(true);
          }}
          className="h-8 text-xs gap-1.5"
        >
          <UserPlus size={13} />
          Invite Member
        </Button>
      </div>

      {notice && (
        <div role="status" className="flex items-center gap-2 rounded-xl border border-emerald-500/25 bg-emerald-500/10 px-3.5 py-2.5 text-xs font-medium text-emerald-700 dark:text-emerald-300">
          <CheckCircle2 size={14} className="shrink-0" />
          <span>{notice}</span>
        </div>
      )}
      {error && !dialogOpen && (
        <div role="alert" className="rounded-xl border border-destructive/25 bg-destructive/5 px-3.5 py-2.5 text-xs text-destructive">
          {error}
        </div>
      )}

      {created && inviteUrl && (
        <div className="rounded-xl border border-primary/25 bg-primary/5 p-3.5 space-y-2">
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs font-semibold text-foreground">
              One-time acceptance link for {created.email}
            </span>
            <button
              type="button"
              onClick={() => setCreated(null)}
              aria-label="Dismiss invitation link"
              className="rounded p-1 text-muted-foreground hover:bg-muted cursor-pointer"
            >
              <X size={13} />
            </button>
          </div>
          <div className="flex items-center gap-2">
            <Input readOnly value={inviteUrl} className="h-8 font-mono text-[11px] bg-card" />
            <Button size="sm" variant="outline" onClick={() => void copyLink()} className="h-8 text-xs gap-1.5 shrink-0">
              {copied ? <Check size={13} /> : <Copy size={13} />}
              {copied ? "Copied" : "Copy Link"}
            </Button>
          </div>
        </div>
      )}

      {/* Compact Invitations Table */}
      <section className="rounded-xl border border-border bg-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse" aria-label="Workspace invitations">
            <thead className="bg-muted/40 text-[11px] font-semibold text-muted-foreground border-b border-border">
              <tr>
                <th scope="col" className="px-4 py-2.5">Email</th>
                <th scope="col" className="px-4 py-2.5">Role</th>
                <th scope="col" className="px-4 py-2.5">Status</th>
                <th scope="col" className="px-4 py-2.5">Invited</th>
                <th scope="col" className="px-4 py-2.5">Expires</th>
                <th scope="col" className="px-4 py-2.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/70">
              {items.map((inv) => {
                const canResend = inv.status === "PENDING" || inv.status === "EXPIRED";
                const canRevoke = inv.status === "PENDING";
                return (
                  <tr key={inv.id} className="hover:bg-muted/20">
                    <td className="px-4 py-2.5 font-medium text-foreground">{inv.email}</td>
                    <td className="px-4 py-2.5 capitalize text-muted-foreground">
                      {inv.role.toLowerCase()}
                    </td>
                    <td className="px-4 py-2.5">
                      <span
                        className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold ${
                          STATUS_STYLE[inv.status] || STATUS_STYLE.EXPIRED
                        }`}
                      >
                        {inv.status.charAt(0) + inv.status.slice(1).toLowerCase()}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-muted-foreground tabular-nums">
                      {formatDate(inv.created_at)}
                    </td>
                    <td className="px-4 py-2.5 text-muted-foreground tabular-nums">
                      {formatDate(inv.expires_at)}
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      <div className="inline-flex items-center gap-1">
                        {canResend && (
                          <Button
                            size="sm"
                            variant="ghost"
                            disabled={busyId === inv.id}
                            onClick={() => void handleResend(inv)}
                            className="h-7 px-2 text-[11px] gap-1"
                          >
                            <RefreshCw size={11} className={busyId === inv.id ? "animate-spin" : ""} />
                            Resend
                          </Button>
                        )}
                        {canRevoke && (
                          <Button
                            size="sm"
                            variant="ghost"
                            disabled={busyId === inv.id}
                            onClick={() => void handleRevoke(inv)}
                            className="h-7 px-2 text-[11px] text-muted-foreground hover:text-destructive gap-1"
                          >
                            <Trash2 size={11} />
                            Revoke
                          </Button>
                        )}
                        {!canResend && !canRevoke && (
                          <span className="text-[11px] text-muted-foreground/60">—</span>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
              {items.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">
                    <Mail className="mx-auto mb-2 h-5 w-5 opacity-50" />
                    No invitations sent yet. Click &ldquo;Invite Member&rdquo; to add a teammate.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {totalPages > 1 && (
          <div className="flex items-center justify-between border-t border-border/70 px-4 py-2.5 text-[11px] text-muted-foreground">
            <span>
              Page {page} of {totalPages}
            </span>
            <div className="flex gap-1.5">
              <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage((p) => p - 1)} className="h-7 px-2.5 text-[11px]">
                Previous
              </Button>
              <Button size="sm" variant="outline" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)} className="h-7 px-2.5 text-[11px]">
                Next
              </Button>
            </div>
          </div>
        )}
      </section>

      {/* Invite Member Dialog */}
      <Dialog.Root open={dialogOpen} onOpenChange={setDialogOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40 backdrop-blur-[1px]" />
          <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[calc(100%-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-border bg-card p-5 shadow-xl space-y-4">
            <div className="flex items-start justify-between gap-2">
              <div>
                <Dialog.Title className="text-base font-semibold text-foreground">
                  Invite Member
                </Dialog.Title>
                <Dialog.Description className="text-xs text-muted-foreground mt-0.5">
                  Send a verified workspace invitation (expires in 7 days).
                </Dialog.Description>
              </div>
              <Dialog.Close asChild>
                <button className="rounded-lg p-1 text-muted-foreground hover:bg-muted" aria-label="Close">
                  <X size={16} />
                </button>
              </Dialog.Close>
            </div>

            <form onSubmit={(e) => void submit(e)} className="space-y-3.5">
              <div className="space-y-1">
                <label htmlFor="invite-email" className="text-xs font-medium text-foreground">
                  Work email
                </label>
                <Input
                  id="invite-email"
                  type="email"
                  required
                  placeholder="teammate@company.com"
                  value={email}
                  disabled={pending}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>

              <div className="space-y-1">
                <label htmlFor="invite-role" className="text-xs font-medium text-foreground">
                  Workspace role
                </label>
                <select
                  id="invite-role"
                  value={role}
                  disabled={pending}
                  onChange={(e) => setRole(e.target.value)}
                  className="h-9 w-full rounded-lg border border-border bg-background px-3 text-xs text-foreground"
                >
                  <option value="MEMBER">Member — Run discoveries, manage signals &amp; monitors</option>
                  <option value="VIEWER">Viewer — Read-only access to workspace insights</option>
                  {list.data?.can_invite_admin && (
                    <option value="ADMIN">Admin — Manage integrations, feeds, team &amp; settings</option>
                  )}
                </select>
              </div>

              {error && (
                <p role="alert" className="text-xs text-destructive">
                  {error}
                </p>
              )}

              <div className="flex justify-end gap-2 pt-1">
                <Button type="button" variant="outline" size="sm" onClick={() => setDialogOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" size="sm" disabled={pending || !email.trim()}>
                  {pending ? "Sending…" : "Send Invitation"}
                </Button>
              </div>
            </form>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}

export const InvitationSettings = Invitations;

export function InvitationResponse({
  email,
  initialToken,
}: {
  email?: string;
  initialToken?: string;
} = {}) {
  const [token, setToken] = useState(initialToken || "");
  const [pending, setPending] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  // Automatically read invitation token from URL fragment (#token) on mount if not pre-supplied
  useEffect(() => {
    if (!initialToken && typeof window !== "undefined") {
      const hashToken = window.location.hash.slice(1).trim();
      if (hashToken) setToken(hashToken);
    }
  }, [initialToken]);

  async function respond(action: "ACCEPT" | "REJECT") {
    if (pending || !token.trim()) return;
    setPending(true);
    setError("");
    setStatus("");
    try {
      const result = await request<{ status: string; organization_id: string }>(
        "/organization/invitations/respond",
        {
          method: "POST",
          body: JSON.stringify({ token: token.trim(), action }),
        }
      );
      setStatus(
        result.status === "ACCEPTED"
          ? "Invitation accepted. You can now switch to this workspace from the workspace menu."
          : "Invitation declined."
      );
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not process this invitation."
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <section className="mx-auto max-w-lg rounded-2xl border border-border bg-card p-6 space-y-4">
      <div className="space-y-1">
        <h1 className="text-lg font-bold tracking-tight text-foreground">Workspace Invitation</h1>
        <p className="text-xs text-muted-foreground">
          Accepting grants membership only to the invited workspace using your verified signed-in account
          {email ? ` (${email})` : ""}.
        </p>
      </div>

      <div className="space-y-1.5">
        <label htmlFor="invitation-token" className="text-xs font-medium text-foreground">
          Invitation code
        </label>
        <Input
          id="invitation-token"
          value={token}
          disabled={pending}
          placeholder="Paste invitation code"
          onChange={(e) => setToken(e.target.value)}
          className="font-mono text-xs"
        />
      </div>

      {!status && (
        <div className="flex flex-wrap gap-2">
          <Button size="sm" disabled={pending || !token.trim()} onClick={() => void respond("ACCEPT")}>
            {pending ? "Working…" : "Accept Invitation"}
          </Button>
          <Button size="sm" variant="outline" disabled={pending || !token.trim()} onClick={() => void respond("REJECT")}>
            Decline
          </Button>
        </div>
      )}

      {status && (
        <p role="status" className="rounded-lg border border-emerald-500/25 bg-emerald-500/10 px-3 py-2 text-xs font-medium text-emerald-700 dark:text-emerald-300">
          {status}
        </p>
      )}
      {error && (
        <p role="alert" className="rounded-lg border border-destructive/25 bg-destructive/5 px-3 py-2 text-xs text-destructive">
          {error}
        </p>
      )}
    </section>
  );
}
