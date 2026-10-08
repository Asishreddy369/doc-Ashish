# Local ML Classifier

DocVault uses a local trainable text classifier plus high-confidence rules.
The goal is fast, private classification on an 8 GB laptop while still allowing
the model to improve as more labeled documents are added.

## Current Model Status

Model file:

```powershell
backend\documents\ml_models\document_classifier.json
```

Latest training run:

- Dataset root: `C:\Users\HP\Downloads\Yanvior Technology`
- Training documents used: `193`
- Holdout accuracy: `0.9459` on `37` validation documents
- OCR was used for this training run
- Training uses extracted document content only; filenames and folder paths are
  not used as category evidence.

Trained labels:

- Accounts and Bank Related Documents: `117`
- Audit: `2`
- Certificates and Registration: `4`
- Incorporation and MCA related: `9`
- Land And Building: `5`
- Share Capital and Other Instruments Issued: `5`
- Tax: `51`

`Loans and Debt` was skipped by the minimum-document rule because only one
training document was available. Add more labeled examples before expecting
good classification for that label.

Top current confusions:

- Accounts and Bank Related Documents -> Audit
- Accounts and Bank Related Documents -> Land And Building

## What The Model Does

- Trains from a folder where each child folder is a document category.
- Skips raw upload folders such as `Yanvior Technolgies` by default.
- Saves a compact JSON model for fast local inference.
- Classifies uploads from extracted document content, not filename/path text.
- Runs background extraction and classification in batches of up to `7`
  documents at a time.
- Combines ML predictions with high-confidence rules for PAN, Aadhaar, GST,
  invoices, purchase orders, bank statements, tax filings, archives, digital
  certificates, and agreements.
- Stores classifier confidence, source, alternatives, and review flags on each
  uploaded document.
- Extracts generic fields from all document types, not only known categories:
  GSTIN, PAN, Aadhaar, IFSC, email, phone, invoice number, PO number, account
  number, CIN, dates, and amounts.

## Retrain From Labeled Folders

Run from the backend folder:

```powershell
cd backend
..\.venv\Scripts\python.exe manage.py train_document_classifier "C:\Users\HP\Downloads\Yanvior Technology"
```

The trainer skips these labels by default:

- `Uncertain`
- `Testing`
- `Yanvior Technolgies`

## Retrain With Existing Corrected Documents

After users correct categories and OCR has extracted text, retrain using the
database as additional training data:

```powershell
cd backend
..\.venv\Scripts\python.exe manage.py train_document_classifier "C:\Users\HP\Downloads\Yanvior Technology" --from-db
```

## When To Use OCR Training

For scanned-image documents where fast PDF/DOCX/XLSX text extraction does not
capture enough content, train with OCR. This is the recommended command for
the production model:

```powershell
cd backend
..\.venv\Scripts\python.exe manage.py train_document_classifier "C:\Users\HP\Downloads\Yanvior Technology" --use-ocr
```

This is slower, but improves scanned-document categories.

## Fast Classification + Extraction

Uploads now queue extraction first. The worker extracts content, classifies
from that content, extracts fields, and then routes the file into the selected
folder structure. Filename/path text is not used for the category decision.

Default performance limits:

- Digital PDFs: first `3` pages
- Scanned PDFs: first page OCR at `96` DPI, no high-DPI retries
- Images: OCR after resizing the longest edge to `1000` pixels
- DOCX: first `250` paragraphs and `8` tables
- XLSX: first `4` sheets and `120` rows per sheet
- Text/CSV/log files: first `40000` characters

Each processed document stores timing diagnostics in `classifier_details`:

- `extraction_seconds`
- `extraction_is_ocr`
- `extraction_text_chars`
- `extraction_spatial_blocks`
- `extraction_profile`

For a slower but more complete one-off run, set:

```powershell
$env:DOCVAULT_EXTRACTION_PROFILE="full"
```

For scanned documents where quality is more important than speed, enable
high-DPI retries:

```powershell
$env:DOCVAULT_OCR_RETRY_HIGH_DPI="1"
```

## How To Make It Stronger

The model cannot reliably classify an unseen category without examples. For
production-quality classification, collect at least `20-50` corrected examples
per category, then retrain.

Best next labels to improve:

- Audit
- Certificates and Registration
- Land And Building
- Share Capital and Other Instruments Issued
- Loans and Debt
- Insurance
- Power

The training command writes validation accuracy and top confusions into the
model file every time, so model quality can be tracked after each retrain.
