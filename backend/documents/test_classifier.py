from django.test import TestCase
from django.core.management import call_command
import tempfile
from pathlib import Path
from .classifier import RuleEngine, extract_key_fields
from .ml_classifier import MultinomialTextClassifier

class ClassifierTests(TestCase):
    def setUp(self):
        self.engine = RuleEngine() # Should load default rules.json

    def test_pan_classification_keyword(self):
        text = "This is a document from the INCOME TAX DEPARTMENT of India."
        category, rule_id = self.engine.classify(text)
        self.assertEqual(category, "PAN")

    def test_pan_classification_regex(self):
        # A valid PAN format is 5 letters, 4 digits, 1 letter
        text = "My PAN is ABCDE1234F."
        category, rule_id = self.engine.classify(text)
        self.assertEqual(category, "PAN")

    def test_aadhaar_classification_keyword(self):
        text = "MERA AADHAAR MERI PEHCHAAN"
        category, rule_id = self.engine.classify(text)
        self.assertEqual(category, "Aadhaar")

    def test_gst_classification(self):
        text = "Registration Certificate for Goods and Services Tax"
        category, rule_id = self.engine.classify(text)
        self.assertEqual(category, "GST Certificate")

    def test_unclassified(self):
        text = "Just some random text that does not match any rules."
        category, rule_id = self.engine.classify(text)
        self.assertIsNone(category)
        self.assertIsNone(rule_id)

    def test_invoice_classification(self):
        text = "Tax Invoice No: 12345"
        category, rule_id = self.engine.classify(text)
        self.assertEqual(category, "Invoice")

    def test_generic_key_field_extraction_for_unknown_document(self):
        text = """
        Vendor: Example Tools Pvt Ltd
        Email: accounts@example.com
        Phone: +91 98765 43210
        GSTIN: 29ABCDE1234F1Z5
        PAN: ABCDE1234F
        IFSC: HDFC0001234
        Invoice No: INV-25-26/001
        PO Number: PO-0091
        Total Amount INR 12,345.67
        Date: 16/09/2026
        """

        fields = extract_key_fields("Technical Resource", text)

        self.assertIn("29ABCDE1234F1Z5", fields["GSTINs"])
        self.assertIn("ABCDE1234F", fields["PANs"])
        self.assertIn("accounts@example.com", fields["Emails"])
        self.assertIn("+91 98765 43210", fields["Phone_Numbers"])
        self.assertEqual(fields["Invoice_Number"], "INV-25-26/001")
        self.assertEqual(fields["PO_Number"], "PO-0091")
        self.assertIn("16/09/2026", fields["Dates"])

    def test_train_command_skips_raw_upload_folder_by_default(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            for label in ("Invoices", "Bank Statements", "Yanvior Technolgies"):
                (root / label).mkdir()

            for index in range(5):
                (root / "Invoices" / f"invoice_{index}.txt").write_text(
                    f"Tax Invoice Invoice No INV-{index} Total Amount INR {index + 1},000.00",
                    encoding="utf-8",
                )
                (root / "Bank Statements" / f"statement_{index}.txt").write_text(
                    f"Bank Statement Account No 12345{index} IFSC HDFC0001234 Balance {index + 1},000.00",
                    encoding="utf-8",
                )
                (root / "Yanvior Technolgies" / f"raw_{index}.txt").write_text(
                    "This raw upload folder must not become a model label.",
                    encoding="utf-8",
                )

            model_path = root / "model.json"
            call_command("train_document_classifier", str(root), "--model-path", str(model_path), verbosity=0)
            model = MultinomialTextClassifier.load(model_path)

            self.assertEqual(set(model.labels), {"Bank Statements", "Invoices"})
            self.assertNotIn("Yanvior Technolgies", model.labels)
            self.assertEqual(model.training_summary["evaluation"]["eval_documents"], 2)
