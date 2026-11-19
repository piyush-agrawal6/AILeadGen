"use client";

import { DeveloperSettings, type DevTabKey } from "@/components/workspaces/developer-settings";

export function DeveloperSection({
  activeTab,
  onSwitchTab,
}: {
  activeTab: string;
  onSwitchTab?: (tab: string) => void;
}) {
  const validTab: DevTabKey = (
    ["keys", "overview", "mcp", "api", "usage"].includes(activeTab)
      ? activeTab
      : "keys"
  ) as DevTabKey;

  return (
    <DeveloperSettings
      activeTab={validTab}
      onTabChange={(tab) => onSwitchTab?.(tab)}
    />
  );
}
