import { Suspense } from "react";
import { notFound } from "next/navigation";
import { UnifiedSettingsCenter } from "@/components/settings/unified-settings-center";

export default function CompanyPage() {
  if (process.env.HEYSOW_WORKSPACE_MANAGEMENT_ENABLED !== "true") notFound();
  return (
    <Suspense fallback={<p role="status" className="p-8 text-sm text-muted-foreground">Loading company settings…</p>}>
      <UnifiedSettingsCenter initialCategory="company" initialTab="profile" />
    </Suspense>
  );
}
