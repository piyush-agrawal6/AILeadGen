"use client";
import Link from 'next/link';
import {useEffect} from 'react';
import {usePathname,useRouter} from 'next/navigation';
import {useWorkspace} from './use-workspace';
import {Button} from '@/components/ui/button';
export type {WorkspaceSummary} from './use-workspace';
function ResumeOwnerSetup(){
 const router=useRouter();useEffect(()=>{router.replace('/onboarding')},[router]);
 return <p role="status">Resuming your saved company setup…</p>;
}
export function WorkspaceGate({children}:{children:React.ReactNode}){
 const path=usePathname(),state=useWorkspace();
 if(state.isPending)return <p role="status" className="text-sm text-muted-foreground">Loading your workspace…</p>;
 if(state.isError)return <section className="settings-page"><header><h1>Your workspace could not be loaded</h1><p>Retry or sign out and sign in again with your permitted account.</p></header><Button onClick={()=>void state.refetch()}>Retry workspace access</Button></section>;
 const personal=path==='/account'||path.startsWith('/account/')||path==='/help';
 const create=path==='/settings/workspaces'||path==='/settings'||path==='/settings/profile';
 if(!state.data.items.length&&!personal&&!create)return <section className="workspace-welcome"><p className="page-eyebrow">PlaneByte · Intent Radar</p><h1>Welcome to PlaneByte</h1><p>Your verified account is signed in. Create a company workspace to set up your profile and ideal customers, or accept an invitation from your team.</p><Link className="control ops-primary inline-flex" href="/settings/workspaces">Create your workspace</Link></section>;
 if(state.data.items.length&&!state.data.active_organization_id&&!personal&&!create)return <section className="workspace-welcome"><h1>Choose your workspace</h1><p>Select a workspace from the menu above. Each company has its own data and permissions.</p></section>;
 const setup=personal||path==='/billing'||path.startsWith('/billing/')||path==='/settings'||path.startsWith('/settings/')||path.startsWith('/onboarding')||path==='/acquisition/sheets/callback';
 const incomplete=Boolean(state.data.active_organization_id&&state.data.active_onboarding_status!=='COMPLETED');
 const deferred=Boolean(state.data.active_onboarding_deferred);
 if(incomplete&&!deferred&&!setup&&state.active?.role==='OWNER')return <ResumeOwnerSetup/>;
 if(incomplete&&!deferred&&!setup)return <section className="workspace-welcome"><p className="page-eyebrow">Your next step</p><h1>Finish setting up your workspace</h1><p>Confirm your company information and ideal customers to establish your workspace context. Your permitted workspace settings are already available.</p><div className="flex flex-wrap gap-3"><Link className="control ops-primary inline-flex" href="/onboarding">Resume company setup</Link><Link className="control inline-flex" href="/settings">Open settings</Link></div></section>;
 if(incomplete&&deferred&&!setup){
  return <>
   <div role="status" className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border bg-card/90 px-4 py-2.5 text-sm shadow-sm">
    <span><strong>Finish setting up your workspace</strong> — your onboarding progress is saved. Resume anytime to complete your ICPs and research preferences.</span>
    <Link className="control ops-primary inline-flex text-xs" href="/onboarding">Resume Onboarding →</Link>
   </div>
   {children}
  </>;
 }
 return <>{children}</>;
}
