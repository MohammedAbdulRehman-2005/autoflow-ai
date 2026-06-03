import { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  LayoutDashboard,
  GitBranch,
  ShoppingBag,
  ListTodo,
  Settings,
  ChevronLeft,
  ChevronRight,
  LogOut,
  Zap
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

export default function Sidebar({ isCollapsed, setIsCollapsed, onOpenSettings }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const menuItems = [
    { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
    { name: 'Workflow Builder', path: '/workflow-builder', icon: GitBranch },
    { name: 'Marketplace', path: '/marketplace', icon: ShoppingBag },
    { name: 'Logs', path: '/logs', icon: ListTodo },
  ];

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <motion.aside
      animate={{ width: isCollapsed ? '76px' : '260px' }}
      transition={{ duration: 0.3, ease: [0.25, 0.1, 0.25, 1] }}
      className="fixed bottom-0 top-0 left-0 z-30 flex flex-col border-r border-white/10 bg-slate-900/40 backdrop-blur-xl shadow-2xl"
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
              `flex items-center space-x-3.5 px-4 py-3 rounded-xl text-sm font-medium tracking-wide transition-all duration-200 outline-none group cursor-pointer border ${
                isActive
                  ? 'bg-white/10 text-white border-white/10 shadow-sm font-semibold'
                  : 'text-slate-400 hover:text-slate-100 hover:bg-white/5 border-transparent'
              }`
            }
          >
            <div className="flex-shrink-0 transition-transform duration-200 group-hover:scale-105">
              <item.icon className="h-5 w-5" />
            </div>
            {!isCollapsed && (
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="whitespace-nowrap"
              >
                {item.name}
              </motion.span>
            )}
          </NavLink>
        ))}

        {/* Settings button explicitly mentioned */}
        <button
          onClick={onOpenSettings}
          className="w-full flex items-center space-x-3.5 px-4 py-3 rounded-xl text-sm font-medium tracking-wide transition-all duration-200 text-slate-400 hover:text-slate-100 hover:bg-white/5 border border-transparent hover:border-white/5 group cursor-pointer outline-none text-left"
        >
          <div className="flex-shrink-0 transition-transform duration-200 group-hover:rotate-45">
            <Settings className="h-5 w-5" />
          </div>
          {!isCollapsed && (
            <motion.span
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="whitespace-nowrap"
            >
              Settings
            </motion.span>
          )}
        </button>
      </nav>

      {/* User Session Footer */}
      <div className="border-t border-white/10 p-4 bg-slate-900/20">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3 overflow-hidden">
            {/* User Avatar */}
            <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500/10 to-cyan-400/10 border border-white/10 text-cyan-200 font-semibold text-sm">
              {user?.name ? user.name.split(' ').map(n => n[0]).join('') : 'S'}
            </div>
            
            {/* User Details */}
            {!isCollapsed && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex flex-col overflow-hidden text-left"
              >
                <span className="text-sm font-semibold text-white truncate">{user?.name || 'Student'}</span>
                <span className="text-xs text-slate-500 truncate">{user?.email || ''}</span>
              </motion.div>
            )}
          </div>

          {/* Logout Action */}
          {!isCollapsed && (
            <button
              onClick={handleLogout}
              className="p-2 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/5 transition-all duration-200 group cursor-pointer"
              title="Logout"
            >
              <LogOut className="h-4 w-4" />
            </button>
          )}
        </div>
        {isCollapsed && (
          <button
            onClick={handleLogout}
            className="mt-3 mx-auto flex items-center justify-center p-2 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/5 transition-all duration-200 cursor-pointer w-full"
            title="Logout"
          >
            <LogOut className="h-4 w-4" />
          </button>
        )}
      </div>
    </motion.aside>
  );
}