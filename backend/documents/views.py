import hashlib
import json
import os
import uuid
from django.utils import timezone
from django.db.models import Sum, Count, Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Document
from .serializers import DocumentListSerializer, DocumentSerializer
from .folder_planner import build_folder_plan, plan_document_route
from .background import queue_extraction
from .processing import (
    mark_content_processing_queued,
    process_document_extraction,
    quick_classify_and_route,
)


def parse_json_field(value, default):
    if value in (None, ''):
        return default
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default

class DocumentUploadView(APIView):
    """
    Upload documents with category tagging, structured file storage, and instant text extraction / OCR.
    """
    def post(self, request, *args, **kwargs):
        files = request.FILES.getlist('files')
        if not files and 'file' in request.FILES:
            files = [request.FILES['file']]

        if not files:
            return Response(
                {"error": "No files provided. Send files under form key 'files' or 'file'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        category = request.data.get('category', 'Unclassified')
        organization_mode = request.data.get('organization_mode', 'auto')
        structure_levels = parse_json_field(request.data.get('structure_levels'), ['category', 'year', 'month'])
        category_map = parse_json_field(request.data.get('category_map'), {})
        folder_options = parse_json_field(request.data.get('folder_options'), {})

        batch_id = request.data.get('batch_id', str(uuid.uuid4()))
        created_documents = []
        errors = []

        allowed_extensions = Document.ALLOWED_EXTENSIONS

        for file_obj in files:
            orig_name = file_obj.name
            ext = orig_name.split('.')[-1].lower() if '.' in orig_name else ''

            if ext not in allowed_extensions:
                errors.append({
                    "file": orig_name,
                    "error": f"Unsupported file type .{ext}. Allowed: {', '.join(sorted(allowed_extensions))}"
                })
                continue

            try:
                original_relative_path = request.data.get('relative_path', '')

                # Compute SHA256 checksum
                sha256_hash = hashlib.sha256()
                for chunk in file_obj.chunks():
                    sha256_hash.update(chunk)
                checksum = sha256_hash.hexdigest()
                if hasattr(file_obj, 'seek'):
                    file_obj.seek(0)

                # Generate clean filename with UUID prefix
                doc_uuid = uuid.uuid4()
                safe_name = f"{doc_uuid}_{orig_name}"
                file_obj.name = safe_name

                doc = Document.objects.create(
                    id=doc_uuid,
                    original_name=orig_name,
                    file_type=ext,
                    file_size=file_obj.size,
                    file=file_obj,
                    category=category,
                    status='PROCESSING',
                    checksum=checksum,
                    batch_id=batch_id,
                    original_relative_path=original_relative_path
                )

                # BUG-B08 FIX: folder_structure must be persisted BEFORE the background
                # worker starts, otherwise the worker reads an empty folder_structure
                # and routes to "Unclassified" regardless of upload settings.
                doc.folder_structure = {
                    "mode": organization_mode,
                    "levels": structure_levels,
                    "category_map": category_map,
                    "folder_options": folder_options,
                }
                doc.save(update_fields=["folder_structure", "updated_at"])

                # Industry/content-first path: do not classify from filename/path.
                # The worker extracts document content first, then classifies,
                # extracts fields, and routes into the selected folder structure.
                mark_content_processing_queued(doc)
                queue_extraction(doc.id)

                created_documents.append(doc)

            except Exception as e:
                errors.append({
                    "file": orig_name,
                    "error": str(e)
                })

        serializer = DocumentSerializer(created_documents, many=True, context={'request': request})
        
        return Response({
            "message": f"Successfully uploaded and processed {len(created_documents)} file(s).",
            "batch_id": batch_id,
            "category": category,
            "documents": serializer.data,
            "errors": errors
        }, status=status.HTTP_201_CREATED if created_documents else status.HTTP_400_BAD_REQUEST)


class DocumentListView(APIView):
    """
    Search & Filter uploaded documents.
    """
    def get(self, request, *args, **kwargs):
        queryset = Document.objects.all()

        category = request.query_params.get('category')
        if category and category.upper() != 'ALL':
            queryset = queryset.filter(category__iexact=category)

        status_param = request.query_params.get('status')
        if status_param and status_param.upper() != 'ALL':
            queryset = queryset.filter(status__iexact=status_param)

        file_type = request.query_params.get('file_type')
        if file_type:
            queryset = queryset.filter(file_type__iexact=file_type)

        batch_id = request.query_params.get('batch_id')
        if batch_id:
            queryset = queryset.filter(batch_id=batch_id)

        organization_path = request.query_params.get('organization_path')
        if organization_path:
            queryset = queryset.filter(organization_path__icontains=organization_path)

        document_year = request.query_params.get('document_year')
        if document_year:
            queryset = queryset.filter(document_year=document_year)

        document_month = request.query_params.get('document_month')
        if document_month:
            queryset = queryset.filter(document_month=document_month)

        date_from = request.query_params.get('date_from')
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)

        date_to = request.query_params.get('date_to')
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)

        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(original_name__icontains=search) |
                Q(id__icontains=search) |
                Q(extracted_text__icontains=search) |
                Q(category__icontains=search)
            )

        serializer = DocumentListSerializer(queryset, many=True, context={'request': request})
        # BUG-B06 FIX: Use len(serializer.data) to avoid a second DB query from queryset.count()
        return Response({
            "count": len(serializer.data),
            "documents": serializer.data
        })


class DocumentDetailView(APIView):
    """
    Retrieve document details, update category/metadata, or delete document.
    """
    def get(self, request, doc_id, *args, **kwargs):
        try:
            doc = Document.objects.get(id=doc_id)
            serializer = DocumentSerializer(doc, context={'request': request})
            return Response(serializer.data)
        except Document.DoesNotExist:
            return Response({"error": "Document not found"}, status=status.HTTP_404_NOT_FOUND)

    def patch(self, request, doc_id, *args, **kwargs):
        try:
            doc = Document.objects.get(id=doc_id)
            serializer = DocumentSerializer(doc, data=request.data, partial=True, context={'request': request})
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Document.DoesNotExist:
            return Response({"error": "Document not found"}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, doc_id, *args, **kwargs):
        try:
            doc = Document.objects.get(id=doc_id)
            if doc.file and os.path.isfile(doc.file.path):
                try:
                    os.remove(doc.file.path)
                except Exception:
                    pass
            doc.delete()
            return Response({"message": "Document deleted successfully"}, status=status.HTTP_200_OK)
        except Document.DoesNotExist:
            return Response({"error": "Document not found"}, status=status.HTTP_404_NOT_FOUND)

class BatchDeleteView(APIView):
    """
    Delete all documents matching a batch_id and optionally a category.
    """
    def delete(self, request, *args, **kwargs):
        batch_id = request.query_params.get('batch_id')
        category = request.query_params.get('category')
        
        if not batch_id and not category:
            return Response({"error": "batch_id or category is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        queryset = Document.objects.all()
        if batch_id:
            queryset = queryset.filter(batch_id=batch_id)
        if category:
            queryset = queryset.filter(category=category)
            
        count = queryset.count()
        
        for doc in queryset:
            if doc.file and os.path.isfile(doc.file.path):
                try:
                    os.remove(doc.file.path)
                except Exception:
                    pass
        
        queryset.delete()
        
        return Response({
            "message": f"Successfully deleted {count} document(s)",
            "deleted_count": count
        }, status=status.HTTP_200_OK)


class DocumentExtractTextView(APIView):
    """
    Explicit API endpoint to re-run text extraction & OCR on a single document.
    """
    def post(self, request, doc_id, *args, **kwargs):
        try:
            doc = Document.objects.get(id=doc_id)
            doc.status = 'PROCESSING'
            doc.save(update_fields=['status', 'updated_at'])
            doc = process_document_extraction(doc.id)

            serializer = DocumentSerializer(doc, context={'request': request})
            return Response({
                "message": "Text extraction completed successfully.",
                "document": serializer.data
            })
        except Document.DoesNotExist:
            return Response({"error": "Document not found"}, status=status.HTTP_404_NOT_FOUND)


class BulkDocumentExtractTextView(APIView):
    """
    Explicit API endpoint to run batch text extraction & OCR on all documents lacking text.
    """
    def post(self, request, *args, **kwargs):
        docs = Document.objects.filter(Q(extracted_text__isnull=True) | Q(extracted_text='') | Q(status='FAILED')).distinct()
        queued_count = 0
        pending_worker_count = 0

        for doc in docs:
            details = doc.classifier_details or {}
            details["extraction_status"] = "queued"
            doc.classifier_details = details
            doc.status = 'PENDING'
            doc.error_info = None
            doc.save(update_fields=['classifier_details', 'status', 'error_info', 'updated_at'])
            if queue_extraction(doc.id):
                doc.status = 'PROCESSING'
                doc.save(update_fields=['status', 'updated_at'])
                queued_count += 1
            else:
                pending_worker_count += 1

        return Response({
            "message": f"Queued {queued_count} document(s) for background extraction. {pending_worker_count} document(s) are ready for the OCR worker.",
            "matched": docs.count(),
            "queued": queued_count,
            "pending_worker": pending_worker_count,
        })


class BulkDocumentReclassifyView(APIView):
    """
    Re-run the fast classifier and routing on existing documents without re-uploading.
    """
    def post(self, request, *args, **kwargs):
        batch_id = request.data.get('batch_id')
        use_existing_text = bool(request.data.get('use_existing_text', True))
        force = bool(request.data.get('force', False))

        queryset = Document.objects.all()
        if batch_id:
            queryset = queryset.filter(batch_id=batch_id)

        updated = 0
        errors = []
        for doc in queryset.iterator():
            try:
                quick_classify_and_route(
                    doc,
                    use_existing_text=use_existing_text,
                    force=force,
                    mark_extraction_queued=False,
                )
                updated += 1
            except Exception as exc:
                errors.append({
                    "id": str(doc.id),
                    "file": doc.original_name,
                    "error": str(exc),
                })

        return Response({
            "message": f"Reclassified {updated} document(s).",
            "updated": updated,
            "errors": errors[:25],
            "error_count": len(errors),
        })


class DocumentStatusUpdateView(APIView):
    """
    Update document processing status, OCR text, key fields, and error logs.
    """
    def patch(self, request, doc_id, *args, **kwargs):
        try:
            doc = Document.objects.get(id=doc_id)
            
            new_status = request.data.get('status')
            if new_status:
                if new_status not in dict(Document.STATUS_CHOICES):
                    return Response({"error": f"Invalid status '{new_status}'"}, status=status.HTTP_400_BAD_REQUEST)
                doc.status = new_status
                if new_status in ['COMPLETED', 'FAILED']:
                    doc.processed_at = timezone.now()

            if 'extracted_text' in request.data:
                doc.extracted_text = request.data['extracted_text']

            if 'key_fields' in request.data:
                doc.key_fields = request.data['key_fields']

            if 'error_info' in request.data:
                doc.error_info = request.data['error_info']

            if 'category' in request.data:
                doc.category = request.data['category']

            if 'organization_path' in request.data:
                doc.organization_path = request.data['organization_path']

            if 'document_year' in request.data:
                doc.document_year = request.data['document_year'] or None

            if 'document_month' in request.data:
                doc.document_month = request.data['document_month'] or None

            doc.save()
            serializer = DocumentSerializer(doc, context={'request': request})
            return Response(serializer.data)

        except Document.DoesNotExist:
            return Response({"error": "Document not found"}, status=status.HTTP_404_NOT_FOUND)


class DocumentStatsView(APIView):
    """
    Summary metrics dashboard.
    """
    def get(self, request, *args, **kwargs):
        total_count = Document.objects.count()
        total_size = Document.objects.aggregate(total=Sum('file_size'))['total'] or 0

        type_breakdown = Document.objects.values('file_type').annotate(count=Count('id')).order_by('-count')
        category_breakdown = Document.objects.values('category').annotate(count=Count('id')).order_by('-count')
        status_breakdown = Document.objects.values('status').annotate(count=Count('id')).order_by('-count')

        size = total_size
        formatted_total = "0 B"
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                formatted_total = f"{size:.1f} {unit}"
                break
            size /= 1024.0

        # Calculate processing speed (documents processed in the last 10 minutes)
        from datetime import timedelta
        ten_mins_ago = timezone.now() - timedelta(minutes=10)
        recent_processed = Document.objects.filter(processed_at__gte=ten_mins_ago).count()
        docs_per_minute = round(recent_processed / 10, 2)

        existing_categories = Document.objects.values_list('category', flat=True).distinct()
        all_categories = list(set([c[0] for c in Document.CATEGORY_CHOICES] + list(existing_categories)))

        return Response({
            "total_documents": total_count,
            "total_bytes": total_size,
            "formatted_total_size": formatted_total,
            "type_breakdown": type_breakdown,
            "category_breakdown": category_breakdown,
            "status_breakdown": status_breakdown,
            "processing_speed_dpm": docs_per_minute,
            "available_categories": all_categories
        })


class FolderPlanView(APIView):
    """
    Build a reviewable folder structure before upload, or from an existing batch.
    """
    def post(self, request, *args, **kwargs):
        mode = request.data.get('mode', 'auto')
        structure_levels = request.data.get('structure_levels') or ['category', 'year', 'month']
        category_map = request.data.get('category_map') or {}
        folder_options = request.data.get('folder_options') or {}
        batch_id = request.data.get('batch_id')

        if isinstance(structure_levels, str):
            structure_levels = parse_json_field(structure_levels, ['category', 'year', 'month'])
        if isinstance(category_map, str):
            category_map = parse_json_field(category_map, {})
        if isinstance(folder_options, str):
            folder_options = parse_json_field(folder_options, {})

        if batch_id:
            documents = Document.objects.filter(batch_id=batch_id)
            items = [
                {
                    "name": doc.original_name,
                    "relative_path": doc.original_relative_path,
                    "category": doc.category,
                    "text": doc.extracted_text,
                    "year": doc.document_year,
                    "month": doc.document_month,
                }
                for doc in documents
            ]
        else:
            items = request.data.get('documents') or []

        if not isinstance(items, list):
            return Response(
                {"error": "documents must be a list of file metadata objects."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        plan = build_folder_plan(
            items,
            mode=mode,
            structure_levels=structure_levels,
            category_map=category_map,
            folder_options=folder_options,
        )
        return Response(plan)
