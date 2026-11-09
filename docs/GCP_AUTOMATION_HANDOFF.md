# Production handoff

Mac authentication is verified for project `querryside`, region `asia-south1`. The existing API/worker service accounts and Secret Manager references remain in use; no service-account keys were created.

The final incremental release is deployed on schema 9. Controlled acceptance and current readiness are documented in `AUTOMATION_IMPLEMENTATION_REPORT.md`. Exact live image/revision/scheduler state is in `AUTOMATION_DEPLOYMENT_STATE.json`.

All three activation flags remain false. Database scan/email controls are paused. Acquisition/outreach schedules are paused; five-minute inbox sync is enabled. Activation is owner-only. See `FINAL_ACTIVATION_CHECKLIST.md` for exact configuration, resume and emergency-stop commands.

For future Mac reauthentication only:

```sh
gcloud auth login
gcloud config set project querryside
gcloud config set run/region asia-south1
gcloud auth application-default login
gcloud auth application-default set-quota-project querryside
```

Do not create service-account JSON keys, paste tokens into chat, rerun schema migrations, or overwrite existing Gmail/Hostinger secrets to activate automation.
