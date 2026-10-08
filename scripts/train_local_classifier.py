import argparse
import importlib
import re
import sys
from pathlib import Path
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from documents.ml_classifier import DEFAULT_MODEL_PATH, MultinomialTextClassifier, normalize_training_text


SUPPORTED_EXTENSIONS = {
    ".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif",
    ".docx", ".xlsx", ".txt", ".csv", ".log", ".bat",
}
DEFAULT_SKIP_LABELS = ["Uncertain", "Testing", "Yanvior Technolgies"]


def clean_filename_text(path):
    name = Path(path).stem
    name = re.sub(r"^[0-9a-fA-F-]{32,}_?", " ", name)
    name = re.sub(r"[_\-]+", " ", name)
    return name


def optional_import(module_name):
    try:
        return importlib.import_module(module_name)
    except Exception:
        return None


def extract_pdf_text(path):
    fitz = optional_import("fitz")
    if fitz is None:
        return ""

    parts = []
    with fitz.open(path) as doc:
        for page_index in range(min(len(doc), 2)):
            text = doc[page_index].get_text("text")
            if text:
                parts.append(text)
    return " ".join(parts)


def extract_docx_text(path):
    docx = optional_import("docx")
    if docx is not None:
        document = docx.Document(path)
        parts = [p.text for p in document.paragraphs if p.text.strip()]
        for table in document.tables[:5]:
            for row in table.rows[:30]:
                parts.append(" | ".join(cell.text.strip() for cell in row.cells if cell.text.strip()))
        return " ".join(parts)

    try:
        with ZipFile(path) as archive:
            xml = archive.read("word/document.xml")
        root = ElementTree.fromstring(xml)
        texts = [node.text for node in root.iter() if node.text and node.text.strip()]
        return " ".join(texts)
    except (BadZipFile, KeyError, ElementTree.ParseError):
        return ""


def extract_xlsx_text(path):
    openpyxl = optional_import("openpyxl")
    if openpyxl is not None:
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
        parts = []
        for sheet_name in wb.sheetnames[:4]:
            sheet = wb[sheet_name]
            for idx, row in enumerate(sheet.iter_rows(values_only=True)):
                if idx >= 80:
                    break
                values = [str(value).strip() for value in row if value is not None and str(value).strip()]
                if values:
                    parts.append(" | ".join(values))
        wb.close()
        return " ".join(parts)

    try:
        with ZipFile(path) as archive:
            shared = []
            if "xl/sharedStrings.xml" in archive.namelist():
                shared_root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
                shared = [" ".join(node.itertext()) for node in shared_root]
            text_parts = shared[:200]
            for name in archive.namelist():
                if name.startswith("xl/worksheets/") and name.endswith(".xml"):
                    root = ElementTree.fromstring(archive.read(name))
                    text_parts.extend(node.text for node in root.iter() if node.text and node.text.strip())
            return " ".join(text_parts)
    except (BadZipFile, ElementTree.ParseError):
        return ""


def extract_text(path):
    path = Path(path)
    ext = path.suffix.lower()
    parts = [clean_filename_text(path)]

    try:
        if ext == ".pdf":
            parts.append(extract_pdf_text(path))
        elif ext == ".docx":
            parts.append(extract_docx_text(path))
        elif ext == ".xlsx":
            parts.append(extract_xlsx_text(path))
        elif ext in {".txt", ".csv", ".log", ".bat"}:
            parts.append(path.read_text(encoding="utf-8", errors="ignore")[:12000])
    except Exception:
        pass

    return normalize_training_text(" ".join(parts))


def iter_examples(dataset_root, skip_labels, limit_per_label):
    counts = {}
    examples = []

    for label_dir in sorted(path for path in dataset_root.iterdir() if path.is_dir()):
        label = label_dir.name
        if label.lower() in skip_labels:
            continue

        used = 0
        for path in label_dir.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            if limit_per_label and used >= limit_per_label:
                break

            text = extract_text(path)
            if len(text) < 8:
                continue
            examples.append((text, label))
            used += 1

        counts[label] = used
        print(f"{label}: {used} training document(s)")

    return examples, counts


def main():
    parser = argparse.ArgumentParser(description="Train local lightweight document classifier from folder labels.")
    parser.add_argument("dataset_root", nargs="?", default=r"C:\Users\HP\Downloads\Yanvior Technology")
    parser.add_argument("--model-path", default=str(DEFAULT_MODEL_PATH))
    parser.add_argument("--limit-per-label", type=int, default=0)
    parser.add_argument("--min-docs-per-label", type=int, default=2)
    parser.add_argument("--skip-label", action="append", default=DEFAULT_SKIP_LABELS.copy())
    args = parser.parse_args()

    dataset_root = Path(args.dataset_root)
    if not dataset_root.exists():
        raise SystemExit(f"Dataset folder not found: {dataset_root}")

    examples, counts = iter_examples(
        dataset_root,
        {label.lower() for label in args.skip_label},
        args.limit_per_label,
    )
    examples = [
        (text, label)
        for text, label in examples
        if counts.get(label, 0) >= args.min_docs_per_label
    ]

    labels = sorted({label for _text, label in examples})
    if len(labels) < 2:
        raise SystemExit("Need at least two labels with enough documents to train.")

    model = MultinomialTextClassifier()
    model.fit(examples)
    model.training_summary = {
        "dataset_root": str(dataset_root),
        "labels": labels,
        "documents_per_label": {label: counts[label] for label in labels},
        "total_documents": len(examples),
        "trainer": "scripts/train_local_classifier.py",
    }
    model.save(args.model_path)

    print(f"Saved ML classifier: {args.model_path}")
    print(f"Trained labels: {', '.join(labels)}")
    print(f"Training documents used: {len(examples)}")


if __name__ == "__main__":
    main()
