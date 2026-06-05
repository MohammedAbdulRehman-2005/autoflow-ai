const WORKFLOWS_KEY = 'autoflow_workflows_data';
const LOGS_KEY = 'autoflow_logs_data';

export const INITIAL_TEMPLATES = [
  {
    id: 'tpl-pdf-sys',
    title: 'PDF Summary Generator',
    description: 'Scans recently uploaded course syllabi, files, or scientific paper PDFs, and generates concise, structured AI takeaways, definitions, and study summaries.',
    category: 'Document Processing',
    installs: 1480,
    trigger: 'PDF Uploaded',
    action: 'Generate AI Summary',
    complexity: 'Medium'
  },
  {
    id: 'tpl-meet-notes',
    title: 'Meeting Notes Workflow',
    description: 'Takes uploaded seminar and consultation audio files, automatically transcribes the discussion, and crafts precise summaries, notes, and action items.',
    category: 'Meeting Reminders',
    installs: 920,
    trigger: 'Meeting Recording Uploaded',
    action: 'Generate Notes and Action Items',
    complexity: 'Medium'
  },
  {
    id: 'tpl-research-asst',
    title: 'Research Assistant',
    description: 'Queries open scientific citations and academic paper listings in real-time, delivering aggregated literature reports on any specified topic.',
    category: 'AI Task Automation',
    installs: 2450,
    trigger: 'Research Query Submitted',
    action: 'Generate Research Summary',
    complexity: 'Advanced'
  },
  {
    id: 'tpl-qna-asst',
    title: 'Document Q&A Assistant',
    description: 'Ingests heavy slides and texts so you can query questions on local lecture slides, returning targeted chapter mappings and responses.',
    category: 'Document Processing',
    installs: 1890,
    trigger: 'Document Uploaded',
    action: 'Answer Questions From Document',
    complexity: 'Advanced'
  },
  {
    id: 'tpl-email-class',
    title: 'Email Classification Workflow',
    description: 'Checks student and project inboxes to smartly label core priority threads, separating grading alerts and advisor schedules from standard newsletters.',
    category: 'Email Automation',
    installs: 1560,
    trigger: 'New Email Received',
    action: 'Categorize and Prioritize',
    complexity: 'Easy'
  },
  {
    id: 'tpl-smart-planner',
    title: 'Smart Task Planner',
    description: 'Input study routine and dates in pure English to build step-by-step revision timelines and automatically sync schedules into task databases.',
    category: 'Student Productivity Automation',
    installs: 1340,
    trigger: 'Natural Language Task Input',
    action: 'Generate Task Schedule',
    complexity: 'Medium'
  },
  {
    id: 'tpl-1',
    title: 'Email Summary Generator',
    description: 'Scans incoming academic and personal emails via Gmail, identifies crucial homework and assignment deadlines using AI, and logs summaries to a priority workspace dashboard.',
    category: 'Email Automation',
    installs: 1840,
    trigger: 'Gmail: New Email Received',
    action: 'Task Priority Dashboard Sync',
    complexity: 'Medium'
  },
  {
    id: 'tpl-2',
    title: 'Telegram Alert Workflow',
    description: 'Monitors class announcements or syllabus webpage HTML modifications, compiling instant summarized notifications sent directly to your Telegram study group.',
    category: 'Telegram Notifications',
    installs: 1420,
    trigger: 'Page Monitor: syllabus changed',
    action: 'Telegram Group Message Dispatch',
    complexity: 'Easy'
  }
];

export const INITIAL_WORKFLOWS = [
  {
    id: 'wf-1',
    name: 'Email Monitoring Trigger',
    description: 'Scans student inbox for assignment deadlines from professors, compiles task cards, and publishes study guides.',
    status: 'active',
    lastRun: '2 minutes ago',
    successRate: 98.4,
    runsCount: 145,
    trigger: 'Email: Academic Ingest',
    action: 'Telegram Group Message Dispatch',
    createdAt: '2026-05-15T09:00:00Z',
    nodes: [
      { id: 'n1', type: 'trigger', title: 'Email Monitoring', description: 'When a user receives important academic emails', icon: 'Email', config: {} },
      { id: 'n2', type: 'ai_planner', title: 'AI Workflow Planner', description: 'Generate structured markdown study plans', icon: 'Brain', config: {} },
      { id: 'n3', type: 'action', title: 'Telegram Notification', description: 'Notify private Telegram study channel', icon: 'Telegram', config: {} }
    ],
    connections: [
      { from: 'n1', to: 'n2' },
      { from: 'n2', to: 'n3' }
    ]
  },
  {
    id: 'wf-2',
    name: 'Telegram Notification Workflow',
    description: 'Monitors bibliography folder uploads, analyzes research paper drafts via AI, and broadcasts study flashcards.',
    status: 'active',
    lastRun: '2 hours ago',
    successRate: 100,
    runsCount: 840,
    trigger: 'Drive: Research PDF Upload',
    action: 'Telegram Send Message',
    createdAt: '2026-05-20T10:15:00Z',
    nodes: [
      { id: 'trig-1', type: 'trigger', title: 'PDF Document Listener', description: 'At research folder watch', icon: 'GoogleDrive', config: {} },
      { id: 'audit-2', type: 'ai_planner', title: 'AI Synthesizer', description: 'Draft revision notes and quiz cards', icon: 'Brain', config: {} },
      { id: 'action-3', type: 'action', title: 'Telegram Push Alert', description: 'Deliver summaries directly to mobile logs', icon: 'CheckSquare', config: {} }
    ],
    connections: [
      { from: 'trig-1', to: 'audit-2' },
      { from: 'audit-2', to: 'action-3' }
    ]
  },
  {
    id: 'wf-3',
    name: 'Meeting Scheduler Workflow',
    description: 'Parses advisor booking requests, generates calendar events on Google Calendar, and updates consultation logs.',
    status: 'active',
    lastRun: '5 hours ago',
    successRate: 96.8,
    runsCount: 312,
    trigger: 'Calendar: Consultation Requested',
    action: 'Google Calendar Batch Sync',
    createdAt: '2026-04-12T14:30:00Z',
    nodes: [
      { id: 'cal-1', type: 'trigger', title: 'Booking Request Received', description: 'When coordinator books session', icon: 'Calendar', config: {} },
      { id: 'match-2', type: 'ai_planner', title: 'AI Availability Solver', description: 'Skins time blocks and flags conflicts', icon: 'Brain', config: {} },
      { id: 'green-3', type: 'action', title: 'Send Google Calendar Invite', description: 'Deploys calendar details & link', icon: 'Database', config: {} }
    ],
    connections: [
      { from: 'cal-1', to: 'match-2' },
      { from: 'match-2', to: 'green-3' }
    ]
  },
  {
    id: 'wf-4',
    name: 'Student Productivity Tracker',
    description: 'Aggregates homework due dates, formats task lists, and saves automated summaries inside a synchronized check sheet.',
    status: 'draft',
    lastRun: 'Never',
    successRate: 0,
    runsCount: 0,
    trigger: 'Task Board: Due Status Changed',
    action: 'Daily Summary Email Dispatch',
    createdAt: '2026-05-28T16:00:00Z',
    nodes: [
      { id: 'trig-1', type: 'trigger', title: 'Set Routine Scheduler', description: 'Fires every day at 8:00 AM', icon: 'Clock', config: {} },
      { id: 'ai-2', type: 'ai_planner', title: 'AI Syllabus Analyzer', description: 'Calculates countdown values and ranks tasks', icon: 'Brain', config: {} },
      { id: 'act-3', type: 'action', title: 'Update Study Log Database', description: 'Populates active Notion study trackers', icon: 'BookOpen', config: {} }
    ],
    connections: [
      { from: 'trig-1', to: 'ai-2' },
      { from: 'ai-2', to: 'act-3' }
    ]
  }
];

export const INITIAL_LOGS = [
  {
    id: 'log-1',
    workflowId: 'wf-1',
    workflowName: 'Email Monitoring Trigger',
    status: 'success',
    duration: '1.24s',
    timestamp: '2026-06-02T17:12:00Z',
    triggerEvent: 'New email from: Prof. Alice Vance [CS-501 assignment update]'
  },
  {
    id: 'log-2',
    workflowId: 'wf-2',
    workflowName: 'Telegram Notification Workflow',
    status: 'success',
    duration: '0.98s',
    timestamp: '2026-06-02T15:14:00Z',
    triggerEvent: 'Sent paper summary for "Attention is All You Need" to Telegram group'
  },
  {
    id: 'log-3',
    workflowId: 'wf-1',
    workflowName: 'Email Monitoring Trigger',
    status: 'success',
    duration: '2.40s',
    timestamp: '2026-06-02T14:45:00Z',
    triggerEvent: 'New email from: Dean of Students [Weekly Campus News & Alerts]'
  },
  {
    id: 'log-4',
    workflowId: 'wf-3',
    workflowName: 'Meeting Scheduler Workflow',
    status: 'success',
    duration: '3.12s',
    timestamp: '2026-06-02T12:30:00Z',
    triggerEvent: 'Scheduled office hours meeting with Advisor Robert on Google Calendar'
  },
  {
    id: 'log-5',
    workflowId: 'wf-1',
    workflowName: 'Email Monitoring Trigger',
    status: 'failed',
    duration: '0.45s',
    timestamp: '2026-06-02T11:00:00Z',
    triggerEvent: 'Failed to access mailbox',
    errorMessage: 'Gmail IMAP server timeout. Token validation expired.'
  },
  {
    id: 'log-6',
    workflowId: 'wf-2',
    workflowName: 'Telegram Notification Workflow',
    status: 'success',
    duration: '1.05s',
    timestamp: '2026-06-02T10:15:00Z',
    triggerEvent: 'Broadcasted study flashcards regarding midterm exam schedule'
  },
  {
    id: 'log-7',
    workflowId: 'wf-3',
    workflowName: 'Meeting Scheduler Workflow',
    status: 'failed',
    duration: '1.10s',
    timestamp: '2026-06-02T08:00:00Z',
    triggerEvent: 'Syllabus parser error on uploaded file: scanned_sheet.jpg',
    errorMessage: 'Failed to extract text structures. Low-contrast or corrupted file pixels.'
  },
  {
    id: 'log-8',
    workflowId: 'wf-1',
    workflowName: 'Email Monitoring Trigger',
    status: 'running',
    duration: '...',
    timestamp: '2026-06-02T17:14:30Z',
    triggerEvent: 'Processing email subject: "CS-501 Project Milestones Submission"'
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