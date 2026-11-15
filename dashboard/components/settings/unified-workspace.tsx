"use client";
import Link from 'next/link';
import {usePathname} from 'next/navigation';
import {UserRound,Building2,Link2,Users,Radio,CreditCard,Code2,ShieldCheck,X,Target,Globe} from 'lucide-react';
import {useWorkspace} from '@/components/workspaces/use-workspace';
import {useWorkspaceCapabilities} from '@/components/workspaces/features';
const sections=[
 {href:'/account/profile',title:'Account',description:'Your profile and verified sign-in identity.',icon:UserRound},
 {href:'/settings/company',title:'Company',description:'Business context shared by discovery and research.',icon:Building2},
 {href:'/settings/icp',title:'Ideal customers',description:'Review who you serve and how research is matched.',icon:Target},
 {href:'/intent-radar/integrations',title:'Connected accounts',description:'Available providers and genuine connection status.',icon:Link2},
 {href:'/settings/members',title:'Team & permissions',description:'Members, workspace roles and access.',icon:Users},
 {href:'/intent-radar/settings',title:'Sources & preferences',description:'Research defaults, alerts and source retention.',icon:Radio},
 {href:'/billing',title:'Billing & usage',description:'Current access, remaining allowance and plan details.',icon:CreditCard},
 {href:'/settings/developer',title:'Developer access',description:'Manage scoped API keys and MCP access.',icon:Code2},
 {href:'/account/security',title:'Security',description:'Verified identity and sign-in protection.',icon:ShieldCheck},
 {href:'/settings/domains',title:'Business domains',description:'Review workspace domain verification.',icon:Globe},
];
export function UnifiedSettingsWorkspace({children}:{children:React.ReactNode}){
 const path=usePathname(),workspace=useWorkspace(),capabilities=useWorkspaceCapabilities();
 const visible=sections.filter(s=>s.href!=='/settings/developer'||capabilities.developerApi&&workspace.canManage);
 const selected=visible.find(s=>s.href===path)||visible.find(s=>path.startsWith('/settings/team')||path.startsWith('/settings/access')?s.href==='/settings/members':path.startsWith('/account')?s.href==='/account/profile':false);
 return <div className="pb-settings-stage"><div className="pb-settings-workspace"><aside><h2>Settings</h2><nav aria-label="Unified settings">{visible.map(({href,title,icon:Icon})=><Link href={href} key={href} aria-current={selected?.href===href?'page':undefined}><Icon size={17}/>{title}</Link>)}</nav><Link className="pb-settings-overview" href="/settings">Workspace overview →</Link></aside><section className="pb-settings-body"><header><div><h2>{selected?.title||'Workspace'}</h2><p>{selected?.description||'Manage your workspace and account.'}</p></div><Link href="/intent-radar" aria-label="Close settings" className="shell-icon-button"><X size={20}/></Link></header><div className="pb-settings-scroll">{children}</div></section></div></div>;
}
