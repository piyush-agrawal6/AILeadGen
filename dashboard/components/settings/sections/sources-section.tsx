"use client";

import { ResearchSourcesPanel } from "@/components/intent-radar/integrations/ResearchSourcesPanel";
import { CustomFeedsPanel } from "@/components/intent-radar/integrations/CustomFeedsPanel";

export function SourcesSection({
  activeTab,
  onSwitchTab,
}: {
  activeTab: string;
  onSwitchTab?: (tab: string) => void;
}) {
  if (activeTab === "feeds") {
    return <CustomFeedsPanel />;
  }

  return <ResearchSourcesPanel onOpenFeedsTab={() => onSwitchTab?.("feeds")} />;
}
