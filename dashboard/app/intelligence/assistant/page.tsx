import { Suspense } from "react";
import { AssistantPageClient } from "@/components/intelligence/AssistantPageClient";

export const metadata = {
  title: "AI Assistant | PlaneByte",
};

export default function IntelligenceAssistantPage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-[calc(100vh-5rem)] items-center justify-center rounded-2xl border border-border bg-card text-sm text-muted-foreground">
          Loading AI Assistant…
        </div>
      }
    >
      <AssistantPageClient />
    </Suspense>
  );
}
