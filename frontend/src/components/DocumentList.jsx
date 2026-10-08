import React, { useState, useEffect, useRef } from 'react';
import {
  FileText,
  Image,
  FileSpreadsheet,
  FileCode,
  File,
  Search,
  Trash2,
  Download,
  Clock,
  Eye,
  Loader2,
  Folder,
  ChevronRight,
  Home,
  FolderOpen,
  Zap
} from 'lucide-react';

export default function DocumentList({
  documents,
  loading,
  onDelete,
  onBatchDelete,
  onSelectDocument,
  onExtractMissingText,
  extractingMissingText = false,
  missingTextCount = 0,
  onUpdateCategory: _onUpdateCategory,
  availableCategories: _availableCategories = []
}) {
  const [searchTerm, setSearchTerm] = useState('');
  // BUG-F07 FIX: Debounced search term — only update filter after 300ms idle
  // to prevent scanning large extracted_text strings on every keystroke.
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const debounceTimer = useRef(null);

  useEffect(() => {
    if (debounceTimer.current) clearTimeout(debounceTimer.current);
    debounceTimer.current = setTimeout(() => setDebouncedSearch(searchTerm), 300);
    return () => clearTimeout(debounceTimer.current);
  }, [searchTerm]);
  
  // viewPath: [] = root, ['category' | 'batch_id'] = inside folder, then nested organization path segments
  const [viewPath, setViewPath] = useState([]);
  const [groupMode, setGroupMode] = useState('batch');

  const getFileIcon = (fileType) => {
    const type = fileType?.toLowerCase();
    if (['jpg', 'jpeg', 'png', 'tiff', 'tif'].includes(type)) {
      return <Image className="w-8 h-8 text-blue-500" />;
    }
    if (type === 'pdf') {
      return <FileText className="w-8 h-8 text-red-500" />;
    }
    if (['docx', 'doc'].includes(type)) {
      return <FileText className="w-8 h-8 text-blue-600" />;
    }
    if (['xlsx', 'xls'].includes(type)) {
      return <FileSpreadsheet className="w-8 h-8 text-emerald-600" />;
    }
    if (type === 'txt') {
      return <FileCode className="w-8 h-8 text-slate-700" />;
    }
    return <File className="w-8 h-8 text-slate-500" />;
  };

  // BUG-F07 FIX: Use debouncedSearch for filtering. Removed extracted_text search
  // (too expensive client-side at scale). Added category and organization_path search.
  const filteredDocuments = documents.filter((doc) => {
    if (!debouncedSearch) return true;
    const q = debouncedSearch.toLowerCase();
    return (
      doc.original_name.toLowerCase().includes(q) ||
      doc.id.toLowerCase().includes(q) ||
      (doc.category && doc.category.toLowerCase().includes(q)) ||
      (doc.organization_path && doc.organization_path.toLowerCase().includes(q))
    );
  });

  // Group by Category (Clean, executive-friendly view)
  const groupedCategories = filteredDocuments.reduce((acc, doc) => {
    const cat = doc.category || 'Unclassified';
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(doc);
    return acc;
  }, {});

  // Group by Batch -> nested organization_path
  const groupedDocs = filteredDocuments.reduce((acc, doc) => {
    const batch = doc.batch_id || 'Unknown Folder';
    if (!acc[batch]) acc[batch] = [];
    acc[batch].push(doc);
    return acc;
  }, {});

  const getBatchTimestamp = (batchId, docs = []) => {
    const isoMatch = String(batchId).match(/^Batch_(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})/);
    if (isoMatch) {
      const [, y, m, d, hr, min, sec] = isoMatch;
      const t = new Date(y, m - 1, d, hr, min, sec).getTime();
      if (!isNaN(t)) return t;
    }
    const epochMatch = String(batchId).match(/^batch_(\d{10,13})/);
    if (epochMatch) {
      const t = parseInt(epochMatch[1], 10);
      if (!isNaN(t)) return t;
    }
    if (docs.length > 0 && docs[0].created_at) {
      const t = new Date(docs[0].created_at).getTime();
      if (!isNaN(t)) return t;
    }
    return 0;
  };

  const formatBatchLabel = (batchId, docs = []) => {
    const ts = getBatchTimestamp(batchId, docs);
    if (ts > 0) {
      const d = new Date(ts);
      return `Batch — ${d.toLocaleDateString(undefined, { day: '2-digit', month: 'short', year: 'numeric' })} at ${d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', hour12: true })}`;
    }
    return batchId;
  };

  const getOrganizationParts = (doc) => {
    const path = doc.organization_path || doc.category || 'Unclassified';
    return path.split('/').map((part) => part.trim()).filter(Boolean);
  };

  const getCategoryFolderView = (category, pathSegments) => {
    const docs = groupedCategories[category] || [];
    const childFolders = {};
    const childFolderOrder = [];
    const files = [];

    const getDocSubparts = (doc) => {
      const orgPath = doc.organization_path || '';
      const parts = orgPath.split('/').map((p) => p.trim()).filter(Boolean);
      const catIdx = parts.findIndex((p) => p.toLowerCase() === category.toLowerCase());
      if (catIdx !== -1) {
        return parts.slice(catIdx + 1);
      }
      const fallback = [];
      if (doc.document_year) fallback.push(String(doc.document_year));
      if (doc.document_month) {
        const monthNames = [
          'January', 'February', 'March', 'April', 'May', 'June',
          'July', 'August', 'September', 'October', 'November', 'December'
        ];
        fallback.push(monthNames[doc.document_month - 1] || String(doc.document_month));
      }
      return fallback;
    };

    docs.forEach((doc) => {
      const subparts = getDocSubparts(doc);
      const matchesPath = pathSegments.every((segment, index) => subparts[index] === segment);
      if (!matchesPath) {
        if (pathSegments.length === 0) files.push(doc);
        return;
      }
      if (subparts.length > pathSegments.length) {
        const child = subparts[pathSegments.length];
        if (!childFolders[child]) {
          childFolders[child] = [];
          childFolderOrder.push(child);
        }
        childFolders[child].push(doc);
      } else {
        files.push(doc);
      }
    });

    return { childFolders, childFolderOrder, files };
  };

  const getImportedStructurePaths = (batchId) => {
    const docs = documents.filter((doc) => (doc.batch_id || 'Unknown Folder') === batchId);
    const structureDoc = docs.find((doc) => doc.folder_structure?.mode === 'user_defined' && doc.folder_structure?.folder_options);
    const folderOptions = structureDoc?.folder_structure?.folder_options;
    if (!folderOptions) return [];

    const rootParts = String(folderOptions.root_folder || '')
      .split('/')
      .map((part) => part.trim())
      .filter(Boolean);
    const folders = Array.isArray(folderOptions.folders) ? folderOptions.folders : [];
    const paths = [];
    const seen = new Set();

    const addPath = (parts) => {
      if (parts.length === 0) return;
      const key = parts.join('/');
      if (seen.has(key)) return;
      seen.add(key);
      paths.push(parts);
    };

    if (rootParts.length > 0) {
      addPath(rootParts);
    }

    folders.forEach((folder) => {
      const folderParts = String(folder || '')
        .split('/')
        .map((part) => part.trim())
        .filter(Boolean);
      const fullParts = [...rootParts, ...folderParts];
      for (let depth = 1; depth <= fullParts.length; depth += 1) {
        addPath(fullParts.slice(0, depth));
      }
    });

    return paths;
  };

  const getFolderView = (batchId, pathSegments) => {
    const docs = groupedDocs[batchId] || [];
    const childFolders = {};
    const childFolderOrder = [];
    const files = [];

    const ensureChildFolder = (folder) => {
      if (!childFolders[folder]) {
        childFolders[folder] = [];
        childFolderOrder.push(folder);
      }
    };

    getImportedStructurePaths(batchId).forEach((parts) => {
      const matchesPath = pathSegments.every((segment, index) => parts[index] === segment);
      if (!matchesPath) return;
      if (parts.length > pathSegments.length) {
        ensureChildFolder(parts[pathSegments.length]);
      }
    });

    docs.forEach((doc) => {
      const parts = getOrganizationParts(doc);
      const matchesPath = pathSegments.every((segment, index) => parts[index] === segment);
      if (!matchesPath) return;

      if (parts.length > pathSegments.length) {
        const child = parts[pathSegments.length];
        ensureChildFolder(child);
        childFolders[child].push(doc);
      } else {
        files.push(doc);
      }
    });

    return { childFolders, childFolderOrder, files };
  };

  const renderBreadcrumbs = () => {
    return (
      <div className="flex items-center space-x-2 text-sm font-bold text-slate-600 mb-6 pb-4 border-b border-slate-200">
        <button 
          onClick={() => setViewPath([])}
          className="flex items-center hover:text-red-600 transition-colors"
        >
          <Home className="w-4 h-4 mr-1" /> Vault Root
        </button>
        {viewPath.length > 0 && (
          <>
            <ChevronRight className="w-4 h-4 text-slate-400" />
            <button 
              onClick={() => setViewPath([viewPath[0]])}
              className={`hover:text-red-600 transition-colors ${viewPath.length === 1 ? 'text-slate-900' : ''}`}
            >
              {groupMode === 'batch' || String(viewPath[0]).toLowerCase().startsWith('batch_')
                ? formatBatchLabel(viewPath[0], groupedDocs[viewPath[0]])
                : viewPath[0]}
            </button>
          </>
        )}
        {viewPath.slice(1).map((segment, index) => {
          const targetPath = viewPath.slice(0, index + 2);
          const isLast = index === viewPath.length - 2;
          return (
            <React.Fragment key={`${segment}-${index}`}>
              <ChevronRight className="w-4 h-4 text-slate-400" />
              {isLast ? (
                <span className="text-slate-900">{segment}</span>
              ) : (
                <button
                  onClick={() => setViewPath(targetPath)}
                  className="hover:text-red-600 transition-colors"
                >
                  {segment}
                </button>
              )}
            </React.Fragment>
          );
        })}
      </div>
    );
  };

  const renderContent = () => {
    if (loading) {
      return (
        <div className="py-20 text-center text-slate-500 flex flex-col items-center">
          <div className="w-8 h-8 border-4 border-red-600 border-t-transparent rounded-full animate-spin mb-4" />
          <span className="font-bold text-lg">Loading vault...</span>
        </div>
      );
    }

    // Searching flattens the view
    if (debouncedSearch) {
      if (filteredDocuments.length === 0) {
        return (
          <div className="py-20 text-center text-slate-500">
            <Search className="w-12 h-12 text-slate-300 mx-auto mb-3" />
            <p className="font-bold text-lg text-slate-700">No matching documents found</p>
          </div>
        );
      }
      return renderFileGrid(filteredDocuments);
    }

    // LEVEL 0: ROOT FOLDERS
    if (viewPath.length === 0) {
      if (groupMode === 'category') {
        const categories = Object.keys(groupedCategories).sort();
        if (categories.length === 0) {
          return (
            <div className="py-20 text-center text-slate-500">
              <FolderOpen className="w-16 h-16 text-slate-300 mx-auto mb-4" />
              <p className="font-bold text-xl text-slate-800">Your Vault is Empty</p>
              <p className="text-sm mt-2">Upload documents to see them organized by category here.</p>
            </div>
          );
        }
        return (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {categories.map((cat) => {
              const fileCount = groupedCategories[cat].length;
              return (
                <div
                  key={cat}
                  className="group flex flex-col bg-white border border-slate-200 rounded-2xl p-5 shadow-sm hover:shadow-md hover:border-red-300 transition-all cursor-pointer"
                >
                  <div
                    className="flex-1 flex flex-col items-center text-center"
                    onClick={() => setViewPath([cat])}
                  >
                    <Folder className="w-16 h-16 text-rose-500 group-hover:text-red-600 transition-colors mb-3" fill="currentColor" />
                    <h4 className="font-extrabold text-slate-800 text-sm break-words w-full line-clamp-2">{cat}</h4>
                    <p className="text-xs font-bold text-slate-500 mt-1">{fileCount} {fileCount === 1 ? 'file' : 'files'}</p>
                  </div>
                  <div className="mt-4 pt-3 border-t border-slate-100 flex justify-center">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        if (onBatchDelete) onBatchDelete(null, cat);
                      }}
                      className="flex items-center text-[11px] font-bold text-red-600 hover:text-red-800 bg-red-50 hover:bg-red-100 px-3 py-1.5 rounded-lg transition-colors w-full justify-center"
                    >
                      <Trash2 className="w-3.5 h-3.5 mr-1.5" /> Delete Category
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        );
      }

      // Batch mode: sort by latest timestamp first!
      const sortedBatches = Object.keys(groupedDocs).sort((a, b) => {
        const timeA = getBatchTimestamp(a, groupedDocs[a]);
        const timeB = getBatchTimestamp(b, groupedDocs[b]);
        return timeB - timeA;
      });

      if (sortedBatches.length === 0) {
        return (
          <div className="py-20 text-center text-slate-500">
            <FolderOpen className="w-16 h-16 text-slate-300 mx-auto mb-4" />
            <p className="font-bold text-xl text-slate-800">Your Vault is Empty</p>
            <p className="text-sm mt-2">Upload folders to see them here.</p>
          </div>
        );
      }
      return (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {sortedBatches.map((batchId, index) => {
            const fileCount = groupedDocs[batchId].length;
            const formattedName = formatBatchLabel(batchId, groupedDocs[batchId]);
            const isLatest = index === 0;
            return (
              <div
                key={batchId}
                className={`group flex flex-col bg-white border ${
                  isLatest ? 'border-red-300 ring-1 ring-red-200' : 'border-slate-200'
                } rounded-2xl p-5 shadow-sm hover:shadow-md hover:border-red-400 transition-all cursor-pointer`}
              >
                <div 
                  className="flex-1 flex flex-col items-center text-center"
                  onClick={() => setViewPath([batchId])}
                >
                  <div className="relative">
                    <Folder
                      className={`w-16 h-16 ${
                        isLatest ? 'text-red-500' : 'text-slate-400'
                      } group-hover:text-red-600 transition-colors mb-3`}
                      fill="currentColor"
                    />
                    {isLatest && (
                      <span className="absolute -top-1 -right-2 px-1.5 py-0.5 rounded-full bg-emerald-500 text-white text-[9px] font-black uppercase tracking-wider shadow-sm">
                        New
                      </span>
                    )}
                  </div>
                  <h4 className="font-extrabold text-slate-800 text-sm break-words w-full line-clamp-2" title={formattedName}>
                    {formattedName}
                  </h4>
                  <div className="flex items-center gap-1.5 mt-1.5">
                    <span className="text-xs font-bold text-slate-500">{fileCount} {fileCount === 1 ? 'file' : 'files'}</span>
                    {isLatest && (
                      <span className="px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 text-[10px] font-bold border border-emerald-200">
                        Latest Batch
                      </span>
                    )}
                  </div>
                </div>
                <div className="mt-4 pt-3 border-t border-slate-100 flex justify-center">
                  <button 
                    onClick={(e) => { e.stopPropagation(); if (onBatchDelete) onBatchDelete(batchId); }}
                    className="flex items-center text-[11px] font-bold text-red-600 hover:text-red-800 bg-red-50 hover:bg-red-100 px-3 py-1.5 rounded-lg transition-colors w-full justify-center"
                  >
                    <Trash2 className="w-3.5 h-3.5 mr-1.5" /> Delete Batch
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      );
    }

    // NESTED LEVELS INSIDE A CATEGORY OR BATCH
    if (viewPath.length >= 1) {
      const rootFolderId = viewPath[0];
      const pathSegments = viewPath.slice(1);
      const { childFolders, childFolderOrder, files } = groupMode === 'category'
        ? getCategoryFolderView(rootFolderId, pathSegments)
        : getFolderView(rootFolderId, pathSegments);
      const folderNames = childFolderOrder;
      
      if (folderNames.length === 0 && files.length === 0) {
        return <p className="text-center py-10 font-bold text-slate-500">Folder is empty.</p>;
      }

      return (
        <div className="space-y-5">
          {folderNames.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {folderNames.map(folder => (
                <div
                  key={folder}
                  className="group flex flex-col bg-slate-50 border border-slate-200 rounded-2xl p-5 hover:border-red-300 hover:bg-white transition-all cursor-pointer shadow-sm hover:shadow-md"
                  onClick={() => setViewPath([rootFolderId, ...pathSegments, folder])}
                >
                  <div className="flex-1 flex flex-col items-center text-center">
                    <FolderOpen className="w-14 h-14 text-slate-400 group-hover:text-red-500 transition-colors mb-3" fill="currentColor" />
                    <h4 className="font-extrabold text-slate-800 text-sm break-words w-full">{folder}</h4>
                    <p className="text-xs font-bold text-slate-500 mt-1">{childFolders[folder].length} files</p>
                  </div>
                </div>
              ))}
            </div>
          )}

          {files.length > 0 && (
            <div>
              {folderNames.length > 0 && (
                <h4 className="text-xs font-extrabold uppercase tracking-wider text-slate-500 mb-3">Files in this folder</h4>
              )}
              {renderFileGrid(files)}
            </div>
          )}
        </div>
      );
    }
  };

  const renderFileGrid = (files) => {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {files.map(doc => (
          <div key={doc.id} className="bg-white border border-slate-200 rounded-2xl p-4 flex flex-col hover:border-red-300 hover:shadow-md transition-all">
            <div className="flex items-start justify-between mb-3">
              <div className="p-2 bg-slate-50 rounded-xl border border-slate-100">
                {getFileIcon(doc.file_type)}
              </div>
              <span className={`px-2 py-1 rounded text-[9px] uppercase font-bold border ${
                doc.status === 'COMPLETED' ? 'bg-emerald-50 text-emerald-800 border-emerald-300' :
                doc.status === 'FAILED' ? 'bg-red-50 text-red-800 border-red-300' :
                doc.status === 'NEEDS_REVIEW' ? 'bg-amber-50 text-amber-800 border-amber-300' :
                'bg-blue-50 text-blue-800 border-blue-300'
              }`}>
                {doc.status}
              </span>
            </div>
            
            <h4 className="font-bold text-sm text-slate-900 line-clamp-2 mb-1" title={doc.original_name}>
              {doc.original_name}
            </h4>
            
            <div className="text-[10px] text-slate-500 font-medium space-y-1 mb-4 flex-1">
              <p className="flex items-center"><Clock className="w-3 h-3 mr-1"/> {new Date(doc.created_at).toLocaleDateString()}</p>
              <p>{doc.formatted_size}</p>
              {doc.organization_path && <p className="text-red-700 font-bold line-clamp-2">{doc.organization_path}</p>}
            </div>

            <div className="flex items-center justify-between pt-3 border-t border-slate-100">
              <div className="flex space-x-1.5">
                <button
                  onClick={() => onSelectDocument(doc)}
                  className="p-2 rounded-lg bg-slate-100 hover:bg-slate-800 text-slate-600 hover:text-white transition-colors"
                  title="View Details"
                >
                  <Eye className="w-4 h-4" />
                </button>
                {doc.file_url && (
                  <a
                    href={doc.file_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-2 rounded-lg bg-slate-100 hover:bg-blue-600 text-slate-600 hover:text-white transition-colors flex items-center justify-center"
                    title="Download"
                  >
                    <Download className="w-4 h-4" />
                  </a>
                )}
              </div>
              <button
                onClick={() => onDelete(doc.id)}
                className="p-2 rounded-lg bg-red-50 hover:bg-red-600 text-red-600 hover:text-white transition-colors"
                title="Delete File"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="w-full mt-8 rounded-3xl bg-white border border-slate-200 p-8 shadow-xl">
      
      {/* Header & Search */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <h3 className="text-2xl font-black text-slate-900 tracking-tight flex items-center space-x-3">
            <span>DocVault Explorer</span>
          </h3>
          <p className="text-sm text-slate-500 mt-1 font-medium">Browse your documents exactly as you uploaded them.</p>
        </div>

        <div className="flex flex-col sm:flex-row sm:items-center gap-3">
          {/* View mode toggle: By Batch (Default) vs By Category */}
          <div className="flex items-center bg-slate-100 p-1 rounded-2xl border border-slate-200">
            <button
              type="button"
              onClick={() => { setGroupMode('batch'); setViewPath([]); }}
              className={`px-3 py-2 rounded-xl text-xs font-extrabold transition-all flex items-center gap-1.5 ${
                groupMode === 'batch'
                  ? 'bg-white text-red-600 shadow-sm border border-slate-200'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <span>By Batch</span>
            </button>
            <button
              type="button"
              onClick={() => { setGroupMode('category'); setViewPath([]); }}
              className={`px-3 py-2 rounded-xl text-xs font-extrabold transition-all flex items-center gap-1.5 ${
                groupMode === 'category'
                  ? 'bg-white text-red-600 shadow-sm border border-slate-200'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Folder className="w-3.5 h-3.5" />
              <span>By Category</span>
            </button>
          </div>

          {onExtractMissingText && missingTextCount > 0 && (
            <button
              type="button"
              onClick={onExtractMissingText}
              disabled={extractingMissingText}
              className="px-4 py-3 rounded-2xl bg-red-600 hover:bg-red-700 text-white text-xs font-extrabold shadow-sm disabled:opacity-60 inline-flex items-center justify-center gap-2"
            >
              {extractingMissingText ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
              <span>{extractingMissingText ? 'Queueing OCR...' : `Extract Missing Text (${missingTextCount})`}</span>
            </button>
          )}

          <div className="relative min-w-[280px]">
            <Search className="w-5 h-5 text-slate-400 absolute left-3 top-1/2 transform -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search across all files..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-3 rounded-2xl bg-slate-50 border border-slate-300 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-red-500 focus:ring-2 focus:ring-red-200 font-bold shadow-inner"
            />
          </div>
        </div>
      </div>

      {/* Breadcrumbs */}
      {!searchTerm && renderBreadcrumbs()}

      {/* Main Content Area */}
      <div className="min-h-[400px]">
        {renderContent()}
      </div>

    </div>
  );
}
