# PlaneByte P0 customer reset and native authentication — 16 November 2026

Status: production reset committed and independently verified; native authentication frontend/backend deployed with controlled signup. The first real signup exposed a transactional worker-launch failure; its repair is in verification. Public registration remains closed. Owner explicitly gave final authorization for ALL existing customer accounts and customer-owned data in this conversation; no additional reset approval is pending.

## Recovery

- Exact full snapshot: `data/backups/beta-recovery-20261116T115020Z/production.dump`.
- SHA256: `7c1561c5f53784ae1d95917e384564d590277b44a14f80dabda90ee05d97e732`; bytes: 118991786. Access-controlled local file0600, directory0700.
- All201 restored table counts and content fingerprints exactly match the source snapshot. Schema51. PostgreSQL18.6 restore could not understand Neon `pg_attver`; the existing18.7 runtime successfully restored the unchanged dump. The failed attempt is retained as evidence; it is not a recovery pass.
- Recovery target: a NEW isolated local database only. Never overwrite production with a stale recovery dump.

## Scope and specific protected exceptions

The rehearsal removes 747 rows. All customer authentication, memberships, keys, integrations, profiles, ICPs, application research, jobs, customer quotas/trials and customer cache rows are in scope. No database/schema drop, truncation, migration, secret destruction or financial action is performed.

The two original identity records are either deleted or retired. One original user row and one original organization row are needed as foreign-key parents of retained payment history. They are converted to inaccessible ledger references: no customer account, credential, session, membership, product grant or admission remains; the organization is ARCHIVED and the user has an undeliverable retired address and RETIRED provider. These are protected referential records, not usable customer accounts. Original ledger IDs remain traceable. Payment, security/audit, suppression/opt-out records and system configuration/history are preserved. No active customer workspace survives.

External Google accounts and documents owned outside PlaneByte are not deleted. Application-side customer OAuth connections and capabilities are deleted. Existing read caches are authorized after current membership/account checks and keyed by tenant; deleted memberships cannot read cached data. Preserved infrastructure credentials are unchanged.

## Exact production reset manifest

| Table | Before | Delete | Retain | Classification |
|---|---:|---:|---:|---|
| `access_period_reservations` | 0 | 0 | 0 | CUSTOMER_RESET |
| `access_period_usage` | 0 | 0 | 0 | CUSTOMER_RESET |
| `access_periods` | 0 | 0 | 0 | CUSTOMER_RESET |
| `account_admissions` | 0 | 0 | 0 | CUSTOMER_RESET |
| `account_link_tickets` | 0 | 0 | 0 | CUSTOMER_RESET |
| `account_login_tickets` | 0 | 0 | 0 | CUSTOMER_RESET |
| `account_privacy_requests` | 0 | 0 | 0 | PROTECTED |
| `account_rate_limits` | 2 | 2 | 0 | CUSTOMER_RESET |
| `account_recovery_requests` | 0 | 0 | 0 | CUSTOMER_RESET |
| `account_recovery_tokens` | 0 | 0 | 0 | CUSTOMER_RESET |
| `account_roles` | 0 | 0 | 0 | CUSTOMER_RESET |
| `account_security_events` | 0 | 0 | 0 | PROTECTED |
| `account_terms_acceptances` | 0 | 0 | 0 | PROTECTED |
| `account_verifications` | 0 | 0 | 0 | CUSTOMER_RESET |
| `acquisition_ai_cache` | 4 | 4 | 0 | CUSTOMER_RESET |
| `acquisition_batches` | 5 | 5 | 0 | CUSTOMER_RESET |
| `acquisition_events` | 46 | 46 | 0 | CUSTOMER_RESET |
| `acquisition_google_connections` | 1 | 1 | 0 | CUSTOMER_RESET |
| `acquisition_issues` | 43 | 43 | 0 | CUSTOMER_RESET |
| `acquisition_jobs` | 1 | 1 | 0 | CUSTOMER_RESET |
| `acquisition_oauth_states` | 1 | 1 | 0 | CUSTOMER_RESET |
| `acquisition_preferences` | 1 | 1 | 0 | CUSTOMER_RESET |
| `acquisition_provider_health` | 3 | 3 | 0 | CUSTOMER_RESET |
| `acquisition_requests` | 56 | 56 | 0 | CUSTOMER_RESET |
| `activities` | 22 | 22 | 0 | CUSTOMER_RESET |
| `ai_request_usage` | 26 | 26 | 0 | CUSTOMER_RESET |
| `analysis_cache` | 0 | 0 | 0 | CUSTOMER_RESET |
| `analysis_operations` | 0 | 0 | 0 | CUSTOMER_RESET |
| `artifact_objects` | 0 | 0 | 0 | CUSTOMER_RESET |
| `audit_log` | 128 | 0 | 128 | PROTECTED |
| `automation_controls` | 1 | 1 | 0 | CUSTOMER_RESET |
| `automation_email_queue` | 0 | 0 | 0 | CUSTOMER_RESET |
| `automation_runs` | 0 | 0 | 0 | CUSTOMER_RESET |
| `automation_scans` | 0 | 0 | 0 | CUSTOMER_RESET |
| `automation_schedule_runs` | 0 | 0 | 0 | CUSTOMER_RESET |
| `automation_schedules` | 0 | 0 | 0 | CUSTOMER_RESET |
| `billing_action_windows` | 2 | 2 | 0 | CUSTOMER_RESET |
| `billing_customers` | 1 | 0 | 1 | PROTECTED |
| `billing_payments` | 2 | 0 | 2 | PROTECTED |
| `billing_plan_mappings` | 3 | 0 | 3 | SYSTEM |
| `billing_reservations` | 0 | 0 | 0 | CUSTOMER_RESET |
| `billing_subscriptions` | 1 | 0 | 1 | PROTECTED |
| `billing_usage` | 0 | 0 | 0 | CUSTOMER_RESET |
| `billing_webhook_events` | 4 | 0 | 4 | PROTECTED |
| `billing_workspace_slots` | 1 | 1 | 0 | CUSTOMER_RESET |
| `business_identities` | 28 | 28 | 0 | CUSTOMER_RESET |
| `business_intelligence` | 0 | 0 | 0 | CUSTOMER_RESET |
| `businesses` | 11 | 11 | 0 | CUSTOMER_RESET |
| `campaign_business_snapshots` | 0 | 0 | 0 | CUSTOMER_RESET |
| `campaign_settings_snapshots` | 1 | 1 | 0 | CUSTOMER_RESET |
| `client_reports` | 0 | 0 | 0 | CUSTOMER_RESET |
| `commercial_contracts` | 0 | 0 | 0 | PROTECTED |
| `commercial_reservations` | 0 | 0 | 0 | CUSTOMER_RESET |
| `commercial_usage` | 0 | 0 | 0 | CUSTOMER_RESET |
| `commercial_workspace_slots` | 0 | 0 | 0 | CUSTOMER_RESET |
| `company_pdf_assets` | 1 | 1 | 0 | CUSTOMER_RESET |
| `contact_evidence` | 0 | 0 | 0 | CUSTOMER_RESET |
| `contact_list_members` | 0 | 0 | 0 | CUSTOMER_RESET |
| `contact_people` | 0 | 0 | 0 | CUSTOMER_RESET |
| `contact_person_notes` | 0 | 0 | 0 | CUSTOMER_RESET |
| `contacted_recipient_sends` | 44 | 0 | 44 | PROTECTED |
| `contacted_recipients` | 34 | 0 | 34 | PROTECTED |
| `contacted_unsubscribe_tokens` | 43 | 0 | 43 | PROTECTED |
| `contacts` | 7 | 7 | 0 | CUSTOMER_RESET |
| `customer_accounts` | 0 | 0 | 0 | CUSTOMER_RESET |
| `customer_gmail_connections` | 0 | 0 | 0 | CUSTOMER_RESET |
| `customer_gmail_oauth_states` | 0 | 0 | 0 | CUSTOMER_RESET |
| `customer_gmail_sync` | 0 | 0 | 0 | CUSTOMER_RESET |
| `customer_mail_policies` | 0 | 0 | 0 | CUSTOMER_RESET |
| `customer_mail_suppressions` | 0 | 0 | 0 | PROTECTED |
| `customer_mail_tracking_preferences` | 0 | 0 | 0 | CUSTOMER_RESET |
| `customer_sessions` | 0 | 0 | 0 | CUSTOMER_RESET |
| `customer_workspace_access` | 0 | 0 | 0 | CUSTOMER_RESET |
| `deletion_batches` | 0 | 0 | 0 | PROTECTED |
| `deletion_targets` | 0 | 0 | 0 | PROTECTED |
| `developer_action_approvals` | 0 | 0 | 0 | CUSTOMER_RESET |
| `developer_request_windows` | 4 | 4 | 0 | CUSTOMER_RESET |
| `discovery_searches` | 0 | 0 | 0 | CUSTOMER_RESET |
| `duplicate_resolutions` | 0 | 0 | 0 | CUSTOMER_RESET |
| `email_accounts` | 2 | 2 | 0 | CUSTOMER_RESET |
| `email_address_suppressions` | 0 | 0 | 0 | PROTECTED |
| `email_drafts` | 0 | 0 | 0 | CUSTOMER_RESET |
| `email_engagement_events` | 4 | 4 | 0 | CUSTOMER_RESET |
| `email_messages` | 2 | 2 | 0 | CUSTOMER_RESET |
| `email_sync_lock` | 0 | 0 | 0 | CUSTOMER_RESET |
| `email_sync_state` | 2 | 2 | 0 | CUSTOMER_RESET |
| `email_templates` | 22 | 22 | 0 | CUSTOMER_RESET |
| `email_threads` | 2 | 2 | 0 | CUSTOMER_RESET |
| `email_tracking_preferences` | 1 | 1 | 0 | CUSTOMER_RESET |
| `email_tracking_rate_limits` | 2 | 2 | 0 | CUSTOMER_RESET |
| `email_tracking_tokens` | 4 | 4 | 0 | CUSTOMER_RESET |
| `experiment_catalog` | 1 | 0 | 1 | SYSTEM |
| `experiment_events` | 0 | 0 | 0 | CUSTOMER_RESET |
| `experiment_members` | 0 | 0 | 0 | CUSTOMER_RESET |
| `experiment_replies` | 0 | 0 | 0 | CUSTOMER_RESET |
| `experiment_segments` | 0 | 0 | 0 | CUSTOMER_RESET |
| `experiment_sources` | 0 | 0 | 0 | CUSTOMER_RESET |
| `experiments` | 0 | 0 | 0 | CUSTOMER_RESET |
| `findings` | 0 | 0 | 0 | CUSTOMER_RESET |
| `followups` | 0 | 0 | 0 | CUSTOMER_RESET |
| `growth_company_links` | 0 | 0 | 0 | CUSTOMER_RESET |
| `growth_competitors` | 0 | 0 | 0 | CUSTOMER_RESET |
| `growth_notes` | 1 | 1 | 0 | CUSTOMER_RESET |
| `growth_research` | 35 | 35 | 0 | CUSTOMER_RESET |
| `growth_theme_signals` | 40 | 40 | 0 | CUSTOMER_RESET |
| `growth_themes` | 31 | 31 | 0 | CUSTOMER_RESET |
| `growth_watchlists` | 1 | 1 | 0 | CUSTOMER_RESET |
| `icp_ai_proposals` | 2 | 2 | 0 | CUSTOMER_RESET |
| `icp_versions` | 5 | 5 | 0 | CUSTOMER_RESET |
| `ideal_customer_profiles` | 5 | 5 | 0 | CUSTOMER_RESET |
| `identity_resolutions` | 0 | 0 | 0 | CUSTOMER_RESET |
| `integration_oauth_states` | 0 | 0 | 0 | CUSTOMER_RESET |
| `intelligence_job_items` | 27 | 27 | 0 | CUSTOMER_RESET |
| `intelligence_jobs` | 27 | 27 | 0 | CUSTOMER_RESET |
| `intent_alerts` | 20 | 20 | 0 | CUSTOMER_RESET |
| `intent_analyses` | 1 | 1 | 0 | CUSTOMER_RESET |
| `intent_analysis_usage` | 4 | 4 | 0 | CUSTOMER_RESET |
| `intent_collection_cursors` | 3 | 3 | 0 | CUSTOMER_RESET |
| `intent_discoveries` | 16 | 16 | 0 | CUSTOMER_RESET |
| `intent_feedback` | 0 | 0 | 0 | CUSTOMER_RESET |
| `intent_monitor_signals` | 17 | 17 | 0 | CUSTOMER_RESET |
| `intent_monitors` | 3 | 3 | 0 | CUSTOMER_RESET |
| `intent_opportunities` | 1 | 1 | 0 | CUSTOMER_RESET |
| `intent_preferences` | 2 | 2 | 0 | CUSTOMER_RESET |
| `intent_provider_limits` | 0 | 0 | 0 | SYSTEM |
| `intent_rankings` | 1 | 1 | 0 | CUSTOMER_RESET |
| `intent_retention_cursors` | 1 | 1 | 0 | CUSTOMER_RESET |
| `intent_saved_signals` | 1 | 1 | 0 | CUSTOMER_RESET |
| `intent_signals` | 17 | 17 | 0 | CUSTOMER_RESET |
| `intent_source_cache` | 0 | 0 | 0 | CUSTOMER_RESET |
| `intent_source_configs` | 0 | 0 | 0 | CUSTOMER_RESET |
| `intent_source_runs` | 10 | 10 | 0 | CUSTOMER_RESET |
| `intent_source_usage` | 4 | 4 | 0 | CUSTOMER_RESET |
| `intent_worker_health` | 1 | 0 | 1 | SYSTEM |
| `internal_request_nonces` | 4 | 0 | 4 | SYSTEM |
| `launch_trial_claims` | 0 | 0 | 0 | CUSTOMER_RESET |
| `lead_assistant_actions` | 0 | 0 | 0 | CUSTOMER_RESET |
| `lead_assistant_conversations` | 0 | 0 | 0 | CUSTOMER_RESET |
| `lead_assistant_turns` | 0 | 0 | 0 | CUSTOMER_RESET |
| `lead_list_members` | 0 | 0 | 0 | CUSTOMER_RESET |
| `lead_lists` | 0 | 0 | 0 | CUSTOMER_RESET |
| `lead_scores` | 0 | 0 | 0 | CUSTOMER_RESET |
| `lead_source_evidence` | 7 | 7 | 0 | CUSTOMER_RESET |
| `lighthouse_results` | 0 | 0 | 0 | CUSTOMER_RESET |
| `master_lead_state` | 7 | 7 | 0 | CUSTOMER_RESET |
| `opportunity_scores` | 0 | 0 | 0 | CUSTOMER_RESET |
| `organization_acquisition_preferences` | 1 | 1 | 0 | CUSTOMER_RESET |
| `organization_ai_usage` | 10 | 10 | 0 | CUSTOMER_RESET |
| `organization_domains` | 0 | 0 | 0 | CUSTOMER_RESET |
| `organization_integrations` | 0 | 0 | 0 | CUSTOMER_RESET |
| `organization_memberships` | 3 | 3 | 0 | CUSTOMER_RESET |
| `organization_onboarding` | 3 | 3 | 0 | CUSTOMER_RESET |
| `organization_products` | 9 | 9 | 0 | CUSTOMER_RESET |
| `organization_profile_job_events` | 4 | 4 | 0 | CUSTOMER_RESET |
| `organization_profile_jobs` | 10 | 10 | 0 | CUSTOMER_RESET |
| `organization_profile_sources` | 23 | 23 | 0 | CUSTOMER_RESET |
| `organization_profiles` | 3 | 3 | 0 | CUSTOMER_RESET |
| `organization_services` | 22 | 22 | 0 | CUSTOMER_RESET |
| `organization_settings` | 1 | 1 | 0 | CUSTOMER_RESET |
| `organization_setup` | 2 | 2 | 0 | CUSTOMER_RESET |
| `organization_sheet_exports` | 0 | 0 | 0 | CUSTOMER_RESET |
| `organizations` | 3 | 2 | 1 | PROTECTED_FK_REFERENCE |
| `outreach_run_items` | 0 | 0 | 0 | CUSTOMER_RESET |
| `payu_access_callback_events` | 0 | 0 | 0 | PROTECTED |
| `payu_access_orders` | 0 | 0 | 0 | PROTECTED |
| `payu_access_refunds` | 0 | 0 | 0 | PROTECTED |
| `payu_refund_observations` | 0 | 0 | 0 | PROTECTED |
| `pipeline_run_events` | 0 | 0 | 0 | CUSTOMER_RESET |
| `pipeline_runs` | 5 | 5 | 0 | CUSTOMER_RESET |
| `prospect_notes` | 0 | 0 | 0 | CUSTOMER_RESET |
| `prospect_observations` | 7 | 7 | 0 | CUSTOMER_RESET |
| `prospect_sales` | 1 | 1 | 0 | CUSTOMER_RESET |
| `prospects` | 7 | 7 | 0 | CUSTOMER_RESET |
| `provider_rate_limits` | 1 | 0 | 1 | SYSTEM |
| `recovery_checkpoints` | 4 | 0 | 4 | SYSTEM |
| `review_cases` | 0 | 0 | 0 | CUSTOMER_RESET |
| `saved_market_groups` | 0 | 0 | 0 | CUSTOMER_RESET |
| `saved_views` | 1 | 1 | 0 | CUSTOMER_RESET |
| `scan_campaigns` | 1 | 1 | 0 | CUSTOMER_RESET |
| `scan_markets` | 304 | 0 | 304 | SYSTEM |
| `schema_migrations` | 51 | 0 | 51 | SYSTEM |
| `shared_settings` | 1 | 1 | 0 | CUSTOMER_RESET |
| `social_profile_sources` | 0 | 0 | 0 | CUSTOMER_RESET |
| `social_profiles` | 0 | 0 | 0 | CUSTOMER_RESET |
| `transactional_notification_events` | 1 | 1 | 0 | CUSTOMER_RESET |
| `transactional_notifications` | 1 | 1 | 0 | CUSTOMER_RESET |
| `transactional_suppressions` | 0 | 0 | 0 | PROTECTED |
| `user_profiles` | 2 | 2 | 0 | CUSTOMER_RESET |
| `users` | 2 | 1 | 1 | PROTECTED_FK_REFERENCE |
| `webhook_deliveries` | 0 | 0 | 0 | CUSTOMER_RESET |
| `webhook_delivery_attempts` | 0 | 0 | 0 | CUSTOMER_RESET |
| `webhook_endpoints` | 0 | 0 | 0 | CUSTOMER_RESET |
| `website_captures` | 0 | 0 | 0 | CUSTOMER_RESET |
| `website_profiles` | 0 | 0 | 0 | CUSTOMER_RESET |
| `worker_attempts` | 0 | 0 | 0 | CUSTOMER_RESET |
| `worker_health` | 5 | 0 | 5 | SYSTEM |
| `workflow_runs` | 0 | 0 | 0 | CUSTOMER_RESET |
| `workspace_api_keys` | 5 | 5 | 0 | CUSTOMER_RESET |
| `workspace_creation_requests` | 2 | 2 | 0 | CUSTOMER_RESET |
| `workspace_invitations` | 2 | 2 | 0 | CUSTOMER_RESET |
| `workspace_notifications` | 20 | 20 | 0 | CUSTOMER_RESET |

Restricted machine manifest contains the complete303 foreign-key dependencies, deletion order and pre/post content fingerprints: `data/artifacts/verification/final-owner-20261116/reset-production.json`. The separate rehearsal rolled back; production execution then committed747 deletions. A new read-only connection independently verified24 customer/auth/resource tables empty, zero active customer workspaces, all remaining user/workspace references retired, and2 preserved payment rows.


## Live P0 release and exact remaining acceptance

- Backend source9cde7cc; current API `leadengine-api-00159-cuv`,100% traffic; matching workers. Native accounts, current-term enforcement, strict work-email validation and controlled `contact@planebyte.com` signup enabled. Public registration and checkout remainfalse. Compatible closed-admission rollback is154, not the old flag-off149.
- Frontend sourcef4f1708; production deployment `dpl_CTzTkou3fSdyxfs8yA4FfFbdTVQJ` (READY; authoritative alias matched) at https://app.planebyte.com. Email/password login/signup/recovery and approved legal version `planebyte-2026-11-16-v1` are live. Actual guest acceptance passed22 light/dark screenshots, including320px mobile legal/recovery routes. No password or OTP was read.
- The controlled signed legacy-session probe was accepted before deployment (session identity returned; private profile200). After deployment the same legacy claim class returns a null session and private profile401. This is a constructed cryptographic regression probe, not a completed real Google callback.
- Real production password signup with a personal domain returns422; Google admission with personal identity returns403. An unapproved custom work address returns503 while public admission is closed. Native quota/auth isolation and retry tests retain their real protections.
- Initial frozen baseline1161 backend passes, one explicit live-mail skip; frontend193 passes, types/lint/build and isolated browser account journey pass. Public paid launch is not claimed.
- Owner's first genuine new signup was recorded, but its OTP remainedQUEUED with zero provider attempts and an unconfirmed worker launch. No active customer account or trial was created. A later request superseded the first challenge; neither is counted as successful verification.
- Incident repair: launch authentication mail before request completion; retain CPU until an already-claimed launch acknowledges; keep recovery identity lookup in the worker, bound cloud acknowledgement and worker retries, and hand off pending outbox work before a worker exits. This uses existing infrastructure and retains unknown-outcome leases/idempotency. It does not switch to instance-based billing or change hosting plans. The production API uses request-based CPU allocation, under which detached background activity can stall; see [Google Cloud's guidance](https://cloud.google.com/run/docs/tips/general#avoid_background_activities). Actual Resend delivery and the fresh customer journey must be retested after this repair is deployed.
- Mail repair source9cde7cc deployed at API159 with matching workers; build743799cd SUCCESS, API health200, personal password/Google admission403, all runtime settings preserved, no migration or repeated reset. Frozen mail repair:1,169 backend passes/one explicit live-mail skip,45 targeted passes, isolated browser1pass; frontend193passes/types/lint/build pass. Frontend deadline fixf4f1708 matches the bounded foreground launch. Actual fresh OTP delivery remains unverified.
- P0 pending: one owner-entered fresh OTP verification → exact7-day trial → genuine website research → five reviewed ICPs → saved context → dashboard → logout/password-login and recovery. Do not retrieve passwords, OTPs or private user tokens. Do not repeat the completed customer reset or reopen legal/pricing/hosting decisions.
