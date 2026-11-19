"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  LayoutDashboard,
  TrendingUp,
  Users,
  Sparkles,
  HelpCircle,
} from "lucide-react";
import { PrimaryTabs, type PrimaryTabItem } from "@/components/ui/tabs";
import { EmptyState } from "./ui";
import { GrowthOverviewDashboard } from "./growth/GrowthOverviewDashboard";
import { GrowthThemesPage } from "./growth/GrowthThemesPage";
import { GrowthCompetitorsPage } from "./growth/GrowthCompetitorsPage";
import { GrowthResearchWorkspace } from "./growth/GrowthResearchWorkspace";
import type { GrowthOverview } from "@/lib/growth";

export { growthQuery } from "@/lib/growth";

export function ConversationChart({ rows }: { rows: GrowthOverview["daily"] }) {
  const [selected, setSelected] = useState<string | null>(null);
  const maximum = Math.max(1, ...rows.map((r) => r.conversations));

  if (!rows.length) {
    return (
      <EmptyState
        title="No conversation history yet"
        description="The chart uses actual stored publication dates. It will populate as approved monitors collect evidence."
      />
    );
  }

  return (
    <section className="ir-panel ir-form-section">
      <h2>Published conversations in this collection</h2>
      <p>Choose a bar to inspect its count. Missing days are not proof of zero market activity.</p>
      <div className="growth-chart" role="group" aria-label="Collected conversations by publication day">
        {rows.map((row) => (
          <button
            key={row.day}
            className="growth-bar"
            aria-label={row.day + ": " + row.conversations + " conversations"}
            aria-pressed={selected === row.day}
            onClick={() => setSelected(row.day)}
          >
            <span
              className="growth-bar-fill"
              style={{ height: Math.max(8, (row.conversations / maximum) * 140) }}
            />
            <small>{row.day.slice(5)}</small>
          </button>
        ))}
      </div>
      <p role="status">
        {selected
          ? selected + ": " + rows.find((r) => r.day === selected)?.conversations + " collected conversations"
          : "Select a day for its exact count."}
      </p>
      <details>
        <summary>View chart data</summary>
        <table className="growth-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Conversations</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.day}>
                <td>{row.day}</td>
                <td>{row.conversations}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </section>
  );
}

interface GrowthExperienceProps {
  route: string;
}

export function GrowthExperience({ route }: GrowthExperienceProps) {
  const router = useRouter();

  // Normalize route segments: "growth", "growth/themes", "growth/themes/123", "growth/competitors", "growth/research", "growth/research/456"
  const parts = route.replace(/^\/?intent-radar\//, "").split("/");
  const section = parts[1] || "overview";
  const itemId = parts[2];

  // Determine active tab ID
  const activeTab =
    section === "themes"
      ? "themes"
      : section === "competitors"
        ? "competitors"
        : section === "research"
          ? "research"
          : "overview";

  const tabs: PrimaryTabItem[] = [
    {
      id: "overview",
      label: "Overview",
      href: "/intent-radar/growth",
      icon: LayoutDashboard,
    },
    {
      id: "themes",
      label: "Trends & Themes",
      href: "/intent-radar/growth/themes",
      icon: TrendingUp,
    },
    {
      id: "competitors",
      label: "Competitor Intelligence",
      href: "/intent-radar/growth/competitors",
      icon: Users,
    },
    {
      id: "research",
      label: "AI Research",
      href: "/intent-radar/growth/research",
      icon: Sparkles,
    },
  ];

  function handleNavigateTab(tabId: string) {
    if (tabId === "overview") {
      router.push("/intent-radar/growth");
    } else {
      router.push(`/intent-radar/growth/${tabId}`);
    }
  }

  return (
    <div className="w-full min-w-0 space-y-6 pb-20">
      {/* Top Header & Context */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border pb-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">
              Growth Intelligence
            </h1>
            <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[11px] font-semibold text-primary">
              2.0
            </span>
          </div>
          <p className="text-xs text-muted-foreground">
            Transform conversations collected through Discovery and Monitoring into evidence-backed market and customer intelligence.
          </p>
        </div>

        <Link
          href="/help?article=growth-intelligence"
          className="text-xs text-muted-foreground hover:text-foreground inline-flex items-center gap-1 self-start sm:self-auto"
        >
          <HelpCircle size={13} />
          <span>Growth Guide</span>
        </Link>
      </div>

      {/* 4 Primary Navigation Tabs */}
      <PrimaryTabs
        items={tabs}
        activeId={activeTab}
        onChange={handleNavigateTab}
        ariaLabel="Growth Intelligence navigation"
      />

      {/* Dynamic Section Router */}
      <div className="pt-1">
        {activeTab === "overview" && (
          <GrowthOverviewDashboard onNavigateTab={handleNavigateTab} />
        )}

        {activeTab === "themes" && (
          <GrowthThemesPage themeId={itemId} onNavigateTab={handleNavigateTab} />
        )}

        {activeTab === "competitors" && (
          <GrowthCompetitorsPage onNavigateTab={handleNavigateTab} />
        )}

        {activeTab === "research" && (
          <GrowthResearchWorkspace researchId={itemId} onNavigateTab={handleNavigateTab} />
        )}
      </div>
    </div>
  );
}
