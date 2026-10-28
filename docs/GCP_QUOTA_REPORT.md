# Cloud Run quota preflight

Inspected 2026-10-25 against the configured project, using the authenticated gcloud account. These are project-specific observations, not generic limits.

| Item | Observed result |
| --- | --- |
| Project | querryside / 248535449008, ACTIVE |
| Region from application environment | asia-south1 |
| Billing | Enabled |
| Cloud Run API | Enabled |
| Artifact Registry / Cloud Build / Secret Manager | Enabled |
| Regional CPU allocation | 20,000 milli-vCPU (20 vCPU) |
| Regional memory allocation | 42,949,672,960 bytes (40 GiB) |
| Job run requests | 30 per minute per region |
| Running executions | 1,000 per project |
| Existing jobs in region | None at initial inspection |
| Initial proposed worker | 1 task, parallelism 1, 1 vCPU, 2 GiB, bounded timeout/retries |
| Actual quota canary | PASSED: leadengine-quota-canary-zk27p |
| Worker image availability | Both builds succeeded; acceptance worker tag 20261026-000239 |

Raw read-only quota response: `gcp-quota-raw.json`. Connectivity checks: `cloud-connectivity.json`.

Command used successfully:

```powershell
gcloud quotas info list --service=run.googleapis.com --project=querryside --format=json
```

The installed CLI does not support `gcloud beta services quota list`. The supported quotas command supplied the observed project limits above. The minimal one-task canary actually scheduled and completed with 1 vCPU, 2 GiB, 60-second timeout and zero retries. The deployed application image is checked separately by the worker canary; the quota canary alone does not establish application correctness.

## Approval history

Automatic approval review rejected creation of `leadengine-worker-sa@querryside.iam.gserviceaccount.com` and deployment/execution of `leadengine-quota-canary` in asia-south1, citing persistent IAM/cloud resources and potential billing/security effects needing explicit approval at that scope. No workaround was attempted. The rejected canary used public `python:3.12-slim`, command `python --version`, one task/parallelism one, 1 vCPU, 2 GiB, 60-second timeout and zero retries. It would not access database credentials or discover businesses.

The user subsequently explicitly approved this deployment scope and the canary passed. A project-wide build logging role was rejected and was not applied. The user then approved a private regional build-log bucket and bucket-scoped object-admin/metadata-read access for the existing build identity. Both final images built successfully with GCS-only logs. No quota failure was observed; Azure fallback is not warranted.

Expanded application-image canary `leadengine-worker-b25gn` completed successfully. It checked temporary PostgreSQL events, private R2 write/read/delete, DuckDB/httpfs, Chromium, Lighthouse, Node, imports/environment and Overture. System Health verifies its image and completed execution before reporting READY. The public Overpass check remained a bounded warning.
