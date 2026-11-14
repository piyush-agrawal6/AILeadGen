"use client";
import {useWorkspaceCapabilities} from './features';
import Link from 'next/link';
import {PlaneByteBrand} from '@/components/auth/brand';
import {AccountMenu,type UserIdentity} from '@/components/layout/account-menu';
import {WorkspaceSwitcher} from './switcher';
export function FocusedOnboardingShell({children,user}:{children:React.ReactNode;user:UserIdentity}){const leadAvailable=useWorkspaceCapabilities().leadEngineAvailable!==false;return <div className="onboarding-shell"><header className="onboarding-topbar"><Link href="/settings" aria-label="PlaneByte workspace"><PlaneByteBrand/></Link><div className="flex items-center gap-4"><div className="hidden sm:block"><WorkspaceSwitcher onSelected={()=>window.location.assign('/onboarding')}/></div><AccountMenu user={user} workspaceManagementEnabled/></div></header><main id="main-content" className="onboarding-content">{children}</main><footer className="onboarding-bottom"><span>PlaneByte · {leadAvailable?'Lead Engine':'Intent Radar'}</span><Link href="/help">Need a hand?</Link></footer></div>}
