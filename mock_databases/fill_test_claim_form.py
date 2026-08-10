#!/usr/bin/env python3
"""
Fill TEST beneficiary claim form for the first beneficiary designation
Creates a filled PDF form
"""

import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import random

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

from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import io

def format_date_mmddyyyy(date_str):
    """Convert YYYY-MM-DD or M/D/YYYY to MM/DD/YYYY"""
    # Handle both input formats
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
    # If same last name and different gender, likely spouse
    if ben_last_name == deceased_last_name and ben_gender != deceased_gender:
        return 'spouse'
    # Otherwise, assume child (for simplicity)
    elif ben_last_name == deceased_last_name:
        return 'child'
    else:
        return 'non-spouse'

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
    print("FILLING TEST BENEFICIARY CLAIM FORM")
    print("=" * 80)
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

    # Determine relationship
    relationship = determine_relationship(
        des['last_name'],
        deceased['last_name'],
        des['gender'],
        deceased['gender']
    )

    print("Filling form with:")
    print(f"  Deceased: {deceased['full_name']}")
    print(f"  Account: {account['account_number']}")
    print(f"  Beneficiary: {des['full_name']}")
    print(f"  Relationship: {relationship}")
    print()

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
        'US Citizen': '/Yes',  # Checkbox
    }

    # Section 3: Beneficiary Relationship and Election (based on relationship)
    if relationship == 'spouse':
        # Spouse: Check Section A boxes
        form_fields.update({
            'Surviving spouse': '/Yes',
            'Treat IRA as my own': '/Yes',
        })
    else:
        # Non-spouse: Check Section B boxes
        form_fields.update({
            'NonSpouse': '/Yes',
            '10Year Rule Payout Establish Beneficiary IRA': '/Yes',
            # Fill in beneficiary name in Section B (this replaces Rosa Harms)
            'Name-0': des['full_name'],
            'DOB-0': format_date_mmddyyyy(des['dob']),
        })

    # Clear any pre-filled example data (like "Rosa Harms")
    # These might be in the original PDF template
    form_fields.update({
        'Name of Beneficiary': des['full_name'],  # Make sure this overwrites any sample data
    })

    # We'll need to add signature graphics/text after filling form fields
    # For now, leave signature fields empty as they need to be drawn on the PDF

    # Fill the form fields using the newer API
    print("Filling form fields:")
    filled_count = 0

    # Update all form fields at once
    try:
        writer.update_page_form_field_values(
            writer.pages[0],
            form_fields
        )
        filled_count = len(form_fields)
        print(f"  ✓ Filled {filled_count} fields on page 1")
    except Exception as e:
        print(f"  ⚠️  Error filling page 1: {e}")
        print(f"  Trying alternative method...")

        # Try filling each field individually
        for field_name, value in form_fields.items():
            try:
                writer.update_page_form_field_values(
                    writer.pages[0],
                    {field_name: value}
                )
                print(f"    ✓ {field_name}")
                filled_count += 1
            except Exception as e2:
                print(f"    ⚠️  {field_name}: {str(e2)[:50]}")

    # Try to fill fields on page 2 as well
    if len(writer.pages) > 1:
        try:
            writer.update_page_form_field_values(
                writer.pages[1],
                form_fields
            )
            print(f"  ✓ Also filled fields on page 2")
        except:
            pass

    print()
    print(f"Filled {filled_count} fields")
    print()

    # Now add signatures and notary information by overlaying text on page 2
    print("Adding signatures and notary information...")

    # Save intermediate PDF to a BytesIO buffer
    temp_buffer = io.BytesIO()
    writer.write(temp_buffer)
    temp_buffer.seek(0)

    # Re-read the PDF to add signature overlays
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter

    # Get page 2 dimensions (signatures are on page 2)
    page2 = reader.pages[1]
    page_width = float(page2.mediabox.width)
    page_height = float(page2.mediabox.height)

    # Create signature overlay
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=(page_width, page_height))

    # Reset to black for text
    can.setFillColorRGB(0, 0, 0)

    # Beneficiary Signature (handwritten-style cursive)
    # Use italic font to simulate cursive handwriting
    can.setFont("Helvetica-Oblique", 22)

    # Position moved down much more (twice as much)
    signature_text = f"{des['first_name']} {des['last_name']}"
    sig_x = 120
    sig_y = 120

    # Cover "Rosa Harms" signature with white rectangle positioned directly behind Karen Thompson
    can.setFillColorRGB(1, 1, 1)  # White color
    # Rectangle positioned exactly where Karen Thompson signature will be
    can.rect(sig_x - 5, sig_y - 5, 200, 30, fill=1, stroke=0)  # Behind the signature

    # Reset to black for signature text
    can.setFillColorRGB(0, 0, 0)
    can.drawString(sig_x, sig_y, signature_text)  # Draw signature on top of white rectangle

    # Date next to signature - moved down much more
    can.setFont("Helvetica", 11)
    can.drawString(480, 120, signature_date.strftime("%m/%d/%Y"))  # Moved down twice as much

    # Notary section - "Sworn to and subscribed before me on" date
    # Moved down and slightly left
    can.setFont("Helvetica", 10)
    can.drawString(270, 95, notary_date.strftime("%B %d"))  # Moved down and slightly left

    # Year - only last 2 digits, lined up next to "20"
    year_last_two = str(notary_date.year)[2:]  # Get last 2 digits (e.g., "26")
    can.drawString(405, 95, year_last_two)  # Moved down and slightly left

    # Notary signature - handwritten style, moved slightly right
    can.setFont("Helvetica-Oblique", 20)
    can.drawString(95, 70, "Sarah J. Martinez")  # Moved slightly right

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

    print("  ✓ Added beneficiary signature")
    print("  ✓ Added signature date")
    print("  ✓ Added notary information")
    print()

    # Save the final PDF
    output_path = base_dir / f"TEST_Claim_Form_{des['beneficiary_id']:03d}_{des['last_name']}_{des['first_name']}.pdf"
    with open(output_path, 'wb') as output_file:
        final_writer.write(output_file)

    print("=" * 80)
    print("TEST FORM GENERATED")
    print("=" * 80)
    print(f"Saved to: {output_path}")
    print()
    print("NEXT STEPS:")
    print("1. Open the generated PDF to check if fields are filled correctly")
    print("2. Verify the data alignment and completeness")
    print("3. Check the signatures and notary information")
    print("4. Once approved, we can generate all 93 forms")
    print()

if __name__ == "__main__":
    main()
