import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Zap, Eye, EyeOff, Mail, Lock, ArrowRight, Sparkles, Info } from 'lucide-react';
import { motion } from 'motion/react';

const DEMO_EMAIL    = 'demo@autoflow.ai';
const DEMO_PASSWORD = 'demo1234';

export default function LoginPage() {
  const { login, error, clearError, isLoading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // Pre-fill with demo credentials
  const [email, setEmail]               = useState('');
  const [password, setPassword]         = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe]     = useState(true);
  const [localError, setLocalError]     = useState(null);
  const [demoWarning, setDemoWarning]   = useState(false);

  useEffect(() => { clearError(); setLocalError(null); }, []);

  const from = location.state?.from?.pathname || '/dashboard';

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLocalError(null);
    setDemoWarning(false);

    if (!email || !password) {
      setLocalError('Please fill in all fields.');
      return;
    }

    const result = await login(email, password);
    if (result !== false) {
      if (result?.demo) setDemoWarning(true);
      navigate(from, { replace: true });
    }
  };

  const fillDemo = () => {
    setEmail(DEMO_EMAIL);
    setPassword(DEMO_PASSWORD);
    setLocalError(null);
  };

  return (
    <div className="relative min-h-screen bg-[#020617] flex flex-col items-center justify-center px-4 sm:px-6 lg:px-8 overflow-hidden select-none">

      {/* Ambient background */}
      <div className="absolute inset-0 z-0 overflow-hidden">
        <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-blue-600/15 rounded-full blur-[120px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-cyan-500/15 rounded-full blur-[120px]" />
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#1f293708_1px,transparent_1px),linear-gradient(to_bottom,#1f293708_1px,transparent_1px)] bg-[size:24px_24px]" />
      </div>

      <div className="relative z-10 w-full max-w-md">

        {/* Brand */}
        <div className="text-center mb-8">
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
            className="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-600 to-cyan-400 p-0.5 shadow-[0_0_30px_rgba(59,130,246,0.2)] mb-4"
          >
            <Zap className="h-7 w-7 text-white" />
          </motion.div>
          <motion.h1
            initial={{ y: -10, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="text-3xl font-extrabold tracking-tight text-white font-display"
          >
            AutoFlow<span className="text-cyan-400">.AI</span>
          </motion.h1>
          <motion.p
            initial={{ y: -5, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="mt-2 text-sm text-slate-400 font-sans font-medium"
          >
            Turn natural language into automation
          </motion.p>
        </div>

        {/* Form card */}
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.3, ease: [0.25, 0.1, 0.25, 1] }}
          className="border border-white/10 rounded-3xl bg-white/5 p-8 shadow-2xl backdrop-blur-lg"
        >
         

          <form className="space-y-5" onSubmit={handleSubmit}>

            {/* Error banner */}
            {(error || localError) && (
              <motion.div
                initial={{ opacity: 0, y: -5 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-rose-500/10 border border-rose-500/20 rounded-xl p-3 text-xs font-semibold text-rose-400 text-center"
              >
                {error || localError}
              </motion.div>
            )}

            {/* Email */}
            <div className="space-y-1.5 text-left">
              <label className="text-[10px] font-bold text-slate-350 tracking-wider font-display" htmlFor="email">
                EMAIL
              </label>
              <div className="relative">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3.5 text-slate-500">
                  <Mail className="h-4 w-4" />
                </div>
                <input
                  id="email"
                  type="email"
                  required
                  placeholder="demo@autoflow.ai"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-xl border border-white/10 bg-white/5 py-3 pr-4 pl-10 text-xs text-white placeholder-slate-500 outline-none backdrop-blur-md transition-all hover:border-white/20 focus:border-cyan-500/50 focus:bg-slate-900/40"
                />
              </div>
            </div>

            {/* Password */}
            <div className="space-y-1.5 text-left">
              <div className="flex justify-between items-center">
                <label className="text-[10px] font-bold text-slate-350 tracking-wider font-display" htmlFor="password">
                  PASSWORD
                </label>
              
              </div>
              <div className="relative">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3.5 text-slate-500">
                  <Lock className="h-4 w-4" />
                </div>
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  required
                  placeholder="Enter password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-xl border border-white/10 bg-white/5 py-3 pr-11 pl-10 text-xs text-white placeholder-slate-500 outline-none backdrop-blur-md transition-all hover:border-white/20 focus:border-cyan-500/50 focus:bg-slate-900/40"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 flex items-center pr-3.5 text-slate-500 hover:text-slate-300 cursor-pointer"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            {/* Remember me */}
            <div className="flex items-center">
              <input
                id="remember_me"
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                className="h-4 w-4 rounded border-white/10 bg-white/5 text-cyan-500 focus:outline-none focus:ring-0 cursor-pointer"
              />
              <label htmlFor="remember_me" className="ml-2 py-0.5 text-xs font-medium text-slate-400 select-none cursor-pointer">
                Keep me signed in on this device
              </label>
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={isLoading}
              className="relative w-full flex items-center justify-center space-x-2 py-3 px-4 rounded-xl font-bold text-sm bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 text-white shadow-lg shadow-blue-500/20 hover:shadow-cyan-500/30 transition-all duration-300 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed group active:scale-[0.98]"
            >
              {isLoading ? (
                <div className="h-5 w-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  <span>Continue into Workspace</span>
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                </>
              )}
            </button>
          </form>

         

          {/* Create account link */}
          <div className="mt-4 text-center">
            <span className="text-xs text-slate-550 font-medium">New to AutoFlow AI? </span>
            <Link to="/signup" className="text-xs font-semibold text-cyan-400 hover:text-cyan-300 hover:underline transition-colors">
              Create free Account
            </Link>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
