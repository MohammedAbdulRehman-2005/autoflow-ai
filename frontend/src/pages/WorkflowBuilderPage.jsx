/**
 * AutoFlow AI — Workflow Studio (React Flow Edition)
 *
 * Architecture:
 *  - WorkflowDSL is the single source of truth (kept in `plannedDsl` state).
 *  - React Flow graph is derived from the DSL every time the DSL changes.
 *  - Persistent right-side AI Chat Panel drives incremental DSL edits.
 *  - Node positions dragged by the user are persisted in `savedPositions` and
 *    survive DSL updates so the canvas never unexpectedly jumps.
 */

import { useState, useCallback, useRef, useMemo,useEffect } from 'react';
import {useLocation } from 'react-router-dom' ;
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  Panel,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { motion, AnimatePresence } from 'framer-motion';
import {
  GitBranch, Play, Save, Download, Upload, AlertCircle, Brain, Zap,
  Terminal, RotateCw, Sparkles, RefreshCw, CheckCircle2, Send,
  User, Bot, ChevronRight,  ChevronDown ,Trash2, X,Mic,Square
} from 'lucide-react';

import WorkflowNode from '../components/WorkflowNode';
import { dslToFlow } from '../utils/flowLayout';
import { workflowApi } from '../services/workflowApi';

// ── React Flow custom node type map ──────────────────────────────────────────
const nodeTypes = { workflowNode: WorkflowNode };

// -- Validation Panel --------------------------------------------------------
function ValidationPanel({ errors, warnings, onClose }) {
  if (!errors?.length && !warnings?.length) return null;
  const hasErrors = errors?.length > 0;
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={`rounded-2xl border p-4 space-y-2 ${
        hasErrors
          ? 'border-rose-500/20 bg-rose-500/5'
          : 'border-amber-500/20 bg-amber-500/5'
      }`}
    >
      <div className="flex justify-between items-center">
        <span className={`text-xs font-bold flex items-center gap-1.5 ${hasErrors ? 'text-rose-400' : 'text-amber-400'}`}>
          <AlertCircle className="h-3.5 w-3.5" />
          {hasErrors
            ? `Validation Failed — ${errors.length} error(s), ${warnings?.length || 0} warning(s)`
            : `Saved with ${warnings.length} warning(s) — connect integrations before running`}
        </span>
        <button onClick={onClose} className="text-xs text-slate-500 hover:text-white cursor-pointer">✕</button>
      </div>
      {errors?.map((e, i) => (
        <div key={i} className="text-[11px] text-rose-300 bg-rose-500/10 rounded-lg px-3 py-2">
          <span className="font-bold">{e.code || 'ERROR'}</span>
          {e.node_id && <span className="text-rose-400/70 ml-1">@{e.node_id}</span>}
          <span className="text-rose-300/80 ml-1">— {e.message || e}</span>
        </div>
      ))}
      {warnings?.map((w, i) => (
        <div key={i} className="text-[11px] text-amber-300 bg-amber-500/10 rounded-lg px-3 py-2">
          <span className="font-bold">⚠ {w.code || 'WARN'}</span>
          {w.node_id && <span className="text-amber-400/70 ml-1">@{w.node_id}</span>}
          <span className="text-amber-300/80 ml-1">— {w.message || w}</span>
        </div>
      ))}
    </motion.div>
  );
}

// ── Chat Message Bubble ───────────────────────────────────────────────────────
function ChatBubble({ msg }) {
  const isUser = msg.role === 'user';
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={`flex gap-2.5 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
    >
      <div className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-xs
        ${isUser
          ? 'bg-blue-500/20 border border-blue-500/40 text-blue-400'
          : 'bg-purple-500/20 border border-purple-500/40 text-purple-400'}`}>
        {isUser ? <User size={13} /> : <Bot size={13} />}
      </div>
      <div className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-xs leading-relaxed
        ${isUser
          ? 'bg-blue-500/15 border border-blue-500/20 text-slate-200 rounded-tr-sm'
          : 'bg-white/5 border border-white/10 text-slate-300 rounded-tl-sm'}`}>
        {msg.content}
        {msg.status === 'loading' && (
          <span className="inline-flex gap-0.5 ml-1">
            {[0, 0.15, 0.3].map((d, i) => (
              <span key={i} className="w-1 h-1 rounded-full bg-purple-400 animate-bounce"
                style={{ animationDelay: `${d}s` }} />
            ))}
          </span>
        )}
      </div>
    </motion.div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function WorkflowBuilderPage() {
  const location = useLocation();
  // ── Canonical DSL state ───────────────────────────────────────────────────
  const [plannedDsl, setPlannedDsl]     = useState(null);

  // ── React Flow state ─────────────────────────────────────────────────────
  const [rfNodes, setRfNodes, onNodesChange] = useNodesState([]);
  const [rfEdges, setRfEdges, onEdgesChange] = useEdgesState([]);

  const [showTemplates,setShowTemplates] = useState(false);
  
  const [recording,setRecording]=useState(false);
  const mediaRecorderRef =useRef(null);
  const chunksRef= useRef([]);
  
  const startRecording = async () => {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: true,
    });

    const recorder = new MediaRecorder(stream);

    chunksRef.current = [];

    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        chunksRef.current.push(event.data);
      }
    };

    recorder.onstop = async () => {
      const audioBlob = new Blob(chunksRef.current, {
        type: "audio/webm",
      });

      const formData = new FormData();
      formData.append("audio", audioBlob, "recording.webm");

        const response = await fetch(
          "https://autoflow-ai-production.up.railway.app/api/v1/transcribe",
          {
            method: "POST",
            body: formData,
          }
        );

        const data = await response.json();

        if (data.success) {
          setChatInput((prev) => prev + " " + data.text);
        }
      };

    mediaRecorderRef.current = recorder;  
    recorder.start();
    
    setRecording(true);
  } catch (error) {
    console.error("Microphone error:", error);
  }
};

const stopRecording = () => {
  mediaRecorderRef.current?.stop();
  setRecording(false);
};

 const [followupQuestions,setFollowupQuestions] =useState([]);

  // Saved manual positions: { nodeId: { x, y } }
  const savedPositionsRef = useRef({});

  // ── Chat state ────────────────────────────────────────────────────────────
  const [chatHistory, setChatHistory]   = useState([{
    role: 'assistant',
    content: "Hi! I'm your AI Workflow Planner. Describe what you'd like to automate and I'll build it on the canvas. You can also ask me to modify the workflow at any time.",
  }]);
  const [chatInput, setChatInput]       = useState('');
  const [isThinking, setIsThinking]     = useState(false);
  const chatEndRef = useRef(null);

  // ── Follow-up question context ────────────────────────────────────────────
  // When the AI needs clarification, we store the original prompt and asked
  // questions here. On the user's next reply we fuse them together and generate.
  const [pendingContext, setPendingContext] = useState(null);
  // pendingContext shape: { originalPrompt: string, questions: string[] }

  // ── Sidebar + Action state ────────────────────────────────────────────────
  const [workflowName, setWorkflowName] = useState('My AI Workflow');
  const [isSaving, setIsSaving]         = useState(false);
  const [isRunning, setIsRunning]       = useState(false);
  const [saveResult, setSaveResult]     = useState(null);
  const [runResult, setRunResult]       = useState(null);
  const [terminalLogs, setTerminalLogs] = useState([]);
  const [validationResult, setValidationResult] = useState(null);
  const [showTerminal, setShowTerminal] = useState(false);

  const addLog = (msg) => setTerminalLogs(prev => [...prev, `${new Date().toLocaleTimeString()} › ${msg}`]);

  // ── Apply a new DSL to the canvas ────────────────────────────────────────
  const applyDsl = useCallback((dsl) => {
    setPlannedDsl(dsl);
    localStorage.setItem("draft_workflow",JSON.stringify(dsl));
    const { nodes, edges } = dslToFlow(dsl, savedPositionsRef.current);
    setRfNodes(nodes);
    setRfEdges(edges);
    if (dsl.name) setWorkflowName(dsl.name);
  }, [setRfNodes, setRfEdges]);

useEffect(() => {
  const workflowId =
    localStorage.getItem("current_workflow_id");

  if (!workflowId) return;

  workflowApi.get(workflowId)
    .then((wf) => {
      
      const dsl =
      wf?.dsl || 
      wf?.dsl_json ||
      wf?.ai_context_json ||
      wf?.plan || 
      wf?.workflow_dsl || 
      wf?.definition ;
      
      if (dsl) {
        applyDsl(dsl);
      }
    })
    .catch(console.error);
}, [applyDsl]);

useEffect(() => {
const workflowId =localStorage.getItem("current_workflow_id");

if(workflowId) return ;
  const draft = localStorage.getItem("draft_workflow");

  if (draft) {
    try {
      const dsl = JSON.parse(draft);
      applyDsl(dsl);
    } catch (err) {
      console.error("Failed to load draft", err);
    }
  }
}, [applyDsl]);

// ── Auto-send prompt handed off from Dashboard ───────────────────────────
  useEffect(() => {
    const incomingPrompt = location.state?.initialPrompt;
    if (incomingPrompt) {
      sendMessage(incomingPrompt);
      // Clear the navigation state so refreshing this page won't re-trigger it
      window.history.replaceState({}, document.title);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  
  // ── Handle node drag stop → save position ────────────────────────────────
  const onNodeDragStop = useCallback((_, node) => {
    savedPositionsRef.current[node.id] = node.position;
    // Mark this node as having a manual position so dagre won't touch it
    setRfNodes(nds => nds.map(n =>
      n.id === node.id ? { ...n, data: { ...n.data, manualPosition: true } } : n
    ));
  }, [setRfNodes]);

  // ── Clarification heuristic ───────────────────────────────────────────────
  // Returns true if the prompt is specific enough to generate without follow-ups.
  const isPromptSpecific = (text) => {
    const lower = text.toLowerCase();
    // Specific enough if: mentions a trigger (when, every, schedule, webhook, form),
    // an action (send, email, slack, notify, create, append), and is reasonably long.
    const hasTrigger = /\b(when|every|schedule|cron|webhook|form|daily|weekly|monthly|morning|night|hour)\b/.test(lower);
    const hasAction  = /\b(send|email|notify|slack|whatsapp|sms|create|save|append|post|update|generate|summarize|report)\b/.test(lower);
    const isLong     = text.trim().split(/\s+/).length >= 10;
    return (hasTrigger && hasAction) || isLong;
  };

  // ── Build clarifying questions for vague prompts ──────────────────────────
  const buildClarifyingQuestions = (prompt) => {
    const lower = prompt.toLowerCase();
    const questions = [];

    if (!/\b(when|every|schedule|cron|webhook|form|daily|weekly|monthly|morning|night|hour|trigger|monday|friday)\b/.test(lower)) {
      questions.push('⏰ **When should this run?** (e.g. every Monday at 9 AM, when a form is submitted, when a webhook fires, or manually)');
    }
    if (!/\b(email|slack|whatsapp|sms|sheets|notion|airtable|hubspot|http|telegram|calendar|drive)\b/.test(lower)) {
      questions.push('🔌 **Which apps or services should it use?** (e.g. Gmail, Slack, Google Sheets, WhatsApp, Notion)');
    }
    if (questions.length === 0) {
      questions.push('📋 **Any specific details?** (e.g. email addresses, sheet names, Slack channels, message templates)');
    }
    return questions.slice(0, 2); // max 2 questions to stay concise
  };

  // ── Generate workflow from a fully-resolved prompt ────────────────────────
  const generateFromPrompt = useCallback(async (fullPrompt, name) => {
    addLog('🤖 Sending to AI planner...');
    const intent = {
      goal: fullPrompt,
      trigger: 'Auto-inferred from prompt',
      integrations: [],
    };
    const result = await workflowApi.planWorkflow(
      name || workflowName,
      intent,
      plannedDsl,
    );
    if(result.questions){
    setFollowupQuestions(result.questions || []);
  }


    const dsl = result.dsl || result;
    localStorage.removeItem("current_workflow_id")
    applyDsl(dsl);
      try {
  const response = await fetch(
    "https://autoflow-ai-production.up.railway.app/api/v1/ai/parse-intent",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        prompt: fullPrompt,
      }),
    }
  );

  const clarificationData = await response.json();

  if (clarificationData.need_clarification) {
    setChatHistory(prev => prev.slice(0,-1));
    setFollowupQuestions(
      clarificationData.questions
    );
    setIsThinking(false);
    return
  }
} catch (err) {
  console.error("Clarification error:", err);
}
finally{
  setIsThinking(false);
}
    
    const nodeCount = dsl.nodes?.length || 0;
    const stats = result.graph_stats;
    const summary = stats
      ? `✅ Done! Built a **${stats.node_count}-node** workflow using: ${stats.services_used?.join(', ') || 'various services'}. You can drag nodes around, then hit **Save** when ready.`
      : `✅ Done! Built a ${nodeCount}-node workflow. Hit **Save** when ready.`;

    setChatHistory(prev => [
      ...prev.slice(0, -1),
      { role: 'assistant', content: summary },
    ]);
    addLog(`✅ AI planner returned DSL: "${dsl.name}" with ${nodeCount} node(s)`);
  }, [workflowName, plannedDsl, applyDsl]);

  // ── Send message to AI ────────────────────────────────────────────────────
  const sendMessage = useCallback(async (overrideText) => {
    const userText = (overrideText ?? chatInput).trim();
    if (!userText || isThinking) return;

    setChatInput('');
    const userMsg = { role: 'user', content: userText };
    const thinkingMsg = { role: 'assistant', content: '', status: 'loading' };

    setChatHistory(prev => [...prev, userMsg, thinkingMsg]);
    setIsThinking(true);
    setTimeout(() => chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 50);
    addLog(`💬 User: ${userText}`);

    try {
      // ── Case A: User is answering a pending follow-up question ───────────
      if (pendingContext) {
        // Fuse original prompt + the user's clarification answers
        const enrichedPrompt = `${pendingContext.originalPrompt}\n\nAdditional details from user: ${userText}`;
        setPendingContext(null);
        await generateFromPrompt(enrichedPrompt, workflowName);
        return;
      }

      // ── Case B: First message or an incremental edit on an existing DSL ──
      // If there's already a canvas AND the prompt is a modification request, skip clarification
      const isModification = !!plannedDsl;
      const specific = isModification || isPromptSpecific(userText);

      if (!specific) {
        // ── Ask clarifying questions ────────────────────────────────────────
        const questions = buildClarifyingQuestions(userText);
        const questionText = `Great idea! Before I build this, I have a couple of quick questions to make it more accurate:\n\n${questions.join('\n\n')}\n\nFeel free to answer both in one message!`;

        setPendingContext({ originalPrompt: userText, questions });
        setChatHistory(prev => [
          ...prev.slice(0, -1),
          { role: 'assistant', content: questionText },
        ]);
        addLog('❓ AI asking clarifying questions...');
        return;
      }

      // ── Specific enough — generate directly ─────────────────────────────
      await generateFromPrompt(userText, workflowName);

    } catch (err) {
      const errMsg = err.message || 'AI planning failed.';
      setChatHistory(prev => [
        ...prev.slice(0, -1),
        { role: 'assistant', content: `❌ ${errMsg}` },
      ]);
      addLog(`❌ Planning error: ${errMsg}`);
    } finally {
      setIsThinking(false);
      setTimeout(() => chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
    }
  }, [chatInput, isThinking, workflowName, plannedDsl, pendingContext, generateFromPrompt]);

  // -- Save -----------------------------------------------------------------
  const handleSave = async () => {
    if (!plannedDsl) {
      addLog('No workflow to save. Chat with the AI first!');
      return;
    }
    setIsSaving(true);
    setValidationResult(null);
    addLog('Validating workflow...');
    try {
      const validation = await workflowApi.validate(plannedDsl);

      if (!validation.valid) {
        // Hard errors - cannot save
        setValidationResult(validation);
        addLog(`Validation failed with ${validation.errors.length} error(s). Fix them before saving.`);
        setIsSaving(false);
        return;
      }

      // Show warnings (e.g. missing credentials) but still allow save
      if (validation.warnings?.length) {
        setValidationResult(validation);
        addLog(`${validation.warnings.length} warning(s) - saving anyway. Connect integrations before running.`);
      } else {
        addLog('Validation passed!');
      }

      addLog('Saving workflow...');
      const desc = plannedDsl.description || '';
      const created = await workflowApi.create({ name: workflowName, description: desc, dsl: plannedDsl });
      localStorage.setItem("current_workflow_id",created.id);
      localStorage.removeItem("draft_workflow");
      setSaveResult(created);
      window.dispatchEvent(new Event("workflow-saved"));
      addLog(`Saved as "${created.name}" (ID: ${created.id})`);
    } catch (err) {
      addLog(`Save error: ${err.message}`);
    } finally {
      setIsSaving(false);
    }
  };


  // ── Run ───────────────────────────────────────────────────────────────────
  const handleRun = async () => {
    if (!saveResult?.id) {
      addLog('⚠ Save the workflow first before running.');
      return;
    }
    setIsRunning(true);
    setShowTerminal(true);
    addLog(`⚡ Firing workflow "${saveResult.name}"...`);
    try {
      const run = await workflowApi.run(saveResult.id);
      setRunResult(run);
      addLog(`🚀 Run started! run_id: ${run.run_id}`);
    } catch (err) {
      addLog(`❌ Run error: ${err.message}`);
    } finally {
      setIsRunning(false);
    }
  };

  // ── Export / Import ───────────────────────────────────────────────────────
  const handleExport = () => {
    if (!plannedDsl) return;
    const blob = new Blob([JSON.stringify(plannedDsl, null, 2)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `${workflowName.toLowerCase().replace(/ /g, '_')}.json`;
    a.click();
    addLog('📥 DSL exported.');
  };

  const fileInputRef = useRef(null);

  const handleImport = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const json = JSON.parse(event.target.result);
        if (json.name) setWorkflowName(json.name);
        setPlannedDsl(json);
        setSaveResult(null); // Clear previous save state
        addLog(`📤 Imported DSL: "${json.name || 'Untitled'}". Click the Save button to save it!`);
      } catch (error) {
        addLog(`❌ Failed to parse JSON: ${error.message}`);
      }
    };
    reader.readAsText(file);
    e.target.value = null;
  };

  // ── Quick Templates ───────────────────────────────────────────────────────
  const templates = [
    "Scan my inbox for new emails, summarize with AI, then send a Slack notification",
    "Book an appointment from a Google Form submission and send confirmation via SMS",
    "Every Monday at 9 AM, read this week's sales from Google Sheets and email a report",
    "When a webhook fires, extract key data using AI and append a row to Airtable",
    "Send WhatsApp reminders 24 hours before any Google Calendar event",
  ];

  return (
    <div className="flex h-[calc(100vh-7rem)] gap-0 overflow-hidden -m-6 select-none">

      {/* ── Left Toolbar ──────────────────────────────────────────────────── */}
      <div className="w-14 flex-shrink-0 flex flex-col items-center gap-3 py-4 border-r border-white/8 bg-slate-950/60 backdrop-blur-md">
        <button
          onClick={handleRun}
          disabled={isRunning || !saveResult}
          title="Run Workflow"
          className="w-9 h-9 rounded-xl flex items-center justify-center bg-cyan-500/15 border border-cyan-500/20 text-cyan-400 hover:bg-cyan-500 hover:text-slate-950 transition-all cursor-pointer disabled:opacity-30"
        >
          {isRunning ? <RotateCw size={16} className="animate-spin" /> : <Play size={16} className="fill-current" />}
        </button>
        <button
          onClick={handleSave}
          disabled={isSaving || !plannedDsl}
          title="Save Workflow"
          className="w-9 h-9 rounded-xl flex items-center justify-center bg-blue-500/15 border border-blue-500/20 text-blue-400 hover:bg-blue-500 hover:text-white transition-all cursor-pointer disabled:opacity-30"
        >
          {isSaving ? <RotateCw size={16} className="animate-spin" /> : <Save size={16} />}
        </button>
        <button
          onClick={handleExport}
          disabled={!plannedDsl}
          title="Export DSL JSON"
          className="w-9 h-9 rounded-xl flex items-center justify-center bg-white/5 border border-white/10 text-slate-400 hover:bg-white/10 hover:text-white transition-all cursor-pointer disabled:opacity-30"
        >
          <Download size={16} />
        </button>
        <button
          onClick={() => fileInputRef.current?.click()}
          title="Import DSL JSON"
          className="w-9 h-9 rounded-xl flex items-center justify-center bg-white/5 border border-white/10 text-slate-400 hover:bg-white/10 hover:text-white transition-all cursor-pointer"
        >
          <Upload size={16} />
          <input type="file" accept=".json" className="hidden" ref={fileInputRef} onChange={handleImport} />
        </button>
        <div className="h-px w-6 bg-white/10 my-1" />
        <button
          onClick={() => setShowTerminal(v => !v)}
          title="Toggle Terminal"
          className={`w-9 h-9 rounded-xl flex items-center justify-center border transition-all cursor-pointer
            ${showTerminal
              ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-400'
              : 'bg-white/5 border-white/10 text-slate-400 hover:text-white'}`}
        >
          <Terminal size={16} />
        </button>
      </div>

      {/* ── Canvas ────────────────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Toolbar banner */}
        <div className="flex items-center gap-3 px-4 py-2.5 border-b border-white/8 bg-slate-950/40 backdrop-blur-sm flex-shrink-0">
          <GitBranch size={16} className="text-blue-400" />
          <input
            value={workflowName}
            onChange={e => setWorkflowName(e.target.value)}
            className="flex-1 bg-transparent text-sm font-bold text-white outline-none placeholder-slate-500 max-w-xs"
            placeholder="Workflow Name..."
          />
          {saveResult && (
            <span className="text-[10px] text-emerald-400 font-mono flex items-center gap-1">
              <CheckCircle2 size={11} /> Saved · {saveResult.id?.slice(0, 8)}
            </span>
          )}
          {runResult && (
            <span className="text-[10px] text-cyan-400 font-mono flex items-center gap-1">
              <Play size={11} className="fill-current" /> Run · {runResult.run_id?.slice(0, 8)}
            </span>
          )}
        </div>

        {/* Validation errors */}
        {validationResult && (
          <div className="px-4 py-2 flex-shrink-0">
            <ValidationPanel
              errors={validationResult.errors}
              warnings={validationResult.warnings}
              onClose={() => setValidationResult(null)}
            />
          </div>
        )}

        {/* React Flow Canvas */}
        <div className="flex-1 relative">
          <ReactFlow
            nodes={rfNodes}
            edges={rfEdges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            nodeTypes={nodeTypes}
            onNodeDragStop={onNodeDragStop}
            fitView
            fitViewOptions={{ padding: 0.3, maxZoom: 1.2 }}
            minZoom={0.2}
            maxZoom={2}
            proOptions={{ hideAttribution: true }}
            style={{ background: 'transparent' }}
          >
            <Background
              color="#1e293b"
              gap={20}
              size={1}
              style={{ opacity: 0.6 }}
            />
            <Controls
              className="!bg-slate-900/80 !border-white/10 !rounded-xl [&>button]:!bg-transparent [&>button]:!text-slate-400 [&>button:hover]:!text-white [&>button]:!border-white/10"
            />
            <MiniMap
              nodeColor={(n) => n.data?.colors?.accent || '#3b82f6'}
              maskColor="rgba(2,6,23,0.7)"
              className="!bg-slate-900/80 !border-white/10 !rounded-xl"
            />

            {/* Empty state overlay */}
            {rfNodes.length === 0 && (
              <Panel position="top-center">
                <div className="mt-20 flex flex-col items-center gap-4 text-center pointer-events-none">
                  <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-blue-500/20 to-purple-500/20 border border-white/10 flex items-center justify-center">
                    <Sparkles size={32} className="text-blue-400 animate-pulse" />
                  </div>
                  <div>
                    <p className="text-white font-bold text-lg">Your canvas is empty</p>
                    <p className="text-slate-400 text-sm mt-1">Chat with the AI assistant →</p>
                  </div>
                </div>
              </Panel>
            )}
          </ReactFlow>
        </div>

        {/* Terminal Drawer */}
        <AnimatePresence>
          {showTerminal && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 160, opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="border-t border-white/10 bg-slate-950/80 backdrop-blur-md overflow-hidden flex-shrink-0"
            >
              <div className="flex items-center justify-between px-4 py-2 border-b border-white/8">
                <span className="text-[10px] font-bold text-slate-500 font-mono tracking-widest">EXECUTION TERMINAL</span>
                <div className="flex gap-2">
                  <button onClick={() => setTerminalLogs([])} className="text-[10px] text-rose-400 font-bold cursor-pointer hover:underline">CLEAR</button>
                  <button onClick={() => setShowTerminal(false)} className="text-slate-500 hover:text-white cursor-pointer"><X size={12} /></button>
                </div>
              </div>
              <div className="px-4 py-2 space-y-0.5 overflow-y-auto h-[120px] font-mono text-[11px] text-emerald-400">
                {terminalLogs.length === 0
                  ? <div className="text-slate-500 italic">No logs yet.</div>
                  : terminalLogs.map((log, i) => <div key={i}>{log}</div>)
                }
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* ── Right AI Chat Panel ────────────────────────────────────────────── */}
      <div className="w-[340px] flex-shrink-0 flex flex-col border-l border-white/8 bg-slate-950/60 backdrop-blur-md">

        {/* Chat Header */}
        <div className="flex items-center gap-3 px-4 py-3.5 border-b border-white/8 flex-shrink-0">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-purple-500/30 to-blue-500/30 border border-purple-500/30 flex items-center justify-center">
            <Brain size={14} className="text-purple-400" />
          </div>
          <div>
            <p className="text-sm font-bold text-white">AI Planner</p>
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-[10px] text-emerald-400 font-mono">
                {isThinking ? 'Thinking...' : 'Ready'}
              </span>
            </div>
          </div>
          <button
            onClick={() => setChatHistory(prev => [prev[0]])}
            title="Clear chat history"
            className="ml-auto text-slate-600 hover:text-slate-300 cursor-pointer transition-colors"
          >
            <Trash2 size={13} />
          </button>
        </div>

        {/* Chat Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4 min-h-0">
          {chatHistory.map((msg, i) => <ChatBubble key={i} msg={msg} />)}
          <div ref={chatEndRef} />
        </div>

     {/* Quick Templates */}
<div className="px-4 pt-2 pb-2 border-t border-white/8 flex-shrink-0">
  <button
    onClick={() => setShowTemplates(!showTemplates)}
    className="w-full flex items-center justify-between text-[9px] font-bold text-slate-600 tracking-widest uppercase mb-2 cursor-pointer hover:text-slate-400 transition-colors"
  >
    <span>Quick Templates</span>
    <ChevronDown
      className={`h-3 w-3 transition-transform duration-200 ${showTemplates ? 'rotate-180' : ''}`}
    />
  </button>
  {showTemplates && (
    <div className="flex flex-col gap-1.5 max-h-32 overflow-y-auto">
      {templates.map((t, i) => (
        <button
          key={i}
          onClick={() => setChatInput(t)}
          className="text-left text-[10px] text-slate-400 hover:text-white bg-white/3 hover:bg-white/8 bo..."
        >
          👉{t}
        </button>
      ))}
    </div>
  )}
</div>

        {followupQuestions.length > 0 && (
       <div className="mt-4">
     <p className="text-[11px] uppercase tracking-wider text-gray-500 font-semibold mb-3">
  Suggested refinements
</p>

<div className="flex gap-2 overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-gray-700 scrollbar-track-transparent">
  {followupQuestions.map((q, index) => (
    <div
      key={index}
      className="group relative flex-shrink-0"
    >
      <button
        type="button"
        className="flex items-center gap-2 max-w-[260px] pl-3 pr-7 py-1.5 rounded-full
                   bg-gray-800/80 hover:bg-gray-700 border border-gray-700/50
                   text-xs text-gray-200 whitespace-nowrap overflow-hidden
                   transition-colors"
        onClick={() => setChatInput(q)}
        title={q}
      >
        <span className="truncate">{q}</span>
      </button>

      <button
        type="button"
        aria-label="Remove suggestion"
        className="absolute right-2 top-1/2 -translate-y-1/2
                   text-gray-500 hover:text-red-400
                   opacity-0 group-hover:opacity-100
                   transition-opacity text-xs"
        onClick={(e) => {
          e.stopPropagation();
          setFollowupQuestions(prev => prev.filter((_, i) => i !== index));
        }}
      >
        ✕
      </button>
    </div>
  ))}
</div>
  </div>
)}


        {/* Chat Input */}
        <div className="px-4 pt-2 pb-4 flex-shrink-0 border-t border-white/8">
          <div className="flex gap-2 items-end">
            <textarea
              value={chatInput}
              onChange={e => setChatInput(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  sendMessage();
                }
              }}
              rows={2}
              placeholder={
                pendingContext
                  ? "Answer the questions above…"
                  : plannedDsl
                  ? "Modify the workflow… (e.g. 'Add a Slack notification on failure')"
                  : "Describe your automation… (e.g. 'Send a daily email summary of new leads')"
              }
              className={`flex-1 text-xs text-slate-200 placeholder-slate-600 bg-white/5 border rounded-xl px-3 py-2.5 outline-none resize-none transition-all font-sans
                ${
                  pendingContext
                    ? 'border-amber-500/40 focus:border-amber-500/70 hover:border-amber-500/50'
                    : 'border-white/10 hover:border-white/20 focus:border-purple-500/50'
                }`}
            />
            <button
  onClick={recording ? stopRecording : startRecording}
  className="flex-shrink-0 w-9 h-9 rounded-xl border border-white/10 hover:border-white/20 flex items-center justify-center"
>
  {recording ? "⏸️": (
    <Mic size={15} />
  )}
</button>
            <button
              onClick={sendMessage}
              disabled={!chatInput.trim() || isThinking}
              className="flex-shrink-0 w-9 h-9 rounded-xl bg-gradient-to-br from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white flex items-center justify-center cursor-pointer disabled:opacity-40 transition-all shadow-lg"
            >
              {isThinking
                ? <RefreshCw size={14} className="animate-spin" />
                : <Send size={14} />}
            </button>
          </div>
          <p className="text-[9px] text-slate-600 mt-1.5 text-center">
                        {pendingContext
              ? <span className="text-amber-400">⏳ Awaiting your answers to generate the workflow</span>
              : plannedDsl
              ? '✨ Incremental edit mode — node IDs preserved'
              : 'Press Enter to send · Shift+Enter for newline'}
          </p>
        </div>
      </div>
    </div>
  );
}




