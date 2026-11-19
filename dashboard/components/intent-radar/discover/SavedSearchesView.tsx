"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Copy,
  Edit3,
  FolderOpen,
  MoreHorizontal,
  Play,
  Plus,
  Radio,
  Search,
  Trash2,
} from "lucide-react";
import type { IntentJob, IntentPage, SavedSearch } from "@/lib/intent-radar";
import { Button } from "@/components/ui/button";
import { SearchInput } from "@/components/ui/search-input";
import { Menu, MenuContent } from "@/components/ui/menu";
import { EmptyState, ErrorState, LoadingSkeleton, PageHeading } from "../ui";
import { ProviderLogo } from "../provider-logo";
import { useRadarCapabilities, useRadarMutation, useRadarRead } from "../provider";
import { MonitorWizard } from "../monitors";
import { DiscoverNav } from "./DiscoverNav";
import { DISCOVERY_PRELOAD_KEY } from "./DiscoveryCopilotPanel";

function formatRelativeTime(iso: string): string {
  const d = new Date(iso);
  const diff = Date.now() - d.getTime();
  if (Number.isNaN(diff)) return iso;
  if (diff < 60_000) return "just now";
  const mins = Math.floor(diff / 60_000);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days === 1) return "yesterday";
  if (days < 30) return `${days}d ago`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months}mo ago`;
  return `${Math.floor(months / 12)}y ago`;
}

export function SavedSearchesView({
  embeddedInMain = false,
}: {
  embeddedInMain?: boolean;
} = {}) {
  let router: any = null;
  try {
    router = useRouter();
  } catch {
    // ignore
  }
  const access = useRadarCapabilities();
  const mutation = useRadarMutation();
  const icps = useRadarRead<{ items: { id: string; name: string }[] }>("/icps");

  const [search, setSearch] = useState("");
  const [editing, setEditing] = useState<SavedSearch | null>(null);
  const [editName, setEditName] = useState("");
  const [editDesc, setEditDesc] = useState("");
  const [monitorTarget, setMonitorTarget] = useState<SavedSearch | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<SavedSearch | null>(null);
  const [runningId, setRunningId] = useState<string | null>(null);
  const [notice, setNotice] = useState("");
  const [err, setErr] = useState("");

  const params = new URLSearchParams({
    page: "1",
    page_size: "50",
    ...(search.trim() ? { search: search.trim() } : {}),
  });
  const query = useRadarRead<IntentPage<SavedSearch>>(`/saved-searches?${params.toString()}`);

  function openInBuilder(item: SavedSearch) {
    try {
      sessionStorage.setItem(
        DISCOVERY_PRELOAD_KEY,
        JSON.stringify({
          configuration: item.configuration,
          original_prompt: item.original_prompt,
          title: item.name,
        })
      );
    } catch {
      // ignore storage errors
    }
    router.push(`/intent-radar/discover/new?saved_search_id=${item.id}`);
  }

  async function runDirectly(item: SavedSearch) {
    setErr("");
    setNotice("");
    setRunningId(item.id);
    try {
      const res = (await mutation.mutateAsync({
        path: "/discover",
        body: {
          configuration: item.configuration,
          request_id: crypto.randomUUID(),
          title: item.name,
          original_prompt: item.original_prompt || item.name,
          search_mode: "saved",
        },
      })) as IntentJob;

      const targetRunId = res.discovery_id || res.id;
      router.push(`/intent-radar/discover/runs/${targetRunId}`);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not execute saved search.");
      setRunningId(null);
    }
  }

  async function saveEdit() {
    if (!editing || !editName.trim()) return;
    setErr("");
    setNotice("");
    try {
      await mutation.mutateAsync({
        path: `/saved-searches/${editing.id}`,
        method: "PUT",
        body: {
          name: editName.trim(),
          description: editDesc.trim(),
          original_prompt: editing.original_prompt,
          configuration: editing.configuration,
          revision: editing.revision,
        },
      });
      setEditing(null);
      setNotice(`Saved search "${editName.trim()}" updated.`);
      void query.refetch();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not update saved search.");
    }
  }

  async function duplicateItem(item: SavedSearch) {
    setErr("");
    setNotice("");
    try {
      await mutation.mutateAsync({
        path: `/saved-searches/${item.id}/duplicate`,
        method: "POST",
      });
      setNotice(`Duplicated "${item.name}".`);
      void query.refetch();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not duplicate saved search.");
    }
  }

  async function deleteItem(item: SavedSearch) {
    setErr("");
    setNotice("");
    try {
      await mutation.mutateAsync({
        path: `/saved-searches/${item.id}`,
        method: "DELETE",
      });
      setNotice(`Deleted "${item.name}".`);
      void query.refetch();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not delete saved search.");
    }
  }

  const items = query.data?.items || [];

  return (
    <div className={embeddedInMain ? "space-y-4" : "ir-page space-y-5"}>
      {!embeddedInMain && (
        <>
          <PageHeading
            title="Saved Searches"
            description="Reusable discovery search configurations. Saved searches do not run automatically — convert any search into a Monitor when you want recurring checks."
          />
          <DiscoverNav activeTab="saved" />
        </>
      )}

      {/* Header controls: search and new discovery */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-border bg-card p-3.5 text-xs">
        <SearchInput
          aria-label="Filter saved searches"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onClear={() => setSearch("")}
          placeholder="Filter saved searches by name, prompt, or keyword…"
          wrapperClassName="flex-1 min-w-[200px] max-w-md"
        />
        {!embeddedInMain && (
          <Button size="sm" onClick={() => router.push("/intent-radar/discover/new")} className="gap-1.5">
            <Plus size={14} /> New Discovery
          </Button>
        )}
      </div>

      {notice && (
        <div role="status" className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-2.5 text-xs text-emerald-700 dark:text-emerald-300">
          {notice}
        </div>
      )}
      {err && <ErrorState message={err} />}

      {query.error ? (
        <ErrorState message={query.error.message} retry={() => void query.refetch()} />
      ) : !query.data ? (
        <LoadingSkeleton />
      ) : items.length === 0 ? (
        <EmptyState
          title="No saved searches yet"
          description="Save frequently used search configurations to run them anytime or convert them into recurring monitors."
          action={
            <Button size="sm" onClick={() => router.push("/intent-radar/discover")} className="gap-1.5 mt-2">
              <Plus size={14} /> Create your first search
            </Button>
          }
        />
      ) : (
        <div className="rounded-2xl border border-border bg-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left text-xs">
              <thead>
                <tr className="border-b border-border bg-muted/30 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  <th scope="col" className="py-3 pl-4 pr-3 min-w-[240px]">Saved Search</th>
                  <th scope="col" className="py-3 px-3 whitespace-nowrap">Sources</th>
                  <th scope="col" className="py-3 px-3 min-w-[200px]">Keywords</th>
                  <th scope="col" className="py-3 px-3 whitespace-nowrap">Updated</th>
                  <th scope="col" className="py-3 pl-2 pr-4 whitespace-nowrap text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/70">
                {items.map((item) => {
                  const sources = item.configuration.sources ?? ["hacker_news"];
                  const keywords = item.configuration.keywords || [];
                  const displayedKeywords = keywords.slice(0, 3);
                  const extraKeywordsCount = keywords.length - displayedKeywords.length;
                  const icpName = item.configuration.icp_id
                    ? icps.data?.items.find((i) => i.id === item.configuration.icp_id)?.name
                    : null;
                  const isRunning = runningId === item.id;

                  return (
                    <tr
                      key={item.id}
                      className="group hover:bg-muted/30 transition-colors"
                    >
                      {/* Saved Search: Name, description/objective, ICP tag */}
                      <td className="py-3.5 pl-4 pr-3 max-w-sm">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-[13px] text-foreground group-hover:text-primary transition-colors">
                            {item.name}
                          </span>
                          {icpName && (
                            <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-semibold text-primary shrink-0">
                              {icpName}
                            </span>
                          )}
                        </div>
                        {item.description ? (
                          <p className="mt-0.5 text-[11px] text-muted-foreground line-clamp-1">
                            {item.description}
                          </p>
                        ) : item.original_prompt ? (
                          <p className="mt-0.5 text-[11px] text-muted-foreground line-clamp-1 italic">
                            “{item.original_prompt}”
                          </p>
                        ) : null}
                      </td>

                      {/* Sources: Small source icons */}
                      <td className="py-3.5 px-3 whitespace-nowrap">
                        <div className="flex items-center gap-1.5" title={sources.join(", ")}>
                          {sources.map((src) => (
                            <div
                              key={src}
                              className="flex h-6 w-6 items-center justify-center rounded-md border border-border bg-background"
                              title={src.replace("_", " ")}
                            >
                              <ProviderLogo provider={src} size={13} />
                            </div>
                          ))}
                        </div>
                      </td>

                      {/* Keywords: First 3 pills + N more */}
                      <td className="py-3.5 px-3">
                        <div className="flex flex-wrap items-center gap-1">
                          {displayedKeywords.map((kw) => (
                            <span
                              key={kw}
                              className="rounded-md bg-primary/10 px-2 py-0.5 text-[11px] font-medium text-primary"
                            >
                              {kw}
                            </span>
                          ))}
                          {extraKeywordsCount > 0 && (
                            <span
                              className="rounded-md bg-muted px-1.5 py-0.5 text-[10px] font-semibold text-muted-foreground"
                              title={keywords.slice(3).join(", ")}
                            >
                              +{extraKeywordsCount} more
                            </span>
                          )}
                          {keywords.length === 0 && (
                            <span className="text-[11px] text-muted-foreground italic">No keywords</span>
                          )}
                        </div>
                      </td>

                      {/* Updated: Relative timestamp */}
                      <td className="py-3.5 px-3 whitespace-nowrap text-muted-foreground text-[11px]" title={new Date(item.updated_at).toLocaleString()}>
                        {formatRelativeTime(item.updated_at)}
                      </td>

                      {/* Actions: Open in Builder, Run Search, 3-dot dropdown */}
                      <td className="py-3.5 pl-2 pr-4 whitespace-nowrap text-right">
                        <div className="inline-flex items-center justify-end gap-1.5">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => openInBuilder(item)}
                            className="h-7 px-2.5 text-xs gap-1"
                            title="Open in Search Builder"
                          >
                            <FolderOpen size={12} />
                            <span className="hidden sm:inline">Open in Builder</span>
                          </Button>

                          <Button
                            size="sm"
                            disabled={isRunning || mutation.isPending}
                            onClick={() => void runDirectly(item)}
                            className="h-7 px-2.5 text-xs gap-1"
                            title="Execute this search immediately"
                          >
                            <Play size={11} fill="currentColor" />
                            <span className="hidden sm:inline">{isRunning ? "Starting…" : "Run Search"}</span>
                          </Button>

                          {access.data?.can_write && (
                            <Menu.Root>
                              <Menu.Trigger asChild>
                                <button
                                  type="button"
                                  aria-label={`Actions for ${item.name}`}
                                  className="inline-flex h-7 w-7 items-center justify-center rounded-md border border-border bg-card text-muted-foreground hover:bg-muted hover:text-foreground transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
                                >
                                  <MoreHorizontal size={14} />
                                </button>
                              </Menu.Trigger>
                              <MenuContent align="end" className="w-48 p-1 text-xs">
                                <Menu.Item
                                  onSelect={() => {
                                    setEditing(item);
                                    setEditName(item.name);
                                    setEditDesc(item.description || "");
                                  }}
                                  className="flex items-center gap-2 rounded-md px-2.5 py-1.5 cursor-pointer hover:bg-muted outline-none"
                                >
                                  <Edit3 size={13} />
                                  <span>Rename</span>
                                </Menu.Item>
                                <Menu.Item
                                  disabled={mutation.isPending}
                                  onSelect={() => void duplicateItem(item)}
                                  className="flex items-center gap-2 rounded-md px-2.5 py-1.5 cursor-pointer hover:bg-muted outline-none"
                                >
                                  <Copy size={13} />
                                  <span>Duplicate</span>
                                </Menu.Item>
                                <Menu.Item
                                  onSelect={() => router.push(`/intent-radar/monitors/new?saved_search_id=${item.id}`)}
                                  className="flex items-center gap-2 rounded-md px-2.5 py-1.5 cursor-pointer hover:bg-muted outline-none"
                                >
                                  <Radio size={13} />
                                  <span>Convert to Monitor</span>
                                </Menu.Item>
                                <Menu.Separator className="my-1 h-px bg-border" />
                                <Menu.Item
                                  onSelect={() => setDeleteTarget(item)}
                                  className="flex items-center gap-2 rounded-md px-2.5 py-1.5 cursor-pointer text-destructive hover:bg-destructive/10 outline-none"
                                >
                                  <Trash2 size={13} />
                                  <span>Delete</span>
                                </Menu.Item>
                              </MenuContent>
                            </Menu.Root>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Rename Modal */}
      {editing && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-4 backdrop-blur-[1px]"
          role="dialog"
          aria-modal="true"
          aria-label="Rename saved search"
          onClick={() => setEditing(null)}
        >
          <div
            className="w-full max-w-md rounded-2xl border border-border bg-card p-5 shadow-2xl space-y-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div>
              <h3 className="text-sm font-semibold text-foreground">Rename Saved Search</h3>
              <p className="text-xs text-muted-foreground mt-0.5">
                Update the display name and notes for this saved configuration.
              </p>
            </div>
            <div className="space-y-3">
              <div>
                <label className="text-xs font-medium text-foreground block mb-1">Search Name</label>
                <input
                  value={editName}
                  maxLength={120}
                  onChange={(e) => setEditName(e.target.value)}
                  className="w-full rounded-lg border border-border bg-background px-3 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  autoFocus
                />
              </div>
              <div>
                <label className="text-xs font-medium text-foreground block mb-1">Description / Notes (optional)</label>
                <textarea
                  rows={2}
                  value={editDesc}
                  maxLength={400}
                  onChange={(e) => setEditDesc(e.target.value)}
                  placeholder="Notes about when to run this search…"
                  className="w-full rounded-lg border border-border bg-background px-3 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-1">
              <Button size="sm" variant="outline" onClick={() => setEditing(null)}>
                Cancel
              </Button>
              <Button
                size="sm"
                disabled={!editName.trim() || mutation.isPending}
                onClick={() => void saveEdit()}
              >
                Save Changes
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Convert to Monitor Wizard */}
      {monitorTarget && (
        <MonitorWizard
          open={Boolean(monitorTarget)}
          configuration={monitorTarget.configuration}
          onClose={() => setMonitorTarget(null)}
        />
      )}

      {/* Delete Confirmation Modal */}
      {deleteTarget && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-4 backdrop-blur-[1px]"
          role="dialog"
          aria-modal="true"
          aria-label="Delete saved search"
          onClick={() => setDeleteTarget(null)}
        >
          <div
            className="w-full max-w-md rounded-2xl border border-border bg-card p-5 shadow-2xl space-y-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div>
              <h3 className="text-sm font-semibold text-foreground">Delete Saved Search?</h3>
              <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                “{deleteTarget.name}” will be permanently removed from Saved Searches. Past discovery runs and signals are unaffected.
              </p>
            </div>
            <div className="flex justify-end gap-2">
              <Button size="sm" variant="outline" onClick={() => setDeleteTarget(null)}>
                Cancel
              </Button>
              <Button
                size="sm"
                variant="destructive"
                disabled={mutation.isPending}
                onClick={() => {
                  const target = deleteTarget;
                  setDeleteTarget(null);
                  void deleteItem(target);
                }}
              >
                Delete Search
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
