"use client";

import { Bookmark, History } from "lucide-react";
import { PrimaryTabs, type PrimaryTabItem } from "@/components/ui/tabs";

export type DiscoverTab = "history" | "saved" | "new";

export function DiscoverNav({
  activeTab,
  onTabChange,
}: {
  activeTab: DiscoverTab;
  onTabChange?: (tab: DiscoverTab) => void;
}) {
  const tabs: PrimaryTabItem[] = [
    {
      id: "history",
      label: "Discovery History",
      href: "/intent-radar/discover",
      icon: History,
    },
    {
      id: "saved",
      label: "Saved Searches",
      href: "/intent-radar/discover/saved",
      icon: Bookmark,
    },
  ];

  return (
    <div className="border-b border-border">
      <PrimaryTabs
        items={tabs}
        activeId={activeTab === "saved" ? "saved" : "history"}
        onChange={onTabChange ? (id) => onTabChange(id as DiscoverTab) : undefined}
        ariaLabel="Discovery workspace sections"
      />
    </div>
  );
}
