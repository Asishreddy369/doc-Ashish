import sys

with open('doc_management/settings.py', 'r') as f:
    content = f.read()

# Find the second occurrence of '"""' which starts the duplicated django settings header
idx = content.find('"""', 10)

if idx != -1:
    new_content = content[:idx] + '''
# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Celery Configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
'''
    with open('doc_management/settings.py', 'w') as f:
        f.write(new_content)
    print("Fixed settings.py")
else:
    print("Could not find the duplicate string")
