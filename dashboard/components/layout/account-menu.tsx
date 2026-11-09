"use client";
import Link from 'next/link';
import {useTheme} from 'next-themes';
import {useQuery} from '@tanstack/react-query';
import {signOut} from 'next-auth/react';
import {Check,ChevronRight,LogOut,Monitor,Moon,Settings2,Sun,UserRound,LifeBuoy} from 'lucide-react';
import {Menu,MenuContent} from '@/components/ui/menu';
import {request} from '@/lib/intelligence';
import {initials} from '@/components/workspaces/use-workspace';
export type UserIdentity={name?:string|null;email?:string|null;image?:string|null};
export function AppearanceOptions(){const {theme,setTheme}=useTheme();return <Menu.RadioGroup value={theme||'light'} onValueChange={setTheme}>{[{value:'light',label:'Light',icon:Sun},{value:'dark',label:'Dark',icon:Moon},{value:'system',label:'Use system setting',icon:Monitor}].map(({value,label,icon:Icon})=><Menu.RadioItem value={value} key={value} className="app-menu-item"><Icon size={15}/>{label}<Menu.ItemIndicator className="ml-auto"><Check size={14}/></Menu.ItemIndicator></Menu.RadioItem>)}</Menu.RadioGroup>}
export function AccountMenu({user,workspaceManagementEnabled}:{user:UserIdentity;workspaceManagementEnabled:boolean}){
 const profile=useQuery({queryKey:['account-profile'],queryFn:()=>request<{display_name:string;email:string}>('/profile'),enabled:workspaceManagementEnabled,retry:false});
 const name=profile.data?.display_name||user.name||user.email?.split('@')[0]||'Your account';const email=profile.data?.email||user.email;
 return <Menu.Root><Menu.Trigger asChild><button className="account-trigger" aria-label="Account menu"><span className="account-avatar">{initials(name)}</span></button></Menu.Trigger><MenuContent align="end" className="w-64"><Menu.Label className="app-menu-identity"><span className="block truncate font-semibold">{name}</span>{email&&<span className="mt-1 block truncate text-xs text-muted-foreground">{email}</span>}</Menu.Label><Menu.Separator className="app-menu-separator"/>
 {workspaceManagementEnabled&&<><Menu.Item asChild className="app-menu-item"><Link href="/account/profile"><UserRound size={15}/>Personal profile</Link></Menu.Item><Menu.Item asChild className="app-menu-item"><Link href="/account"><Settings2 size={15}/>Account settings</Link></Menu.Item></>}
 <Menu.Sub><Menu.SubTrigger className="app-menu-item"><Sun size={15}/>Appearance<ChevronRight size={14} className="ml-auto"/></Menu.SubTrigger><Menu.Portal><Menu.SubContent sideOffset={5} collisionPadding={12} className="app-menu min-w-48"><AppearanceOptions/></Menu.SubContent></Menu.Portal></Menu.Sub>
 <Menu.Item asChild className="app-menu-item"><Link href="/help"><LifeBuoy size={15}/>Help & support</Link></Menu.Item><Menu.Separator className="app-menu-separator"/><Menu.Item className="app-menu-item" onSelect={()=>void signOut({callbackUrl:'/login'})}><LogOut size={15}/>Sign out</Menu.Item>
 </MenuContent></Menu.Root>;
}
