# Optional Gmail integration

Gmail is disabled and is not required for Phase 4 acceptance. The current Gmail provider is an explicit unavailable adapter behind the same sending/synchronization contract. It does not implement a pretend OAuth connection or claim production verification. Hostinger handles the current workflow.

A future implementation must use OAuth rather than a Gmail password, with a dedicated Gmail client and a protected callback. Existing AUTH_GOOGLE_ID/AUTH_GOOGLE_SECRET remain Google sign-in credentials and are not repurposed or rotated. GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET and GMAIL_REDIRECT_URI are reserved for the optional adapter; server-side token encryption/Secret Manager and disconnect/revoke behavior must be implemented before enabling it.

For a future least-privilege review, consider gmail.send for reviewed outbound messages and gmail.readonly only if required to read referenced reply bodies. Do not request gmail.modify or full-mailbox permissions without a concrete feature need. Document consent, test users, callback URI, accessed data and credential storage when that adapter is actually implemented. No scopes are currently requested by this disabled feature.
