"use client";

import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, Mail, Save, Send, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { request } from "@/lib/intelligence";
import { Button } from "@/components/ui/button";

type UserNotifPrefs = {
  in_app_enabled: boolean;
  email_enabled: boolean;
  email_cadence: "immediate" | "daily_digest" | "weekly_digest" | "off";
  high_priority_only: boolean;
  timezone: string;
  quiet_hours_enabled: boolean;
  quiet_hours_start: string;
  quiet_hours_end: string;
  categories: Record<string, boolean>;
  email_delivery_available?: boolean;
};

const CATEGORY_META = [
  { key: "discovery", label: "Discovery runs", desc: "Search completed, failed, or limit reached.", mandatory: false },
  { key: "signals", label: "Intent signals", desc: "High-relevance signals and completed AI analyses.", mandatory: false },
  { key: "opportunities", label: "Opportunities", desc: "New opportunities created or stage updates.", mandatory: false },
  { key: "monitoring", label: "Scheduled monitoring", desc: "Monitor findings, failures, or source health issues.", mandatory: false },
  { key: "ai", label: "AI assistant actions", desc: "Long-running AI tasks completed or requiring confirmation.", mandatory: false },
  { key: "billing", label: "Billing & subscriptions", desc: "Trial expiration, payment confirmations, and renewals (mandatory).", mandatory: true },
  { key: "security", label: "Security & team access", desc: "Invitations, API keys, and role changes (mandatory).", mandatory: true },
];

export function NotificationPreferencesPanel() {
  const client = useQueryClient();
  const query = useQuery({
    queryKey: ["notification-preferences"],
    queryFn: () => request<UserNotifPrefs>("/organization/notifications/preferences"),
    retry: false,
  });

  const [form, setForm] = useState<UserNotifPrefs | null>(null);
  const [saving, setSaving] = useState(false);
  const [sendingTest, setSendingTest] = useState(false);

  useEffect(() => {
    if (query.data && !form) {
      setForm(query.data);
    }
  }, [query.data, form]);

  async function save() {
    if (!form) return;
    setSaving(true);
    try {
      const { email_delivery_available: _ignore, ...payload } = form;
      const updated = await request<UserNotifPrefs>("/organization/notifications/preferences", {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      setForm(updated);
      await client.invalidateQueries({ queryKey: ["notification-preferences"] });
      toast.success("Notification preferences saved.");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not save notification preferences.");
    } finally {
      setSaving(false);
    }
  }

  async function sendTestEmail() {
    setSendingTest(true);
    try {
      const res = await request<{ recipient: string }>("/organization/notifications/test-email", {
        method: "POST",
      });
      toast.success(`Test notification email queued for ${res.recipient}.`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not send test notification email.");
    } finally {
      setSendingTest(false);
    }
  }

  if (query.isPending || !form) {
    return <div className="h-36 rounded-xl border border-border bg-muted/30 animate-pulse" />;
  }

  return (
    <div className="rounded-xl border border-border bg-card p-6 space-y-5 text-xs">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-border pb-4">
        <div>
          <h3 className="text-base font-semibold text-foreground flex items-center gap-2">
            <Mail size={16} className="text-primary" /> Personal Delivery &amp; Email Preferences
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            Control how you receive in-app notifications and branded PlaneByte transactional emails.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {form.email_delivery_available && (
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={sendingTest}
              onClick={() => void sendTestEmail()}
              className="gap-1.5"
            >
              <Send size={13} />
              {sendingTest ? "Sending…" : "Send test email"}
            </Button>
          )}
          <Button type="button" size="sm" disabled={saving} onClick={() => void save()} className="gap-1.5">
            <Save size={13} />
            {saving ? "Saving…" : "Save delivery preferences"}
          </Button>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="flex items-start gap-2.5 rounded-xl border border-border bg-muted/15 p-3.5 cursor-pointer">
          <input
            type="checkbox"
            checked={form.in_app_enabled}
            onChange={(e) => setForm({ ...form, in_app_enabled: e.target.checked })}
            className="accent-primary mt-0.5"
          />
          <div>
            <span className="font-semibold text-foreground flex items-center gap-1.5">
              <Bell size={13} /> In-app notifications
            </span>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              Show real-time unread count and alerts in the top navbar notification bell.
            </p>
          </div>
        </label>

        <label className="flex items-start gap-2.5 rounded-xl border border-border bg-muted/15 p-3.5 cursor-pointer">
          <input
            type="checkbox"
            checked={form.email_enabled}
            onChange={(e) => setForm({ ...form, email_enabled: e.target.checked })}
            className="accent-primary mt-0.5"
          />
          <div>
            <span className="font-semibold text-foreground flex items-center gap-1.5">
              <Mail size={13} /> Email notifications{" "}
              <span className="rounded-full bg-muted px-1.5 py-0.5 text-[10px] font-medium">
                {form.email_delivery_available ? "Resend active" : "Unavailable"}
              </span>
            </span>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              Deliver optional product alerts to your verified workspace email.
            </p>
          </div>
        </label>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="space-y-1">
          <label htmlFor="notif-cadence" className="block font-medium text-foreground">
            Email cadence
          </label>
          <select
            id="notif-cadence"
            value={form.email_cadence}
            onChange={(e) =>
              setForm({
                ...form,
                email_cadence: e.target.value as UserNotifPrefs["email_cadence"],
              })
            }
            className="w-full rounded-lg border border-border bg-card px-2.5 py-2 text-xs text-foreground"
          >
            <option value="immediate">Immediate alerts</option>
            <option value="daily_digest">Daily digest</option>
            <option value="weekly_digest">Weekly digest</option>
            <option value="off">Off (mandatory security/billing only)</option>
          </select>
        </div>

        <div className="space-y-1">
          <label htmlFor="notif-tz" className="block font-medium text-foreground">
            Timezone
          </label>
          <input
            id="notif-tz"
            value={form.timezone}
            onChange={(e) => setForm({ ...form, timezone: e.target.value })}
            placeholder="UTC or America/New_York"
            className="w-full rounded-lg border border-border bg-card px-2.5 py-2 text-xs text-foreground"
          />
        </div>

        <div className="flex items-end pb-1">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={form.high_priority_only}
              onChange={(e) => setForm({ ...form, high_priority_only: e.target.checked })}
              className="accent-primary"
            />
            <span className="font-medium text-foreground">High-priority alerts only</span>
          </label>
        </div>
      </div>

      {/* Quiet Hours */}
      <div className="rounded-xl border border-border bg-muted/15 p-3.5 space-y-2.5">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={form.quiet_hours_enabled}
            onChange={(e) => setForm({ ...form, quiet_hours_enabled: e.target.checked })}
            className="accent-primary"
          />
          <span className="font-semibold text-foreground">Enable quiet hours for optional emails</span>
        </label>
        {form.quiet_hours_enabled && (
          <div className="flex flex-wrap items-center gap-3 pl-6">
            <label className="flex items-center gap-1.5">
              <span className="text-muted-foreground">From</span>
              <input
                type="time"
                value={form.quiet_hours_start}
                onChange={(e) => setForm({ ...form, quiet_hours_start: e.target.value })}
                className="rounded-lg border border-border bg-card px-2 py-1 text-xs"
              />
            </label>
            <label className="flex items-center gap-1.5">
              <span className="text-muted-foreground">To</span>
              <input
                type="time"
                value={form.quiet_hours_end}
                onChange={(e) => setForm({ ...form, quiet_hours_end: e.target.value })}
                className="rounded-lg border border-border bg-card px-2 py-1 text-xs"
              />
            </label>
          </div>
        )}
      </div>

      {/* Category Toggles */}
      <div className="space-y-2">
        <p className="font-semibold text-foreground">Notification Categories</p>
        <div className="grid gap-2 sm:grid-cols-2">
          {CATEGORY_META.map((cat) => (
            <label
              key={cat.key}
              className="flex items-start gap-2.5 rounded-xl border border-border/80 bg-card px-3 py-2.5 cursor-pointer"
            >
              <input
                type="checkbox"
                disabled={cat.mandatory}
                checked={cat.mandatory ? true : Boolean(form.categories[cat.key] ?? true)}
                onChange={(e) =>
                  setForm({
                    ...form,
                    categories: { ...form.categories, [cat.key]: e.target.checked },
                  })
                }
                className="accent-primary mt-0.5"
              />
              <div className="min-w-0">
                <span className="font-medium text-foreground flex items-center gap-1">
                  {cat.label}
                  {cat.mandatory && <ShieldCheck size={11} className="text-primary" />}
                </span>
                <p className="text-[11px] text-muted-foreground leading-snug">{cat.desc}</p>
              </div>
            </label>
          ))}
        </div>
      </div>
    </div>
  );
}
