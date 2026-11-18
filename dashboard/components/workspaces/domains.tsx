"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import * as Dialog from "@radix-ui/react-dialog";
import {
  AlertTriangle,
  Check,
  CheckCircle2,
  Clock,
  Copy,
  Globe,
  Plus,
  RefreshCw,
  ShieldCheck,
  Trash2,
  X,
} from "lucide-react";
import { request } from "@/lib/intelligence";
import { useWorkspace } from "./use-workspace";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type DomainItem = {
  id: string;
  domain: string;
  status: string;
  record_type?: string;
  record_name?: string;
  challenge_expires_at?: string | null;
  verified_at?: string | null;
  checked_at?: string | null;
  attempts?: number;
};

type ChallengeResult = {
  id: string;
  domain: string;
  record_type: string;
  record_name: string;
  record_value: string;
  expires_at: string;
};

const STATUS_META: Record<string, { label: string; style: string }> = {
  VERIFIED: {
    label: "Verified",
    style: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/20",
  },
  PENDING: {
    label: "Pending DNS",
    style: "bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/20",
  },
  EXPIRED: {
    label: "Expired",
    style: "bg-muted text-muted-foreground border-border",
  },
  REVOKED: {
    label: "Revoked",
    style: "bg-destructive/10 text-destructive border-destructive/20",
  },
};

function formatDateTime(iso?: string | null) {
  if (!iso) return "Never";
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

export function DomainSettings() {
  const workspace = useWorkspace();
  const orgId = workspace.data?.active_organization_id || "";

  const domains = useQuery({
    queryKey: ["organization-domains", orgId || "default"],
    queryFn: ({ signal }) =>
      request<{ items: DomainItem[]; can_edit: boolean }>("/organization/domains", { signal }),
    retry: false,
  });

  const [addOpen, setAddOpen] = useState(false);
  const [domainInput, setDomainInput] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [activeChallenge, setActiveChallenge] = useState<ChallengeResult | null>(null);
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  async function copyText(key: string, text: string) {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedField(key);
      setTimeout(() => setCopiedField(null), 1800);
    } catch {
      // ignore clipboard errors
    }
  }

  async function createChallenge(domainName: string) {
    const clean = domainName.trim().toLowerCase().replace(/^https?:\/\//, "").split("/")[0];
    if (!clean) return;
    setCreating(true);
    setError("");
    setNotice("");
    try {
      const res = await request<ChallengeResult>("/organization/domains", {
        method: "POST",
        body: JSON.stringify({ domain: clean }),
      });
      setActiveChallenge(res);
      setDomainInput("");
      setAddOpen(false);
      setNotice(`DNS verification record generated for ${res.domain}. Add the TXT record below, then click Verify Now.`);
      await domains.refetch();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not generate domain verification record.");
    } finally {
      setCreating(false);
    }
  }

  async function verifyDomain(item: DomainItem) {
    setBusyId(item.id);
    setError("");
    setNotice("");
    try {
      const res = await request<{ status: string; verified_at?: string | null }>(
        `/organization/domains/${item.id}/verify`,
        { method: "POST" }
      );
      if (res.status === "VERIFIED") {
        setNotice(`${item.domain} ownership verified via DNS TXT record.`);
        if (activeChallenge?.id === item.id) setActiveChallenge(null);
      } else {
        setError(
          `Matching TXT record not found yet for _heysow-verify.${item.domain}. DNS changes typically propagate within 5–30 minutes.`
        );
      }
      await domains.refetch();
    } catch (err) {
      setError(err instanceof Error ? err.message : "DNS check could not be completed.");
    } finally {
      setBusyId(null);
    }
  }

  async function revokeDomain(item: DomainItem) {
    setBusyId(item.id);
    setError("");
    setNotice("");
    try {
      await request(`/organization/domains/${item.id}`, { method: "DELETE" });
      if (activeChallenge?.id === item.id) setActiveChallenge(null);
      setNotice(`Revoked verification for ${item.domain}.`);
      await domains.refetch();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not revoke domain.");
    } finally {
      setBusyId(null);
    }
  }

  const items = domains.data?.items || [];
  const canEdit = Boolean(domains.data?.can_edit);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-foreground">Business Domains</h3>
          <p className="text-[11px] text-muted-foreground">
            Verify company domain ownership via DNS TXT records (separate from public website URLs).
          </p>
        </div>
        {canEdit && (
          <Button
            size="sm"
            onClick={() => {
              setError("");
              setAddOpen(true);
            }}
            className="h-8 text-xs gap-1.5"
          >
            <Plus size={13} />
            Add Domain
          </Button>
        )}
      </div>

      {notice && (
        <div role="status" className="flex items-center gap-2 rounded-xl border border-emerald-500/25 bg-emerald-500/10 px-3.5 py-2.5 text-xs font-medium text-emerald-700 dark:text-emerald-300">
          <CheckCircle2 size={14} className="shrink-0" />
          <span>{notice}</span>
        </div>
      )}
      {error && !addOpen && (
        <div role="alert" className="flex items-start gap-2 rounded-xl border border-destructive/25 bg-destructive/5 px-3.5 py-2.5 text-xs text-destructive">
          <AlertTriangle size={14} className="shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {/* Guided DNS Verification Card (shown after generating/regenerating a challenge) */}
      {activeChallenge && (
        <section className="rounded-xl border border-primary/30 bg-primary/[0.03] p-4 space-y-3.5">
          <div className="flex items-start justify-between gap-2">
            <div>
              <h4 className="text-xs font-semibold text-foreground">
                DNS Verification Instructions · {activeChallenge.domain}
              </h4>
              <p className="text-[11px] text-muted-foreground mt-0.5">
                Add this TXT record at your DNS provider, wait for propagation, then click Verify Now. Expires {formatDateTime(activeChallenge.expires_at)}.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setActiveChallenge(null)}
              aria-label="Close DNS instructions"
              className="rounded p-1 text-muted-foreground hover:bg-muted cursor-pointer"
            >
              <X size={14} />
            </button>
          </div>

          <div className="grid gap-2.5 sm:grid-cols-2">
            <div className="rounded-lg border border-border bg-card p-3 space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Record Name ({activeChallenge.record_type})
                </span>
                <button
                  type="button"
                  onClick={() => void copyText("name", activeChallenge.record_name)}
                  className="inline-flex items-center gap-1 text-[11px] font-medium text-primary hover:underline cursor-pointer"
                >
                  {copiedField === "name" ? <Check size={11} /> : <Copy size={11} />}
                  {copiedField === "name" ? "Copied" : "Copy"}
                </button>
              </div>
              <p className="font-mono text-[11px] text-foreground break-all">
                {activeChallenge.record_name}
              </p>
            </div>

            <div className="rounded-lg border border-border bg-card p-3 space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Record Value
                </span>
                <button
                  type="button"
                  onClick={() => void copyText("value", activeChallenge.record_value)}
                  className="inline-flex items-center gap-1 text-[11px] font-medium text-primary hover:underline cursor-pointer"
                >
                  {copiedField === "value" ? <Check size={11} /> : <Copy size={11} />}
                  {copiedField === "value" ? "Copied" : "Copy"}
                </button>
              </div>
              <p className="font-mono text-[11px] text-foreground break-all">
                {activeChallenge.record_value}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] text-muted-foreground">
            <span className="inline-flex items-center gap-1">
              <Clock size={12} /> Keep this value saved—for security it is only shown when created.
            </span>
            <Button
              size="sm"
              disabled={busyId === activeChallenge.id}
              onClick={() =>
                void verifyDomain({
                  id: activeChallenge.id,
                  domain: activeChallenge.domain,
                  status: "PENDING",
                })
              }
              className="h-7 px-3 text-xs gap-1.5"
            >
              <ShieldCheck size={13} />
              {busyId === activeChallenge.id ? "Checking DNS…" : "Verify Now"}
            </Button>
          </div>
        </section>
      )}

      {/* Compact Domains Table */}
      {domains.isPending ? (
        <div className="h-36 rounded-xl border border-border bg-muted/30 animate-pulse" />
      ) : (
        <section className="rounded-xl border border-border bg-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse" aria-label="Business domains">
              <thead className="bg-muted/40 text-[11px] font-semibold text-muted-foreground border-b border-border">
                <tr>
                  <th scope="col" className="px-4 py-2.5">Domain</th>
                  <th scope="col" className="px-4 py-2.5">Verification Status</th>
                  <th scope="col" className="px-4 py-2.5">Last Checked</th>
                  <th scope="col" className="px-4 py-2.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/70">
                {items.map((item) => {
                  const meta = STATUS_META[item.status] || STATUS_META.PENDING;
                  const isBusy = busyId === item.id;
                  return (
                    <tr key={item.id} className="hover:bg-muted/20">
                      <td className="px-4 py-3">
                        <div className="font-semibold text-foreground">{item.domain}</div>
                        {item.status === "PENDING" && item.record_name && (
                          <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground font-mono mt-0.5">
                            <span>TXT {item.record_name}</span>
                            <button
                              type="button"
                              onClick={() => void copyText(item.id, item.record_name!)}
                              className="text-primary hover:underline cursor-pointer"
                            >
                              {copiedField === item.id ? "Copied" : "Copy host"}
                            </button>
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold ${meta.style}`}
                        >
                          {meta.label}
                        </span>
                        {item.status === "PENDING" && item.challenge_expires_at && (
                          <p className="text-[10px] text-muted-foreground mt-0.5">
                            Expires {formatDateTime(item.challenge_expires_at)}
                          </p>
                        )}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground tabular-nums">
                        {item.status === "VERIFIED"
                          ? `Verified ${formatDateTime(item.verified_at)}`
                          : formatDateTime(item.checked_at)}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {canEdit ? (
                          <div className="inline-flex items-center gap-1.5">
                            {item.status === "PENDING" && (
                              <Button
                                size="sm"
                                variant="outline"
                                disabled={isBusy}
                                onClick={() => void verifyDomain(item)}
                                className="h-7 px-2.5 text-[11px] gap-1"
                              >
                                <RefreshCw size={11} className={isBusy ? "animate-spin" : ""} />
                                Verify
                              </Button>
                            )}
                            {(item.status === "EXPIRED" || item.status === "REVOKED") && (
                              <Button
                                size="sm"
                                variant="outline"
                                disabled={creating}
                                onClick={() => void createChallenge(item.domain)}
                                className="h-7 px-2.5 text-[11px] gap-1"
                              >
                                <RefreshCw size={11} />
                                New Challenge
                              </Button>
                            )}
                            {item.status !== "REVOKED" && (
                              <Button
                                size="sm"
                                variant="ghost"
                                disabled={isBusy}
                                onClick={() => void revokeDomain(item)}
                                className="h-7 px-2 text-[11px] text-muted-foreground hover:text-destructive gap-1"
                              >
                                <Trash2 size={11} />
                                Revoke
                              </Button>
                            )}
                          </div>
                        ) : (
                          <span className="text-[11px] text-muted-foreground/60">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
                {items.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-4 py-8 text-center text-muted-foreground">
                      <Globe className="mx-auto mb-2 h-5 w-5 opacity-50" />
                      No business domains verified yet. Add a domain to generate a DNS TXT verification record.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Add Domain Dialog */}
      <Dialog.Root open={addOpen} onOpenChange={setAddOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40 backdrop-blur-[1px]" />
          <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[calc(100%-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-border bg-card p-5 shadow-xl space-y-4">
            <div className="flex items-start justify-between gap-2">
              <div>
                <Dialog.Title className="text-base font-semibold text-foreground">
                  Add Business Domain
                </Dialog.Title>
                <Dialog.Description className="text-xs text-muted-foreground mt-0.5">
                  Enter your domain (without https://) to generate a DNS TXT verification record.
                </Dialog.Description>
              </div>
              <Dialog.Close asChild>
                <button className="rounded-lg p-1 text-muted-foreground hover:bg-muted" aria-label="Close">
                  <X size={16} />
                </button>
              </Dialog.Close>
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                void createChallenge(domainInput);
              }}
              className="space-y-3.5"
            >
              <div className="space-y-1">
                <label htmlFor="add-domain-input" className="text-xs font-medium text-foreground">
                  Domain name
                </label>
                <Input
                  id="add-domain-input"
                  placeholder="example.com"
                  required
                  value={domainInput}
                  disabled={creating}
                  onChange={(e) => setDomainInput(e.target.value)}
                />
              </div>

              {error && (
                <p role="alert" className="text-xs text-destructive">
                  {error}
                </p>
              )}

              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" size="sm" onClick={() => setAddOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" size="sm" disabled={creating || !domainInput.trim()}>
                  {creating ? "Generating…" : "Generate DNS Record"}
                </Button>
              </div>
            </form>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}
