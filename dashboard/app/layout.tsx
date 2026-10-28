import "@/app/globals.css";
import { Shell } from "@/components/layout/shell";
import { Providers } from "@/components/providers";
import type { Metadata } from "next";
import { headers } from "next/headers";

export const metadata: Metadata = {
  title: "PlaneByte | Lead Intelligence",
  description: "PlaneByte private business intelligence and client website reviews",
  icons: { icon: "/logo.png", apple: "/logo.png" },
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  await headers();
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen bg-background text-foreground antialiased overflow-hidden">
        <Providers>
          <Shell>{children}</Shell>
        </Providers>
      </body>
    </html>
  );
}
