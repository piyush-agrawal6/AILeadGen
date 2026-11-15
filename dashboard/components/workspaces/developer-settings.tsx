"use client";

import { useWorkspaceCapabilities } from "@/components/workspaces/features";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { request } from "@/lib/intelligence";
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
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [confirm, setConfirm] = useState<{ id: string; action: "rotate" | "revoke" } | null>(null);
  const [copied, setCopied] = useState(false);

  const status = useQuery({
    queryKey: ["developer-status"],
    queryFn: () => request<{ enabled: boolean; can_manage: boolean; mcp_available: boolean; webhooks_available?: boolean }>("/organization/developer/status"),
    retry: false,
  });

  const list = useQuery({
    queryKey: ["developer-keys"],
    queryFn: () => request<{ items: Key[]; available_scopes: string[]; rate_limit_per_minute: number }>("/organization/developer/keys"),
    enabled: !!status.data?.enabled && status.data.can_manage,
    retry: false,
  });

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
      setCopied(false);
      setName("");
      await list.refetch();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "The key could not be created. If the response was interrupted, review existing keys and revoke the uncertain credential before creating another."
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
        "/organization/developer/keys/" + confirm.id + (confirm.action === "rotate" ? "/rotate" : ""),
        { method: confirm.action === "rotate" ? "POST" : "DELETE" }
      );
      setToken(result.token || "");
      setCopied(false);
      setConfirm(null);
      await list.refetch();
    } catch (err) {
      setError(err instanceof Error ? err.message : "The credential could not be updated.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-xl font-semibold tracking-tight">Developer Access & MCP</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Connect your own tools using workspace-scoped API keys. Keys inherit the issuing member’s current access; revocation and workspace membership changes are enforced on every request.
        </p>
      </header>

      {status.isPending ? (
        <p role="status" className="text-sm text-muted-foreground">Checking developer access…</p>
      ) : status.error ? (
        <p role="alert" className="text-sm text-destructive">{status.error.message}</p>
      ) : !status.data?.enabled ? (
        <p className="text-sm text-muted-foreground">The developer API is disabled in this environment. Existing workspace workflows remain available.</p>
      ) : !status.data.can_manage ? (
        <p className="text-sm text-muted-foreground">Only a workspace owner or administrator can manage API credentials.</p>
      ) : (
        <>
          {token && (
            <section className="rounded-xl border border-primary/20 bg-primary/5 p-5 space-y-3">
              <h3 className="font-semibold text-sm">Save your new API key</h3>
              <p className="text-xs text-muted-foreground">
                This is the only time the full key is shown. Store it in your own secret manager. Do not put it in a website, URL, shared document or source control.
              </p>
              <label className="block text-xs font-medium">
                One-time API key
                <input className="control mt-1.5 w-full font-mono text-xs" readOnly type="password" value={token} />
              </label>
              <div className="flex flex-wrap gap-3">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={async () => {
                    try {
                      await navigator.clipboard.writeText(token);
                      setCopied(true);
                    } catch {
                      setError("Clipboard is unavailable. Select and securely copy the key before dismissing.");
                    }
                  }}
                >
                  {copied ? "Copied" : "Copy key"}
                </Button>
                <Button variant="outline" size="sm" onClick={() => setToken("")}>
                  I have saved the key
                </Button>
              </div>
            </section>
          )}

          <section className="rounded-xl border bg-card p-5 space-y-4">
            <h3 className="font-semibold text-sm">Create scoped API key</h3>
            <form className="space-y-4" onSubmit={create}>
              <fieldset disabled={busy} className="space-y-4">
                <div className="space-y-1.5">
                  <label htmlFor="dev-key-name" className="text-xs font-medium">Key name</label>
                  <input
                    id="dev-key-name"
                    aria-label="Key name"
                    className="control w-full"
                    required
                    minLength={2}
                    maxLength={100}
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Your CRM or internal integration"
                  />
                </div>

                <div className="space-y-1.5">
                  <label htmlFor="dev-key-days" className="text-xs font-medium">Expires in days</label>
                  <input
                    id="dev-key-days"
                    aria-label="Expires in days"
                    className="control w-full"
                    type="number"
                    required
                    min={1}
                    max={365}
                    value={days}
                    onChange={(e) => setDays(Number(e.target.value))}
                  />
                </div>

                <div className="space-y-2">
                  <p className="text-xs font-medium">Permissions</p>
                  <div className="mt-2 grid gap-2.5 sm:grid-cols-2">
                    {list.data?.available_scopes.map((scope) => (
                      <label key={scope} className="flex items-center gap-2.5 text-xs cursor-pointer">
                        <input
                          type="checkbox"
                          aria-label={scope}
                          checked={scopes.includes(scope)}
                          onChange={(e) =>
                            setScopes((values) =>
                              e.target.checked ? [...values, scope] : values.filter((value) => value !== scope)
                            )
                          }
                          className="accent-primary"
                        />
                        <code>{scope}</code>
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
                {busy ? "Working…" : "Create API key"}
              </Button>
            </form>
          </section>

          <section className="space-y-3">
            <h3 className="font-semibold text-sm">Active Workspace Keys</h3>
            {list.isPending ? (
              <p role="status" className="text-xs text-muted-foreground">Loading keys…</p>
            ) : list.error ? (
              <p role="alert" className="text-xs text-destructive">{list.error.message}</p>
            ) : (
              <ul className="divide-y rounded-xl border bg-card overflow-hidden">
                {list.data?.items.map((key) => (
                  <li className="p-4 space-y-2" key={key.id}>
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <h4 className="font-medium text-sm">{key.name}</h4>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          {key.revoked_at
                            ? "Revoked"
                            : new Date(key.expires_at) <= new Date()
                            ? "Expired"
                            : "Active"}{" "}
                          · Expires {new Date(key.expires_at).toLocaleDateString()}
                        </p>
                      </div>
                      {!key.revoked_at && (
                        <div className="flex gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            disabled={busy || !!token}
                            onClick={() => setConfirm({ id: key.id, action: "rotate" })}
                          >
                            Rotate
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            disabled={busy}
                            onClick={() => setConfirm({ id: key.id, action: "revoke" })}
                          >
                            Revoke
                          </Button>
                        </div>
                      )}
                    </div>
                    <p className="text-xs font-mono text-muted-foreground break-words">{key.scopes.join(" · ")}</p>
                    <p className="text-[11px] text-muted-foreground">
                      Last used: {key.last_used_at ? new Date(key.last_used_at).toLocaleString() : "Never"}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </section>

          {confirm && (
            <section className="rounded-xl border border-destructive/20 bg-destructive/5 p-5 space-y-3">
              <p className="text-sm">
                {confirm.action === "rotate"
                  ? "Rotate this key? The existing credential will stop working immediately. Save and configure the new credential in your client."
                  : "Revoke this key? Its clients will immediately lose access. Historical data stays intact."}
              </p>
              <div className="flex gap-3">
                <Button size="sm" disabled={busy} onClick={() => void apply()}>
                  Confirm {confirm.action}
                </Button>
                <Button variant="outline" size="sm" disabled={busy} onClick={() => setConfirm(null)}>
                  Cancel
                </Button>
              </div>
            </section>
          )}

          <section className="rounded-xl border bg-card p-5 space-y-3">
            <h3 className="font-semibold text-sm">API v1 Specifications</h3>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Use header <code>Authorization: Bearer YOUR_KEY</code>. Never place credentials in URLs. Each key is limited to {list.data?.rate_limit_per_minute || 60} requests per minute with an additional workspace cap. Write requests require a unique UUID in the <code>Idempotency-Key</code> header.
            </p>
            <p className="text-xs text-muted-foreground">
              Base path: <code>/api/v1</code> · Authenticated schema: <code>/api/v1/openapi.json</code>.
            </p>
          </section>

          {status.data.mcp_available && (
            <>
              <section className="rounded-xl border bg-card p-5 space-y-3">
                <h3 className="font-semibold text-sm">Connect an MCP client</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Use endpoint <code>/api/v1/mcp</code> over Streamable HTTP. Add an Authorization bearer header using a dedicated scoped key with <code>mcp:use</code> and <code>intent:read</code> permissions.
                </p>
              </section>
              {leadAvailable && <DeveloperApprovals />}
            </>
          )}

          {leadAvailable && status.data.webhooks_available && <WebhookSettings />}
        </>
      )}

      {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
    </div>
  );
}
