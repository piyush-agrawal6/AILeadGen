"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Check,
  Code2,
  Copy,
  Eye,
  EyeOff,
  KeyRound,
  Lock,
  Plus,
  RefreshCw,
  ShieldCheck,
  Terminal,
  Trash2,
} from "lucide-react";
import { request } from "@/lib/intelligence";
import { copilotConfiguration } from "@/lib/mcp-configuration";
import { useWorkspaceCapabilities } from "@/components/workspaces/features";
import { DeveloperApprovals } from "@/components/workspaces/developer-approvals";
import { WebhookSettings } from "@/components/workspaces/webhook-settings";
import { Button } from "@/components/ui/button";

type Key = {
  id: string;
  name: string;
  scopes: string[];
  created_at: string;
  expires_at: string;
  revoked_at: string | null;
  last_used_at: string | null;
};

export function DeveloperSettings() {
  const leadAvailable = useWorkspaceCapabilities().leadEngineAvailable !== false;
  const [name, setName] = useState("");
  const [scopes, setScopes] = useState<string[]>([]);
  const [days, setDays] = useState(90);
  const [token, setToken] = useState("");
  const [revealToken, setRevealToken] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [confirm, setConfirm] = useState<{ id: string; name: string; action: "rotate" | "revoke" } | null>(null);
  const [copiedLabel, setCopiedLabel] = useState("");

  const status = useQuery({
    queryKey: ["developer-status"],
    queryFn: () =>
      request<{
        enabled: boolean;
        can_manage: boolean;
        mcp_available: boolean;
        webhooks_available?: boolean;
      }>("/organization/developer/status"),
    retry: false,
  });

  const list = useQuery({
    queryKey: ["developer-keys"],
    queryFn: () =>
      request<{ items: Key[]; available_scopes: string[]; rate_limit_per_minute: number }>(
        "/organization/developer/keys"
      ),
    enabled: !!status.data?.enabled && status.data.can_manage,
    retry: false,
  });

  const mcpEndpoint =
    typeof window !== "undefined" ? `${window.location.origin}/api/v1/mcp` : "/api/v1/mcp";

  async function copyText(value: string, label: string) {
    try {
      await navigator.clipboard.writeText(value);
      setCopiedLabel(label);
      setTimeout(() => setCopiedLabel(""), 2500);
    } catch {
      setError("Clipboard is unavailable. Select and copy the value manually.");
    }
  }

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await request<{ token: string }>("/organization/developer/keys", {
        method: "POST",
        body: JSON.stringify({
          name,
          scopes: scopes.filter((scope) => list.data?.available_scopes.includes(scope)),
          lifetime_days: days,
        }),
      });
      setToken(result.token);
      setRevealToken(false);
      setCopiedLabel("");
      setName("");
      await list.refetch();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "The key could not be created. Review existing keys and revoke any uncertain credential before retrying."
      );
    } finally {
      setBusy(false);
    }
  }

  async function apply() {
    if (!confirm) return;
    setBusy(true);
    setError("");
    try {
      const result = await request<{ token?: string }>(
        "/organization/developer/keys/" +
          confirm.id +
          (confirm.action === "rotate" ? "/rotate" : ""),
        { method: confirm.action === "rotate" ? "POST" : "DELETE" }
      );
      setToken(result.token || "");
      setRevealToken(false);
      setCopiedLabel("");
      setConfirm(null);
      await list.refetch();
    } catch (err) {
      setError(err instanceof Error ? err.message : "The credential could not be updated.");
    } finally {
      setBusy(false);
    }
  }

  if (status.isPending) {
    return (
      <div className="space-y-4" role="status" aria-label="Checking developer access">
        <div className="h-32 rounded-2xl border border-border bg-muted/30 animate-pulse" />
        <div className="h-44 rounded-2xl border border-border bg-muted/30 animate-pulse" />
      </div>
    );
  }

  if (status.error) {
    return (
      <div role="alert" className="rounded-2xl border border-destructive/25 bg-destructive/5 p-5 text-xs text-destructive">
        {status.error.message}
      </div>
    );
  }

  if (!status.data?.enabled) {
    return (
      <div className="rounded-2xl border border-border bg-card p-6 text-sm text-muted-foreground">
        The Developer API is disabled in this environment. Existing workspace workflows remain available.
      </div>
    );
  }

  if (!status.data.can_manage) {
    return (
      <div className="rounded-2xl border border-border bg-card p-6 text-sm text-muted-foreground">
        Only a workspace owner or administrator can manage MCP and Developer API credentials.
      </div>
    );
  }

  const keys = list.data?.items || [];
  const activeKeyCount = keys.filter((k) => !k.revoked_at && new Date(k.expires_at) > new Date()).length;

  return (
    <div className="space-y-6">
      {/* Top 2-Column Connection & API Overview */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* MCP Connection Card */}
        <section className="rounded-2xl border border-border bg-card p-5 space-y-3.5">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <Terminal size={17} aria-hidden="true" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-foreground">MCP Server (Streamable HTTP)</h3>
                <p className="text-[11px] text-muted-foreground">
                  Read-only workspace intelligence for MCP-compatible clients
                </p>
              </div>
            </div>
            <span
              className={
                "rounded-full border px-2.5 py-0.5 text-[11px] font-semibold " +
                (status.data.mcp_available
                  ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/25"
                  : "bg-muted text-muted-foreground border-border")
              }
            >
              {status.data.mcp_available ? "Available" : "Disabled"}
            </span>
          </div>

          <div className="space-y-2 text-xs">
            <div className="flex items-center justify-between gap-2 rounded-xl border border-border/80 bg-muted/25 px-3 py-2">
              <code className="truncate text-[11px] text-foreground">{mcpEndpoint}</code>
              <button
                type="button"
                onClick={() => void copyText(mcpEndpoint, "endpoint")}
                className="inline-flex items-center gap-1 text-[11px] font-semibold text-primary hover:underline shrink-0 cursor-pointer"
              >
                {copiedLabel === "endpoint" ? <Check size={12} /> : <Copy size={12} />}
                {copiedLabel === "endpoint" ? "Copied" : "Copy"}
              </button>
            </div>
            <p className="text-[11px] text-muted-foreground leading-relaxed">
              Authenticate with <code>Authorization: Bearer YOUR_KEY</code> using a scoped key carrying{" "}
              <code>mcp:use</code> and <code>intent:read</code>.
            </p>
          </div>

          {status.data.mcp_available && (
            <div className="flex flex-wrap gap-2 pt-1">
              <Button
                variant="outline"
                size="sm"
                className="h-8 text-xs gap-1.5"
                onClick={() => void copyText(copilotConfiguration(mcpEndpoint), "mcp-config")}
              >
                {copiedLabel === "mcp-config" ? <Check size={12} /> : <Copy size={12} />}
                {copiedLabel === "mcp-config" ? "Config copied" : "Copy MCP JSON config"}
              </Button>
            </div>
          )}
        </section>

        {/* Developer API Access & Limits Card */}
        <section className="rounded-2xl border border-border bg-card p-5 space-y-3.5">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-500/10 text-blue-600 dark:text-blue-400">
                <Code2 size={17} aria-hidden="true" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-foreground">Developer REST API v1</h3>
                <p className="text-[11px] text-muted-foreground">
                  Workspace-scoped programmatic access with idempotent writes
                </p>
              </div>
            </div>
            <span className="rounded-full border border-border bg-muted px-2.5 py-0.5 text-[11px] font-semibold text-foreground tabular-nums">
              {list.data?.rate_limit_per_minute || 60} req/min
            </span>
          </div>

          <dl className="grid grid-cols-2 gap-2.5 text-xs">
            <div className="rounded-xl bg-muted/25 px-3 py-2">
              <dt className="text-[11px] text-muted-foreground">Base path</dt>
              <dd className="font-mono font-medium text-foreground mt-0.5">/api/v1</dd>
            </div>
            <div className="rounded-xl bg-muted/25 px-3 py-2">
              <dt className="text-[11px] text-muted-foreground">OpenAPI schema</dt>
              <dd className="font-mono font-medium text-foreground mt-0.5">/api/v1/openapi.json</dd>
            </div>
          </dl>

          <p className="text-[11px] text-muted-foreground leading-relaxed">
            Never pass API keys in URLs. Write endpoints require a unique UUID in the{" "}
            <code>Idempotency-Key</code> header. Keys inherit active workspace membership and permissions on every call.
          </p>
        </section>
      </div>

      {/* One-time Secret Display Banner (masked by default!) */}
      {token && (
        <section
          role="status"
          className="rounded-2xl border border-primary/30 bg-primary/5 p-5 space-y-3"
        >
          <div className="flex items-center gap-2">
            <ShieldCheck size={17} className="text-primary" aria-hidden="true" />
            <h3 className="font-semibold text-sm text-foreground">Save your new API key now</h3>
          </div>
          <p className="text-xs text-muted-foreground">
            This is the only time the full secret is displayed. Store it in a secure secret manager — never commit it to source control or client-side code.
          </p>
          <div className="flex items-center gap-2">
            <label className="sr-only" htmlFor="one-time-api-key">
              One-time API key
            </label>
            <input
              id="one-time-api-key"
              className="flex-1 rounded-xl border border-border bg-card px-3 py-2 font-mono text-xs text-foreground"
              readOnly
              type={revealToken ? "text" : "password"}
              value={token}
            />
            <Button
              type="button"
              variant="outline"
              size="sm"
              aria-label={revealToken ? "Hide API key" : "Reveal API key"}
              onClick={() => setRevealToken((v) => !v)}
            >
              {revealToken ? <EyeOff size={14} /> : <Eye size={14} />}
            </Button>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              size="sm"
              onClick={() => void copyText(token, "key")}
              className="gap-1.5"
            >
              {copiedLabel === "key" ? <Check size={13} /> : <Copy size={13} />}
              {copiedLabel === "key" ? "Copied" : "Copy key"}
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => {
                setToken("");
                setRevealToken(false);
              }}
            >
              I have saved the key
            </Button>
          </div>
        </section>
      )}

      {/* Create Scoped API Key */}
      <section className="rounded-2xl border border-border bg-card p-5 space-y-4">
        <div className="flex items-center gap-2">
          <Plus size={16} className="text-primary" aria-hidden="true" />
          <h3 className="font-semibold text-sm text-foreground">Create scoped API key</h3>
        </div>

        <form className="space-y-4" onSubmit={(e) => void create(e)}>
          <fieldset disabled={busy} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-3">
              <div className="sm:col-span-2 space-y-1.5">
                <label htmlFor="dev-key-name" className="block text-xs font-medium text-foreground">
                  Key name
                </label>
                <input
                  id="dev-key-name"
                  aria-label="Key name"
                  className="w-full rounded-xl border border-border bg-card px-3 py-2 text-xs text-foreground"
                  required
                  minLength={2}
                  maxLength={100}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Cursor MCP client or internal integration"
                />
              </div>

              <div className="space-y-1.5">
                <label htmlFor="dev-key-days" className="block text-xs font-medium text-foreground">
                  Expires in days
                </label>
                <input
                  id="dev-key-days"
                  aria-label="Expires in days"
                  className="w-full rounded-xl border border-border bg-card px-3 py-2 text-xs text-foreground"
                  type="number"
                  required
                  min={1}
                  max={365}
                  value={days}
                  onChange={(e) => setDays(Number(e.target.value))}
                />
              </div>
            </div>

            <div className="space-y-2">
              <p className="text-xs font-medium text-foreground">Permissions &amp; scopes</p>
              <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                {list.data?.available_scopes.map((scope) => (
                  <label
                    key={scope}
                    className="flex items-center gap-2.5 rounded-xl border border-border/80 bg-muted/15 px-3 py-2 text-xs cursor-pointer hover:border-primary/40"
                  >
                    <input
                      type="checkbox"
                      aria-label={scope}
                      checked={scopes.includes(scope)}
                      onChange={(e) =>
                        setScopes((values) =>
                          e.target.checked
                            ? [...values, scope]
                            : values.filter((value) => value !== scope)
                        )
                      }
                      className="accent-primary"
                    />
                    <code className="text-[11px]">{scope}</code>
                  </label>
                ))}
              </div>
            </div>
          </fieldset>

          <Button
            type="submit"
            size="sm"
            disabled={
              busy ||
              !name.trim() ||
              !scopes.some((scope) => list.data?.available_scopes.includes(scope)) ||
              !!token
            }
          >
            {busy ? "Creating…" : "Create API key"}
          </Button>
        </form>
      </section>

      {/* Active & Historical Workspace Keys */}
      <section className="space-y-3">
        <div className="flex items-center justify-between gap-2">
          <h3 className="font-semibold text-sm text-foreground">
            Workspace API Keys ({activeKeyCount} active)
          </h3>
          <span className="inline-flex items-center gap-1 text-[11px] text-muted-foreground">
            <Lock size={11} aria-hidden="true" /> Stored hashed · never displayed again
          </span>
        </div>

        {list.isPending ? (
          <div className="h-24 rounded-2xl border border-border bg-muted/30 animate-pulse" />
        ) : list.error ? (
          <p role="alert" className="text-xs text-destructive">
            {list.error.message}
          </p>
        ) : keys.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-border bg-muted/15 p-6 text-center space-y-1.5">
            <KeyRound size={20} className="mx-auto text-muted-foreground" aria-hidden="true" />
            <p className="text-sm font-medium text-foreground">No API keys created yet</p>
            <p className="text-xs text-muted-foreground">
              Create a scoped key above to connect an MCP client or call the Intent Radar API.
            </p>
          </div>
        ) : (
          <ul className="divide-y divide-border rounded-2xl border border-border bg-card overflow-hidden">
            {keys.map((key) => {
              const isExpired = !key.revoked_at && new Date(key.expires_at) <= new Date();
              const isActive = !key.revoked_at && !isExpired;
              return (
                <li className="p-4 space-y-2.5" key={key.id}>
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="space-y-0.5">
                      <div className="flex flex-wrap items-center gap-2">
                        <h4 className="font-semibold text-sm text-foreground">{key.name}</h4>
                        <span
                          className={
                            "rounded-full px-2 py-0.5 text-[10px] font-semibold " +
                            (isActive
                              ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
                              : "bg-muted text-muted-foreground")
                          }
                        >
                          {key.revoked_at ? "Revoked" : isExpired ? "Expired" : "Active"}
                        </span>
                      </div>
                      <p className="text-[11px] text-muted-foreground">
                        Expires {new Date(key.expires_at).toLocaleDateString()} · Last used:{" "}
                        {key.last_used_at ? new Date(key.last_used_at).toLocaleString() : "Never"}
                      </p>
                    </div>

                    {!key.revoked_at && (
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={busy || !!token}
                          onClick={() => setConfirm({ id: key.id, name: key.name, action: "rotate" })}
                          className="h-8 text-xs gap-1"
                        >
                          <RefreshCw size={12} /> Rotate
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={busy}
                          onClick={() => setConfirm({ id: key.id, name: key.name, action: "revoke" })}
                          className="h-8 text-xs gap-1 text-destructive hover:text-destructive"
                        >
                          <Trash2 size={12} /> Revoke
                        </Button>
                      </div>
                    )}
                  </div>

                  <div className="flex flex-wrap gap-1.5">
                    {key.scopes.map((sc) => (
                      <code
                        key={sc}
                        className="rounded-md bg-muted px-2 py-0.5 text-[11px] text-muted-foreground"
                      >
                        {sc}
                      </code>
                    ))}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      {confirm && (
        <section
          role="alertdialog"
          aria-label={`Confirm key ${confirm.action}`}
          className="rounded-2xl border border-destructive/30 bg-destructive/5 p-5 space-y-3"
        >
          <p className="text-xs text-foreground leading-relaxed">
            <strong>
              {confirm.action === "rotate" ? "Rotate" : "Revoke"} “{confirm.name}”?
            </strong>{" "}
            {confirm.action === "rotate"
              ? "The existing credential will stop working immediately. Save and update the replacement key in your client."
              : "Any client using this key will immediately lose access. Workspace research history stays intact."}
          </p>
          <div className="flex gap-2">
            <Button size="sm" variant="destructive" disabled={busy} onClick={() => void apply()}>
              Confirm {confirm.action}
            </Button>
            <Button size="sm" variant="outline" disabled={busy} onClick={() => setConfirm(null)}>
              Cancel
            </Button>
          </div>
        </section>
      )}

      {status.data.mcp_available && leadAvailable && <DeveloperApprovals />}
      {leadAvailable && status.data.webhooks_available && <WebhookSettings />}
      {error && (
        <p role="alert" className="text-xs font-medium text-destructive">
          {error}
        </p>
      )}
    </div>
  );
}
