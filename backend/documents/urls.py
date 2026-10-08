from django.urls import path
from .views import (
    DocumentUploadView,
    DocumentListView,
    DocumentDetailView,
    DocumentStatusUpdateView,
    DocumentExtractTextView,
    BulkDocumentExtractTextView,
    BulkDocumentReclassifyView,
    DocumentStatsView,
    BatchDeleteView,
    FolderPlanView,
)

urlpatterns = [
    path('upload/', DocumentUploadView.as_view(), name='document-upload'),
    path('batch-delete/', BatchDeleteView.as_view(), name='document-batch-delete'),
    path('', DocumentListView.as_view(), name='document-list'),
    path('stats/', DocumentStatsView.as_view(), name='document-stats'),
    path('folder-plan/', FolderPlanView.as_view(), name='document-folder-plan'),
    path('extract-text-all/', BulkDocumentExtractTextView.as_view(), name='document-extract-text-all'),
    path('reclassify/', BulkDocumentReclassifyView.as_view(), name='document-reclassify'),
    path('<uuid:doc_id>/', DocumentDetailView.as_view(), name='document-detail'),
    path('<uuid:doc_id>/status/', DocumentStatusUpdateView.as_view(), name='document-status-update'),
    path('<uuid:doc_id>/extract-text/', DocumentExtractTextView.as_view(), name='document-extract-text'),
]
