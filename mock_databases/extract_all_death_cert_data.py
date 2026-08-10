#!/usr/bin/env python3
"""
Extract all data from death certificate PDFs
"""

import PyPDF2
import re
import json
from pathlib import Path

def clean_spaces(text):
    """Remove extra spaces from text"""
    return ' '.join(text.split())

def extract_death_cert_data(pdf_path):
    """Extract structured data from death certificate PDF"""
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            page = reader.pages[0]
            raw_text = page.extract_text()

            # Clean up the text
            text = raw_text.replace('\n', ' ')

            # Extract name from filename as primary source
            name_part = pdf_path.stem.replace("-DC", "").replace("-", " ")
            parts = name_part.split()
            first_name = parts[0] if len(parts) > 0 else ""
            last_name = ' '.join(parts[1:]) if len(parts) > 1 else ""

            # Try to extract SSN (looking for pattern of 9 digits with spaces)
            # Format in PDF appears to be: XXX XX XXXX with spaces between each digit
            ssn_pattern = r'(\d)\s*(\d)\s*(\d)\s+(\d)\s*(\d)\s+(\d)\s*(\d)\s*(\d)\s*(\d)'
            ssn_match = re.search(ssn_pattern, text)
            ssn = ""
            if ssn_match:
                digits = ''.join(ssn_match.groups())
                ssn = f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"

            # Extract dates - looking for patterns like "10 18 202 4" for 10/18/2024
            # DOB pattern: typically appears first
            date_pattern = r'(\d{1,2})\s+(\d{1,2})\s+(\d{2,4})\s*(\d)'
            dates = re.findall(date_pattern, text)

            dob = ""
            dod = ""
            if len(dates) >= 2:
                # First date is usually DOB, second is usually DOD
                d1 = dates[0]
                dob = f"{d1[0].zfill(2)}/{d1[1].zfill(2)}/{d1[2]}{d1[3]}"

                d2 = dates[1]
                dod = f"{d2[0].zfill(2)}/{d2[1].zfill(2)}/{d2[2]}{d2[3]}"

            # Extract gender
            gender = ""
            if ' M ' in text or text.startswith('M '):
                gender = "M"
            elif ' F ' in text or text.startswith('F '):
                gender = "F"

            # Try to find address - look for street names
            address_match = re.search(r'(\d+)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(St|Ave|Dr|Rd|Ln|Way|Blvd|Ct)', text)
            address_street = ""
            if address_match:
                address_street = f"{address_match.group(1)} {address_match.group(2)} {address_match.group(3)}"

            # Extract city - common LA County cities
            cities = ["Los Angeles", "Pasadena", "Glendale", "Long Beach", "Burbank",
                     "Torrance", "El Monte", "Inglewood", "Downey", "Pomona"]
            city = ""
            for c in cities:
                if c in text:
                    city = c
                    break

            # Extract zip code
            zip_match = re.search(r'\b(9\d{4})\b', text)
            zip_code = zip_match.group(1) if zip_match else ""

            return {
                'first_name': first_name,
                'last_name': last_name,
                'full_name': f"{first_name} {last_name}",
                'gender': gender,
                'ssn': ssn,
                'dob': dob,
                'dod': dod,
                'address_street': address_street,
                'address_city': city,
                'address_state': "CA",
                'address_zip': zip_code
            }

    except Exception as e:
        print(f"Error processing {pdf_path.name}: {e}")
        return None

def main():
    cert_dir = Path("/Users/danallen/Library/Mobile Documents/com~apple~CloudDocs/MCA_Bridge/BeneBridgePOC/Mock Death Certs")

    print("=" * 80)
    print("EXTRACTING DATA FROM ALL DEATH CERTIFICATES")
    print("=" * 80)
    print()

    cert_files = sorted(cert_dir.glob("*.pdf"))
    all_data = []

    for i, cert_file in enumerate(cert_files, 1):
        print(f"Processing {i}/20: {cert_file.name}...")

        data = extract_death_cert_data(cert_file)
        if data:
            data['case_id'] = i
            all_data.append(data)

            print(f"  Name: {data['full_name']}")
            print(f"  Gender: {data['gender']}")
            print(f"  SSN: {data['ssn']}")
            print(f"  DOB: {data['dob']}")
            print(f"  DOD: {data['dod']}")
            print(f"  Address: {data['address_street']}, {data['address_city']}, {data['address_state']} {data['address_zip']}")
            print()

    # Save to JSON
    output_file = Path(__file__).parent / "EXTRACTED_DECEASED_DATA.json"
    with open(output_file, 'w') as f:
        json.dump(all_data, f, indent=2)

    print("=" * 80)
    print(f"Extracted {len(all_data)} deceased person records")
    print(f"Saved to: {output_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()
