import { render, screen, fireEvent, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Header, getBreadcrumbs } from "@/components/layout/header";
import { QuickSearchTrigger } from "@/components/layout/quick-search";
import {
  WorkspaceLoadingState,
  WorkspaceErrorState,
} from "@/components/ui/workspace-loading-state";

let mockPathname = "/intent-radar/monitors";

vi.mock("next/navigation", () => ({
  usePathname: () => mockPathname,
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
  }),
}));

vi.mock("@/components/workspaces/use-workspace", () => ({
  useWorkspace: () => ({
    data: {
      active_organization_id: "org-1",
      items: [{ organization_id: "org-1", name: "Test Org" }],
    },
    active: { organization_id: "org-1", name: "Test Org" },
    isPending: false,
    isError: false,
  }),
  initials: (n: string) => n.slice(0, 2),
}));

vi.mock("@/components/workspaces/use-products", () => ({
  useProducts: () => ({
    data: {
      intent_radar: { enabled: true, growth_enabled: true },
    },
  }),
}));

vi.mock("@/lib/intelligence", () => ({
  request: vi.fn().mockResolvedValue({
    query: "",
    organization_id: "org-1",
    radar_enabled: true,
    growth_enabled: true,
    groups: {},
    partial_errors: [],
  }),
}));

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );
}

describe("Header Navbar and Breadcrumb Redesign", () => {
  beforeEach(() => {
    mockPathname = "/intent-radar/monitors";
  });

  it("does NOT display duplicate 'PlaneByte ›' text branding in navbar", () => {
    renderWithClient(<Header />);
    expect(screen.queryByText(/PlaneByte ›/i)).not.toBeInTheDocument();
  });

  it("renders lightweight breadcrumbs for Intent Radar routes", () => {
    mockPathname = "/intent-radar/monitors";
    const crumbs = getBreadcrumbs(mockPathname);
    expect(crumbs).toHaveLength(2);
    expect(crumbs[0].title).toBe("Intent Radar");
    expect(crumbs[1].title).toBe("Monitoring");
  });

  it("generates correct nested breadcrumbs for create monitor", () => {
    mockPathname = "/intent-radar/monitors/new";
    const crumbs = getBreadcrumbs(mockPathname);
    expect(crumbs).toHaveLength(3);
    expect(crumbs[0].title).toBe("Intent Radar");
    expect(crumbs[1].title).toBe("Monitoring");
    expect(crumbs[2].title).toBe("Create Monitor");
  });

  it("renders wide global search trigger with ⌘K badge", () => {
    renderWithClient(<Header />);
    const searchTrigger = screen.getAllByLabelText(/Universal search/i)[0];
    expect(searchTrigger).toBeInTheDocument();
    expect(screen.getAllByText("⌘K")[0]).toBeInTheDocument();
  });
});

describe("Command Center QuickSearch", () => {
  it("opens modal and displays Quick Actions when input is empty", () => {
    renderWithClient(<QuickSearchTrigger />);
    const trigger = screen.getAllByLabelText(/Universal search/i)[0];
    fireEvent.click(trigger);

    expect(screen.getByText("Quick Actions")).toBeInTheDocument();
    expect(screen.getByText("New Discovery")).toBeInTheDocument();
    expect(screen.getByText("Create Monitor")).toBeInTheDocument();
    expect(screen.getByText("Explore Signals")).toBeInTheDocument();
    expect(screen.getByText("View Opportunities")).toBeInTheDocument();
  });

  it("does not show 'Workspace data search failed (Sign in to continue)' error banner", () => {
    renderWithClient(<QuickSearchTrigger />);
    const trigger = screen.getAllByLabelText(/Universal search/i)[0];
    fireEvent.click(trigger);

    expect(
      screen.queryByText(/Workspace data search failed/i)
    ).not.toBeInTheDocument();
  });
});

describe("WorkspaceLoadingState & WorkspaceErrorState", () => {
  it("renders centered loading spinner and text", () => {
    render(<WorkspaceLoadingState />);
    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(screen.getByText("Loading your workspace")).toBeInTheDocument();
    expect(
      screen.getByText("Preparing your workspace and account settings…")
    ).toBeInTheDocument();
  });

  it("renders centered error card with retry action", async () => {
    const onRetry = vi.fn();
    render(
      <WorkspaceErrorState
        error="Network timeout"
        onRetry={onRetry}
      />
    );
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("Unable to load your workspace")).toBeInTheDocument();
    expect(screen.getByText("Network timeout")).toBeInTheDocument();

    const retryBtn = screen.getByRole("button", { name: /Retry loading/i });
    await act(async () => {
      fireEvent.click(retryBtn);
    });
    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});
