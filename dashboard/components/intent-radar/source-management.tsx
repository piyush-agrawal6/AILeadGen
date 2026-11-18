"use client";

import { ResearchSourcesPanel } from "./integrations/ResearchSourcesPanel";
import { CustomFeedsPanel } from "./integrations/CustomFeedsPanel";

export function SourceManagement() {
  return (
    <div className="space-y-8">
      <ResearchSourcesPanel />
      <CustomFeedsPanel />
    </div>
  );
}
