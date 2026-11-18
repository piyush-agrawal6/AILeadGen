"use client";

import type { IntentSignal } from "@/lib/intent-radar";

export const SIGNALS_RETURN_KEY = "planebyte:signals-return";

export interface SignalsReturnContext {
  returnUrl: string;
  scrollY: number;
  orderedIds: string[];
  savedAt: number;
}

export function saveSignalsReturnContext(ctx: Omit<SignalsReturnContext, "savedAt">) {
  if (typeof window === "undefined") return;
  try {
    const payload: SignalsReturnContext = { ...ctx, savedAt: Date.now() };
    window.sessionStorage.setItem(SIGNALS_RETURN_KEY, JSON.stringify(payload));
  } catch {
    // Ignore storage quota / private-mode restrictions
  }
}

export function readSignalsReturnContext(): SignalsReturnContext | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.sessionStorage.getItem(SIGNALS_RETURN_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<SignalsReturnContext>;
    if (!parsed || typeof parsed.returnUrl !== "string" || !parsed.returnUrl.startsWith("/intent-radar/signals")) {
      return null;
    }
    return {
      returnUrl: parsed.returnUrl,
      scrollY: typeof parsed.scrollY === "number" ? parsed.scrollY : 0,
      orderedIds: Array.isArray(parsed.orderedIds) ? parsed.orderedIds.filter((x): x is string => typeof x === "string") : [],
      savedAt: typeof parsed.savedAt === "number" ? parsed.savedAt : 0,
    };
  } catch {
    return null;
  }
}

export function formatObservedDate(iso: string): { short: string; full: string } {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return { short: iso.slice(0, 10), full: iso };
  return {
    short: d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }),
    full: d.toLocaleString(),
  };
}

export function statusPillClasses(status: string): string {
  switch (status) {
    case "Qualified":
      return "border-emerald-500/30 bg-emerald-500/12 text-emerald-700 dark:text-emerald-300";
    case "Reviewed":
      return "border-blue-500/25 bg-blue-500/10 text-blue-700 dark:text-blue-300";
    case "In Review":
    case "Needs Review":
      return "border-amber-500/30 bg-amber-500/12 text-amber-700 dark:text-amber-300";
    case "Dismissed":
      return "border-border bg-muted/60 text-muted-foreground";
    case "Saved":
      return "border-violet-500/25 bg-violet-500/10 text-violet-700 dark:text-violet-300";
    case "New":
    default:
      return "border-sky-500/25 bg-sky-500/10 text-sky-700 dark:text-sky-300";
  }
}

export function buyingIntentDisplay(signal: IntentSignal): { label: string; shortLabel: string; tone: string } {
  if (signal.buying_intent_basis === "ai_assessed" && signal.buying_intent) {
    switch (signal.buying_intent) {
      case "Explicit commercial intent":
        return {
          label: "Explicit commercial intent",
          shortLabel: "Explicit intent",
          tone: "border-emerald-500/30 bg-emerald-500/12 text-emerald-700 dark:text-emerald-300",
        };
      case "Possible commercial intent":
        return {
          label: "Possible commercial intent",
          shortLabel: "Possible intent",
          tone: "border-amber-500/30 bg-amber-500/12 text-amber-700 dark:text-amber-300",
        };
      case "No demonstrated commercial intent":
        return {
          label: "No demonstrated commercial intent",
          shortLabel: "Non-commercial",
          tone: "border-border bg-muted/60 text-muted-foreground",
        };
      case "Insufficient evidence":
      default:
        return {
          label: "Insufficient evidence",
          shortLabel: "Insufficient",
          tone: "border-border bg-muted/50 text-muted-foreground",
        };
    }
  }
  return {
    label: "Not assessed",
    shortLabel: "Not assessed",
    tone: "border-border/70 bg-transparent text-muted-foreground",
  };
}

export function provenanceSummary(signal: IntentSignal): {
  author: string | null;
  authorUrl: string | null;
  repo: string | null;
  fetchLabel: string;
  contentKind: string | null;
  visibility: string | null;
} {
  const prov = signal.evidence?.provenance;
  const attr = prov?.attribution;
  const author = typeof attr === "string" ? attr : attr?.author || null;
  const authorUrl = typeof attr === "object" && attr?.profile_url ? attr.profile_url : null;
  const fetchMap: Record<string, string> = {
    github_webhook: "GitHub Webhook",
    official_api: "Official API",
    official_graphql: "Official GraphQL API",
    official_jetstream: "Bluesky Jetstream",
    official_hn: "Official Hacker News API",
    public_feed: "Approved Public Feed",
  };
  const fetchLabel = prov?.fetch_method ? fetchMap[prov.fetch_method] || prov.fetch_method.replaceAll("_", " ") : "Public source";
  return {
    author,
    authorUrl,
    repo: prov?.repo || null,
    fetchLabel,
    contentKind: prov?.content_kind ? prov.content_kind.replaceAll("_", " ") : null,
    visibility: prov?.visibility === "private_connected" ? "Authorized workspace repo" : prov?.visibility === "public" ? "Public" : null,
  };
}
