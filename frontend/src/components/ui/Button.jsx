import React from 'react';
import { RotateCw } from 'lucide-react';

/**
 * Universal Button component adhering to AutoFlow AI design system
 */
export function Button({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  disabled = false,
  icon: Icon = null,
  iconRight: IconRight = null,
  shortcut = null,
  className = '',
  onClick,
  type = 'button',
  title = '',
  ...props
}) {
  const baseStyles = 'relative inline-flex items-center justify-center font-medium transition-all duration-150 select-none cursor-pointer focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-slate-950 disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none rounded-xl';

  const variants = {
    primary: 'bg-cyan-500 hover:bg-cyan-400 active:bg-cyan-600 text-slate-950 font-semibold shadow-lg shadow-cyan-500/20 hover:shadow-cyan-500/30 border border-cyan-400/30 focus:ring-cyan-400',
    secondary: 'bg-slate-800/80 hover:bg-slate-700/80 active:bg-slate-800 text-slate-200 hover:text-white border border-slate-700/60 hover:border-slate-600/80 shadow-sm focus:ring-slate-400',
    danger: 'bg-rose-500/15 hover:bg-rose-500/25 active:bg-rose-500/30 text-rose-400 hover:text-rose-300 border border-rose-500/30 hover:border-rose-500/50 focus:ring-rose-400',
    success: 'bg-emerald-500/15 hover:bg-emerald-500/25 active:bg-emerald-500/30 text-emerald-400 hover:text-emerald-300 border border-emerald-500/30 hover:border-emerald-500/50 focus:ring-emerald-400',
    outline: 'bg-transparent hover:bg-white/5 active:bg-white/10 text-slate-300 hover:text-white border border-white/15 hover:border-white/25 focus:ring-white/20',
    ghost: 'bg-transparent hover:bg-white/5 active:bg-white/10 text-slate-400 hover:text-slate-200 border border-transparent focus:ring-white/10',
    gradient: 'bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 text-white font-semibold shadow-lg shadow-blue-500/20 border border-blue-400/20 focus:ring-cyan-400'
  };

  const sizes = {
    xs: 'px-2.5 py-1 text-xs gap-1.5',
    sm: 'px-3 py-1.5 text-xs gap-2',
    md: 'px-4 py-2 text-sm gap-2',
    lg: 'px-5 py-2.5 text-base gap-2.5'
  };

  return (
    <button
      type={type}
      disabled={disabled || isLoading}
      onClick={onClick}
      title={title}
      className={`${baseStyles} ${variants[variant] || variants.primary} ${sizes[size] || sizes.md} ${className}`}
      {...props}
    >
      {isLoading ? (
        <RotateCw className="h-4 w-4 animate-spin shrink-0" />
      ) : Icon ? (
        <Icon className="h-4 w-4 shrink-0" />
      ) : null}

      <span className="truncate">{children}</span>

      {IconRight && !isLoading && (
        <IconRight className="h-4 w-4 shrink-0 ml-0.5" />
      )}

      {shortcut && (
        <kbd className="hidden sm:inline-block ml-1.5 px-1.5 py-0.5 text-[10px] font-mono font-medium rounded bg-black/30 border border-white/10 text-slate-400">
          {shortcut}
        </kbd>
      )}
    </button>
  );
}
