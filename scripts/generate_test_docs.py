import os
import random

# Create 2000 test files
TARGET_COUNT = 2000
TARGET_DIR = 'sample_docs'
os.makedirs(TARGET_DIR, exist_ok=True)

CATEGORIES = {
    'PAN': ["PERMANENT ACCOUNT NUMBER", "INCOME TAX DEPARTMENT", "GOVT. OF INDIA", "ABCDE1234F"],
    'Aadhaar': ["Government of India", "DOB", "MERA AADHAAR MERI PEHCHAAN", "VID :", "1234 5678 9012"],
    'GST Certificate': ["GSTIN", "Goods and Services Tax", "Registration Certificate", "22AAAAA0000A1Z5"],
    'Invoice': ["Tax Invoice", "Invoice No: 123", "Invoice Date", "Billed To"],
    'Purchase Order': ["Purchase Order", "PO Number", "PO Date", "Vendor Number"],
    'Bank Statement': ["Account Statement", "Bank Statement", "Account No: 123", "IFSC", "Branch Code", "Balance summary"],
    'Contract': ["Agreement", "Contract", "Non-Disclosure", "Terms and Conditions", "Memorandum of Understanding", "WHEREAS"],
    'Licence': ["Licence", "License", "Valid Upto", "Authorized Signatory", "Issued By"],
    'Unclassified': ["Just a regular letter.", "No specific keywords here.", "Hello world", "Random document content"]
}

print(f"Generating {TARGET_COUNT} test documents...")

for i in range(TARGET_COUNT):
    category = random.choice(list(CATEGORIES.keys()))
    keywords = CATEGORIES[category]
    
    # Pick 2 random keywords
    selected_keywords = random.sample(keywords, k=min(2, len(keywords)))
    content = f"Document ID: {i}\n" + "\n".join(selected_keywords) + "\nThis is auto-generated test data."
    
    filename = f"test_doc_{i:04d}.txt"
    filepath = os.path.join(TARGET_DIR, filename)
    with open(filepath, 'w') as f:
        f.write(content)
        
print(f"Done. Generated {TARGET_COUNT} documents in '{TARGET_DIR}' folder.")
