import { useState, useEffect } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  LayoutDashboard,
  GitBranch,
  Activity,
  ShieldAlert,
  PauseCircle,
  Terminal,
  ShoppingBag,
  Settings,
  ChevronLeft,
  ChevronRight,
  LogOut,
  Zap
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { apiBridge } from '../services/apiBridge';

export default function Sidebar({ isCollapsed, setIsCollapsed, onOpenSettings }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const [pendingApprovalsCount, setPendingApprovalsCount] = useState(0);
  const [pendingIncidentsCount, setPendingIncidentsCount] = useState(0);

  useEffect(() => {
    async function fetchCounts() {
      try {
        const [apprs, incs] = await Promise.all([
          apiBridge.getApprovals({ status: 'pending' }),
          apiBridge.getRecoveryIncidents({ status: 'pending_triage' })
        ]);
        setPendingApprovalsCount((apprs || []).length);
        setPendingIncidentsCount((incs || []).length);
      } catch (_) {}
    }
    fetchCounts();
    const interval = setInterval(fetchCounts, 15000);
    return () => clearInterval(interval);
  }, []);

  const menuItems = [
    { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
    { name: 'Workflow Studio', path: '/workflow-builder', icon: GitBranch },
    { name: 'Execution Monitor', path: '/executions', icon: Activity },
    { 
      name: 'Recovery Center', 
      path: '/recovery', 
      icon: ShieldAlert, 
      badge: pendingIncidentsCount > 0 ? pendingIncidentsCount : null,
      badgeColor: 'bg-rose-500/20 text-rose-300 border-rose-500/30'
    },
    { 
      name: 'Approval Center', 
      path: '/approvals', 
      icon: PauseCircle, 
      badge: pendingApprovalsCount > 0 ? pendingApprovalsCount : null,
      badgeColor: 'bg-purple-500/20 text-purple-300 border-purple-500/30'
    },
    { name: 'Raw Logs', path: '/logs', icon: Terminal },
    { name: 'Marketplace', path: '/marketplace', icon: ShoppingBag },
  ];

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <motion.aside
      animate={{ width: isCollapsed ? '76px' : '260px' }}
      transition={{ duration: 0.3, ease: [0.25, 0.1, 0.25, 1] }}
      className="fixed bottom-0 top-0 left-0 z-30 flex flex-col border-r border-white/10 bg-slate-900/60 backdrop-blur-xl shadow-2xl"
    >
      {/* Brand Header */}
      <div className="flex h-16 items-center justify-between px-5 relative border-b border-white/10">
        <NavLink to="/dashboard" className="flex items-center space-x-3 group outline-none">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-cyan-400 p-0.5 shadow-[0_0_15px_rgba(59,130,246,0.3)] group-hover:shadow-[0_0_22px_rgba(34,211,238,0.5)] transition-all duration-300">
            <Zap className="h-5 w-5 text-white" />
          </div>
          <AnimatePresence mode="wait">
            {!isCollapsed && (
              <motion.span
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                transition={{ duration: 0.2 }}
                className="bg-gradient-to-r from-white to-slate-400 bg-clip-text text-lg font-bold tracking-tight text-transparent font-display"
              >
                AutoFlow<span className="text-cyan-400 font-medium">.AI</span>
              </motion.span>
            )}
          </AnimatePresence>
        </NavLink>

        {/* Floating Collapse Trigger */}
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="absolute -right-3 top-5 flex h-6.5 w-6.5 items-center justify-center rounded-full border border-white/10 bg-slate-900/90 text-slate-400 hover:text-white hover:bg-slate-800 cursor-pointer shadow-md transition-colors"
        >
          {isCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </button>
      </div>

      {/* Primary Navigation */}
      <nav className="flex-1 space-y-1.5 py-6 px-3.5 overflow-y-auto [&::-webkit-scrollbar]:hidden">
        {menuItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-medium tracking-wide transition-all duration-200 outline-none group cursor-pointer border ${
                isActive
                  ? 'bg-white/10 text-white border-white/10 shadow-sm font-semibold'
                  : 'text-slate-400 hover:text-slate-100 hover:bg-white/5 border-transparent'
              }`
            }
          >
            <div className="flex items-center space-x-3 min-w-0">
              <div className="flex-shrink-0 transition-transform duration-200 group-hover:scale-105">
                <item.icon className="h-4.5 w-4.5" />
              </div>
              {!isCollapsed && (
                <motion.span
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="whitespace-nowrap truncate font-sans"
                >
                  {item.name}
                </motion.span>
              )}
            </div>

            {item.badge && !isCollapsed && (
              <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono font-bold border ${item.badgeColor || 'bg-cyan-500/20 text-cyan-300'}`}>
                {item.badge}
              </span>
            )}
          </NavLink>
        ))}

        {/* Settings */}
        <NavLink
          to="/settings"
          className={({ isActive }) =>
            `w-full flex items-center space-x-3 px-3.5 py-2.5 rounded-xl text-xs font-medium tracking-wide transition-all duration-200 border group cursor-pointer outline-none text-left ${
              isActive
                ? 'text-white bg-white/8 border-white/10 shadow-sm'
                : 'text-slate-400 hover:text-slate-100 hover:bg-white/5 border-transparent hover:border-white/5'
            }`
          }
        >
          <div className="flex-shrink-0 transition-transform duration-200 group-hover:rotate-45">
            <Settings className="h-4.5 w-4.5" />
          </div>
          {!isCollapsed && (
            <motion.span
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="whitespace-nowrap font-sans"
            >
              Settings
            </motion.span>
          )}
        </NavLink>
      </nav>

      {/* User Session Footer */}
      <div className="border-t border-white/10 p-4 bg-slate-900/30">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3 overflow-hidden">
            <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500/10 to-cyan-400/10 border border-white/10 text-cyan-200 font-semibold text-xs">
              {user?.name ? user.name.split(' ').map(n => n[0]).join('') : 'OP'}
            </div>
            
            {!isCollapsed && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex flex-col overflow-hidden text-left"
              >
                <span className="text-xs font-semibold text-white truncate font-display">
                  {user?.name || 'Security Operator'}
                </span>
                <span className="text-[10px] text-slate-500 truncate font-mono">
                  {user?.email || 'admin@autoflow.ai'}
                </span>
              </motion.div>
            )}
          </div>

          {!isCollapsed && (
            <button
              onClick={handleLogout}
              className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-all cursor-pointer"
              title="Logout"
            >
              <LogOut className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>
    </motion.aside>
  );
}