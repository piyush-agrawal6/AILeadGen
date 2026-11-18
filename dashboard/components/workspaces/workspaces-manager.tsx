"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import * as Dialog from "@radix-ui/react-dialog";
import {
  ArrowRightLeft,
  Building2,
  Check,
  Edit3,
  LogOut,
  Plus,
  Settings2,
  Sparkles,
  Users,
  X,
} from "lucide-react";
import { request } from "@/lib/intelligence";
import {
  useWorkspace,
  initials,
  clearWorkspaceSessionState,
  type Membership,
} from "./use-workspace";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

function setupMeta(item: Membership): { label: string; tone: string } {
  const done = item.onboarding_completed_steps ?? 0;
  const total = item.onboarding_total_steps ?? 5;
  if (item.onboarding_status === "COMPLETED" && done >= total) {
    return {
      label: `Complete · ${total}/${total}`,
      tone: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/20",
    };
  }
  switch (item.access_state) {
    case "ACTIVE":
    case "TRIAL_ACTIVE":
      return {
        label: `Complete · ${done}/${total}`,
        tone: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/20",
      };
    case "CANCELED_REMAINING":
      return {
        label: done >= total ? `Complete · ${total}/${total}` : `Setup · ${done}/${total}`,
        tone: "bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/20",
      };
    case "SETUP_REQUIRED":
      return {
        label: `Setup · ${done}/${total}`,
        tone: "bg-primary/10 text-primary border-primary/20",
      };
    case "TRIAL_AVAILABLE":
    case "SUBSCRIPTION_REQUIRED":
      return {
        label: `Activation needed · ${done}/${total}`,
        tone: "bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/20",
      };
    case "PAYMENT_PENDING":
      return {
        label: "Payment pending",
        tone: "bg-blue-500/10 text-blue-700 dark:text-blue-300 border-blue-500/20",
      };
    case "EXPIRED":
      return {
        label: "Expired",
        tone: "bg-destructive/10 text-destructive border-destructive/20",
      };
    default:
      return {
        label:
          item.onboarding_status === "COMPLETED"
            ? `Complete · ${done}/${total}`
            : `Setup · ${done}/${total}`,
        tone: "bg-muted text-muted-foreground border-border",
      };
  }
}

function onboardingHref(item: Membership): string {
  return item.next_setup_step
    ? `/onboarding?step=${encodeURIComponent(item.next_setup_step)}`
    : "/onboarding";
}

export function WorkspacesManager() {
  const client = useQueryClient();
  const searchParams = useSearchParams();
  const ws = useWorkspace();

  const [createOpen, setCreateOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState("");
  const createReqId = useRef<string | null>(null);

  const [renameTarget, setRenameTarget] = useState<Membership | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [renaming, setRenaming] = useState(false);

  const [leaveTarget, setLeaveTarget] = useState<Membership | null>(null);
  const [leaving, setLeaving] = useState(false);

  const [switchingId, setSwitchingId] = useState<string | null>(null);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (searchParams.get("create") === "1") {
      setCreateOpen(true);
    }
  }, [searchParams]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (creating || newName.trim().length < 2) return;
    setCreating(true);
    setCreateError("");
    createReqId.current ??= crypto.randomUUID();
    try {
      await client.cancelQueries();
      await request<{ organization_id: string; reused: boolean }>("/organization/workspaces", {
        method: "POST",
        body: JSON.stringify({ name: newName.trim(), request_id: createReqId.current }),
      });
      clearWorkspaceSessionState();
      client.clear();
      window.location.assign("/onboarding");
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : "Could not create workspace.");
    } finally {
      setCreating(false);
    }
  }

  async function handleSwitch(item: Membership, dest?: string) {
    if (switchingId) return;
    setSwitchingId(item.organization_id);
    setError("");
    try {
      await client.cancelQueries();
      await request("/organization/active", {
        method: "PUT",
        body: JSON.stringify({ organization_id: item.organization_id }),
      });
      clearWorkspaceSessionState();
      client.clear();
      const targetUrl =
        dest ||
        (item.access_state === "SETUP_REQUIRED" ? onboardingHref(item) : "/intent-radar");
      window.location.assign(targetUrl);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not switch workspace.");
      setSwitchingId(null);
    }
  }

  async function handleRename(e: React.FormEvent) {
    e.preventDefault();
    if (!renameTarget || renaming || renameValue.trim().length < 2) return;
    setRenaming(true);
    setError("");
    setNotice("");
    try {
      await request(`/organization/workspaces/${renameTarget.organization_id}`, {
        method: "PATCH",
        body: JSON.stringify({ name: renameValue.trim() }),
      });
      setNotice(`Renamed workspace to "${renameValue.trim()}".`);
      setRenameTarget(null);
      await ws.refetch();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not rename workspace.");
    } finally {
      setRenaming(false);
    }
  }

  async function handleLeave() {
    if (!leaveTarget || leaving) return;
    setLeaving(true);
    setError("");
    setNotice("");
    try {
      const res = await request<{ left: boolean; next_organization_id: string | null }>(
        `/organization/workspaces/${leaveTarget.organization_id}/leave`,
        { method: "POST", body: "{}" }
      );
      const wasActive = leaveTarget.organization_id === ws.data?.active_organization_id;
      setLeaveTarget(null);
      setNotice(`You left ${leaveTarget.name}.`);
      if (wasActive) {
        clearWorkspaceSessionState();
        client.clear();
        window.location.assign(res.next_organization_id ? "/intent-radar" : "/settings/workspaces");
      } else {
        await ws.refetch();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not leave workspace.");
    } finally {
      setLeaving(false);
    }
  }

  const items = ws.data?.items || [];
  const activeId = ws.data?.active_organization_id;

  return (
    <div className="mx-auto max-w-5xl space-y-5 py-2">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-foreground">Workspaces</h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Each workspace maintains separate billing, integrations, company profile, and research data.
          </p>
        </div>
        <Button
          size="sm"
          onClick={() => {
            setNewName("");
            setCreateError("");
            createReqId.current = null;
            setCreateOpen(true);
          }}
          className="h-8 text-xs gap-1.5"
        >
          <Plus size={14} />
          Create Workspace
        </Button>
      </header>

      {notice && (
        <div role="status" className="rounded-xl border border-emerald-500/25 bg-emerald-500/10 px-4 py-2.5 text-xs font-medium text-emerald-700 dark:text-emerald-300">
          {notice}
        </div>
      )}
      {error && (
        <div role="alert" className="rounded-xl border border-destructive/25 bg-destructive/5 px-4 py-2.5 text-xs text-destructive">
          {error}
        </div>
      )}

      {ws.isPending ? (
        <div role="status" className="rounded-2xl border border-border bg-card p-6 text-xs text-muted-foreground">
          Loading your workspaces…
        </div>
      ) : ws.isError ? (
        <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-destructive/25 bg-destructive/5 p-5 text-xs text-destructive">
          <span>
            {ws.error instanceof Error ? ws.error.message : "Could not load your workspaces."}
          </span>
          <Button size="sm" variant="outline" onClick={() => void ws.refetch()}>
            Retry
          </Button>
        </div>
      ) : (
        <section className="rounded-2xl border border-border bg-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse" aria-label="Your workspaces">
              <thead className="bg-muted/40 text-[11px] font-semibold text-muted-foreground border-b border-border">
                <tr>
                  <th scope="col" className="px-4 py-2.5">Workspace</th>
                  <th scope="col" className="px-4 py-2.5">Role</th>
                  <th scope="col" className="px-4 py-2.5">Plan</th>
                  <th scope="col" className="px-4 py-2.5">Setup</th>
                  <th scope="col" className="px-4 py-2.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/70">
                {items.map((item) => {
                  const isActive = item.organization_id === activeId;
                  const meta = setupMeta(item);
                  const needsSetup =
                    item.access_state === "SETUP_REQUIRED" ||
                    item.onboarding_status !== "COMPLETED" ||
                    (item.onboarding_completed_steps ?? 0) < (item.onboarding_total_steps ?? 5);
                  return (
                    <tr key={item.organization_id} className={isActive ? "bg-primary/[0.03]" : "hover:bg-muted/20"}>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2.5 min-w-0">
                          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-xs font-semibold text-primary">
                            {initials(item.name)}
                          </span>
                          <div className="min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="font-semibold text-foreground truncate">{item.name}</span>
                              {isActive && (
                                <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-semibold text-primary">
                                  <Check size={10} /> Current
                                </span>
                              )}
                            </div>
                            <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground mt-0.5">
                              <Users size={11} />
                              <span>{item.member_count ?? 1} {(item.member_count ?? 1) === 1 ? "member" : "members"}</span>
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className="rounded-md border border-border bg-muted/40 px-2 py-0.5 text-[11px] font-medium capitalize text-foreground">
                          {item.role.toLowerCase()}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="font-medium text-foreground">
                          {item.plan_label || "No active plan"}
                        </div>
                        {item.plan_status && item.plan_status !== "Not activated" && (
                          <div className="text-[10px] text-muted-foreground mt-0.5">
                            {item.plan_status}
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium ${meta.tone}`}>
                          {meta.label}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="inline-flex flex-wrap items-center justify-end gap-1.5">
                          {!isActive && (
                            <Button
                              size="sm"
                              variant="outline"
                              disabled={switchingId !== null}
                              onClick={() => void handleSwitch(item)}
                              className="h-7 px-2.5 text-[11px] gap-1"
                            >
                              <ArrowRightLeft size={12} />
                              {switchingId === item.organization_id ? "Switching workspace…" : "Switch"}
                            </Button>
                          )}
                          {needsSetup && (
                            <Button
                              size="sm"
                              variant="outline"
                              disabled={switchingId !== null}
                              onClick={() => void handleSwitch(item, onboardingHref(item))}
                              className="h-7 px-2.5 text-[11px] gap-1 text-primary border-primary/30"
                            >
                              <Sparkles size={12} />
                              Continue setup
                            </Button>
                          )}
                          {isActive ? (
                            <Link
                              href="/settings?category=company"
                              className="inline-flex h-7 items-center gap-1 rounded-md px-2 text-[11px] font-medium text-foreground hover:bg-accent transition-colors"
                            >
                              <Settings2 size={12} />
                              Settings
                            </Link>
                          ) : (
                            <Button
                              size="sm"
                              variant="ghost"
                              disabled={switchingId !== null}
                              onClick={() => void handleSwitch(item, "/settings?category=company")}
                              className="h-7 px-2 text-[11px] gap-1"
                            >
                              <Settings2 size={12} />
                              Settings
                            </Button>
                          )}
                          {item.role === "OWNER" && (
                            <Button
                              size="sm"
                              variant="ghost"
                              disabled={switchingId !== null}
                              onClick={() => {
                                setRenameTarget(item);
                                setRenameValue(item.name);
                              }}
                              aria-label={`Rename ${item.name}`}
                              className="h-7 px-2 text-[11px] gap-1"
                            >
                              <Edit3 size={12} />
                              Rename
                            </Button>
                          )}
                          <Button
                            size="sm"
                            variant="ghost"
                            disabled={switchingId !== null}
                            onClick={() => setLeaveTarget(item)}
                            aria-label={`Leave ${item.name}`}
                            className="h-7 px-2 text-[11px] text-muted-foreground hover:text-destructive gap-1"
                          >
                            <LogOut size={12} />
                            Leave
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
                {items.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-muted-foreground">
                      <Building2 className="mx-auto mb-2 h-6 w-6 opacity-50" />
                      No workspaces yet. Create your first workspace to get started.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Create Workspace Dialog */}
      <Dialog.Root open={createOpen} onOpenChange={setCreateOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40 backdrop-blur-[1px]" />
          <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[calc(100%-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-border bg-card p-5 shadow-xl space-y-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <Dialog.Title className="text-base font-semibold text-foreground">
                  Create workspace
                </Dialog.Title>
                <Dialog.Description className="text-xs text-muted-foreground mt-1">
                  Start an independent workspace with its own company profile, integrations, and billing.
                </Dialog.Description>
              </div>
              <Dialog.Close asChild>
                <button className="rounded-lg p-1 text-muted-foreground hover:bg-muted" aria-label="Close">
                  <X size={16} />
                </button>
              </Dialog.Close>
            </div>
            <form onSubmit={(e) => void handleCreate(e)} className="space-y-4">
              <div className="space-y-1.5">
                <label htmlFor="create-ws-name" className="text-xs font-medium text-foreground">
                  Workspace / company name
                </label>
                <Input
                  id="create-ws-name"
                  placeholder="e.g. Acme Labs"
                  required
                  minLength={2}
                  maxLength={120}
                  value={newName}
                  disabled={creating}
                  onChange={(e) => {
                    setNewName(e.target.value);
                    createReqId.current = null;
                  }}
                />
              </div>
              <p className="text-[11px] text-muted-foreground leading-relaxed">
                Your existing workspaces stay untouched. You will be taken to the new workspace&apos;s onboarding flow next.
              </p>
              {createError && (
                <p role="alert" className="text-xs text-destructive">
                  {createError}
                </p>
              )}
              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" size="sm" onClick={() => setCreateOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" size="sm" disabled={creating || newName.trim().length < 2}>
                  {creating ? "Creating…" : "Create & Continue"}
                </Button>
              </div>
            </form>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>

      {/* Rename Workspace Dialog */}
      <Dialog.Root open={Boolean(renameTarget)} onOpenChange={(o) => !o && setRenameTarget(null)}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40 backdrop-blur-[1px]" />
          <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[calc(100%-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-border bg-card p-5 shadow-xl space-y-4">
            <Dialog.Title className="text-base font-semibold text-foreground">
              Rename workspace
            </Dialog.Title>
            <form onSubmit={(e) => void handleRename(e)} className="space-y-4">
              <Input
                value={renameValue}
                minLength={2}
                maxLength={120}
                required
                disabled={renaming}
                onChange={(e) => setRenameValue(e.target.value)}
              />
              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" size="sm" onClick={() => setRenameTarget(null)}>
                  Cancel
                </Button>
                <Button type="submit" size="sm" disabled={renaming || renameValue.trim().length < 2}>
                  {renaming ? "Saving…" : "Save Name"}
                </Button>
              </div>
            </form>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>

      {/* Leave Workspace Confirmation */}
      <Dialog.Root open={Boolean(leaveTarget)} onOpenChange={(o) => !o && setLeaveTarget(null)}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40 backdrop-blur-[1px]" />
          <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[calc(100%-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-border bg-card p-5 shadow-xl space-y-4">
            <Dialog.Title className="text-base font-semibold text-foreground">
              Leave {leaveTarget?.name}?
            </Dialog.Title>
            <Dialog.Description className="text-xs text-muted-foreground leading-relaxed">
              You will lose access to this workspace unless re-invited by an owner or administrator. If you are the only active owner, you must transfer ownership before leaving.
            </Dialog.Description>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" size="sm" onClick={() => setLeaveTarget(null)}>
                Cancel
              </Button>
              <Button type="button" variant="destructive" size="sm" disabled={leaving} onClick={() => void handleLeave()}>
                {leaving ? "Leaving…" : "Leave Workspace"}
              </Button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}
