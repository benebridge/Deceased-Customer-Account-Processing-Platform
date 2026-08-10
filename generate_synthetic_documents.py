"""
Comprehensive Synthetic Document Generator for BeneBridge POC

Following Chapter 4 methodology, this generates:
- 500 complete case scenarios
- Death certificates (PDF) - both physical and blockchain-verified
- Beneficiary ID documents (driver's license images)
- Claim application forms (PDF)
- Supporting documents as needed
- Organized folder structure: synthetic_cases/CASE-NUMBER/

Each case includes ground truth labels for ML training and evaluation.
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
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from PIL import Image, ImageDraw, ImageFont
import qrcode

# Initialize Faker
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

# Document quality variations for ML training
DOCUMENT_QUALITY = {
    'high': 0.70,      # 70% - Clean scans, good lighting
    'medium': 0.20,    # 20% - Slightly degraded
    'low': 0.10        # 10% - Poor quality, testing OCR limits
}


class DocumentGenerator:
    """Generates realistic legal and financial documents"""

    def __init__(self, output_dir='synthetic_cases'):
        self.output_dir = output_dir
        self.styles = getSampleStyleSheet()

        # Create custom styles
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )

        self.header_style = ParagraphStyle(
            'CustomHeader',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#333333'),
            spaceAfter=10,
            fontName='Helvetica-Bold'
        )

        self.body_style = ParagraphStyle(
            'CustomBody',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=6,
            fontName='Helvetica'
        )

    def generate_death_certificate(self, case_data, case_dir, quality='high'):
        """Generate realistic death certificate PDF"""

        cert_path = os.path.join(case_dir, 'death_certificate.pdf')
        doc = SimpleDocTemplate(cert_path, pagesize=letter)
        story = []

        # State seal placeholder
        story.append(Spacer(1, 0.5*inch))

        # Title
        title = Paragraph("STATE OF CALIFORNIA<br/>CERTIFICATE OF DEATH", self.title_style)
        story.append(title)
        story.append(Spacer(1, 0.3*inch))

        # Certificate number
        cert_num = Paragraph(
            f"<b>Certificate Number:</b> {case_data['death_certificate_number']}",
            self.header_style
        )
        story.append(cert_num)
        story.append(Spacer(1, 0.2*inch))

        # Decedent information table
        decedent_data = [
            ['DECEDENT INFORMATION', ''],
            ['Full Legal Name:', case_data['deceased_name']],
            ['Social Security Number:', case_data['deceased_ssn']],
            ['Date of Birth:', case_data['date_of_birth']],
            ['Date of Death:', case_data['date_of_death']],
            ['Age at Death:', str(case_data.get('age_at_death', 'N/A'))],
            ['Place of Death:', case_data.get('place_of_death', 'Los Angeles County, CA')],
        ]

        t1 = Table(decedent_data, colWidths=[2.5*inch, 4*inch])
        t1.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ]))
        story.append(t1)
        story.append(Spacer(1, 0.3*inch))

        # Certifier information
        certifier_data = [
            ['CERTIFIER INFORMATION', ''],
            ['Certifier Name:', fake.name()],
            ['Title:', random.choice(['Medical Examiner', 'Attending Physician', 'Coroner'])],
            ['License Number:', f"CA-{random.randint(100000, 999999)}"],
            ['Date Certified:', case_data['date_of_death']],
        ]

        t2 = Table(certifier_data, colWidths=[2.5*inch, 4*inch])
        t2.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ]))
        story.append(t2)
        story.append(Spacer(1, 0.4*inch))

        # Blockchain verification (if applicable)
        if case_data['death_cert_type'] == 'blockchain':
            story.append(Spacer(1, 0.2*inch))
            blockchain_text = Paragraph(
                f"<b>BLOCKCHAIN VERIFIED</b><br/>"
                f"Transaction Hash: {case_data['blockchain_hash']}<br/>"
                f"Verified via Titan Seal Network<br/>"
                f"Timestamp: {case_data['date_of_death']} 14:32:18 UTC",
                self.body_style
            )
            story.append(blockchain_text)

            # Add QR code for blockchain verification
            qr = qrcode.QRCode(version=1, box_size=3, border=2)
            qr.add_data(case_data['blockchain_hash'])
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white")
            qr_path = os.path.join(case_dir, 'temp_qr.png')
            qr_img.save(qr_path)
            story.append(RLImage(qr_path, width=1*inch, height=1*inch))

        # Official seal placeholder
        story.append(Spacer(1, 0.3*inch))
        seal_text = Paragraph(
            "<i>Official State Seal</i><br/>"
            "This is a certified copy of the original death certificate.<br/>"
            f"Issued: {datetime.now().strftime('%B %d, %Y')}",
            ParagraphStyle('Seal', parent=self.body_style, alignment=TA_CENTER, fontSize=8)
        )
        story.append(seal_text)

        # Build PDF
        doc.build(story)

        # Clean up temp QR code
        if case_data['death_cert_type'] == 'blockchain':
            if os.path.exists(qr_path):
                os.remove(qr_path)

        # Apply quality degradation if needed
        if quality != 'high':
            self._degrade_pdf_quality(cert_path, quality)

        return cert_path

    def generate_drivers_license(self, case_data, case_dir, quality='high'):
        """Generate realistic driver's license image"""

        # Create realistic driver's license
        width, height = 1050, 650  # Standard ID card proportions
        img = Image.new('RGB', (width, height), color='#F0E6D2')
        draw = ImageDraw.Draw(img)

        # Try to use system fonts, fallback to default
        try:
            title_font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf', 32)
            header_font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf', 24)
            body_font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 20)
            small_font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 16)
        except:
            title_font = ImageFont.load_default()
            header_font = ImageFont.load_default()
            body_font = ImageFont.load_default()
            small_font = ImageFont.load_default()

        # Header bar
        draw.rectangle([0, 0, width, 80], fill='#003D7A')
        draw.text((30, 20), "CALIFORNIA", font=title_font, fill='white')
        draw.text((30, 50), "DRIVER LICENSE", font=header_font, fill='#FFD700')

        # Photo placeholder
        draw.rectangle([50, 120, 300, 450], fill='#CCCCCC', outline='#666666', width=2)
        draw.text((120, 270), "PHOTO", font=body_font, fill='#666666')

        # License information
        y_offset = 120
        fields = [
            ("DL", f"D{random.randint(1000000, 9999999)}"),
            ("EXP", fake.date_between(start_date='+1y', end_date='+5y').strftime('%m/%d/%Y')),
            ("DOB", case_data['beneficiary_dob']),
            ("NAME", case_data['beneficiary_name'].upper()),
            ("ADDRESS", case_data['beneficiary_address'][:40]),
            ("SEX", random.choice(['M', 'F'])),
            ("HAIR", random.choice(['BRN', 'BLK', 'BLD', 'RED'])),
            ("EYES", random.choice(['BRN', 'BLU', 'GRN', 'HAZ'])),
            ("HGT", f"{random.randint(5, 6)}'-{random.randint(0, 11):02d}\""),
        ]

        for label, value in fields:
            draw.text((350, y_offset), f"{label}:", font=body_font, fill='#000000')
            draw.text((480, y_offset), str(value), font=body_font, fill='#1a1a1a')
            y_offset += 35

        # Barcode placeholder
        draw.rectangle([50, 480, 950, 550], fill='white', outline='#000000', width=2)
        for i in range(50, 950, 3):
            if random.random() > 0.5:
                draw.rectangle([i, 485, i+2, 545], fill='#000000')

        # Issue date
        draw.text((50, 570), f"ISS: {fake.date_between(start_date='-5y', end_date='today').strftime('%m/%d/%Y')}",
                 font=small_font, fill='#666666')

        # Save base image
        dl_path = os.path.join(case_dir, 'beneficiary_id.png')

        # Apply quality degradation
        if quality == 'medium':
            # Add slight blur and compression
            img = img.resize((int(width * 0.8), int(height * 0.8)), Image.Resampling.BILINEAR)
            img = img.resize((width, height), Image.Resampling.BILINEAR)
            img.save(dl_path, quality=75)
        elif quality == 'low':
            # Significant degradation
            img = img.resize((int(width * 0.5), int(height * 0.5)), Image.Resampling.BILINEAR)
            img = img.resize((width, height), Image.Resampling.NEAREST)
            # Add noise
            pixels = img.load()
            for i in range(width):
                for j in range(height):
                    if random.random() < 0.02:
                        pixels[i, j] = tuple([min(255, c + random.randint(-30, 30)) for c in pixels[i, j]])
            img.save(dl_path, quality=50)
        else:
            img.save(dl_path, quality=95)

        return dl_path

    def generate_claim_application(self, case_data, case_dir, quality='high'):
        """Generate claim application form PDF"""

        app_path = os.path.join(case_dir, 'claim_application.pdf')
        doc = SimpleDocTemplate(app_path, pagesize=letter)
        story = []

        # Title
        story.append(Spacer(1, 0.5*inch))
        title = Paragraph("DEATH CLAIM BENEFIT APPLICATION", self.title_style)
        story.append(title)
        story.append(Spacer(1, 0.2*inch))

        # Institution info
        inst_info = Paragraph(
            f"<b>{case_data['financial_institution']}</b><br/>"
            f"Case Number: {case_data['case_number']}<br/>"
            f"Submission Date: {case_data['submission_date'][:10]}",
            self.body_style
        )
        story.append(inst_info)
        story.append(Spacer(1, 0.3*inch))

        # Deceased account holder information
        section1 = Paragraph("SECTION 1: DECEASED ACCOUNT HOLDER INFORMATION", self.header_style)
        story.append(section1)

        deceased_data = [
            ['Full Name:', case_data['deceased_name']],
            ['Social Security Number:', case_data['deceased_ssn']],
            ['Date of Birth:', case_data['date_of_birth']],
            ['Date of Death:', case_data['date_of_death']],
            ['Account Number:', case_data['account_number']],
            ['Account Type:', case_data['account_type']],
            ['Account Balance:', f"${case_data['account_balance']:,.2f}"],
        ]

        t1 = Table(deceased_data, colWidths=[2.5*inch, 4*inch])
        t1.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ]))
        story.append(t1)
        story.append(Spacer(1, 0.3*inch))

        # Beneficiary information
        section2 = Paragraph("SECTION 2: BENEFICIARY INFORMATION", self.header_style)
        story.append(section2)

        beneficiary_data = [
            ['Full Name:', case_data['beneficiary_name']],
            ['Relationship to Deceased:', case_data['beneficiary_relationship'].title()],
            ['Email Address:', case_data['beneficiary_email']],
            ['Phone Number:', case_data['beneficiary_phone']],
            ['Mailing Address:', case_data['beneficiary_address']],
            ['Date of Birth:', case_data.get('beneficiary_dob', 'N/A')],
        ]

        t2 = Table(beneficiary_data, colWidths=[2.5*inch, 4*inch])
        t2.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ]))
        story.append(t2)
        story.append(Spacer(1, 0.3*inch))

        # Distribution election
        section3 = Paragraph("SECTION 3: DISTRIBUTION ELECTION", self.header_style)
        story.append(section3)

        distribution_text = Paragraph(
            f"I elect to receive the account balance as a: <b>{random.choice(['Lump Sum Payment', 'Inherited IRA', 'Five-Year Rule Distribution'])}</b><br/>"
            f"Tax Withholding Election: <b>{random.choice(['10%', '20%', 'No Withholding'])}</b>",
            self.body_style
        )
        story.append(distribution_text)
        story.append(Spacer(1, 0.4*inch))

        # Signature section
        section4 = Paragraph("SECTION 4: CERTIFICATION AND SIGNATURE", self.header_style)
        story.append(section4)

        cert_text = Paragraph(
            "I certify under penalty of perjury that the information provided in this application is true and correct to the best of my knowledge. "
            "I understand that any false statements may result in denial of the claim and potential legal action.",
            self.body_style
        )
        story.append(cert_text)
        story.append(Spacer(1, 0.3*inch))

        # Signature line
        sig_data = [
            ['Beneficiary Signature:', '_' * 50, 'Date:', '_' * 20],
        ]
        t3 = Table(sig_data, colWidths=[1.8*inch, 2.5*inch, 0.7*inch, 1.5*inch])
        t3.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
        ]))
        story.append(t3)

        # Build PDF
        doc.build(story)

        if quality != 'high':
            self._degrade_pdf_quality(app_path, quality)

        return app_path

    def _degrade_pdf_quality(self, pdf_path, quality):
        """Simulate scanning degradation on PDF (placeholder)"""
        # In a real implementation, this would:
        # 1. Convert PDF to images
        # 2. Apply degradation (blur, noise, compression)
        # 3. Convert back to PDF
        # For now, we'll just note the quality in metadata
        pass


class SyntheticDataGenerator:
    """Main generator orchestrating document and database creation"""

    def __init__(self, db_path='benebridge.db', output_dir='synthetic_cases'):
        self.db_path = db_path
        self.output_dir = output_dir
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.used_ssns = set()
        self.used_case_numbers = set()
        self.doc_generator = DocumentGenerator(output_dir)

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

    def generate_ssn(self):
        """Generate SSN from test range"""
        available_ssns = [ssn for ssn in TEST_SSN_RANGE if ssn not in self.used_ssns]
        if available_ssns:
            ssn_num = random.choice(available_ssns)
            self.used_ssns.add(ssn_num)
            ssn = f"{str(ssn_num)[:3]}-{str(ssn_num)[3:5]}-{str(ssn_num)[5:]}"
        else:
            # Fallback to fictional SSN
            ssn = f"{random.randint(900, 999)}-{random.randint(10, 99)}-{random.randint(1000, 9999)}"
        return ssn

    def generate_deceased_persona(self):
        """Generate deceased person"""
        age_at_death = int(random.gauss(75, 10))
        age_at_death = max(18, min(105, age_at_death))

        date_of_death = fake.date_between(start_date='-1y', end_date='today')
        date_of_birth = date_of_death - timedelta(days=age_at_death * 365)

        return {
            'name': fake.name(),
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

        # Generate beneficiary DOB (must be 18+)
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
        county = random.choice(['SF', 'LA', 'SD', 'OC', 'SAC', 'ALA'])
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

        # Document quality (for ML training diversity)
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
        death_cert_path = self.doc_generator.generate_death_certificate(case_data, case_dir, quality)
        id_path = self.doc_generator.generate_drivers_license(case_data, case_dir, quality)
        app_path = self.doc_generator.generate_claim_application(case_data, case_dir, quality)

        # Save case metadata as JSON (ground truth)
        metadata = {
            **case_data,
            'documents': {
                'death_certificate': os.path.basename(death_cert_path),
                'beneficiary_id': os.path.basename(id_path),
                'claim_application': os.path.basename(app_path)
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
                case_number, deceased_name, deceased_ssn, date_of_death,
                beneficiary_name, beneficiary_email, beneficiary_phone, beneficiary_address,
                account_number, account_type, account_balance, financial_institution,
                death_cert_type, blockchain_hash, death_certificate_number,
                status, submission_date, access_code, workflow_stage, priority
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            case_data['case_number'],
            case_data['deceased_name'],
            case_data['deceased_ssn'],
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
        print(f"Generating {num_cases} synthetic cases with documents...")
        print("=" * 70)

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

        print("\n" + "=" * 70)
        print("Dataset Generation Complete!")
        print("=" * 70)
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
        print(f"Total documents: {num_cases * 3}")
        print(f"Storage location: {self.output_dir}/")

        # Sample cases
        print("\n" + "=" * 70)
        print("Sample Cases for Testing:")
        print("=" * 70)

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
    print("BeneBridge Synthetic Data Generator")
    print("=" * 70)
    print("This will generate 500 complete case scenarios with documents")
    print("=" * 70)

    generator = SyntheticDataGenerator()

    # Clear existing
    print("\nClearing existing data...")
    generator.cursor.execute('DELETE FROM cases')
    generator.cursor.execute('DELETE FROM workflow_tasks')
    generator.conn.commit()

    # Generate
    generator.generate_dataset(num_cases=500)

    generator.close()

    print("\n✓ Complete! Ready for POC testing and ML training.")
