#!/usr/bin/env python3
"""
Update database with correct deceased data from death certificates
Keep beneficiaries, update them to be California residents
"""

import sqlite3
import csv
import random
from pathlib import Path

def generate_height():
    """Generate realistic height"""
    feet = random.randint(5, 6)
    inches = random.randint(0, 11)
    return f"{feet}'{inches}\""

def generate_weight():
    """Generate realistic weight"""
    return random.randint(120, 250)

def generate_eye_color():
    """Generate eye color"""
    return random.choice(["Brown", "Blue", "Green", "Hazel", "Gray"])

def main():
    base_dir = Path(__file__).parent

    print("=" * 80)
    print("UPDATING DATABASE WITH CORRECT DECEASED DATA")
    print("=" * 80)
    print()

    # Read the completed deceased data
    deceased_file = base_dir / "DECEASED_DATA_COMPLETE.csv"
    deceased_list = []

    with open(deceased_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Fill in missing height, weight, eye_color if needed
            if not row['height']:
                row['height'] = generate_height()
            if not row['weight']:
                row['weight'] = str(generate_weight())
            if not row['eye_color']:
                row['eye_color'] = generate_eye_color()

            deceased_list.append(row)

    print(f"✓ Loaded {len(deceased_list)} deceased persons from completed template")
    print()

    # Get existing beneficiaries from current database
    existing_beneficiaries = []
    beneficiary_db = base_dir / "beneficiary_registry.db"

    if beneficiary_db.exists():
        print("Reading existing beneficiaries...")
        conn = sqlite3.connect(beneficiary_db)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM beneficiaries")
        for row in c.fetchall():
            existing_beneficiaries.append(dict(row))
        conn.close()
        print(f"✓ Found {len(existing_beneficiaries)} existing beneficiaries")
        print()

    # Update DMF database with correct deceased data
    print("=" * 80)
    print("UPDATING DMF DATABASE")
    print("=" * 80)

    dmf_db = base_dir / "dmf_mock.db"
    conn = sqlite3.connect(dmf_db)
    c = conn.cursor()

    # Drop and recreate table to ensure clean data
    c.execute("DROP TABLE IF EXISTS deceased_persons")

    c.execute('''CREATE TABLE deceased_persons (
        case_id INTEGER PRIMARY KEY,
        ssn TEXT UNIQUE NOT NULL,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        full_name TEXT NOT NULL,
        gender TEXT NOT NULL,
        dob TEXT NOT NULL,
        dod TEXT NOT NULL,
        address_street TEXT,
        address_city TEXT,
        address_state TEXT,
        address_zip TEXT,
        height TEXT,
        weight INTEGER,
        eye_color TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    for person in deceased_list:
        c.execute('''INSERT INTO deceased_persons
                     (case_id, ssn, first_name, last_name, full_name, gender, dob, dod,
                      address_street, address_city, address_state, address_zip,
                      height, weight, eye_color)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (int(person["case_id"]), person["ssn"], person["first_name"], person["last_name"],
                   person["full_name"], person["gender"], person["dob"], person["dod"],
                   person["address_street"], person["address_city"], person["address_state"],
                   person["address_zip"], person["height"], int(person["weight"]), person["eye_color"]))

        print(f"  ✓ Case {int(person['case_id']):2d}: {person['full_name']}")

    conn.commit()
    conn.close()

    print()
    print(f"✓ Updated DMF database with {len(deceased_list)} deceased persons")
    print()

    # Update beneficiaries to ensure they're all California residents
    print("=" * 80)
    print("UPDATING BENEFICIARIES (Ensuring all are California residents)")
    print("=" * 80)

    # California cities for beneficiaries
    CA_CITIES = [
        ("Los Angeles", "CA", "90001"),
        ("San Francisco", "CA", "94102"),
        ("San Diego", "CA", "92101"),
        ("Sacramento", "CA", "95814"),
        ("San Jose", "CA", "95113"),
        ("Fresno", "CA", "93650"),
        ("Oakland", "CA", "94612"),
        ("Santa Ana", "CA", "92701"),
        ("Anaheim", "CA", "92805"),
        ("Riverside", "CA", "92501"),
        ("Pasadena", "CA", "91101"),
        ("Torrance", "CA", "90501"),
        ("El Monte", "CA", "91731"),
        ("Glendale", "CA", "91201"),
        ("Long Beach", "CA", "90801")
    ]

    conn = sqlite3.connect(beneficiary_db)
    c = conn.cursor()

    # Update all beneficiaries to have California addresses
    updated_count = 0
    for ben in existing_beneficiaries:
        # If not already in California, update to CA city
        if ben['address_state'] != 'CA':
            city, state, zip_code = random.choice(CA_CITIES)

            c.execute('''UPDATE beneficiaries
                         SET address_city = ?, address_state = ?, address_zip = ?
                         WHERE beneficiary_id = ?''',
                      (city, state, zip_code, ben['beneficiary_id']))
            updated_count += 1

    conn.commit()
    conn.close()

    print(f"✓ Updated {updated_count} beneficiaries to California addresses")
    print(f"✓ Total beneficiaries: {len(existing_beneficiaries)}")
    print()

    # Also update identity records to have CA driver's licenses
    identity_db = base_dir / "identity_verification.db"
    if identity_db.exists():
        conn = sqlite3.connect(identity_db)
        c = conn.cursor()

        c.execute("UPDATE identity_records SET dl_state = 'CA' WHERE dl_state != 'CA'")
        updated_dl = c.rowcount

        conn.commit()
        conn.close()

        print(f"✓ Updated {updated_dl} driver's licenses to California (CA)")
        print()

    print("=" * 80)
    print("DATABASE UPDATE COMPLETE")
    print("=" * 80)
    print()
    print("Summary:")
    print(f"  • Deceased persons: {len(deceased_list)} (from death certificates)")
    print(f"  • Beneficiaries: {len(existing_beneficiaries)} (all California residents)")
    print(f"  • All driver's licenses: California (CA)")
    print()
    print("Next step: Regenerate PERSON_REFERENCE_FOR_FORMS.docx")

if __name__ == "__main__":
    main()
