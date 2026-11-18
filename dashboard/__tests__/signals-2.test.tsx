import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { SignalsWorkspace } from "@/components/intent-radar/signal-workspace";
import { EvidenceDetail } from "@/components/intent-radar/evidence-experience";
import { saveSignalsReturnContext } from "@/components/intent-radar/signals/signals-context";
import type { IntentSignal } from "@/lib/intent-radar";

const mocks = vi.hoisted(() => ({
  push: vi.fn(),
  mutateAsync: vi.fn(),
  mutate: vi.fn(),
  searchParams: new URLSearchParams(),
  signals: [] as IntentSignal[],
  signalsError: null as Error | null,
  analysisHistory: { items: [] as unknown[], feedback: { items: [], ranking_adjustment: 0 } },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mocks.push }),
  useSearchParams: () => mocks.searchParams,
}));

vi.mock("@/components/intent-radar/provider", () => ({
  useRadarMutation: () => ({
    mutateAsync: mocks.mutateAsync,
    mutate: mocks.mutate,
    isPending: false,
  }),
  useRadarCapabilities: () => ({
    data: {
      can_write: true,
      can_manage: true,
      sources: [
        { id: "hacker_news", name: "Hacker News", state: "Available", coverage: "Official v0 API" },
        { id: "github", name: "GitHub", state: "Connected", coverage: "GitHub App REST & GraphQL" },
      ],
    },
  }),
  useRadarRead: (path: string) => {
    if (path === "/settings") {
      return {
        data: { default_view: "table", min_relevance: 0, topics: [], alerts_enabled: true, alert_threshold: 85, revision: 1 },
      };
    }
    if (path.startsWith("/monitors")) {
      return { data: { items: [{ id: "mon-1", name: "GitHub CRM Monitor" }], total: 1, page: 1, page_size: 100 } };
    }
    if (path === "/icps") {
      return { data: { items: [{ id: "icp-1", name: "B2B SaaS Founders" }] } };
    }
    if (path.startsWith("/signals?")) {
      if (mocks.signalsError) {
        return {
          data: undefined,
          error: mocks.signalsError,
          refetch: vi.fn(),
        };
      }
      return {
        data: {
          items: mocks.signals,
          total: mocks.signals.length,
          page: 1,
          page_size: 25,
          has_more: false,
          view_counts: {
            all: 2,
            needs_review: 1,
            high_intent: 1,
            saved: 1,
            qualified: 1,
            dismissed: 0,
          },
        },
        refetch: vi.fn(),
      };
    }
    if (path.endsWith("/analysis")) {
      return { data: mocks.analysisHistory, refetch: vi.fn() };
    }
    if (path.startsWith("/signals/")) {
      const id = path.replace("/signals/", "");
      const found = mocks.signals.find((s) => s.id === id) || mocks.signals[0];
      return { data: found, refetch: vi.fn() };
    }
    return { data: undefined, refetch: vi.fn() };
  },
}));

const SAMPLE_SIGNALS: IntentSignal[] = [
  {
    id: "sig-1",
    title: "Looking for a B2B CRM alternative with webhook sync",
    source: "GitHub",
    source_url: "https://github.com/planebytelabs/demo/issues/1",
    excerpt: "We are comparing CRM software platforms to replace our legacy sync pipeline.",
    observed_at: "2026-11-17T10:00:00Z",
    retrieved_at: "2026-11-17T10:05:00Z",
    category: "Alternative search",
    score: 89,
    status: "New",
    notes: "",
    revision: 1,
    available: 1,
    saved: false,
    buying_intent: null,
    buying_intent_basis: "unassessed",
    icp_fit: "Unassessed",
    has_analysis: false,
    opportunity_id: null,
    opportunity_status: null,
    opportunity_eligibility: {
      eligible: true,
      intent_quote: "comparing CRM software platforms to replace our legacy sync",
      reasons: [],
      basis: "Observed request plus targeting alignment.",
      next_step: "Review the original request and unknowns.",
      policy_version: "OPPORTUNITY_EVIDENCE_V1",
    },
    evidence: {
      matched_keywords: ["crm", "webhook"],
      matched_topics: ["automation"],
      intent_phrase: "looking for",
      confidence: "Strong evidence",
      explanation: "Matched crm, webhook and explicit evaluation phrase.",
      observed_text: "We are comparing CRM software platforms.",
      unknown: ["Budget", "Purchase authority"],
      purchasing_event_verified: false,
      provenance: {
        fetch_method: "github_webhook",
        content_kind: "issue",
        repo: "planebytelabs/demo",
        attribution: { author: "buyer_alice", source: "GitHub" },
      },
    },
    monitors: [{ id: "mon-1", name: "GitHub CRM Monitor" }],
    activity: [
      { kind: "collected", title: "Collected from GitHub", detail: "Via github webhook · planebytelabs/demo", actor: null, at: "2026-11-17T10:05:00Z" },
    ],
  },
  {
    id: "sig-2",
    title: "Next.js v16.5.0 technical release announcement",
    source: "Hacker News",
    source_url: "https://news.ycombinator.com/item?id=999002",
    excerpt: "Release notes for bundler speed improvements.",
    observed_at: "2026-11-16T08:00:00Z",
    retrieved_at: "2026-11-16T08:05:00Z",
    category: "Market / technology intelligence",
    score: 62,
    status: "Qualified",
    notes: "Track release cadence",
    revision: 2,
    available: 1,
    saved: true,
    buying_intent: "No demonstrated commercial intent",
    buying_intent_basis: "ai_assessed",
    icp_fit: "Unassessed",
    has_analysis: true,
    latest_analysis_summary: "Technical framework release notes with no commercial purchase request.",
    opportunity_id: "opp-existing-1",
    opportunity_status: "Reviewing",
    opportunity_eligibility: {
      eligible: false,
      intent_quote: null,
      reasons: ["Technical releases are market/technology intelligence, not buyer opportunities."],
      basis: "Observed text only.",
      next_step: "Keep as a signal or saved research.",
      policy_version: "OPPORTUNITY_EVIDENCE_V1",
    },
    evidence: {
      matched_keywords: ["nextjs"],
      matched_topics: [],
      intent_phrase: null,
      confidence: "Market / tech intelligence",
      explanation: "Matched nextjs in a technical release.",
      observed_text: "Release notes for bundler speed improvements.",
      unknown: ["Identity"],
      purchasing_event_verified: false,
      provenance: { fetch_method: "official_hn", content_kind: "release" },
    },
    monitors: [],
    activity: [],
  },
];

describe("Signals 2.0 Workspace & Full Signal Details", () => {
  beforeEach(() => {
    mocks.push.mockReset();
    mocks.mutateAsync.mockReset().mockResolvedValue({});
    mocks.mutate.mockReset();
    mocks.searchParams = new URLSearchParams();
    mocks.signals = SAMPLE_SIGNALS;
    mocks.analysisHistory = { items: [], feedback: { items: [], ranking_adjustment: 0 } };
    window.sessionStorage.clear();
  });

  it("renders Saved View tabs with counts, truthful unassessed Buying Intent, Filters popover, and Quick Review Drawer", async () => {
    render(<SignalsWorkspace />);

    expect(screen.getByRole("tab", { name: /All Signals/i })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: /Needs Review/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /High Intent/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Qualified/i })).toBeInTheDocument();

    // Unanalyzed signal shows truthful "Not assessed"; analyzed shows "Non-commercial"
    expect(screen.getByText("Not assessed")).toBeInTheDocument();
    expect(screen.getByText("Non-commercial")).toBeInTheDocument();

    // Open Filters popover and select a source -> renders active filter chip + Clear all
    fireEvent.click(screen.getByRole("button", { name: /Filters/i }));
    fireEvent.change(screen.getByLabelText("Filter by source"), { target: { value: "GitHub" } });
    expect(screen.getByLabelText("Active filters")).toHaveTextContent("Source: GitHub");
    fireEvent.click(screen.getByRole("button", { name: /Clear all filters/i }));
    expect(screen.queryByLabelText("Active filters")).not.toBeInTheDocument();

    // Select a row -> unambiguous "1 selected on this page" bulk bar + confirmation for Dismiss
    fireEvent.click(screen.getByLabelText("Select Looking for a B2B CRM alternative with webhook sync"));
    expect(screen.getByText(/1 selected on this page/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /^Dismiss$/i }));
    expect(screen.getByText(/Confirm dismissing 1 signal/i)).toBeInTheDocument();

    // Click row title -> opens spacious Quick Review Drawer with Open Full Details link
    fireEvent.click(screen.getAllByText("Looking for a B2B CRM alternative with webhook sync")[0]);
    const drawer = await screen.findByRole("dialog", { name: /Quick signal review/i });
    expect(drawer).toHaveTextContent("Open Full Details");
    expect(drawer).toHaveTextContent("planebytelabs/demo");

    // Pressing Escape closes the Quick Review Drawer
    fireEvent.keyDown(window, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog", { name: /Quick signal review/i })).not.toBeInTheDocument());
  });

  it("renders Full Signal Details with Back-to-Signals restoration, Prev/Next, ONE Analyze Signal CTA, feedback, and editable Opportunity modal", async () => {
    saveSignalsReturnContext({
      returnUrl: "/intent-radar/signals?view=high_intent&sort=score",
      scrollY: 240,
      orderedIds: ["sig-1", "sig-2"],
    });

    render(<EvidenceDetail id="sig-1" />);

    // Back to Signals restores exact prior filter URL
    const backLink = screen.getByRole("link", { name: /Back to Signals/i });
    expect(backLink).toHaveAttribute("href", "/intent-radar/signals?view=high_intent&sort=score");

    // Prev is disabled on first item; Next navigates to sig-2
    expect(screen.getByRole("button", { name: /Previous Signal/i })).toBeDisabled();
    const nextBtn = screen.getByRole("button", { name: /Next Signal/i });
    expect(nextBtn).toBeEnabled();
    fireEvent.click(nextBtn);
    expect(mocks.push).toHaveBeenCalledWith("/intent-radar/signals/sig-2");

    // ONE clear primary AI action ("Analyze Signal"); Translate is tucked behind secondary toggle
    expect(screen.getByRole("button", { name: /^Analyze Signal$/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Run with translation/i })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Translate/i }));
    expect(screen.getByRole("button", { name: /Run with translation/i })).toBeInTheDocument();

    // Reviewer relevance feedback ("Was this signal relevant?")
    fireEvent.click(screen.getByRole("button", { name: /^Relevant$/i }));
    await waitFor(() =>
      expect(mocks.mutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          path: "/signals/sig-1/feedback",
          method: "PUT",
          body: expect.objectContaining({ label: "Relevant", active: true }),
        })
      )
    );

    // Open Create Opportunity modal -> readiness check + editable form submit
    fireEvent.click(screen.getByRole("button", { name: /Create Opportunity/i }));
    expect(await screen.findByText(/Opportunity readiness check passed/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Confirm & Create Opportunity/i }));
    await waitFor(() =>
      expect(mocks.mutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          path: "/opportunities/sig-1",
          method: "POST",
          body: expect.objectContaining({ priority: "High" }),
        })
      )
    );
  });

  it("prevents duplicate Opportunity creation when signal already has a linked opportunity", async () => {
    render(<EvidenceDetail id="sig-2" />);
    fireEvent.click(screen.getByRole("button", { name: /View Opportunity/i }));
    expect(await screen.findByText(/An opportunity already exists for this signal/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open Opportunity/i })).toHaveAttribute(
      "href",
      "/intent-radar/opportunities/opp-existing-1"
    );
  });

  it("never displays 0 matching signals when the signals API request fails", () => {
    mocks.signalsError = new Error("The engine could not complete this request. Please retry.");
    try {
      render(<SignalsWorkspace />);
      expect(screen.queryByText("0 matching signals")).not.toBeInTheDocument();
      expect(screen.getByText(/Could not load signals/i)).toBeInTheDocument();
      expect(screen.getByText(/The engine could not complete this request/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Try again/i })).toBeInTheDocument();
    } finally {
      mocks.signalsError = null;
    }
  });
});
