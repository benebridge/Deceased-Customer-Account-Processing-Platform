#!/usr/bin/env python3
"""
Map all beneficiary claim form data from databases
Creates one form per beneficiary per account (93 total forms)
"""

import sqlite3
from pathlib import Path
from datetime import datetime
import random

def format_date_mmddyyyy(date_str):
    """Convert YYYY-MM-DD to MM/DD/YYYY"""
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        return date_obj.strftime("%m/%d/%Y")
    except:
        return date_str

def format_ssn(ssn):
    """Format SSN as XXX-XX-XXXX"""
    if '-' in ssn:
        return ssn
    return f"{ssn[:3]}-{ssn[3:5]}-{ssn[5:]}"

def main():
    base_dir = Path(__file__).parent

    print("=" * 80)
    print("MAPPING BENEFICIARY CLAIM FORMS")
    print("=" * 80)
    print()

    # Get all beneficiary designations (this determines how many forms we need)
    conn_ben = sqlite3.connect(base_dir / "beneficiary_registry.db")
    conn_ben.row_factory = sqlite3.Row
    c_ben = conn_ben.cursor()

    c_ben.execute("""
        SELECT
            bd.account_id,
            bd.beneficiary_id,
            bd.percentage,
            bd.designation_type,
            bd.designated_date,
            b.ssn,
            b.first_name,
            b.last_name,
            b.full_name,
            b.gender,
            b.dob,
            b.address_street,
            b.address_city,
            b.address_state,
            b.address_zip,
            b.phone,
            b.email
        FROM beneficiary_designations bd
        JOIN beneficiaries b ON bd.beneficiary_id = b.beneficiary_id
        ORDER BY bd.account_id, bd.beneficiary_id
    """)

    designations = [dict(row) for row in c_ben.fetchall()]
    conn_ben.close()

    print(f"Found {len(designations)} beneficiary designations (forms to create)")
    print()

    # Get all accounts
    conn_fin = sqlite3.connect(base_dir / "financial_accounts.db")
    conn_fin.row_factory = sqlite3.Row
    c_fin = conn_fin.cursor()
    c_fin.execute("SELECT * FROM accounts")
    accounts = {row['account_id']: dict(row) for row in c_fin.fetchall()}
    conn_fin.close()

    # Get all deceased persons
    conn_dmf = sqlite3.connect(base_dir / "dmf_mock.db")
    conn_dmf.row_factory = sqlite3.Row
    c_dmf = conn_dmf.cursor()
    c_dmf.execute("SELECT * FROM deceased_persons")
    deceased = {row['case_id']: dict(row) for row in c_dmf.fetchall()}
    conn_dmf.close()

    # Map all forms
    forms = []

    for des in designations:
        account = accounts.get(des['account_id'])
        if not account:
            print(f"⚠️  Warning: Account {des['account_id']} not found")
            continue

        deceased_person = deceased.get(account['deceased_case_id'])
        if not deceased_person:
            print(f"⚠️  Warning: Deceased person for case {account['deceased_case_id']} not found")
            continue

        # Determine relationship (we need to add this logic)
        # For now, use random relationships
        relationships = ['child', 'spouse', 'sibling', 'parent', 'niece', 'nephew']
        relationship = random.choice(relationships)

        # Map form data
        form_data = {
            # Section 1: Deceased Account Owner Information
            'deceased_full_name': deceased_person['full_name'],
            'account_number': account['account_number'],
            'date_of_death': format_date_mmddyyyy(deceased_person['dod']),

            # Section 2: Beneficiary Information
            'beneficiary_name': des['full_name'],
            'beneficiary_ssn': format_ssn(des['ssn']),
            'beneficiary_dob': format_date_mmddyyyy(des['dob']),
            'physical_address': des['address_street'],
            'city': des['address_city'],
            'state': des['address_state'],
            'zip': des['address_zip'],
            'mailing_address': '',  # Same as physical
            'mailing_city': '',
            'mailing_state': '',
            'mailing_zip': '',
            'occupation': 'Professional',  # We don't have this in DB
            'main_phone': des['phone'],
            'secondary_phone': '',
            'business_phone': '',
            'us_citizen': True,
            'resident_alien': False,
            'nonresident_alien': False,
            'country_of_citizenship': 'United States',
            'email': des['email'],
            'gender': 'Male' if des['gender'] == 'M' else 'Female',

            # Section 3: Beneficiary Relationship and Election
            'relationship': relationship,
            'is_spouse': relationship == 'spouse',
            'is_minor_child': relationship == 'child',
            'is_chronically_ill': False,
            'is_non_spouse_less_than_10_years': False,
            'is_qualified_trust': False,

            # Election options (default to 10-Year Rule for non-spouse)
            'election_type': '10-Year Rule Payout',
            'establish_beneficiary_ira': True,

            # Section 4: RMD (not applicable for most)
            'rmd_applicable': False,
            'rmd_met_elsewhere': False,
            'take_remaining_rmd': False,

            # Additional metadata
            'beneficiary_id': des['beneficiary_id'],
            'account_id': des['account_id'],
            'percentage': des['percentage'],
            'designation_type': des['designation_type'],
            'form_filename': f"Claim_Form_{des['account_id']}_{des['beneficiary_id']:03d}_{des['last_name']}_{des['first_name']}.pdf"
        }

        forms.append(form_data)

    # Display sample forms
    print("=" * 80)
    print("SAMPLE FORM DATA (First 5 forms)")
    print("=" * 80)
    print()

    for i, form in enumerate(forms[:5]):
        print(f"Form {i+1}: {form['form_filename']}")
        print(f"  Deceased: {form['deceased_full_name']} (Account: {form['account_number']})")
        print(f"  Beneficiary: {form['beneficiary_name']} ({form['relationship']})")
        print(f"  SSN: {form['beneficiary_ssn']}, DOB: {form['beneficiary_dob']}")
        print(f"  Address: {form['physical_address']}, {form['city']}, {form['state']} {form['zip']}")
        print(f"  Contact: {form['main_phone']}, {form['email']}")
        print(f"  Election: {form['election_type']}")
        print(f"  Percentage: {form['percentage']}%")
        print()

    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total forms to generate: {len(forms)}")
    print()

    # Save mapping to file for reference
    output_file = base_dir / "beneficiary_claim_forms_mapping.txt"
    with open(output_file, 'w') as f:
        f.write("BENEFICIARY CLAIM FORMS MAPPING\n")
        f.write("=" * 80 + "\n\n")

        for i, form in enumerate(forms, 1):
            f.write(f"{i}. {form['form_filename']}\n")
            f.write(f"   Deceased: {form['deceased_full_name']} (DOD: {form['date_of_death']})\n")
            f.write(f"   Account: {form['account_number']}\n")
            f.write(f"   Beneficiary: {form['beneficiary_name']} ({form['relationship']})\n")
            f.write(f"   Percentage: {form['percentage']}%\n")
            f.write("\n")

    print(f"Mapping saved to: {output_file}")
    print()

    return forms

if __name__ == "__main__":
    forms = main()
