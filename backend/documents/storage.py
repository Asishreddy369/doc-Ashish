import os
import shutil
import time
import gc

from django.core.files.storage import default_storage
from django.conf import settings

from .folder_planner import sanitize_folder_name

def get_document_storage():
    """
    Returns the configured default storage engine.
    For local development, defaults to FileSystemStorage pointing to MEDIA_ROOT.
    For cloud deployment (e.g., AWS S3), configure DEFAULT_FILE_STORAGE or STORAGES in settings.py.
    """
    return default_storage


def route_document_file(document):
    """
    Move a local document file into its company/category folder and update FileField path.

    NOTE: This function updates document.file.name in memory but does NOT call document.save().
    Callers are responsible for persisting the updated file path to the database.
    """
    if not document.file or not hasattr(document.file, "path"):
        return document

    category = document.category or "Unclassified"
    organization_path = document.organization_path

    if document.batch_id and not str(document.batch_id).startswith("batch_"):
        root_parts = ["company_documents", sanitize_folder_name(document.batch_id, "Company Documents")]
    else:
        root_parts = ["company_documents"]

    if organization_path:
        route_parts = [
            sanitize_folder_name(part)
            for part in str(organization_path).replace("\\", "/").split("/")
            if str(part).strip()
        ]
    else:
        route_parts = [sanitize_folder_name(category, "Unclassified")]

    db_path_parts = root_parts + route_parts
    target_dir = os.path.join(settings.MEDIA_ROOT, *db_path_parts)
    # BUG-B02 FIX: Use forward slashes for the DB/URL path to avoid Windows backslash
    # in file.name which breaks browser URL generation.
    db_path_prefix = "/".join(db_path_parts)

    os.makedirs(target_dir, exist_ok=True)
    filename = os.path.basename(document.file.name)
    target_path = os.path.join(target_dir, filename)

    if os.path.abspath(document.file.path) != os.path.abspath(target_path):
        source_path = document.file.path
        try:
            document.file.close()
        except Exception:
            pass
        last_error = None
        for _attempt in range(6):
            try:
                shutil.move(source_path, target_path)
                last_error = None
                break
            except PermissionError as exc:
                last_error = exc
                gc.collect()
                time.sleep(0.25)
        if last_error is not None:
            shutil.copy2(source_path, target_path)
            try:
                os.remove(source_path)
            except OSError:
                pass
        document.file.name = f"{db_path_prefix}/{filename}"

    return document
