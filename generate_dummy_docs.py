"""
Dummy Document Generator — 1000 masked documents
=================================================
Generates realistic-looking but fully masked dummy documents across
7 categories (Employee, Payroll, Company/Legal, Client/Vendor,
IT/Technical, Internal/Operational, Sensitive/Confidential).

File types produced: PDF, DOCX, XLSX, PNG (matching the app's allowed set)
All PII / sensitive values are replaced with XXXX, XX-XXX-XXXX, etc.

Requirements:
    pip install reportlab python-docx openpyxl Pillow

Run:
    python generate_dummy_docs.py

Output:
    ./dummy_documents/<category>/<filename>   (1000 files total)
"""

import os
import random
import string
from datetime import datetime, timedelta
from pathlib import Path

# ── third-party ──────────────────────────────────────────────────────────────
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.units import inch
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False
    print("⚠  reportlab not found — PDFs will be plain-text stubs. Run: pip install reportlab")

try:
    from docx import Document as DocxDocument
    from docx.shared import Pt, RGBColor
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False
    print("⚠  python-docx not found — DOCX will be plain-text stubs. Run: pip install python-docx")

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False
    print("⚠  openpyxl not found — XLSX will be plain-text stubs. Run: pip install openpyxl")

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("⚠  Pillow not found — PNG will be minimal stubs. Run: pip install Pillow")

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def masked_name():
    return "XXXX XXXX"

def masked_email():
    return "xxxx.xxxx@xxxxx.com"

def masked_phone():
    return "XX-XXXX-XXXX"

def masked_id(prefix=""):
    return f"{prefix}XXXX-XXXX-XXXX"

def masked_amount():
    return "₹XX,XXX.XX"

def masked_date():
    base = datetime(2024, 1, 1) + timedelta(days=random.randint(0, 500))
    return base.strftime("%d/%m/%Y")

def masked_account():
    return "XXXX XXXX XXXX " + str(random.randint(1000, 9999))

def masked_pan():
    return "XXXXX0000X"

def masked_gstin():
    return "XX XXXXX0000X XXX"

def random_ref():
    return "REF-" + "".join(random.choices(string.digits, k=8))

def random_version():
    return f"v{random.randint(1,3)}.{random.randint(0,9)}"

OUTPUT_DIR = Path("dummy_documents")

# ─────────────────────────────────────────────────────────────────────────────
# DOCUMENT DEFINITIONS  (category → list of (filename_template, type, content_fn))
# ─────────────────────────────────────────────────────────────────────────────

DOCUMENTS = []   # filled below via register()

def register(category, filename, ext, content_fn):
    DOCUMENTS.append((category, filename, ext, content_fn))


# ══════════════════════════════════════════════════════════════════════════════
# 1. EMPLOYEE DOCUMENTS  (20 types × 2 = 40 per group, scaled to fill quota)
# ══════════════════════════════════════════════════════════════════════════════

def _employee_resume(idx):
    return {
        "title": "Resume / CV",
        "lines": [
            f"Name            : {masked_name()}",
            f"Date of Birth   : {masked_date()}",
            f"Contact         : {masked_phone()}",
            f"Email           : {masked_email()}",
            f"Address         : XXXX, XXXX Nagar, XXXX – XXXXXX",
            "",
            "OBJECTIVE",
            "Seeking a challenging position in XXXX department to leverage XXXX years of experience.",
            "",
            "EDUCATION",
            f"B.Tech / B.E in XXXX  |  XXXX University  |  {masked_date()}",
            f"12th Standard  |  XXXX School  |  {masked_date()}",
            "",
            "EXPERIENCE",
            f"Company: XXXX Pvt. Ltd.   |  Role: XXXX Manager  |  {masked_date()} – {masked_date()}",
            "  – Handled XXXX operations and managed a team of XX members.",
            "",
            "SKILLS  : XXXX, XXXX, XXXX",
            f"Reference ID: {random_ref()}",
        ],
    }

def _employee_job_application(idx):
    return {
        "title": "Job Application",
        "lines": [
            f"Date            : {masked_date()}",
            f"Applicant Name  : {masked_name()}",
            f"Applied For     : XXXX – Senior Level",
            f"Department      : XXXX",
            f"Application Ref : {random_ref()}",
            "",
            "Dear Hiring Manager,",
            "",
            "I, XXXX XXXX, wish to apply for the position of XXXX in your esteemed organisation.",
            "My qualifications and experience make me a suitable candidate for this role.",
            "",
            "Enclosures:",
            "  1. Resume",
            "  2. Educational Certificates",
            "  3. Experience Letters",
            "",
            f"Signature: XXXX          Date: {masked_date()}",
        ],
    }

def _offer_letter(idx):
    return {
        "title": "Offer Letter",
        "lines": [
            f"Ref No      : {random_ref()}",
            f"Date        : {masked_date()}",
            "",
            f"To,",
            f"Mr./Ms. {masked_name()}",
            f"Address: XXXX, XXXX – XXXXXX",
            "",
            "Dear Candidate,",
            "",
            "We are pleased to offer you the position of XXXX in XXXX Pvt. Ltd.",
            "",
            f"Designation  : XXXX",
            f"Department   : XXXX",
            f"CTC          : {masked_amount()} per annum",
            f"Date of Joining: {masked_date()}",
            "",
            "This offer is subject to verification of documents and background check.",
            "",
            "Authorised Signatory: XXXX",
        ],
    }

def _appointment_letter(idx):
    return {
        "title": "Appointment Letter",
        "lines": [
            f"Ref: {random_ref()}   Date: {masked_date()}",
            "",
            f"Employee Name : {masked_name()}",
            f"Employee ID   : EMP-{random_ref()}",
            f"Designation   : XXXX",
            f"Department    : XXXX",
            f"Date of Joining: {masked_date()}",
            f"Probation Period: XX months",
            f"Gross Salary  : {masked_amount()} per month",
            "",
            "Terms and conditions apply as per the employment agreement.",
            "",
            "HR Manager Signature: XXXX",
        ],
    }

def _employment_agreement(idx):
    return {
        "title": "Employment Agreement",
        "lines": [
            f"Agreement Date  : {masked_date()}",
            f"Employer        : XXXX Pvt. Ltd., XXXX, India",
            f"Employee        : {masked_name()}, {masked_id('EMP')}",
            "",
            "TERMS:",
            "1. Position      : XXXX",
            "2. Remuneration  : {masked_amount()} per month",
            "3. Work Location : XXXX",
            "4. Working Hours : XX hours/week",
            "5. Notice Period : XX days",
            "6. Confidentiality: Employee agrees to maintain confidentiality of XXXX.",
            "",
            "SIGNATURES:",
            f"Employee: XXXX          Date: {masked_date()}",
            f"Employer: XXXX          Date: {masked_date()}",
        ],
    }

def _nda(idx):
    return {
        "title": "NDA / Confidentiality Agreement",
        "lines": [
            f"NDA Ref     : {random_ref()}",
            f"Date        : {masked_date()}",
            f"Party A     : XXXX Pvt. Ltd.",
            f"Party B     : {masked_name()}",
            "",
            "WHEREAS both parties wish to explore a business relationship and may disclose",
            "confidential information to each other.",
            "",
            "CONFIDENTIAL INFORMATION means: XXXX, XXXX, XXXX trade secrets.",
            "",
            "OBLIGATIONS: Party B shall not disclose to any third party any Confidential",
            "Information without prior written consent of Party A.",
            "",
            "TERM: XX years from the date of signing.",
            "",
            f"Signatures — Party A: XXXX   Party B: XXXX   Date: {masked_date()}",
        ],
    }

def _id_proof(idx):
    return {
        "title": "ID & Address Proof",
        "lines": [
            "DOCUMENT TYPE: Aadhaar / Passport / Voter ID (MASKED)",
            "",
            f"Name         : {masked_name()}",
            f"DOB          : {masked_date()}",
            f"ID Number    : XXXX-XXXX-XXXX",
            f"Address      : XXXX, XXXX Street, XXXX City – XXXXXX",
            f"Issue Date   : {masked_date()}",
            f"Expiry Date  : {masked_date()}",
            "",
            "*** This is a masked duplicate for testing purposes ***",
        ],
    }

def _edu_certificate(idx):
    return {
        "title": "Educational Certificate",
        "lines": [
            "CERTIFICATE OF GRADUATION",
            "",
            f"This is to certify that {masked_name()} has successfully completed",
            "the programme of XXXX (Bachelor of XXXX) from XXXX University",
            f"in the year XXXX with XXXX% marks.",
            "",
            f"Roll No     : XXXX-XXXX",
            f"Reg No      : {random_ref()}",
            f"Issue Date  : {masked_date()}",
            "",
            "Registrar: XXXX          Seal: [MASKED]",
        ],
    }

def _experience_letter(idx):
    return {
        "title": "Experience / Relieving Letter",
        "lines": [
            f"Date        : {masked_date()}",
            f"Ref No      : {random_ref()}",
            "",
            f"To Whom It May Concern,",
            "",
            f"This is to certify that {masked_name()} was employed with XXXX Pvt. Ltd.",
            f"from {masked_date()} to {masked_date()} as {masked_name()} in the XXXX department.",
            "",
            "During tenure, the employee was found to be hardworking and sincere.",
            "We wish XXXX all the best in future endeavours.",
            "",
            "HR Manager: XXXX",
        ],
    }

def _joining_form(idx):
    return {
        "title": "Employee Joining Form",
        "lines": [
            f"Employee Name       : {masked_name()}",
            f"Employee ID         : EMP-{random_ref()}",
            f"Date of Joining     : {masked_date()}",
            f"Department          : XXXX",
            f"Designation         : XXXX",
            f"Reporting Manager   : {masked_name()}",
            f"Emergency Contact   : {masked_phone()}",
            f"Bank Account        : {masked_account()}",
            f"IFSC Code           : XXXX0XXXXX",
            f"PAN Number          : {masked_pan()}",
            f"Aadhaar             : XXXX-XXXX-XXXX",
            "",
            f"Signature: XXXX    Date: {masked_date()}",
        ],
    }

def _salary_bank_details(idx):
    return {
        "title": "Salary and Bank Details",
        "lines": [
            f"Employee Name   : {masked_name()}",
            f"Employee ID     : EMP-{random_ref()}",
            f"Bank Name       : XXXX Bank",
            f"Branch          : XXXX Branch",
            f"Account No      : {masked_account()}",
            f"IFSC Code       : XXXX0XXXXX",
            f"Account Type    : Savings",
            f"PAN             : {masked_pan()}",
            f"Monthly Salary  : {masked_amount()}",
            "",
            "Authorised by HR: XXXX",
        ],
    }

def _leave_record(idx):
    return {
        "title": "Leave Record",
        "lines": [
            f"Employee Name  : {masked_name()}",
            f"Employee ID    : EMP-{random_ref()}",
            f"Year           : 20XX",
            "",
            "Leave Type    | Allotted | Taken | Balance",
            "Casual Leave  |    XX    |   XX  |   XX",
            "Sick Leave    |    XX    |   XX  |   XX",
            "Earned Leave  |    XX    |   XX  |   XX",
            "Maternity/Paternity | XX |  XX  |   XX",
            "",
            f"Approved by   : {masked_name()}",
            f"Date          : {masked_date()}",
        ],
    }

def _attendance_record(idx):
    return {
        "title": "Attendance Record",
        "lines": [
            f"Employee Name  : {masked_name()}",
            f"Month/Year     : XX / 20XX",
            "",
            "Date  | In-Time | Out-Time | Hours | Status",
            "XX    | XX:XX   | XX:XX    | X.X   | Present",
            "XX    | XX:XX   | XX:XX    | X.X   | Present",
            "XX    | --      | --       | --    | Leave",
            "XX    | XX:XX   | XX:XX    | X.X   | Present",
            "",
            f"Total Working Days: XX   Present: XX   Absent: XX",
            f"Approved by: {masked_name()}",
        ],
    }

def _performance_review(idx):
    return {
        "title": "Performance Review",
        "lines": [
            f"Review Period  : Q{random.randint(1,4)} 20XX",
            f"Employee Name  : {masked_name()}",
            f"Designation    : XXXX",
            f"Manager        : {masked_name()}",
            "",
            "RATINGS (1-5):",
            "Quality of Work       : X",
            "Communication         : X",
            "Team Collaboration    : X",
            "Goal Achievement      : X",
            "Overall Rating        : X.X",
            "",
            "Comments: XXXX XXXX XXXX",
            f"Reviewer Signature: XXXX   Date: {masked_date()}",
        ],
    }

def _appraisal_letter(idx):
    return {
        "title": "Promotion / Appraisal Letter",
        "lines": [
            f"Ref: {random_ref()}   Date: {masked_date()}",
            "",
            f"To: {masked_name()}, EMP-{random_ref()}",
            "",
            "Dear XXXX,",
            "",
            "Based on your performance in 20XX, we are pleased to inform you of",
            "the following changes effective XXXX:",
            "",
            f"New Designation  : XXXX",
            f"Revised CTC      : {masked_amount()} per annum",
            f"Increment        : XX%",
            "",
            "HR Manager: XXXX",
        ],
    }

def _training_record(idx):
    return {
        "title": "Training & Certification Record",
        "lines": [
            f"Employee Name  : {masked_name()}",
            f"Training Name  : XXXX Certification Program",
            f"Provider       : XXXX Institute",
            f"Duration       : XX hours",
            f"Start Date     : {masked_date()}",
            f"End Date       : {masked_date()}",
            f"Score          : XX/100",
            f"Certificate No : {random_ref()}",
            "",
            f"Issued by      : XXXX   Date: {masked_date()}",
        ],
    }

def _warning_letter(idx):
    return {
        "title": "Warning / Disciplinary Letter",
        "lines": [
            f"Ref: {random_ref()}   Date: {masked_date()}",
            "",
            f"To: {masked_name()}",
            f"Department: XXXX",
            "",
            "Dear XXXX,",
            "",
            "This letter serves as a formal warning regarding: XXXX behaviour / misconduct.",
            "",
            "Incident Date  : {masked_date()}",
            "Incident Detail: XXXX XXXX XXXX",
            "",
            "Immediate corrective action is required failing which further disciplinary",
            "action will be taken.",
            "",
            f"HR Manager: XXXX   Date: {masked_date()}",
        ],
    }

def _resignation(idx):
    return {
        "title": "Resignation Letter",
        "lines": [
            f"Date        : {masked_date()}",
            f"From        : {masked_name()}, EMP-{random_ref()}",
            f"To          : {masked_name()}, HR Manager",
            "",
            "Subject: Resignation",
            "",
            "I hereby tender my resignation from the position of XXXX, effective",
            f"{masked_date()}, serving a notice period of XX days.",
            "",
            "I appreciate the opportunities provided and wish the organisation continued success.",
            "",
            f"Signature: XXXX   Date: {masked_date()}",
        ],
    }

def _exit_documents(idx):
    return {
        "title": "Exit Documents / Full & Final Settlement",
        "lines": [
            f"Employee Name  : {masked_name()}",
            f"Employee ID    : EMP-{random_ref()}",
            f"Last Working Day: {masked_date()}",
            "",
            "SETTLEMENT DETAILS:",
            f"  Basic Salary (XX days)   : {masked_amount()}",
            f"  Earned Leave Encashment  : {masked_amount()}",
            f"  Gratuity                 : {masked_amount()}",
            f"  Deductions               : {masked_amount()}",
            f"  Net Payable              : {masked_amount()}",
            "",
            "No Dues Certificate: Cleared",
            f"Processed by: {masked_name()}   Date: {masked_date()}",
        ],
    }


# ══════════════════════════════════════════════════════════════════════════════
# 2. PAYROLL & FINANCE DOCUMENTS
# ══════════════════════════════════════════════════════════════════════════════

def _salary_slip(idx):
    return {
        "title": "Salary Slip",
        "lines": [
            f"Month/Year     : XX / 20XX",
            f"Employee Name  : {masked_name()}",
            f"Employee ID    : EMP-{random_ref()}",
            f"Department     : XXXX",
            f"Designation    : XXXX",
            f"PAN            : {masked_pan()}",
            "",
            "EARNINGS              AMOUNT    DEDUCTIONS            AMOUNT",
            f"Basic                 {masked_amount()}  PF                    {masked_amount()}",
            f"HRA                   {masked_amount()}  ESI                   {masked_amount()}",
            f"Special Allowance     {masked_amount()}  TDS                   {masked_amount()}",
            f"Bonus                 {masked_amount()}  Professional Tax      {masked_amount()}",
            "",
            f"GROSS SALARY  : {masked_amount()}   NET SALARY: {masked_amount()}",
        ],
    }

def _payroll_register(idx):
    return {
        "title": "Payroll Register",
        "lines": [
            f"Payroll Month   : XX / 20XX",
            f"Generated By    : {masked_name()}",
            f"Ref No          : {random_ref()}",
            "",
            "EMP ID      | Employee Name  | Gross     | Deductions | Net",
            f"EMP-XXXX    | {masked_name()}| {masked_amount()} | {masked_amount()} | {masked_amount()}",
            f"EMP-XXXX    | {masked_name()}| {masked_amount()} | {masked_amount()} | {masked_amount()}",
            f"EMP-XXXX    | {masked_name()}| {masked_amount()} | {masked_amount()} | {masked_amount()}",
            "",
            f"Total Gross: {masked_amount()}   Total Net: {masked_amount()}",
            f"Authorised by: {masked_name()}",
        ],
    }

def _tax_document(idx):
    return {
        "title": "Tax Document / Form 16",
        "lines": [
            "FORM 16 — Certificate of Tax Deducted at Source",
            "",
            f"PAN of Deductee    : {masked_pan()}",
            f"Name of Deductee   : {masked_name()}",
            f"TAN of Deductor    : XXXX00000X",
            f"Name of Deductor   : XXXX Pvt. Ltd.",
            f"Assessment Year    : 20XX–20XX",
            "",
            f"Gross Salary       : {masked_amount()}",
            f"HRA Exemption      : {masked_amount()}",
            f"Standard Deduction : {masked_amount()}",
            f"Taxable Income     : {masked_amount()}",
            f"Tax Deducted       : {masked_amount()}",
            "",
            f"Issued by: XXXX   Date: {masked_date()}",
        ],
    }

def _tds_record(idx):
    return {
        "title": "TDS Record",
        "lines": [
            f"Quarter        : Q{random.randint(1,4)} 20XX",
            f"TAN            : XXXX00000X",
            f"Company        : XXXX Pvt. Ltd.",
            "",
            "PAN          | Deductee Name  | Payment  | TDS      | Challan",
            f"{masked_pan()} | {masked_name()} | {masked_amount()} | {masked_amount()} | {random_ref()}",
            f"{masked_pan()} | {masked_name()} | {masked_amount()} | {masked_amount()} | {random_ref()}",
            "",
            f"Total TDS Deposited: {masked_amount()}",
            f"Challan Date       : {masked_date()}",
        ],
    }

def _expense_claim(idx):
    return {
        "title": "Expense Reimbursement Claim",
        "lines": [
            f"Claim Ref      : {random_ref()}",
            f"Employee Name  : {masked_name()}",
            f"Date           : {masked_date()}",
            "",
            "Item           | Date       | Amount   | Receipt No",
            f"Travel         | {masked_date()} | {masked_amount()} | {random_ref()}",
            f"Hotel          | {masked_date()} | {masked_amount()} | {random_ref()}",
            f"Meals          | {masked_date()} | {masked_amount()} | {random_ref()}",
            "",
            f"Total Claim    : {masked_amount()}",
            f"Approved by    : {masked_name()}   Date: {masked_date()}",
        ],
    }

def _invoice(idx):
    return {
        "title": "Invoice",
        "lines": [
            f"Invoice No     : INV-{random_ref()}",
            f"Date           : {masked_date()}",
            f"Due Date       : {masked_date()}",
            "",
            f"Billed To      : XXXX Company, XXXX – XXXXXX",
            f"Billed By      : XXXX Pvt. Ltd.  GSTIN: {masked_gstin()}",
            "",
            "Item          | Qty | Unit Price | Total",
            f"XXXX Service  |  X  | {masked_amount()} | {masked_amount()}",
            f"XXXX Product  |  X  | {masked_amount()} | {masked_amount()}",
            "",
            f"Sub-Total    : {masked_amount()}",
            f"GST (18%)    : {masked_amount()}",
            f"Grand Total  : {masked_amount()}",
            "",
            f"Bank: XXXX  Acc: {masked_account()}  IFSC: XXXX0XXXXX",
        ],
    }

def _purchase_order(idx):
    return {
        "title": "Purchase Order",
        "lines": [
            f"PO Number      : PO-{random_ref()}",
            f"Date           : {masked_date()}",
            f"Vendor         : XXXX Suppliers Pvt. Ltd.",
            f"Buyer          : XXXX Pvt. Ltd.",
            "",
            "Item           | Qty | Rate      | Amount",
            f"XXXX Material  |  XX | {masked_amount()} | {masked_amount()}",
            f"XXXX Equipment |   X | {masked_amount()} | {masked_amount()}",
            "",
            f"Total          : {masked_amount()}",
            f"Delivery by    : {masked_date()}",
            f"Authorised by  : {masked_name()}",
        ],
    }

def _receipt(idx):
    return {
        "title": "Receipt",
        "lines": [
            f"Receipt No     : REC-{random_ref()}",
            f"Date           : {masked_date()}",
            f"Received from  : {masked_name()}",
            f"Amount         : {masked_amount()}",
            f"For            : XXXX Services / Products",
            f"Payment Mode   : XXXX (Cheque/NEFT/Cash)",
            f"Reference      : {random_ref()}",
            "",
            "Thank you for your payment.",
            f"Authorised by  : {masked_name()}",
        ],
    }

def _bank_statement(idx):
    return {
        "title": "Bank Statement",
        "lines": [
            f"Account Holder : {masked_name()}",
            f"Account Number : {masked_account()}",
            f"IFSC Code      : XXXX0XXXXX",
            f"Period         : XX/20XX – XX/20XX",
            "",
            "Date     | Description         | Debit     | Credit    | Balance",
            f"{masked_date()} | SALARY CREDIT    | --        | {masked_amount()} | {masked_amount()}",
            f"{masked_date()} | UPI PAYMENT      | {masked_amount()} | --        | {masked_amount()}",
            f"{masked_date()} | NEFT RECEIVED    | --        | {masked_amount()} | {masked_amount()}",
            f"{masked_date()} | ATM WITHDRAWAL   | {masked_amount()} | --        | {masked_amount()}",
            "",
            f"Closing Balance: {masked_amount()}",
        ],
    }

def _accounting_record(idx):
    return {
        "title": "Accounting Record - Ledger",
        "lines": [
            f"Ledger Name    : XXXX Account",
            f"Period         : XX/20XX",
            f"Ref No         : {random_ref()}",
            "",
            "Date     | Voucher No    | Particulars    | Debit     | Credit",
            f"{masked_date()} | {random_ref()} | XXXX           | {masked_amount()} | --",
            f"{masked_date()} | {random_ref()} | XXXX           | --        | {masked_amount()}",
            "",
            f"Total Debit  : {masked_amount()}",
            f"Total Credit : {masked_amount()}",
            f"Balance      : {masked_amount()}",
        ],
    }

def _budget_report(idx):
    return {
        "title": "Budget & Financial Report",
        "lines": [
            f"Report Period  : FY 20XX–20XX",
            f"Prepared By    : {masked_name()}",
            f"Date           : {masked_date()}",
            "",
            "Department     | Budget       | Actual       | Variance",
            f"XXXX           | {masked_amount()} | {masked_amount()} | {masked_amount()}",
            f"XXXX           | {masked_amount()} | {masked_amount()} | {masked_amount()}",
            f"XXXX           | {masked_amount()} | {masked_amount()} | {masked_amount()}",
            "",
            f"Total Budget   : {masked_amount()}",
            f"Total Actual   : {masked_amount()}",
            f"Net Variance   : {masked_amount()}",
        ],
    }


# ══════════════════════════════════════════════════════════════════════════════
# 3. COMPANY / LEGAL DOCUMENTS
# ══════════════════════════════════════════════════════════════════════════════

def _cert_incorporation(idx):
    return {
        "title": "Certificate of Incorporation",
        "lines": [
            "CERTIFICATE OF INCORPORATION",
            "",
            f"Company Name   : XXXX XXXX Pvt. Ltd.",
            f"CIN            : UXXXXX0000XPTCXXXXXX",
            f"Date of Incorp : {masked_date()}",
            f"Registered Off : XXXX, XXXX, India – XXXXXX",
            f"Type           : Private Limited Company",
            "",
            "Issued by Ministry of Corporate Affairs, Government of India",
            f"Certificate No : {random_ref()}",
        ],
    }

def _moa(idx):
    return {
        "title": "Memorandum & Articles of Association",
        "lines": [
            "MEMORANDUM OF ASSOCIATION",
            "",
            "1. Name Clause    : XXXX XXXX Pvt. Ltd.",
            "2. Situation Clause: The registered office is in XXXX, India.",
            "3. Objects Clause  : To carry on business of XXXX.",
            "4. Liability Clause: Liability of members is limited.",
            "5. Capital Clause  : Authorised capital is ₹XX,XX,XXX.",
            "",
            f"Subscribers: {masked_name()}, {masked_name()}",
            f"Date: {masked_date()}",
        ],
    }

def _business_reg(idx):
    return {
        "title": "Business Registration",
        "lines": [
            "BUSINESS REGISTRATION CERTIFICATE",
            "",
            f"Business Name  : XXXX Enterprises",
            f"Registration No: {random_ref()}",
            f"Type           : Partnership / Proprietorship / LLP",
            f"Date           : {masked_date()}",
            f"Address        : XXXX, XXXX – XXXXXX",
            f"Owner/Partner  : {masked_name()}",
            "",
            f"Issued by      : XXXX Registrar Office",
        ],
    }

def _gst_doc(idx):
    return {
        "title": "GST Certificate / Document",
        "lines": [
            "GST REGISTRATION CERTIFICATE",
            "",
            f"GSTIN          : {masked_gstin()}",
            f"Legal Name     : XXXX XXXX Pvt. Ltd.",
            f"Trade Name     : XXXX",
            f"Registration Date: {masked_date()}",
            f"Type           : Regular Taxpayer",
            f"State          : XXXX",
            f"Address        : XXXX, XXXX – XXXXXX",
            "",
            "Issued by GSTN",
        ],
    }

def _pan_tan(idx):
    return {
        "title": "PAN / TAN Document",
        "lines": [
            "PERMANENT ACCOUNT NUMBER CARD",
            "",
            f"PAN            : {masked_pan()}",
            f"Name           : XXXX XXXX PVT LTD",
            f"Date of Issue  : {masked_date()}",
            f"Father's Name  : XXXX (for individual) / NA",
            "",
            "TAN ALLOTMENT LETTER",
            "",
            f"TAN            : XXXX00000X",
            f"Name           : XXXX XXXX PVT LTD",
            f"Date           : {masked_date()}",
        ],
    }

def _license_doc(idx):
    return {
        "title": "License Document",
        "lines": [
            "BUSINESS / TRADE LICENSE",
            "",
            f"License No     : LIC-{random_ref()}",
            f"Holder Name    : XXXX XXXX Pvt. Ltd.",
            f"Type           : XXXX License",
            f"Issue Date     : {masked_date()}",
            f"Expiry Date    : {masked_date()}",
            f"Issuing Auth   : XXXX Municipal Corporation / Govt. of XXXX",
            "",
            "Conditions: XXXX XXXX XXXX",
        ],
    }

def _contract(idx):
    return {
        "title": "Contract / Agreement",
        "lines": [
            f"Contract No    : CON-{random_ref()}",
            f"Date           : {masked_date()}",
            f"Party A        : XXXX Pvt. Ltd.",
            f"Party B        : XXXX Corp.",
            "",
            "SCOPE OF WORK: XXXX XXXX XXXX services as described in Annex A.",
            f"CONTRACT VALUE : {masked_amount()}",
            f"DURATION       : {masked_date()} to {masked_date()}",
            "PAYMENT TERMS  : XX days net",
            "GOVERNING LAW  : Laws of India",
            "",
            f"Signed A: XXXX   Signed B: XXXX   Date: {masked_date()}",
        ],
    }

def _vendor_agreement(idx):
    return {
        "title": "Vendor Agreement",
        "lines": [
            f"Agreement Ref  : VA-{random_ref()}",
            f"Date           : {masked_date()}",
            f"Vendor Name    : XXXX Suppliers",
            f"GSTIN          : {masked_gstin()}",
            f"Buyer          : XXXX Pvt. Ltd.",
            "",
            "TERMS:",
            "1. Supply XXXX products as per specifications.",
            f"2. Price    : {masked_amount()} per unit",
            "3. Delivery : XX working days",
            "4. Payment  : XX days after delivery",
            "",
            f"Signatures: Vendor XXXX   Buyer XXXX   Date: {masked_date()}",
        ],
    }

def _insurance_doc(idx):
    return {
        "title": "Insurance Document",
        "lines": [
            "INSURANCE POLICY",
            "",
            f"Policy No      : POL-{random_ref()}",
            f"Insured        : {masked_name()} / XXXX Pvt. Ltd.",
            f"Type           : XXXX Insurance",
            f"Sum Insured    : {masked_amount()}",
            f"Premium        : {masked_amount()} per annum",
            f"Issue Date     : {masked_date()}",
            f"Expiry Date    : {masked_date()}",
            f"Insurer        : XXXX Insurance Co. Ltd.",
            "",
            f"Policy Holder Sign: XXXX   Agent Code: XXXX",
        ],
    }

def _ip_doc(idx):
    return {
        "title": "Intellectual Property Document",
        "lines": [
            "INTELLECTUAL PROPERTY ASSIGNMENT / PATENT",
            "",
            f"IP Ref No      : IP-{random_ref()}",
            f"Title          : XXXX Invention / XXXX Trademark",
            f"Owner          : XXXX XXXX Pvt. Ltd.",
            f"Inventor/Author: {masked_name()}",
            f"Filing Date    : {masked_date()}",
            f"Grant Date     : {masked_date()}",
            f"Registration No: {random_ref()}",
            "",
            "Description: XXXX XXXX XXXX (confidential)",
            f"Issued by: Intellectual Property India",
        ],
    }

def _board_meeting(idx):
    return {
        "title": "Board Meeting Record / Minutes",
        "lines": [
            f"Meeting No     : BM-{random_ref()}",
            f"Date           : {masked_date()}",
            f"Venue          : XXXX Conference Room",
            "",
            "Attendees:",
            f"  1. {masked_name()} — Director",
            f"  2. {masked_name()} — CFO",
            f"  3. {masked_name()} — Legal Counsel",
            "",
            "AGENDA:",
            "1. Approval of previous minutes",
            "2. Financial review Q{random.randint(1,4)} 20XX",
            "3. XXXX business matter",
            "",
            "RESOLUTIONS:",
            "  Resolution 1: XXXX approved unanimously.",
            "",
            f"Secretary: {masked_name()}   Chairperson: {masked_name()}",
        ],
    }


# ══════════════════════════════════════════════════════════════════════════════
# 4. CLIENT & VENDOR DOCUMENTS
# ══════════════════════════════════════════════════════════════════════════════

def _client_proposal(idx):
    return {
        "title": "Client Proposal",
        "lines": [
            f"Proposal No    : PROP-{random_ref()}",
            f"Date           : {masked_date()}",
            f"Client         : XXXX Company",
            f"Prepared By    : {masked_name()}, XXXX Pvt. Ltd.",
            "",
            "EXECUTIVE SUMMARY:",
            "XXXX Pvt. Ltd. proposes to provide XXXX services to meet your",
            "business objectives as outlined in the RFP dated XXXX.",
            "",
            "SCOPE        : XXXX XXXX XXXX",
            f"TIMELINE     : {masked_date()} – {masked_date()}",
            f"ESTIMATED COST: {masked_amount()}",
            "",
            "Terms & Conditions apply.",
        ],
    }

def _quotation(idx):
    return {
        "title": "Quotation",
        "lines": [
            f"Quotation No   : QUO-{random_ref()}",
            f"Date           : {masked_date()}",
            f"Valid Until    : {masked_date()}",
            f"Client         : XXXX Company",
            "",
            "Item           | Qty | Unit Price | Total",
            f"XXXX Service A |  X  | {masked_amount()} | {masked_amount()}",
            f"XXXX Product B |  X  | {masked_amount()} | {masked_amount()}",
            "",
            f"Sub-Total : {masked_amount()}",
            f"GST 18%   : {masked_amount()}",
            f"Total     : {masked_amount()}",
            "",
            f"Contact: {masked_email()} | {masked_phone()}",
        ],
    }

def _sow(idx):
    return {
        "title": "Statement of Work (SOW)",
        "lines": [
            f"SOW No         : SOW-{random_ref()}",
            f"Date           : {masked_date()}",
            f"Client         : XXXX Corp.",
            f"Vendor         : XXXX Pvt. Ltd.",
            "",
            "DELIVERABLES:",
            "  1. XXXX deliverable by {masked_date()}",
            "  2. XXXX report by {masked_date()}",
            "",
            f"CONTRACT VALUE : {masked_amount()}",
            f"MILESTONES     : M1 {masked_date()}, M2 {masked_date()}",
            "ACCEPTANCE CRITERIA: XXXX as per Annex B",
            "",
            f"Signed Client: XXXX   Vendor: XXXX   Date: {masked_date()}",
        ],
    }

def _delivery_doc(idx):
    return {
        "title": "Delivery Document",
        "lines": [
            f"Delivery Note  : DN-{random_ref()}",
            f"Date           : {masked_date()}",
            f"PO Reference   : PO-{random_ref()}",
            f"Delivered To   : XXXX Company, XXXX – XXXXXX",
            f"Delivered By   : XXXX Logistics",
            "",
            "Items Delivered:",
            f"  XXXX Item A — Qty: XX",
            f"  XXXX Item B — Qty: XX",
            "",
            "Received by    : {masked_name()}",
            f"Date           : {masked_date()}",
            f"Condition      : Good / XXXX",
        ],
    }

def _vendor_onboarding(idx):
    return {
        "title": "Vendor Onboarding Document",
        "lines": [
            f"Onboarding Ref : VO-{random_ref()}",
            f"Vendor Name    : XXXX Suppliers Pvt. Ltd.",
            f"GSTIN          : {masked_gstin()}",
            f"PAN            : {masked_pan()}",
            f"Contact Person : {masked_name()}",
            f"Email          : {masked_email()}",
            f"Phone          : {masked_phone()}",
            f"Bank Account   : {masked_account()}",
            f"IFSC           : XXXX0XXXXX",
            "",
            "Documents Submitted: GST, PAN, Bank Details, Trade License",
            f"Approved by    : {masked_name()}   Date: {masked_date()}",
        ],
    }


# ══════════════════════════════════════════════════════════════════════════════
# 5. IT & TECHNICAL DOCUMENTS
# ══════════════════════════════════════════════════════════════════════════════

def _software_doc(idx):
    return {
        "title": "Software Documentation",
        "lines": [
            f"System Name    : XXXX Application",
            f"Version        : {random_version()}",
            f"Author         : {masked_name()}",
            f"Date           : {masked_date()}",
            "",
            "1. OVERVIEW",
            "   XXXX is a system designed to XXXX. It provides XXXX functionality.",
            "",
            "2. MODULES",
            "   Module A: XXXX — handles XXXX",
            "   Module B: XXXX — handles XXXX",
            "",
            "3. INSTALLATION",
            "   Step 1: XXXX",
            "   Step 2: XXXX",
            "",
            "4. KNOWN ISSUES",
            "   Issue #XXXX: XXXX (Status: XXXX)",
        ],
    }

def _system_arch(idx):
    return {
        "title": "System Architecture Document",
        "lines": [
            f"Document       : System Architecture",
            f"System         : XXXX Platform",
            f"Version        : {random_version()}",
            f"Author         : {masked_name()}",
            f"Date           : {masked_date()}",
            "",
            "ARCHITECTURE OVERVIEW:",
            "  Frontend  : XXXX (React/Vue/Angular — MASKED)",
            "  Backend   : XXXX (Django/Node — MASKED)",
            "  Database  : XXXX (PostgreSQL/MySQL — MASKED)",
            "  Cache     : XXXX",
            "  Storage   : XXXX",
            "  CDN       : XXXX",
            "",
            "NETWORK TOPOLOGY: XXXX XXXX XXXX",
            f"Reviewed by: {masked_name()}",
        ],
    }

def _api_doc(idx):
    return {
        "title": "API Documentation",
        "lines": [
            f"API Name       : XXXX API",
            f"Version        : {random_version()}",
            f"Base URL       : https://api.xxxx.com/vX",
            f"Auth Method    : Bearer Token / API Key (MASKED)",
            "",
            "ENDPOINTS:",
            "  GET  /xxxx          — Returns list of XXXX",
            "  POST /xxxx          — Creates a new XXXX",
            "  PUT  /xxxx/{id}     — Updates XXXX by ID",
            "  DELETE /xxxx/{id}   — Deletes XXXX",
            "",
            "REQUEST HEADERS:",
            "  Authorization: Bearer XXXX",
            "  Content-Type : application/json",
            "",
            "SAMPLE RESPONSE: { 'id': 'XXXX', 'name': 'XXXX', 'status': 'XXXX' }",
        ],
    }

def _tech_spec(idx):
    return {
        "title": "Technical Specification",
        "lines": [
            f"Spec Title     : XXXX Feature Technical Spec",
            f"Version        : {random_version()}",
            f"Author         : {masked_name()}",
            f"Date           : {masked_date()}",
            "",
            "FUNCTIONAL REQUIREMENTS:",
            "  FR-1: System shall XXXX",
            "  FR-2: System shall XXXX",
            "",
            "NON-FUNCTIONAL REQUIREMENTS:",
            "  NFR-1: Response time < XX ms",
            "  NFR-2: Uptime > XX%",
            "",
            "DATABASE SCHEMA: XXXX (see Annex)",
            "SECURITY: XXXX encryption, XXXX auth",
        ],
    }

def _deployment_record(idx):
    return {
        "title": "Deployment Record",
        "lines": [
            f"Deployment ID  : DEP-{random_ref()}",
            f"Environment    : XXXX (Prod/Stage/Dev — MASKED)",
            f"Date/Time      : {masked_date()} XX:XX:XX",
            f"Deployed By    : {masked_name()}",
            f"Version        : {random_version()}",
            "",
            "CHANGES DEPLOYED:",
            "  - XXXX feature added",
            "  - XXXX bug fixed",
            "",
            "ROLLBACK PLAN  : XXXX",
            "STATUS         : SUCCESS / FAILED (MASKED)",
            f"Verified by    : {masked_name()}",
        ],
    }

def _security_policy(idx):
    return {
        "title": "Security Policy",
        "lines": [
            "INFORMATION SECURITY POLICY",
            "",
            f"Version        : {random_version()}",
            f"Effective Date : {masked_date()}",
            f"Approved By    : {masked_name()}",
            "",
            "1. PASSWORD POLICY",
            "   - Minimum length: XX characters",
            "   - Complexity: XXXX",
            "   - Expiry: XX days",
            "",
            "2. ACCESS CONTROL",
            "   - Role-based access: XXXX",
            "   - MFA required for: XXXX",
            "",
            "3. DATA CLASSIFICATION: Confidential / Internal / Public",
            "4. INCIDENT RESPONSE: XXXX procedure",
        ],
    }

def _access_control(idx):
    return {
        "title": "Access Control Record",
        "lines": [
            f"Record Date    : {masked_date()}",
            f"System         : XXXX Platform",
            "",
            "User           | Role        | Access Level | Status",
            f"{masked_name()} | Admin       | Full         | Active",
            f"{masked_name()} | Developer   | Read/Write   | Active",
            f"{masked_name()} | Viewer      | Read Only    | Inactive",
            "",
            "Last Reviewed  : {masked_date()}",
            f"Reviewed By    : {masked_name()}",
            "Next Review    : {masked_date()}",
        ],
    }

def _it_asset(idx):
    return {
        "title": "IT Asset Record",
        "lines": [
            f"Asset ID       : ASSET-{random_ref()}",
            f"Asset Type     : Laptop / Server / Monitor (MASKED)",
            f"Brand          : XXXX",
            f"Model          : XXXX XXXX",
            f"Serial No      : XXXX-XXXX-XXXX",
            f"Purchase Date  : {masked_date()}",
            f"Warranty Expiry: {masked_date()}",
            f"Assigned To    : {masked_name()}",
            f"Location       : XXXX Office, XXXX Floor",
            f"Status         : In Use / In Stock (MASKED)",
        ],
    }

def _backup_recovery(idx):
    return {
        "title": "Backup & Recovery Documentation",
        "lines": [
            "BACKUP AND RECOVERY PLAN",
            "",
            f"Version        : {random_version()}",
            f"Date           : {masked_date()}",
            f"Author         : {masked_name()}",
            "",
            "BACKUP SCHEDULE:",
            "  Full Backup    : Every XXXX at XX:XX",
            "  Incremental    : Every XXXX at XX:XX",
            "  Retention      : XX days",
            "",
            "STORAGE LOCATION: XXXX (S3/NAS — MASKED)",
            "ENCRYPTION      : XXXX",
            "",
            "RECOVERY PROCEDURE:",
            "  Step 1: XXXX",
            "  Step 2: XXXX",
            "RTO: XX hours   RPO: XX hours",
        ],
    }


# ══════════════════════════════════════════════════════════════════════════════
# 6. INTERNAL / OPERATIONAL DOCUMENTS
# ══════════════════════════════════════════════════════════════════════════════

def _company_policy(idx):
    return {
        "title": "Company Policy",
        "lines": [
            "COMPANY POLICY DOCUMENT",
            "",
            f"Policy Name    : XXXX Policy",
            f"Policy No      : POL-{random_ref()}",
            f"Effective Date : {masked_date()}",
            f"Approved By    : {masked_name()}",
            "",
            "PURPOSE: This policy establishes guidelines for XXXX.",
            "",
            "SCOPE: Applicable to all employees of XXXX Pvt. Ltd.",
            "",
            "POLICY DETAILS:",
            "  1. XXXX employees must XXXX.",
            "  2. In case of XXXX, follow XXXX procedure.",
            "  3. Violations will result in XXXX action.",
            "",
            "Review Cycle: XXXX   Next Review: {masked_date()}",
        ],
    }

def _sop(idx):
    return {
        "title": "SOP (Standard Operating Procedure)",
        "lines": [
            f"SOP No         : SOP-{random_ref()}",
            f"Title          : XXXX Standard Operating Procedure",
            f"Version        : {random_version()}",
            f"Effective Date : {masked_date()}",
            f"Author         : {masked_name()}",
            "",
            "PURPOSE: To define the procedure for XXXX.",
            "",
            "PROCEDURE:",
            "  Step 1: XXXX",
            "  Step 2: XXXX",
            "  Step 3: XXXX",
            "  Step 4: Verify and document results.",
            "",
            "RESPONSIBLE PERSON: {masked_name()}",
            "REVIEW DATE: {masked_date()}",
        ],
    }

def _employee_handbook(idx):
    return {
        "title": "Employee Handbook",
        "lines": [
            "EMPLOYEE HANDBOOK",
            f"Version: {random_version()}   Updated: {masked_date()}",
            "",
            "WELCOME TO XXXX PVT. LTD.",
            "",
            "SECTION 1 — COMPANY OVERVIEW",
            "  XXXX was founded in XXXX and operates in XXXX sector.",
            "",
            "SECTION 2 — CODE OF CONDUCT",
            "  Employees are expected to XXXX and maintain XXXX standards.",
            "",
            "SECTION 3 — LEAVE POLICY",
            "  Annual Leave: XX days",
            "  Sick Leave  : XX days",
            "",
            "SECTION 4 — GRIEVANCE REDRESSAL",
            "  Contact XXXX at {masked_email()}",
        ],
    }

def _meeting_minutes(idx):
    return {
        "title": "Meeting Minutes",
        "lines": [
            f"Meeting Ref    : MOM-{random_ref()}",
            f"Date           : {masked_date()}",
            f"Venue          : XXXX",
            f"Chairperson    : {masked_name()}",
            "",
            "ATTENDEES:",
            f"  {masked_name()}, {masked_name()}, {masked_name()}",
            "",
            "AGENDA ITEMS:",
            "  1. Review of XXXX — Discussion: XXXX — Decision: XXXX",
            "  2. Update on XXXX — Discussion: XXXX — Decision: XXXX",
            "",
            "ACTION ITEMS:",
            f"  {masked_name()} to complete XXXX by {masked_date()}",
            "",
            f"Next Meeting   : {masked_date()}   Prepared By: {masked_name()}",
        ],
    }

def _project_plan(idx):
    return {
        "title": "Project Plan",
        "lines": [
            f"Project Name   : XXXX Project",
            f"Project ID     : PROJ-{random_ref()}",
            f"PM             : {masked_name()}",
            f"Start Date     : {masked_date()}",
            f"End Date       : {masked_date()}",
            "",
            "MILESTONES:",
            f"  M1 – XXXX Phase     : {masked_date()}",
            f"  M2 – XXXX Phase     : {masked_date()}",
            f"  M3 – Testing        : {masked_date()}",
            f"  M4 – Go Live        : {masked_date()}",
            "",
            f"BUDGET        : {masked_amount()}",
            "RISKS         : XXXX, XXXX",
            f"Approved By   : {masked_name()}",
        ],
    }

def _project_report(idx):
    return {
        "title": "Project Report",
        "lines": [
            f"Project        : XXXX Project",
            f"Report Period  : {masked_date()} – {masked_date()}",
            f"Prepared By    : {masked_name()}",
            "",
            "STATUS         : On Track / Delayed (MASKED)",
            "COMPLETION     : XX%",
            "",
            "ACHIEVEMENTS:",
            "  - XXXX milestone delivered",
            "  - XXXX issue resolved",
            "",
            "ISSUES/RISKS:",
            "  - XXXX risk identified — Mitigation: XXXX",
            "",
            f"Next Steps     : XXXX   Due: {masked_date()}",
        ],
    }

def _training_material(idx):
    return {
        "title": "Training Material",
        "lines": [
            f"Module         : XXXX Training Module {idx}",
            f"Version        : {random_version()}",
            f"Prepared By    : {masked_name()}",
            f"Date           : {masked_date()}",
            "",
            "LEARNING OBJECTIVES:",
            "  1. Understand XXXX concepts.",
            "  2. Apply XXXX in daily work.",
            "",
            "CONTENT OUTLINE:",
            "  Section 1 : XXXX (XX minutes)",
            "  Section 2 : XXXX (XX minutes)",
            "  Section 3 : Hands-on exercise (XX minutes)",
            "",
            "ASSESSMENT: XX multiple choice questions",
            "PASSING SCORE: XX%",
        ],
    }

def _audit_report(idx):
    return {
        "title": "Audit Report",
        "lines": [
            f"Audit Ref      : AUD-{random_ref()}",
            f"Audit Type     : Internal / External (MASKED)",
            f"Period         : {masked_date()} – {masked_date()}",
            f"Auditor        : {masked_name()}",
            "",
            "SCOPE: XXXX processes, XXXX department",
            "",
            "FINDINGS:",
            "  1. Observation: XXXX — Risk: XXXX — Recommendation: XXXX",
            "  2. Observation: XXXX — Risk: XXXX — Recommendation: XXXX",
            "",
            "COMPLIANCE STATUS: XX% compliant",
            f"Management Response: {masked_name()} – XXXX",
            f"Report Date    : {masked_date()}",
        ],
    }

def _compliance_record(idx):
    return {
        "title": "Compliance Record",
        "lines": [
            f"Compliance Area : XXXX Regulation / ISO XXXX",
            f"Period          : {masked_date()} – {masked_date()}",
            f"Responsible     : {masked_name()}",
            "",
            "REQUIREMENTS:",
            "  REQ-1: XXXX — Status: Compliant",
            "  REQ-2: XXXX — Status: Compliant",
            "  REQ-3: XXXX — Status: In Progress",
            "",
            f"Overall Compliance: XX%",
            f"Last Review    : {masked_date()}",
            f"Next Review    : {masked_date()}",
            f"Signed off by  : {masked_name()}",
        ],
    }


# ══════════════════════════════════════════════════════════════════════════════
# 7. SENSITIVE / CONFIDENTIAL RECORDS
# ══════════════════════════════════════════════════════════════════════════════

def _personal_info(idx):
    return {
        "title": "Employee Personal Information",
        "lines": [
            "CONFIDENTIAL — PERSONAL INFORMATION RECORD",
            "",
            f"Employee Name  : {masked_name()}",
            f"Employee ID    : EMP-{random_ref()}",
            f"DOB            : {masked_date()}",
            f"Gender         : XXXX",
            f"Nationality    : XXXX",
            f"Marital Status : XXXX",
            f"Emergency Contact: {masked_name()} — {masked_phone()}",
            f"Medical Conditions: XXXX (MASKED)",
            f"Blood Group    : XX",
            "",
            "ACCESS: HR ONLY",
        ],
    }

def _financial_info(idx):
    return {
        "title": "Confidential Financial Information",
        "lines": [
            "CONFIDENTIAL — FINANCIAL INFORMATION",
            "",
            f"Entity         : XXXX Pvt. Ltd.",
            f"Period         : FY 20XX–20XX",
            "",
            f"Revenue        : {masked_amount()}",
            f"EBITDA         : {masked_amount()}",
            f"Net Profit     : {masked_amount()}",
            f"Total Assets   : {masked_amount()}",
            f"Total Liabilities: {masked_amount()}",
            f"Cash Position  : {masked_amount()}",
            "",
            "CLASSIFICATION: STRICTLY CONFIDENTIAL",
            "NOT FOR DISTRIBUTION",
        ],
    }

def _confidential_contract(idx):
    return {
        "title": "Confidential Contract",
        "lines": [
            "STRICTLY CONFIDENTIAL",
            "",
            f"Contract Ref   : CC-{random_ref()}",
            f"Date           : {masked_date()}",
            f"Party A        : XXXX Pvt. Ltd.",
            f"Party B        : XXXX Corp. (MASKED)",
            "",
            "TERMS: CONFIDENTIAL — details masked.",
            f"Value          : {masked_amount()}",
            f"Duration       : {masked_date()} – {masked_date()}",
            "",
            "This document contains trade secrets and confidential business terms.",
            "Unauthorised disclosure is prohibited.",
            "",
            f"Signed: XXXX   Date: {masked_date()}",
        ],
    }

def _customer_info(idx):
    return {
        "title": "Customer Information Record",
        "lines": [
            "CONFIDENTIAL — CUSTOMER RECORD",
            "",
            f"Customer ID    : CUST-{random_ref()}",
            f"Name           : {masked_name()}",
            f"Company        : XXXX Corp.",
            f"Email          : {masked_email()}",
            f"Phone          : {masked_phone()}",
            f"Address        : XXXX, XXXX – XXXXXX",
            f"GSTIN          : {masked_gstin()}",
            f"Account Since  : {masked_date()}",
            f"Credit Limit   : {masked_amount()}",
            "",
            "ACCESS: SALES TEAM ONLY",
        ],
    }

def _business_strategy(idx):
    return {
        "title": "Business Strategy Document",
        "lines": [
            "CONFIDENTIAL — BUSINESS STRATEGY",
            "",
            f"Period         : FY 20XX–20XX",
            f"Prepared By    : {masked_name()}",
            f"Date           : {masked_date()}",
            "",
            "STRATEGIC PILLARS:",
            "  1. XXXX growth in XXXX segment",
            "  2. Expansion into XXXX geography",
            "  3. XXXX cost optimisation",
            "  4. Digital transformation via XXXX",
            "",
            f"Revenue Target : {masked_amount()}",
            "KEY RISKS      : XXXX, XXXX",
            "",
            "CLASSIFICATION : BOARD CONFIDENTIAL",
        ],
    }

def _trade_secret(idx):
    return {
        "title": "Trade Secret Document",
        "lines": [
            "TRADE SECRET — PROPRIETARY INFORMATION",
            "",
            f"Ref No         : TS-{random_ref()}",
            f"Subject        : XXXX Proprietary Formula / Process",
            f"Owner          : XXXX Pvt. Ltd.",
            f"Date Created   : {masked_date()}",
            "",
            "DESCRIPTION    : XXXX (FULLY MASKED — CONFIDENTIAL)",
            "CLASSIFICATION : HIGHLY CONFIDENTIAL",
            "ACCESS         : AUTHORISED PERSONNEL ONLY",
            "",
            "Disclosure without authorisation is a legal offence.",
        ],
    }

def _password_record(idx):
    return {
        "title": "Password / Access Record (Masked)",
        "lines": [
            "CONFIDENTIAL — ACCESS CREDENTIALS RECORD",
            "",
            f"Date           : {masked_date()}",
            f"Maintained By  : {masked_name()}",
            "",
            "System         | Username     | Password  | Last Changed",
            "XXXX Portal    | xxxx_user    | ********* | {masked_date()}",
            "XXXX Database  | db_xxxx      | ********* | {masked_date()}",
            "XXXX Server    | srv_xxxx     | ********* | {masked_date()}",
            "",
            "NOTE: Actual passwords are stored in XXXX vault system.",
            "This record is MASKED and for audit reference only.",
            "ACCESS: IT ADMIN ONLY",
        ],
    }

def _security_compliance(idx):
    return {
        "title": "Security & Compliance Report",
        "lines": [
            f"Report Ref     : SCR-{random_ref()}",
            f"Period         : {masked_date()} – {masked_date()}",
            f"Prepared By    : {masked_name()}",
            "",
            "SECURITY INCIDENTS:",
            "  INC-XXXX: XXXX — Resolved {masked_date()}",
            "  INC-XXXX: XXXX — In Progress",
            "",
            "COMPLIANCE STATUS:",
            "  ISO 27001  : XX% compliant",
            "  GDPR/PDPA  : XX% compliant",
            "  SOC 2      : XX% compliant",
            "",
            "NEXT AUDIT     : {masked_date()}",
            f"CISO Sign-off  : {masked_name()}",
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# MASTER DOCUMENT LIST  (100 unique templates × 10 instances each = 1000 docs)
# ─────────────────────────────────────────────────────────────────────────────

TEMPLATE_MAP = [
    # (category_folder, filename_prefix, ext, content_fn)
    # ── Employee (19 types)
    ("1_Employee",        "resume",                  "pdf",  _employee_resume),
    ("1_Employee",        "job_application",         "pdf",  _employee_job_application),
    ("1_Employee",        "offer_letter",            "pdf",  _offer_letter),
    ("1_Employee",        "appointment_letter",      "pdf",  _appointment_letter),
    ("1_Employee",        "employment_agreement",    "docx", _employment_agreement),
    ("1_Employee",        "nda",                     "docx", _nda),
    ("1_Employee",        "id_proof",                "pdf",  _id_proof),
    ("1_Employee",        "educational_certificate", "pdf",  _edu_certificate),
    ("1_Employee",        "experience_letter",       "pdf",  _experience_letter),
    ("1_Employee",        "joining_form",            "pdf",  _joining_form),
    ("1_Employee",        "salary_bank_details",     "xlsx", _salary_bank_details),
    ("1_Employee",        "leave_record",            "xlsx", _leave_record),
    ("1_Employee",        "attendance_record",       "xlsx", _attendance_record),
    ("1_Employee",        "performance_review",      "pdf",  _performance_review),
    ("1_Employee",        "appraisal_letter",        "pdf",  _appraisal_letter),
    ("1_Employee",        "training_record",         "pdf",  _training_record),
    ("1_Employee",        "warning_letter",          "pdf",  _warning_letter),
    ("1_Employee",        "resignation_letter",      "pdf",  _resignation),
    ("1_Employee",        "exit_ffs_document",       "pdf",  _exit_documents),
    # ── Payroll & Finance (11 types)
    ("2_Payroll_Finance", "salary_slip",             "pdf",  _salary_slip),
    ("2_Payroll_Finance", "payroll_register",        "xlsx", _payroll_register),
    ("2_Payroll_Finance", "tax_form16",              "pdf",  _tax_document),
    ("2_Payroll_Finance", "tds_record",              "xlsx", _tds_record),
    ("2_Payroll_Finance", "expense_claim",           "pdf",  _expense_claim),
    ("2_Payroll_Finance", "invoice",                 "pdf",  _invoice),
    ("2_Payroll_Finance", "purchase_order",          "pdf",  _purchase_order),
    ("2_Payroll_Finance", "receipt",                 "pdf",  _receipt),
    ("2_Payroll_Finance", "bank_statement",          "pdf",  _bank_statement),
    ("2_Payroll_Finance", "accounting_ledger",       "xlsx", _accounting_record),
    ("2_Payroll_Finance", "budget_report",           "xlsx", _budget_report),
    # ── Company / Legal (12 types)
    ("3_Company_Legal",   "cert_incorporation",      "pdf",  _cert_incorporation),
    ("3_Company_Legal",   "moa",                     "pdf",  _moa),
    ("3_Company_Legal",   "business_registration",   "pdf",  _business_reg),
    ("3_Company_Legal",   "gst_certificate",         "pdf",  _gst_doc),
    ("3_Company_Legal",   "pan_tan_document",        "pdf",  _pan_tan),
    ("3_Company_Legal",   "license",                 "pdf",  _license_doc),
    ("3_Company_Legal",   "contract",                "docx", _contract),
    ("3_Company_Legal",   "vendor_agreement",        "docx", _vendor_agreement),
    ("3_Company_Legal",   "insurance_policy",        "pdf",  _insurance_doc),
    ("3_Company_Legal",   "ip_document",             "pdf",  _ip_doc),
    ("3_Company_Legal",   "board_meeting_minutes",   "docx", _board_meeting),
    ("3_Company_Legal",   "client_agreement",        "docx", _contract),      # reuse contract fn
    # ── Client & Vendor (9 types)
    ("4_Client_Vendor",   "client_proposal",         "pdf",  _client_proposal),
    ("4_Client_Vendor",   "quotation",               "pdf",  _quotation),
    ("4_Client_Vendor",   "sow",                     "pdf",  _sow),
    ("4_Client_Vendor",   "client_contract",         "docx", _contract),
    ("4_Client_Vendor",   "client_purchase_order",   "pdf",  _purchase_order),
    ("4_Client_Vendor",   "client_invoice",          "pdf",  _invoice),
    ("4_Client_Vendor",   "delivery_document",       "pdf",  _delivery_doc),
    ("4_Client_Vendor",   "vendor_onboarding",       "pdf",  _vendor_onboarding),
    ("4_Client_Vendor",   "client_nda",              "docx", _nda),
    # ── IT & Technical (9 types)
    ("5_IT_Technical",    "software_doc",            "pdf",  _software_doc),
    ("5_IT_Technical",    "system_architecture",     "pdf",  _system_arch),
    ("5_IT_Technical",    "api_documentation",       "pdf",  _api_doc),
    ("5_IT_Technical",    "technical_spec",          "pdf",  _tech_spec),
    ("5_IT_Technical",    "deployment_record",       "pdf",  _deployment_record),
    ("5_IT_Technical",    "security_policy",         "pdf",  _security_policy),
    ("5_IT_Technical",    "access_control_record",   "xlsx", _access_control),
    ("5_IT_Technical",    "it_asset_record",         "xlsx", _it_asset),
    ("5_IT_Technical",    "backup_recovery_doc",     "pdf",  _backup_recovery),
    # ── Internal / Operational (9 types)
    ("6_Internal_Ops",    "company_policy",          "pdf",  _company_policy),
    ("6_Internal_Ops",    "sop",                     "pdf",  _sop),
    ("6_Internal_Ops",    "employee_handbook",       "pdf",  _employee_handbook),
    ("6_Internal_Ops",    "meeting_minutes",         "pdf",  _meeting_minutes),
    ("6_Internal_Ops",    "project_plan",            "pdf",  _project_plan),
    ("6_Internal_Ops",    "project_report",          "pdf",  _project_report),
    ("6_Internal_Ops",    "training_material",       "pdf",  _training_material),
    ("6_Internal_Ops",    "audit_report",            "pdf",  _audit_report),
    ("6_Internal_Ops",    "compliance_record",       "pdf",  _compliance_record),
    # ── Sensitive / Confidential (8 types)  → total templates = 87 → ×11 or ×12 = 1000
    ("7_Sensitive",       "employee_personal_info",  "pdf",  _personal_info),
    ("7_Sensitive",       "confidential_financials", "pdf",  _financial_info),
    ("7_Sensitive",       "confidential_contract",   "docx", _confidential_contract),
    ("7_Sensitive",       "customer_info",           "pdf",  _customer_info),
    ("7_Sensitive",       "business_strategy",       "pdf",  _business_strategy),
    ("7_Sensitive",       "trade_secret",            "pdf",  _trade_secret),
    ("7_Sensitive",       "password_access_record",  "pdf",  _password_record),
    ("7_Sensitive",       "security_compliance_rpt", "pdf",  _security_compliance),
]

# Also add PNG scans for a subset (ID cards, certificates, etc.)
PNG_TEMPLATES = [
    ("1_Employee",        "id_proof_scan",           "png",  _id_proof),
    ("1_Employee",        "edu_cert_scan",           "png",  _edu_certificate),
    ("2_Payroll_Finance", "salary_slip_scan",        "png",  _salary_slip),
    ("3_Company_Legal",   "gst_cert_scan",           "png",  _gst_doc),
    ("3_Company_Legal",   "pan_scan",                "png",  _pan_tan),
    ("3_Company_Legal",   "license_scan",            "png",  _license_doc),
    ("4_Client_Vendor",   "invoice_scan",            "png",  _invoice),
    ("2_Payroll_Finance", "receipt_scan",            "png",  _receipt),
    ("7_Sensitive",       "id_card_scan",            "png",  _id_proof),
    ("1_Employee",        "joining_form_scan",       "png",  _joining_form),
    ("3_Company_Legal",   "cert_incorp_scan",        "png",  _cert_incorporation),
    ("2_Payroll_Finance", "bank_stmt_scan",          "png",  _bank_statement),
    ("1_Employee",        "offer_letter_scan",       "png",  _offer_letter),
]

ALL_TEMPLATES = TEMPLATE_MAP + PNG_TEMPLATES  # 87 + 13 = 100


# ─────────────────────────────────────────────────────────────────────────────
# FILE GENERATION FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def _make_pdf(path: Path, data: dict):
    if not HAS_REPORTLAB:
        path.write_text("\n".join(data["lines"]), encoding="utf-8")
        return

    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        rightMargin=60, leftMargin=60,
        topMargin=60, bottomMargin=60,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleCustom",
        parent=styles["Title"],
        fontSize=14,
        textColor=colors.HexColor("#1a1a2e"),
        spaceAfter=12,
    )
    normal_style = ParagraphStyle(
        "NormalCustom",
        parent=styles["Normal"],
        fontSize=9,
        leading=14,
        textColor=colors.HexColor("#2d2d2d"),
    )
    body = []

    # Header banner
    banner_data = [["MASKED DUPLICATE — FOR TESTING PURPOSES ONLY"]]
    banner = Table(banner_data, colWidths=[6.5 * inch])
    banner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#e8f0fe")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#1a1a2e")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    body.append(banner)
    body.append(Spacer(1, 12))
    body.append(Paragraph(data["title"], title_style))
    body.append(Spacer(1, 8))

    for line in data["lines"]:
        if line.strip() == "":
            body.append(Spacer(1, 6))
        else:
            body.append(Paragraph(line.replace("<", "&lt;").replace(">", "&gt;"), normal_style))

    body.append(Spacer(1, 20))
    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontSize=7,
        textColor=colors.grey,
    )
    body.append(Paragraph(
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | "
        "All data is masked and fictitious | Document ID: XXXX",
        footer_style
    ))
    doc.build(body)


def _make_docx(path: Path, data: dict):
    if not HAS_DOCX:
        path.write_text("\n".join(data["lines"]), encoding="utf-8")
        return

    doc = DocxDocument()
    # Banner paragraph
    banner = doc.add_paragraph()
    run = banner.add_run("MASKED DUPLICATE — FOR TESTING PURPOSES ONLY")
    run.bold = True
    run.font.size = Pt(8)
    run.font.color.rgb = RGBColor(0x1a, 0x1a, 0x2e)

    # Title
    heading = doc.add_heading(data["title"], level=1)
    heading.runs[0].font.size = Pt(14)

    doc.add_paragraph()
    for line in data["lines"]:
        p = doc.add_paragraph()
        if line.strip() == "":
            continue
        run = p.add_run(line)
        run.font.size = Pt(9)

    doc.add_paragraph()
    footer_p = doc.add_paragraph()
    footer_run = footer_p.add_run(
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | "
        "All data masked | Document ID: XXXX"
    )
    footer_run.font.size = Pt(7)
    footer_run.font.color.rgb = RGBColor(0x80, 0x80, 0x80)

    doc.save(str(path))


def _make_xlsx(path: Path, data: dict):
    if not HAS_OPENPYXL:
        path.write_text("\n".join(data["lines"]), encoding="utf-8")
        return

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = data["title"][:31]

    # Banner row
    ws.merge_cells("A1:F1")
    ws["A1"] = "MASKED DUPLICATE — FOR TESTING PURPOSES ONLY"
    ws["A1"].font = Font(bold=True, size=9, color="1A1A2E")
    ws["A1"].fill = PatternFill("solid", fgColor="E8F0FE")
    ws["A1"].alignment = Alignment(horizontal="center")

    # Title row
    ws.merge_cells("A2:F2")
    ws["A2"] = data["title"]
    ws["A2"].font = Font(bold=True, size=12)

    row = 4
    for line in data["lines"]:
        if "|" in line and not line.startswith("|"):
            # Table-like row — split by pipe
            cells = [c.strip() for c in line.split("|")]
            for col, val in enumerate(cells, start=1):
                cell = ws.cell(row=row, column=col, value=val)
                cell.font = Font(size=9)
        else:
            ws.merge_cells(f"A{row}:F{row}")
            cell = ws.cell(row=row, column=1, value=line)
            cell.font = Font(size=9)
        row += 1

    # Footer
    row += 1
    ws.merge_cells(f"A{row}:F{row}")
    footer = ws.cell(row=row, column=1,
                     value=f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | All data masked")
    footer.font = Font(size=7, color="808080")

    # Column widths
    ws.column_dimensions["A"].width = 30
    for col in ["B", "C", "D", "E", "F"]:
        ws.column_dimensions[col].width = 18

    wb.save(str(path))


def _make_png(path: Path, data: dict):
    width, height = 794, 1123  # A4 at 96dpi
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Try to use a system font, fall back to default
    try:
        font_title = ImageFont.truetype("arial.ttf", 18)
        font_body  = ImageFont.truetype("arial.ttf", 12)
        font_small = ImageFont.truetype("arial.ttf", 9)
    except Exception:
        font_title = ImageFont.load_default()
        font_body  = font_title
        font_small = font_title

    # Banner
    draw.rectangle([(0, 0), (width, 32)], fill=(232, 240, 254))
    draw.text((10, 8), "MASKED DUPLICATE — FOR TESTING PURPOSES ONLY",
              fill=(26, 26, 46), font=font_body)

    # Watermark
    draw.text((200, 500), "MASKED", fill=(220, 220, 220), font=font_title)

    # Document border
    draw.rectangle([(20, 40), (width - 20, height - 20)], outline=(200, 200, 200), width=1)

    # Title
    draw.text((40, 55), data["title"], fill=(26, 26, 46), font=font_title)

    # Content lines
    y = 90
    for line in data["lines"]:
        if y > height - 50:
            break
        draw.text((40, y), line, fill=(45, 45, 45), font=font_body)
        y += 18

    # Footer
    draw.text((40, height - 30),
              f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | All data masked",
              fill=(150, 150, 150), font=font_small)

    img.save(str(path), "PNG", optimize=True)


def generate_file(out_path: Path, ext: str, data: dict):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if ext == "pdf":
        _make_pdf(out_path, data)
    elif ext == "docx":
        _make_docx(out_path, data)
    elif ext == "xlsx":
        _make_xlsx(out_path, data)
    elif ext == "png":
        _make_png(out_path, data)
    else:
        out_path.write_text("\n".join(data["lines"]), encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    TARGET = 1000
    total_templates = len(ALL_TEMPLATES)

    # Calculate how many instances of each template to generate
    # so we hit exactly 1000 files
    base_count, remainder = divmod(TARGET, total_templates)
    counts = [base_count + (1 if i < remainder else 0) for i in range(total_templates)]

    print(f"Templates     : {total_templates}")
    print(f"Files/template: ~{base_count}–{base_count + 1}")
    print(f"Total target  : {TARGET}")
    print(f"Output dir    : {OUTPUT_DIR.resolve()}")
    print()

    generated = 0
    for tmpl_idx, ((category, prefix, ext, content_fn), count) in enumerate(
        zip(ALL_TEMPLATES, counts)
    ):
        for i in range(1, count + 1):
            filename = f"{prefix}_{i:04d}.{ext}"
            out_path = OUTPUT_DIR / category / filename
            data = content_fn(i)
            try:
                generate_file(out_path, ext, data)
                generated += 1
                if generated % 50 == 0 or generated == TARGET:
                    print(f"  [{generated:4d}/{TARGET}] {out_path}")
            except Exception as e:
                print(f"  ERROR [{generated}] {out_path}: {e}")

    print()
    print(f"Done! {generated} files generated in '{OUTPUT_DIR}/'")
    print()
    # Summary
    print("SUMMARY BY CATEGORY:")
    for cat_dir in sorted(OUTPUT_DIR.iterdir()):
        if cat_dir.is_dir():
            files = list(cat_dir.glob("*.*"))
            print(f"  {cat_dir.name:30s}  {len(files):4d} files")


if __name__ == "__main__":
    main()
