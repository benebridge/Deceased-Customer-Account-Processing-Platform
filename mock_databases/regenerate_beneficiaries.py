#!/usr/bin/env python3
"""
Regenerate beneficiaries to ensure every deceased has 1-3 beneficiaries
Match by last name, all California residents
"""

import sqlite3
import random
from pathlib import Path
from datetime import datetime, timedelta

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
    ("Long Beach", "CA", "90801"),
    ("Bakersfield", "CA", "93301"),
    ("Santa Monica", "CA", "90401"),
    ("Irvine", "CA", "92602")
]

RELATIONSHIPS = ["spouse", "child", "sibling", "parent", "cousin", "niece", "nephew"]

# Common first names
MALE_NAMES = ["James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph", "Thomas", "Charles"]
FEMALE_NAMES = ["Mary", "Patricia", "Jennifer", "Linda", "Barbara", "Elizabeth", "Susan", "Jessica", "Sarah", "Karen"]

def generate_ssn():
    """Generate realistic SSN"""
    area = random.randint(100, 899)
    group = random.randint(10, 99)
    serial = random.randint(1000, 9999)
    return f"{area}-{group}-{serial}"

def generate_dob(deceased_dob, relationship):
    """Generate realistic DOB based on relationship"""
    # Parse deceased DOB
    deceased_date = datetime.strptime(deceased_dob, "%m/%d/%Y")

    if relationship == "spouse":
        # Spouse: similar age, +/- 5 years
        offset_years = random.randint(-5, 5)
        ben_date = deceased_date.replace(year=deceased_date.year + offset_years)
    elif relationship in ["child", "son", "daughter"]:
        # Child: 20-40 years younger
        offset_years = random.randint(20, 40)
        ben_date = deceased_date.replace(year=deceased_date.year + offset_years)
    elif relationship == "parent":
        # Parent: 20-40 years older
        offset_years = random.randint(20, 40)
        ben_date = deceased_date.replace(year=deceased_date.year - offset_years)
    elif relationship == "sibling":
        # Sibling: +/- 10 years
        offset_years = random.randint(-10, 10)
        ben_date = deceased_date.replace(year=deceased_date.year + offset_years)
    else:
        # Cousin, niece, nephew: varied
        offset_years = random.randint(-15, 15)
        ben_date = deceased_date.replace(year=deceased_date.year + offset_years)

    # Add some random days
    ben_date = ben_date + timedelta(days=random.randint(0, 364))

    return ben_date.strftime("%Y-%m-%d")

def generate_phone():
    """Generate phone number"""
    area = random.randint(200, 999)
    exchange = random.randint(200, 999)
    number = random.randint(1000, 9999)
    return f"({area}) {exchange}-{number}"

def generate_email(first_name, last_name):
    """Generate email address"""
    domains = ["email.com", "mail.com", "example.com", "inbox.com"]
    return f"{first_name.lower()}.{last_name.lower()}@{random.choice(domains)}"

def generate_drivers_license():
    """Generate CA driver's license number"""
    letter = random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
    numbers = ''.join([str(random.randint(0, 9)) for _ in range(7)])
    return f"{letter}{numbers}"

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

def generate_hair_color():
    """Generate hair color"""
    return random.choice(["Black", "Brown", "Blonde", "Red", "Gray", "White"])

def main():
    base_dir = Path(__file__).parent

    print("=" * 80)
    print("REGENERATING BENEFICIARIES FOR ALL DECEASED")
    print("=" * 80)
    print()

    # Get all deceased
    conn_dmf = sqlite3.connect(base_dir / "dmf_mock.db")
    conn_dmf.row_factory = sqlite3.Row
    c_dmf = conn_dmf.cursor()
    c_dmf.execute("SELECT * FROM deceased_persons ORDER BY case_id")
    deceased_list = [dict(row) for row in c_dmf.fetchall()]
    conn_dmf.close()

    print(f"Found {len(deceased_list)} deceased persons")
    print()

    # Clear existing beneficiaries and related data
    print("Clearing existing beneficiaries...")

    conn_ben = sqlite3.connect(base_dir / "beneficiary_registry.db")
    c_ben = conn_ben.cursor()
    c_ben.execute("DELETE FROM beneficiary_designations")
    c_ben.execute("DELETE FROM beneficiaries")
    conn_ben.commit()
    conn_ben.close()

    conn_id = sqlite3.connect(base_dir / "identity_verification.db")
    c_id = conn_id.cursor()
    c_id.execute("DELETE FROM identity_records")
    conn_id.commit()
    conn_id.close()

    print("✓ Cleared existing beneficiaries and identity records")
    print()

    # Generate beneficiaries for each deceased
    all_beneficiaries = []
    all_identities = []
    all_designations = []
    beneficiary_id = 1

    print("=" * 80)
    print("GENERATING BENEFICIARIES")
    print("=" * 80)
    print()

    for deceased in deceased_list:
        num_beneficiaries = random.randint(1, 3)

        print(f"Case {deceased['case_id']:2d}: {deceased['full_name']:<25} ({num_beneficiaries} beneficiaries)")

        # Get accounts for this deceased
        conn_fin = sqlite3.connect(base_dir / "financial_accounts.db")
        conn_fin.row_factory = sqlite3.Row
        c_fin = conn_fin.cursor()
        c_fin.execute("SELECT * FROM accounts WHERE deceased_case_id = ?", (deceased['case_id'],))
        accounts = [dict(row) for row in c_fin.fetchall()]
        conn_fin.close()

        for i in range(num_beneficiaries):
            # Determine relationship
            relationship = random.choice(RELATIONSHIPS)

            # Generate name - try to use same last name for spouse/child
            if relationship in ["spouse", "child", "son", "daughter"] and random.random() < 0.7:
                last_name = deceased['last_name']
            else:
                # Different last name
                last_name = deceased['last_name'] if random.random() < 0.3 else random.choice([
                    "Smith", "Johnson", "Brown", "Davis", "Miller", "Wilson", "Moore",
                    "Taylor", "Anderson", "Thomas", "Jackson", "White", "Harris", "Martin"
                ])

            # Pick gender-appropriate first name
            if deceased['gender'] == 'M' and relationship == 'spouse':
                gender = 'F'
                first_name = random.choice(FEMALE_NAMES)
            elif deceased['gender'] == 'F' and relationship == 'spouse':
                gender = 'M'
                first_name = random.choice(MALE_NAMES)
            else:
                gender = random.choice(['M', 'F'])
                first_name = random.choice(MALE_NAMES if gender == 'M' else FEMALE_NAMES)

            full_name = f"{first_name} {last_name}"
            ssn = generate_ssn()
            dob = generate_dob(deceased['dob'], relationship)

            # Address - California city
            city, state, zip_code = random.choice(CA_CITIES)
            streets = ["Main St", "Oak Ave", "Elm Dr", "Maple Rd", "Pine St", "Cedar Ln",
                      "Lake Dr", "Park Ave", "Hill Rd", "Valley St", "River Rd", "Mountain View"]
            street_number = random.randint(100, 9999)
            address_street = f"{street_number} {random.choice(streets)}"

            phone = generate_phone()
            email = generate_email(first_name, last_name)

            # Create beneficiary record
            beneficiary = {
                'beneficiary_id': beneficiary_id,
                'ssn': ssn,
                'first_name': first_name,
                'last_name': last_name,
                'full_name': full_name,
                'gender': gender,
                'dob': dob,
                'address_street': address_street,
                'address_city': city,
                'address_state': state,
                'address_zip': zip_code,
                'phone': phone,
                'email': email
            }
            all_beneficiaries.append(beneficiary)

            # Create identity record
            drivers_license = generate_drivers_license()
            dl_issue_date = datetime.now() - timedelta(days=random.randint(365, 3650))
            dl_expiration = dl_issue_date + timedelta(days=365*5)

            identity = {
                'ssn': ssn,
                'first_name': first_name,
                'last_name': last_name,
                'full_name': full_name,
                'gender': gender,
                'dob': dob,
                'address_street': address_street,
                'address_city': city,
                'address_state': state,
                'address_zip': zip_code,
                'drivers_license': drivers_license,
                'dl_state': 'CA',
                'dl_issue_date': dl_issue_date.strftime("%Y-%m-%d"),
                'dl_expiration': dl_expiration.strftime("%Y-%m-%d"),
                'height': generate_height(),
                'weight': generate_weight(),
                'eye_color': generate_eye_color(),
                'hair_color': generate_hair_color(),
                'photo_reference': f"photo_{ssn.replace('-', '')}.jpg",
                'verification_status': 'verified',
                'last_verified': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            all_identities.append(identity)

            # Create beneficiary designations for accounts
            if accounts:
                # Distribute percentages across accounts
                for account in accounts:
                    if num_beneficiaries == 1:
                        percentage = 100
                    elif i == 0:
                        percentage = random.choice([50, 60, 70])
                    elif i == 1 and num_beneficiaries == 2:
                        # Get first beneficiary's percentage for this account
                        first_ben_des = next((d for d in all_designations if d['account_id'] == account['account_id']), None)
                        if first_ben_des:
                            percentage = 100 - first_ben_des['percentage']
                        else:
                            percentage = 50
                    else:
                        # Third beneficiary gets remainder
                        existing_total = sum(d['percentage'] for d in all_designations if d['account_id'] == account['account_id'])
                        percentage = 100 - existing_total

                    designation = {
                        'account_id': account['account_id'],
                        'beneficiary_id': beneficiary_id,
                        'percentage': percentage,
                        'designation_type': 'primary',
                        'designated_date': (datetime.now() - timedelta(days=random.randint(365, 7300))).strftime("%Y-%m-%d")
                    }
                    all_designations.append(designation)

            print(f"  {i+1}. {full_name:<25} ({relationship}, {gender}) - CA resident")

            beneficiary_id += 1

        print()

    # Insert all beneficiaries
    print("=" * 80)
    print("INSERTING INTO DATABASES")
    print("=" * 80)
    print()

    conn_ben = sqlite3.connect(base_dir / "beneficiary_registry.db")
    c_ben = conn_ben.cursor()

    for ben in all_beneficiaries:
        c_ben.execute('''INSERT INTO beneficiaries
                         (beneficiary_id, ssn, first_name, last_name, full_name, gender, dob,
                          address_street, address_city, address_state, address_zip, phone, email)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (ben['beneficiary_id'], ben['ssn'], ben['first_name'], ben['last_name'],
                       ben['full_name'], ben['gender'], ben['dob'], ben['address_street'],
                       ben['address_city'], ben['address_state'], ben['address_zip'],
                       ben['phone'], ben['email']))

    for des in all_designations:
        c_ben.execute('''INSERT INTO beneficiary_designations
                         (account_id, beneficiary_id, percentage, designation_type, designated_date)
                         VALUES (?, ?, ?, ?, ?)''',
                      (des['account_id'], des['beneficiary_id'], des['percentage'],
                       des['designation_type'], des['designated_date']))

    conn_ben.commit()
    conn_ben.close()

    print(f"✓ Inserted {len(all_beneficiaries)} beneficiaries")
    print(f"✓ Created {len(all_designations)} beneficiary designations")

    # Insert identity records
    conn_id = sqlite3.connect(base_dir / "identity_verification.db")
    c_id = conn_id.cursor()

    for identity in all_identities:
        c_id.execute('''INSERT INTO identity_records
                        (ssn, first_name, last_name, full_name, gender, dob,
                         address_street, address_city, address_state, address_zip,
                         drivers_license, dl_state, dl_issue_date, dl_expiration,
                         height, weight, eye_color, hair_color, photo_reference,
                         verification_status, last_verified)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                     (identity['ssn'], identity['first_name'], identity['last_name'], identity['full_name'],
                      identity['gender'], identity['dob'], identity['address_street'], identity['address_city'],
                      identity['address_state'], identity['address_zip'], identity['drivers_license'],
                      identity['dl_state'], identity['dl_issue_date'], identity['dl_expiration'],
                      identity['height'], identity['weight'], identity['eye_color'], identity['hair_color'],
                      identity['photo_reference'], identity['verification_status'], identity['last_verified']))

    conn_id.commit()
    conn_id.close()

    print(f"✓ Inserted {len(all_identities)} identity records (CA driver's licenses)")
    print()

    print("=" * 80)
    print("REGENERATION COMPLETE")
    print("=" * 80)
    print()
    print(f"Summary:")
    print(f"  - Deceased: {len(deceased_list)} (unchanged)")
    print(f"  - Beneficiaries: {len(all_beneficiaries)} (1-3 per deceased)")
    print(f"  - All beneficiaries are California residents")
    print(f"  - All have CA driver's licenses")
    print(f"  - Logical relationships (matching last names where appropriate)")
    print()
    print("Next: Regenerate PERSON_REFERENCE_FOR_FORMS.docx")

if __name__ == "__main__":
    main()
