import os
import django
import multiprocessing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'doc_management.settings')
django.setup()

from documents.models import Document
from documents.tasks import process_document_task
from django.db import connection

def process_doc(doc_id):
    try:
        connection.close()
        process_document_task(doc_id)
        return True
    except Exception as e:
        print(f"Error on {doc_id}: {e}")
        return False

if __name__ == '__main__':
    # Reset PROCESSING to PENDING
    Document.objects.filter(status='PROCESSING').update(status='PENDING')
    
    docs = list(Document.objects.filter(status='PENDING').values_list('id', flat=True))
    print(f"Processing {len(docs)} documents...")
    
    cores = max(1, multiprocessing.cpu_count() - 1)
    with multiprocessing.Pool(cores) as pool:
        for i, _ in enumerate(pool.imap_unordered(process_doc, docs), 1):
            if i % 50 == 0:
                print(f"Done {i}/{len(docs)}")
    
    print("All done!")
