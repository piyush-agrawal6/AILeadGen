"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Copy,
  Edit3,
  FolderOpen,
  Radio,
  Search,
  Trash2,
} from "lucide-react";
import type { IntentPage, SavedSearch } from "@/lib/intent-radar";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState, LoadingSkeleton, PageHeading } from "../ui";
import { useRadarCapabilities, useRadarMutation, useRadarRead } from "../provider";
import { MonitorWizard } from "../monitors";
import { DiscoverNav } from "./DiscoverNav";
import { DISCOVERY_PRELOAD_KEY } from "./DiscoveryCopilotPanel";

export function SavedSearchesView() {
  const router = useRouter();
  const access = useRadarCapabilities();
  const mutation = useRadarMutation();

  const [search, setSearch] = useState("");
  const [editing, setEditing] = useState<SavedSearch | null>(null);
  const [editName, setEditName] = useState("");
  const [editDesc, setEditDesc] = useState("");
  const [monitorTarget, setMonitorTarget] = useState<SavedSearch | null>(null);
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
    router.push("/intent-radar/discover");
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
      setNotice("Saved search updated.");
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

  return (
    <div className="ir-page space-y-5">
      <PageHeading
        title="Saved Searches"
        description="Reusable discovery search configurations. Saved searches do not run automatically — convert any search into a Monitor when you want recurring checks."
      />
      <DiscoverNav activeTab="saved" />

      <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-border bg-card p-3.5 text-xs">
        <div className="relative flex-1 min-w-[200px]">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filter saved searches by name or keyword…"
            className="w-full rounded-lg border border-border bg-background pl-8 pr-3 py-1.5 text-xs text-foreground"
          />
        </div>
        <Button size="sm" onClick={() => router.push("/intent-radar/discover")}>
          New Discovery
        </Button>
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
      ) : query.data.items.length === 0 ? (
        <EmptyState
          title="No saved searches yet"
          description="Review any discovery setup and click Save Search to keep reusable templates separate from recurring Monitors."
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {query.data.items.map((item) => {
            const isEditing = editing?.id === item.id;
            return (
              <article
                key={item.id}
                className="flex flex-col justify-between rounded-2xl border border-border bg-card p-5 space-y-3"
              >
                <div className="space-y-2.5">
                  {isEditing ? (
                    <div className="space-y-2">
                      <input
                        value={editName}
                        maxLength={120}
                        onChange={(e) => setEditName(e.target.value)}
                        className="w-full rounded-lg border border-border bg-background px-3 py-1.5 text-xs font-semibold text-foreground"
                      />
                      <textarea
                        rows={2}
                        value={editDesc}
                        maxLength={400}
                        onChange={(e) => setEditDesc(e.target.value)}
                        placeholder="Optional notes"
                        className="w-full rounded-lg border border-border bg-background px-3 py-1.5 text-xs text-foreground"
                      />
                      <div className="flex items-center gap-2">
                        <Button size="sm" disabled={!editName.trim() || mutation.isPending} onClick={() => void saveEdit()}>
                          Save
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => setEditing(null)}>
                          Cancel
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <>
                      <div className="flex items-start justify-between gap-2">
                        <h3 className="text-sm font-semibold text-foreground">{item.name}</h3>
                        <span className="text-[10px] text-muted-foreground shrink-0">
                          Updated {new Date(item.updated_at).toLocaleDateString()}
                        </span>
                      </div>
                      {item.description && (
                        <p className="text-xs text-muted-foreground line-clamp-2">{item.description}</p>
                      )}
                    </>
                  )}

                  <div className="flex flex-wrap gap-1.5 text-[11px]">
                    {(item.configuration.sources ?? ["hacker_news"]).map((src) => (
                      <span key={src} className="rounded-md bg-muted px-2 py-0.5 font-medium text-foreground">
                        {src.replace("_", " ")}
                      </span>
                    ))}
                    {item.configuration.keywords.slice(0, 6).map((kw) => (
                      <span key={kw} className="rounded-md bg-primary/10 px-2 py-0.5 font-medium text-primary">
                        {kw}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-1.5 border-t border-border/70 pt-3">
                  <Button size="sm" onClick={() => openInBuilder(item)} className="gap-1.5 text-xs">
                    <FolderOpen size={12} /> Open in Builder
                  </Button>
                  {access.data?.can_write && (
                    <>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          setEditing(item);
                          setEditName(item.name);
                          setEditDesc(item.description);
                        }}
                        className="gap-1 text-xs"
                      >
                        <Edit3 size={12} /> Rename
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={mutation.isPending}
                        onClick={() => void duplicateItem(item)}
                        className="gap-1 text-xs"
                      >
                        <Copy size={12} /> Duplicate
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setMonitorTarget(item)}
                        className="gap-1 text-xs"
                      >
                        <Radio size={12} /> Convert to Monitor
                      </Button>
                      <button
                        type="button"
                        onClick={() => void deleteItem(item)}
                        aria-label={`Delete saved search ${item.name}`}
                        className="ml-auto rounded-lg p-1.5 text-muted-foreground hover:bg-destructive/10 hover:text-destructive cursor-pointer"
                      >
                        <Trash2 size={13} />
                      </button>
                    </>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      )}

      {monitorTarget && (
        <MonitorWizard
          open={Boolean(monitorTarget)}
          configuration={monitorTarget.configuration}
          onClose={() => {
            setMonitorTarget(null);
          }}
        />
      )}
    </div>
  );
}
