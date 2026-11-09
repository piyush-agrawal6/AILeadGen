// Only the versioned machine API uses bearer credentials instead of browser cookies.
export function isDeveloperApiPath(pathname:string){return pathname.startsWith('/api/v1/')}
