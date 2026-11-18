"use client";

import type { RefObject } from "react";
import Link from "next/link";
import { Bookmark, Compass, History } from "lucide-react";

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
  const tabs: { id: DiscoverTab; label: string; href: string; icon: typeof Compass }[] = [
    { id: "new", label: "New Discovery", href: "/intent-radar/discover", icon: Compass },
    { id: "history", label: "Discovery History", href: "/intent-radar/discover/history", icon: History },
    { id: "saved", label: "Saved Searches", href: "/intent-radar/discover/saved", icon: Bookmark },
  ];

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-3">
      <nav aria-label="Discovery workspace sections" className="flex items-center gap-1 overflow-x-auto">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const active = activeTab === tab.id;
          return (
            <Link
              key={tab.id}
              href={tab.href}
              aria-current={active ? "page" : undefined}
              className={
                "inline-flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-xs font-semibold transition-colors whitespace-nowrap " +
                (active
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:bg-muted/60 hover:text-foreground")
              }
            >
              <Icon size={14} aria-hidden="true" />
              {tab.label}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
