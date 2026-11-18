"use client";

import Link from "next/link";
import { CompanyProfileSettings } from "@/components/workspaces/company-profile";
import { DomainSettings } from "@/components/workspaces/domains";

export function CompanySection({ activeTab }: { activeTab: string }) {
  if (activeTab === "domains") {
    return (
      <div className="space-y-6">
        <DomainSettings />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-border bg-muted/20 px-4 py-3 text-xs text-muted-foreground flex flex-wrap items-center justify-between gap-2">
        <span>
          Ideal Customer Profiles (ICP) now have a dedicated workspace under <strong>Intelligence → Ideal Customers</strong>.
        </span>
        <Link
          href="/intent-radar/ideal-customers"
          className="font-semibold text-primary hover:underline shrink-0"
        >
          Open Ideal Customers →
        </Link>
      </div>
      <CompanyProfileSettings embedded={true} />
    </div>
  );
}
