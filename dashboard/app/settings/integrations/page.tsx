import { Suspense } from "react";
import { UnifiedSettingsCenter } from "@/components/settings/unified-settings-center";

export default function IntegrationsPage() {
  return (
    <Suspense fallback={<p role="status" className="p-8 text-sm text-muted-foreground">Loading workspace integrations…</p>}>
      <UnifiedSettingsCenter initialCategory="integrations" initialTab="sources" />
    </Suspense>
  );
}
