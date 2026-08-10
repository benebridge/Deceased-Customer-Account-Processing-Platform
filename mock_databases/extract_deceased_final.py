#!/usr/bin/env python3
"""
Final extraction script with correct PDF structure understanding
"""

import PyPDF2
import re
import json
import csv
from pathlib import Path

def clean_text(text):
    """Remove extra spaces from text"""
    return ' '.join(text.split())

def parse_ssn(ssn_line):
    """Parse SSN from format like '501 62 96 2 8' """
    digits = re.findall(r'\d', ssn_line)
    if len(digits) >= 9:
        return f"{(''.join(digits[:3]))}-{(''.join(digits[3:5]))}-{(''.join(digits[5:9]))}"
    return ""

def parse_date(date_line):
    """Parse date from format like '12 23 19 5 9' or '04 11 202 6'"""
    # Extract all digits
    parts = date_line.split()
    if len(parts) >= 3:
        month = parts[0].strip()
        day = parts[1].strip()
        # Year might be split as "19 5 9" or "202 6"
        year_parts = [p.strip() for p in parts[2:] if p.strip().isdigit()]
        year = ''.join(year_parts)

        return f"{month.zfill(2)}/{day.zfill(2)}/{year}"
    return ""

def parse_death_cert(pdf_path):
    """Parse death certificate with correct structure"""
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            page = reader.pages[0]
            text = page.extract_text()
            lines = text.split('\n')

            # Find the name (usually around line 9-10)
            first_name = ""
            last_name = ""
            gender = ""
            dob = ""
            ssn = ""
            dod = ""
            address_street = ""
            city = ""
            zip_code = ""

            for i, line in enumerate(lines):
                line = line.strip()

                # Look for first name (contains letters, not just numbers/symbols)
                if not first_name and len(line) > 2 and any(c.isalpha() for c in line) and line not in ['CA', 'Married', 'Single', 'Divorced', 'Widowed']:
                    # Check if it's a proper name (mostly letters)
                    clean = ''.join(c for c in line if c.isalpha())
                    if len(clean) >= 3 and clean[0].isupper():
                        first_name = clean
                        # Next line should be last name
                        if i + 1 < len(lines):
                            next_line = lines[i + 1].strip()
                            last_clean = ''.join(c for c in next_line if c.isalpha())
                            if len(last_clean) >= 2:
                                last_name = last_clean

                # Gender (single letter M or F)
                if line in ['M', 'F', 'M  ', 'F  ',  '  M', '  F']:
                    gender = line.strip()[0]

                # DOB - pattern like "12 23 19 5 9"
                dob_match = re.match(r'^\s*(\d{1,2})\s+(\d{1,2})\s+(\d{2,3})\s+(\d)\s+(\d)', line)
                if dob_match and not dob:
                    dob = parse_date(line)

                # SSN - pattern like "501 62 96 2 8"
                ssn_match = re.match(r'^\s*(\d{3})\s+(\d{2})\s+(\d{2})\s+(\d)\s+(\d)', line)
                if ssn_match and not ssn:
                    ssn = parse_ssn(line)

                # DOD - pattern like "04 11 202 6"
                if re.match(r'^\s*(\d{1,2})\s+(\d{1,2})\s+(\d{3})\s+(\d)', line) and dob and not dod:
                    dod = parse_date(line)

                # Address - contains numbers and street suffix
                if re.search(r'\d+.*?(St|Ave|Dr|Rd|Ln|Way|Blvd|Ct)', line, re.IGNORECASE) and not address_street:
                    address_street = clean_text(line)

                # Zip code
                zip_match = re.match(r'^\s*(9\d{4})\s*$', line)
                if zip_match:
                    zip_code = zip_match.group(1)

            # City - look for known LA County cities
            text_clean = ' '.join(lines)
            cities = ["Los Angeles", "Pasadena", "Glendale", "Long Beach", "Burbank",
                     "Torrance", "El Monte", "Inglewood", "Downey", "Pomona"]
            for c in cities:
                if c.lower() in text_clean.lower():
                    city = c
                    break

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
                'address_state': 'CA',
                'address_zip': zip_code,
                'height': '',  # Not in PDF text extraction
                'weight': '',  # Not in PDF text extraction
                'eye_color': ''  # Not in PDF text extraction
            }

    except Exception as e:
        print(f"Error processing {pdf_path.name}: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    cert_dir = Path("/Users/danallen/Library/Mobile Documents/com~apple~CloudDocs/MCA_Bridge/BeneBridgePOC/Mock Death Certs")
    output_dir = Path(__file__).parent

    print("=" * 80)
    print("EXTRACTING DECEASED DATA FROM DEATH CERTIFICATES")
    print("=" * 80)
    print()

    cert_files = sorted(cert_dir.glob("*.pdf"))
    all_data = []

    for i, cert_file in enumerate(cert_files, 1):
        print(f"Processing {i}/20: {cert_file.name}...")

        data = parse_death_cert(cert_file)
        if data:
            data['case_id'] = i
            all_data.append(data)

            print(f"  ✓ {data['full_name']} ({data['gender']})")
            print(f"    SSN: {data['ssn']}")
            print(f"    DOB: {data['dob']} | DOD: {data['dod']}")
            if data['address_street']:
                print(f"    {data['address_street']}, {data['address_city']}, {data['address_state']} {data['address_zip']}")
            else:
                print(f"    {data['address_city']}, {data['address_state']} {data['address_zip']}")
            print()

    # Save to JSON
    json_file = output_dir / "DECEASED_FROM_CERTIFICATES.json"
    with open(json_file, 'w') as f:
        json.dump(all_data, f, indent=2)

    # Save to CSV
    csv_file = output_dir / "DECEASED_FROM_CERTIFICATES.csv"
    if all_data:
        with open(csv_file, 'w', newline='') as f:
            fieldnames = ['case_id', 'full_name', 'first_name', 'last_name', 'gender',
                         'ssn', 'dob', 'dod', 'address_street', 'address_city',
                         'address_state', 'address_zip', 'height', 'weight', 'eye_color']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in all_data:
                writer.writerow(row)

    print("=" * 80)
    print(f"✓ Successfully extracted {len(all_data)}/20 deceased person records")
    print(f"✓ Saved to: {json_file}")
    print(f"✓ Saved to: {csv_file}")
    print("=" * 80)
    print()
    print("These are the ORIGINAL deceased persons that should be preserved in the database.")
    print("Beneficiaries will remain unchanged (California residents with DL info).")

if __name__ == "__main__":
    main()
