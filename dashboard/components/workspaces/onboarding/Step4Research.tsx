'use client';
import React from 'react';
import { Info, Sparkles, Wand2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { formatHonestSourceState, type SourceStatus } from './types';

export function Step4Research({
  companyName,
  mainOffering,
  primaryICPName,
  keywords,
  excluded,
  sources,
  pending,
  chatPending,
  onKeywordsChange,
  onExcludedChange,
  onAskCopilot,
  onSave,
  onBack
}: {
  companyName: string;
  mainOffering: string;
  primaryICPName: string;
  keywords: string;
  excluded: string;
  sources: SourceStatus[];
  pending: boolean;
  chatPending: boolean;
  onKeywordsChange: (value: string) => void;
  onExcludedChange: (value: string) => void;
  onAskCopilot: (prompt: string) => void;
  onSave: () => void;
  onBack: () => void;
}) {
  return (
    <section className="ai-card p-6 md:p-8 space-y-6" aria-label="Research Setup">
      {/* Compact Workspace Summary Row */}
      <dl className="grid grid-cols-1 sm:grid-cols-3 gap-3 rounded-xl border border-border/70 bg-muted/25 p-4 text-xs">
        <div className="min-w-0">
          <dt className="text-muted-foreground">Company</dt>
          <dd className="text-sm font-semibold text-foreground truncate mt-0.5">{companyName || 'Saved workspace'}</dd>
        </div>
        <div className="min-w-0">
          <dt className="text-muted-foreground">Main offering</dt>
          <dd className="text-sm font-semibold text-foreground truncate mt-0.5">{mainOffering || 'Confirmed'}</dd>
        </div>
        <div className="min-w-0">
          <dt className="text-muted-foreground">Primary ICP</dt>
          <dd className="text-sm font-semibold text-primary truncate mt-0.5">{primaryICPName || 'Active segment'}</dd>
        </div>
      </dl>

      {/* Buying-Intent Research Terms & Excluded Terms */}
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 className="text-sm font-semibold text-foreground">Research terms and exclusions</h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              Edit the phrases that guide future discovery and filter out irrelevant noise.
            </p>
          </div>
          <div className="flex flex-wrap gap-1.5">
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={chatPending}
              onClick={() =>
                onAskCopilot(
                  `Suggest 5 better buying-intent phrases (concrete buyer questions, comparisons, or pain phrases — no vague labels) for "${companyName}" targeting "${primaryICPName}". Return ready-to-apply proposed_updates.`
                )
              }
            >
              <Wand2 size={13} className="mr-1.5" aria-hidden="true" />
              Suggest 5 better phrases
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={chatPending}
              onClick={() =>
                onAskCopilot(
                  `Suggest 5 negative keywords to filter out irrelevant noise for "${companyName}" without blocking real buyers. Return ready-to-apply proposed_updates.`
                )
              }
            >
              Suggest negative keywords
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <div className="ai-field-header">
              <label htmlFor="onboarding-research-keywords" className="text-xs font-semibold text-foreground">
                Buying-intent research terms
              </label>
              <button
                type="button"
                className="ai-improve-btn"
                disabled={chatPending}
                onClick={() =>
                  onAskCopilot(
                    'Explain why my current buying-intent research terms match my primary ICP and suggest improvements for search relevance.'
                  )
                }
              >
                <Sparkles size={11} aria-hidden="true" /> Improve relevance
              </button>
            </div>
            <textarea
              id="onboarding-research-keywords"
              rows={6}
              value={keywords}
              onChange={e => onKeywordsChange(e.target.value)}
              className="ai-textarea"
              placeholder={'One phrase per line (up to 12)\ne.g. buyer intent tools for B2B\ncomparing sales intelligence platforms'}
            />
            <span className="text-[11px] text-muted-foreground block mt-1">
              Up to 12 concrete buyer phrases (one per line). Specific problems and vendor comparisons work best.
            </span>
          </div>

          <div>
            <div className="ai-field-header">
              <label htmlFor="onboarding-excluded-keywords" className="text-xs font-semibold text-foreground">
                Excluded terms
              </label>
              <button
                type="button"
                className="ai-improve-btn"
                disabled={chatPending}
                onClick={() =>
                  onAskCopilot(
                    'Suggest negative exclusion keywords to filter out noise like student projects, hiring posts, or unrelated tutorials without hiding real buyers.'
                  )
                }
              >
                <Sparkles size={11} aria-hidden="true" /> Suggest exclusions
              </button>
            </div>
            <textarea
              id="onboarding-excluded-keywords"
              rows={6}
              value={excluded}
              onChange={e => onExcludedChange(e.target.value)}
              className="ai-textarea"
              placeholder={'One term per line (up to 12)\ne.g. internship\nhomework\nhiring'}
            />
            <span className="text-[11px] text-muted-foreground block mt-1">
              Filters matching noise terms in results; does not restrict or disable discovery sources.
            </span>
          </div>
        </div>
      </div>

      {/* Honest Verified Source Coverage */}
      <div className="pt-4 border-t border-border/70 space-y-3">
        <div>
          <h3 className="text-sm font-semibold text-foreground">Discovery sources</h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            Live verification state for each supported integration. You can connect or configure additional sources anytime in Settings.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {sources.map(src => {
            const honest = formatHonestSourceState(src.state);
            const badgeTone =
              honest.tone === 'connected'
                ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
                : honest.tone === 'permission'
                  ? 'bg-amber-500/10 text-amber-700 dark:text-amber-300'
                  : honest.tone === 'unavailable'
                    ? 'bg-destructive/10 text-destructive'
                    : 'bg-muted text-muted-foreground';
            return (
              <div
                key={src.id}
                className="rounded-xl border border-border/80 bg-muted/15 p-3 flex items-start justify-between gap-3"
              >
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <strong className="text-xs font-semibold text-foreground">{src.name}</strong>
                    <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${badgeTone}`}>
                      {honest.label}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{src.coverage}</p>
                </div>
              </div>
            );
          })}
        </div>

        <p className="flex items-center gap-1.5 text-xs text-muted-foreground pt-1">
          <Info size={13} className="flex-shrink-0" aria-hidden="true" />
          <span>Saving these defaults stores your research setup only — it does not automatically run searches or start monitors.</span>
        </p>
      </div>

      <div className="ai-actions pt-2 border-t border-border/70">
        <Button size="lg" disabled={pending} onClick={onSave} className="ai-btn-primary">
          {pending ? 'Saving research setup…' : 'Save research setup & continue'}
        </Button>
        <Button variant="ghost" disabled={pending} onClick={onBack}>
          ← Back to ideal customers
        </Button>
      </div>
    </section>
  );
}
