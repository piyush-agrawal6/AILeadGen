import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ResearchSourcesPanel } from "@/components/intent-radar/integrations/ResearchSourcesPanel";
import { CustomFeedsPanel } from "@/components/intent-radar/integrations/CustomFeedsPanel";
import { DeveloperSettings } from "@/components/workspaces/developer-settings";
import { ProviderLogo } from "@/components/intent-radar/provider-logo";
import { request } from "@/lib/intelligence";

const mutateAsyncMock = vi.fn();

vi.mock("@/lib/intelligence", () => ({
  request: vi.fn(),
}));

vi.mock("@/components/workspaces/features", () => ({
  useWorkspaceCapabilities: () => ({ leadEngineAvailable: false }),
}));

vi.mock("@/components/intent-radar/provider", () => ({
  useRadarCapabilities: () => ({
    data: {
      stage: "Beta",
      growth_enabled: true,
      can_write: true,
      can_manage: true,
      sources: [
        {
          id: "github",
          name: "GitHub",
          state: "Connected",
          coverage: "GitHub App & Public Search",
          documentation: "https://docs.github.com/en/rest",
          oauth_configured: true,
          webhooks_configured: true,
          policy: {
            provider_id: "github",
            publisher: "GitHub, Inc.",
            authorized_app: "PlaneByte Intent Radar",
            authorization_reference: "GitHub App OAuth",
            commercial_use_authorized: true,
            ai_processing_authorized: true,
            ai_status: "Authorized",
            capabilities: { fetch: true, search: true, summarize: true, analyze_intent: true },
            retention_days: 30,
            attribution_required: "GitHub author & permalink",
            restrictions: ["Rate limits respected."],
            missing_approval_note: null,
          },
        },
        {
          id: "youtube",
          name: "YouTube",
          state: "Available",
          coverage: "YouTube Data API v3",
          documentation: "https://developers.google.com/youtube/v3",
          ai_analytics_authorized: false,
          policy: {
            provider_id: "youtube",
            publisher: "Google LLC",
            authorized_app: "PlaneByte Intent Radar",
            authorization_reference: "YouTube Data API v3",
            commercial_use_authorized: true,
            ai_processing_authorized: false,
            ai_status: "Restricted (YouTube API policy)",
            capabilities: { fetch: true, search: true, analyze_intent: false },
            retention_days: 30,
            attribution_required: "YouTube channel & link",
            restrictions: ["Derived AI analytics gated OFF."],
            missing_approval_note: "Google YouTube API compliance review in progress.",
          },
        },
        {
          id: "rss",
          name: "RSS & Atom Feeds",
          state: "Not configured",
          availability_label: "No custom feeds",
          coverage: "Optional custom RSS feeds; Atom & Discourse presets are active.",
          documentation: "https://www.rssboard.org/rss-specification",
          configured_feeds_count: 0,
          enabled_feeds_count: 0,
        },
      ],
      usage: { searches_today: 1, daily_search_limit: 50, monitor_limit: 20 },
    },
    isPending: false,
    isError: false,
    refetch: vi.fn(),
  }),
  useRadarRead: (path: string) => {
    if (path === "/sources/configurations") {
      return {
        data: {
          items: [
            {
              id: "feed-1",
              name: "Next.js Releases",
              family: "atom",
              endpoint: "https://github.com/vercel/next.js/releases.atom",
              policy_reference: "GitHub Releases Atom",
              attribution: "Vercel",
              retention_days: 14,
              polling_minutes: 60,
              enabled: true,
              ai_processing_authorized: true,
            },
            {
              id: "feed-2",
              name: "n8n Community",
              family: "discourse",
              endpoint: "https://community.n8n.io/latest.rss",
              policy_reference: "Public RSS",
              attribution: "n8n",
              retention_days: 7,
              polling_minutes: 60,
              enabled: true,
              ai_processing_authorized: false,
            },
          ],
        },
        isPending: false,
        isError: false,
        refetch: vi.fn(),
      };
    }
    if (path === "/sources/presets") {
      return {
        data: {
          items: [
            {
              preset_id: "atom-nextjs",
              name: "Next.js Releases",
              family: "atom",
              endpoint: "https://github.com/vercel/next.js/releases.atom",
              policy_reference: "GitHub Releases Atom",
              attribution: "Vercel",
              ai_processing_authorized: true,
              host_approved: true,
              configured: true,
              enabled: true,
            },
          ],
        },
        isPending: false,
        isError: false,
        refetch: vi.fn(),
      };
    }
    if (path === "/sources/github/status") {
      return {
        data: {
          app_configured: true,
          oauth_configured: true,
          webhooks_configured: true,
          public_search_available: true,
          app_slug: "planebyte-intent-radar",
          status: "CONNECTED",
          installation_id: "123456",
          account_login: "planebytelabs",
          account_type: "Organization",
          repositories: [],
          last_verified_at: "2026-11-18T10:00:00Z",
          last_error_code: null,
        },
        isPending: false,
        isError: false,
        refetch: vi.fn(),
      };
    }
    if (path === "/sources/health") {
      return { data: { items: [] }, isPending: false, isError: false, refetch: vi.fn() };
    }
    return { data: null, isPending: false, isError: false, refetch: vi.fn() };
  },
  useRadarMutation: () => ({ mutateAsync: mutateAsyncMock, isPending: false }),
}));

describe("Integrations 3.0, Developer Platform 3.0 & Official Source Branding", () => {
  beforeEach(() => {
    mutateAsyncMock.mockReset();
    vi.mocked(request).mockReset();
  });

  it("renders official brand artwork for supplied source providers", () => {
    const { container } = render(
      <div>
        <ProviderLogo provider="github" size={24} />
        <ProviderLogo provider="youtube" size={24} />
        <ProviderLogo provider="bluesky" size={24} />
        <ProviderLogo provider="stack_exchange" size={24} />
        <ProviderLogo provider="rss" size={24} />
      </div>
    );
    const imgs = Array.from(container.querySelectorAll("img"));
    const srcs = imgs.map((i) => i.getAttribute("src"));
    expect(srcs).toContain("/brands/sources/github.png");
    expect(srcs).toContain("/brands/sources/youtube.png");
    expect(srcs).toContain("/brands/sources/bluesky.png");
    expect(srcs).toContain("/brands/sources/stack-exchange.png");
    expect(srcs).toContain("/brands/sources/rss.png");
  });

  it("shows truthful RSS 'No custom feeds' status, opens Details drawer, and runs live Test Connection", async () => {
    mutateAsyncMock.mockResolvedValueOnce({
      ok: true,
      provider: "youtube",
      http_status: 200,
      latency_ms: 82,
      checked_at: "2026-11-18T11:00:00Z",
      summary: "YouTube Data API v3 key verified.",
      error: null,
    });

    render(<ResearchSourcesPanel />);
    expect(screen.getByText("No custom feeds")).toBeTruthy();

    // Click Details on YouTube card
    const detailsButtons = screen.getAllByRole("button", { name: /^Details$/i });
    fireEvent.click(detailsButtons[0]);

    // Slide-over drawer opens with centralized policy notice
    const dialog = screen.getByRole("dialog", { name: "YouTube" });
    expect(dialog).toBeTruthy();
    expect(screen.getByText(/Google YouTube API compliance review in progress/i)).toBeTruthy();

    // Run live Test Connection inside drawer
    fireEvent.click(screen.getByRole("button", { name: /Test Connection/i }));
    await waitFor(() =>
      expect(mutateAsyncMock).toHaveBeenCalledWith({
        path: "/sources/youtube/test",
        method: "POST",
        body: {},
      })
    );
    expect((await screen.findAllByText(/YouTube Data API v3 key verified/i)).length).toBeGreaterThan(0);
  });

  it("renders Custom Feeds 3-tab layout, opens Manage drawer, and runs live Endpoint Test", async () => {
    mutateAsyncMock.mockResolvedValueOnce({
      ok: true,
      endpoint: "https://github.com/vercel/next.js/releases.atom",
      http_status: 200,
      latency_ms: 95,
      checked_at: "2026-11-18T11:00:00Z",
      feed_format: "atom",
      entry_count: 10,
      latest_entry_at: "2026-11-17T10:00:00Z",
      sample_titles: ["v16.1.0"],
      etag: '"abc"',
      last_modified: null,
      error: null,
    });

    render(<CustomFeedsPanel />);
    expect(screen.getByRole("tab", { name: /My Feeds \(2\)/i })).toHaveAttribute(
      "aria-selected",
      "true"
    );
    expect(screen.getByRole("tab", { name: /Browse Feed Catalog/i })).toBeTruthy();
    expect(screen.getByRole("tab", { name: /Add Custom Feed/i })).toBeTruthy();

    // Open Manage drawer on first row
    fireEvent.click(screen.getAllByRole("button", { name: /Manage/i })[0]);
    expect(screen.getByRole("dialog", { name: /Manage Next\.js Releases/i })).toBeTruthy();

    // Trigger live Test Endpoint
    fireEvent.click(screen.getByRole("button", { name: /Test Endpoint/i }));
    await waitFor(() =>
      expect(mutateAsyncMock).toHaveBeenCalledWith({
        path: "/sources/configurations/feed-1/test",
        method: "POST",
        body: {},
      })
    );
    expect(await screen.findByText(/Endpoint healthy \(HTTP 200\)/i)).toBeTruthy();
  });

  it("renders Developer Console 3.0 5 tabs, masked API key table, MCP Setup, and Diagnostics", async () => {
    vi.mocked(request).mockImplementation(async (path: string) => {
      if (path.endsWith("/status")) {
        return { enabled: true, can_manage: true, mcp_available: true, webhooks_available: false };
      }
      if (path.endsWith("/keys")) {
        return {
          items: [
            {
              id: "31f3721b-d880-448a-b399-c1255ffcba91",
              name: "planebyte",
              key_prefix: "pbk_31f3721b…",
              status: "Active",
              scopes: ["intent:read", "mcp:use"],
              created_at: "2026-11-15T10:00:00Z",
              expires_at: "2027-02-15T10:00:00Z",
              revoked_at: null,
              last_used_at: null,
            },
          ],
          available_scopes: ["intent:read", "mcp:use"],
          rate_limit_per_minute: 60,
        };
      }
      if (path.endsWith("/diagnostics")) {
        return {
          ok: true,
          checked_at: "2026-11-18T11:00:00Z",
          rest_api: { enabled: true, base_path: "/api/v1", openapi_path: "/api/v1/openapi.json", endpoint_count: 12, rate_limit_per_minute: 60 },
          mcp: { enabled: true, endpoint_path: "/api/v1/mcp", transport: "Streamable HTTP", authentication: "Bearer", oauth_2_1_supported: false, tools: ["search_intent_signals"], resources: ["planebyte://sources/policies"] },
          available_scopes: ["intent:read", "mcp:use"],
          active_keys: 1,
          last_used_at: null,
        };
      }
      if (path.endsWith("/usage")) {
        return {
          keys: { total: 1, active: 1, revoked: 0, expired: 0, last_used_at: null },
          rate_limits: { per_key_per_minute: 60, per_workspace_per_minute: 180, requests_current_minute: 2 },
          usage: { mcp_calls_today: 4, mcp_calls_month: 12, mcp_errors_month: 0, monthly_api_requests_used: 9, monthly_api_requests_limit: 1000 },
          recent_events: [],
        };
      }
      return {};
    });

    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <DeveloperSettings />
      </QueryClientProvider>
    );

    expect((await screen.findAllByText("pbk_31f3721b…")).length).toBeGreaterThan(0);

    // Switch to Overview & Diagnostics and run Test Connection
    fireEvent.click(screen.getByRole("tab", { name: /Overview & Diagnostics/i }));
    fireEvent.click(screen.getByRole("button", { name: /Test Connection/i }));
    expect(await screen.findByText(/Developer Platform Healthy/i)).toBeTruthy();

    // Switch to MCP Setup and verify client selector & honest OAuth 2.1 note
    fireEvent.click(screen.getByRole("tab", { name: /MCP Setup/i }));
    expect(screen.getByText(/OAuth 2\.1 DCR not enabled/i)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /Codex CLI/i }));
    expect(screen.getByText(/bearer_token_env_var/i)).toBeTruthy();
  });
});
