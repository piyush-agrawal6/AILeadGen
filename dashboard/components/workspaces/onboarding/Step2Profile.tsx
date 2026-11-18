'use client';
import React from 'react';
import { Building2, Globe, Layers, Plus, Sparkles, Users2, Wand2, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { companyFieldLabels, type CompanyFields } from '../company-profile-types';
import { AIJobStatus } from './AIJobStatus';
import { ErrorSummary, FormField, FormSection, InlineFieldError } from './FormField';
import { validateWebsiteField, type FieldErrors, type Review } from './types';

function fieldProvenance(review: Review | undefined, key: keyof CompanyFields): 'supported' | 'suggested' | null {
  if (!review || review.status !== 'READY' || !review.preview) return null;
  const src = review.preview.sources?.[key];
  if (src?.basis === 'SOURCE_ASSERTION' || src?.kind === 'REVIEWED_URL') return 'supported';
  if (src?.basis === 'AI_INTERPRETATION' || (review.preview.suggestions && key in review.preview.suggestions)) {
    return 'suggested';
  }
  return null;
}

export function OfferingEditor({
  offerings,
  fieldErrors,
  companyReady,
  onChange,
  onClearError
}: {
  offerings: CompanyFields['products_services'];
  fieldErrors: FieldErrors;
  companyReady: boolean;
  onChange: (next: CompanyFields['products_services']) => void;
  onClearError: (key: string) => void;
}) {
  return (
    <div className="space-y-3">
      {fieldErrors.offerings && <InlineFieldError id="onb-offerings-error" message={fieldErrors.offerings} />}
      {offerings.length === 0 && companyReady && !fieldErrors.offerings && (
        <p className="text-xs text-muted-foreground">
          No offerings were detected directly on your homepage — add at least one product or service below.
        </p>
      )}
      <div className="space-y-2.5">
        {offerings.map((offering, i) => {
          const nameErr = fieldErrors[`offering-${i}-name`];
          const descErr = fieldErrors[`offering-${i}-desc`];
          return (
            <div key={i} className="grid grid-cols-1 md:grid-cols-12 gap-3 items-start rounded-xl border border-border/70 bg-muted/20 p-3.5">
              <div className="md:col-span-4">
                <label
                  htmlFor={`onb-prod-name-${i}`}
                  className={`block text-xs font-medium mb-1 ${nameErr ? 'text-destructive' : 'text-foreground'}`}
                >
                  Product or service name
                </label>
                <input
                  id={`onb-prod-name-${i}`}
                  value={offering.name}
                  maxLength={120}
                  aria-invalid={Boolean(nameErr)}
                  aria-describedby={nameErr ? `onb-prod-name-${i}-error` : undefined}
                  onChange={e => {
                    onClearError(`offering-${i}-name`);
                    onClearError('offerings');
                    onChange(offerings.map((o, j) => (i === j ? { ...o, name: e.target.value } : o)));
                  }}
                  className={`ai-input text-xs ${nameErr ? 'is-invalid' : ''}`}
                  placeholder="e.g. Intent Radar"
                />
                <InlineFieldError id={`onb-prod-name-${i}-error`} message={nameErr} />
              </div>

              <div className="md:col-span-8">
                <label
                  htmlFor={`onb-prod-desc-${i}`}
                  className={`block text-xs font-medium mb-1 ${descErr ? 'text-destructive' : 'text-foreground'}`}
                >
                  What it does / primary customer value
                </label>
                <div className="flex gap-2 items-start">
                  <div className="flex-1 min-w-0">
                    <input
                      id={`onb-prod-desc-${i}`}
                      value={offering.description}
                      maxLength={1000}
                      aria-invalid={Boolean(descErr)}
                      aria-describedby={descErr ? `onb-prod-desc-${i}-error` : undefined}
                      onChange={e => {
                        onClearError(`offering-${i}-desc`);
                        onChange(offerings.map((o, j) => (i === j ? { ...o, description: e.target.value } : o)));
                      }}
                      className={`ai-input text-xs ${descErr ? 'is-invalid' : ''}`}
                      placeholder="What does this offering help customers achieve?"
                    />
                    <InlineFieldError id={`onb-prod-desc-${i}-error`} message={descErr} />
                  </div>
                  <button
                    type="button"
                    className="text-muted-foreground hover:text-destructive p-2 rounded-lg transition-colors"
                    onClick={() => onChange(offerings.filter((_, j) => j !== i))}
                    aria-label={`Remove offering ${offering.name || i + 1}`}
                  >
                    <X size={15} />
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function Step2Profile({
  draft,
  companyId,
  companyReview,
  pending,
  chatPending,
  fieldErrors,
  onDraftChange,
  onFieldBlur,
  onClearError,
  onControlReview,
  onAskCopilot,
  onSave,
  onBack
}: {
  draft: CompanyFields;
  companyId: string | null;
  companyReview: { data?: Review; error: Error | null; refetch: () => Promise<unknown> };
  pending: boolean;
  chatPending: boolean;
  fieldErrors: FieldErrors;
  onDraftChange: (updater: (prev: CompanyFields) => CompanyFields) => void;
  onFieldBlur: (field: string, error: string) => void;
  onClearError: (field: string) => void;
  onControlReview: (action: 'CANCEL' | 'RETRY') => Promise<void>;
  onAskCopilot: (prompt: string) => void;
  onSave: () => void;
  onBack: () => void;
}) {
  const review = companyReview.data;
  const companyReady = review?.status === 'READY';
  const sourceUrl = review?.preview?.source_url || draft.website;
  const pagesReviewed = review?.preview?.pages_reviewed;

  return (
    <section className="ai-card p-6 md:p-8" aria-label="Business Profile">
      {companyId && (
        <AIJobStatus kind="company" query={companyReview} onControl={onControlReview} />
      )}

      <ErrorSummary errors={fieldErrors} />

      {/* Optional discreet Sources popover — zero inline raw quote walls */}
      {companyReady && sourceUrl && (
        <div className="flex items-center justify-end mb-2">
          <details className="pb-sources-popover">
            <summary className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground cursor-pointer select-none">
              <Globe size={13} aria-hidden="true" />
              <span>Sources{pagesReviewed ? ` (${pagesReviewed} page${pagesReviewed === 1 ? '' : 's'})` : ''}</span>
            </summary>
            <div className="pb-sources-panel">
              <p className="text-xs font-medium text-foreground">Reviewed public source</p>
              <a
                href={sourceUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-primary underline break-all block mt-1"
              >
                {sourceUrl}
              </a>
              <p className="text-[11px] text-muted-foreground mt-1.5">
                Fields marked “From website” come from public pages. Fields marked “AI suggestion” are editable drafts for your review.
              </p>
            </div>
          </details>
        </div>
      )}

      {/* Section A: Company Overview */}
      <FormSection icon={<Building2 size={16} className="text-primary" aria-hidden="true" />} title="Company overview">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <FormField
            id="onb-company-name"
            label={companyFieldLabels['name']}
            error={fieldErrors.name}
            provenance={fieldProvenance(review, 'name')}
          >
            <input
              id="onb-company-name"
              aria-label={companyFieldLabels['name']}
              aria-invalid={Boolean(fieldErrors.name)}
              aria-describedby={fieldErrors.name ? 'onb-company-name-error' : undefined}
              value={draft.name}
              maxLength={120}
              onChange={e => {
                onClearError('name');
                onDraftChange(v => ({ ...v, name: e.target.value }));
              }}
              onBlur={() => {
                const trimmed = draft.name.trim();
                onFieldBlur('name', !trimmed || trimmed.length < 2 ? 'Enter a company name (at least 2 characters).' : '');
              }}
              className={`ai-input ${fieldErrors.name ? 'is-invalid' : ''}`}
              placeholder="e.g. PlaneByte"
            />
          </FormField>

          <FormField
            id="onb-company-website"
            label={companyFieldLabels['website']}
            error={fieldErrors.website}
            provenance={fieldProvenance(review, 'website')}
          >
            <input
              id="onb-company-website"
              type="text"
              inputMode="url"
              aria-label={companyFieldLabels['website']}
              aria-invalid={Boolean(fieldErrors.website)}
              aria-describedby={fieldErrors.website ? 'onb-company-website-error' : undefined}
              value={draft.website}
              maxLength={600}
              onChange={e => {
                onClearError('website');
                onDraftChange(v => ({ ...v, website: e.target.value }));
              }}
              onBlur={() => onFieldBlur('website', validateWebsiteField(draft.website, false))}
              className={`ai-input ${fieldErrors.website ? 'is-invalid' : ''}`}
              placeholder="https://yourcompany.com"
            />
          </FormField>

          <FormField
            id="onb-company-industry"
            label={companyFieldLabels['industry']}
            error={fieldErrors.industry}
            provenance={fieldProvenance(review, 'industry')}
            action={
              <button
                type="button"
                className="ai-improve-btn"
                disabled={chatPending}
                onClick={() =>
                  onAskCopilot(
                    'Suggest a concise primary industry category for my business based on our offerings and description.'
                  )
                }
              >
                <Wand2 size={11} aria-hidden="true" /> {draft.industry.trim() ? 'Refine' : 'Draft with AI'}
              </button>
            }
          >
            <input
              id="onb-company-industry"
              aria-label={companyFieldLabels['industry']}
              aria-invalid={Boolean(fieldErrors.industry)}
              aria-describedby={fieldErrors.industry ? 'onb-company-industry-error' : undefined}
              value={draft.industry}
              maxLength={120}
              onChange={e => {
                onClearError('industry');
                onDraftChange(v => ({ ...v, industry: e.target.value }));
              }}
              className={`ai-input ${fieldErrors.industry ? 'is-invalid' : ''}`}
              placeholder="e.g. B2B SaaS · Buyer-Intent Intelligence"
            />
          </FormField>
        </div>

        <div className="mt-4">
          <FormField
            id="onb-company-desc"
            label={companyFieldLabels['description']}
            error={fieldErrors.description}
            provenance={fieldProvenance(review, 'description')}
            action={
              <button
                type="button"
                className="ai-improve-btn"
                disabled={chatPending}
                onClick={() =>
                  onAskCopilot(
                    draft.description.trim()
                      ? `Improve wording for my company description so it clearly communicates what we do and who we help:\n"${draft.description}"`
                      : 'Draft a concise company description based on my offerings and website.'
                  )
                }
              >
                <Wand2 size={11} aria-hidden="true" /> {draft.description.trim() ? 'Improve wording' : 'Draft with AI'}
              </button>
            }
          >
            <textarea
              id="onb-company-desc"
              aria-label={companyFieldLabels['description']}
              aria-invalid={Boolean(fieldErrors.description)}
              aria-describedby={fieldErrors.description ? 'onb-company-desc-error' : undefined}
              rows={3}
              value={draft.description}
              maxLength={1000}
              onChange={e => {
                onClearError('description');
                onDraftChange(v => ({ ...v, description: e.target.value }));
              }}
              className={`ai-textarea ${fieldErrors.description ? 'is-invalid' : ''}`}
              placeholder="Concise overview of your company and the value you deliver…"
            />
          </FormField>
        </div>
      </FormSection>

      {/* Section B: Products and Services */}
      <FormSection
        id="onb-offerings-section"
        icon={<Layers size={16} className="text-primary" aria-hidden="true" />}
        title="Products and services"
        count={draft.products_services.length}
        action={
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={draft.products_services.length >= 20}
            onClick={() => {
              onClearError('offerings');
              onDraftChange(v => ({
                ...v,
                products_services: [...v.products_services, { name: '', category: 'Software', description: '' }]
              }));
            }}
          >
            <Plus size={14} className="mr-1" aria-hidden="true" /> Add offering
          </Button>
        }
      >
        <OfferingEditor
          offerings={draft.products_services}
          fieldErrors={fieldErrors}
          companyReady={companyReady}
          onChange={next => onDraftChange(v => ({ ...v, products_services: next }))}
          onClearError={onClearError}
        />
      </FormSection>

      {/* Section C: Market Positioning */}
      <FormSection icon={<Sparkles size={16} className="text-primary" aria-hidden="true" />} title="Market positioning">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FormField
            id="onb-positioning"
            label={companyFieldLabels['positioning']}
            error={fieldErrors.positioning}
            provenance={fieldProvenance(review, 'positioning')}
            action={
              <button
                type="button"
                className="ai-improve-btn"
                disabled={chatPending}
                onClick={() =>
                  onAskCopilot(
                    draft.positioning.trim()
                      ? `Make my business positioning statement more specific and differentiated:\n"${draft.positioning}"`
                      : 'Draft a clear positioning statement based on my company overview and offerings.'
                  )
                }
              >
                <Wand2 size={11} aria-hidden="true" /> {draft.positioning.trim() ? 'Make more specific' : 'Draft with AI'}
              </button>
            }
          >
            <textarea
              id="onb-positioning"
              aria-label={companyFieldLabels['positioning']}
              rows={3}
              value={draft.positioning}
              maxLength={1000}
              onChange={e => {
                onClearError('positioning');
                onDraftChange(v => ({ ...v, positioning: e.target.value }));
              }}
              className={`ai-textarea ${fieldErrors.positioning ? 'is-invalid' : ''}`}
              placeholder="How you differentiate and the core problem you solve…"
            />
          </FormField>

          <FormField
            id="onb-specialties"
            label={companyFieldLabels['specialties']}
            hint="One specialty or differentiator per line."
            provenance={fieldProvenance(review, 'specialties')}
            action={
              <button
                type="button"
                className="ai-improve-btn"
                disabled={chatPending}
                onClick={() =>
                  onAskCopilot('Suggest 4 to 6 specific specialties and differentiators for my business profile.')
                }
              >
                <Wand2 size={11} aria-hidden="true" /> Suggest specialties
              </button>
            }
          >
            <textarea
              id="onb-specialties"
              rows={3}
              value={draft.specialties.join('\n')}
              onChange={e => onDraftChange(v => ({ ...v, specialties: e.target.value.split('\n') }))}
              className="ai-textarea"
              placeholder="e.g. Buyer-Intent Signals&#10;Pipeline Analytics"
            />
          </FormField>
        </div>
      </FormSection>

      {/* Section D: Target Market */}
      <FormSection icon={<Users2 size={16} className="text-primary" aria-hidden="true" />} title="Target market">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <FormField
            id="onb-target-customers"
            label={companyFieldLabels['target_customers']}
            hint="One customer group per line."
            provenance={fieldProvenance(review, 'target_customers')}
            action={
              <button
                type="button"
                className="ai-improve-btn"
                disabled={chatPending}
                onClick={() => onAskCopilot('Suggest target customer roles and teams for our offerings.')}
              >
                <Wand2 size={11} aria-hidden="true" /> Suggest
              </button>
            }
          >
            <textarea
              id="onb-target-customers"
              rows={3}
              value={draft.target_customers.join('\n')}
              onChange={e => onDraftChange(v => ({ ...v, target_customers: e.target.value.split('\n') }))}
              className="ai-textarea"
              placeholder="e.g. B2B Founders&#10;RevOps Teams"
            />
          </FormField>

          <FormField
            id="onb-target-industries"
            label={companyFieldLabels['target_industries']}
            hint="One industry per line."
            provenance={fieldProvenance(review, 'target_industries')}
            action={
              <button
                type="button"
                className="ai-improve-btn"
                disabled={chatPending}
                onClick={() => onAskCopilot('Suggest target industries that fit our products and positioning.')}
              >
                <Wand2 size={11} aria-hidden="true" /> Suggest target industries
              </button>
            }
          >
            <textarea
              id="onb-target-industries"
              rows={3}
              value={draft.target_industries.join('\n')}
              onChange={e => onDraftChange(v => ({ ...v, target_industries: e.target.value.split('\n') }))}
              className="ai-textarea"
              placeholder="e.g. B2B SaaS&#10;Growth Agencies"
            />
          </FormField>

          <FormField
            id="onb-countries"
            label={companyFieldLabels['countries_served']}
            hint="Leave blank for global markets."
            provenance={fieldProvenance(review, 'countries_served')}
          >
            <textarea
              id="onb-countries"
              rows={3}
              value={draft.countries_served.join('\n')}
              onChange={e => onDraftChange(v => ({ ...v, countries_served: e.target.value.split('\n') }))}
              className="ai-textarea"
              placeholder="e.g. United States&#10;United Kingdom"
            />
          </FormField>
        </div>
      </FormSection>

      {/* Single Primary Step 2 CTA — never ambiguously disabled; runs inline validation & focuses first invalid field */}
      <div className="ai-actions pt-5 border-t border-border/70">
        <Button size="lg" disabled={pending} onClick={onSave} className="ai-btn-primary">
          {pending ? 'Saving business profile…' : 'Save business profile & continue'}
        </Button>
        <Button variant="ghost" disabled={pending} onClick={onBack}>
          ← Back to your business
        </Button>
      </div>
    </section>
  );
}
