import { Suspense } from "react";
import { HelpCenterClient } from "@/components/help/HelpCenterClient";

export const metadata = {
  title: "Help & Support | PlaneByte",
};

export default function HelpPage() {
  return (
    <Suspense fallback={<div className="h-64 rounded-2xl border border-border bg-muted/30 animate-pulse" />}>
      <HelpCenterClient />
    </Suspense>
  );
}
