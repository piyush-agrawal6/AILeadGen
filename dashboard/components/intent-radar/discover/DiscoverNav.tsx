"use client";

import type { RefObject } from "react";
import { Bookmark, Compass, History } from "lucide-react";
import { PrimaryTabs, type PrimaryTabItem } from "@/components/ui/tabs";

export type DiscoverTab = "new" | "history" | "saved";

export function DiscoverNav({
  activeTab,
}: {
  activeTab: DiscoverTab;
  copilotOpen?: boolean;
  onToggleCopilot?: () => void;
  copilotButtonRef?: RefObject<HTMLButtonElement | null>;
  showCopilotButton?: boolean;
}) {
  const tabs: PrimaryTabItem[] = [
    { id: "new", label: "New Discovery", href: "/intent-radar/discover", icon: Compass },
    { id: "history", label: "Discovery History", href: "/intent-radar/discover/history", icon: History },
    { id: "saved", label: "Saved Searches", href: "/intent-radar/discover/saved", icon: Bookmark },
  ];

  return (
    <div className="border-b border-border">
      <PrimaryTabs
        items={tabs}
        activeId={activeTab}
        ariaLabel="Discovery workspace sections"
      />
    </div>
  );
}
