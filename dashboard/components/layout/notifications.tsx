"use client";
import {useState} from 'react';
import {useQuery} from '@tanstack/react-query';
import {Bell} from 'lucide-react';
import Link from 'next/link';
import {Menu,MenuContent} from '@/components/ui/menu';
import {request} from '@/lib/intelligence';
export function Notifications(){
 const [open,setOpen]=useState(false);
 const query=useQuery({queryKey:['workspace-notifications'],queryFn:()=>request<{items:{id:string;kind:string;created_at:string}[]}>('/organization/notifications'),enabled:open,retry:false});
 return <Menu.Root open={open} onOpenChange={setOpen}><Menu.Trigger asChild><button className="shell-icon-button" aria-label="Workspace notifications"><Bell size={18}/></button></Menu.Trigger><MenuContent align="end" className="w-80 max-w-[calc(100vw-24px)]"><Menu.Label className="px-3 py-2 text-sm font-semibold">Workspace updates</Menu.Label><Menu.Separator className="app-menu-separator"/>{query.isPending?<p role="status" className="p-3 text-sm text-muted-foreground">Loading updates…</p>:query.isError?<div className="p-3"><p role="alert" className="text-sm">Updates could not be loaded.</p><Menu.Item className="app-menu-item mt-2" onSelect={event=>{event.preventDefault();void query.refetch()}}>Retry updates</Menu.Item></div>:query.data?.items.length?<div className="max-h-80 overflow-y-auto">{query.data.items.map(item=><div className="border-b px-3 py-3 last:border-0" key={item.id}><p className="text-sm">{item.kind==='INVITATION_ACCEPTED'?'A teammate accepted an invitation':item.kind==='INVITATION_REJECTED'?'A teammate declined an invitation':item.kind==='INTENT_RADAR'?<Link href="/intent-radar/alerts" onClick={()=>setOpen(false)}>Intent Radar monitor activity — review alerts</Link>:'Workspace activity recorded'}</p><p className="mt-1 text-xs text-muted-foreground">{new Date(item.created_at).toLocaleString()}</p></div>)}</div>:<p className="p-3 text-sm text-muted-foreground">No workspace updates yet.</p>}</MenuContent></Menu.Root>;
}
