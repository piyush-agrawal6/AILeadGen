import { Suspense } from "react";
import { UnifiedSettingsCenter } from "@/components/settings/unified-settings-center";

export default function Security() {
  return (
    <Suspense fallback={<p role="status" className="p-8 text-sm text-muted-foreground">Loading account security…</p>}>
      <UnifiedSettingsCenter initialCategory="account" initialTab="security" />
    </Suspense>
  );
}
