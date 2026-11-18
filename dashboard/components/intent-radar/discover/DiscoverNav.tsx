"use client";

import Link from "next/link";
import { Bookmark, Compass, History, Sparkles } from "lucide-react";

export type DiscoverTab = "new" | "history" | "saved";

export function DiscoverNav({
  activeTab,
  onOpenMobileCopilot,
  showCopilotButton = false,
}: {
  activeTab: DiscoverTab;
  onOpenMobileCopilot?: () => void;
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

      {showCopilotButton && onOpenMobileCopilot && (
        <button
          type="button"
          onClick={onOpenMobileCopilot}
          className="lg:hidden inline-flex items-center gap-1.5 rounded-lg border border-primary/40 bg-primary/10 px-3 py-1.5 text-xs font-semibold text-primary hover:bg-primary/15 transition-colors cursor-pointer"
        >
          <Sparkles size={14} aria-hidden="true" />
          Discovery Copilot
        </button>
      )}
    </div>
  );
}
