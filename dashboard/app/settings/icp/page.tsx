import { notFound, redirect } from "next/navigation";

export default function ICP() {
  if (process.env.HEYSOW_WORKSPACE_MANAGEMENT_ENABLED !== "true") notFound();
  redirect("/intent-radar/ideal-customers");
}
