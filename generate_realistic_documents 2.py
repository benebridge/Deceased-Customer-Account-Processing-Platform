"""
Enhanced Realistic Document Generator for BeneBridge POC

Generates documents that closely match official formats:
- California Death Certificate (matching LA County format)
- CNB Custody Beneficiary Claim Form
- California Driver's License (front and back)

All documents match real-world layouts and formatting.
"""

import sqlite3
import random
import string
import os
import json
from datetime import datetime, timedelta
from faker import Faker
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from PIL import Image, ImageDraw, ImageFont
import qrcode
from io import BytesIO

fake = Faker('en_US')

# SSA test SSN range
TEST_SSN_RANGE = range(987654320, 987654330)

# Distributions from Chapter 5
ACCOUNT_TYPES = {
    'IRA': 0.40,
    '401k': 0.25,
    'Life Insurance': 0.15,
    'Trust': 0.10,
    'Brokerage': 0.10
}

COMPLEXITY_LEVELS = {
    'simple': 0.60,
    'moderate': 0.30,
    'complex': 0.10
}

CERT_TYPES = {
    'blockchain': 0.15,
    'physical': 0.85
}

FRAUD_RATE = 0.05

DOCUMENT_QUALITY = {
    'high': 0.70,
    'medium': 0.20,
    'low': 0.10
}


class RealisticDocumentGenerator:
    """Generates documents matching official formats"""

    def __init__(self, output_dir='synthetic_cases'):
        self.output_dir = output_dir
        self.styles = getSampleStyleSheet()

    def generate_california_death_certificate(self, case_data, case_dir, quality='high'):
        """
        Generate realistic California death certificate matching the official format
        from Los Angeles County Department of Public Health
        """

        cert_path = os.path.join(case_dir, 'death_certificate.pdf')

        # Create PDF with custom drawing
        c = canvas.Canvas(cert_path, pagesize=letter)
        width, height = letter

        # Draw ornate border (simulating official certificate border)
        c.setStrokeColor(colors.HexColor('#003D5B'))
        c.setLineWidth(3)
        c.rect(20, 20, width-40, height-40, stroke=1, fill=0)

        # Inner decorative border
        c.setLineWidth(1)
        c.rect(25, 25, width-50, height-50, stroke=1, fill=0)

        # Header banner
        c.setFillColor(colors.HexColor('#003D5B'))
        c.roundRect(40, height-100, width-80, 45, 10, stroke=0, fill=1)

        # "STATE OF CALIFORNIA" header
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(width/2, height-65, "STATE OF CALIFORNIA")

        # "CERTIFICATION OF VITAL RECORD" subheader
        c.setFont("Helvetica", 10)
        c.drawCentredString(width/2, height-80, "CERTIFICATION OF VITAL RECORD")

        # County header
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 24)
        c.drawCentredString(width/2, height-130, "COUNTY OF LOS ANGELES")

        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(width/2, height-150, "DEPARTMENT OF PUBLIC HEALTH")

        # Certificate number (top right)
        c.setFont("Helvetica", 9)
        c.drawRightString(width-60, height-120, str(case_data['death_certificate_number']))
        c.drawRightString(width-60, height-132, "LOCAL REGISTRATION NUMBER")

        # State file number (top left)
        state_file = f"{random.randint(3000000, 4000000)}"
        c.drawString(60, height-120, state_file)
        c.drawString(60, height-132, "STATE FILE NUMBER")

        # Main content area starts
        y_position = height - 190

        # Section: Decedent Information
        c.setFont("Helvetica-Bold", 10)
        c.drawString(60, y_position, "1. NAME OF DECEDENT (First, Middle, Last)")
        c.setFont("Helvetica", 10)
        c.drawString(280, y_position, str(case_data['deceased_name']).upper())

        y_position -= 20
        c.setFont("Helvetica-Bold", 10)
        c.drawString(60, y_position, "2. SEX")
        c.setFont("Helvetica", 10)
        sex = random.choice(['M', 'F'])
        c.drawString(120, y_position, sex)

        c.setFont("Helvetica-Bold", 10)
        c.drawString(200, y_position, "3. SOCIAL SECURITY NUMBER")
        c.setFont("Helvetica", 10)
        c.drawString(380, y_position, str(case_data['deceased_ssn']))

        y_position -= 20
        c.setFont("Helvetica-Bold", 10)
        c.drawString(60, y_position, "4. DATE OF BIRTH")
        c.setFont("Helvetica", 10)
        c.drawString(180, y_position, str(case_data['date_of_birth']))

        c.setFont("Helvetica-Bold", 10)
        c.drawString(320, y_position, "5. AGE")
        c.setFont("Helvetica", 10)
        c.drawString(370, y_position, str(case_data.get('age_at_death', 'N/A')))

        c.setFont("Helvetica-Bold", 10)
        c.drawString(420, y_position, "6. DATE OF DEATH")
        c.setFont("Helvetica", 10)
        c.drawString(520, y_position, str(case_data['date_of_death']))

        y_position -= 25
        c.setFont("Helvetica-Bold", 10)
        c.drawString(60, y_position, "7. BIRTHPLACE")
        c.setFont("Helvetica", 10)
        birthplace = random.choice(['CALIFORNIA', 'NEW YORK', 'TEXAS', 'ILLINOIS', 'FLORIDA'])
        c.drawString(160, y_position, birthplace)

        c.setFont("Helvetica-Bold", 10)
        c.drawString(320, y_position, "8. MARITAL STATUS")
        c.setFont("Helvetica", 10)
        marital = random.choice(['MARRIED', 'DIVORCED', 'WIDOWED', 'NEVER MARRIED'])
        c.drawString(450, y_position, marital)

        y_position -= 25
        c.setFont("Helvetica-Bold", 10)
        c.drawString(60, y_position, "9. SURVIVING SPOUSE (if wife, give maiden name)")
        if case_data['beneficiary_relationship'] == 'spouse':
            c.setFont("Helvetica", 10)
            c.drawString(350, y_position, str(case_data['beneficiary_name']).upper())

        y_position -= 25
        c.setFont("Helvetica-Bold", 10)
        c.drawString(60, y_position, "10. FATHER'S NAME")
        c.setFont("Helvetica", 10)
        c.drawString(200, y_position, fake.name().upper())

        y_position -= 20
        c.setFont("Helvetica-Bold", 10)
        c.drawString(60, y_position, "11. MOTHER'S MAIDEN NAME")
        c.setFont("Helvetica", 10)
        c.drawString(230, y_position, fake.name_female().upper())

        y_position -= 25
        c.setFont("Helvetica-Bold", 10)
        c.drawString(60, y_position, "12. INFORMANT")
        c.setFont("Helvetica", 10)
        c.drawString(170, y_position, str(case_data['beneficiary_name']).upper())

        y_position -= 20
        c.setFont("Helvetica", 9)
        c.drawString(90, y_position, "Address: " + str(case_data['beneficiary_address']))

        y_position -= 25
        c.setFont("Helvetica-Bold", 10)
        c.drawString(60, y_position, "13. PLACE OF DEATH")
        c.setFont("Helvetica", 10)
        c.drawString(190, y_position, case_data.get('place_of_death', 'LOS ANGELES'))

        y_position -= 20
        c.setFont("Helvetica-Bold", 10)
        c.drawString(60, y_position, "14. FACILITY NAME")
        c.setFont("Helvetica", 10)
        facility = random.choice(['CEDARS-SINAI MEDICAL CENTER', 'UCLA MEDICAL CENTER',
                                 'USC MEDICAL CENTER', 'RESIDENCE', 'GOOD SAMARITAN HOSPITAL'])
        c.drawString(200, y_position, facility)

        y_position -= 25
        c.setFont("Helvetica-Bold", 10)
        c.drawString(60, y_position, "15. MANNER OF DEATH")
        c.setFont("Helvetica", 10)
        manner = random.choice(['NATURAL', 'ACCIDENT', 'PENDING', 'COULD NOT BE DETERMINED'])
        c.drawString(220, y_position, manner)

        y_position -= 25
        c.setFont("Helvetica-Bold", 10)
        c.drawString(60, y_position, "16. IMMEDIATE CAUSE OF DEATH")
        c.setFont("Helvetica", 9)
        cause = random.choice(['HYPERTENSION', 'CARDIAC ARREST', 'RESPIRATORY FAILURE',
                              'NATURAL CAUSES', 'COMPLICATIONS OF DIABETES'])
        c.drawString(90, y_position-12, cause)

        y_position -= 50
        c.setFont("Helvetica-Bold", 10)
        c.drawString(60, y_position, "CERTIFIER INFORMATION")
        y_position -= 18
        c.setFont("Helvetica", 9)
        certifier_name = fake.name()
        c.drawString(60, y_position, f"Name: {certifier_name}, M.D.")
        y_position -= 15
        c.drawString(60, y_position, f"License: G{random.randint(10000, 99999)}")
        y_position -= 15
        c.drawString(60, y_position, f"Date Certified: {case_data['date_of_death']}")

        # Blockchain verification if applicable
        if case_data['death_cert_type'] == 'blockchain':
            y_position -= 30
            c.setFont("Helvetica-Bold", 11)
            c.setFillColor(colors.HexColor('#0066CC'))
            c.drawString(60, y_position, "BLOCKCHAIN VERIFIED - TITAN SEAL")
            c.setFillColor(colors.black)
            c.setFont("Helvetica", 8)
            y_position -= 12
            c.drawString(60, y_position, f"Transaction Hash: {case_data['blockchain_hash'][:32]}")
            y_position -= 10
            c.drawString(60, y_position, case_data['blockchain_hash'][32:])

            # Add QR code
            qr = qrcode.QRCode(version=1, box_size=3, border=2)
            qr.add_data(case_data['blockchain_hash'])
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white")
            qr_path = os.path.join(case_dir, 'temp_qr.png')
            qr_img.save(qr_path)
            c.drawImage(qr_path, width-140, y_position-60, width=60, height=60)

        # Bottom section - Official certification
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(width/2, 150, "CERTIFIED COPY OF VITAL RECORD")
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(width/2, 135, "STATE OF CALIFORNIA, COUNTY OF LOS ANGELES")

        c.setFont("Helvetica", 9)
        cert_text = ("This is a true certified copy of the record on file at the County of Los Angeles "
                    "Department of Public Health if it bears the Registrar's signature in purple ink.")

        # Wrap text
        c.drawCentredString(width/2, 115, cert_text[:75])
        c.drawCentredString(width/2, 105, cert_text[75:])

        # Signature line
        c.setFont("Helvetica-Oblique", 14)
        c.drawString(80, 75, "Health Officer and Registrar")

        # Date stamp
        c.setFont("Helvetica-Bold", 12)
        c.setFillColor(colors.HexColor('#0033AA'))
        issue_date = datetime.now().strftime("%b %d, %Y").upper()
        c.drawRightString(width-100, 70, issue_date)

        # Barcode at bottom
        c.setFillColor(colors.black)
        c.setFont("Courier", 10)
        barcode_num = f"{random.randint(100000000, 999999999)}"
        c.drawCentredString(width/2, 45, f"||||| {barcode_num} |||||")

        # Warning text
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(width/2, 25, "ANY ALTERATION OR ERASURE VOIDS THIS CERTIFICATE")

        c.save()

        # Clean up temp QR
        if case_data['death_cert_type'] == 'blockchain':
            if os.path.exists(qr_path):
                os.remove(qr_path)

        return cert_path

    def generate_cnb_beneficiary_claim_form(self, case_data, case_dir, quality='high'):
        """
        Generate realistic CNB Custody beneficiary claim form matching the official format
        """

        form_path = os.path.join(case_dir, 'beneficiary_claim_form.pdf')
        c = canvas.Canvas(form_path, pagesize=letter)
        width, height = letter

        # Header - CNB Logo and title
        c.setFillColor(colors.HexColor('#C1272D'))  # CNB red color
        c.setFont("Helvetica-Bold", 24)
        c.drawString(60, height-60, "cnb")
        c.setFillColor(colors.HexColor('#666666'))
        c.setFont("Helvetica", 16)
        c.drawString(120, height-58, "CUSTODY")

        c.setFont("Helvetica", 10)
        c.drawString(60, height-75, "A DIVISION OF COMMUNITY NATIONAL BANK")

        # Form title (right side)
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 18)
        c.drawRightString(width-60, height-50, "BENEFICIARY CLAIM FORM")
        c.setFont("Helvetica", 10)
        c.drawRightString(width-60, height-67, "Effective for Deaths after 12/31/2019")
        c.setFont("Helvetica-Oblique", 9)
        c.drawRightString(width-60, height-80, "If death occurred before 1/1/20, a different form is required.")

        # Section 1: Deceased Account Owner Information
        y = height - 120
        c.setFillColor(colors.HexColor('#8B0000'))
        c.rect(40, y-15, width-80, 20, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(45, y-10, "1. DECEASED ACCOUNT OWNER INFORMATION")

        y -= 35
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 10)
        c.drawString(45, y, f"Full Name: {case_data['deceased_name']}")
        c.drawString(340, y, f"Account #: {case_data['account_number']}")
        c.drawRightString(width-45, y, f"Date of Death: {case_data['date_of_death']}")

        # Section 2: Beneficiary Information
        y -= 35
        c.setFillColor(colors.HexColor('#8B0000'))
        c.rect(40, y-15, width-80, 20, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(45, y-10, "2. BENEFICIARY INFORMATION")

        y -= 30
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 10)
        c.drawString(45, y, f"{case_data['beneficiary_name']}")
        c.drawString(340, y, "123-45-6789")
        c.drawRightString(width-45, y, case_data.get('beneficiary_dob', '00/00/0000'))

        y -= 12
        c.setFont("Helvetica", 8)
        c.drawString(45, y, "Name of Beneficiary")
        c.drawString(340, y, "SS# or Tax ID#")
        c.drawRightString(width-45, y, "Birth Date")

        y -= 20
        c.setFont("Helvetica", 10)
        address_parts = case_data['beneficiary_address'].split(',')
        c.drawString(45, y, address_parts[0] if len(address_parts) > 0 else case_data['beneficiary_address'])

        y -= 12
        c.setFont("Helvetica", 8)
        c.drawString(45, y, "Physical Address (required)")
        c.drawString(340, y, "City")
        c.drawString(450, y, "State")
        c.drawString(520, y, "Zip")

        y -= 20
        c.setFont("Helvetica", 10)
        # Occupation, phones
        occupation = random.choice(['Teacher', 'Engineer', 'Nurse', 'Accountant', 'Manager', 'Consultant'])
        c.drawString(45, y, occupation)
        c.drawString(180, y, str(case_data['beneficiary_phone']))

        y -= 12
        c.setFont("Helvetica", 8)
        c.drawString(45, y, "Occupation")
        c.drawString(180, y, "Main Phone (required)")
        c.drawString(340, y, "Secondary Phone")
        c.drawString(480, y, "Business Phone")

        y -= 20
        c.setFont("Helvetica", 10)
        # Citizenship
        c.rect(45, y-2, 10, 10, fill=1, stroke=1)
        c.drawString(60, y, "US Citizen")
        c.rect(140, y-2, 10, 10, fill=0, stroke=1)
        c.drawString(155, y, "Resident Alien")
        c.rect(250, y-2, 10, 10, fill=0, stroke=1)
        c.drawString(265, y, "Nonresident Alien")

        y -= 20
        c.drawString(45, y, f"Email Address: {case_data['beneficiary_email']}")
        c.drawRightString(width-45, y, f"Gender: {'Female' if random.random() > 0.5 else 'Male'}")

        # Section 3: Beneficiary Relationship and Election
        y -= 35
        c.setFillColor(colors.HexColor('#8B0000'))
        c.rect(40, y-15, width-80, 20, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(45, y-10, "3. BENEFICIARY RELATIONSHIP AND ELECTION")

        y -= 30
        c.setFillColor(colors.black)

        # Draw the two-column layout
        col1_x = 45
        col2_x = 320

        c.setFont("Helvetica-Bold", 10)
        c.drawString(col1_x, y, "Beneficiary Relationship:")
        c.drawString(col2_x, y, "Beneficiary Election Option:")

        y -= 20

        # Left column - Relationship checkboxes
        c.setFont("Helvetica-Bold", 9)
        c.drawString(col1_x, y, "A. Eligible Designated Beneficiary (EDB)")

        y -= 15
        c.setFont("Helvetica", 9)
        c.drawString(col1_x+5, y, "Please indicate relationship at the time of death:")

        y -= 15
        # Determine which box to check based on relationship
        rel = case_data['beneficiary_relationship']

        if rel == 'spouse':
            c.rect(col1_x+5, y-2, 8, 8, fill=1, stroke=1)
        else:
            c.rect(col1_x+5, y-2, 8, 8, fill=0, stroke=1)
        c.drawString(col1_x+18, y, "Surviving spouse")

        y -= 12
        if rel == 'child':
            c.rect(col1_x+5, y-2, 8, 8, fill=1, stroke=1)
        else:
            c.rect(col1_x+5, y-2, 8, 8, fill=0, stroke=1)
        c.drawString(col1_x+18, y, "Minor child of decedent")

        y -= 12
        c.rect(col1_x+5, y-2, 8, 8, fill=0, stroke=1)
        c.drawString(col1_x+18, y, "I am chronically ill or disabled")

        y -= 12
        if rel not in ['spouse', 'child']:
            c.rect(col1_x+5, y-2, 8, 8, fill=1, stroke=1)
        else:
            c.rect(col1_x+5, y-2, 8, 8, fill=0, stroke=1)
        c.drawString(col1_x+18, y, "I am a non-spouse less than 10 years younger")

        # Right column - Election options
        y_right = y + 60  # Reset to top of right column
        c.setFont("Helvetica-Bold", 9)

        if rel == 'spouse':
            c.drawString(col2_x, y_right, "Election Options for Surviving Spouse Only:")
            y_right -= 15
            c.setFont("Helvetica", 9)
            c.rect(col2_x, y_right-2, 8, 8, fill=0, stroke=1)
            c.drawString(col2_x+13, y_right, "Treat IRA as my own")
            y_right -= 12
            c.rect(col2_x, y_right-2, 8, 8, fill=0, stroke=1)
            c.drawString(col2_x+13, y_right, "Life Expectancy Payout - Establish Beneficiary IRA")
            y_right -= 12
            c.rect(col2_x, y_right-2, 8, 8, fill=1, stroke=1)
            c.drawString(col2_x+13, y_right, "10-Year Rule Payout - Establish Beneficiary IRA")
        else:
            c.drawString(col2_x, y_right, "Election Options for Non-Spouse EDB:")
            y_right -= 15
            c.setFont("Helvetica", 9)
            c.rect(col2_x, y_right-2, 8, 8, fill=0, stroke=1)
            c.drawString(col2_x+13, y_right, "Life Expectancy Payout - Establish Beneficiary IRA")
            y_right -= 12
            c.rect(col2_x, y_right-2, 8, 8, fill=1, stroke=1)
            c.drawString(col2_x+13, y_right, "10-Year Rule Payout - Establish Beneficiary IRA")

        # Section 4: RMD (if applicable)
        y = y - 60
        c.setFillColor(colors.HexColor('#8B0000'))
        c.rect(40, y-15, width-80, 20, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(45, y-10, "4. REQUIRED MINIMUM DISTRIBUTION (RMD) for Traditional or SEP IRAs:")

        y -= 25
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 8)
        c.drawString(45, y, "Complete this section if the decedent turned 70 ½ prior to 2020, turned 72 after 2019, or turned 73 after 2022.")

        y -= 15
        c.setFont("Helvetica", 9)
        c.rect(45, y-2, 8, 8, fill=0, stroke=1)
        c.drawString(58, y, "I am aware that the decedent did not meet the entire RMD from the IRA held at CNB Custody prior to death.")

        y -= 12
        c.rect(45, y-2, 8, 8, fill=1, stroke=1)
        c.drawString(58, y, "I would like to take the remaining RMD that the decedent did not meet prior to death.")

        # Section 5: Signature
        y -= 35
        c.setFillColor(colors.HexColor('#8B0000'))
        c.rect(40, y-15, width-80, 20, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(45, y-10, "5. SIGNATURE")

        y -= 30
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 8)
        disclaimer = ("I understand that it is my responsibility to satisfy the IRS minimum distribution requirements. "
                     "I certify that Community National Bank has not provided me with tax, legal, financial, or estate planning advice.")
        c.drawString(45, y, disclaimer[:95])
        y -= 10
        c.drawString(45, y, disclaimer[95:])

        y -= 25
        c.setFont("Helvetica-Oblique", 14)
        c.drawString(45, y, str(case_data['beneficiary_name']))
        c.line(45, y-5, 350, y-5)
        c.setFont("Helvetica", 8)
        c.drawString(45, y-15, "Beneficiary Signature")
        c.drawString(380, y, f"Date: {datetime.now().strftime('%m/%d/%Y')}")
        c.line(420, y-5, 550, y-5)

        y -= 35
        c.setFont("Helvetica", 9)
        c.drawString(45, y, "Sworn to and subscribed before me on: _________________________, 20____.")

        y -= 25
        c.drawString(45, y, "Notary Signature: _________________________________________")
        c.drawString(400, y, "(Seal)")

        # Footer
        c.setFont("Helvetica", 8)
        c.drawCentredString(width/2, 40, "225 MAIN ST - PO BOX 225 | SENECA, KS 66538 | P: 800.680.0340 | F: 785.336.2214")
        c.drawCentredString(width/2, 28, "BENECLAIMS@CNBCUSTODY.COM | CNBCUSTODY.COM")

        c.save()
        return form_path

    def generate_california_drivers_license(self, case_data, case_dir, quality='high'):
        """
        Generate realistic California driver's license (front and back) matching the 2018+ Real ID format
        """

        # Front of license
        front_path = os.path.join(case_dir, 'drivers_license_front.png')
        back_path = os.path.join(case_dir, 'drivers_license_back.png')

        # Standard CA DL dimensions (3.375" x 2.125" at 300 DPI)
        width_px = 1013
        height_px = 638

        # FRONT OF LICENSE
        front = Image.new('RGB', (width_px, height_px), color='#F5E6D3')
        draw_front = ImageDraw.Draw(front)

        # Try to load fonts
        try:
            title_font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf', 48)
            large_font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf', 36)
            medium_font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf', 28)
            body_font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 24)
            small_font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 18)
            tiny_font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 14)
        except:
            # Fallback
            title_font = large_font = medium_font = body_font = small_font = tiny_font = ImageFont.load_default()

        # Background gradient effect (simple version)
        for i in range(height_px):
            alpha = int(255 * (1 - i/height_px * 0.3))
            for j in range(width_px):
                if (i + j) % 4 == 0:
                    draw_front.point((j, i), fill=(245, 230, 211))

        # Top blue bar
        draw_front.rectangle([0, 0, width_px, 120], fill='#003D7A')

        # "California" text
        draw_front.text((40, 20), "California", font=title_font, fill='white')

        # "USA" badge
        draw_front.text((750, 15), "USA", font=medium_font, fill='#FFD700')

        # "DRIVER LICENSE" text
        draw_front.text((40, 72), "DRIVER LICENSE", font=large_font, fill='#FFD700')

        # Gold star (Real ID indicator)
        draw_front.polygon([(950, 40), (970, 80), (1000, 90), (975, 110), (985, 145),
                           (950, 125), (915, 145), (925, 110), (900, 90), (930, 80)],
                          fill='#FFD700', outline='white')

        # California bear silhouette (simplified)
        draw_front.ellipse([870, 50, 920, 100], fill='#8B6914', outline='#6B5414')

        # Photo box
        draw_front.rectangle([50, 145, 330, 510], fill='#CCCCCC', outline='#333333', width=3)
        draw_front.text((140, 310), "PHOTO", font=medium_font, fill='#666666')

        # License information
        x_offset = 360
        y_offset = 145

        # DL Number
        dl_number = f"D{random.randint(1000000, 9999999)}"
        draw_front.text((x_offset, y_offset), "DL", font=small_font, fill='#000000')
        draw_front.text((x_offset + 50, y_offset), dl_number, font=medium_font, fill='#1a1a1a')
        draw_front.text((750, y_offset), "CLASS C", font=small_font, fill='#000000')

        y_offset += 45

        # Expiration date
        exp_date = fake.date_between(start_date='+1y', end_date='+5y').strftime('%m/%d/%Y')
        draw_front.text((x_offset, y_offset), "EXP", font=small_font, fill='#000000')
        draw_front.text((x_offset + 50, y_offset), exp_date, font=body_font, fill='#C00000')
        draw_front.text((750, y_offset), "END NONE", font=small_font, fill='#000000')

        y_offset += 45

        # Name
        draw_front.text((x_offset, y_offset), "LN", font=tiny_font, fill='#000000')
        last_name = case_data['beneficiary_name'].split()[-1].upper()
        draw_front.text((x_offset + 30, y_offset), last_name, font=body_font, fill='#000000')

        y_offset += 35
        draw_front.text((x_offset, y_offset), "FN", font=tiny_font, fill='#000000')
        first_name = case_data['beneficiary_name'].split()[0].upper()
        draw_front.text((x_offset + 30, y_offset), first_name, font=body_font, fill='#000000')

        y_offset += 45

        # Address
        address = case_data['beneficiary_address'][:35]
        draw_front.text((x_offset, y_offset), address, font=small_font, fill='#000000')

        y_offset += 45

        # DOB
        draw_front.text((x_offset, y_offset), "DOB", font=small_font, fill='#000000')
        draw_front.text((x_offset + 70, y_offset), case_data.get('beneficiary_dob', '00/00/0000'),
                       font=body_font, fill='#C00000')

        y_offset += 40

        # RSTR
        draw_front.text((x_offset, y_offset), "RSTR NONE", font=small_font, fill='#000000')

        y_offset += 45

        # Physical characteristics - use sex from deceased persona
        sex = case_data.get('deceased_sex', random.choice(['M', 'F']))
        hair = random.choice(['BRN', 'BLK', 'BLD', 'RED'])
        eyes = random.choice(['BRN', 'BLU', 'GRN', 'HAZ'])

        # Realistic height distribution: most people are between 5'2" and 6'4"
        # Males tend to be taller, females shorter
        if sex == 'M':
            height_total_inches = int(random.gauss(70, 3))  # ~5'10" avg for men
        else:
            height_total_inches = int(random.gauss(64, 2.5))  # ~5'4" avg for women
        height_total_inches = max(58, min(78, height_total_inches))  # 4'10" to 6'6"
        height_ft = height_total_inches // 12
        height_in = height_total_inches % 12

        draw_front.text((x_offset, y_offset), "SEX", font=small_font, fill='#000000')
        draw_front.text((x_offset + 60, y_offset), sex, font=body_font, fill='#000000')

        draw_front.text((x_offset + 150, y_offset), "HAIR", font=small_font, fill='#000000')
        draw_front.text((x_offset + 220, y_offset), hair, font=body_font, fill='#000000')

        draw_front.text((x_offset + 320, y_offset), "EYES", font=small_font, fill='#000000')
        draw_front.text((x_offset + 390, y_offset), eyes, font=body_font, fill='#000000')

        y_offset += 35

        draw_front.text((x_offset, y_offset), "HGT", font=small_font, fill='#000000')
        draw_front.text((x_offset + 60, y_offset), f"{height_ft}'-{height_in:02d}\"",
                       font=body_font, fill='#000000')

        weight = random.randint(110, 250)
        draw_front.text((x_offset + 150, y_offset), "WGT", font=small_font, fill='#000000')
        draw_front.text((x_offset + 220, y_offset), f"{weight} lb", font=body_font, fill='#000000')

        # ISS date
        iss_date = fake.date_between(start_date='-5y', end_date='today').strftime('%m/%d/%Y')
        draw_front.text((x_offset + 320, y_offset), "ISS", font=small_font, fill='#000000')
        draw_front.text((x_offset + 370, y_offset), iss_date, font=small_font, fill='#000000')

        # DD section at bottom right
        draw_front.text((750, 520), f"DD {random.randint(10000000, 99999999)}",
                       font=tiny_font, fill='#666666')

        # Barcode at bottom
        draw_front.rectangle([50, 530, width_px-50, 600], fill='white', outline='#000000', width=2)
        for i in range(60, width_px-60, 4):
            if random.random() > 0.5:
                draw_front.rectangle([i, 535, i+2, 595], fill='#000000')

        # Apply quality degradation if needed
        if quality == 'medium':
            front = front.resize((int(width_px * 0.7), int(height_px * 0.7)), Image.Resampling.BILINEAR)
            front = front.resize((width_px, height_px), Image.Resampling.BILINEAR)
        elif quality == 'low':
            front = front.resize((int(width_px * 0.4), int(height_px * 0.4)), Image.Resampling.BILINEAR)
            front = front.resize((width_px, height_px), Image.Resampling.NEAREST)

        front.save(front_path, quality=95 if quality == 'high' else 75 if quality == 'medium' else 50)

        # BACK OF LICENSE
        back = Image.new('RGB', (width_px, height_px), color='#F5E6D3')
        draw_back = ImageDraw.Draw(back)

        # Barcode at top
        draw_back.rectangle([0, 0, width_px, 100], fill='black')
        for i in range(10, width_px-10, 3):
            if random.random() > 0.3:
                draw_back.line([(i, 10), (i, 90)], fill='white', width=2)

        # Class information
        y_back = 130
        draw_back.text((80, y_back), f"CLASS: C - Veh w/GVWR ≤26000, No M/C",
                      font=small_font, fill='#000000')
        y_back += 25
        draw_back.text((80, y_back), "ENDORSEMENTS: None", font=small_font, fill='#000000')
        y_back += 25
        draw_back.text((80, y_back), "RESTRICTIONS: None", font=small_font, fill='#000000')

        # 2D Barcode
        y_back += 60
        draw_back.rectangle([80, y_back, 450, y_back+120], fill='white', outline='#000000', width=2)
        # Simulate 2D barcode pattern
        for i in range(85, 445, 3):
            for j in range(y_back+5, y_back+115, 3):
                if random.random() > 0.5:
                    draw_back.rectangle([i, j, i+2, j+2], fill='#000000')

        # License disclaimer text
        disclaimer_x = 480
        disclaimer_y = y_back + 20
        draw_back.text((disclaimer_x, disclaimer_y),
                      "This license is issued as a license",
                      font=tiny_font, fill='#000000')
        disclaimer_y += 15
        draw_back.text((disclaimer_x, disclaimer_y),
                      "to drive a motor vehicle; it does",
                      font=tiny_font, fill='#000000')
        disclaimer_y += 15
        draw_back.text((disclaimer_x, disclaimer_y),
                      "not establish eligibility for employment,",
                      font=tiny_font, fill='#000000')
        disclaimer_y += 15
        draw_back.text((disclaimer_x, disclaimer_y),
                      "voter registration, or public benefits.",
                      font=tiny_font, fill='#000000')

        # Audit number
        y_back += 150
        audit_num = random.randint(10000000, 99999999)
        draw_back.text((700, y_back), str(audit_num), font=small_font, fill='#666666')

        # Rev date and inventory number
        y_back += 30
        draw_back.text((650, y_back), "Rev 04/16/2010", font=tiny_font, fill='#666666')
        y_back += 15
        draw_back.text((620, y_back), f"102731{random.randint(10000000, 99999999)}",
                      font=tiny_font, fill='#666666')

        # Apply quality degradation
        if quality == 'medium':
            back = back.resize((int(width_px * 0.7), int(height_px * 0.7)), Image.Resampling.BILINEAR)
            back = back.resize((width_px, height_px), Image.Resampling.BILINEAR)
        elif quality == 'low':
            back = back.resize((int(width_px * 0.4), int(height_px * 0.4)), Image.Resampling.BILINEAR)
            back = back.resize((width_px, height_px), Image.Resampling.NEAREST)

        back.save(back_path, quality=95 if quality == 'high' else 75 if quality == 'medium' else 50)

        return front_path, back_path


# Use the same SyntheticDataGenerator class from before but with the new DocumentGenerator
class SyntheticDataGenerator:
    """Main generator orchestrating document and database creation"""

    def __init__(self, db_path='benebridge.db', output_dir='synthetic_cases'):
        self.db_path = db_path
        self.output_dir = output_dir
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.used_ssns = set()
        self.used_case_numbers = set()
        self.doc_generator = RealisticDocumentGenerator(output_dir)

        os.makedirs(output_dir, exist_ok=True)

    def generate_ssn(self):
        """Generate SSN from test range"""
        available_ssns = [ssn for ssn in TEST_SSN_RANGE if ssn not in self.used_ssns]
        if available_ssns:
            ssn_num = random.choice(available_ssns)
            self.used_ssns.add(ssn_num)
            ssn = f"{str(ssn_num)[:3]}-{str(ssn_num)[3:5]}-{str(ssn_num)[5:]}"
        else:
            ssn = f"{random.randint(900, 999)}-{random.randint(10, 99)}-{random.randint(1000, 9999)}"
        return ssn

    def generate_deceased_persona(self):
        """Generate deceased person"""
        age_at_death = int(random.gauss(75, 10))
        age_at_death = max(18, min(105, age_at_death))

        date_of_death = fake.date_between(start_date='-1y', end_date='today')
        date_of_birth = date_of_death - timedelta(days=age_at_death * 365)

        # Generate sex first, then name matching that sex
        sex = random.choice(['M', 'F'])
        if sex == 'M':
            name = fake.name_male()
        else:
            name = fake.name_female()

        return {
            'name': name,
            'sex': sex,
            'ssn': self.generate_ssn(),
            'dob': date_of_birth.strftime('%Y-%m-%d'),
            'dod': date_of_death.strftime('%Y-%m-%d'),
            'age': age_at_death,
            'place_of_death': f"{fake.city()}, CA"
        }

    def generate_beneficiary_persona(self, deceased_name):
        """Generate beneficiary"""
        relationship = random.choice(['spouse', 'child', 'sibling', 'other'])

        if relationship in ['spouse', 'child']:
            last_name = deceased_name.split()[-1]
            first_name = fake.first_name()
            name = f"{first_name} {last_name}"
        else:
            name = fake.name()

        age = random.randint(18, 75)
        dob = datetime.now() - timedelta(days=age * 365)

        return {
            'name': name,
            'dob': dob.strftime('%Y-%m-%d'),
            'email': fake.email(),
            'phone': fake.phone_number(),
            'address': f"{fake.street_address()}, {fake.city()}, CA {fake.zipcode()}",
            'relationship': relationship
        }

    def generate_account_balance(self, account_type):
        """Generate realistic balance"""
        if account_type == 'IRA':
            balance = random.lognormvariate(11.3, 1.2)
        elif account_type == '401k':
            balance = random.lognormvariate(11.7, 1.3)
        elif account_type == 'Life Insurance':
            balance = random.choice([25000, 50000, 100000, 250000, 500000, 1000000])
        elif account_type == 'Trust':
            balance = random.lognormvariate(12.5, 1.5)
        else:
            balance = random.lognormvariate(11.5, 1.4)

        return round(balance / 100) * 100

    def determine_complexity(self, account_type, balance, relationship):
        """Determine case complexity"""
        score = 0
        if account_type in ['Trust', '401k']:
            score += 2
        elif account_type == 'Life Insurance':
            score += 1

        if balance > 500000:
            score += 2
        elif balance > 100000:
            score += 1

        if relationship not in ['spouse', 'child']:
            score += 1

        if score >= 4:
            return 'complex'
        elif score >= 2:
            return 'moderate'
        else:
            return 'simple'

    def generate_case_number(self, institution_code='CNB'):
        """Generate unique case number"""
        year = datetime.now().year
        for _ in range(100):
            random_num = random.randint(1000, 9999)
            case_number = f"{institution_code}-{year}-{random_num}"
            if case_number not in self.used_case_numbers:
                self.used_case_numbers.add(case_number)
                return case_number

        timestamp = int(datetime.now().timestamp() * 1000) % 10000
        case_number = f"{institution_code}-{year}-{timestamp}"
        self.used_case_numbers.add(case_number)
        return case_number

    def generate_access_code(self):
        """Generate access code"""
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

    def generate_certificate_number(self, death_date, cert_type):
        """Generate death certificate number"""
        year = death_date.split('-')[0]
        county = random.choice(['LA', 'SF', 'SD', 'OC', 'SAC', 'ALA'])
        number = random.randint(10000, 99999)
        return f"{year}-CA-{county}-{number}"

    def generate_blockchain_hash(self):
        """Generate Ethereum hash"""
        return '0x' + ''.join(random.choices('0123456789abcdef', k=64))

    def create_complete_case(self, is_fraud=False):
        """Create complete case with all documents"""

        # Generate personas
        deceased = self.generate_deceased_persona()
        beneficiary = self.generate_beneficiary_persona(deceased['name'])

        # Account details
        account_type = random.choices(
            list(ACCOUNT_TYPES.keys()),
            weights=list(ACCOUNT_TYPES.values())
        )[0]

        balance = self.generate_account_balance(account_type)
        account_number = f"{account_type[:3].upper()}-{random.randint(100000, 999999)}"

        # Complexity
        complexity = self.determine_complexity(account_type, balance, beneficiary['relationship'])

        # Certificate details
        cert_type = random.choices(
            list(CERT_TYPES.keys()),
            weights=list(CERT_TYPES.values())
        )[0]

        cert_number = self.generate_certificate_number(deceased['dod'], cert_type)
        blockchain_hash = self.generate_blockchain_hash() if cert_type == 'blockchain' else None

        # Case metadata
        case_number = self.generate_case_number()
        access_code = self.generate_access_code()
        submission_date = datetime.now().isoformat()

        # Document quality
        quality = random.choices(
            list(DOCUMENT_QUALITY.keys()),
            weights=list(DOCUMENT_QUALITY.values())
        )[0]

        # Fraud handling
        if is_fraud:
            fraud_type = random.choice([
                'forged_document',
                'identity_theft',
                'duplicate_claim',
                'beneficiary_fraud'
            ])
            if fraud_type == 'duplicate_claim':
                deceased['ssn'] = random.choice(list(self.used_ssns)) if self.used_ssns else deceased['ssn']
        else:
            fraud_type = None

        # Assemble case data
        case_data = {
            'case_number': case_number,
            'access_code': access_code,
            'deceased_name': deceased['name'],
            'deceased_ssn': deceased['ssn'],
            'deceased_sex': deceased['sex'],
            'date_of_birth': deceased['dob'],
            'date_of_death': deceased['dod'],
            'age_at_death': deceased['age'],
            'place_of_death': deceased['place_of_death'],
            'beneficiary_name': beneficiary['name'],
            'beneficiary_dob': beneficiary['dob'],
            'beneficiary_email': beneficiary['email'],
            'beneficiary_phone': beneficiary['phone'],
            'beneficiary_address': beneficiary['address'],
            'beneficiary_relationship': beneficiary['relationship'],
            'account_number': account_number,
            'account_type': account_type,
            'account_balance': balance,
            'financial_institution': 'Community National Bank',
            'death_cert_type': cert_type,
            'death_certificate_number': cert_number,
            'blockchain_hash': blockchain_hash,
            'status': 'pending',
            'submission_date': submission_date,
            'complexity': complexity,
            'is_fraud': is_fraud,
            'fraud_type': fraud_type,
            'document_quality': quality
        }

        # Create case directory
        case_dir = os.path.join(self.output_dir, case_number)
        os.makedirs(case_dir, exist_ok=True)

        # Generate documents
        death_cert_path = self.doc_generator.generate_california_death_certificate(case_data, case_dir, quality)
        claim_form_path = self.doc_generator.generate_cnb_beneficiary_claim_form(case_data, case_dir, quality)
        dl_front, dl_back = self.doc_generator.generate_california_drivers_license(case_data, case_dir, quality)

        # Save case metadata as JSON
        metadata = {
            **case_data,
            'documents': {
                'death_certificate': os.path.basename(death_cert_path),
                'beneficiary_claim_form': os.path.basename(claim_form_path),
                'drivers_license_front': os.path.basename(dl_front),
                'drivers_license_back': os.path.basename(dl_back)
            },
            'ground_truth': {
                'is_fraud': is_fraud,
                'fraud_type': fraud_type,
                'expected_outcome': 'deny' if is_fraud else 'approve',
                'complexity_level': complexity,
                'document_quality': quality
            }
        }

        with open(os.path.join(case_dir, 'metadata.json'), 'w') as f:
            json.dump(metadata, f, indent=2)

        return case_data, case_dir

    def insert_case_to_db(self, case_data):
        """Insert case to database"""
        self.cursor.execute('''
            INSERT INTO cases (
                case_number, deceased_name, deceased_ssn, deceased_sex, date_of_death,
                beneficiary_name, beneficiary_email, beneficiary_phone, beneficiary_address,
                account_number, account_type, account_balance, financial_institution,
                death_cert_type, blockchain_hash, death_certificate_number,
                status, submission_date, access_code, workflow_stage, priority
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            case_data['case_number'],
            case_data['deceased_name'],
            case_data['deceased_ssn'],
            case_data['deceased_sex'],
            case_data['date_of_death'],
            case_data['beneficiary_name'],
            case_data['beneficiary_email'],
            case_data['beneficiary_phone'],
            case_data['beneficiary_address'],
            case_data['account_number'],
            case_data['account_type'],
            case_data['account_balance'],
            case_data['financial_institution'],
            case_data['death_cert_type'],
            case_data['blockchain_hash'],
            case_data['death_certificate_number'],
            case_data['status'],
            case_data['submission_date'],
            case_data['access_code'],
            1,
            'medium'
        ))

        case_id = self.cursor.lastrowid
        self.create_workflow_tasks(case_id, case_data['account_type'])
        return case_id

    def create_workflow_tasks(self, case_id, account_type):
        """Create workflow tasks"""
        tasks = []

        if account_type == 'IRA':
            tasks = [
                ('Initial Review', 'Review submitted documents', 1),
                ('Document Verification', 'Verify death certificate and ID', 2),
                ('Tax Calculation', 'Calculate tax withholding', 3),
                ('Final Approval', 'Final approval for payment', 4)
            ]
        elif account_type == '401k':
            tasks = [
                ('Initial Review', 'Review documents', 1),
                ('Document Verification', 'Verify certificates', 2),
                ('Spousal Consent', 'Check spousal waiver', 3),
                ('ERISA Compliance', 'ERISA compliance check', 3),
                ('Tax Calculation', 'Calculate withholding', 4),
                ('Final Approval', 'Dual approval required', 5)
            ]
        elif account_type == 'Trust':
            tasks = [
                ('Initial Review', 'Review trust documents', 1),
                ('Document Verification', 'Verify documentation', 2),
                ('Trustee Verification', 'Verify trustee authority', 3),
                ('Legal Review', 'Legal compliance', 4),
                ('Final Approval', 'Executive approval', 5)
            ]
        else:
            tasks = [
                ('Initial Review', 'Review documentation', 1),
                ('Document Verification', 'Verify certificate', 2),
                ('Compliance Check', 'Standard compliance', 3),
                ('Final Approval', 'Approve distribution', 4)
            ]

        for task_name, description, stage in tasks:
            self.cursor.execute('''
                INSERT INTO workflow_tasks (
                    case_id, task_name, task_description, stage, completed
                ) VALUES (?, ?, ?, ?, 0)
            ''', (case_id, task_name, description, stage))

    def generate_dataset(self, num_cases=500):
        """Generate complete dataset"""
        print(f"\nGenerating {num_cases} REALISTIC synthetic cases with official-format documents...")
        print("=" * 80)
        print("Documents will match:")
        print("  - California Death Certificate (LA County format)")
        print("  - CNB Custody Beneficiary Claim Form")
        print("  - California Real ID Driver's License (front & back)")
        print("=" * 80)

        stats = {
            'simple': 0,
            'moderate': 0,
            'complex': 0,
            'fraud': 0,
            'high_quality': 0,
            'medium_quality': 0,
            'low_quality': 0
        }

        for i in range(num_cases):
            is_fraud = random.random() < FRAUD_RATE

            case_data, case_dir = self.create_complete_case(is_fraud=is_fraud)
            case_id = self.insert_case_to_db(case_data)

            # Update stats
            if is_fraud:
                stats['fraud'] += 1
            else:
                stats[case_data['complexity']] += 1

            stats[f"{case_data['document_quality']}_quality"] += 1

            if (i + 1) % 50 == 0:
                self.conn.commit()
                print(f"Created {i + 1}/{num_cases} cases...")

        self.conn.commit()

        print("\n" + "=" * 80)
        print("Dataset Generation Complete!")
        print("=" * 80)
        print(f"\nCase Distribution:")
        print(f"  Simple cases:   {stats['simple']} ({stats['simple']/num_cases*100:.1f}%)")
        print(f"  Moderate cases: {stats['moderate']} ({stats['moderate']/num_cases*100:.1f}%)")
        print(f"  Complex cases:  {stats['complex']} ({stats['complex']/num_cases*100:.1f}%)")
        print(f"  Fraud cases:    {stats['fraud']} ({stats['fraud']/num_cases*100:.1f}%)")
        print(f"\nDocument Quality:")
        print(f"  High quality:   {stats['high_quality']} ({stats['high_quality']/num_cases*100:.1f}%)")
        print(f"  Medium quality: {stats['medium_quality']} ({stats['medium_quality']/num_cases*100:.1f}%)")
        print(f"  Low quality:    {stats['low_quality']} ({stats['low_quality']/num_cases*100:.1f}%)")
        print(f"\nTotal cases: {num_cases}")
        print(f"Total documents: {num_cases * 4} (death cert, claim form, DL front, DL back)")
        print(f"Storage location: {self.output_dir}/")

        # Sample cases
        print("\n" + "=" * 80)
        print("Sample Cases for Testing:")
        print("=" * 80)

        sample = self.cursor.execute('''
            SELECT case_number, access_code, beneficiary_name, account_type,
                   account_balance, death_cert_type
            FROM cases ORDER BY RANDOM() LIMIT 5
        ''').fetchall()

        for case in sample:
            print(f"\nCase: {case[0]}")
            print(f"  Access Code: {case[1]}")
            print(f"  Beneficiary: {case[2]}")
            print(f"  Account: {case[3]} - ${case[4]:,.2f}")
            print(f"  Certificate: {case[5]}")
            print(f"  Documents: synthetic_cases/{case[0]}/")

    def close(self):
        """Close connection"""
        self.conn.close()


if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("BeneBridge REALISTIC Synthetic Data Generator")
    print("=" * 80)
    print("Generating documents matching official formats")
    print("=" * 80)

    generator = SyntheticDataGenerator()

    # Clear existing
    print("\nClearing existing data...")
    generator.cursor.execute('DELETE FROM cases')
    generator.cursor.execute('DELETE FROM workflow_tasks')
    generator.conn.commit()

    # Generate
    generator.generate_dataset(num_cases=500)

    generator.close()

    print("\n✓ COMPLETE! Realistic documents ready for POC and dissertation.")
