import React from "react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { resolveRadarToast } from "@/lib/action-toast";

const pushMock = vi.fn();
const replaceMock = vi.fn();

vi.mock("next/navigation", () => ({
  usePathname: () => "/intelligence/assistant",
  useRouter: () => ({ push: pushMock, replace: replaceMock }),
  useSearchParams: () => new URLSearchParams(""),
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}));

vi.mock("@/components/workspaces/use-workspace", () => ({
  useWorkspace: () => ({
    active: { id: "org-1", name: "PlaneByte", role: "OWNER" },
    data: { active_organization_id: "org-1", workspaces: [{ id: "org-1", name: "PlaneByte", role: "OWNER" }] },
  }),
}));

vi.mock("@/components/workspaces/use-products", () => ({
  useProducts: () => ({
    data: {
      intent_radar: { enabled: true, growth_enabled: true },
      lead_engine: false,
    },
  }),
}));

vi.mock("@/components/workspaces/switcher", () => ({
  WorkspaceSwitcher: () => <div data-testid="workspace-switcher" />,
}));

vi.mock("@/components/layout/account-menu", () => ({
  AccountMenu: () => <div data-testid="account-menu" />,
}));

import { Shell } from "@/components/layout/shell";
import { AssistantPageClient } from "@/components/intelligence/AssistantPageClient";
import { Notifications } from "@/components/layout/notifications";

function withQueryClient(ui: React.ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe("Action-aware toast messages", () => {
  it("never returns the generic Intent Radar updated string", () => {
    const cases: [string, string, Record<string, unknown> | undefined, string][] = [
      ["/discover", "POST", undefined, "Discovery started"],
      ["/monitors", "POST", undefined, "Monitor created"],
      ["/monitors/123", "PUT", { status: "Paused" }, "Monitor paused"],
      ["/signals/abc/save", "POST", undefined, "Research Library"],
      ["/signals/abc/review", "POST", { status: "Qualified" }, "Qualified"],
      ["/custom-feeds/1", "DELETE", undefined, "Custom feed removed"],
      ["/saved-searches", "POST", undefined, "reusable templates"],
    ];
    for (const [path, method, payload, expected] of cases) {
      const msg = resolveRadarToast(path, method, payload);
      expect(msg).not.toBe("Intent Radar updated.");
      expect(msg.toLowerCase()).toContain(expected.toLowerCase());
    }
  });
});

describe("Global Shell, Navigation & Retired Floating AI Popup", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/organization/notifications")) {
          return new Response(
            JSON.stringify({
              items: [
                {
                  id: "n-1",
                  kind: "DISCOVERY_COMPLETED",
                  category: "discovery",
                  priority: "high",
                  title: "Discovery completed (12 signals)",
                  description: "Found 12 matching discussions.",
                  url: "/intent-radar/discover/runs/run-1",
                  read_at: null,
                  created_at: new Date().toISOString(),
                },
              ],
              unread_count: 1,
              total: 1,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } },
          );
        }
        return new Response(JSON.stringify({ items: [] }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }),
    );
  });

  it("renders top navbar AI Assistant icon, Ideal Customers in Intelligence sidebar, and NO floating popup button", async () => {
    withQueryClient(
      <Shell workspaceManagementEnabled={false} capabilities={{ leadEngineAvailable: false, companyDiscovery: false }}>
        <div>Workspace Content</div>
      </Shell>,
    );

    // Top navbar AI Assistant icon points to /intelligence/assistant
    const aiLinks = screen.getAllByRole("link", { name: "AI Assistant" });
    expect(aiLinks.length).toBe(1);
    expect(aiLinks[0].getAttribute("href")).toBe("/intelligence/assistant");

    // Ideal Customers exists under sidebar navigation
    const icpLinks = screen.getAllByRole("link", { name: "Ideal Customers" });
    expect(icpLinks.length).toBeGreaterThanOrEqual(1);
    expect(icpLinks[0].getAttribute("href")).toBe("/intent-radar/ideal-customers");

    // No floating popup button exists anywhere in the DOM
    expect(screen.queryByRole("button", { name: /open intelligence assistant/i })).toBeNull();
    expect(screen.queryByText(/ask intelligence assistant/i)).toBeNull();
  });

  it("renders functional Notification Bell dropdown with unread count and View all notifications link", async () => {
    withQueryClient(<Notifications />);
    const bell = await screen.findByRole("button", { name: /notifications/i });
    await waitFor(() => expect(bell.textContent).toContain("1"));

    fireEvent.pointerDown(bell, { button: 0, ctrlKey: false });
    fireEvent.click(bell);
    expect(await screen.findByText("Discovery completed (12 signals)")).toBeTruthy();
    const viewAll = screen.getByRole("link", { name: /view all notifications/i });
    expect(viewAll.getAttribute("href")).toBe("/notifications");
  });
});

describe("Full-Page AI Assistant UI", () => {
  beforeEach(() => {
    window.HTMLElement.prototype.scrollIntoView = vi.fn();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/intent-radar/assistant/conversations")) {
          return new Response(JSON.stringify({ items: [] }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }
        if (url.includes("/intent-radar/assistant/chat")) {
          const encoder = new TextEncoder();
          const ssePayload = [
            `event: status\ndata: ${JSON.stringify({ step: "planning", label: "Checking workspace…", thread_id: "t-1" })}\n\n`,
            `event: tool_start\ndata: ${JSON.stringify({ tool: "get_workspace_summary", label: "Workspace overview" })}\n\n`,
            `event: tool_done\ndata: ${JSON.stringify({ tool: "get_workspace_summary", label: "Workspace overview", status: "completed" })}\n\n`,
            `event: proposals\ndata: ${JSON.stringify({
              proposals: [
                {
                  action_id: "act-1",
                  tool: "create_monitor",
                  title: 'Create monitor "HubSpot Alternatives"',
                  description: "Creates an Active monitor.",
                  quota_note: "Uses 1 active monitor slot.",
                  status: "pending",
                  params: { name: "HubSpot Alternatives" },
                },
              ],
            })}\n\n`,
            `event: delta\ndata: ${JSON.stringify({ text: "### Workspace Summary\nYou have **12 active signals**." })}\n\n`,
            `event: followups\ndata: ${JSON.stringify({ followups: ["Compare my ICPs", "Check remaining quota"] })}\n\n`,
            `event: done\ndata: ${JSON.stringify({
              message: {
                id: "m-1",
                thread_id: "t-1",
                question: "Summarize workspace",
                status: "COMPLETE",
                created_at: new Date().toISOString(),
                markdown: "### Workspace Summary\nYou have **12 active signals**.",
                tool_calls: [{ tool: "get_workspace_summary", label: "Workspace overview", status: "completed" }],
                cards: [],
                proposals: [
                  {
                    action_id: "act-1",
                    tool: "create_monitor",
                    title: 'Create monitor "HubSpot Alternatives"',
                    description: "Creates an Active monitor.",
                    quota_note: "Uses 1 active monitor slot.",
                    status: "pending",
                    params: { name: "HubSpot Alternatives" },
                  },
                ],
                followups: ["Compare my ICPs", "Check remaining quota"],
                citations: [],
                limitations: ["0 AI operations used."],
                mode: "Workspace data — no AI used",
              },
            })}\n\n`,
          ].join("");
          const stream = new ReadableStream({
            start(controller) {
              controller.enqueue(encoder.encode(ssePayload));
              controller.close();
            },
          });
          return new Response(stream, {
            status: 200,
            headers: { "Content-Type": "text/event-stream" },
          });
        }
        if (url.includes("/intent-radar/assistant/actions/act-1/execute")) {
          return new Response(
            JSON.stringify({
              action_id: "act-1",
              status: "executed",
              result: { summary: "Created active monitor 'HubSpot Alternatives'.", resource_url: "/intent-radar/monitors" },
            }),
            { status: 200, headers: { "Content-Type": "application/json" } },
          );
        }
        return new Response(JSON.stringify({ items: [] }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }),
    );
  });

  it("streams response, shows tool pills, action approval card, executes on approval, and renders clickable follow-ups", async () => {
    withQueryClient(<AssistantPageClient />);

    expect(screen.getByText("How can I help with your workspace?")).toBeTruthy();

    const starter = screen.getByText("Workspace daily briefing");
    fireEvent.click(starter);

    await waitFor(() => expect(screen.getByText(/12 active signals/i)).toBeTruthy());
    expect(screen.getByText("Workspace overview")).toBeTruthy();
    expect(screen.getByText("Compare my ICPs")).toBeTruthy();
    expect(screen.getByText("Check remaining quota")).toBeTruthy();

    const approveBtn = screen.getByRole("button", { name: /approve & execute/i });
    fireEvent.click(approveBtn);

    await waitFor(() =>
      expect(screen.getByText("Created active monitor 'HubSpot Alternatives'.")).toBeTruthy(),
    );
  });
});
