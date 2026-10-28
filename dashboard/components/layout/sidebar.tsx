"use client";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { Gauge, Radar, Plus, Building2, Files, Settings2, Activity } from "lucide-react";
const items = [
  { href:"/", title:"Overview", icon:Gauge },
  { href:"/scans/new", title:"New scan", icon:Plus },
  { href:"/scans", title:"Campaigns & scans", icon:Radar },
  { href:"/leads", title:"Lead workspace", icon:Building2 },
  { href:"/outreach", title:"Outreach", icon:Activity },
  { href:"/reports", title:"Reports & exports", icon:Files },
];
export function Sidebar() {
  const path=usePathname();
  const active=(href:string)=>path===href||(href==="/leads"&&path.startsWith("/leads/"))||(href==="/scans"&&(path.startsWith("/campaigns/")||/^\/scans\/\d+/.test(path)));
  return <aside className="flex w-14 shrink-0 flex-col border-r bg-card md:w-52">
    <Link href="/" className="flex h-16 items-center gap-3 border-b px-3 md:px-5" aria-label="PlaneByte overview"><Image src="/logo.png" width={30} height={30} alt="" className="shrink-0 rounded-md"/><span className="hidden text-[17px] font-bold tracking-tight md:inline">PlaneByte</span></Link>
    <div className="hidden px-5 pb-3 pt-7 text-[9px] font-semibold uppercase tracking-[.16em] text-muted-foreground md:block">Workspace</div>
    <nav aria-label="Main navigation" className="space-y-1 px-2 pt-4 md:pt-0">{items.map(({href,title,icon:Icon})=><Link href={href} key={href} title={title} aria-current={active(href)?"page":undefined} className={"flex items-center gap-3 rounded px-2 py-2.5 text-xs transition-colors "+(active(href)?"bg-primary/10 font-semibold text-primary":"text-muted-foreground hover:bg-muted/60 hover:text-foreground")}><Icon className="h-4 w-4 shrink-0"/><span className="hidden md:inline">{title}</span></Link>)}</nav>
    <nav aria-label="Workspace settings" className="mt-auto space-y-1 px-2 pb-5">{[{href:"/settings",title:"Preferences",icon:Settings2},{href:"/system",title:"System health",icon:Activity}].map(({href,title,icon:Icon})=><Link href={href} key={href} title={title} className="flex items-center gap-3 rounded px-2 py-2.5 text-xs text-muted-foreground hover:bg-muted"><Icon className="h-4 w-4"/><span className="hidden md:inline">{title}</span></Link>)}</nav>
    <div className="hidden border-t px-5 py-4 md:block"><p className="text-xs font-medium">PlaneByte</p><p className="mt-1 text-[10px] text-muted-foreground">Private lead intelligence</p></div>
  </aside>;
}

