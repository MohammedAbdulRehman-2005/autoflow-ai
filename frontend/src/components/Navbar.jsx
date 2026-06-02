import React, { useState, useRef, useEffect } from 'react';
import { Search, Bell, ChevronDown, User as UserIcon, Settings, LogOut, Shield, Zap } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';

export default function Navbar({ onSearch, onOpenSettings }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  const profileRef = useRef(null);
  const notifRef = useRef(null);

  const notifications = [
    { id: 1, title: 'Workflow Triggered Successfully', desc: 'Email Monitoring Trigger fired 2 minutes ago', time: '2m ago', type: 'success' },
    { id: 2, title: 'AI Automation Refined', desc: 'Step 2 planner summary optimization active', time: '1h ago', type: 'info' },
    { id: 3, title: 'Database Connection Alert', desc: 'Query latency in Calendar Sync exceeded limit slightly', time: '5h ago', type: 'warning' },
  ];

  // Close dropdowns on outside click
  useEffect(() => {
    function handleClickOutside(event) {
      if (profileRef.current && !profileRef.current.contains(event.target)) {
        setShowProfileMenu(false);
      }
      if (notifRef.current && !notifRef.current.contains(event.target)) {
        setShowNotifications(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSearchChange = (e) => {
    const val = e.target.value;
    setSearchTerm(val);
    if (onSearch) onSearch(val);
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <header className="fixed top-0 right-0 left-0 z-20 flex h-16 items-center justify-between border-b border-white/10 bg-slate-950/20 px-6 md:px-10 backdrop-blur-md transition-all duration-300">
      {/* Search Bar - styled with premium glassmorphism */}
      <div className="flex flex-1 max-w-sm">
        <div className="group relative w-full">
          <Search className="absolute top-1/2 left-3.5 h-4 w-4 -translate-y-1/2 text-slate-400 group-focus-within:text-cyan-400 transition-colors" />
          <input
            type="text"
            value={searchTerm}
            onChange={handleSearchChange}
            placeholder="Search workflows, triggers, templates..."
            className="w-full rounded-full border border-white/10 bg-white/5 py-1.5 pr-4 pl-10 text-xs text-slate-200 placeholder-slate-500 outline-none backdrop-blur-md transition-all hover:border-white/20 focus:border-cyan-500/40 focus:bg-slate-900/40 font-sans shadow-sm"
          />
        </div>
      </div>

      {/* Action Icons */}
      <div className="flex items-center space-x-4">

        {/* Notifications Dropdown */}
        <div className="relative" ref={notifRef}>
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="relative flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 bg-white/5 text-slate-400 hover:text-white hover:bg-white/10 focus:bg-white/10 transition-all duration-200 cursor-pointer shadow-sm"
          >
            <Bell className="h-4.5 w-4.5" />
            <span className="absolute top-2.5 right-2.5 h-1.5 w-1.5 rounded-full bg-cyan-400 shadow-[0_0_8px_#22d3ee]"></span>
          </button>

          <AnimatePresence>
            {showNotifications && (
              <motion.div
                initial={{ opacity: 0, y: 10, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 10, scale: 0.95 }}
                transition={{ duration: 0.15 }}
                className="absolute right-0 mt-2 w-80 rounded-2xl border border-white/10 bg-slate-900/95 p-1 shadow-2xl backdrop-blur-2xl"
              >
                <div className="px-4 py-3 border-b border-white/10 flex justify-between items-center">
                  <span className="text-sm font-semibold text-white font-display">Notifications</span>
                  <span className="text-2xs text-cyan-400 font-mono">3 UNREAD</span>
                </div>
                <div className="py-1 max-h-80 overflow-y-auto">
                  {notifications.map((notif) => (
                    <div
                      key={notif.id}
                      className="px-4 py-2.5 hover:bg-white/5 transition-colors cursor-pointer flex flex-col"
                    >
                      <div className="flex justify-between items-start">
                        <span className="text-xs font-medium text-slate-200">{notif.title}</span>
                        <span className="text-[10px] text-slate-500 shrink-0 font-mono ml-2">{notif.time}</span>
                      </div>
                      <span className="text-2xs text-slate-400 mt-0.5 line-clamp-1">{notif.desc}</span>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Profile Dropdown */}
        <div className="relative" ref={profileRef}>
          <button
            onClick={() => setShowProfileMenu(!showProfileMenu)}
            className="flex items-center space-x-2 rounded-xl border border-white/10 bg-white/5 p-1.5 pr-3 hover:border-white/20 hover:bg-white/10 transition-all cursor-pointer shadow-sm"
          >
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-cyan-400 p-0.5 text-[11px] font-bold text-white shadow-[0_0_8px_rgba(59,130,246,0.3)]">
              {user?.name ? user.name.split(' ').map(n => n[0]).join('') : 'D'}
            </div>
            <div className="hidden md:flex flex-col items-start text-xs text-left">
              <span className="font-semibold text-white truncate max-w-[100px] font-display">{user?.name || 'Demo User'}</span>
            </div>
            <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
          </button>

          <AnimatePresence>
            {showProfileMenu && (
              <motion.div
                initial={{ opacity: 0, y: 10, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 10, scale: 0.95 }}
                transition={{ duration: 0.15 }}
                className="absolute right-0 mt-2 w-56 rounded-2xl border border-white/10 bg-slate-900/95 p-1.5 shadow-2xl backdrop-blur-2xl"
              >
                <div className="px-3.5 py-3 border-b border-white/10">
                  <p className="text-xs font-semibold text-slate-200 font-display">{user?.name || 'Demo User'}</p>
                  <p className="text-[10px] text-slate-500 font-medium mt-0.5 truncate font-mono">{user?.email || 'demo@autoflow.ai'}</p>
                </div>
                <div className="py-1">
                  <button
                    onClick={() => {
                      setShowProfileMenu(false);
                    }}
                    className="w-full flex items-center space-x-2 rounded-lg px-3 py-2 text-xs text-slate-300 hover:text-white hover:bg-white/5 transition-colors text-left"
                  >
                    <UserIcon className="h-4 w-4 text-slate-400" />
                    <span>My Account</span>
                  </button>
                  <button
                    onClick={() => {
                      setShowProfileMenu(false);
                      onOpenSettings();
                    }}
                    className="w-full flex items-center space-x-2 rounded-lg px-3 py-2 text-xs text-slate-300 hover:text-white hover:bg-white/5 transition-colors text-left"
                  >
                    <Settings className="h-4 w-4 text-slate-400" />
                    <span>Workspace Settings</span>
                  </button>
                </div>
                <div className="border-t border-white/10 pt-1 mt-1">
                  <button
                    onClick={handleLogout}
                    className="w-full flex items-center space-x-2 rounded-lg px-3 py-2 text-xs text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 transition-colors cursor-pointer text-left"
                  >
                    <LogOut className="h-4 w-4" />
                    <span>Sign Out</span>
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </header>
  );
}