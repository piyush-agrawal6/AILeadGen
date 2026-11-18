import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { DiscoverExperience } from "@/components/intent-radar/discovery";
import { applyProposalsToDraft } from "@/components/intent-radar/discover/DiscoveryCopilotPanel";
import { emptyIntentSearch, type DiscoveryRun, type SavedSearch } from "@/lib/intent-radar";

const mocks = vi.hoisted(() => ({
  push: vi.fn(),
  mutateAsync: vi.fn(),
  mutate: vi.fn(),
  radarRead: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mocks.push, replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/intent-radar/discover",
  useSearchParams: () => new URLSearchParams(),
}));

const MOCK_USAGE = {
  usage: [
    { dimension: "plan_searches", label: "Monthly searches", used: 1, limit: 50, remaining: 49, basis: "monthly", resets_at: null, near_limit: false },
    { dimension: "plan_ai_calls", label: "Shared AI operations", used: 1, limit: 50, remaining: 49, basis: "monthly", resets_at: null, near_limit: false },
  ],
};

vi.mock("@/components/workspaces/usage", () => ({
  useUsage: () => ({
    data: MOCK_USAGE,
    isPending: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  }),
}));

vi.mock("@/components/intent-radar/provider", () => ({
  useRadarCapabilities: () => ({
    data: {
      stage: "Beta",
      growth_enabled: true,
      can_write: true,
      can_manage: true,
      sources: [
        { id: "hacker_news", name: "Hacker News", state: "Available", coverage: "Official HN Firebase v0", documentation: "https://github.com/HackerNews/API", request_limit_per_check: 30 },
        { id: "github", name: "GitHub", state: "Connected", coverage: "GitHub REST & GraphQL", documentation: "https://docs.github.com", request_limit_per_check: 24 },
        { id: "stack_exchange", name: "Stack Exchange", state: "Available", coverage: "SE API 2.3", documentation: "https://api.stackexchange.com", configured_sites: ["stackoverflow", "devops"], request_limit_per_check: 8 },
      ],
      usage: { searches_today: 1, daily_search_limit: 20, monitor_limit: 50, automatic_schedules_enabled: true, minimum_schedule_hours: 6 },
    },
    isPending: false,
    isError: false,
    refetch: vi.fn(),
  }),
  useRadarRead: (path: string) => mocks.radarRead(path),
  useRadarMutation: () => ({ mutateAsync: mocks.mutateAsync, mutate: mocks.mutate, isPending: false }),
  useRadarRefresh: () => vi.fn(),
}));

function wrap(node: React.ReactNode) {
  return (
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })}>
      {node}
    </QueryClientProvider>
  );
}

const SAMPLE_RUN: DiscoveryRun = {
  id: "11111111-1111-1111-1111-111111111111",
  job_id: "22222222-2222-2222-2222-222222222222",
  title: "CRM Alternative Evaluations",
  original_prompt: "Find teams comparing Salesforce vs HubSpot",
  search_mode: "ai",
  parent_discovery_id: null,
  monitor_id: null,
  created_by: "contact@planebyte.com",
  created_at: "2026-11-18T08:00:00Z",
  completed_at: "2026-11-18T08:00:12Z",
  status: "COMPLETED",
  error_code: null,
  attempts: 1,
  sources: ["hacker_news", "github"],
  keywords: ["CRM alternative", "Salesforce vs HubSpot"],
  matched_count: 2,
  scanned_count: 40,
  requests_count: 6,
  coverage: "HN Ask & GitHub issues scanned.",
  configuration: {
    ...emptyIntentSearch(),
    keywords: ["CRM alternative", "Salesforce vs HubSpot"],
    sources: ["hacker_news", "github"],
  },
  strategy: {
    objective: "Find B2B teams evaluating CRM replacements",
    target_customer_context: "PlaneByte · ICP: Seed SaaS Founders",
    keyword_rationale: "Comparison phrases isolate active evaluation threads.",
    source_rationale: "HN and GitHub host founder and engineering tool evaluations.",
    exclusions_rationale: "No exclusions applied.",
    limitations: ["Recent indexed discussions only."],
  },
  source_runs: [
    { provider: "hacker_news", status: "COMPLETE", scanned: 25, requests: 3, coverage: "Ask HN", signals_count: 1 },
    { provider: "github", status: "COMPLETE", scanned: 15, requests: 3, coverage: "Public issues", signals_count: 1 },
  ],
  signal_ids: ["sig-1", "sig-2"],
  signals: [
    {
      id: "sig-1",
      title: "Ask HN: Lightweight CRM alternative to Salesforce?",
      source: "Hacker News",
      source_url: "https://news.ycombinator.com/item?id=1",
      excerpt: "We want to replace Salesforce with something simpler.",
      observed_at: "2026-11-18T07:00:00Z",
      retrieved_at: "2026-11-18T08:00:00Z",
      category: "Alternative search",
      score: 88,
      status: "New",
      notes: "",
      revision: 1,
      available: 1,
      saved: false,
      evidence: { matched_keywords: ["CRM alternative"], matched_topics: [], intent_phrase: "alternative to", confidence: "high", explanation: "Direct alternative search", observed_text: "replace Salesforce", unknown: [], purchasing_event_verified: false },
      monitors: [],
    },
    {
      id: "sig-2",
      title: "CRM benchmark release notes",
      source: "GitHub",
      source_url: "https://github.com/org/repo/releases/tag/v1",
      excerpt: "New release benchmark.",
      observed_at: "2026-11-18T06:00:00Z",
      retrieved_at: "2026-11-18T08:00:00Z",
      category: "Market / technology intelligence",
      score: 45,
      status: "New",
      notes: "",
      revision: 1,
      available: 1,
      saved: false,
      evidence: { matched_keywords: ["CRM alternative"], matched_topics: [], intent_phrase: null, confidence: "medium", explanation: "Release", observed_text: "benchmark", unknown: [], purchasing_event_verified: false },
      monitors: [],
    },
  ],
};

const SAMPLE_SAVED: SavedSearch = {
  id: "33333333-3333-3333-3333-333333333333",
  name: "Weekly CRM Replacement Watch",
  description: "Reusable template for CRM alternative discussions",
  original_prompt: "Find teams looking for a CRM alternative",
  configuration: { ...emptyIntentSearch(), keywords: ["CRM alternative"], sources: ["hacker_news"] },
  revision: 1,
  last_run_discovery_id: null,
  created_by: "contact@planebyte.com",
  created_at: "2026-11-18T07:00:00Z",
  updated_at: "2026-11-18T07:30:00Z",
};

beforeEach(() => {
  vi.clearAllMocks();
  Element.prototype.scrollIntoView = vi.fn();
  mocks.radarRead.mockImplementation((path: string) => {
    if (path === "/settings") {
      return { data: { discovery_keywords: [], discovery_excluded: [], topics: [], min_relevance: 0, default_view: "cards", alerts_enabled: false, alert_threshold: 70, revision: 1, default_icp_id: null }, error: null, isPending: false, refetch: vi.fn() };
    }
    if (path === "/icps") {
      return { data: { items: [{ id: "icp-1", name: "Seed SaaS Founders" }] }, error: null, isPending: false, refetch: vi.fn() };
    }
    if (path.startsWith("/discover/context")) {
      return {
        data: {
          context_version: "discovery_context_v2",
          company_name: "PlaneByte",
          has_company_profile: true,
          selected_icp_id: "icp-1",
          selected_icp_name: "Seed SaaS Founders",
          icp_count: 1,
          available_source_ids: ["hacker_news", "github", "stack_exchange"],
          available_source_count: 3,
          recent_run_count: 1,
          draft_fingerprint: "abc123",
        },
        error: null,
        isPending: false,
        refetch: vi.fn(),
      };
    }
    if (path.startsWith("/discoveries?")) {
      return { data: { items: [SAMPLE_RUN], total: 1, page: 1, page_size: 15 }, error: null, isPending: false, refetch: vi.fn() };
    }
    if (path === `/discoveries/${SAMPLE_RUN.id}`) {
      return { data: SAMPLE_RUN, error: null, isPending: false, refetch: vi.fn() };
    }
    if (path.startsWith("/saved-searches")) {
      return { data: { items: [SAMPLE_SAVED], total: 1, page: 1, page_size: 50 }, error: null, isPending: false, refetch: vi.fn() };
    }
    if (path === "/sources/configurations") {
      return { data: { items: [] }, error: null, isPending: false, refetch: vi.fn() };
    }
    return { data: null, error: null, isPending: false, refetch: vi.fn() };
  });
});

afterEach(cleanup);

describe("Discovery 2.0 Workspace", () => {
  it("renders 3-tab navigation, compact source cards with Configure drawer, and inline review on the same page", async () => {
    render(wrap(<DiscoverExperience route="discover" />));

    // 3-tab nav links
    expect(screen.getByRole("link", { name: /New Discovery/i })).toHaveAttribute("href", "/intent-radar/discover");
    expect(screen.getByRole("link", { name: /Discovery History/i })).toHaveAttribute("href", "/intent-radar/discover/history");
    expect(screen.getByRole("link", { name: /Saved Searches/i })).toHaveAttribute("href", "/intent-radar/discover/saved");

    // Compact source options: no stacked inline provider wall by default
    expect(screen.queryByText("Selected source options")).not.toBeInTheDocument();
    expect(screen.queryByText("Hacker News feeds")).not.toBeInTheDocument();

    // Clicking Configure on Hacker News opens the per-source drawer
    fireEvent.click(screen.getByRole("button", { name: /Configure/i }));
    expect(await screen.findByRole("dialog", { name: /Configure Hacker News/i })).toBeVisible();
    expect(screen.getByText("Hacker News feeds")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Done" }));
    expect(screen.queryByRole("dialog", { name: /Configure Hacker News/i })).not.toBeInTheDocument();

    // Add keyword and click Review Search -> expands inline below builder
    fireEvent.change(screen.getByLabelText("Add Keywords"), { target: { value: "CRM alternative" } });
    fireEvent.keyDown(screen.getByLabelText("Add Keywords"), { key: "Enter" });
    fireEvent.click(screen.getByRole("button", { name: /Review Search/i }));

    expect(await screen.findByRole("heading", { name: "Review Search Criteria" })).toBeVisible();
    // Builder remains on the same page (inline review, never navigated away!)
    expect(screen.getByText("1 · Search Terms")).toBeVisible();
  });

  it("Discovery Copilot shows workspace context, proposes selectable changes, applies selected, and supports Undo", async () => {
    mocks.mutateAsync.mockResolvedValue({
      reply: "I suggested sharper CRM comparison terms and B2B exclusions.",
      strategy: null,
      proposals: [
        { id: "p1", action: "add_keywords", label: "Add CRM comparison phrases", rationale: "High intent", keywords: ["CRM alternative", "Salesforce vs HubSpot"] },
        { id: "p2", action: "add_exclusions", label: "Exclude hiring noise", rationale: "Cut job posts", excluded: ["hiring", "intern"] },
      ],
      warnings: [],
      mode: "AI Copilot",
      cached: false,
      quota_exhausted: false,
      fallback_reason: null,
      draft_fingerprint: "abc123",
    });

    render(wrap(<DiscoverExperience route="discover" />));

    // Workspace context badges visible in sticky Copilot panel
    expect(screen.getByText("PlaneByte")).toBeVisible();
    expect(screen.getByText("ICP: Seed SaaS Founders")).toBeVisible();
    expect(screen.getByText("3 sources ready")).toBeVisible();

    // Click quick action Improve keywords
    fireEvent.click(screen.getByRole("button", { name: "Improve keywords" }));

    expect(await screen.findByText("I suggested sharper CRM comparison terms and B2B exclusions.")).toBeVisible();
    expect(screen.getByText("Add CRM comparison phrases")).toBeVisible();
    expect(screen.getByText("Exclude hiring noise")).toBeVisible();

    // Uncheck second proposal, apply only selected
    const checkboxes = screen.getAllByRole("checkbox");
    const exclCheckbox = checkboxes.find((cb) => cb.closest("label")?.textContent?.includes("Exclude hiring noise"));
    expect(exclCheckbox).toBeTruthy();
    fireEvent.click(exclCheckbox!);

    fireEvent.click(screen.getByRole("button", { name: "Apply Selected" }));

    // Keyword applied to shared draft
    await waitFor(() => {
      expect(screen.getByText("CRM alternative")).toBeVisible();
      expect(screen.getByText("Salesforce vs HubSpot")).toBeVisible();
    });

    // Undo button restores previous empty keywords
    fireEvent.click(screen.getByRole("button", { name: /Undo/i }));
    await waitFor(() => {
      expect(screen.getByText("0 / 12 keywords")).toBeVisible();
    });
  });

  it("renders Discovery History, Run Detail with Buyer-Intent vs Market/Tech filter, and Saved Searches", async () => {
    const { rerender } = render(wrap(<DiscoverExperience route="discover/history" />));
    expect(screen.getByRole("heading", { name: "Discovery History" })).toBeVisible();
    expect(screen.getByText("CRM Alternative Evaluations")).toBeVisible();
    expect(screen.getByRole("link", { name: /Open Results/i })).toHaveAttribute(
      "href",
      `/intent-radar/discover/runs/${SAMPLE_RUN.id}`
    );

    // Run Detail route
    rerender(wrap(<DiscoverExperience route={`discover/runs/${SAMPLE_RUN.id}`} />));
    expect(screen.getByRole("heading", { name: "CRM Alternative Evaluations" })).toBeVisible();
    expect(screen.getByText("Buyer-Intent Signal")).toBeVisible();
    expect(screen.getAllByText("Market / Tech Intelligence").length).toBeGreaterThanOrEqual(1);

    // Filter inline results to Buyer Intent only
    fireEvent.click(screen.getByRole("button", { name: "Buyer Intent" }));
    expect(screen.getByText("Ask HN: Lightweight CRM alternative to Salesforce?")).toBeVisible();
    expect(screen.queryByText("CRM benchmark release notes")).not.toBeInTheDocument();

    // Saved Searches route
    rerender(wrap(<DiscoverExperience route="discover/saved" />));
    expect(screen.getByRole("heading", { name: "Saved Searches" })).toBeVisible();
    expect(screen.getByText("Weekly CRM Replacement Watch")).toBeVisible();
    expect(screen.getByRole("button", { name: /Open in Builder/i })).toBeVisible();
    expect(screen.getByRole("button", { name: /Convert to Monitor/i })).toBeVisible();
  });

  it("applyProposalsToDraft merges cleanly without enabling semantic silently", () => {
    const base = { ...emptyIntentSearch(), keywords: ["crm"], sources: ["hacker_news" as const] };
    const next = applyProposalsToDraft(base, [
      { id: "1", action: "add_keywords", label: "Add", rationale: "", keywords: ["CRM alternative", "crm"] },
      { id: "2", action: "add_exclusions", label: "Excl", rationale: "", excluded: ["hiring"] },
      { id: "3", action: "select_sources", label: "Src", rationale: "", sources: ["github", "hacker_news"] },
    ]);
    expect(next.keywords).toEqual(["crm", "CRM alternative"]);
    expect(next.excluded).toEqual(["hiring"]);
    expect(next.sources).toEqual(["github", "hacker_news"]);
    expect(next.semantic).toBeFalsy();
  });
});
