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
        { id: "hacker_news", name: "Hacker News", state: "Available", coverage: "Official HN Firebase v0", documentation: "https://github.com/HackerNews/API", request_limit_per_check: 30 },
        { id: "github", name: "GitHub", state: "Connected", coverage: "GitHub REST & GraphQL", documentation: "https://docs.github.com", request_limit_per_check: 24 },
        { id: "stack_exchange", name: "Stack Exchange", state: "Available", coverage: "SE API 2.3", documentation: "https://api.stackexchange.com", configured_sites: ["stackoverflow"], request_limit_per_check: 8 },
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
  created_by: "contact@planebyte.com",
  created_at: "2026-11-18T09:00:00Z",
  completed_at: "2026-11-18T09:00:15Z",
  status: "COMPLETED",
  error_code: null,
  attempts: 1,
  sources: ["hacker_news", "github"],
  keywords: ["AI code review", "CodeRabbit", "Copilot review"],
  matched_count: 1,
  scanned_count: 50,
  requests_count: 8,
  coverage: "HN Ask & GitHub active PR issues scanned.",
  configuration: {
    ...emptyIntentSearch(),
    keywords: ["AI code review", "CodeRabbit", "Copilot review"],
    excluded: ["tutorial", "free", "intern"],
    sources: ["hacker_news", "github"],
    min_relevance: 70,
    result_limit: 20,
  },
  strategy: {
    objective: "Identify engineering teams comparing AI code review solutions",
    target_customer_context: "PlaneByte · ICP: Engineering Leaders",
    keyword_rationale: "Targeting active tool evaluations and comparison queries.",
    source_rationale: "Hacker News and GitHub capture authentic developer feedback.",
    exclusions_rationale: "Filter academic papers and beginner tutorials.",
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

describe("PlaneByte Intent Radar — Discover 3.0 Redesign", () => {
  it("Phase 1: renders 3 clear top-level tabs and switches modes smoothly", () => {
    render(wrap(<DiscoverExperience route="discover" />));

    // 3 clean top-level tabs
    expect(screen.getByRole("link", { name: /New Discovery/i })).toBeVisible();
    expect(screen.getByRole("link", { name: /Discovery History/i })).toBeVisible();
    expect(screen.getByRole("link", { name: /Saved Searches/i })).toBeVisible();

    // Mode toggle between AI Discovery (recommended) and Advanced Search
    const aiBtn = screen.getByRole("button", { name: /AI Discovery/i });
    const advBtn = screen.getByRole("button", { name: "Advanced Search" });
    expect(aiBtn).toBeVisible();
    expect(advBtn).toBeVisible();
    expect(aiBtn).toHaveAttribute("aria-pressed", "true");

    // Switching to Advanced Search reveals the 4 structured sections
    fireEvent.click(advBtn);
    expect(advBtn).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText("1 · Search Terms")).toBeVisible();
    expect(screen.getByText("2 · Research Sources")).toBeVisible();
    expect(screen.getByText("3 · Search Intent")).toBeVisible();
    expect(screen.getByText(/4 · Advanced Filters/i)).toBeVisible();
  });

  it("Phase 2: AI Discovery generates strategy review, supports natural language refinement and Undo", async () => {
    mocks.mutateAsync.mockResolvedValueOnce({
      draft: {
        name: "AI Code Review Evaluations",
        configuration: {
          ...emptyIntentSearch(),
          keywords: ["AI code review", "CodeRabbit"],
          excluded: ["tutorial"],
          sources: ["hacker_news", "github"],
          categories: ["Tool / service evaluation"],
          result_limit: 20,
        },
        strategy: {
          objective: "Find engineering teams evaluating AI code review tools",
          target_customer_context: "Engineering Leaders",
          keyword_rationale: "Comparison terms identify active evaluators",
          source_rationale: "HN and GitHub capture technical discussions",
          limitations: [],
        },
      },
      mode: "AI-assisted draft",
      quota_exhausted: false,
      fallback_reason: null,
    });

    render(wrap(<DiscoverExperience route="discover" />));

    // Clear starting prompt input
    expect(screen.getByRole("heading", { name: "What would you like to discover?" })).toBeVisible();
    const promptInput = screen.getByPlaceholderText(/Find engineering leaders evaluating AI code review tools/i);
    expect(promptInput).toBeVisible();

    // Click example suggestion chip
    fireEvent.click(screen.getByText("Find engineering leaders evaluating AI code review tools"));
    expect(promptInput).toHaveValue("Find engineering leaders evaluating AI code review tools");

    // Click Build Discovery
    fireEvent.click(screen.getByRole("button", { name: /Build Discovery/i }));

    // Strategy review card renders
    expect(await screen.findByRole("heading", { name: "Discovery Strategy Review" })).toBeVisible();
    expect(screen.getByText("Find engineering teams evaluating AI code review tools")).toBeVisible();
    expect(screen.getByText("AI code review")).toBeVisible();
    expect(screen.getByText("CodeRabbit")).toBeVisible();
    expect(screen.getByRole("button", { name: /Run Discovery/i })).toBeVisible();

    // Natural-language Refine with AI
    mocks.mutateAsync.mockResolvedValueOnce({
      draft: {
        name: "AI Code Review (GitHub Only)",
        configuration: {
          ...emptyIntentSearch(),
          keywords: ["AI code review", "CodeRabbit", "Copilot"],
          excluded: ["tutorial", "free tier"],
          sources: ["github"],
          categories: ["Tool / service evaluation"],
          result_limit: 20,
        },
        strategy: {
          objective: "Narrowed to GitHub with Copilot evaluation terms",
          target_customer_context: "Engineering Leaders",
          keyword_rationale: "Added Copilot",
          source_rationale: "Filtered to GitHub",
          limitations: [],
        },
      },
      mode: "AI-assisted draft",
      quota_exhausted: false,
    });

    const refineInput = screen.getByPlaceholderText(/Narrow to GitHub and Hacker News only/i);
    fireEvent.change(refineInput, { target: { value: "Focus on GitHub only and add Copilot" } });
    fireEvent.click(screen.getByRole("button", { name: "Refine" }));

    expect(await screen.findByText(/Refined: applied changes based on/i)).toBeVisible();
    expect(screen.getByText("Copilot")).toBeVisible();

    // Click Undo to revert refinement
    fireEvent.click(screen.getByRole("button", { name: /Undo Last Refinement/i }));
    expect(screen.getByText("Reverted to previous strategy criteria.")).toBeVisible();
  });

  it("Phase 3: Advanced Search builder validates inputs and opens review", async () => {
    render(wrap(<DiscoverExperience route="discover" />));

    fireEvent.click(screen.getByRole("button", { name: "Advanced Search" }));

    // Try clicking Review Discovery without keywords -> shows validation
    fireEvent.click(screen.getByRole("button", { name: /Review Discovery/i }));
    expect(await screen.findByText(/Add at least 1 keyword/i)).toBeVisible();

    // Add keyword & negative exclusion in section 1
    fireEvent.change(screen.getByLabelText("Add Primary Search Keywords"), { target: { value: "PostgreSQL vs ClickHouse" } });
    fireEvent.keyDown(screen.getByLabelText("Add Primary Search Keywords"), { key: "Enter" });

    fireEvent.change(screen.getByLabelText("Add Negative Keywords (Exclusions)"), { target: { value: "homework" } });
    fireEvent.keyDown(screen.getByLabelText("Add Negative Keywords (Exclusions)"), { key: "Enter" });

    // Review Discovery button expands the strategy review card
    fireEvent.click(screen.getByRole("button", { name: /Review Discovery/i }));
    expect(await screen.findByRole("heading", { name: "Discovery Strategy Review" })).toBeVisible();
    expect(screen.getAllByText("PostgreSQL vs ClickHouse")[0]).toBeVisible();
    expect(screen.getAllByText("homework")[0]).toBeVisible();
  });

  it("Phase 5: Saved Searches renders clean minimal table with Open in Builder and Run Search", async () => {
    render(wrap(<DiscoverExperience route="discover/saved" />));

    expect(screen.getByRole("heading", { name: "Saved Searches" })).toBeVisible();
    expect(screen.getByRole("table")).toBeVisible();

    // Table columns check
    expect(screen.getByText("AI Code Review Evaluation Watch")).toBeVisible();
    expect(screen.getByText("Engineering Leaders")).toBeVisible(); // ICP tag
    expect(screen.getByRole("button", { name: /Open in Builder/i })).toBeVisible();
    expect(screen.getByRole("button", { name: /Run Search/i })).toBeVisible();

    // Run Search executes search directly
    mocks.mutateAsync.mockResolvedValueOnce({
      id: "job-saved-1",
      discovery_id: "run-saved-1",
      status: "QUEUED",
      items: [],
    });

    fireEvent.click(screen.getByRole("button", { name: /Run Search/i }));
    await waitFor(() => {
      expect(mocks.push).toHaveBeenCalledWith(expect.stringContaining("/intent-radar/discover?run=run-saved-1&job=job-saved-1"));
    });
  });

  it("Phase 6: Discovery History renders standard table, Results primary action, and row navigation", async () => {
    render(wrap(<DiscoverExperience route="discover/history" />));

    expect(screen.getByRole("heading", { name: "Discovery History" })).toBeVisible();
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

  it("Phase 4: Results table renders Conversation, Source, Relevance, Intent, Observed, Actions, and supports Convert to Opportunity & CSV export", async () => {
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

    // CSV Export button exists
    expect(screen.getByRole("button", { name: /CSV/i })).toBeVisible();
    expect(screen.getByRole("button", { name: /JSON/i })).toBeVisible();
  });
});
