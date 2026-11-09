"use client";
import Link from 'next/link';
import {usePathname} from 'next/navigation';
import {PanelLeftClose,PanelLeftOpen,LifeBuoy} from 'lucide-react';
import {WorkspaceSwitcher} from '@/components/workspaces/switcher';
import {useWorkspace} from '@/components/workspaces/use-workspace';
import {AccountMenu,type UserIdentity} from './account-menu';
import {Notifications} from './notifications';
export function pageTitle(path:string){if(path.startsWith('/settings'))return 'Settings';if(path.startsWith('/account'))return 'Your account';if(path.startsWith('/help'))return 'Help & support';if(path.startsWith('/find-leads'))return 'Find Leads';if(path.startsWith('/leads'))return 'Companies';if(path.startsWith('/assistant'))return 'Prospecting assistant';if(path.startsWith('/recommendations'))return 'Recommendations';if(path.startsWith('/lists'))return 'Lists';if(path.startsWith('/tasks'))return 'Tasks';if(path.startsWith('/contacts'))return 'Contacts';if(path.startsWith('/enrichment'))return 'Enrichment';if(path.startsWith('/campaigns')||path.startsWith('/scans')||path.startsWith('/discovery'))return 'Campaigns';if(path.startsWith('/outreach')||path.startsWith('/runs'))return 'Outreach';if(path.startsWith('/schedules'))return 'Schedules';return 'Overview'}
export function Header({workspaceManagementEnabled=false,collapsed=false,onToggle,mobileTrigger,user={}}:{workspaceManagementEnabled?:boolean;collapsed?:boolean;onToggle?:()=>void;mobileTrigger?:React.ReactNode;user?:UserIdentity}){
 const path=usePathname(),workspace=useWorkspace(workspaceManagementEnabled);
 return <header className="shell-header"><div className="flex min-w-0 items-center gap-3"><button className="shell-icon-button shell-desktop-toggle" onClick={onToggle} aria-label={collapsed?'Expand sidebar':'Collapse sidebar'} aria-expanded={!collapsed} aria-controls="desktop-navigation">{collapsed?<PanelLeftOpen size={19}/>:<PanelLeftClose size={19}/>}</button>{mobileTrigger}<span className="shell-page-title">{pageTitle(path)}</span></div><div className="shell-header-context">{workspaceManagementEnabled&&<WorkspaceSwitcher onSelected={()=>window.location.assign('/')}/>}</div><div className="flex shrink-0 items-center gap-1 sm:gap-2">{workspaceManagementEnabled&&workspace.active&&<Notifications/>}<Link className="shell-icon-button shell-help-action" href="/help" aria-label="Help & support"><LifeBuoy size={18}/></Link><AccountMenu user={user} workspaceManagementEnabled={workspaceManagementEnabled}/></div></header>;
}
