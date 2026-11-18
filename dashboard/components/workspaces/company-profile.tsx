"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  Building2,
  CheckCircle2,
  Edit3,
  ExternalLink,
  Globe,
  Layers,
  Plus,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";
import { request } from "@/lib/intelligence";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useWorkspace } from "./use-workspace";
import { CompanyAutofill } from "./company-autofill";
import {
  companyDraft,
  type CompanyFields,
  type CompanyProfile,
} from "./company-profile-types";

const COMMON_TIMEZONES = [
  "UTC",
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
  "Europe/London",
  "Europe/Berlin",
  "Europe/Paris",
  "Asia/Dubai",
  "Asia/Kolkata",
  "Asia/Singapore",
  "Asia/Tokyo",
  "Australia/Sydney",
];

const COMPANY_SIZES = [
  "",
  "1-10",
  "11-50",
  "51-200",
  "201-500",
  "501-1,000",
  "1,000+",
];

function ListTagEditor({
  id,
  label,
  values,
  placeholder,
  disabled,
  onChange,
}: {
  id: string;
  label: string;
  values: string[];
  placeholder: string;
  disabled?: boolean;
  onChange: (next: string[]) => void;
}) {
  const [draft, setDraft] = useState("");

  function commit(raw: string) {
    const clean = raw.trim().replace(/,+/g, "");
    if (!clean || values.includes(clean)) {
      setDraft("");
      return;
    }
    onChange([...values, clean]);
    setDraft("");
  }

  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="text-xs font-medium text-foreground">
        {label}
      </label>
      <div className="flex flex-wrap items-center gap-1.5 rounded-lg border border-border bg-background px-2.5 py-1.5 focus-within:ring-1 focus-within:ring-primary">
        {values.map((tag) => (
          <span
            key={tag}
            className="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-0.5 text-xs text-foreground"
          >
            <span>{tag}</span>
            {!disabled && (
              <button
                type="button"
                aria-label={`Remove ${tag}`}
                onClick={() => onChange(values.filter((v) => v !== tag))}
                className="rounded hover:bg-muted-foreground/20 p-0.5 cursor-pointer"
              >
                <X size={11} />
              </button>
            )}
          </span>
        ))}
        <input
          id={id}
          type="text"
          value={draft}
          disabled={disabled}
          placeholder={placeholder}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={() => {
            if (draft.trim()) commit(draft);
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === ",") {
              e.preventDefault();
              commit(draft);
            } else if (e.key === "Backspace" && !draft && values.length > 0) {
              onChange(values.slice(0, -1));
            }
          }}
          className="min-w-[140px] flex-1 bg-transparent py-0.5 text-xs text-foreground outline-none placeholder:text-muted-foreground"
        />
      </div>
    </div>
  );
}

function PillList({ items, empty }: { items: string[]; empty: string }) {
  if (!items || items.length === 0) {
    return <span className="text-xs text-muted-foreground">{empty}</span>;
  }
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((item) => (
        <span
          key={item}
          className="rounded-md border border-border bg-muted/30 px-2 py-0.5 text-[11px] text-foreground"
        >
          {item}
        </span>
      ))}
    </div>
  );
}

function ProfileWorkspace({
  profile,
  onSaved,
  onDirty,
  onReload,
}: {
  profile: CompanyProfile;
  onSaved: (value: CompanyProfile) => void;
  onDirty: (dirty: boolean) => void;
  onReload: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [showAi, setShowAi] = useState(false);
  const [values, setValues] = useState<CompanyFields>(() => companyDraft(profile));
  const [review, setReview] = useState<{ review_id: string; reviewed_fields: string[] } | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const issues = profile.quality_issues || [];
  const warningIssues = issues.filter((i) => i.severity === "warning");

  function edit(patch: Partial<CompanyFields>) {
    setValues((prev) => ({ ...prev, ...patch }));
    onDirty(true);
  }

  async function save(event: React.FormEvent) {
    event.preventDefault();
    if (pending || !profile.can_edit) return;
    setPending(true);
    setError(null);
    try {
      const result = await request<CompanyProfile>("/organization/profile", {
        method: "PUT",
        body: JSON.stringify({
          ...values,
          countries_served: values.countries_served.filter(Boolean),
          target_customers: values.target_customers.filter(Boolean),
          target_industries: values.target_industries.filter(Boolean),
          specialties: values.specialties.filter(Boolean),
          version: profile.version,
          ...review,
        }),
      });
      onDirty(false);
      setEditing(false);
      setShowAi(false);
      onSaved(result);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Company profile could not be saved.");
    } finally {
      setPending(false);
    }
  }

  const tzOptions = COMMON_TIMEZONES.includes(values.timezone)
    ? COMMON_TIMEZONES
    : [values.timezone || "UTC", ...COMMON_TIMEZONES];

  const hqDisplay = [profile.city, profile.country].filter(Boolean).join(", ") || "—";

  return (
    <div className="space-y-4">
      {/* Non-destructive Data Quality Review Banner */}
      {warningIssues.length > 0 && (
        <div
          role="status"
          className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 space-y-2.5"
        >
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div className="flex items-start gap-2">
              <AlertTriangle size={15} className="text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
              <div>
                <p className="text-xs font-semibold text-foreground">
                  {warningIssues.length} profile field{warningIssues.length === 1 ? "" : "s"} flagged for review
                </p>
                <p className="text-[11px] text-muted-foreground">
                  Low-quality or placeholder values reduce discovery &amp; ICP accuracy. Existing values are kept untouched until you approve changes.
                </p>
              </div>
            </div>
            {profile.can_edit && (
              <div className="flex items-center gap-1.5 shrink-0">
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setShowAi(true);
                    setEditing(true);
                  }}
                  className="h-7 px-2.5 text-[11px] gap-1"
                >
                  <Sparkles size={12} /> Fix with AI
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  onClick={() => setEditing(true)}
                  className="h-7 px-2.5 text-[11px]"
                >
                  Edit
                </Button>
              </div>
            )}
          </div>
          <ul className="space-y-1 pl-6 list-disc text-[11px] text-muted-foreground">
            {warningIssues.slice(0, 4).map((iss) => (
              <li key={`${iss.field}-${iss.code}`}>{iss.message}</li>
            ))}
          </ul>
        </div>
      )}

      {/* AI Company Profile Research Panel */}
      {showAi && profile.can_edit && (
        <CompanyAutofill
          initialWebsite={values.website || profile.website}
          canEdit={profile.can_edit && !pending}
          currentValues={values}
          onManual={() => {
            setShowAi(false);
            setEditing(true);
          }}
          onApply={(patch, id, selected) => {
            edit(patch);
            setReview({ review_id: id, reviewed_fields: selected });
            setEditing(true);
          }}
        />
      )}

      {/* READ-FIRST SUMMARY VIEW */}
      {!editing ? (
        <div className="space-y-4">
          {/* Card 1: Primary Company Information */}
          <section className="rounded-xl border border-border bg-card p-5 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <Building2 size={15} className="text-primary" />
                <h3 className="text-sm font-semibold text-foreground">Primary Company Information</h3>
              </div>
              {profile.can_edit && (
                <div className="flex items-center gap-2">
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => setShowAi((v) => !v)}
                    className="h-8 text-xs gap-1.5"
                  >
                    <Sparkles size={13} />
                    {showAi ? "Hide AI Research" : "Analyze Website with AI"}
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    onClick={() => {
                      setValues(companyDraft(profile));
                      setEditing(true);
                    }}
                    className="h-8 text-xs gap-1.5"
                  >
                    <Edit3 size={13} />
                    Edit Profile
                  </Button>
                </div>
              )}
            </div>

            <dl className="grid gap-3.5 sm:grid-cols-2 lg:grid-cols-3 border-t border-border/70 pt-3.5 text-xs">
              <div>
                <dt className="text-[11px] text-muted-foreground">Company name</dt>
                <dd className="font-semibold text-foreground mt-0.5">{profile.name || "—"}</dd>
              </div>
              <div>
                <dt className="text-[11px] text-muted-foreground">Website</dt>
                <dd className="font-medium text-foreground mt-0.5">
                  {profile.website ? (
                    <a
                      href={profile.website}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-primary hover:underline break-all"
                    >
                      {profile.website.replace(/^https?:\/\//, "")}
                      <ExternalLink size={11} />
                    </a>
                  ) : (
                    "—"
                  )}
                </dd>
              </div>
              <div>
                <dt className="text-[11px] text-muted-foreground">Industry</dt>
                <dd className="font-medium text-foreground mt-0.5">{profile.industry || "—"}</dd>
              </div>
              <div>
                <dt className="text-[11px] text-muted-foreground">Company size</dt>
                <dd className="font-medium text-foreground mt-0.5">{profile.company_size || "—"}</dd>
              </div>
              <div>
                <dt className="text-[11px] text-muted-foreground">Headquarters</dt>
                <dd className="font-medium text-foreground mt-0.5">{hqDisplay}</dd>
              </div>
              <div>
                <dt className="text-[11px] text-muted-foreground">Timezone</dt>
                <dd className="font-medium text-foreground mt-0.5">{profile.timezone || "UTC"}</dd>
              </div>
            </dl>
          </section>

          {/* Card 2: Business Overview */}
          <section className="rounded-xl border border-border bg-card p-5 space-y-4">
            <div className="flex items-center gap-2">
              <Globe size={15} className="text-primary" />
              <h3 className="text-sm font-semibold text-foreground">Business Overview</h3>
            </div>

            <div className="space-y-3 border-t border-border/70 pt-3.5 text-xs">
              <div>
                <p className="text-[11px] text-muted-foreground mb-1">Company description</p>
                <p className="text-foreground leading-relaxed">
                  {profile.description || <span className="text-muted-foreground">Not set</span>}
                </p>
              </div>
              {profile.positioning && (
                <div>
                  <p className="text-[11px] text-muted-foreground mb-1">Business positioning</p>
                  <p className="text-foreground leading-relaxed">{profile.positioning}</p>
                </div>
              )}
              <div className="grid gap-3.5 sm:grid-cols-2 pt-1">
                <div className="space-y-1">
                  <p className="text-[11px] text-muted-foreground">Countries served</p>
                  <PillList items={profile.countries_served} empty="Not specified" />
                </div>
                <div className="space-y-1">
                  <p className="text-[11px] text-muted-foreground">Target customers</p>
                  <PillList items={profile.target_customers} empty="Not specified" />
                </div>
                <div className="space-y-1">
                  <p className="text-[11px] text-muted-foreground">Target industries</p>
                  <PillList items={profile.target_industries} empty="Not specified" />
                </div>
                <div className="space-y-1">
                  <p className="text-[11px] text-muted-foreground">Specialties</p>
                  <PillList items={profile.specialties} empty="Not specified" />
                </div>
              </div>
            </div>
          </section>

          {/* Card 3: Products & Services */}
          <section className="rounded-xl border border-border bg-card p-5 space-y-3.5">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <Layers size={15} className="text-primary" />
                <h3 className="text-sm font-semibold text-foreground">
                  Products &amp; Services ({(profile.products_services || []).length})
                </h3>
              </div>
              {profile.can_edit && (
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setValues(companyDraft(profile));
                    setEditing(true);
                  }}
                  className="h-7 px-2.5 text-[11px]"
                >
                  Manage Offerings
                </Button>
              )}
            </div>

            {(profile.products_services || []).length === 0 ? (
              <p className="text-xs text-muted-foreground border-t border-border/70 pt-3">
                No products or services listed yet. Add offerings or run AI website research so discovery understands what you sell.
              </p>
            ) : (
              <div className="grid gap-2.5 sm:grid-cols-2 border-t border-border/70 pt-3.5">
                {(profile.products_services || []).map((svc, idx) => (
                  <div
                    key={`${svc.name}-${idx}`}
                    className="rounded-lg border border-border/70 bg-muted/15 p-3 space-y-1"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-semibold text-foreground">{svc.name}</span>
                      {svc.category && (
                        <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
                          {svc.category}
                        </span>
                      )}
                    </div>
                    {svc.description && (
                      <p className="text-[11px] text-muted-foreground leading-relaxed">
                        {svc.description}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      ) : (
        /* STRUCTURED EDIT FORM */
        <form onSubmit={(e) => void save(e)} aria-label="Company profile" className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-primary/25 bg-primary/[0.03] px-4 py-3">
            <span className="text-xs font-semibold text-foreground">
              Editing Organization Profile
            </span>
            <div className="flex items-center gap-2">
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => setShowAi((v) => !v)}
                className="h-7 px-2.5 text-[11px] gap-1"
              >
                <Sparkles size={12} />
                {showAi ? "Hide AI Research" : "Use AI Research"}
              </Button>
              <Button
                type="button"
                size="sm"
                variant="ghost"
                disabled={pending}
                onClick={() => {
                  setValues(companyDraft(profile));
                  setEditing(false);
                  onDirty(false);
                }}
                className="h-7 px-2.5 text-[11px]"
              >
                Cancel
              </Button>
              <Button type="submit" size="sm" disabled={pending} className="h-7 px-3 text-[11px]">
                {pending ? "Saving…" : "Save Changes"}
              </Button>
            </div>
          </div>

          {error && (
            <div role="alert" className="flex items-center justify-between gap-2 rounded-xl border border-destructive/25 bg-destructive/5 px-3.5 py-2.5 text-xs text-destructive">
              <span>{error}</span>
              <Button type="button" size="sm" variant="outline" onClick={onReload} className="h-7 text-[11px]">
                Reload
              </Button>
            </div>
          )}

          {/* Primary Info Section */}
          <section className="rounded-xl border border-border bg-card p-5 space-y-4">
            <h3 className="text-xs font-semibold text-foreground">Primary Company Information</h3>
            <div className="grid gap-3.5 sm:grid-cols-2 lg:grid-cols-3">
              <div className="space-y-1">
                <label htmlFor="company-name" className="text-xs font-medium text-foreground">
                  Company name *
                </label>
                <Input
                  id="company-name"
                  required
                  minLength={2}
                  maxLength={120}
                  value={values.name}
                  disabled={pending}
                  onChange={(e) => edit({ name: e.target.value })}
                  className="h-8 text-xs"
                />
              </div>
              <div className="space-y-1">
                <label htmlFor="company-website" className="text-xs font-medium text-foreground">
                  Website
                </label>
                <Input
                  id="company-website"
                  type="url"
                  placeholder="https://company.com"
                  maxLength={600}
                  value={values.website}
                  disabled={pending}
                  onChange={(e) => edit({ website: e.target.value })}
                  className="h-8 text-xs"
                />
              </div>
              <div className="space-y-1">
                <label htmlFor="company-industry" className="text-xs font-medium text-foreground">
                  Industry
                </label>
                <Input
                  id="company-industry"
                  placeholder="e.g. B2B SaaS, Developer Tools"
                  maxLength={100}
                  value={values.industry}
                  disabled={pending}
                  onChange={(e) => edit({ industry: e.target.value })}
                  className="h-8 text-xs"
                />
              </div>
              <div className="space-y-1">
                <label htmlFor="company-size" className="text-xs font-medium text-foreground">
                  Company size
                </label>
                <select
                  id="company-size"
                  value={COMPANY_SIZES.includes(values.company_size) ? values.company_size : ""}
                  disabled={pending}
                  onChange={(e) => edit({ company_size: e.target.value })}
                  className="h-8 w-full rounded-lg border border-border bg-background px-2.5 text-xs text-foreground"
                >
                  <option value="">Select size</option>
                  {COMPANY_SIZES.filter(Boolean).map((sz) => (
                    <option key={sz} value={sz}>
                      {sz} employees
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-1">
                <label htmlFor="company-city" className="text-xs font-medium text-foreground">
                  Headquarters city
                </label>
                <Input
                  id="company-city"
                  maxLength={100}
                  value={values.city}
                  disabled={pending}
                  onChange={(e) => edit({ city: e.target.value })}
                  className="h-8 text-xs"
                />
              </div>
              <div className="space-y-1">
                <label htmlFor="company-country" className="text-xs font-medium text-foreground">
                  Headquarters country
                </label>
                <Input
                  id="company-country"
                  maxLength={100}
                  value={values.country}
                  disabled={pending}
                  onChange={(e) => edit({ country: e.target.value })}
                  className="h-8 text-xs"
                />
              </div>
              <div className="space-y-1">
                <label htmlFor="company-timezone" className="text-xs font-medium text-foreground">
                  Timezone *
                </label>
                <select
                  id="company-timezone"
                  required
                  value={values.timezone || "UTC"}
                  disabled={pending}
                  onChange={(e) => edit({ timezone: e.target.value })}
                  className="h-8 w-full rounded-lg border border-border bg-background px-2.5 text-xs text-foreground"
                >
                  {tzOptions.map((tz) => (
                    <option key={tz} value={tz}>
                      {tz}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-1 sm:col-span-2">
                <label htmlFor="company-contact_email" className="text-xs font-medium text-foreground">
                  Public business contact email
                </label>
                <Input
                  id="company-contact_email"
                  type="email"
                  maxLength={254}
                  value={values.contact_email}
                  disabled={pending}
                  onChange={(e) => edit({ contact_email: e.target.value })}
                  className="h-8 text-xs"
                />
              </div>
            </div>
          </section>

          {/* Business Overview Section */}
          <section className="rounded-xl border border-border bg-card p-5 space-y-4">
            <h3 className="text-xs font-semibold text-foreground">Business Overview</h3>
            <div className="grid gap-3.5 sm:grid-cols-2">
              <div className="space-y-1 sm:col-span-2">
                <label htmlFor="company-description" className="text-xs font-medium text-foreground">
                  Company description
                </label>
                <textarea
                  id="company-description"
                  rows={3}
                  maxLength={1000}
                  value={values.description}
                  disabled={pending}
                  onChange={(e) => edit({ description: e.target.value })}
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>
              <div className="space-y-1 sm:col-span-2">
                <label htmlFor="company-positioning" className="text-xs font-medium text-foreground">
                  Business positioning
                </label>
                <textarea
                  id="company-positioning"
                  rows={2}
                  maxLength={1000}
                  value={values.positioning}
                  disabled={pending}
                  onChange={(e) => edit({ positioning: e.target.value })}
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>
              <ListTagEditor
                id="company-countries_served"
                label="Countries served"
                values={values.countries_served}
                placeholder="Type region & press Enter…"
                disabled={pending}
                onChange={(countries_served) => edit({ countries_served })}
              />
              <ListTagEditor
                id="company-target_customers"
                label="Target customers"
                values={values.target_customers}
                placeholder="Type buyer segment & press Enter…"
                disabled={pending}
                onChange={(target_customers) => edit({ target_customers })}
              />
              <ListTagEditor
                id="company-target_industries"
                label="Target industries"
                values={values.target_industries}
                placeholder="Type industry & press Enter…"
                disabled={pending}
                onChange={(target_industries) => edit({ target_industries })}
              />
              <ListTagEditor
                id="company-specialties"
                label="Specialties"
                values={values.specialties}
                placeholder="Type specialty & press Enter…"
                disabled={pending}
                onChange={(specialties) => edit({ specialties })}
              />
            </div>
          </section>

          {/* Products & Services Editor */}
          <section className="rounded-xl border border-border bg-card p-5 space-y-3.5" aria-label="Company products and services">
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-xs font-semibold text-foreground">Products &amp; Services</h3>
              <Button
                type="button"
                size="sm"
                variant="outline"
                disabled={pending || values.products_services.length >= 20}
                onClick={() =>
                  edit({
                    products_services: [
                      ...values.products_services,
                      { name: "", category: "", description: "" },
                    ],
                  })
                }
                className="h-7 px-2.5 text-[11px] gap-1"
              >
                <Plus size={12} /> Add Offering
              </Button>
            </div>

            <div className="space-y-3">
              {values.products_services.map((service, index) => (
                <div
                  key={index}
                  className="rounded-lg border border-border/70 bg-muted/15 p-3.5 space-y-2.5"
                >
                  <div className="grid gap-2.5 sm:grid-cols-2">
                    <Input
                      placeholder="Product or service name *"
                      required
                      minLength={2}
                      maxLength={120}
                      value={service.name}
                      disabled={pending}
                      onChange={(e) =>
                        edit({
                          products_services: values.products_services.map((item, i) =>
                            i === index ? { ...item, name: e.target.value } : item
                          ),
                        })
                      }
                      className="h-8 text-xs"
                    />
                    <div className="flex items-center gap-2">
                      <Input
                        placeholder="Category (optional)"
                        maxLength={100}
                        value={service.category}
                        disabled={pending}
                        onChange={(e) =>
                          edit({
                            products_services: values.products_services.map((item, i) =>
                              i === index ? { ...item, category: e.target.value } : item
                            ),
                          })
                        }
                        className="h-8 text-xs flex-1"
                      />
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        aria-label={`Remove offering ${index + 1}`}
                        onClick={() =>
                          edit({
                            products_services: values.products_services.filter((_, i) => i !== index),
                          })
                        }
                        className="h-8 px-2 text-muted-foreground hover:text-destructive"
                      >
                        <Trash2 size={13} />
                      </Button>
                    </div>
                  </div>
                  <textarea
                    rows={2}
                    maxLength={1000}
                    placeholder="Concise description of what this product or service delivers…"
                    value={service.description}
                    disabled={pending}
                    onChange={(e) =>
                      edit({
                        products_services: values.products_services.map((item, i) =>
                          i === index ? { ...item, description: e.target.value } : item
                        ),
                      })
                    }
                    className="w-full rounded-lg border border-border bg-background px-3 py-1.5 text-xs text-foreground"
                  />
                </div>
              ))}
            </div>
          </section>

          <div className="flex justify-end gap-2">
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={pending}
              onClick={() => {
                setValues(companyDraft(profile));
                setEditing(false);
                onDirty(false);
              }}
            >
              Cancel
            </Button>
            <Button type="submit" size="sm" disabled={pending}>
              {pending ? "Saving…" : "Save Changes"}
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}

export function CompanyProfileSettings({
  embedded = false,
  onSaved,
  onDirty,
}: {
  embedded?: boolean;
  onSaved?: (value: CompanyProfile) => void;
  onDirty?: (dirty: boolean) => void;
}) {
  const client = useQueryClient();
  const workspace = useWorkspace();
  const orgId = workspace.data?.active_organization_id || "";
  const [savedNotice, setSavedNotice] = useState(false);

  const profile = useQuery({
    queryKey: ["organization-profile", orgId || "default"],
    queryFn: ({ signal }) => request<CompanyProfile>("/organization/profile", { signal }),
    retry: false,
    refetchOnWindowFocus: false,
  });

  return (
    <section className="space-y-4">
      {!embedded && (
        <header>
          <p className="page-eyebrow">Company settings</p>
          <h1 className="mt-1 text-xl font-bold tracking-tight">Organization Profile</h1>
        </header>
      )}

      {savedNotice && (
        <div role="status" className="flex items-center gap-2 rounded-xl border border-emerald-500/25 bg-emerald-500/10 px-3.5 py-2.5 text-xs font-medium text-emerald-700 dark:text-emerald-300">
          <CheckCircle2 size={14} />
          <span>Organization profile saved.</span>
        </div>
      )}

      {profile.isPending ? (
        <div className="space-y-3" role="status" aria-label="Loading company profile">
          <div className="h-36 rounded-xl border border-border bg-muted/30 animate-pulse" />
          <div className="h-44 rounded-xl border border-border bg-muted/30 animate-pulse" />
        </div>
      ) : profile.isError ? (
        <div role="alert" className="rounded-xl border border-destructive/25 bg-destructive/5 p-4 text-xs text-destructive space-y-2">
          <p>Company information could not be loaded.</p>
          <Button size="sm" variant="outline" onClick={() => void profile.refetch()}>
            Retry
          </Button>
        </div>
      ) : (
        profile.data && (
          <ProfileWorkspace
            key={profile.data.version || "new"}
            profile={profile.data}
            onDirty={(dirty) => {
              if (dirty) setSavedNotice(false);
              onDirty?.(dirty);
            }}
            onReload={() => {
              onDirty?.(false);
              void profile.refetch();
            }}
            onSaved={(value) => {
              client.setQueryData(["organization-profile", orgId], value);
              void client.invalidateQueries({ queryKey: ["account-workspaces"] });
              void client.invalidateQueries({ queryKey: ["onboarding-progress"] });
              setSavedNotice(true);
              onSaved?.(value);
            }}
          />
        )
      )}
    </section>
  );
}
