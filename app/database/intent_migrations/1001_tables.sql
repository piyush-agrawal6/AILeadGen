-- Clean Intent Radar + Growth baseline; structure only, no customer seeds.
-- access_period_reservations; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.access_period_reservations (
    organization_id text NOT NULL,
    contract_id text NOT NULL,
    period_start bigint NOT NULL,
    operation_id text NOT NULL,
    dimension text NOT NULL,
    amount bigint NOT NULL,
    state text NOT NULL,
    actual_amount bigint,
    created_at text NOT NULL,
    updated_at text NOT NULL,
    CONSTRAINT access_period_reservations_amount_check CHECK ((amount > 0)),
    CONSTRAINT access_period_reservations_check CHECK (((actual_amount >= 0) AND (actual_amount <= amount))),
    CONSTRAINT access_period_reservations_state_check CHECK ((state = ANY (ARRAY['RESERVED'::text, 'COMMITTED'::text, 'RELEASED'::text])))
);

-- access_period_usage; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.access_period_usage (
    organization_id text NOT NULL,
    contract_id text NOT NULL,
    period_start bigint NOT NULL,
    period_end bigint NOT NULL,
    dimension text NOT NULL,
    reserved bigint DEFAULT 0 NOT NULL,
    used bigint DEFAULT 0 NOT NULL,
    CONSTRAINT access_period_usage_reserved_check CHECK ((reserved >= 0)),
    CONSTRAINT access_period_usage_used_check CHECK ((used >= 0))
);

-- access_periods; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.access_periods (
    id text NOT NULL,
    organization_id text NOT NULL,
    source_kind text NOT NULL,
    source_id text NOT NULL,
    plan_code text NOT NULL,
    plan_json text NOT NULL,
    status text NOT NULL,
    paid_start bigint NOT NULL,
    paid_end bigint NOT NULL,
    verified_at text NOT NULL,
    mode text NOT NULL,
    created_at text NOT NULL,
    updated_at text NOT NULL,
    CONSTRAINT access_periods_check CHECK ((paid_end > paid_start)),
    CONSTRAINT access_periods_mode_check CHECK ((mode = ANY (ARRAY['trial'::text, 'test'::text, 'live'::text]))),
    CONSTRAINT access_periods_source_kind_check CHECK ((source_kind = ANY (ARRAY['TRIAL'::text, 'PAYMENT'::text]))),
    CONSTRAINT access_periods_status_check CHECK ((status = ANY (ARRAY['ACTIVE'::text, 'EXPIRED'::text, 'REVOKED'::text, 'REPLACED'::text])))
);

-- account_admissions; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.account_admissions (
    user_id text NOT NULL,
    google_subject text NOT NULL,
    status text NOT NULL,
    terms_version text NOT NULL,
    created_at text NOT NULL,
    updated_at text NOT NULL,
    CONSTRAINT account_admissions_status_check CHECK ((status = ANY (ARRAY['ACTIVE'::text, 'SUSPENDED'::text, 'CLOSED'::text])))
);

-- account_link_tickets; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.account_link_tickets (
    id text NOT NULL,
    user_id text NOT NULL,
    session_id text NOT NULL,
    token_hash text NOT NULL,
    expires_at bigint NOT NULL,
    consumed_at text,
    created_at text NOT NULL
);

-- account_login_tickets; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.account_login_tickets (
    id text NOT NULL,
    user_id text NOT NULL,
    token_hash text NOT NULL,
    expires_at bigint NOT NULL,
    consumed_at text,
    created_at text NOT NULL
);

-- account_privacy_requests; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.account_privacy_requests (
    id text NOT NULL,
    user_id text NOT NULL,
    request_id text NOT NULL,
    kind text NOT NULL,
    status text NOT NULL,
    verified_session_id text NOT NULL,
    policy_version text NOT NULL,
    created_at text NOT NULL,
    updated_at text NOT NULL,
    closure_verified_at bigint,
    ordinary_data_due_at bigint,
    backup_target_at bigint,
    completed_at text,
    resolution_reference text,
    CONSTRAINT account_privacy_requests_check CHECK (((ordinary_data_due_at IS NULL) OR (ordinary_data_due_at = (closure_verified_at + 2592000)))),
    CONSTRAINT account_privacy_requests_check1 CHECK (((backup_target_at IS NULL) OR (backup_target_at = (closure_verified_at + 7776000)))),
    CONSTRAINT account_privacy_requests_kind_check CHECK ((kind = ANY (ARRAY['EXPORT'::text, 'CLOSE_AND_DELETE'::text, 'ERASURE'::text]))),
    CONSTRAINT account_privacy_requests_status_check CHECK ((status = ANY (ARRAY['REQUESTED'::text, 'REVIEW'::text, 'AWAITING_INFORMATION'::text, 'VERIFIED_CLOSURE'::text, 'COMPLETED'::text, 'REJECTED'::text])))
);

-- account_rate_limits; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.account_rate_limits (
    kind text NOT NULL,
    bucket_hash text NOT NULL,
    window_start bigint NOT NULL,
    used integer DEFAULT 0 NOT NULL,
    CONSTRAINT account_rate_limits_used_check CHECK ((used >= 0))
);

-- account_recovery_requests; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.account_recovery_requests (
    id text NOT NULL,
    email text,
    email_hash text NOT NULL,
    request_id text NOT NULL,
    status text NOT NULL,
    expires_at bigint NOT NULL,
    created_at text NOT NULL,
    processed_at text,
    CONSTRAINT account_recovery_requests_status_check CHECK ((status = ANY (ARRAY['QUEUED'::text, 'PROCESSED'::text, 'EXPIRED'::text])))
);

-- account_recovery_tokens; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.account_recovery_tokens (
    id text NOT NULL,
    user_id text NOT NULL,
    token_hash text NOT NULL,
    request_id text NOT NULL,
    expires_at bigint NOT NULL,
    consumed_at text,
    created_at text NOT NULL
);

-- account_roles; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.account_roles (
    email text NOT NULL,
    role text NOT NULL,
    updated_at text NOT NULL,
    updated_by text NOT NULL
);

-- account_security_events; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.account_security_events (
    id text NOT NULL,
    account_hash text NOT NULL,
    action text NOT NULL,
    result text NOT NULL,
    created_at text NOT NULL
);

-- account_terms_acceptances; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.account_terms_acceptances (
    nonce text NOT NULL,
    user_id text NOT NULL,
    terms_version text NOT NULL,
    accepted_at text NOT NULL,
    recorded_at text NOT NULL
);

-- account_verifications; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.account_verifications (
    id text NOT NULL,
    email text NOT NULL,
    purpose text NOT NULL,
    capability_hash text NOT NULL,
    code_hash text NOT NULL,
    payload_json text NOT NULL,
    request_id text NOT NULL,
    request_fingerprint text NOT NULL,
    attempts integer DEFAULT 0 NOT NULL,
    expires_at bigint NOT NULL,
    consumed_at text,
    invalidated_at text,
    created_at text NOT NULL,
    CONSTRAINT account_verifications_attempts_check CHECK (((attempts >= 0) AND (attempts <= 5))),
    CONSTRAINT account_verifications_purpose_check CHECK ((purpose = ANY (ARRAY['SIGNUP'::text, 'SET_PASSWORD'::text])))
);

-- acquisition_ai_cache; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.acquisition_ai_cache (
    fingerprint text NOT NULL,
    actor text NOT NULL,
    task text NOT NULL,
    result_json text NOT NULL,
    expires_at text NOT NULL,
    created_at text NOT NULL,
    organization_id text
);

-- acquisition_provider_health; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.acquisition_provider_health (
    provider text NOT NULL,
    status text NOT NULL,
    checked_at text NOT NULL,
    error_code text
);

-- ai_request_usage; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.ai_request_usage (
    id text NOT NULL,
    organization_id text NOT NULL,
    actor text NOT NULL,
    operation text NOT NULL,
    provider text NOT NULL,
    model text NOT NULL,
    status text NOT NULL,
    input_tokens integer,
    output_tokens integer,
    cached_tokens integer,
    thinking_tokens integer,
    usage_basis text NOT NULL,
    estimated_cost_usd text,
    pricing_reference text,
    fallback integer DEFAULT 0 NOT NULL,
    duration_ms integer NOT NULL,
    created_at text NOT NULL
);

-- artifact_objects; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.artifact_objects (
    object_key text NOT NULL,
    run_id integer,
    business_id integer,
    kind text NOT NULL,
    content_type text NOT NULL,
    created_at text NOT NULL
);

-- audit_log; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.audit_log (
    id text NOT NULL,
    actor text NOT NULL,
    action text NOT NULL,
    entity text NOT NULL,
    result text NOT NULL,
    details_json text DEFAULT '{}'::text NOT NULL,
    created_at text NOT NULL,
    organization_id text
);

-- billing_action_windows; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.billing_action_windows (
    organization_id text NOT NULL,
    action text NOT NULL,
    window_start bigint NOT NULL,
    requests integer NOT NULL
);

-- billing_customers; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.billing_customers (
    organization_id text NOT NULL,
    mode text NOT NULL,
    provider_id text NOT NULL,
    created_at text NOT NULL
);

-- billing_payments; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.billing_payments (
    mode text NOT NULL,
    provider_id text NOT NULL,
    organization_id text NOT NULL,
    subscription_id text NOT NULL,
    invoice_id text NOT NULL,
    amount bigint NOT NULL,
    currency text NOT NULL,
    status text NOT NULL,
    period_start bigint NOT NULL,
    period_end bigint NOT NULL,
    recorded_at text NOT NULL
);

-- billing_plan_mappings; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.billing_plan_mappings (
    mode text NOT NULL,
    code text NOT NULL,
    provider_plan_id text NOT NULL,
    catalog_hash text NOT NULL,
    verified_at text NOT NULL,
    CONSTRAINT billing_plan_mappings_mode_check CHECK ((mode = ANY (ARRAY['test'::text, 'live'::text])))
);

-- billing_reservations; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.billing_reservations (
    organization_id text NOT NULL,
    dimension text NOT NULL,
    request_id text NOT NULL,
    subscription_id text NOT NULL,
    period_start bigint NOT NULL,
    amount bigint NOT NULL,
    created_at text NOT NULL,
    CONSTRAINT billing_reservations_amount_check CHECK ((amount > 0))
);

-- billing_subscriptions; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.billing_subscriptions (
    id text NOT NULL,
    organization_id text NOT NULL,
    created_by text NOT NULL,
    mode text NOT NULL,
    request_id text NOT NULL,
    plan_code text NOT NULL,
    plan_json text NOT NULL,
    provider_id text,
    customer_id text,
    status text DEFAULT 'CREATING'::text NOT NULL,
    current_start bigint,
    current_end bigint,
    paid_start bigint,
    paid_end bigint,
    cancel_at_cycle_end integer DEFAULT 0 NOT NULL,
    last_reconciled_at text,
    next_reconcile_at text NOT NULL,
    failures integer DEFAULT 0 NOT NULL,
    created_at text NOT NULL,
    updated_at text NOT NULL,
    CONSTRAINT billing_subscriptions_mode_check CHECK ((mode = ANY (ARRAY['test'::text, 'live'::text])))
);

-- billing_usage; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.billing_usage (
    organization_id text NOT NULL,
    subscription_id text NOT NULL,
    period_start bigint NOT NULL,
    period_end bigint NOT NULL,
    dimension text NOT NULL,
    used bigint DEFAULT 0 NOT NULL,
    CONSTRAINT billing_usage_used_check CHECK ((used >= 0))
);

-- billing_webhook_events; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.billing_webhook_events (
    mode text NOT NULL,
    event_id text NOT NULL,
    body_hash text NOT NULL,
    event_type text NOT NULL,
    provider_subscription_id text NOT NULL,
    status text DEFAULT 'PENDING'::text NOT NULL,
    attempts integer DEFAULT 0 NOT NULL,
    lease_token text,
    lease_until text,
    next_attempt_at text NOT NULL,
    received_at text NOT NULL,
    processed_at text,
    error_code text
);

-- billing_workspace_slots; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.billing_workspace_slots (
    organization_id text NOT NULL,
    mode text NOT NULL,
    subscription_id text NOT NULL
);

-- businesses; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.businesses (
    id bigint NOT NULL,
    external_overture_id text,
    external_osm_id text,
    name text NOT NULL,
    normalized_name text NOT NULL,
    vertical text NOT NULL,
    subcategory text,
    country text,
    country_code text,
    state text,
    city text,
    postcode text,
    address text,
    latitude real,
    longitude real,
    phone text,
    normalized_phone text,
    website text,
    domain text,
    public_email text,
    instagram text,
    facebook text,
    linkedin text,
    x_url text,
    source_overture integer DEFAULT 0,
    source_osm integer DEFAULT 0,
    source_confidence real DEFAULT 0.5,
    operating_status text DEFAULT 'active'::text,
    is_chain integer DEFAULT 0,
    is_duplicate integer DEFAULT 0,
    is_rejected integer DEFAULT 0,
    rejection_reason text,
    processing_status text DEFAULT 'DISCOVERED'::text,
    created_at text DEFAULT (CURRENT_TIMESTAMP)::text,
    updated_at text DEFAULT (CURRENT_TIMESTAMP)::text,
    source_category text,
    source_tags_json text,
    vertical_validation_status text DEFAULT 'VALID'::text,
    vertical_validation_reason text,
    vertical_validation_confidence real DEFAULT 1.0,
    chain_reason text,
    chain_confidence real DEFAULT 0.0,
    website_status text,
    run_id integer,
    prospect_id text
);

-- businesses_id_seq; Type: SEQUENCE; Schema: configured target; Owner: -
CREATE SEQUENCE __PLANEBYTE_SCHEMA__.businesses_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- businesses_id_seq; Type: SEQUENCE OWNED BY; Schema: configured target; Owner: -
ALTER SEQUENCE __PLANEBYTE_SCHEMA__.businesses_id_seq OWNED BY __PLANEBYTE_SCHEMA__.businesses.id;

-- commercial_contracts; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.commercial_contracts (
    id text NOT NULL,
    organization_id text NOT NULL,
    provider text NOT NULL,
    mode text NOT NULL,
    provider_subscription_id text NOT NULL,
    plan_code text NOT NULL,
    catalog_version text NOT NULL,
    plan_json text NOT NULL,
    status text NOT NULL,
    mandate_verified integer DEFAULT 0 NOT NULL,
    paid_start bigint,
    paid_end bigint,
    verified_at text,
    created_at text NOT NULL,
    updated_at text NOT NULL,
    CONSTRAINT commercial_contracts_check CHECK ((((paid_start IS NULL) AND (paid_end IS NULL)) OR ((paid_start IS NOT NULL) AND (paid_end IS NOT NULL) AND (paid_end > paid_start)))),
    CONSTRAINT commercial_contracts_mandate_verified_check CHECK ((mandate_verified = ANY (ARRAY[0, 1]))),
    CONSTRAINT commercial_contracts_mode_check CHECK ((mode = ANY (ARRAY['test'::text, 'live'::text]))),
    CONSTRAINT commercial_contracts_provider_check CHECK ((provider = 'payu'::text)),
    CONSTRAINT commercial_contracts_status_check CHECK ((status = ANY (ARRAY['PENDING'::text, 'ACTIVE'::text, 'PAST_DUE'::text, 'CANCELLED'::text, 'COMPLETED'::text, 'REVIEW'::text])))
);

-- commercial_reservations; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.commercial_reservations (
    organization_id text NOT NULL,
    contract_id text NOT NULL,
    period_start bigint NOT NULL,
    operation_id text NOT NULL,
    dimension text NOT NULL,
    amount bigint NOT NULL,
    state text NOT NULL,
    actual_amount bigint,
    created_at text NOT NULL,
    updated_at text NOT NULL,
    CONSTRAINT commercial_reservations_amount_check CHECK ((amount > 0)),
    CONSTRAINT commercial_reservations_check CHECK (((actual_amount >= 0) AND (actual_amount <= amount))),
    CONSTRAINT commercial_reservations_state_check CHECK ((state = ANY (ARRAY['RESERVED'::text, 'COMMITTED'::text, 'RELEASED'::text])))
);

-- commercial_usage; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.commercial_usage (
    organization_id text NOT NULL,
    contract_id text NOT NULL,
    period_start bigint NOT NULL,
    period_end bigint NOT NULL,
    dimension text NOT NULL,
    reserved bigint DEFAULT 0 NOT NULL,
    used bigint DEFAULT 0 NOT NULL,
    CONSTRAINT commercial_usage_reserved_check CHECK ((reserved >= 0)),
    CONSTRAINT commercial_usage_used_check CHECK ((used >= 0))
);

-- commercial_workspace_slots; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.commercial_workspace_slots (
    organization_id text NOT NULL,
    mode text NOT NULL,
    contract_id text NOT NULL
);

-- customer_accounts; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.customer_accounts (
    email text NOT NULL,
    user_id text,
    name text NOT NULL,
    company_name text NOT NULL,
    status text NOT NULL,
    password_hash text,
    google_subject text,
    verified_at text,
    terms_version text NOT NULL,
    terms_accepted_at bigint,
    created_at text NOT NULL,
    updated_at text NOT NULL,
    CONSTRAINT customer_accounts_status_check CHECK ((status = ANY (ARRAY['PENDING'::text, 'ACTIVE'::text, 'SUSPENDED'::text, 'CLOSED'::text])))
);

-- customer_sessions; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.customer_sessions (
    id text NOT NULL,
    user_id text NOT NULL,
    token_hash text NOT NULL,
    provider text NOT NULL,
    created_at text NOT NULL,
    expires_at bigint NOT NULL,
    revoked_at text,
    CONSTRAINT customer_sessions_provider_check CHECK ((provider = ANY (ARRAY['PASSWORD'::text, 'GOOGLE'::text])))
);

-- customer_workspace_access; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.customer_workspace_access (
    organization_id text NOT NULL,
    registered_by text NOT NULL,
    created_at text NOT NULL
);

-- developer_action_approvals; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.developer_action_approvals (
    id text NOT NULL,
    organization_id text NOT NULL,
    key_id text NOT NULL,
    requested_by text NOT NULL,
    request_id text NOT NULL,
    fingerprint text NOT NULL,
    kind text NOT NULL,
    payload_json text NOT NULL,
    status text DEFAULT 'PENDING'::text NOT NULL,
    result_json text DEFAULT '{}'::text NOT NULL,
    expires_at text NOT NULL,
    created_at text NOT NULL,
    decided_at text,
    decided_by text
);

-- developer_request_windows; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.developer_request_windows (
    owner_key text NOT NULL,
    window_start integer NOT NULL,
    requests integer NOT NULL
);

-- discovery_searches; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.discovery_searches (
    id text NOT NULL,
    organization_id text NOT NULL,
    name text NOT NULL,
    configuration_json text NOT NULL,
    revision integer DEFAULT 1 NOT NULL,
    request_id text NOT NULL,
    fingerprint text NOT NULL,
    created_by text NOT NULL,
    created_at text NOT NULL,
    updated_at text NOT NULL,
    archived_at text
);

-- email_accounts; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.email_accounts (
    id text NOT NULL,
    user_id text NOT NULL,
    provider text NOT NULL,
    email_address text NOT NULL,
    display_name text NOT NULL,
    status text NOT NULL,
    is_default integer DEFAULT 1 NOT NULL,
    last_sync_at text,
    created_at text NOT NULL,
    updated_at text NOT NULL,
    smtp_health text DEFAULT 'UNKNOWN'::text NOT NULL,
    imap_health text DEFAULT 'UNKNOWN'::text NOT NULL,
    health_checked_at text,
    organization_id text
);

-- growth_company_links; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.growth_company_links (
    organization_id text NOT NULL,
    opportunity_id text NOT NULL,
    business_id bigint NOT NULL,
    created_by text NOT NULL,
    created_at text NOT NULL
);

-- growth_competitors; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.growth_competitors (
    id text NOT NULL,
    organization_id text NOT NULL,
    name text NOT NULL,
    aliases_json text DEFAULT '[]'::text NOT NULL,
    context text DEFAULT ''::text NOT NULL,
    request_id text NOT NULL,
    archived_at text,
    revision integer DEFAULT 1 NOT NULL,
    created_by text NOT NULL,
    created_at text NOT NULL,
    updated_at text NOT NULL
);

-- growth_notes; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.growth_notes (
    id text NOT NULL,
    organization_id text NOT NULL,
    resource_kind text NOT NULL,
    resource_id text NOT NULL,
    author text NOT NULL,
    body text NOT NULL,
    revision integer DEFAULT 1 NOT NULL,
    created_at text NOT NULL,
    updated_at text NOT NULL
);

-- growth_research; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.growth_research (
    id text NOT NULL,
    organization_id text NOT NULL,
    created_by text NOT NULL,
    kind text NOT NULL,
    question text DEFAULT ''::text NOT NULL,
    title text NOT NULL,
    scope_json text NOT NULL,
    snapshot_json text DEFAULT '{}'::text NOT NULL,
    output_json text DEFAULT '{}'::text NOT NULL,
    input_hash text NOT NULL,
    request_id text NOT NULL,
    status text DEFAULT 'QUEUED'::text NOT NULL,
    job_id text,
    saved_at text,
    created_at text NOT NULL,
    updated_at text NOT NULL,
    revision integer DEFAULT 1 NOT NULL
);

-- growth_theme_signals; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.growth_theme_signals (
    organization_id text NOT NULL,
    theme_id text NOT NULL,
    signal_id text NOT NULL
);

-- growth_themes; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.growth_themes (
    id text NOT NULL,
    organization_id text NOT NULL,
    research_id text NOT NULL,
    name text NOT NULL,
    description text NOT NULL,
    method text NOT NULL,
    evidence_json text NOT NULL,
    saved_at text,
    status text DEFAULT 'Active'::text NOT NULL,
    revision integer DEFAULT 1 NOT NULL,
    created_at text NOT NULL,
    updated_at text NOT NULL
);

-- growth_watchlists; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.growth_watchlists (
    organization_id text NOT NULL,
    monitor_id text NOT NULL,
    kind text NOT NULL,
    resource_id text,
    created_at text NOT NULL
);

-- icp_ai_proposals; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.icp_ai_proposals (
    id text NOT NULL,
    organization_id text NOT NULL,
    created_by text NOT NULL,
    source text NOT NULL,
    input_hash text NOT NULL,
    result_json text NOT NULL,
    profile_version text,
    created_at text NOT NULL,
    expires_at text NOT NULL,
    CONSTRAINT icp_ai_proposals_source_check CHECK ((source = ANY (ARRAY['BUSINESS_PROFILE'::text, 'AI_ASSISTED'::text, 'AI_REFINED'::text])))
);

-- icp_versions; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.icp_versions (
    icp_id text NOT NULL,
    organization_id text NOT NULL,
    revision integer NOT NULL,
    snapshot_json text NOT NULL,
    changed_by text NOT NULL,
    created_at text NOT NULL
);

-- ideal_customer_profiles; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.ideal_customer_profiles (
    id text NOT NULL,
    organization_id text NOT NULL,
    name text NOT NULL,
    description text DEFAULT ''::text NOT NULL,
    status text NOT NULL,
    criteria_json text NOT NULL,
    revision integer NOT NULL,
    request_id text NOT NULL,
    creation_fingerprint text NOT NULL,
    created_by text NOT NULL,
    updated_by text NOT NULL,
    created_at text NOT NULL,
    updated_at text NOT NULL,
    generation_source text DEFAULT 'MANUAL'::text NOT NULL,
    generation_metadata_json text DEFAULT '{}'::text NOT NULL,
    CONSTRAINT ideal_customer_profiles_status_check CHECK ((status = ANY (ARRAY['ACTIVE'::text, 'INACTIVE'::text, 'ARCHIVED'::text, 'DELETED'::text])))
);

-- integration_oauth_states; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.integration_oauth_states (
    state_hash text NOT NULL,
    organization_id text NOT NULL,
    connection_id text NOT NULL,
    actor text NOT NULL,
    connection_revision integer NOT NULL,
    verifier_ciphertext text,
    status text NOT NULL,
    expires_at text NOT NULL,
    created_at text NOT NULL,
    requested_scope text DEFAULT 'https://www.googleapis.com/auth/spreadsheets.readonly'::text NOT NULL,
    CONSTRAINT integration_oauth_states_status_check CHECK ((status = ANY (ARRAY['PENDING'::text, 'CONSUMED'::text, 'CANCELLED'::text, 'EXPIRED'::text])))
);

-- intelligence_job_items; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.intelligence_job_items (
    id text NOT NULL,
    job_id text NOT NULL,
    resource_id text NOT NULL,
    status text DEFAULT 'QUEUED'::text NOT NULL,
    result_json text DEFAULT '{}'::text NOT NULL,
    error_code text,
    updated_at text NOT NULL
);

-- intelligence_jobs; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.intelligence_jobs (
    id text NOT NULL,
    organization_id text NOT NULL,
    created_by text NOT NULL,
    kind text NOT NULL,
    status text DEFAULT 'QUEUED'::text NOT NULL,
    request_id text NOT NULL,
    fingerprint text NOT NULL,
    configuration_json text DEFAULT '{}'::text NOT NULL,
    created_at text NOT NULL,
    updated_at text NOT NULL,
    completed_at text,
    lease_owner text,
    lease_until text,
    attempts integer DEFAULT 0 NOT NULL,
    dispatch_attempts integer DEFAULT 0 NOT NULL,
    error_code text,
    execution_name text
);

-- intent_alerts; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.intent_alerts (
    id text NOT NULL,
    organization_id text NOT NULL,
    monitor_id text,
    signal_id text,
    event_key text NOT NULL,
    title text NOT NULL,
    description text NOT NULL,
    read_at text,
    created_at text NOT NULL
);

-- intent_analyses; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.intent_analyses (
    id text NOT NULL,
    organization_id text NOT NULL,
    signal_id text NOT NULL,
    input_hash text NOT NULL,
    icp_id text,
    icp_revision integer,
    analysis_json text NOT NULL,
    created_at text NOT NULL
);

-- intent_analysis_usage; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.intent_analysis_usage (
    organization_id text NOT NULL,
    day text NOT NULL,
    reserved_tokens integer DEFAULT 0 NOT NULL,
    calls integer DEFAULT 0 NOT NULL
);

-- intent_collection_cursors; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.intent_collection_cursors (
    organization_id text NOT NULL,
    monitor_id text NOT NULL,
    provider text NOT NULL,
    configuration_hash text NOT NULL,
    cursor_json text NOT NULL,
    updated_at text NOT NULL
);

-- intent_discoveries; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.intent_discoveries (
    id text NOT NULL,
    organization_id text NOT NULL,
    created_by text NOT NULL,
    monitor_id text,
    configuration_json text NOT NULL,
    created_at text NOT NULL,
    monitor_revision integer
);

-- intent_feedback; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.intent_feedback (
    organization_id text NOT NULL,
    signal_id text NOT NULL,
    actor text NOT NULL,
    label text NOT NULL,
    note text DEFAULT ''::text NOT NULL,
    active integer DEFAULT 1 NOT NULL,
    updated_at text NOT NULL
);

-- intent_monitor_signals; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.intent_monitor_signals (
    organization_id text NOT NULL,
    monitor_id text NOT NULL,
    signal_id text NOT NULL,
    matched_at text NOT NULL
);

-- intent_monitors; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.intent_monitors (
    id text NOT NULL,
    organization_id text NOT NULL,
    created_by text NOT NULL,
    name text NOT NULL,
    description text DEFAULT ''::text NOT NULL,
    goal text DEFAULT ''::text NOT NULL,
    configuration_json text NOT NULL,
    status text DEFAULT 'Draft'::text NOT NULL,
    request_id text NOT NULL,
    fingerprint text NOT NULL,
    revision integer DEFAULT 1 NOT NULL,
    last_checked text,
    last_job_id text,
    created_at text NOT NULL,
    updated_at text NOT NULL,
    schedule_json text DEFAULT '{}'::text NOT NULL,
    next_run_at text,
    CONSTRAINT intent_monitors_status_check CHECK ((status = ANY (ARRAY['Draft'::text, 'Active'::text, 'Paused'::text, 'Archived'::text])))
);

-- intent_opportunities; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.intent_opportunities (
    id text NOT NULL,
    organization_id text NOT NULL,
    signal_id text NOT NULL,
    status text DEFAULT 'New'::text NOT NULL,
    priority text DEFAULT 'Medium'::text NOT NULL,
    notes text DEFAULT ''::text NOT NULL,
    next_action text DEFAULT 'Review context'::text NOT NULL,
    assigned_to text,
    revision integer DEFAULT 1 NOT NULL,
    created_by text NOT NULL,
    created_at text NOT NULL,
    updated_at text NOT NULL
);

-- intent_preferences; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.intent_preferences (
    organization_id text NOT NULL,
    configuration_json text NOT NULL,
    revision integer DEFAULT 1 NOT NULL,
    updated_at text NOT NULL
);

-- intent_provider_limits; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.intent_provider_limits (
    id text NOT NULL,
    next_request_at text NOT NULL,
    state_json text DEFAULT '{}'::text NOT NULL
);

-- intent_rankings; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.intent_rankings (
    organization_id text NOT NULL,
    signal_id text NOT NULL,
    score integer NOT NULL,
    input_hash text NOT NULL,
    icp_id text,
    icp_revision integer,
    explanation_json text NOT NULL,
    updated_at text NOT NULL
);

-- intent_retention_cursors; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.intent_retention_cursors (
    organization_id text NOT NULL,
    signal_after text DEFAULT ''::text NOT NULL,
    cache_after text DEFAULT ''::text NOT NULL,
    updated_at text NOT NULL
);

-- intent_saved_signals; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.intent_saved_signals (
    organization_id text NOT NULL,
    signal_id text NOT NULL,
    collection text DEFAULT 'Inbox'::text NOT NULL,
    tags_json text DEFAULT '[]'::text NOT NULL,
    notes text DEFAULT ''::text NOT NULL,
    saved_by text NOT NULL,
    saved_at text NOT NULL,
    revision integer DEFAULT 1 NOT NULL
);

-- intent_signals; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.intent_signals (
    id text NOT NULL,
    organization_id text NOT NULL,
    source text NOT NULL,
    source_record_id text NOT NULL,
    source_url text NOT NULL,
    title text NOT NULL,
    excerpt text NOT NULL,
    observed_at text NOT NULL,
    retrieved_at text NOT NULL,
    category text NOT NULL,
    score integer NOT NULL,
    evidence_json text NOT NULL,
    status text DEFAULT 'New'::text NOT NULL,
    notes text DEFAULT ''::text NOT NULL,
    available integer DEFAULT 1 NOT NULL,
    revision integer DEFAULT 1 NOT NULL,
    CONSTRAINT intent_signals_score_check CHECK (((score >= 0) AND (score <= 100)))
);

-- intent_source_cache; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.intent_source_cache (
    organization_id text NOT NULL,
    fingerprint text NOT NULL,
    result_json text NOT NULL,
    expires_at text NOT NULL
);

-- intent_source_configs; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.intent_source_configs (
    organization_id text NOT NULL,
    id text NOT NULL,
    configuration_json text NOT NULL,
    updated_at text NOT NULL
);

-- intent_source_runs; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.intent_source_runs (
    organization_id text NOT NULL,
    discovery_id text NOT NULL,
    provider text NOT NULL,
    status text NOT NULL,
    result_json text DEFAULT '{}'::text NOT NULL,
    updated_at text NOT NULL
);

-- intent_source_usage; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.intent_source_usage (
    organization_id text NOT NULL,
    provider text NOT NULL,
    day text NOT NULL,
    reserved_requests integer DEFAULT 0 NOT NULL
);

-- intent_worker_health; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.intent_worker_health (
    worker_id text NOT NULL,
    last_tick_at text NOT NULL,
    state text NOT NULL,
    detail_json text NOT NULL
);

-- internal_request_nonces; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.internal_request_nonces (
    nonce text NOT NULL,
    expires_at integer NOT NULL
);

-- launch_trial_claims; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.launch_trial_claims (
    id text NOT NULL,
    user_id text NOT NULL,
    company_domain text NOT NULL,
    organization_id text NOT NULL,
    policy_version text NOT NULL,
    claimed_at text NOT NULL
);

-- organization_ai_usage; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.organization_ai_usage (
    organization_id text NOT NULL,
    day text NOT NULL,
    feature text NOT NULL,
    requests integer DEFAULT 0 NOT NULL,
    updated_at text NOT NULL
);

-- organization_domains; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.organization_domains (
    id text NOT NULL,
    organization_id text NOT NULL,
    domain text NOT NULL,
    status text NOT NULL,
    challenge_hash text NOT NULL,
    challenge_expires_at text NOT NULL,
    created_at text NOT NULL,
    updated_at text NOT NULL,
    verified_at text,
    checked_at text,
    attempts integer DEFAULT 0 NOT NULL,
    CONSTRAINT organization_domains_status_check CHECK ((status = ANY (ARRAY['PENDING'::text, 'VERIFIED'::text, 'REVOKED'::text])))
);

-- organization_integrations; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.organization_integrations (
    id text NOT NULL,
    organization_id text NOT NULL,
    provider text NOT NULL,
    status text DEFAULT 'NOT_CONNECTED'::text NOT NULL,
    revision integer DEFAULT 1 NOT NULL,
    credentials_ciphertext text,
    scopes_json text DEFAULT '[]'::text NOT NULL,
    connected_by text,
    connected_at text,
    last_success_at text,
    last_error_code text,
    refresh_lease_id text,
    refresh_lease_until text,
    created_at text NOT NULL,
    updated_at text NOT NULL,
    CONSTRAINT organization_integrations_provider_check CHECK ((provider = 'GOOGLE_SHEETS'::text)),
    CONSTRAINT organization_integrations_status_check CHECK ((status = ANY (ARRAY['NOT_CONNECTED'::text, 'CONNECTED'::text, 'REAUTH_REQUIRED'::text, 'DISCONNECTED'::text])))
);

-- organization_memberships; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.organization_memberships (
    id text NOT NULL,
    organization_id text NOT NULL,
    user_id text NOT NULL,
    role text DEFAULT 'MEMBER'::text NOT NULL,
    status text DEFAULT 'ACTIVE'::text NOT NULL,
    created_at text NOT NULL,
    updated_at text NOT NULL,
    CONSTRAINT organization_memberships_role_check CHECK ((role = ANY (ARRAY['OWNER'::text, 'ADMIN'::text, 'MEMBER'::text, 'VIEWER'::text]))),
    CONSTRAINT organization_memberships_status_check CHECK ((status = ANY (ARRAY['ACTIVE'::text, 'INVITED'::text, 'SUSPENDED'::text, 'REVOKED'::text])))
);

-- organization_onboarding; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.organization_onboarding (
    organization_id text NOT NULL,
    status text DEFAULT 'NOT_STARTED'::text NOT NULL,
    current_step text,
    setup_method text,
    website_import_status text,
    website_import_started_at text,
    website_import_completed_at text,
    website_import_error text,
    website_import_preview_json text,
    profile_completed integer DEFAULT 0 NOT NULL,
    services_completed integer DEFAULT 0 NOT NULL,
    audience_completed integer DEFAULT 0 NOT NULL,
    preferences_completed integer DEFAULT 0 NOT NULL,
    completed_at text,
    created_at text NOT NULL,
    updated_at text NOT NULL,
    CONSTRAINT organization_onboarding_setup_method_check CHECK (((setup_method IS NULL) OR (setup_method = ANY (ARRAY['MANUAL'::text, 'WEBSITE_IMPORT'::text, 'MANUAL_AND_WEBSITE'::text, 'SYSTEM_SEEDED'::text])))),
    CONSTRAINT organization_onboarding_status_check CHECK ((status = ANY (ARRAY['NOT_STARTED'::text, 'IN_PROGRESS'::text, 'COMPLETED'::text, 'FAILED'::text])))
);

-- organization_products; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.organization_products (
    organization_id text NOT NULL,
    product text NOT NULL,
    enabled integer DEFAULT 1 NOT NULL,
    created_at text NOT NULL,
    updated_at text NOT NULL,
    CONSTRAINT organization_products_product_check CHECK ((product = ANY (ARRAY['LEADGEN'::text, 'INTENT_RADAR'::text, 'SEARCH_VISIBILITY'::text])))
);

-- organization_profile_job_events; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.organization_profile_job_events (
    id text NOT NULL,
    organization_id text NOT NULL,
    job_id text NOT NULL,
    attempt integer NOT NULL,
    stage text NOT NULL,
    outcome text NOT NULL,
    error_code text,
    provider text,
    model text,
    duration_ms integer NOT NULL,
    created_at text NOT NULL,
    CONSTRAINT organization_profile_job_events_attempt_check CHECK (((attempt >= 1) AND (attempt <= 3))),
    CONSTRAINT organization_profile_job_events_duration_ms_check CHECK ((duration_ms >= 0)),
    CONSTRAINT organization_profile_job_events_outcome_check CHECK ((outcome = ANY (ARRAY['STARTED'::text, 'PROGRESS'::text, 'READY'::text, 'FAILED'::text, 'CANCELLED'::text, 'SUPERSEDED'::text])))
);

-- organization_profile_jobs; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.organization_profile_jobs (
    id text NOT NULL,
    organization_id text NOT NULL,
    created_by text NOT NULL,
    request_id text NOT NULL,
    website text NOT NULL,
    status text NOT NULL,
    result_json text,
    error_code text,
    lease_owner text,
    lease_expires_at text,
    execution_name text,
    attempts integer DEFAULT 0 NOT NULL,
    confirmed_hash text,
    created_at text NOT NULL,
    updated_at text NOT NULL,
    source_kind text DEFAULT 'WEBSITE'::text NOT NULL,
    input_text text DEFAULT ''::text NOT NULL,
    use_ai integer DEFAULT 0 NOT NULL,
    input_hash text DEFAULT ''::text NOT NULL,
    progress_stage text DEFAULT ''::text NOT NULL,
    CONSTRAINT organization_profile_jobs_status_check CHECK ((status = ANY (ARRAY['QUEUED'::text, 'RUNNING'::text, 'READY'::text, 'FAILED'::text, 'CANCELLED'::text])))
);

-- organization_profile_sources; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.organization_profile_sources (
    id text NOT NULL,
    organization_id text NOT NULL,
    source_type text NOT NULL,
    source_url text,
    field_name text NOT NULL,
    extracted_value_json text,
    confidence text,
    detected_at text NOT NULL,
    confirmed_by_user integer DEFAULT 0 NOT NULL,
    confirmed_at text,
    CONSTRAINT organization_profile_sources_source_type_check CHECK ((source_type = ANY (ARRAY['USER_ENTERED'::text, 'USER_CONFIRMED'::text, 'WEBSITE_EXTRACTED'::text, 'AI_INFERRED'::text, 'SYSTEM_SEEDED'::text])))
);

-- organization_profiles; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.organization_profiles (
    organization_id text NOT NULL,
    display_name text,
    legal_name text,
    company_type text,
    website_url text,
    primary_domain text,
    tagline text,
    short_description text,
    long_description text,
    industry text,
    sub_industry text,
    company_size text,
    country text,
    city text,
    timezone text,
    contact_email text,
    contact_phone text,
    linkedin_url text,
    x_url text,
    facebook_url text,
    instagram_url text,
    youtube_url text,
    other_socials_json text DEFAULT '{}'::text NOT NULL,
    target_customer_types_json text DEFAULT '[]'::text NOT NULL,
    target_industries_json text DEFAULT '[]'::text NOT NULL,
    target_countries_json text DEFAULT '[]'::text NOT NULL,
    service_regions_json text DEFAULT '[]'::text NOT NULL,
    business_goals_json text DEFAULT '[]'::text NOT NULL,
    brand_logo_url text,
    brand_favicon_url text,
    brand_primary_color text,
    brand_secondary_color text,
    created_at text NOT NULL,
    updated_at text NOT NULL,
    specialties_json text DEFAULT '[]'::text NOT NULL
);

-- organization_services; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.organization_services (
    id text NOT NULL,
    organization_id text NOT NULL,
    name text NOT NULL,
    slug text NOT NULL,
    category text,
    description text,
    active integer DEFAULT 1 NOT NULL,
    source text DEFAULT 'MANUAL'::text NOT NULL,
    created_at text NOT NULL,
    updated_at text NOT NULL,
    CONSTRAINT organization_services_source_check CHECK ((source = ANY (ARRAY['MANUAL'::text, 'WEBSITE_DISCOVERY'::text, 'SYSTEM_SEEDED'::text, 'USER_CONFIRMED'::text])))
);

-- organization_settings; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.organization_settings (
    organization_id text NOT NULL,
    configuration_json text NOT NULL,
    updated_by text NOT NULL,
    updated_at text NOT NULL
);

-- organization_setup; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.organization_setup (
    organization_id text NOT NULL,
    default_icp_id text,
    objectives_json text DEFAULT '[]'::text NOT NULL,
    preferences_json text DEFAULT '{}'::text NOT NULL,
    current_step text NOT NULL,
    revision integer NOT NULL,
    completed_revision integer,
    updated_by text NOT NULL,
    updated_at text NOT NULL
);

-- organizations; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.organizations (
    id text NOT NULL,
    name text NOT NULL,
    slug text NOT NULL,
    status text DEFAULT 'ACTIVE'::text NOT NULL,
    created_by_user_id text,
    created_at text NOT NULL,
    updated_at text NOT NULL,
    CONSTRAINT organizations_status_check CHECK ((status = ANY (ARRAY['ACTIVE'::text, 'SUSPENDED'::text, 'ARCHIVED'::text])))
);

-- payu_access_callback_events; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.payu_access_callback_events (
    id text NOT NULL,
    order_id text NOT NULL,
    body_sha256 text NOT NULL,
    event_type text NOT NULL,
    created_at text NOT NULL
);

-- payu_access_orders; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.payu_access_orders (
    id text NOT NULL,
    organization_id text NOT NULL,
    created_by text NOT NULL,
    provider text DEFAULT 'payu'::text NOT NULL,
    mode text NOT NULL,
    txn_id text NOT NULL,
    request_id text NOT NULL,
    request_fingerprint text NOT NULL,
    plan_code text NOT NULL,
    "interval" text NOT NULL,
    plan_json text NOT NULL,
    catalog_version text NOT NULL,
    policy_version text NOT NULL,
    terms_version text NOT NULL,
    terms_accepted_at text NOT NULL,
    currency text NOT NULL,
    subtotal_minor bigint NOT NULL,
    tax_minor bigint NOT NULL,
    total_minor bigint NOT NULL,
    tax_json text NOT NULL,
    expected_json text NOT NULL,
    billing_encrypted text NOT NULL,
    status text NOT NULL,
    checkout_url text,
    provider_payment_id text,
    verified_json text,
    period_start bigint,
    period_end bigint,
    verified_at text,
    creation_started_at text,
    expires_at bigint NOT NULL,
    created_at text NOT NULL,
    updated_at text NOT NULL,
    CONSTRAINT payu_access_orders_check CHECK ((total_minor = (subtotal_minor + tax_minor))),
    CONSTRAINT payu_access_orders_interval_check CHECK (("interval" = ANY (ARRAY['monthly'::text, 'yearly'::text]))),
    CONSTRAINT payu_access_orders_mode_check CHECK ((mode = ANY (ARRAY['test'::text, 'live'::text]))),
    CONSTRAINT payu_access_orders_provider_check CHECK ((provider = 'payu'::text)),
    CONSTRAINT payu_access_orders_status_check CHECK ((status = ANY (ARRAY['CREATING'::text, 'PENDING'::text, 'PAID'::text, 'FAILED'::text, 'CANCELLED'::text, 'EXPIRED'::text, 'REVIEW'::text, 'REFUNDED'::text]))),
    CONSTRAINT payu_access_orders_subtotal_minor_check CHECK ((subtotal_minor > 0)),
    CONSTRAINT payu_access_orders_tax_minor_check CHECK ((tax_minor >= 0)),
    CONSTRAINT payu_access_orders_total_minor_check CHECK ((total_minor > 0))
);

-- payu_access_refunds; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.payu_access_refunds (
    id text NOT NULL,
    organization_id text NOT NULL,
    order_id text NOT NULL,
    requested_by text NOT NULL,
    request_id text NOT NULL,
    amount_minor bigint NOT NULL,
    currency text NOT NULL,
    status text NOT NULL,
    provider_refund_id text,
    verified_json text,
    created_at text NOT NULL,
    updated_at text NOT NULL,
    CONSTRAINT payu_access_refunds_amount_minor_check CHECK ((amount_minor > 0)),
    CONSTRAINT payu_access_refunds_status_check CHECK ((status = ANY (ARRAY['REQUESTED'::text, 'REVIEW'::text, 'PENDING'::text, 'SUCCEEDED'::text, 'REJECTED'::text])))
);

-- payu_refund_observations; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.payu_refund_observations (
    mode text NOT NULL,
    provider_refund_id text NOT NULL,
    order_id text NOT NULL,
    organization_id text NOT NULL,
    provider_payment_id text NOT NULL,
    amount_minor bigint NOT NULL,
    currency text,
    status text NOT NULL,
    verified_json text NOT NULL,
    first_seen_at text NOT NULL,
    updated_at text NOT NULL,
    CONSTRAINT payu_refund_observations_amount_minor_check CHECK ((amount_minor > 0)),
    CONSTRAINT payu_refund_observations_mode_check CHECK ((mode = ANY (ARRAY['test'::text, 'live'::text]))),
    CONSTRAINT payu_refund_observations_status_check CHECK ((status = ANY (ARRAY['PENDING'::text, 'SUCCEEDED'::text, 'FAILED'::text, 'REVIEW'::text])))
);

-- pipeline_runs; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.pipeline_runs (
    id bigint NOT NULL,
    market text NOT NULL,
    vertical text NOT NULL,
    target integer NOT NULL,
    started_at text DEFAULT (CURRENT_TIMESTAMP)::text,
    finished_at timestamp without time zone,
    status text DEFAULT 'RUNNING'::text,
    raw_found integer DEFAULT 0,
    deduped integer DEFAULT 0,
    filtered integer DEFAULT 0,
    websites_processed integer DEFAULT 0,
    qualified integer DEFAULT 0,
    exported integer DEFAULT 0,
    output_file text,
    error_message text,
    run_configuration_json text,
    cancelled_at timestamp without time zone,
    campaign_id text,
    cancellation_requested integer DEFAULT 0 NOT NULL,
    execution_name text,
    lease_owner text,
    lease_expires_at text,
    failure_class text,
    organization_id text
);

-- pipeline_runs_id_seq; Type: SEQUENCE; Schema: configured target; Owner: -
CREATE SEQUENCE __PLANEBYTE_SCHEMA__.pipeline_runs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- pipeline_runs_id_seq; Type: SEQUENCE OWNED BY; Schema: configured target; Owner: -
ALTER SEQUENCE __PLANEBYTE_SCHEMA__.pipeline_runs_id_seq OWNED BY __PLANEBYTE_SCHEMA__.pipeline_runs.id;

-- prospects; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.prospects (
    id text NOT NULL,
    first_seen_at text NOT NULL,
    last_seen_at text NOT NULL,
    first_campaign_id text,
    times_discovered integer DEFAULT 0 NOT NULL,
    lead_status text DEFAULT 'NEW'::text NOT NULL,
    assigned_to text,
    created_by text,
    updated_by text,
    updated_at text NOT NULL,
    business_scale text DEFAULT 'LOCAL'::text NOT NULL,
    scale_reason text,
    scale_confidence real DEFAULT 0.5 NOT NULL,
    organization_id text,
    CONSTRAINT prospects_lead_status_check CHECK ((lead_status = ANY (ARRAY['NEW'::text, 'SHORTLISTED'::text, 'READY_TO_CONTACT'::text, 'CONTACTED'::text, 'FOLLOW_UP'::text, 'REPLIED'::text, 'MEETING'::text, 'PROPOSAL'::text, 'WON'::text, 'LOST'::text, 'NOT_INTERESTED'::text, 'DO_NOT_CONTACT'::text])))
);

-- provider_rate_limits; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.provider_rate_limits (
    provider text NOT NULL,
    next_request_at real NOT NULL
);

-- scan_campaigns; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.scan_campaigns (
    id text NOT NULL,
    created_by text NOT NULL,
    status text DEFAULT 'QUEUED'::text NOT NULL,
    configuration_json text NOT NULL,
    created_at text NOT NULL,
    started_at text,
    completed_at text,
    target_total integer NOT NULL,
    cancellation_requested integer DEFAULT 0 NOT NULL,
    source_type text DEFAULT 'OVERTURE'::text NOT NULL,
    source_metadata text DEFAULT '{}'::text NOT NULL,
    original_prompt text,
    organization_id text,
    email_account_id text
);

-- shared_settings; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.shared_settings (
    id integer NOT NULL,
    configuration_json text NOT NULL,
    updated_by text NOT NULL,
    updated_at text NOT NULL,
    organization_id text,
    CONSTRAINT shared_settings_id_check CHECK ((id = 1))
);

-- transactional_notification_events; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.transactional_notification_events (
    provider_event_id text NOT NULL,
    provider_message_id text NOT NULL,
    notification_id text,
    event_type text NOT NULL,
    occurred_at text,
    received_at text NOT NULL
);

-- transactional_notifications; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.transactional_notifications (
    id text NOT NULL,
    account_email text NOT NULL,
    organization_id text,
    purpose text NOT NULL,
    authority_id text NOT NULL,
    dedupe_key text NOT NULL,
    payload_encrypted text,
    status text NOT NULL,
    attempts integer DEFAULT 0 NOT NULL,
    provider_message_id text,
    error_code text,
    execution_name text,
    dispatch_attempts integer DEFAULT 0 NOT NULL,
    lease_token text,
    lease_until bigint,
    available_at bigint NOT NULL,
    expires_at bigint NOT NULL,
    created_at text NOT NULL,
    updated_at text NOT NULL,
    CONSTRAINT transactional_notifications_attempts_check CHECK (((attempts >= 0) AND (attempts <= 3))),
    CONSTRAINT transactional_notifications_dispatch_attempts_check CHECK (((dispatch_attempts >= 0) AND (dispatch_attempts <= 3))),
    CONSTRAINT transactional_notifications_status_check CHECK ((status = ANY (ARRAY['QUEUED'::text, 'SENDING'::text, 'ACCEPTED'::text, 'DELIVERED'::text, 'BOUNCED'::text, 'COMPLAINED'::text, 'FAILED'::text, 'CANCELLED'::text])))
);

-- transactional_suppressions; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.transactional_suppressions (
    account_email text NOT NULL,
    reason text NOT NULL,
    created_at text NOT NULL
);

-- user_profiles; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.user_profiles (
    user_id text NOT NULL,
    display_name text,
    job_title text,
    phone text,
    timezone text,
    locale text,
    avatar_url text,
    onboarding_seen integer DEFAULT 0 NOT NULL,
    created_at text NOT NULL,
    updated_at text NOT NULL,
    active_organization_id text
);

-- users; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.users (
    id text NOT NULL,
    email text NOT NULL,
    display_name text NOT NULL,
    avatar_url text,
    role text DEFAULT 'ADMIN'::text NOT NULL,
    last_login text,
    provider text,
    updated_at text
);

-- webhook_deliveries; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.webhook_deliveries (
    id text NOT NULL,
    endpoint_id text NOT NULL,
    organization_id text NOT NULL,
    event_id text NOT NULL,
    topic text NOT NULL,
    body_json text NOT NULL,
    status text DEFAULT 'QUEUED'::text NOT NULL,
    attempts integer DEFAULT 0 NOT NULL,
    next_attempt_at text NOT NULL,
    lease_owner text,
    lease_until text,
    last_http_status integer,
    last_error_code text,
    created_at text NOT NULL,
    delivered_at text
);

-- webhook_delivery_attempts; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.webhook_delivery_attempts (
    delivery_id text NOT NULL,
    organization_id text NOT NULL,
    attempt integer NOT NULL,
    started_at text NOT NULL,
    finished_at text,
    http_status integer,
    error_code text
);

-- webhook_endpoints; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.webhook_endpoints (
    id text NOT NULL,
    organization_id text NOT NULL,
    name text NOT NULL,
    url text NOT NULL,
    topics_json text NOT NULL,
    status text DEFAULT 'ACTIVE'::text NOT NULL,
    revision integer DEFAULT 1 NOT NULL,
    signing_secret_ciphertext text NOT NULL,
    created_by text NOT NULL,
    request_id text NOT NULL,
    creation_fingerprint text NOT NULL,
    created_at text NOT NULL,
    updated_at text NOT NULL,
    last_error_code text,
    dispatch_token text,
    dispatch_until text,
    last_dispatch_at text
);

-- workspace_api_keys; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.workspace_api_keys (
    id text NOT NULL,
    organization_id text NOT NULL,
    created_by text NOT NULL,
    name text NOT NULL,
    token_hash text NOT NULL,
    scopes_json text NOT NULL,
    created_at text NOT NULL,
    expires_at text NOT NULL,
    revoked_at text,
    last_used_at text,
    rotated_from text
);

-- workspace_creation_requests; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.workspace_creation_requests (
    user_id text NOT NULL,
    request_id text NOT NULL,
    organization_id text NOT NULL,
    requested_name text NOT NULL,
    created_at text NOT NULL
);

-- workspace_invitations; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.workspace_invitations (
    id text NOT NULL,
    organization_id text NOT NULL,
    email text NOT NULL,
    role text NOT NULL,
    token_hash text NOT NULL,
    status text NOT NULL,
    invited_by text NOT NULL,
    created_at text NOT NULL,
    expires_at text NOT NULL,
    responded_at text,
    CONSTRAINT workspace_invitations_role_check CHECK ((role = ANY (ARRAY['ADMIN'::text, 'MEMBER'::text, 'VIEWER'::text]))),
    CONSTRAINT workspace_invitations_status_check CHECK ((status = ANY (ARRAY['PENDING'::text, 'ACCEPTED'::text, 'REJECTED'::text, 'REVOKED'::text, 'EXPIRED'::text])))
);

-- workspace_notifications; Type: TABLE; Schema: configured target; Owner: -
CREATE TABLE __PLANEBYTE_SCHEMA__.workspace_notifications (
    id text NOT NULL,
    organization_id text NOT NULL,
    user_id text NOT NULL,
    kind text NOT NULL,
    entity_id text NOT NULL,
    created_at text NOT NULL,
    read_at text
);

-- businesses id; Type: DEFAULT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.businesses ALTER COLUMN id SET DEFAULT nextval('__PLANEBYTE_SCHEMA__.businesses_id_seq'::regclass);

-- pipeline_runs id; Type: DEFAULT; Schema: configured target; Owner: -
ALTER TABLE ONLY __PLANEBYTE_SCHEMA__.pipeline_runs ALTER COLUMN id SET DEFAULT nextval('__PLANEBYTE_SCHEMA__.pipeline_runs_id_seq'::regclass);
