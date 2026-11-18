"use client";
import {UnifiedSettingsWorkspace} from '@/components/settings/unified-workspace';
import {WorkspaceErrorBoundary} from '@/components/ui/workspace-error-boundary';
import {useState} from 'react';
import {usePathname} from 'next/navigation';
import * as Dialog from '@radix-ui/react-dialog';
import * as Tooltip from '@radix-ui/react-tooltip';
import {Menu,X} from 'lucide-react';
import {WorkspaceFeatures,CapabilityFeatures,type WorkspaceCapabilities} from '@/components/workspaces/features';
import {Header} from './header';
import {Sidebar} from './sidebar';
import {isPublicPage} from '@/lib/auth-experience';
import {WorkspaceGate} from '@/components/workspaces/gate';
import type {UserIdentity} from './account-menu';
import {FocusedOnboardingShell} from '@/components/workspaces/onboarding-shell';
export function Shell({children,workspaceManagementEnabled=false,capabilities={companyDiscovery:false},initialCollapsed=false,user={}}:{children:React.ReactNode;workspaceManagementEnabled?:boolean;capabilities?:WorkspaceCapabilities;initialCollapsed?:boolean;user?:UserIdentity}){
 const path=usePathname(),[collapsed,setCollapsed]=useState(initialCollapsed),[mobileOpen,setMobileOpen]=useState(false);
 if(isPublicPage(path))return <>{children}</>;
 function toggle(){const next=!collapsed;setCollapsed(next);document.cookie='planebyte-sidebar='+(next?'collapsed':'expanded')+'; Path=/; Max-Age=31536000; SameSite=Lax'+(window.location.protocol==='https:'?'; Secure':'')}
 const settings=path.startsWith('/settings')||path.startsWith('/account')||path==='/billing'||path==='/intent-radar/settings';
 const content=settings&&capabilities.leadEngineAvailable===false?<UnifiedSettingsWorkspace>{children}</UnifiedSettingsWorkspace>:children;
 const gated=workspaceManagementEnabled?<WorkspaceGate>{content}</WorkspaceGate>:content;
 return <WorkspaceFeatures.Provider value={workspaceManagementEnabled}><CapabilityFeatures.Provider value={capabilities}><Tooltip.Provider delayDuration={250}>{path.startsWith('/onboarding')?<FocusedOnboardingShell user={user}>{gated}</FocusedOnboardingShell>:<Dialog.Root open={mobileOpen} onOpenChange={setMobileOpen}><div className={'app-shell '+(collapsed?'sidebar-collapsed':'')}><a href="#main-content" className="shell-skip-link">Skip to content</a><div id="desktop-navigation" className="hidden min-h-0 md:flex"><Sidebar collapsed={collapsed}/></div><div className="shell-main"><Header workspaceManagementEnabled={workspaceManagementEnabled} collapsed={collapsed} onToggle={toggle} user={user} mobileTrigger={<Dialog.Trigger asChild><button className="shell-icon-button shell-mobile-toggle" aria-label="Open navigation"><Menu size={20}/></button></Dialog.Trigger>}/><main id="main-content" tabIndex={-1} className="shell-content"><WorkspaceErrorBoundary>{gated}</WorkspaceErrorBoundary></main></div></div><Dialog.Portal><Dialog.Overlay className="navigation-backdrop"/><Dialog.Content className="navigation-drawer"><Dialog.Title className="sr-only">Navigation</Dialog.Title><Dialog.Description className="sr-only">Navigate your PlaneByte workspace and available product tools.</Dialog.Description><Dialog.Close asChild><button className="shell-icon-button navigation-close" aria-label="Close navigation"><X size={19}/></button></Dialog.Close><Sidebar mobile onNavigate={()=>setMobileOpen(false)}/></Dialog.Content></Dialog.Portal></Dialog.Root>}</Tooltip.Provider></CapabilityFeatures.Provider></WorkspaceFeatures.Provider>;
}
