import React, { useState, useEffect, useRef } from 'react';
import Navbar from './components/Navbar';
import UploadZone from './components/UploadZone';
import BatchProgress from './components/BatchProgress';
import DocumentList from './components/DocumentList';
import DocumentDetailModal from './components/DocumentDetailModal';
import FolderPlanReview from './components/FolderPlanReview';
import StatsCards from './components/StatsCards';
import {
  fetchDocuments,
  fetchDocumentDetailApi,
  fetchDocumentStats,
  deleteDocumentApi,
  batchDeleteApi,
  extractAllTextApi,
  uploadSingleFileApi,
  updateDocumentCategoryApi,
  fetchFolderPlanApi
} from './services/api';

const MAX_CONCURRENT_UPLOADS = 7;

const DEFAULT_USER_FOLDERS = [];
const DEFAULT_USER_FOLDER_MAPPINGS = {};

export default function App() {
  const [documents, setDocuments] = useState([]);
  const [stats, setStats] = useState(null);
  const [loadingDocs, setLoadingDocs] = useState(false);
  // BUG-F05 FIX: Track load errors so we can show an error banner instead of a blank page.
  const [loadError, setLoadError] = useState(null);
  const [uploadCategory, setUploadCategory] = useState('Unclassified');
  const [organizationMode, setOrganizationMode] = useState('auto');
  const [structureLevels, setStructureLevels] = useState(['category', 'year', 'month']);
  const [customCategories, setCustomCategories] = useState('Bank Statements, GST, Invoices, PAN, Aadhaar, Employee Documents, Certificates, Tax Documents, Land and Building, Loans and Debt, Share Capital, Insurance, Power, Other Documents');
  const [userFolderRoot, setUserFolderRoot] = useState('');
  const [userFolders, setUserFolders] = useState(DEFAULT_USER_FOLDERS);
  const [userFolderMappings, setUserFolderMappings] = useState(DEFAULT_USER_FOLDER_MAPPINGS);
  const [selectedDocForModal, setSelectedDocForModal] = useState(null);
  const [activeTab, setActiveTab] = useState('upload');
  const [plannedBatch, setPlannedBatch] = useState(null);
  const [folderPlan, setFolderPlan] = useState(null);
  const [folderPlanLoading, setFolderPlanLoading] = useState(false);
  const [folderPlanError, setFolderPlanError] = useState(null);
  const [extractingMissingText, setExtractingMissingText] = useState(false);

  const [queue, setQueue] = useState([]);
  // BUG-F03 FIX: Removed isProcessingQueue mutex — the slot-based check
  // (uploadingItems.length >= MAX_CONCURRENT_UPLOADS) is sufficient and correctly
  // handles new PENDING items added while a batch is already uploading.
  const dataRefreshTimer = useRef(null);
  const activeTabRef = useRef(activeTab);
  const extractionPollTimers = useRef(new Set());

  // Fetch initial documents and metrics
  const loadData = async () => {
    try {
      setLoadingDocs(true);
      setLoadError(null);
      const [docRes, statRes] = await Promise.all([
        fetchDocuments(),
        fetchDocumentStats(),
      ]);
      setDocuments(docRes.documents || []);
      setStats(statRes);
    } catch (err) {
      console.error('Failed to load initial data:', err);
      // BUG-F05 FIX: Surface the error so the user sees a message and a retry button.
      setLoadError(err.userMessage || err.message || 'Failed to connect to server');
    } finally {
      setLoadingDocs(false);
    }
  };

  const loadStats = async () => {
    try {
      const statRes = await fetchDocumentStats();
      setStats(statRes);
    } catch (err) {
      console.error('Failed to refresh document stats:', err);
    }
  };

  const scheduleDataRefresh = (delay = 2000) => {
    if (dataRefreshTimer.current) {
      clearTimeout(dataRefreshTimer.current);
    }

    dataRefreshTimer.current = setTimeout(() => {
      if (activeTabRef.current === 'files') {
        loadData();
      } else {
        loadStats();
      }
    }, delay);
  };

  useEffect(() => {
    const pollTimers = extractionPollTimers.current;
    // Initial server sync when the app opens.
    // eslint-disable-next-line react/set-state-in-effect
    loadData();

    return () => {
      if (dataRefreshTimer.current) {
        clearTimeout(dataRefreshTimer.current);
      }
      pollTimers.forEach((timer) => clearTimeout(timer));
      pollTimers.clear();
    };
  }, []);

  useEffect(() => {
    activeTabRef.current = activeTab;
    if (activeTab === 'files') {
      // Refresh the explorer when the files tab becomes active.
      // eslint-disable-next-line react/set-state-in-effect
      loadData();
    }
  }, [activeTab]);

  const buildCategoryMap = (categoriesText) => {
    const custom = categoriesText
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean);
    const find = (needle, fallback) => custom.find((item) => item.toLowerCase().includes(needle)) || fallback;

    return {
      'Accounts and Bank Related Documents': find('bank', 'Bank Statements'),
      'Accounts and Bank related Documents': find('bank', 'Bank Statements'),
      'Bank Statement': find('bank', 'Bank Statements'),
      'GST Certificate': find('gst', 'GST'),
      Invoice: find('invoice', 'Invoices'),
      'Proforma Invoice': find('invoice', 'Invoices'),
      Tax: find('tax', 'Tax Documents'),
      'Tax Filing': find('tax', 'Tax Documents'),
      'Land And Building': find('land', 'Land and Building'),
      'Land and Building': find('land', 'Land and Building'),
      'Loans and Debt': find('loan', 'Loans and Debt'),
      'Share Capital and Other Instruments Issued': find('share', 'Share Capital'),
      'Share Capital and Other Instruments issued': find('share', 'Share Capital'),
      Insurance: find('insurance', 'Insurance'),
      Power: find('power', 'Power'),
      PAN: find('pan', 'PAN'),
      Aadhaar: find('aadhaar', 'Aadhaar'),
      'Certificates and Registration': find('certificate', 'Certificates'),
      Other: find('other', 'Other Documents'),
      Unclassified: find('other', 'Other Documents'),
    };
  };

  const buildUserFolderOptions = () => {
    const cleanFolders = userFolders
      .map((folder) => folder.trim())
      .filter(Boolean);
    const fallbackFolder = cleanFolders.find((folder) => folder.toLowerCase() === 'unclassified') || cleanFolders[0] || 'Unclassified';

    return {
      root_folder: userFolderRoot.trim(),
      folders: cleanFolders.length > 0 ? cleanFolders : ['Unclassified'],
      fallback_folder: fallbackFolder,
      category_folder_map: userFolderMappings,
    };
  };

  const getBatchIdForFiles = (files) => {
    const firstRelativePath = files.find((file) => file.webkitRelativePath)?.webkitRelativePath;
    if (firstRelativePath) {
      return firstRelativePath.split('/')[0] || `Batch_${Date.now()}`;
    }
    const now = new Date();
    const pad = (n) => String(n).padStart(2, '0');
    const dateStr = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}_${pad(now.getHours())}-${pad(now.getMinutes())}-${pad(now.getSeconds())}`;
    return `Batch_${dateStr}`;
  };

  // Handle new files dropped/selected
  const handleFilesSelected = async (newFiles, options) => {
    const generatedBatchId = getBatchIdForFiles(newFiles);
    const selectedMode = options?.mode || organizationMode;
    const folderOptions = selectedMode === 'user_defined'
      ? options?.folderOptions || buildUserFolderOptions()
      : {};
    const categoryMap = selectedMode === 'user_defined' ? {} : buildCategoryMap(customCategories);
    const planItems = newFiles.map((file) => ({
      name: file.name,
      relative_path: file.webkitRelativePath || file.name,
      category: uploadCategory === 'Unclassified' ? '' : uploadCategory,
    }));

    setFolderPlanLoading(true);
    setFolderPlanError(null);
    setFolderPlan(null);

    try {
      const plan = await fetchFolderPlanApi({
        mode: selectedMode,
        structure_levels: options?.structureLevels || structureLevels,
        category_map: categoryMap,
        folder_options: folderOptions,
        documents: planItems,
      });

      setPlannedBatch({
        files: newFiles,
        batchId: generatedBatchId,
        category: uploadCategory,
        organization: {
          mode: options?.mode || organizationMode,
          structureLevels: options?.structureLevels || structureLevels,
          categoryMap,
          folderOptions,
        },
      });
      setFolderPlan(plan);
    } catch (err) {
      setFolderPlanError(err.response?.data?.error || err.message || 'Failed to build folder plan');
    } finally {
      setFolderPlanLoading(false);
    }
  };

  const startPlannedUpload = () => {
    if (!plannedBatch) return;

    const newQueueItems = plannedBatch.files.map((file, index) => {
      const fileCategory = plannedBatch.category;

      return {
        id: `${plannedBatch.batchId}_${index}_${file.name}`,
        file,
        batchId: plannedBatch.batchId,
        category: fileCategory,
        relativePath: file.webkitRelativePath || file.name,
        organization: plannedBatch.organization,
        status: 'PENDING',
        progress: 0,
        error: null,
        docId: null,
      };
    });

    setQueue((prevQueue) => [...prevQueue, ...newQueueItems]);
    setPlannedBatch(null);
    setFolderPlan(null);
    setFolderPlanError(null);
  };

  const cancelPlannedUpload = () => {
    setPlannedBatch(null);
    setFolderPlan(null);
    setFolderPlanError(null);
  };

  const isExtractionStillRunning = (doc) => {
    const extractionStatus = doc?.classifier_details?.extraction_status;
    return doc?.status === 'PROCESSING' || ['queued', 'running'].includes(extractionStatus);
  };

  const pollExtractionStatus = (docId, queueItemId, attempt = 0) => {
    if (!docId || attempt > 120) {
      return;
    }

    const timer = setTimeout(async () => {
      extractionPollTimers.current.delete(timer);
      try {
        const freshDoc = await fetchDocumentDetailApi(docId);
        if (isExtractionStillRunning(freshDoc)) {
          pollExtractionStatus(docId, queueItemId, attempt + 1);
          return;
        }

        setQueue((prev) =>
          prev.map((q) =>
            q.id === queueItemId
              ? {
                  ...q,
                  status: freshDoc.status === 'FAILED' || freshDoc.classifier_details?.extraction_status === 'failed' ? 'FAILED' : 'COMPLETED',
                  error: freshDoc.status === 'FAILED' || freshDoc.classifier_details?.extraction_status === 'failed' ? freshDoc.error_info || 'Extraction failed' : null,
                  progress: 100,
                }
              : q
          )
        );
        scheduleDataRefresh(250);
      } catch (err) {
        if (attempt < 10) {
          pollExtractionStatus(docId, queueItemId, attempt + 1);
          return;
        }

        setQueue((prev) =>
          prev.map((q) =>
            q.id === queueItemId
              ? { ...q, status: 'FAILED', error: err.response?.data?.error || err.message || 'Extraction status check failed' }
              : q
          )
        );
      }
    }, attempt === 0 ? 600 : 1500);

    extractionPollTimers.current.add(timer);
  };

  // Queue Worker Engine (processes queued files with concurrency control)
  useEffect(() => {
    const processQueue = async () => {
      // BUG-F03 FIX: Removed isProcessingQueue mutex — the slot count check below
      // correctly throttles concurrency without blocking new items from starting.
      const pendingItems = queue.filter(item => item.status === 'PENDING');
      const uploadingItems = queue.filter(item => item.status === 'UPLOADING');

      if (pendingItems.length === 0 || uploadingItems.length >= MAX_CONCURRENT_UPLOADS) {
        return;
      }

      const availableSlots = MAX_CONCURRENT_UPLOADS - uploadingItems.length;
      const itemsToStart = pendingItems.slice(0, availableSlots);

      // Mark items as UPLOADING
      setQueue((prev) =>
        prev.map((item) =>
          itemsToStart.some((s) => s.id === item.id)
            ? { ...item, status: 'UPLOADING' }
            : item
        )
      );

      // Launch upload promises in parallel
      await Promise.all(
        itemsToStart.map(async (queueItem) => {
          try {
            const res = await uploadSingleFileApi(
              queueItem.file,
              queueItem.batchId,
              queueItem.category,
              (percent) => {
                setQueue((prev) =>
                  prev.map((q) =>
                    q.id === queueItem.id ? { ...q, progress: percent } : q
                  )
                );
              },
              {
                relativePath: queueItem.relativePath,
                mode: queueItem.organization?.mode,
                structureLevels: queueItem.organization?.structureLevels,
                categoryMap: queueItem.organization?.categoryMap,
                folderOptions: queueItem.organization?.folderOptions,
              }
            );

            const uploadedDoc = res.documents?.[0];
            const uploadedDocStillProcessing = isExtractionStillRunning(uploadedDoc);

            setQueue((prev) =>
              prev.map((q) =>
                q.id === queueItem.id
                  ? {
                      ...q,
                      status: uploadedDocStillProcessing ? 'EXTRACTING' : 'COMPLETED',
                      progress: 100,
                      docId: uploadedDoc?.id || null,
                    }
                  : q
              )
            );

            if (uploadedDocStillProcessing) {
              pollExtractionStatus(uploadedDoc.id, queueItem.id);
            }

            scheduleDataRefresh();
          } catch (err) {
            const errorMsg = err.response?.data?.error || err.message || 'Upload failed';
            setQueue((prev) =>
              prev.map((q) =>
                q.id === queueItem.id
                  ? { ...q, status: 'FAILED', error: errorMsg }
                  : q
              )
            );
          }
        })
      );
    };

    processQueue();
  // Queue processing intentionally reacts only to queue changes; helper functions
  // are stable enough for this local worker loop and would restart uploads if
  // included directly.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [queue]);

  const handleClearCompleted = () => {
    setQueue((prev) => prev.filter((item) => item.status !== 'COMPLETED'));
  };

  const handleRetryFailed = () => {
    setQueue((prev) =>
      prev.map((item) =>
        item.status === 'FAILED' ? { ...item, status: 'PENDING', error: null, progress: 0 } : item
      )
    );
  };

  const handleExtractMissingText = async () => {
    setExtractingMissingText(true);
    try {
      await extractAllTextApi();
      await loadData();
    } catch (err) {
      alert('Failed to queue missing text extraction: ' + (err.response?.data?.error || err.message));
    } finally {
      setExtractingMissingText(false);
    }
  };

  const handleDeleteDocument = async (id) => {
    if (!window.confirm('Are you sure you want to delete this document from storage?')) {
      return;
    }
    try {
      await deleteDocumentApi(id);
      if (selectedDocForModal?.id === id) {
        setSelectedDocForModal(null);
      }
      // BUG-F10 FIX: Added .catch() so network errors don't silently swallow.
      loadData().catch(console.error);
    } catch (err) {
      alert('Failed to delete document: ' + (err.userMessage || err.message));
    }
  };

  const handleBatchDelete = async (batchId, category = null) => {
    const msg = batchId && category
      ? `Are you sure you want to delete all documents in category '${category}' for folder '${batchId}'?`
      : category
      ? `Are you sure you want to delete all documents in category '${category}'?`
      : `Are you sure you want to delete the entire folder '${batchId}'?`;
      
    if (!window.confirm(msg)) return;
    
    try {
      await batchDeleteApi(batchId, category);
      if (selectedDocForModal && ((batchId && selectedDocForModal.batch_id === batchId) || (category && selectedDocForModal.category === category))) {
        setSelectedDocForModal(null);
      }
      // BUG-F10 FIX: Added .catch() so network errors don't silently swallow.
      loadData().catch(console.error);
    } catch (err) {
      alert('Failed to delete batch: ' + (err.userMessage || err.message));
    }
  };

  const handleUpdateCategory = async (id, newCategory) => {
    try {
      await updateDocumentCategoryApi(id, newCategory);
      setDocuments((prev) =>
        prev.map((d) => (d.id === id ? { ...d, category: newCategory } : d))
      );
      if (selectedDocForModal?.id === id) {
        setSelectedDocForModal((prev) => (prev ? { ...prev, category: newCategory } : null));
      }
      // BUG-F10 FIX: Added .catch() so network errors don't silently swallow.
      loadData().catch(console.error);
    } catch (err) {
      console.error('Failed to update category:', err);
      alert('Failed to update category');
    }
  };

  const handleSelectDocument = async (doc) => {
    setSelectedDocForModal(doc);
    try {
      const fullDoc = await fetchDocumentDetailApi(doc.id);
      setSelectedDocForModal(fullDoc);
    } catch (err) {
      console.error('Failed to load document details:', err);
    }
  };

  const handleDocumentUpdated = (updatedDoc) => {
    setSelectedDocForModal(updatedDoc);
    setDocuments((prev) => prev.map((doc) => (doc.id === updatedDoc.id ? { ...doc, ...updatedDoc } : doc)));
    loadStats();
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans">
      
      {/* Navbar Header */}
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} />

      {/* BUG-F05 FIX: Error banner with retry button when backend is unreachable */}
      {loadError && (
        <div className="max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 pt-4">
          <div className="flex items-center justify-between p-4 rounded-xl bg-red-50 border border-red-300 text-red-800 text-sm font-medium">
            <span>⚠️ Could not connect to server: <strong>{loadError}</strong></span>
            <button
              onClick={() => loadData()}
              className="ml-4 px-3 py-1.5 rounded-lg bg-red-600 text-white text-xs font-bold hover:bg-red-700 transition-colors"
            >
              Retry
            </button>
          </div>
        </div>
      )}

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        
        {activeTab === 'upload' && (
          <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            {/* Stats Overview — BUG-F02/IMP-01 FIX: StatsCards integrated into Upload Dashboard */}
            <StatsCards stats={stats} />

            {/* Upload Dropzone Component */}
            <UploadZone
              onFilesSelected={handleFilesSelected}
              selectedCategory={uploadCategory}
              onCategoryChange={setUploadCategory}
              organizationMode={organizationMode}
              onOrganizationModeChange={setOrganizationMode}
              structureLevels={structureLevels}
              onStructureLevelsChange={setStructureLevels}
              customCategories={customCategories}
              onCustomCategoriesChange={setCustomCategories}
              userFolderRoot={userFolderRoot}
              onUserFolderRootChange={setUserFolderRoot}
              userFolders={userFolders}
              onUserFoldersChange={setUserFolders}
              userFolderMappings={userFolderMappings}
              onUserFolderMappingsChange={setUserFolderMappings}
            />

            <FolderPlanReview
              plan={folderPlan}
              loading={folderPlanLoading}
              error={folderPlanError}
              onStart={startPlannedUpload}
              onCancel={cancelPlannedUpload}
            />

            {/* Live Batch Progress Manager */}
            {queue.length > 0 && (
              <BatchProgress
                queue={queue}
                stats={stats}
                onClearCompleted={handleClearCompleted}
                onRetryFailed={handleRetryFailed}
              />
            )}
          </div>
        )}

        {activeTab === 'files' && (
          <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
            {/* Stored Document Library Table */}
            <DocumentList
              documents={documents}
              loading={loadingDocs}
              onDelete={handleDeleteDocument}
              onBatchDelete={handleBatchDelete}
              onSelectDocument={handleSelectDocument}
              onExtractMissingText={handleExtractMissingText}
              extractingMissingText={extractingMissingText}
              missingTextCount={documents.filter((doc) => !doc.has_extracted_text).length}
              onUpdateCategory={handleUpdateCategory}
              availableCategories={stats?.available_categories || []}
            />
          </div>
        )}

      </main>

      {/* Document Details Modal */}
      {selectedDocForModal && (
        <DocumentDetailModal
          document={selectedDocForModal}
          onClose={() => setSelectedDocForModal(null)}
          onUpdateCategory={handleUpdateCategory}
          onDocumentUpdated={handleDocumentUpdated}
          availableCategories={stats?.available_categories || []}
        />
      )}

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white py-6 text-center text-xs text-slate-500 font-medium">
        <p>DocVault &copy; {new Date().getFullYear()} Enterprise Document Management</p>
      </footer>

    </div>
  );
}
