import React, { useEffect, useRef, useState, useMemo } from 'react';
import {
  X,
  FileText,
  Tag,
  Clock,
  Download,
  AlertCircle,
  Code2,
  ListFilter,
  Calendar,
  Zap,
  Loader2,
  CheckCircle2
} from 'lucide-react';
import { extractDocumentTextApi, fetchDocumentDetailApi } from '../services/api';

const DEFAULT_CATEGORIES = [
  'Aadhaar',
  'PAN',
  'GST Certificate',
  'Invoice',
  'Purchase Order',
  'Bank Statement',
  'Contract',
  'Licence',
  'Other',
  'Unclassified'
];

// BUG-F23 FIX: Renamed prop from 'document' to 'doc' to avoid shadowing browser's window.document.
export default function DocumentDetailModal({ document: doc, onClose, onUpdateCategory, onDocumentUpdated, availableCategories = [] }) {
  // BUG-F16 FIX: Memoize merged categories so it's not recalculated on every render.
  const mergedCategories = useMemo(
    () => Array.from(new Set([...DEFAULT_CATEGORIES, ...availableCategories])).sort(),
    [availableCategories]
  );
  const safeDocument = doc || {};

  const [activeTab, setActiveTab] = useState('extracted_text');
  const [selectedCategory, setSelectedCategory] = useState(safeDocument.category || 'Unclassified');
  const [updatingCategory, setUpdatingCategory] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [currentDoc, setCurrentDoc] = useState(safeDocument);
  const onDocumentUpdatedRef = useRef(onDocumentUpdated);
  const extractionStatus = currentDoc.classifier_details?.extraction_status;
  const extractionInProgress = currentDoc.status === 'PROCESSING' || ['queued', 'running'].includes(extractionStatus);

  useEffect(() => {
    onDocumentUpdatedRef.current = onDocumentUpdated;
  }, [onDocumentUpdated]);

  useEffect(() => {
    if (!doc) return;
    // Sync the modal's editable local state when a new document is selected or refreshed.
    // eslint-disable-next-line react/set-state-in-effect
    setCurrentDoc(doc);
    setSelectedCategory(doc.category || 'Unclassified');
  }, [doc]);

  useEffect(() => {
    if (!currentDoc?.id || !extractionInProgress) return;

    let isMounted = true;
    // BUG-F08 FIX: Add max poll limit so we don't poll forever if server is stuck.
    let attempts = 0;
    const MAX_POLL_ATTEMPTS = 200; // 200 × 1500ms = 5 minutes max

    const poll = async () => {
      try {
        const freshDoc = await fetchDocumentDetailApi(currentDoc.id);
        if (!isMounted) return;
        setCurrentDoc(freshDoc);
        setSelectedCategory(freshDoc.category || 'Unclassified');
        if (onDocumentUpdatedRef.current) onDocumentUpdatedRef.current(freshDoc);
      } catch (err) {
        console.error('Failed to refresh extraction status:', err);
      }
    };

    const timer = setInterval(() => {
      attempts += 1;
      if (attempts >= MAX_POLL_ATTEMPTS) {
        clearInterval(timer);
        return;
      }
      poll();
    }, 1500);

    return () => {
      isMounted = false;
      clearInterval(timer);
    };
  }, [currentDoc?.id, extractionInProgress]);

  const handleCategoryChange = async (newCategory) => {
    // BUG-F04 FIX: Save previous category to restore it if the API call fails.
    const previousCategory = selectedCategory;
    setSelectedCategory(newCategory);
    setUpdatingCategory(true);
    try {
      await onUpdateCategory(currentDoc.id, newCategory);
      setCurrentDoc(prev => ({ ...prev, category: newCategory }));
    } catch (err) {
      console.error('Failed to update category:', err);
      // BUG-F04 FIX: Revert the optimistic update on failure.
      setSelectedCategory(previousCategory);
      alert('Failed to update category');
    } finally {
      setUpdatingCategory(false);
    }
  };

  const handleRunExtraction = async () => {
    setExtracting(true);
    try {
      const res = await extractDocumentTextApi(currentDoc.id);
      if (res.document) {
        setCurrentDoc(res.document);
        if (onDocumentUpdated) onDocumentUpdated(res.document);
      }
    } catch (err) {
      alert('Text extraction / OCR failed: ' + (err.response?.data?.error || err.message));
    } finally {
      setExtracting(false);
    }
  };

  const charCount = currentDoc.extracted_text ? currentDoc.extracted_text.length : 0;
  const wordCount = currentDoc.extracted_text ? currentDoc.extracted_text.trim().split(/\s+/).filter(Boolean).length : 0;

  if (!document) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-3xl bg-white rounded-2xl border border-slate-200 shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        
        {/* Header */}
        <div className="p-6 border-b border-slate-200 flex items-start justify-between bg-slate-50">
          <div className="flex items-start space-x-3 min-w-0 pr-4">
            <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-red-600 shrink-0">
              <FileText className="w-6 h-6" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center space-x-2 flex-wrap gap-y-1">
                <h3 className="text-lg font-extrabold text-slate-900 truncate" title={currentDoc.original_name}>
                  {currentDoc.original_name}
                </h3>
                <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold border ${
                  currentDoc.status === 'COMPLETED' ? 'bg-emerald-50 text-emerald-800 border-emerald-300' :
                  currentDoc.status === 'FAILED' ? 'bg-red-50 text-red-800 border-red-300' :
                  currentDoc.status === 'NEEDS_REVIEW' ? 'bg-amber-50 text-amber-800 border-amber-300' :
                  'bg-blue-50 text-blue-800 border-blue-300'
                }`}>
                  {currentDoc.status}
                </span>
              </div>
              
              <div className="mt-1 flex items-center space-x-3 text-xs text-slate-500 font-medium">
                <span className="font-mono text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-200 font-bold">
                  UUID: {currentDoc.id}
                </span>
                <span>•</span>
                <span className="uppercase font-bold text-slate-700">{currentDoc.file_type}</span>
                <span>•</span>
                <span>{currentDoc.formatted_size}</span>
              </div>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-200 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Category & Action Bar */}
        <div className="px-6 py-3 bg-red-50/50 border-b border-red-100 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center space-x-2 text-xs font-bold text-slate-700">
            <Tag className="w-4 h-4 text-red-600" />
            <span>Document Category:</span>
            <select
              value={selectedCategory}
              onChange={(e) => handleCategoryChange(e.target.value)}
              disabled={updatingCategory}
              className="px-3 py-1.5 rounded-lg bg-white border border-slate-300 text-xs font-bold text-slate-800 focus:outline-none focus:border-red-500 shadow-sm"
            >
              {mergedCategories.map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>
            {updatingCategory && <span className="text-xs text-red-600 font-semibold animate-pulse">Saving...</span>}
          </div>

          <button
            onClick={handleRunExtraction}
            disabled={extracting || extractionInProgress}
            className="px-3.5 py-1.5 rounded-lg bg-red-600 hover:bg-red-700 text-white text-xs font-bold shadow-sm flex items-center space-x-1.5 transition-colors disabled:opacity-50"
          >
            {extracting || extractionInProgress ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>{extractionStatus === 'queued' ? 'OCR Queued...' : 'Running OCR...'}</span>
              </>
            ) : (
              <>
                <Zap className="w-3.5 h-3.5" />
                <span>Run OCR / Extract Text</span>
              </>
            )}
          </button>
        </div>

        {/* Navigation Tabs */}
        <div className="flex border-b border-slate-200 bg-white px-6">
          <button
            onClick={() => setActiveTab('extracted_text')}
            className={`py-3 px-4 text-xs font-bold border-b-2 flex items-center space-x-2 transition-colors ${
              activeTab === 'extracted_text'
                ? 'border-red-600 text-red-600'
                : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          >
            <FileText className="w-4 h-4" />
            <span>Extracted Text ({wordCount} words)</span>
          </button>

          <button
            onClick={() => setActiveTab('overview')}
            className={`py-3 px-4 text-xs font-bold border-b-2 flex items-center space-x-2 transition-colors ${
              activeTab === 'overview'
                ? 'border-red-600 text-red-600'
                : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          >
            <ListFilter className="w-4 h-4" />
            <span>Metadata Overview</span>
          </button>

          <button
            onClick={() => setActiveTab('key_fields')}
            className={`py-3 px-4 text-xs font-bold border-b-2 flex items-center space-x-2 transition-colors ${
              activeTab === 'key_fields'
                ? 'border-red-600 text-red-600'
                : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          >
            <Code2 className="w-4 h-4" />
            <span>Key Fields (JSON)</span>
          </button>
        </div>

        {/* Tab Contents */}
        <div className="p-6 overflow-y-auto flex-1 space-y-4">
          
          {/* EXTRACTED TEXT TAB */}
          {activeTab === 'extracted_text' && (
            <div className="space-y-3">
              <div className="flex items-center justify-between text-xs text-slate-600 font-medium">
                <span>Normalized Text Content ({charCount} characters, {wordCount} words):</span>
                {currentDoc.extracted_text && (
                  <span className="text-emerald-700 font-bold flex items-center space-x-1">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Searchable Text Available</span>
                  </span>
                )}
              </div>

              {currentDoc.extracted_text ? (
                <div className="p-4 rounded-xl bg-slate-900 text-slate-100 font-mono text-xs whitespace-pre-wrap leading-relaxed max-h-80 overflow-y-auto border border-slate-800">
                  {currentDoc.extracted_text}
                </div>
              ) : extractionInProgress ? (
                <div className="p-10 text-center bg-blue-50 rounded-xl border border-blue-200 text-blue-700">
                  <Loader2 className="w-10 h-10 text-blue-600 mx-auto mb-2 animate-spin" />
                  <p className="font-bold text-blue-900">Extraction is running</p>
                  <p className="text-xs text-blue-700 mt-1 max-w-sm mx-auto">
                    Classification is already available. Text and key fields will appear here automatically when OCR finishes.
                  </p>
                </div>
              ) : (
                <div className="p-10 text-center bg-slate-50 rounded-xl border border-slate-200 text-slate-500">
                  <FileText className="w-10 h-10 text-slate-400 mx-auto mb-2" />
                  <p className="font-bold text-slate-800">No text extracted yet</p>
                  {currentDoc.error_info && (
                    <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 mt-3 max-w-md mx-auto">
                      {currentDoc.error_info}
                    </p>
                  )}
                  <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                    Click "Run OCR / Extract Text" above to process this document with our PyMuPDF & RapidOCR engine.
                  </p>
                  <button
                    onClick={handleRunExtraction}
                    disabled={extracting}
                    className="mt-4 px-4 py-2 rounded-xl bg-red-600 hover:bg-red-700 text-white text-xs font-bold shadow-md inline-flex items-center space-x-2 disabled:opacity-50"
                  >
                    {extracting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
                    <span>{extracting ? 'Extracting...' : 'Extract Text Now'}</span>
                  </button>
                </div>
              )}
            </div>
          )}

          {/* OVERVIEW TAB */}
          {activeTab === 'overview' && (
            <div className="space-y-4 text-xs text-slate-700">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
                  <p className="text-[10px] uppercase font-bold text-slate-500 mb-1">SHA-256 Checksum</p>
                  <p className="font-mono text-slate-800 break-all">{currentDoc.checksum || 'N/A'}</p>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
                  <p className="text-[10px] uppercase font-bold text-slate-500 mb-1">Matched Rule ID</p>
                  <p className="font-mono text-slate-800 break-all">{currentDoc.matched_rule || 'N/A'}</p>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
                  <p className="text-[10px] uppercase font-bold text-slate-500 mb-1">Upload Date & Time</p>
                  <p className="font-semibold text-slate-800 flex items-center space-x-1">
                    <Calendar className="w-3.5 h-3.5 text-slate-500" />
                    <span>{new Date(currentDoc.created_at).toLocaleString()}</span>
                  </p>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
                  <p className="text-[10px] uppercase font-bold text-slate-500 mb-1">Processing Date & Time</p>
                  <p className="font-semibold text-slate-800 flex items-center space-x-1">
                    <Clock className="w-3.5 h-3.5 text-slate-500" />
                    <span>{currentDoc.processed_at ? new Date(currentDoc.processed_at).toLocaleString() : 'Not Processed Yet'}</span>
                  </p>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
                  <p className="text-[10px] uppercase font-bold text-slate-500 mb-1">Batch Identifier</p>
                  <p className="font-mono text-slate-800">{currentDoc.batch_id || 'N/A'}</p>
                </div>
              </div>

              {currentDoc.error_info && (
                <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-800">
                  <div className="flex items-center space-x-2 font-bold mb-1">
                    <AlertCircle className="w-4 h-4 text-red-600" />
                    <span>Processing Error Logs</span>
                  </div>
                  <pre className="text-[11px] font-mono whitespace-pre-wrap bg-white p-2.5 rounded border border-red-200 mt-2">
                    {currentDoc.error_info}
                  </pre>
                </div>
              )}
            </div>
          )}

          {/* KEY FIELDS TAB */}
          {activeTab === 'key_fields' && (
            <div className="space-y-2">
              <p className="text-xs font-bold text-slate-600">Structured Key Fields (JSON):</p>
              {currentDoc.key_fields && Object.keys(currentDoc.key_fields).length > 0 ? (
                <div className="p-4 rounded-xl bg-slate-900 text-emerald-400 font-mono text-xs whitespace-pre-wrap max-h-80 overflow-y-auto border border-slate-800">
                  {JSON.stringify(currentDoc.key_fields, null, 2)}
                </div>
              ) : (
                <div className="p-8 text-center bg-slate-50 rounded-xl border border-slate-200 text-slate-500">
                  <Code2 className="w-8 h-8 text-slate-400 mx-auto mb-2" />
                  <p className="font-bold text-slate-700">No key fields extracted</p>
                  <p className="text-xs text-slate-500 mt-1">Structured key-value entities will appear here once parsed.</p>
                </div>
              )}
            </div>
          )}

        </div>

        {/* Footer Actions */}
        <div className="p-4 border-t border-slate-200 bg-slate-50 flex justify-between items-center">
          {currentDoc.file_url ? (
            <a
              href={currentDoc.file_url}
              target="_blank"
              rel="noopener noreferrer"
              className="px-4 py-2 rounded-xl bg-red-600 hover:bg-red-700 text-white font-bold text-xs shadow-md flex items-center space-x-2"
            >
              <Download className="w-4 h-4" />
              <span>Download Original File</span>
            </a>
          ) : <div />}

          <button
            onClick={onClose}
            className="px-5 py-2 rounded-xl bg-white border border-slate-300 text-slate-700 font-bold text-xs hover:bg-slate-100 shadow-sm"
          >
            Close
          </button>
        </div>

      </div>
    </div>
  );
}
