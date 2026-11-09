# Local development and release boundaries

## Authenticated isolated preview

Use Python 3.12 with dependencies installed into the ignored project `.venv`.
From the repository root, run in two terminals:

```sh
.venv/bin/python scripts/local_preview.py backend
.venv/bin/python scripts/local_preview.py frontend
```

`npm run dev` from dashboard uses the same isolated frontend launcher. Start the
backend separately with the command above. It does not fall back to production
when the local backend is unavailable.

The frontend listens at http://localhost:3000 and the API at
http://127.0.0.1:18790. The launcher reads existing root authentication settings
without changing environment files or printing their values. Google sign-in stays
real; a provider callback rejection must be resolved through approved OAuth setup,
never an authentication bypass.

The separate SQLite database and artifacts live under
data/e2e/local-preview, which is ignored by Git. Restarting preserves that local
data. Development migrations affect only that isolated database. The launcher
disables sending, inbox sync, automatic scanning, acquisition providers and the
internal archive. The gated workspace/profile/ICP UI is enabled only in this local
process. Existing production data, settings and credentials are not modified.

If local processes have stopped after a computer/app interruption, rerun these
commands. A successful login-page response does not prove the backend is ready;
also check the local API health endpoint. Do not point the preview at production
to work around a local backend problem.

The frontend launcher preloads dashboard defaults before restoring the exact
inherited root values, including in Next's child server. This prevents
dotenv expansion from changing literal `$` characters in credentials duplicated
in historical dashboard env files. No replacement secret or browser variable is
created. Restart both preview services after authorized root changes. A session
created under the earlier expanded value must sign in again after the correction.
The dedicated preview browser check uses disposable `$`-containing credentials
and the real signed backend path, not APP_ENV=test authentication bypass.

## Verification and known environment issue

Use APP_ENV=test, DATABASE_BACKEND=sqlite and disabled provider/sending flags for
backend tests. Frontend tests/builds use fixture authentication values and isolated
browser databases; the running preview's real credentials are not test fixtures.
Browser servers use separate ports from the owner's localhost preview.

The bundled Python 3.12 runtime currently fails to build locked cryptography
50.0.2 on this Mac. The restored local environment retains its working 48.0.1
package; repository lockfiles were not changed. This exception is recorded for
staging validation and must not be presented as an exact production-environment
certification. Local PostgreSQL integration and restore validation pass; approved staging remains separate.

## Production

No production deployment, secret update, OAuth change, schema migration or live
send is authorized by the local preview commands. Public registration and the
remaining SaaS features are incomplete. Follow HEYSOW_RELEASE_READINESS.md and
the owner-provided staging/approval gates before proposing production changes.
