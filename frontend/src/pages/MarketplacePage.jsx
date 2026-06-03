import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ShoppingBag,
  Search,
  Download,
  CheckCircle,
  RotateCw,
  GitBranch,
  ArrowRight,
  TrendingUp,
  Brain,
  Layers,
  Sparkles,
  HelpCircle
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { INITIAL_TEMPLATES, addWorkflow } from '../mockData';

export default function MarketplacePage() {
  const navigate = useNavigate();
  const [templates, setTemplates] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [installingId, setInstallingId] = useState(null);

  useEffect(() => {
    setTemplates(INITIAL_TEMPLATES);
  }, []);

  const categories = [
    'All', 
    'Email Automation', 
    'Telegram Notifications', 
    'Meeting Reminders', 
    'Calendar Scheduling', 
    'Document Processing', 
    'Student Productivity Automation',
    'AI Task Automation'
  ];

  const filteredTemplates = templates.filter((tpl) => {
    const matchesSearch = tpl.title.toLowerCase().includes(searchTerm.toLowerCase()) || 
                          tpl.description.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = selectedCategory === 'All' || tpl.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  const handleInstallTemplate = (template) => {
    setInstallingId(template.id);
    setTimeout(() => {
      // Install directly so that user sees updates in Dashboard Page!
      addWorkflow(
        `[Preset] ${template.title}`,
        template.description,
        template.trigger,
        template.action
      );
      setInstallingId(null);
      alert(`Successfully deployed "${template.title}" template inside your active workflows container!`);
      navigate('/dashboard');
    }, 1500);
  };

  return (
    <div className="space-y-8 select-none text-left">
      
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white font-display flex items-center gap-2">
            <ShoppingBag className="h-8 w-8 text-blue-500 animate-pulse" />
            <span>Workflow Library</span>
          </h1>
          <p className="text-sm text-slate-400 mt-1 font-sans">
            Bootstrap setups immediately using 1-click verified pre-built Gemini workflow models.
          </p>
        </div>
      </div>

      {/* Grid Filters Control Room */}
      <div className="flex flex-col lg:flex-row gap-4 justify-between items-stretch lg:items-center pb-2">
        
        {/* Categories selector */}
        <div className="flex items-center space-x-1.5 overflow-x-auto pb-1 md:pb-0 [&::-webkit-scrollbar]:hidden">
          {categories.map((cat) => (
            <button
               key={cat}
               onClick={() => setSelectedCategory(cat)}
               className={`px-3.5 py-1.5 rounded-xl text-xs font-bold cursor-pointer transition-all shrink-0 shadow-sm ${
                selectedCategory === cat
                   ? 'bg-gradient-to-r from-blue-600 to-cyan-500 text-white'
                   : 'bg-white/5 border border-white/10 text-slate-400 hover:text-white hover:border-white/20'
               }`}
            >
              {cat.toUpperCase()}
            </button>
          ))}
        </div>

        {/* Search Input box */}
        <div className="relative w-full lg:w-80 shrink-0">
          <Search className="absolute top-1/2 left-3.5 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search templates..."
            className="w-full rounded-xl border border-white/10 bg-white/5 py-2.5 pr-4 pl-10 text-xs text-white placeholder-slate-500 outline-none hover:border-white/20 focus:border-cyan-500/50"
          />
        </div>

      </div>

      {/* Templates responsive grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        <AnimatePresence mode="wait">
          {filteredTemplates.map((tpl) => (
            <motion.div
              key={tpl.id}
              layout
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.98 }}
              transition={{ duration: 0.25 }}
              className="border border-white/10 rounded-3xl bg-white/5 p-6 backdrop-blur-lg flex flex-col justify-between hover:border-blue-500/35 hover:shadow-lg transition-all relative overflow-hidden group shadow-sm"
            >
              <div className="absolute top-0 right-0 h-16 w-16 bg-blue-500/5 blur-xl rounded-full"></div>
              
              <div>
                {/* Category label & installations count */}
                <div className="flex justify-between items-center mb-4 text-[10px] font-mono font-bold tracking-wider uppercase text-slate-500">
                  <span className="text-cyan-400 border border-cyan-500/10 bg-cyan-500/5 px-2 py-0.5 rounded-full">
                    {tpl.category}
                  </span>
                  <span>
                    {tpl.installs.toLocaleString()} INSTALLS
                  </span>
                </div>

                {/* Title */}
                <h3 className="text-base font-bold text-slate-100 group-hover:text-white font-display mb-2 text-left leading-snug">
                  {tpl.title}
                </h3>

                {/* Description */}
                <p className="text-xs text-slate-400 font-sans font-medium line-clamp-3 mb-5 text-left leading-relaxed">
                  {tpl.description}
                </p>

                {/* Triggers and Connections */}
                <div className="space-y-2 border-t border-white/10 pt-4.5 mb-6 text-[11px] font-mono text-slate-500 flex flex-col items-start">
                  <div className="flex items-center space-x-2">
                    <span className="text-blue-400 font-bold">TRIGGER:</span>
                    <span className="text-slate-300 font-medium">{tpl.trigger}</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="text-cyan-400 font-bold">ACTION:</span>
                    <span className="text-slate-300 font-medium">{tpl.action}</span>
                  </div>
                </div>
              </div>

              {/* Install and deploy button container */}
              <div className="flex justify-between items-center pt-2">
                <span className={`text-[10px] font-bold font-mono border px-2 py-0.5 rounded-full ${
                  tpl.complexity === 'Advanced' ? 'text-red-400 border-red-500/15 bg-red-500/5' :
                  tpl.complexity === 'Medium' ? 'text-blue-400 border-blue-500/15 bg-blue-500/5' : 'text-emerald-400 border-emerald-500/15 bg-emerald-500/5'
                }`}>
                  {tpl.complexity.toUpperCase()}
                </span>

                <button
                  onClick={() => handleInstallTemplate(tpl)}
                  disabled={installingId !== null}
                  className="flex items-center space-x-1.5 px-3.5 py-1.5 bg-white/5 hover:bg-white/10 text-white rounded-xl text-xs font-bold border border-white/10 hover:border-white/20 transition-all cursor-pointer disabled:opacity-50 shadow-sm"
                >
                  {installingId === tpl.id ? (
                    <RotateCw className="h-3.5 w-3.5 animate-spin text-cyan-400" />
                  ) : (
                    <Download className="h-3.5 w-3.5 text-blue-400 group-hover:translate-y-0.5 transition-transform" />
                  )}
                  <span>{installingId === tpl.id ? 'Deploying...' : 'Deploy'}</span>
                </button>
              </div>

            </motion.div>
          ))}
        </AnimatePresence>
      </div>

    </div>
  );
}