"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  AlertCircle,
  BookOpen,
  Check,
  CheckCircle2,
  Code2,
  Copy,
  Eye,
  EyeOff,
  Info,
  KeyRound,
  Loader2,
  Lock,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  Terminal,
  Trash2,
  Wifi,
} from "lucide-react";
import { request } from "@/lib/intelligence";
import {
  copilotConfiguration,
  mcpClientSnippet,
  type McpClientId,
} from "@/lib/mcp-configuration";
import { useWorkspaceCapabilities } from "@/components/workspaces/features";
import { DeveloperApprovals } from "@/components/workspaces/developer-approvals";
import { WebhookSettings } from "@/components/workspaces/webhook-settings";
import { SlideOverDrawer } from "@/components/intent-radar/integrations/SlideOverDrawer";
import { Button } from "@/components/ui/button";

type ApiKeyRow = {
  id: string;
  name: string;
  key_prefix?: string;
  status?: "Active" | "Expired" | "Revoked";
  scopes: string[];
  created_at: string;
  expires_at: string;
  revoked_at: string | null;
  last_used_at: string | null;
};

type DiagnosticsResponse = {
  ok: boolean;
  checked_at: string;
  workspace_id?: string;
  rest_api: {
    enabled: boolean;
    base_path: string;
    openapi_path: string;
    endpoint_count: number;
    rate_limit_per_minute: number;
  };
  mcp: {
    enabled: boolean;
    endpoint_path: string;
    transport: string;
    authentication: string;
    oauth_2_1_supported: boolean;
    oauth_note?: string;
    tools: string[];
    resources: string[];
  };
  available_scopes: string[];
  active_keys: number;
  last_used_at: string | null;
};

type UsageResponse = {
  keys: {
    total: number;
    active: number;
    revoked: number;
    expired: number;
    last_used_at: string | null;
  };
  rate_limits: {
    per_key_per_minute: number;
    per_workspace_per_minute: number;
    requests_current_minute: number;
  };
  usage: {
    mcp_calls_today: number;
    mcp_calls_month: number;
    mcp_errors_month: number;
    monthly_api_requests_used: number;
    monthly_api_requests_limit: number | null;
  };
  recent_events: {
    id: string;
    actor: string;
    action: string;
    entity: string;
    result: string;
    tool: string | null;
    created_at: string;
  }[];
};

type OpenApiDoc = {
  openapi?: string;
  info?: { title?: string; version?: string; description?: string };
  paths?: Record<
    string,
    Record<
      string,
      {
        summary?: string;
        description?: string;
        parameters?: {
          name: string;
          in: string;
          required?: boolean;
          description?: string;
          schema?: { type?: string; default?: unknown };
        }[];
        responses?: Record<string, { description?: string }>;
      }
    >
  >;
};

export type DevTabKey = "keys" | "overview" | "mcp" | "api" | "usage";

const SCOPE_DESCRIPTIONS: Record<string, string> = {
  "intent:read": "Read workspace Intent Radar signals, discoveries, saved searches, monitors, opportunities, ICPs, and source status.",
  "mcp:use": "Connect read-only MCP clients over Streamable HTTP (combine with intent:read).",
  "companies:read": "Read workspace companies and accounts.",
  "companies:write": "Create or update workspace companies.",
  "leads:read": "Read workspace contacts and leads.",
  "leads:write": "Create or update workspace leads.",
  "approvals:write": "Propose approval-gated write actions.",
};

const MCP_RESOURCES = [
  {
    uri: "planebyte://workspace/context",
    description: "Workspace company context, active ICP count, and enabled Intent Radar summary.",
  },
  {
    uri: "planebyte://sources/catalog",
    description: "Configured workspace sources, operational availability, and enabled feed count.",
  },
  {
    uri: "planebyte://sources/policies",
    description: "Centralized commercial-use and AI-processing policy matrix for all research sources.",
  },
];

const MCP_TOOLS_CATALOG = [
  { name: "search_intent_signals", desc: "Search and filter workspace signals by query, source, category, status, saved state, and min score." },
  { name: "get_intent_signal", desc: "Retrieve full signal detail, provenance, and latest AI analysis." },
  { name: "list_intent_monitors", desc: "List active and paused scheduled monitors in the workspace." },
  { name: "list_intent_discoveries", desc: "List recent Discovery 2.0 research runs with match counts and source runs." },
  { name: "get_intent_discovery", desc: "Inspect a specific discovery run configuration, strategy, and matched signals." },
  { name: "list_saved_searches", desc: "List reusable saved discovery searches in the workspace." },
  { name: "list_intent_icps", desc: "List ideal customer profiles (ICPs) configured for targeting." },
  { name: "list_intent_opportunities", desc: "List qualified opportunities linked to Intent Radar signals." },
  { name: "list_intent_alerts", desc: "List unread and recent monitor alert notifications." },
  { name: "get_intent_overview", desc: "Get workspace overview KPIs, trends, and recent signals." },
  { name: "list_intent_sources", desc: "Inspect available research sources and adapter states." },
  { name: "get_company_profile", desc: "Read the workspace organization profile and positioning." },
  { name: "list_intent_saved", desc: "List bookmarked/saved signals and collections." },
];

function computeKeyStatus(key: ApiKeyRow): "Active" | "Expired" | "Revoked" {
  if (key.status) return key.status;
  if (key.revoked_at) return "Revoked";
  if (new Date(key.expires_at) <= new Date()) return "Expired";
  return "Active";
}

function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "Never";
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function formatShortDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

function buildCodeExample(
  lang: "curl" | "ts" | "python",
  origin: string,
  method: string,
  path: string
): string {
  const fullPath = path.startsWith("/api/") ? path : `/api${path}`;
  const url = `${origin}${fullPath}`;
  if (lang === "curl") {
    return [
      `curl -X ${method.toUpperCase()} "${url}" \\`,
      `  -H "Authorization: Bearer $PLANEBYTE_API_KEY" \\`,
      `  -H "Accept: application/json"`,
    ].join("\n");
  }
  if (lang === "ts") {
    return [
      `const response = await fetch("${url}", {`,
      `  method: "${method.toUpperCase()}",`,
      `  headers: {`,
      `    Authorization: \`Bearer \${process.env.PLANEBYTE_API_KEY}\`,`,
      `    Accept: "application/json",`,
      `  },`,
      `});`,
      `if (!response.ok) throw new Error(\`HTTP \${response.status}\`);`,
      `const data = await response.json();`,
    ].join("\n");
  }
  return [
    `import os, httpx`,
    ``,
    `resp = httpx.request(`,
    `    "${method.toUpperCase()}",`,
    `    "${url}",`,
    `    headers={"Authorization": f"Bearer {os.environ['PLANEBYTE_API_KEY']}"},`,
    `    timeout=15.0,`,
    `)`,
    `resp.raise_for_status()`,
    `data = resp.json()`,
  ].join("\n");
}

export function DeveloperSettings({
  activeTab: externalTab,
  onTabChange,
}: {
  activeTab?: DevTabKey;
  onTabChange?: (tab: DevTabKey) => void;
} = {}) {
  const leadAvailable = useWorkspaceCapabilities().leadEngineAvailable !== false;

  // Sub-tab navigation — defaults to "keys" to preserve immediate API key management & existing tests
  const [internalTab, setInternalTab] = useState<DevTabKey>("keys");
  const activeTab = externalTab ?? internalTab;

  function setActiveTab(tab: DevTabKey) {
    setInternalTab(tab);
    onTabChange?.(tab);
  }

  // Create & manage key state
  const [name, setName] = useState("");
  const [scopes, setScopes] = useState<string[]>([]);
  const [days, setDays] = useState(90);
  const [token, setToken] = useState("");
  const [revealToken, setRevealToken] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [confirm, setConfirm] = useState<{
    id: string;
    name: string;
    action: "rotate" | "revoke";
  } | null>(null);
  const [selectedKey, setSelectedKey] = useState<ApiKeyRow | null>(null);
  const [copiedLabel, setCopiedLabel] = useState("");

  // Diagnostics state
  const [diagLoading, setDiagLoading] = useState(false);
  const [diagResult, setDiagResult] = useState<DiagnosticsResponse | null>(null);

  // MCP Setup state
  const [mcpClient, setMcpClient] = useState<McpClientId>("claude_code");

  // API Reference state
  const [apiSearch, setApiSearch] = useState("");
  const [selectedEndpointKey, setSelectedEndpointKey] = useState<string>(
    "GET /v1/intent-radar/signals"
  );
  const [exampleLang, setExampleLang] = useState<"curl" | "ts" | "python">("curl");

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
      request<{ items: ApiKeyRow[]; available_scopes: string[]; rate_limit_per_minute: number }>(
        "/organization/developer/keys"
      ),
    enabled: !!status.data?.enabled && status.data.can_manage,
    retry: false,
  });

  const usageQuery = useQuery({
    queryKey: ["developer-usage"],
    queryFn: () => request<UsageResponse>("/organization/developer/usage"),
    enabled:
      !!status.data?.enabled &&
      status.data.can_manage &&
      (activeTab === "usage" || activeTab === "overview"),
    retry: false,
  });

  const openApiQuery = useQuery({
    queryKey: ["developer-openapi"],
    queryFn: () => request<OpenApiDoc>("/organization/developer/openapi"),
    enabled: !!status.data?.enabled && status.data.can_manage && activeTab === "api",
    retry: false,
  });

  const origin =
    typeof window !== "undefined" ? window.location.origin : "https://app.planebyte.com";
  const mcpEndpoint = `${origin}/api/v1/mcp`;

  async function copyText(value: string, label: string) {
    try {
      await navigator.clipboard.writeText(value);
      setCopiedLabel(label);
      setTimeout(() => setCopiedLabel(""), 2500);
    } catch {
      setError("Clipboard is unavailable. Select and copy the value manually.");
    }
  }

  async function runDiagnostics() {
    setDiagLoading(true);
    setError("");
    try {
      const res = await request<DiagnosticsResponse>("/organization/developer/diagnostics", {
        method: "POST",
        body: JSON.stringify({}),
      });
      setDiagResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not run developer diagnostics.");
    } finally {
      setDiagLoading(false);
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
      setSelectedKey(null);
      await list.refetch();
    } catch (err) {
      setError(err instanceof Error ? err.message : "The credential could not be updated.");
    } finally {
      setBusy(false);
    }
  }

  const openApiEndpoints = useMemo(() => {
    const paths = openApiQuery.data?.paths || {};
    const rows: {
      key: string;
      method: string;
      path: string;
      summary: string;
      description: string;
      parameters: {
        name: string;
        in: string;
        required?: boolean;
        description?: string;
        schema?: { type?: string; default?: unknown };
      }[];
    }[] = [];
    for (const [path, methods] of Object.entries(paths)) {
      for (const [method, meta] of Object.entries(methods || {})) {
        const upper = method.toUpperCase();
        if (!["GET", "POST", "PUT", "PATCH", "DELETE"].includes(upper)) continue;
        rows.push({
          key: `${upper} ${path}`,
          method: upper,
          path,
          summary: meta?.summary || path,
          description: meta?.description || "",
          parameters: meta?.parameters || [],
        });
      }
    }
    return rows;
  }, [openApiQuery.data?.paths]);

  const filteredEndpoints = useMemo(() => {
    const q = apiSearch.trim().toLowerCase();
    if (!q) return openApiEndpoints;
    return openApiEndpoints.filter((ep) =>
      `${ep.method} ${ep.path} ${ep.summary} ${ep.description}`.toLowerCase().includes(q)
    );
  }, [openApiEndpoints, apiSearch]);

  const activeEndpoint =
    openApiEndpoints.find((ep) => ep.key === selectedEndpointKey) ||
    filteredEndpoints[0] ||
    null;

  if (status.isPending) {
    return (
      <div className="space-y-4" role="status" aria-label="Checking developer access">
        <div className="grid gap-3 grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((n) => (
            <div key={n} className="h-20 rounded-xl border border-border bg-muted/30 animate-pulse" />
          ))}
        </div>
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
  const activeKeyCount = keys.filter((k) => computeKeyStatus(k) === "Active").length;
  const rateLimit = list.data?.rate_limit_per_minute || 60;
  const snippet = mcpClientSnippet(mcpClient, mcpEndpoint);

  return (
    <div className="space-y-6">
      {/* Compact Developer Summary Strip */}
      <div className="grid gap-3 grid-cols-2 lg:grid-cols-4" aria-label="Developer platform summary">
        <div className="rounded-xl border border-border bg-card px-4 py-3">
          <p className="text-[11px] font-medium text-muted-foreground">MCP Server</p>
          <p className="text-base font-bold tracking-tight text-foreground mt-0.5 flex items-center gap-1.5">
            <span
              className={
                "inline-block h-2 w-2 rounded-full " +
                (status.data.mcp_available ? "bg-emerald-500" : "bg-muted-foreground")
              }
            />
            {status.data.mcp_available ? "Available" : "Disabled"}
          </p>
          <p className="text-[11px] text-muted-foreground truncate">Streamable HTTP · Bearer key</p>
        </div>

        <div className="rounded-xl border border-border bg-card px-4 py-3">
          <p className="text-[11px] font-medium text-muted-foreground">REST API v1</p>
          <p className="text-base font-bold font-mono tracking-tight text-foreground mt-0.5">
            /api/v1
          </p>
          <p className="text-[11px] text-muted-foreground truncate">OpenAPI 3.1 · Workspace-scoped</p>
        </div>

        <div className="rounded-xl border border-border bg-card px-4 py-3">
          <p className="text-[11px] font-medium text-muted-foreground">Rate limit</p>
          <p className="text-base font-bold tracking-tight text-foreground mt-0.5 tabular-nums">
            {rateLimit} req/min
          </p>
          <p className="text-[11px] text-muted-foreground">Per workspace sliding window</p>
        </div>

        <div className="rounded-xl border border-border bg-card px-4 py-3">
          <p className="text-[11px] font-medium text-muted-foreground">Active API keys</p>
          <p className="text-base font-bold tracking-tight text-foreground mt-0.5 tabular-nums">
            {activeKeyCount}
            <span className="text-xs font-normal text-muted-foreground"> / {keys.length} total</span>
          </p>
          <p className="text-[11px] text-muted-foreground">Hashed at rest · instant revoke</p>
        </div>
      </div>

      {/* 5-Tab Developer Console Navigation */}
      <div
        role="tablist"
        aria-label="Developer console sections"
        className="flex items-center gap-1 overflow-x-auto rounded-xl border border-border bg-muted/50 p-1 w-fit max-w-full"
      >
        {(
          [
            { id: "keys", label: `API Keys (${activeKeyCount})`, icon: KeyRound },
            { id: "overview", label: "Overview & Diagnostics", icon: Activity },
            { id: "mcp", label: "MCP Setup", icon: Terminal },
            { id: "api", label: "API Reference", icon: BookOpen },
            { id: "usage", label: "Usage & Logs", icon: Code2 },
          ] as { id: DevTabKey; label: string; icon: typeof KeyRound }[]
        ).map((tab) => {
          const Icon = tab.icon;
          const active = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => setActiveTab(tab.id)}
              className={
                "inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium whitespace-nowrap transition-all cursor-pointer " +
                (active
                  ? "bg-card text-foreground shadow-sm font-semibold"
                  : "text-muted-foreground hover:text-foreground")
              }
            >
              <Icon size={13} aria-hidden="true" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {error && (
        <div
          role="alert"
          className="rounded-xl border border-destructive/25 bg-destructive/5 px-4 py-2.5 text-xs font-medium text-destructive flex items-center gap-2"
        >
          <AlertCircle size={14} className="shrink-0" aria-hidden="true" />
          <span>{error}</span>
        </div>
      )}

      {/* =================================================================
          TAB 1: API KEYS (Default Tab)
      ================================================================== */}
      {activeTab === "keys" && (
        <div className="space-y-6">
          {/* One-time Secret Display Banner (masked by default) */}
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
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <Plus size={16} className="text-primary" aria-hidden="true" />
                <h3 className="font-semibold text-sm text-foreground">Create scoped API key</h3>
              </div>
              <span className="text-[11px] text-muted-foreground">Least-privilege scopes required</span>
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
                      placeholder="e.g. Claude Code MCP or Analytics Worker"
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
                  <div className="grid gap-2 sm:grid-cols-2">
                    {list.data?.available_scopes.map((scope) => (
                      <label
                        key={scope}
                        className="flex items-start gap-2.5 rounded-xl border border-border/80 bg-muted/15 px-3 py-2.5 text-xs cursor-pointer hover:border-primary/40"
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
                          className="accent-primary mt-0.5"
                        />
                        <div className="min-w-0">
                          <code className="text-[11px] font-semibold text-foreground">{scope}</code>
                          {SCOPE_DESCRIPTIONS[scope] && (
                            <p className="text-[11px] text-muted-foreground mt-0.5 leading-snug">
                              {SCOPE_DESCRIPTIONS[scope]}
                            </p>
                          )}
                        </div>
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

          {/* Clean 8-Column API Keys Table */}
          <section className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="font-semibold text-sm text-foreground">
                Workspace API Keys ({activeKeyCount} active)
              </h3>
              <span className="inline-flex items-center gap-1 text-[11px] text-muted-foreground">
                <Lock size={11} aria-hidden="true" /> Stored hashed (SHA-256) · never displayed again
              </span>
            </div>

            {list.isPending ? (
              <div className="h-28 rounded-2xl border border-border bg-muted/30 animate-pulse" />
            ) : list.error ? (
              <p role="alert" className="text-xs text-destructive">
                {list.error.message}
              </p>
            ) : keys.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-border bg-muted/15 p-6 text-center space-y-1.5">
                <KeyRound size={20} className="mx-auto text-muted-foreground" aria-hidden="true" />
                <p className="text-sm font-medium text-foreground">No API keys created yet</p>
                <p className="text-xs text-muted-foreground">
                  Create a scoped key above to connect an MCP client or call the Intent Radar REST API.
                </p>
              </div>
            ) : (
              <>
                {/* Desktop Table */}
                <div className="hidden md:block overflow-x-auto rounded-2xl border border-border bg-card">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="border-b border-border bg-muted/35 text-[11px] font-semibold text-muted-foreground">
                        <th className="px-3 py-2.5">Key</th>
                        <th className="px-2.5 py-2.5">Status</th>
                        <th className="px-2.5 py-2.5">Scopes</th>
                        <th className="px-2.5 py-2.5">Last Used</th>
                        <th className="px-2.5 py-2.5">Created / Expires</th>
                        <th className="px-3 py-2.5 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {keys.map((key) => {
                        const st = computeKeyStatus(key);
                        const prefix = key.key_prefix || `pbk_${key.id.slice(0, 8)}…`;
                        return (
                          <tr key={key.id} className="hover:bg-muted/20 transition-colors">
                            <td className="px-3 py-2.5 whitespace-nowrap">
                              <p className="font-semibold text-foreground">{key.name}</p>
                              <p className="font-mono text-[11px] text-muted-foreground">{prefix}</p>
                            </td>
                            <td className="px-2.5 py-2.5 whitespace-nowrap">
                              <span
                                className={
                                  "inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold " +
                                  (st === "Active"
                                    ? "border-emerald-500/25 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
                                    : st === "Expired"
                                      ? "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300"
                                      : "border-border bg-muted text-muted-foreground")
                                }
                              >
                                {st}
                              </span>
                            </td>
                            <td className="px-2.5 py-2.5">
                              <div className="flex flex-wrap gap-1">
                                {key.scopes.map((sc) => (
                                  <code
                                    key={sc}
                                    className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground"
                                  >
                                    {sc}
                                  </code>
                                ))}
                              </div>
                            </td>
                            <td className="px-2.5 py-2.5 text-[11px] text-muted-foreground whitespace-nowrap">
                              {formatDateTime(key.last_used_at)}
                            </td>
                            <td className="px-2.5 py-2.5 text-[11px] text-muted-foreground whitespace-nowrap">
                              <p>{formatShortDate(key.created_at)}</p>
                              <p className="text-[10px]">Exp {formatShortDate(key.expires_at)}</p>
                            </td>
                            <td className="px-3 py-2.5 text-right whitespace-nowrap">
                              <div className="inline-flex items-center gap-1">
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => setSelectedKey(key)}
                                  className="h-7 px-2 text-[11px]"
                                >
                                  Details
                                </Button>
                                {!key.revoked_at && (
                                  <>
                                    <Button
                                      variant="outline"
                                      size="sm"
                                      disabled={busy || !!token}
                                      onClick={() =>
                                        setConfirm({ id: key.id, name: key.name, action: "rotate" })
                                      }
                                      className="h-7 px-2 text-[11px] gap-1"
                                    >
                                      <RefreshCw size={11} /> Rotate
                                    </Button>
                                    <Button
                                      variant="outline"
                                      size="sm"
                                      disabled={busy}
                                      onClick={() =>
                                        setConfirm({ id: key.id, name: key.name, action: "revoke" })
                                      }
                                      className="h-7 px-2 text-[11px] gap-1 text-destructive hover:text-destructive"
                                    >
                                      <Trash2 size={11} /> Revoke
                                    </Button>
                                  </>
                                )}
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                {/* Mobile Cards */}
                <ul className="md:hidden divide-y divide-border rounded-2xl border border-border bg-card overflow-hidden">
                  {keys.map((key) => {
                    const st = computeKeyStatus(key);
                    const prefix = key.key_prefix || `pbk_${key.id.slice(0, 8)}…`;
                    return (
                      <li className="p-4 space-y-2.5" key={key.id}>
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <h4 className="font-semibold text-sm text-foreground">{key.name}</h4>
                            <p className="font-mono text-[11px] text-muted-foreground">{prefix}</p>
                          </div>
                          <span
                            className={
                              "rounded-full border px-2 py-0.5 text-[10px] font-semibold " +
                              (st === "Active"
                                ? "border-emerald-500/25 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
                                : "border-border bg-muted text-muted-foreground")
                            }
                          >
                            {st}
                          </span>
                        </div>
                        <p className="text-[11px] text-muted-foreground">
                          Expires {formatShortDate(key.expires_at)} · Last used:{" "}
                          {formatDateTime(key.last_used_at)}
                        </p>
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
                        <div className="flex flex-wrap gap-2 pt-1">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setSelectedKey(key)}
                            className="h-7 text-xs"
                          >
                            Details
                          </Button>
                          {!key.revoked_at && (
                            <>
                              <Button
                                variant="outline"
                                size="sm"
                                disabled={busy || !!token}
                                onClick={() =>
                                  setConfirm({ id: key.id, name: key.name, action: "rotate" })
                                }
                                className="h-7 text-xs gap-1"
                              >
                                <RefreshCw size={11} /> Rotate
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                disabled={busy}
                                onClick={() =>
                                  setConfirm({ id: key.id, name: key.name, action: "revoke" })
                                }
                                className="h-7 text-xs gap-1 text-destructive"
                              >
                                <Trash2 size={11} /> Revoke
                              </Button>
                            </>
                          )}
                        </div>
                      </li>
                    );
                  })}
                </ul>
              </>
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
        </div>
      )}

      {/* =================================================================
          TAB 2: OVERVIEW & LIVE DIAGNOSTICS
      ================================================================== */}
      {activeTab === "overview" && (
        <div className="space-y-5">
          <div className="grid gap-4 lg:grid-cols-2">
            {/* MCP Server Status Card */}
            <section className="rounded-2xl border border-border bg-card p-5 space-y-3.5">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2.5">
                  <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 text-primary">
                    <Terminal size={17} aria-hidden="true" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-foreground">
                      MCP Server (Streamable HTTP)
                    </h3>
                    <p className="text-[11px] text-muted-foreground">
                      Authenticated read-only workspace intelligence for MCP clients
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
                Supports Claude Code, Cursor, Codex, and Streamable HTTP clients with{" "}
                <code>Authorization: Bearer YOUR_KEY</code> carrying <code>mcp:use</code> and{" "}
                <code>intent:read</code>.
              </p>

              <div className="flex flex-wrap gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setActiveTab("mcp")}
                  className="h-8 text-xs"
                >
                  Open MCP Setup Guide
                </Button>
                {status.data.mcp_available && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-8 text-xs gap-1.5"
                    onClick={() => void copyText(copilotConfiguration(mcpEndpoint), "mcp-config")}
                  >
                    {copiedLabel === "mcp-config" ? <Check size={12} /> : <Copy size={12} />}
                    {copiedLabel === "mcp-config" ? "Config copied" : "Copy MCP JSON config"}
                  </Button>
                )}
              </div>
            </section>

            {/* Developer REST API v1 Card */}
            <section className="rounded-2xl border border-border bg-card p-5 space-y-3.5">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2.5">
                  <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-500/10 text-blue-600 dark:text-blue-400">
                    <Code2 size={17} aria-hidden="true" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-foreground">Developer REST API v1</h3>
                    <p className="text-[11px] text-muted-foreground">
                      {leadAvailable
                        ? "Workspace-scoped programmatic access with idempotent writes"
                        : "Workspace-scoped read-only Intent Radar REST API"}
                    </p>
                  </div>
                </div>
                <span className="rounded-full border border-border bg-muted px-2.5 py-0.5 text-[11px] font-semibold text-foreground tabular-nums">
                  {rateLimit} req/min
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
                Never pass API keys in URLs. Keys inherit verified workspace membership and role permissions on every call.
                {leadAvailable && (
                  <>
                    {" "}
                    Write endpoints require a unique UUID in the <code>Idempotency-Key</code> header.
                  </>
                )}
              </p>

              <Button
                size="sm"
                variant="outline"
                onClick={() => setActiveTab("api")}
                className="h-8 text-xs"
              >
                Explore API Reference
              </Button>
            </section>
          </div>

          {/* Live Platform Diagnostics Panel */}
          <section className="rounded-2xl border border-border bg-card p-5 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-foreground">
                  Live Developer Platform Diagnostics
                </h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Run a real backend self-check verifying REST API v1 routes, OpenAPI schema, MCP tool &amp; resource registry, and workspace key posture.
                </p>
              </div>
              <Button
                size="sm"
                disabled={diagLoading}
                onClick={() => void runDiagnostics()}
                className="gap-1.5"
              >
                {diagLoading ? (
                  <Loader2 size={13} className="animate-spin" />
                ) : (
                  <Wifi size={13} />
                )}
                {diagLoading ? "Checking…" : "Test Connection"}
              </Button>
            </div>

            {diagResult && (
              <div
                role="status"
                className="rounded-xl border border-emerald-500/25 bg-emerald-500/5 p-4 space-y-3 text-xs"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="inline-flex items-center gap-1.5 font-semibold text-emerald-700 dark:text-emerald-300">
                    <CheckCircle2 size={15} /> Developer Platform Healthy
                  </span>
                  <span className="text-[11px] text-muted-foreground">
                    Verified {formatDateTime(diagResult.checked_at)}
                  </span>
                </div>

                <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  <div className="rounded-lg border border-border bg-card p-3">
                    <dt className="text-[11px] text-muted-foreground">REST v1 Endpoints</dt>
                    <dd className="text-base font-bold text-foreground mt-0.5 tabular-nums">
                      {diagResult.rest_api.endpoint_count}
                    </dd>
                    <dd className="text-[11px] text-muted-foreground font-mono">
                      {diagResult.rest_api.base_path}
                    </dd>
                  </div>
                  <div className="rounded-lg border border-border bg-card p-3">
                    <dt className="text-[11px] text-muted-foreground">MCP Tools</dt>
                    <dd className="text-base font-bold text-foreground mt-0.5 tabular-nums">
                      {diagResult.mcp.tools.length}
                    </dd>
                    <dd className="text-[11px] text-muted-foreground">Read-only scoped</dd>
                  </div>
                  <div className="rounded-lg border border-border bg-card p-3">
                    <dt className="text-[11px] text-muted-foreground">MCP Resources</dt>
                    <dd className="text-base font-bold text-foreground mt-0.5 tabular-nums">
                      {diagResult.mcp.resources.length}
                    </dd>
                    <dd className="text-[11px] text-muted-foreground">planebyte:// URIs</dd>
                  </div>
                  <div className="rounded-lg border border-border bg-card p-3">
                    <dt className="text-[11px] text-muted-foreground">Authentication</dt>
                    <dd className="text-sm font-semibold text-foreground mt-0.5">
                      Bearer API Key
                    </dd>
                    <dd className="text-[11px] text-muted-foreground">
                      OAuth 2.1 DCR: {diagResult.mcp.oauth_2_1_supported ? "Enabled" : "Not enabled"}
                    </dd>
                  </div>
                </dl>
              </div>
            )}
          </section>
        </div>
      )}

      {/* =================================================================
          TAB 3: MCP SETUP (Verified Streamable HTTP + Client Snippets)
      ================================================================== */}
      {activeTab === "mcp" && (
        <div className="space-y-5">
          {/* Endpoint + Auth Notice */}
          <section className="rounded-2xl border border-border bg-card p-5 space-y-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-foreground">
                  Remote MCP Server Configuration
                </h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Connect AI coding assistants and agents directly to your workspace Intent Radar intelligence via Streamable HTTP.
                </p>
              </div>
              <span className="rounded-full border border-emerald-500/25 bg-emerald-500/10 px-2.5 py-0.5 text-[11px] font-semibold text-emerald-700 dark:text-emerald-300">
                Streamable HTTP
              </span>
            </div>

            <div className="flex items-center justify-between gap-2 rounded-xl border border-border bg-muted/25 px-3.5 py-2.5">
              <div className="min-w-0">
                <span className="block text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">
                  MCP Endpoint URL
                </span>
                <code className="block truncate text-xs font-mono text-foreground mt-0.5">
                  {mcpEndpoint}
                </code>
              </div>
              <Button
                size="sm"
                variant="outline"
                onClick={() => void copyText(mcpEndpoint, "mcp-url")}
                className="h-8 text-xs gap-1.5 shrink-0"
              >
                {copiedLabel === "mcp-url" ? <Check size={12} /> : <Copy size={12} />}
                {copiedLabel === "mcp-url" ? "Copied" : "Copy URL"}
              </Button>
            </div>

            {/* Client Selector */}
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-1.5">
                {(
                  [
                    { id: "claude_code", label: "Claude Code" },
                    { id: "cursor", label: "Cursor" },
                    { id: "codex", label: "Codex CLI" },
                    { id: "streamable_http", label: "Streamable HTTP / cURL" },
                  ] as { id: McpClientId; label: string }[]
                ).map((c) => (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => setMcpClient(c.id)}
                    className={
                      "rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors cursor-pointer " +
                      (mcpClient === c.id
                        ? "border-primary/40 bg-primary/10 text-primary font-semibold"
                        : "border-border bg-card text-muted-foreground hover:text-foreground")
                    }
                  >
                    {c.label}
                  </button>
                ))}
              </div>

              <div className="rounded-xl border border-border bg-muted/30 overflow-hidden">
                <div className="flex items-center justify-between border-b border-border px-3.5 py-2 text-[11px]">
                  <span className="font-semibold text-foreground">{snippet.title}</span>
                  <button
                    type="button"
                    onClick={() => void copyText(snippet.code, `snippet-${mcpClient}`)}
                    className="inline-flex items-center gap-1 font-semibold text-primary hover:underline cursor-pointer"
                  >
                    {copiedLabel === `snippet-${mcpClient}` ? (
                      <Check size={12} />
                    ) : (
                      <Copy size={12} />
                    )}
                    {copiedLabel === `snippet-${mcpClient}` ? "Copied" : "Copy snippet"}
                  </button>
                </div>
                <pre className="overflow-x-auto p-3.5 text-[11px] font-mono text-foreground leading-relaxed">
                  <code>{snippet.code}</code>
                </pre>
              </div>

              <p className="text-[11px] text-muted-foreground leading-relaxed">{snippet.note}</p>
            </div>

            {/* Honest Auth Compatibility Note */}
            <div className="rounded-xl border border-border bg-muted/20 p-3.5 text-[11px] text-muted-foreground flex items-start gap-2.5">
              <Info size={14} className="text-primary shrink-0 mt-0.5" aria-hidden="true" />
              <div className="space-y-1">
                <p className="font-semibold text-foreground">
                  Authentication compatibility: Bearer API Keys (OAuth 2.1 DCR not enabled)
                </p>
                <p className="leading-relaxed">
                  PlaneByte MCP authenticates via workspace-scoped Bearer API keys (<code>mcp:use</code> + <code>intent:read</code>) over Streamable HTTP. Clients requiring OAuth 2.1 Dynamic Client Registration (such as browser-based ChatGPT / Claude Web connectors without custom header support) are not supported yet.
                </p>
              </div>
            </div>
          </section>

          {/* Exposed MCP Tools & Resources */}
          <div className="grid gap-4 lg:grid-cols-2">
            <section className="rounded-2xl border border-border bg-card p-5 space-y-3">
              <h4 className="text-sm font-semibold text-foreground">
                Available MCP Tools ({MCP_TOOLS_CATALOG.length})
              </h4>
              <div className="divide-y divide-border/70">
                {MCP_TOOLS_CATALOG.map((tool) => (
                  <div key={tool.name} className="py-2 first:pt-0 last:pb-0">
                    <code className="text-[11px] font-semibold text-primary">{tool.name}</code>
                    <p className="text-[11px] text-muted-foreground mt-0.5 leading-snug">
                      {tool.desc}
                    </p>
                  </div>
                ))}
              </div>
            </section>

            <section className="rounded-2xl border border-border bg-card p-5 space-y-3">
              <h4 className="text-sm font-semibold text-foreground">
                Authenticated MCP Resources ({MCP_RESOURCES.length})
              </h4>
              <div className="divide-y divide-border/70">
                {MCP_RESOURCES.map((res) => (
                  <div key={res.uri} className="py-2.5 first:pt-0 last:pb-0">
                    <code className="text-[11px] font-semibold text-foreground">{res.uri}</code>
                    <p className="text-[11px] text-muted-foreground mt-0.5 leading-snug">
                      {res.description}
                    </p>
                  </div>
                ))}
              </div>
            </section>
          </div>
        </div>
      )}

      {/* =================================================================
          TAB 4: API REFERENCE (Live OpenAPI Explorer + Multi-Lang Examples)
      ================================================================== */}
      {activeTab === "api" && (
        <div className="space-y-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="relative flex-1 min-w-[220px] max-w-md">
              <Search
                size={14}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none"
              />
              <input
                type="search"
                aria-label="Filter API endpoints"
                placeholder="Filter endpoints (e.g. signals, discoveries, sources)…"
                value={apiSearch}
                onChange={(e) => setApiSearch(e.target.value)}
                className="w-full rounded-xl border border-border bg-card pl-8 pr-3 py-2 text-xs text-foreground"
              />
            </div>

            <a
              href="/api/v1/openapi.json"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-medium text-foreground hover:border-primary/40"
            >
              <Code2 size={13} /> Download OpenAPI JSON
            </a>
          </div>

          {openApiQuery.isPending ? (
            <div className="h-48 rounded-2xl border border-border bg-muted/30 animate-pulse" />
          ) : openApiQuery.isError ? (
            <div
              role="alert"
              className="rounded-xl border border-destructive/25 bg-destructive/5 p-4 text-xs text-destructive"
            >
              Could not load live OpenAPI specification: {openApiQuery.error.message}
            </div>
          ) : (
            <div className="grid gap-4 lg:grid-cols-12">
              {/* Endpoint List */}
              <div className="lg:col-span-5 rounded-2xl border border-border bg-card overflow-hidden divide-y divide-border max-h-[520px] overflow-y-auto">
                {filteredEndpoints.map((ep) => {
                  const isActive = activeEndpoint?.key === ep.key;
                  return (
                    <button
                      key={ep.key}
                      type="button"
                      onClick={() => setSelectedEndpointKey(ep.key)}
                      className={
                        "w-full text-left px-3.5 py-3 transition-colors cursor-pointer " +
                        (isActive ? "bg-primary/10" : "hover:bg-muted/30")
                      }
                    >
                      <div className="flex items-center gap-2">
                        <span
                          className={
                            "rounded px-1.5 py-0.5 text-[10px] font-bold font-mono " +
                            (ep.method === "GET"
                              ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300"
                              : "bg-blue-500/15 text-blue-700 dark:text-blue-300")
                          }
                        >
                          {ep.method}
                        </span>
                        <code className="text-[11px] font-mono text-foreground truncate">
                          /api{ep.path}
                        </code>
                      </div>
                      <p className="text-[11px] text-muted-foreground mt-1 truncate">
                        {ep.summary}
                      </p>
                    </button>
                  );
                })}
                {filteredEndpoints.length === 0 && (
                  <p className="p-4 text-xs text-muted-foreground">No endpoints match your filter.</p>
                )}
              </div>

              {/* Selected Endpoint Details & Code Examples */}
              <div className="lg:col-span-7 rounded-2xl border border-border bg-card p-5 space-y-4">
                {activeEndpoint ? (
                  <>
                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="rounded bg-emerald-500/15 px-2 py-0.5 text-[11px] font-bold font-mono text-emerald-700 dark:text-emerald-300">
                          {activeEndpoint.method}
                        </span>
                        <code className="text-xs font-mono font-semibold text-foreground break-all">
                          /api{activeEndpoint.path}
                        </code>
                      </div>
                      <p className="text-xs text-muted-foreground leading-relaxed pt-1">
                        {activeEndpoint.description || activeEndpoint.summary}
                      </p>
                    </div>

                    <div className="flex flex-wrap gap-2 text-[11px]">
                      <span className="rounded-md border border-border bg-muted/40 px-2 py-0.5 text-foreground">
                        Auth: <code>Authorization: Bearer &lt;key&gt;</code>
                      </span>
                      <span className="rounded-md border border-border bg-muted/40 px-2 py-0.5 text-foreground">
                        Scope: <code>intent:read</code>
                      </span>
                    </div>

                    {activeEndpoint.parameters.length > 0 && (
                      <div className="space-y-2">
                        <h4 className="text-xs font-semibold text-foreground">Parameters</h4>
                        <div className="rounded-xl border border-border overflow-hidden">
                          <table className="w-full text-left text-[11px] border-collapse">
                            <thead>
                              <tr className="border-b border-border bg-muted/35 text-muted-foreground">
                                <th className="px-3 py-1.5">Name</th>
                                <th className="px-3 py-1.5">In</th>
                                <th className="px-3 py-1.5">Type</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-border">
                              {activeEndpoint.parameters.map((p) => (
                                <tr key={`${p.in}-${p.name}`}>
                                  <td className="px-3 py-1.5 font-mono text-foreground">
                                    {p.name}
                                    {p.required && <span className="text-destructive ml-0.5">*</span>}
                                  </td>
                                  <td className="px-3 py-1.5 text-muted-foreground">{p.in}</td>
                                  <td className="px-3 py-1.5 font-mono text-muted-foreground">
                                    {p.schema?.type || "string"}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}

                    {/* Copyable cURL / TypeScript / Python Examples */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-1">
                          {(
                            [
                              { id: "curl", label: "cURL" },
                              { id: "ts", label: "TypeScript" },
                              { id: "python", label: "Python" },
                            ] as { id: "curl" | "ts" | "python"; label: string }[]
                          ).map((l) => (
                            <button
                              key={l.id}
                              type="button"
                              onClick={() => setExampleLang(l.id)}
                              className={
                                "rounded-md px-2.5 py-1 text-[11px] font-medium cursor-pointer " +
                                (exampleLang === l.id
                                  ? "bg-primary/10 text-primary font-semibold"
                                  : "text-muted-foreground hover:text-foreground")
                              }
                            >
                              {l.label}
                            </button>
                          ))}
                        </div>
                        <button
                          type="button"
                          onClick={() =>
                            void copyText(
                              buildCodeExample(
                                exampleLang,
                                origin,
                                activeEndpoint.method,
                                activeEndpoint.path
                              ),
                              "api-example"
                            )
                          }
                          className="inline-flex items-center gap-1 text-[11px] font-semibold text-primary hover:underline cursor-pointer"
                        >
                          {copiedLabel === "api-example" ? <Check size={12} /> : <Copy size={12} />}
                          {copiedLabel === "api-example" ? "Copied" : "Copy"}
                        </button>
                      </div>
                      <pre className="overflow-x-auto rounded-xl border border-border bg-muted/30 p-3.5 text-[11px] font-mono text-foreground leading-relaxed">
                        <code>
                          {buildCodeExample(
                            exampleLang,
                            origin,
                            activeEndpoint.method,
                            activeEndpoint.path
                          )}
                        </code>
                      </pre>
                    </div>
                  </>
                ) : (
                  <p className="text-xs text-muted-foreground">Select an endpoint to inspect.</p>
                )}
              </div>
            </div>
          )}

          {/* Error & Rate Limit Codes Reference */}
          <section className="rounded-2xl border border-border bg-card p-5 space-y-3 text-xs">
            <h4 className="text-sm font-semibold text-foreground">
              HTTP Status Codes &amp; Rate Limit Headers
            </h4>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3 text-[11px] text-muted-foreground">
              <div>
                <code className="font-semibold text-foreground">401 Unauthorized</code> — Missing, invalid, expired, or revoked Bearer key.
              </div>
              <div>
                <code className="font-semibold text-foreground">403 Forbidden</code> — Valid key lacks required scope (e.g. <code>intent:read</code>) or workspace access.
              </div>
              <div>
                <code className="font-semibold text-foreground">404 Not Found</code> — Resource does not exist in the key&apos;s workspace.
              </div>
              <div>
                <code className="font-semibold text-foreground">409 Conflict</code> — Duplicate resource or stale optimistic revision.
              </div>
              <div>
                <code className="font-semibold text-foreground">422 Unprocessable</code> — Query parameter or payload validation failed.
              </div>
              <div>
                <code className="font-semibold text-foreground">429 Too Many Requests</code> — Exceeded <code>X-RateLimit-Limit</code> ({rateLimit}/min).
              </div>
            </div>
          </section>
        </div>
      )}

      {/* =================================================================
          TAB 5: USAGE & LOGS (Real Backend Telemetry)
      ================================================================== */}
      {activeTab === "usage" && (
        <div className="space-y-5">
          {usageQuery.isPending ? (
            <div className="h-40 rounded-2xl border border-border bg-muted/30 animate-pulse" />
          ) : usageQuery.isError ? (
            <div
              role="alert"
              className="rounded-xl border border-destructive/25 bg-destructive/5 p-4 text-xs text-destructive"
            >
              Could not load developer usage telemetry: {usageQuery.error.message}
            </div>
          ) : usageQuery.data ? (
            <>
              <div className="grid gap-3 grid-cols-2 lg:grid-cols-4">
                <div className="rounded-xl border border-border bg-card px-4 py-3">
                  <p className="text-[11px] text-muted-foreground">Requests (current min)</p>
                  <p className="text-lg font-bold text-foreground mt-0.5 tabular-nums">
                    {usageQuery.data.rate_limits.requests_current_minute}
                    <span className="text-xs font-normal text-muted-foreground">
                      {" "}
                      / {usageQuery.data.rate_limits.per_workspace_per_minute}
                    </span>
                  </p>
                </div>
                <div className="rounded-xl border border-border bg-card px-4 py-3">
                  <p className="text-[11px] text-muted-foreground">MCP calls (today / month)</p>
                  <p className="text-lg font-bold text-foreground mt-0.5 tabular-nums">
                    {usageQuery.data.usage.mcp_calls_today}
                    <span className="text-xs font-normal text-muted-foreground">
                      {" "}
                      / {usageQuery.data.usage.mcp_calls_month}
                    </span>
                  </p>
                </div>
                <div className="rounded-xl border border-border bg-card px-4 py-3">
                  <p className="text-[11px] text-muted-foreground">Monthly API requests</p>
                  <p className="text-lg font-bold text-foreground mt-0.5 tabular-nums">
                    {usageQuery.data.usage.monthly_api_requests_used}
                    {usageQuery.data.usage.monthly_api_requests_limit != null && (
                      <span className="text-xs font-normal text-muted-foreground">
                        {" "}
                        / {usageQuery.data.usage.monthly_api_requests_limit}
                      </span>
                    )}
                  </p>
                </div>
                <div className="rounded-xl border border-border bg-card px-4 py-3">
                  <p className="text-[11px] text-muted-foreground">Last API activity</p>
                  <p className="text-xs font-semibold text-foreground mt-1.5">
                    {formatDateTime(usageQuery.data.keys.last_used_at)}
                  </p>
                </div>
              </div>

              <section className="rounded-2xl border border-border bg-card overflow-hidden">
                <div className="flex items-center justify-between border-b border-border px-4 py-3">
                  <h4 className="text-sm font-semibold text-foreground">
                    Recent API Key &amp; MCP Audit Activity
                  </h4>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => void usageQuery.refetch()}
                    className="h-7 text-xs gap-1"
                  >
                    <RefreshCw size={12} /> Refresh
                  </Button>
                </div>

                {usageQuery.data.recent_events.length === 0 ? (
                  <p className="p-6 text-center text-xs text-muted-foreground">
                    No developer API or MCP audit events recorded yet.
                  </p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="border-b border-border bg-muted/35 text-[11px] text-muted-foreground">
                          <th className="px-4 py-2">Event</th>
                          <th className="px-4 py-2">Detail / Result</th>
                          <th className="px-4 py-2">Timestamp</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border">
                        {usageQuery.data.recent_events.map((ev) => (
                          <tr key={ev.id}>
                            <td className="px-4 py-2.5 font-mono text-[11px] text-foreground">
                              {ev.action}
                              {ev.tool ? ` · ${ev.tool}` : ""}
                            </td>
                            <td className="px-4 py-2.5 text-muted-foreground">
                              {ev.entity} · {ev.result}
                            </td>
                            <td className="px-4 py-2.5 text-muted-foreground whitespace-nowrap">
                              {formatDateTime(ev.created_at)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </section>
            </>
          ) : null}
        </div>
      )}

      {/* Key Details Slide-Over Drawer */}
      <SlideOverDrawer
        open={!!selectedKey}
        onClose={() => setSelectedKey(null)}
        title={selectedKey?.name || "API Key Details"}
        subtitle="Workspace credential metadata, active scopes, and lifecycle controls."
        icon={
          <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-border bg-muted/30 text-primary">
            <KeyRound size={17} />
          </div>
        }
      >
        {selectedKey && (() => {
          const st = computeKeyStatus(selectedKey);
          const prefix = selectedKey.key_prefix || `pbk_${selectedKey.id.slice(0, 8)}…`;
          return (
            <div className="space-y-5 text-xs">
              <div className="rounded-xl border border-border bg-muted/20 p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Status</span>
                  <span
                    className={
                      "rounded-full border px-2.5 py-0.5 text-[11px] font-semibold " +
                      (st === "Active"
                        ? "border-emerald-500/25 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
                        : "border-border bg-muted text-muted-foreground")
                    }
                  >
                    {st}
                  </span>
                </div>
                <dl className="grid grid-cols-2 gap-3">
                  <div>
                    <dt className="text-muted-foreground">Masked prefix</dt>
                    <dd className="font-mono font-medium text-foreground mt-0.5">{prefix}</dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Key ID</dt>
                    <dd className="font-mono text-[11px] text-foreground mt-0.5 truncate">
                      {selectedKey.id}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Created</dt>
                    <dd className="text-foreground mt-0.5">
                      {formatDateTime(selectedKey.created_at)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Last used</dt>
                    <dd className="text-foreground mt-0.5">
                      {formatDateTime(selectedKey.last_used_at)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Expires</dt>
                    <dd className="text-foreground mt-0.5">
                      {formatDateTime(selectedKey.expires_at)}
                    </dd>
                  </div>
                  {selectedKey.revoked_at && (
                    <div>
                      <dt className="text-muted-foreground">Revoked</dt>
                      <dd className="text-destructive mt-0.5">
                        {formatDateTime(selectedKey.revoked_at)}
                      </dd>
                    </div>
                  )}
                </dl>
              </div>

              <div className="space-y-2">
                <h4 className="font-semibold text-sm text-foreground">Assigned Scopes</h4>
                <div className="space-y-1.5">
                  {selectedKey.scopes.map((sc) => (
                    <div
                      key={sc}
                      className="rounded-lg border border-border bg-card px-3 py-2 space-y-0.5"
                    >
                      <code className="text-[11px] font-semibold text-foreground">{sc}</code>
                      {SCOPE_DESCRIPTIONS[sc] && (
                        <p className="text-[11px] text-muted-foreground">
                          {SCOPE_DESCRIPTIONS[sc]}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {!selectedKey.revoked_at && (
                <div className="flex flex-wrap gap-2 border-t border-border pt-4">
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={busy || !!token}
                    onClick={() => {
                      setConfirm({ id: selectedKey.id, name: selectedKey.name, action: "rotate" });
                      setSelectedKey(null);
                    }}
                    className="gap-1.5"
                  >
                    <RefreshCw size={13} /> Rotate key
                  </Button>
                  <Button
                    size="sm"
                    variant="destructive"
                    disabled={busy}
                    onClick={() => {
                      setConfirm({ id: selectedKey.id, name: selectedKey.name, action: "revoke" });
                      setSelectedKey(null);
                    }}
                    className="gap-1.5"
                  >
                    <Trash2 size={13} /> Revoke key
                  </Button>
                </div>
              )}
            </div>
          );
        })()}
      </SlideOverDrawer>

      {status.data.mcp_available && leadAvailable && <DeveloperApprovals />}
      {leadAvailable && status.data.webhooks_available && <WebhookSettings />}
    </div>
  );
}
