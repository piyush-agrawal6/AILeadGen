export function sameOrigin(origin: string | null, host: string | null, production: boolean): boolean {
  if (!origin || !host) return false;
  try { const url=new URL(origin); return url.host.toLowerCase()===host.toLowerCase() && (url.protocol==="https:" || (!production&&url.protocol==="http:")); } catch { return false; }
}
