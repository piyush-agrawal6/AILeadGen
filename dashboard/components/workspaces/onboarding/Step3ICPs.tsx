'use client';
import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Plus, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { OnboardingICP } from '../onboarding-icp';
import type { Candidate } from '../icp-suggestions';
import { AIJobStatus } from './AIJobStatus';
import { describe, list, type Review } from './types';

export function ICPSelectionCard({
  index,
  candidate,
  isSelected,
  isPrimary,
  isExpanded,
  chatPending,
  onSelect,
  onSetPrimary,
  onToggleExpand,
  onNameChange,
  onFieldChange,
  onGenerateTriggers
}: {
  index: number;
  candidate: Candidate;
  isSelected: boolean;
  isPrimary: boolean;
  isExpanded: boolean;
  chatPending: boolean;
  onSelect: (checked: boolean) => void;
  onSetPrimary: () => void;
  onToggleExpand: () => void;
  onNameChange: (name: string) => void;
  onFieldChange: (group: 'company' | 'contact' | 'intent', field: string, value: string) => void;
  onGenerateTriggers: () => void;
}) {
  const roles = list(candidate.draft.criteria.contact.job_titles);
  const sizes = list(candidate.draft.criteria.company.company_sizes);
  const industries = list(candidate.draft.criteria.company.industries);
  const needs = [...list(candidate.draft.criteria.intent.pain_points), ...list(candidate.draft.criteria.intent.business_needs)];
  const signals = list(candidate.draft.criteria.intent.buying_signals);

  return (
    <article
      className={`pb-icp-card ${isPrimary ? 'is-primary' : ''} ${isSelected ? 'is-selected' : 'is-unselected'}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-2.5 min-w-0 flex-1">
          <input
            type="checkbox"
            aria-label={`Include ${candidate.draft.name}`}
            checked={isSelected}
            onChange={e => onSelect(e.target.checked)}
            className="ai-checkbox mt-1 flex-shrink-0"
          />
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="font-semibold text-sm sm:text-base text-foreground">{candidate.draft.name}</h3>
              {isPrimary && <span className="ai-badge-primary">Primary ICP</span>}
            </div>
            <p className="text-xs text-muted-foreground mt-1 leading-relaxed line-clamp-2">{candidate.reason}</p>
          </div>
        </div>

        <div className="flex items-center gap-3 flex-shrink-0">
          <label className="flex items-center gap-1.5 text-xs text-muted-foreground cursor-pointer hover:text-foreground">
            <input
              type="radio"
              name="primary-segment"
              aria-label={`Set ${candidate.draft.name} as primary ICP`}
              disabled={!isSelected}
              checked={isPrimary}
              onChange={onSetPrimary}
              className="ai-radio"
            />
            <span>Set as primary</span>
          </label>
          <button
            type="button"
            onClick={onToggleExpand}
            aria-expanded={isExpanded}
            className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
          >
            {isExpanded ? 'Hide criteria' : 'Edit criteria'}
            {isExpanded ? <ChevronUp size={14} aria-hidden="true" /> : <ChevronDown size={14} aria-hidden="true" />}
          </button>
        </div>
      </div>

      {/* Buyer-role & Company-size Chips */}
      <div className="mt-3 flex flex-wrap gap-1.5">
        {roles.slice(0, 3).map((role, idx) => (
          <span key={`r-${idx}`} className="ai-tag">{role}</span>
        ))}
        {sizes.slice(0, 2).map((sz, idx) => (
          <span key={`s-${idx}`} className="ai-tag is-size">{sz} employees</span>
        ))}
        {industries.slice(0, 2).map((ind, idx) => (
          <span key={`i-${idx}`} className="ai-tag is-muted">{ind}</span>
        ))}
      </div>

      {/* 2 Key Needs + 2-3 Buying Triggers */}
      <div className="mt-3 pt-3 border-t border-border/60 grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
        <div>
          <span className="font-semibold text-foreground block mb-1">Key needs</span>
          <ul className="list-disc pl-4 text-muted-foreground space-y-1">
            {needs.slice(0, 2).map((item, idx) => (
              <li key={idx}>{item}</li>
            ))}
          </ul>
        </div>

        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="font-semibold text-foreground">Buying triggers</span>
            {signals.length === 0 && (
              <button
                type="button"
                className="text-[11px] text-primary underline font-medium"
                disabled={chatPending}
                onClick={onGenerateTriggers}
              >
                Suggest with AI
              </button>
            )}
          </div>
          {signals.length > 0 ? (
            <ul className="list-disc pl-4 text-muted-foreground space-y-1">
              {signals.slice(0, 3).map((sig, idx) => (
                <li key={idx}>{sig}</li>
              ))}
            </ul>
          ) : (
            <p className="text-muted-foreground italic">Expand “Edit criteria” to add buying triggers.</p>
          )}
        </div>
      </div>

      {/* Expandable Secondary Criteria & Inline Editor */}
      {isExpanded && (
        <div className="mt-4 pt-4 border-t border-border space-y-3 text-xs">
          <div>
            <label htmlFor={`icp-name-${index}`} className="block text-[11px] font-semibold text-foreground mb-1">
              ICP title
            </label>
            <input
              id={`icp-name-${index}`}
              value={candidate.draft.name}
              maxLength={120}
              onChange={e => onNameChange(e.target.value)}
              className="ai-input text-xs"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {(
              [
                ['contact', 'job_titles', 'Target buyer roles'],
                ['company', 'industries', 'Industries'],
                ['company', 'company_sizes', 'Company sizes (e.g. 11-50, 51-200)'],
                ['company', 'countries', 'Markets / countries (optional)'],
                ['intent', 'business_needs', 'Main needs'],
                ['intent', 'pain_points', 'Pain points'],
                ['intent', 'buying_signals', 'Buying-intent triggers'],
                ['intent', 'exclusions', 'Disqualifiers / exclusions']
              ] as const
            ).map(([grp, fld, lbl]) => (
              <div key={fld}>
                <label htmlFor={`icp-${index}-${fld}`} className="block text-[11px] font-semibold text-foreground mb-1">
                  {lbl}
                </label>
                <textarea
                  id={`icp-${index}-${fld}`}
                  rows={2}
                  value={describe(candidate.draft.criteria[grp][fld])}
                  onChange={e => onFieldChange(grp, fld, e.target.value)}
                  className="ai-textarea text-xs"
                  placeholder="One per line…"
                />
              </div>
            ))}
          </div>
        </div>
      )}
    </article>
  );
}

export function Step3ICPs({
  icpId,
  icpReview,
  canGenerate,
  candidates,
  selected,
  primary,
  expandedICP,
  savedProfiles,
  defaultICP,
  pending,
  chatPending,
  onControlReview,
  onGenerateFresh,
  onSelectCandidate,
  onSetPrimary,
  onToggleExpand,
  onCandidateNameChange,
  onCandidateFieldChange,
  onGenerateTriggers,
  onManualCreated,
  onSelectManualDefault,
  onAccept,
  onContinueManual,
  onBack
}: {
  icpId: string | null;
  icpReview: { data?: Review; error: Error | null; refetch: () => Promise<unknown> };
  canGenerate: boolean;
  candidates: Candidate[];
  selected: number[];
  primary: number;
  expandedICP: number | null;
  savedProfiles: { id: string; name: string; status: string }[];
  defaultICP: string;
  pending: boolean;
  chatPending: boolean;
  onControlReview: (action: 'CANCEL' | 'RETRY') => Promise<void>;
  onGenerateFresh: () => Promise<void>;
  onSelectCandidate: (index: number, checked: boolean) => void;
  onSetPrimary: (index: number) => void;
  onToggleExpand: (index: number) => void;
  onCandidateNameChange: (index: number, name: string) => void;
  onCandidateFieldChange: (index: number, group: 'company' | 'contact' | 'intent', field: string, value: string) => void;
  onGenerateTriggers: (index: number) => void;
  onManualCreated: (profile: { id: string; name: string; status: string }) => void;
  onSelectManualDefault: (id: string) => void;
  onAccept: () => void;
  onContinueManual: () => void;
  onBack: () => void;
}) {
  const [showManual, setShowManual] = useState(false);
  const isFailed = icpReview.data?.status === 'FAILED' || icpReview.data?.status === 'CANCELLED';

  return (
    <section className="ai-card p-6 md:p-8 space-y-5" aria-label="Ideal Customers">
      {icpId && (
        <AIJobStatus
          kind="icp"
          query={icpReview}
          onControl={onControlReview}
          onFreshRun={onGenerateFresh}
        />
      )}

      {!icpId && canGenerate && (
        <div className="text-center py-6 space-y-3 rounded-xl border border-dashed border-border bg-muted/15">
          <p className="text-sm text-muted-foreground max-w-md mx-auto">
            Generate 5 distinct ideal customer segments from your saved business profile, complete with buyer roles and buying triggers.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-2.5">
            <Button size="lg" disabled={pending} onClick={() => void onGenerateFresh()} className="ai-btn-primary">
              <Sparkles size={16} className="mr-2" aria-hidden="true" />
              Generate 5 ideal customers
            </Button>
            <Button variant="outline" size="lg" onClick={() => setShowManual(v => !v)}>
              <Plus size={15} className="mr-1.5" aria-hidden="true" />
              Create manually
            </Button>
          </div>
        </div>
      )}

      {candidates.length > 0 && (
        <div className="space-y-3.5">
          <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
            <span>
              <strong className="text-foreground">{selected.length} of {candidates.length}</strong> segments included
            </span>
            <span>Choose 1 primary ICP to guide your research setup · AI suggestions are targeting hypotheses, not verified customers.</span>
          </div>

          <div className="space-y-3">
            {candidates.map((cand, i) => (
              <ICPSelectionCard
                key={i}
                index={i}
                candidate={cand}
                isSelected={selected.includes(i)}
                isPrimary={primary === i && selected.includes(i)}
                isExpanded={expandedICP === i}
                chatPending={chatPending}
                onSelect={checked => onSelectCandidate(i, checked)}
                onSetPrimary={() => onSetPrimary(i)}
                onToggleExpand={() => onToggleExpand(i)}
                onNameChange={name => onCandidateNameChange(i, name)}
                onFieldChange={(grp, fld, val) => onCandidateFieldChange(i, grp, fld, val)}
                onGenerateTriggers={() => onGenerateTriggers(i)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Usable Manual Path if AI failed, unavailable, or user prefers manual ICP */}
      {(isFailed || !canGenerate || showManual || (candidates.length === 0 && savedProfiles.length > 0)) && (
        <div className="rounded-xl border border-border bg-muted/15 p-4 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h3 className="text-sm font-semibold text-foreground">Manual ideal customer profile</h3>
              <p className="text-xs text-muted-foreground">
                Your approved business profile is preserved. Create or choose an active ICP manually at any time.
              </p>
            </div>
            <Button type="button" variant="outline" size="sm" onClick={() => setShowManual(v => !v)}>
              {showManual ? 'Hide manual form' : 'Create ICP manually'}
            </Button>
          </div>

          {showManual && (
            <OnboardingICP
              onCreated={created => {
                onManualCreated(created);
                setShowManual(false);
              }}
            />
          )}

          {savedProfiles.length > 0 && (
            <div>
              <label htmlFor="manual-default-icp" className="block text-xs font-semibold text-foreground mb-1">
                Saved active ICP
              </label>
              <select
                id="manual-default-icp"
                className="ai-select"
                value={defaultICP}
                onChange={e => onSelectManualDefault(e.target.value)}
              >
                <option value="">Choose an active profile</option>
                {savedProfiles.map(p => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      )}

      <div className="ai-actions pt-2 border-t border-border/70">
        {candidates.length > 0 ? (
          <Button
            size="lg"
            disabled={pending || !selected.length || !selected.includes(primary)}
            onClick={onAccept}
            className="ai-btn-primary"
          >
            {pending ? 'Saving ideal customers…' : 'Save ideal customers & continue'}
          </Button>
        ) : defaultICP ? (
          <Button size="lg" disabled={pending} onClick={onContinueManual} className="ai-btn-primary">
            Save ideal customers &amp; continue
          </Button>
        ) : null}
        <Button variant="ghost" disabled={pending} onClick={onBack}>
          ← Back to business profile
        </Button>
      </div>
    </section>
  );
}
