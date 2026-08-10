#!/usr/bin/env python3
"""
Parse death certificates with correct structure understanding
"""

import PyPDF2
import re
import json
import csv
from pathlib import Path

def parse_death_cert(pdf_path):
    """Parse death certificate using known structure"""
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            page = reader.pages[0]
            text = page.extract_text()
            lines = [line.strip() for line in text.split('\n') if line.strip()]

            # Extract data based on observed structure
            data = {
                'gender': lines[0] if len(lines) > 0 else '',
                'first_name': lines[1].strip() if len(lines) > 1 else '',
                'last_name': lines[2].strip() if len(lines) > 2 else '',
            }

            data['full_name'] = f"{data['first_name']} {data['last_name']}"

            # SSN is in lines 4-6 typically
            if len(lines) > 6:
                ssn_part1 = lines[4].replace(' ', '')
                ssn_part2 = lines[5].replace(' ', '')
                ssn_part3 = lines[6].replace(' ', '')
                data['ssn'] = f"{ssn_part1}-{ssn_part2}-{ssn_part3}"
            else:
                data['ssn'] = ''

            # DOD - look for date pattern MM DD YYYY
            dod = ''
            dob = ''
            for line in lines:
                # Match patterns like "05 16 202 5" or "02 06 193 5"
                date_match = re.match(r'(\d{2})\s+(\d{2})\s+(\d{3})\s+(\d)', line)
                if date_match:
                    month, day, year_part1, year_part2 = date_match.groups()
                    year = year_part1 + year_part2
                    formatted_date = f"{month}/{day}/{year}"

                    # First date found is usually DOD, second is DOB
                    if not dod:
                        dod = formatted_date
                    elif not dob:
                        dob = formatted_date

            data['dod'] = dod
            data['dob'] = dob

            # Address - look for street pattern
            address_street = ''
            for line in lines:
                if re.search(r'\d+\s+\w+\s+(St|Ave|Dr|Rd|Ln|Way|Blvd|Ct)', line, re.IGNORECASE):
                    address_street = ' '.join(line.split())
                    break

            data['address_street'] = address_street

            # City - look for known LA County cities
            cities = ["Los Angeles", "Pasadena", "Glendale", "Long Beach", "Burbank",
                     "Torrance", "El Monte", "Inglewood", "Downey", "Pomona"]
            city = ''
            for line in lines:
                for c in cities:
                    if c.lower() in line.lower():
                        city = c
                        break
                if city:
                    break

            data['address_city'] = city
            data['address_state'] = 'CA'

            # Zip code
            zip_code = ''
            for line in lines:
                if re.match(r'^9\d{4}$', line):
                    zip_code = line
                    break

            data['address_zip'] = zip_code

            # Height, weight, eye color - might need to extract from other lines
            # For now, we'll leave these blank and add them later
            data['height'] = ''
            data['weight'] = ''
            data['eye_color'] = ''

            return data

    except Exception as e:
        print(f"Error processing {pdf_path.name}: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    cert_dir = Path("/Users/danallen/Library/Mobile Documents/com~apple~CloudDocs/MCA_Bridge/BeneBridgePOC/Mock Death Certs")
    output_dir = Path(__file__).parent

    print("=" * 80)
    print("PARSING DEATH CERTIFICATES")
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

            print(f"  Name: {data['full_name']}")
            print(f"  Gender: {data['gender']}")
            print(f"  SSN: {data['ssn']}")
            print(f"  DOB: {data['dob']}")
            print(f"  DOD: {data['dod']}")
            if data['address_street']:
                print(f"  Address: {data['address_street']}")
            print(f"  City/Zip: {data['address_city']}, {data['address_state']} {data['address_zip']}")
            print()

    # Save to JSON
    json_file = output_dir / "EXTRACTED_DECEASED_DATA.json"
    with open(json_file, 'w') as f:
        json.dump(all_data, f, indent=2)

    # Also save to CSV
    csv_file = output_dir / "EXTRACTED_DECEASED_DATA.csv"
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
    print(f"Extracted {len(all_data)} deceased person records")
    print(f"Saved to: {json_file}")
    print(f"Saved to: {csv_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()
