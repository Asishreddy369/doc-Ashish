import React, { useState } from 'react';
import { UploadCloud, FolderOpen } from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab }) {
  // BUG-F11 FIX: Track icon load failure so we show a text fallback instead of
  // a broken image icon when /icon.png is missing.
  const [iconError, setIconError] = useState(false);

  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-200 bg-white/90 backdrop-blur-md shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        
        {/* Logo & Title */}
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 flex items-center justify-center rounded-xl bg-gradient-to-br from-rose-600 to-red-600 shadow-md text-white overflow-hidden">
            {iconError ? (
              <span className="text-white font-black text-sm">DV</span>
            ) : (
              <img
                src="/icon.png"
                alt="Logo"
                className="w-full h-full object-cover"
                onError={() => setIconError(true)}
              />
            )}
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-900">
              DocVault
            </h1>
            <p className="text-[10px] text-slate-500 font-medium uppercase tracking-wider">Enterprise Document Management</p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setActiveTab('upload')}
            className={`px-4 py-2 rounded-lg text-sm font-semibold flex items-center space-x-2 transition-colors ${
              activeTab === 'upload' 
                ? 'bg-rose-50 text-rose-700' 
                : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
            }`}
          >
            <UploadCloud className="w-4 h-4" />
            <span>Upload Dashboard</span>
          </button>
          
          <button
            onClick={() => setActiveTab('files')}
            className={`px-4 py-2 rounded-lg text-sm font-semibold flex items-center space-x-2 transition-colors ${
              activeTab === 'files' 
                ? 'bg-rose-50 text-rose-700' 
                : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
            }`}
          >
            <FolderOpen className="w-4 h-4" />
            <span>Document Files</span>
          </button>
        </div>

      </div>
    </header>
  );
}
