import { Suspense } from "react";
import { UnifiedSettingsCenter } from "@/components/settings/unified-settings-center";

export default function Appearance() {
  return (
    <Suspense fallback={<p role="status" className="p-8 text-sm text-muted-foreground">Loading appearance settings…</p>}>
      <UnifiedSettingsCenter initialCategory="account" initialTab="appearance" />
    </Suspense>
  );
}
