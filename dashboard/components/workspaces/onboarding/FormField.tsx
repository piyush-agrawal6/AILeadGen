'use client';
import React from 'react';
import { AlertCircle } from 'lucide-react';
import { fieldElementId, type FieldErrors } from './types';

export function InlineFieldError({ id, message }: { id: string; message?: string }) {
  if (!message) return null;
  return (
    <p id={id} role="alert" className="pb-field-error">
      <AlertCircle size={13} className="flex-shrink-0 mt-0.5" aria-hidden="true" />
      <span>{message}</span>
    </p>
  );
}

export function FormField({
  id,
  label,
  hint,
  error,
  action,
  provenance,
  children
}: {
  id: string;
  label: string;
  hint?: string;
  error?: string;
  action?: React.ReactNode;
  provenance?: 'supported' | 'suggested' | null;
  children: React.ReactNode;
}) {
  const errId = `${id}-error`;
  return (
    <div className="pb-form-field">
      <div className="ai-field-header">
        <div className="flex items-center gap-2 min-w-0">
          <label htmlFor={id} className={`text-xs font-semibold ${error ? 'text-destructive' : 'text-foreground'}`}>
            {label}
          </label>
          {provenance === 'supported' && (
            <span className="pb-provenance-pill is-supported" title="Supported by your public website">
              From website
            </span>
          )}
          {provenance === 'suggested' && (
            <span className="pb-provenance-pill is-suggested" title="AI suggestion — review before saving">
              AI suggestion
            </span>
          )}
        </div>
        {action}
      </div>
      {children}
      <InlineFieldError id={errId} message={error} />
      {hint && !error && <p className="text-[11px] text-muted-foreground mt-1">{hint}</p>}
    </div>
  );
}

export function FormSection({
  id,
  icon,
  title,
  count,
  action,
  children
}: {
  id?: string;
  icon: React.ReactNode;
  title: string;
  count?: number;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div id={id} className="pb-onb-section">
      <div className="pb-onb-section-head">
        <div className="pb-onb-section-title">
          {icon}
          <span>{title}</span>
          {typeof count === 'number' && (
            <span className="text-xs font-normal text-muted-foreground">({count})</span>
          )}
        </div>
        {action}
      </div>
      {children}
    </div>
  );
}

export function ErrorSummary({
  errors,
  title = 'Please fix the following before continuing'
}: {
  errors: FieldErrors;
  title?: string;
}) {
  const entries = Object.entries(errors);
  if (entries.length < 2) return null;
  return (
    <div role="alert" tabIndex={-1} className="pb-error-summary mb-5" aria-labelledby="pb-error-summary-heading">
      <div className="flex items-center gap-2 text-xs font-semibold text-destructive">
        <AlertCircle size={15} className="flex-shrink-0" aria-hidden="true" />
        <h3 id="pb-error-summary-heading">{title}</h3>
      </div>
      <ul className="mt-2 space-y-1 pl-6 list-disc text-xs">
        {entries.map(([key, msg]) => (
          <li key={key}>
            <button
              type="button"
              className="text-destructive underline text-left hover:opacity-80"
              onClick={() => {
                const el = document.getElementById(fieldElementId(key));
                el?.scrollIntoView?.({ behavior: 'smooth', block: 'center' });
                (el as HTMLElement | null)?.focus?.({ preventScroll: true });
              }}
            >
              {msg}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
