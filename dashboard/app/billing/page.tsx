import { Suspense } from "react";
import { UnifiedSettingsCenter } from "@/components/settings/unified-settings-center";

export const metadata = { title: "Billing & usage | PlaneByte" };

export default async function BillingPage({
  searchParams,
}: {
  searchParams: Promise<{ plan?: string; tab?: string }>;
}) {
  const p = await searchParams;
  const initialTab = p.plan || p.tab === "plans" ? "plans" : "overview";

  return (
    <Suspense fallback={<p role="status" className="p-8 text-sm text-muted-foreground">Loading billing & usage…</p>}>
      <UnifiedSettingsCenter initialCategory="billing" initialTab={initialTab} />
    </Suspense>
  );
}
