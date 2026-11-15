"use client";

import { useWorkspaceManagement } from "@/components/workspaces/features";
import { useWorkspace } from "@/components/workspaces/use-workspace";

export default function SettingsLayout({ children }: { children: React.ReactNode }) {
  return <div className="settings-layout-unified w-full min-w-0">{children}</div>;
}
