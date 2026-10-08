from rest_framework import serializers
from .models import Document

class DocumentSerializer(serializers.ModelSerializer):
    formatted_size = serializers.ReadOnlyField()
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            'id',
            'original_name',
            'file_type',
            'file_size',
            'formatted_size',
            'file',
            'file_url',
            'category',
            'status',
            'extracted_text',
            'key_fields',
            'matched_rule',
            'classification_confidence',
            'classifier_source',
            'classifier_details',
            'document_year',
            'document_month',
            'organization_path',
            'original_relative_path',
            'folder_structure',
            'checksum',
            'batch_id',
            'error_info',
            'created_at',
            'processed_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'formatted_size', 'file_url']

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file:
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None


class DocumentListSerializer(DocumentSerializer):
    has_extracted_text = serializers.SerializerMethodField()

    class Meta(DocumentSerializer.Meta):
        fields = [
            'id',
            'original_name',
            'file_type',
            'file_size',
            'formatted_size',
            'file_url',
            'category',
            'status',
            'has_extracted_text',
            'document_year',
            'document_month',
            'organization_path',
            'folder_structure',
            'batch_id',
            'created_at',
        ]

    def get_has_extracted_text(self, obj):
        return bool(obj.extracted_text)
