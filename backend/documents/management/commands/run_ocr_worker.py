import time
import multiprocessing
import django
import os
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.models import Q

def init_worker():
    """
    Initialize the Django environment for the worker process.
    """
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'doc_management.settings')
    django.setup()

def process_document(doc_id):
    """
    Worker function to process a single document.
    """
    from documents.tasks import process_document_task
    try:
        from django.db import connection
        connection.close()
        process_document_task(doc_id)
        return doc_id, True
    except Exception as e:
        print(f"Worker Error on {doc_id}: {str(e)}")
        return doc_id, False

class Command(BaseCommand):
    help = 'Runs a high-performance multiprocessing worker to process PENDING OCR documents.'

    def handle(self, *args, **options):
        # Use all available CPU cores, or leave 1 core free for the web server
        num_cores = max(1, multiprocessing.cpu_count() - 1)
        self.stdout.write(self.style.SUCCESS(f'Starting High-Performance OCR Worker on {num_cores} cores...'))
        self.stdout.write(self.style.WARNING('Press Ctrl+C to stop.'))

        pool = multiprocessing.Pool(processes=num_cores, initializer=init_worker)

        try:
            while True:
                # Ensure the main thread's DB connection is fresh
                connection.close()
                
                from documents.models import Document
                # Fetch pending documents. Fetch exactly num_cores * 2 to keep the queue fed
                pending_ids = list(
                    Document.objects.filter(
                        Q(status='PENDING') |
                        Q(status='PROCESSING', extracted_text__isnull=True) |
                        Q(status='PROCESSING', extracted_text='')
                    ).values_list('id', flat=True)[:num_cores * 2]
                )

                if not pending_ids:
                    time.sleep(2)
                    continue

                self.stdout.write(f'Dispatched {len(pending_ids)} documents to the worker pool...')
                
                # We use map to block until the chunk is done. 
                # This prevents us from fetching the same PENDING docs again.
                # In a real app we'd mark them as PROCESSING first, but this is a simple local worker.
                
                # Mark as PROCESSING to avoid fetching them again if we change the loop
                Document.objects.filter(id__in=pending_ids).update(status='PROCESSING')
                
                results = pool.map(process_document, pending_ids)
                
                success_count = sum(1 for r in results if r[1])
                self.stdout.write(self.style.SUCCESS(f'Processed {success_count}/{len(results)} successfully.'))

        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\nWorker stopping gracefully...'))
            pool.terminate()
            pool.join()
