import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { DiscoverExperience } from "@/components/intent-radar/discovery";
import { emptyIntentSearch, type DiscoveryRun, type SavedSearch, type IntentSignal } from "@/lib/intent-radar";

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
    { dimension: "plan_searches", label: "Monthly searches", used: 2, limit: 50, remaining: 48, basis: "monthly", resets_at: null, near_limit: false },
    { dimension: "plan_ai_calls", label: "Shared AI operations", used: 3, limit: 50, remaining: 47, basis: "monthly", resets_at: null, near_limit: false },
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
        { id: "hacker_news", name: "Hacker News", configured: true, state: "Available" },
        { id: "github", name: "GitHub", configured: true, state: "Connected" },
        { id: "stack_exchange", name: "Stack Exchange", configured: true, state: "Available" },
        { id: "bluesky", name: "Bluesky", configured: true, state: "Available" },
        { id: "rss", name: "RSS Feeds", configured: true, state: "Available" },
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

const SAMPLE_SIGNAL_1: IntentSignal = {
  id: "sig-ai-1",
  title: "Teams evaluating AI code review tools in production",
  source: "Hacker News",
  source_url: "https://news.ycombinator.com/item?id=42",
  excerpt: "We are currently testing Cursor vs Copilot vs CodeRabbit for our team of 25 engineers.",
  observed_at: "2026-11-18T10:00:00Z",
  retrieved_at: "2026-11-18T10:05:00Z",
  category: "Tool / service evaluation",
  score: 92,
  status: "New",
  notes: "",
  revision: 1,
  available: 1,
  saved: false,
  evidence: {
    matched_keywords: ["AI code review", "evaluating"],
    matched_topics: ["developer tools"],
    intent_phrase: "testing Cursor vs Copilot",
    confidence: "high",
    explanation: "Explicit team tool evaluation comparing multiple commercial products.",
    observed_text: "testing Cursor vs Copilot vs CodeRabbit",
    unknown: [],
    purchasing_event_verified: false,
  },
  monitors: [],
};

const SAMPLE_RUN: DiscoveryRun = {
  id: "run-9999-9999-9999-9999",
  job_id: "job-9999-9999-9999-9999",
  title: "AI Code Review Evaluations",
  original_prompt: "Find engineering leaders evaluating AI code review tools",
  search_mode: "ai",
  parent_discovery_id: null,
  monitor_id: null,
  created_by: "user@test.com",
  error_code: null,
  attempts: 1,
  requests_count: 8,
  coverage: "Ask HN + GitHub Discussions",
  configuration: {
    ...emptyIntentSearch(),
    keywords: ["AI code review", "CodeRabbit"],
    sources: ["hacker_news", "github"],
    categories: ["Tool / service evaluation"],
    result_limit: 20,
    min_relevance: 50,
  },
  status: "COMPLETED",
  matched_count: 1,
  scanned_count: 50,
  sources: ["hacker_news", "github"],
  keywords: ["AI code review", "CodeRabbit"],
  created_at: "2026-11-18T10:00:00Z",
  completed_at: "2026-11-18T10:02:00Z",
  strategy: {
    objective: "Find engineering leaders evaluating AI code review tools",
    target_customer_context: "Engineering Leaders",
    keyword_rationale: "Comparison terms identify active evaluators",
    source_rationale: "HN and GitHub capture technical discussions",
    exclusions_rationale: "Excludes generic job postings",
    limitations: ["Past 30 days discussions only."],
  },
  source_runs: [
    { provider: "hacker_news", status: "COMPLETE", scanned: 30, requests: 4, coverage: "Ask HN", signals_count: 1 },
    { provider: "github", status: "COMPLETE", scanned: 20, requests: 4, coverage: "Discussions", signals_count: 0 },
  ],
  signal_ids: ["sig-ai-1"],
  signals: [SAMPLE_SIGNAL_1],
};

const SAMPLE_SAVED: SavedSearch = {
  id: "saved-8888-8888-8888-8888",
  name: "AI Code Review Evaluation Watch",
  description: "Tracks engineering teams testing automated code reviewers",
  original_prompt: "Find engineering leaders evaluating AI code review tools",
  configuration: {
    ...emptyIntentSearch(),
    keywords: ["AI code review", "CodeRabbit"],
    sources: ["hacker_news", "github"],
    icp_id: "icp-eng",
  },
  revision: 1,
  last_run_discovery_id: null,
  created_by: "contact@planebyte.com",
  created_at: "2026-11-18T08:00:00Z",
  updated_at: "2026-11-18T08:30:00Z",
};

beforeEach(() => {
  vi.clearAllMocks();
  sessionStorage.clear();
  window.history.replaceState({}, "", "/intent-radar/discover");
  Element.prototype.scrollIntoView = vi.fn();
  mocks.radarRead.mockImplementation((path: string) => {
    if (path === "/settings") {
      return {
        data: {
          discovery_keywords: [],
          discovery_excluded: [],
          topics: [],
          min_relevance: 0,
          default_view: "cards",
          alerts_enabled: false,
          alert_threshold: 70,
          revision: 1,
          default_icp_id: null,
        },
        error: null,
        isPending: false,
        refetch: vi.fn(),
      };
    }
    if (path === "/icps") {
      return {
        data: { items: [{ id: "icp-eng", name: "Engineering Leaders" }] },
        error: null,
        isPending: false,
        refetch: vi.fn(),
      };
    }
    if (path.startsWith("/discoveries?")) {
      return {
        data: { items: [SAMPLE_RUN], total: 1, page: 1, page_size: 20 },
        error: null,
        isPending: false,
        refetch: vi.fn(),
      };
    }
    if (path === `/discoveries/${SAMPLE_RUN.id}`) {
      return { data: SAMPLE_RUN, error: null, isPending: false, refetch: vi.fn() };
    }
    if (path.startsWith("/saved-searches")) {
      return {
        data: { items: [SAMPLE_SAVED], total: 1, page: 1, page_size: 50 },
        error: null,
        isPending: false,
        refetch: vi.fn(),
      };
    }
    if (path.startsWith("/signals/")) {
      return { data: SAMPLE_SIGNAL_1, error: null, isPending: false, refetch: vi.fn() };
    }
    return { data: null, error: null, isPending: false, refetch: vi.fn() };
  });
});

afterEach(cleanup);

describe("PlaneByte Intent Radar — Discover Module Redesign", () => {
  it("Phase 1: Discover Main Page renders 4 real metrics, exactly 2 tabs, and + Create Discovery button", () => {
    render(wrap(<DiscoverExperience route="discover" />));

    // Header & action
    expect(screen.getByRole("heading", { name: "Discover Conversations" })).toBeVisible();
    expect(screen.getByText(/Search public conversations, review discoveries, and save research for later./i)).toBeVisible();
    const createBtn = screen.getByRole("link", { name: /Create Discovery/i });
    expect(createBtn).toBeVisible();
    expect(createBtn).toHaveAttribute("href", "/intent-radar/discover/new");

    // 4 Real metrics
    expect(screen.getByText("Total Discovery Runs")).toBeVisible();
    expect(screen.getByText("Conversations Found")).toBeVisible();
    expect(screen.getAllByText("Saved Searches")[0]).toBeVisible();
    expect(screen.getByText("Runs Requiring Attention")).toBeVisible();

    // Exactly 2 tabs
    const historyTab = screen.getByRole("tab", { name: /Discovery History/i });
    const savedTab = screen.getByRole("tab", { name: /Saved Searches/i });
    expect(historyTab).toBeVisible();
    expect(savedTab).toBeVisible();
    expect(historyTab).toHaveAttribute("aria-selected", "true");

    // Click Saved Searches tab switches view
    fireEvent.click(savedTab);
    expect(savedTab).toHaveAttribute("aria-selected", "true");
  });

  it("Phase 2: Create Discovery page renders unified 2-column workspace layout with 5 sections", () => {
    render(wrap(<DiscoverExperience route="discover/new" />));

    // Page title and breadcrumb
    expect(screen.getByRole("heading", { name: "Create Discovery" })).toBeVisible();

    // LEFT: Permanent AI Assistant
    fireEvent.click(screen.getByRole("button",{name:/Open AI Assistant/i}));
    expect(screen.getByText("Discovery Assistant")).toBeVisible();
    expect(screen.getByText(/Describe what you want to find. I'll help configure your search./i)).toBeVisible();
    expect(screen.getByText("Discovery setup")).toBeVisible();
    expect(screen.getByPlaceholderText(/Find teams looking for Postgres alternatives/i)).toBeVisible();

    // Quick starter chips
    expect(screen.getByText("Founders complaining about CRM complexity & cost")).toBeVisible();

    // RIGHT: 5 Logical sections
    expect(screen.getByRole("heading", { name: "Discovery Objective" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Keywords & Search Criteria" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Research Sources" })).toBeVisible();
    expect(screen.getByText("Advanced Filters",{exact:true})).toBeVisible();
    expect(screen.getByRole("heading", { name: "Review & Run" })).toBeVisible();

    // Contained action bar
    expect(screen.getAllByRole("link", { name: "Cancel" })[0]).toBeVisible();
    expect(screen.getAllByRole("button", { name: "Save Search" })[0]).toBeVisible();
    expect(screen.getAllByRole("button", { name: "Run Discovery" })[0]).toBeVisible();
  });

  it("Phase 3: AI Assistant receives prompt, generates proposed criteria diff, and applies to form", async () => {
    mocks.mutateAsync.mockResolvedValueOnce({
      schema_version:1,mode:'AI-assisted draft',draft:{name:'CRM alternatives',configuration:{keywords:['CRM alternative','replace HubSpot','affordable CRM'],topics:[],phrases:[],excluded:[],offerings:'',categories:['Tool / service evaluation'],sources:['hacker_news','github'],result_limit:20,min_relevance:65},strategy:{objective:'Find founders looking for CRM alternatives'}},
    });

    render(wrap(<DiscoverExperience route="discover/new" />));

    fireEvent.click(screen.getByRole("button",{name:/Open AI Assistant/i}));
    const assistantInput = screen.getByPlaceholderText(/Find teams looking for Postgres alternatives/i);
    fireEvent.change(assistantInput, { target: { value: "Find founders seeking CRM alternatives" } });
    fireEvent.submit(assistantInput.closest("form")!);

    // Proposed changes diff card appears
    expect(await screen.findByText("Proposed Search Criteria")).toBeVisible();
    expect(screen.getByText("+ CRM alternative")).toBeVisible();
    expect(screen.getByText("+ replace HubSpot")).toBeVisible();

    // Click Apply to Form
    const applyBtn = screen.getByRole("button", { name: /Apply to Form/i });
    expect(applyBtn).toBeVisible();
    fireEvent.click(applyBtn);

    // Form keywords updated
    expect(screen.getByText("CRM alternative")).toBeVisible();
    expect(screen.getByText("replace HubSpot")).toBeVisible();
    expect(screen.getByText("affordable CRM")).toBeVisible();

    // Undo button appears and works
    const undoBtn = screen.getByRole("button", { name: /Undo Changes/i });
    expect(undoBtn).toBeVisible();
    fireEvent.click(undoBtn);
  });

  it("Phase 4: Run Discovery validates inputs, calls /discover, and routes to run details", async () => {
    mocks.mutateAsync.mockResolvedValueOnce({executable:true}).mockResolvedValueOnce({
      id: "job-new-123",
      discovery_id: "run-new-123",
      status: "QUEUED",
      items: [],
    });

    render(wrap(<DiscoverExperience route="discover/new" />));

    // Try running without keywords -> validation alert
    const runBtn = screen.getAllByRole("button", { name: "Run Discovery" })[0];
    fireEvent.click(runBtn);

    // Add required keyword
    const kwInput = screen.getByPlaceholderText(/Type keyword/i);
    fireEvent.change(kwInput, { target: { value: "developer tools" } });
    fireEvent.keyDown(kwInput, { key: "Enter" });

    // Now keywords exist
    expect(screen.getByText("developer tools")).toBeVisible();

    // Click Run Discovery
    const activeRunBtn = screen.getAllByRole("button", { name: "Run Discovery" })[0];
    fireEvent.click(activeRunBtn);

    await waitFor(() => {
      expect(mocks.mutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          path: "/discover",
          body: expect.objectContaining({
            configuration: expect.objectContaining({
              keywords: expect.arrayContaining(["developer tools"]),
            }),
          }),
        })
      );
      expect(mocks.push).toHaveBeenCalledWith("/intent-radar/discover/runs/run-new-123");
    });
  });

  it("Phase 5: Saved Searches renders clean minimal table with Open in Builder and Run Search", async () => {
    render(wrap(<DiscoverExperience route="discover/saved" />));

    expect(screen.getByRole("tab", { name: /Saved Searches/i })).toBeVisible();
    expect(screen.getByRole("table")).toBeVisible();

    // Table columns check
    expect(screen.getByText("AI Code Review Evaluation Watch")).toBeVisible();
    expect(screen.getByText("Engineering Leaders")).toBeVisible(); // ICP tag
    expect(screen.getByRole("button", { name: /Open in Builder/i })).toBeVisible();
    expect(screen.getByRole("button", { name: /Run Search/i })).toBeVisible();

    // Open in builder navigates to /intent-radar/discover/new?saved_search_id=[id]
    fireEvent.click(screen.getByRole("button", { name: /Open in Builder/i }));
    expect(mocks.push).toHaveBeenCalledWith(`/intent-radar/discover/new?saved_search_id=${SAMPLE_SAVED.id}`);

    // Run Search executes search directly
    mocks.mutateAsync.mockResolvedValueOnce({
      id: "job-saved-1",
      discovery_id: "run-saved-1",
      status: "QUEUED",
      items: [],
    });

    fireEvent.click(screen.getByRole("button", { name: /Run Search/i }));
    await waitFor(() => {
      expect(mocks.push).toHaveBeenCalledWith("/intent-radar/discover/runs/run-saved-1");
    });
  });

  it("Phase 6: Discovery History renders standard table, Results primary action, and row navigation", async () => {
    render(wrap(<DiscoverExperience route="discover/history" />));

    expect(screen.getByRole("tab", { name: /Discovery History/i })).toBeVisible();
    expect(screen.getByRole("table")).toBeVisible();

    // Row details
    expect(screen.getByText("AI Code Review Evaluations")).toBeVisible();
    expect(screen.getByText("1 match")).toBeVisible();

    // Primary action button is Results
    const resultsBtn = screen.getByRole("button", { name: /Results/i });
    expect(resultsBtn).toBeVisible();
    fireEvent.click(resultsBtn);
    expect(mocks.push).toHaveBeenCalledWith(`/intent-radar/discover/runs/${SAMPLE_RUN.id}`);
  });

  it("Phase 7: Results table renders Conversation, Source, Relevance, Intent, Observed, Actions, and supports Convert to Opportunity & CSV export", async () => {
    render(wrap(<DiscoverExperience route={`discover/runs/${SAMPLE_RUN.id}`} />));

    expect(screen.getByRole("heading", { name: "AI Code Review Evaluations" })).toBeVisible();
    expect(screen.getByRole("table")).toBeVisible();

    // Table header columns
    expect(screen.getByRole("columnheader", { name: "Conversation" })).toBeVisible();
    expect(screen.getByRole("columnheader", { name: "Source" })).toBeVisible();
    expect(screen.getByRole("columnheader", { name: "Relevance" })).toBeVisible();
    expect(screen.getByRole("columnheader", { name: "Intent" })).toBeVisible();
    expect(screen.getByRole("columnheader", { name: "Observed" })).toBeVisible();
    expect(screen.getByRole("columnheader", { name: "Actions" })).toBeVisible();

    // Signal data row
    expect(screen.getByText("Teams evaluating AI code review tools in production")).toBeVisible();
    expect(screen.getByText("92/100")).toBeVisible();
    expect(screen.getAllByText("Tool / service evaluation")[0]).toBeVisible();

    // Convert to Opportunity action
    mocks.mutateAsync.mockResolvedValueOnce({ id: "opp-1", signal_id: "sig-ai-1" });
    const convertBtn = screen.getByRole("button", { name: /Convert/i });
    expect(convertBtn).toBeVisible();
    fireEvent.click(convertBtn);

    expect(await screen.findByText(/into an Opportunity/i)).toBeVisible();
    expect(screen.getByText("Added")).toBeVisible();

    const formats=screen.getByRole('combobox',{name:'Export format'});
    expect(formats).toHaveTextContent('CSV');
    expect(formats).toHaveTextContent('JSON');
    expect(screen.getByRole('button',{name:'Export'})).toBeEnabled();
  });
});
