"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { PanelLeftClose, PanelLeftOpen, LifeBuoy, Sparkles } from "lucide-react";
import { WorkspaceSwitcher } from "@/components/workspaces/switcher";
import { useWorkspace } from "@/components/workspaces/use-workspace";
import { AccountMenu, type UserIdentity } from "./account-menu";
import { Notifications } from "./notifications";
import { QuickSearchTrigger } from "./quick-search";

export function pageTitle(path: string) {
  if (path.startsWith("/intelligence/assistant")) return "AI Assistant";
  if (path.startsWith("/notifications")) return "Notifications";
  if (path.startsWith("/intent-radar")) {
    const part = path.split("/")[2] || "";
    return (
      ({
        "": "Intent Radar",
        "ideal-customers": "Ideal Customers",
        graph: "Overview",
        assistant: "AI Assistant",
        discover: "Discover",
        monitors: "Monitoring",
        signals: "Intent Signals",
        opportunities: "Opportunities",
        saved: "Research Library",
        alerts: "Alerts",
        integrations: "Integrations & MCP",
        settings: "Intent Radar Settings",
        growth: "Growth Intelligence",
      } as Record<string, string>)[part] || "Intent Radar"
    );
  }
  if (path.startsWith("/billing")) return "Billing & usage";
  if (path.startsWith("/settings")) return "Settings";
  if (path.startsWith("/account")) return "Your account";
  if (path.startsWith("/help")) return "Help & support";
  if (path.startsWith("/find-leads")) return "Find Leads";
  if (path.startsWith("/leads")) return "Companies";
  if (path.startsWith("/assistant")) return "Prospecting assistant";
  if (path.startsWith("/recommendations")) return "Recommendations";
  if (path.startsWith("/lists")) return "Lists";
  if (path.startsWith("/tasks")) return "Tasks";
  if (path.startsWith("/contacts")) return "Contacts";
  if (path.startsWith("/enrichment")) return "Enrichment";
  if (path.startsWith("/campaigns") || path.startsWith("/scans") || path.startsWith("/discovery"))
    return "Campaigns";
  if (path.startsWith("/outreach") || path.startsWith("/runs")) return "Outreach";
  if (path.startsWith("/schedules")) return "Schedules";
  return "Intent Radar";
}

export interface Crumb {
  title: string;
  href?: string;
}

export function getBreadcrumbs(path: string): Crumb[] {
  if (path.startsWith("/intent-radar")) {
    const parts = path.split("/").filter(Boolean);
    const crumbs: Crumb[] = [{ title: "Intent Radar", href: "/intent-radar" }];

    if (parts.length === 1) {
      crumbs.push({ title: "Overview" });
      return crumbs;
    }

    const section = parts[1];
    const sectionTitles: Record<string, string> = {
      discover: "Discover",
      signals: "Intent Signals",
      opportunities: "Opportunities",
      monitors: "Monitoring",
      "ideal-customers": "Ideal Customers",
      growth: "Growth Intelligence",
      saved: "Research Library",
      settings: "Settings",
      integrations: "Integrations",
      alerts: "Alerts",
      assistant: "AI Assistant",
    };

    const sectionTitle =
      sectionTitles[section] || section.charAt(0).toUpperCase() + section.slice(1);

    if (parts.length === 2) {
      crumbs.push({ title: sectionTitle });
      return crumbs;
    }

    crumbs.push({ title: sectionTitle, href: `/intent-radar/${section}` });

    const sub = parts[2];
    if (sub === "new") {
      crumbs.push({
        title:
          section === "monitors"
            ? "Create Monitor"
            : section === "discover"
              ? "New Discovery"
              : section === "ideal-customers"
                ? "New ICP"
                : "New",
      });
    } else if (sub === "history") {
      crumbs.push({ title: "Discovery History" });
    } else if (sub === "saved") {
      crumbs.push({ title: "Saved Searches" });
    } else if (sub === "compare") {
      crumbs.push({ title: "Compare" });
    } else if (sub === "themes") {
      crumbs.push({ title: "Trends & Themes" });
    } else if (sub === "competitors") {
      crumbs.push({ title: "Competitors" });
    } else if (sub === "research") {
      crumbs.push({ title: "AI Research" });
    } else if (parts[3] === "edit") {
      crumbs.push({ title: "Edit" });
    } else {
      crumbs.push({ title: "Details" });
    }

    return crumbs;
  }

  const title = pageTitle(path);
  return [{ title }];
}

export function Header({
  workspaceManagementEnabled = false,
  collapsed = false,
  onToggle,
  mobileTrigger,
  user = {},
}: {
  workspaceManagementEnabled?: boolean;
  collapsed?: boolean;
  onToggle?: () => void;
  mobileTrigger?: React.ReactNode;
  user?: UserIdentity;
}) {
  const path = usePathname();
  const workspace = useWorkspace(workspaceManagementEnabled);
  const onAssistant =
    path.startsWith("/intelligence/assistant") || path === "/intent-radar/assistant";
  const crumbs = getBreadcrumbs(path);

  return (
    <header className="shell-header">
      {/* Left: Sidebar Toggle + Lightweight Breadcrumb */}
      <div className="flex min-w-0 items-center gap-2.5 sm:gap-3 flex-1 lg:flex-initial">
        <button
          className="shell-icon-button shell-desktop-toggle shrink-0 cursor-pointer"
          onClick={onToggle}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          aria-expanded={!collapsed}
          aria-controls="desktop-navigation"
        >
          {collapsed ? <PanelLeftOpen size={19} /> : <PanelLeftClose size={19} />}
        </button>
        {mobileTrigger}

        <nav
          aria-label="Breadcrumb"
          className="flex items-center gap-1.5 text-xs text-muted-foreground min-w-0 truncate"
        >
          {crumbs.map((crumb, idx) => (
            <span key={crumb.title + idx} className="flex items-center gap-1.5 min-w-0 shrink-0">
              {idx > 0 && (
                <span className="text-muted-foreground/40 font-normal" aria-hidden="true">
                  /
                </span>
              )}
              {crumb.href ? (
                <Link
                  href={crumb.href}
                  className="text-muted-foreground hover:text-foreground transition-colors font-medium truncate"
                >
                  {crumb.title}
                </Link>
              ) : (
                <span className="font-semibold text-foreground truncate">{crumb.title}</span>
              )}
            </span>
          ))}
        </nav>
      </div>

      {/* Center-Right: Wide Global Search (340-420px on desktop) */}
      <div className="flex items-center justify-end flex-1 max-w-[420px] mx-2 hidden sm:flex">
        <QuickSearchTrigger />
      </div>

      {/* Right Actions: AI Shortcut, Notifications, Help, Workspace Switcher, User Avatar */}
      <div className="flex shrink-0 items-center gap-1 sm:gap-2">
        <div className="sm:hidden">
          <QuickSearchTrigger />
        </div>

        <Link
          href="/intelligence/assistant"
          aria-label="AI Assistant"
          title="AI Assistant"
          aria-current={onAssistant ? "page" : undefined}
          className={"shell-icon-button " + (onAssistant ? "bg-primary/15 text-primary" : "")}
        >
          <Sparkles size={18} />
        </Link>

        {workspaceManagementEnabled && workspace.active && <Notifications />}

        <Link
          className="shell-icon-button shell-help-action"
          href="/help"
          aria-label="Help & support"
          title="Help & support"
        >
          <LifeBuoy size={18} />
        </Link>

        {workspaceManagementEnabled && (
          <div className="hidden md:block">
            <WorkspaceSwitcher
              onSelected={(id) => {
                const target = workspace.data?.items.find((i) => i.organization_id === id);
                const setupUrl = target?.next_setup_step
                  ? `/onboarding?step=${encodeURIComponent(target.next_setup_step)}`
                  : "/onboarding";
                window.location.assign(
                  target?.access_state === "SETUP_REQUIRED" ? setupUrl : "/intent-radar"
                );
              }}
            />
          </div>
        )}

        <AccountMenu user={user} workspaceManagementEnabled={workspaceManagementEnabled} />
      </div>
    </header>
  );
}
