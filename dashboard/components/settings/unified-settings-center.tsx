"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import {
  UserRound,
  Building2,
  Users,
  SlidersHorizontal,
  Plug,
  CreditCard,
  X,
  ChevronRight,
  type LucideIcon,
} from "lucide-react";

import { useWorkspace } from "@/components/workspaces/use-workspace";
import { IntentRadarProvider } from "@/components/intent-radar/provider";

import { AccountSection } from "./sections/account-section";
import { CompanySection } from "./sections/company-section";
import { TeamSection } from "./sections/team-section";
import { PreferencesSection } from "./sections/preferences-section";
import { IntegrationsSection } from "./sections/integrations-section";
import { BillingSection } from "./sections/billing-section";

export type SettingsCategoryKey =
  | "account"
  | "company"
  | "team"
  | "preferences"
  | "integrations"
  | "billing";

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
    description: "Signal discovery defaults, notification alerts, data retention, and daily safety caps.",
    icon: SlidersHorizontal,
    defaultTab: "discovery",
    tabs: [
      { id: "discovery", label: "Discovery Defaults" },
      { id: "notifications", label: "Notifications & Alerts" },
      { id: "retention", label: "Data Retention" },
      { id: "limits", label: "Capacity & Limits" },
    ],
  },
  {
    key: "integrations",
    label: "Integrations & API",
    shortLabel: "Integrations",
    description: "Manage your research sources, connected accounts, approved feeds, and developer access.",
    icon: Plug,
    defaultTab: "sources",
    tabs: [
      { id: "sources", label: "Research Sources" },
      { id: "developer", label: "MCP & Developer API" },
      { id: "feeds", label: "Custom Feeds" },
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
  const paramCategory = searchParams.get("category") as SettingsCategoryKey | null;
  const paramTab = searchParams.get("tab");

  const resolvedCategory: SettingsCategoryKey =
    initialCategory ||
    (paramCategory && SETTINGS_CATEGORIES.some((c) => c.key === paramCategory)
      ? paramCategory
      : "account");

  const [category, setCategory] = useState<SettingsCategoryKey>(resolvedCategory);

  const categoryDef =
    SETTINGS_CATEGORIES.find((c) => c.key === category) ?? SETTINGS_CATEGORIES[0];

  const resolvedTab =
    initialTab ||
    (paramTab && categoryDef.tabs.some((t) => t.id === paramTab)
      ? paramTab
      : categoryDef.defaultTab);

  const [activeTab, setActiveTab] = useState<string>(resolvedTab);

  // Sync state if initial props change
  useEffect(() => {
    if (initialCategory && initialCategory !== category) {
      setCategory(initialCategory);
    }
  }, [initialCategory]);

  useEffect(() => {
    if (initialTab && initialTab !== activeTab) {
      setActiveTab(initialTab);
    }
  }, [initialTab]);

  // Support browser back/forward navigation
  useEffect(() => {
    function onPopState() {
      const search = new URLSearchParams(window.location.search);
      const cat = search.get("category") as SettingsCategoryKey | null;
      const t = search.get("tab");
      if (cat && SETTINGS_CATEGORIES.some((c) => c.key === cat)) {
        setCategory(cat);
        const def = SETTINGS_CATEGORIES.find((c) => c.key === cat);
        setActiveTab(t && def?.tabs.some((tab) => tab.id === t) ? t : def?.defaultTab ?? "profile");
      }
    }
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  function switchCategory(newCategory: SettingsCategoryKey) {
    setCategory(newCategory);
    const newDef = SETTINGS_CATEGORIES.find((c) => c.key === newCategory) ?? SETTINGS_CATEGORIES[0];
    const newTab = newDef.defaultTab;
    setActiveTab(newTab);

    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.pathname = "/settings";
      url.searchParams.set("category", newCategory);
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
              <div className="flex items-start justify-between gap-4">
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

                <Link
                  href="/intent-radar"
                  aria-label="Close settings"
                  className="rounded-lg p-2 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors shrink-0"
                >
                  <X size={18} />
                </Link>
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
              {category === "integrations" && <IntegrationsSection activeTab={activeTab} onSwitchTab={switchTab} />}
              {category === "billing" && <BillingSection activeTab={activeTab} onSwitchTab={switchTab} />}
            </div>
          </main>
        </div>
      </div>
    </IntentRadarProvider>
  );
}
