/**
 * Centralized action-aware toast resolver for PlaneByte Intent Radar mutations.
 * Replaces generic "Intent Radar updated." notifications with clear, contextual feedback.
 */
export function resolveRadarToast(
  path: string,
  method = "POST",
  response?: unknown,
): string {
  const m = method.toUpperCase();
  const cleanPath = path.split("?")[0];
  const data = (response && typeof response === "object" ? response : {}) as Record<string, unknown>;

  if (cleanPath === "/discover") {
    return "Discovery started — scanning selected sources.";
  }
  if (/^\/discoveries\/[^/]+$/.test(cleanPath)) {
    if (m === "DELETE") return "Discovery run deleted from history.";
    if (m === "PATCH") return "Discovery title updated.";
  }
  if (cleanPath.startsWith("/saved-searches")) {
    if (m === "DELETE") return "Saved search deleted.";
    if (cleanPath.endsWith("/duplicate")) return "Saved search duplicated.";
    if (m === "PUT") return "Saved search updated.";
    return "Search saved to your reusable templates.";
  }
  if (/^\/jobs\/[^/]+\/cancel$/.test(cleanPath)) {
    return "Discovery job canceled.";
  }
  if (/^\/jobs\/[^/]+\/retry$/.test(cleanPath)) {
    return "Discovery job re-queued for retry.";
  }
  if (cleanPath.startsWith("/monitors")) {
    if (cleanPath.endsWith("/schedule")) return "Monitor schedule saved.";
    if (cleanPath.endsWith("/duplicate")) return "Monitor duplicated.";
    if (m === "DELETE") return "Monitor removed.";
    if (m === "PUT") {
      const status = typeof data.status === "string" ? data.status : "";
      if (status === "Paused") return "Monitor paused.";
      if (status === "Active") return "Monitor updated and active.";
      if (status === "Archived") return "Monitor archived.";
      return "Monitor updated.";
    }
    return "Monitor created and ready.";
  }
  if (cleanPath === "/signals/actions") {
    return "";
  }
  if (
    /^\/saved\/[^/]+$/.test(cleanPath) ||
    /^\/signals\/[^/]+\/save$/.test(cleanPath) ||
    /^\/signals\/[^/]+\/bookmark$/.test(cleanPath)
  ) {
    if (m === "DELETE") return "Signal removed from Research Library.";
    if (m === "PUT" || m === "PATCH") return "Bookmark notes and tags updated.";
    return "Signal saved to Research Library.";
  }
  if (/^\/signals\/[^/]+$/.test(cleanPath) && m === "PATCH") {
    const status = typeof data.status === "string" ? data.status : "";
    return status ? `Signal marked as ${status}.` : "Signal review saved.";
  }
  if (/^\/signals\/[^/]+\/review$/.test(cleanPath)) {
    const status = typeof data.status === "string" ? data.status : "";
    return status ? `Signal marked as ${status}.` : "Signal review status saved.";
  }
  if (/^\/signals\/[^/]+\/feedback$/.test(cleanPath)) {
    return "Signal relevance feedback recorded.";
  }
  if (/^\/signals\/[^/]+\/analysis$/.test(cleanPath)) {
    if (!data.interpretation) {
      return "";
    }
    return data.cached ? "Loaded cached AI signal analysis." : "Signal AI analysis completed.";
  }
  if (/^\/signals\/[^/]+\/withdraw$/.test(cleanPath)) {
    return "Source excerpt withdrawn while preserving your notes.";
  }
  if (/^\/signals\/[^/]+\/opportunity$/.test(cleanPath) || cleanPath.startsWith("/opportunities")) {
    if (m === "PUT" || m === "PATCH") return "Opportunity updated.";
    return data.already_existed ? "Linked to existing opportunity." : "Opportunity created and tracked.";
  }
  if (cleanPath.startsWith("/alerts")) {
    return "Alert status updated.";
  }
  if (cleanPath.startsWith("/preferences")) {
    return "Workspace research preferences saved.";
  }
  if (cleanPath.startsWith("/custom-feeds")) {
    if (m === "DELETE") return "Custom feed removed.";
    if (cleanPath.endsWith("/test")) return "Custom feed validation completed.";
    if (m === "PUT" || m === "PATCH") return "Custom feed configuration saved.";
    return "Custom feed added.";
  }
  if (cleanPath.startsWith("/sources/github")) {
    if (cleanPath.endsWith("/disconnect")) return "GitHub integration disconnected.";
    return "GitHub integration settings saved.";
  }
  if (cleanPath.startsWith("/sources/")) {
    return "Source integration updated.";
  }
  if (cleanPath.startsWith("/growth/watchlists")) {
    return m === "DELETE" ? "Watchlist removed." : "Watchlist saved.";
  }
  if (cleanPath.startsWith("/growth/competitors")) {
    return m === "DELETE" ? "Competitor removed." : "Competitor tracking saved.";
  }
  if (cleanPath.startsWith("/growth/research")) {
    return "Growth intelligence report started.";
  }
  if (cleanPath.startsWith("/assistant")) {
    return "AI Assistant conversation updated.";
  }
  return "Changes saved.";
}
