# Security model

Production access is restricted to the configured Google account allowlist. The deployed account is `planebyte@gmail.com`, as explicitly requested. Auth.js requires Google's verified email. Sessions expire after eight hours, use secure HTTP-only cookies in production, and every protected route rechecks the current allowlist. There is no public signup or browser-held backend credential.

Next.js signs method, raw path/query, body digest, actor, timestamp and nonce with HMAC-SHA256. FastAPI requires the same allowlisted actor, a 60-second timestamp window, constant-time signature comparison and a unique database-backed nonce. Payloads are limited to 1 MiB. Mutating browser requests must have an acceptable same-origin header. The public health response is deliberately minimal. Production errors omit internal exception details; production API docs are disabled.

The dashboard sends a per-request nonce CSP, disables framing and object embedding, and adds content-type, referrer and permissions policies. Production script policy excludes unsafe-eval. Inline styles remain allowed for the component library. HTML reports escape business-controlled text and download inside a restrictive sandbox policy. CSV/XLSX strings beginning with spreadsheet formula characters are escaped.

Crawlers require HTTP(S), public DNS/IP destinations and verified TLS. Redirects are bounded and each destination is validated. The transport pins the validated destination IP while retaining TLS hostname verification. Lighthouse uses a public-only outbound proxy, including subresources, with Chromium local proxy bypass and QUIC disabled. Robots, body size, depth, page count, concurrency and elapsed time are bounded. No port scanning, authentication attempts, exploit payloads, directory brute forcing or vulnerability exploitation is implemented. Security findings are passive observations, not penetration-test certification.

Production configuration fails closed for missing server secrets, local auth bypasses, non-PostgreSQL storage or missing worker/R2 configuration. Database, R2, signing and Google client secrets never use NEXT_PUBLIC variables. GCP secrets are assigned individually: the API can read its seven secrets; the worker can read database/R2 secrets only. Cloud Build permissions are scoped to its source bucket, private log bucket and Artifact Registry repository. The rejected project-wide logging role was not applied.

R2 credentials should remain bucket scoped. Reachability checks alone do not establish the bucket's public-access policy. Cloud Run's API endpoint is publicly reachable at the network layer, but application routes require signed internal authentication. No service-account JSON keys are created. The API and worker can invoke only the LeadEngine worker job with overrides.

Dependency findings and exceptions are recorded in `PHASE_3_AUDIT.md`. Lockfiles are committed inputs. Auth.js 5 is pinned to the current beta integration documented there; monitor its stable release before upgrading. Never place environment files, downloaded credentials or signed sessions in source control or logs.

Rotate a secret by adding a Secret Manager version, updating Vercel if relevant, and redeploying the API/worker. Removing an account from both server allowlists revokes its next authorized request even if its session has not expired.
# Phase 3.5 client PDFs

Client PDF creation, metadata and downloads use the same allowlisted session and signed BFF authentication as other workspace routes. The renderer uses stored, escaped text and bundled fonts/vector assets; it performs no client-site fetches. Private R2 keys are not returned in the public report DTO. Downloads stream through the authenticated API with `application/pdf`, attachment disposition, `nosniff` and private/no-store caching. PDFs omit internal workflow, notes, assignment and database identifiers; failure details remain in private metadata. Queue capacity shares the existing bounded worker dispatcher, and prior report versions are preserved.

