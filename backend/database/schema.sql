-- ==============================================================
--  AutoFlow AI X — PostgreSQL Schema
--  Designed for production-grade workflow automation SaaS
-- ==============================================================

-- Enable UUID generation extension
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ==============================================================
-- ENUM TYPES
-- ==============================================================

CREATE TYPE user_plan AS ENUM ('free', 'starter', 'pro', 'enterprise');

CREATE TYPE workflow_status AS ENUM ('draft', 'active', 'paused', 'archived');

CREATE TYPE run_status AS ENUM ('pending', 'running', 'success', 'failed', 'cancelled', 'retrying');

CREATE TYPE node_type AS ENUM (
    'trigger',
    'action',
    'condition',
    'delay',
    'loop',
    'ai_agent',
    'webhook',
    'transformer'
);

CREATE TYPE integration_service AS ENUM (
    'gmail',
    'google_sheets',
    'google_calendar',
    'whatsapp',
    'slack',
    'notion',
    'hubspot',
    'salesforce',
    'stripe',
    'custom_webhook'
);

-- ==============================================================
-- TABLE 1: users
-- Central identity table. Stores authentication and plan info.
-- ==============================================================

CREATE TABLE users (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email               VARCHAR(320)    NOT NULL,
    password_hash       TEXT            NOT NULL,
    full_name           VARCHAR(255),
    avatar_url          TEXT,
    plan                user_plan       NOT NULL DEFAULT 'free',
    is_verified         BOOLEAN         NOT NULL DEFAULT FALSE,
    is_active           BOOLEAN         NOT NULL DEFAULT TRUE,

    -- Rate limiting & quota tracking
    monthly_run_count   INTEGER         NOT NULL DEFAULT 0,
    last_run_reset_at   TIMESTAMPTZ,

    -- Timestamps
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    deleted_at          TIMESTAMPTZ,            -- Soft delete

    CONSTRAINT users_email_unique UNIQUE (email)
);

-- Indexes on users
CREATE INDEX idx_users_email         ON users (email);
CREATE INDEX idx_users_plan          ON users (plan);
CREATE INDEX idx_users_is_active     ON users (is_active) WHERE is_active = TRUE;
CREATE INDEX idx_users_deleted_at    ON users (deleted_at) WHERE deleted_at IS NULL;


-- ==============================================================
-- TABLE 2: api_keys
-- Personal API keys for users to call AutoFlow programmatically.
-- ==============================================================

CREATE TABLE api_keys (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID            NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name            VARCHAR(100)    NOT NULL,               -- e.g. "My Production Key"
    key_hash        TEXT            NOT NULL UNIQUE,        -- Hashed API key (never store plaintext)
    key_prefix      VARCHAR(12)     NOT NULL,               -- First 8 chars shown in UI (e.g. "af_xyz123")
    last_used_at    TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ,
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_api_keys_user_id    ON api_keys (user_id);
CREATE INDEX idx_api_keys_key_hash   ON api_keys (key_hash);


-- ==============================================================
-- TABLE 3: workflows
-- Core workflow definitions. Each workflow belongs to a user.
-- ==============================================================

CREATE TABLE workflows (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID            NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name            VARCHAR(255)    NOT NULL,
    description     TEXT,
    status          workflow_status NOT NULL DEFAULT 'draft',

    -- AI-generated context: stores the original NLP prompt and extracted intent
    original_prompt TEXT,
    ai_context_json JSONB,

    -- Scheduling: cron expression for time-based triggers
    cron_expression VARCHAR(100),
    timezone        VARCHAR(100)    NOT NULL DEFAULT 'UTC',

    -- Versioning & rollback
    version         INTEGER         NOT NULL DEFAULT 1,

    -- Soft delete
    deleted_at      TIMESTAMPTZ,

    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- Indexes on workflows
CREATE INDEX idx_workflows_user_id       ON workflows (user_id);
CREATE INDEX idx_workflows_status        ON workflows (status);
CREATE INDEX idx_workflows_created_at    ON workflows (created_at DESC);
CREATE INDEX idx_workflows_deleted_at    ON workflows (deleted_at) WHERE deleted_at IS NULL;
-- Partial index: only active workflows
CREATE INDEX idx_workflows_active        ON workflows (user_id, status) WHERE status = 'active';


-- ==============================================================
-- TABLE 4: workflow_nodes
-- Individual steps (nodes) inside a workflow.
-- Stores visual canvas position and step configuration.
-- ==============================================================

CREATE TABLE workflow_nodes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id     UUID            NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
    node_type       node_type       NOT NULL,
    label           VARCHAR(255),                   -- Human-readable name for the node
    config_json     JSONB           NOT NULL DEFAULT '{}',  -- Node-specific settings (e.g. API keys refs, filters)
    position_x      FLOAT           NOT NULL DEFAULT 0,     -- Canvas X coordinate
    position_y      FLOAT           NOT NULL DEFAULT 0,     -- Canvas Y coordinate
    is_disabled     BOOLEAN         NOT NULL DEFAULT FALSE,  -- Allows skipping a node without deleting
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- Indexes on workflow_nodes
CREATE INDEX idx_nodes_workflow_id   ON workflow_nodes (workflow_id);
CREATE INDEX idx_nodes_node_type     ON workflow_nodes (node_type);
-- GIN index for fast JSONB queries (e.g. find all nodes with a specific config key)
CREATE INDEX idx_nodes_config_gin    ON workflow_nodes USING GIN (config_json);


-- ==============================================================
-- TABLE 5: workflow_edges
-- Directed connections between nodes (the arrows on the canvas).
-- A condition node can have multiple outgoing edges (true/false).
-- ==============================================================

CREATE TABLE workflow_edges (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id     UUID            NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
    source_node_id  UUID            NOT NULL REFERENCES workflow_nodes(id) ON DELETE CASCADE,
    target_node_id  UUID            NOT NULL REFERENCES workflow_nodes(id) ON DELETE CASCADE,

    -- Edge label (e.g. "Yes", "No", "On Error") for conditional branching
    label           VARCHAR(100),
    condition_expr  TEXT,           -- Optional: evaluated at runtime to decide if this edge fires

    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    -- Prevent duplicate connections between the same two nodes on the same label
    CONSTRAINT edges_unique_connection UNIQUE (workflow_id, source_node_id, target_node_id, label),

    -- Prevent self-loops
    CONSTRAINT edges_no_self_loop CHECK (source_node_id != target_node_id)
);

-- Indexes on workflow_edges
CREATE INDEX idx_edges_workflow_id       ON workflow_edges (workflow_id);
CREATE INDEX idx_edges_source_node_id   ON workflow_edges (source_node_id);
CREATE INDEX idx_edges_target_node_id   ON workflow_edges (target_node_id);


-- ==============================================================
-- TABLE 6: workflow_runs
-- Records every execution instance of a workflow.
-- One workflow can have many runs.
-- ==============================================================

CREATE TABLE workflow_runs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id         UUID            NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
    user_id             UUID            NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status              run_status      NOT NULL DEFAULT 'pending',

    -- Trigger metadata: how/why this run was triggered
    trigger_type        VARCHAR(50),            -- e.g. 'manual', 'scheduled', 'webhook', 'api'
    trigger_payload     JSONB,                  -- The incoming data that triggered the run

    -- Execution context
    context_snapshot    JSONB,                  -- Snapshot of workflow config at time of run (for auditing)
    output_json         JSONB,                  -- Final output of the workflow run

    -- Retry tracking
    attempt_number      INTEGER         NOT NULL DEFAULT 1,
    max_attempts        INTEGER         NOT NULL DEFAULT 3,
    parent_run_id       UUID            REFERENCES workflow_runs(id), -- Points to original run on retry

    -- Error info
    error_message       TEXT,
    error_stack         TEXT,

    -- Timing
    started_at          TIMESTAMPTZ,
    finished_at         TIMESTAMPTZ,
    duration_ms         INTEGER,                -- Computed: finished_at - started_at in ms
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT runs_attempt_positive CHECK (attempt_number >= 1),
    CONSTRAINT runs_finished_after_start CHECK (finished_at IS NULL OR finished_at >= started_at)
);

-- Indexes on workflow_runs
CREATE INDEX idx_runs_workflow_id    ON workflow_runs (workflow_id);
CREATE INDEX idx_runs_user_id        ON workflow_runs (user_id);
CREATE INDEX idx_runs_status         ON workflow_runs (status);
CREATE INDEX idx_runs_created_at     ON workflow_runs (created_at DESC);
CREATE INDEX idx_runs_parent_run_id  ON workflow_runs (parent_run_id) WHERE parent_run_id IS NOT NULL;
-- Composite index for dashboard queries (filter by workflow + status)
CREATE INDEX idx_runs_workflow_status ON workflow_runs (workflow_id, status, created_at DESC);


-- ==============================================================
-- TABLE 7: workflow_run_step_logs
-- Fine-grained per-node execution records within a single run.
-- Crucial for debugging and monitoring.
-- ==============================================================

CREATE TABLE workflow_run_step_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id          UUID            NOT NULL REFERENCES workflow_runs(id) ON DELETE CASCADE,
    node_id         UUID            NOT NULL REFERENCES workflow_nodes(id) ON DELETE CASCADE,
    status          run_status      NOT NULL DEFAULT 'pending',
    input_json      JSONB,          -- Data flowing INTO this node
    output_json     JSONB,          -- Data flowing OUT of this node
    error_message   TEXT,
    started_at      TIMESTAMPTZ,
    finished_at     TIMESTAMPTZ,
    duration_ms     INTEGER
);

CREATE INDEX idx_step_logs_run_id    ON workflow_run_step_logs (run_id);
CREATE INDEX idx_step_logs_node_id   ON workflow_run_step_logs (node_id);
CREATE INDEX idx_step_logs_status    ON workflow_run_step_logs (status);


-- ==============================================================
-- TABLE 8: integrations
-- Stores OAuth tokens / API credentials for third-party services.
-- Credentials are ALWAYS stored encrypted. Never plaintext.
-- ==============================================================

CREATE TABLE integrations (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID            NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    service_name            integration_service NOT NULL,
    display_name            VARCHAR(255),           -- e.g. "Work Gmail", "Client Sheets"
    credentials_encrypted   TEXT            NOT NULL, -- AES-256-GCM encrypted blob
    scopes                  TEXT[],                  -- OAuth scopes granted
    is_active               BOOLEAN         NOT NULL DEFAULT TRUE,
    expires_at              TIMESTAMPTZ,             -- Token expiry (null = no expiry / API key)
    last_synced_at          TIMESTAMPTZ,
    created_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    -- A user should have one active integration per service (can have multiple if display_name differs)
    CONSTRAINT integrations_unique_per_user UNIQUE (user_id, service_name, display_name)
);

-- Indexes on integrations
CREATE INDEX idx_integrations_user_id       ON integrations (user_id);
CREATE INDEX idx_integrations_service       ON integrations (service_name);
CREATE INDEX idx_integrations_is_active     ON integrations (is_active) WHERE is_active = TRUE;
CREATE INDEX idx_integrations_expires_at    ON integrations (expires_at) WHERE expires_at IS NOT NULL;


-- ==============================================================
-- TABLE 9: industry_templates
-- Pre-built workflow templates for specific industries.
-- Can be cloned by any user as a starting point.
-- ==============================================================

CREATE TABLE industry_templates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255)    NOT NULL,
    description     TEXT,
    industry        VARCHAR(100)    NOT NULL,       -- e.g. 'healthcare', 'real_estate', 'e-commerce'
    tags            TEXT[],                         -- e.g. ARRAY['appointments', 'reminders', 'patients']
    dsl_json        JSONB           NOT NULL,       -- Full workflow definition (nodes + edges)
    thumbnail_url   TEXT,                           -- Preview image for template gallery
    is_published    BOOLEAN         NOT NULL DEFAULT FALSE,
    use_count       INTEGER         NOT NULL DEFAULT 0,  -- Popularity tracking
    created_by      UUID            REFERENCES users(id) ON DELETE SET NULL,  -- NULL = system template
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- Indexes on industry_templates
CREATE INDEX idx_templates_industry         ON industry_templates (industry);
CREATE INDEX idx_templates_is_published     ON industry_templates (is_published) WHERE is_published = TRUE;
CREATE INDEX idx_templates_tags_gin         ON industry_templates USING GIN (tags);
CREATE INDEX idx_templates_dsl_gin          ON industry_templates USING GIN (dsl_json);
CREATE INDEX idx_templates_use_count        ON industry_templates (use_count DESC);


-- ==============================================================
-- TABLE 10: audit_logs
-- Immutable record of every user action. Critical for security,
-- compliance, and debugging in a SaaS product.
-- ==============================================================

CREATE TABLE audit_logs (
    id              BIGSERIAL PRIMARY KEY,          -- BIGSERIAL for high-volume sequential inserts
    user_id         UUID            REFERENCES users(id) ON DELETE SET NULL,
    action          VARCHAR(100)    NOT NULL,       -- e.g. 'workflow.create', 'run.trigger', 'integration.delete'
    resource_type   VARCHAR(100),                   -- e.g. 'workflow', 'integration'
    resource_id     UUID,
    metadata        JSONB,                          -- Additional context (IP, user-agent, before/after state)
    ip_address      INET,
    user_agent      TEXT,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- Audit logs should only ever be appended — never updated or deleted.
-- Indexes optimized for querying by user and time range.
CREATE INDEX idx_audit_user_id       ON audit_logs (user_id, created_at DESC);
CREATE INDEX idx_audit_action        ON audit_logs (action);
CREATE INDEX idx_audit_resource      ON audit_logs (resource_type, resource_id);
CREATE INDEX idx_audit_created_at    ON audit_logs (created_at DESC);


-- ==============================================================
-- TRIGGERS: Auto-update updated_at columns
-- ==============================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_workflows_updated_at
    BEFORE UPDATE ON workflows
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_nodes_updated_at
    BEFORE UPDATE ON workflow_nodes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_integrations_updated_at
    BEFORE UPDATE ON integrations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_templates_updated_at
    BEFORE UPDATE ON industry_templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
