"use client";
import { useTheme } from "next-themes";
import { usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { request } from "@/lib/intelligence";
import { signOut } from "next-auth/react";
import { Sun, Moon, Monitor } from "lucide-react";
export function Header() {
  const {theme,setTheme}=useTheme(); const path=usePathname();
  const attention=useQuery({queryKey:["outreach-indicator"],queryFn:()=>request<{counts:Record<string,number>}>("/sales/outreach?queue=today&page_size=1&tz="+encodeURIComponent(Intl.DateTimeFormat().resolvedOptions().timeZone)),refetchInterval:60000});
  const title=path.startsWith("/outreach")?"Outreach":path.startsWith("/leads")?"Lead workspace":path.startsWith("/campaigns")?"Campaign":path.startsWith("/scans")?"Discovery":path.startsWith("/reports")?"Reports":path.startsWith("/system")?"System":"Workspace";
  return <header className="flex h-16 shrink-0 items-center justify-between border-b px-5 md:px-8"><div className="flex items-center gap-3 text-xs"><span className="hidden text-muted-foreground sm:inline">PlaneByte</span><span className="hidden text-border sm:inline">/</span><span>{title}</span></div><div className="flex items-center gap-3"><Link href="/outreach" className="hidden text-[10px] text-muted-foreground sm:block">{attention.data?attention.data.counts.today||0:"—"} follow-ups · {attention.data?attention.data.counts.replied||0:"—"} replies</Link><div aria-label="Color theme" className="flex items-center gap-1">{[{key:"light",icon:Sun},{key:"dark",icon:Moon},{key:"system",icon:Monitor}].map(({key,icon:Icon})=><button key={key} aria-label={key+" theme"} aria-pressed={theme===key} onClick={()=>setTheme(key)} className="rounded p-1.5 text-muted-foreground hover:bg-muted"><Icon className="h-3.5 w-3.5"/></button>)}</div><button className="border-l pl-3 text-xs text-muted-foreground hover:text-foreground" onClick={()=>signOut({callbackUrl:"/login"})}>Sign out</button></div></header>;
}

