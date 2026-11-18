"use client";

export interface SourceBrandIdentity {
  id: string;
  displayName: string;
  logoSrc: string | null;
  alt: string;
  sourceType: "api" | "feed" | "community" | "release" | "research" | "social";
  /** Adds a crisp light backing in dark mode for dark monochrome marks (e.g. GitHub). */
  needsLightBackingInDark?: boolean;
  fallbackKind: "github" | "youtube" | "bluesky" | "stackexchange" | "discourse" | "atom" | "rss" | "arxiv" | "generic";
}

export const SOURCE_BRAND_REGISTRY: Record<string, SourceBrandIdentity> = {
  hacker_news: {
    id: "hacker_news",
    displayName: "Hacker News",
    logoSrc: "/brands/sources/hacker-news.svg",
    alt: "Hacker News logo",
    sourceType: "community",
    fallbackKind: "generic",
  },
  github: {
    id: "github",
    displayName: "GitHub",
    logoSrc: "/brands/sources/github.png",
    alt: "GitHub logo",
    sourceType: "api",
    needsLightBackingInDark: true,
    fallbackKind: "github",
  },
  stack_exchange: {
    id: "stack_exchange",
    displayName: "Stack Exchange",
    logoSrc: "/brands/sources/stack-exchange.png",
    alt: "Stack Exchange logo",
    sourceType: "community",
    fallbackKind: "stackexchange",
  },
  youtube: {
    id: "youtube",
    displayName: "YouTube",
    logoSrc: "/brands/sources/youtube.png",
    alt: "YouTube logo",
    sourceType: "social",
    fallbackKind: "youtube",
  },
  bluesky: {
    id: "bluesky",
    displayName: "Bluesky",
    logoSrc: "/brands/sources/bluesky.png",
    alt: "Bluesky logo",
    sourceType: "social",
    fallbackKind: "bluesky",
  },
  rss: {
    id: "rss",
    displayName: "Custom RSS / Atom",
    logoSrc: "/brands/sources/rss.png",
    alt: "RSS / Atom logo",
    sourceType: "feed",
    fallbackKind: "rss",
  },
  atom: {
    id: "atom",
    displayName: "Atom Feeds",
    logoSrc: "/brands/sources/rss.png",
    alt: "Atom Feeds logo",
    sourceType: "feed",
    fallbackKind: "atom",
  },
  discourse: {
    id: "discourse",
    displayName: "Approved Discourse",
    logoSrc: null,
    alt: "Discourse community icon",
    sourceType: "community",
    fallbackKind: "discourse",
  },
  vscode: {
    id: "vscode",
    displayName: "VS Code",
    logoSrc: "/brands/sources/vscode.png",
    alt: "Visual Studio Code logo",
    sourceType: "release",
    fallbackKind: "github",
  },
  arxiv: {
    id: "arxiv",
    displayName: "arXiv",
    logoSrc: null,
    alt: "arXiv research icon",
    sourceType: "research",
    fallbackKind: "arxiv",
  },
};

export function resolveSourceBrand(providerOrName: string): SourceBrandIdentity {
  const key = (providerOrName || "").trim().toLowerCase();
  if (!key) {
    return {
      id: "generic",
      displayName: "Source",
      logoSrc: null,
      alt: "Research source icon",
      sourceType: "api",
      fallbackKind: "generic",
    };
  }
  if (key === "hacker_news" || key === "hacker news" || key === "hn" || key.includes("hacker news")) {
    return SOURCE_BRAND_REGISTRY.hacker_news;
  }
  if (key === "vscode" || key.includes("vs code") || key.includes("visual studio code")) {
    return SOURCE_BRAND_REGISTRY.vscode;
  }
  if (key === "youtube" || key.includes("youtube")) {
    return SOURCE_BRAND_REGISTRY.youtube;
  }
  if (key === "github" || key.includes("github") || key.includes("releases")) {
    // GitHub releases (Next.js, n8n, LangChain, OpenAI SDK, FastAPI) use GitHub logo until product-specific icons are supplied
    return SOURCE_BRAND_REGISTRY.github;
  }
  if (key === "stack_exchange" || key.includes("stack exchange") || key.includes("stackoverflow") || key.includes("stack overflow")) {
    return SOURCE_BRAND_REGISTRY.stack_exchange;
  }
  if (key === "bluesky" || key.includes("bluesky") || key.includes("bsky")) {
    return SOURCE_BRAND_REGISTRY.bluesky;
  }
  if (key.includes("arxiv")) {
    return SOURCE_BRAND_REGISTRY.arxiv;
  }
  if (key === "discourse" || key.includes("discourse") || key.includes("forum") || key.includes("community")) {
    return SOURCE_BRAND_REGISTRY.discourse;
  }
  if (key === "atom" || key.includes("atom")) {
    return SOURCE_BRAND_REGISTRY.atom;
  }
  if (key === "rss" || key.includes("rss")) {
    return SOURCE_BRAND_REGISTRY.rss;
  }
  return {
    id: key,
    displayName: providerOrName,
    logoSrc: null,
    alt: `${providerOrName} source icon`,
    sourceType: "api",
    fallbackKind: "generic",
  };
}
