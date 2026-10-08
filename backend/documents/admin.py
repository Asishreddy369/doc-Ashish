from django.contrib import admin
from .models import Document


# BUG-B11 FIX: Register Document model with admin so it can be browsed and managed
# via Django's built-in admin interface at /admin/.
@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = [
        'original_name', 'category', 'status', 'file_type',
        'formatted_size', 'batch_id', 'created_at'
    ]
    list_filter = ['category', 'status', 'file_type']
    search_fields = ['original_name', 'batch_id', 'extracted_text']
    readonly_fields = ['id', 'checksum', 'created_at', 'updated_at', 'formatted_size', 'file_url']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'

    fieldsets = [
        ('File Info', {
            'fields': ['id', 'original_name', 'file', 'file_type', 'file_size', 'formatted_size', 'checksum']
        }),
        ('Classification', {
            'fields': ['category', 'status', 'matched_rule', 'classification_confidence',
                       'classifier_source', 'classifier_details']
        }),
        ('Organization', {
            'fields': ['batch_id', 'organization_path', 'original_relative_path', 'folder_structure',
                       'document_year', 'document_month']
        }),
        ('Extracted Content', {
            'fields': ['extracted_text', 'key_fields'],
            'classes': ['collapse']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at', 'processed_at', 'error_info']
        }),
    ]

    def file_url(self, obj):
        """URL of the stored file for admin display."""
        try:
            return obj.file.url
        except Exception:
            return '—'
    file_url.short_description = 'File URL'
