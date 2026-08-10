#!/usr/bin/env python3
"""
Extract actual data from death certificate PDFs using OCR
"""

import re
import subprocess
from pathlib import Path
from pdf2image import convert_from_path
import pytesseract
from PIL import Image

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF using OCR"""
    try:
        # Convert PDF to images
        images = convert_from_path(pdf_path, first_page=1, last_page=1)

        if not images:
            return ""

        # OCR the first page
        text = pytesseract.image_to_string(images[0])
        return text

    except Exception as e:
        print(f"Error processing {pdf_path.name}: {e}")
        return ""

def parse_death_cert(text, filename):
    """Parse death certificate text to extract fields"""
    lines = text.split('\n')

    data = {
        'filename': filename,
        'first_name': '',
        'last_name': '',
        'ssn': '',
        'dob': '',
        'dod': '',
        'gender': '',
        'address': '',
        'city': '',
        'zip': '',
        'height': '',
        'weight': '',
        'eye_color': ''
    }

    # Extract name from filename as fallback
    name_part = filename.replace("-DC.pdf", "").replace("-", " ")
    parts = name_part.split()
    if len(parts) >= 2:
        data['first_name'] = parts[0]
        data['last_name'] = ' '.join(parts[1:])

    # Try to extract SSN (format: XXX-XX-XXXX)
    ssn_match = re.search(r'(\d{3}[-\s]?\d{2}[-\s]?\d{4})', text)
    if ssn_match:
        ssn = ssn_match.group(1)
        # Normalize format
        ssn = re.sub(r'[^\d]', '', ssn)
        data['ssn'] = f"{ssn[:3]}-{ssn[3:5]}-{ssn[5:]}"

    # Try to extract dates (MM/DD/YYYY or MM DD YYYY)
    date_pattern = r'(\d{1,2}[\s/]\d{1,2}[\s/]\d{4})'
    dates = re.findall(date_pattern, text)
    if len(dates) >= 2:
        # Normalize dates
        for i, date in enumerate(dates[:2]):
            normalized = date.replace(' ', '/').strip()
            if i == 0:
                data['dob'] = normalized
            else:
                data['dod'] = normalized

    return data

def main():
    cert_dir = Path("/Users/danallen/Library/Mobile Documents/com~apple~CloudDocs/MCA_Bridge/BeneBridgePOC/Mock Death Certs")

    print("=" * 80)
    print("EXTRACTING DATA FROM DEATH CERTIFICATES")
    print("=" * 80)
    print()

    cert_files = sorted(cert_dir.glob("*.pdf"))

    all_data = []

    for i, cert_file in enumerate(cert_files, 1):
        print(f"Processing {i}/20: {cert_file.name}...")

        # Extract text
        text = extract_text_from_pdf(cert_file)

        # Parse data
        data = parse_death_cert(text, cert_file.name)
        all_data.append(data)

        print(f"  Name: {data['first_name']} {data['last_name']}")
        if data['ssn']:
            print(f"  SSN: {data['ssn']}")
        if data['dob']:
            print(f"  DOB: {data['dob']}")
        if data['dod']:
            print(f"  DOD: {data['dod']}")
        print()

    print("=" * 80)
    print(f"Extracted data from {len(all_data)} death certificates")
    print("=" * 80)

    # Save to file
    output_file = Path(__file__).parent / "extracted_death_cert_data.txt"
    with open(output_file, 'w') as f:
        for data in all_data:
            f.write(f"{data['filename']}\n")
            for key, value in data.items():
                if key != 'filename' and value:
                    f.write(f"  {key}: {value}\n")
            f.write("\n")

    print(f"Data saved to: {output_file}")

if __name__ == "__main__":
    main()
