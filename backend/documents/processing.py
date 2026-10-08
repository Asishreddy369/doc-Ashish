import time

from django.conf import settings
from django.utils import timezone

from .classifier import classify_document_with_details, extract_key_fields
from .extractor import extract_document_text
from .folder_planner import plan_document_route
from .models import Document
from .storage import route_document_file


LOCKED_RULE_IDS = {
    "rule_bank_stmt_name_01",
    "rule_pan_name_01",
    "rule_aadhaar_name_01",
}


def build_classification_text(document, extracted_text="", include_identity=False):
    identity_parts = []
    if include_identity:
        identity_parts = [
            f"filename:{document.original_name}",
            f"path:{document.original_relative_path}" if document.original_relative_path else "",
        ]

    return "\n".join(
        part
        for part in [*identity_parts, extracted_text]
        if part
    )


def should_apply_new_classification(document, classification, force=False):
    new_category = classification.get("category")
    if not new_category:
        return False

    if force:
        return True

    if document.matched_rule in LOCKED_RULE_IDS and document.classification_confidence >= 0.95:
        return False

    if document.category in {"Unclassified", "Other", "Other Documents", None, ""}:
        return True

    if classification.get("source") == "rule" and classification.get("confidence", 0) >= 0.97:
        return True

    return document.classification_confidence < 0.75 and not classification.get("needs_review")


def apply_classification_and_route(document, classification, structure_levels=None, category_map=None, extracted_text="", force=False):
    if should_apply_new_classification(document, classification, force=force):
        document.category = classification["category"]

    document.matched_rule = classification.get("matched_rule")
    document.classification_confidence = classification.get("confidence", 0.0)
    document.classifier_source = classification.get("source")

    details = document.classifier_details or {}
    details.update({
        "needs_review": classification.get("needs_review", True),
        "ml_prediction": classification.get("ml_prediction"),
    })
    document.classifier_details = details

    folder_structure = document.folder_structure or {}
    mode = folder_structure.get("mode") or "auto"
    levels = structure_levels or folder_structure.get("levels") or ["category", "year", "month"]
    category_map = category_map if category_map is not None else folder_structure.get("category_map") or {}
    folder_options = folder_structure.get("folder_options") or {}

    upload_date = document.created_at or timezone.now()
    route = plan_document_route(
        {
            "name": document.original_name,
            "relative_path": document.original_relative_path,
            "category": document.category,
            "text": extracted_text,
            "year": upload_date.year,
            "month": upload_date.month,
        },
        structure_levels=levels,
        category_map=category_map,
        mode=mode,
        folder_options=folder_options,
    )
    document.document_year = route["year"]
    document.document_month = route["month"]
    document.organization_path = route["target_folder"]
    document.folder_structure = {
        **folder_structure,
        "mode": mode,
        "levels": levels,
        "category_map": category_map,
        "folder_options": folder_options,
        "route": route,
    }


def quick_classify_and_route(
    document,
    structure_levels=None,
    category_map=None,
    use_existing_text=False,
    force=False,
    mark_extraction_queued=True,
):
    existing_text = document.extracted_text if use_existing_text else ""
    classification = classify_document_with_details(build_classification_text(document, existing_text))
    apply_classification_and_route(
        document,
        classification,
        structure_levels=structure_levels,
        category_map=category_map,
        extracted_text=existing_text,
        force=force,
    )
    details = document.classifier_details or {}
    details["classification_status"] = "completed"
    route_document_file(document)
    if mark_extraction_queued:
        details["extraction_status"] = "queued"
        document.status = "PROCESSING"
        document.processed_at = None
    else:
        if existing_text:
            details["extraction_status"] = "completed"
        document.status = "NEEDS_REVIEW" if classification.get("needs_review") else "COMPLETED"
        document.processed_at = timezone.now()

    document.classifier_details = details
    document.save()
    return document


def mark_content_processing_queued(document):
    details = document.classifier_details or {}
    details.update({
        "classification_status": "queued",
        "classification_mode": "content_first",
        "classification_uses_filename": False,
        "extraction_status": "queued",
    })
    document.classifier_details = details
    document.category = "Unclassified"
    document.status = "PROCESSING"
    document.processed_at = None
    document.save(update_fields=[
        "classifier_details",
        "category",
        "status",
        "processed_at",
        "updated_at",
    ])
    return document


def process_document_extraction(document_id, allow_reclassify=True):
    document = Document.objects.get(id=document_id)
    details = document.classifier_details or {}
    details["extraction_status"] = "running"
    document.classifier_details = details
    document.status = "PROCESSING"
    document.save(update_fields=["classifier_details", "status", "updated_at"])

    extraction_started = time.perf_counter()
    text, is_ocr, err_msg, spatial_blocks = extract_document_text(document.file.path, document.file_type)
    extraction_seconds = round(time.perf_counter() - extraction_started, 3)
    if err_msg:
        details["classification_status"] = "not_run"
        details["classification_mode"] = "content_first"
        details["classification_uses_filename"] = False
        details["extraction_status"] = "failed"
        details["extraction_seconds"] = extraction_seconds
        details["extraction_profile"] = getattr(settings, "DOCVAULT_EXTRACTION_PROFILE", "fast")
        document.classifier_details = details
        document.error_info = err_msg
        document.status = "FAILED" if not document.category or document.category == "Unclassified" else "NEEDS_REVIEW"
        document.processed_at = timezone.now()
        document.save(update_fields=["classifier_details", "error_info", "status", "processed_at", "updated_at"])
        return document

    document.extracted_text = text
    classification = classify_document_with_details(
        build_classification_text(document, text, include_identity=False)
    )

    if allow_reclassify:
        apply_classification_and_route(document, classification, extracted_text=text)

    field_error = None
    try:
        document.key_fields = extract_key_fields(document.category or classification.get("category") or "Unclassified", text, spatial_blocks=spatial_blocks)
    except Exception as exc:
        document.key_fields = {}
        field_error = f"Key field extraction failed: {exc}"

    # BUG-B01 FIX: Re-read from document.classifier_details (which was populated by
    # apply_classification_and_route) to preserve needs_review/ml_prediction keys.
    # Do NOT shadow with a fresh empty dict.
    details = document.classifier_details or {}
    details["classification_status"] = "completed"
    details["classification_mode"] = "content_first"
    details["classification_uses_filename"] = False
    details["extraction_status"] = "completed" if text else "empty"
    details["extraction_seconds"] = extraction_seconds
    details["extraction_is_ocr"] = is_ocr
    details["extraction_text_chars"] = len(text or "")
    details["extraction_spatial_blocks"] = len(spatial_blocks or [])
    details["extraction_profile"] = getattr(settings, "DOCVAULT_EXTRACTION_PROFILE", "fast")
    document.classifier_details = details
    # BUG-B01 FIX: needs_review is now correctly read from details (set by apply_classification_and_route)
    document.status = "NEEDS_REVIEW" if details.get("needs_review") or not text else "COMPLETED"
    document.processed_at = timezone.now()
    document.error_info = field_error or (None if text else "No text could be extracted from this file.")

    route_document_file(document)
    document.save()
    return document
