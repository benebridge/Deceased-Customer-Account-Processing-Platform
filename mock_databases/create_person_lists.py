#!/usr/bin/env python3
"""
Create comprehensive lists of all persons in the databases
- Deceased persons from DMF
- Beneficiaries from beneficiary_registry
- Identity records from identity_verification
"""

import sqlite3
import json
from pathlib import Path

def create_lists():
    base_dir = Path(__file__).parent

    # Output files
    deceased_file = base_dir / "LIST_ALL_DECEASED.txt"
    beneficiary_file = base_dir / "LIST_ALL_BENEFICIARIES.txt"
    identity_file = base_dir / "LIST_ALL_IDENTITY_RECORDS.txt"
    combined_file = base_dir / "LIST_ALL_PERSONS_COMBINED.txt"

    print("=" * 80)
    print("CREATING PERSON LISTS FROM DATABASES")
    print("=" * 80)

    # ========== DECEASED PERSONS ==========
    print("\nExtracting deceased persons from dmf_mock.db...")
    conn = sqlite3.connect(base_dir / "dmf_mock.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT * FROM deceased_persons ORDER BY case_id")
    deceased = [dict(row) for row in c.fetchall()]
    conn.close()

    print(f"✓ Found {len(deceased)} deceased persons")

    # Write deceased list
    with open(deceased_file, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("DECEASED PERSONS LIST (DMF Database)\n")
        f.write("=" * 80 + "\n")
        f.write(f"Total: {len(deceased)} persons\n")
        f.write("All from Los Angeles County, CA\n")
        f.write("=" * 80 + "\n\n")

        for person in deceased:
            f.write(f"CASE #{person['case_id']}: {person['full_name']}\n")
            f.write(f"  SSN: {person['ssn']}\n")
            f.write(f"  Gender: {person['gender']}\n")
            f.write(f"  DOB: {person['dob']}\n")
            f.write(f"  DOD: {person['dod']}\n")
            f.write(f"  Address: {person['address_street']}, {person['address_city']}, {person['address_state']} {person['address_zip']}\n")
            f.write(f"  Physical: Height {person['height']}, Weight {person['weight']} lbs, Eyes {person['eye_color']}\n")
            f.write("\n")

    print(f"✓ Created {deceased_file}")

    # ========== BENEFICIARIES ==========
    print("\nExtracting beneficiaries from beneficiary_registry.db...")
    conn = sqlite3.connect(base_dir / "beneficiary_registry.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT * FROM beneficiaries ORDER BY beneficiary_id")
    beneficiaries = [dict(row) for row in c.fetchall()]
    conn.close()

    print(f"✓ Found {len(beneficiaries)} beneficiaries")

    # Write beneficiaries list
    with open(beneficiary_file, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("BENEFICIARIES LIST (Beneficiary Registry Database)\n")
        f.write("=" * 80 + "\n")
        f.write(f"Total: {len(beneficiaries)} beneficiaries\n")
        f.write("Can live anywhere in the US\n")
        f.write("=" * 80 + "\n\n")

        for person in beneficiaries:
            f.write(f"BENEFICIARY #{person['beneficiary_id']}: {person['full_name']}\n")
            f.write(f"  SSN: {person['ssn']}\n")
            f.write(f"  Gender: {person['gender']}\n")
            f.write(f"  DOB: {person['dob']}\n")
            f.write(f"  Address: {person['address_street']}, {person['address_city']}, {person['address_state']} {person['address_zip']}\n")
            f.write(f"  Contact: {person['phone']}, {person['email']}\n")
            f.write("\n")

    print(f"✓ Created {beneficiary_file}")

    # ========== IDENTITY RECORDS ==========
    print("\nExtracting identity records from identity_verification.db...")
    conn = sqlite3.connect(base_dir / "identity_verification.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT * FROM identity_records ORDER BY id")
    identities = [dict(row) for row in c.fetchall()]
    conn.close()

    print(f"✓ Found {len(identities)} identity records")

    # Write identity records list
    with open(identity_file, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("IDENTITY VERIFICATION RECORDS LIST\n")
        f.write("=" * 80 + "\n")
        f.write(f"Total: {len(identities)} identity records\n")
        f.write("All beneficiaries (for ID verification)\n")
        f.write("=" * 80 + "\n\n")

        for person in identities:
            f.write(f"IDENTITY #{person['id']}: {person['full_name']}\n")
            f.write(f"  SSN: {person['ssn']}\n")
            f.write(f"  Gender: {person['gender']}\n")
            f.write(f"  DOB: {person['dob']}\n")
            f.write(f"  Address: {person['address_street']}, {person['address_city']}, {person['address_state']} {person['address_zip']}\n")
            f.write(f"  Driver's License: {person['drivers_license']} ({person['dl_state']})\n")
            f.write(f"  DL Expiration: {person['dl_expiration']}\n")
            f.write(f"  Physical: Height {person['height']}, Weight {person['weight']} lbs, Eyes {person['eye_color']}\n")
            f.write(f"  Photo Reference: {person['photo_reference']}\n")
            f.write(f"  Verification Status: {person['verification_status']}\n")
            f.write("\n")

    print(f"✓ Created {identity_file}")

    # ========== COMBINED LIST ==========
    print("\nCreating combined list...")

    with open(combined_file, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("COMBINED PERSONS LIST - ALL DATABASES\n")
        f.write("=" * 80 + "\n")
        f.write(f"Deceased Persons: {len(deceased)}\n")
        f.write(f"Beneficiaries: {len(beneficiaries)}\n")
        f.write(f"Identity Records: {len(identities)}\n")
        f.write(f"Total Unique Persons: {len(deceased) + len(beneficiaries)}\n")
        f.write("=" * 80 + "\n\n")

        # Deceased section
        f.write("=" * 80 + "\n")
        f.write("DECEASED PERSONS (All from Los Angeles County, CA)\n")
        f.write("=" * 80 + "\n\n")

        for person in deceased:
            f.write(f"CASE #{person['case_id']}: {person['full_name']}\n")
            f.write(f"  Type: DECEASED\n")
            f.write(f"  SSN: {person['ssn']}\n")
            f.write(f"  Gender: {person['gender']}\n")
            f.write(f"  DOB: {person['dob']}\n")
            f.write(f"  DOD: {person['dod']}\n")
            f.write(f"  Address: {person['address_street']}, {person['address_city']}, {person['address_state']} {person['address_zip']}\n")
            f.write(f"  Physical: Height {person['height']}, Weight {person['weight']} lbs, Eyes {person['eye_color']}\n")
            f.write("\n")

        # Beneficiaries section
        f.write("\n" + "=" * 80 + "\n")
        f.write("BENEFICIARIES (Can live anywhere)\n")
        f.write("=" * 80 + "\n\n")

        for person in beneficiaries:
            # Find corresponding identity record
            identity = next((i for i in identities if i['ssn'] == person['ssn']), None)

            f.write(f"BENEFICIARY #{person['beneficiary_id']}: {person['full_name']}\n")
            f.write(f"  Type: BENEFICIARY\n")
            f.write(f"  SSN: {person['ssn']}\n")
            f.write(f"  Gender: {person['gender']}\n")
            f.write(f"  DOB: {person['dob']}\n")
            f.write(f"  Address: {person['address_street']}, {person['address_city']}, {person['address_state']} {person['address_zip']}\n")
            f.write(f"  Contact: {person['phone']}, {person['email']}\n")

            if identity:
                f.write(f"  Driver's License: {identity['drivers_license']} ({identity['dl_state']})\n")
                f.write(f"  DL Expiration: {identity['dl_expiration']}\n")
                f.write(f"  Physical: Height {identity['height']}, Weight {identity['weight']} lbs, Eyes {identity['eye_color']}\n")
                f.write(f"  Photo: {identity['photo_reference']}\n")
                f.write(f"  Verification: {identity['verification_status']}\n")

            f.write("\n")

    print(f"✓ Created {combined_file}")

    # Create summary statistics
    print("\n" + "=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)
    print(f"Deceased Persons: {len(deceased)}")
    print(f"  - All from Los Angeles County, CA")
    print(f"  - Gender breakdown: {sum(1 for p in deceased if p['gender'] == 'M')} Male, {sum(1 for p in deceased if p['gender'] == 'F')} Female")
    print(f"\nBeneficiaries: {len(beneficiaries)}")
    print(f"  - Gender breakdown: {sum(1 for p in beneficiaries if p['gender'] == 'M')} Male, {sum(1 for p in beneficiaries if p['gender'] == 'F')} Female")

    # Count unique states for beneficiaries
    states = set(p['address_state'] for p in beneficiaries)
    print(f"  - Living in {len(states)} different states: {', '.join(sorted(states))}")

    print(f"\nIdentity Records: {len(identities)}")
    print(f"  - All identity records are for beneficiaries")
    print(f"  - Verification status: {sum(1 for i in identities if i['verification_status'] == 'verified')} verified")

    # Count DL states
    dl_states = {}
    for identity in identities:
        state = identity['dl_state']
        dl_states[state] = dl_states.get(state, 0) + 1

    print(f"\nDriver's License States:")
    for state, count in sorted(dl_states.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {state}: {count}")

    print("\n" + "=" * 80)
    print("FILES CREATED")
    print("=" * 80)
    print(f"1. {deceased_file.name}")
    print(f"2. {beneficiary_file.name}")
    print(f"3. {identity_file.name}")
    print(f"4. {combined_file.name}")
    print("\nAll lists created successfully!")

if __name__ == "__main__":
    create_lists()
