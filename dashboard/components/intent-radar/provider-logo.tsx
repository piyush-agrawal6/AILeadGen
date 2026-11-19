"use client";

import { useState } from "react";
import Image from "next/image";
import { Atom, Blocks, BookOpen, Code2, MessageSquare, Radio, Rss, Video } from "lucide-react";
import { resolveSourceBrand } from "@/lib/source-branding";

export function ProviderLogo({ provider, size = 32 }: { provider: string; size?: number }) {
  const [hasError, setHasError] = useState(false);
  const brand = resolveSourceBrand(provider);
  const dimension = Number.isFinite(size) ? Math.min(128, Math.max(14, size)) : 32;

  if (brand.logoSrc && !hasError) {
    return (
      <span
        className={
          "inline-flex shrink-0 items-center justify-center overflow-hidden rounded-md " +
          (brand.needsLightBackingInDark ? "dark:bg-white dark:p-0.5" : "")
        }
        style={{ width: dimension, height: dimension }}
      >
        <Image
          className="ir-provider-logo h-full w-full object-contain"
          src={brand.logoSrc}
          alt={brand.alt}
          width={dimension}
          height={dimension}
          unoptimized
          onError={() => setHasError(true)}
        />
      </span>
    );
  }

  const iconSize = Math.max(14, Math.round(dimension * 0.72));
  const Icon =
    brand.fallbackKind === "github"
      ? Code2
      : brand.fallbackKind === "youtube"
        ? Video
        : brand.fallbackKind === "bluesky"
          ? Radio
          : brand.fallbackKind === "arxiv"
            ? BookOpen
            : brand.fallbackKind === "stackexchange" || brand.fallbackKind === "discourse"
              ? MessageSquare
              : brand.fallbackKind === "atom"
                ? Atom
                : brand.fallbackKind === "rss"
                  ? Rss
                  : Blocks;

  return (
    <span
      className="ir-provider-fallback inline-flex shrink-0 items-center justify-center rounded-md text-muted-foreground"
      style={{ width: dimension, height: dimension }}
      role="img"
      aria-label={brand.alt}
    >
      <Icon size={iconSize} aria-hidden="true" />
    </span>
  );
}
