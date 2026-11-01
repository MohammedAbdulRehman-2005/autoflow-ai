import React from 'react';
import { Button } from './Button';
import { Sparkles, Inbox } from 'lucide-react';

/**
 * Standardized EmptyState component
 */
export function EmptyState({
  title = 'No records found',
  description = 'There are no active items matching your current filters or selection.',
  icon: Icon = Inbox,
  actionLabel = null,
  onAction = null,
  actionIcon = null,
  className = ''
}) {
  return (
    <div className={`flex flex-col items-center justify-center text-center p-8 lg:p-12 rounded-2xl border border-dashed border-white/10 bg-slate-900/30 backdrop-blur-md ${className}`}>
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white/5 border border-white/10 text-slate-400 mb-4 shadow-inner">
        <Icon className="h-6 w-6" />
      </div>

      <h3 className="text-base font-semibold text-slate-200 font-display">
        {title}
      </h3>

      <p className="mt-1.5 text-xs text-slate-400 max-w-sm leading-relaxed">
        {description}
      </p>

      {actionLabel && onAction && (
        <div className="mt-5">
          <Button
            size="sm"
            variant="secondary"
            onClick={onAction}
            icon={actionIcon}
          >
            {actionLabel}
          </Button>
        </div>
      )}
    </div>
  );
}
