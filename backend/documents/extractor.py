import os
import re
import threading
import fitz  # PyMuPDF
import docx
import openpyxl
from PIL import Image
from django.conf import settings

# Lazy OCR instances avoid reloading models on every call. OCR engines are kept
# per worker thread because RapidOCR/ONNX sessions can stall when one singleton
# is used concurrently across a large batch.
_ocr_engine = None
_ocr_local = threading.local()
# BUG-B07 FIX: Lock for global (non-thread-local) OCR engine initialization.
_ocr_engine_lock = threading.Lock()

def get_ocr_engine():
    global _ocr_engine
    if _setting("DOCVAULT_OCR_THREAD_LOCAL", True):
        if not hasattr(_ocr_local, "engine"):
            try:
                from rapidocr_onnxruntime import RapidOCR
            except ImportError as exc:
                raise RuntimeError(
                    "RapidOCR is not installed in this Python environment. "
                    "Use Python 3.11/3.12 with rapidocr-onnxruntime for scanned OCR."
                ) from exc
            _ocr_local.engine = RapidOCR()
        return _ocr_local.engine

    # BUG-B07 FIX: Double-checked locking for global singleton.
    if _ocr_engine is None:
        with _ocr_engine_lock:
            if _ocr_engine is None:
                try:
                    from rapidocr_onnxruntime import RapidOCR
                except ImportError as exc:
                    raise RuntimeError(
                        "RapidOCR is not installed in this Python environment. "
                        "Use Python 3.11/3.12 with rapidocr-onnxruntime for scanned OCR."
                    ) from exc
                _ocr_engine = RapidOCR()
    return _ocr_engine

def normalize_text(text):
    """
    Normalizes extracted text:
    - Standardizes carriage returns and line endings.
    - Collapses excessive newlines (3+ -> 2).
    - Cleans non-printable ASCII control characters.
    - Collapses multiple spaces.
    """
    if not text:
        return ""

    # Replace carriage returns
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # Remove non-printable control characters except newlines and tabs
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    # Collapse multiple spaces or tabs on a single line
    text = re.sub(r'[ \t]+', ' ', text)

    # Clean trailing spaces before line breaks
    text = re.sub(r' +(?=\n)', '', text)

    # Collapse 3 or more consecutive newlines into 2
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


def _setting(name, default):
    return getattr(settings, name, default)


def _is_fast_profile():
    return _setting("DOCVAULT_EXTRACTION_PROFILE", "fast") != "full"


def _debug(message):
    if _setting("DOCVAULT_EXTRACTOR_DEBUG", False):
        print(message)


def _limit_text(text):
    max_chars = _setting("DOCVAULT_MAX_TEXT_CHARS", 40000)
    if max_chars and len(text) > max_chars:
        return text[:max_chars] + "\n\n[Extraction truncated for fast processing]"
    return text


def _extract_ocr_lines_from_pdf_page(page, ocr_engine, dpi):
    pix = page.get_pixmap(dpi=dpi)
    img_bytes = pix.tobytes("png")
    result, _ = ocr_engine(img_bytes)

    lines = []
    blocks = []
    if result:
        for line in result:
            if line and len(line) >= 2:
                box = line[0]
                text = line[1]
                if text:
                    lines.append(text)
                    blocks.append({'box': box, 'text': text})
    return lines, blocks


def extract_from_pdf(file_path):
    _debug("  [PDF] Opening file...")
    doc = fitz.open(file_path)
    digital_text_blocks = []

    try:
        total_pages = len(doc)
        max_pages = _setting("DOCVAULT_MAX_PDF_DIGITAL_PAGES", 3)
        page_count = total_pages
        if _is_fast_profile() and max_pages:
            page_count = min(total_pages, max_pages)

        _debug(f"  [PDF] Extracting digital text from {page_count}/{total_pages} pages...")
        for page_num in range(page_count):
            page = doc[page_num]
            text = page.get_text("text")
            if text:
                digital_text_blocks.append(text)

        full_digital_text = "\n".join(digital_text_blocks)
        non_ws_count = len(re.sub(r'\s+', '', full_digital_text))
        _debug(f"  [PDF] Digital non-ws char count: {non_ws_count}")

        # If digital text exists, return digital text
        if non_ws_count >= 30:
            if page_count < total_pages:
                full_digital_text += "\n\n[Extraction truncated for fast processing]"
            # BUG-B07 FIX: Always return 3-tuple (text, is_ocr, spatial_blocks)
            # instead of 2-tuple for digital PDFs to avoid length-check branching in caller.
            return normalize_text(_limit_text(full_digital_text)), False, []  # (text, is_ocr, spatial_blocks)

        _debug("  [PDF] Falling back to RapidOCR...")
        # Scanned PDF Fallback -> OCR first page only for predictable batch speed.
        ocr_engine = get_ocr_engine()
        ocr_blocks = []
        spatial_blocks = []

        dpi = _setting("DOCVAULT_OCR_PDF_DPI", 96)
        retry_high_dpi = _setting("DOCVAULT_OCR_RETRY_HIGH_DPI", False)
        _debug("  [PDF] Starting OCR on 1st page only for max speed...")
        for page_num in range(min(total_pages, 1)):
            _debug(f"  [PDF] Rendering page {page_num}...")
            page = doc[page_num]

            _debug(f"  [PDF] OCR engine processing page {page_num} at {dpi} DPI...")
            lines, blocks = _extract_ocr_lines_from_pdf_page(page, ocr_engine, dpi=dpi)

            if retry_high_dpi and not lines:
                _debug(f"  [PDF] Empty fast OCR result; retrying page {page_num} at 180 DPI...")
                lines, blocks = _extract_ocr_lines_from_pdf_page(page, ocr_engine, dpi=180)

            if retry_high_dpi and not lines:
                _debug(f"  [PDF] Empty 180 DPI OCR result; retrying page {page_num} at 300 DPI...")
                lines, blocks = _extract_ocr_lines_from_pdf_page(page, ocr_engine, dpi=300)

            ocr_blocks.extend(lines)
            spatial_blocks.extend(blocks)

        _debug("  [PDF] Finished OCR.")
        full_ocr_text = "\n\n".join(ocr_blocks)
        return normalize_text(_limit_text(full_ocr_text)), True, spatial_blocks
    finally:
        doc.close()


# BUG-B07 FIX: extract_from_image was dead code (extract_from_image_with_blocks is used
# exclusively). Removed to eliminate the inconsistent 2-tuple/3-tuple return values.

def extract_from_image_with_blocks(file_path):
    """
    Extracts text and returns spatial blocks.
    """
    try:
        img = Image.open(file_path)
        max_edge = _setting("DOCVAULT_OCR_IMAGE_MAX_EDGE", 1000)
        img.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
        
        import io
        img_byte_arr = io.BytesIO()
        if img.mode != 'RGB':
            img = img.convert('RGB')
        img.save(img_byte_arr, format='JPEG', quality=85)
        img_bytes = img_byte_arr.getvalue()
        
        ocr_engine = get_ocr_engine()
        result, _ = ocr_engine(img_bytes)
        
        if not result:
            return "", True, []

        blocks = []
        lines = []
        for line in result:
            if line and len(line) >= 2:
                box = line[0]
                text = line[1]
                lines.append(text)
                blocks.append({'box': box, 'text': text})
                
        full_text = "\n".join(lines)
        return normalize_text(_limit_text(full_text)), True, blocks
    except Exception as e:
        _debug(f"Image extract error: {e}")
        return "", True, []


def extract_from_docx(file_path):
    """
    Extracts text from DOCX files (paragraphs and tables).
    """
    doc = docx.Document(file_path)
    max_paragraphs = _setting("DOCVAULT_MAX_DOCX_PARAGRAPHS", 250)
    max_tables = _setting("DOCVAULT_MAX_DOCX_TABLES", 8)
    paragraphs = []
    for paragraph in doc.paragraphs:
        if paragraph.text.strip():
            paragraphs.append(paragraph.text)
        if _is_fast_profile() and max_paragraphs and len(paragraphs) >= max_paragraphs:
            break
    
    # Extract table content
    table_texts = []
    tables = doc.tables
    if _is_fast_profile() and max_tables:
        tables = tables[:max_tables]
    for table in tables:
        for row in table.rows:
            row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if row_cells:
                table_texts.append(" | ".join(row_cells))

    full_text = "\n".join(paragraphs)
    if table_texts:
        full_text += "\n\n--- Tables ---\n" + "\n".join(table_texts)

    return normalize_text(_limit_text(full_text)), False


def extract_from_legacy_doc(file_path):
    """
    Best-effort fallback for old binary .doc files when no external converter is available.
    This extracts readable ASCII and UTF-16LE strings from the OLE payload.
    """
    with open(file_path, 'rb') as f:
        data = f.read()

    text_parts = []

    ascii_chunks = re.findall(rb'[\x20-\x7E]{4,}', data)
    text_parts.extend(chunk.decode('latin-1', errors='ignore') for chunk in ascii_chunks)

    utf16_chars = []
    current = []
    for index in range(0, len(data) - 1, 2):
        value = data[index] | (data[index + 1] << 8)
        if value in (9, 10, 13) or 32 <= value <= 126:
            current.append(chr(value))
        else:
            if len(current) >= 4:
                utf16_chars.append(''.join(current))
            current = []
    if len(current) >= 4:
        utf16_chars.append(''.join(current))

    text_parts.extend(utf16_chars)
    noise_markers = (
        '[Content_Types].xml',
        '_rels/.rels',
        'theme/theme',
        'Root Entry',
        'WordDocument',
        'SummaryInformation',
        'DocumentSummaryInformation',
        'CompObj',
        'PK',
        'xmlns:',
        '<?xml',
    )
    cleaned = []
    seen = set()
    for part in text_parts:
        part = normalize_text(part)
        if not part or part in seen:
            continue
        if len(part) < 4:
            continue
        if any(marker in part for marker in noise_markers):
            continue
        if len(part) <= 8 and not re.search(r'[aeiouAEIOU]', part):
            continue
        seen.add(part)
        cleaned.append(part)

    return normalize_text("\n".join(cleaned)), False


def extract_from_xlsx(file_path):
    """
    Extracts text from XLSX files across all worksheets.
    """
    wb = openpyxl.load_workbook(file_path, data_only=True, read_only=True)
    sheet_texts = []
    max_sheets = _setting("DOCVAULT_MAX_XLSX_SHEETS", 4)
    max_rows = _setting("DOCVAULT_MAX_XLSX_ROWS", 120)

    try:
        sheet_names = wb.sheetnames
        if _is_fast_profile() and max_sheets:
            sheet_names = sheet_names[:max_sheets]

        for sheet_name in sheet_names:
            sheet = wb[sheet_name]
            rows_text = []
            for row_index, row in enumerate(sheet.iter_rows(values_only=True), start=1):
                if _is_fast_profile() and max_rows and row_index > max_rows:
                    rows_text.append("[Sheet rows truncated for fast processing]")
                    break
                row_vals = [str(val).strip() for val in row if val is not None and str(val).strip() != '']
                if row_vals:
                    rows_text.append(" | ".join(row_vals))

            if rows_text:
                sheet_texts.append(f"Sheet: {sheet_name}\n" + "\n".join(rows_text))

        if _is_fast_profile() and max_sheets and len(wb.sheetnames) > len(sheet_names):
            sheet_texts.append("[Workbook sheets truncated for fast processing]")

        full_text = "\n\n".join(sheet_texts)
        return normalize_text(_limit_text(full_text)), False
    finally:
        wb.close()


def extract_from_txt(file_path):
    """
    Extracts text from plain text files.
    """
    encodings = ['utf-8', 'latin-1', 'cp1252']
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                max_chars = _setting("DOCVAULT_MAX_TEXT_CHARS", 40000)
                content = f.read(max_chars + 1 if _is_fast_profile() and max_chars else -1)
                content = _limit_text(content)
                return normalize_text(content), False
        except UnicodeDecodeError:
            continue
    return "", False


def extract_document_text(file_path, file_type):
    """
    Unified entry point for document text extraction & OCR pipeline.
    Returns: (extracted_text, is_ocr, error_message, spatial_blocks)
    """
    if not file_path or not os.path.exists(file_path):
        return "", False, "File path does not exist.", []

    ext = file_type.lower() if file_type else file_path.split('.')[-1].lower()

    try:
        if ext == 'pdf':
            # BUG-B07 FIX: extract_from_pdf now always returns 3-tuple — no len() check needed.
            text, is_ocr, spatial_blocks = extract_from_pdf(file_path)
            return text, is_ocr, None, spatial_blocks

        elif ext in ['jpg', 'jpeg', 'png', 'tiff', 'tif']:
            # extract_from_image_with_blocks always returns 3-tuple.
            text, is_ocr, spatial_blocks = extract_from_image_with_blocks(file_path)
            return text, is_ocr, None, spatial_blocks

        elif ext == 'docx':
            text, is_ocr = extract_from_docx(file_path)
            return text, is_ocr, None, []

        elif ext == 'doc':
            text, is_ocr = extract_from_legacy_doc(file_path)
            if text:
                return text, is_ocr, None, []
            return "", False, "Legacy .doc text could not be extracted without a Word converter such as LibreOffice.", []

        elif ext in ['xlsx', 'xls']:
            text, is_ocr = extract_from_xlsx(file_path)
            return text, is_ocr, None, []

        elif ext in ['txt', 'log', 'bat', 'csv']:
            text, is_ocr = extract_from_txt(file_path)
            return text, is_ocr, None, []

        elif ext in ['zip', 'jar']:
            import zipfile
            try:
                with zipfile.ZipFile(file_path, 'r') as z:
                    file_list = "\n".join(z.namelist())
                    return f"Archive Contents:\n{file_list}", False, None, []
            except zipfile.BadZipFile:
                return "", False, "Invalid ZIP/JAR archive", []

        elif ext == 'rar':
            return "RAR Archive (Contents not parsed)", False, None, []

        elif ext in ['cer', 'csi']:
            return "Digital Security Certificate (Binary)", False, None, []

        else:
            return "", False, f"Unsupported extension .{ext} for text extraction.", []

    except Exception as e:
        return "", False, str(e), []
