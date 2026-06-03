import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  GitBranch,
  CheckCircle2,
  Activity,
  Percent,
  Play,
  RotateCw,
  Sparkles,
  ArrowRight,
  TrendingUp,
  Brain,
  ArrowUpRight,
  ShieldCheck,
  Zap,
  CheckSquare,
  BadgeAlert,
  Mic,
  MicOff
} from 'lucide-react';
import { motion } from 'motion/react';
import SummaryCard from '../components/SummaryCard';
import { getWorkflows, getLogs, simulateRunningWorkflow } from '../mockData';

export default function DashboardPage() {
  const navigate = useNavigate();
  const [workflows, setWorkflows] = useState([]);
  const [logs, setLogs] = useState([]);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [optimizingId, setOptimizingId] = useState(null);
  const [optimizationSuggestion, setOptimizationSuggestion] = useState(null);

  const loadData = () => {
    setWorkflows(getWorkflows());
    setLogs(getLogs());
  };

  useEffect(() => {
    loadData();
    
    // Automatically poll every 8 seconds for a lively look if simulation runs
    const interval = setInterval(() => {
      loadData();
    }, 8000);
    return () => clearInterval(interval);
  }, []);

  const handleRefresh = () => {
    setIsRefreshing(true);
    setTimeout(() => {
      loadData();
      setIsRefreshing(false);
    }, 600);
  };

  const handleRunSimulation = (wfId) => {
    simulateRunningWorkflow(wfId);
    loadData();
  };

  // AI workflow optimization simulator
  const handleAIOptimize = (wfId, wfName) => {
    setOptimizingId(wfId);
    setOptimizationSuggestion(null);
    setTimeout(() => {
      setOptimizingId(null);
      setOptimizationSuggestion(
        `Gemini recommended: Restructured compilation steps in [${wfName}]. Aggregating bibliography queries improved throughput speed by 28.4% and resolved academic mailbox server timeout retries.`
      );
    }, 1800);
  };

  // State for AI Prompt Workspace Card box
  const [promptBoxValue, setPromptBoxValue] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);

  // States for Voice speech inputs
  const [isListening, setIsListening] = useState(false);
  const [activeSpeechInstance, setActiveSpeechInstance] = useState(null);

  const toggleSpeechRecognition = () => {
    const SpeechObj = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechObj) {
      alert("Speech recognition is not supported in this browser. Try using Google Chrome, Safari, or Microsoft Edge.");
      return;
    }

    if (isListening) {
      if (activeSpeechInstance) {
        activeSpeechInstance.stop();
      }
      setIsListening(false);
      return;
    }

    try {
      const rec = new SpeechObj();
      rec.continuous = false;
      rec.interimResults = false;
      rec.lang = 'en-US';

      rec.onstart = () => {
        setIsListening(true);
      };

      rec.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        if (transcript) {
          setPromptBoxValue(prev => (prev ? prev.trim() + ' ' : '') + transcript);
        }
      };

      rec.onerror = (event) => {
        console.error("Speech recognition error:", event.error);
        if (event.error === 'not-allowed') {
          alert("Microphone permission was denied. Please allow microphone access in your browser settings to use voice input.");
        } else if (event.error === 'no-speech') {
          // Quietly update state without intrusive alerts since standard speech end will trigger this or user can retry
        } else {
          alert(`Speech recognition issue: ${event.error}. Please try again.`);
        }
        setIsListening(false);
      };

      rec.onend = () => {
        setIsListening(false);
      };

      setActiveSpeechInstance(rec);
      rec.start();
    } catch (e) {
      console.error(e);
      alert("Error initializing speech recognition. Please check your system settings.");
      setIsListening(false);
    }
  };

  // Turn off record listening when page is destroyed or swapped
  useEffect(() => {
    return () => {
      if (activeSpeechInstance) {
        activeSpeechInstance.stop();
      }
    };
  }, [activeSpeechInstance]);

  const handleGenerateWorkflowText = () => {
    if (!promptBoxValue.trim()) {
      alert("Please describe your automation workflow first!");
      return;
    }
    setIsGenerating(true);
    setTimeout(() => {
      const finalPrompt = promptBoxValue;
      let title = "AI Custom Workflow";
      let trigger = "Custom Trigger";
      let action = "Custom Action";
      
      const lower = finalPrompt.toLowerCase();
      if (lower.includes("email") || lower.includes("gmail")) {
        title = "Smart Email Summary Flow";
        trigger = "Gmail Monitoring Ingestion";
        action = "Send Telegram Notification";
      } else if (lower.includes("telegram")) {
        title = "Telegram Notification Workflow";
        trigger = "Academic Page Monitor";
        action = "Telegram Broadcast Outpost";
      } else if (lower.includes("calendar") || lower.includes("meeting")) {
        title = "Calendar Scheduler Alert";
        trigger = "Consultation Scheduled";
        action = "Google Calendar Update";
      } else if (lower.includes("document") || lower.includes("pdf")) {
        title = "Document Processing Pipeline";
        trigger = "Drive: Academic PDF Upload";
        action = "Notion Pages Generated";
      } else {
        title = "AI Prompt Task Automation";
        trigger = "Workspace Folder Poller";
        action = "Notion Notebook Append";
      }
      
      addWorkflow(
        title,
        `Generated from prompt: "${finalPrompt.substring(0, 50)}..."`,
        trigger,
        action
      );
      
      setIsGenerating(false);
      setPromptBoxValue('');
      loadData();
      alert(`AI successfully generated and deployed workflow: "${title}" into your local database!`);
    }, 1200);
  };

  // Compute metrics dynamically from actual workflows & logs state!
  const totalWorkflows = workflows.length;
  const activeAutomations = workflows.filter(w => w.status === 'active').length;
  
  // Succesful list
  const successRate = totalWorkflows > 0 
    ? parseFloat((workflows.reduce((acc, curr) => acc + (curr.successRate || 0), 0) / activeAutomations).toFixed(1)) 
    : 98.4;

  const totalRuns = logs.length;

  return (
    <div className="space-y-8 select-none text-left">
      {/* Title Header Section */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white font-display">
            Workspace Overview
          </h1>
          <p className="text-sm text-slate-400 mt-1 font-sans">
            Monitor and refine your natural language student automation pipelines.
          </p>
        </div>

        {/* Header Actions */}
        <div className="flex items-center space-x-3 self-start sm:self-auto">
          <button
            onClick={handleRefresh}
            className="flex items-center space-x-2 px-3.5 py-2 border border-white/5 rounded-xl bg-slate-900/55 hover:bg-slate-900 text-slate-300 hover:text-white transition-all text-xs font-semibold cursor-pointer"
          >
            <RotateCw className={`h-4.5 w-4.5 ${isRefreshing ? 'animate-spin' : ''}`} />
            <span>Sync Stats</span>
          </button>
          
          <Link
            to="/workflow-builder"
            className="inline-flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 text-white shadow-lg shadow-blue-500/10 hover:shadow-cyan-500/20 rounded-xl text-xs font-bold transition-all"
          >
            <Zap className="h-4 w-4" />
            <span>Deploy Workflow</span>
          </Link>
        </div>
      </div>

      {/* Main AI USP Section: Describe your automation in natural language */}
      <div className="border border-cyan-500/15 rounded-3xl bg-gradient-to-br from-slate-940/90 via-[#070b19]/95 to-cyan-950/20 p-6 md:p-8 backdrop-blur-xl relative overflow-hidden shadow-xl">
        <div className="absolute top-0 right-0 h-40 w-40 rounded-full bg-cyan-500/10 blur-3xl pointer-events-none"></div>
        <div className="absolute -top-10 -left-10 h-32 w-32 rounded-full bg-blue-600/5 blur-2xl pointer-events-none"></div>
        
        <div className="flex flex-col md:flex-row gap-6 md:items-center justify-between relative z-10">
          <div className="space-y-2 flex-1">
            <div className="flex items-center space-x-2 text-cyan-400">
              <Sparkles className="h-5 w-5 animate-pulse" />
              <span className="text-2xs font-extrabold tracking-widest uppercase font-mono">Create Workflow using AI</span>
            </div>
            <h2 className="text-xl md:text-2xl font-black text-white font-display tracking-tight">
              Create Workflow using AI
            </h2>
            <p className="text-xs text-slate-450 max-w-xl leading-relaxed">
              Describe your automation in natural language. Gemini will analyze your description, draft the trigger-action sequence, and construct your flow topology instantly.
            </p>
          </div>

          <div className="w-full md:max-w-md flex flex-col space-y-3">
            <div className="flex flex-col space-y-2 text-xs">
              <div className="relative">
                <textarea
                  value={promptBoxValue}
                  onChange={(e) => setPromptBoxValue(e.target.value)}
                  placeholder="Describe your automation in natural language..."
                  rows={2}
                  className="w-full text-xs text-slate-200 placeholder-slate-500 bg-slate-950/50 border border-white/10 rounded-xl p-3 pr-10 outline-none resize-none hover:border-white/20 focus:border-cyan-500/55 transition-all font-sans"
                />
                <button
                  type="button"
                  onClick={toggleSpeechRecognition}
                  title={isListening ? "Stop listening" : "Start voice dictation"}
                  className={`absolute right-3 top-3 p-1.5 rounded-lg transition-all cursor-pointer ${
                    isListening 
                      ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30 animate-pulse' 
                      : 'text-slate-400 hover:text-white hover:bg-white/10'
                  }`}
                >
                  {isListening ? (
                    <MicOff className="h-4 w-4" />
                  ) : (
                    <Mic className="h-4 w-4" />
                  )}
                </button>
              </div>

              {isListening && (
                <div className="flex items-center space-x-2 text-[10px] text-rose-400 font-medium px-1 py-0.5">
                  <span className="flex h-1.5 w-1.5 relative">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-rose-500"></span>
                  </span>
                  <span>Listening... Speak your prompt details clearly</span>
                </div>
              )}

              <div className="flex justify-between items-center text-[10px] text-slate-500 px-1">
                <span>Example:</span>
                <button 
                  onClick={() => setPromptBoxValue("Send today's important emails summary and notify me on Telegram")}
                  className="text-cyan-400 hover:underline cursor-pointer"
                >
                  "Send today's important emails summary and notify me on Telegram"
                </button>
              </div>
            </div>

            <button
              onClick={handleGenerateWorkflowText}
              disabled={isGenerating}
              className="py-2.5 px-5 rounded-xl font-bold text-xs text-center bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 text-white cursor-pointer active:scale-98 transition-all shadow-md flex items-center justify-center gap-1.5 disabled:opacity-50"
            >
              {isGenerating ? (
                <>
                  <RotateCw className="h-3.5 w-3.5 animate-spin" />
                  <span>Configuring custom models...</span>
                </>
              ) : (
                <>
                  <Sparkles className="h-3.5 w-3.5 text-cyan-200" />
                  <span>Generate Workflow</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Grid containing 4 core metrics cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <SummaryCard
          title="TOTAL WORKFLOWS"
          value={totalWorkflows}
          icon={GitBranch}
          glowColor="blue"
          trend={{ value: '+4 new', isPositive: true }}
          description="Local workflow descriptors"
        />
        <SummaryCard
          title="SUCCESSFUL RUNS"
          value={`${totalRuns} runs`}
          icon={CheckSquare}
          glowColor="emerald"
          trend={{ value: '100% cloud', isPositive: true }}
          description="Jobs dispatched successfully"
        />
        <SummaryCard
          title="ACTIVE AUTOMATIONS"
          value={activeAutomations}
          icon={Activity}
          glowColor="cyan"
          trend={{ value: 'Live tracking', isPositive: true }}
          description="Background trigger pollers active"
        />
        <SummaryCard
          title="AVERAGE SUCCESS"
          value={`${successRate}%`}
          icon={Percent}
          glowColor="emerald"
          trend={{ value: '+0.4% MoM', isPositive: true }}
          description="Average transaction safety threshold"
        />
      </div>

      {/* Main split sections */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left side column: Main Graph & Recent Execs (spans 2 columns) */}
        <div className="lg:col-span-2 space-y-8">
          
          {/* Visual stat charts built with clean glassmorphism */}
          <div className="border border-white/10 rounded-3xl bg-white/5 p-6 backdrop-blur-lg relative overflow-hidden shadow-md">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-600 to-cyan-400"></div>
            <div className="flex justify-between items-center mb-6">
              <div>
                <span className="text-2xs font-bold text-cyan-400 font-mono tracking-wider">SYSTEM PERFORMANCE</span>
                <h3 className="text-lg font-bold text-white mt-1 font-display">Weekly Despatch Activity</h3>
              </div>
              <span className="text-2xs font-mono font-bold border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 rounded-full text-emerald-400">
                ● LIVE MONITOR
              </span>
            </div>

            {/* Custom SVG spark charts - pixel-perfect styled for a premium bento box look */}
            <div className="relative h-44 w-full flex items-end justify-between font-mono text-2xs text-slate-500 pt-4">
              {/* Backgrid rows */}
              <div className="absolute inset-0 flex flex-col justify-between pointer-events-none opacity-20 py-2">
                <div className="border-b border-white/10 w-full"></div>
                <div className="border-b border-white/10 w-full"></div>
                <div className="border-b border-white/10 w-full"></div>
                <div className="border-b border-white/10 w-full"></div>
              </div>

              {/* Graphical bars */}
              {[45, 68, 55, 87, 80, 95, 110].map((val, i) => (
                <div key={i} className="flex-1 flex flex-col items-center group relative z-10">
                  {/* Floating value hover snippet */}
                  <span className="absolute -top-7 scale-0 group-hover:scale-100 transition-all bg-slate-950 border border-white/10 rounded-lg px-2 py-1 text-[10px] font-bold text-cyan-400 shadow-xl">
                    {val} runs
                  </span>
                  <div className="w-8 xs:w-10 rounded-t-lg bg-gradient-to-t from-blue-600/45 to-cyan-500/80 hover:from-blue-500 hover:to-cyan-400 transition-all duration-300" style={{ height: `${val * 1.2}px` }}></div>
                  <span className="mt-2 text-3xs tracking-wider">
                    {['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'][i]}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Recent Execs Table */}
          <div className="border border-white/10 rounded-3xl bg-white/5 p-6 backdrop-blur-lg shadow-md">
            <div className="flex justify-between items-center mb-5">
              <div>
                <h3 className="text-lg font-bold text-white font-display">Recent Execution History</h3>
                <p className="text-xs text-slate-400 mt-1 font-sans">Live status update across active webhook channels</p>
              </div>
              <Link
                to="/logs"
                className="flex items-center space-x-1.5 text-xs font-bold text-cyan-400 hover:text-cyan-300 transition-colors font-display"
              >
                <span>Full Audit logs</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>

            {/* Logs List Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-white/10 text-slate-500 pb-2 font-display uppercase tracking-wider text-[10px]">
                    <th className="pb-3 pt-1 font-semibold">WORKFLOW</th>
                    <th className="pb-3 pt-1 font-semibold">STATUS</th>
                    <th className="pb-3 pt-1 font-semibold">DURATION</th>
                    <th className="pb-3 pt-1 font-semibold text-right">TIMESTAMP</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/10 text-slate-350">
                  {logs.slice(0, 4).map((log) => (
                    <tr key={log.id} className="hover:bg-white/5 transition-colors">
                      <td className="py-3.5 pr-2">
                        <div className="flex flex-col">
                          <span className="font-semibold text-slate-200">{log.workflowName}</span>
                          <span className="text-[10px] text-slate-500 mt-0.5 font-medium">{log.triggerEvent}</span>
                        </div>
                      </td>
                      <td className="py-3.5">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                          log.status === 'success' ? 'bg-emerald-500/10 text-emerald-400' :
                          log.status === 'running' ? 'bg-blue-500/10 text-blue-400' : 'bg-rose-500/10 text-rose-400'
                        }`}>
                          <span className={`h-1.5 w-1.5 rounded-full mr-1.5 ${
                            log.status === 'success' ? 'bg-emerald-400' :
                            log.status === 'running' ? 'bg-blue-400 animate-pulse' : 'bg-rose-400'
                          }`}></span>
                          {log.status.toUpperCase()}
                        </span>
                      </td>
                      <td className="py-3.5 font-mono text-[11px] text-slate-400">{log.duration}</td>
                      <td className="py-3.5 font-mono text-[10px] text-slate-500 text-right">
                        {new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

        </div>

        {/* Right side column: AI Insights & Quick Actions */}
        <div className="space-y-8">
          
          {/* Quick Actions List */}
          <div className="border border-white/10 rounded-3xl bg-white/5 p-6 backdrop-blur-lg shadow-md">
            <h3 className="text-lg font-bold text-white mb-4 font-display">Quick Shortcuts</h3>
            <div className="flex flex-col space-y-3">
              <Link
                to="/workflow-builder"
                className="flex items-center justify-between p-4 rounded-xl border border-white/10 bg-slate-950/30 hover:border-blue-500/40 hover:bg-white/5 transition-all font-medium text-slate-200 hover:text-white cursor-pointer group shadow-sm"
              >
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-blue-500/10 text-blue-400 rounded-lg">
                    <Brain className="h-4 w-4" />
                  </div>
                  <div className="flex flex-col text-left">
                    <span className="text-xs font-bold">Write AI Prompt</span>
                    <span className="text-[10px] text-slate-500 mt-0.5">Let Gemini frame a trigger flowchart</span>
                  </div>
                </div>
                <ArrowUpRight className="h-4 w-4 text-slate-500 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
              </Link>

              <Link
                to="/marketplace"
                className="flex items-center justify-between p-4 rounded-xl border border-white/10 bg-slate-950/30 hover:border-cyan-500/40 hover:bg-white/5 transition-all font-medium text-slate-200 hover:text-white cursor-pointer group shadow-sm"
              >
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-cyan-500/10 text-cyan-400 rounded-lg border border-cyan-500/20">
                    <Sparkles className="h-4 w-4" />
                  </div>
                  <div className="flex flex-col text-left">
                    <span className="text-xs font-bold">Import SaaS Template</span>
                    <span className="text-[10px] text-slate-500 mt-0.5">Deploy 1-click preset triggers</span>
                  </div>
                </div>
                <ArrowUpRight className="h-4 w-4 text-slate-500 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
              </Link>
            </div>
          </div>

          {/* AI Optimizer / Insights Box */}
          <div className="border border-white/10 rounded-3xl bg-white/5 p-6 backdrop-blur-lg relative overflow-hidden shadow-md">
            <div className="absolute top-0 right-0 h-28 w-28 rounded-full bg-cyan-500/10 blur-2xl pointer-events-none"></div>
            
            <div className="flex items-center space-x-2.5 mb-4">
              <div className="p-2 bg-gradient-to-br from-cyan-500 to-indigo-500 rounded-xl shadow-md">
                <Sparkles className="h-4.5 w-4.5 text-white animate-pulse" />
              </div>
              <h3 className="text-[15px] font-extrabold text-white font-display">AI Copilot Analysis</h3>
            </div>

            <p className="text-xs text-slate-400 leading-relaxed text-left font-sans">
              Our Gemini model has mapped pipeline latency ratios. Select a workflow below to run structural query optimization.
            </p>

            <div className="mt-5 space-y-3.5">
              {workflows.slice(0, 2).map((wf) => (
                <div
                  key={wf.id}
                  className="p-3.5 rounded-xl bg-slate-950/40 border border-white/10 flex items-center justify-between shadow-sm"
                >
                  <div className="flex flex-col text-left">
                    <span className="text-xs font-bold text-white truncate max-w-[120px] font-display">{wf.name}</span>
                    <span className="text-[10px] text-slate-500 mt-0.5 font-mono">
                      LATENCY: 1.4s • RATE: {wf.successRate}%
                    </span>
                  </div>
                  <button
                    onClick={() => handleAIOptimize(wf.id, wf.name)}
                    disabled={optimizingId !== null}
                    className="flex h-8 items-center space-x-1.5 rounded-lg px-2.5 bg-blue-500/10 border border-blue-500/20 text-[10px] font-bold text-blue-400 hover:bg-blue-500/20 transition-all cursor-pointer disabled:opacity-50"
                  >
                    {optimizingId === wf.id ? (
                      <RotateCw className="h-3 w-3 animate-spin" />
                    ) : (
                      <>
                        <Sparkles className="h-3 w-3" />
                        <span>OPTIMIZE</span>
                      </>
                    )}
                  </button>
                </div>
              ))}
            </div>

            {/* Suggestions Overlay */}
            {optimizationSuggestion && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-4 p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium text-left leading-relaxed"
              >
                {optimizationSuggestion}
              </motion.div>
            )}
          </div>

          {/* Trigger list simulation sandbox */}
          <div className="border border-white/10 rounded-3xl bg-white/5 p-6 backdrop-blur-lg shadow-md">
            <h3 className="text-sm font-bold text-white mb-1 font-display">Trigger Simulations</h3>
            <p className="text-xs text-slate-400 mb-4 font-sans">Click "FIRE" to trigger an API transaction and logs mock-event updates.</p>
            
            <div className="flex flex-col space-y-2">
              {workflows.map((wf) => (
                <div key={wf.id} className="flex justify-between items-center p-2.5 rounded-lg hover:bg-white/5 border border-transparent hover:border-white/10 transition-all">
                  <span className="text-xs text-slate-300 truncate max-w-[170px] font-medium">{wf.name}</span>
                  <button
                    onClick={() => handleRunSimulation(wf.id)}
                    className="flex items-center space-x-1 border border-cyan-500/30 bg-cyan-500/10 text-cyan-400 hover:bg-cyan-500 hover:text-slate-950 px-2 py-1 rounded-md text-[10px] font-bold transition-all cursor-pointer"
                  >
                    <Play className="h-2.5 w-2.5 shrink-0 fill-current" />
                    <span>FIRE</span>
                  </button>
                </div>
              ))}
            </div>
          </div>

        </div>

      </div>
    </div>
  );
}
