import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MonitorsDashboard } from "@/components/intent-radar/monitors/MonitorsDashboard";
import { MonitorBuilderPage } from "@/components/intent-radar/monitors/MonitorBuilderPage";
import { MonitorDetailPage } from "@/components/intent-radar/monitors/MonitorDetailPage";
import { RecordEditDrawer } from "@/components/intent-radar/detail/RecordEditDrawer";
import type { IntentMonitor } from "@/lib/intent-radar";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => "/intent-radar/monitors",
}));

const mockMutateAsync = vi.fn().mockResolvedValue({ id: "job-1", status: "QUEUED" });

vi.mock("@/components/intent-radar/provider", () => ({
  useRadarCapabilities: () => ({
    data: {
      can_write: true,
      can_manage: true,
      sources: [
        { id: "hacker_news", name: "Hacker News", state: "Connected", coverage: "100%", documentation: "" },
        { id: "github", name: "GitHub", state: "Connected", coverage: "100%", documentation: "" },
      ],
      usage: { searches_today: 5, daily_search_limit: 100, monitor_limit: 25 },
    },
  }),
  useRadarMutation: () => ({
    mutate: vi.fn(),
    mutateAsync: mockMutateAsync,
    isPending: false,
  }),
  useRadarRead: (path: string, enabled = true) => {
    if (!enabled) return { data: null, isPending: false, error: null, refetch: vi.fn() };

    if (path.startsWith("/monitors/mon-1/runs")) {
      return {
        data: {
          items: [
            {
              id: "run-1",
              created_at: "2026-11-18T14:00:00Z",
              provider: "hacker_news",
              status: "COMPLETED",
              result: { scanned: 45, matched: 3, new_signals: 2 },
            },
          ],
        },
        isPending: false,
        error: null,
        refetch: vi.fn(),
      };
    }

    if (path.startsWith("/monitors/mon-1")) {
      return {
        data: {
          id: "mon-1",
          name: "Vector Database Migration",
          description: "Tracking developer discussions on vector DB alternatives",
          goal: "Find teams migrating from Pinecone",
          configuration: {
            keywords: ["vector database", "pinecone", "pgvector"],
            excluded: ["hiring", "crypto"],
            sources: ["hacker_news", "github"],
            categories: ["Tool / service evaluation"],
            min_relevance: 60,
          },
          status: "Active",
          revision: 2,
          created_at: "2026-11-18T10:00:00Z",
          last_checked: "2026-11-18T14:00:00Z",
          last_job_id: "job-1",
          schedule: { frequency: "Daily", timezone: "UTC" },
          next_run_at: "2026-11-19T14:00:00Z",
          signals_count: 12,
        },
        isPending: false,
        error: null,
        refetch: vi.fn(),
      };
    }

    if (path.startsWith("/monitors")) {
      return {
        data: {
          items: [
            {
              id: "mon-1",
              name: "Vector Database Migration",
              description: "Tracking developer discussions on vector DB alternatives",
              goal: "Find teams migrating from Pinecone",
              configuration: {
                keywords: ["vector database", "pinecone", "pgvector"],
                excluded: ["hiring"],
                sources: ["hacker_news", "github"],
                categories: ["Tool / service evaluation"],
                min_relevance: 60,
              },
              status: "Active",
              revision: 2,
              created_at: "2026-11-18T10:00:00Z",
              last_checked: "2026-11-18T14:00:00Z",
              last_job_id: "job-1",
              schedule: { frequency: "Daily", timezone: "UTC" },
              next_run_at: "2026-11-19T14:00:00Z",
              signals_count: 12,
            },
          ],
          total: 1,
          page: 1,
          page_size: 20,
        },
        isPending: false,
        error: null,
        refetch: vi.fn(),
      };
    }

    if (path.startsWith("/signals")) {
      return {
        data: {
          items: [
            {
              id: "sig-10",
              title: "Migrating from Pinecone to pgvector in production",
              source: "Hacker News",
              source_url: "https://news.ycombinator.com/item?id=123",
              excerpt: "We hit scaling bottlenecks with Pinecone and are evaluating self-hosted alternatives.",
              observed_at: "2026-11-18T13:00:00Z",
              retrieved_at: "2026-11-18T14:00:00Z",
              category: "Tool / service evaluation",
              score: 91,
              status: "New",
              saved: false,
              revision: 1,
              available: 1,
              monitors: [{ id: "mon-1", name: "Vector Database Migration" }],
              evidence: {
                explanation: "Explicit migration discussion.",
                matched_keywords: ["pinecone", "pgvector"],
                matched_topics: ["Databases"],
                intent_phrase: "evaluating self-hosted alternatives",
                confidence: "High",
                observed_text: "We hit scaling bottlenecks with Pinecone.",
                unknown: [],
                purchasing_event_verified: false,
              },
            },
          ],
          total: 1,
          page: 1,
          page_size: 20,
        },
        isPending: false,
        error: null,
        refetch: vi.fn(),
      };
    }

    if (path === "/jobs") {
      return { data: { items: [] }, isPending: false, error: null, refetch: vi.fn() };
    }

    if (path === "/icps") {
      return {
        data: {
          items: [
            { id: "icp-1", name: "B2B SaaS Technical Founders" },
            { id: "icp-2", name: "Enterprise DevOps Leads" },
          ],
        },
        isPending: false,
        error: null,
        refetch: vi.fn(),
      };
    }

    return { data: null, isPending: false, error: null, refetch: vi.fn() };
  },
}));

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe("Monitors Rebuild & Details 3.0", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the 8-column Monitors data table with metrics and status tabs", async () => {
    wrap(<MonitorsDashboard />);

    expect(await screen.findByRole("heading", { name: "Monitoring" })).toBeVisible();

    // 8 Required Columns
    expect(screen.getByRole("columnheader", { name: "Monitor" })).toBeVisible();
    expect(screen.getByRole("columnheader", { name: "Status" })).toBeVisible();
    expect(screen.getByRole("columnheader", { name: "Sources" })).toBeVisible();
    expect(screen.getByRole("columnheader", { name: "Frequency" })).toBeVisible();
    expect(screen.getByRole("columnheader", { name: "Last Check" })).toBeVisible();
    expect(screen.getByRole("columnheader", { name: "Next Check" })).toBeVisible();
    expect(screen.getByRole("columnheader", { name: "New Matches" })).toBeVisible();
    expect(screen.getByRole("columnheader", { name: "Actions" })).toBeVisible();

    // Status filter tabs
    expect(screen.getByRole("button", { name: /All Monitors/i })).toBeVisible();
    expect(screen.getByRole("button", { name: /Running/i })).toBeVisible();
    expect(screen.getByRole("button", { name: /Paused/i })).toBeVisible();
    expect(screen.getByRole("button", { name: /Drafts/i })).toBeVisible();
    expect(screen.getByRole("button", { name: /Archived/i })).toBeVisible();

    // Data Row
    expect(screen.getByText("Vector Database Migration")).toBeVisible();
    expect(screen.getByText("Enabled · Daily")).toBeVisible();
    expect(screen.getAllByText("Hacker News").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Daily")).toBeVisible();

    // Run Immediate Check
    const runBtn = screen.getByRole("button", { name: "Run" });
    expect(runBtn).toBeVisible();
    fireEvent.click(runBtn);
    expect(mockMutateAsync).toHaveBeenCalledWith(
      expect.objectContaining({ path: "/discover" })
    );
  });

  it("renders the dedicated full-page Monitor Builder with AI setup and quality validation", async () => {
    wrap(<MonitorBuilderPage />);

    expect(await screen.findByRole("heading", { name: "Create Monitor" })).toBeVisible();
    expect(screen.getByText("Describe what you want to monitor")).toBeVisible();
    expect(screen.getByPlaceholderText(/Find SaaS founders/i)).toBeVisible();

    // Form Sections
    expect(screen.getByText("1. What to monitor")).toBeVisible();
    expect(screen.getByText("2. Search criteria & keywords")).toBeVisible();
    expect(screen.getByText("3. Approved sources")).toBeVisible();
    expect(screen.getByText("4. Schedule & check frequency")).toBeVisible();

    // Action bar buttons
    expect(screen.getByRole("button", { name: /Save Draft/i })).toBeVisible();
    expect(screen.getByRole("button", { name: /Create Monitor/i })).toBeVisible();

    // Enter low quality keywords to trigger warning
    const kwInput = screen.getByPlaceholderText(/Add keyword/i);
    fireEvent.change(kwInput, { target: { value: "xx" } });
    fireEvent.keyDown(kwInput, { key: "Enter" });

    // Informative non-blocking quality warning
    await waitFor(() => {
      expect(screen.getByText(/Low-information keyword/i)).toBeVisible();
    });
  });

  it("renders Monitor Details with metrics strip, 3 tabs, and execution history", async () => {
    wrap(<MonitorDetailPage id="mon-1" />);

    expect(await screen.findByRole("heading", { name: "Vector Database Migration" })).toBeVisible();
    expect(screen.getByRole("link", { name: /Back to Monitors/i })).toBeVisible();

    // Operational metrics strip
    expect(screen.getByText("Sources Monitored")).toBeVisible();
    expect(screen.getByText("Last Execution")).toBeVisible();
    expect(screen.getByText("Next Scheduled Check")).toBeVisible();
    expect(screen.getByText("Total Matches")).toBeVisible();

    // 3 Tabs
    expect(screen.getByRole("button", { name: "Overview" })).toBeVisible();
    expect(screen.getByRole("button", { name: /Run History/i })).toBeVisible();
    expect(screen.getByRole("button", { name: /Matches/i })).toBeVisible();

    // Switch to Run History Tab
    fireEvent.click(screen.getByRole("button", { name: /Run History/i }));
    expect(await screen.findByRole("columnheader", { name: "Started" })).toBeVisible();
    expect(screen.getByRole("columnheader", { name: "Source" })).toBeVisible();
    expect(screen.getByRole("columnheader", { name: "Status" })).toBeVisible();
    expect(screen.getByRole("columnheader", { name: "Coverage & Errors" })).toBeVisible();
    expect(screen.getByText("COMPLETED")).toBeVisible();

    // Switch to Matches Tab
    fireEvent.click(screen.getByRole("button", { name: /^Matches/i }));
    expect(await screen.findByText(/Discovered Signals/i)).toBeVisible();
    expect(screen.getAllByText(/Migrating from Pinecone/i)[0]).toBeVisible();
  });

  it("RecordEditDrawer opens and updates status, priority, and notes", async () => {
    const handleSave = vi.fn().mockResolvedValue(undefined);
    const { rerender } = wrap(
      <RecordEditDrawer
        open={true}
        onOpenChange={vi.fn()}
        initialValues={{
          status: "New",
          priority: "Medium",
          assigned_to: null,
          next_action: "Review proposal",
          notes: "Initial qualification note",
        }}
        onSave={handleSave}
      />
    );

    expect(screen.getByRole("heading", { name: "Edit Record" })).toBeVisible();
    expect(screen.getByDisplayValue("Review proposal")).toBeVisible();
    expect(screen.getByDisplayValue("Initial qualification note")).toBeVisible();

    // Update Priority to High
    const highBtn = screen.getByRole("button", { name: "High" });
    fireEvent.click(highBtn);

    // Save
    const saveBtn = screen.getByRole("button", { name: "Save Changes" });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(handleSave).toHaveBeenCalledWith(
        expect.objectContaining({
          priority: "High",
          status: "New",
        })
      );
    });
  });
});
