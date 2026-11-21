import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CommandCentre } from "@/components/intent-radar/command-centre";
import { SafeMarkdown } from "@/components/ui/safe-markdown";
import { WorkspacesManager } from "@/components/workspaces/workspaces-manager";
import { TeamSection } from "@/components/settings/sections/team-section";
import { DomainSettings } from "@/components/workspaces/domains";
import { AccessSettings } from "@/components/workspaces/access-settings";
import { request } from "@/lib/intelligence";

vi.mock("@/lib/intelligence", () => ({ request: vi.fn() }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => "/intent-radar",
}));
vi.mock("@/components/intent-radar/provider", () => ({
  useRadarCapabilities: () => ({
    data: { growth_enabled: true, can_write: true },
  }),
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
});

describe("Production Stabilization & Dashboard 3.0", () => {
  it("renders the Discovery Launchpad without the broken inline AI prompt", () => {
    wrap(<CommandCentre />);
    expect(
      screen.getByRole("heading", { name: "Find your next opportunity." }),
    ).toBeVisible();
    expect(
      screen.getByRole("link", { name: /Discover Intent/i }),
    ).toHaveAttribute("href", "/intent-radar/discover");
    expect(
      screen.getByRole("link", { name: /Create Monitor/i }),
    ).toHaveAttribute("href", "/intent-radar/monitors/new");
    expect(
      screen.getByRole("link", { name: /Explore Signals/i }),
    ).toHaveAttribute("href", "/intent-radar/signals");
    expect(
      screen.getByRole("link", { name: /Open AI Assistant/i }),
    ).toHaveAttribute("href", "/intelligence/assistant");

    // Broken inline prompt and textarea must be completely removed
    expect(
      screen.queryByText(/What would you like to discover today/i),
    ).not.toBeInTheDocument();
    expect(screen.queryByText(/Ask PlaneByte/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });

  it("renders sanitized Markdown with zero raw **Markdown** syntax", () => {
    const md =
      "### Top Signals\n\n- **High intent** on [GitHub](/intent-radar/signals/1)\n- Check `webhook` alerts";
    const { container } = render(<SafeMarkdown content={md} compact />);
    expect(container.textContent).not.toContain("**");
    expect(container.querySelector("strong")?.textContent).toBe("High intent");
    expect(container.querySelector("a")?.getAttribute("href")).toBe(
      "/intent-radar/signals/1",
    );
    expect(container.querySelector("code")?.textContent).toBe("webhook");
  });

  it("displays reconciled workspace plans, setup progress, and labeled actions", async () => {
    call.mockImplementation(async (path) => {
      if (path === "/organization/workspaces") {
        return {
          active_organization_id: "org-pb",
          active_onboarding_status: "COMPLETED",
          items: [
            {
              organization_id: "org-pb",
              name: "PlaneByte",
              role: "OWNER",
              plan_label: "Starter Trial",
              plan_status: "Canceled · Access remaining",
              access_state: "CANCELED_REMAINING",
              onboarding_status: "COMPLETED",
              onboarding_completed_steps: 5,
              onboarding_total_steps: 5,
              next_setup_step: null,
              member_count: 2,
            },
            {
              organization_id: "org-syn",
              name: "Syntaxwars",
              role: "OWNER",
              plan_label: "No active plan",
              plan_status: "Not activated",
              access_state: "SETUP_REQUIRED",
              onboarding_status: "IN_PROGRESS",
              onboarding_completed_steps: 2,
              onboarding_total_steps: 5,
              next_setup_step: "icp",
              member_count: 1,
            },
            {
              organization_id: 'org-configured',name:'Configured workspace',role:'OWNER',
              onboarding_status:'COMPLETED',access_state:'SUBSCRIPTION_REQUIRED',plan_label:'Activation required',
              onboarding_completed_steps:4,onboarding_total_steps:5,next_setup_step:'plan',
            },
          ],
        } as never;
      }
      return {} as never;
    });

    wrap(<WorkspacesManager />);
    expect(await screen.findByText("Starter Trial")).toBeVisible();
    expect(screen.getByText("Canceled · Access remaining")).toBeVisible();
    expect(screen.getAllByText("Complete · 5/5")).toHaveLength(2);
    expect(screen.getAllByRole('button',{name:'Continue setup'})).toHaveLength(1);
    expect(screen.getByText("No active plan")).toBeVisible();
    expect(screen.getByText("Setup · 2/5")).toBeVisible();
    expect(screen.getByRole("button", { name: /Rename PlaneByte/i })).toBeVisible();
    expect(screen.getByRole("button", { name: /Leave PlaneByte/i })).toBeVisible();
  });

  it("shows actionable error + retry when Team members fail to load", async () => {
    call.mockImplementation(async (path) => {
      if (path === "/organization/workspaces") {
        return {
          active_organization_id: "org-1",
          items: [{ organization_id: "org-1", name: "PlaneByte", role: "OWNER" }],
        } as never;
      }
      if (path === "/organization/members") {
        throw new Error("Upstream database timeout");
      }
      return {} as never;
    });

    wrap(<TeamSection activeTab="members" />);
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Could not load team members.");
    expect(alert).toHaveTextContent("Upstream database timeout");
    expect(screen.getByRole("button", { name: /Retry/i })).toBeVisible();
  });

  it("requires confirmation before revoking a business domain and shows TXT details drawer", async () => {
    call.mockImplementation(async (path, opts) => {
      if (path === "/organization/workspaces") {
        return {
          active_organization_id: "org-1",
          items: [{ organization_id: "org-1", name: "PlaneByte", role: "OWNER" }],
        } as never;
      }
      if (path === "/organization/domains" && !opts?.method) {
        return {
          can_edit: true,
          items: [
            {
              id: "dom-1",
              domain: "planebyte.com",
              status: "PENDING",
              record_type: "TXT",
              record_name: "_heysow-verify.planebyte.com",
              challenge_expires_at: "2026-11-25T00:00:00Z",
              attempts: 1,
            },
          ],
        } as never;
      }
      if (opts?.method === "DELETE") {
        return { status: "REVOKED" } as never;
      }
      return {} as never;
    });

    wrap(<DomainSettings />);
    expect(await screen.findByText("planebyte.com")).toBeVisible();
    expect(screen.getByText(/Copy Record Name/i)).toBeVisible();

    // Clicking Revoke opens confirmation dialog and does NOT delete immediately
    fireEvent.click(screen.getByRole("button", { name: /^Revoke$/i }));
    expect(await screen.findByText(/Revoke planebyte\.com\?/i)).toBeVisible();
    expect(
      call.mock.calls.some(([, opts]) => opts?.method === "DELETE"),
    ).toBe(false);
  });

  it("humanizes Audit Log targets and keeps raw identifiers inside collapsible diagnostics", async () => {
    call.mockImplementation(async (path) => {
      if (path === "/organization/workspaces") {
        return {
          active_organization_id: "org-1",
          items: [{ organization_id: "org-1", name: "PlaneByte", role: "OWNER" }],
        } as never;
      }
      if (path.startsWith("/foundation/audit")) {
        return {
          total: 1,
          page: 1,
          page_size: 20,
          items: [
            {
              id: "audit-uuid-9999",
              actor: "owner@planebyte.com",
              action: "DOMAIN_CHALLENGE_CREATED",
              entity: "domain:aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
              result: "SUCCESS",
              details: { domain: "planebyte.com" },
              created_at: "2026-11-18T12:00:00Z",
            },
          ],
        } as never;
      }
      return {} as never;
    });

    wrap(<AccessSettings />);
    expect(await screen.findByText("Created DNS verification challenge")).toBeVisible();
    expect(screen.getByText("planebyte.com")).toBeVisible();
    expect(
      screen.queryByText(/aaaaaaaa-bbbb/i),
    ).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /View details/i }));
    expect(await screen.findByText("Technical diagnostics")).toBeVisible();
  });
});
