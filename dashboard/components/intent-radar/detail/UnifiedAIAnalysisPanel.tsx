"use client";

import { SignalIntelligencePanel } from "../signals/SignalIntelligencePanel";

export function UnifiedAIAnalysisPanel({
  signalId,
  monitorId,
  available = 1,
}: {
  signalId: string;
  monitorId?: string;
  available?: number;
}) {
  return (
    <div className="space-y-4">
      <SignalIntelligencePanel
        id={signalId}
        monitorId={monitorId}
        available={available}
      />
    </div>
  );
}
