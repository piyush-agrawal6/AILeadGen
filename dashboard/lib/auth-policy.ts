export function googleAccountAllowed(profile: { email?: string | null; email_verified?: unknown } | undefined, allowlist: readonly string[]): boolean {
  return profile?.email_verified === true && typeof profile.email === "string" && allowlist.includes(profile.email.trim().toLowerCase());
}

export function isPublicBrandAsset(pathname:string):boolean {
  return ['/logo.png','/fonts/planebyte-sans-regular.woff2','/fonts/planebyte-sans-medium.woff2','/fonts/planebyte-sans-bold.woff2'].includes(pathname);
}
