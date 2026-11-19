"use client";

import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bell,
  CheckCircle2,
  Clock,
  Lock,
  Mail,
  Send,
  AlertTriangle,
} from "lucide-react";
import { request } from "@/lib/intelligence";
import { useWorkspace } from "@/components/workspaces/use-workspace";
import { Button } from "@/components/ui/button";

export interface NotificationPrefs {
  in_app_enabled: boolean;
  email_enabled: boolean;
  email_cadence: "immediate" | "daily_digest" | "weekly_digest" | "off";
  high_priority_only: boolean;
  timezone: string;
  quiet_hours_enabled: boolean;
  quiet_hours_start: string;
  quiet_hours_end: string;
  categories: Record<string, boolean>;
  email_categories?: Record<string, boolean>;
  email_delivery_available: boolean;
  can_send_test_email?: boolean;
}

const NOTIFICATION_TYPES = [
  { key: "discovery", label: "Discovery results", description: "Completed runs and newly found discussions", required: false },
  { key: "signals", label: "High-intent signals", description: "Conversations scoring above your alert threshold", required: false },
  { key: "opportunities", label: "New opportunities", description: "Qualified leads and opportunity status updates", required: false },
  { key: "monitoring", label: "Monitoring alerts", description: "Scheduled monitor matches and source issues", required: false },
  { key: "ai", label: "AI agent actions", description: "Completed AI analyses and assistant action results", required: false },
  { key: "billing", label: "Billing & subscription", description: "Invoices, renewals, trials, and payment status", required: true },
  { key: "security", label: "Security & access", description: "Sign-in alerts, role changes, and domain updates", required: true },
] as const;

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

function Toggle({
  checked,
  disabled,
  label,
  onChange,
}: {
  checked: boolean;
  disabled?: boolean;
  label: string;
  onChange: (next: boolean) => void;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer ${
        checked ? "bg-primary" : "bg-muted-foreground/30"
      }`}
    >
      <span
        className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform ${
          checked ? "translate-x-4.5" : "translate-x-0.5"
        }`}
      />
    </button>
  );
}

export function NotificationPreferencesPanel({ activeTab }: { activeTab?: string } = {}) {
  const client = useQueryClient();
  const workspace = useWorkspace();
  const orgId = workspace.data?.active_organization_id || "";

  const prefsQuery = useQuery({
    queryKey: ["notification-preferences", orgId || "default"],
    queryFn: ({ signal }) =>
      request<NotificationPrefs>("/organization/notifications/preferences", { signal }),
    retry: false,
  });

  const [draft, setDraft] = useState<NotificationPrefs | null>(null);
  const [saving, setSaving] = useState(false);
  const [testingEmail, setTestingEmail] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (prefsQuery.data && !draft) {
      setDraft({
        ...prefsQuery.data,
        email_categories: prefsQuery.data.email_categories || { ...prefsQuery.data.categories },
      });
    }
  }, [prefsQuery.data, draft]);

  useEffect(() => {
    setDraft(null);
  }, [orgId]);

  if (prefsQuery.isPending || !draft) {
    return (
      <div className="space-y-3" role="status" aria-label="Loading notification preferences">
        <div className="h-32 rounded-xl border border-border bg-muted/30 animate-pulse" />
        <div className="h-44 rounded-xl border border-border bg-muted/30 animate-pulse" />
      </div>
    );
  }

  if (prefsQuery.isError) {
    return (
      <div role="alert" className="rounded-xl border border-destructive/25 bg-destructive/5 p-4 text-xs text-destructive space-y-2">
        <p>Could not load notification preferences.</p>
        <Button size="sm" variant="outline" onClick={() => void prefsQuery.refetch()}>
          Retry
        </Button>
      </div>
    );
  }

  async function savePreferences() {
    if (!draft || saving) return;
    setSaving(true);
    setNotice("");
    setError("");
    try {
      const updated = await request<NotificationPrefs>("/organization/notifications/preferences", {
        method: "PUT",
        body: JSON.stringify({
          in_app_enabled: draft.in_app_enabled,
          email_enabled: draft.email_enabled,
          email_cadence: draft.email_cadence,
          high_priority_only: draft.high_priority_only,
          timezone: draft.timezone || "UTC",
          quiet_hours_enabled: draft.quiet_hours_enabled,
          quiet_hours_start: draft.quiet_hours_start,
          quiet_hours_end: draft.quiet_hours_end,
          categories: draft.categories,
          email_categories: draft.email_categories || draft.categories,
        }),
      });
      setDraft(updated);
      client.setQueryData(["notification-preferences", orgId], updated);
      setNotice("Personal notification preferences saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save notification preferences.");
    } finally {
      setSaving(false);
    }
  }

  async function sendTestEmail() {
    if (testingEmail) return;
    setTestingEmail(true);
    setNotice("");
    setError("");
    try {
      const res = await request<{
        delivered?: boolean;
        recipient: string;
        provider_message_id?: string | null;
      }>("/organization/notifications/test-email", { method: "POST" });
      if (res.delivered) {
        setNotice(
          `Test email delivered to ${res.recipient}${res.provider_message_id ? ` (ID: ${res.provider_message_id})` : ""}.`
        );
      } else {
        setError("Test email could not be confirmed by the email provider.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not deliver test email.");
    } finally {
      setTestingEmail(false);
    }
  }

  const emailCats = draft.email_categories || draft.categories;
  const tzOptions = COMMON_TIMEZONES.includes(draft.timezone)
    ? COMMON_TIMEZONES
    : [draft.timezone, ...COMMON_TIMEZONES];

  return (
    <div className="space-y-4">
      {notice && (
        <div role="status" className="flex items-center gap-2 rounded-xl border border-emerald-500/25 bg-emerald-500/10 px-3.5 py-2.5 text-xs font-medium text-emerald-700 dark:text-emerald-300">
          <CheckCircle2 size={14} className="shrink-0" />
          <span>{notice}</span>
        </div>
      )}
      {error && (
        <div role="alert" className="flex items-start gap-2 rounded-xl border border-destructive/25 bg-destructive/5 px-3.5 py-2.5 text-xs text-destructive">
          <AlertTriangle size={14} className="shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {/* Section 1: Delivery Channels (Personal) */}
      {activeTab !== "types" && (
        <section className="rounded-xl border border-border bg-card p-4 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Bell size={15} className="text-primary" />
            <h3 className="text-sm font-semibold text-foreground">Delivery Channels</h3>
            <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
              Personal
            </span>
          </div>
          {draft.can_send_test_email && draft.email_delivery_available && (
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={testingEmail}
              onClick={() => void sendTestEmail()}
              className="h-7 px-2.5 text-xs gap-1.5"
            >
              <Send size={12} />
              {testingEmail ? "Sending test…" : "Send Test Email"}
            </Button>
          )}
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <div className="flex items-center justify-between rounded-lg border border-border/70 bg-muted/15 px-3.5 py-2.5">
            <div className="min-w-0 pr-3">
              <p className="text-xs font-semibold text-foreground">In-app notifications</p>
              <p className="text-[11px] text-muted-foreground">Alerts in the notification bell &amp; center</p>
            </div>
            <Toggle
              checked={draft.in_app_enabled}
              label="Enable in-app notifications"
              onChange={(v) => setDraft({ ...draft, in_app_enabled: v })}
            />
          </div>

          <div className="flex items-center justify-between rounded-lg border border-border/70 bg-muted/15 px-3.5 py-2.5">
            <div className="min-w-0 pr-3">
              <div className="flex items-center gap-1.5">
                <Mail size={12} className="text-muted-foreground" />
                <p className="text-xs font-semibold text-foreground">Email notifications</p>
              </div>
              <p className="text-[11px] text-muted-foreground">
                {draft.email_delivery_available
                  ? "Transactional email delivery configured"
                  : "Email delivery unavailable in this environment"}
              </p>
            </div>
            <Toggle
              checked={draft.email_enabled}
              disabled={!draft.email_delivery_available}
              label="Enable email notifications"
              onChange={(v) => setDraft({ ...draft, email_enabled: v })}
            />
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-3 border-t border-border/60 pt-3">
          <label className="space-y-1">
            <span className="text-[11px] font-medium text-muted-foreground">Email cadence</span>
            <select
              value={draft.email_cadence}
              disabled={!draft.email_enabled}
              onChange={(e) =>
                setDraft({
                  ...draft,
                  email_cadence: e.target.value as NotificationPrefs["email_cadence"],
                })
              }
              className="h-8 w-full rounded-lg border border-border bg-background px-2.5 text-xs text-foreground disabled:opacity-50"
            >
              <option value="immediate">Immediate alerts</option>
              <option value="daily_digest">Daily digest</option>
              <option value="weekly_digest">Weekly digest</option>
              <option value="off">Off (mandatory only)</option>
            </select>
          </label>

          <label className="space-y-1">
            <span className="text-[11px] font-medium text-muted-foreground">Timezone</span>
            <select
              value={draft.timezone}
              onChange={(e) => setDraft({ ...draft, timezone: e.target.value })}
              className="h-8 w-full rounded-lg border border-border bg-background px-2.5 text-xs text-foreground"
            >
              {tzOptions.map((tz) => (
                <option key={tz} value={tz}>
                  {tz}
                </option>
              ))}
            </select>
          </label>

          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="inline-flex items-center gap-1 text-[11px] font-medium text-muted-foreground">
                <Clock size={11} /> Quiet hours
              </span>
              <Toggle
                checked={draft.quiet_hours_enabled}
                label="Enable quiet hours"
                onChange={(v) => setDraft({ ...draft, quiet_hours_enabled: v })}
              />
            </div>
            {draft.quiet_hours_enabled ? (
              <div className="flex items-center gap-1.5">
                <input
                  type="time"
                  aria-label="Quiet hours start"
                  value={draft.quiet_hours_start}
                  onChange={(e) => setDraft({ ...draft, quiet_hours_start: e.target.value })}
                  className="h-8 w-full rounded-lg border border-border bg-background px-2 text-xs tabular-nums"
                />
                <span className="text-[11px] text-muted-foreground">to</span>
                <input
                  type="time"
                  aria-label="Quiet hours end"
                  value={draft.quiet_hours_end}
                  onChange={(e) => setDraft({ ...draft, quiet_hours_end: e.target.value })}
                  className="h-8 w-full rounded-lg border border-border bg-background px-2 text-xs tabular-nums"
                />
              </div>
            ) : (
              <p className="text-[11px] text-muted-foreground pt-1.5">
                Optional email alerts pause during quiet hours.
              </p>
            )}
          </div>
        </div>

        <div className="flex items-center justify-between border-t border-border/60 pt-3">
          <div className="flex items-center gap-2.5">
            <Toggle
              checked={draft.high_priority_only}
              label="High-priority email alerts only"
              onChange={(v) => setDraft({ ...draft, high_priority_only: v })}
            />
            <span className="text-xs text-foreground">
              Only email high-priority &amp; urgent alerts
            </span>
          </div>
          {activeTab === "channels" && (
            <Button size="sm" disabled={saving} onClick={() => void savePreferences()} className="h-8 text-xs">
              {saving ? "Saving…" : "Save Personal Preferences"}
            </Button>
          )}
        </div>
      </section>
      )}

      {/* Section 2: Notification Types Table (Personal) */}
      {activeTab !== "channels" && (
        <section className="rounded-xl border border-border bg-card overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-border/70">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-foreground">Notification Types</h3>
            <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
              Personal
            </span>
          </div>
          <span className="text-[11px] text-muted-foreground">
            Security &amp; billing notices stay active
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse" aria-label="Notification types">
            <thead className="bg-muted/35 text-[11px] font-semibold text-muted-foreground border-b border-border/70">
              <tr>
                <th scope="col" className="px-4 py-2">Category</th>
                <th scope="col" className="px-4 py-2 text-center w-24">In-App</th>
                <th scope="col" className="px-4 py-2 text-center w-24">Email</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {NOTIFICATION_TYPES.map((item) => {
                const inAppChecked = item.required ? true : Boolean(draft.categories[item.key] ?? true);
                const emailChecked = item.required ? true : Boolean(emailCats[item.key] ?? true);
                return (
                  <tr key={item.key} className="hover:bg-muted/15">
                    <td className="px-4 py-2.5">
                      <div className="flex items-center gap-1.5 font-medium text-foreground">
                        <span>{item.label}</span>
                        {item.required && (
                          <span className="inline-flex items-center gap-0.5 rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                            <Lock size={9} /> Required
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-muted-foreground">{item.description}</p>
                    </td>
                    <td className="px-4 py-2.5 text-center">
                      <Toggle
                        checked={inAppChecked}
                        disabled={item.required || !draft.in_app_enabled}
                        label={`${item.label} in-app notifications`}
                        onChange={(v) =>
                          setDraft({
                            ...draft,
                            categories: { ...draft.categories, [item.key]: v },
                          })
                        }
                      />
                    </td>
                    <td className="px-4 py-2.5 text-center">
                      <Toggle
                        checked={emailChecked}
                        disabled={item.required || !draft.email_enabled || !draft.email_delivery_available}
                        label={`${item.label} email notifications`}
                        onChange={(v) =>
                          setDraft({
                            ...draft,
                            email_categories: { ...emailCats, [item.key]: v },
                          })
                        }
                      />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="flex items-center justify-end border-t border-border/70 bg-muted/15 px-4 py-3">
          <Button size="sm" disabled={saving} onClick={() => void savePreferences()} className="h-8 text-xs">
            {saving ? "Saving…" : "Save Personal Preferences"}
          </Button>
        </div>
      </section>
      )}
    </div>
  );
}
