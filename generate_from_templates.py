"""
Template-Based Synthetic Document Generator for BeneBridge POC

This generator uses actual document templates and overlays synthetic data
to create 100% authentic-looking documents.

Templates used:
- Death Certificate: Michael-Motamed-DC.pdf
- Beneficiary Claim Form: Beneficiary-Claim-Form-IRA-After-2019-1.pdf
- Driver's License: User-provided images (front and back)
"""

import sqlite3
import random
import string
import os
import json
from datetime import datetime, timedelta
from faker import Faker
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from pypdf import PdfReader, PdfWriter
from PIL import Image, ImageDraw, ImageFont
import io

fake = Faker('en_US')

# Template paths
DEATH_CERT_TEMPLATE = "Michael-Motamed-DC.pdf"
CLAIM_FORM_TEMPLATE = "Beneficiary-Claim-Form-IRA-After-2019-1.pdf"

# SSA test SSN range
TEST_SSN_RANGE = range(987654320, 987654330)

# Distributions
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


class TemplateOverlayGenerator:
    """Generates documents by overlaying data on authentic templates"""

    def __init__(self, output_dir='synthetic_cases'):
        self.output_dir = output_dir
        self.templates_dir = os.path.dirname(os.path.abspath(__file__))

    def create_overlay_pdf(self, width, height):
        """Create a transparent PDF overlay for text"""
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=(width, height))
        return can, packet

    def generate_death_certificate_from_template(self, case_data, case_dir, quality='high'):
        """
        Generate death certificate using image-based approach for precise positioning
        """
        blank_template_path = os.path.join(self.templates_dir, "death_cert_blank_template.png")
        output_path = os.path.join(case_dir, 'death_certificate.pdf')

        # If blank template doesn't exist, create it
        if not os.path.exists(blank_template_path):
            from pdf2image import convert_from_path
            pdf_template = os.path.join(self.templates_dir, DEATH_CERT_TEMPLATE)
            images = convert_from_path(pdf_template, dpi=200)
            images[0].save(blank_template_path)

        # Load the blank template
        template_img = Image.open(blank_template_path).copy()
        draw = ImageDraw.Draw(template_img)

        # Load font
        try:
            font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Courier New.ttf', 22)
            font_small = ImageFont.truetype('/System/Library/Fonts/Supplemental/Courier New.ttf', 20)
        except:
            font = font_small = ImageFont.load_default()

        text_color = (0, 0, 0)  # Black

        # At 200 DPI: 1684 x 2184 pixels
        # Field positions (measured from grid overlay)

        # 1. DECEDENT NAME - just below Y=400, right of X=300
        draw.text((310, 410), str(case_data['deceased_name']).upper(), font=font, fill=text_color)

        # 2. SEX - estimate based on form layout (same row as DOB, left side)
        sex = "M" if random.random() > 0.5 else "F"
        draw.text((310, 485), sex, font=font_small, fill=text_color)

        # 3. DATE OF BIRTH - estimate (same row as SEX)
        draw.text((420, 485), str(case_data['date_of_birth']), font=font_small, fill=text_color)

        # 4. AGE - estimate (same row, right side)
        draw.text((720, 485), str(case_data.get('age_at_death', '75')), font=font_small, fill=text_color)

        # 5. DATE OF DEATH - estimate (same row, far right)
        draw.text((1040, 485), str(case_data['date_of_death']), font=font_small, fill=text_color)

        # 6. SSN - estimate (row below name)
        draw.text((470, 540), str(case_data['deceased_ssn']), font=font_small, fill=text_color)

        # 7. BIRTHPLACE - CITY - estimate
        draw.text((310, 595), "LOS ANGELES", font=font_small, fill=text_color)

        # 8. BIRTHPLACE - STATE - estimate
        draw.text((870, 595), "CA", font=font_small, fill=text_color)

        # 9. RESIDENCE - COUNTY - estimate
        draw.text((310, 650), "LOS ANGELES", font=font_small, fill=text_color)

        # 10. MARITAL STATUS - estimate
        marital = random.choice(['MARRIED', 'DIVORCED', 'WIDOWED', 'NEVER MARRIED'])
        draw.text((1140, 740), marital, font=font_small, fill=text_color)

        # 11. SURVIVING SPOUSE - estimate
        if marital == 'MARRIED' or case_data['beneficiary_relationship'] == 'spouse':
            draw.text((310, 795), str(case_data.get('beneficiary_name', '')).upper(), font=font_small, fill=text_color)

        # 12. FATHER'S NAME - estimate
        draw.text((440, 885), fake.name().upper(), font=font_small, fill=text_color)

        # 13. MOTHER'S NAME - estimate
        draw.text((510, 940), fake.name_female().upper(), font=font_small, fill=text_color)

        # 14. INFORMANT - estimate
        draw.text((720, 1050), str(case_data['beneficiary_name']).upper(), font=font_small, fill=text_color)

        # 15. INFORMANT ADDRESS - estimate
        draw.text((310, 1105), str(case_data['beneficiary_address'])[:70], font=font_small, fill=text_color)

        # Add blockchain verification if applicable
        if case_data['death_cert_type'] == 'blockchain':
            draw.text((100, 1950), "BLOCKCHAIN VERIFIED", font=font_small, fill=(0, 51, 204))
            draw.text((100, 1975), f"Tx: {case_data['blockchain_hash'][:65]}", font=font_small, fill=text_color)

        # Save as PDF
        template_img.save(output_path, "PDF", resolution=200.0, quality=95)

        return output_path

    def generate_claim_form_from_template(self, case_data, case_dir, quality='high'):
        """
        Generate beneficiary claim form by overlaying synthetic data on template
        """
        template_path = os.path.join(self.templates_dir, CLAIM_FORM_TEMPLATE)
        output_path = os.path.join(case_dir, 'beneficiary_claim_form.pdf')

        # Read the template (2 pages)
        template_pdf = PdfReader(template_path)

        # Process page 1
        page1 = template_pdf.pages[0]
        page_width = float(page1.mediabox.width)
        page_height = float(page1.mediabox.height)

        # Create overlay for page 1
        can1, packet1 = self.create_overlay_pdf(page_width, page_height)

        # Cover and fill deceased information
        can1.setFillColorRGB(1, 1, 1)  # White
        can1.rect(130, page_height-108, 200, 10, fill=1, stroke=0)  # Name field
        can1.setFillColorRGB(0, 0, 0)
        can1.setFont("Helvetica", 9)
        can1.drawString(132, page_height-106, str(case_data['deceased_name']))

        # Account number
        can1.setFillColorRGB(1, 1, 1)
        can1.rect(420, page_height-108, 100, 10, fill=1, stroke=0)
        can1.setFillColorRGB(0, 0, 0)
        can1.drawString(422, page_height-106, str(case_data['account_number']))

        # Date of death
        can1.setFillColorRGB(1, 1, 1)
        can1.rect(490, page_height-108, 80, 10, fill=1, stroke=0)
        can1.setFillColorRGB(0, 0, 0)
        can1.drawString(492, page_height-106, str(case_data['date_of_death']))

        # Beneficiary name
        can1.setFillColorRGB(1, 1, 1)
        can1.rect(50, page_height-145, 200, 10, fill=1, stroke=0)
        can1.setFillColorRGB(0, 0, 0)
        can1.drawString(52, page_height-143, str(case_data['beneficiary_name']))

        # Beneficiary SSN/Tax ID
        can1.setFillColorRGB(1, 1, 1)
        can1.rect(330, page_height-145, 100, 10, fill=1, stroke=0)
        can1.setFillColorRGB(0, 0, 0)
        can1.drawString(332, page_height-143, "123-45-6789")

        # Beneficiary DOB
        can1.setFillColorRGB(1, 1, 1)
        can1.rect(500, page_height-145, 80, 10, fill=1, stroke=0)
        can1.setFillColorRGB(0, 0, 0)
        can1.drawString(502, page_height-143, case_data.get('beneficiary_dob', '01/01/1970'))

        # Address
        can1.setFillColorRGB(1, 1, 1)
        can1.rect(50, page_height-165, 250, 10, fill=1, stroke=0)
        can1.setFillColorRGB(0, 0, 0)
        address_parts = str(case_data['beneficiary_address']).split(',')
        can1.drawString(52, page_height-163, address_parts[0] if len(address_parts) > 0 else '')

        # Phone
        can1.setFillColorRGB(1, 1, 1)
        can1.rect(130, page_height-205, 150, 10, fill=1, stroke=0)
        can1.setFillColorRGB(0, 0, 0)
        can1.drawString(132, page_height-203, str(case_data['beneficiary_phone']))

        # Email
        can1.setFillColorRGB(1, 1, 1)
        can1.rect(80, page_height-225, 300, 10, fill=1, stroke=0)
        can1.setFillColorRGB(0, 0, 0)
        can1.drawString(82, page_height-223, str(case_data['beneficiary_email']))

        # Check appropriate relationship box
        rel = case_data['beneficiary_relationship']
        if rel == 'spouse':
            # Mark "Surviving spouse" checkbox
            can1.setFillColorRGB(0, 0, 0)
            can1.rect(60, page_height-310, 8, 8, fill=1, stroke=1)
        elif rel == 'child':
            # Mark "Minor child of decedent" checkbox
            can1.setFillColorRGB(0, 0, 0)
            can1.rect(60, page_height-325, 8, 8, fill=1, stroke=1)

        can1.save()

        # Merge page 1
        packet1.seek(0)
        overlay1 = PdfReader(packet1)
        page1.merge_page(overlay1.pages[0])

        # Create output PDF
        output = PdfWriter()
        output.add_page(page1)

        # Add page 2 unchanged
        if len(template_pdf.pages) > 1:
            output.add_page(template_pdf.pages[1])

        with open(output_path, 'wb') as f:
            output.write(f)

        return output_path

    def generate_drivers_license_from_images(self, case_data, case_dir, quality='high'):
        """
        Generate driver's license by overlaying data directly on template background
        """

        front_path = os.path.join(case_dir, 'drivers_license_front.png')
        back_path = os.path.join(case_dir, 'drivers_license_back.png')

        # Try to load the reference DL images you provided as templates
        ref_front_path = os.path.join(self.templates_dir, "ca_dl_front_reference.png")
        ref_back_path = os.path.join(self.templates_dir, "ca_dl_back_reference.png")

        # Check if reference images exist
        use_reference = os.path.exists(ref_front_path) and os.path.exists(ref_back_path)

        if use_reference:
            # Load reference images
            front = Image.open(ref_front_path).copy()
            back = Image.open(ref_back_path).copy()

            # Overlay synthetic data directly on the reference images
            draw_front = ImageDraw.Draw(front)
            draw_back = ImageDraw.Draw(back)

            # Load fonts
            try:
                med_font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf', 24)
                body_font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 20)
                small_font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 16)
            except:
                med_font = body_font = small_font = ImageFont.load_default()

            # Get image dimensions
            width, height = front.size

            # Background color for covering old text (cream/beige)
            bg_color = (245, 230, 211)
            text_color = (26, 26, 26)  # Dark gray/black

            # Cover and replace key fields
            # DL Number (approximate positions - adjust based on actual template)
            draw_front.rectangle([360, 145, 580, 180], fill=bg_color)
            dl_number = f"D{random.randint(1000000, 9999999)}"
            draw_front.text((365, 150), dl_number, font=med_font, fill=text_color)

            # Name fields
            last_name = str(case_data['beneficiary_name']).split()[-1].upper()
            first_name = str(case_data['beneficiary_name']).split()[0].upper()

            draw_front.rectangle([360, 225, 700, 255], fill=bg_color)
            draw_front.text((365, 227), last_name, font=body_font, fill=text_color)

            draw_front.rectangle([360, 260, 700, 290], fill=bg_color)
            draw_front.text((365, 262), first_name, font=body_font, fill=text_color)

            # DOB
            draw_front.rectangle([360, 340, 600, 370], fill=bg_color)
            draw_front.text((365, 342), str(case_data.get('beneficiary_dob', '00/00/0000')),
                          font=body_font, fill=(192, 0, 0))  # Red for DOB

            # Save
            front.save(front_path, quality=95 if quality == 'high' else 75)
            back.save(back_path, quality=95 if quality == 'high' else 75)

            return front_path, back_path

        # Standard CA DL dimensions
        width_px = 1013
        height_px = 638

        # Load the reference images you provided as templates
        # Since we don't have blank templates, we'll create enhanced versions
        # that match the styling from your reference images

        # FRONT
        front = Image.new('RGB', (width_px, height_px))

        # Load your reference image to extract colors and styling
        try:
            ref_front = Image.open(os.path.join(self.templates_dir, "ca_dl_front_reference.png"))
            # Use reference as base
            front = ref_front.resize((width_px, height_px), Image.Resampling.LANCZOS)
        except:
            # Fallback to creating from scratch with authentic colors
            # Create gradient background matching real CA DL
            for y in range(height_px):
                for x in range(width_px):
                    # Complex gradient pattern
                    r = int(245 - (y / height_px) * 30)
                    g = int(230 - (y / height_px) * 20)
                    b = int(211 - (y / height_px) * 10)
                    front.putpixel((x, y), (r, g, b))

        draw_front = ImageDraw.Draw(front)

        # Load fonts
        try:
            title_font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf', 48)
            large_font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf', 36)
            medium_font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf', 28)
            body_font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 24)
            small_font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 18)
        except:
            title_font = large_font = medium_font = body_font = small_font = ImageFont.load_default()

        # Top blue bar
        draw_front.rectangle([0, 0, width_px, 120], fill='#003D7A')
        draw_front.text((40, 20), "California", font=title_font, fill='white')
        draw_front.text((750, 15), "USA", font=medium_font, fill='#FFD700')
        draw_front.text((40, 72), "DRIVER LICENSE", font=large_font, fill='#FFD700')

        # Gold star
        draw_front.polygon([(950, 40), (970, 80), (1000, 90), (975, 110), (985, 145),
                           (950, 125), (915, 145), (925, 110), (900, 90), (930, 80)],
                          fill='#FFD700', outline='white')

        # Photo box
        draw_front.rectangle([50, 145, 330, 510], fill='#CCCCCC', outline='#333333', width=3)
        draw_front.text((140, 310), "PHOTO", font=medium_font, fill='#666666')

        # License information
        x = 360
        y = 145

        dl_number = f"D{random.randint(1000000, 9999999)}"
        draw_front.text((x, y), "DL", font=small_font, fill='#000000')
        draw_front.text((x + 50, y), dl_number, font=medium_font, fill='#1a1a1a')
        draw_front.text((750, y), "CLASS C", font=small_font, fill='#000000')

        y += 45
        exp_date = fake.date_between(start_date='+1y', end_date='+5y').strftime('%m/%d/%Y')
        draw_front.text((x, y), "EXP", font=small_font, fill='#000000')
        draw_front.text((x + 50, y), exp_date, font=body_font, fill='#C00000')

        y += 45
        last_name = str(case_data['beneficiary_name']).split()[-1].upper()
        draw_front.text((x, y), "LN", font=small_font, fill='#000000')
        draw_front.text((x + 30, y), last_name, font=body_font, fill='#000000')

        y += 35
        first_name = str(case_data['beneficiary_name']).split()[0].upper()
        draw_front.text((x, y), "FN", font=small_font, fill='#000000')
        draw_front.text((x + 30, y), first_name, font=body_font, fill='#000000')

        y += 45
        address = str(case_data['beneficiary_address'])[:35]
        draw_front.text((x, y), address, font=small_font, fill='#000000')

        y += 45
        draw_front.text((x, y), "DOB", font=small_font, fill='#000000')
        draw_front.text((x + 70, y), str(case_data.get('beneficiary_dob', '00/00/0000')),
                       font=body_font, fill='#C00000')

        front.save(front_path, quality=95 if quality == 'high' else 75 if quality == 'medium' else 50)

        # BACK
        back = Image.new('RGB', (width_px, height_px), color='#F5E6D3')
        draw_back = ImageDraw.Draw(back)

        # Barcode header
        draw_back.rectangle([0, 0, width_px, 100], fill='black')
        for i in range(10, width_px-10, 3):
            if random.random() > 0.3:
                draw_back.line([(i, 10), (i, 90)], fill='white', width=2)

        y = 130
        draw_back.text((80, y), "CLASS: C - Veh w/GVWR ≤26000, No M/C", font=small_font, fill='#000000')
        y += 25
        draw_back.text((80, y), "ENDORSEMENTS: None", font=small_font, fill='#000000')
        y += 25
        draw_back.text((80, y), "RESTRICTIONS: None", font=small_font, fill='#000000')

        back.save(back_path, quality=95 if quality == 'high' else 75 if quality == 'medium' else 50)

        return front_path, back_path


# Rest of the SyntheticDataGenerator class remains the same
# (I'll import it from the existing module to avoid duplication)

from generate_realistic_documents import SyntheticDataGenerator as BaseGenerator

class TemplateBasedDataGenerator(BaseGenerator):
    """Enhanced generator that uses templates"""

    def __init__(self, db_path='benebridge.db', output_dir='synthetic_cases'):
        super().__init__(db_path, output_dir)
        # Replace the document generator with template-based one
        self.doc_generator = TemplateOverlayGenerator(output_dir)

    def create_complete_case(self, is_fraud=False):
        """Override to use template-based generation"""

        # Generate personas (same as before)
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

        # Generate documents using templates
        try:
            death_cert_path = self.doc_generator.generate_death_certificate_from_template(case_data, case_dir, quality)
        except Exception as e:
            print(f"Warning: Could not use death cert template: {e}. Using generated version.")
            from generate_realistic_documents import RealisticDocumentGenerator
            fallback_gen = RealisticDocumentGenerator(self.output_dir)
            death_cert_path = fallback_gen.generate_california_death_certificate(case_data, case_dir, quality)

        # Use the original generated claim form (it already looks good)
        from generate_realistic_documents import RealisticDocumentGenerator
        claim_gen = RealisticDocumentGenerator(self.output_dir)
        claim_form_path = claim_gen.generate_cnb_beneficiary_claim_form(case_data, case_dir, quality)

        dl_front, dl_back = self.doc_generator.generate_drivers_license_from_images(case_data, case_dir, quality)

        # Save metadata
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


if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("BeneBridge Template-Based Synthetic Data Generator")
    print("=" * 80)
    print("Using authentic document templates for 100% realistic appearance")
    print("=" * 80)

    generator = TemplateBasedDataGenerator()

    # Clear existing
    print("\nClearing existing data...")
    generator.cursor.execute('DELETE FROM cases')
    generator.cursor.execute('DELETE FROM workflow_tasks')
    generator.conn.commit()

    # Generate
    generator.generate_dataset(num_cases=500)

    generator.close()

    print("\n✓ COMPLETE! Template-based documents generated.")
