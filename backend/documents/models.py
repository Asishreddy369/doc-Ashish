import uuid
import os
from django.db import models

class Document(models.Model):
    CATEGORY_CHOICES = [
        ('Aadhaar', 'Aadhaar'),
        ('PAN', 'PAN'),
        ('GST Certificate', 'GST Certificate'),
        ('Invoice', 'Invoice'),
        ('Proforma Invoice', 'Proforma Invoice'),
        ('Purchase Order', 'Purchase Order'),
        ('Bank Statement', 'Bank Statement'),
        ('Agreement', 'Agreement'),
        ('Board Resolution', 'Board Resolution'),
        ('Meeting Minutes', 'Meeting Minutes'),
        ('Offer Letter', 'Offer Letter'),
        ('Cap Table', 'Cap Table'),
        ('Reconciliation', 'Reconciliation'),
        ('Tax Filing', 'Tax Filing'),
        ('Digital Certificate', 'Digital Certificate'),
        ('Technical Resource', 'Technical Resource'),
        ('Archive', 'Archive'),
        ('Other', 'Other'),
        ('Unclassified', 'Unclassified'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('NEEDS_REVIEW', 'Needs Review'),
    ]

    ALLOWED_EXTENSIONS = {
        'pdf', 'jpg', 'jpeg', 'png', 'tiff', 'tif', 'docx', 'doc', 
        'xlsx', 'xls', 'txt', 'csv', 'zip', 'rar', 'jar', 'cer', 
        'csi', 'log', 'bat'
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    original_name = models.CharField(max_length=512, db_index=True)
    file_type = models.CharField(max_length=50)
    file_size = models.BigIntegerField(help_text="File size in bytes")
    file = models.FileField(upload_to='uploads/%Y/%m/%d/', max_length=1000)
    
    category = models.CharField(
        max_length=150,
        default='Unclassified',
        db_index=True
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        db_index=True
    )

    extracted_text = models.TextField(blank=True, null=True, help_text="OCR or parsed text content")
    key_fields = models.JSONField(default=dict, blank=True, null=True, help_text="Structured extracted key-value pairs")
    matched_rule = models.CharField(max_length=100, blank=True, null=True, help_text="ID of the classification rule matched")
    classification_confidence = models.FloatField(default=0.0, help_text="Classifier confidence from 0.0 to 1.0")
    classifier_source = models.CharField(max_length=50, blank=True, null=True, help_text="rule, ml, ml_low_confidence, or none")
    classifier_details = models.JSONField(default=dict, blank=True, null=True, help_text="Model alternatives and diagnostics")
    document_year = models.PositiveSmallIntegerField(blank=True, null=True, db_index=True)
    document_month = models.PositiveSmallIntegerField(blank=True, null=True, db_index=True)
    organization_path = models.CharField(max_length=700, blank=True, null=True, db_index=True)
    original_relative_path = models.CharField(max_length=700, blank=True, null=True)
    folder_structure = models.JSONField(default=dict, blank=True, null=True, help_text="Folder organization mode, levels, and route diagnostics")

    checksum = models.CharField(max_length=64, blank=True, null=True, help_text="SHA256 checksum of document content")
    batch_id = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    error_info = models.TextField(blank=True, null=True, help_text="Diagnostic failure logs or error message")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    processed_at = models.DateTimeField(blank=True, null=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['original_name']),
            models.Index(fields=['category']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['processed_at']),
            models.Index(fields=['batch_id']),
            models.Index(fields=['file_type']),
        ]

    def __str__(self):
        return f"{self.original_name} [{self.category}] ({self.id})"

    @property
    def formatted_size(self):
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
