"use client";

import Image from 'next/image';
import {Blocks} from 'lucide-react';

const logos: Readonly<Record<string, {src: string; alt: string}>> = {
  'hacker news': {src: '/integrations/hacker-news.svg', alt: 'Hacker News — Y Combinator Y logo'},
  hn: {src: '/integrations/hacker-news.svg', alt: 'Hacker News — Y Combinator Y logo'},
  'visual studio code': {src: '/integrations/vscode.png', alt: 'Visual Studio Code logo'},
  vscode: {src: '/integrations/vscode.png', alt: 'Visual Studio Code logo'},
};

export function ProviderLogo({provider, size = 32}: {provider: string; size?: number}) {
  const logo = Object.hasOwn(logos, provider.trim().toLowerCase()) ? logos[provider.trim().toLowerCase()] : undefined;
  const dimension = Number.isFinite(size) ? Math.min(128, Math.max(16, size)) : 32;
  return logo ? <Image className="ir-provider-logo" src={logo.src} alt={logo.alt} width={dimension} height={dimension} unoptimized/> :
    <span className="ir-provider-fallback" role="img" aria-label={`${provider} — neutral integration icon`}><Blocks size={dimension} aria-hidden="true"/></span>;
}
