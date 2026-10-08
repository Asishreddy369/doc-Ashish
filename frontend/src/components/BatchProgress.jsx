import React from 'react';
import { Loader2, CheckCircle2, XCircle, Clock, Trash2, RefreshCw, Activity } from 'lucide-react';

// BUG-F13 FIX: Auto-format file size to B / KB / MB / GB.
const formatFileSize = (bytes) => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
};

export default function BatchProgress({ queue, stats: _stats, onCancelAll: _onCancelAll, onClearCompleted, onRetryFailed }) {
  if (!queue || queue.length === 0) return null;

  const totalFiles = queue.length;
  const completedCount = queue.filter(item => item.status === 'COMPLETED').length;
  const failedCount = queue.filter(item => item.status === 'FAILED').length;
  const uploadingCount = queue.filter(item => item.status === 'UPLOADING').length;
  const extractingCount = queue.filter(item => item.status === 'EXTRACTING').length;

  // BUG-F09 FIX: Count EXTRACTING items as 90% done so the progress bar doesn't
  // stall at 0% while all files are in the extraction phase.
  const effectiveCompleted = completedCount + (extractingCount * 0.9);
  const overallProgress = Math.round((effectiveCompleted / totalFiles) * 100) || 0;

  return (
    <div className="w-full mt-6 rounded-2xl bg-white border border-slate-200 p-6 shadow-md">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-slate-200">
        <div>
          <div className="flex items-center space-x-2">
            <Activity className="w-5 h-5 text-red-600 animate-pulse" />
            <h3 className="text-lg font-extrabold text-slate-900">Batch Upload Engine</h3>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-50 text-rose-700 border border-rose-200">
              {uploadingCount > 0
                ? `${uploadingCount} Active Stream(s)`
                : extractingCount > 0
                  ? `${extractingCount} Extracting`
                  : 'Idle'}
            </span>
          </div>
          <p className="text-xs text-slate-600 mt-1 font-medium">
            {completedCount} of {totalFiles} extracted ({overallProgress}%)
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex items-center space-x-2">
          {failedCount > 0 && (
            <button
              onClick={onRetryFailed}
              className="px-3 py-1.5 rounded-lg bg-amber-50 hover:bg-amber-100 text-amber-800 text-xs font-bold border border-amber-300 flex items-center space-x-1.5 transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5 text-amber-600" />
              <span>Retry ({failedCount})</span>
            </button>
          )}

          {completedCount > 0 && (
            <button
              onClick={onClearCompleted}
              className="px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold border border-slate-300 flex items-center space-x-1.5 transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Clear Done</span>
            </button>
          )}
        </div>
      </div>

      {/* Overall Progress Bar */}
      <div className="mt-4">
        <div className="flex justify-between text-xs font-bold text-slate-700 mb-1.5">
          <span>Batch Progress</span>
          <span>{overallProgress}%</span>
        </div>
        <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden p-0.5 border border-slate-200">
          <div
            className="h-full bg-gradient-to-r from-red-600 to-red-500 rounded-full transition-all duration-300 shadow-sm"
            style={{ width: `${overallProgress}%` }}
          />
        </div>
      </div>

      {/* Summary Status Badges */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mt-4">
        <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-center">
          <p className="text-[10px] text-slate-500 uppercase font-bold">Total Queued</p>
          <p className="text-base font-extrabold text-slate-900">{totalFiles}</p>
        </div>
        <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-center">
          <p className="text-[10px] text-emerald-700 uppercase font-bold">Completed</p>
          <p className="text-base font-extrabold text-emerald-700">{completedCount}</p>
        </div>
        <div className="p-3 rounded-xl bg-pink-50 border border-pink-200 text-center">
          <p className="text-[10px] text-pink-700 uppercase font-bold">Uploading</p>
          <p className="text-base font-extrabold text-pink-700">{uploadingCount}</p>
        </div>
        <div className="p-3 rounded-xl bg-blue-50 border border-blue-200 text-center">
          <p className="text-[10px] text-blue-700 uppercase font-bold">Extracting</p>
          <p className="text-base font-extrabold text-blue-700">{extractingCount}</p>
        </div>
        <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-center">
          <p className="text-[10px] text-red-700 uppercase font-bold">Failed</p>
          <p className="text-base font-extrabold text-red-700">{failedCount}</p>
        </div>
      </div>

      {/* File List Item Cards */}
      <div className="mt-5 max-h-72 overflow-y-auto space-y-2.5 pr-1">
        {queue.map((item) => {
          return (
            <div
              key={item.id}
              className="p-3 rounded-xl bg-slate-50 border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs hover:border-slate-300 transition-colors"
            >
              <div className="flex items-center space-x-3 min-w-0 flex-1">
                {item.status === 'COMPLETED' && <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />}
                {item.status === 'UPLOADING' && <Loader2 className="w-4 h-4 text-red-600 animate-spin shrink-0" />}
                {item.status === 'EXTRACTING' && <Loader2 className="w-4 h-4 text-blue-600 animate-spin shrink-0" />}
                {item.status === 'PENDING' && <Clock className="w-4 h-4 text-slate-400 shrink-0" />}
                {item.status === 'FAILED' && <XCircle className="w-4 h-4 text-red-600 shrink-0" />}

                <div className="min-w-0 flex-1">
                  <p className="font-bold text-slate-900 truncate">{item.file.name}</p>
                  <p className="text-[10px] text-slate-500 font-medium">
                    {formatFileSize(item.file.size)}
                    {item.docId && (
                      <span className="ml-2 font-mono text-red-700 bg-red-50 px-1.5 py-0.5 rounded text-[9px] border border-red-200 font-bold">
                        UUID: {item.docId}
                      </span>
                    )}
                  </p>
                </div>
              </div>

              {/* Progress / Status Tag */}
              <div className="flex items-center space-x-3 sm:w-48 justify-end shrink-0">
                {item.status === 'UPLOADING' && (
                  <div className="w-full">
                    <div className="flex justify-between text-[10px] text-red-600 font-bold mb-1">
                      <span>Uploading</span>
                      <span>{item.progress || 0}%</span>
                    </div>
                    <div className="w-full bg-slate-200 rounded-full h-1.5 overflow-hidden">
                      <div
                        className="bg-red-600 h-full transition-all duration-200"
                        style={{ width: `${item.progress || 0}%` }}
                      />
                    </div>
                  </div>
                )}

                {item.status === 'COMPLETED' && (
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
                    Extracted
                  </span>
                )}

                {item.status === 'EXTRACTING' && (
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800 border border-blue-300">
                    Extracting
                  </span>
                )}

                {item.status === 'PENDING' && (
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-200 text-slate-700 border border-slate-300">
                    Queued
                  </span>
                )}

                {item.status === 'FAILED' && (
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-red-100 text-red-800 border border-red-300 truncate max-w-[120px]">
                    {item.error || 'Failed'}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
