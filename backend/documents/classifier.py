import json
import os
import re
from .ml_classifier import predict_document_category

class RuleEngine:
    def __init__(self, rules_file_path=None):
        if rules_file_path is None:
            # Default to the rules.json in the same directory
            base_dir = os.path.dirname(os.path.abspath(__file__))
            rules_file_path = os.path.join(base_dir, 'rules.json')
        
        self.rules_file_path = rules_file_path
        self._rules_mtime = None
        self.rules = []
        self._load_rules(rules_file_path)

    def _load_rules(self, file_path):
        if not os.path.exists(file_path):
            print(f"Warning: Rules file not found at {file_path}")
            return
            
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                rules_data = json.load(f)
                # Sort rules by priority (lower number = higher priority)
                self.rules = sorted(rules_data, key=lambda x: x.get('priority', 999))
                self._rules_mtime = os.path.getmtime(file_path)
            except json.JSONDecodeError:
                print(f"Error: Invalid JSON in rules file {file_path}")
                self.rules = []

    def _refresh_rules_if_changed(self):
        try:
            current_mtime = os.path.getmtime(self.rules_file_path)
        except OSError:
            return

        if self._rules_mtime != current_mtime:
            self._load_rules(self.rules_file_path)

    def classify(self, text):
        """
        Classifies the text based on the loaded rules.
        Returns a tuple of (matched_category, matched_rule_id) or (None, None).
        """
        self._refresh_rules_if_changed()

        if not text:
            return None, None

        for rule in self.rules:
            rule_id = rule.get('id')
            category = rule.get('category')
            rule_type = rule.get('type')
            patterns = rule.get('patterns', [])

            if rule_type == 'keyword':
                if self._match_keyword(text, patterns):
                    return category, rule_id
            elif rule_type == 'regex':
                if self._match_regex(text, patterns):
                    return category, rule_id

        return None, None

    def _match_keyword(self, text, patterns):
        text_lower = re.sub(r'[_\-]+', ' ', text.lower())
        for pattern in patterns:
            # A simple substring check is enough for keywords here,
            # or we could use word boundaries. For flexibility, we use substring.
            pattern_lower = re.sub(r'[_\-]+', ' ', pattern.lower())
            if pattern_lower in text_lower:
                return True
        return False

    def _match_regex(self, text, patterns):
        for pattern in patterns:
            try:
                # regex search over the text
                if re.search(pattern, text, re.IGNORECASE):
                    return True
            except re.error as e:
                print(f"Warning: Invalid regex pattern '{pattern}': {e}")
                continue
        return False

# Create a singleton instance for easy import and usage
default_rule_engine = RuleEngine()

HIGH_PRECISION_RULE_CATEGORIES = {
    "Aadhaar",
    "PAN",
    "GST Certificate",
    "Invoice",
    "Purchase Order",
    "Bank Statement",
    "Tax Filing",
    "Archive",
    "Digital Certificate",
    "Agreement",
}


def classify_document_with_details(text):
    rule_category, rule_id = default_rule_engine.classify(text)
    ml_result = predict_document_category(text)

    if rule_category in HIGH_PRECISION_RULE_CATEGORIES:
        return {
            "category": rule_category,
            "matched_rule": rule_id,
            "confidence": 0.98,
            "source": "rule",
            "ml_prediction": ml_result,
            "needs_review": False,
        }

    if ml_result and ml_result.get("accepted"):
        return {
            "category": ml_result["category"],
            "matched_rule": rule_id,
            "confidence": ml_result["confidence"],
            "source": "ml",
            "ml_prediction": ml_result,
            "needs_review": ml_result["confidence"] < 0.75 or ml_result.get("margin", 0) < 0.2,
        }

    if rule_category:
        return {
            "category": rule_category,
            "matched_rule": rule_id,
            "confidence": 0.9,
            "source": "rule",
            "ml_prediction": ml_result,
            "needs_review": False,
        }

    if ml_result:
        return {
            "category": ml_result["category"],
            "matched_rule": None,
            "confidence": ml_result["confidence"],
            "source": "ml_low_confidence",
            "ml_prediction": ml_result,
            "needs_review": True,
        }

    return {
        "category": None,
        "matched_rule": None,
        "confidence": 0.0,
        "source": "none",
        "ml_prediction": None,
        "needs_review": True,
    }


def classify_document(text):
    details = classify_document_with_details(text)
    return details["category"], details["matched_rule"]


def _unique(values, limit=10):
    seen = set()
    unique_values = []
    for value in values:
        cleaned = str(value or "").strip(" \t\r\n,.;:")
        key = cleaned.lower()
        if not cleaned or key in seen:
            continue
        seen.add(key)
        unique_values.append(cleaned)
        if len(unique_values) >= limit:
            break
    return unique_values


def _extract_generic_fields(text):
    fields = {}

    gstins = _unique(re.findall(r'\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b', text, re.IGNORECASE))
    pans = _unique(re.findall(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b', text, re.IGNORECASE))
    aadhaars = _unique(re.findall(r'\b[2-9][0-9]{3}\s?[0-9]{4}\s?[0-9]{4}\b', text))
    ifscs = _unique(re.findall(r'\b[A-Z]{4}0[A-Z0-9]{6}\b', text, re.IGNORECASE))
    emails = _unique(re.findall(r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b', text, re.IGNORECASE))
    phones = _unique(re.findall(r'(?:\+?91[\s-]?)?[6-9][0-9]{4}[\s-]?[0-9]{5}\b', text))
    dates = _unique(re.findall(r'\b(?:[0-3]?[0-9][./-][01]?[0-9][./-](?:20)?[0-9]{2}|(?:20[0-4][0-9])[./-][01]?[0-9][./-][0-3]?[0-9])\b', text), limit=20)
    amounts = _unique(re.findall(r'(?:Rs\.?|INR|USD|\$|₹)?\s*[0-9]{1,3}(?:,[0-9]{2,3})*(?:\.[0-9]{2})\b', text, re.IGNORECASE), limit=20)

    if gstins:
        fields["GSTINs"] = [value.upper() for value in gstins]
    if pans:
        fields["PANs"] = [value.upper() for value in pans]
    if aadhaars:
        fields["Aadhaar_Numbers"] = aadhaars
    if ifscs:
        fields["IFSC_Codes"] = [value.upper() for value in ifscs]
    if emails:
        fields["Emails"] = emails
    if phones:
        fields["Phone_Numbers"] = phones
    if dates:
        fields["Dates"] = dates
    if amounts:
        fields["Amounts"] = amounts

    labeled_patterns = {
        "Invoice_Number": r'(?:invoice\s*(?:no|number|#)|inv\s*(?:no|#))[\s:.-]*([A-Z0-9][A-Z0-9\-\/_.]+)',
        "PO_Number": r'(?:po\s*(?:no|number|#)|purchase\s*order\s*(?:no|number|#))[\s:.-]*([A-Z0-9][A-Z0-9\-\/_.]+)',
        "Account_Number": r'(?:account\s*(?:no|number)|a/c\s*no)[\s:.-]*([0-9]{6,20})',
        "CIN": r'\b([UL][0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6})\b',
    }
    for field_name, pattern in labeled_patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            fields[field_name] = match.group(1).strip()

    return fields


def extract_key_fields(category, text, spatial_blocks=None):
    """
    Extracts structured key-value data based on the document category using regex and spatial heuristics.
    """
    if not text:
        return {}
    
    spatial_blocks = spatial_blocks or []
    fields = _extract_generic_fields(text)
    
    cat_lower = category.lower() if category else ""
    
    if 'pan' in cat_lower:
        # PAN format: 5 letters, 4 numbers, 1 letter
        pan_match = re.search(r'\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b', text, re.IGNORECASE)
        if pan_match:
            fields['PAN_Number'] = pan_match.group(0).upper()
            
    if 'aadhaar' in cat_lower:
        # Aadhaar format: 12 digits, often formatted as 4-4-4
        aadhaar_match = re.search(r'\b([2-9]{1}[0-9]{3}\s?[0-9]{4}\s?[0-9]{4})\b', text)
        if aadhaar_match:
            fields['Aadhaar_Number'] = aadhaar_match.group(0)
            
    if 'gst' in cat_lower:
        # GSTIN format: 15 alphanumeric characters
        gst_match = re.search(r'\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}\b', text, re.IGNORECASE)
        if gst_match:
            fields['GSTIN'] = gst_match.group(0).upper()
            
    if 'invoice' in cat_lower or 'bill' in cat_lower:
        # Simple regex to catch typical invoice totals and numbers
        inv_num_match = re.search(r'(?:invoice no|inv no|invoice #|pi no)[\s:]*([A-Z0-9\-\/]+)', text, re.IGNORECASE)
        if inv_num_match:
            fields['Invoice_Number'] = inv_num_match.group(1).strip()
            
        total_match = re.search(r'(?:total|amount payable|grand total)[\s:]*(?:rs\.?|inr|\$|₹)?\s*([0-9,]+\.[0-9]{2})', text, re.IGNORECASE)
        if total_match:
            fields['Total_Amount'] = total_match.group(1).strip()

        # Spatial Heuristic Fallback
        if spatial_blocks and ('Total_Amount' not in fields or 'Invoice_Number' not in fields):
            for block in spatial_blocks:
                box = block['box']
                b_text = block['text'].lower()
                
                # Spatial heuristic for Invoice Number
                if 'Invoice_Number' not in fields and 'invoice' in b_text:
                    # Look for a block to the right (same y-level roughly)
                    ymin, ymax = box[0][1], box[2][1]
                    for other in spatial_blocks:
                        if other == block: continue
                        oymin, oymax = other['box'][0][1], other['box'][2][1]
                        # Check if roughly on same line
                        if abs(ymin - oymin) < 15 and other['box'][0][0] > box[1][0]:
                            if re.search(r'^[A-Z0-9\-\/]+$', other['text'].strip(), re.IGNORECASE):
                                fields['Invoice_Number'] = other['text'].strip()
                                break
                
                # Spatial heuristic for Total
                if 'Total_Amount' not in fields and ('total' in b_text or 'amount' in b_text):
                    ymin, ymax = box[0][1], box[2][1]
                    for other in spatial_blocks:
                        if other == block: continue
                        oymin, oymax = other['box'][0][1], other['box'][2][1]
                        if abs(ymin - oymin) < 15 and other['box'][0][0] > box[1][0]:
                            num_match = re.search(r'([0-9,]+\.[0-9]{2})', other['text'])
                            if num_match:
                                fields['Total_Amount'] = num_match.group(1)
                                break

    if 'order' in cat_lower or 'po' in cat_lower:
        po_match = re.search(r'(?:po number|po #|order no)[\s:]*([A-Z0-9\-\/]+)', text, re.IGNORECASE)
        if po_match:
            fields['PO_Number'] = po_match.group(1).strip()
            
    if 'bank' in cat_lower or 'statement' in cat_lower:
        acc_match = re.search(r'(?:account no|a/c no)[\s:]*([0-9]+)', text, re.IGNORECASE)
        if acc_match:
            fields['Account_Number'] = acc_match.group(1).strip()
            
        ifsc_match = re.search(r'IFSC(?: code)?[\s:]*([A-Z]{4}0[A-Z0-9]{6})', text, re.IGNORECASE)
        if ifsc_match:
            fields['IFSC_Code'] = ifsc_match.group(1).strip()

    return fields
