-- Clean Intent Radar + Growth baseline; structure only, no customer seeds.
-- access_period_reservations access_period_reservations_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.access_period_reservations
    ADD CONSTRAINT access_period_reservations_pkey PRIMARY KEY (organization_id, operation_id, dimension);

-- access_period_usage access_period_usage_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.access_period_usage
    ADD CONSTRAINT access_period_usage_pkey PRIMARY KEY (organization_id, contract_id, period_start, dimension);

-- access_periods access_periods_organization_id_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.access_periods
    ADD CONSTRAINT access_periods_organization_id_id_key UNIQUE (organization_id, id);

-- access_periods access_periods_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.access_periods
    ADD CONSTRAINT access_periods_pkey PRIMARY KEY (id);

-- access_periods access_periods_source_kind_source_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.access_periods
    ADD CONSTRAINT access_periods_source_kind_source_id_key UNIQUE (source_kind, source_id);

-- account_admissions account_admissions_google_subject_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.account_admissions
    ADD CONSTRAINT account_admissions_google_subject_key UNIQUE (google_subject);

-- account_admissions account_admissions_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.account_admissions
    ADD CONSTRAINT account_admissions_pkey PRIMARY KEY (user_id);

-- account_link_tickets account_link_tickets_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.account_link_tickets
    ADD CONSTRAINT account_link_tickets_pkey PRIMARY KEY (id);

-- account_link_tickets account_link_tickets_token_hash_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.account_link_tickets
    ADD CONSTRAINT account_link_tickets_token_hash_key UNIQUE (token_hash);

-- account_login_tickets account_login_tickets_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.account_login_tickets
    ADD CONSTRAINT account_login_tickets_pkey PRIMARY KEY (id);

-- account_login_tickets account_login_tickets_token_hash_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.account_login_tickets
    ADD CONSTRAINT account_login_tickets_token_hash_key UNIQUE (token_hash);

-- account_privacy_requests account_privacy_requests_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.account_privacy_requests
    ADD CONSTRAINT account_privacy_requests_pkey PRIMARY KEY (id);

-- account_privacy_requests account_privacy_requests_user_id_request_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.account_privacy_requests
    ADD CONSTRAINT account_privacy_requests_user_id_request_id_key UNIQUE (user_id, request_id);

-- account_rate_limits account_rate_limits_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.account_rate_limits
    ADD CONSTRAINT account_rate_limits_pkey PRIMARY KEY (kind, bucket_hash, window_start);

-- account_recovery_requests account_recovery_requests_email_hash_request_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.account_recovery_requests
    ADD CONSTRAINT account_recovery_requests_email_hash_request_id_key UNIQUE (email_hash, request_id);

-- account_recovery_requests account_recovery_requests_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.account_recovery_requests
    ADD CONSTRAINT account_recovery_requests_pkey PRIMARY KEY (id);

-- account_recovery_tokens account_recovery_tokens_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.account_recovery_tokens
    ADD CONSTRAINT account_recovery_tokens_pkey PRIMARY KEY (id);

-- account_recovery_tokens account_recovery_tokens_token_hash_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.account_recovery_tokens
    ADD CONSTRAINT account_recovery_tokens_token_hash_key UNIQUE (token_hash);

-- account_recovery_tokens account_recovery_tokens_user_id_request_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.account_recovery_tokens
    ADD CONSTRAINT account_recovery_tokens_user_id_request_id_key UNIQUE (user_id, request_id);

-- account_roles account_roles_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.account_roles
    ADD CONSTRAINT account_roles_pkey PRIMARY KEY (email);

-- account_security_events account_security_events_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.account_security_events
    ADD CONSTRAINT account_security_events_pkey PRIMARY KEY (id);

-- account_terms_acceptances account_terms_acceptances_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.account_terms_acceptances
    ADD CONSTRAINT account_terms_acceptances_pkey PRIMARY KEY (nonce);

-- account_verifications account_verifications_email_request_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.account_verifications
    ADD CONSTRAINT account_verifications_email_request_id_key UNIQUE (email, request_id);

-- account_verifications account_verifications_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.account_verifications
    ADD CONSTRAINT account_verifications_pkey PRIMARY KEY (id);

-- acquisition_ai_cache acquisition_ai_cache_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.acquisition_ai_cache
    ADD CONSTRAINT acquisition_ai_cache_pkey PRIMARY KEY (fingerprint);

-- acquisition_provider_health acquisition_provider_health_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.acquisition_provider_health
    ADD CONSTRAINT acquisition_provider_health_pkey PRIMARY KEY (provider);

-- ai_request_usage ai_request_usage_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.ai_request_usage
    ADD CONSTRAINT ai_request_usage_pkey PRIMARY KEY (id);

-- artifact_objects artifact_objects_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.artifact_objects
    ADD CONSTRAINT artifact_objects_pkey PRIMARY KEY (object_key);

-- audit_log audit_log_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.audit_log
    ADD CONSTRAINT audit_log_pkey PRIMARY KEY (id);

-- billing_action_windows billing_action_windows_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.billing_action_windows
    ADD CONSTRAINT billing_action_windows_pkey PRIMARY KEY (organization_id, action, window_start);

-- billing_customers billing_customers_mode_provider_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.billing_customers
    ADD CONSTRAINT billing_customers_mode_provider_id_key UNIQUE (mode, provider_id);

-- billing_customers billing_customers_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.billing_customers
    ADD CONSTRAINT billing_customers_pkey PRIMARY KEY (organization_id, mode, provider_id);

-- billing_payments billing_payments_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.billing_payments
    ADD CONSTRAINT billing_payments_pkey PRIMARY KEY (mode, provider_id);

-- billing_plan_mappings billing_plan_mappings_mode_provider_plan_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.billing_plan_mappings
    ADD CONSTRAINT billing_plan_mappings_mode_provider_plan_id_key UNIQUE (mode, provider_plan_id);

-- billing_plan_mappings billing_plan_mappings_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.billing_plan_mappings
    ADD CONSTRAINT billing_plan_mappings_pkey PRIMARY KEY (mode, code);

-- billing_reservations billing_reservations_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.billing_reservations
    ADD CONSTRAINT billing_reservations_pkey PRIMARY KEY (organization_id, dimension, request_id);

-- billing_subscriptions billing_subscriptions_mode_provider_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.billing_subscriptions
    ADD CONSTRAINT billing_subscriptions_mode_provider_id_key UNIQUE (mode, provider_id);

-- billing_subscriptions billing_subscriptions_organization_id_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.billing_subscriptions
    ADD CONSTRAINT billing_subscriptions_organization_id_id_key UNIQUE (organization_id, id);

-- billing_subscriptions billing_subscriptions_organization_id_mode_request_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.billing_subscriptions
    ADD CONSTRAINT billing_subscriptions_organization_id_mode_request_id_key UNIQUE (organization_id, mode, request_id);

-- billing_subscriptions billing_subscriptions_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.billing_subscriptions
    ADD CONSTRAINT billing_subscriptions_pkey PRIMARY KEY (id);

-- billing_usage billing_usage_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.billing_usage
    ADD CONSTRAINT billing_usage_pkey PRIMARY KEY (organization_id, subscription_id, period_start, dimension);

-- billing_webhook_events billing_webhook_events_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.billing_webhook_events
    ADD CONSTRAINT billing_webhook_events_pkey PRIMARY KEY (mode, event_id);

-- billing_workspace_slots billing_workspace_slots_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.billing_workspace_slots
    ADD CONSTRAINT billing_workspace_slots_pkey PRIMARY KEY (organization_id, mode);

-- businesses businesses_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.businesses
    ADD CONSTRAINT businesses_pkey PRIMARY KEY (id);

-- commercial_contracts commercial_contracts_organization_id_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.commercial_contracts
    ADD CONSTRAINT commercial_contracts_organization_id_id_key UNIQUE (organization_id, id);

-- commercial_contracts commercial_contracts_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.commercial_contracts
    ADD CONSTRAINT commercial_contracts_pkey PRIMARY KEY (id);

-- commercial_contracts commercial_contracts_provider_mode_provider_subscription_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.commercial_contracts
    ADD CONSTRAINT commercial_contracts_provider_mode_provider_subscription_id_key UNIQUE (provider, mode, provider_subscription_id);

-- commercial_reservations commercial_reservations_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.commercial_reservations
    ADD CONSTRAINT commercial_reservations_pkey PRIMARY KEY (organization_id, operation_id, dimension);

-- commercial_usage commercial_usage_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.commercial_usage
    ADD CONSTRAINT commercial_usage_pkey PRIMARY KEY (organization_id, contract_id, period_start, dimension);

-- commercial_workspace_slots commercial_workspace_slots_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.commercial_workspace_slots
    ADD CONSTRAINT commercial_workspace_slots_pkey PRIMARY KEY (organization_id, mode);

-- customer_accounts customer_accounts_google_subject_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.customer_accounts
    ADD CONSTRAINT customer_accounts_google_subject_key UNIQUE (google_subject);

-- customer_accounts customer_accounts_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.customer_accounts
    ADD CONSTRAINT customer_accounts_pkey PRIMARY KEY (email);

-- customer_accounts customer_accounts_user_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.customer_accounts
    ADD CONSTRAINT customer_accounts_user_id_key UNIQUE (user_id);

-- customer_sessions customer_sessions_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.customer_sessions
    ADD CONSTRAINT customer_sessions_pkey PRIMARY KEY (id);

-- customer_sessions customer_sessions_token_hash_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.customer_sessions
    ADD CONSTRAINT customer_sessions_token_hash_key UNIQUE (token_hash);

-- customer_workspace_access customer_workspace_access_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.customer_workspace_access
    ADD CONSTRAINT customer_workspace_access_pkey PRIMARY KEY (organization_id);

-- developer_action_approvals developer_action_approvals_key_id_request_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.developer_action_approvals
    ADD CONSTRAINT developer_action_approvals_key_id_request_id_key UNIQUE (key_id, request_id);

-- developer_action_approvals developer_action_approvals_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.developer_action_approvals
    ADD CONSTRAINT developer_action_approvals_pkey PRIMARY KEY (id);

-- developer_request_windows developer_request_windows_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.developer_request_windows
    ADD CONSTRAINT developer_request_windows_pkey PRIMARY KEY (owner_key, window_start);

-- discovery_searches discovery_searches_organization_id_request_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.discovery_searches
    ADD CONSTRAINT discovery_searches_organization_id_request_id_key UNIQUE (organization_id, request_id);

-- discovery_searches discovery_searches_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.discovery_searches
    ADD CONSTRAINT discovery_searches_pkey PRIMARY KEY (id);

-- email_accounts email_accounts_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.email_accounts
    ADD CONSTRAINT email_accounts_pkey PRIMARY KEY (id);

-- growth_company_links growth_company_links_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.growth_company_links
    ADD CONSTRAINT growth_company_links_pkey PRIMARY KEY (organization_id, opportunity_id, business_id);

-- growth_competitors growth_competitors_organization_id_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.growth_competitors
    ADD CONSTRAINT growth_competitors_organization_id_id_key UNIQUE (organization_id, id);

-- growth_competitors growth_competitors_organization_id_request_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.growth_competitors
    ADD CONSTRAINT growth_competitors_organization_id_request_id_key UNIQUE (organization_id, request_id);

-- growth_competitors growth_competitors_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.growth_competitors
    ADD CONSTRAINT growth_competitors_pkey PRIMARY KEY (id);

-- growth_notes growth_notes_organization_id_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.growth_notes
    ADD CONSTRAINT growth_notes_organization_id_id_key UNIQUE (organization_id, id);

-- growth_notes growth_notes_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.growth_notes
    ADD CONSTRAINT growth_notes_pkey PRIMARY KEY (id);

-- growth_research growth_research_organization_id_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.growth_research
    ADD CONSTRAINT growth_research_organization_id_id_key UNIQUE (organization_id, id);

-- growth_research growth_research_organization_id_request_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.growth_research
    ADD CONSTRAINT growth_research_organization_id_request_id_key UNIQUE (organization_id, request_id);

-- growth_research growth_research_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.growth_research
    ADD CONSTRAINT growth_research_pkey PRIMARY KEY (id);

-- growth_theme_signals growth_theme_signals_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.growth_theme_signals
    ADD CONSTRAINT growth_theme_signals_pkey PRIMARY KEY (organization_id, theme_id, signal_id);

-- growth_themes growth_themes_organization_id_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.growth_themes
    ADD CONSTRAINT growth_themes_organization_id_id_key UNIQUE (organization_id, id);

-- growth_themes growth_themes_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.growth_themes
    ADD CONSTRAINT growth_themes_pkey PRIMARY KEY (id);

-- growth_watchlists growth_watchlists_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.growth_watchlists
    ADD CONSTRAINT growth_watchlists_pkey PRIMARY KEY (organization_id, monitor_id);

-- icp_ai_proposals icp_ai_proposals_organization_id_created_by_input_hash_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.icp_ai_proposals
    ADD CONSTRAINT icp_ai_proposals_organization_id_created_by_input_hash_key UNIQUE (organization_id, created_by, input_hash);

-- icp_ai_proposals icp_ai_proposals_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.icp_ai_proposals
    ADD CONSTRAINT icp_ai_proposals_pkey PRIMARY KEY (id);

-- icp_versions icp_versions_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.icp_versions
    ADD CONSTRAINT icp_versions_pkey PRIMARY KEY (icp_id, revision);

-- ideal_customer_profiles ideal_customer_profiles_id_organization_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.ideal_customer_profiles
    ADD CONSTRAINT ideal_customer_profiles_id_organization_id_key UNIQUE (id, organization_id);

-- ideal_customer_profiles ideal_customer_profiles_organization_id_request_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.ideal_customer_profiles
    ADD CONSTRAINT ideal_customer_profiles_organization_id_request_id_key UNIQUE (organization_id, request_id);

-- ideal_customer_profiles ideal_customer_profiles_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.ideal_customer_profiles
    ADD CONSTRAINT ideal_customer_profiles_pkey PRIMARY KEY (id);

-- integration_oauth_states integration_oauth_states_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.integration_oauth_states
    ADD CONSTRAINT integration_oauth_states_pkey PRIMARY KEY (state_hash);

-- intelligence_job_items intelligence_job_items_job_id_resource_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intelligence_job_items
    ADD CONSTRAINT intelligence_job_items_job_id_resource_id_key UNIQUE (job_id, resource_id);

-- intelligence_job_items intelligence_job_items_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intelligence_job_items
    ADD CONSTRAINT intelligence_job_items_pkey PRIMARY KEY (id);

-- intelligence_jobs intelligence_jobs_organization_id_request_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intelligence_jobs
    ADD CONSTRAINT intelligence_jobs_organization_id_request_id_key UNIQUE (organization_id, request_id);

-- intelligence_jobs intelligence_jobs_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intelligence_jobs
    ADD CONSTRAINT intelligence_jobs_pkey PRIMARY KEY (id);

-- intent_alerts intent_alerts_organization_id_event_key_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_alerts
    ADD CONSTRAINT intent_alerts_organization_id_event_key_key UNIQUE (organization_id, event_key);

-- intent_alerts intent_alerts_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_alerts
    ADD CONSTRAINT intent_alerts_pkey PRIMARY KEY (id);

-- intent_analyses intent_analyses_organization_id_signal_id_input_hash_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_analyses
    ADD CONSTRAINT intent_analyses_organization_id_signal_id_input_hash_key UNIQUE (organization_id, signal_id, input_hash);

-- intent_analyses intent_analyses_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_analyses
    ADD CONSTRAINT intent_analyses_pkey PRIMARY KEY (id);

-- intent_analysis_usage intent_analysis_usage_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_analysis_usage
    ADD CONSTRAINT intent_analysis_usage_pkey PRIMARY KEY (organization_id, day);

-- intent_collection_cursors intent_collection_cursors_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_collection_cursors
    ADD CONSTRAINT intent_collection_cursors_pkey PRIMARY KEY (organization_id, monitor_id, provider);

-- intent_discoveries intent_discoveries_organization_id_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_discoveries
    ADD CONSTRAINT intent_discoveries_organization_id_id_key UNIQUE (organization_id, id);

-- intent_discoveries intent_discoveries_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_discoveries
    ADD CONSTRAINT intent_discoveries_pkey PRIMARY KEY (id);

-- intent_feedback intent_feedback_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_feedback
    ADD CONSTRAINT intent_feedback_pkey PRIMARY KEY (organization_id, signal_id, actor);

-- intent_monitor_signals intent_monitor_signals_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_monitor_signals
    ADD CONSTRAINT intent_monitor_signals_pkey PRIMARY KEY (organization_id, monitor_id, signal_id);

-- intent_monitors intent_monitors_organization_id_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_monitors
    ADD CONSTRAINT intent_monitors_organization_id_id_key UNIQUE (organization_id, id);

-- intent_monitors intent_monitors_organization_id_request_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_monitors
    ADD CONSTRAINT intent_monitors_organization_id_request_id_key UNIQUE (organization_id, request_id);

-- intent_monitors intent_monitors_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_monitors
    ADD CONSTRAINT intent_monitors_pkey PRIMARY KEY (id);

-- intent_opportunities intent_opportunities_organization_id_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_opportunities
    ADD CONSTRAINT intent_opportunities_organization_id_id_key UNIQUE (organization_id, id);

-- intent_opportunities intent_opportunities_organization_id_signal_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_opportunities
    ADD CONSTRAINT intent_opportunities_organization_id_signal_id_key UNIQUE (organization_id, signal_id);

-- intent_opportunities intent_opportunities_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_opportunities
    ADD CONSTRAINT intent_opportunities_pkey PRIMARY KEY (id);

-- intent_preferences intent_preferences_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_preferences
    ADD CONSTRAINT intent_preferences_pkey PRIMARY KEY (organization_id);

-- intent_provider_limits intent_provider_limits_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_provider_limits
    ADD CONSTRAINT intent_provider_limits_pkey PRIMARY KEY (id);

-- intent_rankings intent_rankings_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_rankings
    ADD CONSTRAINT intent_rankings_pkey PRIMARY KEY (organization_id, signal_id);

-- intent_retention_cursors intent_retention_cursors_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_retention_cursors
    ADD CONSTRAINT intent_retention_cursors_pkey PRIMARY KEY (organization_id);

-- intent_saved_signals intent_saved_signals_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_saved_signals
    ADD CONSTRAINT intent_saved_signals_pkey PRIMARY KEY (organization_id, signal_id);

-- intent_signals intent_signals_organization_id_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_signals
    ADD CONSTRAINT intent_signals_organization_id_id_key UNIQUE (organization_id, id);

-- intent_signals intent_signals_organization_id_source_source_record_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_signals
    ADD CONSTRAINT intent_signals_organization_id_source_source_record_id_key UNIQUE (organization_id, source, source_record_id);

-- intent_signals intent_signals_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_signals
    ADD CONSTRAINT intent_signals_pkey PRIMARY KEY (id);

-- intent_source_cache intent_source_cache_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_source_cache
    ADD CONSTRAINT intent_source_cache_pkey PRIMARY KEY (organization_id, fingerprint);

-- intent_source_configs intent_source_configs_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_source_configs
    ADD CONSTRAINT intent_source_configs_pkey PRIMARY KEY (organization_id, id);

-- intent_source_runs intent_source_runs_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_source_runs
    ADD CONSTRAINT intent_source_runs_pkey PRIMARY KEY (organization_id, discovery_id, provider);

-- intent_source_usage intent_source_usage_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_source_usage
    ADD CONSTRAINT intent_source_usage_pkey PRIMARY KEY (organization_id, provider, day);

-- intent_worker_health intent_worker_health_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_worker_health
    ADD CONSTRAINT intent_worker_health_pkey PRIMARY KEY (worker_id);

-- internal_request_nonces internal_request_nonces_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.internal_request_nonces
    ADD CONSTRAINT internal_request_nonces_pkey PRIMARY KEY (nonce);

-- launch_trial_claims launch_trial_claims_company_domain_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.launch_trial_claims
    ADD CONSTRAINT launch_trial_claims_company_domain_key UNIQUE (company_domain);

-- launch_trial_claims launch_trial_claims_organization_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.launch_trial_claims
    ADD CONSTRAINT launch_trial_claims_organization_id_key UNIQUE (organization_id);

-- launch_trial_claims launch_trial_claims_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.launch_trial_claims
    ADD CONSTRAINT launch_trial_claims_pkey PRIMARY KEY (id);

-- launch_trial_claims launch_trial_claims_user_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.launch_trial_claims
    ADD CONSTRAINT launch_trial_claims_user_id_key UNIQUE (user_id);

-- organization_ai_usage organization_ai_usage_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.organization_ai_usage
    ADD CONSTRAINT organization_ai_usage_pkey PRIMARY KEY (organization_id, day, feature);

-- organization_domains organization_domains_organization_id_domain_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.organization_domains
    ADD CONSTRAINT organization_domains_organization_id_domain_key UNIQUE (organization_id, domain);

-- organization_domains organization_domains_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.organization_domains
    ADD CONSTRAINT organization_domains_pkey PRIMARY KEY (id);

-- organization_integrations organization_integrations_id_organization_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.organization_integrations
    ADD CONSTRAINT organization_integrations_id_organization_id_key UNIQUE (id, organization_id);

-- organization_integrations organization_integrations_organization_id_provider_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.organization_integrations
    ADD CONSTRAINT organization_integrations_organization_id_provider_key UNIQUE (organization_id, provider);

-- organization_integrations organization_integrations_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.organization_integrations
    ADD CONSTRAINT organization_integrations_pkey PRIMARY KEY (id);

-- organization_memberships organization_memberships_organization_id_user_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.organization_memberships
    ADD CONSTRAINT organization_memberships_organization_id_user_id_key UNIQUE (organization_id, user_id);

-- organization_memberships organization_memberships_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.organization_memberships
    ADD CONSTRAINT organization_memberships_pkey PRIMARY KEY (id);

-- organization_onboarding organization_onboarding_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.organization_onboarding
    ADD CONSTRAINT organization_onboarding_pkey PRIMARY KEY (organization_id);

-- organization_products organization_products_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.organization_products
    ADD CONSTRAINT organization_products_pkey PRIMARY KEY (organization_id, product);

-- organization_profile_job_events organization_profile_job_events_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.organization_profile_job_events
    ADD CONSTRAINT organization_profile_job_events_pkey PRIMARY KEY (id);

-- organization_profile_jobs organization_profile_jobs_organization_id_request_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.organization_profile_jobs
    ADD CONSTRAINT organization_profile_jobs_organization_id_request_id_key UNIQUE (organization_id, request_id);

-- organization_profile_jobs organization_profile_jobs_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.organization_profile_jobs
    ADD CONSTRAINT organization_profile_jobs_pkey PRIMARY KEY (id);

-- organization_profile_sources organization_profile_sources_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.organization_profile_sources
    ADD CONSTRAINT organization_profile_sources_pkey PRIMARY KEY (id);

-- organization_profiles organization_profiles_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.organization_profiles
    ADD CONSTRAINT organization_profiles_pkey PRIMARY KEY (organization_id);

-- organization_services organization_services_organization_id_slug_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.organization_services
    ADD CONSTRAINT organization_services_organization_id_slug_key UNIQUE (organization_id, slug);

-- organization_services organization_services_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.organization_services
    ADD CONSTRAINT organization_services_pkey PRIMARY KEY (id);

-- organization_settings organization_settings_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.organization_settings
    ADD CONSTRAINT organization_settings_pkey PRIMARY KEY (organization_id);

-- organization_setup organization_setup_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.organization_setup
    ADD CONSTRAINT organization_setup_pkey PRIMARY KEY (organization_id);

-- organizations organizations_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.organizations
    ADD CONSTRAINT organizations_pkey PRIMARY KEY (id);

-- organizations organizations_slug_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.organizations
    ADD CONSTRAINT organizations_slug_key UNIQUE (slug);

-- payu_access_callback_events payu_access_callback_events_order_id_body_sha256_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.payu_access_callback_events
    ADD CONSTRAINT payu_access_callback_events_order_id_body_sha256_key UNIQUE (order_id, body_sha256);

-- payu_access_callback_events payu_access_callback_events_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.payu_access_callback_events
    ADD CONSTRAINT payu_access_callback_events_pkey PRIMARY KEY (id);

-- payu_access_orders payu_access_orders_mode_provider_payment_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.payu_access_orders
    ADD CONSTRAINT payu_access_orders_mode_provider_payment_id_key UNIQUE (mode, provider_payment_id);

-- payu_access_orders payu_access_orders_mode_txn_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.payu_access_orders
    ADD CONSTRAINT payu_access_orders_mode_txn_id_key UNIQUE (mode, txn_id);

-- payu_access_orders payu_access_orders_organization_id_request_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.payu_access_orders
    ADD CONSTRAINT payu_access_orders_organization_id_request_id_key UNIQUE (organization_id, request_id);

-- payu_access_orders payu_access_orders_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.payu_access_orders
    ADD CONSTRAINT payu_access_orders_pkey PRIMARY KEY (id);

-- payu_access_refunds payu_access_refunds_organization_id_request_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.payu_access_refunds
    ADD CONSTRAINT payu_access_refunds_organization_id_request_id_key UNIQUE (organization_id, request_id);

-- payu_access_refunds payu_access_refunds_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.payu_access_refunds
    ADD CONSTRAINT payu_access_refunds_pkey PRIMARY KEY (id);

-- payu_access_refunds payu_access_refunds_provider_refund_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.payu_access_refunds
    ADD CONSTRAINT payu_access_refunds_provider_refund_id_key UNIQUE (provider_refund_id);

-- payu_refund_observations payu_refund_observations_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.payu_refund_observations
    ADD CONSTRAINT payu_refund_observations_pkey PRIMARY KEY (mode, provider_refund_id);

-- pipeline_runs pipeline_runs_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.pipeline_runs
    ADD CONSTRAINT pipeline_runs_pkey PRIMARY KEY (id);

-- prospects prospects_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.prospects
    ADD CONSTRAINT prospects_pkey PRIMARY KEY (id);

-- provider_rate_limits provider_rate_limits_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.provider_rate_limits
    ADD CONSTRAINT provider_rate_limits_pkey PRIMARY KEY (provider);

-- scan_campaigns scan_campaigns_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.scan_campaigns
    ADD CONSTRAINT scan_campaigns_pkey PRIMARY KEY (id);

-- shared_settings shared_settings_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.shared_settings
    ADD CONSTRAINT shared_settings_pkey PRIMARY KEY (id);

-- transactional_notification_events transactional_notification_events_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.transactional_notification_events
    ADD CONSTRAINT transactional_notification_events_pkey PRIMARY KEY (provider_event_id);

-- transactional_notifications transactional_notifications_dedupe_key_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.transactional_notifications
    ADD CONSTRAINT transactional_notifications_dedupe_key_key UNIQUE (dedupe_key);

-- transactional_notifications transactional_notifications_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.transactional_notifications
    ADD CONSTRAINT transactional_notifications_pkey PRIMARY KEY (id);

-- transactional_notifications transactional_notifications_provider_message_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.transactional_notifications
    ADD CONSTRAINT transactional_notifications_provider_message_id_key UNIQUE (provider_message_id);

-- transactional_suppressions transactional_suppressions_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.transactional_suppressions
    ADD CONSTRAINT transactional_suppressions_pkey PRIMARY KEY (account_email);

-- user_profiles user_profiles_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.user_profiles
    ADD CONSTRAINT user_profiles_pkey PRIMARY KEY (user_id);

-- users users_email_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.users
    ADD CONSTRAINT users_email_key UNIQUE (email);

-- users users_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);

-- webhook_deliveries webhook_deliveries_endpoint_id_event_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.webhook_deliveries
    ADD CONSTRAINT webhook_deliveries_endpoint_id_event_id_key UNIQUE (endpoint_id, event_id);

-- webhook_deliveries webhook_deliveries_id_organization_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.webhook_deliveries
    ADD CONSTRAINT webhook_deliveries_id_organization_id_key UNIQUE (id, organization_id);

-- webhook_deliveries webhook_deliveries_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.webhook_deliveries
    ADD CONSTRAINT webhook_deliveries_pkey PRIMARY KEY (id);

-- webhook_delivery_attempts webhook_delivery_attempts_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.webhook_delivery_attempts
    ADD CONSTRAINT webhook_delivery_attempts_pkey PRIMARY KEY (delivery_id, attempt);

-- webhook_endpoints webhook_endpoints_id_organization_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.webhook_endpoints
    ADD CONSTRAINT webhook_endpoints_id_organization_id_key UNIQUE (id, organization_id);

-- webhook_endpoints webhook_endpoints_organization_id_request_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.webhook_endpoints
    ADD CONSTRAINT webhook_endpoints_organization_id_request_id_key UNIQUE (organization_id, request_id);

-- webhook_endpoints webhook_endpoints_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.webhook_endpoints
    ADD CONSTRAINT webhook_endpoints_pkey PRIMARY KEY (id);

-- workspace_api_keys workspace_api_keys_id_organization_id_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.workspace_api_keys
    ADD CONSTRAINT workspace_api_keys_id_organization_id_key UNIQUE (id, organization_id);

-- workspace_api_keys workspace_api_keys_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.workspace_api_keys
    ADD CONSTRAINT workspace_api_keys_pkey PRIMARY KEY (id);

-- workspace_creation_requests workspace_creation_requests_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.workspace_creation_requests
    ADD CONSTRAINT workspace_creation_requests_pkey PRIMARY KEY (user_id, request_id);

-- workspace_invitations workspace_invitations_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.workspace_invitations
    ADD CONSTRAINT workspace_invitations_pkey PRIMARY KEY (id);

-- workspace_invitations workspace_invitations_token_hash_key; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.workspace_invitations
    ADD CONSTRAINT workspace_invitations_token_hash_key UNIQUE (token_hash);

-- workspace_notifications workspace_notifications_pkey; Type: CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.workspace_notifications
    ADD CONSTRAINT workspace_notifications_pkey PRIMARY KEY (id);

-- access_period_current; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX access_period_current ON __PLANEBYTE_SCHEMA__.access_periods USING btree (organization_id, status, paid_start, paid_end);

-- access_period_expiry; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX access_period_expiry ON __PLANEBYTE_SCHEMA__.access_periods USING btree (status, paid_end);

-- account_security_actor; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX account_security_actor ON __PLANEBYTE_SCHEMA__.account_security_events USING btree (account_hash, created_at);

-- account_verification_expiry; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX account_verification_expiry ON __PLANEBYTE_SCHEMA__.account_verifications USING btree (email, expires_at);

-- ai_request_usage_workspace_time; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX ai_request_usage_workspace_time ON __PLANEBYTE_SCHEMA__.ai_request_usage USING btree (organization_id, created_at);

-- billing_payments_page; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX billing_payments_page ON __PLANEBYTE_SCHEMA__.billing_payments USING btree (organization_id, recorded_at, provider_id);

-- billing_reconcile_due; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX billing_reconcile_due ON __PLANEBYTE_SCHEMA__.billing_subscriptions USING btree (mode, next_reconcile_at, id);

-- billing_webhooks_due; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX billing_webhooks_due ON __PLANEBYTE_SCHEMA__.billing_webhook_events USING btree (mode, status, next_attempt_at);

-- commercial_usage_period; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX commercial_usage_period ON __PLANEBYTE_SCHEMA__.commercial_usage USING btree (organization_id, contract_id, period_start);

-- customer_session_owner; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX customer_session_owner ON __PLANEBYTE_SCHEMA__.customer_sessions USING btree (user_id, expires_at);

-- growth_notes_resource; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX growth_notes_resource ON __PLANEBYTE_SCHEMA__.growth_notes USING btree (organization_id, resource_kind, resource_id, created_at);

-- growth_research_page; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX growth_research_page ON __PLANEBYTE_SCHEMA__.growth_research USING btree (organization_id, kind, created_at, id);

-- growth_theme_signal_lookup; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX growth_theme_signal_lookup ON __PLANEBYTE_SCHEMA__.growth_theme_signals USING btree (organization_id, signal_id);

-- growth_themes_page; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX growth_themes_page ON __PLANEBYTE_SCHEMA__.growth_themes USING btree (organization_id, status, created_at, id);

-- idx_account_terms_user; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_account_terms_user ON __PLANEBYTE_SCHEMA__.account_terms_acceptances USING btree (user_id, recorded_at);

-- idx_acquisition_cache_expiry; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_acquisition_cache_expiry ON __PLANEBYTE_SCHEMA__.acquisition_ai_cache USING btree (organization_id, expires_at);

-- idx_ai_usage_day; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_ai_usage_day ON __PLANEBYTE_SCHEMA__.organization_ai_usage USING btree (day, feature);

-- idx_api_keys_workspace; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_api_keys_workspace ON __PLANEBYTE_SCHEMA__.workspace_api_keys USING btree (organization_id, revoked_at, created_at);

-- idx_audit_log_organization; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_audit_log_organization ON __PLANEBYTE_SCHEMA__.audit_log USING btree (organization_id);

-- idx_audit_time; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_audit_time ON __PLANEBYTE_SCHEMA__.audit_log USING btree (created_at);

-- idx_business_run_status; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_business_run_status ON __PLANEBYTE_SCHEMA__.businesses USING btree (run_id, processing_status, prospect_id);

-- idx_businesses_chain; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_businesses_chain ON __PLANEBYTE_SCHEMA__.businesses USING btree (is_chain);

-- idx_businesses_city; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_businesses_city ON __PLANEBYTE_SCHEMA__.businesses USING btree (city);

-- idx_businesses_country; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_businesses_country ON __PLANEBYTE_SCHEMA__.businesses USING btree (country);

-- idx_businesses_domain; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_businesses_domain ON __PLANEBYTE_SCHEMA__.businesses USING btree (domain);

-- idx_businesses_norm_name; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_businesses_norm_name ON __PLANEBYTE_SCHEMA__.businesses USING btree (normalized_name);

-- idx_businesses_norm_phone; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_businesses_norm_phone ON __PLANEBYTE_SCHEMA__.businesses USING btree (normalized_phone);

-- idx_businesses_prospect; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_businesses_prospect ON __PLANEBYTE_SCHEMA__.businesses USING btree (prospect_id, id);

-- idx_businesses_rejected; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_businesses_rejected ON __PLANEBYTE_SCHEMA__.businesses USING btree (is_rejected);

-- idx_businesses_run_id; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_businesses_run_id ON __PLANEBYTE_SCHEMA__.businesses USING btree (run_id);

-- idx_businesses_state; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_businesses_state ON __PLANEBYTE_SCHEMA__.businesses USING btree (state);

-- idx_businesses_status; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_businesses_status ON __PLANEBYTE_SCHEMA__.businesses USING btree (processing_status);

-- idx_businesses_vert_val; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_businesses_vert_val ON __PLANEBYTE_SCHEMA__.businesses USING btree (vertical_validation_status);

-- idx_businesses_vertical; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_businesses_vertical ON __PLANEBYTE_SCHEMA__.businesses USING btree (vertical);

-- idx_businesses_web_status; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_businesses_web_status ON __PLANEBYTE_SCHEMA__.businesses USING btree (website_status);

-- idx_campaign_source_time; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_campaign_source_time ON __PLANEBYTE_SCHEMA__.scan_campaigns USING btree (source_type, created_at);

-- idx_developer_approvals; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_developer_approvals ON __PLANEBYTE_SCHEMA__.developer_action_approvals USING btree (organization_id, status, created_at);

-- idx_developer_window_cleanup; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_developer_window_cleanup ON __PLANEBYTE_SCHEMA__.developer_request_windows USING btree (window_start);

-- idx_discovery_search_workspace; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_discovery_search_workspace ON __PLANEBYTE_SCHEMA__.discovery_searches USING btree (organization_id, archived_at, updated_at);

-- idx_email_accounts_organization; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_email_accounts_organization ON __PLANEBYTE_SCHEMA__.email_accounts USING btree (organization_id);

-- idx_icp_proposal_owner; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_icp_proposal_owner ON __PLANEBYTE_SCHEMA__.icp_ai_proposals USING btree (organization_id, created_by, expires_at);

-- idx_icp_workspace; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_icp_workspace ON __PLANEBYTE_SCHEMA__.ideal_customer_profiles USING btree (organization_id, status, updated_at);

-- idx_integration_states_owner; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_integration_states_owner ON __PLANEBYTE_SCHEMA__.integration_oauth_states USING btree (organization_id, created_at);

-- idx_integrations_workspace; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_integrations_workspace ON __PLANEBYTE_SCHEMA__.organization_integrations USING btree (organization_id, status);

-- idx_intelligence_jobs_queue; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_intelligence_jobs_queue ON __PLANEBYTE_SCHEMA__.intelligence_jobs USING btree (status, organization_id, created_at);

-- idx_membership_organization; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_membership_organization ON __PLANEBYTE_SCHEMA__.organization_memberships USING btree (organization_id, status);

-- idx_membership_user; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_membership_user ON __PLANEBYTE_SCHEMA__.organization_memberships USING btree (user_id, status);

-- idx_nonce_expiry; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_nonce_expiry ON __PLANEBYTE_SCHEMA__.internal_request_nonces USING btree (expires_at);

-- idx_pipeline_campaign_status; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_pipeline_campaign_status ON __PLANEBYTE_SCHEMA__.pipeline_runs USING btree (campaign_id, status);

-- idx_pipeline_runs_organization; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_pipeline_runs_organization ON __PLANEBYTE_SCHEMA__.pipeline_runs USING btree (organization_id);

-- idx_profile_job_events_owned; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_profile_job_events_owned ON __PLANEBYTE_SCHEMA__.organization_profile_job_events USING btree (organization_id, job_id, attempt, created_at);

-- idx_profile_job_scope; Type: INDEX; Schema: configured target; Owner: -
CREATE UNIQUE INDEX idx_profile_job_scope ON __PLANEBYTE_SCHEMA__.organization_profile_jobs USING btree (organization_id, id);

-- idx_profile_jobs_input; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_profile_jobs_input ON __PLANEBYTE_SCHEMA__.organization_profile_jobs USING btree (organization_id, input_hash, status, updated_at);

-- idx_profile_jobs_workspace; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_profile_jobs_workspace ON __PLANEBYTE_SCHEMA__.organization_profile_jobs USING btree (organization_id, created_at);

-- idx_profile_sources_organization; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_profile_sources_organization ON __PLANEBYTE_SCHEMA__.organization_profile_sources USING btree (organization_id, field_name);

-- idx_prospects_organization; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_prospects_organization ON __PLANEBYTE_SCHEMA__.prospects USING btree (organization_id);

-- idx_prospects_seen; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_prospects_seen ON __PLANEBYTE_SCHEMA__.prospects USING btree (first_seen_at, last_seen_at);

-- idx_prospects_workflow; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_prospects_workflow ON __PLANEBYTE_SCHEMA__.prospects USING btree (lead_status, assigned_to);

-- idx_runs_campaign; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_runs_campaign ON __PLANEBYTE_SCHEMA__.pipeline_runs USING btree (campaign_id, status);

-- idx_scan_campaigns_organization; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_scan_campaigns_organization ON __PLANEBYTE_SCHEMA__.scan_campaigns USING btree (organization_id);

-- idx_services_organization; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_services_organization ON __PLANEBYTE_SCHEMA__.organization_services USING btree (organization_id, active);

-- idx_shared_settings_organization; Type: INDEX; Schema: configured target; Owner: -
CREATE UNIQUE INDEX idx_shared_settings_organization ON __PLANEBYTE_SCHEMA__.shared_settings USING btree (organization_id);

-- idx_webhook_delivery_due; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_webhook_delivery_due ON __PLANEBYTE_SCHEMA__.webhook_deliveries USING btree (status, next_attempt_at, endpoint_id);

-- idx_webhook_delivery_workspace; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_webhook_delivery_workspace ON __PLANEBYTE_SCHEMA__.webhook_deliveries USING btree (organization_id, status);

-- idx_webhooks_owner; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_webhooks_owner ON __PLANEBYTE_SCHEMA__.webhook_endpoints USING btree (organization_id, status);

-- idx_workspace_domains; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_workspace_domains ON __PLANEBYTE_SCHEMA__.organization_domains USING btree (organization_id, status);

-- idx_workspace_invitation_list; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_workspace_invitation_list ON __PLANEBYTE_SCHEMA__.workspace_invitations USING btree (organization_id, created_at);

-- idx_workspace_invitation_pending; Type: INDEX; Schema: configured target; Owner: -
CREATE UNIQUE INDEX idx_workspace_invitation_pending ON __PLANEBYTE_SCHEMA__.workspace_invitations USING btree (organization_id, email) WHERE (status = 'PENDING'::text);

-- idx_workspace_notification_user; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX idx_workspace_notification_user ON __PLANEBYTE_SCHEMA__.workspace_notifications USING btree (organization_id, user_id, created_at);

-- intent_alerts_workspace; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX intent_alerts_workspace ON __PLANEBYTE_SCHEMA__.intent_alerts USING btree (organization_id, created_at);

-- intent_due_monitor_page; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX intent_due_monitor_page ON __PLANEBYTE_SCHEMA__.intent_monitors USING btree (status, next_run_at);

-- intent_monitors_due; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX intent_monitors_due ON __PLANEBYTE_SCHEMA__.intent_monitors USING btree (status, next_run_at);

-- intent_monitors_workspace; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX intent_monitors_workspace ON __PLANEBYTE_SCHEMA__.intent_monitors USING btree (organization_id, status, updated_at);

-- intent_saved_page; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX intent_saved_page ON __PLANEBYTE_SCHEMA__.intent_saved_signals USING btree (organization_id, collection, saved_at, signal_id);

-- intent_signal_rank_page; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX intent_signal_rank_page ON __PLANEBYTE_SCHEMA__.intent_signals USING btree (organization_id, available, score, id);

-- intent_signals_workspace; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX intent_signals_workspace ON __PLANEBYTE_SCHEMA__.intent_signals USING btree (organization_id, observed_at, score);

-- intent_source_run_health; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX intent_source_run_health ON __PLANEBYTE_SCHEMA__.intent_source_runs USING btree (organization_id, provider, updated_at);

-- payu_access_order_owner; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX payu_access_order_owner ON __PLANEBYTE_SCHEMA__.payu_access_orders USING btree (organization_id, created_at);

-- payu_refund_order; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX payu_refund_order ON __PLANEBYTE_SCHEMA__.payu_refund_observations USING btree (organization_id, order_id);

-- privacy_request_actor; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX privacy_request_actor ON __PLANEBYTE_SCHEMA__.account_privacy_requests USING btree (user_id, created_at);

-- privacy_request_review; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX privacy_request_review ON __PLANEBYTE_SCHEMA__.account_privacy_requests USING btree (status, ordinary_data_due_at, created_at);

-- transactional_delivery_queue; Type: INDEX; Schema: configured target; Owner: -
CREATE INDEX transactional_delivery_queue ON __PLANEBYTE_SCHEMA__.transactional_notifications USING btree (status, available_at);
