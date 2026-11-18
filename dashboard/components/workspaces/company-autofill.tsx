"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowUpRight,
  Check,
  ExternalLink,
  FileText,
  Globe,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import { request } from "@/lib/intelligence";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useWorkspaceCapabilities } from "./features";
import { useWorkspace } from "./use-workspace";
import { companyFieldLabels, type CompanyFields } from "./company-profile-types";

type Preview = {
  suggestions: Partial<CompanyFields>;
  sources: Record<string, { url: string | null; kind: string }>;
  evidence?: Record<string, { url: string | null; quote: string }[]>;
  source_url: string | null;
  retrieved_at: string;
  missing_fields?: string[];
  warnings?: string[];
  ownership_verified: false;
  pages_reviewed: number;
};

type Review = {
  id: string;
  website: string;
  status: "QUEUED" | "RUNNING" | "READY" | "FAILED" | "CANCELLED";
  error_code?: string | null;
  progress_stage: string;
  preview: Preview | null;
  can_retry: boolean;
};

type Capabilities = {
  can_analyze: boolean;
  ai_enabled: boolean;
  configured: boolean;
  max_pages: number;
  estimated_ai_operations?: number;
  ai_calls_remaining?: number | null;
  ai_calls_limit?: number | null;
};

function formatFieldValue(value: CompanyFields[keyof CompanyFields] | undefined): string {
  if (!value) return "—";
  if (Array.isArray(value)) {
    if (!value.length) return "—";
    return value
      .map((item) =>
        typeof item === "string"
          ? item
          : item.name + (item.description ? ` — ${item.description}` : "")
      )
      .join("; ");
  }
  return String(value) || "—";
}

function normalizeWebsiteUrl(raw: string): string {
  const s = raw.trim();
  if (!s) return "";
  if (/^https?:\/\//i.test(s)) return s;
  return `https://${s}`;
}

function SuggestionsReview({
  review,
  currentValues,
  onApply,
  onManual,
}: {
  review: Review;
  currentValues?: Partial<CompanyFields>;
  onApply: (values: Partial<CompanyFields>, review: string, fields: string[]) => void;
  onManual: () => void;
}) {
  const preview = review.preview!;
  const entries = Object.entries(preview.suggestions).filter(
    ([key]) => key in companyFieldLabels
  );
  const [selected, setSelected] = useState<string[]>(() => entries.map(([k]) => k));
  const [applied, setApplied] = useState(false);

  const allSelected = selected.length === entries.length && entries.length > 0;

  return (
    <section
      aria-label="Suggested company details"
      className="rounded-xl border border-primary/25 bg-card p-4 space-y-4"
    >
      <div className="flex flex-wrap items-start justify-between gap-2 border-b border-border/70 pb-3">
        <div>
          <h4 className="text-xs font-semibold text-foreground">
            Review AI-Extracted Profile Draft
          </h4>
          <p className="text-[11px] text-muted-foreground mt-0.5">
            {preview.pages_reviewed
              ? `${preview.pages_reviewed} public page${preview.pages_reviewed === 1 ? "" : "s"} reviewed`
              : "Generated from your business description"}{" "}
            · Nothing is saved until you approve &amp; save.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setSelected(allSelected ? [] : entries.map(([k]) => k))}
          className="text-[11px] font-medium text-primary hover:underline cursor-pointer"
        >
          {allSelected ? "Deselect all" : "Select all"}
        </button>
      </div>

      <div className="space-y-2.5">
        {entries.map(([key, value]) => {
          const typedKey = key as keyof CompanyFields;
          const isChecked = selected.includes(key);
          const currentVal = currentValues?.[typedKey];
          const evidenceList = preview.evidence?.[key] || [];
          const sourceUrl = evidenceList[0]?.url || preview.sources[key]?.url;
          const isGrounded = evidenceList.length > 0 || Boolean(sourceUrl);

          return (
            <div
              key={key}
              className={`rounded-lg border p-3 text-xs transition-colors ${
                isChecked
                  ? "border-primary/40 bg-primary/[0.03]"
                  : "border-border/70 bg-muted/10"
              }`}
            >
              <label className="flex items-start gap-2.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={isChecked}
                  onChange={(e) => {
                    setApplied(false);
                    setSelected(
                      e.target.checked
                        ? [...selected, key]
                        : selected.filter((item) => item !== key)
                    );
                  }}
                  className="mt-0.5 accent-primary"
                />
                <div className="min-w-0 flex-1 space-y-1.5">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span className="font-semibold text-foreground">
                      {companyFieldLabels[typedKey]}
                    </span>
                    <span
                      className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium ${
                        isGrounded
                          ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
                          : "bg-amber-500/10 text-amber-700 dark:text-amber-300"
                      }`}
                    >
                      {isGrounded ? "Grounded fact" : "Suggestion"}
                    </span>
                    {sourceUrl && (
                      <a
                        href={sourceUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="inline-flex items-center gap-0.5 text-[10px] text-primary hover:underline"
                      >
                        Source <ExternalLink size={10} />
                      </a>
                    )}
                  </div>

                  {currentValues && formatFieldValue(currentVal) !== "—" && (
                    <p className="text-[11px] text-muted-foreground line-through decoration-muted-foreground/50">
                      Current: {formatFieldValue(currentVal)}
                    </p>
                  )}
                  <p className="text-xs text-foreground leading-relaxed">
                    {formatFieldValue(value as CompanyFields[keyof CompanyFields])}
                  </p>

                  {evidenceList.length > 0 && (
                    <details className="pt-1">
                      <summary className="cursor-pointer text-[11px] text-muted-foreground hover:text-foreground">
                        Supporting evidence ({evidenceList.length})
                      </summary>
                      <div className="mt-1.5 space-y-1.5 pl-2 border-l-2 border-border">
                        {evidenceList.map((proof, idx) => (
                          <blockquote key={idx} className="text-[11px] text-muted-foreground">
                            <p>&ldquo;{proof.quote}&rdquo;</p>
                          </blockquote>
                        ))}
                      </div>
                    </details>
                  )}
                </div>
              </label>
            </div>
          );
        })}
      </div>

      {!!preview.missing_fields?.length && (
        <div className="rounded-lg border border-border/70 bg-muted/20 px-3 py-2 text-[11px] text-muted-foreground">
          <strong className="text-foreground">Unknown / not established:</strong>{" "}
          {preview.missing_fields
            .map((f) => companyFieldLabels[f as keyof CompanyFields] || f)
            .join(", ")}
          . These remain untouched unless you edit them manually.
        </div>
      )}

      {preview.warnings?.map((w) => (
        <p key={w} className="text-[11px] text-amber-700 dark:text-amber-300">
          {w}
        </p>
      ))}

      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border/70 pt-3">
        <span className="text-[11px] text-muted-foreground">
          Website analysis never verifies domain ownership.
        </span>
        <div className="flex items-center gap-2">
          <Button type="button" size="sm" variant="outline" onClick={onManual} className="h-8 text-xs">
            Edit Manually
          </Button>
          <Button
            type="button"
            size="sm"
            disabled={!selected.length}
            onClick={() => {
              onApply(
                Object.fromEntries(
                  selected.map((k) => [k, preview.suggestions[k as keyof CompanyFields]])
                ),
                review.id,
                selected
              );
              setApplied(true);
            }}
            className="h-8 text-xs gap-1.5"
          >
            <Check size={13} />
            Apply Selected ({selected.length})
          </Button>
        </div>
      </div>

      {applied && (
        <p role="status" className="text-xs font-medium text-emerald-700 dark:text-emerald-400">
          Selected fields copied into your profile editor. Review and click Save Changes to persist.
        </p>
      )}
    </section>
  );
}

export function CompanyAutofill({
  initialWebsite,
  canEdit,
  currentValues,
  onApply,
  onManual,
}: {
  initialWebsite: string;
  canEdit: boolean;
  currentValues?: Partial<CompanyFields>;
  onApply: (values: Partial<CompanyFields>, review: string, fields: string[]) => void;
  onManual: () => void;
}) {
  const enabled = useWorkspaceCapabilities().companyDiscovery;
  const workspace = useWorkspace();
  const orgId = workspace.data?.active_organization_id || "";
  const client = useQueryClient();

  const [mode, setMode] = useState<"WEBSITE" | "DESCRIPTION">("WEBSITE");
  const [website, setWebsite] = useState(initialWebsite);
  const [description, setDescription] = useState("");
  const [key, setKey] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const requestId = useRef<string | null>(null);
  const pollUntil = useRef(0);

  const capability = useQuery({
    queryKey: ["company-autofill-capabilities", orgId || "default"],
    queryFn: ({ signal }) =>
      request<Capabilities>("/organization/website-reviews/capabilities", { signal }),
    enabled: enabled && canEdit,
    retry: false,
  });

  const review = useQuery({
    queryKey: ["company-autofill", orgId, key],
    queryFn: ({ signal }) =>
      request<Review>(`/organization/website-reviews/${key}`, { signal }),
    enabled: Boolean(key),
    retry: false,
    refetchInterval: (query) =>
      Date.now() < pollUntil.current &&
      ["QUEUED", "RUNNING"].includes(query.state.data?.status || "")
        ? 2000
        : false,
  });

  const busy =
    pending || review.data?.status === "QUEUED" || review.data?.status === "RUNNING";

  async function start() {
    if (busy || !capability.data?.can_analyze) return;
    setPending(true);
    setError("");
    requestId.current ??= crypto.randomUUID();
    try {
      const normalizedUrl = mode === "WEBSITE" ? normalizeWebsiteUrl(website) : "";
      const result = await request<Review>("/organization/website-reviews", {
        method: "POST",
        body: JSON.stringify({
          website: normalizedUrl,
          source_kind: mode,
          description: mode === "DESCRIPTION" ? description.trim() : "",
          use_ai: true,
          request_id: requestId.current,
        }),
      });
      client.setQueryData(["company-autofill", orgId, result.id], result);
      pollUntil.current = Date.now() + 120000;
      setKey(result.id);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Analysis could not be started. You can still edit your profile manually."
      );
    } finally {
      setPending(false);
    }
  }

  async function control(action: "CANCEL" | "RETRY") {
    if (!key || pending) return;
    setPending(true);
    setError("");
    try {
      const result = await request<Review>(`/organization/website-reviews/${key}/control`, {
        method: "POST",
        body: JSON.stringify({ action }),
      });
      client.setQueryData(["company-autofill", orgId, key], result);
      if (action === "RETRY") pollUntil.current = Date.now() + 120000;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update analysis job.");
    } finally {
      setPending(false);
    }
  }

  if (!enabled || !canEdit) return null;

  return (
    <section
      aria-label="Company profile AI research"
      className="rounded-xl border border-border bg-card p-4 space-y-4"
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="flex items-start gap-2.5">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Sparkles size={15} />
          </span>
          <div>
            <h3 className="text-sm font-semibold text-foreground">
              AI Company Profile Research
            </h3>
            <p className="text-[11px] text-muted-foreground">
              Grounded extraction from up to {capability.data?.max_pages ?? 5} public pages or your business description. Every field is reviewed before saving.
            </p>
          </div>
        </div>
        {capability.data && (
          <span className="rounded-full border border-border bg-muted/40 px-2.5 py-0.5 text-[11px] text-muted-foreground tabular-nums">
            Cost: {capability.data.estimated_ai_operations ?? 1} AI op
            {capability.data.ai_calls_remaining != null
              ? ` · ${capability.data.ai_calls_remaining} left`
              : ""}
          </span>
        )}
      </div>

      {capability.isPending ? (
        <p role="status" className="text-xs text-muted-foreground">
          Checking AI research availability…
        </p>
      ) : capability.isError ? (
        <div role="alert" className="flex items-center justify-between gap-2 rounded-lg border border-destructive/25 bg-destructive/5 px-3 py-2 text-xs text-destructive">
          <span>Could not check AI analysis availability.</span>
          <Button size="sm" variant="outline" onClick={() => void capability.refetch()} className="h-7 text-xs">
            Retry
          </Button>
        </div>
      ) : !capability.data?.can_analyze ? (
        <p className="text-xs text-muted-foreground">
          AI company research is unavailable in this workspace. You can edit all profile fields manually.
        </p>
      ) : (
        <div className="space-y-3">
          <div className="inline-flex rounded-lg border border-border bg-muted/30 p-0.5" role="group" aria-label="Information source">
            <button
              type="button"
              aria-pressed={mode === "WEBSITE"}
              disabled={busy}
              onClick={() => {
                setMode("WEBSITE");
                requestId.current = null;
              }}
              className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium cursor-pointer transition-colors ${
                mode === "WEBSITE"
                  ? "bg-card text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Globe size={13} />
              Analyze Website
            </button>
            <button
              type="button"
              aria-pressed={mode === "DESCRIPTION"}
              disabled={busy}
              onClick={() => {
                setMode("DESCRIPTION");
                requestId.current = null;
              }}
              className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium cursor-pointer transition-colors ${
                mode === "DESCRIPTION"
                  ? "bg-card text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <FileText size={13} />
              Describe Business
            </button>
          </div>

          {mode === "WEBSITE" ? (
            <div className="flex flex-wrap items-center gap-2">
              <Input
                id="autofill-website"
                type="text"
                inputMode="url"
                placeholder="https://yourcompany.com"
                maxLength={600}
                disabled={busy}
                value={website}
                onChange={(e) => {
                  setWebsite(e.target.value);
                  requestId.current = null;
                }}
                className="h-8 flex-1 min-w-[220px] text-xs"
              />
              <Button
                type="button"
                size="sm"
                disabled={busy || !website.trim()}
                onClick={() => void start()}
                className="h-8 text-xs gap-1.5"
              >
                <Sparkles size={13} />
                {busy ? "Analyzing…" : "Analyze Website with AI"}
              </Button>
            </div>
          ) : (
            <div className="space-y-2.5">
              <textarea
                id="autofill-description"
                rows={4}
                maxLength={6000}
                disabled={busy}
                value={description}
                onChange={(e) => {
                  setDescription(e.target.value);
                  requestId.current = null;
                }}
                placeholder="Describe what your company builds, who you serve, your products/services, and target markets (min 20 characters)…"
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              />
              <div className="flex flex-wrap items-center justify-between gap-2">
                <Link
                  href={`/intelligence/assistant?prompt=${encodeURIComponent(
                    "Help me draft a clean, grounded company profile and product positioning for my workspace."
                  )}&context=overview`}
                  className="inline-flex items-center gap-1 text-[11px] font-medium text-primary hover:underline"
                >
                  Draft interactively in AI Assistant <ArrowUpRight size={12} />
                </Link>
                <Button
                  type="button"
                  size="sm"
                  disabled={busy || description.trim().length < 20}
                  onClick={() => void start()}
                  className="h-8 text-xs gap-1.5"
                >
                  <Sparkles size={13} />
                  {busy ? "Generating draft…" : "Generate Profile Draft"}
                </Button>
              </div>
            </div>
          )}
        </div>
      )}

      {key && review.data && (
        <div className="space-y-3 border-t border-border/70 pt-3">
          <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
            <span role="status" className="font-medium text-foreground">
              {review.data.status === "QUEUED"
                ? "Queued for grounded website research…"
                : review.data.status === "RUNNING"
                  ? review.data.progress_stage === "ANALYZING"
                    ? "Extracting grounded company facts & offerings…"
                    : "Reading permitted public company pages…"
                  : review.data.status === "READY"
                    ? "Draft ready for selective review."
                    : review.data.status === "CANCELLED"
                      ? "Analysis cancelled."
                      : `Analysis failed${review.data.error_code ? ` (${review.data.error_code})` : ""}. Your saved profile was not modified.`}
            </span>
            <div className="flex items-center gap-1.5">
              {["QUEUED", "RUNNING"].includes(review.data.status) && (
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  disabled={pending}
                  onClick={() => void control("CANCEL")}
                  className="h-7 text-[11px]"
                >
                  Cancel
                </Button>
              )}
              {review.data.can_retry && (
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  disabled={pending}
                  onClick={() => void control("RETRY")}
                  className="h-7 text-[11px] gap-1"
                >
                  <RefreshCw size={11} /> Retry
                </Button>
              )}
            </div>
          </div>

          {review.data.status === "READY" && review.data.preview && (
            <SuggestionsReview
              key={review.data.id}
              review={review.data}
              currentValues={currentValues}
              onApply={onApply}
              onManual={onManual}
            />
          )}
        </div>
      )}

      {error && (
        <div role="alert" className="flex items-start gap-2 rounded-lg border border-destructive/25 bg-destructive/5 px-3 py-2 text-xs text-destructive">
          <AlertTriangle size={13} className="shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}
    </section>
  );
}
