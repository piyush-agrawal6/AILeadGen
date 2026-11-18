"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowUpRight, Bookmark, CheckCheck, Loader2 } from "lucide-react";
import type { IntentSignal } from "@/lib/intent-radar";
import { useRadarCapabilities, useRadarMutation } from "./provider";
import { Badge, EmptyState } from "./ui";
import { ProviderLogo } from "./provider-logo";

export function SignalScore({ score }: { score: number }) {
  return (
    <span
      className="inline-flex items-baseline gap-0.5 rounded-lg border border-border/80 bg-muted/35 px-2 py-0.5 text-xs font-semibold text-muted-foreground tabular-nums"
      aria-label={`Interpreted relevance ${score} out of 100`}
    >
      {score}
      <small className="text-[10px] font-normal">/100</small>
    </span>
  );
}

function isMarketIntelligenceSignal(signal: IntentSignal): boolean {
  const kind = signal.evidence?.provenance?.content_kind || "";
  return (
    signal.category === "Market / technology intelligence" ||
    kind === "release_announcement" ||
    kind === "research_paper"
  );
}

export function SignalCard({
  signal: s,
  onOpen,
}: {
  signal: IntentSignal;
  onOpen?: (id: string) => void;
}) {
  const mutation = useRadarMutation();
  const access = useRadarCapabilities();
  const [savingId, setSavingId] = useState(false);

  const disabled = !access.data?.can_write || mutation.isPending || savingId;
  const kind = s.evidence?.provenance?.content_kind;
  const attr = s.evidence?.provenance?.attribution;
  const author = typeof attr === "string" ? attr : attr?.author;
  const marketIntel = isMarketIntelligenceSignal(s);

  async function toggleSave() {
    if (disabled) return;
    setSavingId(true);
    try {
      await mutation.mutateAsync({
        path: "/saved/" + s.id,
        method: s.saved ? "DELETE" : "POST",
      });
    } finally {
      setSavingId(false);
    }
  }

  return (
    <article className="flex flex-col justify-between rounded-2xl border border-border bg-card p-5 space-y-3 hover:border-primary/35 transition-colors">
      <div className="space-y-2.5">
        <div className="flex items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-2 min-w-0">
            <span className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
              <ProviderLogo provider={s.source} size={18} />
              <span className="truncate">{s.source}</span>
            </span>
            <span
              className={
                "rounded-full border px-2 py-0.5 text-[10px] font-semibold " +
                (marketIntel
                  ? "border-violet-500/25 bg-violet-500/10 text-violet-700 dark:text-violet-300"
                  : "border-blue-500/25 bg-blue-500/10 text-blue-700 dark:text-blue-300")
              }
            >
              {marketIntel ? "Market / Tech Intelligence" : "Buyer-Intent Discussion"}
            </span>
            {kind && !marketIntel && <Badge>{kind.replaceAll("_", " ")}</Badge>}
          </div>

          <SignalScore score={s.score} />
        </div>

        <h3 className="text-sm font-semibold leading-snug text-foreground">
          <Link
            href={`/intent-radar/signals/${s.id}`}
            onClick={
              onOpen
                ? (e) => {
                    e.preventDefault();
                    onOpen(s.id);
                  }
                : undefined
            }
            className="hover:text-primary transition-colors"
          >
            {s.title}
          </Link>
        </h3>

        <p className="text-xs text-muted-foreground leading-relaxed line-clamp-3">
          {s.excerpt || "This discussion has no body excerpt. Review the original title and linked source."}
        </p>

        <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
          <Badge>{s.category}</Badge>
          <Badge>{s.status}</Badge>
          {s.evidence.matched_keywords?.slice(0, 4).map((k) => (
            <span
              key={k}
              className="rounded-md bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground"
            >
              {k}
            </span>
          ))}
        </div>

        <p className="text-[11px] text-muted-foreground">
          Published {new Date(s.observed_at).toLocaleDateString()}
          {author ? ` · ${author}` : ""}
        </p>
      </div>

      <footer className="flex flex-wrap items-center justify-between gap-2 border-t border-border/70 pt-3">
        <div className="flex items-center gap-2">
          <button
            type="button"
            disabled={disabled}
            onClick={() => void toggleSave()}
            className={
              "inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-medium transition-colors cursor-pointer disabled:opacity-50 " +
              (s.saved
                ? "border-primary/40 bg-primary/10 text-primary"
                : "border-border bg-card text-foreground hover:border-primary/45")
            }
          >
            {savingId ? (
              <Loader2 size={13} className="animate-spin" />
            ) : (
              <Bookmark size={13} fill={s.saved ? "currentColor" : "none"} />
            )}
            {s.saved ? "Saved" : "Save signal"}
          </button>

          {s.status === "New" && (
            <button
              type="button"
              disabled={disabled}
              aria-label={"Mark reviewed: " + s.title}
              onClick={() =>
                mutation.mutate({
                  path: "/signals/" + s.id,
                  method: "PATCH",
                  body: { revision: s.revision, status: "Reviewed" },
                })
              }
              className="inline-flex items-center justify-center rounded-lg border border-border bg-card p-1.5 text-muted-foreground hover:text-foreground cursor-pointer disabled:opacity-50"
            >
              <CheckCheck size={15} />
            </button>
          )}

          {s.source_url?.startsWith("http") && (
            <a
              className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-primary"
              href={s.source_url}
              target="_blank"
              rel="noopener noreferrer"
            >
              Source <ArrowUpRight size={13} />
            </a>
          )}
        </div>

        <Link
          className="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline"
          onClick={
            onOpen
              ? (e) => {
                  e.preventDefault();
                  onOpen(s.id);
                }
              : undefined
          }
          href={`/intent-radar/signals/${s.id}`}
        >
          View details <ArrowUpRight size={13} />
        </Link>
      </footer>
    </article>
  );
}

export function SignalTable({
  signals,
  selected = [],
  onSelect,
  onOpen,
}: {
  signals: IntentSignal[];
  selected?: string[];
  onSelect?: (ids: string[]) => void;
  onOpen?: (id: string) => void;
}) {
  if (!signals.length) return <EmptyState />;
  return (
    <>
      <div className="ir-table-wrap">
        <table>
          <thead>
            <tr>
              {onSelect && (
                <th>
                  <input
                    type="checkbox"
                    aria-label="Select displayed signals"
                    checked={signals.every((s) => selected.includes(s.id))}
                    onChange={(e) => onSelect(e.target.checked ? signals.map((s) => s.id) : [])}
                  />
                </th>
              )}
              <th>Signal</th>
              <th>Source</th>
              <th>Intent</th>
              <th>Relevance</th>
              <th>Observed</th>
              <th>Review status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {signals.map((s) => (
              <tr key={s.id}>
                {onSelect && (
                  <td className="ir-select-cell">
                    <input
                      type="checkbox"
                      aria-label={`Select ${s.title}`}
                      checked={selected.includes(s.id)}
                      onChange={(e) =>
                        onSelect(
                          e.target.checked
                            ? [...selected, s.id]
                            : selected.filter((id) => id !== s.id)
                        )
                      }
                    />
                  </td>
                )}
                <td>
                  <Link
                    href={`/intent-radar/signals/${s.id}`}
                    onClick={
                      onOpen
                        ? (e) => {
                            e.preventDefault();
                            onOpen(s.id);
                          }
                        : undefined
                    }
                  >
                    {s.title}
                  </Link>
                  <small>{s.evidence.matched_keywords?.join(" · ")}</small>
                </td>
                <td>
                  <span className="ir-source">
                    <ProviderLogo provider={s.source} size={20} />
                    {s.source}
                  </span>
                </td>
                <td>
                  <Badge>{s.category}</Badge>
                </td>
                <td>
                  <SignalScore score={s.score} />
                </td>
                <td>{s.observed_at.slice(0, 10)}</td>
                <td>
                  <Badge>{s.status}</Badge>
                </td>
                <td>
                  <Link
                    className="ir-link"
                    onClick={
                      onOpen
                        ? (e) => {
                            e.preventDefault();
                            onOpen(s.id);
                          }
                        : undefined
                    }
                    href={`/intent-radar/signals/${s.id}`}
                    aria-label={"Review " + s.title}
                  >
                    Review <ArrowUpRight size={14} />
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="ir-mobile-cards">
        {signals.map((s) => (
          <div key={s.id}>
            {onSelect && (
              <label className="ir-check">
                <input
                  type="checkbox"
                  checked={selected.includes(s.id)}
                  onChange={(e) =>
                    onSelect(
                      e.target.checked
                        ? [...selected, s.id]
                        : selected.filter((id) => id !== s.id)
                    )
                  }
                />
                Select signal
              </label>
            )}
            <SignalCard signal={s} onOpen={onOpen} />
          </div>
        ))}
      </div>
    </>
  );
}
