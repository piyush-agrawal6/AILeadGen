"use client";

import { NotificationPreferencesPanel } from "@/components/notifications/NotificationPreferencesPanel";

export function NotificationsSection({
  activeTab,
}: {
  activeTab: string;
}) {
  return <NotificationPreferencesPanel activeTab={activeTab} />;
}
