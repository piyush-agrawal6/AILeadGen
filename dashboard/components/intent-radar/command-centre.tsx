"use client";

import Link from "next/link";
import { Activity, Radio, Search, Sparkles } from "lucide-react";
import { useRadarCapabilities } from "./provider";

export function CommandCentre() {
  const access = useRadarCapabilities();
  const assistantAvailable = Boolean(access.data?.growth_enabled);

  return (
    <section
      className="pb-command-centre"
      aria-label="Discovery launchpad"
    >
      <p className="pb-command-eyebrow">PLANEBYTE INTENT RADAR</p>
      <h1>Find your next opportunity.</h1>
      <p className="max-w-xl">
        Discover relevant conversations, track emerging needs, and turn signals
        into opportunities.
      </p>
      <div className="mt-2 flex flex-wrap items-center justify-center gap-2">
        <Link
          className="ir-button ir-primary inline-flex items-center gap-1.5 text-xs font-semibold"
          href="/intent-radar/discover"
        >
          <Search size={14} />
          Discover Intent
        </Link>
        <Link
          className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border bg-card/90 px-3.5 text-xs font-medium text-foreground shadow-sm hover:border-primary/40 hover:bg-card transition-colors"
          href="/intent-radar/monitors/new"
        >
          <Radio size={14} className="text-primary" />
          Create Monitor
        </Link>
        <Link
          className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border bg-card/90 px-3.5 text-xs font-medium text-foreground shadow-sm hover:border-primary/40 hover:bg-card transition-colors"
          href="/intent-radar/signals"
        >
          <Activity size={14} className="text-primary" />
          Explore Signals
        </Link>
        {assistantAvailable && (
          <Link
            className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-primary/25 bg-card/90 px-3.5 text-xs font-medium text-primary shadow-sm hover:border-primary/50 hover:bg-primary/5 transition-colors"
            href="/intelligence/assistant"
          >
            <Sparkles size={14} />
            Open AI Assistant
          </Link>
        )}
      </div>
    </section>
  );
}
