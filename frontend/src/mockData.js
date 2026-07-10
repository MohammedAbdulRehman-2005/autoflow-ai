const WORKFLOWS_KEY = 'autoflow_workflows_data';
const LOGS_KEY = 'autoflow_logs_data';

export const INITIAL_TEMPLATES = [
  {
    id: 'tpl-lead-slack',
    title: 'New Lead → Slack Alert',
    description: 'The moment a new lead lands in Salesforce, your sales team gets an instant Slack notification with the lead\'s name, company, and deal value — so no lead sits untouched.',
    category: 'Sales & CRM',
    trigger: 'Salesforce: New Lead Created',
    action: 'Slack Channel Notification'
  },
  {
    id: 'tpl-deal-won',
    title: 'Deal Won → Update Sheet + Notify Team',
    description: 'When a HubSpot deal is marked "Closed Won," this workflow logs the deal to a Google Sheet for reporting and posts a celebration message to your team Slack channel.',
    category: 'Sales & CRM',
    trigger: 'HubSpot: Deal Stage = Closed Won',
    action: 'Google Sheets Row + Slack Message'
  },
  {
    id: 'tpl-stripe-failed',
    title: 'Failed Payment → Team Alert',
    description: 'Catches failed Stripe charges in real time and immediately notifies your billing team on Slack, so retries and customer outreach happen before revenue is lost.',
    category: 'Payments & Billing',
    trigger: 'Stripe: Charge Failed',
    action: 'Slack Billing Channel Alert'
  },
  {
    id: 'tpl-invoice-paid',
    title: 'Invoice Paid → Update CRM Record',
    description: 'When a Stripe invoice is paid, this workflow automatically marks the matching Salesforce account as "Paid" and logs the payment date — keeping your CRM in sync without manual entry.',
    category: 'Payments & Billing',
    trigger: 'Stripe: Invoice Paid',
    action: 'Salesforce Record Update'
  },
  {
    id: 'tpl-daily-digest',
    title: 'Daily Sales Digest Email',
    description: 'Every morning, this workflow pulls the previous day\'s sales totals from Google Sheets, summarizes performance with AI, and emails a clean digest to leadership via Gmail.',
    category: 'Email Automation',
    trigger: 'Scheduled: Daily at 8:00 AM',
    action: 'Gmail Summary Report'
  },
  {
    id: 'tpl-contact-notion',
    title: 'New Contact → Notion Knowledge Base',
    description: 'Automatically syncs new HubSpot contacts into a Notion database, giving your team a searchable, always-up-to-date client directory without duplicate data entry.',
    category: 'Document & Knowledge Base',
    trigger: 'HubSpot: New Contact Created',
    action: 'Notion Database Entry'
  },
  {
    id: 'tpl-meeting-booked',
    title: 'Meeting Booked → Calendar + Slack Confirmation',
    description: 'When a client books a meeting, this workflow creates the Google Calendar event and posts a confirmation in Slack so the right team members are looped in instantly.',
    category: 'Calendar & Scheduling',
    trigger: 'Google Calendar: New Event Booked',
    action: 'Slack Confirmation Message',
  },
  {
    id: 'tpl-weekly-report',
    title: 'Weekly Performance Report Generator',
    description: 'Aggregates the week\'s sales and support activity from Google Sheets, uses AI to write an executive summary, and publishes it as a formatted Notion report every Friday.',
    category: 'Document & Knowledge Base',
    trigger: 'Scheduled: Weekly on Friday',
    action: 'AI Summary → Notion Report'
  },
];

export const INITIAL_LOGS = [
  {
    id: 'log-1',
    workflowId: 'wf-1',
    workflowName: 'New Lead Alert Workflow',
    status: 'success',
    duration: '1.24s',
    timestamp: '2026-06-02T17:12:00Z',
    triggerEvent: 'New lead created in Salesforce: "Acme Corp — Jordan Lee"'
  },
  {
    id: 'log-2',
    workflowId: 'wf-2',
    workflowName: 'Failed Payment Alert Workflow',
    status: 'success',
    duration: '0.98s',
    timestamp: '2026-06-02T15:14:00Z',
    triggerEvent: 'Sent billing alert for declined charge on account #4471'
  },
  {
    id: 'log-3',
    workflowId: 'wf-1',
    workflowName: 'New Lead Alert Workflow',
    status: 'success',
    duration: '2.40s',
    timestamp: '2026-06-02T14:45:00Z',
    triggerEvent: 'New lead created in Salesforce: "Northwind Traders — Priya Shah"'
  },
  {
    id: 'log-4',
    workflowId: 'wf-3',
    workflowName: 'Meeting Booking Workflow',
    status: 'success',
    duration: '3.12s',
    timestamp: '2026-06-02T12:30:00Z',
    triggerEvent: 'Booked discovery call with client on Google Calendar'
  },
  {
    id: 'log-5',
    workflowId: 'wf-2',
    workflowName: 'Failed Payment Alert Workflow',
    status: 'failed',
    duration: '0.45s',
    timestamp: '2026-06-02T11:00:00Z',
    triggerEvent: 'Failed to reach Stripe API',
    errorMessage: 'Stripe webhook timeout. Token validation expired.'
  },
  {
    id: 'log-6',
    workflowId: 'wf-1',
    workflowName: 'New Lead Alert Workflow',
    status: 'success',
    duration: '1.05s',
    timestamp: '2026-06-02T10:15:00Z',
    triggerEvent: 'Slack alert delivered to #sales-leads for lead "Berkshire Tools"'
  },
  {
    id: 'log-7',
    workflowId: 'wf-3',
    workflowName: 'Meeting Booking Workflow',
    status: 'failed',
    duration: '1.10s',
    timestamp: '2026-06-02T08:00:00Z',
    triggerEvent: 'Calendar sync error for requested time slot',
    errorMessage: 'Google Calendar API returned a conflict — slot already booked.'
  },
  {
    id: 'log-8',
    workflowId: 'wf-1',
    workflowName: 'New Lead Alert Workflow',
    status: 'running',
    duration: '...',
    timestamp: '2026-06-02T17:14:30Z',
    triggerEvent: 'Processing new lead: "Vertex Solutions — Marcus Chen"'
  }
];

export const INITIAL_WORKFLOWS = [
  {
    id: 'wf-1',
    name: 'New Lead Alert Workflow',
    description: 'Watches Salesforce for new leads, enriches them with AI-summarized context, and pings the sales team on Slack instantly.',
    status: 'active',
    lastRun: '2 minutes ago',
    successRate: 98.4,
    runsCount: 145,
    trigger: 'Salesforce: New Lead Created',
    action: 'Slack Channel Notification',
    createdAt: '2026-05-15T09:00:00Z',
    nodes: [
      { id: 'n1', type: 'trigger', title: 'New Lead Trigger', description: 'When a new lead is created in Salesforce', icon: 'Database', config: {} },
      { id: 'n2', type: 'ai_planner', title: 'AI Lead Summarizer', description: 'Generates a quick context summary for the sales team', icon: 'Brain', config: {} },
      { id: 'n3', type: 'action', title: 'Slack Notification', description: 'Posts lead details to #sales-leads channel', icon: 'Slack', config: {} }
    ],
    connections: [
      { from: 'n1', to: 'n2' },
      { from: 'n2', to: 'n3' }
    ]
  },
  {
    id: 'wf-2',
    name: 'Failed Payment Alert Workflow',
    description: 'Monitors Stripe for failed charges, analyzes the failure reason with AI, and immediately alerts the billing team on Slack.',
    status: 'active',
    lastRun: '2 hours ago',
    successRate: 100,
    runsCount: 840,
    trigger: 'Stripe: Charge Failed',
    action: 'Slack Billing Alert',
    createdAt: '2026-05-20T10:15:00Z',
    nodes: [
      { id: 'trig-1', type: 'trigger', title: 'Payment Failure Listener', description: 'Fires on any failed Stripe charge', icon: 'CreditCard', config: {} },
      { id: 'audit-2', type: 'ai_planner', title: 'AI Failure Analyzer', description: 'Classifies decline reason and suggests next step', icon: 'Brain', config: {} },
      { id: 'action-3', type: 'action', title: 'Slack Billing Alert', description: 'Notifies #billing channel with account details', icon: 'Slack', config: {} }
    ],
    connections: [
      { from: 'trig-1', to: 'audit-2' },
      { from: 'audit-2', to: 'action-3' }
    ]
  },
  {
    id: 'wf-3',
    name: 'Meeting Booking Workflow',
    description: 'Parses inbound meeting requests, creates the Google Calendar event, and sends a Slack confirmation to the assigned rep.',
    status: 'active',
    lastRun: '5 hours ago',
    successRate: 96.8,
    runsCount: 312,
    trigger: 'Google Calendar: New Event Booked',
    action: 'Slack Confirmation Message',
    createdAt: '2026-04-12T14:30:00Z',
    nodes: [
      { id: 'cal-1', type: 'trigger', title: 'Booking Request Received', description: 'When a client books a meeting slot', icon: 'Calendar', config: {} },
      { id: 'match-2', type: 'ai_planner', title: 'AI Availability Solver', description: 'Checks rep availability and resolves conflicts', icon: 'Brain', config: {} },
      { id: 'green-3', type: 'action', title: 'Send Slack Confirmation', description: 'Notifies rep with meeting details and link', icon: 'Slack', config: {} }
    ],
    connections: [
      { from: 'cal-1', to: 'match-2' },
      { from: 'match-2', to: 'green-3' }
    ]
  },
  {
    id: 'wf-4',
    name: 'Weekly Performance Report',
    description: 'Aggregates weekly sales data from Google Sheets, generates an AI executive summary, and publishes it to Notion every Friday.',
    status: 'draft',
    lastRun: 'Never',
    successRate: 0,
    runsCount: 0,
    trigger: 'Scheduled: Weekly on Friday',
    action: 'AI Summary → Notion Report',
    createdAt: '2026-05-28T16:00:00Z',
    nodes: [
      { id: 'trig-1', type: 'trigger', title: 'Weekly Schedule Trigger', description: 'Fires every Friday at 5:00 PM', icon: 'Clock', config: {} },
      { id: 'ai-2', type: 'ai_planner', title: 'AI Report Generator', description: 'Summarizes weekly performance data', icon: 'Brain', config: {} },
      { id: 'act-3', type: 'action', title: 'Publish to Notion', description: 'Creates a formatted report page in Notion', icon: 'FileText', config: {} }
    ],
    connections: [
      { from: 'trig-1', to: 'ai-2' },
      { from: 'ai-2', to: 'act-3' }
    ]
  }
];

export function getWorkflows() {
  const data = localStorage.getItem(WORKFLOWS_KEY);
  if (!data) {
    localStorage.setItem(WORKFLOWS_KEY, JSON.stringify(INITIAL_WORKFLOWS));
    return INITIAL_WORKFLOWS;
  }
  return JSON.parse(data);
}

export function saveWorkflows(workflows) {
  localStorage.setItem(WORKFLOWS_KEY, JSON.stringify(workflows));
}

export function getLogs() {
  const data = localStorage.getItem(LOGS_KEY);
  if (!data) {
    localStorage.setItem(LOGS_KEY, JSON.stringify(INITIAL_LOGS));
    return INITIAL_LOGS;
  }
  return JSON.parse(data);
}

export function saveLogs(logs) {
  localStorage.setItem(LOGS_KEY, JSON.stringify(logs));
}

export function addWorkflow(name, description, trigger, action, nodes, connections) {
  const workflows = getWorkflows();
  const newWorkflow = {
    id: `wf-${Date.now()}`,
    name,
    description,
    status: 'active',
    lastRun: 'Just now',
    successRate: 100,
    runsCount: 0,
    trigger,
    action,
    nodes: nodes || [
      { id: '1', type: 'trigger', title: trigger, description: 'Default trigger node', icon: 'Zap', config: {} },
      { id: '2', type: 'ai_planner', title: 'AI Automation Planner', description: 'Processes logic with Gemini', icon: 'Brain', config: {} },
      { id: '3', type: 'action', title: action, description: 'Performs final system integration', icon: 'Server', config: {} }
    ],
    connections: connections || [
      { from: '1', to: '2' },
      { from: '2', to: '3' }
    ],
    createdAt: new Date().toISOString()
  };
  const updated = [newWorkflow, ...workflows];
  saveWorkflows(updated);
  return newWorkflow;
}

export function simulateRunningWorkflow(workflowId) {
  const workflows = getWorkflows();
  const logs = getLogs();
  
  const wfIndex = workflows.findIndex(w => w.id === workflowId);
  if (wfIndex === -1) return;

  const wf = workflows[wfIndex];
  
  // Create a running log, then transitions to success or failure in a simulation
  const isFailedSimulation = Math.random() < 0.05; // 5% fail rate
  
  // Calculate new success rates
  const runTotal = wf.runsCount + 1;
  const oldRate = wf.successRate || 100;
  let newRate = ((oldRate * wf.runsCount) + (isFailedSimulation ? 0 : 100)) / runTotal;
  newRate = Math.min(100, Math.max(0, parseFloat(newRate.toFixed(1))));

  // Update workflow details
  workflows[wfIndex] = {
    ...wf,
    lastRun: '1s ago',
    runsCount: runTotal,
    successRate: newRate
  };
  saveWorkflows(workflows);

  // Add Log Entry
  const newLog = {
    id: `log-${Date.now()}`,
    workflowId: wf.id,
    workflowName: wf.name,
    status: isFailedSimulation ? 'failed' : 'success',
    duration: `${(0.8 + Math.random() * 2.5).toFixed(2)}s`,
    timestamp: new Date().toISOString(),
    triggerEvent: `Manual prompt trigger request`,
    errorMessage: isFailedSimulation ? 'Internal server timeout connecting to target endpoint.' : undefined
  };

  saveLogs([newLog, ...logs]);
}
