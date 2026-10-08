import os
import requests
import glob
import time

TARGET_DIR = 'sample_docs'
API_URL = 'http://127.0.0.1:8000/api/documents/upload/'
BATCH_SIZE = 50

# Ensure files exist
files = glob.glob(os.path.join(TARGET_DIR, '*.txt'))
if not files:
    print(f"No files found in {TARGET_DIR}. Run generate_test_docs.py first.")
    exit(1)

print(f"Found {len(files)} files. Starting load test...")

start_time = time.time()
uploaded = 0

for i in range(0, len(files), BATCH_SIZE):
    batch = files[i:i+BATCH_SIZE]
    
    # Prepare files for multipart/form-data upload
    files_to_upload = [
        ('files', (os.path.basename(f), open(f, 'rb'), 'text/plain'))
        for f in batch
    ]
    
    try:
        response = requests.post(API_URL, files=files_to_upload)
        if response.status_code == 200:
            uploaded += len(batch)
            print(f"Uploaded {uploaded}/{len(files)} documents...")
        else:
            print(f"Error uploading batch: {response.text}")
    except Exception as e:
        print(f"Exception during upload: {e}")
        
    # Close file handles
    for _, (name, f_obj, _) in files_to_upload:
        f_obj.close()

end_time = time.time()
print(f"Load test complete! Uploaded {uploaded} documents in {end_time - start_time:.2f} seconds.")
