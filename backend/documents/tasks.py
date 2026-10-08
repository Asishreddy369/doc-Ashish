from celery import shared_task
from .models import Document


# BUG-B10 FIX: Added acks_late=True for at-least-once delivery and proper self.retry()
# call so that max_retries=3 is actually honoured (without self.retry the retries never fire).
@shared_task(bind=True, max_retries=3, acks_late=True)
def process_document_task(self, doc_id):
    from .processing import process_document_extraction

    try:
        doc = process_document_extraction(doc_id)
        return f"Successfully processed {doc.original_name}. Status: {doc.status}"
    except Document.DoesNotExist:
        return f"Document {doc_id} not found."
    except Exception as exc:
        # Retry with 60-second delay; re-raise final failure for Celery to log.
        raise self.retry(exc=exc, countdown=60)
