"use client";
import Link from 'next/link';
import {usePathname} from 'next/navigation';
import {ChevronDown} from 'lucide-react';
import {Menu,MenuContent} from '@/components/ui/menu';
export type SettingsSection={name:string;links:{href:string;title:string}[]};
export function SectionNavigation({sections,label='Settings categories'}:{sections:SettingsSection[];label?:string}){
 const path=usePathname();const title=sections.flatMap(section=>section.links).find(link=>link.href===path)?.title||'Settings overview';
 return <><nav className="settings-desktop-navigation" aria-label={label}>{sections.filter(section=>section.links.length).map(section=><section className="settings-nav-group" key={section.name}><h2>{section.name}</h2>{section.links.map(link=><Link key={link.href} href={link.href} aria-current={path===link.href?'page':undefined}>{link.title}</Link>)}</section>)}</nav><div className="settings-mobile-navigation"><Menu.Root><Menu.Trigger className="settings-category-trigger" aria-label={label}>{title}<ChevronDown size={16}/></Menu.Trigger><MenuContent align="start" className="w-72 max-w-[calc(100vw-32px)]">{sections.filter(section=>section.links.length).map(section=><Menu.Group key={section.name}><Menu.Label className="settings-menu-heading">{section.name}</Menu.Label>{section.links.map(link=><Menu.Item asChild className="app-menu-item" key={link.href}><Link href={link.href} aria-current={path===link.href?'page':undefined}>{link.title}</Link></Menu.Item>)}</Menu.Group>)}</MenuContent></Menu.Root></div></>;
}
