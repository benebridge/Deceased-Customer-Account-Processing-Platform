#!/usr/bin/env python3
"""
Read form field data from death certificate PDFs
"""

import PyPDF2
from pathlib import Path

def extract_form_fields(pdf_path):
    """Extract form field data from PDF"""
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)

            # Get form fields if they exist
            if reader.get_fields():
                fields = reader.get_fields()
                return {k: v.get('/V', '') for k, v in fields.items()}
            else:
                return None
    except Exception as e:
        print(f"Error reading {pdf_path.name}: {e}")
        return None

def main():
    cert_dir = Path("/Users/danallen/Library/Mobile Documents/com~apple~CloudDocs/MCA_Bridge/BeneBridgePOC/Mock Death Certs")

    print("=" * 80)
    print("READING DEATH CERTIFICATE FORM FIELDS")
    print("=" * 80)
    print()

    cert_files = sorted(cert_dir.glob("*.pdf"))

    for i, cert_file in enumerate(cert_files, 1):
        print(f"\n{i}. {cert_file.name}")
        print("-" * 60)

        fields = extract_form_fields(cert_file)

        if fields:
            # Show all fields
            for field_name, value in sorted(fields.items()):
                if value:
                    print(f"  {field_name}: {value}")
        else:
            print("  (No form fields found - might be flattened PDF)")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
