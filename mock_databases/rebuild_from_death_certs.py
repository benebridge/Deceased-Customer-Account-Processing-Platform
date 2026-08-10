#!/usr/bin/env python3
"""
Rebuild database to match existing death certificates exactly
Keep beneficiaries from current database but update deceased to match certs
"""

import sqlite3
import random
from pathlib import Path
from datetime import datetime, timedelta

# Deceased persons from death certificates (alphabetically by filename)
DECEASED_NAMES = [
    ("Anthony", "King", "M"),
    ("Anthony", "Moore", "M"),
    ("Daniel", "Martin", "M"),
    ("David", "Lee", "M"),
    ("Donna", "Rodriguez", "F"),
    ("Dorothy", "Lee", "F"),
    ("Elizabeth", "Walker", "F"),
    ("George", "Scott", "M"),
    ("James", "Allen", "M"),
    ("Jennifer", "Thompson", "F"),
    ("Jessica", "Taylor", "F"),
    ("Kenneth", "Jones", "M"),
    ("Margaret", "Wilson", "F"),
    ("Matthew", "Lewis", "M"),
    ("Nancy", "Wilson", "F"),
    ("Patricia", "Martin", "F"),
    ("Robert", "Anderson", "M"),
    ("Sandra", "Wilson", "F"),
    ("Sarah", "Sanchez", "F"),
    ("William", "Williams", "M")
]

# LA County cities
LA_CITIES = [
    ("Los Angeles", "CA", "90001"),
    ("Pasadena", "CA", "91101"),
    ("Glendale", "CA", "91201"),
    ("Long Beach", "CA", "90801"),
    ("Burbank", "CA", "91501"),
    ("Torrance", "CA", "90501"),
    ("El Monte", "CA", "91731"),
    ("Inglewood", "CA", "90301"),
    ("Downey", "CA", "90241"),
    ("Pomona", "CA", "91766")
]

def generate_ssn():
    """Generate realistic SSN"""
    area = random.randint(100, 899)
    group = random.randint(10, 99)
    serial = random.randint(1000, 9999)
    return f"{area}-{group}-{serial}"

def generate_dob_dod():
    """Generate realistic DOB and DOD for deceased"""
    # Age at death: 55-90 years
    age = random.randint(55, 90)

    # Death date in last 2 years (2024-2026)
    days_ago = random.randint(0, 730)
    dod = datetime.now() - timedelta(days=days_ago)

    # Birth date
    dob = dod - timedelta(days=age*365 + random.randint(0, 364))

    return dob.strftime("%m/%d/%Y"), dod.strftime("%m/%d/%Y")

def generate_address():
    """Generate LA County address"""
    streets = ["Main St", "Oak Ave", "Elm Dr", "Maple Rd", "Pine St", "Cedar Ln",
               "Lake Dr", "Park Ave", "Hill Rd", "Valley St"]
    number = random.randint(100, 9999)
    street = random.choice(streets)
    city, state, zip_code = random.choice(LA_CITIES)
    return f"{number} {street}", city, state, zip_code

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
    print("CHECKING EXISTING DECEASED DATA")
    print("=" * 80)

    # Read existing deceased data from database if it exists
    db_path = base_dir / "dmf_mock.db"
    existing_deceased = {}

    if db_path.exists():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        try:
            c.execute("SELECT * FROM deceased_persons")
            for row in c.fetchall():
                deceased = dict(row)
                existing_deceased[deceased['full_name']] = deceased
                print(f"Found existing: {deceased['full_name']}")
        except:
            pass
        conn.close()

    print(f"\nFound {len(existing_deceased)} existing deceased records")
    print()
    print("=" * 80)
    print("CREATING DECEASED DATA TO MATCH DEATH CERTIFICATES")
    print("=" * 80)
    print()

    deceased_list = []

    for case_id, (first_name, last_name, gender) in enumerate(DECEASED_NAMES, 1):
        full_name = f"{first_name} {last_name}"

        # Check if this person exists in current database
        if full_name in existing_deceased:
            # Use existing data
            person = existing_deceased[full_name].copy()
            person['case_id'] = case_id  # Ensure case_id matches
            print(f"Case {case_id:2d}: {full_name} (keeping existing data)")
        else:
            # Create new data
            dob, dod = generate_dob_dod()
            street, city, state, zip_code = generate_address()

            person = {
                'case_id': case_id,
                'ssn': generate_ssn(),
                'first_name': first_name,
                'last_name': last_name,
                'full_name': full_name,
                'gender': gender,
                'dob': dob,
                'dod': dod,
                'address_street': street,
                'address_city': city,
                'address_state': state,
                'address_zip': zip_code,
                'height': generate_height(),
                'weight': generate_weight(),
                'eye_color': generate_eye_color()
            }
            print(f"Case {case_id:2d}: {full_name} (creating new data)")

        deceased_list.append(person)

    print()
    print(f"✓ Prepared {len(deceased_list)} deceased persons")
    print()

    # Show mapping
    print("=" * 80)
    print("DECEASED PERSON MAPPING")
    print("=" * 80)
    for person in deceased_list:
        print(f"Case {person['case_id']:2d}: {person['full_name']:<25} SSN: {person['ssn']}  DOB: {person['dob']}  DOD: {person['dod']}")

    print()
    print("=" * 80)
    print("Ready to update database with these deceased persons")
    print("Beneficiaries will remain unchanged")
    print("=" * 80)

if __name__ == "__main__":
    main()
