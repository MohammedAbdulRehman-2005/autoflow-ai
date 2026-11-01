import React from 'react';

export function LoadingSkeleton({ rows = 4, className = '' }) {
  return (
    <div className={`space-y-3 animate-pulse ${className}`}>
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="h-16 rounded-xl border border-white/5 bg-slate-900/40 p-4 flex items-center justify-between"
        >
          <div className="flex items-center gap-3 w-1/3">
            <div className="h-8 w-8 rounded-lg bg-white/10" />
            <div className="space-y-1.5 flex-1">
              <div className="h-3 w-3/4 rounded bg-white/10" />
              <div className="h-2 w-1/2 rounded bg-white/5" />
            </div>
          </div>
          <div className="h-5 w-20 rounded-full bg-white/10" />
          <div className="h-3 w-28 rounded bg-white/5 hidden md:block" />
          <div className="h-7 w-16 rounded-lg bg-white/10" />
        </div>
      ))}
    </div>
  );
}

export function MetricSkeleton() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 animate-pulse">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="h-28 rounded-2xl border border-white/10 bg-slate-900/40 p-5 space-y-3">
          <div className="h-3 w-24 rounded bg-white/10" />
          <div className="h-7 w-32 rounded bg-white/15" />
          <div className="h-2.5 w-40 rounded bg-white/5" />
        </div>
      ))}
    </div>
  );
}
