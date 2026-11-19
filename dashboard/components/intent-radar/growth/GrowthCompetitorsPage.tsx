"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  Users,
  Plus,
  Search,
  ExternalLink,
  Archive,
  RefreshCw,
  Sparkles,
  Building2,
  Globe,
  Tag,
  AlertCircle,
  X,
  Radio,
  SlidersHorizontal,
} from "lucide-react";
import { useRadarRead, useRadarMutation, useRadarCapabilities } from "../provider";
import { LoadingSkeleton, ErrorState, EmptyState, Badge } from "../ui";
import { SearchInput } from "@/components/ui/search-input";
import type { GrowthCompetitor } from "@/lib/growth";

interface GrowthCompetitorsPageProps {
  onNavigateTab?: (tabId: string) => void;
  onFilterEvidence?: (competitorId: string) => void;
}

export function GrowthCompetitorsPage({ onNavigateTab, onFilterEvidence }: GrowthCompetitorsPageProps) {
  const [search, setSearch] = useState("");
  const [showAddModal, setShowAddModal] = useState(false);
  const [name, setName] = useState("");
  const [aliases, setAliases] = useState("");
  const [context, setContext] = useState("");
  const [formError, setFormError] = useState("");

  const query = useRadarRead<{ items: GrowthCompetitor[] }>("/growth/competitors");
  const mutation = useRadarMutation();
  const capabilities = useRadarCapabilities();

  const competitors = (query.data?.items || []).filter((c) => !c.archived_at);

  const filteredCompetitors = competitors.filter(
    (c) =>
      c.name.toLowerCase().includes(search.toLowerCase()) ||
      c.context?.toLowerCase().includes(search.toLowerCase()) ||
      c.aliases.some((a) => a.toLowerCase().includes(search.toLowerCase()))
  );

  async function handleCreateCompetitor(e: React.FormEvent) {
    e.preventDefault();
    setFormError("");
    if (!name.trim()) {
      setFormError("Please enter a competitor or product name.");
      return;
    }

    try {
      await mutation.mutateAsync({
        path: "/growth/competitors",
        method: "POST",
        body: {
          name: name.trim(),
          aliases: aliases
            .split(",")
            .map((a) => a.trim())
            .filter(Boolean),
          context: context.trim(),
          request_id: crypto.randomUUID(),
        },
      });
      setName("");
      setAliases("");
      setContext("");
      setShowAddModal(false);
      void query.refetch();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to save competitor.");
    }
  }

  return (
    <div className="w-full min-w-0 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold tracking-tight text-foreground">Competitor Intelligence</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Track mentions, customer dissatisfaction, and buyer alternatives for key competitors in your market.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setShowAddModal(true)}
            className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-primary px-3 text-xs font-semibold text-primary-foreground hover:bg-primary/90 transition-colors shadow-xs cursor-pointer"
          >
            <Plus size={13} />
            <span>Add Competitor</span>
          </button>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-2.5 rounded-xl border border-border bg-card p-2.5">
        <div className="flex flex-wrap items-center gap-2 flex-1 min-w-[260px]">
          <SearchInput
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onClear={() => setSearch("")}
            placeholder="Search tracked competitors or aliases…"
            wrapperClassName="flex-1 min-w-[220px]"
          />
        </div>
      </div>

      {/* Add Competitor Modal / Dialog */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-2xl border border-border bg-card p-5 space-y-4 shadow-2xl animate-in fade-in-50">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <Building2 size={16} className="text-primary" />
                <h3 className="text-sm font-semibold text-foreground">Track a Competitor</h3>
              </div>
              <button
                type="button"
                onClick={() => setShowAddModal(false)}
                className="text-muted-foreground hover:text-foreground p-1"
              >
                <X size={15} />
              </button>
            </div>

            <p className="text-xs text-muted-foreground">
              Add known product names and aliases to identify buyer comparisons and alternatives in public discussions.
            </p>

            {formError && (
              <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-2.5 text-xs text-destructive flex items-center gap-2">
                <AlertCircle size={14} />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleCreateCompetitor} className="space-y-3.5 text-xs">
              <div className="space-y-1">
                <label className="font-medium text-foreground block">
                  Product or Competitor Name <span className="text-destructive">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Acme CRM, Pipeflow, DataHub"
                  className="w-full h-8 rounded-lg border border-border bg-background px-2.5 text-xs text-foreground focus:border-primary focus:outline-none"
                />
              </div>

              <div className="space-y-1">
                <label className="font-medium text-foreground block">
                  Known Aliases & Variations <span className="text-muted-foreground font-normal">(comma-separated)</span>
                </label>
                <input
                  type="text"
                  value={aliases}
                  onChange={(e) => setAliases(e.target.value)}
                  placeholder="e.g. acme, acme.io, acmecrm"
                  className="w-full h-8 rounded-lg border border-border bg-background px-2.5 text-xs text-foreground focus:border-primary focus:outline-none"
                />
              </div>

              <div className="space-y-1">
                <label className="font-medium text-foreground block">
                  Disambiguation & Context Notes <span className="text-muted-foreground font-normal">(optional)</span>
                </label>
                <textarea
                  value={context}
                  onChange={(e) => setContext(e.target.value)}
                  placeholder="e.g. Focus on customer complaints about enterprise pricing and slow sync times."
                  rows={2}
                  className="w-full rounded-lg border border-border bg-background p-2 text-xs text-foreground focus:border-primary focus:outline-none resize-y"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="h-8 rounded-lg border border-border px-3 text-xs font-medium text-muted-foreground hover:bg-muted"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={mutation.isPending}
                  className="h-8 rounded-lg bg-primary px-3 text-xs font-semibold text-primary-foreground hover:bg-primary/90 shadow-xs"
                >
                  {mutation.isPending ? "Saving…" : "Save Competitor"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Competitors Listing */}
      {query.error ? (
        <ErrorState message={query.error.message} retry={() => void query.refetch()} />
      ) : query.isLoading ? (
        <LoadingSkeleton />
      ) : filteredCompetitors.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-border bg-card/50 p-12 text-center space-y-3">
          <Building2 className="mx-auto h-8 w-8 text-muted-foreground/60" />
          <h3 className="text-sm font-semibold text-foreground">No tracked competitors yet</h3>
          <p className="text-xs text-muted-foreground max-w-md mx-auto">
            {search
              ? "No competitors match your search. Try different terms or add a new competitor."
              : "Track competitor products and aliases to identify when buyers complain about them or search for alternatives."}
          </p>
          <button
            type="button"
            onClick={() => setShowAddModal(true)}
            className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-primary px-3 text-xs font-medium text-primary-foreground hover:bg-primary/90 transition-colors shadow-xs"
          >
            <Plus size={12} />
            <span>Add First Competitor</span>
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredCompetitors.map((comp) => (
            <div
              key={comp.id}
              className="rounded-xl border border-border bg-card p-4 space-y-3 shadow-xs hover:border-primary/40 transition-colors flex flex-col justify-between"
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/10 text-primary font-bold text-xs shrink-0">
                      {comp.name.charAt(0).toUpperCase()}
                    </div>
                    <h3 className="text-xs font-bold text-foreground truncate">{comp.name}</h3>
                  </div>

                  <button
                    type="button"
                    onClick={() =>
                      mutation.mutate(
                        {
                          path: `/growth/competitors/${comp.id}`,
                          method: "PUT",
                          body: {
                            name: comp.name,
                            aliases: comp.aliases,
                            context: comp.context,
                            revision: comp.revision,
                            archived: true,
                          },
                        },
                        {
                          onSuccess: () => void query.refetch(),
                        }
                      )
                    }
                    className="text-muted-foreground hover:text-destructive p-1 transition-colors"
                    title="Archive competitor"
                  >
                    <Archive size={13} />
                  </button>
                </div>

                {comp.context && (
                  <p className="text-[11px] text-muted-foreground line-clamp-2 leading-relaxed">
                    {comp.context}
                  </p>
                )}

                {comp.aliases.length > 0 && (
                  <div className="flex flex-wrap gap-1 pt-0.5">
                    {comp.aliases.map((alias) => (
                      <span
                        key={alias}
                        className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground font-mono"
                      >
                        {alias}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              <div className="pt-2 border-t border-border/60 flex items-center justify-between text-xs">
                <Link
                  href={`/intent-radar/growth?competitor=${comp.id}`}
                  className="text-primary hover:underline font-medium text-[11px] inline-flex items-center gap-1"
                >
                  <span>Filter Evidence</span>
                  <ExternalLink size={10} />
                </Link>

                <Link
                  href={`/intent-radar/monitors/new?prompt=${encodeURIComponent(
                    `Monitor customer discussions about ${comp.name} alternatives and dissatisfaction`
                  )}`}
                  className="inline-flex h-6 items-center gap-1 rounded border border-border bg-background px-2 text-[10px] font-medium text-foreground hover:border-primary/40 transition-colors"
                >
                  <Plus size={10} />
                  <span>Monitor</span>
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
