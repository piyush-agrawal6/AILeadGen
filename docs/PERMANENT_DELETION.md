# Permanent deletion

Campaign, scan and lead pages provide a scoped deletion preview and require the exact confirmation DELETE. Requests use existing signed, allowlisted API authentication and browser-origin protection.

Campaign deletion removes its runs, observations, findings, scores, reports and private artifacts. Scan deletion removes one run and its associated data. A shared canonical lead, notes and workflow survive when another observation remains outside the selected campaign/scan. Lead deletion removes all observations of that canonical lead across campaigns, notes, identities, report versions and private artifacts. Related CSV/XLSX exports and run events are removed because they can contain the deleted lead; unrelated leads remain.

Running/queued scans, live worker leases and pending report jobs block deletion. The dialog can request cancellation, then waits for completion before allowing removal. Advisory worker/report locks close dispatch races. A preview token detects changed data. A durable deletion batch is committed before private object cleanup; storage failures retain the database rows and a retryable intent. Pending targets reject workflow/report changes and scan resumes. Retrying finishes idempotent object removal and database cleanup. Successful deletion removes the batch itself.

Private artifact keys are validated and object deletions are bucket-scoped. Legacy filesystem cleanup resolves paths inside their expected root. Production verification must create disposable QA entities and must never delete an existing user record merely to test the feature.
