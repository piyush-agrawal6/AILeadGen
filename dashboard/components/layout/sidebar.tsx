"use client";
import Link from 'next/link';
import {usePathname} from 'next/navigation';
import * as Tooltip from '@radix-ui/react-tooltip';
import {Gauge,Search,Building2,Users,Sparkles,Target,Radar,Inbox,CalendarClock,ListTodo,List,Settings2,LifeBuoy,Plug,Network,CreditCard,type LucideIcon} from 'lucide-react';
import {PlaneByteBrand} from '@/components/auth/brand';
import {brand} from '@/lib/brand';
import {useWorkspaceManagement,useWorkspaceCapabilities} from '@/components/workspaces/features';
import {Activity,Radio,Bookmark,Bell} from 'lucide-react';
import {useProducts} from '@/components/workspaces/use-products';
import {isLeadEnginePage} from '@/lib/product-availability';
type Item={href:string;title:string;icon:LucideIcon};
export function Sidebar({collapsed=false,onNavigate,mobile=false}:{collapsed?:boolean;onNavigate?:()=>void;mobile?:boolean}){
 const path=usePathname(),management=useWorkspaceManagement(),capabilities=useWorkspaceCapabilities();
 const products=useProducts(),leadAvailable=capabilities.leadEngineAvailable!==false;
 const isLeadPage=leadAvailable&&(path==='/'||isLeadEnginePage(path));
 const radar=!isLeadPage;
 const groups:{name:string;items:Item[]}[]=[{name:'Prospecting',items:[{href:'/lead-engine',title:'Overview',icon:Gauge},{href:'/find-leads',title:'Find Leads',icon:Search},{href:'/leads',title:'Companies',icon:Building2},{href:'/contacts',title:'Contacts',icon:Users},{href:'/enrichment',title:'Enrichment',icon:Sparkles},...(management?[{href:'/settings/icp',title:'Ideal customers',icon:Target}]:[])]},{name:'Sales',items:[{href:'/lists',title:'Lists',icon:List},{href:'/tasks',title:'Tasks',icon:ListTodo},{href:'/campaigns',title:'Campaigns',icon:Radar},{href:'/outreach',title:'Outreach',icon:Inbox},{href:'/schedules',title:'Schedules',icon:CalendarClock}]},...(management?[{name:'Intelligence',items:[{href:'/recommendations',title:'Recommendations',icon:Sparkles},...(capabilities.leadAssistant?[{href:'/assistant',title:'AI Assistant',icon:Sparkles}]:[])]}]:[]),...(capabilities.customerIntegrations?[{name:'Tools',items:[{href:'/settings/integrations',title:'Connections',icon:Plug}]}]:[])];
 const radarGroups:{name:string;items:Item[]}[]=[
 {name:'Workspace',items:[{href:'/intent-radar',title:'Home',icon:Gauge},{href:'/intent-radar/discover',title:'Discover',icon:Search},{href:'/intent-radar/signals',title:'Signals',icon:Activity},{href:'/intent-radar/opportunities',title:'Opportunities',icon:Target},{href:'/intent-radar/monitors',title:'Monitoring',icon:Radio}]},
 {name:'Intelligence',items:[{href:'/intent-radar/ideal-customers',title:'Ideal Customers',icon:Users},...(products.data?.intent_radar.growth_enabled?[{href:'/intent-radar/growth',title:'Growth Intelligence',icon:Sparkles}]:[]),{href:'/intent-radar/graph',title:'Intelligence Graph',icon:Network},{href:'/intent-radar/saved',title:'Research Library',icon:Bookmark}]}];
 function active(href:string){return path===href||(href!=='/'&&href!=='/intent-radar'&&href!=='/intent-radar/growth'&&path.startsWith(href+'/'))||(href==='/settings'&&(path.startsWith('/settings')||path.startsWith('/account')||path.startsWith('/billing')))||(href==='/campaigns'&&/^\/(?:scans|discovery)\/\d+/.test(path))}
 function item({href,title,icon:Icon}:Item){const link=<Link href={href} onClick={onNavigate} aria-label={title} aria-current={active(href)?'page':undefined} className={'shell-nav-link '+(active(href)?'is-active':'')}><Icon size={18}/><span className="shell-nav-label">{title}</span></Link>;return collapsed&&!mobile?<Tooltip.Root key={href}><Tooltip.Trigger asChild>{link}</Tooltip.Trigger><Tooltip.Portal><Tooltip.Content className="nav-tooltip" side="right" sideOffset={12}>{title}<Tooltip.Arrow/></Tooltip.Content></Tooltip.Portal></Tooltip.Root>:<div key={href}>{link}</div>}
 return <aside className={'shell-sidebar '+(collapsed&&!mobile?'is-collapsed':'')+(mobile?' is-mobile':'')} aria-label="Product navigation"><Link href="/intent-radar" className="shell-brand" onClick={onNavigate} aria-label="PlaneByte Intent Radar"><PlaneByteBrand compact/><span className="shell-nav-label font-semibold">{brand.name}</span></Link><nav aria-label="Main navigation" className="shell-nav">{(radar?(products.data?.intent_radar.enabled?radarGroups:[]):products.data?.lead_engine?groups:[]).map(group=><section key={group.name} className="shell-nav-group"><p className="shell-nav-heading">{group.name}</p>{group.items.map(item)}</section>)}</nav><nav aria-label="Workspace settings" className="shell-nav shell-nav-bottom">{[{href:'/settings',title:'Settings',icon:Settings2},{href:'/help',title:'Help & support',icon:LifeBuoy}].map(item)}</nav><p className="shell-sidebar-footer shell-nav-label">{radar?'Public conversation intelligence':'Your prospecting workspace'}</p></aside>;
}
