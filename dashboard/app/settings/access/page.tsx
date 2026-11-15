import { Suspense } from "react";
import { notFound } from "next/navigation";
import { UnifiedSettingsCenter } from "@/components/settings/unified-settings-center";

export default function AccessPage() {
  if (process.env.HEYSOW_WORKSPACE_MANAGEMENT_ENABLED !== "true") notFound();
  return (
    <Suspense fallback={<p role="status" className="p-8 text-sm text-muted-foreground">Loading roles & audit…</p>}>
      <UnifiedSettingsCenter initialCategory="team" initialTab="roles" />
    </Suspense>
  );
}
