"use client";

import { Suspense } from "react";
import { UnifiedSettingsCenter } from "@/components/settings/unified-settings-center";

export default function SettingsPage() {
  return (
    <Suspense fallback={<p role="status" className="p-8 text-sm text-muted-foreground">Loading settings…</p>}>
      <UnifiedSettingsCenter />
    </Suspense>
  );
}
