import React from 'react';
import { 
  CheckCircle2, 
  XCircle, 
  Clock, 
  AlertTriangle, 
  ShieldCheck, 
  ShieldAlert, 
  Shield, 
  RotateCw,
  PauseCircle,
  HelpCircle
} from 'lucide-react';

/**
 * StatusBadge for workflow & run statuses
 */
export function StatusBadge({ status, size = 'sm', className = '' }) {
  const norm = (status || '').toLowerCase().replace(/_/g, ' ');

  const configs = {
    'success': {
      bg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
      icon: CheckCircle2,
      label: 'Success'
    },
    'succeeded': {
      bg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
      icon: CheckCircle2,
      label: 'Succeeded'
    },
    'running': {
      bg: 'bg-blue-500/10 text-blue-400 border-blue-500/20 animate-pulse',
      icon: RotateCw,
      spin: true,
      label: 'Running'
    },
    'failed': {
      bg: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
      icon: XCircle,
      label: 'Failed'
    },
    'pending': {
      bg: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
      icon: Clock,
      label: 'Pending'
    },
    'pending triage': {
      bg: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
      icon: AlertTriangle,
      label: 'Pending Triage'
    },
    'awaiting approval': {
      bg: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
      icon: PauseCircle,
      label: 'Awaiting Approval'
    },
    'paused': {
      bg: 'bg-slate-500/10 text-slate-400 border-slate-500/20',
      icon: PauseCircle,
      label: 'Paused'
    },
    'active': {
      bg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
      icon: CheckCircle2,
      label: 'Active'
    },
    'resolved': {
      bg: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
      icon: CheckCircle2,
      label: 'Resolved'
    },
    'approved': {
      bg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
      icon: CheckCircle2,
      label: 'Approved'
    },
    'rejected': {
      bg: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
      icon: XCircle,
      label: 'Rejected'
    },
    'dismissed': {
      bg: 'bg-slate-500/10 text-slate-400 border-slate-500/20',
      icon: HelpCircle,
      label: 'Dismissed'
    }
  };

  const current = configs[norm] || {
    bg: 'bg-slate-500/10 text-slate-400 border-slate-500/20',
    icon: HelpCircle,
    label: status || 'Unknown'
  };

  const Icon = current.icon;
  const isSm = size === 'sm';

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-mono font-medium rounded-full border ${current.bg} ${
        isSm ? 'px-2.5 py-0.5 text-xs' : 'px-3 py-1 text-sm'
      } ${className}`}
    >
      <Icon className={`${isSm ? 'h-3 w-3' : 'h-3.5 w-3.5'} ${current.spin ? 'animate-spin' : ''}`} />
      <span>{current.label}</span>
    </span>
  );
}

/**
 * PriorityBadge for incident & approval triage
 */
export function PriorityBadge({ priority, className = '' }) {
  const norm = (priority || '').toLowerCase();

  const configs = {
    critical: 'bg-red-500/15 text-red-400 border-red-500/30',
    high: 'bg-orange-500/15 text-orange-400 border-orange-500/30',
    medium: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
    low: 'bg-slate-500/15 text-slate-400 border-slate-500/30'
  };

  const styling = configs[norm] || configs.medium;

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 text-[11px] font-mono uppercase tracking-wider font-semibold rounded-md border ${styling} ${className}`}
    >
      {priority}
    </span>
  );
}

/**
 * PolicyBadge for governance rules evaluation
 */
export function PolicyBadge({ status, className = '' }) {
  const norm = (status || '').toUpperCase();

  const isCompliant = norm === 'COMPLIANT_AUTO_APPROVABLE' || norm === 'COMPLIANT';
  const isRequiresSignoff = norm === 'REQUIRES_HUMAN_SIGN_OFF' || norm === 'REQUIRES_SIGN_OFF';

  if (isCompliant) {
    return (
      <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 text-xs font-mono rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 ${className}`}>
        <ShieldCheck className="h-3.5 w-3.5" />
        <span>Pre-Approved / Auto-Remediable</span>
      </span>
    );
  }

  if (isRequiresSignoff) {
    return (
      <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 text-xs font-mono rounded-md bg-purple-500/10 text-purple-400 border border-purple-500/20 ${className}`}>
        <Shield className="h-3.5 w-3.5" />
        <span>Requires Human Sign-Off</span>
      </span>
    );
  }

  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 text-xs font-mono rounded-md bg-rose-500/10 text-rose-400 border border-rose-500/20 ${className}`}>
      <ShieldAlert className="h-3.5 w-3.5" />
      <span>Policy Violation</span>
    </span>
  );
}
