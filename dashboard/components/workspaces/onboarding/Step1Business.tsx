'use client';
import React from 'react';
import { AlertCircle, Building2, ShieldCheck, Sparkles, Users2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { FormField } from './FormField';
import { OBJECTIVES, validateWebsiteField, type FieldErrors } from './types';

export function Step1Business({
  website,
  objective,
  pending,
  canAnalyze,
  fieldErrors,
  onWebsiteChange,
  onWebsiteBlur,
  onObjectiveChange,
  onAnalyze,
  onManual
}: {
  website: string;
  objective: string;
  pending: boolean;
  canAnalyze: boolean;
  fieldErrors: FieldErrors;
  onWebsiteChange: (value: string) => void;
  onWebsiteBlur: (error: string) => void;
  onObjectiveChange: (value: string) => void;
  onAnalyze: () => void;
  onManual: () => void;
}) {
  const websiteError = fieldErrors.welcome_website || fieldErrors.website;

  return (
    <section className="ai-card p-6 md:p-8 space-y-6" aria-label="Your Business">
      <div className="space-y-5">
        <FormField
          id="onboarding-website-url"
          label="Company website"
          error={websiteError}
          hint="We review up to 5 public pages (honoring robots.txt) to prepare an editable draft for your approval."
        >
          <input
            id="onboarding-website-url"
            type="text"
            inputMode="url"
            autoComplete="url"
            placeholder="https://yourcompany.com"
            value={website}
            maxLength={600}
            aria-invalid={Boolean(websiteError)}
            aria-describedby={websiteError ? 'onboarding-website-url-error' : undefined}
            onChange={e => onWebsiteChange(e.target.value)}
            onBlur={() => {
              if (website.trim()) {
                onWebsiteBlur(validateWebsiteField(website, true));
              }
            }}
            onKeyDown={e => {
              if (e.key === 'Enter' && !pending && canAnalyze) {
                e.preventDefault();
                onAnalyze();
              }
            }}
            className={`ai-input ${websiteError ? 'is-invalid' : ''}`}
          />
        </FormField>

        <FormField
          id="onboarding-objective"
          label="Primary research objective"
          hint="Helps prioritize which buying signals and customer segments we recommend."
        >
          <select
            id="onboarding-objective"
            value={objective}
            onChange={e => onObjectiveChange(e.target.value)}
            className="ai-select"
          >
            {OBJECTIVES.map(([key, label, desc]) => (
              <option value={key} key={key}>
                {label} — {desc}
              </option>
            ))}
          </select>
        </FormField>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-4 border-t border-border/70 text-xs text-muted-foreground">
        <div className="flex items-start gap-2">
          <Building2 size={15} className="text-primary flex-shrink-0 mt-0.5" aria-hidden="true" />
          <span>Extracts offerings, positioning, and target markets</span>
        </div>
        <div className="flex items-start gap-2">
          <Users2 size={15} className="text-primary flex-shrink-0 mt-0.5" aria-hidden="true" />
          <span>Recommends 5 distinct ICPs with concrete buying triggers</span>
        </div>
        <div className="flex items-start gap-2">
          <ShieldCheck size={15} className="text-primary flex-shrink-0 mt-0.5" aria-hidden="true" />
          <span>You review and approve every field before saving</span>
        </div>
      </div>

      <div className="ai-actions pt-2">
        <Button
          size="lg"
          disabled={pending || !canAnalyze}
          onClick={onAnalyze}
          className="ai-btn-primary"
        >
          <Sparkles size={16} className="mr-2" aria-hidden="true" />
          {pending ? 'Starting website research…' : 'Analyze my website'}
        </Button>
        <Button variant="outline" size="lg" disabled={pending} onClick={onManual}>
          Set up manually
        </Button>
      </div>

      {!canAnalyze && (
        <div className="ai-notice-box" role="status">
          <AlertCircle size={16} className="text-amber-500 flex-shrink-0" aria-hidden="true" />
          <p>AI website analysis is currently unavailable. Click “Set up manually” to continue.</p>
        </div>
      )}
    </section>
  );
}
