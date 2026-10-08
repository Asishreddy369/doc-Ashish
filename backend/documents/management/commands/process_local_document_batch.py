import hashlib
import json
import os
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections
from django.utils import timezone

from documents.models import Document
from documents.processing import mark_content_processing_queued, process_document_extraction


def iter_directories_in_os_order(root):
    root = Path(root)

    def walk(path):
        try:
            entries = list(os.scandir(path))
        except OSError:
            return

        for entry in entries:
            if entry.is_dir():
                child = Path(entry.path)
                yield child
                yield from walk(child)

    yield from walk(root)


def iter_files_in_os_order(root):
    root = Path(root)

    def walk(path):
        try:
            entries = list(os.scandir(path))
        except OSError:
            return

        for entry in entries:
            if entry.is_file():
                yield Path(entry.path)
        for entry in entries:
            if entry.is_dir():
                yield from walk(Path(entry.path))

    yield from walk(root)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_folder_options(structure_root):
    structure_root = Path(structure_root)
    folders = [
        directory.relative_to(structure_root).as_posix()
        for directory in iter_directories_in_os_order(structure_root)
    ]
    if "Unclassified" not in {folder.replace("\\", "/") for folder in folders}:
        folders.append("Unclassified")

    folder_set = {folder.replace("\\", "/") for folder in folders}
    category_folder_map = {}

    def add_mapping(category, folder):
        if folder in folder_set:
            category_folder_map[category] = folder

    add_mapping("Accounts and Bank Related Documents", "Accounts and Bank related Documents")
    add_mapping("Bank Statement", "Accounts and Bank related Documents")
    add_mapping("GST Certificate", "Tax/GST")
    add_mapping("Tax", "Tax")
    add_mapping("Tax Filing", "Tax")
    add_mapping("PAN", "Certificates and Registration/PAN")
    add_mapping("Digital Certificate", "Certificates and Registration")
    add_mapping("Agreement", "Land and Building/EPC Contracts")
    add_mapping("Board Resolution", "Incorporation and MCA related/Board meetings")
    add_mapping("Meeting Minutes", "Incorporation and MCA related/Board meetings")

    return {
        "root_folder": structure_root.name,
        "folders": folders,
        "fallback_folder": "Unclassified",
        "category_folder_map": category_folder_map,
    }


def process_one(document_id):
    close_old_connections()
    try:
        document = process_document_extraction(document_id)
        return {
            "id": str(document.id),
            "file": document.original_name,
            "category": document.category,
            "route": document.organization_path,
            "status": document.status,
            "error": document.error_info,
            "seconds": (document.classifier_details or {}).get("extraction_seconds"),
            "is_ocr": (document.classifier_details or {}).get("extraction_is_ocr"),
            "text_chars": (document.classifier_details or {}).get("extraction_text_chars"),
        }
    finally:
        close_old_connections()


class Command(BaseCommand):
    help = "Import a local document folder, use a local folder tree as template, and process content-first."

    def add_arguments(self, parser):
        parser.add_argument("document_root", help="Folder containing documents to process.")
        parser.add_argument("structure_root", help="Folder whose directory tree should be used for routing.")
        parser.add_argument("--batch-id", default="", help="Optional batch id. Defaults to a timestamped local test batch.")
        parser.add_argument("--limit", type=int, default=0, help="Optional file limit for a smaller smoke test.")
        parser.add_argument("--max-workers", type=int, default=7, help="Number of concurrent content extraction/classification workers.")
        parser.add_argument("--report", default="", help="Optional JSON report path.")
        parser.add_argument(
            "--resume-existing",
            action="store_true",
            help="Do not import files. Reprocess unfinished/missing-text documents from --batch-id.",
        )

    def handle(self, *args, **options):
        document_root = Path(options["document_root"]).expanduser()
        structure_root = Path(options["structure_root"]).expanduser()
        if not document_root.exists() or not document_root.is_dir():
            raise CommandError(f"Document folder not found: {document_root}")
        if not structure_root.exists() or not structure_root.is_dir():
            raise CommandError(f"Folder structure root not found: {structure_root}")

        files = [
            path for path in iter_files_in_os_order(document_root)
            if path.suffix.lower().lstrip(".") in Document.ALLOWED_EXTENSIONS
        ]
        if options["limit"]:
            files = files[:options["limit"]]
        if not files:
            raise CommandError("No supported documents found.")

        batch_id = options["batch_id"] or f"{structure_root.name}_content_test_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
        if options["resume_existing"] and not options["batch_id"]:
            raise CommandError("--resume-existing requires --batch-id.")

        folder_options = build_folder_options(structure_root)
        folder_structure = {
            "mode": "user_defined",
            "levels": ["category", "year", "month"],
            "category_map": {},
            "folder_options": folder_options,
        }

        self.stdout.write(f"Folder template: {structure_root}")
        self.stdout.write(f"Document source: {document_root}")
        self.stdout.write(f"Template folders imported: {len(folder_options['folders'])}")
        self.stdout.write(f"Documents selected: {len(files)}")
        self.stdout.write(f"Batch id: {batch_id}")
        self.stdout.write(f"Workers: {options['max_workers']}")

        documents = []
        errors = []
        if options["resume_existing"]:
            documents = list(
                Document.objects.filter(batch_id=batch_id)
                .filter(status__in=["PROCESSING", "FAILED"])
                .order_by("created_at")
            )
            missing_text_docs = list(
                Document.objects.filter(batch_id=batch_id)
                .filter(extracted_text__isnull=True)
                .exclude(id__in=[document.id for document in documents])
                .order_by("created_at")
            )
            empty_text_docs = list(
                Document.objects.filter(batch_id=batch_id, extracted_text="")
                .exclude(id__in=[document.id for document in documents])
                .order_by("created_at")
            )
            documents.extend(missing_text_docs)
            documents.extend(empty_text_docs)
            for document in documents:
                document.folder_structure = folder_structure
                mark_content_processing_queued(document)
            self.stdout.write(f"Resuming {len(documents)} unfinished/missing-text documents...")
        else:
            for index, path in enumerate(files, start=1):
                try:
                    doc_uuid = uuid.uuid4()
                    original_name = path.name
                    safe_name = f"{doc_uuid}_{original_name}"
                    with open(path, "rb") as handle:
                        document = Document.objects.create(
                            id=doc_uuid,
                            original_name=original_name,
                            file_type=path.suffix.lower().lstrip("."),
                            file_size=path.stat().st_size,
                            file=File(handle, name=safe_name),
                            category="Unclassified",
                            status="PROCESSING",
                            checksum=sha256_file(path),
                            batch_id=batch_id,
                            original_relative_path=path.relative_to(document_root).as_posix(),
                            folder_structure=folder_structure,
                        )
                    document.file.close()
                    mark_content_processing_queued(document)
                    documents.append(document)
                    if index % 50 == 0:
                        self.stdout.write(f"Imported {index}/{len(files)} documents...")
                except Exception as exc:
                    errors.append({"file": str(path), "error": str(exc)})

        results = []
        completed = 0
        with ThreadPoolExecutor(max_workers=max(1, options["max_workers"])) as executor:
            futures = {
                executor.submit(process_one, document.id): document
                for document in documents
            }
            for future in as_completed(futures):
                completed += 1
                document = futures[future]
                try:
                    results.append(future.result())
                except Exception as exc:
                    errors.append({"file": document.original_name, "id": str(document.id), "error": str(exc)})
                if completed % 25 == 0 or completed == len(documents):
                    self.stdout.write(f"Processed {completed}/{len(documents)} documents...")

        category_counts = Counter(result["category"] for result in results)
        route_counts = Counter(result["route"] or "Unrouted" for result in results)
        status_counts = Counter(result["status"] for result in results)

        report = {
            "batch_id": batch_id,
            "document_root": str(document_root),
            "structure_root": str(structure_root),
            "documents_selected": len(files),
            "documents_imported": len(documents),
            "documents_processed": len(results),
            "errors": errors,
            "status_counts": dict(status_counts),
            "category_counts": dict(category_counts),
            "route_counts": dict(route_counts),
            "results": results,
        }

        report_path = Path(options["report"]) if options["report"] else Path("local_batch_report.json")
        if not report_path.is_absolute():
            report_path = Path.cwd() / report_path
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("Batch processing complete."))
        self.stdout.write(f"Report: {report_path}")
        self.stdout.write(f"Status counts: {dict(status_counts)}")
        self.stdout.write(f"Top categories: {category_counts.most_common(12)}")
        self.stdout.write(f"Top routes: {route_counts.most_common(12)}")
        if errors:
            self.stdout.write(self.style.WARNING(f"Errors: {len(errors)}"))
