"use client";
import Link from 'next/link';
import {usePathname} from 'next/navigation';
import * as Menu from '@radix-ui/react-dropdown-menu';
import {Layers,Radar,ChevronDown,Check} from 'lucide-react';
import {useProducts} from '@/components/workspaces/use-products';
import './product-switcher.css';
export function ProductSwitcher({onNavigate}:{onNavigate?:()=>void}){
 const path=usePathname(),access=useProducts();
 const radar=!!(path.startsWith('/intent-radar')&&access.data?.intent_radar.enabled);
 const products=[
   ...(access.data?.intent_radar.enabled?[{name:'Intent Radar',description:'Buyer intent and Growth Intelligence',href:'/intent-radar',icon:Radar,active:radar,badge:access.data.intent_radar.stage}]:[]),
   ...(access.data?.lead_engine?[{name:'Lead Engine',description:'Company research and prospecting',href:'/lead-engine',icon:Layers,active:!radar,badge:undefined}]:[]),
 ];
 return <Menu.Root>
  <Menu.Trigger className="shell-product product-switcher-trigger" aria-label="Switch PlaneByte product" title={radar?'Intent Radar':'Lead Engine'}>
   <span className="product-dot" aria-hidden="true"/>
   <span className="shell-nav-label product-switcher-name">{radar?'Intent Radar':'Lead Engine'}</span>
   <ChevronDown size={13} className="shell-nav-label" aria-hidden="true"/>
  </Menu.Trigger>
  <Menu.Portal>
   <Menu.Content className="product-menu" side="bottom" align="start" sideOffset={8} collisionPadding={12} sticky="always">
    <Menu.Label className="product-menu-label">PlaneByte products</Menu.Label>
    {products.map(({name,description,href,icon:Icon,active,badge})=><Menu.Item key={href} asChild textValue={name}>
     <Link href={href} onClick={onNavigate} className="product-menu-item" data-active={active} aria-current={active?'page':undefined}>
      <span className="product-menu-icon" aria-hidden="true"><Icon size={18}/></span>
      <span className="product-menu-copy"><strong>{name}{badge&&<span className="product-menu-badge">{badge}</span>}</strong><small>{description}</small></span>
      <span className="product-menu-indicator" aria-hidden="true">{active&&<Check size={16}/>}</span>
     </Link>
    </Menu.Item>)}
   </Menu.Content>
  </Menu.Portal>
 </Menu.Root>;
}
