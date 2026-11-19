"use client";

import { usePathname } from "next/navigation";
import { ICPDashboard } from "./ICPDashboard";
import { ICPBuilderPage } from "./ICPBuilderPage";
import { ICPComparePage } from "./ICPComparePage";
import { ICPDetailPage } from "./ICPDetailPage";

export function IdealCustomersWorkspace({
  route,
  id: explicitId,
}: {
  route?: string;
  id?: string;
} = {}) {
  const pathname = usePathname() || "";
  const effectiveRoute = route || pathname.replace(/^\/intent-radar\/?/, "");

  // Route: /intent-radar/ideal-customers/new
  if (effectiveRoute === "ideal-customers/new") {
    return <ICPBuilderPage />;
  }

  // Route: /intent-radar/ideal-customers/compare
  if (effectiveRoute === "ideal-customers/compare") {
    return <ICPComparePage />;
  }

  // Check for dynamic subroutes: /intent-radar/ideal-customers/:id/edit or /intent-radar/ideal-customers/:id
  const parts = effectiveRoute.split("/");
  if (parts[0] === "ideal-customers" && parts[1]) {
    const targetId = explicitId || parts[1];
    if (parts[2] === "edit") {
      return <ICPBuilderPage existingId={targetId} />;
    }
    return <ICPDetailPage id={targetId} />;
  }

  // Default: ICP Dashboard
  return <ICPDashboard />;
}
