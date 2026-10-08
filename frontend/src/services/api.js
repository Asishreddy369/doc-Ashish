import axios from 'axios';

const API = axios.create({
  baseURL: '/api/documents',
  timeout: 120000, // 2 min timeout for OCR processing
});

// BUG-F01 FIX: Global response error interceptor so callers don't have to
// each duplicate `err.response?.data?.error || err.message` handling.
API.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error.response?.data?.error ||
      error.response?.data?.detail ||
      error.message ||
      'Unknown error';
    error.userMessage = message;
    return Promise.reject(error);
  }
);

export const fetchDocuments = async (params = {}) => {
  const response = await API.get('/', { params });
  return response.data;
};

export const fetchDocumentDetailApi = async (id) => {
  const response = await API.get(`/${id}/`);
  return response.data;
};

export const fetchDocumentStats = async () => {
  const response = await API.get('/stats/');
  return response.data;
};

export const deleteDocumentApi = async (id) => {
  const response = await API.delete(`/${id}/`);
  return response.data;
};

export const batchDeleteApi = async (batchId, category = null) => {
  const params = {};
  if (batchId) {
    params.batch_id = batchId;
  }
  if (category) {
    params.category = category;
  }
  const response = await API.delete('/batch-delete/', { params });
  return response.data;
};

export const updateDocumentCategoryApi = async (id, category) => {
  const response = await API.patch(`/${id}/`, { category });
  return response.data;
};

// BUG-F14 FIX: Removed dead updateDocumentStatusApi (defined but never imported anywhere).

export const extractDocumentTextApi = async (id) => {
  const response = await API.post(`/${id}/extract-text/`);
  return response.data;
};

export const extractAllTextApi = async () => {
  const response = await API.post('/extract-text-all/');
  return response.data;
};

export const fetchFolderPlanApi = async (payload) => {
  const response = await API.post('/folder-plan/', payload);
  return response.data;
};

export const uploadSingleFileApi = async (
  file,
  batchId,
  category = 'Unclassified',
  onProgress,
  organization = {}
) => {
  const formData = new FormData();
  formData.append('files', file);
  if (batchId) {
    formData.append('batch_id', batchId);
  }
  if (category) {
    formData.append('category', category);
  }
  if (organization.relativePath) {
    formData.append('relative_path', organization.relativePath);
  }
  if (organization.mode) {
    formData.append('organization_mode', organization.mode);
  }
  if (organization.structureLevels) {
    formData.append('structure_levels', JSON.stringify(organization.structureLevels));
  }
  if (organization.categoryMap) {
    formData.append('category_map', JSON.stringify(organization.categoryMap));
  }
  if (organization.folderOptions) {
    formData.append('folder_options', JSON.stringify(organization.folderOptions));
  }

  // BUG-F01 FIX: Do NOT set Content-Type manually.
  // Axios auto-sets "multipart/form-data; boundary=..." when passing FormData —
  // manually overriding it strips the boundary, breaking server-side multipart parsing.
  const response = await API.post('/upload/', formData, {
    onUploadProgress: (progressEvent) => {
      if (progressEvent.total) {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        if (onProgress) onProgress(percentCompleted, progressEvent.loaded);
      }
    },
  });

  return response.data;
};

export default API;
