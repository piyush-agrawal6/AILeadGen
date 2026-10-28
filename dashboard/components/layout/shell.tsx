"use client";
import { usePathname } from "next/navigation";
import { Header } from "./header";
import { Sidebar } from "./sidebar";
export function Shell({ children }: { children: React.ReactNode }) {
  if (usePathname() === "/login") return <main>{children}</main>;
  return <div className="flex h-dvh w-full overflow-hidden"><Sidebar/><div className="flex min-w-0 flex-1 flex-col"><Header/><main className="flex-1 overflow-y-auto p-5 md:p-8">{children}</main></div></div>;
}
