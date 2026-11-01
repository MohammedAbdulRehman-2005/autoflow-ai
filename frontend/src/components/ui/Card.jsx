import React from 'react';

/**
 * GlassCard - high performance glassmorphic container
 */
export function GlassCard({
  children,
  className = '',
  hoverEffect = false,
  padding = 'p-5',
  onClick,
  ...props
}) {
  return (
    <div
      onClick={onClick}
      className={`rounded-2xl border border-white/10 bg-slate-900/60 backdrop-blur-xl shadow-xl transition-all duration-200 ${
        hoverEffect ? 'hover:border-white/20 hover:bg-slate-900/80 hover:shadow-cyan-500/5 cursor-pointer' : ''
      } ${padding} ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}

/**
 * MetricCard - high-density observability metric card
 */
export function MetricCard({
  title,
  value,
  subtitle = null,
  trend = null, // e.g. { value: '+12%', isPositive: true }
  icon: Icon = null,
  accentColor = 'cyan', // 'cyan', 'blue', 'emerald', 'purple', 'rose', 'amber'
  className = '',
  onClick
}) {
  const accentBorders = {
    cyan: 'from-cyan-500/20 to-transparent text-cyan-400 bg-cyan-500/10',
    blue: 'from-blue-500/20 to-transparent text-blue-400 bg-blue-500/10',
    emerald: 'from-emerald-500/20 to-transparent text-emerald-400 bg-emerald-500/10',
    purple: 'from-purple-500/20 to-transparent text-purple-400 bg-purple-500/10',
    rose: 'from-rose-500/20 to-transparent text-rose-400 bg-rose-500/10',
    amber: 'from-amber-500/20 to-transparent text-amber-400 bg-amber-500/10'
  };

  const accentStyle = accentBorders[accentColor] || accentBorders.cyan;

  return (
    <div
      onClick={onClick}
      className={`relative overflow-hidden rounded-2xl border border-white/10 bg-slate-900/60 p-5 backdrop-blur-xl shadow-xl ${
        onClick ? 'cursor-pointer hover:border-white/20 transition-all' : ''
      } ${className}`}
    >
      {/* Top subtle gradient highlight line */}
      <div className={`absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r ${accentStyle}`} />

      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <p className="text-xs font-medium uppercase tracking-wider text-slate-400 font-mono">
            {title}
          </p>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl lg:text-3xl font-bold tracking-tight text-white font-display">
              {value}
            </span>
            {trend && (
              <span
                className={`text-xs font-mono font-medium ${
                  trend.isPositive ? 'text-emerald-400' : 'text-rose-400'
                }`}
              >
                {trend.value}
              </span>
            )}
          </div>
        </div>

        {Icon && (
          <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-white/10 ${accentStyle}`}>
            <Icon className="h-5 w-5" />
          </div>
        )}
      </div>

      {subtitle && (
        <p className="mt-3 text-xs text-slate-400 truncate">
          {subtitle}
        </p>
      )}
    </div>
  );
}

/**
 * PanelHeader - uniform section and screen header
 */
export function PanelHeader({
  title,
  description = null,
  badge = null,
  actions = null,
  className = ''
}) {
  return (
    <div className={`flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-white/10 ${className}`}>
      <div className="space-y-1">
        <div className="flex items-center gap-3">
          <h1 className="text-xl lg:text-2xl font-bold text-white tracking-tight font-display">
            {title}
          </h1>
          {badge}
        </div>
        {description && (
          <p className="text-sm text-slate-400 max-w-2xl leading-relaxed">
            {description}
          </p>
        )}
      </div>

      {actions && (
        <div className="flex items-center gap-2.5 shrink-0 flex-wrap">
          {actions}
        </div>
      )}
    </div>
  );
}
