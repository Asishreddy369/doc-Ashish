import React from 'react';
import { CheckCircle2, FolderTree, RotateCcw, Route, Sparkles } from 'lucide-react';

export default function FolderPlanReview({ plan, loading, error, onStart, onCancel }) {
  if (loading) {
    return (
      <div className="rounded-xl bg-white border border-slate-200 p-5 shadow-sm flex items-center gap-3">
        <Sparkles className="w-5 h-5 text-red-600 animate-pulse" />
        <div>
          <h3 className="text-sm font-extrabold text-slate-900">Building folder plan</h3>
          <p className="text-xs text-slate-500 font-medium">Analyzing names, paths, dates, and category hints.</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl bg-red-50 border border-red-200 p-5 text-sm text-red-800 font-semibold">
        {error}
      </div>
    );
  }

  if (!plan) return null;

  const routes = plan.routes || [];
  const treeLines = plan.tree_lines || [];
  const summary = plan.summary || {};
  const categoryCounts = Object.entries(summary.category_counts || {});
  const isUserDefined = plan.mode === 'user_defined';

  return (
    <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
      <div className="p-5 border-b border-slate-200 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-lg bg-red-50 text-red-600 border border-red-100 flex items-center justify-center">
            <FolderTree className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-extrabold text-slate-900">Review Folder Structure</h3>
            <p className="text-xs text-slate-500 font-medium">
              {summary.document_count || routes.length} document(s) planned using {isUserDefined ? 'user-defined folders' : plan.structure_levels?.join(' / ')}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="px-3 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold border border-slate-300 flex items-center gap-1.5"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Change</span>
          </button>
          <button
            type="button"
            onClick={onStart}
            className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white text-xs font-bold shadow-sm flex items-center gap-1.5"
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Start Organization</span>
          </button>
        </div>
      </div>

      <div className="grid gap-0 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="p-5 border-b lg:border-b-0 lg:border-r border-slate-200">
          <div className="flex items-center gap-2 mb-3">
            <FolderTree className="w-4 h-4 text-red-600" />
            <h4 className="text-xs font-extrabold uppercase tracking-wider text-slate-600">Suggested Tree</h4>
          </div>
          <div className="max-h-64 overflow-y-auto rounded-lg bg-slate-50 border border-slate-200 p-3 font-mono text-xs text-slate-800">
            {treeLines.slice(0, 80).map((line, index) => (
              <div key={`${line.name}-${index}`} style={{ paddingLeft: `${line.depth * 18}px` }} className="py-0.5">
                {line.depth > 0 ? '- ' : ''}{line.name}
              </div>
            ))}
            {treeLines.length > 80 && (
              <div className="pt-2 text-slate-500">...and {treeLines.length - 80} more folders</div>
            )}
          </div>
        </div>

        <div className="p-5 space-y-4">
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Sparkles className="w-4 h-4 text-red-600" />
              <h4 className="text-xs font-extrabold uppercase tracking-wider text-slate-600">{isUserDefined ? 'Folder Counts' : 'Category Counts'}</h4>
            </div>
            <div className="flex flex-wrap gap-2">
              {categoryCounts.slice(0, 10).map(([category, count]) => (
                <span key={category} className="px-2.5 py-1 rounded-md bg-slate-100 border border-slate-200 text-[11px] font-bold text-slate-700">
                  {category}: {count}
                </span>
              ))}
              {isUserDefined && (
                <span className="px-2.5 py-1 rounded-md bg-amber-50 border border-amber-200 text-[11px] font-bold text-amber-800">
                  Unmatched to fallback: {summary.unmatched_count || 0}
                </span>
              )}
            </div>
          </div>

          <div>
            <div className="flex items-center gap-2 mb-3">
              <Route className="w-4 h-4 text-red-600" />
              <h4 className="text-xs font-extrabold uppercase tracking-wider text-slate-600">Sample Routes</h4>
            </div>
            <div className="space-y-2 max-h-40 overflow-y-auto">
              {routes.slice(0, 6).map((route, index) => (
                <div key={`${route.file}-${index}`} className="rounded-lg bg-slate-50 border border-slate-200 p-2">
                  <p className="text-xs font-bold text-slate-900 truncate">{route.file}</p>
                  <p className="text-[10px] text-red-700 font-bold truncate">{route.target_folder}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
