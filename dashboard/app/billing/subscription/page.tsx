import { redirect } from "next/navigation";

export const metadata = { title: "Billing & Usage · PlaneByte" };

export default async function Page({
  searchParams,
}: {
  searchParams: Promise<{ plan?: string; payment?: string }>;
}) {
  const params = await searchParams;
  const qs = new URLSearchParams({ category: "billing" });
  if (params.plan && ["starter", "growth", "scale"].includes(params.plan)) {
    qs.set("tab", "plans");
    qs.set("plan", params.plan);
  } else {
    qs.set("tab", "overview");
  }
  if (params.payment === "returned") {
    qs.set("payment", "returned");
  }
  redirect(`/settings?${qs.toString()}`);
}
