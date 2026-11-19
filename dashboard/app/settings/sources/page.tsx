import { Suspense } from "react";
import { UnifiedSettingsCenter } from "@/components/settings/unified-settings-center";

export default function SourcesPage() {
  return (
    <Suspense fallback={<p role="status" className="p-8 text-sm text-muted-foreground">Loading sources &amp; tools…</p>}>
      <UnifiedSettingsCenter initialCategory="sources" initialTab="sources" />
    </Suspense>
  );
}
