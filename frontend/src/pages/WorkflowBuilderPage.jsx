import { useState, useEffect, useRef } from 'react';
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
  Trash2,
  Mic,
  MicOff,
  Paperclip
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { addWorkflow, simulateRunningWorkflow } from '../mockData';

// Dynamic AI prompt analyzer that evaluates custom prompts and maps node states
const analyzePrompt = (promptText) => {
  const text = (promptText || '').toLowerCase();

  // Example 1: PDF / Summarize / Document
  if (text.includes('pdf') || text.includes('summarize') || text.includes('document') || text.includes('paper') || text.includes('syllabus')) {
    return {
      name: "PDF Summary Generator",
      desc: "Scans uploaded syllabus files or paper PDFs and outputs custom AI study summaries.",
      trigger: {
        title: "PDF Upload",
        desc: "At course slides and research papers uploads",
        channel: "Drive Asset Ingestion",
        icon: "zap"
      },
      ai: {
        title: "AI Workflow Planner",
        desc: "Skins natural text and structures Document Summarization strategies",
        channel: "LLM Engine",
        icon: "brain"
      },
      action: {
        title: "Generate Summary",
        desc: "Constructs custom summaries database card representation",
        channel: "Notion Workspace API",
        icon: "server"
      },
      confidence: 96,
      reasoning: [
        "🔍 Detected PDF processing workflow",
        "📄 Identified 'PDF' / 'document' trigger entity",
        "🧠 Selected summarization strategy for academic files",
        "⚡ Formulating layout schemas for PDF token indexer",
        "🚀 Generated output action: Generate Summary in Notion"
      ]
    };
  }

  // Example 2: Book / appointment / Friday / calendar / schedule
  if (text.includes('book') || text.includes('appointment') || text.includes('friday') || text.includes('calendar') || text.includes('schedule') || text.includes('meeting')) {
    return {
      name: "AI Smart Calendar Scheduler",
      desc: "Decodes natural language appointments and books them into Google Calendar.",
      trigger: {
        title: "Calendar Request",
        desc: "Monitors calendar event booking invites and requests",
        channel: "Schedules Web Gateway",
        icon: "zap"
      },
      ai: {
        title: "AI Workflow Planner",
        desc: "Calculates timeline slots for optimal Schedule Management",
        channel: "LLM Engine",
        icon: "brain"
      },
      action: {
        title: "Create Calendar Event",
        desc: "Pushes event reminders with scheduled block dates",
        channel: "Google Calendar Sync",
        icon: "server"
      },
      confidence: 94,
      reasoning: [
        "🔍 Detected scheduling request from prompt text",
        "📅 Identified scheduling target for Friday appointment",
        "🕰️ Checking calendar workflow constraints and slot limits",
        "🧠 Selected Schedule Management reasoning engine",
        "🚀 Generated calendar event action: Create Calendar Event on Google Calendar"
      ]
    };
  }

  // Example 4: Convert meeting recording / notes / voice / audio / video / seminar
  if (text.includes('recording') || text.includes('audio') || text.includes('transcript') || text.includes('lecture') || text.includes('voice') || text.includes('convert') || text.includes('notes')) {
    return {
      name: "Lecture Voice Transcription & Notes Builder",
      desc: "Extracts spoken discussion points from audio recordings and files to build revision sheets.",
      trigger: {
        title: "Meeting Recording",
        desc: "Detects syllabus and consultation audio clips uploads",
        channel: "Google Drive Listener",
        icon: "zap"
      },
      ai: {
        title: "AI Workflow Planner",
        desc: "Performs deep Speech Analysis to compile core study blocks",
        channel: "LLM Engine",
        icon: "brain"
      },
      action: {
        title: "Meeting Notes Generation",
        desc: "Compiles formatted study guides and actions sheets",
        channel: "Formatted Output API",
        icon: "server"
      },
      confidence: 92,
      reasoning: [
        "🔍 Detected voice recording processing request",
        "🎙️ Identified audio stream trigger: 'recording' / 'audio'",
        "🧠 Ingesting parameters into Speech Analysis node",
        "📝 Structuring verbal text arrays into outline sections",
        "🚀 Generated output action: Meeting Notes Generation inside notebook"
      ]
    };
  }

  // Example 5: Research / trends / latest / find / bibliography / literature
  if (text.includes('research') || text.includes('trend') || text.includes('latest') || text.includes('index') || text.includes('query') || text.includes('find') || text.includes('search')) {
    return {
      name: "Intelligent Research Digest Assistant",
      desc: "Queries global publication catalogs and indexes summaries in databases.",
      trigger: {
        title: "Research Query",
        desc: "Watches for targeted research requests and listings",
        channel: "Web Console Listener",
        icon: "zap"
      },
      ai: {
        title: "AI Workflow Planner",
        desc: "Spins up specialized Knowledge Retrieval and summary indices",
        channel: "LLM Engine",
        icon: "brain"
      },
      action: {
        title: "Research Report",
        desc: "Outputs compiled literature studies and bibliographies",
        channel: "Research Outpost API",
        icon: "server"
      },
      confidence: 93,
      reasoning: [
        "🔍 Detected trend query processing instruction",
        "📚 Identified keyword indexing target: 'research' / 'trend'",
        "🧠 Initializing Knowledge Retrieval agent strategies",
        "⚡ Cross-referencing indexed library citations and titles",
        "🚀 Generated output action: Research Report dispatch format configuration"
      ]
    };
  }

  // Example 3: Send assignment alerts / Telegram / alert / message / chat (Gmail / Email)
  // Standard default matching Telegram, Email or others
  if (text.includes('telegram') || text.includes('alert') || text.includes('assignment') || text.includes('gmail') || text.includes('email') || text.includes('inbox') || text.includes('prof') || text.includes('inbox') || text.includes('send')) {
    return {
      name: "Academic Email to Telegram Dispatcher",
      desc: "Monitors academic newsletters, extracts assignments, and flashes structured digests to student Telegram logs.",
      trigger: {
        title: "Gmail Monitor",
        desc: "Checks mailbox announcements from professors and schools",
        channel: "Gmail IMAP Poller",
        icon: "zap"
      },
      ai: {
        title: "AI Workflow Planner",
        desc: "Runs student task categorization routines under Task Detection mode",
        channel: "LLM Engine",
        icon: "brain"
      },
      action: {
        title: "Telegram Notification",
        desc: "Pushes formatted study summaries and deadlines to Telegram",
        channel: "Telegram Bot Botfather",
        icon: "server"
      },
      confidence: 95,
      reasoning: [
        "🔍 Detected notification trigger entity: 'Telegram' / 'Email'",
        "📧 Identified Gmail inbox poller target state",
        "🧠 Selected Task Detection strategy for assignment logs",
        "⚡ Constructing secure web payload with custom message keys",
        "🚀 Generated output action: Dispatch Telegram Notification"
      ]
    };
  }

  // General Fallback
  return {
    name: "Custom Automated AI Flow",
    desc: "Intelligently routing custom event streams dynamically translated by AI.",
    trigger: {
      title: "Custom Application Trigger",
      desc: "Listens for custom input event hooks or file creations",
      channel: "Universal Webhook URL",
      icon: "zap"
    },
    ai: {
      title: "AI Workflow Planner",
      desc: "Decodes complex intent sequences using the LLM semantic parser",
      channel: "LLM Engine",
      icon: "brain"
    },
    action: {
      title: "Custom Target Action",
      desc: "Executes final user-specified webhook, email alert or write template",
      channel: "Automated API Gateway",
      icon: "server"
    },
    confidence: 89,
    reasoning: [
      "🔍 Scanning custom prompt tokens...",
      "💡 Constructing real-time semantic query correlations",
      "🧠 Intent mapped: Dynamic Intent Processor parsing custom properties",
      "⚡ Validating webhook endpoints and data schema formats",
      "🚀 Selected output action matched dynamically to query context"
    ]
  };
};

export default function WorkflowBuilderPage() {
  const [naturalLanguagePrompt, setNaturalLanguagePrompt] = useState(
    'Scan my student inbox for new assignment announcements from profs, make a study guide outline, and send a structured alert to my Telegram chat.'
  );

  const initialAnalysis = analyzePrompt('Scan my student inbox for new assignment announcements from profs, make a study guide outline, and send a structured alert to my Telegram chat.');

  const [workflowName, setWorkflowName] = useState(initialAnalysis.name);
  const [workflowDesc, setWorkflowDesc] = useState(initialAnalysis.desc);
  
  // Whisper Speech Recording & Attachment States
  const [recordingState, setRecordingState] = useState('idle'); // 'idle' | 'listening' | 'recording' | 'processing'
  const [recordingDuration, setRecordingDuration] = useState(0);
  const [recordedBlob, setRecordedBlob] = useState(null);
  const [recordedAudioUrl, setRecordedAudioUrl] = useState(null);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [appendMode, setAppendMode] = useState(false); // Default: replace mode
  const appendModeRef = useRef(appendMode);
  useEffect(() => {
    appendModeRef.current = appendMode;
  }, [appendMode]);
  const [uploadedFile, setUploadedFile] = useState(null);

  // Auto incrementing timer for active recording
  useEffect(() => {
    let interval;
    if (recordingState === 'recording') {
      interval = setInterval(() => {
        setRecordingDuration(prev => prev + 1);
      }, 1000);
    } else {
      setRecordingDuration(0);
    }
    return () => clearInterval(interval);
  }, [recordingState]);

  // Clean up recording URL and media recorder tracks on components unmount
  useEffect(() => {
    return () => {
      if (recordedAudioUrl) {
        URL.revokeObjectURL(recordedAudioUrl);
      }
      if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
      }
    };
  }, [recordedAudioUrl, mediaRecorder]);

  const startRecording = async () => {
    setRecordingState('listening');
    setRecordedBlob(null);
    setRecordedAudioUrl(null);
    
    // Attempt actual browser microphone interface access
    try {
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const recorder = new MediaRecorder(stream);
        const chunks = [];
        
        recorder.ondataavailable = (e) => {
          if (e.data && e.data.size > 0) {
            chunks.push(e.data);
          }
        };

        recorder.onstop = () => {
          const blob = new Blob(chunks, { type: 'audio/webm' });
          setRecordedBlob(blob);
          setRecordedAudioUrl(URL.createObjectURL(blob));
          stream.getTracks().forEach(track => track.stop());
          
          processAudioFile(blob);
        };

        setMediaRecorder(recorder);
        recorder.start();
        setRecordingState('recording');
      } else {
        // Fallback for sandboxed frames or non-mic environments
        simulateAudioRecording();
      }
    } catch (err) {
      console.warn("Media Recording failed/denied. Emulating in-browser speech recorder component:", err);
      simulateAudioRecording();
    }
  };

  const simulateAudioRecording = () => {
    setRecordingState('recording');
    // Emulated recorder runs and stops on user action
  };

  const stopRecording = () => {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop();
    } else {
      // Create a dummy mock blob for state persistence in simulated mode
      const dummyBlob = new Blob([new Uint8Array(1024)], { type: 'audio/mp3' });
      setRecordedBlob(dummyBlob);
      setRecordedAudioUrl(URL.createObjectURL(dummyBlob));
      processAudioFile(dummyBlob);
    }
  };

  const processAudioFile = (blob) => {
    setRecordingState('processing');
    setTerminalLogs(prev => [
      ...prev,
      '🎙️ Recording stopped. Ingested audio stream blob into browser memory.',
      '📡 Whisper API Pipeline Ready: Mocking AI transcript generator...'
    ]);

    // Choose a realistic prompt translation target to support testings
    const testTranscripts = [
      "Summarize this PDF and create study notes",
      "Book an appointment next Friday",
      "Extract tasks from this document",
      "Send important emails to Telegram"
    ];
    const transcript = testTranscripts[Math.floor(Math.random() * testTranscripts.length)];

    setTimeout(() => {
      setRecordingState('idle');

      if (appendModeRef.current) {
        setNaturalLanguagePrompt(prev => prev ? prev.trim() + " " + transcript : transcript);
        setTerminalLogs(prev => [...prev, `✅ Whisper Transcribed (Appended Mode): "${transcript}"`]);
      } else {
        setNaturalLanguagePrompt(transcript);
        setTerminalLogs(prev => [...prev, `✅ Whisper Transcribed (Replace Mode): "${transcript}"`]);
      }
    }, 2000);
  };

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const sizeStr = (file.size / 1024 / 1024).toFixed(2) + ' MB';
    setUploadedFile({
      name: file.name,
      size: sizeStr,
      type: file.type
    });

    setTerminalLogs(prev => [
      ...prev,
      `📎 File Attached: "${file.name}" (${sizeStr})`,
      `⚙️ Parsing client data schema for in-memory LLM processing context.`
    ]);

    // Suggest suitable prompts according to type
    if (!naturalLanguagePrompt || naturalLanguagePrompt.trim() === 'Describe your workflow, speak a command, or upload a file...') {
      if (file.name.toLowerCase().endsWith('.pdf')) {
        setNaturalLanguagePrompt("Summarize this PDF and create study notes");
      } else {
        setNaturalLanguagePrompt("Extract tasks from this document");
      }
    }
  };

  // Custom states that allow the user to modify the visual flow
  const [triggerNode, setTriggerNode] = useState(initialAnalysis.trigger);
  const [aiNode, setAINode] = useState(initialAnalysis.ai);
  const [actionNode, setActionNode] = useState(initialAnalysis.action);
  const [confidence, setConfidence] = useState(initialAnalysis.confidence);
  const [aiReasoning, setAiReasoning] = useState(initialAnalysis.reasoning);

  const [isTranslating, setIsTranslating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [activeTab, setActiveTab] = useState('config');

  // Logs terminal simulation state
  const [terminalLogs, setTerminalLogs] = useState([]);

  // Natural Language prompt translator simulator
  const handleTranslatePrompt = () => {
    setIsTranslating(true);
    setTerminalLogs(prev => [...prev, '🔄 Initializing AI prompt analysis...', '📡 Feeding prompt string into neural layout processor...']);
    setTimeout(() => {
      // Analyze current prompt
      const result = analyzePrompt(naturalLanguagePrompt);

      setWorkflowName(result.name);
      setWorkflowDesc(result.desc);
      setTriggerNode(result.trigger);
      setAINode(result.ai);
      setActionNode(result.action);
      setConfidence(result.confidence);
      setAiReasoning(result.reasoning);

      setTerminalLogs(prev => [
        ...prev,
        '✨ Natural language triggers parsed by AI',
        `✅ Generated Pipeline Name: [${result.name}]`,
        `✅ Extracted TRIGGER Node: [${result.trigger.title}]`,
        `✅ Extracted ACTION Node: [${result.action.title}]`,
        `🎯 AI Reasoning Match: Confidence is ${result.confidence}% with selected mapping parameters!`,
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
      '📊 Ingest payload: { "auth": "ok", "timestamp": "2526-06-03T17:14:44Z", "actor": "AI System Client" }',
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

            {/* Redesigned Prompt Slate Input Container */}
            <div className="relative border border-white/10 rounded-2xl bg-slate-900/40 p-3 shadow-inner hover:border-white/20 transition-all">
              <textarea
                value={naturalLanguagePrompt}
                onChange={(e) => setNaturalLanguagePrompt(e.target.value)}
                placeholder="Describe your workflow, speak a command, or upload a file..."
                rows={4}
                className="w-full text-xs text-slate-200 placeholder-slate-500 bg-transparent border-0 outline-none resize-none pb-12 font-sans font-semibold leading-relaxed"
              />
              
              {/* Floating Bottom Control Toolbar */}
              <div className="absolute bottom-2.5 left-2.5 right-2.5 flex items-center justify-between pt-2 border-t border-white/5 bg-slate-950/20 px-1">
                {/* Left controls: Mic, Upload button, Clear */}
                <div className="flex items-center space-x-1.5">
                  <button
                    type="button"
                    onClick={recordingState === 'recording' ? stopRecording : startRecording}
                    disabled={isTranslating}
                    title={recordingState === 'recording' ? "Stop Recording" : "Start Voice Recording"}
                    className={`p-2 rounded-xl transition-all cursor-pointer flex items-center justify-center border ${
                      recordingState === 'recording'
                        ? 'bg-rose-500/20 border-rose-500/40 text-rose-400 animate-pulse'
                        : recordingState === 'listening'
                        ? 'bg-amber-500/20 border-amber-500/40 text-amber-400 animate-pulse'
                        : recordingState === 'processing'
                        ? 'bg-purple-500/20 border-purple-500/40 text-purple-400'
                        : 'bg-white/5 border-white/10 text-slate-400 hover:text-white hover:bg-white/10 hover:border-white/25'
                    }`}
                  >
                    {recordingState === 'recording' ? (
                      <MicOff className="h-4 w-4" />
                    ) : (
                      <Mic className={`h-4 w-4 ${recordingState === 'processing' ? 'animate-spin' : ''}`} />
                    )}
                  </button>

                  {/* 📎 Upload File Attachment label trigger */}
                  <label 
                    title="Attach File (.pdf, .docx, .txt, .png, .jpg)"
                    className="p-2 rounded-xl bg-white/5 border border-white/10 text-slate-400 hover:text-white hover:bg-white/10 hover:border-white/25 transition-all cursor-pointer flex items-center justify-center"
                  >
                    <Paperclip className="h-4 w-4" />
                    <input
                      type="file"
                      accept=".pdf,.docx,.txt,.png,.jpg,.jpeg"
                      onChange={handleFileUpload}
                      disabled={isTranslating || recordingState !== 'idle'}
                      className="hidden"
                    />
                  </label>

                  {/* Clear Button */}
                  {naturalLanguagePrompt && (
                    <button
                      type="button"
                      onClick={() => setNaturalLanguagePrompt('')}
                      disabled={isTranslating || recordingState !== 'idle'}
                      title="Clear Prompt Text"
                      className="p-2 rounded-xl bg-white/5 border border-white/10 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 hover:border-rose-500/25 transition-all cursor-pointer flex items-center justify-center"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  )}
                </div>

                {/* Right controls: Append switch toggle & count indicators */}
                <div className="flex items-center space-x-2 text-[10px] text-slate-400 font-mono">
                  <div className="flex items-center space-x-1.5 border border-white/5 bg-slate-950/40 px-2.5 py-1 rounded-lg">
                    <span className="text-slate-500 select-none">Append:</span>
                    <button
                      type="button"
                      onClick={() => setAppendMode(!appendMode)}
                      title="Toggle between replacing prompt or appending to it"
                      className={`font-black tracking-wider uppercase transition-colors outline-none ${
                        appendMode ? 'text-cyan-400 hover:text-cyan-300' : 'text-slate-500 hover:text-slate-400'
                      }`}
                    >
                      {appendMode ? 'ON' : 'OFF'}
                    </button>
                  </div>
                  <span className="bg-slate-950/40 px-2 py-1 rounded-lg border border-white/5 font-black hidden sm:inline-block">
                    {naturalLanguagePrompt.length} chars
                  </span>
                </div>
              </div>
            </div>

            {/* Dynamic File Attachment Visual Status Badge */}
            {uploadedFile && (
              <motion.div
                initial={{ opacity: 0, scale: 0.98, y: 6 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.98, y: 6 }}
                className="mt-2.5 p-2 rounded-2xl border border-cyan-500/25 bg-cyan-950/20 flex items-center justify-between text-left"
              >
                <div className="flex items-center space-x-2 overflow-hidden">
                  <div className="p-2 bg-cyan-500/10 text-cyan-400 rounded-lg shrink-0">
                    <Paperclip className="h-3.5 w-3.5" />
                  </div>
                  <div className="overflow-hidden">
                    <div className="text-[11px] font-bold text-slate-200 truncate pr-2">
                      {uploadedFile.name}
                    </div>
                    <div className="text-[9px] text-slate-450 font-mono">
                      {uploadedFile.size} • Upload Ready
                    </div>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setUploadedFile(null);
                    setTerminalLogs(prev => [...prev, "❌ Removed document file attachment."]);
                  }}
                  className="p-1 px-2 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 font-bold text-xs transition-colors cursor-pointer shrink-0"
                  title="Remove attachment"
                >
                  Remove
                </button>
              </motion.div>
            )}

            {/* Whisper speech recording live progress card */}
            {recordingState !== 'idle' && (
              <motion.div
                initial={{ opacity: 0, scale: 0.98, y: 6 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.98, y: 6 }}
                className="mt-2.5 p-3.5 border border-white/10 rounded-2xl bg-slate-950/60 backdrop-blur-md text-xs space-y-2.5 text-left"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span className="flex h-2 w-2 relative">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500"></span>
                    </span>
                    <span className="font-bold text-white uppercase tracking-wider text-3xs font-mono">
                      {recordingState === 'listening' ? 'SYSTEM: Requesting Mic...' : recordingState === 'recording' ? 'SYSTEM: Recording Voice...' : 'SYSTEM: Transcribing Waveform...'}
                    </span>
                  </div>
                  {recordingState === 'recording' && (
                    <span className="text-[10px] font-bold font-mono text-rose-450 bg-rose-500/10 border border-rose-500/20 px-2 py-0.5 rounded-lg animate-pulse">
                      REC {Math.floor(recordingDuration / 60)}:{(recordingDuration % 60).toString().padStart(2, '0')}
                    </span>
                  )}
                </div>

                {recordingState === 'recording' && (
                  <div className="flex items-center justify-between px-1">
                    <span className="text-[10px] text-slate-400">Equalizer Waveform</span>
                    <div className="flex items-end space-x-0.5 h-3.5 mt-0.5 select-none">
                      <span className="w-0.5 bg-cyan-500 rounded-full h-1 animate-[pulse_0.7s_infinite]"></span>
                      <span className="w-0.5 bg-indigo-500 rounded-full h-3 animate-[pulse_1.1s_infinite]"></span>
                      <span className="w-0.5 bg-cyan-400 rounded-full h-2 animate-[pulse_0.9s_infinite]"></span>
                      <span className="w-0.5 bg-purple-500 rounded-full h-3.5 animate-[pulse_1.3s_infinite]"></span>
                      <span className="w-0.5 bg-cyan-500 rounded-full h-1 animate-[pulse_0.6s_infinite]"></span>
                      <span className="w-0.5 bg-indigo-400 rounded-full h-2.5 animate-[pulse_1.0s_infinite]"></span>
                    </div>
                  </div>
                )}

                {/* Secure Backend Warning Message */}
                <div className="p-2 border border-white/5 bg-white/5 rounded-xl text-[10px] leading-relaxed text-slate-400 font-medium italic">
                  ℹ️ "Whisper transcription will be provided by backend integration."
                </div>

                {recordingState === 'processing' && (
                  <div className="flex items-center space-x-2 text-purple-400 text-3xs font-mono font-bold animate-pulse">
                    <RefreshCw className="h-3 w-3 animate-spin text-purple-400" />
                    <span>Feeding encoded sound bytes to neural speech decoders...</span>
                  </div>
                )}
              </motion.div>
            )}

            <button
               onClick={handleTranslatePrompt}
               disabled={isTranslating || recordingState !== 'idle'}
               className="w-full mt-3 flex items-center justify-center space-x-2 py-2.5 px-4 rounded-xl font-bold text-xs bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 text-white shadow-md active:scale-95 cursor-pointer disabled:opacity-50"
            >
               {isTranslating ? (
                <>
                   <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                   <span>Analyzing Prompter Intent...</span>
                </>
              ) : (
                <>
                   <Sparkles className="h-3.5 w-3.5" />
                   <span>Generate Pipeline via AI</span>
                </>
              )}
            </button>

            {/* Quick-Click Prompt Examples Picker Block */}
            <div className="mt-4 pt-3 border-t border-white/5 space-y-2">
              <label className="text-[9px] font-bold text-slate-500 tracking-wider font-mono uppercase block text-left">
                💡 CLICK TO INSERT QUICK TEMPLATES
              </label>
              <div className="flex flex-col space-y-1.5 max-h-[175px] overflow-y-auto pr-1">
                {[
                  "Summarize this PDF and create study notes",
                  "Book an appointment next Friday",
                  "Extract tasks from this document",
                  "Send assignment alerts to Telegram",
                  "Research latest AI trends"
                ].map((sample, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => {
                      if (appendMode) {
                        setNaturalLanguagePrompt(prev => prev ? prev.trim() + " " + sample : sample);
                      } else {
                        setNaturalLanguagePrompt(sample);
                      }
                      setTerminalLogs(prev => [...prev, `💡 Clicked Quick Example: "${sample}"`]);
                    }}
                    className="p-2 w-full text-left font-sans font-semibold text-[11px] text-slate-400 hover:text-white rounded-xl bg-white/5 border border-transparent hover:border-white/10 hover:bg-slate-900/40 transition-all cursor-pointer truncate"
                  >
                    👉 {sample}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* AI Reasoning Section */}
          <div className="border border-white/10 rounded-3xl bg-white/5 p-5 backdrop-blur-lg space-y-3 shadow-md relative overflow-hidden">
            <div className="absolute top-0 right-0 h-16 w-16 bg-purple-500/5 blur-xl rounded-full"></div>
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold text-slate-200 tracking-wider font-display uppercase flex items-center gap-1.5">
                <Brain className="h-4 w-4 text-purple-400" />
                <span>AI Reasoning</span>
              </h3>
              <div className="flex items-center space-x-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                <span className="text-[10px] font-bold text-emerald-400 tracking-widest uppercase">Active Agent</span>
              </div>
            </div>

            <div className="space-y-2 bg-[#020617]/50 rounded-2xl p-4 border border-white/5 text-[11px] font-mono text-slate-300">
              {aiReasoning && aiReasoning.length > 0 ? (
                aiReasoning.map((log, index) => (
                  <motion.div
                    key={`${index}-${log}`}
                    initial={{ opacity: 0, x: -6 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.2, delay: index * 0.1 }}
                    className="flex items-start space-x-1.5"
                  >
                    <span className="text-purple-400 select-none font-bold">›</span>
                    <span className="leading-relaxed text-left antialiased">{log}</span>
                  </motion.div>
                ))
              ) : (
                <div className="text-slate-500 text-left py-2 italic font-sans text-2xs">
                  Awaiting natural language input trigger to start reasoning logs...
                </div>
              )}
            </div>

            <div className="flex items-center justify-between text-[10px] text-slate-500 font-medium px-1 pt-1">
              <span>Agent Confidence Meter</span>
              <span className="text-emerald-400 font-bold font-mono">{confidence}% Match</span>
            </div>
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
                  
                  {/* AI Generated Diagnostics Stats Panel */}
                  <div className="w-full max-w-md flex items-center justify-between px-2 pb-3.5 border-b border-white/5 mb-3 shrink-0">
                    <div className="flex items-center space-x-2">
                      <span className="inline-flex items-center px-2.5 py-1 rounded-full text-[10px] font-bold tracking-wider uppercase bg-gradient-to-r from-cyan-500/15 to-blue-500/15 text-cyan-400 border border-cyan-500/30 shadow-sm shadow-cyan-500/5">
                        ✨ AI Generated Workflow
                      </span>
                    </div>
                    <div className="flex items-center space-x-1.5 text-xs">
                      <span className="text-slate-400 font-medium font-sans">AI Confidence:</span>
                      <span className="font-mono font-black text-emerald-400 text-sm select-all">{confidence}%</span>
                    </div>
                  </div>

                  {/* Node 1: Webhook Trigger Node */}
                  <motion.div
                    key={`trig-node-${triggerNode.title}`}
                    initial={{ opacity: 0, y: 12, scale: 0.98 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -12, scale: 0.98 }}
                    transition={{ type: "spring", stiffness: 220, damping: 22 }}
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

                  {/* Node 2: AI Planner Node */}
                  <motion.div
                    key={`ai-node-${aiNode.title}-${aiNode.desc}`}
                    initial={{ opacity: 0, y: 12, scale: 0.98 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -12, scale: 0.98 }}
                    transition={{ type: "spring", stiffness: 220, damping: 22 }}
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
                    key={`action-node-${actionNode.title}`}
                    initial={{ opacity: 0, y: 12, scale: 0.98 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -12, scale: 0.98 }}
                    transition={{ type: "spring", stiffness: 220, damping: 22 }}
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
