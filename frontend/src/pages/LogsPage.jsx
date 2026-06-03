import React, { useState, useEffect } from 'react';
import {
  Search,
  ListTodo,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RotateCw,
  Terminal,
  Activity,
  SlidersHorizontal,
  ChevronRight,
  ChevronDown
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { getLogs, saveLogs } from '../mockData';

export default function LogsPage() {
  const [logs, setLogs] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('All');
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [expandedLogId, setExpandedLogId] = useState(null);

  const loadLogs = () => {
    setLogs(getLogs());
  };

  useEffect(() => {
    loadLogs();
  }, []);

  const handleRefresh = () => {
    setIsRefreshing(true);
    setTimeout(() => {
      loadLogs();
      setIsRefreshing(false);
    }, 600);
  };

  const handleClearLogs = () => {
    if (confirm('Are you sure you want to flush all system logs? This action is irreversible.')) {
      saveLogs([]);
      setLogs([]);
    }
  };

  const filteredLogs = logs.filter((log) => {
    const matchesSearch = log.workflowName.toLowerCase().includes(searchTerm.toLowerCase()) || 
                          log.triggerEvent.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = selectedStatus === 'All' || log.status === selectedStatus.toLowerCase();
    return matchesSearch && matchesStatus;
  });

  const toggleExpandLog = (id) => {
    setExpandedLogId(expandedLogId === id ? null : id);
  };

  // Helper status elements
  const statusStyles = {
    success: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/15',
    running: 'bg-blue-500/10 text-blue-400 border border-blue-500/15 animate-pulse',
    failed: 'bg-rose-500/10 text-rose-400 border border-rose-500/15'
  };

  const statusIcons = {
    success: <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 shrink-0" />,
    running: <Activity className="h-3.5 w-3.5 text-blue-400 shrink-0 animate-spin" />,
    failed: <XCircle className="h-3.5 w-3.5 text-rose-400 shrink-0" />
  };

  return (
    <div className="space-y-8 select-none text-left">
      
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white font-display flex items-center gap-2">
            <ListTodo className="h-8 w-8 text-cyan-400" />
            <span>Execution Monitoring</span>
          </h1>
          <p className="text-sm text-slate-400 mt-1 font-sans">
            Inspect transaction histories, system latency logs and diagnostics.
          </p>
        </div>

        {/* Global Toolbar buttons */}
        <div className="flex items-center space-x-2.5 self-start sm:self-auto">
          <button
            onClick={handleRefresh}
            className="flex items-center space-x-1.5 px-3.5 py-2 border border-white/10 bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white rounded-xl text-xs font-semibold cursor-pointer shadow-sm transition-all"
          >
            <RotateCw className={`h-4.5 w-4.5 ${isRefreshing ? 'animate-spin' : ''}`} />
            <span>Force Sync</span>
          </button>
          
          <button
            onClick={handleClearLogs}
            className="flex items-center space-x-1.5 px-3.5 py-2 border border-rose-500/30 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 rounded-xl text-xs font-semibold cursor-pointer transition-all shadow-sm"
          >
            <span>Flush Logs</span>
          </button>
        </div>
      </div>

      {/* Grid Filters Control Room */}
      <div className="flex flex-col md:flex-row gap-4 justify-between items-stretch md:items-center pb-2">
        
        {/* Status filters */}
        <div className="flex items-center space-x-1.5">
          {['All', 'Success', 'Running', 'Failed'].map((status) => (
            <button
               key={status}
               onClick={() => setSelectedStatus(status)}
               className={`px-3.5 py-1.5 rounded-xl text-xs font-bold cursor-pointer transition-all shadow-sm ${
                selectedStatus === status
                   ? 'bg-gradient-to-r from-blue-600 to-cyan-500 text-white'
                   : 'bg-white/5 border border-white/10 text-slate-400 hover:text-white hover:border-white/20'
               }`}
            >
              {status.toUpperCase()}
            </button>
          ))}
        </div>

        {/* Search filter input */}
        <div className="relative w-full md:w-80 shrink-0">
          <Search className="absolute top-1/2 left-3.5 h-4 w-4 -translate-y-1/2 text-slate-555" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search triggers or workflows..."
            className="w-full rounded-xl border border-white/10 bg-white/5 py-2.5 pr-4 pl-10 text-xs text-white placeholder-slate-500 outline-none hover:border-white/20 focus:border-cyan-500/50"
          />
        </div>

      </div>

      {/* Main logs display table card */}
      <div className="border border-white/10 rounded-3xl bg-white/5 p-6 backdrop-blur-lg shadow-md">
        {filteredLogs.length === 0 ? (
          <div className="text-center py-20 text-slate-500 flex flex-col items-center justify-center space-y-3">
            <SlidersHorizontal className="h-8 w-8 text-slate-600 animate-pulse" />
            <span className="text-sm">No transaction traces match active search filters.</span>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-white/10 text-slate-500 pb-2 font-display uppercase tracking-wider text-[10px]">
                  <th className="pb-3 pt-1 w-8"></th>
                  <th className="pb-3 pt-1 font-semibold">WORKFLOW</th>
                  <th className="pb-3 pt-1 font-semibold">STATUS</th>
                  <th className="pb-3 pt-1 font-semibold">DURATION</th>
                  <th className="pb-3 pt-1 font-semibold text-right">TIMESTAMP</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/10 text-slate-350">
                {filteredLogs.map((log) => {
                  const isExpanded = expandedLogId === log.id;
                  
                  return (
                    <React.Fragment key={log.id}>
                      {/* Table Row */}
                      <tr
                        className={`hover:bg-white/5 transition-colors cursor-pointer ${isExpanded ? 'bg-white/5' : ''}`}
                        onClick={() => toggleExpandLog(log.id)}
                      >
                        <td className="py-4 text-center">
                          {isExpanded ? <ChevronDown className="h-4 w-4 text-slate-400" /> : <ChevronRight className="h-4 w-4 text-slate-500" />}
                        </td>
                        <td className="py-4 pr-3">
                          <div className="flex flex-col">
                            <span className="font-bold text-slate-200 text-sm group-hover:text-white transition-colors">{log.workflowName}</span>
                            <span className="text-2xs text-slate-500 mt-0.5 font-medium">{log.triggerEvent}</span>
                          </div>
                        </td>
                        <td className="py-4">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-2xs font-semibold ${statusStyles[log.status]}`}>
                            <span className="mr-1.5 shrink-0">{statusIcons[log.status]}</span>
                            <span>{log.status.toUpperCase()}</span>
                          </span>
                        </td>
                        <td className="py-4 font-mono text-xs text-slate-400">{log.duration}</td>
                        <td className="py-4 font-mono text-2xs text-slate-500 text-right">
                          {new Date(log.timestamp).toLocaleString([], {
                            year: 'numeric',
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                            second: '2-digit'
                          })}
                        </td>
                      </tr>

                      {/* Expandable diagnostics sub-board */}
                      {isExpanded && (
                        <tr className="bg-slate-950/20">
                          <td colSpan={5} className="p-4 border-b border-white/10 text-left">
                            <div className="rounded-xl border border-white/10 bg-slate-900/80 p-4 backdrop-blur-md font-mono text-[11px] text-slate-350 space-y-3.5 relative overflow-hidden">
                              {/* Background soft red/emerald lamp depends on status */}
                              <div className={`absolute top-0 right-0 h-16 w-16 opacity-5 blur-xl rounded-full ${log.status === 'success' ? 'bg-emerald-500' : 'bg-rose-500'}`}></div>
                              
                              <div className="flex justify-between items-center text-slate-500 border-b border-white/10 pb-2">
                                <span className="font-bold text-3xs text-cyan-400">TRANSACTION METADATA DETAILS</span>
                                <span>LOG ID: {log.id}</span>
                              </div>

                              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="space-y-1.5">
                                  <p><span className="text-slate-500">Workflow Target:</span> {log.workflowName}</p>
                                  <p><span className="text-slate-500">Trigger Ingest:</span> {log.triggerEvent}</p>
                                  <p><span className="text-slate-500">Active Duration:</span> {log.duration}</p>
                                </div>
                                <div className="space-y-1.5">
                                  <p><span className="text-slate-500">Integrity Check:</span> SHA-256 Verified</p>
                                  <p><span className="text-slate-500">Security Context:</span> TLS_AES_256_GCM</p>
                                  <p><span className="text-slate-500">Response Code:</span> {log.status === 'success' ? '200 OK SUCCESS' : '500 SERVICE EXCEPTION'}</p>
                                </div>
                              </div>

                              {/* Error diagnostics banner if failure */}
                              {log.status === 'failed' && (
                                <div className="p-3.5 rounded-lg bg-rose-500/10 border border-rose-500/15 text-rose-400 flex items-start space-x-2">
                                  <AlertTriangle className="h-4.5 w-4.5 shrink-0" />
                                  <div className="flex flex-col leading-relaxed">
                                    <span className="font-bold">SYSTEM ERROR REASON:</span>
                                    <span className="mt-1">{log.errorMessage || 'Unknown system trigger exception.'}</span>
                                  </div>
                                </div>
                              )}

                              {/* Action tracing flows */}
                              <div className="pt-2 text-slate-500 flex justify-between items-center">
                                <span>Tracing hops: Ingress Webhook ➔ LLM Classification ➔ API Outpost Endpoint</span>
                                <span className="text-[10px] text-cyan-400 font-bold border border-cyan-500/30 bg-cyan-500/5 px-2 py-0.5 rounded-full shrink-0">
                                  SECURED WITH AUTOFLOW AI
                                </span>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

    </div>
  );
}
