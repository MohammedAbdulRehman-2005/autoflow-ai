import { useState } from 'react';
import {
  GitBranch,
  Play,
  Save,
  Download,
  AlertCircle,
  Database,
  Brain,
  Zap,
  Radio,
  Server,
  Plus,
  ArrowRight,
  Terminal,
  RotateCw,
  Sparkles,
  RefreshCw,
  Sliders,
  CheckCircle2,
  Trash2
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { addWorkflow, simulateRunningWorkflow } from '../mockData';

export default function WorkflowBuilderPage() {
  const [workflowName, setWorkflowName] = useState('Academic Email to Telegram Dispatcher');
  const [workflowDesc, setWorkflowDesc] = useState('Monitors academic newsletters, extracts assignments, and flashes structured digests to student Telegram logs.');
  
  // Custom states that allow the user to modify the visual flow
  const [triggerNode, setTriggerNode] = useState({
    title: 'Email Monitoring',
    desc: 'Scans incoming course syllabus lists',
    channel: 'Gmail IMAP Poller',
    icon: 'zap'
  });
  const [aiNode, setAINode] = useState({
    title: 'Gemini AI Workflow Planner',
    desc: 'Synthesizes assignment timelines and drafts concise task briefs',
    channel: 'Gemini Pro Model',
    icon: 'brain'
  });
  const [actionNode, setActionNode] = useState({
    title: 'Telegram Notification',
    desc: 'Pushes formatted study warnings to private group',
    channel: 'Telegram Bot Botfather',
    icon: 'server'
  });

  const [naturalLanguagePrompt, setNaturalLanguagePrompt] = useState(
    'Scan my student inbox for new assignment announcements from profs, make a study guide outline, and send a structured alert to my Telegram chat.'
  );

  const [isTranslating, setIsTranslating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [activeTab, setActiveTab] = useState('config');

  // Logs terminal simulation state
  const [terminalLogs, setTerminalLogs] = useState([]);

  // Natural Language prompt translator simulator
  const handleTranslatePrompt = () => {
    setIsTranslating(true);
    setTerminalLogs(prev => [...prev, '🔄 Initializing Gemini prompt analysis...']);
    setTimeout(() => {
      // Intelligently map nodes based on what are the keywords in the active prompt
      const text = naturalLanguagePrompt.toLowerCase();
      
      let trig = { title: 'Email Monitoring', desc: 'Checks mailbox announcements from professors', channel: 'Gmail IMAP Poller', icon: 'zap' };
      let action = { title: 'Telegram Notification', desc: 'Pushes formatted study summaries', channel: 'Telegram Bot Botfather', icon: 'server' };

      if (text.includes('document') || text.includes('pdf') || text.includes('paper')) {
        trig = { title: 'PDF Document Listener', desc: 'At course slides and research papers uploads', channel: 'Google Drive Asset Ingestion', icon: 'zap' };
        action = { title: 'Notion Course Dashboard Upload', desc: 'Constructs custom summaries database card', channel: 'Notion Workspace API', icon: 'database' };
      } else if (text.includes('calendar') || text.includes('appointment') || text.includes('meeting')) {
        trig = { title: 'Booking Request Received', desc: 'Monitors calendar event booking invites', channel: 'Schedules Web Gateway', icon: 'zap' };
        action = { title: 'Send Google Calendar Invite', desc: 'Sends event reminders with study block dates', channel: 'Google Calendar Sync', icon: 'server' };
      } else if (text.includes('grade') || text.includes('portal')) {
        trig = { title: 'Student Grade Monitor', desc: 'Scans grading portals for status fluctuations', channel: 'HTTP Canvas Web Scraper', icon: 'zap' };
        action = { title: 'Local Alert Dispatcher', desc: 'Signals desktop urgent warning flash', channel: 'Desktop Notification Hub', icon: 'server' };
      }

      setTriggerNode(trig);
      setActionNode(action);
      
      setAINode({
        title: 'Gemini AI Workflow Planner',
        desc: 'Skins natural language text and schedules optimal study pipelines',
        channel: 'Gemini Pro Model',
        icon: 'brain'
      });

      setTerminalLogs(prev => [
        ...prev,
        '✨ Natural language triggers parsed by Gemini',
        `✅ Extracted TRIGGER Node: [${trig.title}]`,
        `✅ Extracted ACTION Node: [${action.title}]`,
        '🚀 Student workspace flow chart built successfully.'
      ]);
      setIsTranslating(false);
    }, 1500);
  };

  const handleSaveWorkflow = () => {
    setIsSaving(true);
    setTimeout(() => {
      // Save directly to static local lists so that the Dashboard updates its values!
      addWorkflow(
        workflowName,
        workflowDesc,
        triggerNode.title,
        actionNode.title,
        [triggerNode, aiNode, actionNode],
        [{ from: 'trigger', to: 'ai' }, { from: 'ai', to: 'action' }]
      );
      setIsSaving(false);
      setTerminalLogs(prev => [...prev, `💾 Successfully persists [${workflowName}] to local workflow ledger.`]);
      alert(`Workflow "${workflowName}" saved! You can find it deployed on your Dashboard page now.`);
    }, 1200);
  };

  const handleRunWorkflow = () => {
    setIsRunning(true);
    setActiveTab('logs');
    setTerminalLogs([
      '⚡ Direct injection command fired manually.',
      `🔍 Compiling graph sequence [${workflowName}]...`,
      `📡 Executing Node 1 (Trigger): [${triggerNode.title}]`,
      '📊 Ingest payload: { "auth": "ok", "timestamp": "2026-06-02T17:14:44Z", "actor": "Gemini System Client" }',
      '🤖 Calling LLM core optimizer: sending target token arrays...'
    ]);

    setTimeout(() => {
      setTerminalLogs(prev => [
        ...prev,
        `🧠 Ingesting parameters into [${aiNode.title}]`,
        '📝 LLM Response OK (Status: 200). Ensembled prompt translated standard arrays.'
      ]);

      setTimeout(() => {
        setTerminalLogs(prev => [
          ...prev,
          `📡 Transferring parsed payload to Node 3 (Action): [${actionNode.title}]`,
          '🎯 Integration client response headers matched positive results!',
          '🏁 Pipeline sequence finished. Duration: 1.48s. Return code: 0 SUCCESS.'
        ]);
        
        // Push actual Execution logs in localStorage
        const wfs = addWorkflow(workflowName, workflowDesc, triggerNode.title, actionNode.title);
        simulateRunningWorkflow(wfs.id);
        
        setIsRunning(false);
      }, 1000);
    }, 1200);
  };

  const handleExportWorkflow = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify({
      workflowName,
      workflowDesc,
      nodes: [triggerNode, aiNode, actionNode]
    }, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `${workflowName.toLowerCase().replace(/ /g, "_")}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
    setTerminalLogs(prev => [...prev, '📥 Download anchor fired. Core JSON structure exported.']);
  };

  return (
    <div className="space-y-8 select-none text-left">
      
      {/* Visual Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white font-display flex items-center gap-2">
            <GitBranch className="h-8 w-8 text-blue-500" />
            <span>Workflow Studio</span>
          </h1>
          <p className="text-sm text-slate-400 mt-1 font-sans">
            Draft, simulate and deploy natural language workflows using visual connectors.
          </p>
        </div>

        {/* Builder top buttons */}
        <div className="flex items-center space-x-2.5 self-start sm:self-auto">
          <button
            onClick={handleRunWorkflow}
            disabled={isRunning || isSaving || isTranslating}
            className="flex items-center space-x-1.5 px-3.5 py-2 hover:border-cyan-500/35 bg-cyan-500/15 text-cyan-400 border border-cyan-500/20 hover:bg-cyan-500 hover:text-slate-950 rounded-xl text-xs font-bold transition-all cursor-pointer disabled:opacity-50 shadow-sm"
          >
            {isRunning ? <RotateCw className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4 fill-current" />}
            <span>Run Workflow</span>
          </button>
          
          <button
            onClick={handleSaveWorkflow}
            disabled={isRunning || isSaving || isTranslating}
            className="flex items-center space-x-1.5 px-3.5 py-2 hover:border-blue-500/35 bg-blue-500/15 text-blue-400 border border-blue-500/20 hover:bg-blue-500 hover:text-slate-900 rounded-xl text-xs font-bold transition-all cursor-pointer disabled:opacity-50 shadow-sm"
          >
            {isSaving ? <RotateCw className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            <span>Save Workflow</span>
          </button>

          <button
            onClick={handleExportWorkflow}
            disabled={isRunning || isSaving || isTranslating}
            className="flex items-center space-x-1.5 px-3.5 py-2 border border-white/10 bg-white/5 hover:bg-white/10 text-slate-350 hover:text-white rounded-xl text-xs font-semibold cursor-pointer transition-all shadow-sm"
            title="Export Manifest"
          >
            <Download className="h-4 w-4" />
            <span className="hidden sm:inline">Export</span>
          </button>
        </div>
      </div>

      {/* Main visual interface panel columns */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left column: AI Generator & Workflow configuration parameters */}
        <div className="space-y-6">
          
          {/* AI natural language translation input boxes */}
          <div className="border border-white/10 rounded-3xl bg-white/5 p-5 backdrop-blur-lg relative overflow-hidden shadow-md">
            <div className="absolute top-0 right-0 h-20 w-20 rounded-full bg-blue-500/10 blur-xl pointer-events-none"></div>
            
            <div className="flex items-center space-x-1.5 mb-3.5">
              <Sparkles className="h-4.5 w-4.5 text-cyan-400 animate-pulse" />
              <h3 className="text-2xs font-bold text-cyan-400 tracking-wider font-mono">GENERATE PIPELINE VIA LLM</h3>
            </div>

            <textarea
              value={naturalLanguagePrompt}
              onChange={(e) => setNaturalLanguagePrompt(e.target.value)}
              placeholder="Describe your target app integration triggers..."
              rows={4}
              className="w-full text-xs text-slate-200 placeholder-slate-500 bg-white/5 border border-white/10 rounded-xl p-3 outline-none resize-none hover:border-white/20 focus:border-cyan-500/50 focus:bg-slate-900/20 transition-all font-sans font-semibold shadow-inner"
            />

            <button
               onClick={handleTranslatePrompt}
               disabled={isTranslating}
               className="w-full mt-3 flex items-center justify-center space-x-2 py-2.5 px-4 rounded-xl font-bold text-xs bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 text-white shadow-md active:scale-95 cursor-pointer disabled:opacity-50"
            >
               {isTranslating ? (
                <>
                   <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                   <span>Configuring Schema...</span>
                </>
              ) : (
                <>
                   <Sparkles className="h-3.5 w-3.5" />
                   <span>Translate to Trigger Nodes</span>
                </>
              )}
            </button>
          </div>

          {/* Workflow details edit cards */}
          <div className="border border-white/10 rounded-3xl bg-white/5 p-5 backdrop-blur-lg space-y-4 shadow-md">
            <h3 className="text-sm font-bold text-white mb-2 font-display">Workflow Configurations</h3>
            
            <div className="space-y-1 text-left">
              <label className="text-[10px] font-bold text-slate-450 tracking-wider font-display">WORKFLOW TITLE</label>
              <input
                type="text"
                value={workflowName}
                onChange={(e) => setWorkflowName(e.target.value)}
                className="w-full rounded-xl border border-white/10 bg-white/5 py-2.5 px-3.5 text-xs text-white placeholder-slate-550 outline-none hover:border-white/20 focus:border-blue-500/50 focus:bg-slate-900/40"
              />
            </div>

            <div className="space-y-1 text-left">
              <label className="text-[10px] font-bold text-slate-450 tracking-wider font-display">DESCRIPTION</label>
              <input
                type="text"
                value={workflowDesc}
                onChange={(e) => setWorkflowDesc(e.target.value)}
                className="w-full rounded-xl border border-white/10 bg-white/5 py-2.5 px-3.5 text-xs text-white placeholder-slate-550 outline-none hover:border-white/20 focus:border-blue-500/50 focus:bg-slate-900/40"
              />
            </div>
          </div>

          {/* Node parameter tweaking card */}
          <div className="border border-white/10 rounded-3xl bg-white/5 p-5 backdrop-blur-lg shadow-md">
            <h3 className="text-sm font-bold text-white mb-3 font-display">Trigger Environment</h3>
            <div className="space-y-3.5 text-left text-xs text-slate-400 font-medium">
              <div className="flex justify-between pb-1 border-b border-white/10">
                <span>Webhook SSL Check</span>
                <span className="text-cyan-400 font-mono font-bold">ENFORCED (TLS)</span>
              </div>
              <div className="flex justify-between pb-1 border-b border-white/10">
                <span>Max Request Queuing</span>
                <span className="font-mono">10,000 req/sec</span>
              </div>
              <div className="flex justify-between">
                <span>Gemini Backoff Limit</span>
                <span className="font-mono">5 Retries</span>
              </div>
            </div>
          </div>

        </div>

        {/* Center/Right side: The Visual Node Canvas flowchart viewport & logs */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* Canvas tab selectors */}
          <div className="flex border-b border-white/10">
            <button
              onClick={() => setActiveTab('config')}
              className={`pb-3.5 px-5 text-xs font-bold border-b-2 mr-2 cursor-pointer transition-all ${
                activeTab === 'config'
                  ? 'border-blue-500 text-white'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              Visual Flowchart Canvas
            </button>
            <button
              onClick={() => setActiveTab('logs')}
              className={`pb-3.5 px-5 text-xs font-bold border-b-2 cursor-pointer transition-all flex items-center space-x-1.5 ${
                activeTab === 'logs'
                  ? 'border-cyan-500 text-white'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <Terminal className="h-3.5 w-3.5 text-cyan-400" />
              <span>Flow Test Log Output Terminal</span>
            </button>
          </div>

          <div className="relative min-h-[460px] border border-white/10 rounded-3xl bg-[#020617]/30 backdrop-blur-lg p-8 flex flex-col justify-between overflow-hidden shadow-md">
            {/* Grid dot pattern overlay */}
            <div className="absolute inset-0 bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:16px_16px] pointer-events-none opacity-40"></div>

            <AnimatePresence mode="wait">
              {activeTab === 'config' ? (
                <motion.div
                  key="canvas"
                  initial={{ opacity: 0, scale: 0.98 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.98 }}
                  className="flex-1 flex flex-col items-center justify-center space-y-8 relative z-10 py-4"
                >
                  
                  {/* Node 1: Webhook Trigger Node */}
                  <motion.div
                    whileHover={{ scale: 1.02, y: -2 }}
                    className="w-full max-w-md p-4 bg-white/5 border-2 border-blue-500/20 hover:border-blue-500/40 rounded-2xl flex items-center justify-between text-left relative shadow-lg shadow-blue-500/2 shadow-blue-600/5 backdrop-blur-md group"
                  >
                    <div className="flex items-center space-x-4">
                      <div className="p-3 bg-blue-500/10 text-blue-400 rounded-xl shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)] border border-blue-500/10">
                        <Zap className="h-5 w-5 animate-pulse" />
                      </div>
                      <div>
                        <span className="text-[10px] font-bold text-blue-400 tracking-widest font-mono">STAGE 1: TRIGGER NODE</span>
                        <h4 className="text-sm font-bold text-white mt-0.5 font-display">{triggerNode.title}</h4>
                        <p className="text-2xs text-slate-400 mt-1">{triggerNode.desc}</p>
                      </div>
                    </div>
                    <div className="text-right text-3xs font-mono font-semibold text-slate-500 bg-white/5 border border-white/10 rounded p-1">
                      {triggerNode.channel}
                    </div>
                  </motion.div>

                  {/* Flow Connection Arrow 1 */}
                  <div className="relative h-10 w-full flex items-center justify-center">
                    <svg className="absolute inset-0 h-10 w-full" xmlns="http://www.w3.org/2000/svg">
                      <line x1="50%" y1="0%" x2="50%" y2="100%" stroke="url(#bluecyan)" strokeWidth="2.5" strokeDasharray="4 4" />
                      <defs>
                        <linearGradient id="bluecyan" x1="0%" y1="0%" x2="0%" y2="100%">
                          <stop offset="0%" stopColor="#3b82f6" />
                          <stop offset="100%" stopColor="#06b6d4" />
                        </linearGradient>
                      </defs>
                    </svg>
                    <div className="p-1.5 rounded-full border border-blue-500/20 bg-slate-950 relative z-10 text-cyan-400">
                      <ArrowRight className="h-3.5 w-3.5 rotate-90" />
                    </div>
                  </div>

                  {/* Node 2: AI Planner Node (Gemini) */}
                  <motion.div
                    whileHover={{ scale: 1.02, y: -2 }}
                    className="w-full max-w-md p-4 bg-gradient-to-r from-purple-500/5 via-white/5 to-blue-500/5 border-2 border-purple-500/20 hover:border-purple-500/40 rounded-2xl flex items-center justify-between text-left relative shadow-lg shadow-purple-500/2 shadow-indigo-600/5 backdrop-blur-md group"
                  >
                    <div className="absolute top-0 right-0 h-10 w-10 bg-purple-500/5 blur-lg rounded-full"></div>
                    <div className="flex items-center space-x-4">
                      <div className="p-3 bg-purple-500/10 text-purple-400 rounded-xl border border-purple-500/10">
                        <Brain className="h-5 w-5" />
                      </div>
                      <div>
                        <span className="text-[10px] font-bold text-purple-400 tracking-widest font-mono">STAGE 2: AI PLANNER</span>
                        <h4 className="text-sm font-bold text-white mt-0.5 font-display">{aiNode.title}</h4>
                        <p className="text-2xs text-slate-400 mt-1">{aiNode.desc}</p>
                      </div>
                    </div>
                    <div className="text-right text-3xs font-mono font-semibold text-slate-500 bg-white/5 border border-white/10 rounded p-1">
                      {aiNode.channel}
                    </div>
                  </motion.div>

                  {/* Flow Connection Arrow 2 */}
                  <div className="relative h-10 w-full flex items-center justify-center">
                    <svg className="absolute inset-0 h-10 w-full" xmlns="http://www.w3.org/2000/svg">
                      <line x1="50%" y1="0%" x2="50%" y2="100%" stroke="url(#cyanblue)" strokeWidth="2.5" strokeDasharray="4 4" />
                      <defs>
                        <linearGradient id="cyanblue" x1="0%" y1="0%" x2="0%" y2="100%">
                          <stop offset="0%" stopColor="#c084fc" />
                          <stop offset="100%" stopColor="#06b6d4" />
                        </linearGradient>
                      </defs>
                    </svg>
                    <div className="p-1.5 rounded-full border border-purple-500/20 bg-slate-950 relative z-10 text-cyan-400">
                      <ArrowRight className="h-3.5 w-3.5 rotate-90" />
                    </div>
                  </div>

                  {/* Node 3: Outpost Action Node */}
                  <motion.div
                    whileHover={{ scale: 1.02, y: -2 }}
                    className="w-full max-w-md p-4 bg-white/5 border-2 border-cyan-500/20 hover:border-cyan-500/40 rounded-2xl flex items-center justify-between text-left relative shadow-lg shadow-cyan-500/2 shadow-cyan-600/5 backdrop-blur-md group"
                  >
                    <div className="flex items-center space-x-4">
                      <div className="p-3 bg-cyan-500/10 text-cyan-400 rounded-xl border border-cyan-500/10">
                        <Server className="h-5 w-5" />
                      </div>
                      <div>
                        <span className="text-[10px] font-bold text-cyan-400 tracking-widest font-mono">STAGE 3: ACTION NODE</span>
                        <h4 className="text-sm font-bold text-white mt-0.5 font-display">{actionNode.title}</h4>
                        <p className="text-2xs text-slate-400 mt-1">{actionNode.desc}</p>
                      </div>
                    </div>
                    <div className="text-right text-3xs font-mono font-semibold text-slate-500 bg-white/5 border border-white/10 rounded p-1">
                      {actionNode.channel}
                    </div>
                  </motion.div>

                </motion.div>
              ) : (
                
                // Terminal screen interface
                <motion.div
                  key="logs"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 10 }}
                  className="flex-1 flex flex-col font-mono text-xs text-emerald-400 text-left bg-slate-950/50 backdrop-blur-md rounded-2xl p-5 border border-white/10 relative z-10 space-y-2 overflow-y-auto max-h-[380px] shadow-lg"
                >
                  <div className="flex items-center justify-between text-slate-550 border-b border-white/10 pb-2.5 mb-2.5">
                    <span className="text-3xs font-bold">FLOW SANDBOX OUTPUT SHELL</span>
                    <button
                      onClick={() => setTerminalLogs([])}
                      className="text-3xs text-rose-400 font-bold hover:underline cursor-pointer"
                    >
                      CLEAR TERMINAL
                    </button>
                  </div>
                  {terminalLogs.length === 0 ? (
                    <div className="flex-1 flex flex-col items-center justify-center text-slate-500 text-center space-y-2 py-10">
                      <Terminal className="h-7 w-7 text-slate-600 animate-pulse" />
                      <span>Console idle. Click "Run Workflow" above or type triggers to dispatch event frames.</span>
                    </div>
                  ) : (
                    terminalLogs.map((log, i) => <div key={i}>{log}</div>)
                  )}
                </motion.div>
              )}
            </AnimatePresence>
            
          </div>

        </div>

      </div>
    </div>
  );
}