# Folder Structure Workflow

The upload flow supports two organization modes.

## Automatic Mode

The user selects files or uploads a folder. Before uploading begins, the frontend sends file metadata to:

```text
POST /api/documents/folder-plan/
```

The backend suggests a folder tree using filename/path signals such as document type, year, and month. After the user approves, each file is uploaded with:

- `relative_path`
- `organization_mode`
- `structure_levels`
- `category_map`

During processing, the backend re-plans the route using extracted text and the final classifier category, then stores the file under `organization_path`.

## Custom Mode

The user can choose the folder level order before upload, for example:

- `category -> year -> month`
- `year -> month -> category`
- `category`
- `original_folder -> category -> year`

The user can also provide preferred category labels. Common classifier outputs such as `Accounts and Bank Related Documents`, `Tax`, and `GST Certificate` are mapped to cleaner folders such as `Bank Statements`, `Tax Documents`, and `GST`.

## Stored Metadata

Each document stores:

- `document_year`
- `document_month`
- `organization_path`
- `original_relative_path`
- `folder_structure`

The file explorer uses `organization_path` to show nested folders such as:

```text
Yanvior Technologies/
  Bank Statements/
    2026/
      April/
```
