#!/usr/bin/env python3
"""
Generate TEST beneficiary claim form for the first beneficiary designation
"""

import sqlite3
from pathlib import Path
from datetime import datetime
import random

try:
    from pypdf import PdfReader, PdfWriter
    HAS_PYPDF = True
except ImportError:
    try:
        from PyPDF2 import PdfReader, PdfWriter
        HAS_PYPDF = True
    except ImportError:
        HAS_PYPDF = False

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
    # Remove any existing formatting
    ssn_clean = ssn.replace('-', '').replace(' ', '')
    return f"{ssn_clean[:3]}-{ssn_clean[3:5]}-{ssn_clean[5:]}"

def main():
    base_dir = Path(__file__).parent
    parent_dir = base_dir.parent
    template_path = parent_dir / "Beneficiary-Claim-Form-IRA-After-2019-1.pdf"

    if not template_path.exists():
        print(f"Error: Template not found at {template_path}")
        return

    if not HAS_PYPDF:
        print("Error: pypdf or PyPDF2 is required. Install with: pip3 install pypdf")
        return

    print("=" * 80)
    print("GENERATING TEST BENEFICIARY CLAIM FORM")
    print("=" * 80)
    print()
    print(f"Template: {template_path}")
    print()

    # Get first beneficiary designation
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
        LIMIT 1
    """)

    des = dict(c_ben.fetchone())
    conn_ben.close()

    # Get account info
    conn_fin = sqlite3.connect(base_dir / "financial_accounts.db")
    conn_fin.row_factory = sqlite3.Row
    c_fin = conn_fin.cursor()
    c_fin.execute("SELECT * FROM accounts WHERE account_id = ?", (des['account_id'],))
    account = dict(c_fin.fetchone())
    conn_fin.close()

    # Get deceased info
    conn_dmf = sqlite3.connect(base_dir / "dmf_mock.db")
    conn_dmf.row_factory = sqlite3.Row
    c_dmf = conn_dmf.cursor()
    c_dmf.execute("SELECT * FROM deceased_persons WHERE case_id = ?", (account['deceased_case_id'],))
    deceased = dict(c_dmf.fetchone())
    conn_dmf.close()

    print("Data Summary:")
    print(f"  Deceased: {deceased['full_name']} (DOD: {deceased['dod']})")
    print(f"  Account: {account['account_number']}")
    print(f"  Beneficiary: {des['full_name']} ({des['percentage']}%)")
    print()

    # Read the PDF template
    reader = PdfReader(str(template_path))
    writer = PdfWriter()

    # Check if PDF has form fields
    if reader.get_fields() is None:
        print("⚠️  This PDF does not appear to have fillable form fields.")
        print("   We'll need to use a different approach (overlaying text on the PDF).")
        print()

        # List all fields if they exist
        print("Analyzing PDF structure...")
        print(f"  Pages: {len(reader.pages)}")
        print()
        return

    # Get form fields
    fields = reader.get_fields()
    print(f"Found {len(fields)} form fields in the PDF:")
    print()

    for field_name, field in fields.items():
        print(f"  - {field_name}: {field.get('/FT', 'Unknown type')}")

    print()
    print("=" * 80)
    print("FORM FIELD MAPPING")
    print("=" * 80)
    print()

    # Map our data to PDF form fields (we'll need to discover the actual field names)
    # For now, just show what data we have
    form_data = {
        # Section 1: Deceased Account Owner Information
        'deceased_full_name': deceased['full_name'],
        'account_number': account['account_number'],
        'date_of_death': format_date_mmddyyyy(deceased['dod']),

        # Section 2: Beneficiary Information
        'beneficiary_name': des['full_name'],
        'beneficiary_ssn': format_ssn(des['ssn']),
        'beneficiary_dob': format_date_mmddyyyy(des['dob']),
        'physical_address': des['address_street'],
        'city': des['address_city'],
        'state': des['address_state'],
        'zip': des['address_zip'],
        'main_phone': des['phone'],
        'email': des['email'],
        'gender': 'Male' if des['gender'] == 'M' else 'Female',
        'us_citizen': True,
        'country': 'United States',
        'occupation': 'Professional',
    }

    print("Data to fill:")
    for key, value in form_data.items():
        print(f"  {key}: {value}")

    print()
    print("Next steps:")
    print("1. Identify the actual PDF form field names")
    print("2. Map our data to those field names")
    print("3. Fill the form programmatically")
    print()

if __name__ == "__main__":
    main()
