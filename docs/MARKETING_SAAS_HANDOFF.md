# Future marketing → SaaS handoff

Prepared contract, not activated marketing checkout. Do not change the existing
marketing design, payment buttons, DNS or independent deployment in this release.

A future approved marketing link is:
`https://app.planebyte.com/start?product=intent-radar&plan=starter`

Allowed product: `intent-radar`. Allowed plans: `starter`, `growth`, `scale`,
`enterprise`. Unknown values are rejected. No amount, entitlement, workspace ID,
external callback or return URL is authoritative or accepted. Starter/Growth/Scale
currently refer to internal Test Mode catalog fixtures, not approved sale prices.

The SaaS validates enums and stores a two-hour HMAC-protected, HttpOnly, SameSite=Lax,
host-only cookie (Secure in production). Login uses existing real Google OAuth;
account admission/allowlist is unchanged. The selected plan is reviewed after
sign-in, workspace selection and resumable onboarding. No subscription is created
automatically. The backend revalidates the configured catalog, owner permission,
approved test workspace and price mapping before a consequential action.

New users remain subject to the existing closed registration gates. Existing
workspace ownership is resolved server-side; a plan intent cannot join another
workspace. Cancelled/abandoned checkout preserves the same local subscription;
retrying never creates another mandate. Closing a checkout does not cancel an
already authorized recurring subscription; cancellation uses the billing API.

Both Next.js applications keep their own package manifest/build and deployment.
`dashboard/` is Vercel. `planebyte-website/planebyte/` is independent owner code;
no marketing deployment or payment integration is authorized here.
