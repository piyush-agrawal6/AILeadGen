-- Clean Intent Radar + Growth baseline; structure only, no customer seeds.
-- access_period_reservations access_period_reservations_organization_id_contract_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.access_period_reservations
    ADD CONSTRAINT access_period_reservations_organization_id_contract_id_fkey FOREIGN KEY (organization_id, contract_id) REFERENCES __PLANEBYTE_SCHEMA__.access_periods(organization_id, id);

-- access_period_usage access_period_usage_organization_id_contract_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.access_period_usage
    ADD CONSTRAINT access_period_usage_organization_id_contract_id_fkey FOREIGN KEY (organization_id, contract_id) REFERENCES __PLANEBYTE_SCHEMA__.access_periods(organization_id, id);

-- access_periods access_periods_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.access_periods
    ADD CONSTRAINT access_periods_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- account_admissions account_admissions_user_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.account_admissions
    ADD CONSTRAINT account_admissions_user_id_fkey FOREIGN KEY (user_id) REFERENCES __PLANEBYTE_SCHEMA__.users(id);

-- account_link_tickets account_link_tickets_session_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.account_link_tickets
    ADD CONSTRAINT account_link_tickets_session_id_fkey FOREIGN KEY (session_id) REFERENCES __PLANEBYTE_SCHEMA__.customer_sessions(id);

-- account_link_tickets account_link_tickets_user_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.account_link_tickets
    ADD CONSTRAINT account_link_tickets_user_id_fkey FOREIGN KEY (user_id) REFERENCES __PLANEBYTE_SCHEMA__.users(id);

-- account_login_tickets account_login_tickets_user_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.account_login_tickets
    ADD CONSTRAINT account_login_tickets_user_id_fkey FOREIGN KEY (user_id) REFERENCES __PLANEBYTE_SCHEMA__.users(id);

-- account_privacy_requests account_privacy_requests_user_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.account_privacy_requests
    ADD CONSTRAINT account_privacy_requests_user_id_fkey FOREIGN KEY (user_id) REFERENCES __PLANEBYTE_SCHEMA__.users(id);

-- account_privacy_requests account_privacy_requests_verified_session_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.account_privacy_requests
    ADD CONSTRAINT account_privacy_requests_verified_session_id_fkey FOREIGN KEY (verified_session_id) REFERENCES __PLANEBYTE_SCHEMA__.customer_sessions(id);

-- account_recovery_tokens account_recovery_tokens_user_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.account_recovery_tokens
    ADD CONSTRAINT account_recovery_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES __PLANEBYTE_SCHEMA__.users(id);

-- account_terms_acceptances account_terms_acceptances_user_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.account_terms_acceptances
    ADD CONSTRAINT account_terms_acceptances_user_id_fkey FOREIGN KEY (user_id) REFERENCES __PLANEBYTE_SCHEMA__.users(id);

-- acquisition_ai_cache acquisition_ai_cache_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.acquisition_ai_cache
    ADD CONSTRAINT acquisition_ai_cache_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- ai_request_usage ai_request_usage_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.ai_request_usage
    ADD CONSTRAINT ai_request_usage_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- artifact_objects artifact_objects_business_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.artifact_objects
    ADD CONSTRAINT artifact_objects_business_id_fkey FOREIGN KEY (business_id) REFERENCES __PLANEBYTE_SCHEMA__.businesses(id);

-- artifact_objects artifact_objects_run_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.artifact_objects
    ADD CONSTRAINT artifact_objects_run_id_fkey FOREIGN KEY (run_id) REFERENCES __PLANEBYTE_SCHEMA__.pipeline_runs(id);

-- billing_action_windows billing_action_windows_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.billing_action_windows
    ADD CONSTRAINT billing_action_windows_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- billing_customers billing_customers_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.billing_customers
    ADD CONSTRAINT billing_customers_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- billing_payments billing_payments_organization_id_subscription_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.billing_payments
    ADD CONSTRAINT billing_payments_organization_id_subscription_id_fkey FOREIGN KEY (organization_id, subscription_id) REFERENCES __PLANEBYTE_SCHEMA__.billing_subscriptions(organization_id, id);

-- billing_reservations billing_reservations_organization_id_subscription_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.billing_reservations
    ADD CONSTRAINT billing_reservations_organization_id_subscription_id_fkey FOREIGN KEY (organization_id, subscription_id) REFERENCES __PLANEBYTE_SCHEMA__.billing_subscriptions(organization_id, id);

-- billing_subscriptions billing_subscriptions_created_by_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.billing_subscriptions
    ADD CONSTRAINT billing_subscriptions_created_by_fkey FOREIGN KEY (created_by) REFERENCES __PLANEBYTE_SCHEMA__.users(id);

-- billing_subscriptions billing_subscriptions_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.billing_subscriptions
    ADD CONSTRAINT billing_subscriptions_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- billing_usage billing_usage_organization_id_subscription_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.billing_usage
    ADD CONSTRAINT billing_usage_organization_id_subscription_id_fkey FOREIGN KEY (organization_id, subscription_id) REFERENCES __PLANEBYTE_SCHEMA__.billing_subscriptions(organization_id, id);

-- billing_workspace_slots billing_workspace_slots_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.billing_workspace_slots
    ADD CONSTRAINT billing_workspace_slots_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- billing_workspace_slots billing_workspace_slots_organization_id_subscription_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.billing_workspace_slots
    ADD CONSTRAINT billing_workspace_slots_organization_id_subscription_id_fkey FOREIGN KEY (organization_id, subscription_id) REFERENCES __PLANEBYTE_SCHEMA__.billing_subscriptions(organization_id, id);

-- businesses businesses_prospect_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.businesses
    ADD CONSTRAINT businesses_prospect_id_fkey FOREIGN KEY (prospect_id) REFERENCES __PLANEBYTE_SCHEMA__.prospects(id);

-- commercial_contracts commercial_contracts_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.commercial_contracts
    ADD CONSTRAINT commercial_contracts_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- commercial_reservations commercial_reservations_organization_id_contract_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.commercial_reservations
    ADD CONSTRAINT commercial_reservations_organization_id_contract_id_fkey FOREIGN KEY (organization_id, contract_id) REFERENCES __PLANEBYTE_SCHEMA__.commercial_contracts(organization_id, id);

-- commercial_usage commercial_usage_organization_id_contract_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.commercial_usage
    ADD CONSTRAINT commercial_usage_organization_id_contract_id_fkey FOREIGN KEY (organization_id, contract_id) REFERENCES __PLANEBYTE_SCHEMA__.commercial_contracts(organization_id, id);

-- commercial_workspace_slots commercial_workspace_slots_organization_id_contract_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.commercial_workspace_slots
    ADD CONSTRAINT commercial_workspace_slots_organization_id_contract_id_fkey FOREIGN KEY (organization_id, contract_id) REFERENCES __PLANEBYTE_SCHEMA__.commercial_contracts(organization_id, id);

-- commercial_workspace_slots commercial_workspace_slots_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.commercial_workspace_slots
    ADD CONSTRAINT commercial_workspace_slots_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- customer_accounts customer_accounts_user_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.customer_accounts
    ADD CONSTRAINT customer_accounts_user_id_fkey FOREIGN KEY (user_id) REFERENCES __PLANEBYTE_SCHEMA__.users(id);

-- customer_sessions customer_sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.customer_sessions
    ADD CONSTRAINT customer_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES __PLANEBYTE_SCHEMA__.users(id);

-- customer_workspace_access customer_workspace_access_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.customer_workspace_access
    ADD CONSTRAINT customer_workspace_access_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- customer_workspace_access customer_workspace_access_registered_by_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.customer_workspace_access
    ADD CONSTRAINT customer_workspace_access_registered_by_fkey FOREIGN KEY (registered_by) REFERENCES __PLANEBYTE_SCHEMA__.users(id);

-- developer_action_approvals developer_action_approvals_decided_by_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.developer_action_approvals
    ADD CONSTRAINT developer_action_approvals_decided_by_fkey FOREIGN KEY (decided_by) REFERENCES __PLANEBYTE_SCHEMA__.users(id);

-- developer_action_approvals developer_action_approvals_key_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.developer_action_approvals
    ADD CONSTRAINT developer_action_approvals_key_id_fkey FOREIGN KEY (key_id) REFERENCES __PLANEBYTE_SCHEMA__.workspace_api_keys(id);

-- developer_action_approvals developer_action_approvals_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.developer_action_approvals
    ADD CONSTRAINT developer_action_approvals_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- developer_action_approvals developer_action_approvals_requested_by_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.developer_action_approvals
    ADD CONSTRAINT developer_action_approvals_requested_by_fkey FOREIGN KEY (requested_by) REFERENCES __PLANEBYTE_SCHEMA__.users(id);

-- discovery_searches discovery_searches_created_by_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.discovery_searches
    ADD CONSTRAINT discovery_searches_created_by_fkey FOREIGN KEY (created_by) REFERENCES __PLANEBYTE_SCHEMA__.users(id);

-- discovery_searches discovery_searches_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.discovery_searches
    ADD CONSTRAINT discovery_searches_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- email_accounts email_accounts_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.email_accounts
    ADD CONSTRAINT email_accounts_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- growth_company_links growth_company_links_business_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.growth_company_links
    ADD CONSTRAINT growth_company_links_business_id_fkey FOREIGN KEY (business_id) REFERENCES __PLANEBYTE_SCHEMA__.businesses(id);

-- growth_company_links growth_company_links_created_by_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.growth_company_links
    ADD CONSTRAINT growth_company_links_created_by_fkey FOREIGN KEY (created_by) REFERENCES __PLANEBYTE_SCHEMA__.users(id);

-- growth_company_links growth_company_links_organization_id_opportunity_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.growth_company_links
    ADD CONSTRAINT growth_company_links_organization_id_opportunity_id_fkey FOREIGN KEY (organization_id, opportunity_id) REFERENCES __PLANEBYTE_SCHEMA__.intent_opportunities(organization_id, id);

-- growth_competitors growth_competitors_created_by_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.growth_competitors
    ADD CONSTRAINT growth_competitors_created_by_fkey FOREIGN KEY (created_by) REFERENCES __PLANEBYTE_SCHEMA__.users(id);

-- growth_competitors growth_competitors_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.growth_competitors
    ADD CONSTRAINT growth_competitors_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- growth_notes growth_notes_author_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.growth_notes
    ADD CONSTRAINT growth_notes_author_fkey FOREIGN KEY (author) REFERENCES __PLANEBYTE_SCHEMA__.users(id);

-- growth_notes growth_notes_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.growth_notes
    ADD CONSTRAINT growth_notes_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- growth_research growth_research_created_by_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.growth_research
    ADD CONSTRAINT growth_research_created_by_fkey FOREIGN KEY (created_by) REFERENCES __PLANEBYTE_SCHEMA__.users(id);

-- growth_research growth_research_job_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.growth_research
    ADD CONSTRAINT growth_research_job_id_fkey FOREIGN KEY (job_id) REFERENCES __PLANEBYTE_SCHEMA__.intelligence_jobs(id);

-- growth_research growth_research_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.growth_research
    ADD CONSTRAINT growth_research_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- growth_theme_signals growth_theme_signals_organization_id_signal_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.growth_theme_signals
    ADD CONSTRAINT growth_theme_signals_organization_id_signal_id_fkey FOREIGN KEY (organization_id, signal_id) REFERENCES __PLANEBYTE_SCHEMA__.intent_signals(organization_id, id);

-- growth_theme_signals growth_theme_signals_organization_id_theme_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.growth_theme_signals
    ADD CONSTRAINT growth_theme_signals_organization_id_theme_id_fkey FOREIGN KEY (organization_id, theme_id) REFERENCES __PLANEBYTE_SCHEMA__.growth_themes(organization_id, id);

-- growth_themes growth_themes_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.growth_themes
    ADD CONSTRAINT growth_themes_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- growth_themes growth_themes_organization_id_research_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.growth_themes
    ADD CONSTRAINT growth_themes_organization_id_research_id_fkey FOREIGN KEY (organization_id, research_id) REFERENCES __PLANEBYTE_SCHEMA__.growth_research(organization_id, id);

-- growth_watchlists growth_watchlists_organization_id_monitor_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.growth_watchlists
    ADD CONSTRAINT growth_watchlists_organization_id_monitor_id_fkey FOREIGN KEY (organization_id, monitor_id) REFERENCES __PLANEBYTE_SCHEMA__.intent_monitors(organization_id, id);

-- icp_ai_proposals icp_ai_proposals_created_by_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.icp_ai_proposals
    ADD CONSTRAINT icp_ai_proposals_created_by_fkey FOREIGN KEY (created_by) REFERENCES __PLANEBYTE_SCHEMA__.users(id);

-- icp_ai_proposals icp_ai_proposals_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.icp_ai_proposals
    ADD CONSTRAINT icp_ai_proposals_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- icp_versions icp_versions_changed_by_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.icp_versions
    ADD CONSTRAINT icp_versions_changed_by_fkey FOREIGN KEY (changed_by) REFERENCES __PLANEBYTE_SCHEMA__.users(id);

-- icp_versions icp_versions_icp_id_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.icp_versions
    ADD CONSTRAINT icp_versions_icp_id_organization_id_fkey FOREIGN KEY (icp_id, organization_id) REFERENCES __PLANEBYTE_SCHEMA__.ideal_customer_profiles(id, organization_id);

-- ideal_customer_profiles ideal_customer_profiles_created_by_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.ideal_customer_profiles
    ADD CONSTRAINT ideal_customer_profiles_created_by_fkey FOREIGN KEY (created_by) REFERENCES __PLANEBYTE_SCHEMA__.users(id);

-- ideal_customer_profiles ideal_customer_profiles_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.ideal_customer_profiles
    ADD CONSTRAINT ideal_customer_profiles_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- ideal_customer_profiles ideal_customer_profiles_updated_by_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.ideal_customer_profiles
    ADD CONSTRAINT ideal_customer_profiles_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES __PLANEBYTE_SCHEMA__.users(id);

-- integration_oauth_states integration_oauth_states_actor_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.integration_oauth_states
    ADD CONSTRAINT integration_oauth_states_actor_fkey FOREIGN KEY (actor) REFERENCES __PLANEBYTE_SCHEMA__.users(id);

-- integration_oauth_states integration_oauth_states_connection_id_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.integration_oauth_states
    ADD CONSTRAINT integration_oauth_states_connection_id_organization_id_fkey FOREIGN KEY (connection_id, organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organization_integrations(id, organization_id);

-- intelligence_job_items intelligence_job_items_job_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intelligence_job_items
    ADD CONSTRAINT intelligence_job_items_job_id_fkey FOREIGN KEY (job_id) REFERENCES __PLANEBYTE_SCHEMA__.intelligence_jobs(id);

-- intelligence_jobs intelligence_jobs_created_by_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intelligence_jobs
    ADD CONSTRAINT intelligence_jobs_created_by_fkey FOREIGN KEY (created_by) REFERENCES __PLANEBYTE_SCHEMA__.users(id);

-- intelligence_jobs intelligence_jobs_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intelligence_jobs
    ADD CONSTRAINT intelligence_jobs_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- intent_alerts intent_alerts_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_alerts
    ADD CONSTRAINT intent_alerts_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- intent_alerts intent_alerts_organization_id_monitor_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_alerts
    ADD CONSTRAINT intent_alerts_organization_id_monitor_id_fkey FOREIGN KEY (organization_id, monitor_id) REFERENCES __PLANEBYTE_SCHEMA__.intent_monitors(organization_id, id);

-- intent_alerts intent_alerts_organization_id_signal_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_alerts
    ADD CONSTRAINT intent_alerts_organization_id_signal_id_fkey FOREIGN KEY (organization_id, signal_id) REFERENCES __PLANEBYTE_SCHEMA__.intent_signals(organization_id, id);

-- intent_analyses intent_analyses_organization_id_icp_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_analyses
    ADD CONSTRAINT intent_analyses_organization_id_icp_id_fkey FOREIGN KEY (organization_id, icp_id) REFERENCES __PLANEBYTE_SCHEMA__.ideal_customer_profiles(organization_id, id);

-- intent_analyses intent_analyses_organization_id_signal_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_analyses
    ADD CONSTRAINT intent_analyses_organization_id_signal_id_fkey FOREIGN KEY (organization_id, signal_id) REFERENCES __PLANEBYTE_SCHEMA__.intent_signals(organization_id, id);

-- intent_analysis_usage intent_analysis_usage_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_analysis_usage
    ADD CONSTRAINT intent_analysis_usage_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- intent_collection_cursors intent_collection_cursors_organization_id_monitor_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_collection_cursors
    ADD CONSTRAINT intent_collection_cursors_organization_id_monitor_id_fkey FOREIGN KEY (organization_id, monitor_id) REFERENCES __PLANEBYTE_SCHEMA__.intent_monitors(organization_id, id);

-- intent_discoveries intent_discoveries_created_by_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_discoveries
    ADD CONSTRAINT intent_discoveries_created_by_fkey FOREIGN KEY (created_by) REFERENCES __PLANEBYTE_SCHEMA__.users(id);

-- intent_discoveries intent_discoveries_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_discoveries
    ADD CONSTRAINT intent_discoveries_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- intent_discoveries intent_discoveries_organization_id_monitor_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_discoveries
    ADD CONSTRAINT intent_discoveries_organization_id_monitor_id_fkey FOREIGN KEY (organization_id, monitor_id) REFERENCES __PLANEBYTE_SCHEMA__.intent_monitors(organization_id, id);

-- intent_feedback intent_feedback_actor_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_feedback
    ADD CONSTRAINT intent_feedback_actor_fkey FOREIGN KEY (actor) REFERENCES __PLANEBYTE_SCHEMA__.users(id);

-- intent_feedback intent_feedback_organization_id_signal_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_feedback
    ADD CONSTRAINT intent_feedback_organization_id_signal_id_fkey FOREIGN KEY (organization_id, signal_id) REFERENCES __PLANEBYTE_SCHEMA__.intent_signals(organization_id, id);

-- intent_monitor_signals intent_monitor_signals_organization_id_monitor_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_monitor_signals
    ADD CONSTRAINT intent_monitor_signals_organization_id_monitor_id_fkey FOREIGN KEY (organization_id, monitor_id) REFERENCES __PLANEBYTE_SCHEMA__.intent_monitors(organization_id, id);

-- intent_monitor_signals intent_monitor_signals_organization_id_signal_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_monitor_signals
    ADD CONSTRAINT intent_monitor_signals_organization_id_signal_id_fkey FOREIGN KEY (organization_id, signal_id) REFERENCES __PLANEBYTE_SCHEMA__.intent_signals(organization_id, id);

-- intent_monitors intent_monitors_created_by_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_monitors
    ADD CONSTRAINT intent_monitors_created_by_fkey FOREIGN KEY (created_by) REFERENCES __PLANEBYTE_SCHEMA__.users(id);

-- intent_monitors intent_monitors_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_monitors
    ADD CONSTRAINT intent_monitors_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- intent_opportunities intent_opportunities_assigned_to_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_opportunities
    ADD CONSTRAINT intent_opportunities_assigned_to_fkey FOREIGN KEY (assigned_to) REFERENCES __PLANEBYTE_SCHEMA__.users(id);

-- intent_opportunities intent_opportunities_created_by_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_opportunities
    ADD CONSTRAINT intent_opportunities_created_by_fkey FOREIGN KEY (created_by) REFERENCES __PLANEBYTE_SCHEMA__.users(id);

-- intent_opportunities intent_opportunities_organization_id_signal_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_opportunities
    ADD CONSTRAINT intent_opportunities_organization_id_signal_id_fkey FOREIGN KEY (organization_id, signal_id) REFERENCES __PLANEBYTE_SCHEMA__.intent_signals(organization_id, id);

-- intent_preferences intent_preferences_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_preferences
    ADD CONSTRAINT intent_preferences_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- intent_rankings intent_rankings_organization_id_icp_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_rankings
    ADD CONSTRAINT intent_rankings_organization_id_icp_id_fkey FOREIGN KEY (organization_id, icp_id) REFERENCES __PLANEBYTE_SCHEMA__.ideal_customer_profiles(organization_id, id);

-- intent_rankings intent_rankings_organization_id_signal_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_rankings
    ADD CONSTRAINT intent_rankings_organization_id_signal_id_fkey FOREIGN KEY (organization_id, signal_id) REFERENCES __PLANEBYTE_SCHEMA__.intent_signals(organization_id, id);

-- intent_retention_cursors intent_retention_cursors_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_retention_cursors
    ADD CONSTRAINT intent_retention_cursors_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- intent_saved_signals intent_saved_signals_organization_id_signal_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_saved_signals
    ADD CONSTRAINT intent_saved_signals_organization_id_signal_id_fkey FOREIGN KEY (organization_id, signal_id) REFERENCES __PLANEBYTE_SCHEMA__.intent_signals(organization_id, id);

-- intent_saved_signals intent_saved_signals_saved_by_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_saved_signals
    ADD CONSTRAINT intent_saved_signals_saved_by_fkey FOREIGN KEY (saved_by) REFERENCES __PLANEBYTE_SCHEMA__.users(id);

-- intent_signals intent_signals_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_signals
    ADD CONSTRAINT intent_signals_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- intent_source_cache intent_source_cache_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_source_cache
    ADD CONSTRAINT intent_source_cache_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- intent_source_configs intent_source_configs_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_source_configs
    ADD CONSTRAINT intent_source_configs_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- intent_source_runs intent_source_runs_organization_id_discovery_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_source_runs
    ADD CONSTRAINT intent_source_runs_organization_id_discovery_id_fkey FOREIGN KEY (organization_id, discovery_id) REFERENCES __PLANEBYTE_SCHEMA__.intent_discoveries(organization_id, id);

-- intent_source_usage intent_source_usage_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.intent_source_usage
    ADD CONSTRAINT intent_source_usage_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- launch_trial_claims launch_trial_claims_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.launch_trial_claims
    ADD CONSTRAINT launch_trial_claims_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- launch_trial_claims launch_trial_claims_user_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.launch_trial_claims
    ADD CONSTRAINT launch_trial_claims_user_id_fkey FOREIGN KEY (user_id) REFERENCES __PLANEBYTE_SCHEMA__.users(id);

-- organization_ai_usage organization_ai_usage_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.organization_ai_usage
    ADD CONSTRAINT organization_ai_usage_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- organization_domains organization_domains_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.organization_domains
    ADD CONSTRAINT organization_domains_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- organization_integrations organization_integrations_connected_by_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.organization_integrations
    ADD CONSTRAINT organization_integrations_connected_by_fkey FOREIGN KEY (connected_by) REFERENCES __PLANEBYTE_SCHEMA__.users(id);

-- organization_integrations organization_integrations_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.organization_integrations
    ADD CONSTRAINT organization_integrations_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- organization_memberships organization_memberships_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.organization_memberships
    ADD CONSTRAINT organization_memberships_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- organization_memberships organization_memberships_user_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.organization_memberships
    ADD CONSTRAINT organization_memberships_user_id_fkey FOREIGN KEY (user_id) REFERENCES __PLANEBYTE_SCHEMA__.users(id);

-- organization_onboarding organization_onboarding_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.organization_onboarding
    ADD CONSTRAINT organization_onboarding_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- organization_products organization_products_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.organization_products
    ADD CONSTRAINT organization_products_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- organization_profile_job_events organization_profile_job_events_organization_id_job_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.organization_profile_job_events
    ADD CONSTRAINT organization_profile_job_events_organization_id_job_id_fkey FOREIGN KEY (organization_id, job_id) REFERENCES __PLANEBYTE_SCHEMA__.organization_profile_jobs(organization_id, id);

-- organization_profile_jobs organization_profile_jobs_created_by_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.organization_profile_jobs
    ADD CONSTRAINT organization_profile_jobs_created_by_fkey FOREIGN KEY (created_by) REFERENCES __PLANEBYTE_SCHEMA__.users(id);

-- organization_profile_jobs organization_profile_jobs_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.organization_profile_jobs
    ADD CONSTRAINT organization_profile_jobs_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- organization_profile_sources organization_profile_sources_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.organization_profile_sources
    ADD CONSTRAINT organization_profile_sources_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- organization_profiles organization_profiles_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.organization_profiles
    ADD CONSTRAINT organization_profiles_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- organization_services organization_services_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.organization_services
    ADD CONSTRAINT organization_services_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- organization_settings organization_settings_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.organization_settings
    ADD CONSTRAINT organization_settings_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- organization_setup organization_setup_default_icp_id_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.organization_setup
    ADD CONSTRAINT organization_setup_default_icp_id_organization_id_fkey FOREIGN KEY (default_icp_id, organization_id) REFERENCES __PLANEBYTE_SCHEMA__.ideal_customer_profiles(id, organization_id);

-- organization_setup organization_setup_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.organization_setup
    ADD CONSTRAINT organization_setup_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- organization_setup organization_setup_updated_by_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.organization_setup
    ADD CONSTRAINT organization_setup_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES __PLANEBYTE_SCHEMA__.users(id);

-- organizations organizations_created_by_user_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.organizations
    ADD CONSTRAINT organizations_created_by_user_id_fkey FOREIGN KEY (created_by_user_id) REFERENCES __PLANEBYTE_SCHEMA__.users(id);

-- payu_access_callback_events payu_access_callback_events_order_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.payu_access_callback_events
    ADD CONSTRAINT payu_access_callback_events_order_id_fkey FOREIGN KEY (order_id) REFERENCES __PLANEBYTE_SCHEMA__.payu_access_orders(id);

-- payu_access_orders payu_access_orders_created_by_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.payu_access_orders
    ADD CONSTRAINT payu_access_orders_created_by_fkey FOREIGN KEY (created_by) REFERENCES __PLANEBYTE_SCHEMA__.users(id);

-- payu_access_orders payu_access_orders_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.payu_access_orders
    ADD CONSTRAINT payu_access_orders_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- payu_access_refunds payu_access_refunds_order_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.payu_access_refunds
    ADD CONSTRAINT payu_access_refunds_order_id_fkey FOREIGN KEY (order_id) REFERENCES __PLANEBYTE_SCHEMA__.payu_access_orders(id);

-- payu_access_refunds payu_access_refunds_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.payu_access_refunds
    ADD CONSTRAINT payu_access_refunds_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- payu_access_refunds payu_access_refunds_requested_by_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.payu_access_refunds
    ADD CONSTRAINT payu_access_refunds_requested_by_fkey FOREIGN KEY (requested_by) REFERENCES __PLANEBYTE_SCHEMA__.users(id);

-- payu_refund_observations payu_refund_observations_order_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.payu_refund_observations
    ADD CONSTRAINT payu_refund_observations_order_id_fkey FOREIGN KEY (order_id) REFERENCES __PLANEBYTE_SCHEMA__.payu_access_orders(id);

-- payu_refund_observations payu_refund_observations_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.payu_refund_observations
    ADD CONSTRAINT payu_refund_observations_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- pipeline_runs pipeline_runs_campaign_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.pipeline_runs
    ADD CONSTRAINT pipeline_runs_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES __PLANEBYTE_SCHEMA__.scan_campaigns(id);

-- pipeline_runs pipeline_runs_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.pipeline_runs
    ADD CONSTRAINT pipeline_runs_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- prospects prospects_assigned_to_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.prospects
    ADD CONSTRAINT prospects_assigned_to_fkey FOREIGN KEY (assigned_to) REFERENCES __PLANEBYTE_SCHEMA__.users(id);

-- prospects prospects_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.prospects
    ADD CONSTRAINT prospects_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- scan_campaigns scan_campaigns_email_account_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.scan_campaigns
    ADD CONSTRAINT scan_campaigns_email_account_id_fkey FOREIGN KEY (email_account_id) REFERENCES __PLANEBYTE_SCHEMA__.email_accounts(id);

-- scan_campaigns scan_campaigns_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.scan_campaigns
    ADD CONSTRAINT scan_campaigns_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- shared_settings shared_settings_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.shared_settings
    ADD CONSTRAINT shared_settings_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- transactional_notification_events transactional_notification_events_notification_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.transactional_notification_events
    ADD CONSTRAINT transactional_notification_events_notification_id_fkey FOREIGN KEY (notification_id) REFERENCES __PLANEBYTE_SCHEMA__.transactional_notifications(id);

-- transactional_notifications transactional_notifications_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.transactional_notifications
    ADD CONSTRAINT transactional_notifications_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- user_profiles user_profiles_active_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.user_profiles
    ADD CONSTRAINT user_profiles_active_organization_id_fkey FOREIGN KEY (active_organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- user_profiles user_profiles_user_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.user_profiles
    ADD CONSTRAINT user_profiles_user_id_fkey FOREIGN KEY (user_id) REFERENCES __PLANEBYTE_SCHEMA__.users(id);

-- webhook_deliveries webhook_deliveries_endpoint_id_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.webhook_deliveries
    ADD CONSTRAINT webhook_deliveries_endpoint_id_organization_id_fkey FOREIGN KEY (endpoint_id, organization_id) REFERENCES __PLANEBYTE_SCHEMA__.webhook_endpoints(id, organization_id);

-- webhook_delivery_attempts webhook_delivery_attempts_delivery_id_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.webhook_delivery_attempts
    ADD CONSTRAINT webhook_delivery_attempts_delivery_id_organization_id_fkey FOREIGN KEY (delivery_id, organization_id) REFERENCES __PLANEBYTE_SCHEMA__.webhook_deliveries(id, organization_id);

-- webhook_endpoints webhook_endpoints_created_by_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.webhook_endpoints
    ADD CONSTRAINT webhook_endpoints_created_by_fkey FOREIGN KEY (created_by) REFERENCES __PLANEBYTE_SCHEMA__.users(id);

-- webhook_endpoints webhook_endpoints_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.webhook_endpoints
    ADD CONSTRAINT webhook_endpoints_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- workspace_api_keys workspace_api_keys_created_by_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.workspace_api_keys
    ADD CONSTRAINT workspace_api_keys_created_by_fkey FOREIGN KEY (created_by) REFERENCES __PLANEBYTE_SCHEMA__.users(id);

-- workspace_api_keys workspace_api_keys_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.workspace_api_keys
    ADD CONSTRAINT workspace_api_keys_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- workspace_api_keys workspace_api_keys_rotated_from_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.workspace_api_keys
    ADD CONSTRAINT workspace_api_keys_rotated_from_fkey FOREIGN KEY (rotated_from) REFERENCES __PLANEBYTE_SCHEMA__.workspace_api_keys(id);

-- workspace_creation_requests workspace_creation_requests_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.workspace_creation_requests
    ADD CONSTRAINT workspace_creation_requests_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- workspace_creation_requests workspace_creation_requests_user_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.workspace_creation_requests
    ADD CONSTRAINT workspace_creation_requests_user_id_fkey FOREIGN KEY (user_id) REFERENCES __PLANEBYTE_SCHEMA__.users(id);

-- workspace_invitations workspace_invitations_invited_by_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.workspace_invitations
    ADD CONSTRAINT workspace_invitations_invited_by_fkey FOREIGN KEY (invited_by) REFERENCES __PLANEBYTE_SCHEMA__.users(id);

-- workspace_invitations workspace_invitations_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.workspace_invitations
    ADD CONSTRAINT workspace_invitations_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- workspace_notifications workspace_notifications_organization_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.workspace_notifications
    ADD CONSTRAINT workspace_notifications_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES __PLANEBYTE_SCHEMA__.organizations(id);

-- workspace_notifications workspace_notifications_user_id_fkey; Type: FK CONSTRAINT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.workspace_notifications
    ADD CONSTRAINT workspace_notifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES __PLANEBYTE_SCHEMA__.users(id);
