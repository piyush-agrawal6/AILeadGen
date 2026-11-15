import { Suspense } from "react";
import { UnifiedSettingsCenter } from "@/components/settings/unified-settings-center";

export default function Account() {
  return (
    <Suspense fallback={<p role="status" className="p-8 text-sm text-muted-foreground">Loading account settings…</p>}>
      <UnifiedSettingsCenter initialCategory="account" initialTab="profile" />
    </Suspense>
  );
}
