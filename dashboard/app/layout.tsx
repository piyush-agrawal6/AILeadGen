import "@/app/globals.css";
import "@/app/planebyte-workspace.css";
import { Shell } from "@/components/layout/shell";
import { Providers } from "@/components/providers";
import type { Metadata } from "next";
import { brand } from "@/lib/brand";
import { headers,cookies } from "next/headers";
import {currentUser} from '@/lib/server/session';
import {leadEngineEnabled} from '@/lib/product-availability';

export const metadata: Metadata = {
  title: "Intent Radar | PlaneByte",
  description: "Evidence-linked intent discovery and Growth Intelligence for your workspace.",
  icons: { icon: brand.mark, apple: brand.mark },
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const publicPage=(await headers()).get('x-heysow-public-page')==='1';
  const user=publicPage?null:await currentUser();
  const collapsed=(await cookies()).get('planebyte-sidebar')?.value==='collapsed';
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen bg-background text-foreground antialiased overflow-hidden">
        {publicPage?children:<Providers><Shell user={user?{name:user.name,email:user.email,image:'image' in user?user.image as string|null:undefined}:undefined} initialCollapsed={collapsed} workspaceManagementEnabled={process.env.HEYSOW_WORKSPACE_MANAGEMENT_ENABLED==='true'} capabilities={{leadEngineAvailable:leadEngineEnabled(process.env.LEAD_ENGINE_AVAILABLE),companyDiscovery:process.env.HEYSOW_COMPANY_DISCOVERY_ENABLED==='true',customerIntegrations:process.env.HEYSOW_CUSTOMER_INTEGRATIONS_ENABLED==='true',leadAssistant:process.env.HEYSOW_LEAD_ASSISTANT_ENABLED==='true',developerApi:process.env.HEYSOW_DEVELOPER_API_ENABLED==='true'}}>{children}</Shell></Providers>}
      </body>
    </html>
  );
}
