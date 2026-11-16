import "server-only";
export function serverEnv() {
  const production = process.env.APP_ENV === "production" || Boolean(process.env.VERCEL);
  const required = ["AUTH_SECRET", "AUTH_GOOGLE_ID", "AUTH_GOOGLE_SECRET", "ALLOWED_USER_EMAILS", "LEADENGINE_API_URL", "LEADENGINE_API_SIGNING_SECRET"] as const;
  if (production) {
    for (const key of required) if (!process.env[key]?.trim()) throw new Error(`Missing required server configuration: ${key}`);
    for (const key of ["AUTH_SECRET", "LEADENGINE_API_SIGNING_SECRET"]) if ((process.env[key]?.length ?? 0) < 32) throw new Error(`${key} must contain at least 32 characters`);
    if (!process.env.LEADENGINE_API_URL?.startsWith("https://")) throw new Error("Production API requires HTTPS");
    if (process.env.AUTH_DISABLED_LOCAL === "true") throw new Error("Local authentication bypass is forbidden in production");
  }
   return { controlledRegistration:Boolean(process.env.HEYSOW_REGISTRATION_ACCEPTANCE_EMAILS?.trim()), accounts:process.env.HEYSOW_ACCOUNTS_ENABLED==="true", production, apiUrl: process.env.LEADENGINE_API_URL || "http://127.0.0.1:8787", secret: process.env.LEADENGINE_API_SIGNING_SECRET || "", allowed: (process.env.ALLOWED_USER_EMAILS || "").split(",").map(x => x.trim().toLowerCase()).filter(Boolean),publicRegistration:process.env.HEYSOW_PUBLIC_REGISTRATION_ENABLED==="true",invitedRegistration:process.env.HEYSOW_INVITED_REGISTRATION_ENABLED==="true",customerAccess:process.env.HEYSOW_CUSTOMER_ACCESS_ENABLED==="true",termsVersion:process.env.HEYSOW_TERMS_VERSION||"" };
}
