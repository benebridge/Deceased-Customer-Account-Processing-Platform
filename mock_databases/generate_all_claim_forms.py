#!/usr/bin/env python3
"""
Generate ALL beneficiary claim forms (93 total)
One form for each beneficiary-account combination
"""

import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import random
import io

try:
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import NameObject
    HAS_PYPDF = True
except ImportError:
    try:
        from PyPDF2 import PdfReader, PdfWriter
        from PyPDF2.generic import NameObject
        HAS_PYPDF = True
    except ImportError:
        HAS_PYPDF = False

from reportlab.pdfgen import canvas

def format_date_mmddyyyy(date_str):
    """Convert YYYY-MM-DD or M/D/YYYY to MM/DD/YYYY"""
    for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%-m/%-d/%Y"]:
        try:
            date_obj = datetime.strptime(date_str, fmt)
            return date_obj.strftime("%m/%d/%Y")
        except:
            continue
    return date_str

def format_ssn(ssn):
    """Format SSN as XXX-XX-XXXX"""
    if '-' in ssn:
        return ssn
    ssn_clean = ssn.replace('-', '').replace(' ', '')
    return f"{ssn_clean[:3]}-{ssn_clean[3:5]}-{ssn_clean[5:]}"

def determine_relationship(ben_last_name, deceased_last_name, ben_gender, deceased_gender):
    """Determine relationship based on names and gender"""
    if ben_last_name == deceased_last_name and ben_gender != deceased_gender:
        return 'spouse'
    elif ben_last_name == deceased_last_name:
        return 'child'
    else:
        return 'non-spouse'

def generate_claim_form(des, account, deceased, template_path, output_path):
    """Generate a single claim form"""

    if not HAS_PYPDF:
        print("Error: pypdf or PyPDF2 is required")
        return False

    # Determine relationship
    relationship = determine_relationship(
        des['last_name'],
        deceased['last_name'],
        des['gender'],
        deceased['gender']
    )

    # Read the PDF
    reader = PdfReader(str(template_path))
    writer = PdfWriter()

    # Clone the entire PDF including form structure
    writer.append(reader)

    # Generate signature date (recent date)
    signature_date = datetime.now() - timedelta(days=random.randint(1, 30))

    # Generate notary date (same or 1-2 days after signature)
    notary_date = signature_date + timedelta(days=random.randint(0, 2))

    # Prepare form field data
    form_fields = {
        # Section 1: Deceased Account Owner Information
        'Full Name': deceased['full_name'],
        'Account': account['account_number'],
        'Date of Death': format_date_mmddyyyy(deceased['dod']),

        # Section 2: Beneficiary Information
        'Name of Beneficiary': des['full_name'],
        'SS or Tax I D': format_ssn(des['ssn']),
        'Birth Date': format_date_mmddyyyy(des['dob']),
        'Physical Address required': des['address_street'],
        'City': des['address_city'],
        'State': des['address_state'],
        'Zip': des['address_zip'],
        'Occupation': 'Professional',
        'Main Phone required': des['phone'],
        'Email Address': des['email'],
        'Gender': 'Male' if des['gender'] == 'M' else 'Female',
        'Country of Citizenship': 'United States',
        'US Citizen': '/Yes',
    }

    # Section 3: Beneficiary Relationship and Election (based on relationship)
    if relationship == 'spouse':
        form_fields.update({
            'Surviving spouse': '/Yes',
            'Treat IRA as my own': '/Yes',
        })
    else:
        form_fields.update({
            'NonSpouse': '/Yes',
            '10Year Rule Payout Establish Beneficiary IRA': '/Yes',
            'Name-0': des['full_name'],
            'DOB-0': format_date_mmddyyyy(des['dob']),
        })

    # Clear any pre-filled example data
    form_fields.update({
        'Name of Beneficiary': des['full_name'],
    })

    # Fill the form fields
    try:
        writer.update_page_form_field_values(
            writer.pages[0],
            form_fields
        )
    except Exception as e:
        print(f"  ⚠️  Error filling page 1: {e}")
        return False

    # Try to fill fields on page 2 as well
    if len(writer.pages) > 1:
        try:
            writer.update_page_form_field_values(
                writer.pages[1],
                form_fields
            )
        except:
            pass

    # Save intermediate PDF to a BytesIO buffer
    temp_buffer = io.BytesIO()
    writer.write(temp_buffer)
    temp_buffer.seek(0)

    # Re-read the PDF to add signature overlays
    page2 = reader.pages[1]
    page_width = float(page2.mediabox.width)
    page_height = float(page2.mediabox.height)

    # Create signature overlay
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=(page_width, page_height))

    # Reset to black for text
    can.setFillColorRGB(0, 0, 0)

    # Beneficiary Signature
    can.setFont("Helvetica-Oblique", 22)
    signature_text = f"{des['first_name']} {des['last_name']}"
    sig_x = 120
    sig_y = 120

    # Cover Rosa Harms with white rectangle positioned directly behind signature
    can.setFillColorRGB(1, 1, 1)
    can.rect(sig_x - 5, sig_y - 5, 200, 30, fill=1, stroke=0)

    # Draw signature on top
    can.setFillColorRGB(0, 0, 0)
    can.drawString(sig_x, sig_y, signature_text)

    # Date next to signature
    can.setFont("Helvetica", 11)
    can.drawString(480, 120, signature_date.strftime("%m/%d/%Y"))

    # Notary section
    can.setFont("Helvetica", 10)
    can.drawString(270, 95, notary_date.strftime("%B %d"))

    # Year - only last 2 digits
    year_last_two = str(notary_date.year)[2:]
    can.drawString(405, 95, year_last_two)

    # Notary signature
    can.setFont("Helvetica-Oblique", 20)
    can.drawString(95, 70, "Sarah J. Martinez")

    can.save()

    # Move to the beginning of the BytesIO buffer
    packet.seek(0)

    # Read the signature overlay
    overlay_pdf = PdfReader(packet)

    # Merge overlay with the filled PDF
    final_reader = PdfReader(temp_buffer)
    final_writer = PdfWriter()

    # Add page 1 without overlay
    final_writer.add_page(final_reader.pages[0])

    # Add page 2 with signature overlay
    page2_final = final_reader.pages[1]
    page2_final.merge_page(overlay_pdf.pages[0])
    final_writer.add_page(page2_final)

    # Save the final PDF
    with open(output_path, 'wb') as output_file:
        final_writer.write(output_file)

    return True

def main():
    base_dir = Path(__file__).parent
    parent_dir = base_dir.parent
    template_path = parent_dir / "Beneficiary-Claim-Form-IRA-After-2019-1.pdf"

    if not template_path.exists():
        print(f"Error: Template not found at {template_path}")
        return

    if not HAS_PYPDF:
        print("Error: pypdf or PyPDF2 is required")
        return

    # Create output directory
    output_dir = parent_dir / "Generated_Claim_Forms"
    output_dir.mkdir(exist_ok=True)

    print("=" * 80)
    print("GENERATING ALL BENEFICIARY CLAIM FORMS")
    print("=" * 80)
    print()

    # Get all beneficiary designations
    conn_ben = sqlite3.connect(base_dir / "beneficiary_registry.db")
    conn_ben.row_factory = sqlite3.Row
    c_ben = conn_ben.cursor()

    c_ben.execute("""
        SELECT
            bd.account_id,
            bd.beneficiary_id,
            bd.percentage,
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

    print(f"Template: {template_path}")
    print(f"Output directory: {output_dir}")
    print(f"Total forms to generate: {len(designations)}")
    print()

    # Generate all forms
    success_count = 0
    for i, des in enumerate(designations, 1):
        account = accounts.get(des['account_id'])
        if not account:
            print(f"⚠️  Skipping form {i}: Account {des['account_id']} not found")
            continue

        deceased_person = deceased.get(account['deceased_case_id'])
        if not deceased_person:
            print(f"⚠️  Skipping form {i}: Deceased person not found")
            continue

        # Generate filename
        filename = f"Claim_Form_{des['account_id']}_{des['beneficiary_id']:03d}_{des['last_name']}_{des['first_name']}.pdf"
        output_path = output_dir / filename

        # Generate the form
        if generate_claim_form(des, account, deceased_person, template_path, output_path):
            print(f"✓ {i}/{len(designations)}: {filename}")
            success_count += 1
        else:
            print(f"✗ {i}/{len(designations)}: Failed to generate {filename}")

    print()
    print("=" * 80)
    print("COMPLETE")
    print("=" * 80)
    print(f"Successfully generated {success_count} of {len(designations)} beneficiary claim forms")
    print(f"Output directory: {output_dir}")
    print()

if __name__ == "__main__":
    main()
