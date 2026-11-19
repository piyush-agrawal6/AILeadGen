import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ICPDashboard } from "@/components/intent-radar/ideal-customers/ICPDashboard";
import { ICPBuilderPage } from "@/components/intent-radar/ideal-customers/ICPBuilderPage";
import { ICPComparePage } from "@/components/intent-radar/ideal-customers/ICPComparePage";
import { ICPDetailPage } from "@/components/intent-radar/ideal-customers/ICPDetailPage";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import * as intelligence from "@/lib/intelligence";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/intent-radar/ideal-customers",
}));

const mockProfiles = [
  {
    id: "icp-1",
    name: "Mid-Market B2B SaaS",
    description: "Founders and CTOs looking for developer tooling",
    status: "ACTIVE" as const,
    revision: 1,
    is_primary: true,
    related_counts: { discoveries: 3, monitors: 2 },
    criteria: {
      company: {
        industries: ["B2B SaaS", "DevTools"],
        size: ["51-200 (Mid-Market / Growth)"],
        geographies: ["North America"],
      },
      contact: {
        job_titles: ["CTO", "VP Engineering"],
      },
      intent: {
        pain_points: ["High database costs", "Deployment friction"],
        buying_triggers: ["Evaluating alternatives", "Software recommendation"],
      },
    },
    updated_at: new Date().toISOString(),
  },
  {
    id: "icp-2",
    name: "Fintech Scaleups",
    description: "Security and compliance officers",
    status: "ACTIVE" as const,
    revision: 2,
    is_primary: false,
    related_counts: { discoveries: 1, monitors: 1 },
    criteria: {
      company: {
        industries: ["Fintech", "Cybersecurity"],
        size: ["201-500 (Scale-Up)"],
        geographies: ["Europe"],
      },
      contact: {
        job_titles: ["CISO", "Head of Compliance"],
      },
      intent: {
        pain_points: ["Audit readiness overhead"],
        buying_triggers: ["SOC 2 automation"],
      },
    },
    updated_at: new Date().toISOString(),
  },
];

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>
  );
}

describe("Ideal Customers (ICP) 2.0 Redesign", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(intelligence, "request").mockImplementation(async (path: string, options?: any) => {
      if (path.startsWith("/organization/icps?")) {
        return {
          items: mockProfiles,
          total: 2,
          can_edit: true,
        };
      }
      if (path === "/organization/icps/icp-1") {
        return mockProfiles[0];
      }
      if (path === "/organization/icps/icp-1/related") {
        return {
          icp_id: "icp-1",
          discoveries: [{ id: "d-1", title: "DevTool Search", status: "COMPLETE", created_at: new Date().toISOString() }],
          monitors: [{ id: "m-1", name: "DevTool Monitor", status: "Active", last_checked: null }],
          signals: [{ id: "s-1", title: "Looking for database alternatives", source: "Hacker News", score: 85, category: "Alternative search", observed_at: new Date().toISOString(), matched_terms: ["DevTools"] }],
        };
      }
      if (path === "/organization/icps/icp-1/versions") {
        return {
          items: [{ revision: 1, name: "Initial", description: "First version", updated_at: new Date().toISOString() }],
          total: 1,
        };
      }
      if (path === "/organization/icps/compare-profiles") {
        return {
          items: [
            {
              id: "icp-1",
              name: "Mid-Market B2B SaaS",
              status: "ACTIVE",
              is_primary: true,
              industries: ["B2B SaaS", "DevTools"],
              job_titles: ["CTO", "VP Engineering"],
              pain_points_count: 2,
              buying_signals_count: 2,
              matched_signals: 14,
              high_intent_matches: 8,
              completeness_score: 95,
              missing_fields: [],
            },
            {
              id: "icp-2",
              name: "Fintech Scaleups",
              status: "ACTIVE",
              is_primary: false,
              industries: ["Fintech"],
              job_titles: ["CISO"],
              pain_points_count: 1,
              buying_signals_count: 1,
              matched_signals: 6,
              high_intent_matches: 3,
              completeness_score: 80,
              missing_fields: ["Revenue Range"],
            },
          ],
          recommended_id: "icp-1",
          recommendation_reason: "Mid-Market B2B SaaS has 14 matched conversations and 8 high-intent evaluation signals.",
          signals_evaluated: 20,
        };
      }
      return {};
    });
  });

  it("renders ICP Dashboard with 4 KPIs and 6-column table", async () => {
    renderWithClient(<ICPDashboard />);

    expect(screen.getByRole("heading", { name: "Ideal Customers" })).toBeInTheDocument();
    expect(screen.getByText("Total ICPs")).toBeInTheDocument();
    expect(screen.getByText("Active Profiles")).toBeInTheDocument();
    expect(screen.getByText("Primary Target")).toBeInTheDocument();
    expect(screen.getAllByText("Linked Research").length).toBeGreaterThanOrEqual(1);

    const matches = await screen.findAllByText("Mid-Market B2B SaaS");
    expect(matches.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Fintech Scaleups")).toBeInTheDocument();

    // Required columns
    expect(screen.getByText("Ideal Customer Profile")).toBeInTheDocument();
    expect(screen.getByText("Target Market")).toBeInTheDocument();
    expect(screen.getByText("Buyer Roles")).toBeInTheDocument();
    expect(screen.getByText("Actions")).toBeInTheDocument();
  });

  it("renders ICP Builder with 2-panel layout and 7 sections", () => {
    renderWithClient(<ICPBuilderPage />);

    // Left Panel: AI Assistant
    expect(screen.getByText("ICP Assistant")).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/e\.g\. Focus on B2B SaaS/i)).toBeInTheDocument();

    // Right Panel: 7 Configuration Sections
    expect(screen.getByText(/1\. Basic Information/i)).toBeInTheDocument();
    expect(screen.getByText(/2\. Target Companies & Market/i)).toBeInTheDocument();
    expect(screen.getByText(/3\. Buyer Personas & Decision Makers/i)).toBeInTheDocument();
    expect(screen.getByText(/4\. Customer Problems & Pain Points/i)).toBeInTheDocument();
    expect(screen.getByText(/5\. Buying Intent & Triggers/i)).toBeInTheDocument();
    expect(screen.getByText(/6\. Exclusions & Negative Filters/i)).toBeInTheDocument();

    // Sticky Actions
    expect(screen.getByRole("button", { name: /Save as Draft/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Create ICP Profile/i })).toBeInTheDocument();
  });

  it("renders Compare ICPs page with multi-selector, recommendation callout, and dimensions table", async () => {
    renderWithClient(<ICPComparePage />);

    expect(screen.getByRole("heading", { name: "Compare Ideal Customers" })).toBeInTheDocument();
    expect(await screen.findByText("Prioritization Recommendation")).toBeInTheDocument();
    expect(screen.getByText(/Recommended to prioritize: Mid-Market B2B SaaS/i)).toBeInTheDocument();
    expect(screen.getByText("Profile Completeness")).toBeInTheDocument();
    expect(screen.getByText("Customer Problems")).toBeInTheDocument();
    expect(screen.getByText("Evidence Matches")).toBeInTheDocument();
  });

  it("renders ICP Details page with 4 tabs and related evidence", async () => {
    renderWithClient(<ICPDetailPage id="icp-1" />);

    expect(await screen.findByRole("heading", { name: "Mid-Market B2B SaaS" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Overview/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Targeting Criteria/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Linked Research & Signals/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Version History/i })).toBeInTheDocument();

    // Check overview cards
    expect(screen.getByText("Target Companies")).toBeInTheDocument();
    expect(screen.getByText("Decision Makers & Roles")).toBeInTheDocument();
    expect(screen.getByText("Customer Problems & Frustrations")).toBeInTheDocument();
    expect(screen.getByText("High-Intent Buying Signals")).toBeInTheDocument();
  });
});
