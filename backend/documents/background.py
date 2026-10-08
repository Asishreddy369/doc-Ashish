import atexit
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from django.conf import settings
from django.db import close_old_connections


def _default_worker_count():
    cpu_count = os.cpu_count() or 4
    return max(1, min(cpu_count, 7))


_executor = ThreadPoolExecutor(
    max_workers=int(os.environ.get("DOC_EXTRACT_MAX_WORKERS", _default_worker_count())),
    thread_name_prefix="doc-extract",
)
# BUG-B03 FIX: Register graceful shutdown so the executor is cleaned up on
# Django dev-server reload instead of leaking threads with stale DB connections.
atexit.register(_executor.shutdown, wait=False)

_queued = set()
_queue_lock = Lock()


def _run_extraction(document_id):
    # BUG-B03 FIX: Catch all exceptions so that failed extractions surface
    # the error on the Document record instead of being silently swallowed.
    try:
        close_old_connections()
        from .processing import process_document_extraction

        process_document_extraction(document_id)
    except Exception as exc:  # noqa: BLE001
        # Mark the document as FAILED so it doesn't get stuck in PROCESSING.
        try:
            from .models import Document
            Document.objects.filter(id=document_id).update(
                status="FAILED",
                error_info=f"Background extraction error: {exc}",
            )
        except Exception:  # noqa: BLE001
            pass
    finally:
        with _queue_lock:
            _queued.discard(str(document_id))
        close_old_connections()


def queue_extraction(document_id):
    if not getattr(settings, "DOCVAULT_BACKGROUND_EXTRACTION", True):
        return False

    document_id = str(document_id)
    with _queue_lock:
        if document_id in _queued:
            return False
        _queued.add(document_id)
    _executor.submit(_run_extraction, document_id)
    return True
