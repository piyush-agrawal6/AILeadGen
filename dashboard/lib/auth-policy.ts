import emailPolicy from './work-email-policy.json';
const blockedDomains = new Set([...emailPolicy.personal_domains, ...emailPolicy.disposable_domains]);
export const workEmailMessage = 'Please use your company email address. Personal email providers are not supported.';
export function isWorkEmail(value: string): boolean {
  const normalized = value.trim().toLowerCase();
  if (normalized.length > 254 || !/^[^\s@<>]+@[a-z0-9.-]+\.[a-z]{2,63}$/.test(normalized)) return false;
  const domain = normalized.split('@')[1];
  return ![...blockedDomains].some(blocked => domain === blocked || domain.endsWith(`.${blocked}`));
}
export function googleAccountAllowed(profile: { email?: string | null; email_verified?: unknown } | undefined, allowlist: readonly string[]): boolean {
  return profile?.email_verified === true && typeof profile.email === "string" && isWorkEmail(profile.email) && allowlist.includes(profile.email.trim().toLowerCase());
}

export function isPublicBrandAsset(pathname:string):boolean {
  return ['/logo.png','/brand/mark.svg','/brand/heysow-mark.svg','/brand/pb-mark.png','/favicon.ico','/pb-logo.ico','/apple-touch-icon.png','/site.webmanifest','/fonts/planebyte-sans-regular.woff2','/fonts/planebyte-sans-medium.woff2','/fonts/planebyte-sans-bold.woff2'].includes(pathname);
}
