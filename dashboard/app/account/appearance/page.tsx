"use client";
import {useTheme} from 'next-themes';
import {useSyncExternalStore} from 'react';
import {Sun,Moon,Monitor} from 'lucide-react';
const subscribe=()=>()=>{};
export default function Appearance(){const {theme,setTheme}=useTheme();const mounted=useSyncExternalStore(subscribe,()=>true,()=>false);return <section className="settings-page"><header><p className="page-eyebrow">Personal preferences</p><h1>Appearance</h1><p>Choose how PlaneByte looks on this browser. Your company settings are unchanged.</p></header><fieldset className="appearance-choices"><legend className="sr-only">Color theme</legend>{[{value:'light',title:'Light',icon:Sun},{value:'dark',title:'Dark',icon:Moon},{value:'system',title:'System',icon:Monitor}].map(({value,title,icon:Icon})=><label key={value} data-selected={mounted&&theme===value}><input type="radio" name="appearance" value={value} checked={mounted&&theme===value} onChange={()=>setTheme(value)}/><Icon size={25}/><strong>{title}</strong></label>)}</fieldset><p className="text-sm text-muted-foreground">The sidebar preference is saved separately. Use the navigation toggle to expand or collapse it.</p></section>}
