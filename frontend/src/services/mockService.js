/**
 * AutoFlow AI X — Mock Service & Typed Domain Model
 * 
 * Provides a typed mock data layer with full in-memory reactivity and LocalStorage persistence.
 * Designed to sit behind an integration-ready service boundary so frontend screens
 * can operate with zero backend coupling, while matching future Stage 2/3 contracts.
 */

// LocalStorage Keys
const STORAGE_KEYS = {
  WORKFLOWS: 'autoflow_x_workflows',
  RUNS: 'autoflow_x_runs',
  INCIDENTS: 'autoflow_x_recovery_incidents',
  APPROVALS: 'autoflow_x_approvals',
};

// ─── INITIAL TYPED SEED DATA ────────────────────────────────────────────────

export const SEED_WORKFLOWS = [
  {
    id: 'wf-prod-sync',
    name: 'Customer Ingestion & CRM Sync',
    description: 'Enriches inbound customer webhook payloads, computes tiering with AI Agent, and synchronizes HubSpot and Notion records.',
    status: 'active',
    version: '2.1.0',
    version_hash: 'a7b8c9d0',
    created_at: '2026-10-15T08:30:00Z',
    updated_at: '2026-11-01T14:20:00Z',
    last_run_at: '2026-11-01T17:35:00Z',
    metrics: { total_runs: 1420, success_rate: 98.6, avg_duration_ms: 1240 },
    nodes_count: 5,
    dsl: {
      name: 'Customer Ingestion & CRM Sync',
      nodes: [
        { id: 'trigger_webhook', service: 'webhook', operation: 'receive_lead', title: 'Webhook: Lead Ingest', type: 'trigger' },
        { id: 'ai_tier_classifier', service: 'groq_ai', operation: 'classify_tier', title: 'AI Lead Classifier', type: 'ai_agent' },
        { id: 'check_high_value', service: 'builtin', operation: 'condition', title: 'High Value Threshold?', type: 'condition' },
        { id: 'human_review', service: 'human', operation: 'request_approval', title: 'Enterprise Lead Approval', type: 'approval' },
        { id: 'hubspot_sync', service: 'hubspot', operation: 'create_contact', title: 'HubSpot Contact Sync', type: 'action' }
      ],
      edges: [
        { id: 'e1', source: 'trigger_webhook', target: 'ai_tier_classifier' },
        { id: 'e2', source: 'ai_tier_classifier', target: 'check_high_value' },
        { id: 'e3', source: 'check_high_value', target: 'human_review', condition: 'tier === "Enterprise"' },
        { id: 'e4', source: 'human_review', target: 'hubspot_sync' },
        { id: 'e5', source: 'check_high_value', target: 'hubspot_sync', condition: 'tier !== "Enterprise"' }
      ]
    }
  },
  {
    id: 'wf-financial-report',
    name: 'Weekly Financial Anomaly Audit',
    description: 'Scheduled batch pipeline querying Stripe ledger, flagging outlier transactions, and generating CFO briefing memo.',
    status: 'active',
    version: '1.4.2',
    version_hash: 'f4e3d2c1',
    created_at: '2026-09-20T11:00:00Z',
    updated_at: '2026-10-30T09:15:00Z',
    last_run_at: '2026-11-01T17:15:00Z',
    metrics: { total_runs: 840, success_rate: 94.2, avg_duration_ms: 3820 },
    nodes_count: 6,
    dsl: {
      name: 'Weekly Financial Anomaly Audit',
      nodes: [
        { id: 'cron_schedule', service: 'scheduler', operation: 'weekly_cron', title: 'Cron: Sunday 00:00 UTC', type: 'trigger' },
        { id: 'fetch_ledger', service: 'http', operation: 'query_ledger', title: 'Fetch Stripe Ledger', type: 'action' },
        { id: 'ai_detect_anomalies', service: 'groq_ai', operation: 'analyze_variance', title: 'AI Anomaly Detector', type: 'ai_agent' },
        { id: 'cfo_approval_step', service: 'human', operation: 'signoff_discrepancy', title: 'CFO Discrepancy Sign-off', type: 'approval' },
        { id: 'post_slack_alert', service: 'slack', operation: 'send_message', title: 'Post to #finance-audit', type: 'action' },
        { id: 'archive_sheets', service: 'google_sheets', operation: 'append_row', title: 'Archive to Google Sheets', type: 'action' }
      ],
      edges: [
        { id: 'fe1', source: 'cron_schedule', target: 'fetch_ledger' },
        { id: 'fe2', source: 'fetch_ledger', target: 'ai_detect_anomalies' },
        { id: 'fe3', source: 'ai_detect_anomalies', target: 'cfo_approval_step' },
        { id: 'fe4', source: 'cfo_approval_step', target: 'post_slack_alert' },
        { id: 'fe5', source: 'cfo_approval_step', target: 'archive_sheets' }
      ]
    }
  },
  {
    id: 'wf-support-auto',
    name: 'Support Ticket Intelligent Resolver',
    description: 'Monitors inbound customer support emails, generates sentiment-aware draft responses, and auto-categorizes Zendesk tickets.',
    status: 'paused',
    version: '1.0.5',
    version_hash: '89ac345b',
    created_at: '2026-10-01T16:00:00Z',
    updated_at: '2026-10-28T12:00:00Z',
    last_run_at: '2026-10-31T22:10:00Z',
    metrics: { total_runs: 512, success_rate: 91.8, avg_duration_ms: 2150 },
    nodes_count: 4,
    dsl: {
      name: 'Support Ticket Intelligent Resolver',
      nodes: [
        { id: 'inbound_email', service: 'gmail', operation: 'watch_threads', title: 'Gmail: Inbound Support', type: 'trigger' },
        { id: 'sentiment_parser', service: 'groq_ai', operation: 'classify_intent', title: 'LLM Sentiment & Intent', type: 'ai_agent' },
        { id: 'draft_reply_approval', service: 'human', operation: 'verify_reply', title: 'Rep Review Auto-Draft', type: 'approval' },
        { id: 'send_gmail_reply', service: 'gmail', operation: 'send_draft', title: 'Dispatch Customer Email', type: 'action' }
      ],
      edges: [
        { id: 'se1', source: 'inbound_email', target: 'sentiment_parser' },
        { id: 'se2', source: 'sentiment_parser', target: 'draft_reply_approval' },
        { id: 'se3', source: 'draft_reply_approval', target: 'send_gmail_reply' }
      ]
    }
  }
];

export const SEED_RUNS = [
  {
    id: 'run-9841',
    workflow_id: 'wf-prod-sync',
    workflow_name: 'Customer Ingestion & CRM Sync',
    status: 'failed',
    started_at: '2026-11-01T17:35:12Z',
    completed_at: '2026-11-01T17:35:16Z',
    duration_ms: 4120,
    trigger_type: 'webhook',
    idempotency_key: 'idem-hook-9841-lead-x42',
    workflow_version: '2.1.0',
    error_summary: 'HubSpot API rejected payload: missing mandatory property "annual_revenue" formatted as numeric.',
    step_logs: [
      {
        step_id: 'step_1',
        node_id: 'trigger_webhook',
        node_title: 'Webhook: Lead Ingest',
        status: 'success',
        duration_ms: 110,
        started_at: '2026-11-01T17:35:12.100Z',
        completed_at: '2026-11-01T17:35:12.210Z',
        input: { webhook_id: 'hook_882', source_ip: '35.192.44.12' },
        output: { lead_id: 'lead_9921', company: 'Acme Cloud Corp', domain: 'acmecloud.io', raw_revenue: '$1,200,000' }
      },
      {
        step_id: 'step_2',
        node_id: 'ai_tier_classifier',
        node_title: 'AI Lead Classifier',
        status: 'success',
        duration_ms: 1240,
        started_at: '2026-11-01T17:35:12.220Z',
        completed_at: '2026-11-01T17:35:13.460Z',
        input: { lead_id: 'lead_9921', company: 'Acme Cloud Corp', raw_revenue: '$1,200,000' },
        output: { tier: 'Enterprise', confidence: 0.96, score: 92, suggested_rep: 'sarah.connor@autoflow.ai' }
      },
      {
        step_id: 'step_3',
        node_id: 'check_high_value',
        node_title: 'High Value Threshold?',
        status: 'success',
        duration_ms: 45,
        started_at: '2026-11-01T17:35:13.470Z',
        completed_at: '2026-11-01T17:35:13.515Z',
        input: { tier: 'Enterprise' },
        output: { condition_met: true, branch_taken: 'true' }
      },
      {
        step_id: 'step_4',
        node_id: 'human_review',
        node_title: 'Enterprise Lead Approval',
        status: 'success',
        duration_ms: 1520,
        started_at: '2026-11-01T17:35:13.520Z',
        completed_at: '2026-11-01T17:35:15.040Z',
        input: { tier: 'Enterprise', lead_id: 'lead_9921' },
        output: { approved_by: 'Alex Morgan (VP Sales)', decision: 'APPROVED', timestamp: '2026-11-01T17:35:15Z' }
      },
      {
        step_id: 'step_5',
        node_id: 'hubspot_sync',
        node_title: 'HubSpot Contact Sync',
        status: 'failed',
        duration_ms: 1205,
        started_at: '2026-11-01T17:35:15.050Z',
        completed_at: '2026-11-01T17:35:16.255Z',
        input: {
          properties: {
            company: 'Acme Cloud Corp',
            email: 'admin@acmecloud.io',
            annual_revenue: '$1,200,000' // string causes schema mismatch
          }
        },
        error: {
          code: 'SCHEMA_VALIDATION_ERROR',
          message: 'HubSpot API Error: Property "annual_revenue" must be a float or integer, received string "$1,200,000". Status code: 400 Bad Request.',
          stack_trace: `HTTPError: 400 Client Error: Bad Request for url: https://api.hubapi.com/crm/v3/objects/contacts\n  at HubspotExecutor.execute (hubspot.py:142)\n  at WorkflowRunner._execute_with_retry (runner.py:388)`
        }
      }
    ]
  },
  {
    id: 'run-9840',
    workflow_id: 'wf-financial-report',
    workflow_name: 'Weekly Financial Anomaly Audit',
    status: 'awaiting_approval',
    started_at: '2026-11-01T17:15:00Z',
    completed_at: null,
    duration_ms: 2800,
    trigger_type: 'schedule',
    idempotency_key: 'idem-sched-2026-11-01-audit',
    workflow_version: '1.4.2',
    error_summary: null,
    step_logs: [
      {
        step_id: 'step_1',
        node_id: 'cron_schedule',
        node_title: 'Cron: Sunday 00:00 UTC',
        status: 'success',
        duration_ms: 30,
        started_at: '2026-11-01T17:15:00.010Z',
        completed_at: '2026-11-01T17:15:00.040Z',
        input: {},
        output: { scheduled_epoch: 1793549700 }
      },
      {
        step_id: 'step_2',
        node_id: 'fetch_ledger',
        node_title: 'Fetch Stripe Ledger',
        status: 'success',
        duration_ms: 950,
        started_at: '2026-11-01T17:15:00.050Z',
        completed_at: '2026-11-01T17:15:01.000Z',
        input: { limit: 500, period: '7d' },
        output: { records_fetched: 489, total_volume_usd: 842100.50 }
      },
      {
        step_id: 'step_3',
        node_id: 'ai_detect_anomalies',
        node_title: 'AI Anomaly Detector',
        status: 'success',
        duration_ms: 1820,
        started_at: '2026-11-01T17:15:01.010Z',
        completed_at: '2026-11-01T17:15:02.830Z',
        input: { records_count: 489 },
        output: {
          anomalies_flagged: 1,
          details: {
            charge_id: 'ch_3Mx89201a',
            amount: 45000.00,
            confidence_outlier: 0.98,
            reason: 'Charge exceeds 3-sigma historical deviance for customer "Nexus Logic Ltd"'
          }
        }
      },
      {
        step_id: 'step_4',
        node_id: 'cfo_approval_step',
        node_title: 'CFO Discrepancy Sign-off',
        status: 'paused',
        duration_ms: 0,
        started_at: '2026-11-01T17:15:02.840Z',
        completed_at: null,
        input: { anomaly_id: 'anom_041', amount: 45000.00 },
        output: null
      }
    ]
  },
  {
    id: 'run-9839',
    workflow_id: 'wf-prod-sync',
    workflow_name: 'Customer Ingestion & CRM Sync',
    status: 'success',
    started_at: '2026-11-01T16:45:00Z',
    completed_at: '2026-11-01T16:45:03Z',
    duration_ms: 2780,
    trigger_type: 'webhook',
    idempotency_key: 'idem-hook-9839-lead-x41',
    workflow_version: '2.1.0',
    error_summary: null,
    step_logs: [
      {
        step_id: 's1',
        node_id: 'trigger_webhook',
        node_title: 'Webhook: Lead Ingest',
        status: 'success',
        duration_ms: 80,
        started_at: '2026-11-01T16:45:00.100Z',
        completed_at: '2026-11-01T16:45:00.180Z',
        input: {},
        output: { company: 'Veloce Data' }
      },
      {
        step_id: 's2',
        node_id: 'ai_tier_classifier',
        node_title: 'AI Lead Classifier',
        status: 'success',
        duration_ms: 1100,
        started_at: '2026-11-01T16:45:00.190Z',
        completed_at: '2026-11-01T16:45:01.290Z',
        input: {},
        output: { tier: 'Growth' }
      },
      {
        step_id: 's3',
        node_id: 'check_high_value',
        node_title: 'High Value Threshold?',
        status: 'success',
        duration_ms: 30,
        started_at: '2026-11-01T16:45:01.300Z',
        completed_at: '2026-11-01T16:45:01.330Z',
        input: {},
        output: { condition_met: false, branch_taken: 'false' }
      },
      {
        step_id: 's4',
        node_id: 'hubspot_sync',
        node_title: 'HubSpot Contact Sync',
        status: 'success',
        duration_ms: 1570,
        started_at: '2026-11-01T16:45:01.340Z',
        completed_at: '2026-11-01T16:45:02.910Z',
        input: {},
        output: { hubspot_id: 'vid_994101', status: 'created' }
      }
    ]
  },
  {
    id: 'run-9838',
    workflow_id: 'wf-support-auto',
    workflow_name: 'Support Ticket Intelligent Resolver',
    status: 'running',
    started_at: '2026-11-01T17:42:10Z',
    completed_at: null,
    duration_ms: 5120,
    trigger_type: 'manual',
    idempotency_key: 'idem-man-9838-test',
    workflow_version: '1.0.5',
    error_summary: null,
    step_logs: [
      {
        step_id: 'st1',
        node_id: 'inbound_email',
        node_title: 'Gmail: Inbound Support',
        status: 'success',
        duration_ms: 240,
        started_at: '2026-11-01T17:42:10.100Z',
        completed_at: '2026-11-01T17:42:10.340Z',
        input: {},
        output: { thread_id: 'th_0912', sender: 'ceo@partner.org' }
      },
      {
        step_id: 'st2',
        node_id: 'sentiment_parser',
        node_title: 'LLM Sentiment & Intent',
        status: 'running',
        duration_ms: 4880,
        started_at: '2026-11-01T17:42:10.350Z',
        completed_at: null,
        input: { body_length: 420 },
        output: null
      }
    ]
  }
];

export const SEED_RECOVERY_INCIDENTS = [
  {
    id: 'inc-4091',
    run_id: 'run-9841',
    workflow_id: 'wf-prod-sync',
    workflow_name: 'Customer Ingestion & CRM Sync',
    failed_node_id: 'hubspot_sync',
    failed_node_title: 'HubSpot Contact Sync',
    cluster_type: 'SCHEMA_MISMATCH',
    cluster_name: 'CRM Property Type Incompatibility',
    severity: 'high',
    status: 'pending_triage',
    created_at: '2026-11-01T17:35:16Z',
    blast_radius: {
      affected_runs_count: 3,
      downstream_blocked: ['Customer Onboarding Notification', 'Slack Lead Dispatch'],
      financial_risk: 'Low'
    },
    diagnosis: {
      summary: 'HubSpot rejected record creation because "annual_revenue" was provided as a string containing currency symbols ("$1,200,000") instead of numeric float.',
      root_cause: 'Webhook source upstream sends unformatted raw strings without stripping non-digits.',
      confidence: 0.96,
      reasoning_steps: [
        'Analyzed HTTP 400 response from https://api.hubapi.com/crm/v3/objects/contacts',
        'Compared target HubSpot schema definition: property "annual_revenue" requires float64',
        'Inspected step input payload: "annual_revenue": "$1,200,000"',
        'Extracted regex clean pattern: s.replace(/[^0-9.-]+/g, "") -> 1200000.00'
      ]
    },
    proposed_action: {
      type: 'TRANSFORM_PAYLOAD_SCHEMA',
      title: 'Sanitize Currency String to Float64',
      description: 'Inject a sanitization transformation in node parameters converting currency strings to standard numeric float values before dispatching to HubSpot.',
      original_payload: {
        company: 'Acme Cloud Corp',
        email: 'admin@acmecloud.io',
        annual_revenue: '$1,200,000'
      },
      patched_payload: {
        company: 'Acme Cloud Corp',
        email: 'admin@acmecloud.io',
        annual_revenue: 1200000
      },
      dry_run_available: true,
      dry_run_result: {
        status: 'simulated_success',
        simulated_status_code: 201,
        message: 'Sandbox HubSpot mock accepted sanitized payload in 120ms.'
      }
    },
    policy: {
      status: 'REQUIRES_HUMAN_SIGN_OFF',
      policy_id: 'POL-DATA-MUTATION-03',
      name: 'External Write Payload Modification Policy',
      description: 'Changes to outbound payloads for external CRM databases require operator verification to prevent accidental data corruption.',
      is_auto_remediable: false
    }
  },
  {
    id: 'inc-4090',
    run_id: 'run-9812',
    workflow_id: 'wf-financial-report',
    workflow_name: 'Weekly Financial Anomaly Audit',
    failed_node_id: 'fetch_ledger',
    failed_node_title: 'Fetch Stripe Ledger',
    cluster_type: 'RATE_LIMIT_EXCEEDED',
    cluster_name: 'Stripe API 429 Throttle',
    severity: 'medium',
    status: 'pending_triage',
    created_at: '2026-11-01T15:20:00Z',
    blast_radius: {
      affected_runs_count: 1,
      downstream_blocked: ['Anomaly Analysis', 'CFO Sign-off'],
      financial_risk: 'None'
    },
    diagnosis: {
      summary: 'Stripe API returned 429 Too Many Requests due to burst limit exhaustion during concurrent bulk queries.',
      root_cause: 'Default retry policy lacked exponential backoff with jitter on HTTP 429 headers.',
      confidence: 0.99,
      reasoning_steps: [
        'Detected response header Retry-After: 45',
        'Current node retry config: 3 retries at fixed 1000ms delay',
        'Recommended policy: Jittered exponential backoff respecting Retry-After header'
      ]
    },
    proposed_action: {
      type: 'EXPONENTIAL_BACKOFF_RETRY',
      title: 'Apply Jittered Backoff & Replay',
      description: 'Configure node retry with exponential backoff (base 2s, max 60s) and immediately resume workflow execution with backoff offset.',
      original_payload: { retry_policy: { type: 'fixed', interval_sec: 1 } },
      patched_payload: { retry_policy: { type: 'exponential_jitter', base_sec: 2, max_sec: 60, respect_headers: true } },
      dry_run_available: true,
      dry_run_result: {
        status: 'simulated_success',
        simulated_status_code: 200,
        message: 'Endpoint rate-limit bucket verified clear. Replay is safe to proceed.'
      }
    },
    policy: {
      status: 'COMPLIANT_AUTO_APPROVABLE',
      policy_id: 'POL-INFRA-RETRY-01',
      name: 'Safe Transient Retry Policy',
      description: 'Retry configuration adjustments for read-only idempotent endpoints are pre-approved under SLA guidelines.',
      is_auto_remediable: true
    }
  }
];

export const SEED_APPROVALS = [
  {
    id: 'appr-701',
    run_id: 'run-9840',
    workflow_id: 'wf-financial-report',
    workflow_name: 'Weekly Financial Anomaly Audit',
    node_id: 'cfo_approval_step',
    node_title: 'CFO Discrepancy Sign-off',
    step_id: 'step_4',
    title: 'High-Value Outlier Transaction Verification ($45,000.00)',
    description: 'An outlier transaction was flagged for customer "Nexus Logic Ltd" exceeding 3-sigma deviance from the 90-day moving average.',
    urgency: 'critical',
    status: 'pending',
    requested_at: '2026-11-01T17:15:02Z',
    expires_at: '2026-11-02T17:15:02Z',
    requester: {
      type: 'AI_AGENT',
      name: 'Financial Auditor Agent (Llama 3.3 70B)',
      model: 'llama-3.3-70b-versatile'
    },
    target_roles: ['CFO', 'VP Finance', 'Compliance Officer'],
    context_data: {
      anomaly_id: 'anom_041',
      customer_name: 'Nexus Logic Ltd',
      amount_usd: 45000.00,
      historical_mean_usd: 3200.00,
      deviance_sigmas: 3.84,
      stripe_charge_id: 'ch_3Mx89201a',
      reason_code: 'OUTLIER_BURST_VOLUME'
    },
    action_preview: {
      type: 'DISPATCH_SECURITY_ESCROW_ALERT',
      summary: 'Approving this action will freeze the transaction settlement in escrow and alert the risk committee on Slack #finance-audit.',
      outbound_payload: {
        action: 'HOLD_SETTLEMENT',
        charge_id: 'ch_3Mx89201a',
        escrow_hold_hours: 48,
        notify_channels: ['#finance-audit', '#risk-ops'],
        cfo_signoff: true
      }
    },
    policy_checks: [
      { name: 'Dual-Custody Exemption', passed: true, note: 'Amount exceeds $25,000 threshold requiring executive sign-off.' },
      { name: 'Audit Trail Signature', passed: true, note: 'Cryptographic signature of action token ready.' },
      { name: 'SLA Window', passed: true, note: '23h 40m remaining before automatic escalation.' }
    ]
  },
  {
    id: 'appr-702',
    run_id: 'run-9830',
    workflow_id: 'wf-support-auto',
    workflow_name: 'Support Ticket Intelligent Resolver',
    node_id: 'draft_reply_approval',
    node_title: 'Rep Review Auto-Draft',
    step_id: 'step_3',
    title: 'Outbound Executive Customer Response Approval',
    description: 'Inbound email detected from Tier-1 Strategic Partner CEO regarding SLA credits. AI generated response requires human sign-off.',
    urgency: 'high',
    status: 'pending',
    requested_at: '2026-11-01T16:50:00Z',
    expires_at: '2026-11-01T20:50:00Z',
    requester: {
      type: 'AI_AGENT',
      name: 'Support Intent Classifier',
      model: 'llama-3.3-70b-versatile'
    },
    target_roles: ['Support Lead', 'Customer Success Director'],
    context_data: {
      thread_id: 'th_0912',
      sender_name: 'David Keller (CEO, Apex Cloud)',
      sender_email: 'dkeller@apexcloud.io',
      sentiment: 'frustrated',
      topic: 'Downtime SLA Credit Request'
    },
    action_preview: {
      type: 'SEND_GMAIL_RESPONSE',
      summary: 'Send personalized email response acknowledging the incident and providing a preliminary $500 credit token.',
      draft_email: {
        to: 'dkeller@apexcloud.io',
        subject: 'Re: AutoFlow AI Platform Incident & SLA Credit',
        body: `Dear David,\n\nThank you for reaching out, and please accept our apologies for the service interruption earlier this week. We have credited your account with $500 in accordance with our 99.9% uptime guarantee.\n\nOur engineering team has published a post-mortem here: status.autoflow.ai/incident/482.\n\nBest regards,\nAutoFlow Executive Support`
      }
    },
    policy_checks: [
      { name: 'Credit Limit Policy', passed: true, note: '$500 credit is within tier limit ($1,000 max).' },
      { name: 'PII Scrubbing', passed: true, note: 'No customer passwords or internal tokens detected in draft.' }
    ]
  }
];

// ─── STATEFUL LOCAL STORAGE CONTROLLER ──────────────────────────────────────

class MockDataService {
  constructor() {
    this._initStorage();
  }

  _initStorage() {
    if (typeof window === 'undefined') return;
    if (!localStorage.getItem(STORAGE_KEYS.WORKFLOWS)) {
      localStorage.setItem(STORAGE_KEYS.WORKFLOWS, JSON.stringify(SEED_WORKFLOWS));
    }
    if (!localStorage.getItem(STORAGE_KEYS.RUNS)) {
      localStorage.setItem(STORAGE_KEYS.RUNS, JSON.stringify(SEED_RUNS));
    }
    if (!localStorage.getItem(STORAGE_KEYS.INCIDENTS)) {
      localStorage.setItem(STORAGE_KEYS.INCIDENTS, JSON.stringify(SEED_RECOVERY_INCIDENTS));
    }
    if (!localStorage.getItem(STORAGE_KEYS.APPROVALS)) {
      localStorage.setItem(STORAGE_KEYS.APPROVALS, JSON.stringify(SEED_APPROVALS));
    }
  }

  _get(key, fallback = []) {
    try {
      const data = localStorage.getItem(key);
      return data ? JSON.parse(data) : fallback;
    } catch (_) {
      return fallback;
    }
  }

  _set(key, val) {
    try {
      localStorage.setItem(key, JSON.stringify(val));
    } catch (e) {
      console.warn('LocalStorage save failed:', e);
    }
  }

  // ── Workflows ─────────────────────────────────────────────────────────────
  getWorkflows() {
    return this._get(STORAGE_KEYS.WORKFLOWS, SEED_WORKFLOWS);
  }

  getWorkflowById(id) {
    const list = this.getWorkflows();
    return list.find(w => w.id === id) || null;
  }

  saveWorkflow(workflow) {
    const list = this.getWorkflows();
    const idx = list.findIndex(w => w.id === workflow.id);
    if (idx >= 0) {
      list[idx] = { ...list[idx], ...workflow, updated_at: new Date().toISOString() };
    } else {
      list.unshift({
        ...workflow,
        id: workflow.id || `wf-${Date.now()}`,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      });
    }
    this._set(STORAGE_KEYS.WORKFLOWS, list);
    return workflow;
  }

  // ── Runs & Timeline ───────────────────────────────────────────────────────
  getRuns({ workflow_id, status } = {}) {
    let list = this._get(STORAGE_KEYS.RUNS, SEED_RUNS);
    if (workflow_id) list = list.filter(r => r.workflow_id === workflow_id);
    if (status && status !== 'all') list = list.filter(r => r.status === status);
    return list;
  }

  getRunById(id) {
    const list = this._get(STORAGE_KEYS.RUNS, SEED_RUNS);
    return list.find(r => r.id === id) || null;
  }

  triggerRun(workflowId, triggerPayload = {}) {
    const wf = this.getWorkflowById(workflowId);
    const newRun = {
      id: `run-${Math.floor(1000 + Math.random() * 9000)}`,
      workflow_id: workflowId,
      workflow_name: wf?.name || 'Manual Workflow Run',
      status: 'running',
      started_at: new Date().toISOString(),
      completed_at: null,
      duration_ms: 0,
      trigger_type: 'manual',
      idempotency_key: `idem-man-${Date.now()}`,
      workflow_version: wf?.version || '1.0.0',
      error_summary: null,
      step_logs: (wf?.dsl?.nodes || []).map((node, index) => ({
        step_id: `step_${index + 1}`,
        node_id: node.id,
        node_title: node.title,
        status: index === 0 ? 'running' : 'pending',
        duration_ms: index === 0 ? 320 : 0,
        started_at: index === 0 ? new Date().toISOString() : null,
        completed_at: null,
        input: triggerPayload,
        output: null
      }))
    };

    const runs = this._get(STORAGE_KEYS.RUNS, SEED_RUNS);
    runs.unshift(newRun);
    this._set(STORAGE_KEYS.RUNS, runs);
    return newRun;
  }

  // ── Recovery Incidents ────────────────────────────────────────────────────
  getIncidents({ status } = {}) {
    let list = this._get(STORAGE_KEYS.INCIDENTS, SEED_RECOVERY_INCIDENTS);
    if (status && status !== 'all') list = list.filter(i => i.status === status);
    return list;
  }

  getIncidentById(id) {
    const list = this.getIncidents();
    return list.find(i => i.id === id) || null;
  }

  applyRecoveryPatch(incidentId, customPatch = null) {
    const incidents = this.getIncidents();
    const idx = incidents.findIndex(i => i.id === incidentId);
    if (idx === -1) throw new Error('Incident not found');

    const incident = incidents[idx];
    incident.status = 'resolved';
    incident.resolved_at = new Date().toISOString();
    incident.resolution_type = customPatch ? 'CUSTOM_INLINE_PATCH' : 'APPLIED_AI_PROPOSED_PATCH';
    incidents[idx] = incident;
    this._set(STORAGE_KEYS.INCIDENTS, incidents);

    // Also update associated run
    const runs = this._get(STORAGE_KEYS.RUNS, SEED_RUNS);
    const runIdx = runs.findIndex(r => r.id === incident.run_id);
    if (runIdx >= 0) {
      runs[runIdx].status = 'succeeded';
      runs[runIdx].recovered_at = new Date().toISOString();
      runs[runIdx].error_summary = null;
      // Mark failed step as resolved
      runs[runIdx].step_logs = runs[runIdx].step_logs.map(s => {
        if (s.node_id === incident.failed_node_id) {
          return {
            ...s,
            status: 'success',
            output: customPatch || incident.proposed_action.patched_payload,
            error: null
          };
        }
        return s;
      });
      this._set(STORAGE_KEYS.RUNS, runs);
    }

    return incident;
  }

  dismissIncident(incidentId, reason = 'Dismissed by operator') {
    const incidents = this.getIncidents();
    const idx = incidents.findIndex(i => i.id === incidentId);
    if (idx >= 0) {
      incidents[idx].status = 'dismissed';
      incidents[idx].dismissed_reason = reason;
      incidents[idx].dismissed_at = new Date().toISOString();
      this._set(STORAGE_KEYS.INCIDENTS, incidents);
    }
  }

  // ── Approvals Queue ───────────────────────────────────────────────────────
  getApprovals({ status } = {}) {
    let list = this._get(STORAGE_KEYS.APPROVALS, SEED_APPROVALS);
    if (status && status !== 'all') list = list.filter(a => a.status === status);
    return list;
  }

  getApprovalById(id) {
    const list = this.getApprovals();
    return list.find(a => a.id === id) || null;
  }

  reviewApproval(approvalId, decision, comments = '') {
    const approvals = this.getApprovals();
    const idx = approvals.findIndex(a => a.id === approvalId);
    if (idx === -1) throw new Error('Approval request not found');

    const item = approvals[idx];
    item.status = decision === 'APPROVED' ? 'approved' : 'rejected';
    item.decision = decision;
    item.decision_notes = comments;
    item.decided_at = new Date().toISOString();
    item.decided_by = 'Security Operator (You)';
    approvals[idx] = item;
    this._set(STORAGE_KEYS.APPROVALS, approvals);

    // If approved, update run step from paused to success
    const runs = this._get(STORAGE_KEYS.RUNS, SEED_RUNS);
    const runIdx = runs.findIndex(r => r.id === item.run_id);
    if (runIdx >= 0) {
      if (decision === 'APPROVED') {
        runs[runIdx].status = 'succeeded';
        runs[runIdx].step_logs = runs[runIdx].step_logs.map(s => {
          if (s.node_id === item.node_id) {
            return {
              ...s,
              status: 'success',
              output: {
                approved: true,
                signer: item.decided_by,
                timestamp: item.decided_at,
                notes: comments
              }
            };
          }
          return s;
        });
      } else {
        runs[runIdx].status = 'cancelled';
        runs[runIdx].error_summary = `Approval rejected: ${comments || 'Action denied by operator'}`;
      }
      this._set(STORAGE_KEYS.RUNS, runs);
    }

    return item;
  }

  resetToDefaults() {
    this._set(STORAGE_KEYS.WORKFLOWS, SEED_WORKFLOWS);
    this._set(STORAGE_KEYS.RUNS, SEED_RUNS);
    this._set(STORAGE_KEYS.INCIDENTS, SEED_RECOVERY_INCIDENTS);
    this._set(STORAGE_KEYS.APPROVALS, SEED_APPROVALS);
  }
}

export const mockService = new MockDataService();
