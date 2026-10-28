import { googleAccountAllowed,isPublicBrandAsset } from "@/lib/auth-policy";
import { describe,expect,it } from "vitest";
describe("Google access policy", () => {
  it("accepts an explicitly verified allowlisted account", () => expect(googleAccountAllowed({ email: "Founder@Example.com", email_verified: true }, ["founder@example.com"])).toBe(true));
  it.each([false, undefined, "true", 1])("rejects an unverified claim %s", value => expect(googleAccountAllowed({ email: "founder@example.com", email_verified: value }, ["founder@example.com"])).toBe(false));
  it("denies accounts outside the list", () => expect(googleAccountAllowed({ email: "stranger@example.com", email_verified: true }, ["founder@example.com"])).toBe(false));
  it("fails closed with missing configuration", () => expect(googleAccountAllowed({ email: "founder@example.com", email_verified: true }, [])).toBe(false));
});
describe('Public branding assets',()=>{
 it.each(['/logo.png','/fonts/planebyte-sans-regular.woff2','/fonts/planebyte-sans-medium.woff2','/fonts/planebyte-sans-bold.woff2'])('allows the exact public asset %s',path=>expect(isPublicBrandAsset(path)).toBe(true));
 it.each(['/api/leads','/api/client-reports','/logo.png/private','/fonts/private.woff2','/fonts/../api/leads','/leads'])('keeps private routes protected: %s',path=>expect(isPublicBrandAsset(path)).toBe(false));
});
