import { Suspense } from "react";
import { UnifiedSettingsCenter } from "@/components/settings/unified-settings-center";

export default function NotificationsPage() {
  return (
    <Suspense fallback={<p role="status" className="p-8 text-sm text-muted-foreground">Loading notification settings…</p>}>
      <UnifiedSettingsCenter initialCategory="notifications" initialTab="channels" />
    </Suspense>
  );
}
