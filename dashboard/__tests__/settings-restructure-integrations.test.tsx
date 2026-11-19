import { describe, it, expect, vi } from "vitest";
vi.mock("server-only", () => ({}));
vi.mock("@/auth", () => ({ signIn: vi.fn(), auth: vi.fn() }));
vi.mock("@/app/account-actions", () => ({}));
vi.mock("next-auth", () => ({ default: vi.fn(), AuthError: class extends Error {} }));
vi.mock("next-auth/react", () => ({ useSession: () => ({ data: null, status: "unauthenticated" }) }));
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CustomerIntegrationsCatalog } from "@/components/intent-radar/integrations/CustomerIntegrationsCatalog";
import { SETTINGS_CATEGORIES, resolveSettingsCategory } from "@/components/settings/unified-settings-center";
import { HELP_CATEGORIES, HELP_CATEGORY_METAS, HELP_ARTICLES } from "@/lib/help-articles";
import { Sidebar } from "@/components/layout/sidebar";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  usePathname: () => "/intent-radar/integrations",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
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

vi.mock("@/components/workspaces/features", () => ({
  useWorkspaceCapabilities: () => ({
    data: { can_manage: true, can_write: true },
  }),
  useWorkspaceManagement: () => ({
    canManage: true,
    canWrite: true,
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

describe("Settings Restructuring & Customer Integrations (Master Prompt 10)", () => {
  it("defines the exact 8 required settings categories in logical order", () => {
    const keys = SETTINGS_CATEGORIES.map((c) => c.key);
    expect(keys).toEqual([
      "account",
      "company",
      "team",
      "preferences",
      "notifications",
      "sources",
      "developer",
      "billing",
    ]);

    const labels = SETTINGS_CATEGORIES.map((c) => c.label);
    expect(labels).toContain("Sources & Tools");
    expect(labels).toContain("Developer & API");
    expect(labels).toContain("Notifications");
    expect(labels).toContain("Research Preferences");
  });

  it("resolves legacy settings deep links and category redirects correctly", () => {
    // Legacy ?category=integrations -> sources
    const res1 = resolveSettingsCategory("integrations", undefined);
    expect(res1.category).toBe("sources");
    expect(res1.tab).toBe("sources");

    // Legacy ?category=integrations&tab=developer -> developer
    const res2 = resolveSettingsCategory("integrations", "developer");
    expect(res2.category).toBe("developer");
    expect(res2.tab).toBe("keys");

    // Legacy ?category=preferences&tab=notifications -> notifications
    const res3 = resolveSettingsCategory("preferences", "notifications");
    expect(res3.category).toBe("notifications");
    expect(res3.tab).toBe("channels");

    // Standard sources & tools
    const res4 = resolveSettingsCategory("sources", "feeds");
    expect(res4.category).toBe("sources");
    expect(res4.tab).toBe("feeds");
  });

  it("renders the Customer-Facing Integrations catalog with categories and search", () => {
    renderWithClient(<CustomerIntegrationsCatalog />);
    
    // Header & description
    expect(screen.getByRole("heading", { name: "Integrations" })).toBeInTheDocument();
    expect(screen.getByText(/Connect your favorite tools and bring Intent Radar insights/i)).toBeInTheDocument();

    // Category filter tabs
    expect(screen.getByRole("tab", { name: /All Integrations/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /CRM/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Spreadsheets/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Automation/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Collaboration/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Developer Tools/i })).toBeInTheDocument();

    // Key integrations present
    expect(screen.getByText("HubSpot")).toBeInTheDocument();
    expect(screen.getByText("Salesforce")).toBeInTheDocument();
    expect(screen.getByText("Google Sheets")).toBeInTheDocument();
    expect(screen.getByText("Slack")).toBeInTheDocument();
    expect(screen.getByText("Zapier")).toBeInTheDocument();
    expect(screen.getByText("REST API")).toBeInTheDocument();

    // Truthful statuses: Unbuilt integrations have "Coming Soon" badges
    const comingSoonBadges = screen.getAllByText("Coming Soon");
    expect(comingSoonBadges.length).toBeGreaterThanOrEqual(10);

    // Filter by CRM
    fireEvent.click(screen.getByRole("tab", { name: /CRM/i }));
    expect(screen.getByText("HubSpot")).toBeInTheDocument();
    expect(screen.getByText("Salesforce")).toBeInTheDocument();
    expect(screen.getByText("Pipedrive")).toBeInTheDocument();
    expect(screen.getByText("Zoho CRM")).toBeInTheDocument();
    expect(screen.getByText("Freshsales")).toBeInTheDocument();
    expect(screen.queryByText("Google Sheets")).not.toBeInTheDocument();
  });

  it("includes Integrations in the sidebar navigation under Intelligence", () => {
    renderWithClient(<Sidebar />);
    expect(screen.getByRole("link", { name: /Integrations/i })).toHaveAttribute(
      "href",
      "/intent-radar/integrations"
    );
  });

  it("has exactly 10 Help Center categories with valid article mappings", () => {
    expect(HELP_CATEGORIES.length).toBe(10);
    expect(HELP_CATEGORY_METAS.length).toBe(10);

    const categoryNames = HELP_CATEGORIES;
    expect(categoryNames).toContain("Getting Started");
    expect(categoryNames).toContain("Discover & Research");
    expect(categoryNames).toContain("Signals & Opportunities");
    expect(categoryNames).toContain("Monitoring & Alerts");
    expect(categoryNames).toContain("AI Assistant & ICPs");
    expect(categoryNames).toContain("Sources & Integrations");
    expect(categoryNames).toContain("Developer & API");
    expect(categoryNames).toContain("Billing & Subscriptions");
    expect(categoryNames).toContain("Team & Security");
    expect(categoryNames).toContain("Troubleshooting");

    // All articles belong to valid categories
    for (const article of HELP_ARTICLES) {
      expect(HELP_CATEGORIES).toContain(article.category);
    }
  });
});
