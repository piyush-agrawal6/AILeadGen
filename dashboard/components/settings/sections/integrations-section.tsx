"use client";

import { DeveloperSettings } from "@/components/workspaces/developer-settings";
import { ResearchSourcesPanel } from "@/components/intent-radar/integrations/ResearchSourcesPanel";
import { CustomFeedsPanel } from "@/components/intent-radar/integrations/CustomFeedsPanel";

export function IntegrationsSection({
  activeTab,
  onSwitchTab,
}: {
  activeTab: string;
  onSwitchTab?: (tab: string) => void;
}) {
  if (activeTab === "developer") {
    return <DeveloperSettings />;
  }

  if (activeTab === "feeds") {
    return <CustomFeedsPanel />;
  }

  return <ResearchSourcesPanel onOpenFeedsTab={() => onSwitchTab?.("feeds")} />;
}
