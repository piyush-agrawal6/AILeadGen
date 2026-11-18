import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { OpportunitiesWorkspace } from "@/components/intent-radar/opportunities/OpportunitiesWorkspace";
import { OpportunityDetail } from "@/components/intent-radar/opportunities/OpportunityDetail";
import { EvidenceDetail } from "@/components/intent-radar/evidence-experience";
import { SignalsWorkspace } from "@/components/intent-radar/signal-workspace";
import { request } from "@/lib/intelligence";

vi.mock("@/lib/intelligence", () => ({ request: vi.fn() }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => "/intent-radar/opportunities",
}));
vi.mock("@/components/intent-radar/provider", () => ({
  useRadarCapabilities: () => ({
    data: { growth_enabled: true, can_write: true, can_manage: true },
  }),
  useRadarMutation: () => ({
    mutate: vi.fn(),
    mutateAsync: vi.fn().mockResolvedValue({}),
    isPending: false,
  }),
  useRadarRead: (path: string, enabled = true) => {
    if (!enabled) return { data: null, isPending: false, error: null, refetch: vi.fn() };
    if (path.startsWith("/opportunities/opp-1")) {
      return {
        data: {
          id: "opp-1",
          signal_id: "sig-1",
          status: "New",
          priority: "High",
          notes: "High intent webhook migration candidate",
          next_action: "Book technical demo",
          assigned_to: "founder@planebyte.com",
          revision: 1,
          created_at: "2026-11-18T10:00:00Z",
          updated_at: "2026-11-18T12:00:00Z",
          signal: {
            id: "sig-1",
            title: "Need enterprise webhook monitoring system",
            source: "GitHub",
            source_url: "https://github.com/org/repo/issues/1",
            excerpt: "Evaluating reliable webhook logging and intent tracking solutions.",
            observed_at: "2026-11-18T09:00:00Z",
            retrieved_at: "2026-11-18T09:30:00Z",
            category: "Recommendation request",
            score: 94,
            status: "Qualified",
            saved: true,
            evidence: {
              explanation: "Direct developer request evaluating commercial webhook monitoring.",
              matched_keywords: ["webhook", "monitoring", "enterprise"],
              intent_phrase: "evaluating reliable webhook logging",
              confidence: "High",
              observed_text: "Evaluating reliable webhook logging solutions.",
              unknown: ["Budget unverified"],
              purchasing_event_verified: false,
            },
            monitors: [],
            buying_intent: "Explicit commercial intent",
            icp_fit: "Match",
          },
        },
        isPending: false,
        error: null,
        refetch: vi.fn(),
      };
    }
    if (path.startsWith("/opportunities")) {
      return {
        data: {
          items: [
            {
              id: "opp-1",
              signal_id: "sig-1",
              status: "New",
              priority: "High",
              notes: "High intent webhook migration candidate",
              next_action: "Book technical demo",
              assigned_to: "founder@planebyte.com",
              revision: 1,
              created_at: "2026-11-18T10:00:00Z",
              updated_at: "2026-11-18T12:00:00Z",
              signal: {
                id: "sig-1",
                title: "Need enterprise webhook monitoring system",
                source: "GitHub",
                source_url: "https://github.com/org/repo/issues/1",
                excerpt: "Evaluating reliable webhook logging and intent tracking solutions.",
                observed_at: "2026-11-18T09:00:00Z",
                retrieved_at: "2026-11-18T09:30:00Z",
                category: "Recommendation request",
                score: 94,
                status: "Qualified",
                saved: true,
                evidence: {
                  explanation: "Direct developer request evaluating commercial webhook monitoring.",
                  matched_keywords: ["webhook", "monitoring", "enterprise"],
                  intent_phrase: "evaluating reliable webhook logging",
                  confidence: "High",
                  observed_text: "Evaluating reliable webhook logging solutions.",
                  unknown: ["Budget unverified"],
                  purchasing_event_verified: false,
                },
                monitors: [],
                buying_intent: "Explicit commercial intent",
                icp_fit: "Match",
              },
            },
          ],
          total: 1,
          page: 1,
          page_size: 25,
          status_counts: {
            all: 1,
            new: 1,
            reviewing: 0,
            qualified: 0,
            saved: 0,
            dismissed: 0,
          },
        },
        isPending: false,
        error: null,
        refetch: vi.fn(),
      };
    }
    if (path.startsWith("/signals/sig-1")) {
      return {
        data: {
          id: "sig-1",
          title: "Need enterprise webhook monitoring system",
          source: "GitHub",
          source_url: "https://github.com/org/repo/issues/1",
          excerpt: "Evaluating reliable webhook logging and intent tracking solutions.",
          observed_at: "2026-11-18T09:00:00Z",
          retrieved_at: "2026-11-18T09:30:00Z",
          category: "Recommendation request",
          score: 94,
          status: "Qualified",
          saved: true,
          opportunity_id: "opp-1",
          opportunity_status: "New",
          evidence: {
            explanation: "Direct developer request evaluating commercial webhook monitoring.",
            matched_keywords: ["webhook", "monitoring", "enterprise"],
            intent_phrase: "evaluating reliable webhook logging",
            confidence: "High",
            observed_text: "Evaluating reliable webhook logging solutions.",
            unknown: ["Budget unverified"],
            purchasing_event_verified: false,
          },
          monitors: [],
          buying_intent: "Explicit commercial intent",
          icp_fit: "Match",
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
              id: "sig-1",
              title: "Need enterprise webhook monitoring system",
              source: "GitHub",
              source_url: "https://github.com/org/repo/issues/1",
              excerpt: "Evaluating reliable webhook logging and intent tracking solutions.",
              observed_at: "2026-11-18T09:00:00Z",
              retrieved_at: "2026-11-18T09:30:00Z",
              category: "Recommendation request",
              score: 94,
              status: "Qualified",
              saved: true,
              opportunity_id: "opp-1",
              opportunity_status: "New",
              evidence: {
                explanation: "Direct developer request evaluating commercial webhook monitoring.",
                matched_keywords: ["webhook", "monitoring"],
                intent_phrase: "evaluating reliable webhook logging",
                confidence: "High",
                observed_text: "Evaluating reliable webhook logging solutions.",
                unknown: [],
                purchasing_event_verified: false,
              },
              monitors: [],
              buying_intent: "Explicit commercial intent",
              icp_fit: "Match",
            },
          ],
          total: 1,
          page: 1,
          page_size: 25,
          view_counts: {
            all: 1,
            needs_review: 0,
            high_intent: 1,
            saved: 1,
            qualified: 1,
            dismissed: 0,
          },
        },
        isPending: false,
        error: null,
        refetch: vi.fn(),
      };
    }
    return { data: null, isPending: false, error: null, refetch: vi.fn() };
  },
}));

const call = vi.mocked(request);

function wrap(ui: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.resetAllMocks();
  call.mockResolvedValue({ items: [] } as never);
});

describe("Opportunities & Signals Redesign", () => {
  it("renders the Opportunities table with the required 7 columns and status counts", async () => {
    wrap(<OpportunitiesWorkspace />);
    expect(
      await screen.findByRole("heading", { name: "Opportunities" }),
    ).toBeVisible();

    // 7 Required Columns
    expect(screen.getByRole("columnheader", { name: "Opportunity" })).toBeVisible();
    expect(screen.getByRole("columnheader", { name: "Source" })).toBeVisible();
    expect(screen.getByRole("columnheader", { name: "Priority" })).toBeVisible();
    expect(screen.getByRole("columnheader", { name: "Status" })).toBeVisible();
    expect(screen.getByRole("columnheader", { name: "Assigned To" })).toBeVisible();
    expect(screen.getByRole("columnheader", { name: "Updated" })).toBeVisible();
    expect(screen.getByRole("columnheader", { name: "Actions" })).toBeVisible();

    // Workflow tabs with real counts
    expect(screen.getByRole("button", { name: /All \(1\)/i })).toBeVisible();
    expect(screen.getByRole("button", { name: /New \(1\)/i })).toBeVisible();
    expect(screen.getByRole("button", { name: /Reviewing \(0\)/i })).toBeVisible();

    // Row contents
    expect(
      screen.getByText("Need enterprise webhook monitoring system"),
    ).toBeVisible();
    expect(screen.getAllByText("GitHub").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("High")).toBeVisible();
    expect(screen.getAllByText("New").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("founder")).toBeVisible();
    expect(screen.getByRole("link", { name: "Open" })).toBeVisible();
  });

  it("renders the dedicated CRM Opportunity Details experience with action bar and 4 tabs", async () => {
    const oppData = {
      id: "opp-1",
      signal_id: "sig-1",
      status: "New",
      priority: "High",
      notes: "High intent webhook migration candidate",
      next_action: "Book technical demo",
      assigned_to: "founder@planebyte.com",
      revision: 1,
      created_at: "2026-11-18T10:00:00Z",
      updated_at: "2026-11-18T12:00:00Z",
      signal: {
        id: "sig-1",
        title: "Need enterprise webhook monitoring system",
        source: "GitHub",
        source_url: "https://github.com/org/repo/issues/1",
        excerpt: "Evaluating reliable webhook logging and intent tracking solutions.",
        observed_at: "2026-11-18T09:00:00Z",
        retrieved_at: "2026-11-18T09:30:00Z",
        category: "Recommendation request" as const,
        score: 94,
        status: "Qualified",
        saved: true,
        evidence: {
          explanation: "Direct developer request evaluating commercial webhook monitoring.",
          matched_keywords: ["webhook", "monitoring", "enterprise"],
          matched_topics: ["Webhooks", "Monitoring"],
          intent_phrase: "evaluating reliable webhook logging",
          confidence: "High",
          observed_text: "Evaluating reliable webhook logging solutions.",
          unknown: ["Budget unverified"],
          purchasing_event_verified: false as const,
        },
        monitors: [],
        buying_intent: "Explicit commercial intent" as const,
        icp_fit: "Match" as const,
        notes: "",
        revision: 1,
        available: 1,
      },
    };

    wrap(
      <OpportunityDetail
        opportunity={oppData}
        onUpdate={vi.fn()}
        onDelete={vi.fn()}
      />,
    );

    expect(
      screen.getByRole("link", { name: /Back to Opportunities/i }),
    ).toBeVisible();
    expect(
      screen.getByRole("button", { name: /Edit Details/i }),
    ).toBeVisible();
    expect(screen.getByRole("link", { name: /View Signal/i })).toBeVisible();
    expect(screen.getByRole("link", { name: /Ask AI/i })).toBeVisible();

    // 4 CRM Tabs
    expect(screen.getByRole("button", { name: "Overview" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Evidence" })).toBeVisible();
    expect(screen.getByRole("button", { name: "AI Intelligence" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Activity & Notes" })).toBeVisible();

    // Overview content
    expect(screen.getAllByText("Book technical demo").length).toBeGreaterThanOrEqual(1);
    expect(
      screen.getByText(/Direct developer request evaluating commercial webhook monitoring/),
    ).toBeVisible();

    // Tab switching to Evidence
    fireEvent.click(screen.getByRole("button", { name: "Evidence" }));
    expect(
      screen.getByText(/Evaluating reliable webhook logging and intent tracking solutions/),
    ).toBeVisible();
    expect(
      screen.getByRole("link", { name: /Open original discussion/i }),
    ).toHaveAttribute("href", "https://github.com/org/repo/issues/1");
  });

  it("renders Signal Details with Decision Summary, actions, and 4 structured tabs", async () => {
    wrap(<EvidenceDetail id="sig-1" />);

    expect(
      await screen.findByRole("link", { name: /Back to Signals/i }),
    ).toBeVisible();
    expect(screen.getByRole("heading", { name: "Decision Summary" })).toBeVisible();
    expect(screen.getByText("Topic Relevance")).toBeVisible();
    expect(screen.getByText("Buying Intent")).toBeVisible();
    expect(screen.getByText("ICP Fit")).toBeVisible();
    expect(screen.getAllByText("Opportunity Status").length).toBeGreaterThanOrEqual(1);

    // Primary action View Opportunity (since already linked)
    expect(screen.getByRole("button", { name: /View Opportunity/i })).toBeVisible();
    expect(screen.getByRole("button", { name: "Qualified" })).toBeVisible();
    expect(screen.getByRole("button", { name: /Mark Reviewed/i })).toBeVisible();
    expect(screen.getByRole("button", { name: "Saved" })).toBeVisible();
    expect(screen.getByRole("button", { name: /Dismiss/i })).toBeVisible();

    // 4 Tabs
    expect(screen.getByRole("button", { name: "Overview" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Evidence" })).toBeVisible();
    expect(screen.getByRole("button", { name: "AI Intelligence" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Activity & Notes" })).toBeVisible();
  });

  it("renders Signals table with the required columns and shows bulk toolbar on selection", async () => {
    wrap(<SignalsWorkspace />);
    expect(
      await screen.findByRole("heading", { name: "Intent Signals" }),
    ).toBeVisible();

    // Check table headers
    expect(screen.getByRole("columnheader", { name: "Signal" })).toBeVisible();
    expect(screen.getByRole("columnheader", { name: "Source" })).toBeVisible();
    expect(screen.getByRole("columnheader", { name: "Relevance" })).toBeVisible();
    expect(screen.getByRole("columnheader", { name: "Buying Intent" })).toBeVisible();
    expect(screen.getByRole("columnheader", { name: "Status" })).toBeVisible();
    expect(screen.getByRole("columnheader", { name: "Observed" })).toBeVisible();
    expect(screen.getByRole("columnheader", { name: "Actions" })).toBeVisible();

    // Bulk selection checkbox
    const selectBox = screen.getByLabelText(/Select all signals on this page/i);
    fireEvent.click(selectBox);

    // Bulk toolbar must appear with confirmed actions
    expect(screen.getByText(/1 selected on this page/i)).toBeVisible();
    expect(screen.getByRole("button", { name: /Mark Reviewed/i })).toBeVisible();
    expect(screen.getByRole("button", { name: /Qualify/i })).toBeVisible();
    expect(
      screen.getByRole("button", { name: /Create Opportunities/i }),
    ).toBeVisible();
    expect(
      screen.getByRole("button", { name: /Reset to Needs Review/i }),
    ).toBeVisible();
    expect(screen.getByRole("button", { name: /Dismiss/i })).toBeVisible();
    expect(screen.getByRole("button", { name: "Clear" })).toBeVisible();
  });
});
