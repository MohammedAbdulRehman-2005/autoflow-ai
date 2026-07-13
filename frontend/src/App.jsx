import { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import ProtectedRoute from './routes/ProtectedRoute';
import { NodeRegistryProvider } from './context/NodeRegistryContext';

// Pages
import LoginPage from './pages/LoginPage';
import SignupPage from './pages/SignupPage';
import DashboardPage from './pages/DashboardPage';
import WorkflowBuilderPage from './pages/WorkflowBuilderPage';
import MarketplacePage from './pages/MarketplacePage';
import LogsPage from './pages/LogsPage';
import SettingsPage from './pages/SettingsPage';

// Components
import Sidebar from './components/Sidebar';
import Navbar from './components/Navbar';

// Icons for Settings pane
import { X, Shield, Cpu, Settings, HardDrive, HelpCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

// Wrapper for workspace pages (Navbar + Sidebar layout)
function WorkspaceLayout() {
  const { user } = useAuth();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  
  // Custom states for mock Profile and connected services settings
  const [profileName, setProfileName] = useState('');
  const [profileEmail, setProfileEmail] = useState('');
  const [gmailConnected, setGmailConnected] = useState(true);
  const [telegramConnected, setTelegramConnected] = useState(true);
  const [calendarConnected, setCalendarConnected] = useState(true);

  // Persistent AI Provider & Model States
  const [selectedProvider, setSelectedProvider] = useState(() => {
    return localStorage.getItem('autoflow_ai_provider') || 'Gemini';
  });
  const [selectedModel, setSelectedModel] = useState(() => {
    return localStorage.getItem('autoflow_ai_model') || 'Gemini 2.5 Flash';
  });

  // Providers map with respective models
  const providerModels = {
    Gemini: ['Gemini 2.5 Flash', 'Gemini 2.5 Pro', 'Gemini 1.5 Pro'],
    OpenAI: ['GPT-4o', 'GPT-4o-mini', 'o1-pro'],
    Grok: ['Grok 2 Stable', 'Grok 2 Beta', 'Grok 1.5']
  };

  // If the provider changes, auto-select its first available model
  const handleProviderChange = (newProvider) => {
    setSelectedProvider(newProvider);
    const models = providerModels[newProvider] || [];
    if (models.length > 0) {
      setSelectedModel(models[0]);
    }
  };

  // Save changes to localStorage
  const handleApplyChanges = () => {
    localStorage.setItem('autoflow_ai_provider', selectedProvider);
    localStorage.setItem('autoflow_ai_model', selectedModel);
    setShowSettings(false);
    alert("Workspace and AI Configuration settings successfully synchronized!");
  };

  // Sync profile details with current user context
  useEffect(() => {
    if (user) {
      setProfileName(user.name || '');
      setProfileEmail(user.email || '');
    }
  }, [user]);

  return (
    <div className="min-h-screen bg-[#020617] text-slate-100 flex font-sans overflow-x-hidden antialiased relative">
      {/* Background Mesh Gradients */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        <div className="absolute top-[-10%] left-[-10%] w-[45%] h-[45%] bg-blue-600/15 rounded-full blur-[120px]"></div>
        <div className="absolute bottom-[-10%] right-[-10%] w-[45%] h-[45%] bg-cyan-500/15 rounded-full blur-[120px]"></div>
        <div className="absolute top-[30%] left-[55%] w-[30%] h-[30%] bg-purple-600/5 rounded-full blur-[130px]"></div>
      </div>

      {/* Main Sidebar */}
      <Sidebar
        isCollapsed={isCollapsed}
        setIsCollapsed={setIsCollapsed}
        onOpenSettings={() => setShowSettings(true)}
      />

      {/* Workspace Area Container */}
      <div className="flex-1 flex flex-col min-h-screen relative z-10 transition-all duration-300" style={{ paddingLeft: isCollapsed ? '76px' : '260px' }}>
        
        {/* Top Navbar */}
        <Navbar onOpenSettings={() => setShowSettings(true)} />

        {/* Content Page Ingress */}
        <main className="flex-1 pt-24 px-6 md:px-10 pb-16">
          <Outlet />
        </main>
      </div>

      {/* Interactive Floating Workspace Settings Panel (Slide-over panel) */}
      <AnimatePresence>
        {showSettings && (
          <>
            {/* Dark glass screen dimmer */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.6 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowSettings(false)}
              className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
            ></motion.div>

            {/* Slider Drawer Container */}
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 220 }}
              className="fixed top-0 bottom-0 right-0 z-50 w-full max-w-md border-l border-white/10 glass-heavy p-7 shadow-2xl flex flex-col justify-between text-left"
            >
              <div className="space-y-6 overflow-y-auto max-h-[80vh] pr-1">
                
                {/* Panel Header */}
                <div className="flex items-center justify-between pb-4 border-b border-white/10">
                  <div className="flex items-center space-x-2">
                    <Settings className="h-5 w-5 text-cyan-400" />
                    <span className="text-base font-bold text-white font-display">Workspace Settings</span>
                  </div>
                  <button
                    onClick={() => setShowSettings(false)}
                    className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors cursor-pointer"
                  >
                    <X className="h-4.5 w-4.5" />
                  </button>
                </div>

                {/* 1. Profile Settings Section */}
                <div className="space-y-3.5">
                  <div className="flex items-center space-x-1.5 text-slate-300">
                    <Shield className="h-4 w-4 text-cyan-400" />
                    <h4 className="text-xs font-bold tracking-wider uppercase font-display">Profile Settings</h4>
                  </div>
                  <div className="space-y-3 text-xs text-left">
                    <div className="space-y-1">
                      <label className="text-[10px] font-bold text-slate-400 tracking-wider">FULL NAME</label>
                      <input
                        type="text"
                        value={profileName}
                        onChange={(e) => setProfileName(e.target.value)}
                        className="w-full rounded-xl border border-white/10 bg-slate-950/40 py-2.5 px-3.5 text-xs text-white placeholder-slate-600 outline-none hover:border-white/20 focus:border-cyan-500/40 focus:bg-slate-950/70 transition-all font-sans"
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-[10px] font-bold text-slate-400 tracking-wider">EMAIL ADDRESS</label>
                      <input
                        type="email"
                        value={profileEmail}
                        onChange={(e) => setProfileEmail(e.target.value)}
                        className="w-full rounded-xl border border-white/10 bg-slate-950/40 py-2.5 px-3.5 text-xs text-white placeholder-slate-600 outline-none hover:border-white/20 focus:border-cyan-500/40 focus:bg-slate-950/70 transition-all font-mono"
                      />
                    </div>
                  </div>
                </div>

                {/* 2. Connected Services Section */}
                <div className="space-y-3">
                  <div className="flex items-center space-x-1.5 text-slate-300">
                    <Cpu className="h-4 w-4 text-blue-400" />
                    <h4 className="text-xs font-bold tracking-wider uppercase font-display">Connected Services</h4>
                  </div>
                  <div className="space-y-2">
                    {/* Gmail */}
                    <div className="flex items-center justify-between p-3 rounded-xl border border-white/10 bg-slate-950/20">
                      <div className="flex flex-col text-left">
                        <span className="text-xs font-bold text-slate-200">Gmail Integration</span>
                        <span className="text-[10px] text-slate-500 mt-0.5">Academic inbox tracker</span>
                      </div>
                      <button
                        onClick={() => setGmailConnected(!gmailConnected)}
                        className={`flex items-center space-x-1.5 px-3 py-1 rounded-full text-[10px] font-bold border transition-all cursor-pointer ${
                          gmailConnected 
                            ? 'text-emerald-450 border-emerald-500/20 bg-emerald-500/10'
                            : 'text-slate-400 border-white/15 bg-white/5'
                        }`}
                      >
                        <span className={`h-1.5 w-1.5 rounded-full ${gmailConnected ? 'bg-emerald-400' : 'bg-slate-500'}`}></span>
                        <span>{gmailConnected ? 'CONNECTED' : 'DISABLED'}</span>
                      </button>
                    </div>

                    {/* Telegram */}
                    <div className="flex items-center justify-between p-3 rounded-xl border border-white/10 bg-slate-950/20">
                      <div className="flex flex-col text-left">
                        <span className="text-xs font-bold text-slate-200">Telegram Channel</span>
                        <span className="text-[10px] text-slate-500 mt-0.5">Study group alerts bot</span>
                      </div>
                      <button
                        onClick={() => setTelegramConnected(!telegramConnected)}
                        className={`flex items-center space-x-1.5 px-3 py-1 rounded-full text-[10px] font-bold border transition-all cursor-pointer ${
                          telegramConnected 
                            ? 'text-emerald-450 border-emerald-500/20 bg-emerald-500/10'
                            : 'text-slate-400 border-white/15 bg-white/5'
                        }`}
                      >
                        <span className={`h-1.5 w-1.5 rounded-full ${telegramConnected ? 'bg-emerald-400' : 'bg-slate-500'}`}></span>
                        <span>{telegramConnected ? 'CONNECTED' : 'DISABLED'}</span>
                      </button>
                    </div>

                    {/* Calendar */}
                    <div className="flex items-center justify-between p-3 rounded-xl border border-white/10 bg-slate-950/20">
                      <div className="flex flex-col text-left">
                        <span className="text-xs font-bold text-slate-200">Google Calendar</span>
                        <span className="text-[10px] text-slate-500 mt-0.5">Consultation & due-dates sync</span>
                      </div>
                      <button
                        onClick={() => setCalendarConnected(!calendarConnected)}
                        className={`flex items-center space-x-1.5 px-3 py-1 rounded-full text-[10px] font-bold border transition-all cursor-pointer ${
                          calendarConnected 
                            ? 'text-emerald-450 border-emerald-500/20 bg-emerald-500/10'
                            : 'text-slate-400 border-white/15 bg-white/5'
                        }`}
                      >
                        <span className={`h-1.5 w-1.5 rounded-full ${calendarConnected ? 'bg-emerald-400' : 'bg-slate-500'}`}></span>
                        <span>{calendarConnected ? 'CONNECTED' : 'DISABLED'}</span>
                      </button>
                    </div>
                  </div>
                </div>

                {/* 3. AI Configuration Section */}
                <div className="space-y-3">
                  <div className="flex items-center space-x-1.5 text-slate-300">
                    <HardDrive className="h-4 w-4 text-purple-400" />
                    <h4 className="text-xs font-bold tracking-wider uppercase font-display">AI Configuration</h4>
                  </div>
                  <div className="p-3.5 rounded-xl border border-white/10 bg-slate-950/20 space-y-3 text-xs">
                    {/* Provider Selection */}
                    <div className="space-y-1">
                      <label className="text-[10px] font-bold text-slate-500 tracking-wider">AI PROVIDER</label>
                      <select
                        value={selectedProvider}
                        onChange={(e) => handleProviderChange(e.target.value)}
                        className="w-full rounded-xl border border-white/10 bg-slate-950/50 py-2 px-3 text-xs text-white outline-none hover:border-white/25 focus:border-cyan-500/40 cursor-pointer h-9"
                      >
                        <option value="Gemini" className="bg-slate-950 text-white">Gemini</option>
                        <option value="OpenAI" className="bg-slate-950 text-white">OpenAI</option>
                        <option value="Grok" className="bg-slate-950 text-white">Grok</option>
                      </select>
                    </div>

                    {/* Model Selection */}
                    <div className="space-y-1">
                      <label className="text-[10px] font-bold text-slate-500 tracking-wider">AI MODEL ENGINE</label>
                      <select
                        value={selectedModel}
                        onChange={(e) => setSelectedModel(e.target.value)}
                        className="w-full rounded-xl border border-white/10 bg-slate-950/50 py-2 px-3 text-xs text-white outline-none hover:border-white/25 focus:border-cyan-500/40 cursor-pointer h-9"
                      >
                        {(providerModels[selectedProvider] || []).map((model) => (
                          <option key={model} value={model} className="bg-slate-950 text-white">
                            {model}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="flex justify-between items-center text-slate-400 font-medium pt-1 border-t border-white/5">
                      <span>Status:</span>
                      <span className="font-bold text-emerald-400 flex items-center gap-1.5">
                        <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                        Active
                      </span>
                    </div>
                  </div>
                </div>

              </div>

              {/* Panel Footer */}
              <div className="border-t border-white/10 pt-4">
                <button
                  onClick={handleApplyChanges}
                  className="w-full py-2.5 rounded-xl font-bold text-xs text-center bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 text-white cursor-pointer active:scale-98 transition-all shadow-lg shadow-blue-500/10"
                >
                  Apply Workspace Changes
                </button>
              </div>

            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}

// Global Application Router root
export default function App() {
  return (
    <Router>
      <AuthProvider>
        <Routes>
          {/* Public Auth routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />

          {/* Secure workspace layout wrap */}
          <Route path="/" element={<ProtectedRoute><WorkspaceLayout /></ProtectedRoute>}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="workflow-builder" element={<NodeRegistryProvider><WorkflowBuilderPage /></NodeRegistryProvider>} />
            <Route path="marketplace" element={<MarketplacePage />} />
            <Route path="logs" element={<LogsPage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>

          {/* Unmatched wildcard route recovery */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </AuthProvider>
    </Router>
  );
}
