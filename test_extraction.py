#!/usr/bin/env python3
"""
Test extraction from actual documents
"""

from PIL import Image
import pytesseract
from pdf2image import convert_from_path
from pypdf import PdfReader
from pathlib import Path

# Test death certificate
death_cert_path = Path("Cases/Case_IRA-001-1_018_Thompson_Karen/Death_Cert_Thompson_Jennifer.pdf")
print("=" * 80)
print("TESTING DEATH CERTIFICATE EXTRACTION")
print("=" * 80)
print(f"File: {death_cert_path}")
print()

# Convert PDF to image
images = convert_from_path(death_cert_path, first_page=1, last_page=1)
image = images[0]

# Perform OCR
text = pytesseract.image_to_string(image)
print("FULL OCR TEXT:")
print(text)
print()
print("=" * 80)

# Test driver's license
dl_path = Path("Cases/Case_IRA-001-1_018_Thompson_Karen/CA_DL_018_Thompson_Karen.png")
print("TESTING DRIVER'S LICENSE EXTRACTION")
print("=" * 80)
print(f"File: {dl_path}")
print()

image = Image.open(dl_path)
text = pytesseract.image_to_string(image)
print("FULL OCR TEXT:")
print(text)
print()
print("=" * 80)

# Test claim form
claim_path = Path("Cases/Case_IRA-001-1_018_Thompson_Karen/Claim_Form_IRA-001-1_018_Thompson_Karen.pdf")
print("TESTING CLAIM FORM EXTRACTION")
print("=" * 80)
print(f"File: {claim_path}")
print()

reader = PdfReader(claim_path)
fields = reader.get_fields()

if fields:
    print(f"Found {len(fields)} form fields:")
    for field_name, field_obj in fields.items():
        if hasattr(field_obj, 'get'):
            value = field_obj.get('/V', '')
            if value:
                print(f"  {field_name}: {value}")
else:
    print("No form fields found")

print()
print("=" * 80)
