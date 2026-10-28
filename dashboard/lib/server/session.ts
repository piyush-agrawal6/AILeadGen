import { auth } from "@/auth";
import "server-only";
import { serverEnv } from "./env";
export async function currentUser() {
  const env = serverEnv();
  if (!env.production && process.env.AUTH_DISABLED_LOCAL === "true") return { email: env.allowed[0] || "local@localhost", name: "Local development" };
  const session = await auth();
  return session?.user?.email && env.allowed.includes(session.user.email.toLowerCase()) ? session.user : null;
}
