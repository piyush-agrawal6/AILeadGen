"use client";
import {RadarExport} from '../RadarExport';

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Sparkles,
  FileText,
  Bookmark,
  BookmarkCheck,
  Download,
  RotateCcw,
  AlertCircle,
  CheckCircle2,
  Clock,
  ExternalLink,
  ChevronRight,
  ArrowLeft,
  X,
  Layers,
  Send,
  Loader2,
  TrendingUp,
  SlidersHorizontal,
} from "lucide-react";
import { useRadarRead, useRadarMutation, useRadarCapabilities } from "../provider";
import { LoadingSkeleton, ErrorState, EmptyState, Badge } from "../ui";
import { ProviderLogo } from "../provider-logo";
import { SearchInput } from "@/components/ui/search-input";
import {
  emptyGrowthScope,
  type GrowthPage,
  type GrowthResearch,
  type GrowthScope,
  type GrowthCitation,
  type GrowthOverview,
} from "@/lib/growth";

interface GrowthResearchWorkspaceProps {
  researchId?: string;
  onNavigateTab?: (tabId: string) => void;
}

export function GrowthResearchWorkspace({ researchId, onNavigateTab }: GrowthResearchWorkspaceProps) {
  const router = useRouter();

  // Active form state for the AI Research Assistant
  const [title, setTitle] = useState("Market demand & buyer pain points");
  const [question, setQuestion] = useState("");
  const [kind, setKind] = useState<GrowthResearch["kind"]>("REPORT");
  const [reportType, setReportType] = useState("Market overview");
  const [scope, setScope] = useState<GrowthScope>(emptyGrowthScope);
  const [generating, setGenerating] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  // Reports listing state
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [savedOnly, setSavedOnly] = useState(false);

  const listingQuery = useRadarRead<GrowthPage<GrowthResearch>>(
    `/growth/research?page=${page}&saved=${savedOnly}&search=${encodeURIComponent(search)}`
  );
  const overviewQuery = useRadarRead<GrowthOverview>("/growth/overview");
  const mutation = useRadarMutation();
  const capabilities = useRadarCapabilities();

  // Handler to submit new AI research job
  async function handleStartResearch(e: React.FormEvent) {
    e.preventDefault();
    setErrorMsg("");
    setGenerating(true);

    try {
      const res = (await mutation.mutateAsync({
        path: "/growth/research",
        method: "POST",
        body: {
          kind,
          title: title.trim() || "Market research",
          question: question.trim(),
          report_type: reportType,
          scope,
          request_id: crypto.randomUUID(),
        },
      })) as GrowthResearch;

      if (res?.id) {
        router.push(`/intent-radar/growth/research/${res.id}`);
      } else {
        void listingQuery.refetch();
      }
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to initiate research generation.");
    } finally {
      setGenerating(false);
    }
  }

  // If a specific research report ID is given in URL, render the Detail Report View
  if (researchId) {
    return (
      <ResearchDetailViewer
        researchId={researchId}
        onBack={() => router.push("/intent-radar/growth/research")}
      />
    );
  }

  const reports = listingQuery.data?.items || [];
  const total = listingQuery.data?.total || 0;

  return (
    <div className="w-full min-w-0 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold tracking-tight text-foreground">AI Market Research Assistant</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Conduct AI-powered, citation-backed market synthesis from real customer discussions and buyer signals.
          </p>
        </div>
      </div>

      {/* 2-Column Layout: Left AI Assistant, Right Research Reports Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-[340px_1fr] gap-6 items-start">
        {/* LEFT PANEL: Persistent AI Research Assistant */}
        <aside className="space-y-4 lg:sticky lg:top-4">
          <section
            aria-label="AI Research Composer"
            className="rounded-2xl border border-primary/20 bg-card p-4 space-y-4 shadow-xs"
          >
            <div className="flex items-center gap-2 text-primary font-semibold text-xs border-b border-border/80 pb-2.5">
              <Sparkles size={15} />
              <span>Research Assistant</span>
            </div>

            <p className="text-[11px] text-muted-foreground leading-relaxed">
              Synthesize customer signals into structured reports with strict evidence citations.
            </p>

            {errorMsg && (
              <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-2.5 text-xs text-destructive flex items-center gap-2">
                <AlertCircle size={14} className="shrink-0" />
                <span>{errorMsg}</span>
              </div>
            )}

            <form onSubmit={handleStartResearch} className="space-y-3.5 text-xs">
              {/* Kind Selector */}
              <div className="space-y-1">
                <label className="font-medium text-foreground block">Research Output</label>
                <div className="grid grid-cols-3 gap-1 rounded-lg border border-border bg-background p-1 text-[11px]">
                  <button
                    type="button"
                    onClick={() => setKind("REPORT")}
                    className={`py-1 rounded font-medium transition-colors cursor-pointer ${
                      kind === "REPORT" ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    Report
                  </button>
                  <button
                    type="button"
                    onClick={() => setKind("THEMES")}
                    className={`py-1 rounded font-medium transition-colors cursor-pointer ${
                      kind === "THEMES" ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    Themes
                  </button>
                  <button
                    type="button"
                    onClick={() => setKind("RESEARCH")}
                    className={`py-1 rounded font-medium transition-colors cursor-pointer ${
                      kind === "RESEARCH" ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    Q&A
                  </button>
                </div>
              </div>

              {/* Title */}
              <div className="space-y-1">
                <label className="font-medium text-foreground block">Research Title</label>
                <input
                  type="text"
                  required
                  maxLength={120}
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. CRM Alternatives & Churn Drivers"
                  className="w-full h-8 rounded-lg border border-border bg-background px-2.5 text-xs text-foreground focus:border-primary focus:outline-none"
                />
              </div>

              {/* Specific Question / Prompt */}
              <div className="space-y-1">
                <label className="font-medium text-foreground block">
                  Focus Question <span className="text-muted-foreground font-normal">(optional)</span>
                </label>
                <textarea
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  placeholder="What specific problems or buyer criteria should this research analyze?"
                  rows={2}
                  className="w-full rounded-lg border border-border bg-background p-2 text-xs text-foreground focus:border-primary focus:outline-none resize-y"
                />
              </div>

              {/* Report Focus (if kind === 'REPORT') */}
              {kind === "REPORT" && (
                <div className="space-y-1">
                  <label className="font-medium text-foreground block">Report Template</label>
                  <select
                    value={reportType}
                    onChange={(e) => setReportType(e.target.value)}
                    className="w-full h-8 rounded-lg border border-border bg-background px-2 text-xs text-foreground focus:border-primary focus:outline-none"
                  >
                    <option value="Market overview">Market Overview & Demand</option>
                    <option value="Emerging demand">Emerging Demand & Trends</option>
                    <option value="Competitor alternatives">Competitor Alternatives & Pain</option>
                    <option value="Intent summary">Buyer Intent & Objections</option>
                    <option value="Opportunity shortlist">High-Priority Opportunities</option>
                    <option value="Market comparison">Multi-Period Comparison</option>
                  </select>
                </div>
              )}

              {/* Time Window Scope */}
              <div className="space-y-1">
                <label className="font-medium text-foreground block">Evidence Window</label>
                <select
                  value={scope.days}
                  onChange={(e) =>
                    setScope((prev) => ({
                      ...prev,
                      days: Number(e.target.value) as GrowthScope["days"],
                    }))
                  }
                  className="w-full h-8 rounded-lg border border-border bg-background px-2 text-xs text-foreground focus:border-primary focus:outline-none"
                >
                  <option value={0}>All available evidence</option>
                  <option value={7}>Last 7 days</option>
                  <option value={30}>Last 30 days</option>
                  <option value={90}>Last 90 days</option>
                </select>
              </div>

              {/* ICP Context */}
              {overviewQuery.data?.filter_options?.icps && overviewQuery.data.filter_options.icps.length > 0 && (
                <div className="space-y-1">
                  <label className="font-medium text-foreground block">Target ICP Context</label>
                  <select
                    value={scope.icp_id || ""}
                    onChange={(e) =>
                      setScope((prev) => ({
                        ...prev,
                        icp_id: e.target.value || null,
                      }))
                    }
                    className="w-full h-8 rounded-lg border border-border bg-background px-2 text-xs text-foreground focus:border-primary focus:outline-none"
                  >
                    <option value="">All / Workspace Default</option>
                    {overviewQuery.data.filter_options.icps.map((icp) => (
                      <option key={icp.id} value={icp.id}>
                        {icp.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <button
                type="submit"
                disabled={generating || mutation.isPending}
                className="w-full h-9 rounded-lg bg-primary font-semibold text-xs text-primary-foreground hover:bg-primary/90 transition-colors shadow-xs flex items-center justify-center gap-1.5 cursor-pointer"
              >
                {generating ? (
                  <>
                    <Loader2 size={13} className="animate-spin" />
                    <span>Analyzing Evidence…</span>
                  </>
                ) : (
                  <>
                    <Sparkles size={13} />
                    <span>Generate Research</span>
                  </>
                )}
              </button>
            </form>
          </section>
        </aside>

        {/* RIGHT PANEL: Research Reports Workspace */}
        <section className="space-y-4 min-w-0">
          {/* Filter Toolbar */}
          <div className="flex flex-wrap items-center justify-between gap-2.5 rounded-xl border border-border bg-card p-2.5">
            <div className="flex flex-wrap items-center gap-2 flex-1 min-w-[220px]">
              <SearchInput
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setPage(1);
                }}
                onClear={() => {
                  setSearch("");
                  setPage(1);
                }}
                placeholder="Search reports by title or topic…"
                wrapperClassName="flex-1 min-w-[180px]"
              />

              <button
                type="button"
                onClick={() => {
                  setSavedOnly(!savedOnly);
                  setPage(1);
                }}
                className={`inline-flex h-8 items-center gap-1.5 rounded-lg border px-2.5 text-xs font-medium transition-colors cursor-pointer ${
                  savedOnly
                    ? "border-primary/50 bg-primary/10 text-primary font-semibold"
                    : "border-border bg-background text-foreground hover:bg-muted"
                }`}
              >
                {savedOnly ? <BookmarkCheck size={13} /> : <Bookmark size={13} />}
                <span>Saved Reports</span>
              </button>
            </div>
          </div>

          {/* Reports Table */}
          {listingQuery.error ? (
            <ErrorState message={listingQuery.error.message} retry={() => void listingQuery.refetch()} />
          ) : listingQuery.isLoading ? (
            <LoadingSkeleton />
          ) : reports.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-border bg-card/50 p-12 text-center space-y-3">
              <FileText className="mx-auto h-8 w-8 text-muted-foreground/60" />
              <h3 className="text-sm font-semibold text-foreground">No research reports yet</h3>
              <p className="text-xs text-muted-foreground max-w-md mx-auto">
                Use the AI Research Assistant on the left to synthesize customer conversations and generate structured intelligence reports.
              </p>
            </div>
          ) : (
            <div className="rounded-xl border border-border bg-card overflow-hidden shadow-xs">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-border bg-muted/40 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                      <th className="py-3 px-4 min-w-[260px]">Research Report</th>
                      <th className="py-3 px-3 min-w-[100px]">Format</th>
                      <th className="py-3 px-3 min-w-[100px]">Status</th>
                      <th className="py-3 px-3 min-w-[110px]">Created</th>
                      <th className="py-3 px-3 text-right sticky right-0 bg-muted/95 backdrop-blur-xs min-w-[150px]">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/60">
                    {reports.map((item) => {
                      const isSaved = Boolean(item.saved_at);
                      const isCompleted = item.status === "COMPLETED";
                      const isFailed = item.status === "FAILED";
                      const isPending = !isCompleted && !isFailed;

                      return (
                        <tr key={item.id} className="group hover:bg-muted/30 transition-colors">
                          <td className="py-3 px-4">
                            <Link
                              href={`/intent-radar/growth/research/${item.id}`}
                              className="font-semibold text-foreground group-hover:text-primary transition-colors block text-xs"
                            >
                              {item.title}
                            </Link>
                            {item.question && (
                              <p className="text-[11px] text-muted-foreground line-clamp-1 mt-0.5">
                                {item.question}
                              </p>
                            )}
                          </td>

                          <td className="py-3 px-3 text-[11px]">
                            <span className="rounded bg-muted px-1.5 py-0.5 font-medium text-foreground">
                              {item.kind}
                            </span>
                          </td>

                          <td className="py-3 px-3 text-[11px]">
                            {isCompleted ? (
                              <span className="inline-flex items-center gap-1 text-emerald-600 font-medium">
                                <CheckCircle2 size={12} />
                                <span>Completed</span>
                              </span>
                            ) : isFailed ? (
                              <span className="inline-flex items-center gap-1 text-destructive font-medium">
                                <AlertCircle size={12} />
                                <span>Failed</span>
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 text-amber-600 font-medium">
                                <Clock size={12} className="animate-spin" />
                                <span>Processing</span>
                              </span>
                            )}
                          </td>

                          <td className="py-3 px-3 text-[11px] text-muted-foreground">
                            {new Date(item.created_at).toLocaleDateString()}
                          </td>

                          <td className="py-3 px-3 text-right sticky right-0 bg-card group-hover:bg-muted/30 transition-colors">
                            <div className="flex items-center justify-end gap-1.5">
                              <button
                                type="button"
                                onClick={() =>
                                  mutation.mutate({
                                    path: `/growth/research/${item.id}`,
                                    method: "PATCH",
                                    body: {
                                      revision: item.revision,
                                      saved: !isSaved,
                                    },
                                  })
                                }
                                className={`p-1.5 rounded-lg border text-muted-foreground hover:text-foreground transition-colors cursor-pointer ${
                                  isSaved
                                    ? "border-primary/40 text-primary bg-primary/5"
                                    : "border-border hover:bg-muted"
                                }`}
                                title={isSaved ? "Unsave report" : "Save report"}
                              >
                                <Bookmark size={12} className={isSaved ? "fill-primary" : ""} />
                              </button>

                              <Link
                                href={`/intent-radar/growth/research/${item.id}`}
                                className="inline-flex h-7 items-center gap-1 rounded-md bg-muted px-2.5 text-[11px] font-medium text-foreground hover:bg-muted/80 transition-colors"
                              >
                                <span>View Report</span>
                                <ChevronRight size={11} />
                              </Link>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {total > 25 && (
                <div className="flex items-center justify-between border-t border-border px-4 py-3 text-xs text-muted-foreground">
                  <span>Showing {reports.length} of {total} reports</span>
                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page <= 1}
                      className="rounded border border-border px-2 py-1 disabled:opacity-40"
                    >
                      Previous
                    </button>
                    <span className="px-2 font-medium text-foreground">{page}</span>
                    <button
                      type="button"
                      onClick={() => setPage((p) => p + 1)}
                      disabled={page * 25 >= total}
                      className="rounded border border-border px-2 py-1 disabled:opacity-40"
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

// Subcomponent: Detail Report Viewer
function ResearchDetailViewer({
  researchId,
  onBack,
}: {
  researchId: string;
  onBack: () => void;
}) {
  const query = useRadarRead<GrowthResearch>(`/growth/research/${researchId}`);
  const mutation = useRadarMutation();
  const research = query.data;

  if (query.error) {
    return <ErrorState message={query.error.message} retry={() => void query.refetch()} />;
  }
  if (!research) {
    return <LoadingSkeleton />;
  }

  const isSaved = Boolean(research.saved_at);
  const out = research.output || {};
  const findings = out.findings || [];
  const themes = out.themes || [];
  const isCompleted = research.status === "COMPLETED";

  function downloadExport(format: "md" | "csv" | "json") {
    window.open(`/api/intent-radar/growth/research/${researchId}/export/${format}`, "_blank");
  }

  return (
    <div className="w-full min-w-0 space-y-6 pb-20">
      {/* Back button & Action Toolbar */}
      <div className="flex items-center justify-between gap-3 border-b border-border pb-3">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
        >
          <ArrowLeft size={13} />
          <span>Back to Research Reports</span>
        </button>

        <div className="flex items-center gap-2">
          {/* Export Options */}
          {research.export_available&&researchId&&<RadarExport selection={{dataset:'growth',parent:researchId}}/>}
          {research.export_available && (
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => downloadExport("md")}
                className="inline-flex h-8 items-center gap-1 rounded-lg border border-border bg-card px-2.5 text-xs font-medium text-foreground hover:bg-muted transition-colors cursor-pointer"
                title="Export as Markdown"
              >
                <Download size={12} />
                <span>Markdown</span>
              </button>
              <button
                type="button"
                onClick={() => downloadExport("json")}
                className="inline-flex h-8 items-center gap-1 rounded-lg border border-border bg-card px-2.5 text-xs font-medium text-foreground hover:bg-muted transition-colors cursor-pointer"
                title="Export as JSON"
              >
                <Download size={12} />
                <span>JSON</span>
              </button>
            </div>
          )}

          {/* Bookmark / Save */}
          <button
            type="button"
            onClick={() =>
              mutation.mutate({
                path: `/growth/research/${research.id}`,
                method: "PATCH",
                body: {
                  revision: research.revision,
                  saved: !isSaved,
                },
              })
            }
            className={`inline-flex h-8 items-center gap-1.5 rounded-lg border px-3 text-xs font-medium transition-colors cursor-pointer ${
              isSaved
                ? "border-primary/40 text-primary bg-primary/5"
                : "border-border hover:bg-muted text-foreground"
            }`}
          >
            <Bookmark size={13} className={isSaved ? "fill-primary" : ""} />
            <span>{isSaved ? "Saved" : "Save Report"}</span>
          </button>
        </div>
      </div>

      {/* Report Header Card */}
      <div className="rounded-2xl border border-border bg-card p-6 space-y-3.5 shadow-xs">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded bg-primary/10 px-2 py-0.5 text-xs font-bold text-primary">
            {research.kind}
          </span>
          <span className="rounded bg-muted px-2 py-0.5 text-xs font-medium text-foreground">
            {research.status}
          </span>
          <span className="text-xs text-muted-foreground ml-auto">
            Generated {new Date(research.created_at).toLocaleString()}
          </span>
        </div>

        <h1 className="text-xl font-bold tracking-tight text-foreground">{research.title}</h1>
        {research.question && (
          <p className="text-xs text-muted-foreground leading-relaxed">{research.question}</p>
        )}
      </div>

      {/* Executive Summary Card */}
      {out.executive_summary && (
        <div className="rounded-2xl border border-border bg-card p-6 space-y-3 shadow-xs">
          <div className="flex items-center gap-2 text-primary font-semibold text-xs uppercase tracking-wider">
            <Sparkles size={14} />
            <span>Executive Summary</span>
          </div>
          <p className="text-xs text-foreground leading-relaxed whitespace-pre-line">
            {out.executive_summary}
          </p>
        </div>
      )}

      {/* Structured Key Findings with Direct Citations */}
      {findings.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-sm font-bold text-foreground">Key Evidence-Backed Findings</h2>
          <div className="space-y-4">
            {findings.map((f, idx) => (
              <div
                key={f.section || idx}
                className="rounded-xl border border-border bg-card p-5 space-y-3 shadow-xs"
              >
                <h3 className="text-xs font-bold text-foreground">{f.section}</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">{f.interpretation}</p>

                {f.citations && f.citations.length > 0 && (
                  <div className="space-y-2 pt-2 border-t border-border/60">
                    <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider block">
                      Supporting Citations ({f.citations.length})
                    </span>
                    <div className="space-y-2">
                      {f.citations.map((c, cIdx) => (
                        <blockquote
                          key={c.signal_id || cIdx}
                          className="border-l-2 border-primary/50 pl-3 text-[11px] text-foreground italic leading-relaxed bg-muted/20 py-1.5 pr-2 rounded-r"
                        >
                          &ldquo;{c.quote}&rdquo;
                        </blockquote>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Themes Output (if present) */}
      {themes.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-sm font-bold text-foreground">Identified Themes</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {themes.map((t, idx) => (
              <div
                key={t.name || idx}
                className="rounded-xl border border-border bg-card p-4 space-y-2 shadow-xs"
              >
                <h3 className="text-xs font-bold text-foreground">{t.name}</h3>
                <p className="text-[11px] text-muted-foreground line-clamp-3 leading-relaxed">
                  {t.description}
                </p>
                <div className="pt-2 flex items-center justify-between text-[11px]">
                  <span className="text-primary font-medium">{t.citations?.length || 0} citations</span>
                  <Link
                    href={`/intent-radar/monitors/new?prompt=${encodeURIComponent(
                      `Monitor customer discussions about ${t.name}: ${t.description}`
                    )}`}
                    className="text-foreground hover:text-primary font-medium inline-flex items-center gap-0.5"
                  >
                    <span>Create Monitor</span>
                    <ChevronRight size={11} />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Limitations / Governance Notice */}
      {out.limitations && out.limitations.length > 0 && (
        <div className="rounded-xl border border-border/80 bg-muted/20 p-4 text-xs space-y-2 text-muted-foreground">
          <span className="font-semibold text-foreground block">Data Limitations & Governance</span>
          <ul className="list-disc list-inside space-y-1 text-[11px]">
            {out.limitations.map((lim, lIdx) => (
              <li key={lIdx}>{lim}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
