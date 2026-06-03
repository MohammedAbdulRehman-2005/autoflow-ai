import { useState } from 'react';
import {
  GitBranch, Play, Save, Download, AlertCircle, Brain, Zap, Server,
  ArrowRight, Terminal, RotateCw, Sparkles, RefreshCw, CheckCircle2
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { workflowApi } from '../services/workflowApi';

// ── Validation Error Panel ────────────────────────────────────────────────────
function ValidationPanel({ errors, warnings, onClose }) {
  if (!errors?.length && !warnings?.length) return null;
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-rose-500/20 bg-rose-500/5 p-4 space-y-2"
    >
      <div className="flex justify-between items-center">
        <span className="text-xs font-bold text-rose-400 flex items-center gap-1.5">
          <AlertCircle className="h-3.5 w-3.5" />
          Validation Failed — {errors.length} error(s), {warnings.length} warning(s)
        </span>
        <button onClick={onClose} className="text-xs text-slate-500 hover:text-white cursor-pointer">✕</button>
      </div>
      {errors.map((e, i) => (
        <div key={i} className="text-[11px] text-rose-300 bg-rose-500/10 rounded-lg px-3 py-2">
          <span className="font-bold">{e.code}</span>
          {e.node_id && <span className="text-rose-400/70 ml-1">@{e.node_id}</span>}
          <span className="text-rose-300/80 ml-1">— {e.message}</span>
        </div>
      ))}
      {warnings.map((w, i) => (
        <div key={i} className="text-[11px] text-amber-300 bg-amber-500/10 rounded-lg px-3 py-2">
          <span className="font-bold">⚠ {w.code}</span>
          <span className="text-amber-300/80 ml-1">— {w.message}</span>
        </div>
      ))}
    </motion.div>
  );
}

export default function WorkflowBuilderPage() {
  // Form state
  const [workflowName, setWorkflowName] = useState('AI Email to Notification Dispatcher');
  const [workflowDesc, setWorkflowDesc] = useState('Monitors notifications and routes them intelligently based on content.');
  const [prompt, setPrompt] = useState('Scan my inbox for new emails, summarize them with AI, then send a notification.');

  // Visual node state — updated when planner returns DSL
  const [triggerNode, setTriggerNode]   = useState({ title: 'Email Monitoring', desc: 'Scans incoming messages', channel: 'Gmail IMAP Poller', icon: 'zap' });
  const [aiNode, setAiNode]             = useState({ title: 'AI Summarizer', desc: 'Extracts and summarizes content', channel: 'Groq LLM', icon: 'brain' });
  const [actionNode, setActionNode]     = useState({ title: 'Notification Sender', desc: 'Delivers the result', channel: 'HTTP / Slack', icon: 'server' });

  // Planner state
  const [plannedDsl, setPlannedDsl]     = useState(null);
  const [isTranslating, setIsTranslating] = useState(false);
  const [planError, setPlanError]       = useState(null);

  // Action states
  const [isSaving, setIsSaving]         = useState(false);
  const [isRunning, setIsRunning]       = useState(false);
  const [saveResult, setSaveResult]     = useState(null); // { id, name }
  const [runResult, setRunResult]       = useState(null); // { run_id }
  const [activeTab, setActiveTab]       = useState('config');
  const [terminalLogs, setTerminalLogs] = useState([]);

  // Validation
  const [validationResult, setValidationResult] = useState(null);

  const addLog = (msg) => setTerminalLogs(prev => [...prev, `${new Date().toLocaleTimeString()} › ${msg}`]);

  // ── Plan Workflow (AI) ─────────────────────────────────────────────────────
  const handleTranslate = async () => {
    if (!prompt.trim()) return;
    setIsTranslating(true);
    setPlanError(null);
    setValidationResult(null);
    addLog('🔄 Sending prompt to AI planner...');
    try {
      const result = await workflowApi.planWorkflow(prompt);
      const dsl = result.dsl || result;
      setPlannedDsl(dsl);

      // Update visual nodes from DSL if possible
      if (dsl.nodes && dsl.nodes.length > 0) {
        const trigNode = dsl.nodes.find(n => n.type === 'trigger');
        const actNode  = dsl.nodes.find(n => n.type === 'action');
        const aiN      = dsl.nodes.find(n => n.type === 'ai_agent');

        if (trigNode) setTriggerNode({ title: trigNode.label || trigNode.id, desc: `${trigNode.service}.${trigNode.operation}`, channel: trigNode.service, icon: 'zap' });
        if (aiN)      setAiNode({ title: aiN.label || aiN.id, desc: `${aiN.service}.${aiN.operation}`, channel: aiN.service, icon: 'brain' });
        if (actNode)  setActionNode({ title: actNode.label || actNode.id, desc: `${actNode.service}.${actNode.operation}`, channel: actNode.service, icon: 'server' });
      }

      addLog(`✅ AI planner returned DSL: "${dsl.name || 'workflow'}" with ${dsl.nodes?.length || 0} node(s)`);
      setWorkflowName(dsl.name || workflowName);
    } catch (err) {
      setPlanError(err.message || 'AI planning failed.');
      addLog(`❌ Planning error: ${err.message}`);
    } finally {
      setIsTranslating(false);
    }
  };

  // ── Save Workflow ─────────────────────────────────────────────────────────
  const handleSave = async () => {
    if (!plannedDsl) {
      addLog('⚠ No DSL yet — run "Translate to Nodes" first to generate a workflow.');
      return;
    }
    setIsSaving(true);
    setValidationResult(null);
    addLog('🔍 Validating workflow...');
    try {
      // Validate first
      const validation = await workflowApi.validate(plannedDsl);
      if (!validation.valid) {
        setValidationResult(validation);
        addLog(`❌ Validation failed with ${validation.errors.length} error(s).`);
        setIsSaving(false);
        return;
      }
      if (validation.warnings?.length) {
        addLog(`⚠ ${validation.warnings.length} warning(s) — proceeding.`);
      }

      addLog('💾 Saving workflow to backend...');
      const created = await workflowApi.create({ name: workflowName, description: workflowDesc, dsl: plannedDsl });
      setSaveResult(created);
      addLog(`✅ Saved as "${created.name}" (ID: ${created.id})`);
    } catch (err) {
      addLog(`❌ Save error: ${err.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  // ── Run Workflow ──────────────────────────────────────────────────────────
  const handleRun = async () => {
    if (!saveResult?.id) {
      addLog('⚠ Save the workflow first before running it.');
      return;
    }
    setIsRunning(true);
    setActiveTab('logs');
    addLog(`⚡ Firing workflow "${saveResult.name}"...`);
    try {
      const run = await workflowApi.run(saveResult.id);
      setRunResult(run);
      addLog(`🚀 Run started! run_id: ${run.run_id}`);
      addLog('📊 Poll the Logs page to monitor execution status.');
    } catch (err) {
      addLog(`❌ Run error: ${err.message}`);
    } finally {
      setIsRunning(false);
    }
  };

  // ── Export ────────────────────────────────────────────────────────────────
  const handleExport = () => {
    const payload = plannedDsl || { name: workflowName, description: workflowDesc };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `${workflowName.toLowerCase().replace(/ /g, '_')}.json`;
    a.click();
    addLog('📥 DSL exported to JSON file.');
  };

  return (
    <div className="space-y-8 select-none text-left">

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white font-display flex items-center gap-2">
            <GitBranch className="h-8 w-8 text-blue-500" />
            <span>Workflow Studio</span>
          </h1>
          <p className="text-sm text-slate-400 mt-1 font-sans">
            Describe → Plan → Validate → Save → Run. All in one place.
          </p>
        </div>

        <div className="flex items-center space-x-2.5 self-start sm:self-auto">
          <button onClick={handleRun} disabled={isRunning || isSaving || isTranslating || !saveResult}
            className="flex items-center space-x-1.5 px-3.5 py-2 hover:border-cyan-500/35 bg-cyan-500/15 text-cyan-400 border border-cyan-500/20 hover:bg-cyan-500 hover:text-slate-950 rounded-xl text-xs font-bold transition-all cursor-pointer disabled:opacity-40 shadow-sm">
            {isRunning ? <RotateCw className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4 fill-current" />}
            <span>Run</span>
          </button>
          <button onClick={handleSave} disabled={isRunning || isSaving || isTranslating || !plannedDsl}
            className="flex items-center space-x-1.5 px-3.5 py-2 hover:border-blue-500/35 bg-blue-500/15 text-blue-400 border border-blue-500/20 hover:bg-blue-500 hover:text-slate-900 rounded-xl text-xs font-bold transition-all cursor-pointer disabled:opacity-40 shadow-sm">
            {isSaving ? <RotateCw className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            <span>Save</span>
          </button>
          <button onClick={handleExport} disabled={isRunning || isSaving}
            className="flex items-center space-x-1.5 px-3.5 py-2 border border-white/10 bg-white/5 hover:bg-white/10 text-slate-350 hover:text-white rounded-xl text-xs font-semibold cursor-pointer transition-all shadow-sm">
            <Download className="h-4 w-4" />
            <span className="hidden sm:inline">Export</span>
          </button>
        </div>
      </div>

      {/* Status banners */}
      {saveResult && (
        <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-2 text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-xl px-4 py-2.5">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          Workflow <strong className="mx-1">"{saveResult.name}"</strong> saved (ID: <code className="ml-1 font-mono">{saveResult.id?.slice(0, 8)}...</code>)
          {runResult && <span className="ml-3 text-cyan-400">→ Run <code className="font-mono">{runResult.run_id?.slice(0, 8)}...</code> dispatched</span>}
        </motion.div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

        {/* Left: AI Prompt + Config */}
        <div className="space-y-6">

          {/* AI Prompt */}
          <div className="border border-white/10 rounded-3xl bg-white/5 p-5 backdrop-blur-lg relative overflow-hidden shadow-md">
            <div className="absolute top-0 right-0 h-20 w-20 rounded-full bg-blue-500/10 blur-xl pointer-events-none" />
            <div className="flex items-center space-x-1.5 mb-3.5">
              <Sparkles className="h-4.5 w-4.5 text-cyan-400 animate-pulse" />
              <h3 className="text-2xs font-bold text-cyan-400 tracking-wider font-mono">GENERATE VIA AI PLANNER</h3>
            </div>

            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Describe your automation in plain English..."
              rows={4}
              className="w-full text-xs text-slate-200 placeholder-slate-500 bg-white/5 border border-white/10 rounded-xl p-3 outline-none resize-none hover:border-white/20 focus:border-cyan-500/50 transition-all font-sans"
            />

            {planError && (
              <div className="mt-2 text-[11px] text-rose-400 bg-rose-500/10 border border-rose-500/20 rounded-lg px-3 py-2 flex items-center gap-1.5">
                <AlertCircle className="h-3.5 w-3.5 shrink-0" />{planError}
              </div>
            )}

            <button
              onClick={handleTranslate} disabled={isTranslating || !prompt.trim()}
              className="w-full mt-3 flex items-center justify-center space-x-2 py-2.5 px-4 rounded-xl font-bold text-xs bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 text-white shadow-md cursor-pointer disabled:opacity-40"
            >
              {isTranslating ? (
                <><RefreshCw className="h-3.5 w-3.5 animate-spin" /><span>Planning...</span></>
              ) : (
                <><Sparkles className="h-3.5 w-3.5" /><span>Translate to Nodes</span></>
              )}
            </button>
          </div>

          {/* Workflow Config */}
          <div className="border border-white/10 rounded-3xl bg-white/5 p-5 backdrop-blur-lg space-y-4 shadow-md">
            <h3 className="text-sm font-bold text-white font-display">Workflow Settings</h3>
            <div className="space-y-1">
              <label className="text-[10px] font-bold text-slate-450 tracking-wider">TITLE</label>
              <input type="text" value={workflowName} onChange={(e) => setWorkflowName(e.target.value)}
                className="w-full rounded-xl border border-white/10 bg-white/5 py-2.5 px-3.5 text-xs text-white outline-none hover:border-white/20 focus:border-blue-500/50" />
            </div>
            <div className="space-y-1">
              <label className="text-[10px] font-bold text-slate-450 tracking-wider">DESCRIPTION</label>
              <input type="text" value={workflowDesc} onChange={(e) => setWorkflowDesc(e.target.value)}
                className="w-full rounded-xl border border-white/10 bg-white/5 py-2.5 px-3.5 text-xs text-white outline-none hover:border-white/20 focus:border-blue-500/50" />
            </div>
          </div>

          {/* Validation errors */}
          {validationResult && (
            <ValidationPanel
              errors={validationResult.errors}
              warnings={validationResult.warnings}
              onClose={() => setValidationResult(null)}
            />
          )}
        </div>

        {/* Right: Canvas + Terminal */}
        <div className="lg:col-span-2 space-y-6">
          <div className="flex border-b border-white/10">
            {[['config', 'Visual Flowchart'], ['logs', 'Execution Terminal']].map(([tab, label]) => (
              <button key={tab} onClick={() => setActiveTab(tab)}
                className={`pb-3.5 px-5 text-xs font-bold border-b-2 mr-2 cursor-pointer transition-all flex items-center gap-1.5 ${activeTab === tab ? 'border-blue-500 text-white' : 'border-transparent text-slate-400 hover:text-slate-200'}`}>
                {tab === 'logs' && <Terminal className="h-3.5 w-3.5 text-cyan-400" />}
                {label}
              </button>
            ))}
          </div>

          <div className="relative min-h-[460px] border border-white/10 rounded-3xl bg-[#020617]/30 backdrop-blur-lg p-8 flex flex-col justify-between overflow-hidden shadow-md">
            <div className="absolute inset-0 bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:16px_16px] pointer-events-none opacity-40" />

            <AnimatePresence mode="wait">
              {activeTab === 'config' ? (
                <motion.div key="canvas" initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }}
                  className="flex-1 flex flex-col items-center justify-center space-y-8 relative z-10 py-4">

                  {/* Node 1: Trigger */}
                  <motion.div whileHover={{ scale: 1.02, y: -2 }}
                    className="w-full max-w-md p-4 bg-white/5 border-2 border-blue-500/20 hover:border-blue-500/40 rounded-2xl flex items-center justify-between text-left shadow-lg backdrop-blur-md">
                    <div className="flex items-center space-x-4">
                      <div className="p-3 bg-blue-500/10 text-blue-400 rounded-xl border border-blue-500/10"><Zap className="h-5 w-5 animate-pulse" /></div>
                      <div>
                        <span className="text-[10px] font-bold text-blue-400 tracking-widest font-mono">STAGE 1: TRIGGER</span>
                        <h4 className="text-sm font-bold text-white mt-0.5 font-display">{triggerNode.title}</h4>
                        <p className="text-2xs text-slate-400 mt-1">{triggerNode.desc}</p>
                      </div>
                    </div>
                    <div className="text-right text-3xs font-mono font-semibold text-slate-500 bg-white/5 border border-white/10 rounded p-1 shrink-0 max-w-[100px] truncate">
                      {triggerNode.channel}
                    </div>
                  </motion.div>

                  {/* Arrow 1 */}
                  <div className="relative h-10 w-full flex items-center justify-center">
                    <svg className="absolute inset-0 h-10 w-full"><line x1="50%" y1="0%" x2="50%" y2="100%" stroke="url(#bc)" strokeWidth="2.5" strokeDasharray="4 4" /><defs><linearGradient id="bc" x1="0%" y1="0%" x2="0%" y2="100%"><stop offset="0%" stopColor="#3b82f6" /><stop offset="100%" stopColor="#06b6d4" /></linearGradient></defs></svg>
                    <div className="p-1.5 rounded-full border border-blue-500/20 bg-slate-950 relative z-10 text-cyan-400"><ArrowRight className="h-3.5 w-3.5 rotate-90" /></div>
                  </div>

                  {/* Node 2: AI */}
                  <motion.div whileHover={{ scale: 1.02, y: -2 }}
                    className="w-full max-w-md p-4 bg-gradient-to-r from-purple-500/5 via-white/5 to-blue-500/5 border-2 border-purple-500/20 hover:border-purple-500/40 rounded-2xl flex items-center justify-between text-left shadow-lg backdrop-blur-md">
                    <div className="flex items-center space-x-4">
                      <div className="p-3 bg-purple-500/10 text-purple-400 rounded-xl border border-purple-500/10"><Brain className="h-5 w-5" /></div>
                      <div>
                        <span className="text-[10px] font-bold text-purple-400 tracking-widest font-mono">STAGE 2: AI PROCESSOR</span>
                        <h4 className="text-sm font-bold text-white mt-0.5 font-display">{aiNode.title}</h4>
                        <p className="text-2xs text-slate-400 mt-1">{aiNode.desc}</p>
                      </div>
                    </div>
                    <div className="text-right text-3xs font-mono font-semibold text-slate-500 bg-white/5 border border-white/10 rounded p-1 shrink-0">{aiNode.channel}</div>
                  </motion.div>

                  {/* Arrow 2 */}
                  <div className="relative h-10 w-full flex items-center justify-center">
                    <svg className="absolute inset-0 h-10 w-full"><line x1="50%" y1="0%" x2="50%" y2="100%" stroke="url(#cb)" strokeWidth="2.5" strokeDasharray="4 4" /><defs><linearGradient id="cb" x1="0%" y1="0%" x2="0%" y2="100%"><stop offset="0%" stopColor="#c084fc" /><stop offset="100%" stopColor="#06b6d4" /></linearGradient></defs></svg>
                    <div className="p-1.5 rounded-full border border-purple-500/20 bg-slate-950 relative z-10 text-cyan-400"><ArrowRight className="h-3.5 w-3.5 rotate-90" /></div>
                  </div>

                  {/* Node 3: Action */}
                  <motion.div whileHover={{ scale: 1.02, y: -2 }}
                    className="w-full max-w-md p-4 bg-white/5 border-2 border-cyan-500/20 hover:border-cyan-500/40 rounded-2xl flex items-center justify-between text-left shadow-lg backdrop-blur-md">
                    <div className="flex items-center space-x-4">
                      <div className="p-3 bg-cyan-500/10 text-cyan-400 rounded-xl border border-cyan-500/10"><Server className="h-5 w-5" /></div>
                      <div>
                        <span className="text-[10px] font-bold text-cyan-400 tracking-widest font-mono">STAGE 3: ACTION</span>
                        <h4 className="text-sm font-bold text-white mt-0.5 font-display">{actionNode.title}</h4>
                        <p className="text-2xs text-slate-400 mt-1">{actionNode.desc}</p>
                      </div>
                    </div>
                    <div className="text-right text-3xs font-mono font-semibold text-slate-500 bg-white/5 border border-white/10 rounded p-1 shrink-0">{actionNode.channel}</div>
                  </motion.div>

                </motion.div>
              ) : (
                <motion.div key="logs" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                  className="flex-1 flex flex-col font-mono text-xs text-emerald-400 text-left bg-slate-950/50 backdrop-blur-md rounded-2xl p-5 border border-white/10 relative z-10 space-y-1.5 overflow-y-auto max-h-[400px]">
                  <div className="flex items-center justify-between text-slate-550 border-b border-white/10 pb-2.5 mb-2.5">
                    <span className="text-3xs font-bold">EXECUTION TERMINAL</span>
                    <button onClick={() => setTerminalLogs([])} className="text-3xs text-rose-400 font-bold hover:underline cursor-pointer">CLEAR</button>
                  </div>
                  {terminalLogs.length === 0 ? (
                    <div className="flex-1 flex flex-col items-center justify-center text-slate-500 text-center space-y-2 py-10">
                      <Terminal className="h-7 w-7 text-slate-600 animate-pulse" />
                      <span>Console idle. Use "Translate to Nodes" → "Save" → "Run" to see output.</span>
                    </div>
                  ) : (
                    terminalLogs.map((log, i) => <div key={i} className="text-[11px]">{log}</div>)
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