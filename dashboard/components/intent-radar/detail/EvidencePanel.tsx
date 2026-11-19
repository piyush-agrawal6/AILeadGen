"use client";

import { useState } from "react";
import {
  ArrowUpRight,
  ChevronDown,
  ChevronUp,
  FileText,
  ShieldCheck,
  Tag,
} from "lucide-react";
import type { IntentEvidence } from "@/lib/intent-radar";
import { ProviderLogo } from "../provider-logo";
import { Button } from "@/components/ui/button";

export function EvidencePanel({
  source,
  sourceUrl,
  excerpt,
  title,
  evidence,
}: {
  source: string;
  sourceUrl?: string | null;
  excerpt: string;
  title: string;
  evidence?: IntentEvidence;
  observedAt?: string | null;
}) {
  const [expanded, setExpanded] = useState(false);

  const rawText = excerpt || title;
  const isLong = rawText.length > 450;
  const displayText = isLong && !expanded ? rawText.slice(0, 450) + "…" : rawText;

  const matchedKeywords = evidence?.matched_keywords || [];
  const matchedTopics = evidence?.matched_topics || [];
  const intentPhrase = evidence?.intent_phrase;
  const prov = evidence?.provenance;
  const author = typeof prov?.attribution === "object" ? prov.attribution.author : prov?.attribution;

  return (
    <div className="space-y-5">
      {/* Excerpt Section */}
      <section className="rounded-2xl border border-border bg-card p-5 space-y-3">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <FileText size={15} className="text-primary" />
            <h3 className="text-sm font-semibold text-foreground">Observed Discussion Excerpt</h3>
          </div>
          <div className="flex items-center gap-2">
            {sourceUrl?.startsWith("http") && (
              <a
                href={sourceUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-2.5 py-1 text-xs font-semibold text-foreground hover:border-primary/50 hover:text-primary transition-colors"
              >
                Open original discussion <ArrowUpRight size={12} />
              </a>
            )}
            {isLong && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setExpanded(!expanded)}
                className="h-7 text-xs text-muted-foreground hover:text-foreground gap-1"
              >
                {expanded ? (
                  <>
                    Show less <ChevronUp size={13} />
                  </>
                ) : (
                  <>
                    Show full excerpt <ChevronDown size={13} />
                  </>
                )}
              </Button>
            )}
          </div>
        </div>

        <div className="rounded-xl border border-border/80 bg-muted/15 p-4 text-xs sm:text-sm text-foreground leading-relaxed whitespace-pre-wrap font-sans">
          {displayText}
        </div>

        {/* Intent phrase if extracted */}
        {intentPhrase && (
          <div className="rounded-xl border border-primary/20 bg-primary/5 p-3 text-xs space-y-1">
            <span className="font-semibold text-primary">Matched Buyer Intent Expression:</span>
            <p className="italic text-foreground">“{intentPhrase}”</p>
          </div>
        )}
      </section>

      {/* Matched Keywords & Topics */}
      <div className="grid gap-4 sm:grid-cols-2">
        <section className="rounded-2xl border border-border bg-card p-5 space-y-3">
          <div className="flex items-center gap-2">
            <Tag size={14} className="text-muted-foreground" />
            <h3 className="text-xs font-semibold text-foreground uppercase tracking-wide">
              Matched Keywords ({matchedKeywords.length})
            </h3>
          </div>
          {matchedKeywords.length === 0 ? (
            <p className="text-xs text-muted-foreground">No specific keywords matched.</p>
          ) : (
            <div className="flex flex-wrap gap-1.5">
              {matchedKeywords.map((kw) => (
                <span
                  key={kw}
                  className="rounded-md border border-border bg-muted/40 px-2 py-0.5 text-xs font-medium text-foreground"
                >
                  {kw}
                </span>
              ))}
            </div>
          )}
        </section>

        <section className="rounded-2xl border border-border bg-card p-5 space-y-3">
          <div className="flex items-center gap-2">
            <Tag size={14} className="text-muted-foreground" />
            <h3 className="text-xs font-semibold text-foreground uppercase tracking-wide">
              Matched Topics ({matchedTopics.length})
            </h3>
          </div>
          {matchedTopics.length === 0 ? (
            <p className="text-xs text-muted-foreground">No specific topics categorized.</p>
          ) : (
            <div className="flex flex-wrap gap-1.5">
              {matchedTopics.map((top) => (
                <span
                  key={top}
                  className="rounded-md border border-border bg-muted/40 px-2 py-0.5 text-xs font-medium text-foreground"
                >
                  {top}
                </span>
              ))}
            </div>
          )}
        </section>
      </div>

      {/* Source Provenance & Verification Notice */}
      <section className="rounded-2xl border border-border bg-card p-5 space-y-3">
        <h3 className="text-sm font-semibold text-foreground">Source Provenance &amp; Verification</h3>
        <div className="grid gap-3 sm:grid-cols-3 text-xs">
          <div className="rounded-xl border border-border/70 bg-background p-3 space-y-1">
            <span className="text-[11px] text-muted-foreground block">Platform Source</span>
            <div className="flex items-center gap-1.5 font-medium text-foreground">
              <ProviderLogo provider={source} size={15} />
              <span>{source}</span>
            </div>
          </div>

          {author && (
            <div className="rounded-xl border border-border/70 bg-background p-3 space-y-1">
              <span className="text-[11px] text-muted-foreground block">Author / Contributor</span>
              <span className="font-medium text-foreground truncate block">{author}</span>
            </div>
          )}

          {prov?.repo && (
            <div className="rounded-xl border border-border/70 bg-background p-3 space-y-1">
              <span className="text-[11px] text-muted-foreground block">Repository</span>
              <span className="font-medium text-foreground truncate block">{prov.repo}</span>
            </div>
          )}

          {prov?.site && (
            <div className="rounded-xl border border-border/70 bg-background p-3 space-y-1">
              <span className="text-[11px] text-muted-foreground block">Community Site</span>
              <span className="font-medium text-foreground truncate block">{prov.site}</span>
            </div>
          )}

          {sourceUrl?.startsWith("http") && (
            <div className="rounded-xl border border-border/70 bg-background p-3 space-y-1">
              <span className="text-[11px] text-muted-foreground block">Direct Link</span>
              <a
                href={sourceUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 font-semibold text-primary hover:underline truncate"
              >
                <span>View online source</span>
                <ArrowUpRight size={12} />
              </a>
            </div>
          )}
        </div>

        {/* Compliance & Privacy Policy Notice */}
        <div className="flex items-start gap-2.5 rounded-xl border border-border/70 bg-muted/20 p-3 text-[11px] text-muted-foreground">
          <ShieldCheck size={14} className="mt-0.5 shrink-0 text-emerald-600 dark:text-emerald-400" />
          <p>
            Collected strictly in accordance with workspace compliance policies. No private messages or
            non-public communication was accessed. Evaluated text remains non-binding evidence.
          </p>
        </div>
      </section>
    </div>
  );
}
