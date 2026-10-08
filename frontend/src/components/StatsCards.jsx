import React from 'react';
import { HardDrive, Files, Shield, Cpu } from 'lucide-react';

// BUG-F02 FIX: Replaced non-existent CSS classes 'spider-glass-card' / 'spider-glass-card-hover'
// with the correct 'glass-card' / 'glass-card-hover' classes defined in index.css.
export default function StatsCards({ stats }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      
      {/* Total Uploads Card */}
      <div className="glass-card glass-card-hover p-5 rounded-2xl relative overflow-hidden bg-white border border-slate-200">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">Total Documents</p>
            <h4 className="text-2xl font-extrabold text-slate-900 mt-1">
              {stats?.total_documents ?? 0}
            </h4>
          </div>
          <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-red-600">
            <Files className="w-6 h-6" />
          </div>
        </div>
        <p className="text-[11px] text-slate-600 mt-3 font-medium flex items-center">
          <span className="text-emerald-600 font-bold mr-1">100% Unique</span> UUID tracked
        </p>
      </div>

      {/* Storage Used Card */}
      <div className="glass-card glass-card-hover p-5 rounded-2xl relative overflow-hidden bg-white border border-slate-200">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">Storage Footprint</p>
            <h4 className="text-2xl font-extrabold text-slate-900 mt-1">
              {stats?.formatted_total_size ?? '0 B'}
            </h4>
          </div>
          <div className="p-3 rounded-xl bg-blue-50 border border-blue-200 text-blue-600">
            <HardDrive className="w-6 h-6" />
          </div>
        </div>
        <p className="text-[11px] text-slate-600 mt-3 font-medium">
          Local / Server Storage (Structured)
        </p>
      </div>

      {/* Processing Speed Card */}
      <div className="glass-card glass-card-hover p-5 rounded-2xl relative overflow-hidden bg-white border border-slate-200">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">Processing Speed</p>
            <h4 className="text-2xl font-extrabold text-slate-900 mt-1">
              {stats?.processing_speed_dpm ?? 0} <span className="text-sm font-bold text-slate-500">docs/min</span>
            </h4>
          </div>
          <div className="p-3 rounded-xl bg-purple-50 border border-purple-200 text-purple-600">
            <Cpu className="w-6 h-6" />
          </div>
        </div>
        <p className="text-[11px] text-slate-600 mt-3 font-medium truncate">
          Calculated over the last 10 minutes
        </p>
      </div>

      {/* Needs Review Card */}
      <div className="glass-card glass-card-hover p-5 rounded-2xl relative overflow-hidden bg-amber-50 border border-amber-200">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-bold text-amber-700 uppercase tracking-wider">Needs Review</p>
            <h4 className="text-2xl font-extrabold text-slate-900 mt-1">
              {stats?.status_breakdown?.find(s => s.status === 'NEEDS_REVIEW')?.count ?? 0}
            </h4>
          </div>
          <div className="p-3 rounded-xl bg-amber-100 border border-amber-300 text-amber-600">
            <Shield className="w-6 h-6" />
          </div>
        </div>
        <p className="text-[11px] text-amber-700 font-medium mt-3">
          Documents failing auto-classification
        </p>
      </div>

    </div>
  );
}
