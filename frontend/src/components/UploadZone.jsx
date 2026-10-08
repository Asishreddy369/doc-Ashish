import React, { useState, useRef } from 'react';
import { UploadCloud, FileCheck, AlertTriangle, Layers, FolderTree, Wand2, FolderPlus, FolderInput } from 'lucide-react';

const ALLOWED_EXTENSIONS = ['pdf', 'jpg', 'jpeg', 'png', 'tiff', 'tif', 'docx', 'doc', 'xlsx', 'xls', 'txt', 'csv', 'zip', 'rar', 'jar', 'cer', 'csi', 'log', 'bat'];

const CATEGORY_OPTIONS = [
  'Unclassified',
  'Invoice',
  'Purchase Order',
  'Agreement',
  'Tax Filing',
  'Board Resolution',
  'Cap Table',
  'Bank Statement',
  'Archive',
  'Other'
];

const STRUCTURE_PRESETS = [
  { label: 'Category / Year / Month', value: ['category', 'year', 'month'] },
  { label: 'Year / Month / Category', value: ['year', 'month', 'category'] },
  { label: 'Category Only', value: ['category'] },
  { label: 'Original Folder / Category / Year', value: ['original_folder', 'category', 'year'] },
];

const MAPPABLE_CATEGORIES = [
  'Accounts and Bank Related Documents',
  'Accounts and Bank related Documents',
  'Audit',
  'Certificates and Registration',
  'Incorporation and MCA related',
  'Insurance',
  'Land and Building',
  'Loans and Debt',
  'Power',
  'Share Capital and Other Instruments Issued',
  'Share Capital and Other Instruments issued',
  'Tax',
  'GST Certificate',
  'PAN',
  'Aadhaar',
  'Invoice',
  'Proforma Invoice',
  'Purchase Order',
  'Bank Statement',
  'Agreement',
  'Board Resolution',
  'Meeting Minutes',
  'Offer Letter',
  'Tax Filing',
  'Digital Certificate',
  'Archive',
  'Other',
  'Unclassified',
];

const CATEGORY_FOLDER_HINTS = {
  'Accounts and Bank Related Documents': ['accountsandbankrelateddocuments', 'accounts', 'bank'],
  'Accounts and Bank related Documents': ['accountsandbankrelateddocuments', 'accounts', 'bank'],
  Audit: ['audit', 'auditedfinancials', 'taxaudit', 'internalaudit'],
  'Certificates and Registration': ['certificatesandregistration', 'certificates', 'registration'],
  'Incorporation and MCA related': ['incorporationandmcarelated', 'incorporation', 'mca'],
  Insurance: ['insurance'],
  'Land and Building': ['landandbuilding', 'land', 'building', 'epccontracts'],
  'Loans and Debt': ['loansanddebt', 'loans', 'debt'],
  Power: ['power', 'electricity', 'solar'],
  'Share Capital and Other Instruments Issued': ['sharecapitalandotherinstrumentsissued', 'sharecapital', 'sharecertificates'],
  'Share Capital and Other Instruments issued': ['sharecapitalandotherinstrumentsissued', 'sharecapital', 'sharecertificates'],
  Tax: ['tax', 'incometax', 'tds'],
  'GST Certificate': ['gst', 'gstr', 'tax'],
  PAN: ['pan'],
  Aadhaar: ['aadhaar', 'adhar'],
  Invoice: ['invoice', 'invoices', 'bill'],
  'Proforma Invoice': ['proforma', 'invoice', 'invoices', 'pi'],
  'Purchase Order': ['purchaseorder', 'purchaseorders', 'po', 'orders'],
  'Bank Statement': ['bankstatement', 'bankstatements', 'bank', 'statement'],
  Agreement: ['agreement', 'agreements', 'contract', 'contracts'],
  'Board Resolution': ['boardresolution', 'resolution', 'contracts'],
  'Meeting Minutes': ['meetingminutes', 'minutes', 'contracts'],
  'Offer Letter': ['offerletter', 'employee', 'hr', 'contracts'],
  'Tax Filing': ['tax', 'tds', 'filing', 'gst'],
  'Digital Certificate': ['certificate', 'certificates', 'digitalcertificate'],
  Archive: ['archive', 'archives'],
  Other: ['other', 'misc', 'unclassified'],
  Unclassified: ['unclassified', 'unknown', 'other'],
};

const normalizeKey = (value) => String(value || '').toLowerCase().replace(/[^a-z0-9]+/g, '');

const buildMappingsForFolders = (folders) => {
  const fallback = folders.find((folder) => normalizeKey(folder.split('/').pop()) === 'unclassified') || folders[0] || 'Unclassified';
  const folderEntries = folders.map((folder) => ({
    folder,
    key: normalizeKey(folder),
    leafKey: normalizeKey(folder.split('/').pop()),
  }));

  const scoreFolder = (folderEntry, hints) => {
    return hints.reduce((bestScore, hint, index) => {
      const hintKey = normalizeKey(hint);
      if (!hintKey) return bestScore;
      const priority = 100 - index;
      if (folderEntry.leafKey === hintKey) return Math.max(bestScore, priority + 1000);
      if (folderEntry.key === hintKey) return Math.max(bestScore, priority + 800);
      if (folderEntry.leafKey.includes(hintKey) || hintKey.includes(folderEntry.leafKey)) return Math.max(bestScore, priority + 500);
      if (folderEntry.key.includes(hintKey)) return Math.max(bestScore, priority + 200);
      return bestScore;
    }, 0);
  };

  return Object.fromEntries(
    MAPPABLE_CATEGORIES.map((category) => {
      const hints = CATEGORY_FOLDER_HINTS[category] || [category];
      const match = folderEntries
        .map((folderEntry) => ({ ...folderEntry, score: scoreFolder(folderEntry, hints) }))
        .filter((folderEntry) => folderEntry.score > 0)
        .sort((a, b) => b.score - a.score || a.folder.length - b.folder.length)[0];
      return [category, match?.folder || fallback];
    })
  );
};

export default function UploadZone({
  onFilesSelected,
  selectedCategory,
  onCategoryChange,
  organizationMode,
  onOrganizationModeChange,
  structureLevels,
  onStructureLevelsChange,
  customCategories,
  onCustomCategoriesChange: _onCustomCategoriesChange,
  userFolderRoot,
  onUserFolderRootChange,
  userFolders,
  onUserFoldersChange,
  userFolderMappings,
  onUserFolderMappingsChange,
}) {
  const [isDragging, setIsDragging] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  const fileInputRef = useRef(null);
  const folderInputRef = useRef(null);

  const importedFolders = (userFolders || []).map((folder) => folder.trim()).filter(Boolean);
  const safeUserFolders = importedFolders.length ? importedFolders : ['Unclassified'];
  const fallbackFolder = safeUserFolders.find((folder) => normalizeKey(folder.split('/').pop()) === 'unclassified') || 'Unclassified';
  const structureLines = importedFolders.map((folder) => ({
    name: folder.split('/').pop(),
    path: folder,
    depth: folder.split('/').filter(Boolean).length,
  }));

  const importFolderStructure = async () => {
    setErrorMessage(null);

    if (!window.showDirectoryPicker) {
      setErrorMessage('Your browser cannot read empty folders from a folder upload. Please use Chrome or Edge on localhost, or add folders manually.');
      return;
    }

    try {
      const rootHandle = await window.showDirectoryPicker({ mode: 'read' });
      const importedFolders = [];

      const walk = async (directoryHandle, prefix = '') => {
        for await (const [name, handle] of directoryHandle.entries()) {
          if (handle.kind !== 'directory') continue;
          const relativePath = prefix ? `${prefix}/${name}` : name;
          importedFolders.push(relativePath);
          await walk(handle, relativePath);
        }
      };

      await walk(rootHandle);

      const folders = importedFolders.length > 0
        ? importedFolders
        : ['Unclassified'];
      const hasFallback = folders.some((folder) => normalizeKey(folder.split('/').pop()) === 'unclassified');
      const finalFolders = hasFallback ? folders : [...folders, 'Unclassified'];

      onUserFolderRootChange(rootHandle.name || 'Company Documents');
      onUserFoldersChange(finalFolders);
      onUserFolderMappingsChange(buildMappingsForFolders(finalFolders));
      onOrganizationModeChange('user_defined');
    } catch (err) {
      if (err?.name === 'AbortError') return;
      setErrorMessage(err.message || 'Failed to import folder structure.');
    }
  };

  const processFiles = (fileList) => {
    setErrorMessage(null);
    const validFiles = [];
    const invalidFiles = [];

    Array.from(fileList).forEach((file) => {
      const parts = file.name.split('.');
      const ext = parts.length > 1 ? parts.pop().toLowerCase() : '';
      if (ext && ALLOWED_EXTENSIONS.includes(ext)) {
        validFiles.push(file);
      } else {
        invalidFiles.push(file.name);
      }
    });

    if (invalidFiles.length > 0 && validFiles.length === 0) {
      setErrorMessage(
        `All selected files were skipped due to unsupported extensions. Supported formats include PDF, Office files, Text, Archives, and Certificates.`
      );
    } else if (invalidFiles.length > 0) {
      // Just log to console instead of showing an annoying banner
      console.log(`Silently skipped ${invalidFiles.length} unsupported/system files.`);
    }

    if (organizationMode === 'user_defined' && importedFolders.length === 0) {
      setErrorMessage('Please import the destination folder structure first.');
      return;
    }

    if (validFiles.length > 0) {
      onFilesSelected(validFiles, {
        mode: organizationMode,
        structureLevels,
        customCategories,
        folderOptions: {
          root_folder: userFolderRoot,
          folders: safeUserFolders,
          fallback_folder: fallbackFolder,
          category_folder_map: userFolderMappings,
        },
      });
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  // BUG-F06 FIX: Check if the cursor moved to a child element rather than outside
  // the drop zone. Without this, dragging over a child (e.g. <h2>) fires dragleave
  // on the parent, causing the highlight to flicker.
  const handleDragLeave = (e) => {
    if (e.currentTarget.contains(e.relatedTarget)) return;
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      processFiles(e.dataTransfer.files);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      processFiles(e.target.files);
      e.target.value = '';
    }
  };

  return (
    <div className="w-full space-y-4">
      
      <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-sm space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="flex items-center space-x-2 text-slate-800 text-xs font-bold">
            <FolderTree className="w-4 h-4 text-red-600" />
            <span>Folder Organization:</span>
            <span className="text-slate-500 font-normal hidden sm:inline">Review the structure before upload starts</span>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => onOrganizationModeChange('auto')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold border flex items-center gap-1.5 ${
                organizationMode === 'auto'
                  ? 'bg-red-600 text-white border-red-600'
                  : 'bg-slate-50 text-slate-700 border-slate-300 hover:bg-slate-100'
              }`}
            >
              <Wand2 className="w-3.5 h-3.5" />
              <span>Automatic</span>
            </button>

            <button
              type="button"
              onClick={() => onOrganizationModeChange('user_defined')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold border flex items-center gap-1.5 ${
                organizationMode === 'user_defined'
                  ? 'bg-red-600 text-white border-red-600'
                  : 'bg-slate-50 text-slate-700 border-slate-300 hover:bg-slate-100'
              }`}
            >
              <FolderPlus className="w-3.5 h-3.5" />
              <span>User Folders</span>
            </button>
          </div>
        </div>

        {organizationMode !== 'user_defined' && (
          <div className="grid gap-3 md:grid-cols-2">
            <label className="space-y-1">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Fallback Category</span>
              <select
                value={selectedCategory}
                onChange={(e) => onCategoryChange(e.target.value)}
                className="w-full px-3.5 py-2 rounded-lg bg-slate-50 border border-slate-300 text-xs font-bold text-slate-900 focus:outline-none focus:border-red-500 shadow-sm"
              >
                {CATEGORY_OPTIONS.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat}
                  </option>
                ))}
              </select>
            </label>

              <label className="space-y-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Folder Levels</span>
                <select
                  value={structureLevels.join('|')}
                  onChange={(e) => onStructureLevelsChange(e.target.value.split('|'))}
                  className="w-full px-3.5 py-2 rounded-lg bg-slate-50 border border-slate-300 text-xs font-bold text-slate-900 focus:outline-none focus:border-red-500 shadow-sm"
                >
                  {STRUCTURE_PRESETS.map((preset) => (
                    <option key={preset.label} value={preset.value.join('|')}>
                      {preset.label}
                    </option>
                  ))}
                </select>
              </label>
          </div>
        )}

        {organizationMode === 'user_defined' && (
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <p className="text-xs font-extrabold text-slate-900">Imported Folder Structure</p>
                <p className="text-[11px] font-medium text-slate-500">
                  {importedFolders.length > 0 ? `${userFolderRoot} / ${importedFolders.length} folder(s)` : 'No structure imported yet'}
                </p>
              </div>
              <button
                type="button"
                onClick={importFolderStructure}
                className="px-4 py-2.5 rounded-lg bg-red-600 hover:bg-red-700 text-white text-xs font-bold inline-flex items-center justify-center gap-1.5 shadow-sm"
              >
                <FolderInput className="w-3.5 h-3.5" />
                <span>Import Folder Structure</span>
              </button>
            </div>

            {importedFolders.length > 0 && (
              <div className="max-h-64 overflow-y-auto rounded-lg bg-white border border-slate-200 p-3 font-mono text-xs text-slate-800">
                <div className="py-0.5 font-bold text-red-700">{userFolderRoot}</div>
                {structureLines.map((line) => (
                  <div key={line.path} style={{ paddingLeft: `${line.depth * 18}px` }} className="py-0.5">
                    - {line.name}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Drag and Drop Zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`relative group cursor-pointer overflow-hidden rounded-2xl border-2 border-dashed transition-all duration-300 shadow-sm ${
          isDragging
            ? 'border-red-600 bg-red-50/80 shadow-lg shadow-red-500/20 scale-[1.01]'
            : 'border-slate-300 bg-white hover:border-red-500 hover:bg-red-50/30 hover:shadow-md'
        }`}
      >
        <div className="relative p-8 md:p-12 flex flex-col items-center justify-center text-center">
          
          {/* Icon Emblem */}
          <div className="mb-4 relative">
            <div className={`w-20 h-20 rounded-2xl flex items-center justify-center transition-all duration-300 ${
              isDragging
                ? 'bg-red-600 text-white shadow-lg shadow-red-600/40 scale-110'
                : 'bg-red-50 text-red-600 group-hover:bg-red-600 group-hover:text-white border border-red-200 group-hover:border-red-600 shadow-sm'
            }`}>
              <UploadCloud className="w-10 h-10" />
            </div>
            <div className="absolute -bottom-1 -right-1 w-7 h-7 rounded-full bg-white border border-slate-300 flex items-center justify-center text-red-600 shadow-sm">
              <Layers className="w-4 h-4" />
            </div>
          </div>

          {/* Heading */}
          <h2 className="text-xl md:text-2xl font-extrabold text-slate-900 tracking-tight">
            Drop your documents here or <span className="text-red-600 group-hover:underline">Browse</span>
          </h2>

          <p className="mt-2 text-sm text-slate-600 max-w-md font-medium">
            Bulk upload support for <strong className="text-slate-900">hundreds or thousands</strong> of files with <strong className="text-red-600">{organizationMode}</strong> folder planning.
          </p>

          {/* Action Buttons */}
          <div className="mt-6 flex flex-wrap gap-3 justify-center items-center">
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="px-6 py-2.5 rounded-xl bg-red-600 hover:bg-red-700 text-white font-bold text-sm shadow-md shadow-red-600/30 hover:shadow-lg hover:shadow-red-600/40 transition-all transform hover:-translate-y-0.5 flex items-center space-x-2"
            >
              <FileCheck className="w-4 h-4" />
              <span>Select Files</span>
            </button>

            <button
              type="button"
              onClick={() => folderInputRef.current?.click()}
              className="px-6 py-2.5 rounded-xl bg-white hover:bg-slate-50 text-slate-800 font-bold text-sm border border-slate-300 shadow-sm hover:border-slate-400 transition-all transform hover:-translate-y-0.5 flex items-center space-x-2"
            >
              <Layers className="w-4 h-4 text-red-600" />
              <span>Upload Folder</span>
            </button>
          </div>

          {/* Supported Format Badges */}
          <div className="mt-6 pt-6 border-t border-slate-200 w-full max-w-lg">
            <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Supported Document Formats</p>
            <div className="flex flex-wrap gap-1.5 justify-center">
              {['PDF', 'JPG', 'PNG', 'DOCX', 'XLSX', 'TXT', 'CSV', 'ZIP', 'RAR', 'JAR', 'CER', 'LOG'].map((ext) => (
                <span
                  key={ext}
                  className="px-2.5 py-1 rounded-md text-[11px] font-bold bg-slate-100 text-slate-700 border border-slate-200"
                >
                  {ext}
                </span>
              ))}
            </div>
          </div>

          {/* Hidden File Inputs */}
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.jpg,.jpeg,.png,.tiff,.tif,.docx,.doc,.xlsx,.xls,.txt,.csv,.zip,.rar,.jar,.cer,.csi,.log,.bat"
            onChange={handleFileChange}
            className="hidden"
          />
          <input
            ref={folderInputRef}
            type="file"
            webkitdirectory="true"
            directory="true"
            multiple
            onChange={handleFileChange}
            className="hidden"
          />

        </div>
      </div>

      {/* Warning/Error notification banner */}
      {errorMessage && (
        <div className="mt-4 p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 text-xs flex items-start space-x-3 font-medium">
          <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
          <span>{errorMessage}</span>
        </div>
      )}
    </div>
  );
}
