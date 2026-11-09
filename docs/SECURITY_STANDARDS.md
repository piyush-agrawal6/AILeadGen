# Security standards

Preserve verified Google claims, Auth.js state/PKCE handling, secure production cookies, eight-hour session expiration, signed internal requests, replay nonces, request limits, same-origin writes and CSP. Never trust a URL token alone as identity or workspace membership. Unsupported auth states must say so, rather than exposing dummy forms.

Every data operation requires authenticated identity, active membership, resource ownership, permission and module availability. Use parameterized SQL and ownership predicates on conflict updates. Template ownership is checked before writes and atomically in `ON CONFLICT`.

External HTML, model output and email are untrusted data. Preserve existing SSRF, redirect, size, time and concurrency limits. Secrets stay server-only; no `.env` file or OAuth credential is changed by this work. No public signup or release is allowed while tenant-scope regressions remain.

Auth threat model: account confusion is addressed by existing verified-email/access policy; open redirects are avoided with a fixed server redirect; provider errors are mapped to fixed public messages; invitation/reset parameters are not proof of access; public-page proxy markers are overwritten server-side. Live OAuth completion requires an authorized real account and is not claimed by the intercepted test handoff.
