import React, { useState } from 'react';
import { Copy, Check, ChevronDown, ChevronRight, Terminal } from 'lucide-react';

/**
 * High-performance JSON/Code Payload Viewer
 */
export function CodePayloadViewer({
  data,
  title = null,
  maxHeight = 'max-h-96',
  allowCopy = true,
  defaultExpanded = true,
  className = ''
}) {
  const [copied, setCopied] = useState(false);
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  const formatted = typeof data === 'string' 
    ? data 
    : JSON.stringify(data, null, 2);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(formatted);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (_) {}
  };

  return (
    <div className={`rounded-xl border border-white/10 bg-slate-950/80 overflow-hidden text-xs font-mono shadow-inner ${className}`}>
      {/* Viewer Header */}
      <div className="flex items-center justify-between px-3.5 py-2 border-b border-white/10 bg-slate-900/60">
        <div className="flex items-center gap-2 text-slate-300">
          <Terminal className="h-3.5 w-3.5 text-cyan-400" />
          <span className="font-semibold">{title || 'Payload Data'}</span>
          <span className="text-[10px] text-slate-500 font-sans">
            ({formatted?.length || 0} bytes)
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          {allowCopy && (
            <button
              onClick={handleCopy}
              className="inline-flex items-center gap-1 px-2 py-1 rounded bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white transition-colors cursor-pointer text-[11px]"
              title="Copy to clipboard"
            >
              {copied ? (
                <>
                  <Check className="h-3 w-3 text-emerald-400" />
                  <span className="text-emerald-400">Copied</span>
                </>
              ) : (
                <>
                  <Copy className="h-3 w-3" />
                  <span>Copy</span>
                </>
              )}
            </button>
          )}

          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1 rounded text-slate-400 hover:text-white hover:bg-white/5 transition-colors cursor-pointer"
          >
            {isExpanded ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
          </button>
        </div>
      </div>

      {/* Code body */}
      {isExpanded && (
        <div className={`p-3 overflow-auto ${maxHeight} text-slate-300 select-text leading-relaxed font-mono`}>
          <pre className="whitespace-pre-wrap break-words">{formatted}</pre>
        </div>
      )}
    </div>
  );
}

/**
 * DiffViewer - Displays side-by-side or block diff between original and patched payload
 */
export function DiffViewer({
  before,
  after,
  titleBefore = 'Current Failing State',
  titleAfter = 'Proposed Patched State'
}) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs font-mono text-rose-400 px-1">
          <span className="font-semibold flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-rose-500 inline-block" />
            {titleBefore}
          </span>
        </div>
        <CodePayloadViewer
          data={before}
          allowCopy={true}
          className="border-rose-500/20 bg-rose-950/10"
        />
      </div>

      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs font-mono text-emerald-400 px-1">
          <span className="font-semibold flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-emerald-500 inline-block" />
            {titleAfter}
          </span>
        </div>
        <CodePayloadViewer
          data={after}
          allowCopy={true}
          className="border-emerald-500/20 bg-emerald-950/10"
        />
      </div>
    </div>
  );
}
