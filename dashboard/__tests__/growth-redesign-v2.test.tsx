import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { expect, it, vi, describe } from "vitest";
import React from "react";
import { GrowthExperience } from "@/components/intent-radar/growth-experience";
import { GrowthOverviewDashboard } from "@/components/intent-radar/growth/GrowthOverviewDashboard";
import { GrowthThemesPage } from "@/components/intent-radar/growth/GrowthThemesPage";
import { GrowthCompetitorsPage } from "@/components/intent-radar/growth/GrowthCompetitorsPage";
import { GrowthResearchWorkspace } from "@/components/intent-radar/growth/GrowthResearchWorkspace";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
  useSearchParams: () => new URLSearchParams(),
}));

const mockOverviewData = {
  sample_size: 42,
  monitored_topics: 5,
  opportunity_candidates: 12,
  theme_count: 8,
  themes: [
    {
      id: "theme-1",
      name: "CRM Dissatisfaction & Migration",
      description: "Users looking for lightweight alternatives to HubSpot and Salesforce.",
      method: "FREQUENCY",
      saved_at: "2026-11-18T10:00:00Z",
      revision: 1,
      citations: [
        {
          signal_id: "sig-1",
          quote: "Looking for an affordable CRM alternative for a team of 10.",
          signal: {
            source: "hacker_news",
            source_url: "https://news.ycombinator.com/item?id=123",
          },
        },
      ],
      comparison: {
        state: "Comparable collection windows",
        current: 24,
        previous: 18,
        percentage_change: 33,
      },
    },
  ],
  sources: { hacker_news: 28, github: 14 },
  categories: { "Software Recommendation": 30, "Alternative Seeking": 12 },
  daily: [
    { day: "2026-11-18", conversations: 15 },
    { day: "2026-11-19", conversations: 27 },
  ],
  comparison: {
    state: "Comparable collection windows",
    current: 42,
    previous: 30,
    percentage_change: 40,
    market_trend_proven: false,
  },
  coverage: {
    comparable: true,
    windows_supported: { "7": true, "30": true, "90": false },
    source_errors: false,
    truncated: false,
    duplicates_excluded: 2,
    current_checks: 10,
    previous_checks: 10,
    scope: "Workspace evidence",
    collection_started_at: "2026-11-01T00:00:00Z",
  },
  as_of: "2026-11-19T10:00:00Z",
  freshest_evidence: "2026-11-19T09:30:00Z",
  signals: [
    {
      id: "sig-1",
      title: "Ask HN: What CRM are you using in 2026?",
      excerpt: "Looking for an affordable CRM alternative for a team of 10.",
      source: "hacker_news",
      source_url: "https://news.ycombinator.com/item?id=123",
      observed_at: "2026-11-19T08:00:00Z",
      retrieved_at: "2026-11-19T08:05:00Z",
      score: 92,
      category: "Software Recommendation",
    },
  ],
  filter_options: {
    icps: [{ id: "icp-1", name: "B2B SaaS Founders" }],
    competitors: [{ id: "comp-1", name: "HubSpot" }],
  },
  geography: "Global",
};

vi.mock("@/components/intent-radar/provider", () => ({
  useRadarRead: (url: string) => {
    if (url.includes("/growth/overview")) {
      return { data: mockOverviewData, isFetching: false, refetch: vi.fn() };
    }
    if (url.includes("/growth/themes")) {
      return {
        data: {
          items: mockOverviewData.themes,
          total: 1,
          page: 1,
          page_size: 25,
        },
        isLoading: false,
        refetch: vi.fn(),
      };
    }
    if (url.includes("/growth/competitors")) {
      return {
        data: {
          items: [
            {
              id: "comp-1",
              name: "Acme CRM",
              aliases: ["acme", "acmecrm"],
              context: "Legacy tool with high seat prices.",
              revision: 1,
              archived_at: null,
            },
          ],
        },
        isLoading: false,
        refetch: vi.fn(),
      };
    }
    if (url.includes("/growth/research")) {
      return {
        data: {
          items: [
            {
              id: "res-1",
              title: "Market overview & demand",
              question: "What are common CRM pain points?",
              kind: "REPORT",
              status: "COMPLETED",
              created_at: "2026-11-19T10:00:00Z",
              saved_at: null,
              revision: 1,
            },
          ],
          total: 1,
          page: 1,
          page_size: 25,
        },
        isLoading: false,
        refetch: vi.fn(),
      };
    }
    return { data: null, isLoading: false };
  },
  useRadarCapabilities: () => ({
    data: {
      can_write: true,
      can_manage: true,
      growth_enabled: true,
      sources: [{ id: "hacker_news", name: "Hacker News" }],
    },
  }),
  useRadarMutation: () => ({
    mutate: vi.fn(),
    mutateAsync: vi.fn().mockResolvedValue({ id: "res-1" }),
    isPending: false,
  }),
}));

describe("Growth Intelligence 2.0 Module", () => {
  it("renders 4 primary tabs: Overview, Trends & Themes, Competitor Intelligence, AI Research", () => {
    render(<GrowthExperience route="growth" />);

    expect(screen.getByRole("link", { name: /Overview/i })).toBeVisible();
    expect(screen.getByRole("link", { name: /Trends & Themes/i })).toBeVisible();
    expect(screen.getByRole("link", { name: /Competitor Intelligence/i })).toBeVisible();
    expect(screen.getByRole("link", { name: /AI Research/i })).toBeVisible();
  });

  it("displays 4 KPI metric cards and conversation timeline on Overview", () => {
    render(<GrowthOverviewDashboard onNavigateTab={vi.fn()} />);

    expect(screen.getByText("Conversations Analyzed")).toBeVisible();
    expect(screen.getAllByText("42")[0]).toBeVisible();

    expect(screen.getByText("Active Recurring Themes")).toBeVisible();
    expect(screen.getByText("8")).toBeVisible();

    expect(screen.getByText("Monitored Topics")).toBeVisible();
    expect(screen.getByText("5")).toBeVisible();

    expect(screen.getByText("Emerging Opportunities")).toBeVisible();
    expect(screen.getByText("12")).toBeVisible();
  });

  it("renders themes table with citations and monitor shortcuts", () => {
    render(<GrowthThemesPage onNavigateTab={vi.fn()} />);

    expect(screen.getByText("CRM Dissatisfaction & Migration")).toBeVisible();
    expect(screen.getByText("1 citations")).toBeVisible();
    expect(screen.getByRole("link", { name: /Monitor/i })).toBeVisible();
  });

  it("renders competitor intelligence with tracked competitors and aliases", () => {
    render(<GrowthCompetitorsPage onNavigateTab={vi.fn()} />);

    expect(screen.getByText("Acme CRM")).toBeVisible();
    expect(screen.getByText("acme")).toBeVisible();
    expect(screen.getByText("acmecrm")).toBeVisible();
    expect(screen.getByRole("button", { name: /Add Competitor/i })).toBeVisible();
  });

  it("renders persistent AI Research Assistant and reports workspace", () => {
    render(<GrowthResearchWorkspace onNavigateTab={vi.fn()} />);

    expect(screen.getByRole("region", { name: /AI Research Composer/i })).toBeVisible();
    expect(screen.getByRole("button", { name: /Generate Research/i })).toBeVisible();
    expect(screen.getByText("Market overview & demand")).toBeVisible();
  });
});
