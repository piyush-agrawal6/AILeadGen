"use client";

import { CompanyProfileSettings } from "@/components/workspaces/company-profile";
import { ICPSettings } from "@/components/workspaces/icp-builder";
import { DomainSettings } from "@/components/workspaces/domains";

export function CompanySection({ activeTab }: { activeTab: string }) {
  if (activeTab === "icp") {
    return (
      <div className="space-y-6">
        <ICPSettings />
      </div>
    );
  }

  if (activeTab === "domains") {
    return (
      <div className="space-y-6">
        <DomainSettings />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <CompanyProfileSettings embedded={true} />
    </div>
  );
}
