"use client";
import { useWorkspaceCapabilities } from './features';
import Link from 'next/link';
import { PlaneByteBrand } from '@/components/auth/brand';
import { AccountMenu, type UserIdentity } from '@/components/layout/account-menu';
import { WorkspaceSwitcher } from './switcher';
export function FocusedOnboardingShell({ children, user }: { children: React.ReactNode; user: UserIdentity }) { return <div className="onboarding-shell"><header className="onboarding-topbar"><Link href="/intent-radar" aria-label="PlaneByte workspace"><PlaneByteBrand /></Link><div className="flex items-center gap-4"><div className="hidden sm:block"><WorkspaceSwitcher onSelected={() => window.location.assign('/onboarding')} /></div><AccountMenu user={user} workspaceManagementEnabled /></div></header><main id="main-content" className="onboarding-content">{children}</main><footer className="onboarding-bottom"><span>PlaneByte · Intent Radar</span><nav aria-label="Legal and help" className="flex flex-wrap items-center gap-4"><Link href="/privacy">Privacy</Link><Link href="/terms">Terms</Link><Link href="/sources-policy">Sources</Link><Link href="/acceptable-use">Acceptable Use</Link><Link href="/help">Need a hand?</Link></nav></footer></div> }
