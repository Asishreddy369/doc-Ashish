import io
from unittest.mock import patch
from django.test import TestCase
from django.test import override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from .models import Document
from .folder_planner import build_folder_plan
from .processing import process_document_extraction

class DocumentManagementApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_upload_queues_content_first_processing_without_trusting_selected_category(self):
        test_file = SimpleUploadedFile(
            "aadhaar_card.pdf",
            b"Aadhaar document payload sample",
            content_type="application/pdf"
        )
        url = reverse('document-upload')
        response = self.client.post(url, {
            'files': test_file,
            'category': 'Aadhaar'
        }, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        doc_data = response.data['documents'][0]
        self.assertEqual(doc_data['category'], 'Unclassified')
        self.assertEqual(doc_data['status'], 'PROCESSING')
        self.assertEqual(doc_data['classifier_details']['classification_status'], 'queued')
        self.assertEqual(doc_data['classifier_details']['classification_mode'], 'content_first')
        self.assertFalse(doc_data['classifier_details']['classification_uses_filename'])
        self.assertEqual(doc_data['original_name'], 'aadhaar_card.pdf')

    def test_user_defined_folder_plan_routes_to_mapped_folder(self):
        plan = build_folder_plan(
            [{"name": "bank_statement.pdf", "relative_path": "bank_statement.pdf", "category": "Bank Statement"}],
            mode="user_defined",
            category_map={"Bank Statement": "Bank Statements"},
            folder_options={
                "root_folder": "Company Documents",
                "folders": ["GST", "Bank Statements", "Unclassified"],
                "fallback_folder": "Unclassified",
                "category_folder_map": {"Bank Statement": "Bank Statements"},
            },
        )

        route = plan["routes"][0]
        self.assertEqual(route["target_folder"], "Company Documents/Bank Statements")
        self.assertEqual(plan["summary"]["unmatched_count"], 0)

    def test_imported_nested_folder_structure_matches_leaf_folder(self):
        plan = build_folder_plan(
            [
                {"name": "gst_certificate.pdf", "relative_path": "gst_certificate.pdf", "category": "GST Certificate"},
                {"name": "unknown_file.pdf", "relative_path": "unknown_file.pdf", "category": "Technical Resource"},
            ],
            mode="user_defined",
            category_map={"GST Certificate": "Land and Building/EPC Contracts"},
            folder_options={
                "root_folder": "Company Documents",
                "folders": ["Compliance/GST", "Finance/Invoices", "Unclassified"],
                "fallback_folder": "Unclassified",
                "category_folder_map": {"GST Certificate": "GST"},
            },
        )

        routes = {route["file"]: route for route in plan["routes"]}
        self.assertEqual(routes["gst_certificate.pdf"]["target_folder"], "Company Documents/Compliance/GST")
        self.assertEqual(routes["unknown_file.pdf"]["target_folder"], "Company Documents/Unclassified")
        self.assertEqual(plan["summary"]["unmatched_count"], 1)

    def test_user_defined_tree_keeps_imported_empty_nested_folders_in_order(self):
        plan = build_folder_plan(
            [
                {"name": "gst_challan.pdf", "relative_path": "gst_challan.pdf", "category": "GST Certificate"},
                {"name": "solar_contract.pdf", "relative_path": "solar_contract.pdf", "category": "Power"},
            ],
            mode="user_defined",
            folder_options={
                "root_folder": "Vetta",
                "folders": [
                    "Incorporation and MCA related",
                    "Insurance",
                    "Land and Building",
                    "Loans and Debt",
                    "Power",
                    "Power/Solar power",
                    "Power/Electricity Board Licenses",
                    "Share Capital and Other Instruments issued",
                    "Tax",
                    "Tax/Service Tax",
                    "Tax/VAT",
                    "Tax/GST",
                    "Tax/TDS",
                    "Tax/Income Tax",
                    "Accounts and Bank related Documents",
                    "Audit",
                    "Certificates and Registration",
                    "Unclassified",
                ],
                "fallback_folder": "Unclassified",
                "category_folder_map": {
                    "GST Certificate": "Tax/GST",
                    "Power": "Power",
                },
            },
        )

        tree_lines = [(line["name"], line["depth"]) for line in plan["tree_lines"]]
        self.assertEqual(tree_lines[:10], [
            ("Vetta", 0),
            ("Incorporation and MCA related", 1),
            ("Insurance", 1),
            ("Land and Building", 1),
            ("Loans and Debt", 1),
            ("Power", 1),
            ("Solar power", 2),
            ("Electricity Board Licenses", 2),
            ("Share Capital and Other Instruments issued", 1),
            ("Tax", 1),
        ])
        self.assertIn(("Service Tax", 2), tree_lines)
        self.assertIn(("VAT", 2), tree_lines)
        self.assertIn(("GST", 2), tree_lines)
        self.assertIn(("TDS", 2), tree_lines)
        self.assertIn(("Income Tax", 2), tree_lines)

    def test_upload_with_user_defined_folder_structure(self):
        test_file = SimpleUploadedFile(
            "bank_statement.pdf",
            b"Bank statement document payload sample",
            content_type="application/pdf"
        )
        url = reverse('document-upload')
        response = self.client.post(url, {
            'files': test_file,
            'category': 'Bank Statement',
            'organization_mode': 'user_defined',
            'category_map': '{"Bank Statement":"Bank Statements"}',
            'folder_options': '{"root_folder":"Company Documents","folders":["GST","Bank Statements","Unclassified"],"fallback_folder":"Unclassified","category_folder_map":{"Bank Statement":"Bank Statements"}}',
        }, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        doc_data = response.data['documents'][0]
        self.assertEqual(doc_data['category'], 'Unclassified')
        self.assertEqual(doc_data['status'], 'PROCESSING')
        self.assertIsNone(doc_data['organization_path'])
        self.assertEqual(doc_data['classifier_details']['classification_mode'], 'content_first')

    @override_settings(DOCVAULT_BACKGROUND_EXTRACTION=True)
    @patch("documents.views.queue_extraction", return_value=True)
    def test_upload_queues_extraction_before_classification(self, mock_queue_extraction):
        test_file = SimpleUploadedFile(
            "GST Certificate.pdf",
            b"PAN filename should not decide this category",
            content_type="application/pdf"
        )
        url = reverse('document-upload')
        response = self.client.post(url, {
            'files': test_file,
            'category': 'Unclassified',
        }, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        doc_data = response.data['documents'][0]
        self.assertEqual(doc_data['category'], 'Unclassified')
        self.assertEqual(doc_data['status'], 'PROCESSING')
        self.assertEqual(doc_data['classifier_details']['classification_status'], 'queued')
        self.assertEqual(doc_data['classifier_details']['classification_mode'], 'content_first')
        self.assertFalse(doc_data['classifier_details']['classification_uses_filename'])
        self.assertEqual(doc_data['classifier_details']['extraction_status'], 'queued')
        mock_queue_extraction.assert_called_once()

    @patch("documents.processing.extract_document_text")
    def test_worker_classifies_from_extracted_content_not_filename(self, mock_extract_document_text):
        mock_extract_document_text.return_value = (
            "Goods and Services Tax Certificate GSTIN 29ABCDE1234F1Z5",
            False,
            None,
            [],
        )
        upload = SimpleUploadedFile(
            "PAN Card.pdf",
            b"fake pdf bytes",
            content_type="application/pdf",
        )
        doc = Document.objects.create(
            original_name="PAN Card.pdf",
            file_type="pdf",
            file_size=upload.size,
            file=upload,
            category="Unclassified",
            status="PROCESSING",
            folder_structure={
                "mode": "user_defined",
                "folder_options": {
                    "root_folder": "Vetta",
                    "folders": ["Tax/GST", "PAN", "Unclassified"],
                    "fallback_folder": "Unclassified",
                    "category_folder_map": {"GST Certificate": "Tax/GST", "PAN": "PAN"},
                },
            },
        )

        processed = process_document_extraction(doc.id)

        self.assertEqual(processed.category, "GST Certificate")
        self.assertEqual(processed.organization_path, "Vetta/Tax/GST")
        self.assertEqual(processed.classifier_details["classification_mode"], "content_first")
        self.assertFalse(processed.classifier_details["classification_uses_filename"])
        self.assertEqual(processed.key_fields["GSTIN"], "29ABCDE1234F1Z5")

    @patch("documents.views.queue_extraction", return_value=True)
    def test_bulk_extract_queues_missing_text_documents(self, mock_queue_extraction):
        doc = Document.objects.create(
            original_name="old_invoice.pdf",
            file_type="pdf",
            file_size=1024,
            category="Invoice",
            status="COMPLETED",
        )

        url = reverse('document-extract-text-all')
        response = self.client.post(url)
        doc.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["matched"], 1)
        self.assertEqual(response.data["queued"], 1)
        self.assertEqual(doc.status, "PROCESSING")
        self.assertEqual(doc.classifier_details["extraction_status"], "queued")
        mock_queue_extraction.assert_called_once_with(doc.id)

    @patch("documents.views.queue_extraction", return_value=False)
    def test_bulk_extract_leaves_missing_text_documents_pending_for_worker(self, mock_queue_extraction):
        doc = Document.objects.create(
            original_name="old_statement.pdf",
            file_type="pdf",
            file_size=1024,
            category="Bank Statement",
            status="COMPLETED",
        )

        url = reverse('document-extract-text-all')
        response = self.client.post(url)
        doc.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["matched"], 1)
        self.assertEqual(response.data["queued"], 0)
        self.assertEqual(response.data["pending_worker"], 1)
        self.assertEqual(doc.status, "PENDING")
        self.assertEqual(doc.classifier_details["extraction_status"], "queued")
        mock_queue_extraction.assert_called_once_with(doc.id)

    def test_category_and_status_filtering(self):
        # Create documents with different categories
        doc1 = Document.objects.create(
            original_name="invoice_101.pdf",
            file_type="pdf",
            file_size=1024,
            category="Invoice",
            status="COMPLETED",
            extracted_text="Invoice total amount $500"
        )
        doc2 = Document.objects.create(
            original_name="pan_card.png",
            file_type="png",
            file_size=2048,
            category="PAN",
            status="PENDING"
        )

        url = reverse('document-list')

        # Filter by Invoice
        res1 = self.client.get(url, {'category': 'Invoice'})
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        self.assertEqual(res1.data['count'], 1)
        self.assertEqual(res1.data['documents'][0]['original_name'], 'invoice_101.pdf')

        # Search by text inside extracted_text
        res2 = self.client.get(url, {'search': 'Invoice total amount'})
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(res2.data['count'], 1)

    def test_update_category_api(self):
        doc = Document.objects.create(
            original_name="unknown_scan.pdf",
            file_type="pdf",
            file_size=512,
            category="Unclassified"
        )

        url = reverse('document-detail', kwargs={'doc_id': doc.id})
        response = self.client.patch(url, {'category': 'GST Certificate'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['category'], 'GST Certificate')

    def test_status_update_and_extracted_text_api(self):
        doc = Document.objects.create(
            original_name="bank_statement.pdf",
            file_type="pdf",
            file_size=4096,
            category="Bank Statement",
            status="PENDING"
        )

        url = reverse('document-status-update', kwargs={'doc_id': doc.id})
        payload = {
            'status': 'COMPLETED',
            'extracted_text': 'Bank Statement - Account Balance: $12,500',
            'key_fields': {'account_number': '123456789', 'balance': 12500}
        }
        response = self.client.patch(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'COMPLETED')
        self.assertEqual(response.data['extracted_text'], payload['extracted_text'])
        self.assertEqual(response.data['key_fields']['account_number'], '123456789')
        self.assertIsNotNone(response.data['processed_at'])
