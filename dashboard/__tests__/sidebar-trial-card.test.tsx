import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { Sidebar } from "@/components/layout/sidebar";
import { TrialUsageCard } from "@/components/layout/TrialUsageCard";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  usePathname: () => "/intent-radar/monitors",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

// Mock hooks
vi.mock("@/components/workspaces/usage", () => ({
  useUsage: () => ({
    data: {
      subscription: {
        is_trial: true,
        entitlement_label: "Starter Trial",
        plan_code: "starter",
        trial_start: Math.floor(Date.now() / 1000) - 86400,
        trial_end: Math.floor(Date.now() / 1000) + 6 * 86400,
        status: "active",
      },
      usage: [
        { dimension: "plan_searches", used: 6, limit: 20 },
        { dimension: "plan_ai_calls", used: 3, limit: 50 },
      ],
    },
    isPending: false,
    isError: false,
  }),
}));

vi.mock("@/components/workspaces/use-workspace", () => ({
  useWorkspace: () => ({
    workspace: { id: "ws-1", name: "PlaneByte" },
  }),
}));

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

describe("Sidebar and Free Trial & Usage Card", () => {
  it("renders the Starter Trial card with clean styling, usage metrics, and no remaining days badge", async () => {
    renderWithClient(<TrialUsageCard />);
    expect(await screen.findByText("Starter Trial")).toBeInTheDocument();
    expect(screen.queryByText(/remaining/i)).not.toBeInTheDocument();
    expect(screen.getByText("Discovery searches")).toBeInTheDocument();
    expect(screen.getByText("6 / 20")).toBeInTheDocument();
    expect(screen.getByText("AI requests")).toBeInTheDocument();
    expect(screen.getByText("3 / 50")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Upgrade Plan/i })).toHaveAttribute(
      "href",
      "/billing"
    );
  });

  it("does NOT display Intelligence Graph in navigation", () => {
    renderWithClient(<Sidebar />);
    expect(screen.queryByText("Intelligence Graph")).not.toBeInTheDocument();
  });

  it("does NOT display 'Public conversation intelligence' footer text", () => {
    renderWithClient(<Sidebar />);
    expect(
      screen.queryByText(/Public conversation intelligence/i)
    ).not.toBeInTheDocument();
  });

  it("marks active navigation item with aria-current='page'", () => {
    renderWithClient(<Sidebar />);
    const monitoringLink = screen.getByRole("link", { name: /Monitoring/i });
    expect(monitoringLink).toHaveAttribute("aria-current", "page");
  });
});
