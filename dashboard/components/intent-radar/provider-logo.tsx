"use client";

import Image from 'next/image';
import {Blocks, Code2, Video, Radio, MessageSquare, Rss, Atom} from 'lucide-react';

const logos: Readonly<Record<string, {src: string; alt: string}>> = {
  'hacker news': {src: '/integrations/hacker-news.svg', alt: 'Hacker News — Y Combinator Y logo'},
  hn: {src: '/integrations/hacker-news.svg', alt: 'Hacker News — Y Combinator Y logo'},
  'visual studio code': {src: '/integrations/vscode.png', alt: 'Visual Studio Code logo'},
  vscode: {src: '/integrations/vscode.png', alt: 'Visual Studio Code logo'},
};

export function ProviderLogo({provider, size = 32}: {provider: string; size?: number}) {
  const key = provider.trim().toLowerCase();
  const logo = Object.hasOwn(logos, key) ? logos[key] : undefined;
  const dimension = Number.isFinite(size) ? Math.min(128, Math.max(16, size)) : 32;
  if (logo) return <Image className="ir-provider-logo" src={logo.src} alt={logo.alt} width={dimension} height={dimension} unoptimized/>;
  const iconSize = Math.max(16, Math.round(dimension * 0.72));
  const Icon = key.includes('github') ? Code2 : key.includes('youtube') ? Video : key.includes('bluesky') ? Radio : key.includes('stack') || key.includes('discourse') ? MessageSquare : key.includes('atom') ? Atom : key.includes('rss') ? Rss : Blocks;
  return <span className="ir-provider-fallback" role="img" aria-label={`${provider} — source icon`}><Icon size={iconSize} aria-hidden="true"/></span>;
}
