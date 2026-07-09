import { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import ProtectedRoute from './routes/ProtectedRoute';

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


// Wrapper for workspace pages (Navbar + Sidebar layout)
function WorkspaceLayout() {
  const { user } = useAuth();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  


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
            <Route path="workflow-builder" element={<WorkflowBuilderPage />} />
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
