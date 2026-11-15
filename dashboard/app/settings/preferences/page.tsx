import { Suspense } from "react";
import { UnifiedSettingsCenter } from "@/components/settings/unified-settings-center";

export default function PreferencesPage() {
  return (
    <Suspense fallback={<p role="status" className="p-8 text-sm text-muted-foreground">Loading research preferences…</p>}>
      <UnifiedSettingsCenter initialCategory="preferences" initialTab="discovery" />
    </Suspense>
  );
}
