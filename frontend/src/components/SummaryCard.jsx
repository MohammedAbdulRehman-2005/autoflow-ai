import { motion } from 'framer-motion';

export default function SummaryCard({
  title,
  value,
  icon: Icon,
  trend,
  description,
  glowColor = 'blue'
}) {
  const glowClasses = {
    blue: 'group-hover:shadow-[0_0_20px_0_rgba(59,130,246,0.15)] group-hover:border-blue-500/30',
    cyan: 'group-hover:shadow-[0_0_20px_0_rgba(6,182,212,0.15)] group-hover:border-cyan-500/30',
    purple: 'group-hover:shadow-[0_0_20px_0_rgba(168,85,247,0.15)] group-hover:border-purple-500/30',
    emerald: 'group-hover:shadow-[0_0_20px_0_rgba(16,185,129,0.15)] group-hover:border-emerald-500/30'
  };

  const iconBgClasses = {
    blue: 'bg-blue-500/10 text-blue-400 group-hover:bg-blue-500/20',
    cyan: 'bg-cyan-500/10 text-cyan-400 group-hover:bg-cyan-500/20',
    purple: 'bg-purple-500/10 text-purple-400 group-hover:bg-purple-500/20',
    emerald: 'bg-emerald-500/10 text-emerald-400 group-hover:bg-emerald-500/20'
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -3 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className={`group relative overflow-hidden rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur-lg transition-all duration-300 shadow-sm ${glowClasses[glowColor]}`}
    >
      {/* Background radial soft light */}
      <div className="absolute -top-12 -right-12 h-24 w-24 rounded-full bg-cyan-500/5 blur-2xl group-hover:bg-cyan-500/10 transition-colors duration-300"></div>

      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-slate-400 tracking-wider font-display uppercase">{title}</span>
        <div className={`rounded-xl p-2.5 transition-colors duration-300 ${iconBgClasses[glowColor]}`}>
          <Icon className="h-5 w-5" />
        </div>
      </div>

      <div className="mt-4 flex items-baseline space-x-2.5">
        <span className="text-3xl font-bold text-white tracking-tight font-display">{value}</span>
        {trend && (
          <span
            className={`inline-flex items-center text-2xs font-bold px-2 py-0.5 rounded-full ${
              trend.isPositive
                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
            }`}
          >
            {trend.value}
          </span>
        )}
      </div>

      {description && (
        <p className="mt-2 text-xs text-slate-500 font-medium">
          {description}
        </p>
      )}
    </motion.div>
  );
}