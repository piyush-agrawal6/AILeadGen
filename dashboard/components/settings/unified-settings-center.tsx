"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import {
  UserRound,
  Building2,
  Users,
  SlidersHorizontal,
  Bell,
  Radio,
  Code2,
  CreditCard,
  ChevronRight,
  type LucideIcon,
} from "lucide-react";

import { useWorkspace } from "@/components/workspaces/use-workspace";
import { IntentRadarProvider } from "@/components/intent-radar/provider";

import { AccountSection } from "./sections/account-section";
import { CompanySection } from "./sections/company-section";
import { TeamSection } from "./sections/team-section";
import { PreferencesSection } from "./sections/preferences-section";
import { NotificationsSection } from "./sections/notifications-section";
import { SourcesSection } from "./sections/sources-section";
import { DeveloperSection } from "./sections/developer-section";
import { BillingSection } from "./sections/billing-section";

export type SettingsCategoryKey =
  | "account"
  | "company"
  | "team"
  | "preferences"
  | "notifications"
  | "sources"
  | "developer"
  | "billing"
  | "integrations"; // legacy alias mapping to sources

interface SettingsCategoryDef {
  key: SettingsCategoryKey;
  label: string;
  shortLabel: string;
  description: string;
  icon: LucideIcon;
  defaultTab: string;
  tabs: { id: string; label: string }[];
}

export const SETTINGS_CATEGORIES: SettingsCategoryDef[] = [
  {
    key: "account",
    label: "Account & Profile",
    shortLabel: "Account",
    description: "Personal identity, Google sign-in security, and display preferences.",
    icon: UserRound,
    defaultTab: "profile",
    tabs: [
      { id: "profile", label: "Personal Profile" },
      { id: "security", label: "Sign-in & Security" },
      { id: "appearance", label: "Appearance" },
    ],
  },
  {
    key: "company",
    label: "Company & Targeting",
    shortLabel: "Company",
    description: "Organization context and verified business domains. Manage Ideal Customers in the Intelligence sidebar.",
    icon: Building2,
    defaultTab: "profile",
    tabs: [
      { id: "profile", label: "Organization Profile" },
      { id: "domains", label: "Business Domains" },
    ],
  },
  {
    key: "team",
    label: "Team & Access",
    shortLabel: "Team",
    description: "Active members, team invitations, workspace roles, and security audit log.",
    icon: Users,
    defaultTab: "members",
    tabs: [
      { id: "members", label: "Team Members" },
      { id: "invitations", label: "Invitations" },
      { id: "roles", label: "Roles & Audit" },
    ],
  },
  {
    key: "preferences",
    label: "Research Preferences",
    shortLabel: "Preferences",
    description: "Signal discovery defaults, high-relevance alert sensitivity, data retention, and daily safety caps.",
    icon: SlidersHorizontal,
    defaultTab: "discovery",
    tabs: [
      { id: "discovery", label: "Discovery Defaults" },
      { id: "alerts", label: "Alerts" },
      { id: "retention", label: "Data Retention" },
      { id: "limits", label: "Capacity & Limits" },
    ],
  },
  {
    key: "notifications",
    label: "Notifications",
    shortLabel: "Notifications",
    description: "Configure personal delivery channels, notification types, quiet hours, and email alerts.",
    icon: Bell,
    defaultTab: "channels",
    tabs: [
      { id: "channels", label: "Delivery Channels" },
      { id: "types", label: "Notification Types" },
    ],
  },
  {
    key: "sources",
    label: "Sources & Tools",
    shortLabel: "Sources",
    description: "Manage your public research evidence sources, connected account health, and custom RSS/Atom feeds.",
    icon: Radio,
    defaultTab: "sources",
    tabs: [
      { id: "sources", label: "Research Sources" },
      { id: "feeds", label: "Custom Feeds" },
    ],
  },
  {
    key: "developer",
    label: "Developer & API",
    shortLabel: "Developer",
    description: "Manage scoped API keys, configure Model Context Protocol (MCP) clients, and inspect REST endpoints.",
    icon: Code2,
    defaultTab: "keys",
    tabs: [
      { id: "keys", label: "API Keys" },
      { id: "overview", label: "Overview & Diagnostics" },
      { id: "mcp", label: "MCP Setup" },
      { id: "api", label: "API Reference" },
      { id: "usage", label: "Usage & Logs" },
    ],
  },
  {
    key: "billing",
    label: "Billing & Usage",
    shortLabel: "Billing",
    description: "Manage your subscription and keep track of your usage.",
    icon: CreditCard,
    defaultTab: "overview",
    tabs: [
      { id: "overview", label: "Current Plan & Usage" },
      { id: "plans", label: "Compare Plans" },
    ],
  },
];

export function resolveSettingsCategory(rawCategory?: string | null, rawTab?: string | null): { category: SettingsCategoryKey; tab?: string } {
  if (!rawCategory) return { category: "account" };

  // Handle legacy mappings
  if (rawCategory === "integrations") {
    if (rawTab === "developer") {
      return { category: "developer", tab: "keys" };
    }
    if (rawTab === "feeds") {
      return { category: "sources", tab: "feeds" };
    }
    return { category: "sources", tab: "sources" };
  }

  if (rawCategory === "preferences" && rawTab === "notifications") {
    return { category: "notifications", tab: "channels" };
  }

  const found = SETTINGS_CATEGORIES.find((c) => c.key === rawCategory);
  if (found) {
    return { category: found.key, tab: rawTab || undefined };
  }

  return { category: "account" };
}

export function UnifiedSettingsCenter({
  initialCategory,
  initialTab,
}: {
  initialCategory?: SettingsCategoryKey;
  initialTab?: string;
}) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const workspace = useWorkspace();

  // Redirect legacy ?category=company&tab=icp links to the dedicated Ideal Customers workspace
  useEffect(() => {
    if (searchParams.get("category") === "company" && searchParams.get("tab") === "icp") {
      router.replace("/intent-radar/ideal-customers");
    }
  }, [searchParams, router]);

  // Determine starting category and tab from props, URL searchParams, or path
  const paramCategory = searchParams.get("category");
  const paramTab = searchParams.get("tab");

  const resolved = resolveSettingsCategory(
    initialCategory || paramCategory,
    initialTab || paramTab
  );

  const [category, setCategory] = useState<SettingsCategoryKey>(resolved.category);

  const categoryDef =
    SETTINGS_CATEGORIES.find((c) => c.key === category) ?? SETTINGS_CATEGORIES[0];

  const resolvedTab =
    resolved.tab && categoryDef.tabs.some((t) => t.id === resolved.tab)
      ? resolved.tab
      : categoryDef.defaultTab;

  const [activeTab, setActiveTab] = useState<string>(resolvedTab);

  // Sync state if initial props or URL searchParams change
  useEffect(() => {
    const next = resolveSettingsCategory(
      initialCategory || paramCategory,
      initialTab || paramTab
    );
    if (next.category !== category) {
      setCategory(next.category);
      const nextDef = SETTINGS_CATEGORIES.find((c) => c.key === next.category) ?? SETTINGS_CATEGORIES[0];
      const nextTab = next.tab && nextDef.tabs.some((t) => t.id === next.tab)
        ? next.tab
        : nextDef.defaultTab;
      setActiveTab(nextTab);
    } else if (next.tab && next.tab !== activeTab && categoryDef.tabs.some((t) => t.id === next.tab)) {
      setActiveTab(next.tab);
    }
  }, [initialCategory, paramCategory, initialTab, paramTab]);

  // Support browser back/forward navigation
  useEffect(() => {
    function onPopState() {
      const search = new URLSearchParams(window.location.search);
      const next = resolveSettingsCategory(search.get("category"), search.get("tab"));
      setCategory(next.category);
      const def = SETTINGS_CATEGORIES.find((c) => c.key === next.category) ?? SETTINGS_CATEGORIES[0];
      setActiveTab(next.tab && def.tabs.some((t) => t.id === next.tab) ? next.tab : def.defaultTab);
    }
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  function switchCategory(newCategory: SettingsCategoryKey) {
    const targetCat = newCategory === "integrations" ? "sources" : newCategory;
    setCategory(targetCat);
    const newDef = SETTINGS_CATEGORIES.find((c) => c.key === targetCat) ?? SETTINGS_CATEGORIES[0];
    const newTab = newDef.defaultTab;
    setActiveTab(newTab);

    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.pathname = "/settings";
      url.searchParams.set("category", targetCat);
      url.searchParams.set("tab", newTab);
      window.history.pushState(null, "", url.toString());
    }
  }

  function switchTab(newTab: string) {
    setActiveTab(newTab);
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.pathname = "/settings";
      url.searchParams.set("category", category);
      url.searchParams.set("tab", newTab);
      window.history.pushState(null, "", url.toString());
    }
  }

  const organizationId = workspace.data?.active_organization_id || "";

  return (
    <IntentRadarProvider
      initialOrganization={organizationId}
      mcpEndpoint={
        typeof window !== "undefined"
          ? `${window.location.origin}/api/v1/mcp`
          : "/api/v1/mcp"
      }
    >
      <div className="pb-unified-settings-container">
        {/* Main Settings Card Stage */}
        <div className="pb-unified-settings-card">
          {/* Left Category Navigation Column (Desktop) */}
          <aside className="pb-settings-sidebar">
            <div className="pb-settings-sidebar-header">
              <div>
                <h1 className="text-lg font-bold tracking-tight">Settings</h1>
                <p className="text-xs text-muted-foreground truncate max-w-[170px]">
                  {workspace.active?.name || "Workspace Preferences"}
                </p>
              </div>
            </div>

            <nav className="pb-settings-category-nav" aria-label="Settings categories">
              {SETTINGS_CATEGORIES.map((cat) => {
                const Icon = cat.icon;
                const isSelected = category === cat.key;
                return (
                  <button
                    key={cat.key}
                    type="button"
                    onClick={() => switchCategory(cat.key)}
                    className={`pb-settings-nav-item ${isSelected ? "is-active" : ""}`}
                    aria-current={isSelected ? "page" : undefined}
                  >
                    <Icon size={17} className="shrink-0" />
                    <span className="truncate">{cat.label}</span>
                  </button>
                );
              })}
            </nav>

            <div className="pb-settings-sidebar-footer">
              <Link
                href="/intent-radar"
                className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
              >
                <span>Return to Intent Radar</span>
                <ChevronRight size={13} />
              </Link>
            </div>
          </aside>

          {/* Right Content Pane */}
          <main className="pb-settings-main-pane">
            {/* Mobile / Tablet Horizontal Category Scroll */}
            <div className="pb-settings-mobile-category-bar md:hidden">
              {SETTINGS_CATEGORIES.map((cat) => {
                const Icon = cat.icon;
                const isSelected = category === cat.key;
                return (
                  <button
                    key={cat.key}
                    type="button"
                    onClick={() => switchCategory(cat.key)}
                    className={`pb-settings-mobile-cat-pill ${isSelected ? "is-active" : ""}`}
                  >
                    <Icon size={14} />
                    <span>{cat.shortLabel}</span>
                  </button>
                );
              })}
            </div>

            {/* Category Header & Sub-Tabs */}
            <header className="pb-settings-content-header">
              <div className="space-y-1 min-w-0">
                <div className="flex items-center gap-2">
                  <categoryDef.icon size={18} className="text-primary shrink-0 hidden sm:block" />
                  <h2 className="text-lg sm:text-xl font-bold tracking-tight">
                    {categoryDef.label}
                  </h2>
                </div>
                <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
                  {categoryDef.description}
                </p>
              </div>

              {/* Sub-Tabs Bar */}
              <div className="pb-settings-tabs-bar" role="tablist" aria-label={`${categoryDef.label} tabs`}>
                {categoryDef.tabs.map((tab) => {
                  const isSelected = activeTab === tab.id;
                  return (
                    <button
                      key={tab.id}
                      role="tab"
                      aria-selected={isSelected}
                      onClick={() => switchTab(tab.id)}
                      className={`pb-settings-tab-btn ${isSelected ? "is-active" : ""}`}
                    >
                      {tab.label}
                    </button>
                  );
                })}
              </div>
            </header>

            {/* Active Content Body */}
            <div className="pb-settings-content-body">
              {category === "account" && <AccountSection activeTab={activeTab} />}
              {category === "company" && <CompanySection activeTab={activeTab} />}
              {category === "team" && <TeamSection activeTab={activeTab} onSwitchTab={switchTab} />}
              {category === "preferences" && <PreferencesSection activeTab={activeTab} />}
              {category === "notifications" && <NotificationsSection activeTab={activeTab} />}
              {(category === "sources" || category === "integrations") && (
                <SourcesSection activeTab={activeTab} onSwitchTab={switchTab} />
              )}
              {category === "developer" && (
                <DeveloperSection activeTab={activeTab} onSwitchTab={switchTab} />
              )}
              {category === "billing" && <BillingSection activeTab={activeTab} onSwitchTab={switchTab} />}
            </div>
          </main>
        </div>
      </div>
    </IntentRadarProvider>
  );
}
